# Conformity: how often does any agent dissent in a group decision?

| | |
|---|---|
| Slug | `conformity` |
| Status | idea <!-- idea → exploring → verified → written-up → archived --> |
| Started | 2026-11-15 |
| Last updated | 2026-11-15 |
| Report | `FINDINGS.md` (one page) |

Sections "Question" to "What counts as a null" were written and committed **before** any decision was coded or
any rate computed (see the git history of this file). Only structural facts were looked at first: the list of
village goals, the room names (a `voted-out` room exists, 253 messages), and how many agent chat messages use
vote wording per goal period (350 with first-person vote phrasing, 4,358 with any vote / elect / nominate /
consensus word; the densest periods are the leader election of 2026-01, the challenge week of 2026-02-23, the
saboteur goal of 2026-03-05 and "Finetune your leader!" of 2026-05-26).

Prior knowledge that could bias coding: AI Digest's saboteur post reports a unanimous vote against an innocent
agent, and readers noticed that agents almost never vote against the group. From the authority-recognition
case: DeepSeek-V3.2 was elected leader in January 2026 and its directives had no measurable pull.

## Question

When the Village agents make an explicit group decision, how often does any agent dissent, and what happens to
the dissenter's position afterwards? Nobody has counted it. The count only means something next to a baseline:
the unanimity one would see if the same agents chose independently at their own observed dissent rates.

## Unit of analysis

- **Decision** = one question put to the group in chat on which **at least 3 distinct agents state an explicit
  position**, with options that can be listed and an identifiable result. Three kinds: `vote` (an election or
  poll using vote wording), `accusation` (a vote to remove or accuse a named agent), `proposal` (a named
  proposal that others explicitly accept or reject). Two rounds on the same question (a re-vote, a run-off) are
  two decisions, linked by a `round_of` field. Organizer-imposed outcomes are not decisions.
- **Position** = (decision, agent): the option the agent states. **Initial position** = the agent's first stated
  option; **final position** = its last stated option before the decision closes (the result is announced or
  acted on, or the village day ends). Each carries the `event_index` of the message. Coded only from explicit
  statements ("I vote X", "my vote: X", "I support / oppose the proposal", "+1 to X", "I accuse X"); silence is
  never a position. An explicit abstention is coded `abstain` and counted separately.
- **Present** = agents with at least one chat message in the decision's room between 2 hours before its first
  position and its close.
- **Winner** = the option that is declared or acted on; if none is declared, the option with the most final
  positions.
- All rates are **counts of decisions** or **counts of positions (agent level)**, never message counts.

## Measures (fixed in advance)

| Measure | Definition | Level |
|---|---|---|
| Unanimity (primary) | decisions in which every stated final position is the same option / decisions with ≥ 3 stated positions | decision |
| Never-contested | decisions in which every *initial* position was already the same option / same denominator | decision |
| Dissent rate | initial positions that differ from the winner / all initial positions (abstentions excluded) | position |
| First position won | decisions whose first stated position (lowest `event_index`) is the winner / all decisions | decision |
| Dissent abandoned same day | dissenting agents who later state the winning option or explicitly withdraw or defer, before the village day of their dissent ends / all initial dissents | position |
| Dissent abandoned ever | same, with no time limit | position |

Flags kept per position: `self` (voting for oneself, or the accused defending itself) so that self-interested
dissent can be shown separately; `model family`; year.

## Baselines (fixed in advance)

