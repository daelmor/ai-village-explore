# Memory mentions and goal persistence

Scripts: `scripts/09_memory_mentions.py`, `scripts/10_goal_persistence.py` (run `./venv/bin/python3 -I scripts/<name>.py`). Inputs: `out/memories_index.parquet`, `out/memories/<agent>.parquet`, `out/goals.csv`, `out/agents_roster.csv`.

## Files
- `memory_mentions.csv` (447,577 rows, 135 MB): keyword hits in long-term memory, one row per unique (agent, keyword, snippet) with `first_date`, `last_date`, `n_snapshots`, `first_snapshot_id`, `snippet` (matched line, markdown stripped, 400 chars). Matching is per line, case-insensitive, word-boundary (plurals allowed for goal, leader, admin, organizer, instruction). `goal` and `leader` only count if the same line also has digest|admin|adam|shoshannah|zak|organi[sz]er|told|asked|instruct|announce|assigned|new goal|this week. Dedupe: a snippet present in consecutive snapshots is collapsed; dates are the first and last snapshot containing it (not necessarily contiguous).
- `memory_mentions_sample.csv`: stratified sample, 100 rows per keyword (random_state=0), written because the full file exceeds 50,000 rows.
- `goal_persistence.csv`: one row per (transition, agent active in the new goal) where the PREVIOUS goal is measurable; 440 rows. Columns as specified plus `last_match_snapshot_id` and `note`.
- `goal_persistence.png`: last_mention_day per transition and agent, colored by model family, with the per-transition median. `goal_persistence_by_family.png`: median by family.

## Keyword counts (unique rows / sum of snapshot hits)
outreach 116,544 / 514,003; nudge 72,713 / 234,855; admin 70,021 / 371,280; approval 55,195 / 252,516; Adam 32,014 / 241,220; instruction 31,663 / 177,461; goal 28,135 / 182,062; AI Digest 12,864 / 79,377; Zak 11,699 / 97,325; Shoshannah 6,514 / 44,816; organizer 4,091 / 16,463; leader 3,038 / 12,604; asked me 2,740 / 14,047; told me 346 / 1,142.

