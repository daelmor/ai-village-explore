"""First look for `{{slug}}`: size the evidence before writing any heuristic.

Writes out/first_look.csv: chat messages per month and role matching KEYWORDS, plus a 100-row sample
(out/first_look_sample.csv) with event_index, UTC timestamp and deep link for every row.
Usage: ./venv/bin/python3 -I data-scouts/{{slug}}/scripts/01_first_look.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

KEYWORDS = re.compile(r"CHANGE_ME", re.I)  # TODO: the terms that operationalize the hypothesis

c = v.chat()
hits = c[c.content.str.contains(KEYWORDS)].copy()
hits["month"] = hits.ts.dt.strftime("%Y-%m")
hits.groupby(["month", "role"]).size().rename("n").reset_index().to_csv(v.OUT / "first_look.csv", index=False)

sample = hits.sample(min(100, len(hits)), random_state=0).sort_values("event_index") if len(hits) else hits
sample = sample.assign(utc=sample.ts.map(v.fmt_ts), link=sample.ts.map(v.deep_link))
sample[["event_index", "utc", "link", "role", "speaker", "room", "content"]].to_csv(v.OUT / "first_look_sample.csv", index=False)
print(f"{len(hits)} matching messages" + (" (sampled 100)" if len(hits) > 100 else ""))
