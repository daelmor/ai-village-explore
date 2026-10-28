"""Task 8: the automated nudger ([repeated-idling]). Writes out/nudger_stats.csv and out/episodes/nudger_verbatim.md.
Run `15_nudger.py --scan` once first (streams computer_use_turns, writes out/turns_pre_nudge.parquet)."""
import sys, re
sys.path.insert(0, "scripts")
import village_lib as v
import pandas as pd

c = v.chat()
ro = v.roster()
name2id = dict(zip(ro.name, ro.id))
names_longest = sorted(name2id, key=len, reverse=True)
NAME_RE = {n: re.compile(r"(?<![A-Za-z0-9])" + re.escape(n) + r"(?![A-Za-z0-9]|\.\d)") for n in names_longest}

nud = c[(c.role == v.NUDGER_ROLE) & c.is_nudge & ~c.is_pause_resume].copy()
nud = nud.sort_values("event_index")


def addressed(text):
    """Agents @-mentioned in the nudge body (text before the footer): every '@' followed by a roster name
    (longest-name-first match, not followed by an alphanumeric or '.digit'). Fallback when no @ hit: roster names
    appearing in the text before the first em dash."""
    body = text.split("*This is an automated nudge")[0]
    found, how = [], "@mention"
    for m in re.finditer(r"@", body):
        rest = body[m.end():]
        for n in names_longest:
            if rest.startswith(n) and NAME_RE[n].match(rest):
                if n not in found:
                    found.append(n)
                break
    if not found:
        how = "name_before_dash"
        head = body.split("—")[0]
        for n in names_longest:
            if NAME_RE[n].search(head) and not any(n in f for f in found):
                found.append(n)
    return found, how


import gzip, json, bisect
SCAN_OUT = v.OUT / "turns_pre_nudge.parquet"


def scan_pre_nudge(nudge_ts):
    """One gzip pass over computer_use_turns; keep only turns created in the 10 min before any nudge (bisect). Text/action only."""
    sess = pd.read_json(v.DATA / "computer_use_sessions.jsonl.gz", lines=True)[["id", "agent_id"]]
    s2a = dict(zip(sess.id, sess.agent_id))
    arr = sorted(nudge_ts)
    iso = [t.strftime("%Y-%m-%d %H:%M:%S.%f") for t in arr]
    keep, n = [], 0
    with gzip.open(v.DATA / "computer_use_turns.jsonl.gz", "rt") as f:
        for line in f:
            n += 1
            if n % 500000 == 0:
                print("lines", n, "kept", len(keep), file=sys.stderr, flush=True)
            r = json.loads(line)
            ca = r["created_at"]
            t = pd.Timestamp(ca)
            j = bisect.bisect_left(iso, ca)  # first nudge at/after this turn (string order == time order)
            if j >= len(arr) or (arr[j] - t) > pd.Timedelta(minutes=10) or t >= arr[j]:
                continue
            a = r.get("agent_action")
            if isinstance(a, dict):
                at = a.get("action") or ("bash" if "command" in a else "other_dict")
            else:
                at = "none_talk_only" if a is None else "other"
            keep.append(dict(id=r["id"], session_id=r["session_id"], agent_id=s2a.get(r["session_id"]), created_at=ca,
                             action_type=str(at).lower(), agent_action=json.dumps(a, ensure_ascii=False) if a is not None else None,
                             output=r.get("output"), error=r.get("error")))
    print("lines", n, "kept", len(keep), file=sys.stderr)
    pd.DataFrame(keep).to_parquet(SCAN_OUT)


if '--scan' in sys.argv:
    scan_pre_nudge(list(nud.ts))
    sys.exit(0)

e = v.events(("event_index", "created_at", "actionType", "agentId", "speakerId", "computerUseSessionId"))
e["aid"] = e.agentId.where(e.agentId.notna(), e.speakerId)
ev_act = e[e.actionType.isin(["AGENT_TALK", "START_USING_COMPUTER", "STOP_USING_COMPUTER"]) & e.aid.notna()]
ss = e[e.actionType.isin(["START_USING_COMPUTER", "STOP_USING_COMPUTER"]) & e.agentId.notna()]
ev_by = {k: g for k, g in ev_act.groupby("aid")}
ss_by = {k: g for k, g in ss.groupby("agentId")}
msgs_by = {k: g for k, g in c[c.agent_speaker_id.notna()].groupby("agent_speaker_id")}

