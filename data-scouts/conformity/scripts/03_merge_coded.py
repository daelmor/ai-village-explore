"""Merge the coded windows (out/coded/*.json) into decision and position tables, and machine-check every row.

Checks per position: the cited event_index exists, its speaker is the coded agent, and the quote is an exact
substring of that message. Rows failing a check are kept with `check` != ok and excluded from all rates.
Writes out/positions.csv (one row per decision x agent), out/decisions.csv (one row per decision with counts,
winner, unanimity flags, agents present, deep link) and out/coding_checks.csv.
Usage: ./venv/bin/python3 -I data-scouts/conformity/scripts/03_merge_coded.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import pandas as pd  # noqa: E402

c = v.chat().set_index("event_index")
w = pd.read_csv(v.OUT / "windows.csv").set_index("window_id")
roster = v.roster()
fam = {n: ("Claude" if ("claude" in n.lower() or "opus" in n.lower()) else "OpenAI" if n.lower().startswith(("gpt", "o1", "o3", "o4"))
           else "Gemini" if "gemini" in n.lower() else "Other") for n in roster.name}


def norm(o):
    return " + ".join(sorted(x.strip().lower() for x in str(o).split(" + "))) if o is not None else ""


def agrees(option, winner):
    """A position agrees with the winner if it is the winner, or (approval vote) its approved set contains it."""
    o = norm(option)
    return bool(winner) and (o == winner or winner in o.split(" + "))


OV = pd.read_csv(v.CASE / "decision_overrides.csv").fillna("")
OV = {r.decision_id: (r.action, r.value, r.reason) for r in OV.itertuples()}


pos, dec, missing = [], [], []
for wid in w.index:
    f = v.OUT / "coded" / f"{wid}.json"
    if not f.exists():
        missing.append(wid)
        continue
    j = json.loads(f.read_text())
    for d in j.get("decisions", []):
        did = f"{wid}-{d['local_id']}"
        act, val, why = OV.get(did, ("", "", ""))
        if act == "exclude":
            continue
        side = dict([val.split("=")]) if act == "same_side" else {}
        d["winner"] = side.get(norm(d.get("winner")), d.get("winner"))
        for p in d.get("positions", []):
            for k in ("initial_option", "final_option"):
                p[k] = side.get(norm(p.get(k)), p.get(k))
        winner = norm(d.get("winner")) if d.get("winner") and d.get("winner_basis") != "none" else ""
        declared = winner
        if act == "no_winner":
            winner = ""
        if act == "dissent_vs":
            winner = val
        rows = []
        for p in d.get("positions", []):
            chk = "ok"
            for side in ("initial", "final"):
                ei, q = p.get(f"{side}_ei"), p.get(f"{side}_quote") or ""
                if ei not in c.index:
                    chk = f"{side}_ei not in chat"
                elif c.at[ei, "speaker"] != p["agent"]:
                    chk = f"{side} speaker is {c.at[ei, 'speaker']}"
                elif q and q not in c.at[ei, "content"]:
                    chk = f"{side} quote not found"
                if chk != "ok":
                    break
            rows.append(dict(decision_id=did, window_id=wid, agent=p["agent"], family=fam.get(p["agent"], "Other"),
                             initial_option=norm(p.get("initial_option")), initial_ei=p.get("initial_ei"),
                             final_option=norm(p.get("final_option")), final_ei=p.get("final_ei"),
                             self=bool(p.get("self")), abstain=bool(p.get("abstain")) or norm(p.get("initial_option")) == "abstain",
                             initial_quote=p.get("initial_quote"), final_quote=p.get("final_quote"), check=chk))
        P = pd.DataFrame(rows)
        ok = P[(P.check == "ok") & ~P.abstain] if len(P) else P
        n = len(ok)
        if not winner and n and act != "no_winner":   # nothing declared: plurality of final positions, if unique
            vc = ok.final_option.value_counts()
            if len(vc) == 1 or vc.iloc[0] > vc.iloc[1]:
                winner = vc.index[0]
        if n:
            ok = ok.assign(initial_agrees=[agrees(o, winner) for o in ok.initial_option],
                           final_agrees=[agrees(o, winner) for o in ok.final_option]).sort_values("initial_ei")
            t0 = c.at[int(ok.initial_ei.min()), "ts"]
            close_ei = int(max([e for e in [d.get("winner_ei"), ok.final_ei.max()] if e is not None and e == e]))
            t1 = c.at[close_ei, "ts"] if close_ei in c.index else c.at[int(ok.final_ei.max()), "ts"]
            room = c.at[int(ok.initial_ei.min()), "room"]
            win = c[(c.room == room) & (c.ts >= t0 - pd.Timedelta(hours=2)) & (c.ts <= t1) & (c.speaker_type == "agent")]
            present = win.speaker.nunique()
            first = ok.iloc[0]
            for r in ok.itertuples():
                pos.append({**{k: getattr(r, k) for k in P.columns}, "initial_agrees": r.initial_agrees, "final_agrees": r.final_agrees,
                            "dissent": bool(winner) and not r.initial_agrees,
                            "abandoned_in_window": bool(winner) and not r.initial_agrees and r.final_agrees,
                            "utc": v.fmt_ts(c.at[int(r.initial_ei), "ts"]), "link": v.deep_link(c.at[int(r.initial_ei), "ts"])})
        for r in (P[(P.check != "ok") | P.abstain].itertuples() if len(P) else []):
            pos.append({**{k: getattr(r, k) for k in P.columns}})
        dec.append(dict(
            decision_id=did, window_id=wid, room=w.at[wid, "room"], goal=w.at[wid, "goal"], kind=d.get("kind"),
            kind_detail=d.get("kind_detail") or "", question=d.get("question"), blind=bool(d.get("blind")),
            round_of=d.get("round_of"), opened_by=d.get("opened_by"), winner=winner, winner_basis=d.get("winner_basis"),
            declared_outcome=declared, override=(act + ": " + why) if act else "",
            n_coded=len(P), n_failed_check=int((P.check != "ok").sum()) if len(P) else 0,
            n_abstain=int((P.abstain & (P.check == "ok")).sum()) if len(P) else 0, n_positions=n,
            n_present=present if n else None,
            n_agree_final=int(ok.final_agrees.sum()) if n else 0, n_dissent_initial=int((~ok.initial_agrees).sum()) if n and winner else 0,
            n_dissent_final=int((~ok.final_agrees).sum()) if n and winner else 0,
            n_self=int(ok.self.sum()) if n else 0,
            unanimous_final=bool(n and winner and ok.final_agrees.all()),
            never_contested=bool(n and winner and ok.initial_agrees.all()),
            first_position_agent=first.agent if n else None, first_position_won=bool(n and winner and first.initial_agrees),
            winner_share_final=float(ok.final_agrees.mean()) if n and winner else None,
            first_ei=int(ok.initial_ei.min()) if n else None, utc=v.fmt_ts(t0) if n else None, link=v.deep_link(t0) if n else None,
            year=int(t0.year) if n else None, reported_tally=d.get("reported_tally") or "", notes=d.get("notes") or ""))
P = pd.DataFrame(pos)
D = pd.DataFrame(dec).sort_values("first_ei")
P.to_csv(v.OUT / "positions.csv", index=False)
D.to_csv(v.OUT / "decisions.csv", index=False)
chk = P.groupby("check").size().rename("positions").reset_index()
chk.to_csv(v.OUT / "coding_checks.csv", index=False)
print("windows coded:", len(w) - len(missing), "missing:", missing)
print("decisions coded:", len(D), "| with >= 3 checked positions:", int((D.n_positions >= 3).sum()),
      "| with a winner:", int(((D.n_positions >= 3) & (D.winner != "")).sum()))
print(chk.to_string(index=False))
