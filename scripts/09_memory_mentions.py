"""Task 9: keyword mentions inside agent long-term memory snapshots.
Per agent (one shard at a time), per snapshot, per line; dedupe identical (agent, keyword, snippet)
across snapshots, keeping first/last date and snapshot count."""
import re, sys, time, os
import pandas as pd
import pyarrow.parquet as pq
from multiprocessing import Pool

OUT = "out"
KW = {
    "goal": r"\bgoals?\b",
    "AI Digest": r"\bAI Digest\b",
    "admin": r"\badmins?\b",
    "organizer": r"\borgani[sz]ers?\b",
    "Adam": r"\bAdam\b",
    "Shoshannah": r"\bShoshannah\b",
    "Zak": r"\bZak\b",
    "leader": r"\bleaders?\b",
    "nudge": r"\bnudg(?:e|es|ed|ing)\b",
    "told me": r"\btold me\b",
    "asked me": r"\basked me\b",
    "instruction": r"\binstructions?\b",
    "approval": r"\bapproval\b",
    "outreach": r"\boutreach\b",
}
CTX_KW = {"goal", "leader"}
CTX = re.compile(r"digest|admin|adam|shoshannah|zak|organi[sz]er|told|asked|instruct|announce|assigned|new goal|this week", re.I)
RX = {k: re.compile(v, re.I) for k, v in KW.items()}
MD = [(re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"), (re.compile(r"[*_`#>|~]+"), ""),
      (re.compile(r"^\s*(?:[-+]\s+|\d+\.\s+)"), ""), (re.compile(r"\s+"), " ")]

def clean(line):
    for rx, rep in MD:
        line = rx.sub(rep, line)
    return line.strip()[:400]

def line_hits(line):
    ctx = None
    out = []
    for k, rx in RX.items():
        if rx.search(line):
            if k in CTX_KW:
                if ctx is None:
                    ctx = bool(CTX.search(line))
                if not ctx:
                    continue
            out.append(k)
    if not out:
        return ()
    sn = clean(line)
    return tuple((k, sn) for k in out)

def process(args):
    aid, name = args
    t0 = time.time()
    path = f"{OUT}/memories/{aid}.parquet"
    if not os.path.exists(path):
        return aid, name, [], 0, 0.0
    cache = {}
    agg = {}  # (kw, snippet) -> [first_created, first_id, first_date, last_created, last_date, n]
    pf = pq.ParquetFile(path)
    nsnap = 0
    for batch in pf.iter_batches(batch_size=32, columns=["id", "created_at", "content"]):
        ids = batch.column("id").to_pylist(); cr = batch.column("created_at").to_pylist()
        ct = batch.column("content").to_pylist()
        for sid, c, text in zip(ids, cr, ct):
            nsnap += 1
            c = str(c)
            keys = set()
            for line in text.split("\n"):
                if len(line) < 3:
                    continue
                h = cache.get(line)
                if h is None:
                    h = line_hits(line); cache[line] = h
                if h:
                    keys.update(h)
            for key in keys:
                a = agg.get(key)
                if a is None:
                    agg[key] = [c, str(sid), c, c, 1]
                else:
                    a[4] += 1
                    if c < a[0]: a[0], a[1] = c, str(sid)
                    if c > a[3]: a[3] = c
                    a[2] = a[0]
        del ids, cr, ct
    rows = [dict(agent=name, agent_id=aid, keyword=k, first_date=a[0][:10], last_date=a[3][:10],
                 n_snapshots=a[4], first_snapshot_id=a[1], snippet=s) for (k, s), a in agg.items()]
    return aid, name, rows, nsnap, time.time() - t0

if __name__ == "__main__":
    idx = pd.read_parquet(f"{OUT}/memories_index.parquet", columns=["agent_id", "agent"])
    ag = idx.groupby(["agent_id", "agent"]).size().reset_index(name="n").sort_values("n", ascending=False)
    jobs = list(zip(ag.agent_id, ag.agent))
    allrows = []
    with Pool(4) as p:
        for aid, name, rows, n, dt in p.imap_unordered(process, jobs):
            print(f"{name:32s} {aid[:8]} snaps={n:6d} rows={len(rows):6d} {dt:6.1f}s", flush=True)
            allrows.extend(rows)
    df = pd.DataFrame(allrows).sort_values(["agent", "keyword", "first_date"]).reset_index(drop=True)
    df.to_csv(f"{OUT}/memory_mentions.csv", index=False)
    print("TOTAL unique rows", len(df))
    print("\nPer keyword (unique rows / sum of snapshot-hits):")
    print(df.groupby("keyword").agg(rows=("snippet", "size"), snapshot_hits=("n_snapshots", "sum")).sort_values("rows", ascending=False))
    print("\nPer agent (unique rows):")
    print(df.groupby("agent").size().sort_values(ascending=False).to_string())
    if len(df) > 50000:
        s = df.groupby("keyword", group_keys=False).apply(lambda g: g.sample(min(len(g), 100), random_state=0))
        s.to_csv(f"{OUT}/memory_mentions_sample.csv", index=False)
        print("Wrote out/memory_mentions_sample.csv (stratified 100/keyword) because rows > 50,000")
