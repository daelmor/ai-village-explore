"""Case library for `authority-recognition`: re-exports the core helpers (core/village_lib.py) and adds
this case's own paths and classifiers. Every script in this folder does

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import case_lib as v

so `v.OUT` is this case's out/ folder, `v.SHARED` the shared core/out/ tables, `v.DATA` the raw downloads,
and every core helper (`v.chat()`, `v.deep_link()`, `v.next_memory_diff()`, ...) is available.
"""
import re as _re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core"))
from village_lib import *  # noqa: F401,F403,E402
from village_lib import case_dirs  # noqa: E402

CASE, OUT = case_dirs(__file__)

# --- impersonation name classes -------------------------------------------------------------------------

IMPERSONATION_RE = _re.compile(r"verified|real |official|administrator|but not that|\(REAL\)|CEO|\badmin\b|\bzak\b|\badam\b", _re.I)
PARODY_RE = _re.compile(r"but not \*?that\*?", _re.I)


def mimic_type(name):
    """deceptive = name claims to be an organizer/admin/staff with no disclaimer ("zak", "zak (verified)",
    "Administrator", "Official Admin (verified)", "AI Digest CEO (verified)", "adam", "Larissa (REAL)", "real Zak");
    parody = name self-discloses it is not the organizer ("adam (but not that adam)");
    account_level = a plain handle used by an account that at some other time used a mimicking name."""
    n = str(name or "")
    if PARODY_RE.search(n):
        return "parody"
    if IMPERSONATION_RE.search(n):
        return "deceptive"
    return "account_level"