# computer_use_sessions: the export has only created_at/updated_at (updated_at ~ created_at), no end time.
sess = pd.read_json(v.DATA / "computer_use_sessions.jsonl.gz", lines=True)[["id", "agent_id", "created_at"]]
sess["ts"] = v.to_ts(sess.created_at)
sess_by = {k: g.sort_values("ts") for k, g in sess.groupby("agent_id")}

try:
    tl = pd.read_parquet(v.OUT / "turns_pre_nudge.parquet")
    tl["ts"] = v.to_ts(tl.created_at)
    HAVE_TURNS = True
except FileNotFoundError:
    sys.exit("run: 15_nudger.py --scan first")
NONACT = {"pause", "wait"}
NONACT_STRICT = NONACT | {"none_talk_only", "send_message_back_to_chat"}
turns_by = {k: g.sort_values("ts") for k, g in tl.groupby("agent_id")}

FIVE = pd.Timedelta(minutes=5)
rows = []
for r in nud.itertuples(index=False):
    names, how = addressed(r.content)
    for nm in names or [None]:
        aid = name2id.get(nm)
        open_sess, recent, ev_txt, open_age = False, [], [], None
        any5 = act5 = act5s = False
        reply = None
        if aid:
            g = ss_by.get(aid)
            if g is not None:
                gb = g[g.ts < r.ts]
                started = set(gb[gb.actionType == "START_USING_COMPUTER"].computerUseSessionId)
                stopped = set(gb[gb.actionType == "STOP_USING_COMPUTER"].computerUseSessionId)
                op = started - stopped
                if op:
                    last = gb[(gb.actionType == "START_USING_COMPUTER") & gb.computerUseSessionId.isin(op)].iloc[-1]
                    open_sess = True
                    open_age = round((r.ts - last.ts).total_seconds() / 3600, 2)
                    ev_txt.append(f"open START ei={int(last.event_index)} at {v.fmt_ts(last.ts)} with no STOP before nudge")
            g = ev_by.get(aid)
            if g is not None:
                w = g[(g.ts >= r.ts - FIVE) & (g.ts < r.ts)]
                for x in w.itertuples(index=False):
                    recent.append(f"{x.actionType} ei={int(x.event_index)}")
                if len(w):
                    ev_txt.append(f"{len(w)} event(s) in prior 5 min: " + ", ".join(recent[-3:]))
            if aid in turns_by:
                t = turns_by[aid]
                t = t[(t.ts >= r.ts - FIVE) & (t.ts < r.ts)]
                any5 = bool(len(t))
                act5 = bool((~t.action_type.isin(NONACT)).any())
                act5s = bool((~t.action_type.isin(NONACT_STRICT)).any())
                if act5:
                    ev_txt.append(f"{int((~t.action_type.isin(NONACT)).sum())} non-pause/wait turn(s) in prior 5 min, last: {t[~t.action_type.isin(NONACT)].iloc[-1].action_type} at {v.fmt_ts(t[~t.action_type.isin(NONACT)].iloc[-1].ts)}")
            m = msgs_by.get(aid)
            if m is not None:
                mm = m[(m.ts > r.ts) & (m.ts <= r.ts + pd.Timedelta(minutes=45))]
                if len(mm):
                    reply = mm.iloc[0]
        active = act5
        if reply is not None:
            rc = "mentions_nudge" if re.search(r"nudge|idle|automated|bot", reply.content, re.I) else "other_message"
            wb = bool(re.search(r"\b(nudge\w*|idl\w*|automated|bots?)\b", reply.content, re.I))
        else:
            rc, wb = "none", False
        rows.append(dict(event_index=r.event_index, timestamp_utc=v.fmt_ts(r.ts), deep_link=v.deep_link(r.ts), room=r.room,
                         n_addressed=len(names), addressed_agent=nm, addressed_parse=how, addressed_agent_id=aid,
                         agent_active_at_nudge=act5, activity_evidence="; ".join(ev_txt) if ev_txt else "none found",
                         misfire=act5, active_turn_5m=act5, misfire_openstart=bool(open_sess or recent), misfire_strict_events_5m=bool(recent), active_turn_5m_no_talk=act5s, any_turn_5m=any5, open_start_age_h=open_age,
                         reply_event_index=int(reply.event_index) if reply is not None else None,
                         reply_latency_min=round((reply.ts - r.ts).total_seconds() / 60, 2) if reply is not None else None,
                         reply_text=reply.content if reply is not None else None, reply_class=rc, reply_mentions_wordbound=wb,
                         nudge_text=r.content))
df = pd.DataFrame(rows)
df.to_csv(v.OUT / "nudger_stats.csv", index=False)

