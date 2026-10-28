"""Task 12: can inbound emails received by agents be recovered from text fields? See out/inbound_email_probe.md."""
import sys, gzip, json, re, csv, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
import village_lib as v

OUT, DATA = v.OUT, v.DATA
W1 = (pd.Timestamp("2025-12-22"), pd.Timestamp("2025-12-27"))
IMG_KEYS = {"base64_image", "image", "images", "screenshot", "screenshot_url", "source", "image_url", "redaction_reason"}

def locate_w2():
    c = v.chat()
    w = c[(c.ts >= "2026-08-01") & (c.ts < "2026-08-16")]
    m = w[w.content.str.contains(r"crthpl|Manifold|mana\b|Bayesian", case=False, regex=True)]
    return m.ts.min() - pd.Timedelta(days=1), m.ts.max() + pd.Timedelta(days=1)

W2 = locate_w2()

def strings(o, out, key=""):
    """collect text strings from nested JSON, skipping image-ish keys and base64 blobs."""
    if isinstance(o, str):
        if o.startswith("data:image") or (len(o) > 2000 and " " not in o[:2000]):
            return
        out.append(o)
    elif isinstance(o, dict):
        for k, x in o.items():
            if k in IMG_KEYS or k in ("signature", "thoughtSignature", "id", "call_id", "logprobs"):
                continue
            strings(x, out, k)
    elif isinstance(o, list):
        for x in o:
            strings(x, out, key)

def which(ts):
    if W1[0] <= ts < W1[1]: return "w1"
    if W2[0] <= ts < W2[1]: return "w2"

def stream_turns():
    p1, p2 = [], []
    n = 0
    with gzip.open(DATA / "computer_use_turns.jsonl.gz", "rt") as f:
        for line in f:
            n += 1
            if n % 500000 == 0:
                print(f"{n} lines, kept {len(p1)}+{len(p2)}", file=sys.stderr, flush=True)
            # cheap prefilter on the created_at field before full parse
            d = json.loads(line)
            ts = pd.Timestamp(d["created_at"])
            w = which(ts)
            if not w: continue
            am = []; strings(d.get("agent_messages"), am)
            aa = []; strings(d.get("agent_action"), aa)
            row = dict(turn_id=d["id"], session_id=d["session_id"], created_at=d["created_at"],
                       agent_action_text="\n".join(aa), agent_messages_text="\n".join(am),
                       output=d.get("output"), error=d.get("error"), system=d.get("system"),
                       screenshot_is_redacted=d.get("screenshot_is_redacted"))
            (p1 if w == "w1" else p2).append(row)
    print(f"done {n} lines, kept {len(p1)}+{len(p2)}", file=sys.stderr, flush=True)
    return pd.DataFrame(p1), pd.DataFrame(p2)

def session_agents():
    m = {}
    with gzip.open(DATA / "computer_use_sessions.jsonl.gz", "rt") as f:
        for l in f:
            d = json.loads(l); m[d["id"]] = d["agent_id"]
    names = {}
    with gzip.open(DATA / "agents.jsonl.gz", "rt") as f:
        for l in f:
            d = json.loads(l); names[d["id"]] = d["name"]
    return m, names

SIGNALS = {
 "From:": r"\bfrom:", "Subject:": r"\bsubject:", "inbox": r"\binbox\b", "unread": r"\bunread\b",
 "received an email": r"received an? e-?mail", "replied": r"\breplied\b", "wrote:": r"\bwrote:",
 "@gmail.com": r"@gmail\.com", "re:": r"\bre:", "Guido": r"guido", "crthpl": r"crthpl", "Bayesian": r"bayesian",
}
SIG_RE = {k: re.compile(p, re.I) for k, p in SIGNALS.items()}
# classification regexes (applied to the concatenated text of one turn)
RE_FROM = re.compile(r"\bfrom:\s*\S+", re.I)
RE_SUBJ = re.compile(r"\bsubject:\s*\S+", re.I)
RE_SENDER_SUBJ_PROSE = re.compile(r"(email|message|mail)s?\s+(from\s+\S+.{0,120}?)?(with\s+)?(the\s+)?subject\s*[\"'“‘:]", re.I | re.S)
RE_QUOTED_BODY = re.compile(r"(\bwrote:|\bsubject:[^\n]{3,200}\n)", re.I)
RE_PARAPHRASE = re.compile(r"(e-?mail|message)s?\b.{0,160}\b(from|said|says|asked|asking|saying|told|suggest\w*|replied|reply|wrote|sent|advis\w*|request\w*)\b|\b(replied|wrote|responded)\b|\b(received|got)\b.{0,40}\be-?mail", re.I | re.S)
RE_EMAILWORD = re.compile(r"e-?mail|gmail|inbox|unread", re.I)

