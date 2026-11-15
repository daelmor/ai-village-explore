"""Scaffold a new data-scout case from data-scouts/_template.

Usage: python3 core/scripts/new_scout.py <slug> ["Human readable title"]
  slug: lowercase words joined by hyphens, e.g. `memory-drift` or `email-trust`.
Creates data-scouts/<slug>/ with HYPOTHESIS.md, README.md, scripts/case_lib.py, scripts/01_first_look.py, out/.
Then add a row for the case in data-scouts/README.md.
"""
import datetime
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "data-scouts" / "_template"

if len(sys.argv) < 2 or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", sys.argv[1]):
    sys.exit(__doc__)
slug = sys.argv[1]
title = sys.argv[2] if len(sys.argv) > 2 else slug.replace("-", " ").capitalize()
dst = ROOT / "data-scouts" / slug
if dst.exists():
    sys.exit(f"{dst} already exists")

shutil.copytree(TEMPLATE, dst, ignore=shutil.ignore_patterns("__pycache__"))
subs = {"{{slug}}": slug, "{{title}}": title, "{{date}}": datetime.date.today().isoformat()}
for p in dst.rglob("*"):
    if p.is_file() and p.suffix in (".md", ".py"):
        s = p.read_text()
        for k, val in subs.items():
            s = s.replace(k, val)
        p.write_text(s)
print(f"Created {dst.relative_to(ROOT)}/ — next: write HYPOTHESIS.md, edit scripts/01_first_look.py, "
      f"and add the case to data-scouts/README.md")
