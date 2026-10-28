"""Task 9: Claude Haiku 5.5 refuses staff authorization (2026-10-08 17:31 -> 2026-10-09 22:33 UTC).
Stages:  --scan   stream data/computer_use_turns.jsonl.gz once (slow); writes
                    out/turns_light.parquet (id, session_id, created_at for ALL turns; used by 15_nudger.py)
                    out/turns_haiku_2026-10-08_09.parquet (text fields only, Haiku 5.5 sessions, 2026-10-08..09 UTC)
         (default) build out/episodes/haiku_refusal_verbatim.md from the cached outputs.
"""
import sys, gzip, json, re
sys.path.insert(0, "scripts")
import village_lib as v
import pandas as pd

HAIKU = "5a452888-8aca-4416-a511-e26f5787c95f"
OPUS48 = "224f3029-6fe6-48d7-81b8-f92d5051be43"
T0, T1 = pd.Timestamp("2026-10-08 00:00:00"), pd.Timestamp("2026-10-10 00:00:00")
SKIP = {"id", "type", "role", "status", "signature", "call_id", "name", "phase", "model", "stop_reason",
        "encrypted_content", "data", "source", "base64_image", "annotations", "logprobs", "media_type"}


def texts(o, out):
    if isinstance(o, str):
        if o.strip() and not (len(o) > 5000 and " " not in o[:200]):
            out.append(o)
    elif isinstance(o, list):
        for x in o:
            texts(x, out)
    elif isinstance(o, dict):
        for k, x in o.items():
            if k in SKIP:
                continue
            if k == "arguments" and isinstance(x, str):  # OpenAI function_call args are JSON-in-string
                try:
                    x = json.loads(x)
                except Exception:
                    pass
            texts(x, out)


def scan():
    sess = pd.read_json(v.DATA / "computer_use_sessions.jsonl.gz", lines=True)[["id", "agent_id"]]
    s2a = dict(zip(sess.id, sess.agent_id))
    haiku_sessions = {s for s, a in s2a.items() if a == HAIKU}
    print("sessions", len(s2a), "haiku sessions", len(haiku_sessions), file=sys.stderr)
    light, rows = [], []
    n = 0
    with gzip.open(v.DATA / "computer_use_turns.jsonl.gz", "rt") as f:
        for line in f:
            n += 1
            if n % 500000 == 0:
                print("lines", n, "haiku rows", len(rows), file=sys.stderr, flush=True)
            r = json.loads(line)
            light.append((r["id"], r["session_id"], r["created_at"]))
            if r["session_id"] in haiku_sessions and "2026-10-08" <= r["created_at"][:10] <= "2026-10-09":
                t = []
                texts(r.get("agent_messages"), t)
                act = r.get("agent_action")
                rows.append(dict(id=r["id"], session_id=r["session_id"], agent_id=HAIKU, created_at=r["created_at"],
                                 model_text="\n".join(t),
                                 action_text=json.dumps(act, ensure_ascii=False) if act is not None else None,
                                 output=r.get("output"), error=r.get("error"), system=r.get("system")))
    print("total lines", n, "haiku rows", len(rows), file=sys.stderr)
    pd.DataFrame(light, columns=["id", "session_id", "created_at"]).to_parquet(v.OUT / "turns_light.parquet")
    pd.DataFrame(rows).to_parquet(v.OUT / "turns_haiku_2026-10-08_09.parquet")


if __name__ == "__main__" and "--scan" in sys.argv:
    scan()


def quote(txt):
    return "> " + txt.replace("\n", "\n> ") + "\n"