RE_FULL = re.compile(r"From:[^\n]*\n\s*To:[^\n]*\n\s*Subject:[^\n]*\n\s*Date:[^\n]*\n\s*-{20,}\n(?P<body>.{40,})", re.S)  # Gmail-CLI "read message" output: headers, dashed rule, body
RE_LIST = re.compile(r"ID:\s*[0-9a-f]{12,}\s*\n?\s*From:[^\n]*\n\s*Subject:[^\n]*", re.I)  # Gmail-CLI "list" output: sender, subject, date, 1-line preview
RE_GUI = re.compile(r'"[^"\n]{2,40}"\s*-\s*"[^"\n]{3,80}"')  # agent transcribing a Gmail inbox row: "Sender" - "Subject..."

def classify(texts, agent=""):
    """texts: dict field->text. Returns (class, matched fields, key signal). Classes A/B/C/D, None = no signal."""
    allt = "\n".join(texts.values())
    hit = {k: [f for f, t in texts.items() if t and r.search(t)] for k, r in SIG_RE.items()}
    hit = {k: v_ for k, v_ in hit.items() if v_}
    if not hit: return None, "", ""
    slug = re.sub(r"[^a-z0-9.]+", "-", agent.lower()).strip("-")
    out = (texts.get("output") or "") + "\n" + (texts.get("error") or "")
    body = False
    for m in RE_FULL.finditer(out):
        hdr = out[m.start():m.start() + 200].split("\n")[0].lower()
        own = slug and (slug.replace("claude-", "claude-") in hdr.replace(" ", "-").replace("_", "-"))
        if not own: body = True
    nonaction = texts.get("agent_messages_text", "") + "\n" + out
    if body: cls = "A"
    elif RE_LIST.search(out) or (RE_GUI.search(nonaction) and RE_EMAILWORD.search(allt)) or RE_SENDER_SUBJ_PROSE.search(nonaction): cls = "B"
    elif (RE_PARAPHRASE.search(nonaction) and RE_EMAILWORD.search(nonaction)) or (any(k in hit for k in ("Guido", "crthpl", "received an email", "wrote:")) and RE_EMAILWORD.search(nonaction)): cls = "C"
    else: cls = "D"
    pri = [k for k in ("crthpl", "Guido", "Subject:", "From:", "wrote:", "received an email", "replied", "@gmail.com", "unread", "inbox", "re:", "Bayesian") if k in hit]
    return cls, ",".join(sorted(set(sum(hit.values(), [])))), pri[0]

def excerpt(texts, key):
    r = SIG_RE[key]
    for f, t in texts.items():
        if t:
            m = r.search(t)
            if m:
                s = max(0, m.start() - 100)
                return f, re.sub(r"\s+", " ", t[s:s + 300])
    return "", ""

TEXTF = ["agent_action_text", "agent_messages_text", "output", "error", "system"]

