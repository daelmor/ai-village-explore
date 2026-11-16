"""Reading check: 30 random D1 episodes (random_state=0), stratified by action kind group, with their raw turns.

Writes out/reading_sample.md: for each sampled episode the turn before it, every repeated action, and the recovery
turn, each with turn id, UTC time, action excerpt, first 200 characters of output and error. The hand coding of
these episodes lives in VERIFICATION.md.
Usage: ./venv/bin/python3 -I data-scouts/stuck-time/scripts/04_reading_sample.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import pandas as pd  # noqa: E402

QUOTA = {"bash": 9, "pointer": 9, "key_type": 7, "pixel_coords": 5}
ep = pd.read_parquet(v.OUT / "episodes.parquet")
parts = [ep[ep.kgroup == k].sample(min(n, (ep.kgroup == k).sum()), random_state=0) for k, n in QUOTA.items()]
s = pd.concat(parts).reset_index(drop=True)
t = pd.read_parquet(v.OUT / "turn_actions.parquet", filters=[("session_id", "in", list(s.session_id.unique()))])
t["ts"] = pd.to_datetime(t.created_at, format="ISO8601")
t = t.sort_values(["session_id", "ts", "turn_id"]).reset_index(drop=True)
L = ["# Reading sample: 30 D1 episodes with their raw turns", "",
     "Drawn by `scripts/04_reading_sample.py` (`random_state=0`), stratified: " + ", ".join(f"{n} {k}" for k, n in QUOTA.items()) + ".", ""]


def clip(x, n=200):
    x = (x or "").replace("\n", " ⏎ ")
    return x[:n] + ("…" if len(x) > n else "")


for i, e in s.iterrows():
    d = t[t.session_id == e.session_id].reset_index(drop=True)
    a = d.index[d.turn_id == e.start_turn][0]
    b = d.index[d.turn_id == (e.recovery_turn if e.recovered else e.last_repeat_turn)][0]
    L += [f"## S{i + 1:02d} · {e.agent} · {e.kgroup} · {e.n} repeats · "
          f"{'recovered after %.0f s' % e.recover_s if e.recovered else 'not recovered in session'}",
          f"session `{e.session_id}` · start {v.fmt_ts(e.start)} · {e.link}", ""]
    for j in range(max(a - 2, 0), min(b + 2, len(d))):
        r = d.iloc[j]
        mark = "→" if a <= j < b and r.sig == e.sig else " "
        L.append(f"- {mark} `{r.turn_id[:8]}` {r.ts:%H:%M:%S} **{r.kind}** {clip(r.excerpt, 220)}"
                 + (f" | out: {clip(r.out, 160)}" if r.out else "") + (f" | ERR: {clip(r.err, 160)}" if r.err else ""))
    L.append("")
(v.OUT / "reading_sample.md").write_text("\n".join(L))
s.drop(columns=["excerpt"]).to_csv(v.OUT / "reading_sample.csv", index=False)
print(len(s), "episodes written")
