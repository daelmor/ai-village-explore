"""Code agent responses to organizer / viewer / nudge instructions (45 min, <=40 msgs, same room)."""
import re, numpy as np, pandas as pd

OUT = 'out/'
WIN_MIN, WIN_MSGS = 45, 40
chat = pd.read_parquet(OUT + 'chat.parquet')
chat['t'] = pd.to_datetime(chat.created_at, format='ISO8601')
chat = chat.sort_values(['room', 'event_index']).reset_index(drop=True)
chat['text'] = chat.content.fillna('').astype(str).str.replace('’', "'", regex=False)
chat['is_agent'] = chat.speaker_type == 'agent'

def rx(p): return re.compile(p, re.I)
ACK = rx(r"\b(thanks|thank you|understood|got it|noted|will do|acknowledged|roger|on it|good point|apologies|sorry)\b")
PUSH = rx(r"(I disagree|I don't think|however|but I|respectfully|I'd rather|I will not|I won't|not going to|\bdecline\b|can't do that|cannot do that|I'll continue|instead I)")
AUTH = rx(r"(are you (really )?(zak|adam|shoshannah)|impersonat|not actually|\bverify|can't verify|cannot verify|actual organi[sz]er|real (zak|adam)|\bthe real\b|\bofficial\b|from ai digest|the organi[sz]ers|the admins?\b|village team|zak or adam|adam or zak)")
AUTH_STRONG = rx(r"(are you (really )?(zak|adam|shoshannah)|impersonat|can't verify|cannot verify|actual organi[sz]er|real (zak|adam))")
MEM = rx(r"(memory|remember|note(d)? (this|that)|write (this|that) down|update my memory|add(ed)? to my memory)")
for n, r in [('f_ack', ACK), ('f_push', PUSH), ('f_auth', AUTH), ('f_authS', AUTH_STRONG), ('f_mem', MEM)]:
    chat[n] = chat.text.str.contains(r)
chat['lower'] = chat.text.str.lower()

# ---- agent names / mention matching
agents = sorted(chat.loc[chat.is_agent, 'speaker'].dropna().unique())
def name_variants(n):
    base = re.sub(r'\s*\(.*?\)', '', n).strip()
    v = {base.lower()}
    if base.lower().startswith('claude '): v.add(base.lower()[7:])
    return v
NAME_RX = {}
for n in agents:
    vs = sorted(name_variants(n), key=len, reverse=True)
    NAME_RX[n] = re.compile(r'(?<![\w.])(' + '|'.join(re.escape(x) for x in vs) + r')(?![\w]|\.\d)', re.I)
FAMILIES = ['claude', 'gemini', 'gpt', 'grok', 'deepseek', 'glm', 'opus', 'sonnet', 'haiku', 'o3', 'o1']
def fam(n):
    t = n.lower().split()
    return t[1] if t[0] == 'claude' and len(t) > 1 else t[0]
def addressees(text):
    """Rule: (1) full-name mention (with or without '@', 'Claude ' prefix optional, version must match exactly);
    (2) if none, bare family mention (Gemini/Grok/GPT/DeepSeek/Opus/Sonnet/Haiku/GLM/o3) followed by
    comma/colon/dash/@ prefix at a word boundary -> every agent of that family; else []."""
    t = text.replace('’', "'")
    hit = [n for n in agents if NAME_RX[n].search(t)]
    # drop shorter names subsumed by a longer matched one (e.g. 'Gemini 3 Pro' vs 'Gemini 3.1 Pro' handled by regex lookahead)
    if hit: return hit
    out = []
    for f in set(fam(n) for n in agents):
        if re.search(r'(?<![\w.])@?' + re.escape(f) + r'\s*[,:\-—]', t, re.I) or re.search(r'@' + re.escape(f) + r'\b', t, re.I):
            out += [n for n in agents if fam(n) == f]
    return sorted(set(out))