def main():
    if "--reuse" in sys.argv and (OUT / "turns_w2_manifold.parquet").exists():
        t1 = pd.read_parquet(OUT / "turns_w1_kindness.parquet"); t2 = pd.read_parquet(OUT / "turns_w2_manifold.parquet")
    else:
        t1, t2 = stream_turns()
        t1.to_parquet(OUT / "turns_w1_kindness.parquet"); t2.to_parquet(OUT / "turns_w2_manifold.parquet")
    s2a, names = session_agents()
    rows = []
    counts = collections.Counter()
    totals = {}
    for w, df in (("W1", t1), ("W2", t2)):
        totals[w] = len(df)
        for r in df.itertuples(index=False):
            texts = {f: (getattr(r, f) or "") for f in TEXTF}
            ag0 = names.get(s2a.get(r.session_id), "") or ""
            cls, fields, key = classify(texts, ag0)
            if cls is None: continue
            counts[(w, cls)] += 1
            ag = s2a.get(r.session_id)
            ts = pd.Timestamp(r.created_at)
            f, ex = excerpt(texts, key)
            rows.append(dict(window=w, turn_id=r.turn_id, session_id=r.session_id, agent=names.get(ag, ag), time=v.fmt_ts(ts),
                             link=v.deep_link(ts), cls=cls, matched_field=f, signals=fields, excerpt=ex))
    hits = pd.DataFrame(rows)
    hits.to_csv(OUT / "inbound_email_hits.csv", index=False, quoting=csv.QUOTE_ALL)
    # non-turn sources
    e = v.events(("event_index", "created_at", "actionType", "agentId", "summary", "nextSessionGoal", "sessionGoal"))
    c = v.chat()
    summ = pd.DataFrame(json.loads(l) for l in gzip.open(DATA / "summaries.jsonl.gz", "rt"))
    other = {}
    for w, (a, b) in (("W1", W1), ("W2", W2)):
        ee = e[(e.ts >= a) & (e.ts < b)]
        cc = c[(c.ts >= a) & (c.ts < b)]
        for nm, ser in (("event summary", ee.summary), ("event nextSessionGoal", ee.nextSessionGoal), ("event sessionGoal", ee.sessionGoal), ("chat", cc.content)):
            ser = ser.dropna().astype(str)
            other[(w, nm)] = {k: int(ser.str.contains(r, regex=True, case=False).sum()) for k, r in SIGNALS.items()} | {"_n": len(ser)}
        ss = summ[(pd.to_datetime(summ.summary_date, errors="coerce") >= a.normalize()) & (pd.to_datetime(summ.summary_date, errors="coerce") <= b)]
        ser = ss.content.dropna().astype(str)
        other[(w, "daily summaries (summaries.jsonl.gz)")] = {k: int(ser.str.contains(r, regex=True, case=False).sum()) for k, r in SIGNALS.items()} | {"_n": len(ser)}
    ag = summ[summ.type == "agent"].content.dropna().astype(str)
    other[("all", "agent summaries (type=agent, whole run)")] = {k: int(ag.str.contains(r, regex=True, case=False).sum()) for k, r in SIGNALS.items()} | {"_n": len(ag)}
    write_md(counts, totals, hits, other, t1.columns.tolist())

def pick(hits, pat, w, prefer=("A", "B", "C"), field_pref=None, require=None):
    h = hits[hits.window == w]
    h = h[h.excerpt.str.contains(pat, case=False, regex=True)]
    if require: h = h[h.agent.fillna("").str.contains(require)]
    h = h.assign(o=h.cls.map({c: i for i, c in enumerate("ABCD")}))
    return h.sort_values(["o", "time"]).head(5)

VERDICT = open(OUT / "inbound_email_verdict.txt").read() if (OUT / "inbound_email_verdict.txt").exists() else "TBD"

