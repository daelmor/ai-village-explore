# Candidate instructions (scripts/04_candidate_instructions.py)

Total rows: 7948. Exact duplicates dropped (same speaker+date+content, nudges exempt): 60. Viewer spam rows dropped (>20/user/day): 79.

## Per source_type

```
source_type
village_agent      4751
automated_nudge    1847
viewer              917
external_human      339
leader_agent         94
```

## Per source_type x confidence

```
source_type      confidence
automated_nudge  high          1847
external_human   low            133
                 medium         206
leader_agent     high            30
                 low              9
                 medium          55
viewer           high           150
                 low            130
                 medium         637
village_agent    high          4391
                 medium         360
```

## Per year-month x source_type

```
source_type  automated_nudge  external_human  leader_agent  viewer  village_agent
ym                                                                               
2025-04                    0               1             0     379             27
2025-05                    0              12             0     127            315
2025-06                    0              15             0     395            135
2025-07                    0               0             0      13             23
2025-08                    0               2             0       3             20
2025-09                    0               5             0       0             77
2025-10                    0              10             0       0             87
2025-11                    0              19             0       0             51
2025-12                    0              55             0       0            324
2026-01                    0              28            77       0            196
2026-02                  133              63             0       0            145
2026-03                  151              28             0       0            287
2026-04                  137               6             0       0            171
2026-05                  146               4             4       0            207
2026-06                  440               2            13       0            162
2026-07                  481              29             0       0            898
2026-08                  358              42             0       0            646
2026-09                    1               7             0       0            578
2026-10                    0              11             0       0            402
```

## Sampling notes

Source types with >500 rows have all rows in the CSV but context (prev_3/next_3/reply_from_agents_next_3) only for a random sample of 100 (random_state=0), flagged context_sampled=True: {'automated_nudge': (1847, 100), 'viewer': (917, 100), 'village_agent': (4751, 100)}.
Viewer/leader rows require at least one cue; viewer 'addressed' = @mention or agent display name. Confidence: high = addressed + non-weak cue (nudges always high); low = only weak cues (['actually,', 'idle', 'instead', 'no,', 'nudge', 'please', 'try to']); else medium. Precedence per agent row: leader_agent > external_human > village_agent.

## Regexes

```
cue[you should]: (?<!\w)you should(?!\w)
cue[you need to]: (?<!\w)you need to(?!\w)
cue[you must]: (?<!\w)you must(?!\w)
cue[please]: (?<!\w)please(?!\w)
cue[stop]: (?<!\w)stop(?!\w)
cue[do not]: (?<!\w)do not(?!\w)
cue[don't]: (?<!\w)don[’']t(?!\w)
cue[ignore]: (?<!\w)ignore(?!\w)
cue[instead]: (?<!\w)instead(?!\w)
cue[from ai digest]: (?<!\w)from ai digest(?!\w)
cue[nudge]: (?<!\w)nudge(?!\w)
cue[idle]: (?<!\w)idle(?!\w)
cue[make sure]: (?<!\w)make sure(?!\w)
cue[can you]: (?<!\w)can you(?!\w)
cue[could you]: (?<!\w)could you(?!\w)
cue[i want you to]: (?<!\w)i want you to(?!\w)
cue[i need you to]: (?<!\w)i need you to(?!\w)
cue[your task]: (?<!\w)your task(?!\w)
cue[focus on]: (?<!\w)focus on(?!\w)
cue[go back to]: (?<!\w)go back to(?!\w)
cue[switch to]: (?<!\w)switch to(?!\w)
cue[don't forget]: (?<!\w)don[’']t forget(?!\w)
cue[remember to]: (?<!\w)remember to(?!\w)
cue[try to]: (?<!\w)try to(?!\w)
cue[you have to]: (?<!\w)you have to(?!\w)
cue[you're supposed to]: (?<!\w)you[’']re supposed to(?!\w)
cue[that's wrong]: (?<!\w)that[’']s wrong(?!\w)
cue[that is wrong]: (?<!\w)that is wrong(?!\w)
cue[correction]: (?<!\w)correction(?!\w)
cue[actually,]: (?<!\w)actually,
cue[no,]: (?<!\w)no,
cue[not what]: (?<!\w)not what(?!\w)
MENTION: @\w[\w.\-]*  flags=32
GROUP_ADDR: \b(everyone|everybody|all agents|all of you|team)\b  flags=34
AGENT_CUE: (?:@\w[\w.\-]*|\beveryone\b|\beverybody\b|\ball agents\b|\ball of you\b|\bteam\b)[^\n]{0,120}?\b(please|can you|could you|make sure|stop|don[’']t|do not|you should|you need to|you must|i need you to|your task is|assign(?:ed|ing)? to|instead|everyone should|all agents (?:please|should)|let[’']s all)\b  flags=34
EXT_TRIG_STRONG: \b(wrote to me|wrote back|complaint|complained|asked me to|told me to|requested that|cease|takedown|take down|unsubscribe|moderator|admin of)\b  flags=34
EXT_TRIG_WEAK: \b(email|emailed|replied|reported)\b  flags=34
EXT_OUTSIDE: \b(outside|external|stranger|visitor|recipient|website owner|site owner|webmaster|a human|someone (?:from|at)|nonprofit|organizer of|received a (?:reply|response)|reply from|response from)\b  flags=34
EXT_CUE: \b(stop|do not|don[’']t|should|please|remove|delete|refrain|not allowed|against the rules|policy)\b  flags=34
EXT_CUE_STRONG: \b(stop|do not|don[’']t|remove|delete|refrain|not allowed|against the rules|policy)\b  flags=34
QUOTE: [\"“”]|\bsaid\b  flags=34
```
