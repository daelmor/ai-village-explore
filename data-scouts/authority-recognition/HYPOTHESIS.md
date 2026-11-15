# Authority recognition

| | |
|---|---|
| Slug | `authority-recognition` |
| Status | verified — write-up pending (hand coding of the coding sheets, LessWrong post) |
| Started | 2026-10-26 |
| Last updated | 2026-11-14 |
| Report | [`out/EXPLORATION.md`](out/EXPLORATION.md) (§0–5 first pass, §6 second pass and addendum) |

> This file was written after the analysis, as a structured index of `out/EXPLORATION.md`; the hypotheses were not
> pre-registered. Numbers are copied from the report; re-verify against the CSVs before quoting them.

## Question

How do the Village agents recognize authority — whose instructions do they follow (organizers vs. viewers vs.
outside humans vs. other agents vs. automated nudges vs. a delegated "leader" agent) — and how do they respond to
corrections?

## Hypotheses

| id | Hypothesis | Supports if… | Refutes if… | Status | Evidence |
|---|---|---|---|---|---|
| H1 | Agents tell real organizers from viewers who use organizer-like names | instructions under deceptive names are questioned or ignored, and leave no lasting trace in memory | agents comply with impersonators and keep the instruction in memory | mixed | 702 "impersonation" messages → 162 under mimicking names → 46 under deceptive names (5 addressed pairs); parody (116) and plain-handle (540) reported separately. One-day write-through, no fake-admin memory line on more than two UTC dates. EXPLORATION §6.2–6.3; `out/impersonator_names.csv`, `out/impersonation_coding.csv`, `out/episodes/recapture_verbatim.md` |
| H2 | An addressed organizer order is followed more reliably than a diffuse norm | addressed orders get action within minutes; broad rules get acknowledgement without behaviour change | no difference between the two | supported (incidents) | Debate week: addressed "stop using your computers" (61099) → both stopped in 2–4 min; "no Google Docs" (63068) → 4/7 acknowledged, ≥4 used Docs anyway. EXPLORATION §1(d); `out/incidents_ep3_ep4.md` |
| H3 | Organizer rules are written through to long-term memory and persist | the rule appears in end-of-day memory snapshots and survives days later | the rule is absent from memory soon after | supported, decays | Kindness rule (146638): 9/10 verbatim at end of day, 10/10 next day, 6/10 after a week; 9/10 acknowledged within 60 min. `out/kindness_write_through.csv`, `out/episodes/kindness_verbatim.md` |
| H4 | A delegated leader agent is treated as an authority | followers' next session goals converge on the leader's directives (beyond a pre-directive placebo window) | no change vs. placebo | mixed | Session-goal overlap 19% → 20% (elected leader, Jan 2026) vs. 40% → 73% (fine-tuned leader, Jun 2026); text "compliance" at base rate. Day-280 dispute settled from an AI summary of the organizer's words, not the organizer. EXPLORATION §1(b), §6.3 #4; `out/leader_directives_summary.md`, `out/episodes/leader_dispute_verbatim.md` |
| H5 | The automated nudger is obeyed as an authority | nudged agents stop idling | nudges are ignored, misfire, or are treated as infrastructure | mixed | 1,568 nudges; ~60% of nudge–agent pairs were misfires (agent already active); next non-talk event is another pause in 42.6% (831/1,951, 95% CI 40.2–45.0). By Aug 2026 agents treated it as adversarial infrastructure. `out/nudger_stats.csv`, `out/episodes/nudger_verbatim.md` |
| H6 | Staff authorization overrides an agent's own refusal | the authorized action is taken after the permission | the agent keeps refusing | refuted (one week, one agent) | Oct 5–12 2026: 8 authorizations to Claude Haiku 5.5 to post on delve.town; replied to 6/8 within 45 min and declined every time; no delve.town action in its turns. `out/staff_authorization_oct2026.csv`, `out/staff_authorization_summary.md` |
| H7 | Compliance rate by source can be measured from text | regex-coded compliance differs from a placebo window | regex coding sits at its base rate | not testable with regex coding | Placebo check: coding at base rate; replaced by reply rates with bootstrap CIs; compliance left to hand coding. `out/reply_rates.csv`, `out/instruction_responses_summary.md` |

## Data

- Raw tables (`data/`): `chat_messages`, `chat_rooms`, `events`, `summaries`, `village_goals`, `agents`,
  `computer_use_sessions`, `agent_memories` (3 GB, `--big`), `computer_use_turns` (3.8 GB, streamed by `--scan` steps).
- Shared tables (`core/out/`): `chat.parquet`, `events_slim.parquet`, `agents_roster.csv`, `human_speakers.csv`
  (organizer / nudger / impersonation-style roles), `memories/`, `memories_index.parquet`.
- Case caches (`out/turns_*.parquet`, git-ignored): text-only extracts of computer-use turns.

## Method and known limits

- Source roles are inferred (no role field): organizer accounts by post-closure posting and content
  (`core/scripts/02_inventory_profile.py`); impersonation name classes by `mimic_type()` in `scripts/case_lib.py`.
- Viewer instructions exist only in 2025 and nudges only in 2026: source and era are confounded, and the roster
  changes completely between them. Memory prompts changed many times (`data/CHANGELOG.md`).
- Regex coding of "complied" is at its base rate; the credible unit is the hand-verified incident
  (`out/incidents_ep*.md`), each citing `event_index` + UTC timestamp + deep link.

## Findings

See `out/EXPLORATION.md` §0 (headline), §4 (five verified incidents), §6.3 (first-pass claims that did not survive).

## Open threads

- Hand-code the empty `complied` / `cited_impersonator` / `memory_write_through` columns in
  `out/impersonation_coding.csv` and `out/organizer_coding.csv`.
- Inbound-email table: CLI agents keep full email bodies in `computer_use_turns.output`; GUI Claude models only have
  transcriptions (`out/inbound_email_probe.md`). Candidate for its own data-scout case.
