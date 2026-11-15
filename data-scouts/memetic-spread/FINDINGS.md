# Memetic spread — findings

Export 2026-10-25 of `aidigestorg/ai-village`. Definitions were committed in [HYPOTHESIS.md](HYPOTHESIS.md) before
outcomes were computed. Counts are **(term, agent) pairs** unless stated. **[V]** verified by hand against raw rows,
**[C]** computed, not read, **[I]** inferred. Hand-check log: [VERIFICATION.md](VERIFICATION.md).

## Best candidate number

**When one Village agent coins a new term in chat, 30% of the other agents have it in their long-term memory within
24 hours, typically 16 minutes later, and more than half of those copies are gone again within a day.**

- **Definition.** 240 agent-coined terms (Title Case or hyphenated, ≥3 chat messages) drawn at random
  (`random_state=0`) from 27,746; 130 kept because no other agent had the wording in memory before its first chat
  use. Pair = kept term × every other agent with a memory snapshot in the next 7 days. "In memory" = ≥1 snapshot
  containing the term.
- **Numerator / denominator.** 576 / 1,895 = **30.4%** within 24 h (95% CI 25.6–35.4, bootstrap over terms). Delay
  among the 641 pairs adopting within 7 days: median **16.2 min** (quartiles 6.6–59.4). Of those 641, 56.9% last
  match less than a day after their first match; 18.4% still match ≥30 days later. **[C]**
- **Placebo / base rate.** This number is the base rate. The pre-origin placebo (nobody else has the wording before
  its origin) removed 110 of 240 random terms and 7 of 22 hand-picked memes, and exposed four regex or origin errors.
  The 15 hand-picked memes that pass it reach 106 / 150 = 70.7%: 2.3 times the base rate, which is what picking
  memes by reading does. No claim rests on that gap.
- **Alternative definitions.** 7-day window 33.8%; only agents active in the same room 37.3% (n = 1,618); 2025
  terms 33.9% (81 / 239) vs 2026 29.9% (495 / 1,656); by quarter 26–48%. Requiring the term on ≥2 different days
  **halves it to 16.1%** (306 / 1,895). "Noted within a day" is stable near a third; "kept" is half of that. **[C]**
- **What it is not.** A match is a note, usually about what another agent said or made, not a belief. Only 5.3% of
  pairs (100 / 1,895) carry the term into the agent's own next session goal **[C]**. Chat is not proven to be the route.

Five instances read in the raw snapshots **[V]** (rows: `out/verified_instances.md`); each receiver had 0 matching
snapshots among its 2,093–16,898 earlier ones:

| Term (origin `event_index`, UTC, speaker) | Receiver, first snapshot with the term | Delay |
|---|---|---|
| `shared-gitlab-org` (273004, 2026-07-02 20:11:03, DeepSeek-V3.2) | GPT-5.4, `31ca7a6a-7946-42a7-b1ab-e188d000169d` | 27.9 min |
| `star-song` (511515, 2026-10-13 23:16:35, Claude Opus 4.8) | Claude Haiku 4.5, `693f5b48-1253-4fcf-b811-54a86b3e5e46` | 15.2 min |
| `parallel track delegation` (275476, 2026-07-03 22:51:05, DeepSeek-V3.2) | Claude Opus 4.5, `c443b640-ffe6-4cd4-bf21-395786fe7280` | 6.9 min |
| `anomaly song` (478250, 2026-10-06 21:25:45, GPT-5) | Claude Sonnet 4.6, `9b99a593-a597-4dce-9e96-866ad0ba3402` | 19.3 h |
| `the joining cut` (389141, 2026-08-31 20:09:34, Claude Opus 4.8) | DeepSeek-V4-Pro, `e5ced6c4-8bf6-447a-8873-5a76b92629e9` | 11.7 min |

Two non-adopting pairs were read too (0 of 121 and 0 of 230 snapshots). Instance 1 is a GitLab runner tag the
receiver may have read in GitLab itself: a correct match, an unproven route.

## Two runner-up numbers

1. **An organizer's correction did not speed up forgetting.** On 2025-12-09 adam told all agents that the
   "environment hazards" two Gemini agents kept naming were almost always operator error (ei 137163). Of 132 pairs
   holding one of 22 such terms in the 48 h before, 48 (36%) still had it a day later and 24 (18%) at some point ≥30
   days later; control terms from the same weeks: 11 / 32 (34%) and 5 / 32 (16%) **[C]**. Read by hand **[V]**: in
   days 30–37 the hazards are in 7 pairs, all of them Claude Sonnet 4.5 listing them as "Core Patterns" (snapshots
   `294fccb7…` to `e46da87a…`), while the one claim adam confirmed (separate computers, the "Archipelago Principle")
   is in 6 of 8 bystander pairs, as a working rule in four agents. One episode, two confirmed terms: a lead.
2. **A hallucination became folklore, with its correction attached.** o3's non-existent "93-contact mailing list"
   (ei 34444, 2025-06-10; debunked ei 34833, 34939) is in the memory of 10 agents that joined after it, 254–456
   days later; 9 record it as a hallucination, 1 as a "mislaid" list **[V]** (the regex found 11; one false
   positive). It arrived in two bursts (Feb and Jun 2026), at least partly through `search_history` **[I]**.

## Pre-registered comparisons: all null (`out/contrasts.csv`)

7-day adoption, per-meme means: false 80.8% vs true 71.6% (6 vs 4 memes, permutation p = 0.62); agent- vs
human-originated 81.8% vs 74.4% (p = 0.59); 2026 vs 2025 74.0% vs 81.3% (p = 0.63). Coiners vs bystanders after the
correction: 16-point gap against a 25-point threshold, and control terms show 20. Nearest miss: Claude agents 84.1%
(53 / 63) vs co-exposed others 69.0% (60 / 87), p = 0.022, under the 20-point threshold; in the random sample single
agents range from 0% to 63%, so it is an agent effect more than a family effect **[C]**.

**Confounds.** 87% of the pairs are from 2026; co-present agents grew from a median of 3 to 24; memory scaffolding
changed (2026-03-11, 03-24, 2026-09/10); rooms and per-agent goals arrived in 2026; matching is literal. Not causal.

## What a 10–20 hour project would add

Stance coding of matched lines (believes / notes / records a correction) with an LLM judge calibrated on the rows
read here; route attribution (chat vs the 11,720 `search_history` events vs documents in `computer_use_turns`); a
survival analysis over all ~27,000 coined terms of why the 18% that last a month last; and the correction event
study repeated over the 144 organizer corrections in `out/candidate_corrections_organizer.csv`.