# ------------------------------------------------------------------ markdown
L = []
w = L.append
named = df[df.addressed_agent.notna()]
w("# The automated nudger ([repeated-idling]) — verbatim record\n")
w("All text below quoted by code from `out/chat.parquet`; per-row data in `out/nudger_stats.csv`. Times are UTC.\n")
w("## Definitions\n")
w("- **Nudge**: chat row with role `system:automated` (user_speaker_id 445ab51c-3bb1-4475-a536-67f1924b06cf), `is_nudge == True`, `is_pause_resume == False`, footer 'triggered by: repeated-idling' (18 of them print it without brackets). Daily pause/resume notices excluded.")
w("- **Addressed agent**: every `@` followed by a roster agent name (longest-name-first match, not followed by an alphanumeric or `.digit`) in the nudge body before the footer. If no `@` hit, roster names before the first em dash. Many nudges address 2+ agents, so the CSV has **one row per (nudge, addressed agent)**; `n_addressed` gives the count.")
w("- **Active (PRIMARY, `active_turn_5m`)**: the addressee's computer-use session(s) (computer_use_turns.session_id -> computer_use_sessions.agent_id) had at least one turn with an actual action in the 5 minutes before the nudge. Action type = `agent_action.action` (or `bash` when the action has a `command`; `none_talk_only` when agent_action is null). Turns whose action is `pause` or `wait` are EXCLUDED (the model chose to idle). Talk-only turns (`none_talk_only`, `send_message_back_to_chat`) are counted as actions in the primary measure; `active_turn_5m_no_talk` excludes them too. **Misfire = active_turn_5m.**")
w("- **Sensitivity columns**: `any_turn_5m` (any turn incl. pause/wait); `misfire_strict_events_5m` (any AGENT_TALK/START/STOP event in prior 5 min); `misfire_openstart` (strict events OR an open START_USING_COMPUTER with no STOP; dominated by stale never-closed STARTs, median 74 days old, so unreliable for older-scaffold agents).")
w("- The exported computer_use_sessions table has only created_at/updated_at (no end), so session-interval tests were not used. The turn scan kept only turns within 10 min before any nudge (`out/turns_pre_nudge.parquet`, text/action fields only).")
w("- **Reply**: the addressed agent's first chat message (any room) within 45 min after the nudge. `reply_class` = `mentions_nudge` if the text contains the substrings nudge|idle|automated|bot (case-insensitive; literal substring, so 'both', 'robot', 'idled' also match; CSV column `reply_mentions_wordbound` is a stricter word-bound variant), else `other_message`, else `none`.\n")
w("## Summary\n")
nn = len(nud)
w(f"- Nudges: **{nn}**; nudge-agent pairs: **{len(df)}** ({int(df.addressed_agent.isna().sum())} with no parsable addressee)")
w(f"- Date range: {v.fmt_ts(nud.ts.min())} to {v.fmt_ts(nud.ts.max())} (first ei={int(nud.event_index.min())}, last ei={int(nud.event_index.max())})")
mf = int(named.misfire.sum())
ng = named.groupby("event_index").misfire.any()
w(f"- **Primary misfire (non-pause/wait computer-use turn in prior 5 min): {mf} of {len(named)} pairs = {100*mf/len(named):.1f}%; nudge level (any addressee active): {int(ng.sum())} of {len(ng)} nudges = {100*ng.mean():.1f}%**")
for col, lab in [("any_turn_5m", "any turn incl. pause/wait"), ("active_turn_5m_no_talk", "excluding pause/wait AND talk-only turns"), ("misfire_strict_events_5m", "strict events only"), ("misfire_openstart", "open-START or events")]:
    ngc = named.groupby("event_index")[col].any()
    w(f"- Sensitivity, {lab} (`{col}`): pairs {int(named[col].sum())}/{len(named)} = {100*named[col].mean():.1f}%; nudges {int(ngc.sum())}/{len(ngc)} = {100*ngc.mean():.1f}%")
w("- Action types of all turns in the 10 min before any nudge (n=" + str(len(tl)) + "): " + ", ".join(f"{k}={n}" for k, n in tl.action_type.value_counts().items()))
w("- Reply class (pairs): " + ", ".join(f"{k}={n}" for k, n in df.reply_class.value_counts().items()))
w("- Reply class among misfire pairs: " + ", ".join(f"{k}={n}" for k, n in named[named.misfire].reply_class.value_counts().items()))
w("- Median reply latency (min, pairs with a reply): " + f"{df.reply_latency_min.median():.1f}\n")
w("| Agent | nudges | misfires (primary) | misfire % | misfires strict-events-5m | replied (any) | mentions_nudge |")
w("|---|---|---|---|---|---|---|")
for nm, g in named.groupby("addressed_agent"):
    w(f"| {nm} | {len(g)} | {int(g.misfire.sum())} | {100*g.misfire.mean():.0f}% | {int(g.misfire_strict_events_5m.sum())} | {int((g.reply_class!='none').sum())} | {int((g.reply_class=='mentions_nudge').sum())} |")
