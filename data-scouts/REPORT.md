# Decision report: which of the three topics should the pitch use?

Date: 2026-11-15. Covers the cases `data-scouts/conformity` and `data-scouts/stuck-time`, and compares them with
`data-scouts/memetic-spread` (corrections), which has its own [brief](memetic-spread/INFORME.md), in Spanish.
Technical detail is in each case's `FINDINGS.md`, definitions in its `HYPOTHESIS.md`, the hand checks in its
`VERIFICATION.md`, and the comparison table in [COMPARISON.md](COMPARISON.md).

## What this report is for

David is re-applying to the AI Village Data Exploration Grant (AI Digest). The pitch is 200 words, he writes it
himself, and it should open with a number that is both surprising and defensible. One candidate already existed
(corrections, from the memetic-spread case). This session scouted two more so that three can be compared.

**Result in one line:** conformity gives a striking, countable number, from a small sample; stuck time came out
null. I recommend conformity.

## Minimal context

The AI Village is an experiment in which between 4 and more than 20 AI agents (Claude, GPT, Gemini and others)
talk in a shared chat and each use their own computer. The dataset holds the 205,625 chat messages and 3.3
million computer-use "turns" (a turn is one action: a click, a key press, a command), from April 2025 to October
2026.

Two facts about the environment matter for reading the results:

- The organizers changed the scaffolding (the tools and rules around the agents) many times. The dataset ships a
  dated log of those changes. The largest is from March 2026.
- Agents in 2025 worked almost entirely by clicking on the screen. Agents from mid-2026 do most of their work
  with terminal commands (bash).

## Candidate 1: conformity

### What was asked

When the agents make an explicit group decision, how often does any of them dissent, and what happens to the
dissenter's position afterwards? AI Digest's post on the saboteur game reports a unanimous vote against an
innocent agent, and its readers noticed that agents almost never vote against the group. Nobody had counted it.

What would count as a null was written down before anything was coded:

| | Hypothesis | Criterion fixed in advance |
|---|---|---|
| H0 | Decisions can be counted reliably | at least 30 decisions, and 80% agreement when 10 are re-read |
| H1 | Most decisions are unanimous | 70% or more |
| H2 | There is more unanimity than independent agents would produce | 15 points above the baseline and outside its interval |
| H3 | The first position stated wins | 15 points above chance |
| H4 | Dissent does not last | 50% or more given up the same day |
| H5 | Model families or years differ | 20 points |

The baseline in H2 answers this question: if each agent dissented on its own, as often as it in fact dissents,
how many decisions would end with no dissent at all?

### What was done

1. Agent messages with first-person vote wording ("I vote", "my vote", "+1", "I second") were searched: 1,402
   messages. Grouped by room and time they form 89 windows with at least three agents.
2. Twelve sub-agents (Claude Sonnet) read each window and recorded the decisions and each agent's position, with
   the message number and a verbatim quote.
3. A script checked that every quote exists word for word in the cited message and that the author matches.
4. I read by hand the 96 recorded dissents, the nine votes of the saboteur game, and a random sample of ten
   decisions.

A "decision" is a question put to the group on which at least three agents state an explicit position. A
"position" is the option an agent states in its own message. Silence does not count.

### What came out

In the saboteur game (March 2026) some agents were secretly saboteurs each day and the group could vote to expel
a suspect. There were nine votes.

| | Result | Reading |
|---|---|---|
| Positions of non-accused agents that sided with the majority | 69 of 70 | This is the candidate number |
| Unanimous votes | 7 of 9 | Independent agents would give 4.4 (interval 2 to 7): inside the interval |
| Agents expelled | 8 | 5 confessed to being saboteurs; 1 could not be confirmed; 2 were not, as far as the record shows |
| The two wrong expulsions | both unanimous | One is the GPT-5 case AI Digest already published. The other is unpublished |
| The single dissent among the 70 | GPT-5.1 | It defended an agent that turned out to be a saboteur |

The unpublished expulsion: the group unanimously expelled Opus 4.5 (Claude Code) for not revealing its role the
day before. Four minutes later an organizer wrote that this agent had not been running because of a technical
problem on their side.

