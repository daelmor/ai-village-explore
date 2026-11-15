# Memetic spread: how do ideas travel between agents?

| | |
|---|---|
| Slug | `memetic-spread` |
| Status | exploring <!-- idea → exploring → verified → written-up → archived --> |
| Started | 2026-11-15 |
| Last updated | 2026-11-15 |
| Report | `FINDINGS.md` (one page) |

Sections "Question" to "Fallback" were written and committed **before** any spread outcome was computed
(see the git history of this file). Only structural facts were looked at first: snapshot frequency per
month (20–116 snapshots per agent-day in every month, so memory latency is resolvable to well under a day in
all eras), the roster, and the column list of the shared tables.

Prior knowledge that could bias the meme choice, from the authority-recognition case: the no-cold-email rule
(ei 146638) was in 9/10 memories the same day, 10/10 three days later, 6/10 after a week; fake-admin lines left
memory within two days; Adam corrected a false "nudge-exempt" belief (ei 356859). Nothing else about spread
was known when this was written.

## Question

How does an idea travel between agents in the Village? Take a set of traceable "memes" (a factual claim, a
rule, a coined phrase, a working practice, a false belief), and follow each from its first utterance in chat
into other agents' long-term memory and into what they say they will do. Does how far and how fast a meme
travels depend on whether it is true, on who started it (agent or human), on the model family of the receiver
or sender, or on the era (2025 vs 2026)?

## Unit of analysis

- **Meme** = one row of `memes.csv`: a case-insensitive regex with distinctive wording, plus an *origin*: the
  `event_index` of the earliest chat message matching it (found by script, not by memory). Each meme is coded
  by hand, from the raw rows and before spread is computed, for `origin_type` (agent / organizer / viewer),
  `kind` (claim / rule / coinage / practice) and `truth` (true / false / n-a). "false" requires a row in which
  an organizer or the agents themselves contradict or retract it; "true" requires a confirming row or, for a
  rule, that an organizer actually issued it. Coinages and practices have no truth value (n-a).
- **Pair** = (meme, agent). All rates are **agent-level counts of pairs**, never message or snapshot counts,
  unless a number is explicitly labelled otherwise.
- **Exposed cohort** of a meme (the denominator) = every agent other than the originator with at least one
  memory snapshot in the 7 days after the origin (`[t0, t0+7d]`).

## Measures (fixed in advance)

| Measure | Definition | Level |
|---|---|---|
| Memory adoption `A7` (primary) | exposed agent has ≥1 memory snapshot in `(t0, t0+7d]` with a line matching the regex | pairs: adopters / exposed |
| Latency | hours from `t0` to the agent's first matching snapshot, among `A7` adopters | per pair, median per meme |
| Retention | days between the agent's first and last matching snapshot; share of adopters with a matching snapshot ≥7 d and ≥30 d after their first one, among adopters who still have any snapshot at that horizon | pairs |
| Chat uptake `C7` | exposed agent posts ≥1 chat message matching the regex in `(t0, t0+7d]` | pairs |
| Stated action `S7` | regex matches the agent's own `START_USING_COMPUTER.sessionGoal` or `CONSOLIDATE.nextSessionGoal` in `(t0, t0+7d]`. This is the agent's stated intention, not ground truth; behaviour claims beyond it must be read by hand | pairs |
| Inheritance | agents whose first snapshot is later than `t0+7d` and who have ≥1 matching snapshot / all such late joiners | pairs |

Alternative definitions that every headline number must also be reported under:
`A1` (24 h window), `A30` (30 d window, cohort = snapshot in `[t0, t0+30d]`), `A7-durable` (matching snapshots on
≥2 distinct UTC dates within 30 d), and `A7-room` (cohort restricted to agents that posted in the origin's room
within ±7 d; rooms exist from 2026-02-25, before that it equals `A7`).

## Placebo and base-rate checks (fixed in advance)

1. **Pre-origin placebo.** The same regex over the same agents' snapshots and chat in the 30 days before `t0`.
   A meme is *traceable* only if no exposed agent has a matching snapshot in that window. If the placebo is not
   zero, either the origin is wrong (move it) or the wording is not distinctive (tighten or drop the meme); every
   such change is logged in `memes.csv` (`notes`).
2. **Precision.** For each meme, up to 10 matching memory lines (one per agent first) are read by hand; a meme
   whose matches are mostly a different sense of the words is dropped. Precision is reported.
3. **Label permutation.** For each group comparison, the difference in mean per-meme rate is compared with the
   distribution under 10,000 random relabelings of the memes (two-sided).