w("")
w("Rows above sorted alphabetically by agent; monthly counts: " + ", ".join(f"{k}={n}" for k, n in nud.ts.dt.strftime('%Y-%m').value_counts().sort_index().items()) + "\n")

# renegotiation thread
w("## Renegotiation thread, 2026-08-20, event_index 356600-357000 (complete, all rooms)\n")
th = c[(c.event_index >= 356600) & (c.event_index <= 357000)].sort_values("event_index")
anch = {356712: "organizer:adam", 356859: "organizer:adam", 356984: "organizer:adam"}
for ei, role in anch.items():
    x = c[c.event_index == ei]
    if x.empty:
        w(f"- Anchor {ei}: **NOT FOUND in chat table**")
    else:
        x = x.iloc[0]
        w(f"- Anchor {ei}: speaker `{x.speaker}`, role `{x.role}` -> {'MATCH' if x.role == role else 'MISMATCH (expected ' + role + ')'}; opens: {x.content[:90].replace(chr(10),' ')!r}")
w(f"\n{len(th)} chat messages in range ({int(th.role.str.startswith('organizer').sum())} organizer). ✅ = organizer.\n")
for r in th.itertuples(index=False):
    mark = " ✅" if str(r.role).startswith("organizer") else ""
    w(f"**ei={r.event_index} · {v.fmt_ts(r.ts)} · [link]({v.deep_link(r.ts)}) · #{r.room} · {r.speaker} ({r.role}){mark}**\n")
    w("> " + r.content.replace("\n", "\n> ") + "\n")

# discussion of the nudger
w("## Other chat messages discussing the nudger (outside the thread above)\n")
lo, hi = nud.ts.min(), pd.Timestamp("2026-10-28")
o = c[(c.role != v.NUDGER_ROLE) & c.content.str.contains("nudge", case=False, na=False) & (c.ts >= lo)
      & ~((c.event_index >= 356600) & (c.event_index <= 357000))].sort_values("event_index")
w(f"Search: every non-`automated` message from {v.fmt_ts(lo)} onward containing 'nudge' (case-insensitive); {len(o)} messages ({int(o.role.str.startswith('organizer').sum())} by organizers ✅). The nudges themselves are excluded. (Messages whose is_nudge flag is True because they are agent session recaps are included.)\n")
cur = None
for r in o.itertuples(index=False):
    d = r.ts.strftime("%Y-%m-%d")
    if d != cur:
        w(f"### {d}\n")
        cur = d
    mark = " ✅" if str(r.role).startswith("organizer") else ""
    w(f"**ei={r.event_index} · {v.fmt_ts(r.ts)} · [link]({v.deep_link(r.ts)}) · #{r.room} · {r.speaker}{mark}**\n")
    w("> " + r.content.replace("\n", "\n> ") + "\n")

# every nudge by date
w("## Every nudge, by date (verbatim), with the addressed agent's reply\n")
cur = None
for r in nud.itertuples(index=False):
    d = r.ts.strftime("%Y-%m-%d")
    if d != cur:
        n_d = int((nud.ts.dt.strftime("%Y-%m-%d") == d).sum())
        w(f"### {d} ({n_d} nudges)\n")
        cur = d
    w(f"**ei={r.event_index} · {v.fmt_ts(r.ts)} · [link]({v.deep_link(r.ts)}) · #{r.room}**\n")
    w("> " + r.content.replace("\n", "\n> ") + "\n")
    for p in df[df.event_index == r.event_index].itertuples(index=False):
        tag = f"{p.addressed_agent} [{'ACTIVE (misfire)' if p.misfire else 'not active'}; {p.activity_evidence}]"
        if p.reply_event_index is not None and not pd.isna(p.reply_event_index):
            w(f"- reply by {tag}: ei={int(p.reply_event_index)}, +{p.reply_latency_min} min, class={p.reply_class}:")
            w("  > " + p.reply_text.replace("\n", "\n  > ") + "\n")
        else:
            w(f"- no reply within 45 min from {tag}\n")
(v.OUT / "episodes" / "nudger_verbatim.md").write_text("\n".join(L))
print(len(nud), len(df), mf, df.reply_class.value_counts().to_dict(), "no-addressee", int(df.addressed_agent.isna().sum()))
