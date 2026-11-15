"""Case library for `{{slug}}`: re-exports the core helpers (core/village_lib.py) and adds this case's own
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
