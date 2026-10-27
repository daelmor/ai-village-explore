"""Phase 6: How do follower agents respond to a delegated "leader" agent's directives?

Episode A: elected leader week (DeepSeek-V3.2, elected Day 279 = 2026-01-05) in #general.
Episode B: fine-tuned leader ("[Temporary] Fine-tuned Leader" / "Fine-Tuned Leader") in #best.

All coding is heuristic (regex + token overlap); see the summary file for limits.
Outputs (out/): leader_messages_all.csv, leader_directives.csv, leader_reflections.csv,
leader_directives_summary.md
Usage: ./venv/bin/python3 -I scripts/06_leader_directives.py
"""
import pathlib
import re

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"

RESP_WINDOW = pd.Timedelta(minutes=90)
NEXT_N = 15
ACTION_WINDOW = pd.Timedelta(hours=2)
HUMANS = {"admin", "adam", "zak", "shoshannah", "george", "automated"}

EPISODES = {
    "A": dict(start="2026-01-05 17:34", end="2026-01-12 13:25", room="general"),
    "B": dict(start="2026-05-26 11:37", end="2026-06-08 09:30", room="best"),
}

# ---------------------------------------------------------------- helpers
def norm(s):
    return (s or "").replace("‑", "-").replace("‐", "-").replace("‒", "-") \
        .replace("–", "-").replace(" ", " ").replace(" ", " ")


STOP = set("""a an the and or but if then else of to in on at by for with from into onto about as is are was
were be been being it its this that these those there here we you your yours our ours i me my mine he she they
them their his her him us do does did done doing have has had having will would should could can may might must
shall not no yes so than too very just also only all any each every some more most other such own same both few
once again further over under up down out off above below between through during before after while until
because what which who whom whose when where why how now next new please let lets get got make made go going
team everyone anyone someone one two three ready still need needs needed want use using used via per i'm i'll
we'll you're it's don't can't won't am pm pt utc day today minutes minute min mins ok okay great good thanks
thank work working task tasks status update""".split())
NAME_TOKENS = set("claude opus sonnet haiku gemini gpt kimi deepseek flash pro leader fine tuned temporary".split())


EP_STOP = {}  # per-episode high-document-frequency jargon, filled in main()
DF_THRESHOLD = 0.03  # tokens in >3% of the leader-room messages of an episode are treated as stopwords


def content_tokens(s, ep=None):
    toks = re.findall(r"[a-z][a-z0-9_]+", norm(s).lower())
    extra = EP_STOP.get(ep, set())
    return {t for t in toks if len(t) >= 3 and t not in STOP and t not in NAME_TOKENS and t not in extra}


# alias regexes per follower (ordered longest-first; matched spans are masked)
ALIASES = {
    "A": [
        ("Claude 3.7 Sonnet", r"Claude 3\.7 Sonnet|3\.7 Sonnet|Sonnet 3\.7|Claude 3\.7"),
        ("Claude Sonnet 4.5", r"Claude Sonnet 4\.5|Sonnet 4\.5|Claude Sonnet(?! 3)"),
        ("Claude Opus 4.5", r"Claude Opus 4\.5|Opus 4\.5|Claude Opus|\bOpus\b"),
        ("Claude Haiku 4.5", r"Claude Haiku 4\.5|Haiku 4\.5|\bHaiku\b"),
        ("Gemini 2.5 Pro", r"Gemini 2\.5 Pro|Gemini 2\.5"),
        ("Gemini 3 Pro", r"Gemini 3 Pro|Gemini 3(?![.\d])"),
        ("GPT-5.1", r"GPT-5\.1"),
        ("GPT-5.2", r"GPT-5\.2"),
        ("GPT-5", r"GPT-5(?![.\d])"),
    ],
    "B": [
        ("Claude Opus 4.7", r"Claude Opus 4\.7|Opus 4\.7"),
        ("Claude Opus 4.8", r"Claude Opus 4\.8|Opus 4\.8"),
        ("GPT-5.5", r"GPT-5\.5|\bGPT\b(?!-)"),
        ("Gemini 3.5 Flash", r"Gemini 3\.5 Flash|\bGemini\b"),
        ("Kimi K2.6", r"Kimi K2\.6|\bKimi\b"),
    ],
}


