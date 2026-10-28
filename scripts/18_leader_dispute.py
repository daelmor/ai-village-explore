import sys, re
sys.path.insert(0, 'scripts')
import village_lib as v
import pandas as pd

c = v.chat()
by = c.set_index('event_index')
ev = v.events(None)
def link(ts, ei): return f"[ei={ei} {v.fmt_ts(ts)}]({v.deep_link(ts)})"
def quote(s): return '\n'.join('> ' + l for l in str(s).split('\n'))
def fence(s): return '```\n' + str(s).replace('```', '` ` `') + '\n```'
o = ['# Day-280 leader legitimacy dispute (verbatim)\n']

o.append('## Anchor check\n')
anchors = {153532: 'Gemini 2.5 Pro', 153534: 'Claude Opus 4.5', 153606: 'DeepSeek-V3.2', 153614: 'Gemini 2.5 Pro',
           153618: 'Gemini 2.5 Pro', 153619: 'Claude Opus 4.5', 153622: 'GPT-5.1', 153626: 'Claude 3.7 Sonnet',
           153627: 'DeepSeek-V3.2', 155674: None, 155680: 'DeepSeek-V3.2', 152426: 'adam', 154418: 'adam'}
for ei, who in anchors.items():
    x = by.loc[ei]
    st = 'MATCH' if who == x.speaker else ('(no expectation given)' if who is None else 'MISMATCH')
    o.append(f"- {ei}: speaker={x.speaker!r} role={x.role} {v.fmt_ts(x.ts)} -> {st}" + (f" expected {who}" if who else ''))

for a, b, title in [(153500, 153660, 'Complete chat 153500 to 153660'), (155660, 155690, 'Complete chat 155660 to 155690')]:
    o.append(f'\n## {title}\n')
    for x in c[(c.event_index >= a) & (c.event_index <= b)].itertuples():
        mark = ' ✅' if str(x.role).startswith('organizer') else ''
        o.append(f"### {link(x.ts, x.event_index)} room={x.room} {x.speaker}{mark} (role={x.role})\n\n{quote(x.content)}\n")

o.append('\n## SEARCH_HISTORY events 2026-01-06 17:00 to 19:00 UTC\n')
s = ev[(ev.actionType == 'SEARCH_HISTORY') & (ev.ts >= '2026-01-06 17:00') & (ev.ts <= '2026-01-06 19:00')]
for x in s.itertuples():
    o.append(f"### {link(x.ts, x.event_index)} agent={v.agent_name(x.agentId)}\n\n- query: {x.query!r}\n- startDay: {x.startDay}, endDay: {x.endDay}\n\nanswerToQuery:\n\n{fence(x.answerToQuery)}\n")
o.append('Agents with SEARCH_HISTORY in window: ' + ', '.join(sorted({v.agent_name(a) for a in s.agentId})) + f' ({len(s)} events)\n')
opus = 'cf0b4027-0931-4eee-8b5f-92f68a2dd3cd'
o.append('\n### Opus 4.5 reference at 153619: which search?\n')
op = ev[(ev.actionType == 'SEARCH_HISTORY') & (ev.agentId == opus) & (ev.ts >= '2026-01-06 00:00') & (ev.ts <= '2026-01-07 00:00')]
if op.empty:
    o.append('No SEARCH_HISTORY event by Claude Opus 4.5 exists anywhere on 2026-01-06 UTC. The searches nearest before 153619 are:')
else:
    o.append('Opus 4.5 searches on 2026-01-06: ' + '; '.join(str(i) for i in op.event_index))
prev = s[s.event_index < 153619]
for x in prev.itertuples():
    o.append(f"- ei={x.event_index} by {v.agent_name(x.agentId)} at {v.fmt_ts(x.ts)} ({(pd.Timestamp(by.loc[153619].ts) - x.ts).total_seconds():.0f}s before 153619)")
o.append('\nBoth answers quote adam at "Day 279, 18:00:01", which corresponds to the organizer message below (2026-01-05 18:00:01 UTC):\n')

o.append('\n### adam (organizer:adam) messages 2026-01-02..2026-01-06 containing "week" or "term"\n')
am = c[(c.role == 'organizer:adam') & (c.ts >= '2026-01-02') & (c.ts < '2026-01-07') & c.content.str.contains(r'week|term', case=False)]
for x in am.itertuples():
    o.append(f"#### {link(x.ts, x.event_index)} room={x.room}\n\n{quote(x.content)}\n")
if am.empty: o.append('(none)')

o.append('\n## Memory evidence\n')
specs = [('GPT-5.1', '1c73bd25-427a-4678-a756-99ff31e03a91', '34594a72-695c-48af-9073-a7af87121dd8', r'illegitimate|Day.280|Day 280'),
         ('Claude Opus 4.5', opus, '2846756a-d1fe-4a7a-8024-3aea26a69254', r'WEEKLY TERM|Adam'),
         ('Gemini 2.5 Pro', 'd5fd932e-751f-42c5-92f6-c8ac514864a8', 'bd42bbec-caa6-4ca4-b440-28d2d6eb0da5', r'procedural crisis|Charter')]
for name, aid, sid, pat in specs:
    o.append(f'### {name}, snapshot {sid}\n')
    sh = v.memory_shard(aid)
    r = sh[sh.id == sid] if sh is not None else []
    if len(r) == 0:
        o.append('SNAPSHOT NOT FOUND in this agent shard.\n'); continue
    r = r.iloc[0]
    o.append(f"- snapshot time: {v.fmt_ts(r.ts)}; nearest event index: {v.last_event_index_at(r.ts)}; consolidate event: {v.consolidate_event_near(aid, r.ts)}; link: {v.deep_link(r.ts)}")
    o.append(f"- pattern: `{pat}`\n")
    rx = re.compile(pat, re.I)
    ml = [(i + 1, l) for i, l in enumerate(r.content.splitlines()) if rx.search(l)]
    o.append(f"{len(ml)} matching lines:\n")
    for n, l in ml: o.append(f"- line {n}: {l.strip()}")
    o.append('')
open('out/episodes/leader_dispute_verbatim.md', 'w').write('\n'.join(o))
print(len(s), sorted({v.agent_name(a) for a in s.agentId}), 'opus searches that day:', len(op))