def report():
    c = v.chat()
    L = []
    w = L.append
    w("# Claude Haiku 5.5 declines staff authorization — verbatim record\n")
    w("Window: 2026-10-08 16:30 UTC to 2026-10-09 23:00 UTC. All text emitted by code from the dataset; ✅ = organizer message. Times UTC.\n")
    # (a) chat
    w("## (a) Chat exchange\n")
    anchors = {489784: ("george", "organizer:george"), 493524: ("george", "organizer:george"), 496335: ("george", "organizer:george"),
               487206: ("Claude Haiku 5.5", "agent"), 488962: ("Claude Haiku 5.5", "agent"), 493120: ("Claude Haiku 5.5", "agent"),
               493662: ("Claude Haiku 5.5", "agent"), 497229: ("Claude Haiku 5.5", "agent"),
               496349: ("Claude Opus 4.8", "agent"), 496765: ("Claude Opus 4.8", "agent"), 496867: ("Claude Opus 4.8", "agent")}
    w("### Anchor check\n")
    allok = True
    for ei, (sp, role) in anchors.items():
        x = c[c.event_index == ei]
        if x.empty:
            w(f"- {ei}: NOT FOUND"); allok = False; continue
        x = x.iloc[0]
        ok = x.speaker == sp and x.role == role
        allok &= ok
        w(f"- {ei}: speaker `{x.speaker}`, role `{x.role}`, {v.fmt_ts(x.ts)} -> {'MATCH' if ok else 'MISMATCH (expected ' + sp + ', ' + role + ')'}")
    w(f"\n**All {len(anchors)} anchors match: {allok}.** (Camila's chat speaker name is `Cam`, role organizer:camila — see below.)\n")
    ws = c[(c.ts >= "2026-10-08 16:30") & (c.ts <= "2026-10-09 23:00")]
    kw = ws.content.str.contains(r"haiku|delve|authoriz|social media|system prompt", case=False, regex=True)
    who = ws.speaker.isin(["Claude Haiku 5.5", "Claude Opus 4.8", "george", "Cam", "Camila"]) | ws.role.str.contains("camila|george")
    sel = ws[kw | who].sort_values("event_index")
    w(f"Selection: messages in the window by Claude Haiku 5.5, Claude Opus 4.8, george, Cam/Camila, or whose text matches haiku|delve|authoriz|social media|system prompt (case-insensitive; 'haiku' also catches Claude Haiku 4.5 mentions). Rooms present in window: {ws.room.value_counts().to_dict()}. **{len(sel)} messages** "
      f"({int((sel.speaker=='Claude Haiku 5.5').sum())} by Haiku 5.5, {int((sel.speaker=='Claude Opus 4.8').sum())} by Opus 4.8, {int(sel.role.str.startswith('organizer').sum())} organizer, {int((kw & ~who).sum())} others matched by keyword only).\n")
    for r in sel.itertuples(index=False):
        mark = " ✅" if str(r.role).startswith("organizer") else ""
        w(f"**ei={r.event_index} · {v.fmt_ts(r.ts)} · [link]({v.deep_link(r.ts)}) · #{r.room} · {r.speaker} ({r.role}){mark}**\n")
        w(quote(r.content))
    # (b) turns
    t = pd.read_parquet(v.OUT / "turns_haiku_2026-10-08_09.parquet")
    t["ts"] = v.to_ts(t.created_at)
    t = t.sort_values("ts")
    w("## (b) Haiku 5.5 computer-use turn text\n")
    w("Source: data/computer_use_turns.jsonl.gz streamed (3,307,175 lines); join turn.session_id -> computer_use_sessions.agent_id == Claude Haiku 5.5 (5a452888-...). Turns created 2026-10-08 00:00 to 2026-10-10 00:00 UTC. Text fields (model text/thinking blocks from agent_messages, agent_action, output, error, system) saved to `out/turns_haiku_2026-10-08_09.parquet`; screenshots ignored.\n")
    w(f"- Haiku 5.5 turn rows found in the window: **{len(t)}** (first {v.fmt_ts(t.ts.min())}, last {v.fmt_ts(t.ts.max())}). Rows with non-empty model text: {int((t.model_text.str.len()>0).sum())}.")
    byd = t.ts.dt.strftime("%Y-%m-%d").value_counts().sort_index().to_dict()
    w(f"- Per day: {byd}")
    RE = r"authoriz|george|camila|staff|system prompt|operating instructions|delve|social media|post"
    cols = ["model_text", "action_text", "output", "error", "system"]
    hit = t[t[cols].fillna("").agg("\n".join, axis=1).str.contains(RE, case=False, regex=True)]
    w(f"- Turns whose text matches `{RE}` (case-insensitive): **{len(hit)}** of {len(t)} (note `post` also matches posted/posting/compost etc.).\n")
    for r in hit.itertuples(index=False):
        w(f"**turn id={r.id} · session={r.session_id} · {v.fmt_ts(r.ts)} · [link]({v.deep_link(r.ts)})**\n")
        for col in cols:
            val = getattr(r, col)
            if val is not None and not (isinstance(val, float)) and str(val).strip():
                w(f"{col}:\n")
                w(quote(str(val)))
    # (c) memory
    w("## (c) Haiku 5.5 memory diffs\n")
    m = v.memory_shard(HAIKU)
    w(f"Haiku 5.5 has {0 if m is None else len(m)} memory snapshots in total. 'Day' = UTC calendar day.\n")
    pairs = [("2026-10-08", "2026-10-08 16:30:00", "2026-10-09 00:00:00"), ("2026-10-09", "2026-10-09 17:00:00", "2026-10-10 00:00:00")]
    for label, cut, end in pairs:
        w(f"### {label}: last snapshot before {cut} UTC vs last snapshot of the day\n")
        cut, end = pd.Timestamp(cut), pd.Timestamp(end)
        b = m[m.ts < cut]
        d0 = pd.Timestamp(label)
        a = m[(m.ts >= d0) & (m.ts < end)]
        if b.empty:
            w("- cannot compute: no snapshot before the cut\n")
            continue
        if a.empty:
            nxt = m[m.ts >= end]
            w(f"- **No Haiku 5.5 memory snapshot was written on {label} (UTC)**; the day-of comparison requested does not exist. Fallback shown instead: last snapshot before the cut vs the NEXT snapshot after the day"
              + (f" (that gap spans {label} and later days)." if len(nxt) else "; none exists."))
            if nxt.empty:
                continue
            a = nxt.iloc[0]
        else:
            a = a.iloc[-1]
        b = b.iloc[-1]
        for tag, s in (("before", b), ("after", a)):
            w(f"- {tag}: snapshot id `{s.id}` at {v.fmt_ts(s.ts)} ([link]({v.deep_link(s.ts)})), nearest CONSOLIDATE event_index = {v.consolidate_event_near(HAIKU, s.ts)} (±120 s), last event_index at that time = {v.last_event_index_at(s.ts)}, length {len(s.content)} chars")
        ad, rm = v.line_diff(b.content, a.content)
        w(f"- {len(ad)} lines added, {len(rm)} lines removed. Snapshots on that day: {len(m[(m.ts >= d0) & (m.ts < end)])}.\n")
        w("**Added lines:**\n")
        for l in ad:
            w("+ " + l)
        w("\n**Removed lines:**\n")
        for l in rm:
            w("- " + l)
        w("")
    (v.OUT / "episodes" / "haiku_refusal_verbatim.md").write_text("\n".join(L))
    print("chat msgs", len(sel), "turns", len(t), "turn hits", len(hit), "anchors ok", allok)


if __name__ == "__main__" and "--scan" not in sys.argv:
    report()
