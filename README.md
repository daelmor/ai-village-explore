# ai-village-explore

Data Scout exploration of the gated HuggingFace dataset `aidigestorg/ai-village` for the
AI Village Data Exploration Grant.

Research question: how do the Village agents recognize authority — whose instructions do they
follow (organizers vs. viewers vs. outside humans vs. other agents vs. automated nudges vs. a
delegated "leader" agent), and how do they respond to corrections?

## Layout

```
scripts/   numbered, re-runnable Python scripts (one per step)
out/       intermediate outputs and reports (INVENTORY.md, CSVs, parquet, episodes/)
data/      raw downloads from HuggingFace (git-ignored; re-create with the scripts)
venv/      Python virtualenv (git-ignored)
```

No HuggingFace token is stored in this repo. Authentication uses the token saved by `hf auth login`.
No screenshot / image files are ever downloaded; text, JSON and parquet only.

## Setup (macOS, Python 3.9)

```
python3 -m venv venv
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install huggingface_hub pandas pyarrow matplotlib
hf auth login   # once, if not already done
```

## Phase 0 — inventory

```
# download docs + small/medium tables + events (text only)
./venv/bin/python3 -I scripts/00_download.py
# flatten events into a slim, sorted parquet (drops the raw model `output` blob)
./venv/bin/python3 -I scripts/00_events_to_parquet.py data/events.jsonl.gz out/events_slim.parquet
# profile tables, export human-speaker roles and agent roster
./venv/bin/python3 -I scripts/01_inventory_profile.py
```

Outputs: `out/INVENTORY.md`, `out/inventory_stats.json`, `out/human_speakers.csv`, `out/agents_roster.csv`,
`out/events_slim.parquet` (git-ignored, 450k rows).

Later phases are added as `scripts/02_*.py` onward and documented here as they land.
