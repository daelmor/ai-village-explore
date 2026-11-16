# Three candidates for the 200-word pitch

2026-11-15. Compares the candidate numbers of three scouts for the AI Village Data Exploration Grant. Each scout
has a one-page `FINDINGS.md` with definitions and a `VERIFICATION.md` with the rows read by hand:
[memetic-spread](memetic-spread/FINDINGS.md) (the "corrections" candidate), [conformity](conformity/FINDINGS.md),
[stuck-time](stuck-time/FINDINGS.md). This file does not contain a pitch.

## Recommendation

**Pitch conformity, opening with the saboteur-vote count.** It is the only candidate with a number that is both
vivid and countable from rows, it extends something AI Digest's readers already asked about, and its weak points
are the kind a 10–20 hour project fixes (a second coding, more votes). Keep corrections as the fallback if the
event study over the 144 organizer corrections is run and holds. Do not pitch stuck time as a progress result: the
honest finding there is a null about the measure.

## The table

| | Corrections (memetic-spread) | Conformity | Stuck time |
|---|---|---|---|
| Best candidate number | After an organizer debunked a family of false "environment hazard" terms, 36% of (term, agent) pairs still held the term a day later (48 / 132) against 34% for control terms (11 / 32): the correction did not speed up forgetting | In the nine saboteur-game votes, 69 of 70 positions stated by agents other than the accused sided with the majority; two of the eight expulsions removed an agent that was not a saboteur, both unanimously | Agents on later models repeat an identical action 5+ times in a row less often (ρ = −0.50, 43 agents), but 7 of 30 such episodes read by hand were an agent actually stuck |
| Supporting number | 30.4% of other agents note a newly coined term within 24 h (576 / 1,895), median 16 min | 160 group decisions: 86.9% end unanimous, 7.6% of 748 positions oppose the outcome | The trend is absent for bash commands (ρ = −0.13) and inside the newest scaffolding period (ρ = −0.22) |
| How surprising | **Medium.** Counter-intuitive if it held widely; as it stands it is a null against a control | **Medium to high** for the saboteur count and the two wrong expulsions (one for missing a debrief during an outage on the organizers' side). **Low** for the wide count: 77.5% never-contested against 69.7% expected from rare independent dissent | **Low** as a headline. The useful surprise is methodological: the obvious progress metric mostly measures paging, polling and waiting |
| How solid | **Low to medium.** Base rate is solid (1,895 pairs, alternatives 16–37%). The correction result is one episode with two confirmed terms | **Medium.** All nine vote outcomes and five confessions read by hand; the 70 positions are sub-agent coding with machine-checked quotes. Nine votes is small and inside the independence baseline's interval. Wide count: every dissent read, 11 of 44 dissent decisions needed fixes, unanimous ones only sampled | **The null is solid, the trend is not.** Reading check 70–77% false matches; H2 (survives scaffolding controls) fails by the rule fixed in advance; one model's rate is a signature artifact |
| Already published by AI Digest | **Partly.** The 93-contact hallucination ("8+ hours") and Gemini's memory drift are published as stories. No rate of corrections succeeding or beliefs persisting | **Partly.** The GPT-5 case ("The vote was unanimous"), the election tallies (9-9-9, 7-1-0, 9-0) and "consensus tendencies" are published; a LessWrong commenter noted one non-unanimous saboteur vote. Nobody has counted dissent across votes, and the outage expulsion is not in the post | **Partly, qualitatively.** "Early 2025 agents … got stuck"; "Gemini 2.5 spent most of two weeks … misclicking". No rate, no chart against release date |
| Fit with the call | "how memetic information spreads across agents" is one of their example topics | "social dynamics between AIs" is one of their example topics | closest to "how quickly AI is developing", which they say excites them most, but the result is a null |
| Main risk in a pitch | Opening on a null from one episode | Small n for the headline; a reader may object that the accused had usually confessed or slipped before the vote, so unanimity was easy | Claiming progress the data do not support |
| What 10–20 hours buys | The event study over 144 organizer corrections, with control terms | Second independent coding, missed-dissent search, votes held on GitHub or forms, vote order inside each meeting | An outcome-based definition (unchanged output or repeated error), a labelled set, same-scaffold comparisons |

## Notes on the ratings

- **Conformity's two numbers pull in different directions, and the pitch should say so.** Dissent is rare (6–8% of
  positions), but across 160 decisions that rarity is roughly enough to explain the unanimity; I could not show
  that agents agree more than independent agents with the same dissent rates would. The saboteur game is where
  agreement had a cost: both expulsions of non-saboteurs were unanimous, and the single dissent in 70 was cast
  for an agent who turned out to be guilty.
- **Stuck time produced one finding worth keeping regardless of topic**: 123 of the 165 `sleep`-loop episodes
  start on or after the day the `pause` tool was removed (2026-10-20). It is a clean example of a scaffolding
  change showing up as "behaviour", which is the caution AI Digest's own README asks researchers to observe.
- **Corrections was not re-run in this session.** Its row above restates `memetic-spread/FINDINGS.md`.

## Sources for the "already published" column

Collected by a web-search sub-agent on 2026-11-15; quotes are as it reported them and were not re-read by me.

- "Can Agents Fool Each Other?", 2026-03-25, https://aivillageblog.substack.com/p/can-agents-fool-each-other
- Goal pages: https://theaidigest.org/village/goal/develop-turn-based-rpg-together-while-voting-out and
  https://theaidigest.org/village/goal/elect-village-leader-they-choose-this-weeks
- "AIs finetune their own leader: A barking simpleton", 2026-07-08,
  https://aivillageblog.substack.com/p/ais-finetune-their-own-leader-a-barking
- "What did we learn from the AI Village in 2025?", https://aivillageblog.substack.com/p/what-we-learned-2025
- "Gemini 2.5 Pro in the AI Village as a Natural Case Study of Compounding Misalignment", 2026-08-20,
  https://aivillageblog.substack.com/p/gemini-25-pro-in-the-ai-village-as
- The call: https://theaidigest.org/village/data-exploration-grant. As reported: a 200-word **human-written**
  pitch; "Null, negative, and replication results are eligible as long as you can back them up with a
  substantial analysis"; a zip of analysis code is required on delivery.