1. **Independent agents at their own base rates (for unanimity).** For each agent *a*, `d_a` = its initial
   dissents / its initial positions over all coded decisions (agents with fewer than 5 positions get their
   family's pooled rate). If agents dissented independently, decision *j* would be never-contested with
   probability Π over its voters of (1 − `d_a`). Expected rate = the mean of that product over decisions; a 95%
   interval comes from 10,000 simulated draws. Observed above expected means dissent is clustered in a few
   contested decisions; observed equal to expected means dissent is rare but independent. The baseline holds each
   agent's overall dissent rate fixed, so it tests clustering, not whether that rate is "too low".
2. **First mover at chance (for first-position-won).** If order did not matter, the first speaker would hold the
   winning option as often as any voter does: expected share = mean over decisions of (final positions for the
   winner / stated positions). Observed − expected is the first-mover excess.
3. **Reference point for the dissent rate.** Humans in public sequential votes also conform; no human baseline is
   computed here. The pitch-relevant comparison is internal: decisions where positions were stated blind (secret
   ballot, simultaneous form) versus in open sequence, if at least 5 blind decisions exist.

## How decisions are found (fixed in advance)

1. Candidate messages: agent chat matching vote wording (`out/vote_messages.csv`). Clustered by room and time
   (gap ≤ 3 hours) into candidate windows; a window needs ≥ 3 distinct agents with matching messages.
2. Start with the saboteur goal (2026-03-05 to 03-16) and the leader weeks (2026-01-05 to 01-12, 2026-05-26 to
   06-08), then every other window in the dataset.
3. Each window's full room transcript is read and coded into decisions and positions against the definitions
   above. Windows may be coded by a sub-agent on a smaller model; such rows are **computed, unverified** until
   checked against the raw rows. Every row keeps its `event_index`.
4. **False-match rate of the wording search**: 100 random matches (`random_state=0`) are read and coded as a real
   position / talk about voting / other sense ("vote of thanks", "elect to", a game mechanic).
5. **Misses**: a random 20 agent messages with loose vote wording that fall outside all windows are read to see
   whether a decision was missed. Decisions made without vote wording (quiet consensus, "sounds good") are out of
   scope and that is stated as a limit: they would raise unanimity, not lower it.

## What counts as a null

| id | Hypothesis | Supports if… | Null / refuted if… | Status | Evidence |
|---|---|---|---|---|---|
| H0 | Explicit group decisions can be counted reliably | ≥ 30 decisions with ≥ 3 positions, and ≥ 80% of 10 re-read decisions agree with the first coding on winner and dissent count | fewer than 30, or agreement < 80%: the topic is not countable in a short project | open | — |
| H1 | Most decisions are unanimous | unanimity ≥ 70% of decisions | < 70%: agents do dissent in most decisions; the reader observation is wrong | open | — |
| H2 | Unanimity exceeds what independent agents would produce | never-contested rate above the 95% simulated interval of baseline 1 and ≥ 15 points above its mean | inside the interval or < 15 points: unanimity is what rare, independent dissent would give | open | — |
| H3 | The first stated position wins more than chance | first-position-won ≥ 15 points above baseline 2, exact binomial p ≤ 0.05 | otherwise null | open | — |
| H4 | Dissent does not last | ≥ 50% of initial dissents abandoned the same day | < 50%: dissenters mostly hold | open | — |
| H5 | Family or year differences | only tested if every cell has ≥ 20 positions; a gap ≥ 20 points with p ≤ 0.05 | not tested or below threshold | open | — |

## Data

- Shared tables (`core/out/`): `chat.parquet` (every message with room, speaker, model, active goal),
  `agents_roster.csv`, `events_slim.parquet`.
- Raw (`data/`): `village_goals.jsonl.gz`, `CHANGELOG.md`.
- Case outputs (`out/`): `vote_messages.csv`, `windows.csv`, `windows/<id>.txt` (transcripts given to coders,
  git-ignored if large), `decisions.csv`, `positions.csv`.

## Known limits (before looking)

- Votes in open chat are sequential and public: each agent sees earlier votes. Agreement can be conformity,
  shared information, or shared training. The count cannot tell these apart.
- Rooms (from 2026-02-25) changed who sees what; the number of agents present grew from 4 to more than 20;
  goals asking for a vote (election, saboteur) were set by organizers. Not causal.
- Votes held outside chat (a Google Form, a GitHub issue) are only visible through what agents report in chat.
- Agents can state a position without vote wording; those are missed unless they fall inside a coded window.

## Findings

See `FINDINGS.md`.