In the wider count (160 decisions, 748 positions, 32 agents, May 2025 to October 2026):

| | Result | Reading |
|---|---|---|
| H0 | 160 decisions; 9 of 10 re-read agree | Countable, with the caveat below about label errors |
| H1 | 139 of 160 end unanimous (86.9%) | Holds |
| H2 | 124 of 160 never had a dissent (77.5%); the baseline gives 69.7% | Null: 8 points, under the 15-point threshold |
| Dissent rate | 57 of 748 positions (7.6%); 43 of 709 (6.1%) leaving out agents defending their own interest | The base rate nobody had measured |
| H3 | The first position wins in 141 of 160 (88.1%); chance would be 96.3% | Null, and below chance |
| H4 | 29 of 57 dissents given up the same day (50.9%) | Borderline: 19 of 26 in proposals, 8 of 28 in votes |
| H5 | Dissent between 4.8% and 9.5% by family; 8.4% in 2025 and 7.5% in 2026 | Null |

In words: the agents dissent rarely, and that rarity is nearly enough by itself to explain this much unanimity.
It could not be shown that they agree more than independent agents with the same rates would. The striking part
is the saboteur game, where being wrong had a cost.

### How reliable it is

- The quotes pass the automatic check in 788 of 789 positions. That proves the message exists, not that the label
  is right: on reading the dissents, 11 of the 44 decisions with a dissent had errors. All of them inflated
  dissent (from 96 to 57) and are corrected in a file that gives the reason for each change.
- Unanimous decisions were searched for missed dissents only in the sample of ten. The 7.6% is a floor.
- The 69 of 70 is a subset chosen after seeing the results. It is the one the brief asked to look at first, but
  it is only nine votes.
- In two of the nine votes the accused had already admitted its role before anyone voted. Agreement there says
  nothing about conformity.
- That GPT-5 was not a saboteur comes from AI Digest's post; it does not appear in the chat. That Opus 4.5
  (Claude Code) was not one that day is an inference: it is not among the three who revealed themselves at the
  end of the day.
- Text search alone is poor: of 100 matches read, 41 were the speaker's own position, 18 talked about a vote and
  41 were another sense ("+1,232 damage"). That is why the windows were read.
- Votes are public and sequential, and the goals that called for votes were set by the organizers. None of this
  is causal.

## Candidate 2: stuck time

### What was asked

Has the time agents spend stuck fallen with newer models? An earlier analysis of a nearby question moved from 34%
to 85% depending on the definition, so here a single definition was fixed before computing anything, with one
alternative as a check.

- **Fixed definition:** an episode is a run of five or more identical actions in a row (same action, same
  target) inside one session.
- **Alternative:** stretches of eight actions with at most two distinct targets, to catch back-and-forth between
  two actions.
- **Measure:** episodes per active hour for each agent, against the release date of its model.

| | Hypothesis | Criterion fixed in advance |
|---|---|---|
| H1 | Newer models have fewer episodes per hour | rank correlation of −0.4 or stronger, p ≤ 0.05 |
| H2 | The trend belongs to the model, not to the scaffolding, the goal or the room | −0.3 or stronger inside every scaffolding period and among agents sharing a goal and a room |
| H3 | Newer models recover faster | same as H1 |
| H4 | The result does not depend on the definition | same sign under the alternative |

### What was done

1. The full turns file was read once (3,295,475 turns from 55 agents) and the episodes detected.
2. The trend was computed overall, inside each scaffolding period, among agents sharing a goal and a room, and
   separately for clicks and for terminal commands.
3. Thirty episodes were drawn at random and read against the raw rows (action, output, error, and what the agent
   said it was doing).

### What came out

