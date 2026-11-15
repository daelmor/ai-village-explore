"""Step 6: build the term list for the correction design (HYPOTHESIS.md, addendum H7).

Combines the hand-listed friction lexicon (friction_terms.csv) with 60 control terms drawn mechanically from
out/candidate_terms.csv (Title Case or hyphenated, first chat use 2025-11-25 .. the correction, >= 5 chat messages,
no lexicon word, random_state=0), in the registry format that 04_trace_memes.py reads.

Reads   friction_terms.csv, out/candidate_terms.csv
Writes  out/fx_terms.csv    (meme_id, regex, set = hazard / concept / confirmed / control)
Then:   ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/04_trace_memes.py --memes data-scouts/memetic-spread/out/fx_terms.csv --tag fx
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/06_friction_terms.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

F = pd.read_csv(v.CASE / "friction_terms.csv", keep_default_na=False)
LEX = re.compile(r"friction|ghost|phantom|schr|reality|entropy|bottleneck|zombie|void|blockade|trap|blur|drift|amnesia|freeze|"
                 r"backspace|sandcastle|archipelago|antibody|wall|lock|illusion|blocker|fragility|mirage|contamination|bug|"
                 r"hazard|atlas|evidence|law of", re.I)
T = pd.read_csv(v.OUT / "candidate_terms.csv", keep_default_na=False)
pool = T[T.kind.isin(["title", "hyph"]) & (T.origin_utc >= "2025-11-25") & (T.origin_utc < v.CORRECTION_UTC) & (T.n_messages >= 5)]
pool = pool[~pool.term.str.contains(LEX)]
pool = pool[~pool.term.map(lambda t: any(re.search(r, t, re.I) for r in F.regex))]
pool = pool.sort_values(["origin_event_index", "term"]).drop_duplicates("term")
ctl = pool.sample(60, random_state=0).sort_values("origin_event_index")
rows = [dict(meme_id=r.term_id, regex=r.regex, set=r["class"]) for _, r in F.iterrows()]
for i, t in enumerate(ctl.term):
    rx = re.escape(t).replace(r"\ ", "[ -]").replace(r"\-", "[ -]")
    rows.append(dict(meme_id=f"ctl_{i:02d}_" + re.sub(r"[^a-z0-9]+", "_", t)[:30], regex=rx, set="control"))
pd.DataFrame(rows).to_csv(v.OUT / "fx_terms.csv", index=False)
print(len(F), "lexicon terms +", len(ctl), "control terms from a pool of", len(pool))
print(ctl[["term", "origin_speaker", "n_messages", "other_agents_7d"]].to_string(index=False))
