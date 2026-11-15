# Memetic spread: how do ideas travel between agents?

Data-scout case `memetic-spread`. Question, definitions and hypotheses: [HYPOTHESIS.md](HYPOTHESIS.md).
Result (one page): [FINDINGS.md](FINDINGS.md). Hand-check log: [VERIFICATION.md](VERIFICATION.md).
Decision brief for the analyst (Spanish): [INFORME.md](INFORME.md).

Hand-curated inputs (tracked, edited by hand): `memes.csv` (meme registry: regex, origin type, kind, truth value,
status and the reason for every change), `friction_terms.csv` (the "friction lexicon" of Nov–Dec 2025).

## Run

Needs the shared tables first (repo README, "Core pipeline", including `--big` and `04_memories_shard.py`). Then,
from the repo root, in this order (`P=./venv/bin/python3 -I data-scouts/memetic-spread/scripts`):

```
$P/01_memory_lines.py           # out/memory_lines.parquet (16.3M distinct memory lines; ~3 min), out/memory_lines_stats.csv
$P/02_candidate_terms.py        # out/candidate_terms.csv (34k novel chat terms), out/candidate_terms_top.csv
$P/03_candidate_corrections.py  # out/candidate_corrections_organizer.csv, out/candidate_corrections_agent.csv (reading lists)
$P/04_trace_memes.py            # out/meme_origins.csv, meme_chat_hits.csv, meme_action_hits.csv, meme_memory_lines.csv,
                                #   meme_memory_daily.csv, meme_memory_agent.csv   (~4 min)
$P/05_measures.py               # out/meme_agent.csv (pairs), meme_summary.csv, meme_first_lines.csv
$P/06_friction_terms.py         # out/fx_terms.csv (36 lexicon terms + 60 control terms)
$P/04_trace_memes.py --memes data-scouts/memetic-spread/out/fx_terms.csv --tag fx
$P/05_measures.py    --memes data-scouts/memetic-spread/out/fx_terms.csv --tag fx
$P/07_correction_survival.py    # out/correction_terms.csv, correction_pairs.csv, correction_summary.csv,
                                #   correction_by_agent.csv, correction_lines.csv
$P/08_background_terms.py       # out/bg_terms.csv (240 terms drawn with random_state=0)
$P/04_trace_memes.py --memes data-scouts/memetic-spread/out/bg_terms.csv --tag bg     # ~8 min
$P/05_measures.py    --memes data-scouts/memetic-spread/out/bg_terms.csv --tag bg
$P/09_contrasts.py              # out/contrasts.csv, contrasts_family.csv, background_rate.csv, background_terms.csv,
                                #   background_by_agent.csv, background_by_group.csv
$P/10_verify_instances.py       # out/verified_instances.md (raw rows behind FINDINGS.md, re-read from the shards)
```

Steps 4, 5, 7 and 9 are deterministic (fixed seeds, total sort orders). Nothing here writes to `core/out/`.

## Outputs

| File | Written by | What |
|---|---|---|
| `out/memory_lines.parquet` (ignored) | 01 | every distinct memory line per agent: first / last snapshot, snapshot and date counts |
| `out/candidate_terms*.csv` | 02 | novel chat terms with origin and chat spread (full file ignored, top list tracked) |
| `out/candidate_corrections_*.csv` | 03 | organizer corrections / rules and agent retractions with context (agent file ignored) |
| `out/<tag>_origins.csv` | 04 | first chat message matching each regex |
| `out/<tag>_memory_agent.csv` | 04 | meme × agent: matching snapshots before the origin (placebo), first / last after it |
| `out/<tag>_memory_daily.csv`, `<tag>_memory_lines.csv` | 04 | per-day presence; every matching line (lines files ignored) |
| `out/<tag>_agent.csv`, `<tag>_summary.csv`, `<tag>_first_lines.csv` | 05 | pair-level measures, per-meme numerators and denominators, first matching line per adopter |
| `out/correction_*.csv` | 07 | holders at the correction of 2025-12-09 and their survival, lexicon vs control, named vs bystander |
| `out/background_*.csv` | 09 | the base rate (headline): overall, by origin year and quarter, by chat usage, by receiving agent, family and join cohort |
| `out/contrasts*.csv` | 09 | H2–H5 with permutation p-values under every alternative definition |
| `out/verified_instances.md` | 10 | raw rows for the hand check |

`<tag>` is `meme` (hand-picked registry), `fx` (friction lexicon + controls) or `bg` (random background terms).
