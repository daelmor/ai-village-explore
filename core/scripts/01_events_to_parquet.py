"""Phase 0 helper: convert events.jsonl.gz to a slim parquet (no raw model `output`),
sorted by event_index. Keeps every data.* field except `output`, which holds the
provider-shaped raw model response (thinking text) and is ~80% of the bytes.
Usage: python3 -I core/scripts/01_events_to_parquet.py [data/events.jsonl.gz core/out/events_slim.parquet]
"""
import gzip, json, sys, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
src = sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "events.jsonl.gz"
dst = sys.argv[2] if len(sys.argv) > 2 else ROOT / "core" / "out" / "events_slim.parquet"
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
