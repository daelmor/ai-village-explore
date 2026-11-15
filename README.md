# ai-village-explore

A small framework for evidence-first research on the gated HuggingFace dataset `aidigestorg/ai-village`.
A shared **core** builds the dataset-level tables once; each **data scout** (a research case with its own
question and hypotheses) lives in its own folder under `data-scouts/` and reads those shared tables.

The first case, built for the AI Village Data Exploration Grant, is
[`data-scouts/authority-recognition`](data-scouts/authority-recognition/): whose instructions do the Village
agents follow, and how do they respond to corrections? The full index is in [data-scouts/README.md](data-scouts/README.md).

## Layout

```
core/
  village_lib.py      shared helpers: paths, day numbers, deep links, loaders for the shared tables,
                      memory-snapshot diffs, active-agent lookup (nothing case-specific)
  scripts/            numbered pipeline that builds the shared tables, plus new_scout.py (scaffolding)
  out/                shared tables + dataset inventory (INVENTORY.md); large parquet files are git-ignored
data-scouts/
  README.md           index of cases, anatomy of a case, conventions
  _template/          skeleton copied by core/scripts/new_scout.py
  <case-slug>/
    HYPOTHESIS.md     question, hypotheses (with refutation criteria), status, findings
    README.md         run order and outputs of this case
    scripts/          case_lib.py (re-exports core + case-specific classifiers) and numbered steps
    out/              this case's outputs and reports
data/                 raw downloads from HuggingFace (git-ignored; shared by every case)
venv/                 Python virtualenv (git-ignored)
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

## Core pipeline (run once, shared by every case)

All scripts resolve paths from their own location, so they can be run from any directory.

```
./venv/bin/python3 -I core/scripts/00_download.py           # docs + small/medium tables + events into data/ (add --big for agent_memories, 3 GB)
./venv/bin/python3 -I core/scripts/01_events_to_parquet.py  # core/out/events_slim.parquet (drops the raw model `output` blob)
./venv/bin/python3 -I core/scripts/02_inventory_profile.py  # core/out/human_speakers.csv, agents_roster.csv, inventory_stats.json
./venv/bin/python3 -I core/scripts/03_build_chat_table.py   # core/out/chat.parquet (every chat message, resolved speaker/role/room/goal)
./venv/bin/python3 -I core/scripts/04_memories_shard.py     # core/out/memories/<agent_id>.parquet + memories_index.parquet (needs --big)
```

| Shared table | What | In git |
|---|---|---|
| `core/out/INVENTORY.md` | schema and table-by-table inventory of the export | yes |
| `core/out/human_speakers.csv` | every human account → names used, message counts, role label (organizer / system / helper / viewer) | yes |
| `core/out/agents_roster.csv` | agent id → name, model, joined / left | yes |
| `core/out/inventory_stats.json` | row counts and value counts behind INVENTORY.md | yes |
| `core/out/events_slim.parquet` | all events, `data.*` flattened, no `output` blob (450k rows) | no |
| `core/out/chat.parquet` | all chat messages with speaker, role, room, active goal | no |
| `core/out/memories/`, `memories_index.parquet` | per-agent memory snapshots (279k) | no |

`computer_use_turns.jsonl.gz` (3.8 GB) is not part of the core pipeline: cases that need it stream it once
with a `--scan` flag and cache text-only extracts in their own `out/` (git-ignored).

## Starting a new case

```
python3 core/scripts/new_scout.py <slug> "Human readable title"   # e.g. memory-drift "Do memories drift from what happened?"
```

This copies `data-scouts/_template/` to `data-scouts/<slug>/`. Then: write the question and hypotheses in
`HYPOTHESIS.md` (with what would refute each one) before looking at results, edit `scripts/01_first_look.py`,
and add a row to [data-scouts/README.md](data-scouts/README.md). If a helper turns out to be useful to more than
one case, move it from the case's `case_lib.py` into `core/village_lib.py`.

## Working rules (all cases)

- Every claim cites raw rows: `event_index` + UTC timestamp + deep link
  (`https://theaidigest.org/village?day={day}&time={unix_ms}`, built by `village_lib.deep_link`), or a memory snapshot id.
  The day number is calendar days since 2025-04-02 plus one, rolling at 17:00 UTC (verified against all 380 numbered
  daily summaries; see `core/village_lib.py`).
- If a heuristic yields more than 500 rows, sample 100 and say so. Regex coding is a pointer to rows, not a result:
  check it against a base rate / placebo window and read the rows.
- Prefer pandas; no compiled dependencies when a pure-Python option exists. Run scripts that read downloaded data with
  `python3 -I`.
- GitHub rejects files over 100 MB: commit large CSVs gzipped and git-ignore parquet caches; every git-ignored file must
  be re-creatable by a script.
