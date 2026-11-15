# {{title}}

| | |
|---|---|
| Slug | `{{slug}}` |
| Status | idea <!-- idea → exploring → verified → written-up → archived --> |
| Started | {{date}} |
| Last updated | {{date}} |
| Report | `out/REPORT.md` (when it exists) |

## Question

One or two sentences. What do we want to learn about the Village agents, and why does it matter?

## Hypotheses

Each hypothesis must say what evidence would support it and what would refute it, before looking.

| id | Hypothesis | Supports if… | Refutes if… | Status | Evidence |
|---|---|---|---|---|---|
| H1 | … | … | … | open | — |

Status values: `open`, `supported`, `refuted`, `mixed`, `not testable with this data`.

## Data

- Raw tables (`data/`): …
- Shared tables (`core/out/`): `chat.parquet`, `events_slim.parquet`, `agents_roster.csv`, …
- Case caches (`out/`, git-ignored if large): …

## Method and known limits

- Operational definitions (regexes, windows, joins) and where they live in `scripts/`.
- Confounds (era, roster, scaffolding changes in `data/CHANGELOG.md`), base-rate / placebo checks.

## Findings

Every claim cites raw rows: `event_index` + UTC timestamp + deep link (`v.deep_link(ts)`), or a memory snapshot id.

## Open threads
