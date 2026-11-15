"""Case library for `conformity`: re-exports the core helpers (core/village_lib.py) and adds this case's own
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

# First-person position wording: seeds candidate windows (script 01). Literal search: read matches before trusting.
POS = re.compile(
    r"\b(i|we)('m| am| will| would|'ll|'d| have|'ve)? (hereby |officially |formally |also |now |still |therefore |thus |do |"
    r"strongly |fully |too |just |already )*(cast|vote|voted|voting|nominate|second|accuse|endorse|approve|object|dissent|"
    r"abstain|veto|concur)\b"
    r"|\bmy (vote|ballot|pick|nomination)\b"
    r"|\bvot(e|ing) (is |goes |remains |stands )?(for|to|against|yes|no|aye|nay)\b"
    r"|\b(aye|nay|yea)\b"
    r"|\bi (support|oppose|back|favor|favour|reject|accept) (the|this|that|[\w.\- ]{2,25}'s) (proposal|motion|plan|nomination|candidacy)"
    r"|(^|\s)\+1\b"
    r"|\bvote\s*[:—-]\s*\S", re.I)
# Any vote / election word: used for the false-match sample and the misses check.
LOOSE = re.compile(r"\bvot(e|es|ed|ing)\b|\bballot|\belect(ion|ed)?\b|\bnominat|\bunanimous|\bconsensus\b|\bpoll\b", re.I)
GAP_H = 3          # windows: position messages in one room separated by at most this many hours
PAD_MIN = 60       # transcript padding before / after a window
MIN_AGENTS = 3     # distinct agents with a position message
# Decision vocabulary: which messages of a window go into the short "focus" transcript handed to coders.
DEC = re.compile(
    LOOSE.pattern + "|" + POS.pattern +
    r"|\bpropos|\bobject(ion|s)?\b|\bseconded\b|\baccus|\bsaboteur|\bcandidate|\btie\b|\brun-?off|\babstain|\bdissent"
    r"|\bdisagree|\boppose|\bmotion\b|\bemergency meeting|\beject|\bquorum|\btally|\bveto", re.I)
