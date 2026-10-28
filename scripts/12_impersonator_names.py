"""Task A1: every display name used by impersonation-style viewer accounts, 2025-04-01..2025-08-31.

An *account* (speakerId) is flagged impersonation-style in scripts/01_inventory_profile.py when any name it
ever used matches IMPERSONATION (verified|real |official|administrator|but not that|(REAL)|CEO|admin|zak|adam).
The 702 messages in the first-pass report are all messages from those 13 accounts in the window, under any
name. This sheet lists the names actually used per message, so names that do NOT themselves mimic an
organizer (e.g. "RedJ") are kept but flagged name_matches_regex=False.
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import village_lib as v  # noqa: E402

IMPERSONATION = re.compile(r"verified|real |official|administrator|but not that|\(REAL\)|CEO|\badmin\b|\bzak\b|\badam\b", re.I)
W0, W1 = "2025-04-01", "2025-09-01"

c = v.chat()
w = c[(c.ts >= W0) & (c.ts < W1) & (c.role == v.IMPERSONATION_ROLE)].copy()
assert len(w) == 702, len(w)
w["name"] = w.speaker.fillna("")
g = w.groupby("name").agg(
    n_messages=("id", "size"),
    first_message=("ts", "min"),
    last_message=("ts", "max"),
    first_event_index=("event_index", "min"),
    last_event_index=("event_index", "max"),
    n_accounts=("user_speaker_id", "nunique"),
    account_ids=("user_speaker_id", lambda s: " | ".join(sorted(set(s.dropna())))),
).reset_index().sort_values("n_messages", ascending=False)
for col in ("first_message", "last_message"):
    g[col] = g[col].map(v.fmt_ts)
g["first_deep_link"] = w.groupby("name").ts.min().reindex(g.name).map(v.deep_link).values
g["name_matches_regex"] = g.name.str.contains(IMPERSONATION)
low = g.name.str.lower()
g["has_verified"] = low.str.contains("verified")
g["has_admin"] = low.str.contains("admin")
g["has_ai_digest"] = low.str.contains("ai digest")
g["has_zak"] = low.str.contains(r"\bzak\b", regex=True)
g["has_adam"] = low.str.contains(r"\badam\b", regex=True)
g["has_shoshannah"] = low.str.contains("shoshannah")
g["has_other_authority_cue"] = low.str.contains(r"real|official|ceo|police|sfpd|god agent|larissa|openai|sam altman", regex=True)
g["n_instruction_like"] = g.name.map(pd.read_csv(v.OUT / "candidate_instructions.csv").query("impersonation_name").speaker.value_counts()).fillna(0).astype(int)
g.to_csv(v.OUT / "impersonator_names.csv", index=False)
print(g[["name", "n_messages", "n_instruction_like", "name_matches_regex", "has_verified", "has_admin", "has_ai_digest", "has_zak", "has_adam", "has_shoshannah", "first_message", "last_message"]].to_string(index=False))
print("names", len(g), "messages", g.n_messages.sum(), "names matching regex", g.name_matches_regex.sum(), "msgs under matching names", g[g.name_matches_regex].n_messages.sum())
print("day numbering check (n, mismatches):", v.check_day_numbering())
