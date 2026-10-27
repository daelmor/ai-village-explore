"""Append agent memories to each episode. For each episode (date range), for each agent with
memory snapshots in range, write a sibling file out/episodes/<ep>_memories.md containing:
  - an index of ALL snapshots in range (id, time, length) so any row can be pulled from out/memories/<agent_id>.parquet
  - the LAST snapshot of each day per agent, in full (consecutive snapshots overlap heavily;
    the last of the day is a superset of that day's additions in practice)
and append a short '## Agent memories' pointer section to the main episode file.
Usage: python3 -I scripts/08_episode_memories.py
"""
import pathlib, re
import pandas as pd, pyarrow.parquet as pq

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"; EP = OUT / "episodes"
EPISODES = {
    "ep1_2025-06-19_esoteric-framework": ("2025-06-19", "2025-06-25"),
    "ep2_2025-06-26_merch-squirrel": ("2025-06-26", "2025-07-15"),
    "ep3_2025-09-01_debate-week": ("2025-09-01", "2025-09-05"),
    "ep4_2025-12-22_kindness": ("2025-12-22", "2025-12-26"),
    "ep5_2026-01-05_elected-leader": ("2026-01-05", "2026-01-09"),
    "ep6_2026-05-26_finetuned-leader": ("2026-05-26", "2026-06-05"),
    "ep7_2026-03-30_no-goal": ("2026-03-30", "2026-04-01"),
}
idx = pd.read_parquet(OUT / "memories_index.parquet")
MARK = "<!-- memories appended by scripts/07_episode_memories.py -->"
for ep, (d0, d1) in EPISODES.items():
    main = EP / f"{ep}.md"
    sel = idx[(idx.date >= d0) & (idx.date <= d1)].sort_values("created_at")
    lines = [f"# {ep} — agent memories {d0}..{d1}", "",
             f"{len(sel)} memory snapshots from {sel.agent.nunique()} agents in range. Each snapshot is the agent's FULL long-term memory at a consolidation moment. "
             "Below: index of every snapshot, then the last snapshot of each day per agent in full. Any other snapshot can be read from `out/memories/<agent_id>.parquet` by `id`.", ""]
    lines += ["## Snapshot index", "", "| agent | created_at (UTC) | id | chars |", "|---|---|---|---|"]
    lines += [f"| {r.agent} | {r.created_at} | `{r.id}` | {r.content_len:,} |" for r in sel.itertuples()]
    lines += ["", "## Last snapshot per agent per day", ""]
    last = sel.groupby(["agent", "date"]).tail(1)
    for aid, grp in last.groupby("agent_id", sort=False):
        shard = pq.read_table(OUT / "memories" / f"{aid}.parquet", columns=["id", "content"]).to_pandas().set_index("id")["content"]
        for r in grp.sort_values("created_at").itertuples():
            body = shard.get(r.id, "")
            body = re.sub(r"^(#{1,6}) ", lambda m: "#" * (len(m.group(1)) + 3) + " ", body, flags=re.M)  # demote headings
            lines += [f"### {r.agent} — {r.created_at} (id `{r.id}`, {r.content_len:,} chars)", "", body, ""]
    (EP / f"{ep}_memories.md").write_text("\n".join(lines))
    if main.exists():
        txt = main.read_text()
        sec = (f"\n## Agent memories\n\n{len(sel)} snapshots from {sel.agent.nunique()} agents in range; "
               f"see `{ep}_memories.md` (index of all snapshots + last snapshot per agent per day in full).\n"
               f"Per-agent snapshot counts: " + ", ".join(f"{a} {n}" for a, n in sel.agent.value_counts().items()) + "\n")
        txt = txt.replace(MARK, sec + MARK) if MARK in txt else txt + sec
        main.write_text(txt)
    print(ep, len(sel), "snapshots,", sel.agent.nunique(), "agents,", f"{(EP / f'{ep}_memories.md').stat().st_size/1e6:.1f} MB")
