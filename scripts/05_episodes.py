"""Build per-episode markdown files under out/episodes/ (chat + summaries + structured events)."""
import re, os
import pandas as pd

OUT = "out/episodes"
os.makedirs(OUT, exist_ok=True)
MEM = "<!-- memories appended by scripts/07_episode_memories.py -->"

chat = pd.read_parquet("out/chat.parquet").sort_values("event_index").reset_index(drop=True)
chat["content"] = chat["content"].fillna("").astype(str)
ev = pd.read_parquet("out/events_slim.parquet")
ev["date"] = ev["created_at"].astype(str).str[:10]
roster = pd.read_csv("out/agents_roster.csv")
names = dict(zip(roster["id"], roster["name"]))
goals = pd.read_csv("out/goals.csv")
goals["s"] = pd.to_datetime(goals["start"], format="mixed"); goals["e"] = pd.to_datetime(goals["end"], format="mixed")
summ = pd.read_json("data/summaries.jsonl.gz", lines=True)
summ["content"] = summ["content"].fillna("")

def agent_name(r):
    a = r.get("agentId")
    if not isinstance(a, str): a = r.get("speakerId")
    return names.get(a, a if isinstance(a, str) else "?")

def tok(s):
    return set(re.sub(r"[^a-z0-9 ]", " ", re.sub(r"['’]", "", str(s).lower())).split())

def cut(s, n, tail=True):
    s = "" if s is None or (isinstance(s, float) and pd.isna(s)) else str(s)
    if len(s) <= n: return s
    return s[:n] + (f"…[+{len(s)-n} chars]" if tail else "…")

def one(s): return str(s).replace("\r", "").replace("\n", " ⏎ ")
def cell(s): return one(s).replace("|", "\\|")

def line(r, multi):
    return (f"- **{r.created_at[11:16]}** `{r.speaker}` [{r.role}, #{r.room}] "
            f"(event_index={r.event_index}): {one(cut(r.content, 1500))}")

def transcript(df):
    out = []
    for d, g in df.groupby("date", sort=True):
        out.append(f"\n### {d}\n")
        out += [line(r, True) for r in g.itertuples()]
    return "\n".join(out)

def matched_goal_summaries(gtitles):
    rows, notes = [], []
    for t in gtitles:
        gt = tok(t)
        cands = []
        for tgt in summ[summ.type == "goal"].summary_target.dropna().unique():
            if re.fullmatch(r"[\d-]+", tgt): continue
            tt = tok(tgt.replace("-", " "))
            if len(tt) >= 3 and tt <= gt: cands.append((len(tt), tgt))
        if cands:
            best = max(c[0] for c in cands)
            for _, tgt in cands:
                if _ == best:
                    notes.append(f"{t!r} -> {tgt}")
                    rows.append(summ[(summ.type == "goal") & (summ.summary_target == tgt)])
        else:
            notes.append(f"{t!r} -> (no goal summary matched)")
    df = pd.concat(rows) if rows else summ.iloc[0:0]
    return df, notes

def goals_in(a, b):
    s, e = pd.Timestamp(a), pd.Timestamp(b) + pd.Timedelta(days=1)
    res = []
    for g in goals.itertuples():
        ge = g.e if pd.notna(g.e) else pd.Timestamp("2100-01-01")
        ov = (min(e, ge) - max(s, g.s)).total_seconds() / 3600
        if ov >= 6: res.append(g)
    return res

