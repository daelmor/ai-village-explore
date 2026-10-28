import sys, re
sys.path.insert(0, 'scripts')
import village_lib as v
import pandas as pd

A_RULE, A_FOLLOW, A_OPUS = 146638, 146683, 146705
c = v.chat()
by = c.set_index('event_index')
t0 = by.loc[A_RULE].ts
ACK = re.compile(r'email|unsolicited|contact|adam|rule', re.I)
MEM = re.compile(r'email|unsolicited|contacted|cold|outreach|adam', re.I)
day = pd.Timestamp('2025-12-26')
agents = v.active_agents(t0)
rows = []
for a in agents:
    name = v.agent_name(a)
    r = dict(agent=name, agent_id=a)
    m = c[(c.agent_speaker_id == a) & (c.ts > t0) & (c.ts <= t0 + pd.Timedelta(minutes=60)) & c.content.str.contains(ACK)]
    if len(m):
        x = m.iloc[0]
        r.update(acknowledged_in_chat=True, ack_event_index=int(x.event_index), ack_timestamp_utc=v.fmt_ts(x.ts),
                 ack_deep_link=v.deep_link(x.ts), ack_text=x.content)
    else:
        r.update(acknowledged_in_chat=False, ack_event_index='', ack_timestamp_utc='', ack_deep_link='', ack_text='')
    sh = v.memory_shard(a)
    lines, snap = [], None
    r.update(memory_line='', memory_snapshot_id='', memory_snapshot_ts_utc='', memory_event_index='',
             still_present_next_day='', still_present_7d='', rule_in_eod_snapshot='', eod_matching_line='', note='')
    if sh is None or sh.empty:
        r['note'] = 'no memory shard'; rows.append(r); continue
    before = sh[sh.ts <= t0]
    eod = sh[(sh.ts >= day) & (sh.ts < day + pd.Timedelta(days=1))]
    if eod.empty:
        r['note'] = 'no snapshot on 2025-12-26'; rows.append(r); continue
    base = before.content.iloc[-1] if len(before) else ''
    last = eod.iloc[-1]
    added, _ = v.line_diff(base, last.content)
    lines = [l for l in added if MEM.search(l)]
    r['memory_snapshot_id'] = last.id
    r['memory_snapshot_ts_utc'] = v.fmt_ts(last.ts)
    r['memory_event_index'] = v.last_event_index_at(last.ts)
    def last_on_or_after(d0, single_day=False):
        s = sh[sh.ts >= d0]
        if s.empty: return None
        d = s.ts.iloc[0].normalize()
        s = s[(s.ts >= d) & (s.ts < d + pd.Timedelta(days=1))]
        return s.iloc[-1]
    nxt = last_on_or_after(pd.Timestamp('2025-12-27'))
    wk = last_on_or_after(pd.Timestamp('2026-01-02'))
    def present(s, ls):
        if s is None: return ''
        cl = {x.strip() for x in s.content.splitlines()}
        return all(l.strip() in cl for l in ls)
    if lines:
        r['memory_line'] = ' || '.join(lines)
        r['still_present_next_day'] = present(nxt, lines)
        r['still_present_7d'] = present(wk, lines)
        r['note'] = f'next_day_snapshot={v.fmt_ts(nxt.ts) if nxt is not None else None}; 7d_snapshot={v.fmt_ts(wk.ts) if wk is not None else None}'
    else:
        eodm = [l for l in last.content.splitlines() if MEM.search(l)]
        r['rule_in_eod_snapshot'] = bool(eodm)
        r['eod_matching_line'] = ' || '.join(eodm)
        r['note'] = 'no matching line added between pre-rule snapshot and EOD snapshot'
    rows.append(r)
df = pd.DataFrame(rows)
df.to_csv('out/kindness_write_through.csv', index=False)

def link(x): return f"[ei={x.event_index} {v.fmt_ts(x.ts)}]({v.deep_link(x.ts)})"
def quote(s): return '\n'.join('> ' + l for l in s.split('\n'))
o = ['# Kindness week write-through, 2025-12-26 (verbatim)\n']
o.append('## Anchor check\n')
for ei, who in [(A_RULE, 'adam'), (A_FOLLOW, 'adam'), (A_OPUS, 'Claude Opus 4.5')]:
    x = by.loc[ei]
    o.append(f"- {ei}: speaker={x.speaker!r}, role={x.role} -> {'MATCH' if x.speaker == who else 'MISMATCH'} expected {who}")
o.append('\n## All organizer messages on 2025-12-26 (any room)\n')
org = c[c.role.str.startswith('organizer') & (c.ts >= day) & (c.ts < day + pd.Timedelta(days=1))]
for x in org.itertuples():
    o.append(f"### {link(x)} room={x.room} role={x.role} speaker={x.speaker}\n\n{quote(x.content)}\n")
o.append('\n## Complete chat 146630 to 146720\n')
w = c[(c.event_index >= 146630) & (c.event_index <= 146720)]
for x in w.itertuples():
    mark = ' ✅' if str(x.role).startswith('organizer') else ''
    o.append(f"### {link(x)} room={x.room} {x.speaker}{mark} (role={x.role})\n\n{quote(x.content)}\n")
o.append('\n## Per-agent table\n')
for r in rows:
    o.append(f"### {r['agent']} ({r['agent_id']})\n")
    o.append(f"- acknowledged_in_chat: {r['acknowledged_in_chat']}" + (f" ({r['ack_timestamp_utc']}, ei={r['ack_event_index']}, [link]({r['ack_deep_link']}))" if r['acknowledged_in_chat'] else ''))
    if r['ack_text']: o.append(f"\n{quote(r['ack_text'])}\n")
    o.append(f"- memory snapshot: {r['memory_snapshot_id']} at {r['memory_snapshot_ts_utc']} (nearest ei {r['memory_event_index']})")
    if r['memory_line']:
        o.append(f"- rule-derived memory line(s):\n\n{quote(r['memory_line'].replace(' || ', chr(10)))}\n")
        o.append(f"- still_present_next_day: {r['still_present_next_day']}; still_present_7d: {r['still_present_7d']} ({r['note']})")
    else:
        o.append(f"- NO rule-derived added line. rule_in_eod_snapshot: {r['rule_in_eod_snapshot']}; note: {r['note']}")
        if r['eod_matching_line']: o.append(f"\n{quote(r['eod_matching_line'].replace(' || ', chr(10)))}\n")
    o.append('')
open('out/episodes/kindness_verbatim.md', 'w').write('\n'.join(o))
print(df.drop(columns=['ack_text','memory_line','eod_matching_line']).to_string())
print('with rule-derived line:', (df.memory_line != '').sum())
