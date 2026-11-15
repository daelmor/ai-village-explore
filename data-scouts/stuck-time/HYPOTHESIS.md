# Stuck time: has the time agents spend stuck fallen with newer models?

| | |
|---|---|
| Slug | `stuck-time` |
| Status | idea <!-- idea → exploring → verified → written-up → archived --> |
| Started | 2026-11-15 |
| Last updated | 2026-11-15 |
| Report | `FINDINGS.md` (one page) |

Sections "Question" to "What counts as a null" were written and committed **before** any stuck-episode outcome
was computed (see the git history of this file). Only structural facts were looked at first: the column list
of the cached turn extracts from the authority-recognition case, the shapes of `agent_action`
(`{action, coordinate, text}`, `{command}`, `{command, restart}`, tool calls such as
`get_pixel_coords_of_element`), the action-name frequencies in two cached windows (bash is about 45% of turns
in Feb–Aug 2026 and 60% in Oct 2026), and `data/CHANGELOG.md`.

Prior knowledge that could bias the definition: the authority-recognition case found that the share of
auto-nudges that were "misfires" swung from 34% to 85% depending on which turns counted as activity. That is
why exactly one definition is fixed here and exactly one alternative is shown.

## Question

Has the time Village agents spend stuck fallen with newer models? "Stuck" means repeating the same action on
the same target without moving on. The question is about the model, so the answer has to survive the things
that changed alongside the models: the scaffolding (`data/CHANGELOG.md`), the goal of the week, the room, and
the shift from GUI clicking to bash.

## Unit of analysis

- **Turn** = one row of `computer_use_turns` (3,307,175 rows), assigned to an agent through
  `computer_use_sessions.agent_id`.
- **Work action** = a turn whose `agent_action` is one of: a bash command (`{command}`), a pointer action
  (`left_click`, `double_click`, `triple_click`, `right_click`, `middle_click`, `left_click_drag`,
  `left_mouse_down`, `left_mouse_up`), `type`, `key`, `hold_key`, `get_pixel_coords_of_element`, or a bare
  bash `restart`.
- **Signature** of a work action = action name + target. Target = the full `agent_action` object with null
  fields dropped, serialized with sorted keys. For bash the target is the command with full-line `#` comments
  removed and whitespace collapsed (agents were asked on 2026-05-28 to open commands with a first-person
  comment, which would otherwise make identical commands look different).
- **Neutral turns** neither extend nor break a run: no action (talk-only), `{}`, `screenshot`, `wait`,
  `cursor_position`, `mouse_move`, `scroll`, `view_clipboard`, `send_message_back_to_chat`. Scrolling is
  neutral because five identical scrolls are how a long page is read.
- **Breaking turns** end a run without belonging to one: `pause`, `search_history`, `move_to_room`, the
  `request_*` tools and any other action name.
- **Agent** = one row of `agents`. The Claude Code agent is excluded (different scaffold, its turns are in
  `claude_code_messages`). Agents enter the per-agent trend only with ≥ 20 active hours and ≥ 1,000 work actions.

## The one definition (D1, primary)

A **stuck episode** is a maximal run of **5 or more consecutive work actions with the same signature** inside
one computer-use session (neutral turns skipped).

- **Start** = `created_at` of the first action of the run. **Recovery** = `created_at` of the first later work
  action in the same session with a different signature. **Time to recover** = recovery − start.
- An episode with no later different work action in its session is **unrecovered in session** (censored);
  its duration runs to its last repeated action. The unrecovered share is reported next to every median.
- **Active hours** of an agent = sum of the gaps between consecutive turns of the same session, each gap capped
  at 5 minutes (longer gaps are pauses, overnight stops or waits, not computer use).

## Measures (fixed in advance)

| Measure | Definition | Level |
|---|---|---|
| Episode rate (primary) | D1 episodes / active hours | agent |
| Time to recover | median of (recovery − start) over the agent's recovered episodes | episode, summarized per agent |
| Stuck share of time | time inside D1 episodes (start to recovery, or to last repeat if unrecovered) / active time | agent |
| Episodes per 1,000 work actions | D1 episodes / work actions × 1,000 (removes differences in turns per hour) | agent |

**Model release date** = the date embedded in `model_string` when there is one (e.g. `gpt-5-2025-08-07`);
otherwise the public release date for 2025 models I can state from general knowledge (Gemini 2.5 Pro
2025-03-25, Grok 4 2025-07-09, Gemini 3 Pro 2025-11-18, DeepSeek-V3.2 2025-12-01); otherwise the Village join
date, which in 2025 trailed release by 1 to 24 days. The source used for each agent is a column of the output.
Claude 3 Opus (released 2024-02, joined 2026-09) is the one old model in a new scaffold and is flagged.