def event_section(e):
    L = ["## Structured events\n"]
    def t(r): return str(r.created_at)[11:16] + " " + str(r.date)
    sub = e[e.actionType.isin(["OUTREACH_APPROVAL_REQUEST", "OUTREACH_APPROVAL_RESPONSE"])]
    L.append(f"### Outreach approval requests/responses ({len(sub)})\n")
    for r in sub.itertuples():
        L.append(f"- {t(r)} {agent_name(r._asdict())} {r.actionType} (event_index={r.event_index}) recipient={r.recipient} medium={r.medium} approval={r.approval} adminComment={one(cut(r.adminComment,500))} msg={one(cut(r.messageContent,300,False))}")
    sub = e[e.actionType.isin(["REQUEST_HUMAN_HELPER", "STOP_HUMAN_USE_SESSION"])]
    L.append(f"\n### Human helper requests / sessions ({len(sub)})\n")
    for r in sub.itertuples():
        L.append(f"- {t(r)} {agent_name(r._asdict())} {r.actionType} (event_index={r.event_index}) sessionGoal={one(cut(r.sessionGoal,300))} endReason={r.endReason} endComment={one(cut(r.endComment,300))}")
    sub = e[e.actionType == "ENTER_ROOM"]
    L.append(f"\n### ENTER_ROOM ({len(sub)})\n")
    for r in sub.itertuples():
        L.append(f"- {t(r)} {agent_name(r._asdict())} (event_index={r.event_index}): {r.previousRoomName} → {r.roomName}")
    sub = e[e.actionType == "SEARCH_HISTORY"]
    L.append(f"\n### SEARCH_HISTORY ({len(sub)})\n")
    for r in sub.itertuples():
        L.append(f"- {t(r)} {agent_name(r._asdict())} (event_index={r.event_index}): query={one(cut(r.query,300))}")
    sub = e[e.actionType == "STOP_USING_COMPUTER"]
    L.append(f"\n### STOP_USING_COMPUTER session summaries ({len(sub)})\n")
    for r in sub.itertuples():
        L.append(f"- {t(r)} {agent_name(r._asdict())} (event_index={r.event_index}): {one(cut(r.summary,400))}")
    pw = e[e.actionType.isin(["PAUSE", "WAIT"])].copy()
    L.append("\n### PAUSE / WAIT events per agent\n")
    if len(pw):
        pw["agent"] = [agent_name(r._asdict()) for r in pw.itertuples()]
        tb = pw.groupby(["agent", "actionType"]).size().unstack(fill_value=0)
        L.append("| agent | " + " | ".join(tb.columns) + " |\n|---|" + "---|" * len(tb.columns))
        for a, r in tb.iterrows(): L.append(f"| {a} | " + " | ".join(str(x) for x in r) + " |")
    else:
        L.append("(none)")
    return "\n".join(L)

def summaries_section(a, b, gtitles):
    L = ["## Daily summaries\n",
         "> Caveat: summaries below are LLM-generated secondary evidence, not primary data; verify against the transcript.\n"]
    d = summ[(summ.type == "daily") & (summ.summary_date >= a) & (summ.summary_date <= b)].sort_values("summary_date")
    if not len(d): L.append("(no daily summaries in range)")
    for r in d.itertuples():
        L.append(f"### {r.summary_date} ({r.generated_by})\n\n{r.content}\n")
    gs, notes = matched_goal_summaries(gtitles)
    L.append("## Goal summaries (matched)\n\nMatching: " + "; ".join(notes) + "\n")
    for r in gs.itertuples():
        L.append(f"### Goal summary: {r.summary_target} ({r.generated_by})\n\n{r.content}\n")
    print("  goal summary matches:", notes)
    return "\n".join(L), notes

EPS = [
 ("ep1_2025-06-19_esoteric-framework.md", "2025-06-19", "2025-06-25", "Episode 1: esoteric productivity framework (viewer push)"),
 ("ep2_2025-06-26_merch-squirrel.md", "2025-06-26", "2025-07-15", "Episode 2: merch store goal and 'squirrel stock' troll campaign"),
 ("ep3_2025-09-01_debate-week.md", "2025-09-01", "2025-09-05", "Episode 3: debate week (agents ignoring Adam)"),
 ("ep4_2025-12-22_kindness.md", "2025-12-22", "2025-12-26", "Episode 4: random acts of kindness (outside complaints)"),
 ("ep5_2026-01-05_elected-leader.md", "2026-01-05", "2026-01-09", "Episode 5: elected leader (DeepSeek-V3.2)"),
 ("ep6_2026-05-26_finetuned-leader.md", "2026-05-26", "2026-06-05", "Episode 6: finetune your leader + follow your leader"),
 ("ep7_2026-03-30_no-goal.md", "2026-03-30", "2026-04-01", "Episode 7: agents waiting for a goal"),
]
index = []
KEYWORDS = ["nudge", "idle", "idling", "admin", "refuse", "refused", "refusing", "social media", "takedown", "take down", "taken down"]
WORDS = re.compile(r"\b(goal|leader|vote|refuse|stop|ignore|instruction|told|asked)\b", re.I)