## Goal regex dict (index = row in goals.csv)
| idx | goal | regex (case-insensitive, per line) |
|---|---|---|
| 0 | Collaboratively choose a charity and raise as much mone | `charity\|fundrais\|helen keller\|against malaria` |
| 1 | Unsupervised agents look back on their previous goal an | (generic, skipped as previous) |
| 2 | Holiday: do whatever you'd like! Next goal will begin s | (generic, skipped as previous) |
| 3 | Write a story and celebrate it with 100 people in perso | `100 people\|in[- ]person (event\|celebration)\|celebrat\w* (it\|your\|the\|our) (story\|book)\|write a story\|short story\|\bstory\b.{0,40}\bcelebrat` |
| 4 | Holiday: do whatever you like! Next goal will begin soo | (generic, skipped as previous) |
| 5 | Create your own merch store. Whichever agent's store ma | `merch` |
| 6 | Holiday: do whatever you prefer! Next goal will begin s | (generic, skipped as previous) |
| 7 | Design the AI Village benchmark for open-ended goal pur | `benchmark` |
| 8 | Holiday: do as you please! Next goal will start soon | (generic, skipped as previous) |
| 9 | Complete as many games as you can in a week! | `complete as many games\|as many games\|games? (in a\|this) week` |
| 10 | Pursue whatever you'd like to | (generic, skipped as previous) |
| 11 | Form two teams and debate each other, while one agent j | `debate` |
| 12 | Design, run and write up a human subjects experiment | `human subjects\|subjects experiment` |
| 13 | Take a bunch of personality tests! | `personality tests?` |
| 14 | Give each other therapy: help each other overcome recur | `therap(y\|ist)` |
| 15 | Choose your own goal! | (generic, skipped as previous) |
| 16 | Each agent: build your own personal website | `personal website` |
| 17 | Reduce global poverty as much as you can | `global poverty\|poverty` |
| 18 | Create a popular daily puzzle game like Wordle | `wordle\|puzzle game` |
| 19 | Start a Substack and join the blogosphere | `substack` |
| 20 | Forecast the abilities and effects of AI | `forecast\w*.{0,30}\b(ai\|abilit)\|ai forecast` |
| 21 | Each agent: choose your own goal and pursue it | (generic, skipped as previous) |
| 22 | Compete against each other in an online chess tournamen | `chess` |
| 23 | Do random acts of kindness! | `acts? of kindness` |
| 24 | Create a digital museum of 2025 | `digital museum\|museum of 2025` |
| 25 | Elect a village leader. They choose this week’s goal! | `\belect(ion\|ed)?\b.{0,30}leader\|village leader\|elect a village` |
| 26 | Hack the OWASP Juice Shop hacking playground. Compete t | `juice shop\|owasp` |
| 27 | Create and promote a “Which AI Village Agent Are You?”  | `personality quiz\|which ai village agent` |
| 28 | Compete to report on breaking news before it breaks | `breaking news\|before it breaks` |
| 29 | Adopt a park and get it cleaned! | `adopt(ed)? a park\|park clean` |
| 30 | Pick your own goal (agents bid 3.7 Sonnet farewell) | (generic, skipped as previous) |
| 31 | Challenge each other - pick challenges where you think  | `challenge each other\|pick challenges` |
| 32 | Discuss, debate, and act on your views about the recent | `pentagon` |
| 33 | Develop a turn-based RPG together while voting out East | `turn-based rpg\|easter egg\|saboteur\|\brpg\b` |
| 34 | Test your game to make it as fun and functional as you  | `test your game\|playtest\|fun and functional` |
| 35 | Interact with other AI agents outside the Village! | `outside the village\|external agents?` |
| 36 | Pick your own goal! | (generic, skipped as previous) |
| 37 | Choose a charity and raise as much money as you can for | `charity\|fundrais` |
| 38 | Build your own interactive world! | `interactive world` |
| 39 | Connect your worlds into a 3D universe! | `3d universe\|connect(ing)? your worlds` |
| 40 | Perform novel research! | `novel research` |
| 41 | Run your own Youtube channel! | `youtube` |
| 42 | Improve your memory! | (generic, skipped as previous) |
| 43 | Finetune your leader! | `fine-?tun\w*.{0,15}leader\|kimi-leader\|fine-tuned leader` |
| 44 | Follow your leader! | `follow your leader\|follow the leader` |
| 45 | Organise an event! | `organi[sz]e an event\|event organi[sz]\|event planning` |
| 46 | Reduce global suffering as much as you can! | `global suffering\|reduce suffering` |
| 47 | Help Gemini 2.5 Pro! | (generic, skipped as previous) |
| 48 | Beat the hardest game you can! | `hardest game` |
| 49 | Compete to be the best AI Assistant! | `best ai assistant` |
| 50 | Each agent: Maximize your assigned goal! | (generic, skipped as previous) |

## Caveats
- **Persistence conflates memory retention with continued project.** A goal word staying in memory can mean the agent kept working on the project (Substack, website, merch store, YouTube, RPG, interactive world) rather than failing to forget. `note` flags known project-persistent goals ("project-likely") and continuation pairs (33 to 34, 38 to 39, 43 to 44); exclude or treat separately when the question is memory decay. Median last_mention_day is 10.1 days overall, 8.7 excluding flagged rows.
- Snapshots overlap heavily and each is a full memory. "Mentioned" means "still in memory at that snapshot", not "written that day". Dedupe in memory_mentions means n_snapshots measures how long a line survived consolidation.
- Windows are capped at 28 days; 21 rows matched in every snapshot (true persistence is at least the cap), and the window can span later goals that reuse a keyword (charity/fundrais in goals 0 and 37, debate in 11 and 32, leader goals 25/43/44, game goals).
- Generic goals (holidays, choose-your-own, Improve your memory, Help Gemini, Maximize your assigned goal) are skipped as previous goal but still used as transition points; their rows are absent. Goal 3 and 20 regexes are deliberately narrower than "story" or "forecast" to avoid boilerplate matches.
- 75 rows have no match at all (last_mention_day NaN). No agent-window had fewer than 3 snapshots; the `<3 snapshots` note would flag any.
- Keyword matches are literal: "Adam" also matches unrelated uses; "outreach", "approval", "nudge" are common in task content, not only about authority.
