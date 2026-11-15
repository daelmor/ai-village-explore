"""Step 7: the correction design (HYPOTHESIS.md addendum, H7).

adam's message ei 137163 (2025-12-09 20:59:04 UTC) told all agents that their "friction" reports were almost always
operator error and named Gemini 3 Pro and Gemini 2.5 Pro as particularly prone to them. For every friction-lexicon
term and every mechanically drawn control term: which agents held it in memory in the 48 h before the correction
(holders, the denominator) and which still had it 1 / 7 / 30 days later (survival, the numerator), split into the
two named agents and the bystanders. Level of every count: (term, agent) pairs.

Reads   out/fx_terms.csv, out/fx_origins.csv, out/fx_memory_agent.csv, out/fx_memory_daily.csv, out/fx_memory_lines.csv,
        core/out/memories_index.parquet  (run 06_friction_terms.py and 04_trace_memes.py --tag fx first)
Writes  out/correction_terms.csv     every term: origin, eligibility, reason if excluded
        out/correction_pairs.csv     one row per (eligible term, cohort agent)
        out/correction_summary.csv   holders / survivors by term set, group and definition, with bootstrap CIs over terms
        out/correction_by_agent.csv  the same per agent
        out/correction_lines.csv     for every surviving pair, the matching memory line that lived longest after the
                                     correction, with snapshot ids (input to the hand verification)
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/07_correction_survival.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

TC = v.CORRECTION_TS
H48, D1, D7, D30 = pd.Timedelta(hours=48), pd.Timedelta(days=1), pd.Timedelta(days=7), pd.Timedelta(days=30)
WINDOW_START = pd.Timestamp("2025-11-20")

T = pd.read_csv(v.OUT / "fx_terms.csv", keep_default_na=False)
O = pd.read_csv(v.OUT / "fx_origins.csv", keep_default_na=False)
O["t0"] = pd.to_datetime(O.origin_utc.str.replace(" UTC", ""))
MA = pd.read_csv(v.OUT / "fx_memory_agent.csv")
MD = pd.read_csv(v.OUT / "fx_memory_daily.csv")
for col in ("first_match_ts", "last_match_ts"):
    MD[col] = pd.to_datetime(MD[col], format="ISO8601")

idx = v.memories_index()
names = idx.drop_duplicates("agent_id").set_index("agent_id").agent.to_dict()
cohort = [aid for aid, g in idx.groupby("agent_id")
          if ((g.ts >= TC - H48) & (g.ts <= TC)).any() and (g.ts >= TC + D30).any()]
print("cohort:", sorted(names[a] for a in cohort))

# --- term eligibility ---------------------------------------------------------------------------------
terms = T.merge(O[["meme_id", "origin_event_index", "origin_utc", "origin_speaker", "origin_agent_id", "t0", "n_chat_messages"]], on="meme_id", how="left")
pre = MA[MA.n_match_before_origin > 0].merge(terms[["meme_id", "origin_agent_id"]], on="meme_id")
pre_other = pre[pre.agent_id != pre.origin_agent_id].groupby("meme_id").agent.apply(lambda s: ", ".join(sorted(s)))


def reason(r):
    if pd.isna(r.t0):
        return "no chat match"
    if not (WINDOW_START <= r.t0 < TC):
        return "first chat use outside 2025-11-20 .. correction"
    if r.meme_id in pre_other.index:
        return "in another agent's memory before the first chat use: " + pre_other[r.meme_id]
    return ""


terms["excluded"] = terms.apply(reason, axis=1)
terms.drop(columns=["t0", "origin_agent_id"]).to_csv(v.OUT / "correction_terms.csv", index=False)
E = terms[terms.excluded == ""]
print(terms.groupby("set").excluded.apply(lambda s: f"{(s == '').sum()} eligible / {len(s)}").to_string())

# --- pairs ----------------------------------------------------------------------------------------------
rows = []
for t in E.itertuples():
    md = MD[MD.meme_id == t.meme_id]
    for aid in cohort:
        d = md[md.agent_id == aid]
        last = d.last_match_ts.max() if len(d) else pd.NaT
        r = dict(term=t.meme_id, set=t.set, agent_id=aid, agent=names[aid], family=v.family(names[aid]),
                 group="named" if names[aid] in v.NAMED_AGENTS else "bystander", coiner=aid == t.origin_agent_id,
                 holder=bool(((d.last_match_ts >= TC - H48) & (d.first_match_ts <= TC)).any()),
                 holder_strict=bool(((d.date == str(TC.date())) & (d.first_match_ts <= TC)).any()),
                 last_match_utc=last, days_after_correction=round((last - TC) / D1, 1) if pd.notna(last) else np.nan)
        for h, hd in ((1, D1), (7, D7), (30, D30)):
            r[f"surv{h}"] = bool(pd.notna(last) and last >= TC + hd)
            r[f"win{h}"] = bool(((d.last_match_ts >= TC + hd) & (d.first_match_ts <= TC + hd + D7)).any())
        rows.append(r)
P = pd.DataFrame(rows)
P.to_csv(v.OUT / "correction_pairs.csv", index=False)

# --- summary with bootstrap over terms ------------------------------------------------------------------
rng = np.random.default_rng(0)


def rate(p, col):
    return (p[col].sum(), len(p))


def boot_gap(p, col, n=2000):
    """bystander minus named survival, resampling terms with replacement."""
    by = {t: g for t, g in p.groupby("term")}
    keys = list(by)
    out = []
    for _ in range(n):
        s = pd.concat([by[k] for k in rng.choice(keys, len(keys))])
        a, b = s[s.group == "bystander"][col], s[s.group == "named"][col]
        if len(a) and len(b):
            out.append(100 * (a.mean() - b.mean()))
    return np.percentile(out, [2.5, 97.5]).round(1) if out else (np.nan, np.nan)


SETS = {"lexicon (hazard+concept)": lambda p: p[p.set.isin(["hazard", "concept"])],
        "hazard only": lambda p: p[p.set == "hazard"],
        "lexicon without sandcastle_effect": lambda p: p[p.set.isin(["hazard", "concept"]) & (p.term != "sandcastle_effect")],
        "confirmed (separate computers)": lambda p: p[p.set == "confirmed"],
        "control terms": lambda p: p[p.set == "control"]}
DEFS = {"holder 48h, any later match": ("holder", "surv"), "strict holder, any later match": ("holder_strict", "surv"),
        "holder 48h, match inside [h, h+7d]": ("holder", "win")}
summ = []
for sname, sel in SETS.items():
    for dname, (hcol, scol) in DEFS.items():
        p = sel(P)
        p = p[p[hcol]]
        row = dict(term_set=sname, definition=dname, n_terms=p.term.nunique())
        for g in ("named", "bystander"):
            q = p[p.group == g]
            row[f"{g}_holders"] = len(q)
            for h in (1, 7, 30):
                row[f"{g}_surv{h}"] = int(q[f"{scol}{h}"].sum())
            row[f"{g}_surv30_pct"] = round(100 * q[f"{scol}30"].mean(), 1) if len(q) else np.nan
        row["gap30_points"] = round(row["bystander_surv30_pct"] - row["named_surv30_pct"], 1)
        lo, hi = boot_gap(p, f"{scol}30")
        row["gap30_ci_lo"], row["gap30_ci_hi"] = lo, hi
        summ.append(row)
S = pd.DataFrame(summ)
S.to_csv(v.OUT / "correction_summary.csv", index=False)
pd.set_option("display.width", 260)
print(S.to_string(index=False))

lex = P[P.set.isin(["hazard", "concept"]) & P.holder]
ctl = P[(P.set == "control") & P.holder]
A = lex.groupby(["group", "family", "agent"]).agg(lexicon_holders=("holder", "size"), lexicon_surv1=("surv1", "sum"), lexicon_surv7=("surv7", "sum"),
                                                 lexicon_surv30=("surv30", "sum"), lexicon_median_days=("days_after_correction", "median")).reset_index()
A = A.merge(ctl.groupby("agent").agg(control_holders=("holder", "size"), control_surv30=("surv30", "sum")).reset_index(), on="agent", how="left")
A.to_csv(v.OUT / "correction_by_agent.csv", index=False)
print(A.to_string(index=False))

# --- lines behind the surviving pairs -------------------------------------------------------------------
L = pd.read_csv(v.OUT / "fx_memory_lines.csv", keep_default_na=False)
L = L[L.meme_id.isin(E.meme_id) & L.agent_id.isin(cohort) & (L.last_ts >= str(TC + D30))]
L = L.sort_values("n_snap", ascending=False).drop_duplicates(["meme_id", "agent_id"])
L = L.merge(P[["term", "agent_id", "set", "group", "holder"]], left_on=["meme_id", "agent_id"], right_on=["term", "agent_id"])
L = L[L.holder & L.set.isin(["hazard", "concept", "confirmed"])]
L["first_link"] = L.first_ts.map(v.deep_link)
L["last_link"] = L.last_ts.map(v.deep_link)
L[["term", "set", "group", "agent", "line", "first_ts", "last_ts", "n_snap", "n_dates", "first_id", "last_id", "first_link", "last_link"]].sort_values(
    ["group", "agent", "term"]).to_csv(v.OUT / "correction_lines.csv", index=False)
print("surviving lexicon pairs with a line alive >= 30 d after the correction:", len(L))
