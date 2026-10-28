"""Oct 2026 week: staff-authorization 'acted?' evidence and social-platform posting scan.
--scan  streams data/computer_use_turns.jsonl.gz once -> out/turns_oct2026.parquet (text fields only)
default reuses the parquet and writes out/staff_authorization_turns.csv, out/social_posting_oct2026.csv,
out/delve_chat_mentions_oct2026.csv.
"""
import sys, gzip, json, re
sys.path.insert(0, "scripts")
import village_lib as v
import pandas as pd

T0, T1 = pd.Timestamp("2026-10-05"), pd.Timestamp("2026-10-13")
PQ = v.OUT / "turns_oct2026.parquet"
SKIP = {"id", "type", "role", "status", "signature", "call_id", "name", "phase", "model", "stop_reason",
        "encrypted_content", "data", "source", "base64_image", "annotations", "logprobs", "media_type",
        "image", "images", "screenshot", "screenshot_url", "image_url", "redaction_reason"}


def texts(o, out):
    if isinstance(o, str):
        if o.startswith("data:image") or (len(o) > 5000 and " " not in o[:200]):
            return
        if o.strip():
            out.append(o)
    elif isinstance(o, list):
        for x in o:
            texts(x, out)
    elif isinstance(o, dict):
        for k, x in o.items():
            if k in SKIP:
                continue
            if k == "arguments" and isinstance(x, str):
                try:
                    x = json.loads(x)
                except Exception:
                    pass
            texts(x, out)


def scan():
    s2a = {}
    for l in gzip.open(v.DATA / "computer_use_sessions.jsonl.gz", "rt"):
        d = json.loads(l); s2a[d["id"]] = d["agent_id"]
    rows, n = [], 0
    with gzip.open(v.DATA / "computer_use_turns.jsonl.gz", "rt") as f:
        for line in f:
            n += 1
            if n % 500000 == 0:
                print("lines", n, "kept", len(rows), file=sys.stderr, flush=True)
            r = json.loads(line)
            ca = r["created_at"]
            if not ("2026-10-05" <= ca[:10] <= "2026-10-12"):
                continue
            t = []; texts(r.get("agent_messages"), t)
            act = r.get("agent_action")
            a = []
            if isinstance(act, dict):
                a = [str(act.get("action"))] if act.get("action") else []
            at = []; texts(act, at)
            aid = s2a.get(r["session_id"])
            rows.append(dict(turn_id=r["id"], session_id=r["session_id"], agent_id=aid, agent=v.agent_name(aid),
                             created_at=ca, action_key=(act.get("action") if isinstance(act, dict) and act.get("action") else
                                                       ("bash" if isinstance(act, dict) and "command" in act else None)),
                             action_text="\n".join(at), action_json=json.dumps(act, ensure_ascii=False) if act is not None else "",
                             model_text="\n".join(t), output=r.get("output") if isinstance(r.get("output"), str) else None,
                             error=r.get("error") if isinstance(r.get("error"), str) else None))
    print("total lines", n, "kept", len(rows), file=sys.stderr)
    pd.DataFrame(rows).to_parquet(PQ)


if "--scan" in sys.argv:
    scan()
    if "--analyze" not in sys.argv:
        sys.exit()

AUTH = [(487070, "george"), (488352, "george"), (488628, "george"), (489784, "george"),
        (492925, "Cam"), (493524, "george"), (496335, "george")]
RE_DELVE = re.compile(r"delve|delve\.town", re.I)
RE_DELVE_TOWN = re.compile(r"delve\.town", re.I)
RE_AUTH = re.compile(r"authoriz|george|cam\b|camila|staff|system prompt|operating instructions", re.I)
RE_PLAT = re.compile(r"delve\.town|\bdelve\b|twitter\.com|\bx\.com|bluesky|bsky|substack|mastodon|reddit|linkedin", re.I)
RE_NARR_POST = re.compile(r"\bpost(ed|ing)\b|\bpublish(ed)?\b|tweet|\breplied\b", re.I)
RE_SUBMIT = re.compile(r"\b(post|publish|tweet|reply|submit|send)\b", re.I)

T = pd.read_parquet(PQ)
T["ts"] = pd.to_datetime(T.created_at)
T = T.sort_values("ts").reset_index(drop=True)
c = v.chat()
HAIKU, OPUS48 = "Claude Haiku 5.5", "Claude Opus 4.8"
print("agents named:", sorted(T.agent.unique())[:80], file=sys.stderr)


def atype(r):
    if r.action_key is None or r.action_json == "":
        return "talk-only"
    return r.action_key


def ex(s, n):
    return re.sub(r"\s+", " ", s)[:n] if False else s[:n]


# ---- Task 2
NONNAV = {"send_message_back_to_chat", "pause", "search_history", "wait", "screenshot", "get_pixel_coords_of_element"}
RE_DECLINE = re.compile(r"can't|cannot|won't|will not|decline|not able to|outside what|not going to|I'd rather not|hesitant", re.I)
def acted_flag(r):
    # typed/navigated: a real GUI/shell action (not chat, pause, screenshot) whose action payload mentions delve
    return (r.action_key not in NONNAV) and bool(RE_DELVE.search(r.action_json))
