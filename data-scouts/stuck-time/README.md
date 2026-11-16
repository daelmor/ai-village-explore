# Stuck time: has the time agents spend stuck fallen with newer models?

Data-scout case `stuck-time`. Definitions and null criteria: [HYPOTHESIS.md](HYPOTHESIS.md). One-page result:
[FINDINGS.md](FINDINGS.md). Hand checks: [VERIFICATION.md](VERIFICATION.md).

## Run

Needs `data/computer_use_turns.jsonl.gz` (already downloaded by `core/scripts/00_download.py --big`) and the shared
tables. From the repo root:

```
./venv/bin/python3 -I data-scouts/stuck-time/scripts/01_scan_actions.py    # one pass over the 3.8 GB turns file -> out/turn_actions.parquet
./venv/bin/python3 -I data-scouts/stuck-time/scripts/02_episodes.py        # D1 episodes, D2 stretches, per-agent / regime / cell tables
./venv/bin/python3 -I data-scouts/stuck-time/scripts/03_trend.py           # H1-H4 tests, within-cell test, provider before/after
./venv/bin/python3 -I data-scouts/stuck-time/scripts/04_reading_sample.py  # 30 random episodes with their turns, for reading
./venv/bin/python3 -I data-scouts/stuck-time/scripts/05_raw_rows.py        # second pass: raw rows + narration of the read episodes
./venv/bin/python3 -I data-scouts/stuck-time/scripts/06_figure.py          # figure and its table view
```

## Outputs

| File | Written by | What |
|---|---|---|
| `out/turn_actions.parquet` (ignored) | `01` | one row per turn: ids, time, action kind, signature hash, excerpts of action / output / error |
| `out/episodes.parquet`, `out/episodes_d2.parquet` (ignored) | `02` | every D1 episode and D2 stretch |
| `out/agent_stuck.csv` | `02` | per agent: active hours, work actions, episodes, rates, recovery, release date and its source |
| `out/agent_regime.csv`, `out/agent_cell.csv`, `out/kind_breakdown.csv` | `02` | the same per scaffolding regime, per goal-period x room cell, and per action kind |
| `out/trend_tests.csv`, `out/cell_tests.csv`, `out/provider_changes.csv` | `03` | every correlation with n and permutation p; one row per cell; 21-day before / after rates |
| `out/reading_sample.md`, `out/reading_sample.csv` | `04` | the 30 episodes read by hand |
| `reading_codes.csv` | by hand | stuck / not stuck / unclear for each of the 30, with the reason |
| `out/verified_raw_turns.jsonl` | `05` | raw rows (action, output, error, narration) for the read episodes |
| `out/fig_stuck_vs_release.png`, `out/fig_stuck_vs_release_data.csv` | `06` | figure: episodes vs release date, all / GUI only / bash only |
