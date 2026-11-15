"""Short transcripts for coding: per window, only the messages that use decision vocabulary (v.DEC).

Messages up to 1,500 characters are kept whole; longer ones are cut to the 350 characters around each match
(marked with [...]). The full transcript stays in out/windows/<id>.txt for context. Writes out/focus/<id>.txt and
adds focus_msgs / focus_chars to out/windows.csv.
Usage: ./venv/bin/python3 -I data-scouts/conformity/scripts/02_focus_transcripts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import pandas as pd  # noqa: E402

c = v.chat()
w = pd.read_csv(v.OUT / "windows.csv")
(v.OUT / "focus").mkdir(exist_ok=True)
pad = pd.Timedelta(minutes=v.PAD_MIN)


def cut(s):
    if len(s) <= 1500:
        return s
    spans = []
    for m in v.DEC.finditer(s):
        a, b = max(0, m.start() - 350), min(len(s), m.end() + 350)
        if spans and a <= spans[-1][1]:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    return " [...] ".join(s[a:b] for a, b in spans)


nm, nc = [], []
for r in w.itertuples():
    s, e = pd.Timestamp(r.start_utc[:19]), pd.Timestamp(r.end_utc[:19])
    t = c[(c.room == r.room) & (c.ts >= s - pad) & (c.ts <= e + pad + pd.Timedelta(seconds=1))]
    t = t[t.content.str.contains(v.DEC.pattern, flags=v.DEC.flags, regex=True)]
    lines = [f"WINDOW {r.window_id} | room #{r.room} | goal: {r.goal} | {r.start_utc} to {r.end_utc} | "
             f"only messages with decision vocabulary; long ones cut around the matches", ""]
    for m in t.itertuples():
        who = m.speaker if m.speaker_type == "agent" else f"{m.speaker} [HUMAN:{m.role}]"
        lines += [f"[ei={m.event_index} {m.ts:%Y-%m-%d %H:%M:%S}] {who}: {cut(m.content)}", ""]
    txt = "\n".join(lines)
    (v.OUT / "focus" / f"{r.window_id}.txt").write_text(txt)
    nm.append(len(t)); nc.append(len(txt))
w["focus_msgs"], w["focus_chars"] = nm, nc
w.to_csv(v.OUT / "windows.csv", index=False)
print(f"{len(w)} windows, {sum(nm)} focus messages, {sum(nc):,} characters")
