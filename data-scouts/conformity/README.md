# Conformity: how often does any agent dissent in a group decision?

Data-scout case `conformity`. Definitions and null criteria: [HYPOTHESIS.md](HYPOTHESIS.md). One-page result:
[FINDINGS.md](FINDINGS.md). Hand checks: [VERIFICATION.md](VERIFICATION.md).

## Run

Needs the shared tables (repo README, "Core pipeline"). From the repo root:

```
./venv/bin/python3 -I data-scouts/conformity/scripts/01_vote_windows.py       # vote-wording messages -> 89 candidate windows + full transcripts
./venv/bin/python3 -I data-scouts/conformity/scripts/02_focus_transcripts.py  # short transcripts handed to coders
#   coding step (not a script): each out/focus/<id>.txt is coded into out/coded/<id>.json following CODING_SPEC.md.
#   Done here by Claude Sonnet sub-agents; the JSON files are committed because the step is not deterministic.
./venv/bin/python3 -I data-scouts/conformity/scripts/03_merge_coded.py        # machine-check quotes, apply decision_overrides.csv -> decisions.csv, positions.csv
./venv/bin/python3 -I data-scouts/conformity/scripts/04_measures.py           # rates, baselines, per-agent dissent, dissent list
./venv/bin/python3 -I data-scouts/conformity/scripts/05_wording_samples.py    # 100-match false-match sample, 20-message misses sample
```

## Outputs

| File | Written by | What |
|---|---|---|
| `out/vote_messages.csv`, `out/windows.csv` | `01`, `02` | 1,402 agent messages with first-person vote wording; 89 windows with at least 3 such agents |
| `out/windows/`, `out/focus/` (ignored) | `01`, `02` | full and short transcripts of each window |
| `CODING_SPEC.md` | by hand | the coding rules given to the coders |
| `out/coded/<id>.json` | coders | decisions and positions per window, each position with `event_index` and a verbatim quote |
| `decision_overrides.csv` | by hand | 8 corrections after reading every coded dissent, with reasons |
| `out/decisions.csv`, `out/positions.csv`, `out/coding_checks.csv` | `03` | one row per decision / per position; result of the quote check |
| `out/measures.csv` | `04` | every rate with numerator, denominator, level and scope; both baselines |
| `out/agent_dissent.csv`, `out/dissents.csv` | `04` | per-agent dissent; every dissent with its rows |
| `dissent_followup.csv` | by hand | what each unresolved dissenter did later the same day |
| `out/wording_sample.csv`, `out/misses_sample.csv`, `out/reread_sample.csv` | `05`, by hand | samples behind the reading checks in VERIFICATION.md |