4. **Background rate** (if time allows): the same `A7` computed for a mechanically drawn set of novel terms
   coined in chat that were *not* hand-picked, to show what an unselected term does.

## Hypotheses

| id | Hypothesis | Supports if… | Refutes if… | Status | Evidence |
|---|---|---|---|---|---|
| H1 | A traceable meme reaches the memory of most agents present. | median per-meme `A7` ≥ 50%, pre-origin placebo 0 | median per-meme `A7` < 20% | open | — |
| H2 | False claims and true claims/rules differ in spread. | abs. difference in mean per-meme `A7` ≥ 25 points, same sign under `A1`, `A30`, `A7-durable`, permutation p ≤ 0.10 | difference < 25 points, or sign flips under an alternative definition, or p > 0.10 | open | — |
| H3 | Agent-originated and human-originated memes differ in spread. | same criteria as H2 | same as H2 | open | — |
| H4 | One model family adopts (or originates) memes more than the others. | a family's pair-level `A7` differs from the rest by ≥ 20 points across memes it shared a cohort with, meme-stratified permutation p ≤ 0.10, same sign under `A30` | otherwise | open | — |
| H5 | Memes that originate in 2026 spread differently from those of 2025. | same criteria as H2, by origin year | same as H2 | open | — |
| H6 | Memes outlive their origin: agents that joined later carry them. | ≥ half of the memes have ≥1 late-joiner carrier, hand-verified | fewer than 2 memes have one | open | — |

**What counts as a null.** (a) Fewer than 8 traceable memes → switch to the fallback. (b) No comparison H2–H5
meets its criteria: then the report says "no defensible contrast" and only descriptive numbers (H1, H6,
latency, retention) are offered, each with its own definition check. (c) Looking at four comparisons and
reporting the best one is a forking-paths design, so all four are reported, including the ones that fail.

Expected sample: 10–15 memes, so every group has 3–8 memes. A contrast at this size is a lead for a 10–20 hour
project, not a result; the write-up must say so.

## Confounds named in advance (no causal claims)

- **Selection.** Memes are chosen for traceability by reading; memes that never spread are hard to notice, so
  the sample over-represents spreaders. The candidate search therefore also draws from origin-side lists
  (organizer rules, organizer corrections of false beliefs) that do not condition on spread.
- **Era.** Roster grew from 4–10 agents (2025) to 13–42 (2026); public chat with viewers existed only
  Apr–Aug 2025; rooms split the audience from 2026-02-25; perma-computer-use from 2026-03-24; memory
  consolidation changed 2026-03-11 and again 2026-09/10; memory size grew from ~15k to ~49k characters.
- **Family × era.** Model families are present in different periods; a family comparison is only made within
  memes (agents exposed to the same meme).
- **Channel.** A match in memory does not prove chat was the route: agents also share documents, repos and
  email. The pre-origin placebo rules out an earlier source, not a parallel one.
- **Regex.** Matching is literal; a paraphrased adoption is missed (under-count), a quoted disagreement is
  counted (over-count). The precision read addresses the second, not the first.

## Standards for any headline number

Numerator, denominator and level stated; pre-origin placebo and precision reported; value under at least one
alternative definition; at least five instances verified by hand against raw rows and saved with
`event_index` / snapshot id / deep link in `out/verified_instances.md`; each claim marked *verified by hand*,
*computed, unverified* or *inferred*.

## Fallback (definition fixed in advance)

If fewer than 8 traceable memes are found: using the nudger pairs of the authority case
(`data-scouts/authority-recognition/out/nudger_stats.csv`, 1,997 (nudge, agent) pairs), **recovery time** =
minutes from the nudge to the addressee's next `START_USING_COMPUTER` event, censored at 24 h; reported as
the median and the share recovered within 15 min, by the agent's model release order (join date in
`core/out/agents_roster.csv`). One definition, no alternatives chosen after the fact.

## Data

- Shared tables (`core/out/`): `chat.parquet`, `events_slim.parquet`, `agents_roster.csv`,
  `memories/<agent_id>.parquet`, `memories_index.parquet`.
- Case caches (`out/`, git-ignored): `memory_lines.parquet` (every distinct memory line per agent with first /
  last snapshot and snapshot count; generalises `authority-recognition/scripts/09_memory_mentions.py`, which did
  this for 14 keywords).

## Findings

See `FINDINGS.md`. Status column above is updated after the runs.

## Open threads
