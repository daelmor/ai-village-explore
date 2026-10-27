"""One streaming pass over agent_memories.jsonl.gz (3 GB gz) -> per-agent parquet shards
in out/memories/<agent_id>.parquet (zstd) plus out/memories_index.parquet (id, agent_id, agent,
created_at, date, content_len). Never loads the whole file in memory.
Usage: python3 -I scripts/07_memories_shard.py
"""
import gzip, json, pathlib, collections
import pandas as pd, pyarrow as pa, pyarrow.parquet as pq

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "agent_memories.jsonl.gz"
DST = ROOT / "out" / "memories"; DST.mkdir(exist_ok=True)
names = pd.read_csv(ROOT / "out" / "agents_roster.csv").set_index("id")["name"].to_dict()
schema = pa.schema([("id", pa.string()), ("agent_id", pa.string()), ("created_at", pa.string()), ("content", pa.string())])
writers, buffers, index = {}, collections.defaultdict(list), []
BATCH = 300

def flush(aid):
    rows = buffers[aid]
    if not rows: return
    if aid not in writers:
        writers[aid] = pq.ParquetWriter(DST / f"{aid}.parquet", schema, compression="zstd")
    writers[aid].write_table(pa.Table.from_pylist(rows, schema=schema))
    buffers[aid] = []

n = 0
with gzip.open(SRC, "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        aid = r["agent_id"]
        buffers[aid].append({"id": r["id"], "agent_id": aid, "created_at": r["created_at"], "content": r["content"]})
        index.append((r["id"], aid, names.get(aid, aid), r["created_at"], r["created_at"][:10], len(r["content"])))
        if len(buffers[aid]) >= BATCH: flush(aid)
        n += 1
        if n % 20000 == 0: print(n, flush=True)
for aid in list(buffers): flush(aid)
for w in writers.values(): w.close()
idx = pd.DataFrame(index, columns=["id", "agent_id", "agent", "created_at", "date", "content_len"]).sort_values("created_at")
idx.to_parquet(ROOT / "out" / "memories_index.parquet", index=False)
print("rows:", len(idx), "agents:", idx.agent.nunique())
print(idx.groupby("agent").agg(n=("id", "size"), first=("date", "min"), last=("date", "max"), mean_len=("content_len", "mean")).round(0).to_string())
