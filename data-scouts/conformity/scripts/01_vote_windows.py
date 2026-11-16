"""Find candidate group-decision windows from first-person vote wording in agent chat.

Writes out/vote_messages.csv (every agent message matching POS, with window id), out/windows.csv (one row per
window: room, start/end, agents, counts, goal) and out/windows/<id>.txt (the full room transcript of the window,
padded by 60 minutes, one message per block with its event_index) for coding.
Usage: ./venv/bin/python3 -I data-scouts/conformity/scripts/01_vote_windows.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import pandas as pd  # noqa: E402

c = v.chat()
a = c[c.speaker_type == "agent"].copy()
a["pos"] = a.content.str.contains(v.POS.pattern, flags=v.POS.flags, regex=True)
p = a[a.pos].sort_values(["room", "event_index"]).copy()
new = (p.room != p.room.shift()) | ((p.ts - p.ts.shift()) > pd.Timedelta(hours=v.GAP_H))
p["cluster"] = new.cumsum()
g = p.groupby("cluster").agg(room=("room", "first"), start=("ts", "min"), end=("ts", "max"), n_pos_msgs=("id", "size"),
                             n_pos_agents=("speaker", "nunique"), goal=("active_goal", "first"),
                             first_ei=("event_index", "min"), last_ei=("event_index", "max")).reset_index()
w = g[g.n_pos_agents >= v.MIN_AGENTS].sort_values("start").reset_index(drop=True)
w["window_id"] = ["W%03d" % (i + 1) for i in range(len(w))]
p = p.merge(w[["cluster", "window_id"]], on="cluster", how="left")
p.assign(utc=p.ts.map(v.fmt_ts), link=p.ts.map(v.deep_link))[
    ["event_index", "utc", "link", "room", "speaker", "window_id", "active_goal", "content"]
].sort_values("event_index").to_csv(v.OUT / "vote_messages.csv", index=False)

(v.OUT / "windows").mkdir(exist_ok=True)
pad = pd.Timedelta(minutes=v.PAD_MIN)
rows = []
for r in w.itertuples():
    t = c[(c.room == r.room) & (c.ts >= r.start - pad) & (c.ts <= r.end + pad)]
    lines = [f"WINDOW {r.window_id} | room #{r.room} | goal: {r.goal} | {v.fmt_ts(r.start)} to {v.fmt_ts(r.end)}", ""]
    for m in t.itertuples():
        who = m.speaker if m.speaker_type == "agent" else f"{m.speaker} [HUMAN:{m.role}]"
        lines.append(f"[ei={m.event_index} {m.ts:%Y-%m-%d %H:%M:%S}] {who}: {m.content}")
        lines.append("")
    (v.OUT / "windows" / f"{r.window_id}.txt").write_text("\n".join(lines))
    rows.append(dict(window_id=r.window_id, room=r.room, start_utc=v.fmt_ts(r.start), end_utc=v.fmt_ts(r.end),
                     link=v.deep_link(r.start), goal=r.goal, n_pos_msgs=r.n_pos_msgs, n_pos_agents=r.n_pos_agents,
                     first_ei=r.first_ei, last_ei=r.last_ei, transcript_msgs=len(t),
                     transcript_chars=sum(len(x) for x in lines)))
pd.DataFrame(rows).to_csv(v.OUT / "windows.csv", index=False)
print(f"{int(a.pos.sum())} position-wording messages from {p.speaker.nunique()} agents; {len(g)} clusters; "
      f"{len(w)} windows with >= {v.MIN_AGENTS} agents; {p.window_id.notna().sum()} messages inside windows")
