# Data scouts

Each folder here is one research case: a question about the AI Village agents, stated as hypotheses with
refutation criteria, plus the scripts and outputs that test them. All cases read the same shared tables in
`core/out/` (built once by `core/scripts/`, see the repo README) and write only to their own `out/`.

## Cases

| Case | Question | Status | Report |
|---|---|---|---|
| [authority-recognition](authority-recognition/) | Whose instructions do the agents follow (organizers, viewers, impersonators, outside humans, other agents, the automated nudger, a delegated leader), and how do they respond to corrections? | verified, write-up pending | [out/EXPLORATION.md](authority-recognition/out/EXPLORATION.md) |

Status values: `idea` → `exploring` → `verified` → `written-up` → `archived`.

## Anatomy of a case

```
data-scouts/<slug>/
  HYPOTHESIS.md   question, hypotheses table (supports if / refutes if / status / evidence), data, limits, findings
  README.md       run order: one line per script with the files it writes; table of outputs
  scripts/
    case_lib.py   `import case_lib as v` → v.OUT (this case's out/), v.SHARED (core/out/), v.DATA (data/),
                  every core helper (v.chat(), v.events(), v.roster(), v.deep_link(), v.next_memory_diff(), ...)
                  and this case's own regexes / labels / classifiers
    NN_step.py    numbered, re-runnable steps; each starts with
                    sys.path.insert(0, str(Path(__file__).resolve().parent)); import case_lib as v
  out/            CSVs, markdown reports, figures; large caches as *.parquet (git-ignored)
```

Create one with `python3 core/scripts/new_scout.py <slug> "Title"` (copies [_template/](_template/)).

## Conventions

- **Hypotheses first.** Write what would support and what would refute each hypothesis before running the
  heuristics, and update the `Status` column as evidence comes in (including `refuted` and `not testable`).
- **Paths in reports.** Inside a case, `out/…` and `scripts/…` are relative to the case folder; shared tables are
  cited as `core/out/…` and raw downloads as `data/…` (both relative to the repo root).
- **Shared vs. case code.** Anything that only makes sense for one question (keyword regexes, name classes,
  coding rules) stays in that case's `case_lib.py`. Promote a helper to `core/village_lib.py` only when a second case
  needs it, and keep it question-neutral.
- **Do not write to `core/out/` from a case.** If a case needs a new dataset-level table, add a core script.
- **Evidence.** Every finding cites `event_index` + UTC timestamp + deep link, or a memory snapshot id; heuristics
  with more than 500 hits are sampled (100) and say so; regex counts are checked against a base rate and read.