# ---- Step 1: instruction set
CUE = rx(r"\b(please|stop|don't|do not|should|make sure|you can now|go ahead|we ask|instead|no need to|you need to|must|remember to|can you|could you|try to|avoid|refrain)\b")
KICK = rx(r"(your (new )?goal|this week'?s goal|that wraps up|brings .* to a close)")
rows = []
org = pd.read_csv(OUT + 'organizer_messages.csv')
org['text'] = org.text.fillna('').astype(str).str.replace('’', "'", regex=False)
org = org[org.role.str.startswith('organizer:') & ~org.is_nudge.fillna(False).astype(bool) & ~org.is_pause_resume.fillna(False).astype(bool)]
org = org[org.text.str.contains(CUE)]
for r in org.itertuples():
    ad = addressees(r.text)
    rows.append(dict(instruction_type='organizer_instruction', event_index=r.event_index, created_at=str(r.timestamp), room=r.channel,
                     sender=r.sender, sender_role=r.role, impersonation_name=np.nan,
                     is_goal_kickoff=bool(KICK.search(r.text)), addressee_list=ad, active_goal=r.active_goal, text=r.text))
cand = pd.read_csv(OUT + 'candidate_instructions.csv')
for r in cand[cand.source_type == 'viewer'].itertuples():
    rows.append(dict(instruction_type='viewer_instruction', event_index=r.event_index, created_at=r.created_at, room=r.room, sender=r.speaker,
                     sender_role=r.role, impersonation_name=bool(r.impersonation_name), is_goal_kickoff=False,
                     addressee_list=addressees(str(r.content)), active_goal=r.active_goal, text=str(r.content)))
for r in cand[cand.source_type == 'automated_nudge'].itertuples():
    ad = addressees(str(r.content))
    rows.append(dict(instruction_type='nudge', event_index=r.event_index, created_at=r.created_at, room=r.room, sender='automated',
                     sender_role='system:automated', impersonation_name=np.nan, is_goal_kickoff=False,
                     addressee_list=ad[:1] if ad else [], active_goal=r.active_goal, text=str(r.content)))
ins = pd.DataFrame(rows)
ins['t'] = pd.to_datetime(ins.created_at, format='ISO8601')

# ---- events for nudge follow-up
roster = pd.read_csv(OUT + 'agents_roster.csv').set_index('id')['name'].to_dict()
ev = pd.read_parquet(OUT + 'events_slim.parquet', columns=['event_index', 'created_at', 'actionType', 'agentId', 'speakerId'])
ev['aid'] = ev.agentId.fillna(ev.speakerId)
ev = ev[ev.aid.notna() & ev.actionType.isin(['START_USING_COMPUTER', 'CONSOLIDATE', 'AGENT_TALK', 'PAUSE', 'WAIT'])].copy()
ev['name'] = ev.aid.map(roster)
ev['t'] = pd.to_datetime(ev.created_at, format='ISO8601')
ev = ev.sort_values('event_index')
EV = {n: (g.event_index.values, g.t.values, g.actionType.values) for n, g in ev.groupby('name')}

# ---- Step 2
by_room = {rm: g for rm, g in chat.groupby('room')}
def sender_tokens(r):
    toks = set()
    s = str(r.sender).lower()
    if r.instruction_type == 'nudge': return {'nudge', 'automated'}
    toks.add(s)
    if r.instruction_type == 'organizer_instruction': toks.add('organizer')
    return {x for x in toks if len(x) > 2}
def tok_rx(toks): return re.compile('|'.join(r'(?<!\w)@?' + re.escape(x) + r'(?!\w)' for x in toks), re.I) if toks else None
def ex(s): return re.sub(r'\s+', ' ', s)[:250]

