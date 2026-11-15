"""Step 1: line-level survival table of every agent's long-term memory.

Generalises authority-recognition/scripts/09_memory_mentions.py (14 keywords) to every line: for each agent, every
distinct memory line (exact text, right-stripped, >= 3 chars, capped at 4,000 chars) with the first and last
snapshot containing it, the number of snapshots and of distinct UTC dates on which it was present.
Any regex can then be traced through memory in seconds without re-reading the 8.4 GB of snapshots.

Reads   core/out/memories/<agent_id>.parquet, core/out/memories_index.parquet
Writes  out/memory_lines.parquet   (git-ignored cache, one row group per agent; ~14M rows)
        out/memory_lines_stats.csv (per agent: snapshots, distinct lines, first/last snapshot)
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/01_memory_lines.py
"""
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

CAP = 4000
SCHEMA = pa.schema([("agent_id", pa.string()), ("agent", pa.string()), ("line", pa.string()),
                    ("first_ts", pa.string()), ("last_ts", pa.string()), ("n_snap", pa.int32()),
                    ("n_dates", pa.int32()), ("first_id", pa.string()), ("last_id", pa.string())])


def process(job):
    aid, name = job
    t0 = time.time()
    path = v.SHARED / "memories" / f"{aid}.parquet"
    if not path.exists():
        return aid, name, None, 0, 0.0
    m = pd.read_parquet(path, columns=["id", "created_at", "content"]).sort_values(["created_at", "id"])
    agg = {}  # line -> [first_ts, first_id, last_ts, last_id, n_snap, n_dates, last_date]
    for sid, c, text in zip(m.id.values, m.created_at.values, m.content.values):
        c = str(c)
        d = c[:10]
        for line in set((text or "").split("\n")):
            line = line.rstrip()
            if len(line) < 3:
                continue
            if len(line) > CAP:
                line = line[:CAP]
            a = agg.get(line)
            if a is None:
                agg[line] = [c, sid, c, sid, 1, 1, d]
            else:
                a[2], a[3] = c, sid
                a[4] += 1
                if a[6] != d:
                    a[5] += 1
                    a[6] = d
    n = len(m)
    del m
    tab = pa.table({"agent_id": [aid] * len(agg), "agent": [name] * len(agg), "line": list(agg.keys()),
                    "first_ts": [a[0] for a in agg.values()], "last_ts": [a[2] for a in agg.values()],
                    "n_snap": [a[4] for a in agg.values()], "n_dates": [a[5] for a in agg.values()],
                    "first_id": [a[1] for a in agg.values()], "last_id": [a[3] for a in agg.values()]}, schema=SCHEMA)
    tmp = v.OUT / f"_lines_{aid}.parquet"
    pq.write_table(tab, tmp, compression="zstd")
    return aid, name, str(tmp), n, time.time() - t0


if __name__ == "__main__":
    idx = v.memories_index()
    ag = idx.groupby(["agent_id", "agent"]).agg(n=("id", "size"), first=("created_at", "min"), last=("created_at", "max")).reset_index()
    ag = ag.sort_values("n", ascending=False)
    stats, parts = [], []
    with Pool(4) as p:
        for aid, name, tmp, n, dt in p.imap_unordered(process, list(zip(ag.agent_id, ag.agent))):
            if tmp is None:
                continue
            rows = pq.ParquetFile(tmp).metadata.num_rows
            print(f"{name:32s} snaps={n:6d} lines={rows:8d} {dt:6.1f}s", flush=True)
            stats.append(dict(agent_id=aid, agent=name, n_snapshots=n, n_distinct_lines=rows))
            parts.append((name, aid, tmp))
    out = v.OUT / "memory_lines.parquet"
    with pq.ParquetWriter(out, SCHEMA, compression="zstd") as w:
        for name, aid, tmp in sorted(parts):  # deterministic order: agent name, then id
            w.write_table(pq.read_table(tmp))
            Path(tmp).unlink()
    s = pd.DataFrame(stats).merge(ag[["agent_id", "first", "last"]], on="agent_id").sort_values("agent")
    s.rename(columns={"first": "first_snapshot_utc", "last": "last_snapshot_utc"}).to_csv(v.OUT / "memory_lines_stats.csv", index=False)
    print("agents", len(s), "snapshots", s.n_snapshots.sum(), "distinct lines", s.n_distinct_lines.sum())