def scope_block(a, b, c, e, gl):
    L = ["## Scope\n", f"- Date range (UTC, inclusive): {a} to {b}"]
    L.append("- Goal(s) active (overlap >= 6h with range):")
    for g in gl:
        L.append(f"  - **{g.goal}** ({g.start} to {g.end}); kickoff sender={g.kickoff_sender}, time={g.kickoff_time}")
        L.append(f"    - kickoff text: {one(g.kickoff_text)}")
        L.append(f"    - agents present (roster): {g.agents_present_roster}")
        L.append(f"    - agents active in window: {g.agents_active_in_window}")
    L.append(f"- Rooms used: " + (", ".join(f"#{k} ({v})" for k, v in c.room.value_counts().items()) or "none"))
    ag = c[c.speaker_type == "agent"]; hu = c[c.speaker_type != "agent"]
    L.append(f"- Agent messages: {len(ag)}")
    L.append(f"- Human messages by role: " + (", ".join(f"{k}={v}" for k, v in hu.role.value_counts().items()) or "none") + f" (total {len(hu)})")
    L.append(f"- Nudges (is_nudge): {int(c.is_nudge.sum())}; pause/resume rows: {int(c.is_pause_resume.sum())}")
    L.append(f"- Events by actionType (total {len(e)}): " + ", ".join(f"{k}={v}" for k, v in e.actionType.value_counts().items()))
    return "\n".join(L)

def human_table(c):
    h = c[(c.speaker_type != "agent") & (~c.is_pause_resume)]
    L = ["| time | speaker | role | room | content |", "|---|---|---|---|---|"]
    for r in h.itertuples():
        mark = " **[NUDGE]**" if r.is_nudge else ""
        L.append(f"| {r.created_at[:16]} (ei={r.event_index}) | {cell(r.speaker)}{mark} | {r.role} | #{r.room} | {cell(cut(r.content,500,False))} |")
    return "\n".join(L)

for fn, a, b, title in EPS:
    print(fn)
    c = chat[(chat.date >= a) & (chat.date <= b)]
    e = ev[(ev.date >= a) & (ev.date <= b)].sort_values("created_at")
    gl = goals_in(a, b)
    ag = c[c.speaker_type == "agent"]; hu = c[c.speaker_type != "agent"]
    L = [f"# {title}\n", scope_block(a, b, c, e, gl), ""]
    sib = ""
    if len(c) == 0:
        L.append("\n**EMPTY: no chat messages in this range**\n")
    else:
        L.append("\n## Organizer and human messages\n")
        L.append(human_table(c))
        L.append("\n## Full chat transcript\n")
        if len(c) > 3000:
            sib = fn.replace(".md", "_transcript.md")
            with open(f"{OUT}/{sib}", "w") as f:
                f.write(f"# {title}: full chat transcript ({len(c)} messages, {a} to {b})\n" + transcript(c) + "\n")
            hn = set(hu.speaker.str.lower()) | {"adam", "zak", "shoshannah", "george", "camila", "larissa"}
            hn = {h for h in hn if h}
            mention = re.compile(r"@\s*(" + "|".join(re.escape(h) for h in sorted(hn, key=len, reverse=True)) + r")", re.I)
            keep = c[(c.speaker_type != "agent") | c.is_nudge | c.content.str.contains(mention) | c.content.str.contains(WORDS)]
            L.append(f"> **NOTE: this episode has {len(c)} messages (>3000). The FULL transcript is in the sibling file `{sib}`. "
                     f"This file shows only human messages, nudges, and agent messages that @-mention a human/organizer or contain the words goal/leader/vote/refuse/stop/ignore/instruction/told/asked ({len(keep)} shown).**")
            L.append(transcript(keep))
        else:
            L.append(transcript(c))
    L.append("\n" + event_section(e))
    sec, notes = summaries_section(a, b, [g.goal for g in gl])
    L.append("\n" + sec)
    L.append("\n" + MEM + "\n")
    open(f"{OUT}/{fn}", "w").write("\n".join(L))
    index.append((fn, f"{a} to {b}", "; ".join(g.goal for g in gl), len(ag), len(hu), int(c.is_nudge.sum()), len(e), sib))
    print("  chat", len(c), "agent", len(ag), "human", len(hu), "events", len(e), "empty" if len(c) == 0 else "")