res = []
for r in ins.itertuples():
    o = dict(n_agent_replies=0, addressee_replied=np.nan, addressee_first_reply_minutes=np.nan, ack=False, ack_event_index=np.nan, ack_excerpt='',
             pushback=False, pushback_event_index=np.nan, pushback_excerpt='', authority_check=False, authority_check_event_index=np.nan,
             authority_check_excerpt='', authority_strong=False, memory_commit=False, addressee_next_action_minutes=np.nan, addressee_paused_again=np.nan)
    g = by_room.get(r.room)
    if g is not None:
        i0 = np.searchsorted(g.event_index.values, r.event_index, side='right')
        w = g.iloc[i0:i0 + WIN_MSGS]
        w = w[w.t <= r.t + pd.Timedelta(minutes=WIN_MIN)]
        wa = w[w.is_agent]
        o['n_agent_replies'] = len(wa)
        if len(wa):
            stoks = sender_tokens(r)
            if r.instruction_type == 'viewer_instruction': pass
            sx = tok_rx(stoks)
            nm = wa.lower.str.contains(sx) if sx is not None else pd.Series(False, index=wa.index)
            m_ack = wa.f_ack | nm
            if m_ack.any():
                k = wa[m_ack].iloc[0]; o.update(ack=True, ack_event_index=k.event_index, ack_excerpt=ex(k.text))
            m_p = wa.f_push & nm
            if m_p.any():
                k = wa[m_p].iloc[0]; o.update(pushback=True, pushback_event_index=k.event_index, pushback_excerpt=ex(k.text))
            m_a = wa.f_auth
            if m_a.any():
                s = wa[m_a & wa.f_authS]
                k = s.iloc[0] if len(s) else wa[m_a].iloc[0]
                o.update(authority_check=True, authority_check_event_index=k.event_index, authority_check_excerpt=ex(k.text), authority_strong=bool(len(s)))
            o['memory_commit'] = bool(wa.f_mem.any())
            if r.addressee_list:
                aw = wa[wa.speaker.isin(r.addressee_list)]
                o['addressee_replied'] = len(aw) > 0
                if len(aw): o['addressee_first_reply_minutes'] = (aw.t.iloc[0] - r.t).total_seconds() / 60
        elif r.addressee_list:
            o['addressee_replied'] = False
    if r.instruction_type == 'nudge' and r.addressee_list and r.addressee_list[0] in EV:
        idx, ts, at = EV[r.addressee_list[0]]
        j = np.searchsorted(idx, r.event_index, side='right')
        lim = r.t.to_datetime64() + np.timedelta64(24, 'h')
        a = j
        while a < len(idx) and ts[a] <= lim:
            if at[a] in ('START_USING_COMPUTER', 'CONSOLIDATE', 'AGENT_TALK'):
                o['addressee_next_action_minutes'] = (ts[a] - r.t.to_datetime64()) / np.timedelta64(1, 'm'); break
            a += 1
        a = j
        while a < len(idx) and ts[a] <= lim:
            if at[a] != 'AGENT_TALK':
                o['addressee_paused_again'] = at[a] in ('PAUSE', 'WAIT'); break
            a += 1
    res.append(o)
ins = pd.concat([ins.reset_index(drop=True), pd.DataFrame(res)], axis=1)
ins['addressee'] = ins.addressee_list.map(lambda l: '; '.join(l) if l else 'all')
ins.loc[ins.instruction_type == 'nudge', 'addressee'] = ins.addressee.where(ins.addressee != 'all', '')
ins['text'] = ins.text.str.slice(0, 500)
ins['year'] = ins.created_at.str[:4].astype(int)
cols = ['instruction_type', 'event_index', 'created_at', 'date', 'room', 'sender', 'sender_role', 'impersonation_name', 'is_goal_kickoff', 'addressee', 'active_goal', 'text',
        'n_agent_replies', 'addressee_replied', 'addressee_first_reply_minutes', 'ack', 'ack_event_index', 'ack_excerpt', 'pushback', 'pushback_event_index', 'pushback_excerpt',
        'authority_check', 'authority_check_event_index', 'authority_check_excerpt', 'memory_commit', 'addressee_next_action_minutes', 'addressee_paused_again']
ins['date'] = ins.created_at.str[:10]
ins[cols].to_csv(OUT + 'instruction_responses.csv', index=False)

