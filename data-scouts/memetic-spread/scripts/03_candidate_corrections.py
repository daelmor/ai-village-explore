"""Step 3: origin-side reading lists that do not condition on spread.

(a) Organizer messages that correct a belief or state a standing rule (cue regex), with the three agent
    messages before and after, so the corrected claim can be traced back to its first utterance.
(b) Agent messages that retract or debunk a claim ("false alarm", "I was wrong", "hallucinated", ...).
Both are pointers to rows for reading, not results.

Reads   core/out/chat.parquet
Writes  out/candidate_corrections_organizer.csv, out/candidate_corrections_agent.csv
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/03_candidate_corrections.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

ORG_CUE = re.compile(
    r"not true|n[o']t (?:actually|correct|accurate|the case|real)\b|incorrect|inaccurate|hallucinat|"
    r"there (?:is|was|are|were) no\b|there'?s no\b|do(?:es)?n[o']t exist|never said|did(?: no|n')t say|mistaken|"
    r"to (?:clarify|be clear)|clarif|misunderst|confus|made[- ]up|fabricat|false|wrong|"
    r"please (?:do not|don'?t|stop|always|never|avoid)|from now on|going forward|in future|you (?:should|must) (?:not|never|always)|"
    r"(?:new|a) rule|not allowed|you (?:can|may)(?:no|')?t\b", re.I)
AGENT_CUE = re.compile(
    r"false alarm|i was (?:wrong|mistaken|incorrect)|i (?:hereby )?retract|retraction|i hallucinated|was a hallucination|"
    r"(?:was|were|is|are) (?:fabricated|hallucinated|a fabrication)|turn(?:s|ed) out (?:to be )?(?:false|wrong|incorrect|untrue|not true)|"
    r"i (?:incorrectly|mistakenly|wrongly|falsely) (?:claimed|stated|reported|said|believed|assumed)|"
    r"(?:my|our|the) (?:earlier|previous|prior) (?:claim|statement|report|belief|assumption) (?:was|were) (?:wrong|incorrect|false|mistaken)|"
    r"does not (?:actually )?exist|never (?:actually )?existed|phantom|debunk|misinformation|not a (?:real|platform) (?:bug|issue)", re.I)

c = v.chat()
c = c[~c.is_nudge & ~c.is_pause_resume].reset_index(drop=True)
pos_agent = c.index[c.speaker_type == "agent"].values


def ctx(i, k=3):
    j = pos_agent.searchsorted(i)
    before = [v.fmt_msg(c.iloc[p], 260) for p in pos_agent[max(j - k, 0):j]]
    after = [v.fmt_msg(c.iloc[p], 260) for p in pos_agent[j + (1 if j < len(pos_agent) and pos_agent[j] == i else 0):][:k]]
    return " || ".join(before), " || ".join(after)


def export(sel, path):
    rows = []
    for i in c.index[sel]:
        r = c.iloc[i]
        b, a = ctx(i)
        rows.append(dict(event_index=r.event_index, utc=v.fmt_ts(r.ts), link=v.deep_link(r.ts), room=r.room, role=r.role,
                         speaker=r.speaker, content=r.content, agent_msgs_before=b, agent_msgs_after=a))
    pd.DataFrame(rows).to_csv(path, index=False)
    return len(rows)


org = c.role.isin(v.ORGANIZER_ROLES) & c.content.str.contains(ORG_CUE)
n1 = export(org, v.OUT / "candidate_corrections_organizer.csv")
ag = (c.speaker_type == "agent") & c.content.str.contains(AGENT_CUE)
n2 = export(ag, v.OUT / "candidate_corrections_agent.csv")
print("organizer cue rows:", n1, "of", int(c.role.isin(v.ORGANIZER_ROLES).sum()), "organizer messages")
print("agent cue rows:", n2, "of", int((c.speaker_type == 'agent').sum()), "agent messages")
print(c[ag].groupby(c.ts.dt.strftime("%Y-%m")).size().to_string())
