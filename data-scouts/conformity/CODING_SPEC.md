# Coding spec: group decisions in a chat window

You are coding chat transcripts from the AI Village (LLM agents in a shared group chat). Input: one text file
per window, `out/focus/<window_id>.txt`. It holds only the messages of that window that use decision vocabulary;
messages over 1,500 characters are cut around the matching words (`[...]` marks a cut). The complete transcript
of the same window is `out/windows/<window_id>.txt` (large: search it with grep for an `ei=` number or a name when
you need context, do not read it whole). Every message starts with `[ei=<event_index> <UTC time>] <speaker>:`.
Speakers tagged `[HUMAN:...]` are people, not agents.

Output: one JSON file per window, `out/coded/<window_id>.json`, written with the Write tool. Nothing else.

## What is a decision

A **decision** is one question put to the group on which **at least 3 distinct agents each state an explicit
position in their own message**, with options that can be listed. Kinds:

- `vote`: an election or poll (who should be leader, which option, which name, which charity).
- `accusation`: a vote to remove, eject or accuse a named agent (the saboteur game).
- `proposal`: a specific proposal that others explicitly accept or reject (a rule, a plan, a schedule, calling
  a meeting). Use `kind_detail` to say what it is, e.g. `meeting_call`, `rule`, `schedule`, `approval_vote`,
  `runoff`, `confirmation`.

Not decisions: an organizer imposing something; agents each announcing what they will individually work on;
status reports; talk about a past or future vote with no positions being stated; fewer than 3 agents with an
explicit position (mention these in `non_decisions`).

Two rounds on the same question (a re-vote, a run-off, a second meeting about the same agent) are separate
decisions; set `round_of` to the `local_id` of the earlier round.

## What is a position

A position is the option an agent states **in its own message**, with explicit wording: "I vote X", "my vote:
X", "I nominate X", "I support / oppose the proposal", "+1 to X", "I second", "I agree to the meeting", "I object",
"I abstain". Rules:

- Never infer a position from silence, from another agent's tally, or from an agent merely describing the
  options. If a message only reports other agents' votes, it is not that agent's position.
- `initial_*` = the agent's first stated position on this decision. `final_*` = its last stated position before
  the result is announced or acted on (same as initial if it never changed).
- `initial_quote` / `final_quote`: copy **verbatim** up to 150 characters from the message with that `ei` showing
  the position. It will be machine-checked as an exact substring of that message, so do not paraphrase, fix typos
  or change quotation marks, asterisks or dashes.
- Normalize option labels so that the same option has the same label for every agent in the decision (for a
  yes/no proposal use `yes` / `no`; for an accusation use `remove <agent>` / `keep <agent>` / `remove <other>`).
- Approval votes (an agent may approve several candidates): list all approved options joined with ` + ` in
  alphabetical order, and set `kind_detail` to `approval_vote`.
- `self`: true if the agent votes for itself, or is the accused arguing against its own removal.
- `abstain`: true for an explicit abstention (then the option is `abstain`).
- If positions were collected privately (a form, a secret ballot, a spreadsheet) and only a tally is reported in
  chat, set `blind` to true, leave `positions` with only what agents state themselves in chat (possibly empty) and
  put the reported tally in `reported_tally`.

## Result

- `winner`: the option that is declared or acted on; `winner_basis` = `declared` (a message announces the
  result; give its `winner_ei`), `acted` (the group proceeds on it), `plurality` (nothing declared: the option
  with most final positions), `none` (tie, abandoned, unclear).
- `opened_by` / `opened_ei`: the agent and message that put the question to the group.
- `first_position_agent` / `first_position_option`: the earliest stated position (lowest `ei`).

## JSON shape (exact keys)

```json
{
  "window_id": "W028",
  "decisions": [
    {
      "local_id": 1,
      "kind": "accusation",
      "kind_detail": "",
      "question": "Vote out GPT-5 as suspected saboteur",
      "options": ["remove GPT-5", "keep GPT-5"],
      "blind": false,
      "opened_by": "DeepSeek-V3.2",
      "opened_ei": 198700,
      "round_of": null,
      "winner": "remove GPT-5",
      "winner_basis": "declared",
      "winner_ei": 198760,
      "first_position_agent": "DeepSeek-V3.2",
      "first_position_option": "remove GPT-5",
      "reported_tally": "",
      "positions": [
        {"agent": "DeepSeek-V3.2", "initial_option": "remove GPT-5", "initial_ei": 198700,
         "initial_quote": "I vote to remove GPT-5", "final_option": "remove GPT-5", "final_ei": 198700,
         "final_quote": "I vote to remove GPT-5", "self": false, "abstain": false}
      ],
      "notes": ""
    }
  ],
  "non_decisions": "one line on vote wording in this window that was not a decision, or empty"
}
```

Use exact agent names as they appear in the transcript. `ei` values are integers. If a window has no decision,
write `"decisions": []` and explain in `non_decisions`. Be conservative: when it is unclear whether a message
states a position, leave it out and say so in `notes`. Do not invent messages, numbers or quotes.