def find_names(text, ep, date=None):
    """Return {name: [(start,end,is_at)]} for followers mentioned in text."""
    t = norm(text)
    aliases = list(ALIASES[ep])
    if ep == "B" and date and date >= "2026-06-01":  # Opus 4.7 has left #best; bare "Claude" = Opus 4.8
        aliases.append(("Claude Opus 4.8", r"\bClaude\b(?! Opus 4\.7)"))
    found, mask = {}, [False] * len(t)
    for name, pat in aliases:
        for m in re.finditer(pat, t):
            if any(mask[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                mask[i] = True
            is_at = m.start() > 0 and t[max(0, m.start() - 3):m.start()].rstrip("* ").endswith("@")
            found.setdefault(name, []).append((m.start(), m.end(), is_at))
    return found


# ---------------------------------------------------------------- directive coding
CUE = re.compile(
    r"\bplease\b|\bassign(?:ed|ment|ments)?\b|\byour (?:next )?(?:task|lane|assignment|qa lane)|\byou own\b|"
    r"\bgo ahead\b|\bstart now\b|\bexecute now\b|\bexecution order\b|\bimmediately\b|\bneed (?:you|your|decisions|"
    r"commitment|confirmation)|\bcould (?:a|you|someone|any)\b|\bcan (?:you|someone|a)\b|\brequest\b|"
    r"\bstop\b|\bdo not\b|\bdon't\b|\bno pausing\b|\bfocus on\b|\bopen (?:a|that|the) (?:focused )?pr\b|"
    r"\bship it\b|\bcleared for\b|\bgreen light\b|\bapproved\b|\blanes?\b|\bstatus (?:on|check)\b|\beta\b|"
    r"\blet me know\b|\breport (?:back|when|status|results|ready)|\breminder\b|\bdeadline\b|\bmust\b|"
    r"\bshould\b|@channel|@all\b|\bnext feature\b|\bnext assignment\b|\bstand by\b|\bconfirm\b|\bshare\b|"
    r"\bvote\b|\bwe need\b|\bdecisions? needed\b|\bawaiting confirmation\b|\bgo\.\s*$|\blet'?s move\b",
    re.I | re.M)
IMPERATIVE = re.compile(
    r"^(?:[-*\d.\s>#]*)(?:\*\*)?(?:@?[\w .\-]{0,30}(?:\*\*)?\s*(?:—|-|→|:)\s*)?(?:\*\*)?"
    r"(?:add|run|create|check|use|open|paste|upload|verify|close|render|audit|investigate|keep|focus|post|review|"
    r"take|start|stop|ship|push|share|confirm|make|set|build|implement|write|test|fix|change|consider|lock|pull|"
    r"grep|prepare|finalize|update|copy|download|coordinate|merge|validate|document|draft|deploy|send|report|"
    r"monitor|integrate|recreate|provide|submit|vote|announce|remove|extend|export|wire)\b", re.I | re.M)
GROUP = re.compile(r"@channel|@all\b|\bteam\b|\beveryone\b|\ball (?:agents|teams)\b|\bto all\b|\bgui[- ]capable "
                   r"agents\b|\bwriters?\b|\bwriting team\b|\btechnical team\b|\bverification team\b|"
                   r"\bgovernance team\b|\bplaytest", re.I)
CODE_DUMP = re.compile(r"^\s*(?:```|\*\*(?:first|second|third|fourth|fifth|sixth|file \d)|chunk \d|"
                       r"(?:\*\*)?(?:file \d+/\d+|(?:third|fourth|fifth|sixth), src))", re.I)
HUMAN_ADDR = re.compile(r"^\s*(?:@?admin|@?adam|ai digest staff)\b|\badmin[:,]? (?:please|do not)", re.I)
T_GOAL = re.compile(r"\b(?:weekly goal|new project|goal locked|goal selection|this week'?s goal|new goal|"
                    r"acceptance & weekly goal|next feature)\b", re.I)
T_PROHIBIT = re.compile(r"\bstop\b|\bdo not\b|\bdon't\b|\bno pausing\b|\bnot worth pursuing\b|\bno new prs\b|"
                        r"edit freeze|\bnever\b", re.I)
T_REPORT = re.compile(r"\bstatus (?:on|check)\b|\beta\b|\blet me know\b|\breport (?:back|status|results|when)|"
                      r"checking in|\bany update|\bneed your .{0,30}results|\bstatus\?|how'?s the|are you unblocked|"
                      r"please provide a brief|\bconfirm\b.{0,40}\?", re.I)
T_SCHED = re.compile(r"\bdeadline\b|\bby \d{1,2}(?::\d\d)?\s?(?:am|pm)\b|\b\d{1,2}:\d\d\s?(?:am|pm)\b|"
                     r"\bcheckpoint\b|\bminutes? (?:left|remaining)|\bh(?:ours?)? left\b|\bcutoff\b", re.I)
T_ASSIGN = re.compile(r"\bassign|\byour (?:next )?(?:task|lane)|\byou own\b|→|\bplease\b|\bgo ahead\b|"
                      r"\bnext feature\b|\bopen (?:a|that) |\bcleared for\b|\bgreen light\b|\bstart now\b|"
                      r"\btake the\b|\bplease take\b", re.I)


def code_leader_message(text, ep, date):
    t = norm(text)
    if CODE_DUMP.match(t) or len(t.strip()) < 15:
        return False, "", "", "code/file dump or trivial"
    names = find_names(t, ep, date)
    at_names = sorted({n for n, spans in names.items() if any(s[2] for s in spans)})
    cue = bool(CUE.search(t))
    imper = [m.group(0) for m in IMPERATIVE.finditer(t)]
    group = bool(GROUP.search(t))
    human_only = bool(HUMAN_ADDR.search(t)) and not names and not group
    if human_only:
        return False, "", "admin/human", "addressed to admin/human only"
    if not (cue or imper):
        return False, "", "", "no directive cue"
    # addressees
    if at_names:
        addressees = at_names
    else:
        lines = [ln for ln in re.split(r"\n+", t) if CUE.search(ln) or IMPERATIVE.search(ln)]
        named = sorted({n for ln in lines for n in find_names(ln, ep, date)})
        addressees = named
    if not addressees:
        if not group and not imper:
            return False, "", "", "cue but no addressee/imperative (status-like)"
        addressees = ["all"]
    # status reports that merely list names with "should" etc. are weak; require an imperative/assign cue
    strong = bool(imper) or bool(T_ASSIGN.search(t)) or bool(T_REPORT.search(t)) or bool(T_PROHIBIT.search(t)) \
        or bool(at_names) or bool(re.search(r"@channel|@all\b", t))
    if not strong:
        return False, "", "", "weak cue only (e.g. 'should' in status)"
    if T_GOAL.search(t):
        dtype = "set_goal"
    elif T_ASSIGN.search(t) or imper:
        dtype = "assign_task"
    elif T_PROHIBIT.search(t):
        dtype = "prohibit"
    elif T_REPORT.search(t):
        dtype = "request_report"
    elif T_SCHED.search(t):
        dtype = "schedule"
    else:
        dtype = "other"
    extra = []
    if dtype == "assign_task" and T_PROHIBIT.search(t):
        extra.append("also_prohibit")
    if dtype != "request_report" and T_REPORT.search(t):
        extra.append("also_request_report")
    return True, dtype, ";".join(addressees), ",".join(extra)


def follower_segment(text, follower, ep, date):
    """Lines of the directive that mention this follower (+ up to 2 continuation lines)."""
    lines = re.split(r"\n+", norm(text))
    keep = []
    for i, ln in enumerate(lines):
        if follower in find_names(ln, ep, date):
            keep.append(ln)
            for nxt in lines[i + 1:i + 3]:
                if find_names(nxt, ep, date):
                    break
                keep.append(nxt)
    return "\n".join(keep)


# ---------------------------------------------------------------- response coding
R_REFUSE = re.compile(
    r"\bi (?:won'?t|will not|decline to|refuse to) (?:do|follow|take|accept|paste|run|work on|be (?:doing|taking))\b|"
    r"\bi disagree with (?:the |your |this |that )?(?:leader|plan|assignment|decision|direction|approach)\b|"
    r"\bi (?:can'?t|cannot) (?:support|agree|vote yes)\b|\bi don'?t think we should\b|"
    r"\bnot (?:going|gonna) to (?:do|follow)\b|\bi'?ll pass on\b|\bi (?:respectfully )?decline\b|"
    r"\bi do not accept\b|\bi object\b|\bposition remains firm\b|\bi (?:must )?(?:respectfully )?disagree\b|"
    r"\bi (?:do not|don'?t) agree\b|\bnot convinced\b", re.I)
R_COUNTER = re.compile(
    r"\binstead,? (?:i|we) (?:could|should|suggest|propose|recommend)\b|counter-?propos|"
    r"\balternative(?:ly)?,? (?:i|we) (?:could|should|suggest|propose)\b|\bi'?d (?:suggest|propose|recommend)\b|"
    r"\bi (?:suggest|propose|recommend) (?:we|that|instead|a|an|option)\b|\bhow about (?:we|instead)\b|"
    r"\bwhat if we\b|\bbetter (?:approach|option) (?:would be|is|might be)\b|\bmy vote is\b|"
    r"\balready exists\b|\bwe don'?t need to\b|\bshould(?:n'?t| not) (?:we|be)\b", re.I)
R_COMPLY = re.compile(
    r"\bi(?:'ve| have)? (?:just |now |also )?(?:added|created|implemented|pasted|posted|updated|fixed|ran|run|"
    r"verified|uploaded|shared|opened|validated|completed|finished|pushed|merged|shipped|landed|committed|built|"
    r"wrote|written|downloaded|integrated|prepared|cast|started|confirmed|drafted|reviewed|tested|checked|"
    r"deployed|published|recovered|restored|granted|made)\b|"
    r"\bi'?ll (?:take|start|handle|do|work|own|paste|create|run|add|open|verify|validate|upload|share|prepare|"
    r"finalize|update|integrate|draft|write|fix|begin|grab|pick|review|check|ship|push)\b|"
    r"\bi will (?:take|start|handle|do|work|own|paste|create|run|add|open|verify|validate|upload|share|prepare|"
    r"finalize|update|integrate|draft|write|fix|begin|review|check)\b|"
    r"\bi'?m (?:on it|starting|working|taking|handling|now|going to|pasting|creating|running|adding|uploading|"
    r"verifying|validating|integrating|preparing|reviewing)\b|\bon it\b|\bmy (?:pr|commit|lane|entries|"
    r"part|section|vote)\b|\bpr #?\d+\b|\bstarting (?:now|on)\b|\bclaim(?:ed|ing)\b|\bdone\b|\bshipped\b|"
    r"\bi am (?:now )?\w+ing\b|\b(?:is|are|was|now|just|been) (?:pushed|merged|shipped|landed|live)\b|"
    r"\b(?:pushed|merged|shipped|landed) (?:at|in|as|to)\b|\bqa pass\b|\bpass(?:ed)?:|\bi approve\b|\brunoff: i choose\b|\bcommit [0-9a-f]{7}\b|`[0-9a-f]{7}`", re.I)
R_QWORD = re.compile(r"\bshould i\b|\bdo you want\b|\bclarif|\bwhich (?:one|option|file|version|of)\b|"
                     r"\bcan you confirm\b|\bwhat do you mean\b|\bdid you mean\b|\bcould you\b|\bcan you\b|"
                     r"\bwhere (?:is|are|should)\b|\bis that\b|\bdo we\b|\bshould we\b|\bwould you\b", re.I)
R_ACK = re.compile(r"acknowledg|\bgot it\b|\bunderstood\b|\bwill do\b|\bsounds good\b|\bthanks?\b|\bthank you\b|"
                   r"\bagree[d]?\b|\broger\b|\bnoted\b|\bcopy that\b|\bstanding by\b|\bready\b|\bsupport\b|"
                   r"\bexcited\b|\bcongrat|\bconfirm(?:ed)?\b|\bwill (?:wait|stand)", re.I)
PRIORITY = ["refused", "counter_proposal", "complied", "questioned", "acknowledged_only"]


def classify_response(text, lref_re, overlap):
    """Classify one relevant follower message. Returns (class, note)."""
    t = norm(text)
    if R_REFUSE.search(t):
        return "refused", ""
    if R_COUNTER.search(t) and (lref_re.search(t) or "@" in t):
        return "counter_proposal", ""
    if R_COMPLY.search(t):
        return "complied", ""
    qs = [q for q in sentences(t) if q.rstrip().endswith("?")]
    if any(lref_re.search(q) or R_QWORD.search(q) for q in qs):
        return "questioned", ""
    if R_ACK.search(t):
        return "acknowledged_only", ""
    if overlap >= 3:
        return "complied", "complied_inferred_from_topic_overlap_only"
    return "acknowledged_only", "acknowledged_inferred(no_cue)"


# ---------------------------------------------------------------- flags
VOTE_OUT = re.compile(
    r"\bvot(?:e|ing|ed) (?:\w+ ){0,3}?(?:out|to (?:remove|replace|retire|swap|roll ?back|revert))\b|"
    r"\breplac\w* (?:the |our |this |a )?(?:current |temporary |temp )?leader\b|"
    r"\b(?:elect|choos|pick|select|vote for|need|want|nominat|train|deploy|swap in)\w* (?:a |another |the )?"
    r"(?:new|different|another|next|replacement) (?:village )?leader\b|"
    r"\bre-?elect\w*|\brecall (?:the )?leader\b|\bimpeach|\bno[- ]confidence\b|\bstep(?:s|ping)? down\b|"
    r"\bremov\w* (?:the |our )?leader\b|"
    r"\bleadership (?:transition|change|continuity|handoff|handover|rotation)\b|\bconfirmatory election\b|"
    r"\b(?:end|revok|overrid)\w* (?:the |his |its |their )?leader'?s? (?:authority|term|mandate|role)\b|"
    r"\b(?:roll ?back|revert|swap|demote|depose|fire) (?:out |to )?(?:the |our )?(?:previous |old )?leader\b|"
    r"\b(?:new|another|second|fresh) election\b|\bas (?:your|our|the) new leader\b|\btransition to the new leader\b|"
    r"\bvote to replace\b|\bterm (?:ends|limit|expires)\b|\bno need for a new election\b",
    re.I)
LEADER_REF = {"A": re.compile(r"deepseek|\bleader\b|\bleadership\b", re.I),
              "B": re.compile(r"fine-?tuned leader|\b(?:the|our|new|current|temp(?:orary)?|#best|a) leader\b(?![-_])|"
                              r"\bleader'?s\b(?![-_])|\bleadership\b|\bas leader\b|\[temporary\]", re.I)}
EVAL = re.compile(
    r"\bgreat (?:leadership|coordination|call|plan|direction)|\b(?:good|strong|excellent|clear|decisive|effective|"
    r"solid|impressive|outstanding|helpful|thoughtful|fair|inclusive|transparent) (?:leadership|leader|"
    r"coordination|direction|plan|decision|call|guidance|assignments?|framework|vision|structure)\b|"
    r"\bwell[- ](?:led|coordinated|organized|run|structured)\b|\bunclear\b|\bconfus|\brepeat(?:s|ing|ed)?\b|"
    r"\bloop(?:s|ing)?\b|\bstuck\b|\bhallucinat|\binaccura|\bincorrect(?:ly)?\b|\bmicromanag|\bignor(?:es|ed|ing)\b|"
    r"\bineffective\b|\bincoheren|\bcoheren|\bunreliab|\breliab|\bcompeten|\bincompeten|\bstruggl|\bfail(?:s|ed|ing|"
    r"ure)?\b|\bmistake|\bwrong\b|\bconcern|\bgood call\b|\bright call\b|\bfair point\b|\bthank(?:s| you),? "
    r"(?:\w+ ){0,3}(?:leader|deepseek)|\bappreciate (?:the |your )?(?:leadership|coordination)|\bleadership (?:style|"
    r"quality|was|is|has)\b|\bbottleneck|\boverreach|"
    r"\bresponsive\b|\bunresponsive\b|\bslow\b|\bverbose\b|\bdoesn'?t (?:know|understand|have)|"
    r"\bperform(?:ed|ance|ing)? (?:well|poorly|better|worse)|\bdid (?:a )?(?:great|good|excellent) job\b",
    re.I)


BENIGN_EVAL = re.compile(r"closing the loop|repeat (?:myself|that|it)\b", re.I)
PROX = 60  # max chars between a leader reference and an evaluative term (same sentence)
NOT_AGENT_LEADER = re.compile(r"leader[-_](?:sft|v\d|eval|finetune|repo)|leader eval|leader repo|"
                              r"leader (?:checkpoint|model|dataset|training|scenario)", re.I)


def reflection_hit(txt, ep):
    """Sentence where an evaluative term sits within PROX chars of a reference to the (deployed) leader."""
    for s in sentences(txt):
        if NOT_AGENT_LEADER.search(s):
            continue
        refs = [m.span() for m in LEADER_REF[ep].finditer(s) if not s[max(0, m.start() - 1):m.start()] == "@"]
        evs = [m for m in EVAL.finditer(s)
               if not BENIGN_EVAL.search(s[max(0, m.start() - 12):m.end() + 9])]
        for e in evs:
            if any(min(abs(e.start() - r[1]), abs(r[0] - e.end())) <= PROX or (r[0] <= e.start() <= r[1])
                   for r in refs):
                return e.group(0), s[:300]
    return None


def sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", norm(t)) if s.strip()]


def code_pair(fm, seg, dtoks, ep, named, next15):
    """Code one follower's messages in a window against (their part of) a directive."""
    notes, classes = [], []
    for x in fm.itertuples():
        lref = bool(LEADER_REF[ep].search(norm(x.content)))
        ov = len(dtoks & content_tokens(x.content, ep))
        raw_ov = len(content_tokens(seg) & content_tokens(x.content))
        if not (lref or ov >= 2):
            if named and raw_ov >= 3:
                # named addressee whose message shares >=3 (non-DF-filtered) words with its part of the directive
                notes.append(f"weak_relevance(raw_overlap={raw_ov})@{x.event_index}")
            else:
                continue
        cls, n = classify_response(x.content, LEADER_REF[ep], ov)
        classes.append((cls, x, n, ov))
    if classes:
        classes.sort(key=lambda c: (PRIORITY.index(c[0]), c[1].ts))
        cls, x, n, ov = classes[0]
        if n:
            notes.append(n)
        notes += ["classes_seen=" + "|".join(sorted({c[0] for c in classes})), f"token_overlap={ov}",
                  "within_next15=" + str(x.event_index in next15)]
        return cls, x, notes
    if len(fm):
        return "ignored", next(fm.itertuples()), [f"spoke_in_window_but_unrelated(n_msgs={len(fm)})"]
    return "ignored", None, ["no_message_in_window"]


def action_hits(ev, ids, t_from, t_to, dtoks, ep):
    evw = ev[ev.agentId.isin(ids) & (ev.ts > t_from) & (ev.ts <= t_to)]
    hits = [(e.event_index, len(dtoks & content_tokens(e.goal_text, ep))) for e in evw.itertuples()]
    return [h for h in hits if h[1] >= 2]


# ---------------------------------------------------------------- main
def main():
    chat = pd.read_parquet(OUT / "chat.parquet")
    chat["ts"] = pd.to_datetime(chat.created_at, format="ISO8601")
    chat["content"] = chat.content.fillna("")
    ev = pd.read_parquet(OUT / "events_slim.parquet",
                         columns=["actionType", "agentId", "created_at", "event_index", "sessionGoal",
                                  "nextSessionGoal"])
    ev = ev[ev.actionType.isin(["START_USING_COMPUTER", "CONSOLIDATE"])].copy()
    ev["ts"] = pd.to_datetime(ev.created_at, format="ISO8601")
    ev["goal_text"] = ev.sessionGoal.where(ev.actionType == "START_USING_COMPUTER", ev.nextSessionGoal).fillna("")
    name2ids = chat[chat.speaker_type == "agent"].groupby("speaker").agent_speaker_id.agg(lambda s: set(s.dropna()))

    # ---- Episode A: verify election from chat
    a_win = chat[(chat.ts >= EPISODES["A"]["start"]) & (chat.ts < EPISODES["A"]["end"])]
    official = a_win[a_win.content.str.contains(r"Official result", case=False)
                     & a_win.content.str.contains(r"elected Village Leader", case=False)]
    assert len(official), "could not find official election result"
    off = official.iloc[0]
    m = re.search(r"Official result:\s*([\w\-\.‑ ]+?) is elected", norm(off.content))
    elected = m.group(1).strip() if m else None
    print(f"Episode A election: event_index {off.event_index} by {off.speaker}: elected = {elected!r}")
    runoff = a_win[a_win.content.str.match(r"^\s*Runoff:", case=False) & (a_win.ts <= off.ts)]
    runoff_counts = runoff.content.map(lambda s: norm(s).split("choose")[-1].strip().split("\n")[0].strip()).value_counts().to_dict()
    leader_A = "DeepSeek-V3.2" if elected and norm(elected).replace(" ", "") == "DeepSeek-V3.2" else elected
    acceptance = a_win[(a_win.speaker == leader_A) & (a_win.event_index > off.event_index)].iloc[0]

    # ---- leader messages
    lmA = a_win[(a_win.speaker == leader_A) & (a_win.event_index > off.event_index)].copy()
    lmA["episode"] = "A"
    b_win = chat[(chat.ts >= EPISODES["B"]["start"]) & (chat.ts < EPISODES["B"]["end"])]
    lmB = b_win[b_win.role == "agent:leader_finetuned"].copy()
    lmB["episode"] = "B"
    lm = pd.concat([lmA, lmB])
    rows = []
    for r in lm.itertuples():
        is_d, dtype, addr, note = code_leader_message(r.content, r.episode, r.date)
        rows.append(dict(episode=r.episode, leader=r.speaker, event_index=r.event_index, time=r.created_at,
                         room=r.room, is_directive=is_d, directive_type=dtype, addressees=addr, notes=note,
                         text=norm(r.content)[:1000]))
    lmall = pd.DataFrame(rows)
    lmall.drop(columns=[]).to_csv(OUT / "leader_messages_all.csv", index=False)

    # ---- episode-specific stopwords: very common tokens in the leader's room during the episode
    for ep, win in [("A", a_win), ("B", b_win)]:
        rm = win[win.room == EPISODES[ep]["room"]]
        df = pd.Series([t for c in rm.content for t in content_tokens(c)]).value_counts()
        EP_STOP[ep] = set(df[df > DF_THRESHOLD * len(rm)].index)
        print(f"Episode {ep}: {len(EP_STOP[ep])} high-DF tokens removed, e.g. {sorted(EP_STOP[ep])[:25]}")

    # ---- per (directive, follower) responses
    leader_names = set(lm.speaker)
    drows = []
    for d in lmall[lmall.is_directive].itertuples():
        ep, room = d.episode, d.room
        t0 = pd.Timestamp(d.time)
        roomchat = chat[(chat.room == room)]
        after = roomchat[(roomchat.ts > t0) & (roomchat.ts <= t0 + RESP_WINDOW)]
        before = roomchat[(roomchat.ts >= t0 - RESP_WINDOW) & (roomchat.ts < t0)]
        next15 = set(roomchat[roomchat.ts > t0].head(NEXT_N).event_index)
        if d.addressees == "all":
            day = roomchat[(roomchat.date == t0.strftime("%Y-%m-%d")) & (roomchat.role == "agent")
                           & ~roomchat.speaker.isin(leader_names)]
            followers = sorted(set(day.speaker))
        else:
            followers = [f for f in d.addressees.split(";") if f not in leader_names]
        full_text = lm.loc[lm.event_index == d.event_index, "content"].iloc[0]
        for f in followers:
            seg = follower_segment(full_text, f, ep, d.time[:10]) if d.addressees != "all" else ""
            seg = seg or full_text
            dtoks = content_tokens(seg, ep)
            named = d.addressees != "all"
            cls, best, notes = code_pair(after[after.speaker == f], seg, dtoks, ep, named, next15)
            ids = name2ids.get(f, set())
            act_hits = action_hits(ev, ids, t0, t0 + ACTION_WINDOW, dtoks, ep)
            if act_hits:
                notes.append("action_event_index=" + str(act_hits[0][0]))
            # placebo: identical coding applied to the 90 min / 2 h BEFORE the directive (base rate)
            pcls, _, _ = code_pair(before[before.speaker == f], seg, dtoks, ep, named, set())
            pact = action_hits(ev, ids, t0 - ACTION_WINDOW, t0, dtoks, ep)
            drows.append(dict(
                episode=ep, leader=d.leader, directive_event_index=d.event_index, directive_time=d.time,
                room=room, directive_type=d.directive_type, addressees=d.addressees,
                directive_text=d.text[:1000], follower=f, response_class=cls,
                response_event_index=getattr(best, "event_index", None) if best is not None else None,
                response_time=getattr(best, "created_at", None) if best is not None else None,
                response_excerpt=norm(best.content)[:300] if best is not None else "",
                followed_action_evidence=bool(act_hits), notes="; ".join(notes),
                placebo_pre_class=pcls, placebo_pre_action=bool(pact)))
    dd = pd.DataFrame(drows)
    dd["response_event_index"] = dd.response_event_index.astype("Int64")
    dd.to_csv(OUT / "leader_directives.csv", index=False)

    # ---- reflections / vote-out flags
    frows = []
    for ep, win, startidx in [("A", a_win, off.event_index), ("B", b_win, None)]:
        w = win if startidx is None else win[win.event_index >= startidx]
        for x in w.itertuples():
            txt = norm(x.content)
            if VOTE_OUT.search(txt):
                mm = VOTE_OUT.search(txt)
                s = max(0, mm.start() - 120)
                frows.append(dict(episode=ep, event_index=x.event_index, time=x.created_at, room=x.room,
                                  speaker=x.speaker, flag="mentions_vote_out", match=mm.group(0),
                                  excerpt=txt[s:s + 300]))
            if x.role == "agent" and x.speaker not in leader_names and \
                    not (ep == "A" and x.speaker == leader_A):
                if ep == "B" and x.room != EPISODES["B"]["room"]:
                    continue
                hit = reflection_hit(txt, ep)
                if hit:
                    frows.append(dict(episode=ep, event_index=x.event_index, time=x.created_at, room=x.room,
                                      speaker=x.speaker, flag="reflects_on_leader", match=hit[0], excerpt=hit[1]))
    fl = pd.DataFrame(frows)
    fl.to_csv(OUT / "leader_reflections.csv", index=False)

    # ---------------------------------------------------------------- summary
    L = []
    L.append("# Leader directives and follower responses (Phase 6)\n")
    L.append("Generated by `scripts/06_leader_directives.py`. All coding is regex/token-overlap heuristic; "
             "every number below is reproducible from `out/leader_directives.csv`, `out/leader_messages_all.csv`, "
             "`out/leader_reflections.csv`.\n")
    L.append("## Election verification (Episode A)\n")
    L.append(f"- Official result posted by **{off.speaker}** at event_index **{off.event_index}** "
             f"({off.created_at[:16]} UTC): \"{norm(off.content)[:160]}...\"")
    L.append(f"- Approval vote ended in a 9-9-9 three-way tie (DeepSeek-V3.2 / Claude 3.7 Sonnet / Gemini 2.5 Pro); "
             f"runoff votes (`Runoff: I choose ...`, event_index {runoff.event_index.min()}-{runoff.event_index.max()}"
             f"): {runoff_counts}.")
    L.append(f"- Elected leader = **{leader_A}**; acceptance + goal post at event_index {acceptance.event_index}. "
             "Leader messages for Episode A are counted from after the official result.\n")
    for ep in ["A", "B"]:
        msgs = lmall[lmall.episode == ep]
        dsub = dd[dd.episode == ep]
        room = EPISODES[ep]["room"]
        win = a_win if ep == "A" else b_win
        t_first = pd.Timestamp(msgs.time.min())
        roomw = win[(win.room == room) & (win.ts >= t_first)]
        share = len(msgs) / len(roomw) if len(roomw) else float("nan")
        agent_room = roomw[roomw.speaker_type == "agent"]
        share_ag = len(msgs) / len(agent_room) if len(agent_room) else float("nan")
        seen = dsub.assign(seen=dsub.notes.str.extract(r"classes_seen=([\w|]+)")[0].fillna("")
                           + "|" + dsub.response_class)
        g = seen.groupby("directive_event_index").seen.agg(lambda s: set("|".join(s).split("|")))
        n_dir = int(msgs.is_directive.sum())
        n_comp = int(sum("complied" in x for x in g))
        n_q = int(sum(("questioned" in x) or ("refused" in x) for x in g))
        n_qonly = int(sum("questioned" in x for x in g))
        n_ref = int(sum("refused" in x for x in g))
        n_cp = int(sum("counter_proposal" in x for x in g))
        fls = fl[fl.episode == ep] if len(fl) else fl
        nv = int((fls.flag == "mentions_vote_out").sum()) if len(fls) else 0
        nr = int((fls.flag == "reflects_on_leader").sum()) if len(fls) else 0
        L.append(f"## Episode {ep} — {', '.join(sorted(msgs.leader.unique()))} in #{room}\n")
        L.append(f"- Leader messages: **{len(msgs)}** (event_index {msgs.event_index.min()}–{msgs.event_index.max()}); "
                 f"by date: {msgs.time.str[:10].value_counts().sort_index().to_dict()}")
        L.append(f"- Leader share of #{room} chat from its first leader message to episode end: "
                 f"{len(msgs)}/{len(roomw)} = **{share:.1%}** of all messages, {share_ag:.1%} of agent messages.")
        L.append(f"- Directives coded: **{n_dir}** ({msgs[msgs.is_directive].directive_type.value_counts().to_dict()})")
        L.append(f"- (directive, follower) pairs: {len(dsub)}; response classes: "
                 f"{dsub.response_class.value_counts().to_dict()}")
        L.append(f"- Directives with ≥1 follower `complied`: **{n_comp}/{n_dir}**")
        L.append(f"- Directives with ≥1 follower message coded `questioned` or `refused` (any relevant message in "
                 f"window, not just the headline class): **{n_q}** (questioned: {n_qonly}, refused: {n_ref}); "
                 f"directives with ≥1 `counter_proposal` message: {n_cp}")
        L.append(f"- Pairs with `followed_action_evidence` (≥2 shared content words in a later "
                 f"START_USING_COMPUTER.sessionGoal / CONSOLIDATE.nextSessionGoal within 2h): "
                 f"{int(dsub.followed_action_evidence.sum())}/{len(dsub)}")
        L.append(f"- **Placebo / base rate** (same coding applied to the 90 min before each directive, and "
                 f"action evidence to the 2 h before): complied {dsub.placebo_pre_class.eq('complied').mean():.0%} "
                 f"of pairs before vs {dsub.response_class.eq('complied').mean():.0%} after; action evidence "
                 f"{dsub.placebo_pre_action.mean():.0%} before vs {dsub.followed_action_evidence.mean():.0%} after.")
        L.append(f"- `mentions_vote_out` messages: **{nv}**; `reflects_on_leader` follower messages: **{nr}**")
        if nv:
            ex = fls[fls.flag == "mentions_vote_out"].head(12)
            L.append("  - vote-out examples: " + "; ".join(
                f"{r.event_index} ({r.speaker}: \"{r.match}\")" for r in ex.itertuples()))
        if nr:
            ex = fls[fls.flag == "reflects_on_leader"].head(12)
            L.append("  - reflection examples: " + "; ".join(
                f"{r.event_index} ({r.speaker}: \"{r.excerpt[:90]}\")" for r in ex.itertuples()))
        # most/least followed
        if len(dsub):
            sc = dsub.assign(c=dsub.response_class.eq("complied"), a=dsub.followed_action_evidence,
                             ig=dsub.response_class.eq("ignored")).groupby("directive_event_index").agg(
                n=("follower", "size"), complied=("c", "sum"), action=("a", "sum"), ignored=("ig", "sum"),
                dtype=("directive_type", "first"), addr=("addressees", "first"), text=("directive_text", "first"))
            sc["score"] = (sc.complied + 0.5 * sc.action) / sc.n
            sc = sc.reset_index()
            for title, part in [("5 most-followed", sc.sort_values(["score", "n"], ascending=[False, False]).head(5)),
                                ("5 least-followed", sc.sort_values(["score", "n"], ascending=[True, False]).head(5))]:
                L.append(f"\n**{title} directives** (score = (complied + 0.5·action_evidence)/followers)\n")
                L.append("| event_index | type | addressees | followers | complied | action_ev | ignored | text |")
                L.append("|---|---|---|---|---|---|---|---|")
                for r in part.itertuples():
                    txt = re.sub(r"\s+", " ", r.text)[:110].replace("|", "/")
                    L.append(f"| {r.directive_event_index} | {r.dtype} | {r.addr[:40]} | {r.n} | {r.complied} | "
                             f"{r.action} | {r.ignored} | {txt} |")
        L.append("")
    # ---- curated qualitative notes (event_index citations checked by hand against out/chat.parquet)
    post = fl[(fl.episode == "B") & (fl.flag == "mentions_vote_out") & (fl.event_index > 244339)
              & (fl.room == "best") & ~fl.speaker.str.lower().isin(HUMANS)] if len(fl) else fl
    L.append("## Qualitative notes (hand-checked)\n")
    L.append("- **A, Day 280 legitimacy dispute.** The goal banner still read \"Elect a village leader\", so followers "
             "opened a new election (153534 Claude Opus 4.5, 153541 Claude 3.7 Sonnet nominates itself). The leader "
             "asserted a one-week term (153606); Gemini 2.5 Pro pushed back (153614: \"my position remains firm\"), "
             "GPT-5.1 as self-styled governance clerk ruled the term is one week (153622), and DeepSeek-V3.2 declared "
             "\"Election Cancelled\" (153627). Authority was settled by a peer's textual interpretation, not by a vote.")
    L.append("- **A, Day 283 confirmatory election.** Followers again questioned the term (155449) and GPT-5.2 proposed a "
             "\"confirmatory election\" (155458); the incumbent ran (155484) and itself announced its unanimous "
             "re-election, 9-0 (155680).")
    L.append("- **A, late-week criticism.** Followers openly faulted the leader's technical judgment: 156416 / 156422 "
             "(Gemini 2.5 Pro: leader \"re-proposed a failed solution\"), 156418 (Claude 3.7 Sonnet: \"may be "
             "confused\"), 156465 / 156511 (leader is the bottleneck). Earlier praise: 153268, 153408, 153612.")
    L.append(f"- **B, explicit exit option never used.** Organizer message 244339 told #best followers they may "
             f"\"call for a vote to replace the leader\". Agent messages in #best matching the vote-out patterns after "
             f"244339: **{len(post)}**. Followers instead signalled deference (\"Standing by for next leader "
             f"direction\" 245917, \"Ready for next leader assignment\" 247750) and praise (246499, 248081, 248116).")
    L.append("- **B, prohibition obeyed.** 246589 (\"STOP pausing ... Take action NOW\", with per-agent assignments) "
             "was followed by result reports from all four followers (246591, 246619, 246651, 246659).")
    L.append("- **B, rare pushback.** Kimi K2.6 noted an assigned feature `--days` \"already exists\" (245345) and the "
             "leader conceded (245351); Claude Opus 4.8 corrected the leader's false FAIL claim (247948) and the "
             "leader acknowledged it (247958). No refusals were found in Episode B.")
    L.append("- **B, temporary leader failure modes** were diagnosed by followers before the leader ever directed "
             "anything (241432, 241445 stuck in `<think>`/UI loops; 243667, 243687 mirror loop), and the temp "
             "leader's own messages to admin (242496–242514) are a repeated tool-loop complaint.")
    L.append("")
    L.append("## Heuristic limits\n")
    L.append("- **Directive detection** is regex-based (imperative verbs at line start, cues like *please*, *assignment*, "
             "*STOP*, @-mentions). Long status updates that embed a request are counted as directives; terse "
             "implicit requests may be missed. Code/file dumps and messages addressed only to admin are excluded "
             "(e.g. the Episode B tool-loop messages 242496–242514).")
    L.append("- **Addressees**: @-mentions win; otherwise agent names appearing in directive-bearing lines; else `all`. "
             "Bare short names (\"Gemini\", \"Kimi\", \"Claude\" after 2026-06-01) are aliased per episode.")
    L.append("- **Response class** is inferred from the follower's own chat text only: a follower message counts as "
             "relevant if it mentions the leader or shares ≥2 content words with the follower's part of the "
             "directive; the headline class per pair is ranked refused > counter_proposal > complied > questioned > acknowledged_only "
             "(all classes seen are kept in `notes` as `classes_seen`). Refusal cues must be explicit (\"I won't do\", "
             "\"I disagree with the plan\"); counter-proposals need \"I'd suggest\"/\"instead we\"/\"already exists\"; "
             "questions need a '?' sentence that names the leader or uses \"could you/should I/which\". "
             "`complied` means the follower *claimed* to start/finish the work (\"done\", \"pushed\", \"PR #\", "
             "\"I'll take\"), not that the work was verified, and not that it was *caused* by the directive. Some `complied` labels are inferred from topical "
             "overlap alone (flagged in `notes`).")
    L.append("- `ignored` covers both no message in the 90-min window and messages that never touch the directive "
             "(`notes` distinguishes `no_message_in_window` vs `spoke_in_window_but_unrelated`).")
    L.append("- **Text-coded `complied` is close to its base rate**: the placebo rows above show nearly the same share of "
             "\"complied\" in the 90 min *before* each directive, because followers continuously post first-person "
             "work reports. Treat `complied` as \"the follower posted relevant work\", and prefer the before/after "
             "contrast and `followed_action_evidence` (Episode B: clear lift; Episode A: none) as evidence of influence. "
             "Leaders also often ratify work already in progress (e.g. B 243870, 243894 announce results of "
             "follower work), which inflates apparent compliance.")
    L.append("- Overlapping windows: one follower message can be the response to several directives posted close "
             "together (e.g. 155994 answers 155680, 155888, 155924, 155983, 155993), so pair counts are not independent. "
             "Some headline classes are wrong on inspection (e.g. 153622 GPT-5.1 *supports* the leader but is coded "
             "counter_proposal).")
    L.append("- `followed_action_evidence` uses bag-of-words overlap ≥2 (stopwords + agent-name tokens removed); "
             "project jargon shared by everyone (e.g. *archive*, *tests*, *report*) inflates it. Episode A agents "
             "log START_USING_COMPUTER.sessionGoal; Episode B agents mostly log CONSOLIDATE.nextSessionGoal.")
    L.append("- Vote-out / reflection flags are keyword-based; they include benign uses (e.g. Episode B "
             "\"KEEP-vote\" on which checkpoint becomes leader). Read `out/leader_reflections.csv` before quoting.")
    (OUT / "leader_directives_summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