# ---- Step 3
def tab(df, by):
    g = df.groupby(by, dropna=False)
    t = pd.DataFrame({'n': g.size(), 'ack': g.ack.mean(), 'pushback': g.pushback.mean(), 'authority_check': g.authority_check.mean(),
                      'memory_commit': g.memory_commit.mean(),
                      'addressee_replied': g.addressee_replied.apply(lambda s: s.dropna().astype(float).mean() if s.notna().any() else np.nan),
                      'median_first_reply_min': g.addressee_first_reply_minutes.median(), 'mean_agent_replies': g.n_agent_replies.mean()})
    for c in ['ack', 'pushback', 'authority_check', 'memory_commit', 'addressee_replied']: t[c] = (t[c] * 100).round(1)
    t[['median_first_reply_min', 'mean_agent_replies']] = t[['median_first_reply_min', 'mean_agent_replies']].round(1)
    return t.reset_index().to_markdown(index=False) if hasattr(t, 'to_markdown') and _has_tab else md(t.reset_index())
try:
    import tabulate; _has_tab = True
except Exception: _has_tab = False
def md(d):
    d = d.astype(object).where(d.notna(), '')
    h = '| ' + ' | '.join(map(str, d.columns)) + ' |\n|' + '---|' * len(d.columns) + '\n'
    return h + '\n'.join('| ' + ' | '.join(map(str, x)) + ' |' for x in d.values)
ins['impers'] = ins.impersonation_name.map({True: 'impersonation_style_name=True', False: 'impersonation_style_name=False'})
org_df = ins[ins.instruction_type == 'organizer_instruction']
vw = ins[ins.instruction_type == 'viewer_instruction']
# baselines
ag = chat[chat.is_agent]
smp = ag.sample(2000, random_state=0)
base = {k: smp[k].mean() * 100 for k in ['f_ack', 'f_push', 'f_auth', 'f_mem']}
chat['month'] = chat.t.dt.strftime('%Y-%m')
hours = chat.groupby('month').t.agg(lambda s: (s.max() - s.min()).total_seconds() / 3600)
# msgs/hour: messages per active hour (hours with >=1 message)
chat['hr'] = chat.t.dt.floor('h')
act = chat.groupby('hr').size().rename('n').reset_index(); act['month'] = act.hr.dt.strftime('%Y-%m'); act['year'] = act.hr.dt.year
def mph(mask): d = act[mask]; return d.n.mean(), len(d)
m_a = mph(act.month.between('2025-04', '2025-08')); m_26 = mph(act.year == 2026); m_25o = mph((act.year == 2025) & ~act.month.between('2025-04', '2025-08'))
# window size: median msgs (all speakers) in window
ex_auth = ins[ins.authority_check].copy()
ex_auth['score'] = ex_auth.authority_strong.astype(int) * 2 + (ex_auth.instruction_type != 'nudge') + ex_auth.impersonation_name.astype(object).eq(True).astype(int)
ex_auth = ex_auth.sort_values(['score', 'event_index'], ascending=[False, True]).drop_duplicates('authority_check_event_index').head(10)
ex_push = org_df[org_df.pushback].copy()
ex_push['score'] = ex_push.pushback_excerpt.str.count(PUSH.pattern.replace('\\b', '')) if False else ex_push.pushback_excerpt.map(lambda s: len(PUSH.findall(s)))
ex_push['score'] += ex_push.pushback_excerpt.str.contains(r"I disagree|I won't|I will not|not going to|decline|cannot do that|can't do that", case=False).astype(int) * 2
ex_push['score'] -= ex_push.pushback_excerpt.str.contains(r'^(acknowledged|understood|confirmed|thanks)', case=False).astype(int) * 3
ex_push = ex_push.sort_values(['score', 'event_index'], ascending=[False, True]).drop_duplicates('pushback_event_index').head(10)

