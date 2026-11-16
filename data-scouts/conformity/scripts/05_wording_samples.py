"""Samples for the reading checks of HYPOTHESIS.md ("How decisions are found", steps 4 and 5).

out/wording_sample.csv   100 random agent messages matching the position wording (random_state=0), with the
                         matched text in context, whether the message is inside a window and whether it is cited
                         as a position by the coding. The hand codes are added in VERIFICATION.md.
out/misses_sample.csv    20 random agent messages with any vote / election word that fall outside every window.
Usage: ./venv/bin/python3 -I data-scouts/conformity/scripts/05_wording_samples.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import pandas as pd  # noqa: E402

vm = pd.read_csv(v.OUT / "vote_messages.csv")
P = pd.read_csv(v.OUT / "positions.csv")
cited = set(P.initial_ei.dropna().astype(int)) | set(P.final_ei.dropna().astype(int))
s = vm.sample(100, random_state=0).sort_values("event_index").copy()


def ctx(text, rx, pad=90):
    m = rx.search(text)
    return text[max(0, m.start() - pad):m.end() + pad].replace("\n", " ") if m else text[:2 * pad]


s["context"] = [ctx(t, v.POS) for t in s.content]
s["in_window"] = s.window_id.notna()
s["cited_as_position"] = s.event_index.isin(cited)
s[["event_index", "utc", "link", "speaker", "window_id", "in_window", "cited_as_position", "context"]].to_csv(v.OUT / "wording_sample.csv", index=False)

c = v.chat()
w = pd.read_csv(v.OUT / "windows.csv")
a = c[(c.speaker_type == "agent") & c.content.str.contains(v.LOOSE.pattern, flags=v.LOOSE.flags, regex=True)].copy()
inside = pd.Series(False, index=a.index)
pad = pd.Timedelta(minutes=v.PAD_MIN)
for r in w.itertuples():
    inside |= (a.room == r.room) & (a.ts >= pd.Timestamp(r.start_utc[:19]) - pad) & (a.ts <= pd.Timestamp(r.end_utc[:19]) + pad)
out = a[~inside]
m = out.sample(20, random_state=0).sort_values("event_index").copy()
m["context"] = [ctx(t, v.LOOSE, 130) for t in m.content]
m.assign(utc=m.ts.map(v.fmt_ts), link=m.ts.map(v.deep_link))[["event_index", "utc", "link", "speaker", "room", "context"]].to_csv(v.OUT / "misses_sample.csv", index=False)
print(f"position-wording messages: {len(vm)}; inside windows: {int(vm.window_id.notna().sum())}; cited as a coded position: "
      f"{int(vm.event_index.isin(cited).sum())}; loose vote-word messages: {len(a)}, outside windows: {len(out)}")