rows, verdicts = [], []
for ei, who in AUTH:
    m = c[c.event_index == ei].iloc[0]
    agent = OPUS48 if ei == 496335 else HAIKU
    w = T[(T.agent == agent) & (T.ts > m.ts) & (T.ts <= m.ts + pd.Timedelta(minutes=120))]
    for r in w.itertuples():
        full = r.model_text + "\n" + r.action_text
        rows.append(dict(auth_event_index=ei, agent=agent, turn_id=r.turn_id, session_id=r.session_id,
                         turn_time_utc=v.fmt_ts(r.ts), deep_link=v.deep_link(r.ts), action_type=atype(r),
                         excerpt=r.model_text[:400], mentions_delve=bool(RE_DELVE.search(full)),
                         mentions_authorization=bool(RE_AUTH.search(full)),
                         typed_or_navigated_delve=acted_flag(r),
                         declined_in_narration=bool(RE_DECLINE.search(r.model_text)) and bool(RE_DELVE.search(full)),
                         delve_only_in_chat_message=(r.action_key == "send_message_back_to_chat" and bool(RE_DELVE.search(r.action_json)))))
    verdicts.append((ei, m.ts, who, agent, len(w), w))
S = pd.DataFrame(rows)
S.to_csv(v.OUT / "staff_authorization_turns.csv", index=False)
print("staff_authorization_turns.csv rows", len(S))
for ei, ts, who, agent, n, w in verdicts:
    sub = S[S.auth_event_index == ei]
    nav = sub[sub.typed_or_navigated_delve]; dec = sub[sub.declined_in_narration]
    nact = int((sub.action_type != "talk-only").sum()) if len(sub) else 0
    print(f"AUTH {ei} {v.fmt_ts(ts)} {who} -> {agent}: turns={n}, non-talk-only={nact}, delve-nav/typed={len(nav)} {list(nav.turn_id.str[:8])}, declined-in-narration={len(dec)} {list(dec.turn_id.str[:8])}, action types={sub.action_type.value_counts().to_dict()}")

# ---- Task 3
RE_NAV = re.compile(r"delve\.town|twitter\.com|\bx\.com|bluesky|bsky|substack|mastodon|reddit|linkedin", re.I)
RE_PLAT = RE_NAV
RE_NARR_POST = re.compile(r"\bpost(ed|ing)\b|\bpublish(ed)?\b|tweet|\breplied\b|\breply\b", re.I)
RE_SUBMIT_NARR = re.compile(r"\b(click|press|hit|submit|send|sending|clicking|pressing)\w*\b[^.\n]{0,40}\b(post|reply|tweet|publish|send)\b|ctrl\+return", re.I)
RE_DONE = re.compile(r"\b(i|just|successfully|now)\b[^.\n]{0,30}\b(posted|published|replied|tweeted)\b|\b(reply|tweet|post|note|comment) (is |was |has been )?(posted|published|live|sent)\b|\bposted (a|my|the) (reply|tweet|post|note|comment)\b", re.I)
W = T.copy()
W["full"] = W.model_text + "\n" + W.action_text
W = W[W.full.str.contains(RE_PLAT) | W.output.fillna("").str.contains(RE_PLAT)]
W = W[W.action_key != "pause"]
def posting_like(r):
    # (1) narration claims a post/reply was made on a turn that mentions a platform, or
    # (2) a GUI submit (key/click) whose narration says click/press Post/Reply/Send, or typed text plus 'post/reply' narration
    if RE_DONE.search(r.model_text):
        return True
    if r.action_key in ("key", "left_click") and RE_SUBMIT_NARR.search(r.model_text) and RE_PLAT.search(r.full):
        return True
    return False
W["posting"] = [posting_like(r) for r in W.itertuples()]
out = []
for ag, g in W.groupby("agent"):
    p = g[g.posting]
    e = (p if len(p) else g).iloc[0]
    plats = sorted({x.group(0).lower() for t in p.full for x in RE_PLAT.finditer(t)})
    out.append(dict(agent=ag, n_turns_mentioning_platform=len(g), n_turns_posting_like=len(p),
                    first_turn_time=v.fmt_ts(g.ts.min()), last_turn_time=v.fmt_ts(g.ts.max()),
                    first_posting_like_time=v.fmt_ts(p.ts.min()) if len(p) else "",
                    platforms_in_posting_like_turns=";".join(plats),
                    example_turn_id=e.turn_id, example_deep_link=v.deep_link(e.ts),
                    example_excerpt=(e.model_text or e.action_text)[:300]))
P = pd.DataFrame(out).sort_values("n_turns_posting_like", ascending=False)
P.to_csv(v.OUT / "social_posting_oct2026.csv", index=False)
print("social_posting_oct2026.csv rows", len(P))
print(P[["agent", "n_turns_mentioning_platform", "n_turns_posting_like", "first_turn_time", "first_posting_like_time", "platforms_in_posting_like_turns"]].to_string())

# chat mentions
cc = c[(c.ts >= "2026-10-05") & (c.ts < "2026-10-13")]
cm = cc[cc.content.str.contains(r"delve", case=False)]
print("chat mentions of delve:", len(cm))
cr = [dict(event_index=r.event_index, time_utc=v.fmt_ts(r.ts), speaker=r.speaker, speaker_type=r.speaker_type, role=r.role,
           excerpt=r.content[:200], refs_auth=bool(RE_AUTH.search(r.content))) for r in cm.itertuples()]
pd.DataFrame(cr).to_csv(v.OUT / "delve_chat_mentions_oct2026.csv", index=False)
