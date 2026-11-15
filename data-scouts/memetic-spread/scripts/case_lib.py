"""Case library for `memetic-spread`: re-exports the core helpers (core/village_lib.py) and adds this case's own
paths and helpers. Every script in this folder starts with

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import case_lib as v

so `v.OUT` is this case's out/ folder, `v.SHARED` the shared core/out/ tables, `v.DATA` the raw downloads,
and every core helper (`v.chat()`, `v.events()`, `v.deep_link()`, ...) is available.
"""
import re as _re
import sys
from pathlib import Path

import pandas as _pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core"))
from village_lib import *  # noqa: F401,F403,E402
from village_lib import case_dirs, chat, roster  # noqa: E402

CASE, OUT = case_dirs(__file__)
MEMES = CASE / "memes.csv"
LINES = OUT / "memory_lines.parquet"

DAY = _pd.Timedelta(days=1)

# adam's correction of the "friction" reports, event_index 137163 (HYPOTHESIS.md addendum, H7)
CORRECTION_EI = 137163
CORRECTION_UTC = "2025-12-09 20:59:04"
CORRECTION_TS = _pd.Timestamp(CORRECTION_UTC)
NAMED_AGENTS = ("Gemini 3 Pro", "Gemini 2.5 Pro")


def memes():
    """The meme registry (hand-curated). One row per meme; `regex` is case-insensitive and must stay within the
    syntax shared by Python `re` and RE2 (no look-arounds, no back-references) because memory lines are matched
    with pyarrow (RE2) and chat/events with pandas (`re`)."""
    m = _pd.read_csv(MEMES, keep_default_na=False)
    m["rx"] = m.regex.map(lambda s: _re.compile(s, _re.I))
    return m


def family(name):
    """Model family of an agent display name (used only for within-meme comparisons)."""
    n = str(name).lower()
    for key, fam in (("claude", "Claude"), ("opus", "Claude"), ("gpt", "GPT"), ("o1", "GPT"), ("o3", "GPT"), ("o4", "GPT"),
                     ("gemini", "Gemini"), ("deepseek", "DeepSeek"), ("grok", "Grok"), ("kimi", "Kimi"), ("glm", "GLM"),
                     ("muse", "Muse"), ("leader", "Kimi")):
        if key in n:
            return fam
    return "other"


def chat_clean():
    """Chat without the nudger bot and the daily pause/resume lines."""
    c = chat()
    return c[~c.is_nudge & ~c.is_pause_resume].reset_index(drop=True)
