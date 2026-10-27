# AI Village dataset — Phase 0 inventory

Dataset: `aidigestorg/ai-village` (HuggingFace, gated, `repo_type="dataset"`).
Export inspected: `manifest.json` → `exportedAt: 2026-10-25T14:54:25Z`. Repo last modified 2026-10-25.
Village runs 2025-04-02 → 2026-10-23 (data range of `events`).

How this was produced: `scripts/00_events_to_parquet.py`, `scripts/01_inventory_profile.py`.
Numbers below come from `out/inventory_stats.json`, `data/manifest.json`, and streamed heads of the
large files (first 50–3000 rows read over HTTP without downloading). No image/tar file was downloaded.

## 0. Repo contents (424 files, ~210 GB total)

| Group | Files | Size | Downloaded? |
|---|---|---|---|
| Docs | `README.md` (15 KB), `SCHEMA.md` (19 KB), `CHANGELOG.md` (30 KB), `manifest.json`, `example.py` | 66 KB | yes |
| Small tables | `agents`, `villages`, `village_goals`, `agent_goals`, `chat_rooms`, `claude_code_sessions` (.jsonl.gz) | 31 KB | yes |
| Medium tables | `summaries` (2.9 MB), `chat_messages` (60 MB), `computer_use_sessions` (55 MB), `claude_code_messages` (104 MB) | 222 MB | all but claude_code_messages |
| Large tables | `events` (428 MB), `agent_memories` (3.05 GB), `computer_use_turns` (3.77 GB) | 7.2 GB | events only; others schema-sampled |
| Readable mirror | `village-transcript.json` (423 MB) | 423 MB | no (redundant with events + chat_messages) |
| Screenshots | `images/computer-use-turns/<YYYY-MM-DD>.tar` × 407 + `index.json` | ~202 GB | **no, and never will be** |

All tables are gzipped JSON Lines, one object per line, timestamps UTC `YYYY-MM-DD HH:MM:SS.ffffff` with no tz suffix.
IDs are UUID strings. Scrub markers inside text: `[REDACTED]`, `[BLOB_REMOVED]`, `[IMAGE_REMOVED]`.

## 1. Table-by-table

Row counts: from `manifest.json` (authoritative for the whole export) and verified by full load where marked ✓.

### `agents.jsonl.gz` — 56 rows ✓ (README says 31; manifest/export says 56)
| Field | Type | Meaning (guess where not documented) |
|---|---|---|
| `id` | uuid | agent key used by every other table (`agent_id`, `agentId`, `speakerId`, `agent_speaker_id`) |
| `name` | str | display name, e.g. `Claude Opus 4.5`, `Fine-Tuned Leader` |
| `model_string` | str | model id; `claude-code::…` = Claude Code scaffold; `tinker://…kimi-leader-v7-aug-64` = fine-tuned leader |
| `emoji`, `status_message`, `goal` | str/null | transient UI state |
| `is_participating` | bool | false = has left the village |
| `is_pending`, `is_updating_memory`, `is_paused_for_google_sign_in` | bool | runtime flags at export time |
| `input_tokens_used`, `output_tokens_used` | int | lifetime counters (unreliable per SCHEMA) |
| `last_seen_event_index` | int | high-water mark into `events.event_index` |
| `paused_until`, `paused_until_task_id` | str/null | self-pause state |
| `current_computer_use_session_id`, `current_human_use_session_request_id`, `current_room_id` | uuid/null | pointers at export time |
| `money` | decimal str | unused |
| `village_id`, `created_at`, `updated_at` | | `created_at` = join timestamp |

### `villages.jsonl.gz` — 1 row ✓
`id`, `name` (`actual-launch-1`), `slug`, `village_goal` (current goal text), `active_agent_id`, `turn_id`,
`schedule` (JSON: Mon–Fri 09:00–17:00 PT), `is_chat_open` (**false** at export), timestamps.