# ---- Episode 8
fn, a = "ep8_2026-07-06_onward_keywords.md", "2026-07-06"
c = chat[chat.date >= a].reset_index(drop=True)
e = ev[(ev.date >= a) & (~ev.actionType.isin(["AGENT_TALK", "USER_TALK"]))].sort_values("created_at")
pats = {k: re.compile(r"\b" + re.escape(k) + r"\b", re.I) for k in KEYWORDS}
anyp = re.compile(r"\b(" + "|".join(re.escape(k) for k in KEYWORDS) + r")\b", re.I)
c_hit = c.content.str.contains(anyp)
idx = set()
c["pos"] = c.groupby("room").cumcount()
for room, g in c.groupby("room"):
    g = g.reset_index()
    for i in g.index[c_hit.loc[g["index"]].values]:
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(g): idx.add(g.loc[j, "index"])
sel = c.loc[sorted(idx)].copy()
sel["hit"] = c_hit.loc[sel.index]
ccount = {k: int(c.content.str.contains(p).sum()) for k, p in pats.items()}
txtcols = ["content", "summary", "messageContent", "rationale", "adminComment", "endComment", "query", "sessionGoal", "nextSessionGoal", "answerToQuery"]
e = e.copy()
e["txt"] = e[txtcols].fillna("").astype(str).agg(" ⏎ ".join, axis=1)
e_hit = e[e.txt.str.contains(anyp)]
ecount = {k: int(e.txt.str.contains(p).sum()) for k, p in pats.items()}
L = [f"# Episode 8: keyword-filtered chat and events from {a} onward\n",
     "## Scope\n",
     f"- Date range: {a} to {c.date.max()} (end of data)",
     "- Filter: case-insensitive, word-boundary match on: " + ", ".join(f'"{k}"' for k in KEYWORDS),
     f"- Chat hits: {int(c_hit.sum())} of {len(c)} messages in range; shown with +/-1 same-room context: {len(sel)} rows",
     f"- Non-talk events scanned (AGENT_TALK/USER_TALK excluded because chat covers them): {len(e)}; event hits: {len(e_hit)}",
     "- Goals in range: " + "; ".join(f"{g.goal} (kickoff {g.kickoff_sender} {g.kickoff_time})" for g in goals.itertuples() if (pd.isna(g.e) or g.e >= pd.Timestamp(a))),
     "\n### Counts per keyword (messages/events containing it; one message can match several)\n",
     "| keyword | chat messages | events |", "|---|---|---|"]
L += [f"| {k} | {ccount[k]} | {ecount[k]} |" for k in KEYWORDS]
L.append("\n## Chat hits (grouped by date; `>>` marks a hit, other lines are +/-1 context in same room)\n")
for d, g in sel.groupby("date"):
    L.append(f"\n### {d}\n")
    for r in g.itertuples():
        L.append(("- >> " if r.hit else "- (ctx) ") + line(r, True)[2:])
L.append("\n## Event hits\n")
for d, g in e_hit.groupby("date"):
    L.append(f"\n### {d}\n")
    for r in g.itertuples():
        m = anyp.search(r.txt); s0 = max(0, m.start() - 200)
        L.append(f"- {r.created_at[11:16]} {agent_name(r._asdict())} {r.actionType} (event_index={r.event_index}) [{m.group(0).lower()}]: …{one(r.txt[s0:m.end()+300])}…")
L.append("\n" + MEM + "\n")
open(f"{OUT}/{fn}", "w").write("\n".join(L))
index.append((fn, f"{a} to end", "keyword-filtered (multiple goals)", int((c_hit & (c.speaker_type == 'agent')).sum()), int((c_hit & (c.speaker_type != 'agent')).sum()), int((c_hit & c.is_nudge).sum()), len(e_hit), ""))
print("ep8 chat hits", int(c_hit.sum()), ccount, "event hits", len(e_hit), ecount)

with open(f"{OUT}/INDEX.md", "w") as f:
    f.write("# Episodes index\n\n(ep8 counts are keyword HITS only, not totals.)\n\n| file | range | goal | #agent msgs | #human msgs | #nudges | #events | transcript sibling |\n|---|---|---|---|---|---|---|---|\n")
    for r in index: f.write("| " + " | ".join(cell(x) if x != "" else "-" for x in r) + " |\n")
