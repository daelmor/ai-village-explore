"""Case library for `stuck-time`: re-exports the core helpers (core/village_lib.py) and adds this case's own
paths and classifiers. Every script in this folder starts with

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import case_lib as v

so `v.OUT` is this case's out/ folder, `v.SHARED` the shared core/out/ tables, `v.DATA` the raw downloads,
and every core helper (`v.chat()`, `v.events()`, `v.deep_link()`, `v.next_memory_diff()`, ...) is available.
Put regexes, labels and helpers that only make sense for this question here, not in core/village_lib.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core"))
from village_lib import *  # noqa: F401,F403,E402
from village_lib import case_dirs  # noqa: E402

CASE, OUT = case_dirs(__file__)

# --- case-specific classifiers below ---------------------------------------------------------------------
import re  # noqa: E402

import pandas as pd  # noqa: E402

# --- definitions fixed in HYPOTHESIS.md -------------------------------------------------------------------
POINTER = {"left_click", "double_click", "triple_click", "right_click", "middle_click", "left_click_drag",
           "left_mouse_down", "left_mouse_up"}
KEYS = {"type", "key", "hold_key"}
WORK = POINTER | KEYS | {"bash", "restart", "get_pixel_coords_of_element"}
NEUTRAL = {"none", "empty", "screenshot", "wait", "cursor_position", "mouse_move", "scroll", "view_clipboard",
           "send_message_back_to_chat"}
MIN_RUN = 5            # D1: consecutive work actions with one signature
D2_WINDOW, D2_MAX_SIGS = 8, 2
GAP_CAP_S = 300        # active time: inter-turn gaps capped at 5 minutes
MIN_HOURS, MIN_WORK = 20, 1000   # eligibility for the per-agent trend
CELL_MIN_AGENTS, CELL_MIN_HOURS = 4, 2

REGIMES = [("R1 sessions (to 2026-03-10)", "2025-04-01", "2026-03-11"),
           ("R2 transition (2026-03-11..23)", "2026-03-11", "2026-03-24"),
           ("R3 perma-computer-use (2026-03-24..09-30)", "2026-03-24", "2026-10-01"),
           ("R4 new bash tool (2026-10-01 on)", "2026-10-01", "2027-01-01")]

# Public release dates for 2025 models whose model_string carries no date (general knowledge, see HYPOTHESIS.md).
KNOWN_RELEASE = {"gemini-2.5-pro": "2025-03-25", "grok-4-0709": "2025-07-09", "gemini-3-pro-preview": "2025-11-18",
                 "deepseek-reasoner": "2025-12-01"}
_DATE = re.compile(r"(20\d{2})-?(\d{2})-?(\d{2})$")


def kind_group(kind):
    if kind == "bash" or kind == "restart":
        return "bash"
    if kind in POINTER:
        return "pointer"
    if kind in KEYS:
        return "key_type"
    if kind == "get_pixel_coords_of_element":
        return "pixel_coords"
    return "other"


def family(name, model_string=""):
    s = f"{name} {model_string}".lower()
    if "claude" in s or "opus" in s:
        return "Claude"
    if "gpt" in s or s.startswith(("o1", "o3", "o4")):
        return "OpenAI"
    if "gemini" in s:
        return "Gemini"
    return "Other"


def release_table():
    """agent id -> name, model_string, joined, release date and where that date comes from."""
    r = roster().copy()  # noqa: F405
    rel, src = [], []
    for ms, joined in zip(r.model_string.fillna(""), r.joined):
        m = _DATE.search(ms)
        if ms in KNOWN_RELEASE:
            rel.append(pd.Timestamp(KNOWN_RELEASE[ms])); src.append("public release (general knowledge)")
        elif m:
            rel.append(pd.Timestamp("-".join(m.groups()))); src.append("date in model_string")
        else:
            rel.append(joined.normalize() if pd.notna(joined) else pd.NaT); src.append("village join date (proxy)")
    r["release"], r["release_source"] = rel, src
    r["family"] = [family(n, m) for n, m in zip(r.name, r.model_string.fillna(""))]
    return r


def regime_of(ts):
    out = pd.Series("", index=ts.index, dtype=object)
    for name, a, b in REGIMES:
        out[(ts >= pd.Timestamp(a)) & (ts < pd.Timestamp(b))] = name
    return out
