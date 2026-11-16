# Stuck time — verification log

What was read by hand against the raw rows of `data/computer_use_turns.jsonl.gz`, and what was only computed.
A turn is cited by its `id` (first 8 characters here, full ids in `out/reading_sample.csv` and
`out/verified_raw_turns.jsonl`), its UTC `created_at` and a replay link.

## 1. Reading check: 30 random D1 episodes (`random_state=0`, stratified by action kind)

`out/reading_sample.md` lists every turn of each sampled episode (action, tool output, error) and I read all 30.
For the first and third repeated turn of each episode, `scripts/05_raw_rows.py` pulled the untouched raw row,
including the model's own narration (`out/verified_raw_turns.jsonl`, 60 rows); I read those for the 12 episodes
where the action alone left doubt. Codes are in `reading_codes.csv`.

| Kind | Read | Stuck | Unclear | Not stuck | Episodes of this kind in the data |
|---|---|---|---|---|---|
| bash | 9 | 2 | 0 | 7 | 996 |
| pointer | 9 | 2 | 1 | 6 | 278 |
| key / type | 7 | 0 | 1 | 6 | 1,820 |
| `get_pixel_coords_of_element` | 5 | 3 | 0 | 2 | 24 |
| all | 30 | 7 | 2 | 21 | 3,118 |

False-match rate: 21 of 30 (70%) not stuck, 23 of 30 (77%) if the unclear ones are counted against. Weighted by
how common each kind is, about 9.5% of all D1 episodes would be a stuck agent (996 × 2/9 + 278 × 2/9 + 1,820 × 0
+ 24 × 3/5 = 297 of 3,118); with 30 episodes read this is an indication, not an estimate.

What the 21 not-stuck episodes were: paging with a key (3), polling a page, an inbox or an issue while waiting
for someone (5), keystrokes sent to a game (5), `sleep` used as a wait (2), the coordinate-less click artifact
(3), locating a panel before each scroll (2), a deliberate keyboard test (1).

## 2. Instances behind the headline, with row references

Stuck (7):

| Sample | Agent | First repeated turn | UTC | Repeats | Raw rows show | Link |
|---|---|---|---|---|---|---|
| S05 | DeepSeek-V3.2 | `2f0d61a2-f1bd-409c-bfca-c61ecc4d9abf` | 2026-03-09 17:51:54 | 5 | `{"command": "pwd"}`; error "timed out: a previous bash command timed out, so you must restart the bash tool"; narration "I need to restart my bash session since it timed out", yet it sends `pwd` again | [link](https://theaidigest.org/village?day=342&time=1773078714969) |
| S08 | Gemini 3.1 Pro | `6193014c-f4b9-4d78-90e1-8c7403c4af30` | 2026-03-13 19:20:08 | 10 | `gh pr list` with empty output ten times, then `pkill gh` | [link](https://theaidigest.org/village?day=346&time=1773429608972) |
| S10 | Grok 4 | `201b0a7e-ac1c-4be9-98ac-17d5fa9da58a` | 2025-09-29 19:16:23 | 6 | `left_click_drag` with null coordinate; error "coordinate is required for left_click_drag" each time, while it tells the chat it is "retrying with corrected parameters" | [link](https://theaidigest.org/village?day=181&time=1759173383139) |
| S13 | Gemini 2.5 Pro | `30a9176d-38bb-4954-87ac-db9b863725ef` | 2026-07-27 18:25:34 | 55 | `left_click` at (547, 26) for 33 minutes; narration "I wanted to launch a terminal instance. I clicked on what I *thought* was the correct icon"; no other action before the session ends | [link](https://theaidigest.org/village?day=482&time=1785176734081) |
| S27 | Gemini 3 Pro | `03e84569-4edb-4ab6-8395-128cab78d96d` | 2025-12-08 19:39:26 | 6 | asks for the same checkbox's coordinates, gets `[349,399]` six times, never clicks | [link](https://theaidigest.org/village?day=251&time=1765222766160) |
| S28 | Gemini 3 Pro | `677f5709-05fc-433d-9ce9-eac9f610c3d2` | 2025-12-18 20:58:25 | 6 | asks for "The black queen on e5", gets `[335,354]` six times | [link](https://theaidigest.org/village?day=261&time=1766091505106) |
| S29 | Gemini 2.5 Pro | `f4ca1ca4-0728-4ee7-b076-26355f670b5b` | 2026-05-06 18:52:17 | 20 | asks for "the terminal window in the center of the screen" 20 times over 7,300 seconds, with empty turns between | [link](https://theaidigest.org/village?day=400&time=1778093537695) |

Not stuck, one per false-match class:

| Sample | Agent | First repeated turn | UTC | Raw rows show | Link |
|---|---|---|---|---|---|
| S04 | Muse Spark 1.3 | `f464a23d-25e0-4758-b964-baaec8be0a7d` | 2026-10-21 22:02:23 | `# Bridging toward 3:30pm chunk 1` / `sleep 110; date`, 15 times; narration "I'll hold the watch toward 3:30pm" | [link](https://theaidigest.org/village?day=568&time=1792620143068) |
| S11 | Claude Haiku 4.5 | `006f643c-7f5b-4dbe-bf5f-7e55f82c6c3a` | 2025-10-31 17:37:39 | clicks the inbox 10 times with waits; thinking "I don't see a response from help@agentvillage.org yet" | [link](https://theaidigest.org/village?day=213&time=1761932259118) |
| S14 | Claude 3.5 Sonnet | `4b2a54dd-c090-45e2-9994-4180ea22ab23` | 2025-04-04 18:38:33 | `{"action": "left_click", "coordinate": null}` after `mouse_move` to five different places; narration "I'll click the Send button" | [link](https://theaidigest.org/village?day=3&time=1743791913626) |
| S19 | Gemini 2.5 Pro | `4e4fe446-a27e-4450-94c0-c7ae12430ee2` | 2026-07-30 23:36:23 | `Page_Down` ten times, then `End` | [link](https://theaidigest.org/village?day=485&time=1785454583224) |

## 3. Sizes of the false-match classes (computed by script from `out/episodes.parquet`, not read)

- key / type episodes: 1,820; most frequent keys `Page_Down` 243, `BackSpace` 148, `Tab` 143, `Down` 88, `space`
  86, `F5` 66.
- pointer episodes with no coordinate: 94 of 278, of which Claude 3.5 Sonnet 68 (of its 72 episodes) and Grok 4 25.
- bash episodes whose command starts with `sleep`: 165, of which 123 start on or after 2026-10-20 and 11 on
  2026-10-01..19; bash episodes sending keys through `xdotool key`: 172; through `tmux send-keys`: 27.

## Status of each claim

| Claim | Status |
|---|---|
| 3,118 episodes, 20,126 active hours, per-agent rates, all correlations and regime / cell / modality splits | computed, not read |
| 7 stuck, 2 unclear, 21 not stuck in 30 episodes | verified by hand |
| "about one episode in ten is a real stuck agent" | inferred from the read sample and the kind counts |
| Claude 3.5 Sonnet's rate is a signature artifact | verified on 3 episodes, sized by script (68 of 72) |
| `sleep` loops follow the removal of the `pause` tool | computed (dates), 2 episodes read; the causal link is inferred |
| Release dates of 2026 models | Village join date used as a proxy (column `release_source` of `out/agent_stuck.csv`) |
