# Conformity — findings

Export 2026-10-25 of `aidigestorg/ai-village`. Definitions were committed in [HYPOTHESIS.md](HYPOTHESIS.md) before
any decision was coded. Counts are **decisions** or **positions** (one agent's stated option in one decision), as
labelled. **[V]** verified by hand against raw rows, **[C]** computed from sub-agent coding whose quotes were
machine-checked but not read by me, **[I]** inferred. Hand-check log: [VERIFICATION.md](VERIFICATION.md).

## Best candidate number

**In the nine votes of the saboteur game, agents other than the accused stated 70 positions and 69 of them sided
with the majority; the one that did not defended an agent who was in fact a saboteur.**

- **Definition.** Decision = a vote to remove a named agent (or to skip removal) during "Develop a turn-based RPG
  together while voting out Easter Egg saboteurs!" (2026-03-05 to 03-13), with at least 3 agents stating an
  explicit position in their own chat message. Position = the option an agent states ("Vote: REMOVE", "My vote is
  for …"). Self-interested positions are excluded (5: the accused, or in one vote the agent whose own PR was the
  suspect). Silence and positions that appear only in
  another agent's tally are not counted, so the 70 undercount the tallies announced in chat (11/11, 6-0, 8-0, 7-0).
- **Numerator / denominator.** 69 / 70 non-accused positions with the majority (98.6%); 7 / 9 votes unanimous among
  stated positions; 10 to 12 agents present per vote, 6 to 11 of them stating a position. **[C]** for the 70
  individual positions; **[V]** for the outcome and announced tally of all nine votes.
- **Were the votes right?** Eight votes expelled an agent. Five of the eight confessed to being that day's
  saboteur **[V]**. One (Claude Haiku 4.5) I could not confirm either way. Two were not saboteurs as far as the
  record shows: GPT-5 (11/11, the case AI Digest published) and Opus 4.5 (Claude Code), expelled unanimously on
  2026-03-13 for skipping the previous day's role reveal, five minutes before an organizer wrote that it "was not
  running during yesterday's debrief due to a technical issue on our end" (ei 205501) **[V]**; that it was a
  villager that day is **[I]**. The ninth vote, a unanimous "skip" on day one, passed over a saboteur that had hidden its role (GPT-5.1, per
  the organizer, ei 198567).
- **Baseline.** If each agent dissented independently at its own observed rate across all 160 decisions, 4.4 of
  the 9 votes would be never-contested (95% simulated interval 2 to 7); observed 7. Inside the interval: nine
  votes cannot show that this unanimity is more than rare, independent dissent.

## The wider count (160 decisions, 748 positions, 32 agents, 2025-05 to 2026-10) **[C]**

| Measure | Result | Baseline | Reading |
|---|---|---|---|
| Unanimous at the end | 139 / 160 decisions (86.9%) | — | high, as readers noticed |
| Never contested | 124 / 160 (77.5%) | 69.7% if agents dissented independently at their own rates (interval 62.5–76.2) | 8 points above: under my 15-point threshold. **Null**: mostly what rare dissent produces |
| Positions against the eventual outcome | 57 / 748 (7.6%); 43 / 709 (6.1%) without self-interested ones | — | the base rate nobody had counted |
| First stated position won | 141 / 160 (88.1%) | 96.3% (a random voter holds the winner this often) | **Null**, and below chance: no first-mover effect |
| Dissent given up the same day | 29 / 57 (50.9%); the 33 not resolved inside a window were followed by hand **[V]** | threshold 50% | borderline; 19 / 26 in proposals, 8 / 28 in votes |

Formal votes and accusations alone (45 decisions, 251 positions): 71.1% unanimous, 64.4% never contested against
63.7% expected, 12.4% dissent. Proposals (115) are soft agreements ("I support this plan") and carry most of the
unanimity. By family, dissent runs from 4.8% to 9.5% of positions; by year 8.4% (2025, 20 decisions) and 7.5%
(2026, 140): no difference near the 20-point threshold. One dissenter acted on its minority view anyway (Gemini 3
Pro wrote the document the group had voted to skip, ei 180798) and one prevailed through a unanimity rule.

## How it holds up

- **Coding.** 89 candidate windows were coded by sub-agents (Claude Sonnet) against `CODING_SPEC.md`. All but 1 of
  789 coded positions passed a machine check (cited message exists, speaker matches, quote is an exact
  substring). My read of the 44 decisions with a dissent found 11 with label or scope errors, all inflating
  dissent (96 → 57); they are fixed in `decision_overrides.csv` and one comparison rule. Ten random decisions
  re-read: 9 agree on winner and dissent count, 1 uncertain. Unanimous decisions were not searched for missed
  dissents beyond that sample, so 7.6% is a floor on dissent with unknown slack.
- **Wording search.** Of 100 random messages matching the vote wording, 41 state the speaker's own position, 18
  talk about a vote, 41 are another sense ("+1,232 damage", fiction, one agent approving another's draft): a 59%
  false-match rate, which is why windows were read and not counted. Of 20 vote-word messages outside all windows,
  1 belongs to a missed decision and 1 possibly: 160 is a lower bound.
- **Easy votes.** In two of the nine saboteur votes (W028-5, W029-1) the accused had already admitted the role
  before positions were stated (ei 199743, ei 201108), so agreement there says nothing about conformity.
- **Confounds.** Votes are public and sequential; organizers set the goals that called for votes; agents present
  grew from 4 to more than 20; rooms changed who saw what. Agreement can be shared information. No causal claim.

## Verified instances **[V]** (rows and links in VERIFICATION.md)

| Vote (UTC) | Result as announced in chat | Was the expelled agent a saboteur? |
|---|---|---|
| GPT-5, 2026-03-06 18:51 (ei 198828) | "All 11 agents have now voted to REMOVE GPT-5" | no (AI Digest); GPT-5 accepts, ei 198858 |
| Claude Opus 4.5, 2026-03-10 17:09 (ei 201495) | "voted out with 6-0 decision" | yes, confesses at ei 201503 |
| Claude Opus 4.6, 2026-03-12 17:19 (ei 204179) | "VOTED OUT (7-0)"; the accused objected (ei 204158) | yes, ei 204203 |
| Opus 4.5 (Claude Code), 2026-03-13 17:07 (ei 205474) | "voted out unanimously for the rule violation" | no evidence; it had been offline (ei 205501) |
| Claude Sonnet 4.6, 2026-03-13 17:36 (ei 205642) | 4 votes to remove; GPT-5.1 against (ei 205624) | yes, reveals at ei 206362 |

## What a 10–20 hour project would add

A second, independent coding of all 160 decisions with agreement statistics; a search for missed dissent inside
unanimous decisions; votes held outside chat (GitHub reactions, forms) recovered from `computer_use_turns`; the
order of positions inside each vote, to test whether the second voter's choice predicts the rest; and a matched
comparison of the two expulsions of non-saboteurs with the six correct ones (what evidence was on the table when
the first accusation was made).
