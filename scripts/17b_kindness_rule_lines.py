"""Task 10 fix-up: the generic regex in 17_kindness_write_through.py picked the first line matching email|adam|... as
the "memory line", which for three agents was not the rule (e.g. the agent's own email address). This script
recomputes, per agent, the rule-specific lines in (i) the last snapshot of 2025-12-26, (ii) the first snapshot on/after
2025-12-29, (iii) the first snapshot on/after 2026-01-02, and overwrites the persistence columns in
out/kindness_write_through.csv. Verbatim lines, snapshot ids and nearest event indices included."""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import village_lib as v  # noqa: E402

RULE = re.compile(r"unsolicited|cold (?:email|outreach)|contacted (?:me|us|you)|reply[- ]only|only reply|"
                  r"who (?:have|has)n[’']?t (?:contacted|emailed|written)|(?:not|no) .{0,20}email(?:ing)? anyone", re.I)
ADJ = re.compile(r"pull[- ]based|consent[- ]first|opt[- ]in|complain", re.I)
RULE_EI = 146638
RULE_TS = pd.Timestamp("2025-12-26 18:00:05")

k = pd.read_csv(v.OUT / "kindness_write_through.csv")
rows = []
for r in k.itertuples(index=False):
    m = v.memory_shard(r.agent_id)
    def snap(sel):
        d = m[sel]
        return None if d.empty else d
    eod = snap((m.ts >= RULE_TS) & (m.ts < "2025-12-27")).iloc[-1]
    before = snap(m.ts < RULE_TS).iloc[-1]
    nd = snap(m.ts >= "2025-12-29").iloc[0]
    d7 = snap(m.ts >= "2026-01-02").iloc[0]
    def lines(s, rx): return [l.strip() for l in s.content.splitlines() if rx.search(l)]
    rows.append(dict(
        agent=r.agent,
        rule_lines_before=" || ".join(lines(before, RULE)), before_snapshot_id=before.id,
        rule_lines_eod=" || ".join(lines(eod, RULE)), rule_adjacent_lines_eod=" || ".join(lines(eod, ADJ)),
        eod_snapshot_id=eod.id, eod_snapshot_ts_utc=v.fmt_ts(eod.ts), eod_event_index=v.last_event_index_at(eod.ts), eod_deep_link=v.deep_link(eod.ts),
        rule_in_eod=bool(lines(eod, RULE)), rule_adjacent_in_eod=bool(lines(eod, ADJ)),
        rule_lines_next_day=" || ".join(lines(nd, RULE)), next_day_snapshot_id=nd.id, next_day_snapshot_ts_utc=v.fmt_ts(nd.ts), rule_in_next_day=bool(lines(nd, RULE)),
        rule_lines_7d=" || ".join(lines(d7, RULE)), d7_snapshot_id=d7.id, d7_snapshot_ts_utc=v.fmt_ts(d7.ts), rule_in_7d=bool(lines(d7, RULE)),
    ))
R = pd.DataFrame(rows)
keep = [c for c in k.columns if c not in ("memory_line", "memory_snapshot_id", "memory_snapshot_ts_utc", "memory_event_index", "still_present_next_day", "still_present_7d", "rule_in_eod_snapshot", "eod_matching_line", "note")]
out = k[keep].merge(R, on="agent")
out.to_csv(v.OUT / "kindness_write_through.csv", index=False)
print(out[["agent", "acknowledged_in_chat", "rule_in_eod", "rule_adjacent_in_eod", "rule_in_next_day", "rule_in_7d"]].to_string(index=False))
print("rule in before-snapshot (should be none):", out.rule_lines_before.str.len().gt(0).sum())
for r in out.itertuples():
    print("-", r.agent, "|", (r.rule_lines_eod or r.rule_adjacent_lines_eod)[:150])