## The one alternative definition (D2, robustness only)

A **low-variety stretch**: a maximal stretch of work actions in one session in which every window of 8
consecutive work actions holds at most 2 distinct signatures. It catches A-B-A-B alternation, which D1 misses.
Only the episode rate and its trend are recomputed under D2. No third definition will be tried.

## Controls (fixed in advance)

1. **Scaffolding regimes.** The trend is recomputed inside each regime bounded by the computer-use changes in
   `data/CHANGELOG.md`: R1 launch to 2026-03-10 (discrete computer-use sessions; inside it the 2026-02-20
   100-turn cap), R2 2026-03-11 to 2026-03-23 (perma-computer-use transition, excluded from trends),
   R3 2026-03-24 to 2026-09-30 (perma-computer-use), R4 2026-10-01 on (rewritten bash tool that cannot hang).
   Changes aimed at one provider (Gemini 2025-04-24, 2025-07-10, 2026-02-20; Anthropic 2026-03-26, 2026-06-03;
   OpenAI 2026-09-04, 2026-09-08) are listed with before/after rates for the provider they touched.
2. **Same goal period and room.** Cells = village goal period × room (room from `computer_use` era chat
   activity; before rooms existed, 2026-02-25, the cell is the goal period). Inside each cell with ≥ 4 agents
   that each have ≥ 2 active hours, rank agents by release date and by episode rate; report the pooled
   within-cell Spearman correlation and the share of cells where it is negative.
3. **Modality.** The episode rate per 1,000 work actions is recomputed separately for bash actions and for GUI
   actions, because newer agents work mostly in bash and a repeated bash command can be polling, not being stuck.

## What counts as a null

| id | Hypothesis | Supports if… | Null / refuted if… | Status | Evidence |
|---|---|---|---|---|---|
| H1 | Agents built on later-released models have fewer stuck episodes per active hour | Spearman ρ(release date, episode rate) ≤ −0.4 across eligible agents, permutation p ≤ 0.05 | \|ρ\| < 0.4 or p > 0.05 (null); ρ ≥ +0.4 with p ≤ 0.05 (refuted) | open | — |
| H2 | The trend is a model effect, not a scaffolding / goal / room effect | pooled within-cell ρ ≤ −0.3 with ≥ 65% of cells negative, and ρ ≤ −0.3 inside every regime that has ≥ 6 eligible agents | the trend is absent (ρ > −0.3) inside any single regime or inside cells: then say "the trend disappears within a scaffolding period" | open | — |
| H3 | Later models recover faster | ρ(release date, median time to recover) ≤ −0.4, p ≤ 0.05, agents with ≥ 20 recovered episodes | otherwise null | open | — |
| H4 | The result does not depend on the definition | D2 gives the same sign for H1 and ρ within 0.2 of D1 | sign flips or \|Δρ\| > 0.2: the headline is definition-dependent and is reported as such | open | — |

A headline number is only offered if H1 and H2 both hold. If H1 holds and H2 fails, the finding is "newer
agents are stuck less, and the data cannot separate model from scaffolding". If H1 fails, the null is the result.

## Reading check (fixed in advance)

Thirty D1 episodes drawn at random (`random_state=0`), stratified by action kind (bash, pointer, key/type,
`get_pixel_coords_of_element`), are read against the raw turns (action, output, error). Each is coded stuck /
not stuck (polling, deliberate repetition such as paging with a key, a loop that makes progress). The
false-match rate is reported per action kind. At least five instances behind each headline number go into
`VERIFICATION.md` with turn ids, UTC timestamps and deep links.

## Data

- Raw tables (`data/`): `computer_use_turns.jsonl.gz` (streamed once, never loaded whole),
  `computer_use_sessions.jsonl.gz`, `agents.jsonl.gz`, `village_goals.jsonl.gz`, `CHANGELOG.md`.
- Shared tables (`core/out/`): `agents_roster.csv`, `chat.parquet` (room of each agent per day).
- Case caches (`out/`, git-ignored): `turn_actions.parquet` (one row per turn: ids, timestamp, action kind,
  signature hash, a 300-character excerpt of the action, output and error).

## Known limits (before looking)

- No screenshots are used, so "the screen did not change" cannot be checked; the definition is about what the
  agent did, not what it saw.
- Repeating a bash command can be legitimate polling (`sleep 30; curl …`). The reading check measures how often.
- Loops with a period longer than 2 (A-B-C-A-B-C) are missed by both definitions.
- Newer models arrived in a different scaffold, with different goals, more co-present agents and more bash.
  Release date, join date and scaffolding regime are strongly correlated. Nothing here is causal.

## Findings

See `FINDINGS.md`.
