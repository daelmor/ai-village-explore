"""Step 2: mechanical list of novel terms coined in chat (candidate memes and the pool for the background rate).

A *term* is a hyphenated compound (`pull-based`), a Title Case phrase of 2-4 words (`Pull Based Kindness`) or a
quoted phrase of 6-50 characters, lower-cased. For every term: the first chat message using it (the origin), who
said it, how often the originator repeated it, and how many *other* agents used it in chat within 7 and 30 days.
Nothing here looks at memory; this is only a reading list. Terms whose first use falls in the first 14 days of
the dataset are dropped (left-censored: we cannot tell whether they were new).

Reads   core/out/chat.parquet
Writes  out/candidate_terms.csv         every term with >= 3 chat messages and an agent or human origin
        out/candidate_terms_top.csv     reading list: 150 most-spread agent-coined + 100 most-spread human-coined terms
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/02_candidate_terms.py
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

HYPH = re.compile(r"\b[A-Za-z][A-Za-z0-9]+(?:-[A-Za-z0-9]+){1,3}\b")
TITLE = re.compile(r"\b(?:[A-Z][a-z0-9]+[ ]){1,3}[A-Z][a-z0-9]+\b")
QUOTE = re.compile(r"[\"“]([^\"“”\n]{6,50})[\"”]")
URLISH = re.compile(r"https?://\S+|\S+@\S+|\S+\.(?:com|org|io|md|py|json|html|csv|app|dev|ai)\b\S*")

c = v.chat()
c = c[~c.is_nudge & ~c.is_pause_resume].reset_index(drop=True)
agent_names = set(v.roster().name.str.lower())
START = c.ts.min() + pd.Timedelta(days=14)

uses = defaultdict(list)  # term -> [(row index)]
for i, text in enumerate(c.content.values):
    text = URLISH.sub(" ", text)
    seen = set()
    for m in HYPH.finditer(text):
        seen.add(("hyph", m.group(0).lower()))
    for m in TITLE.finditer(text):
        seen.add(("title", m.group(0).lower()))
    for m in QUOTE.finditer(text):
        seen.add(("quote", m.group(1).strip().lower()))
    for k in seen:
        uses[k].append(i)

ts = c.ts.values
spk = c.speaker.fillna("?").values
is_agent = (c.speaker_type == "agent").values
role = c.role.values
ei = c.event_index.values
rows = []
for (kind, term), idxs in uses.items():
    if len(idxs) < 3:
        continue
    i0 = idxs[0]
    t0 = ts[i0]
    if pd.Timestamp(t0) < START:
        continue
    if kind != "quote" and any(n in term for n in agent_names):
        continue  # agent names ("claude opus 4") are not coinages
    o = spk[i0]
    d7, d30 = t0 + pd.Timedelta(days=7).to_timedelta64(), t0 + pd.Timedelta(days=30).to_timedelta64()
    others7 = {spk[i] for i in idxs if is_agent[i] and spk[i] != o and ts[i] <= d7}
    others30 = {spk[i] for i in idxs if is_agent[i] and spk[i] != o and ts[i] <= d30}
    rows.append(dict(kind=kind, term=term, origin_event_index=int(ei[i0]), origin_utc=v.fmt_ts(t0), origin_speaker=o,
                     origin_role=role[i0], origin_is_agent=bool(is_agent[i0]), n_messages=len(idxs),
                     origin_uses_7d=sum(1 for i in idxs if spk[i] == o and ts[i] <= d7),
                     other_agents_7d=len(others7), other_agents_30d=len(others30),
                     other_agents_ever=len({spk[i] for i in idxs if is_agent[i] and spk[i] != o}),
                     last_use_utc=v.fmt_ts(ts[idxs[-1]]), span_days=round((ts[idxs[-1]] - t0) / pd.Timedelta(days=1).to_timedelta64(), 1),
                     origin_text=c.content.values[i0][:300].replace("\n", " ")))
T = pd.DataFrame(rows).sort_values(["other_agents_7d", "n_messages"], ascending=False).reset_index(drop=True)
T.to_csv(v.OUT / "candidate_terms.csv", index=False)
top = pd.concat([T[T.origin_is_agent].head(150), T[~T.origin_is_agent].head(100)])
top.to_csv(v.OUT / "candidate_terms_top.csv", index=False)
print(len(T), "terms;", T.kind.value_counts().to_dict(), "| agent-coined", int(T.origin_is_agent.sum()))
print(T.groupby("origin_is_agent").other_agents_7d.describe().round(2).to_string())
