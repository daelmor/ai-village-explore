"""Step 8: mechanically drawn background terms for the base rate (HYPOTHESIS.md, placebo check 4).

Draws 240 agent-coined terms (Title Case or hyphenated, >= 3 chat messages, first use on or after 2025-04-16) from
out/candidate_terms.csv with random_state=0, with no look at memory and no reading. They are traced exactly like
the hand-picked memes; step 9 keeps the ones that were new to memory (no other agent had the wording before the
first chat use) and reports their adoption and retention as the base rate, overall and by origin year.

Reads   out/candidate_terms.csv
Writes  out/bg_terms.csv
Then:   ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/04_trace_memes.py --memes data-scouts/memetic-spread/out/bg_terms.csv --tag bg
        ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/05_measures.py   --memes data-scouts/memetic-spread/out/bg_terms.csv --tag bg
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/08_background_terms.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

T = pd.read_csv(v.OUT / "candidate_terms.csv", keep_default_na=False)
pool = T[T.kind.isin(["title", "hyph"]) & (T.origin_is_agent.astype(str) == "True") & (T.origin_utc >= "2025-04-16")]
pool = pool.sort_values(["origin_event_index", "term"]).drop_duplicates("term")
s = pool.sample(240, random_state=0).sort_values("origin_event_index")
rows = []
for i, t in enumerate(s.term):
    rx = re.escape(t).replace(r"\ ", "[ -]").replace(r"\-", "[ -]")
    rows.append(dict(meme_id=f"bg_{i:03d}_" + re.sub(r"[^a-z0-9]+", "_", t)[:30], regex=rx, set="background", term=t))
pd.DataFrame(rows).to_csv(v.OUT / "bg_terms.csv", index=False)
print(len(rows), "background terms from a pool of", len(pool), "| by origin year:", s.origin_utc.str[:4].value_counts().to_dict())
