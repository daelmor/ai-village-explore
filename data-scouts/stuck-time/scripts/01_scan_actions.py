"""Stream data/computer_use_turns.jsonl.gz once and keep one light row per turn.

Writes out/turn_actions.parquet (git-ignored): turn_id, session_id, agent_id, created_at, kind (action name,
`bash`, `restart`, `none`, `empty`), sig (md5 of the normalized action = signature, see HYPOTHESIS.md),
excerpt (first 300 chars of the normalized action), has_error, err (first 200 chars), out_len, out_sig (md5 of
the tool output), out (first 200 chars). No screenshot is read. Takes roughly 20-30 minutes.
Usage: ./venv/bin/python3 -I data-scouts/stuck-time/scripts/01_scan_actions.py
"""
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

PQ = v.OUT / "turn_actions.parquet"
WS = re.compile(r"\s+")
COLS = ["turn_id", "session_id", "agent_id", "created_at", "kind", "sig", "excerpt", "has_error", "err",
        "out_len", "out_sig", "out"]


def md5(s):
    return hashlib.md5(s.encode("utf-8", "replace")).hexdigest()[:16]


def normalize(act):
    """(kind, normalized target string) for an agent_action value."""
    if act is None:
        return "none", ""
    if not isinstance(act, dict):
        return "other", json.dumps(act, sort_keys=True, ensure_ascii=False)
    d = {k: x for k, x in act.items() if x is not None}
    if not d:
        return "empty", ""
    if "command" in d and isinstance(d["command"], str):
        lines = [l for l in d["command"].split("\n") if not l.lstrip().startswith("#")]
        return "bash", WS.sub(" ", "\n".join(lines)).strip()
    if "action" not in d:
        if d.get("restart"):
            return "restart", "restart"
        return "other", json.dumps(d, sort_keys=True, ensure_ascii=False)
    return str(d["action"]), json.dumps(d, sort_keys=True, ensure_ascii=False)


def main():
    s2a = {}
    for l in gzip.open(v.DATA / "computer_use_sessions.jsonl.gz", "rt"):
        d = json.loads(l)
        s2a[d["id"]] = d["agent_id"]
    buf = {c: [] for c in COLS}
    writer, n = None, 0

    def flush():
        nonlocal writer
        t = pa.table(buf)
        if writer is None:
            writer = pq.ParquetWriter(PQ, t.schema)
        writer.write_table(t)
        for c in COLS:
            buf[c].clear()

    with gzip.open(v.DATA / "computer_use_turns.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            n += 1
            r = json.loads(line)
            kind, target = normalize(r.get("agent_action"))
            out = r.get("output") if isinstance(r.get("output"), str) else ""
            err = r.get("error") if isinstance(r.get("error"), str) else ""
            buf["turn_id"].append(r["id"])
            buf["session_id"].append(r["session_id"])
            buf["agent_id"].append(s2a.get(r["session_id"]))
            buf["created_at"].append(r["created_at"])
            buf["kind"].append(kind)
            buf["sig"].append(md5(kind + "|" + target))
            buf["excerpt"].append(target[:300])
            buf["has_error"].append(bool(err.strip()))
            buf["err"].append(err[:200])
            buf["out_len"].append(len(out))
            buf["out_sig"].append(md5(out) if out else "")
            buf["out"].append(out[:200])
            if n % 250000 == 0:
                flush()
                print("lines", n, file=sys.stderr, flush=True)
    flush()
    writer.close()
    print("total lines", n, file=sys.stderr)


if __name__ == "__main__":
    main()
