# Stuck time — findings

Export 2026-10-25 of `aidigestorg/ai-village`. One definition and one alternative were committed in
[HYPOTHESIS.md](HYPOTHESIS.md) before any episode was computed. Counts are **episodes**, **agents** or **turns**
as labelled. **[V]** verified by hand against raw rows, **[C]** computed, not read, **[I]** inferred. Hand-check
log: [VERIFICATION.md](VERIFICATION.md).

## Best candidate number (a null)

**Agents built on later models repeat the same action five times in a row less often (Spearman ρ = −0.50 across
43 agents), but only 7 of 30 such episodes read by hand were an agent actually stuck, and the trend is absent for
bash commands and inside the newest scaffolding period. The data do not show that stuck time fell with newer
models.**

- **Definition (D1, fixed in advance).** Episode = 5 or more consecutive work actions with an identical signature
  (action + target) inside one computer-use session; observation-only turns are skipped. Rate = episodes per
  active hour (inter-turn gaps capped at 5 minutes). Agent-level trend over agents with ≥ 20 active hours and
  ≥ 1,000 work actions; release date from the model string, else Village join date.
- **Numerator / denominator.** 3,118 episodes in 20,126 active hours (0.155 per hour) over 3,295,475 turns and
  2,412,302 work actions of 55 agents; 1.3% of active time falls inside an episode; 74.9% of episodes are
  followed by a different action in the same session, after a median of 122 seconds (quartiles 78–233). **[C]**
- **The trend.** ρ(release date, episodes per hour) = −0.50, permutation p = 0.0006, 43 agents: H1 passes its
  threshold. The alternative definition D2 (8 actions, at most 2 signatures) gives ρ = −0.63: same sign, within
  0.2. Time to recover shows no trend (ρ = +0.11, 22 agents). **[C]**
- **What the episodes are.** 30 episodes drawn at random and read against the raw turns: **7 stuck, 2 unclear, 21
  not stuck** (false-match rate 70–77%) **[V]**. Not stuck means paging with a key, polling a page or an inbox
  while waiting for someone, `sleep 90` used as a wait, or keystrokes sent to a game. By kind: bash 2 of 9,
  pointer 2 of 9, keys 0 of 7, `get_pixel_coords_of_element` 3 of 5. Keys are 58% of all episodes (1,820), so
  weighted by kind about one episode in ten is a real stuck agent **[I]**.

## How it holds up: it does not

| Check (fixed in advance) | Result | Reading |
|---|---|---|
| Inside scaffolding regimes | R1 to 2026-03-10: ρ = −0.40 (17 agents, p = 0.12). R3 perma-computer-use: −0.76 (32). **R4 from 2026-10-01: −0.22 (33, p = 0.22)** | H2 fails: the trend disappears within the newest scaffolding period |
| Inside goal-period × room cells | pooled within-cell ρ = −0.27 (73 cells; 60 negative, 82%) | sign holds, size is under the −0.30 threshold |
| By modality | GUI actions only: ρ = −0.58 (34 agents). **Bash only: ρ = −0.13 (38, p = 0.45)** | the decline is a GUI effect; agents released before mid-2025 did under 10% of their work actions in bash (Gemini 2.5 Pro 37%), agents that joined from June 2026 a median of 94% |
| Per 1,000 work actions instead of per hour | ρ = −0.40 | weaker once speed is removed |

Three artifacts found by reading, each sized by script **[C]**:

- **A click with no coordinate.** Claude 3.5 Sonnet moved the mouse, then sent `left_click` with no coordinate, so
  five clicks on five different targets share one signature: 68 of its 72 episodes. It is the oldest model in the
  trend and its 2.6 episodes per hour is an artifact of my signature, not behaviour.
- **Waiting in bash.** 165 bash episodes are a command starting with `sleep`; 123 of them start on or after
  2026-10-20, the day the `pause` tool was removed, against 11 in the first 19 days of that month (Muse Spark 1.3
  has 46, Claude Fable 5 28, Claude Opus 4.6 22). A scaffolding change turned waiting into "repetition".
- **Scaffolding steps move the rate more than models do.** In the 21 days after parallel tool use was disabled
  for Claude agents (2026-06-03) their rate went from 0.03 to 0.32 per hour, while other agents went from 0.16 to
  0.33 in the same weeks (the "Follow your leader!" and event goals). After the bash rewrite of 2026-10-01 the
  overall rate went from 0.02 to 0.07, most of it the `sleep` loops above.

**Confounds.** Release date, join date, scaffolding regime, goal, hours per day and the share of work done in
bash all rise together. No screenshots were used, so "the screen did not change" was never checked. Not causal.

## Verified instances **[V]** (turn ids and links in VERIFICATION.md)

| Episode (first turn, UTC) | What the raw rows show | Stuck? |
|---|---|---|
| DeepSeek-V3.2, `2f0d61a2…`, 2026-03-09 17:51:54 | `pwd` 5 times against "a previous bash command timed out, so you must restart the bash tool" | yes |
| Grok 4, `201b0a7e…`, 2025-09-29 19:16:23 | `left_click_drag` 6 times, each answered "coordinate is required" | yes |
| Gemini 2.5 Pro, `30a9176d…`, 2026-07-27 18:25:34 | clicks (547, 26) 55 times in 33 minutes trying to open a terminal; session ends | yes |
| Gemini 2.5 Pro, `f4ca1ca4…`, 2026-05-06 18:52:17 | asks for the terminal window's coordinates 20 times over two hours | yes |
| Gemini 3.1 Pro, `6193014c…`, 2026-03-13 19:20:08 | `gh pr list` 10 times with empty output, then `pkill gh` | yes |
| Muse Spark 1.3, `f464a23d…`, 2026-10-21 22:02:23 | `sleep 110; date` 15 times: "I'll hold the watch toward 3:30pm" | no: waiting |
| Claude 3.5 Sonnet, `4b2a54dd…`, 2025-04-04 18:38:33 | five coordinate-less clicks after five different mouse moves | no: artifact |

## What a 10–20 hour project would add

A definition that reads the outcome and not only the action: repeated action **and** unchanged tool output or a
repeated error string (the three clearest stuck cases here are error loops), with screenshot hashes as the check
for GUI turns; a labelled set of a few hundred episodes to measure precision per action kind before any trend is
computed; waiting (`pause`, `wait`, `sleep`) handled as its own state; and the comparison restricted to agents
that shared a scaffold, a goal and a modality, which is where a model effect would have to show.
