"""Step 4: trace every meme of memes.csv through chat, memory and stated action.

For each meme (regex) this finds the origin (earliest chat message matching it), then every later match in
  - chat                         -> out/meme_chat_hits.csv        (one row per matching message)
  - memory snapshots             -> out/meme_memory_daily.csv     (meme x agent x UTC date: snapshots that day,
                                    snapshots containing a matching line, first/last matching snapshot id)
                                    out/meme_memory_agent.csv     (meme x agent: matching snapshots before the origin,
                                    first and last matching snapshot after it; exact, per snapshot)
                                    out/meme_memory_lines.csv     (every distinct matching memory line with its
                                    first/last snapshot; the lines read for the precision check)
  - stated action                -> out/meme_action_hits.csv      (agent's own START_USING_COMPUTER.sessionGoal /
                                    CONSOLIDATE.nextSessionGoal matching the regex)
  - origin                       -> out/meme_origins.csv
Memory matching is exact per snapshot: matching lines are found in out/memory_lines.parquet (step 1), then every
snapshot of every agent that has at least one such line is re-read and tested line by line.

Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/04_trace_memes.py [--memes other.csv --tag bg]
        (--memes/--tag let step 7 reuse this tracer for the mechanically drawn background terms)
"""
import argparse
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402


def scan_agent(job):
    """Exact per-snapshot presence for one agent. job = (agent_id, {meme_id: set(lines)}, {meme_id: origin ts string}).
    Returns (daily rows, per-agent rows). Timestamps are compared as strings (same fixed-width UTC format)."""
    aid, by_meme, t0 = job
    m = pd.read_parquet(v.SHARED / "memories" / f"{aid}.parquet", columns=["id", "created_at", "content"]).sort_values(["created_at", "id"])
    wanted = {}
    for mid, lines in by_meme.items():
        for ln in lines:
            wanted.setdefault(ln, []).append(mid)
    day = defaultdict(lambda: [0, 0, None, None, None, None])  # (meme, date) -> n_snap, n_match, first_id, first_ts, last_id, last_ts
    dates = defaultdict(int)
    ag = {mid: dict(meme_id=mid, agent_id=aid, n_match_before_origin=0, last_before_origin_ts=None, last_before_origin_id=None,
                    first_after_id=None, first_after_ts=None, last_after_id=None, last_after_ts=None, n_match_after_origin=0)
          for mid in by_meme}
    for sid, c, text in zip(m.id.values, m.created_at.values, m.content.values):
        c = str(c)
        d = c[:10]
        dates[d] += 1
        hit = set()
        for line in set((text or "").split("\n")):
            line = line.rstrip()[:4000]
            if line in wanted:
                hit.update(wanted[line])
        for mid in hit:
            a = day[(mid, d)]
            a[1] += 1
            if a[2] is None:
                a[2], a[3] = sid, c
            a[4], a[5] = sid, c
            g = ag[mid]
            if c < t0[mid]:
                g["n_match_before_origin"] += 1
                g["last_before_origin_ts"], g["last_before_origin_id"] = c, sid
            else:
                g["n_match_after_origin"] += 1
                if g["first_after_id"] is None:
                    g["first_after_id"], g["first_after_ts"] = sid, c
                g["last_after_id"], g["last_after_ts"] = sid, c
    return [dict(meme_id=mid, agent_id=aid, date=d, n_snapshots=dates[d], n_matching=a[1], first_match_id=a[2],
                 first_match_ts=a[3], last_match_id=a[4], last_match_ts=a[5]) for (mid, d), a in day.items()], list(ag.values())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--memes", default=str(v.MEMES))
    ap.add_argument("--tag", default="meme")
    a = ap.parse_args()
    M = pd.read_csv(a.memes, keep_default_na=False)
    if "status" in M.columns:
        M = M[M.status == "keep"].reset_index(drop=True)  # dropped memes stay in the registry with the reason
    tag = a.tag
    names = v.roster().set_index("id")["name"].to_dict()

    # --- chat: origin and uptake ------------------------------------------------------------------------
    c = v.chat_clean()
    origins, chat_hits = [], []
    for r in M.itertuples():
        h = c[c.content.str.contains(r.regex, case=False, regex=True)]
        if h.empty:
            print("!! no chat match:", r.meme_id)
            continue
        o = h.iloc[0]
        origins.append(dict(meme_id=r.meme_id, origin_event_index=int(o.event_index), origin_ts=o.ts, origin_utc=v.fmt_ts(o.ts),
                            origin_link=v.deep_link(o.ts), origin_speaker=o.speaker, origin_role=o.role, origin_room=o.room,
                            origin_agent_id=o.agent_speaker_id if o.speaker_type == "agent" else "",
                            n_chat_messages=len(h), n_agent_speakers=h[h.speaker_type == "agent"].speaker.nunique(),
                            origin_text=o.content[:600].replace("\n", " ")))
        chat_hits.append(h.assign(meme_id=r.meme_id, utc=h.ts.map(v.fmt_ts))[
            ["meme_id", "event_index", "utc", "room", "role", "speaker", "agent_speaker_id", "content"]])
    O = pd.DataFrame(origins)
    O.drop(columns="origin_ts").to_csv(v.OUT / f"{tag}_origins.csv", index=False)
    H = pd.concat(chat_hits)
    H["content"] = H.content.str.slice(0, 500).str.replace("\n", " ")
    H.to_csv(v.OUT / f"{tag}_chat_hits.csv", index=False)

    # --- stated action ----------------------------------------------------------------------------------
    e = v.events(("event_index", "created_at", "actionType", "agentId", "sessionGoal", "nextSessionGoal"))
    e = e[e.actionType.isin(["START_USING_COMPUTER", "CONSOLIDATE"])].copy()
    e["text"] = e.sessionGoal.fillna("") + e.nextSessionGoal.fillna("")
    act = []
    for r in M.itertuples():
        h = e[e.text.str.contains(r.regex, case=False, regex=True)]
        act.append(pd.DataFrame(dict(meme_id=r.meme_id, event_index=h.event_index, utc=h.ts.map(v.fmt_ts), actionType=h.actionType,
                                     agent_id=h.agentId, agent=h.agentId.map(names), text=h.text.str.slice(0, 500).str.replace("\n", " "))))
    pd.concat(act).to_csv(v.OUT / f"{tag}_action_hits.csv", index=False)

    # --- memory: matching lines (RE2 over the line table), then exact per-snapshot presence --------------
    pf = pq.ParquetFile(v.LINES)
    per_agent = defaultdict(lambda: defaultdict(set))
    line_rows = []
    for g in range(pf.num_row_groups):
        t = pf.read_row_group(g)
        for r in M.itertuples():
            mask = pc.match_substring_regex(t["line"], r.regex, ignore_case=True)
            if pc.sum(mask).as_py():
                sub = t.filter(mask).to_pandas()
                sub.insert(0, "meme_id", r.meme_id)
                line_rows.append(sub)
                for aid, ln in zip(sub.agent_id, sub.line):
                    per_agent[aid][r.meme_id].add(ln)
    L = pd.concat(line_rows) if line_rows else pd.DataFrame()
    L.assign(line=L.line.str.slice(0, 600)).sort_values(["meme_id", "agent", "first_ts"]).to_csv(v.OUT / f"{tag}_memory_lines.csv", index=False)
    t0 = {r.meme_id: str(r.origin_ts) for r in O.itertuples()}  # 'YYYY-MM-DD HH:MM:SS[.ffffff]', same as created_at
    jobs = [(aid, {k: s for k, s in d.items() if k in t0}, t0) for aid, d in per_agent.items()]
    rows, arows = [], []
    with Pool(4) as p:
        for out, ag in p.imap_unordered(scan_agent, jobs):
            rows.extend(out)
            arows.extend(ag)
    D = pd.DataFrame(rows)
    D["agent"] = D.agent_id.map(names)
    D.sort_values(["meme_id", "agent", "date"]).to_csv(v.OUT / f"{tag}_memory_daily.csv", index=False)
    A = pd.DataFrame(arows)
    A["agent"] = A.agent_id.map(names)
    A.sort_values(["meme_id", "agent"]).to_csv(v.OUT / f"{tag}_memory_agent.csv", index=False)

    s = O[["meme_id", "origin_event_index", "origin_utc", "origin_speaker", "n_chat_messages", "n_agent_speakers"]].merge(
        D.groupby("meme_id").agg(mem_agents=("agent_id", "nunique"), mem_first=("date", "min"), mem_last=("date", "max")).reset_index(),
        on="meme_id", how="left")
    print(s.to_string(index=False))
