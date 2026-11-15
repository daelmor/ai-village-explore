# Authority recognition

Data-scout case `authority-recognition`, prepared for the AI Village Data Exploration Grant and a LessWrong post.
Question, hypotheses and status: [HYPOTHESIS.md](HYPOTHESIS.md). Final report: [out/EXPLORATION.md](out/EXPLORATION.md).

Research question: how do the Village agents recognize authority — whose instructions do they follow (organizers vs.
viewers vs. outside humans vs. other agents vs. automated nudges vs. a delegated "leader" agent), and how do they
respond to corrections?

## Run

Build the shared tables first (repo README, "Core pipeline"; this case needs `00_download.py --big` and
`04_memories_shard.py` for the memory steps). Then, from the repo root (scripts also work from any directory):

Script numbers are historical: the gaps (00, 01, 03, 07) are the steps that moved to `core/scripts/`, and the
committed reports cite the scripts by these names.

### Phases 1–5

```
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/02_phase1_organizers_goals.py   # out/organizer_messages.csv, out/goals.csv
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/04_candidate_instructions.py    # out/candidate_instructions.csv (+_README.md)
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/05_episodes.py                  # out/episodes/*.md (chat, summaries, events)
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/06_leader_directives.py         # out/leader_directives*.csv, leader_reflections.csv, summary
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/08_episode_memories.py          # out/episodes/*_memories.md
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/09_memory_mentions.py           # out/memory_mentions.csv(.gz) + sample
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/10_goal_persistence.py          # out/goal_persistence.csv + .png
./venv/bin/python3 -I data-scouts/authority-recognition/scripts/11_response_coding.py           # out/instruction_responses.csv + summary (regex-coded; noisy)
```

Hand-verified incident write-ups: `out/incidents_ep1_ep2.md`, `out/incidents_ep3_ep4.md`, `out/incidents_ep5_ep6.md`,
`out/incidents_ep7_ep8.md`. `out/memory_mentions.csv` is not in git (the `.gz` is); re-create it with `09`.

### Second pass (LessWrong post evidence)

`scripts/case_lib.py` re-exports the core helpers (day numbers, deep links, memory-snapshot diffs, active-agent
lookup) and holds this case's `mimic_type()` name classifier. Coding sheets have empty `complied`,
`cited_impersonator`, `memory_write_through` columns for hand coding; the `_long` files have one row per
instruction × active agent.

```
S=data-scouts/authority-recognition/scripts
./venv/bin/python3 -I $S/12_impersonator_names.py   # out/impersonator_names.csv (Task A1)
./venv/bin/python3 -I $S/13_coding_sheets.py        # out/impersonation_coding(.csv|_long.csv), out/organizer_coding(.csv|_long.csv) (A2, A3)
./venv/bin/python3 -I $S/14_recapture_verbatim.py   # out/episodes/recapture_verbatim.md, out/recapture_memory_survival.csv (A4)
./venv/bin/python3 -I $S/15_nudger.py --scan && ./venv/bin/python3 -I $S/15_nudger.py   # out/nudger_stats.csv, out/episodes/nudger_verbatim.md
./venv/bin/python3 -I $S/16_haiku_refusal.py --scan && ./venv/bin/python3 -I $S/16_haiku_refusal.py   # out/episodes/haiku_refusal_verbatim.md
./venv/bin/python3 -I $S/17_kindness_write_through.py && ./venv/bin/python3 -I $S/17b_kindness_rule_lines.py   # out/kindness_write_through.csv, out/episodes/kindness_verbatim.md
./venv/bin/python3 -I $S/18_leader_dispute.py        # out/episodes/leader_dispute_verbatim.md
./venv/bin/python3 -I $S/19_inbound_email_probe.py   # out/inbound_email_probe.md, out/inbound_email_hits.csv (streams computer_use_turns, ~8 min; --reuse uses the cache)
./venv/bin/python3 -I $S/20_reply_rates.py           # out/reply_rates.csv, out/reply_rates_pairs.csv, out/fig_reply_rates.png
./venv/bin/python3 -I $S/21_charts.py                # out/fig_impersonation_weekly.png, out/fig_authority_timeline.png
```

The `--scan` flags stream `data/computer_use_turns.jsonl.gz` (3.8 GB) once and cache text-only extracts as
`out/turns_*.parquet` (git-ignored). Results are written up in `out/EXPLORATION.md` § "Second pass".

### Addendum (staff authorizations Oct 2026, nudger pause-again)

```
./venv/bin/python3 -I $S/22_oct2026_turns.py --scan --analyze   # out/turns_oct2026.parquet, staff_authorization_turns.csv, social_posting_oct2026.csv
./venv/bin/python3 -I $S/23_nudger_pause_again.py              # adds pause_again columns to out/nudger_stats.csv
./venv/bin/python3 -I $S/24_staff_authorization_oct2026.py     # out/staff_authorization_oct2026.csv (+ summary .md)
```
