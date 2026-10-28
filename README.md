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

## Phases 1–5

```
./venv/bin/python3 -I scripts/02_phase1_organizers_goals.py   # out/organizer_messages.csv, out/goals.csv
./venv/bin/python3 -I scripts/03_build_chat_table.py          # out/chat.parquet (shared enriched chat table)
./venv/bin/python3 -I scripts/04_candidate_instructions.py    # out/candidate_instructions.csv (+_README.md)
./venv/bin/python3 -I scripts/05_episodes.py                  # out/episodes/*.md (chat, summaries, events)
./venv/bin/python3 -I scripts/06_leader_directives.py         # out/leader_directives*.csv, leader_reflections.csv, summary
./venv/bin/python3 -I scripts/07_memories_shard.py            # out/memories/<agent_id>.parquet + memories_index.parquet (needs --big download)
./venv/bin/python3 -I scripts/08_episode_memories.py          # out/episodes/*_memories.md
./venv/bin/python3 -I scripts/09_memory_mentions.py           # out/memory_mentions.csv(.gz) + sample
./venv/bin/python3 -I scripts/10_goal_persistence.py          # out/goal_persistence.csv + .png
./venv/bin/python3 -I scripts/11_response_coding.py           # out/instruction_responses.csv + summary (regex-coded; noisy)
```

Hand-verified incident write-ups: `out/incidents_ep1_ep2.md`, `out/incidents_ep3_ep4.md`,
`out/incidents_ep5_ep6.md`, `out/incidents_ep7_ep8.md`. Final report: `out/EXPLORATION.md`.

Large derived files not in git: `out/chat.parquet`, `out/events_slim.parquet`, `out/memories/`,
`out/memory_mentions.csv` (the `.gz` is committed). Re-create with the scripts above.
Download the two big source tables with `./venv/bin/python3 -I scripts/00_download.py --big`
(agent_memories, 3 GB) and, if needed, `computer_use_turns.jsonl.gz` (3.8 GB) via huggingface_hub.

## Second pass (LessWrong post evidence)

Deep links follow the dataset README: `https://theaidigest.org/village?day={day}&time={unix_ms}`.
The day number is calendar days since 2025-04-02 plus one, rolling at 17:00 UTC (verified against all
380 daily summaries that carry a numeric day; see `scripts/village_lib.py`).

```
./venv/bin/python3 -I scripts/12_impersonator_names.py   # out/impersonator_names.csv (Task A1)
./venv/bin/python3 -I scripts/13_coding_sheets.py        # out/impersonation_coding(.csv|_long.csv), out/organizer_coding(.csv|_long.csv) (A2, A3)
./venv/bin/python3 -I scripts/14_recapture_verbatim.py   # out/episodes/recapture_verbatim.md, out/recapture_memory_survival.csv (A4)
```

`scripts/village_lib.py` holds the shared helpers (day numbers, deep links, memory-snapshot diffs,
active-agent lookup). Coding sheets have empty `complied`, `cited_impersonator`, `memory_write_through`
columns for hand coding; the `_long` files have one row per instruction x active agent.
