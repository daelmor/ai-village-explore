"""Pull the raw computer_use_turns rows behind the hand-read episodes (one pass over the 3.8 GB file).

For every episode coded in out/reading_codes.csv, keeps the raw row of its first and third repeated turn:
agent_action, output, error and the text of agent_messages (the model's own narration, cut to 1,500 characters).
Writes out/verified_raw_turns.jsonl.
Usage: ./venv/bin/python3 -I data-scouts/stuck-time/scripts/05_raw_rows.py
"""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import pandas as pd  # noqa: E402

s = pd.read_csv(v.OUT / "reading_sample.csv")
t = pd.read_parquet(v.OUT / "turn_actions.parquet", columns=["turn_id", "session_id", "created_at", "sig"],
                    filters=[("session_id", "in", list(s.session_id.unique()))])
want = {}
for i, e in s.iterrows():
    d = t[(t.session_id == e.session_id) & (t.sig == e.sig) & (t.created_at >= str(e.start)[:19])].sort_values("created_at")
    for k in (0, 2):
        if k < len(d):
            want[d.turn_id.iloc[k]] = f"S{i + 1:02d}"
SKIP = {"signature", "thoughtSignature", "encrypted_content", "data", "image", "image_url", "base64_image"}


def texts(o, out):
    if isinstance(o, str):
        if o.strip() and not o.startswith("data:image") and not (len(o) > 3000 and " " not in o[:200]):
            out.append(o)
    elif isinstance(o, list):
        for x in o:
            texts(x, out)
    elif isinstance(o, dict):
        for k, x in o.items():
            if k not in SKIP:
                texts(x, out)


n = 0
with gzip.open(v.DATA / "computer_use_turns.jsonl.gz", "rt", encoding="utf-8") as f, open(v.OUT / "verified_raw_turns.jsonl", "w") as g:
    for line in f:
        if line[7:43] not in want:     # rows start with {"id":"<uuid>": cheap filter before parsing
            continue
        r = json.loads(line)
        if r["id"] not in want:
            continue
        tx = []
        texts(r.get("agent_messages"), tx)
        g.write(json.dumps(dict(sample=want[r["id"]], turn_id=r["id"], session_id=r["session_id"], created_at=r["created_at"],
                                agent_action=r.get("agent_action"), output=(r.get("output") or "")[:600],
                                error=(r.get("error") or "")[:600], narration=" ⏎ ".join(tx)[:1500]), ensure_ascii=False) + "\n")
        n += 1
print(n, "raw rows of", len(want))