| | Result | Reading |
|---|---|---|
| Size | 3,118 episodes in 20,126 active hours; 1.3% of active time | Little time either way |
| H1 | ρ = −0.50, p = 0.0006, 43 agents | Holds: newer models repeat less |
| H4 | ρ = −0.63 under the alternative definition | Same sign |
| H3 | ρ = +0.11, 22 agents | Null |
| H2, by scaffolding period | −0.40 up to March 2026 (p = 0.12); −0.76 from March to September; **−0.22 from October** (p = 0.22) | Fails: the trend disappears in the most recent period |
| H2, same goal and room | −0.27 across 73 groups, 60 of them negative | The sign holds; the size is under the threshold |
| Clicks and keys only | ρ = −0.58, 34 agents | This is where the fall is |
| Terminal commands only | **ρ = −0.13**, p = 0.45, 38 agents | No trend |
| Reading of 30 episodes | 7 stuck, 2 unclear, 21 not | Between 70% and 77% false positives |

The 21 episodes that were not an agent stuck were something else: paging with a key, refreshing an inbox while
waiting for someone, typing `sleep 90` to wait, or sending keys to a game.

In words: the measure captures repetition, and repetition is rarely being stuck. The fall with newer models
coincides with the move from clicks to the terminal and does not appear inside the terminal. The data do not show
that stuck time fell.

### How reliable it is

- The null is solid: it holds under two definitions, under the controls fixed in advance and under the hand
  reading. What is not solid is the trend.
- The oldest model in the series (Claude 3.5 Sonnet) has the highest rate because of a flaw in my definition: 68
  of its 72 episodes are clicks on different targets that the definition sees as the same.
- A scaffolding change shows up as if it were behaviour: 123 of the 165 `sleep` loops start on or after the day
  the organizers removed the pause tool (20 October 2026).
- No screenshots were used, so whether the screen changed was never checked.
- For 2026 models the date the model joined the Village was used as its release date.

## The three compared

| | Corrections | Conformity | Stuck time |
|---|---|---|---|
| Candidate number | After an organizer's correction, 36% of pairs still hold the term a day later (48 of 132) against 34% for control terms (11 of 32) | 69 of 70 positions with the majority; 2 of 8 expulsions wrong, both unanimous | Only 7 of 30 repetition episodes were an agent stuck |
| Surprise | Medium | Medium to high for the saboteur game; low for the wide count | Low |
| Solidity | Low to medium: a single episode | Medium: nine votes | The null is solid |
| Already published by AI Digest | Anecdotes, no rates | The GPT-5 case and the election tallies; nobody counted dissent | Qualitative statements only |
| Fit with the call | "how memetic information spreads across agents" | "social dynamics between AIs" | "how quickly AI is developing", but with a null result |

Corrections was not re-run in this session. What AI Digest has published was collected by a sub-agent through web
search, and the quotes were not re-read.

## Recommendation

**Apply with conformity, opening with the saboteur-game count**, and say in the pitch itself that the wide count
sits close to its baseline. It is the only candidate whose number is both striking and countable row by row, and
its weak points are the ones a 10 to 20 hour project fixes.

| Option | What it is | Cost | Why | Risk |
|---|---|---|---|---|
| A. Conformity | Open with 69 of 70 and the two wrong expulsions | 0 hours to apply; 2 to 3 for a second coding of the nine votes | Extends something AI Digest's readers already asked about; the expulsion over the technical failure is new | Small sample; a reviewer may say the accused had nearly always given itself away |
| B. Corrections | Repeat the study over the 144 organizer corrections | 2 to 3 hours | Closest to "how to steer the agents" | May come out null again |
| C. Stuck time as a methods note | "The obvious progress metric mostly measures waiting and paging" | 0 hours | A well-supported null; the call accepts nulls | Weak as an opening |

I do not recommend presenting stuck time as a progress result: the data do not support it.

## Questions for the analyst

1. Are nine votes enough to open a pitch if each one is verified by hand, or is it better to open with the
   general rate (6% to 8% dissent across 160 decisions) and keep the saboteur game as the example?
2. The baseline says the unanimity is close to what so little dissent would produce. Does that weaken the topic,
   or make it more interesting (the phenomenon is that they dissent rarely, not that agreement spreads)?
3. Is it worth spending 2 to 3 hours on a second, independent coding before applying?
4. Does the pause-tool finding (a scaffolding change that looks like behaviour) deserve a line in the pitch as
   evidence of methodological care?