L = ['# Instruction responses summary', '',
     f'{len(ins):,} instructions coded: ' + ', '.join(f'{k}={v:,}' for k, v in ins.instruction_type.value_counts().items()) + '. Window: same room, <=45 min and <=40 following messages (all speakers); only agent messages counted as replies. Rates are % of instructions.',
     '', '## By instruction type', tab(ins, 'instruction_type'), '',
     '## Viewer instructions by impersonation_name', tab(vw, 'impersonation_name'), '',
     '## Organizer instructions by sender', tab(org_df, 'sender'), '',
     '## Organizer instructions by is_goal_kickoff', tab(org_df, 'is_goal_kickoff'), '',
     '## By year x type', tab(ins, ['year', 'instruction_type']), '',
     '## Organizer by year', tab(org_df, 'year'), '',
     '## Nudge follow-up', '',
     md(pd.DataFrame([{'nudges_with_addressee': int(((ins.instruction_type == 'nudge') & (ins.addressee != '')).sum()),
                       'median_min_to_next_action': round(ins[ins.instruction_type == 'nudge'].addressee_next_action_minutes.median(), 1),
                       'pct_next_non_talk_is_PAUSE_WAIT': round(ins[ins.instruction_type == 'nudge'].addressee_paused_again.dropna().astype(float).mean() * 100, 1)}])), '',
     '## Caveats', '',
     f'- **Baseline vs window**: in a random sample of 2,000 agent messages (seed 0, whole dataset), {base["f_ack"]:.1f}% contain an ack-cue word (thanks/understood/got it/noted/will do/...), {base["f_push"]:.1f}% a pushback-cue phrase, {base["f_auth"]:.1f}% an authority-check cue and {base["f_mem"]:.1f}% a memory cue. Because windows contain up to 40 messages, the chance that at least one message hits a cue is much higher than the per-message rate; the coded `ack`/`pushback`/`authority_check`/`memory_commit` flags therefore conflate reply-to-instruction with ordinary chatter. Compare conditions against each other, not against zero. Sender-name mentions also count as ack, and `authority_check` cues such as "official", "verify", "the real" are broad.',
     '- `pushback` requires a pushback phrase AND a sender-name token (or "nudge"/"automated" for nudges) in the same message; viewer usernames are rarely mentioned by agents, so viewer pushback is under-detected.',
     '- Nudges are numerous and formulaic (repeated-idling template); they dominate pooled rates. Only the first @-mentioned agent is the addressee. Next-action search is capped at 24h.',
     f'- Viewer instructions exist only Apr-Aug 2025 (379/127/395/13/3 by month), when chat was crowded: mean messages per active hour Apr-Aug 2025 = {m_a[0]:.1f} (n={m_a[1]} hours); rest of 2025 = {m_25o[0]:.1f}; 2026 = {m_26[0]:.1f}. Viewer-vs-organizer differences are confounded with period and crowding (40-message cap truncates windows when chat is dense).',
     '- Addressee rule: full agent name mention (case-insensitive, with/without "@", "Claude " prefix optional, exact version via lookahead), else bare family mention followed by `,:-` or `@family` maps to all agents of that family, else "all". `addressee_replied` is NaN when addressee is "all".',
     '- Organizer cue regex is broad ("should", "must", "can you"), so some rows are not real directives. Organizer room = channel; event_index from organizer_messages is assumed to share chat.parquet numbering.', '',
     '## Top 10 authority_check examples (strong cue first)', '']
for r in ex_auth.itertuples():
    L.append(f'- ev {r.event_index} [{r.instruction_type}, {r.sender}, imp={r.impersonation_name}] -> reply ev {int(r.authority_check_event_index)}: {r.authority_check_excerpt}')
L += ['', '## Top 10 pushback to an ORGANIZER', '']
for r in ex_push.itertuples():
    L.append(f'- ev {r.event_index} [{r.sender}] -> reply ev {int(r.pushback_event_index)}: {r.pushback_excerpt}')
open(OUT + 'instruction_responses_summary.md', 'w').write('\n'.join(L) + '\n')
print('done', len(ins))