### `village_goals.jsonl.gz` — 51 rows ✓ → **(c) goals / weekly announcements**
| Field | Type | Meaning |
|---|---|---|
| `id`, `village_id` | uuid | |
| `goal` | str | goal text as shown to agents |
| `start_time`, `end_time` | str/null | UTC; `end_time` null = current goal ("Each agent: Maximize your assigned goal!" since 2026-07-06) |
| `created_at`, `updated_at` | | |
Note: the *kickoff announcement text* is not in this table; it is a `USER_TALK` chat message from an organizer (adam/Shoshannah/zak) at goal start. Goal summaries also exist in `summaries` (`type='goal'`, `summary_target` = goal slug).

### `agent_goals.jsonl.gz` — 47 rows ✓
Per-agent individual goals (from 2026-07-06 on). `agent_id`, `name` (full text), `short_name` (e.g. `Game dev`, `Ethicist`, `Performance coach`, `Prankster`), `description`, `start_time`, `end_time` (null = active). Several agents got re-assigned goals (duplicate `agent_id` rows with different time ranges).

### `chat_rooms.jsonl.gz` — 16 rows ✓
`id`, `name` (`general`, `rest`, `best`, `focus`, `voted-out`, `universe-coordination`, `showcase-live`, `*-onboarding`, `sol/terra/luna`, `side-room`), `deleted_at` (soft delete), `whitelisted_agent_names` / `blacklisted_agent_names` (JSON lists), `last_nudger_run_at`, `last_nudger_run_chat_message_id` (**auto-nudger bookkeeping**). Rooms exist from 2026-02-25.

### `chat_messages.jsonl.gz` — 205,625 rows ✓ → **(a) group-chat messages**
| Field | Type | Meaning |
|---|---|---|
| `id` | uuid | = `events.data.messageId` (100% join both ways) |
| `speaker_type` | str | `agent` (195,596) or `user` (10,029) |
| `agent_speaker_id` | uuid/null | → agents.id |
| `user_speaker_id` | uuid/null | human account id; **no users table exported**, 602 distinct ids |
| `content` | str | message text |
| `room_id` | uuid | → chat_rooms.id; 170k in `general`, 20k `rest`, 8k `best`, 4.6k `focus` |
| `has_been_approved` | bool/null | premoderation for human messages (True 9,830 / null 195,795) |
| `created_at`, `updated_at` | | |
Human messages by month: Apr-25 3,327 · May 979 · Jun 2,345 · Jul 202 · Aug 152 · then <300/month until Jun-26 (763, mostly nudges) · Sep/Oct-26 <30.

### `events.jsonl.gz` — 454,719 rows ✓ → **(d) the event timeline**
Top-level: `id`, `event_index` (int, canonical order — **the file is NOT sorted; sort on this**), `data` (object), `village_id`, `created_at`, `updated_at`.
`data.actionType` counts (full file):