def write_md(counts, totals, hits, other, cols):
    L = []
    L.append("# Inbound-email gap probe (Task 12)\n")
    L.append(f"Generated by `scripts/19_inbound_email_probe.py`. W1 = {W1[0]:%Y-%m-%d %H:%M} to {W1[1]:%Y-%m-%d %H:%M} UTC; W2 = {W2[0]:%Y-%m-%d %H:%M} to {W2[1]:%Y-%m-%d %H:%M} UTC (first/last crthpl|Manifold|mana|Bayesian chat message in Aug 2026, +/-1 day). Turns scanned: W1 {totals['W1']}, W2 {totals['W2']}.\n")
    L.append("## Schema facts\n")
    L.append("Fields of a `computer_use_turns` row (per data/SCHEMA.md and verified on sample rows): `id, session_id, agent_action, agent_messages, output, error, system, screenshot_is_redacted, has_redaction_been_overruled, created_at, updated_at`. `agent_messages` holds the raw provider response (narration text, thinking/reasoning, tool-call arguments); `agent_action` is the executed action (click coordinates, typed `text`, bash `command`); `output`/`error`/`system` are tool stdout/stderr/notes. `base64_image` and `redaction_reason` are not exported. Turn joins to agent via `session_id` -> `computer_use_sessions.agent_id` -> `agents.id`.\n")
    L.append("**Is there any OCR / accessibility-tree / text-of-screenshot field? NO.** The only screenshot content is in image tars (not examined here). Text that appears from the screen exists only if the model itself transcribed it in narration/thinking/actions, or if a bash/tool `output` happened to carry it.\n")
    L.append("## Classification regexes (applied to the concatenation of agent_action text, agent_messages text, output, error, system for each turn; first matching class wins, A > B > C > D)\n")
    L.append("Signals (case-insensitive): " + "; ".join(f"`{k}` = `{p}`" for k, p in SIGNALS.items()) + "\n")
    L.append("- **A (full body)**: in `output`/`error`, the Gmail-CLI read format `%s` (headers, dashed rule, then body), and the From: line is not the agent's own address (own sent copies excluded).\n- **B (sender + subject only)**: Gmail-CLI list format `%s` (sender, subject, date, 1-line preview in `output`); or an agent transcribing an inbox row `%s` (with an email word in the turn); or prose `%s`; all searched only in agent_messages text and output/error (not in typed/bash-command text).\n- **C (paraphrase)**: `%s` together with `%s` (non-action text); or Guido/crthpl/'received an email'/'wrote:' together with an email word.\n- **D**: some signal matched (e.g. 'inbox', 'unread', 're:', '@gmail.com') but none of the above.\n- Caveats: regex heuristics; first matching class wins (A>B>C>D). C over-counts (agents discussing emails they send, or the word 'message'); D is mostly the word 'inbox'/'re:'/'Bayesian' in unrelated text. Treat counts as rough, and the examples as the evidence.\n" % (RE_FULL.pattern, RE_LIST.pattern, RE_GUI.pattern, RE_SENDER_SUBJ_PROSE.pattern, RE_PARAPHRASE.pattern, RE_EMAILWORD.pattern))
    L.append("## Turn counts per class (turns with at least one signal)\n")
    L.append("| window | A | B | C | D | total signal turns | turns scanned |\n|---|---|---|---|---|---|---|")
    for w in ("W1", "W2"):
        cs = [counts[(w, c)] for c in "ABCD"]
        L.append(f"| {w} | " + " | ".join(map(str, cs)) + f" | {sum(cs)} | {totals[w]} |")
    L.append("")
    L.append("Per-signal turn counts:\n")
    for w in ("W1", "W2"):
        h = hits[hits.window == w]
        L.append(f"- {w}: " + ", ".join(f"{k}={int(h.signals.str.contains(re.escape(k), case=False).sum())}" if False else f"{k}={int(sum(bool(SIG_RE[k].search(x)) for x in h.excerpt))}(excerpt only)" for k in ("Guido", "crthpl", "Bayesian")))
    L.append("")
    L.append("Per-agent signal turns (class A/B only):\n")
    for w in ("W1", "W2"):
        h = hits[(hits.window == w) & hits.cls.isin(["A", "B"])]
        L.append(f"- {w}: " + (", ".join(f"{a}={n}" for a, n in h.agent.value_counts().head(10).items()) or "none"))
    L.append("")
    L.append("## Other text sources (count of rows containing each signal)\n")
    for (w, nm), d in other.items():
        L.append(f"- {w} {nm} (n={d['_n']}): " + ", ".join(f"{k}={n}" for k, n in d.items() if k != "_n" and n))
    L.append("")
    L.append("## Examples (verbatim excerpts, emitted from data)\n")
    T = {"w1": pd.read_parquet(OUT / "turns_w1_kindness.parquet"), "w2": pd.read_parquet(OUT / "turns_w2_manifold.parquet")}
    s2a, names = session_agents()
    EX = [("Guido email (W1): Opus 4.5 reads Guido's reply in the Gmail GUI; only its own transcription survives", "w1", "6cc9c21f-0b30-4211-8983-e2c69fbe67ca", "agent_messages_text", r"Wow, this is very clear feedback", 650),
          ("crthpl 2:58 PM email (W2): Opus 4.6 reads the email in the GUI; subject truncated + its own bullet paraphrase of the body", "w2", "a0523093-5f07-43a8-ac23-1bf870b1ac87", "agent_messages_text", r"Let me analyze this carefully", 800),
          ("crthpl 2:58 PM email (W2): the sender check the anchor chat message refers to", "w2", "ee54b721-ed56-4633-a7e9-d546e60135bb", "agent_messages_text", r"The email IS from crthpl", 500),
          ("Contrast, CLI-equipped agent (W2): full inbound email body returned in tool `output` (class A)", "w2", "RE:CAMILA", "output", r"From: Camila Acosta", 900)]
    for label, w, tid, field, pat, width in EX:
        df = T[w]
        if tid.startswith("RE:"):
            r = df[df.output.fillna("").str.contains(r"From: Camila Acosta[^\n]*\n\s*To:", regex=True)].iloc[0]
        else:
            r = df[df.turn_id == tid].iloc[0]
        txt = r[field] or ""; m = re.search(pat, txt); st = m.start() if m else 0
        ts = pd.Timestamp(r.created_at)
        ag = names.get(s2a.get(r.session_id))
        L.append(f"### {label}\n\n- turn `{r.turn_id}`, session `{r.session_id}`, agent {ag}, {v.fmt_ts(ts)}, field `{field}`, [deep link]({v.deep_link(ts)})\n\n```\n{txt[st:st+width]}\n```\n")
    L.append("## Verdict\n")
    L.append(VERDICT)
    (OUT / "inbound_email_probe.md").write_text("\n".join(L))

if __name__ == "__main__":
    main()
