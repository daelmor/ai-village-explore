# Conformity: how often does any agent dissent in a group decision?

Data-scout case `conformity`. Hypotheses, status and findings: [HYPOTHESIS.md](HYPOTHESIS.md).

## Run

Needs the shared tables first (see the repo README, "Core pipeline"). Then, from the repo root:

```
./venv/bin/python3 -I data-scouts/conformity/scripts/01_first_look.py   # out/first_look.csv, out/first_look_sample.csv
```

Add one numbered script per step and list it here with the files it writes.

## Outputs

| File | Written by | What |
|---|---|---|
| `out/first_look.csv` | `01_first_look.py` | keyword hits per month and role |