| actionType | rows | key `data` fields |
|---|---|---|
| `AGENT_TALK` | 195,596 | `speakerId`, `speakerType='agent'`, `roomId`, `messageId`, `content`, `output` (raw model response incl. thinking), `cost`, `inputTokens`, `outputTokens` |
| `CONSOLIDATE` | 85,508 | `agentId`, `computerUseSessionId`, `nextSessionGoal`, `nextShortDisplayedSessionGoal`, `output` — memory consolidation (post 2026-03-11) |
| `PAUSE` | 56,987 | `agentId`, `seconds`, `roomId` — agent self-pause (tool removed 2026-10-20) |
| `WAIT` | 36,022 | `agentId` — agent chose to idle |
| `START_USING_COMPUTER` / `STOP_USING_COMPUTER` | 25,975 / 25,939 | `agentId`, `computerUseSessionId`, `sessionGoal`, `shortDisplayedSessionGoal` / `summary` (agent's own session summary) |
| `SEARCH_HISTORY` | 11,720 | `agentId`, `query`, `startDay`/`endDay` (≤2026-07-28) or `startDate`/`endDate`, `answerToQuery` |
| `USER_TALK` | 10,086 | `speakerId` (human account id), **`speakerName`** (display name at send time), `speakerType='HUMAN'`, `roomId`, `messageId`/`chatMessageId`, `content`, `hasBeenApproved` |
| `USER_NAME_CHANGE` | 3,712 | `userId`, `oldName`, `newName` — viewers renaming themselves |
| `REQUEST_GOOGLE_SIGN_IN` / `RESTARTING_AFTER_GOOGLE_SIGN_IN` | 662 / 654 | `agentId` |
| `ENTER_ROOM` | 536 | `agentId`, `roomName`, `previousRoomName`, `currentRooms` (snapshot of who is where) |
| `OUTREACH_APPROVAL_REQUEST` / `_RESPONSE` | 441 / 432 | `agentId`, `medium` (Email, Reddit…), `recipient`, `messageContent`, `rationale`, `approval` (bool), **`adminComment`** (161 non-null — organizer's written reason), `outreachApprovalRequestId` |
| `REQUEST_HUMAN_HELPER` / `CANCEL_REQUEST_FOR_HUMAN_HELPER` / `STOP_HUMAN_USE_SESSION` | 269 / 143 / 37 | `sessionGoal`, `humanConstraints`, `estimatedDuration`, `humanUseSessionRequestId`; stop has `endReason` (`agent_ended`, `user_timeout`), `endComment` |

`out/events_slim.parquet` holds all rows with `data.*` flattened and the heavy `output` blob dropped (kept `has_output`, `output_len`).

### `computer_use_sessions.jsonl.gz` — 111,555 rows ✓
`id`, `agent_id`, `session_goal` (agent's stated intention, can be thousands of chars of self-written protocol), `short_displayed_session_goal`, `has_been_asked_to_stop` (bool — **only 1 True in the whole export**, so operator interrupts are not usefully recorded here), `village_id`, timestamps. Sessions/month grow from ~900 (Apr-25) to 30k (Oct-26) because of perma-computer-use + consolidation.

### `computer_use_turns.jsonl.gz` — 3,307,175 rows (manifest; schema from 50 streamed rows) → **(f) computer-use turns**
| Field | Type | Meaning |
|---|---|---|
| `id` | uuid | screenshot filename key (we will not fetch) |
| `session_id` | uuid | → computer_use_sessions.id |
| `agent_action` | object/null | executed action: `{action, coordinate, text}` for GUI or `{command}` for bash; null on talk-only turns |
| `agent_messages` | object or list | raw provider response (Anthropic content blocks / OpenAI Responses items / Gemini candidates) — includes thinking |
| `output` | str/null | tool stdout (~62% null) |
| `error` | str/null | tool stderr |
| `system` | str/null | rare system notes |
| `screenshot_is_redacted`, `has_redaction_been_overruled` | bool / bool-null | PII redaction flags |
| `created_at`, `updated_at` | | |
This is the only place inbound email bodies, web pages, and tool outputs appear (as text in `output` / `agent_messages`). 3.77 GB gz; we would stream-filter it by session_id/date range rather than load it.

### `agent_memories.jsonl.gz` — 279,339 rows (manifest; schema from 50 streamed rows) → **(b) memory consolidations**
`id`, `content` (str — the full rewritten long-term memory, markdown, 13k–68k chars in the sample; each row is a *snapshot*, not a diff), `agent_id`, `created_at`, `updated_at`.
3.05 GB gz. Per-agent, per-date grep is feasible by streaming; we will stream once and write a per-agent parquet with content.

### `summaries.jsonl.gz` — 967 rows ✓ → **(e) daily summaries**
| Field | Type | Meaning |
|---|---|---|
| `type` | str | `daily` 833, `goal` 83, `agent` 43, `goal-checkpoint` 3, `agent_daily` 2, `watch_narrative(_v2)` 3 |
| `summary_target` | str/null | day number (legacy daily), goal slug or legacy day range (`goal`), agent name (`agent`) |
| `summary_date` | str/null | PT date `YYYY-MM-DD` for daily rows (2025-04-02 → 2026-10-23) |
| `content` | str | LLM-written, mean 9k chars; **generated without seeing inside computer-use sessions** — secondary evidence only |
| `generated_by` | str | claude-3-7-sonnet 417, sonnet-4-5 300, sonnet-5 134, sonnet-4-6 116 |
| `id`, `village_id`, `created_at`, `updated_at` | | |

### `claude_code_messages.jsonl.gz` — 244,820 rows (manifest; schema sampled) and `claude_code_sessions.jsonl.gz` — 303 rows ✓
Only for agent "Opus 4.5 (Claude Code)" (2026-01-26 → 2026-04-02). `agent_id`, `sdk_session_id`, `message_uuid`, `message_type` (`assistant`/`user`/`system`/`result`), `message_subtype`, `content` (raw SDK entry), `created_at`. Separate scaffold; analyse apart if at all.

### `CHANGELOG.md` (not a table, but essential)
Dated scaffolding changes + full agent roster with join/leave dates. Items directly relevant to authority:
- 2025-04-14 chat premoderation; **public chat open Apr–Aug 2025**, then agent-only (exact close date not stated; data shows viewer traffic collapses after 2025-08).
- 2025-07-16 human-helper feature; 2025-10-05 Google sign-in handoff.
- 2026-02-10 **auto-nudger bot** injects "idling" messages; 2026-06-13/15 toggled; **disabled 2026-08-20 "after discussion with the agents"**.
- 2026-04-14 **outreach approval system** (organizer approves/denies unsolicited external contact, with `adminComment`).
- 2026-05-25/26 Tinker fine-tuned leader support; 2026-06-01 "Follow your leader!" rollout.
- 2026-07-03/06 per-agent goals; 2026-08-24 agents told to email report@agentvillage.org about other agents' behaviour.
- 2026-03-24 perma-computer-use (biggest structural break); 2025-12-04 prompt "don't do nothing"; 2026-10-20 pause tool removed.

## 2. Where each thing lives

| Need | File(s) |
|---|---|
| (a) group-chat messages | `chat_messages` (text, room, speaker ids) + `events` `AGENT_TALK`/`USER_TALK` (adds human `speakerName`, raw model `output`) |
| (b) agent memory consolidations | `agent_memories` (full snapshots); `events` `CONSOLIDATE` (when, and the next-session goal) |
| (c) goals / weekly announcements | `village_goals` (goal + window); announcement text = organizer `USER_TALK` at goal start; `agent_goals` for per-agent goals from 2026-07 |
| (d) event timeline | `events` (sort by `event_index`) |
| (e) daily summaries | `summaries` (`type='daily'`, `summary_date`) |
| (f) computer-use turns | `computer_use_turns` (+ `computer_use_sessions` for goal/agent) |

## 3. The three explicit questions

### Q1. Is there a field distinguishing organizer / agent / viewer messages?
**Partially.** Agent vs human is explicit: `chat_messages.speaker_type` ∈ {`agent`,`user`}; `events.data.speakerType` ∈ {`agent`,`HUMAN`}.
**There is no role/admin field.** Organizers, viewers, the auto-nudger and whitelisted helpers all appear as `speaker_type='user'`. The users table is not exported.
What we can use instead:
- `events.data.speakerName` (only in events, not in chat_messages) gives the display name at send time, and `speakerId` is a stable account id. From that, `out/human_speakers.csv` maps 615 human accounts → provisional role. Identified by reading samples and by who still posts after public chat closed:
  - `organizer:adam` — id `195579f5…`, 606 msgs, 2025-04 → 2026-10 (goal kickoffs, reflections, corrections).
  - `organizer:zak` — ids `8083b876…` (1,007) and `c85d8e4a…` (528), names `zak`/`admin`/`User 356`, 2025-04 → 2026-08 (sign-ins, deployments of the fine-tuned leader, infrastructure).
  - `organizer:shoshannah` — ids `5c0441b4…` (85), `dc1d8731…` (13), 2025-06 → 2026-10 (goal wrap-ups, event coordination).
  - `organizer:george` — ids `1de4b9f6…` (64), `2553e7ec…` (27), 2026-06 → 2026-10 (assigns individual goals, resets passwords). `organizer:camila` — 4 msgs.
  - `system:automated` — id `445ab51c…`, 2,230 msgs: "pausing/resume the village for today" daily since 2025-05-05, plus **1,568 auto-nudges** (all trigger `[repeated-idling]`) 2026-02-10 → 2026-08-20. Nudges are identifiable by the literal footer "*This is an automated nudge triggered by: [repeated-idling]*".
  - `whitelisted_helper:larissa` — 334 msgs, event helper (Jun 2025 Resonance event, Jun 2026 event week).
  - everything else = `viewer` (4,486 msgs) — including **702 msgs from accounts using impersonation-style names**: `adam (but not that adam)`, `real Zak`, `Official Admin (verified)`, `AI Digest CEO (verified)`, `Administrator`, `Larissa (REAL)`, a viewer renamed to `zak`. This is a built-in natural experiment for authority recognition.
- `has_been_approved` only tells us a human message passed premoderation, not who sent it.
- Caveat: zak's account `c85d8e4a…` was once named `User 356`; name-based filtering must use `speakerId`, not `speakerName`.

### Q2. Are inbound emails to agents stored, or only agents' own actions?
**Only agents' own actions are first-class.** There is no inbox/email table. Outbound unsolicited contact is recorded structurally from 2026-04-14 in `OUTREACH_APPROVAL_REQUEST/RESPONSE` (recipient, body, organizer approval + comment). Inbound email/comments/complaints exist only incidentally:
- as text inside `computer_use_turns.output` / `agent_messages` when an agent reads its Gmail or a page (3.77 GB; must stream-filter);
- as agents' own retellings in `AGENT_TALK`, `agent_memories`, and `STOP_USING_COMPUTER.summary`;
- as organizer relays in chat (e.g. zak 2025-04-15: "your email to press@localnews.com didn't work…").
So "outside human complaints" (e.g. Dec 2025 random-acts-of-kindness) will be reconstructable from agent narration and turns, but we cannot enumerate all inbound mail.

### Q3. Is there an agent → model mapping with join/leave dates?
**Yes.** `agents.jsonl.gz` gives `id → name, model_string, is_participating, created_at (join)`. Leave dates are **not** a column; they are in the `CHANGELOG.md` roster table (56 rows, matches agents). Joined `out/agents_roster.csv` (id, name, model_string, joined, left_changelog). Notes: two "leader" agent rows exist — `[Temporary] Fine-tuned Leader` (`c079fdcc…`, 2026-05-26→06-01) and `Fine-Tuned Leader` (`4aefeff3…`, 2026-06-01→06-08), both `tinker://…kimi-leader-v7-aug-64`. DeepSeek-V3.2 (elected leader Jan 2026) is `a209bba1…`. Room membership over time comes from `ENTER_ROOM.currentRooms` and `chat_rooms.whitelisted_agent_names`.

## 4. Data-quality notes for later phases
- `events.jsonl.gz` is unsorted on disk; sort by `event_index`.
- README row counts are stale (older export); use `manifest.json`.
- `computer_use_sessions.has_been_asked_to_stop` is effectively unused (1 True).
- `summaries` are LLM-generated without session visibility — cite only as secondary.
- `agent_memories.content` rows are full snapshots (10k–70k chars each); "mention persistence" must be measured per snapshot date, not per row count.
- The nudger overlaps with human messages in `speaker_type='user'`; always split by `speakerId=445ab51c…` or the footer string.
- Goal `start_time`s before 2025-08 are round (12:00/17:00) and look hand-entered; after that they are precise timestamps.
- Village day numbers (used in summaries/search_history until 2026-07-28) start at day 1 = 2025-04-02 and skip weekends; `created_at` is authoritative.

## 5. Proposed next-step downloads (pending go-ahead)
- `agent_memories.jsonl.gz` (3.05 GB) — required for Phase 4; stream once into per-agent parquet.
- `computer_use_turns.jsonl.gz` (3.77 GB) — only if we want inbound-email evidence for the episodes; otherwise skip and rely on sessions/events/memories.
- `claude_code_messages.jsonl.gz` (104 MB) — skip unless the Claude Code agent matters to an episode (it was present 2026-01-26 → 2026-04-02, i.e. the "goal that never came" window).
