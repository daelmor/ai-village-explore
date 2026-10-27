"""Phase 0 helper: convert events.jsonl.gz to a slim parquet (no raw model `output`),
sorted by event_index. Keeps every data.* field except `output`, which holds the
provider-shaped raw model response (thinking text) and is ~80% of the bytes.
Usage: python3 -I scripts/00_events_to_parquet.py data/events.jsonl.gz out/events_slim.parquet
"""
import gzip, json, sys, collections
import pandas as pd

src, dst = sys.argv[1], sys.argv[2]
rows = []
with gzip.open(src, "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        d = r["data"]
        out = d.pop("output", None)
        row = {"id": r["id"], "event_index": r["event_index"], "created_at": r["created_at"],
               "has_output": out is not None, "output_len": len(str(out)) if out is not None else 0}
        for k, v in d.items():
            row[k] = v if isinstance(v, (str, int, float, bool)) or v is None else json.dumps(v)
        rows.append(row)
df = pd.DataFrame(rows).sort_values("event_index").reset_index(drop=True)
df.to_parquet(dst, index=False)
print("rows:", len(df), "cols:", list(df.columns))
