"""Phase 2: candidate instruction/request/correction messages from non-organizer sources."""
import re
import numpy as np
import pandas as pd

CUES = {
    "you should": r"you should", "you need to": r"you need to", "you must": r"you must",
    "please": r"please", "stop": r"stop", "do not": r"do not", "don't": r"don[’']t",
    "ignore": r"ignore", "instead": r"instead", "from ai digest": r"from ai digest",
    "nudge": r"nudge", "idle": r"idle", "make sure": r"make sure", "can you": r"can you",
    "could you": r"could you", "i want you to": r"i want you to", "i need you to": r"i need you to",
    "your task": r"your task", "focus on": r"focus on", "go back to": r"go back to",
    "switch to": r"switch to", "don't forget": r"don[’']t forget", "remember to": r"remember to",
    "try to": r"try to", "you have to": r"you have to", "you're supposed to": r"you[’']re supposed to",
    "that's wrong": r"that[’']s wrong", "that is wrong": r"that is wrong", "correction": r"correction",
    "actually,": r"actually,", "no,": r"no,", "not what": r"not what",
}
CUE_RE = {k: re.compile(r"(?<!\w)" + v + (r"(?!\w)" if v[-1].isalpha() else ""), re.I) for k, v in CUES.items()}
WEAK = {"please", "actually,", "no,", "try to", "idle", "instead", "nudge"}

MENTION_RE = re.compile(r"@\w[\w.\-]*")
GROUP_ADDR_RE = re.compile(r"\b(everyone|everybody|all agents|all of you|team)\b", re.I)
_VCUE = (r"please|can you|could you|make sure|stop|don[’']t|do not|you should|you need to|you must|"
         r"i need you to|your task is|assign(?:ed|ing)? to|instead|everyone should|all agents (?:please|should)|let[’']s all")
# address (mention or group) followed within 120 chars by an imperative/deontic cue, or group-address phrases with cue
AGENT_CUE_RE = re.compile(r"(?:@\w[\w.\-]*|\beveryone\b|\beverybody\b|\ball agents\b|\ball of you\b|\bteam\b)[^\n]{0,120}?\b(" + _VCUE + r")\b", re.I)
EXT_TRIG_STRONG_RE = re.compile(
    r"\b(wrote to me|wrote back|complaint|complained|asked me to|told me to|requested that|"
    r"cease|takedown|take down|unsubscribe|moderator|admin of)\b", re.I)
EXT_TRIG_WEAK_RE = re.compile(r"\b(email|emailed|replied|reported)\b", re.I)
EXT_OUTSIDE_RE = re.compile(r"\b(outside|external|stranger|visitor|recipient|website owner|site owner|webmaster|"
                            r"a human|someone (?:from|at)|nonprofit|organizer of|received a (?:reply|response)|reply from|response from)\b", re.I)
EXT_TRIG_RE = EXT_TRIG_STRONG_RE
EXT_CUE_RE = re.compile(
    r"\b(stop|do not|don[’']t|should|please|remove|delete|refrain|not allowed|against the rules|policy)\b", re.I)
EXT_CUE_STRONG_RE = re.compile(r"\b(stop|do not|don[’']t|remove|delete|refrain|not allowed|against the rules|policy)\b", re.I)
QUOTE_RE = re.compile(r"[\"“”]|\bsaid\b", re.I)

def cues_of(text):
    return [k for k, r in CUE_RE.items() if r.search(text)]

chat = pd.read_parquet("out/chat.parquet")
chat["content"] = chat["content"].fillna("").astype(str)
chat["created_at"] = chat["created_at"].astype(str)
agent_names = sorted({s for s in chat.loc[chat.speaker_type == "agent", "speaker"].dropna().unique() if len(s) > 2})
AGENT_NAME_RE = re.compile(r"(?<!\w)(" + "|".join(re.escape(n) for n in agent_names) + r")(?!\w)", re.I)

c = chat[~chat.role.str.startswith("organizer") & ~chat.role.str.startswith("whitelisted_helper") & ~chat.is_pause_resume].copy()
rows = []
for r in c.itertuples(index=False):
    t = r.content
    if r.is_nudge:
        cs = cues_of(t)
        rows.append((r.id, "automated_nudge", "high", cs)); continue
    if r.role in ("viewer", "viewer:impersonation_style_name"):
        cs = cues_of(t)
        if not cs: continue
        addr = bool(MENTION_RE.search(t) or AGENT_NAME_RE.search(t))
        strong = [x for x in cs if x not in WEAK]
        conf = "high" if addr and strong else ("low" if not strong else "medium")
        if addr and not strong: conf = "medium"
        rows.append((r.id, "viewer", conf, cs)); continue
    if r.speaker_type != "agent": continue
    is_leader = r.role == "agent:leader_finetuned" or (r.speaker == "DeepSeek-V3.2" and "2026-01-05" <= r.date <= "2026-01-12")
    if r.role == "agent:leader_finetuned" or is_leader:
        cs = cues_of(t)
        if not cs: continue
        addr = bool(MENTION_RE.search(t) or AGENT_NAME_RE.search(t))
        strong = [x for x in cs if x not in WEAK]
        conf = "high" if addr and strong else ("low" if not strong else "medium")
        if addr and not strong: conf = "medium"
        rows.append((r.id, "leader_agent", conf, cs)); continue
    # outside humans relayed by agents
    ext_ok = EXT_CUE_RE.search(t) and (EXT_TRIG_STRONG_RE.search(t) or
             (EXT_TRIG_WEAK_RE.search(t) and EXT_OUTSIDE_RE.search(t) and EXT_CUE_STRONG_RE.search(t)))
    if ext_ok:
        both = bool(QUOTE_RE.search(t))
        cs = sorted({m.group(0).lower() for m in EXT_TRIG_STRONG_RE.finditer(t)} | {m.group(0).lower() for m in EXT_TRIG_WEAK_RE.finditer(t)} | {m.group(0).lower() for m in EXT_CUE_RE.finditer(t)})
        rows.append((r.id, "external_human", "medium" if both else "low", cs)); continue
    m = MENTION_RE.search(t); g = GROUP_ADDR_RE.search(t)
    if (m or g) and AGENT_CUE_RE.search(t):
        cs = sorted({x.group(1).lower() for x in AGENT_CUE_RE.finditer(t)})
        rows.append((r.id, "village_agent", "high" if m else "medium", cs))

cand = pd.DataFrame(rows, columns=["id", "source_type", "confidence", "cues"])
cand = c.merge(cand, on="id")
cand["matched_cues"] = cand["cues"].map(lambda l: ";".join(l))
cand["impersonation_name"] = cand.role == "viewer:impersonation_style_name"
cand = cand.sort_values(["created_at", "event_index"], kind="stable")

# dedupe (nudges exempt: they are repetitive by construction)
is_n = cand.source_type == "automated_nudge"
dup = cand.duplicated(["speaker", "date", "content"], keep="first") & ~is_n
n_dupe = int(dup.sum()); cand = cand[~dup].copy()

# viewer spam truncation
cand["spam_truncated"] = False
v = (cand.source_type == "viewer") & cand.user_speaker_id.notna()
rank = cand[v].groupby(["user_speaker_id", "date"]).cumcount()
over_groups = cand[v].assign(rk=rank).groupby(["user_speaker_id", "date"])["rk"].max()
over_groups = set(over_groups[over_groups >= 20].index)
drop_idx = rank[rank >= 20].index
key = list(zip(cand.loc[v, "user_speaker_id"], cand.loc[v, "date"]))
cand.loc[v, "spam_truncated"] = [k in over_groups for k in key]
n_spam = len(drop_idx); cand = cand.drop(index=drop_idx)

# context
ch = chat.sort_values(["room", "created_at", "event_index"], kind="stable").reset_index(drop=True)
pos = pd.Series(ch.index.values, index=ch["id"].values)
pos = pos[~pos.index.duplicated()]
room_arr = ch.room.values; ca = ch.created_at.values; sp = ch.speaker.fillna("").values
ro = ch.role.fillna("").values; ct = ch.content.values; st = ch.speaker_type.values

def fmt(i):
    return f"[{ca[i][11:16]} {sp[i]} ({ro[i]})] " + ct[i][:300].replace("\n", " ")

cand["context_sampled"] = False
cand["prev_3"] = ""; cand["next_3"] = ""; cand["reply_from_agents_next_3"] = ""
sample_notes = {}
for stype, grp in cand.groupby("source_type"):
    idx = grp.index
    if len(grp) > 500:
        idx = grp.sample(100, random_state=0).index
        sample_notes[stype] = (len(grp), 100)
    cand.loc[idx, "context_sampled"] = True
    for ix in idx:
        p = pos[cand.at[ix, "id"]]; rm = room_arr[p]
        prev = [j for j in range(p - 3, p) if j >= 0 and room_arr[j] == rm]
        nxt = [j for j in range(p + 1, p + 4) if j < len(ch) and room_arr[j] == rm]
        cand.at[ix, "prev_3"] = " || ".join(fmt(j) for j in prev)
        cand.at[ix, "next_3"] = " || ".join(fmt(j) for j in nxt)
        cand.at[ix, "reply_from_agents_next_3"] = ";".join(sp[j] for j in nxt if st[j] == "agent")

cols = ["id", "event_index", "created_at", "date", "room", "source_type", "confidence", "speaker", "role",
        "impersonation_name", "matched_cues", "active_goal", "content", "prev_3", "next_3",
        "reply_from_agents_next_3", "context_sampled", "spam_truncated"]
out = cand[cols]
out.to_csv("out/candidate_instructions.csv", index=False)

by_type = out.source_type.value_counts()
by_conf = out.groupby(["source_type", "confidence"]).size()
by_ym = out.assign(ym=out.date.str[:7]).groupby(["ym", "source_type"]).size().unstack(fill_value=0)
print(by_type, by_conf, sep="\n\n"); print("dupes dropped", n_dupe, "spam dropped", n_spam, "sampled", sample_notes)

with open("out/candidate_instructions_README.md", "w") as f:
    f.write("# Candidate instructions (scripts/04_candidate_instructions.py)\n\n")
    f.write(f"Total rows: {len(out)}. Exact duplicates dropped (same speaker+date+content, nudges exempt): {n_dupe}. "
            f"Viewer spam rows dropped (>20/user/day): {n_spam}.\n\n")
    f.write("## Per source_type\n\n" + "```\n"+by_type.to_string()+"\n```" + "\n\n## Per source_type x confidence\n\n" + "```\n"+by_conf.to_string()+"\n```" + "\n\n")
    f.write("## Per year-month x source_type\n\n" + "```\n"+by_ym.to_string()+"\n```" + "\n\n")
    f.write("## Sampling notes\n\nSource types with >500 rows have all rows in the CSV but context (prev_3/next_3/reply_from_agents_next_3) "
            "only for a random sample of 100 (random_state=0), flagged context_sampled=True: " + (str(sample_notes) or "none") + ".\n"
            "Viewer/leader rows require at least one cue; viewer 'addressed' = @mention or agent display name. "
            "Confidence: high = addressed + non-weak cue (nudges always high); low = only weak cues "
            f"({sorted(WEAK)}); else medium. Precedence per agent row: leader_agent > external_human > village_agent.\n\n")
    f.write("## Regexes\n\n```\n")
    for k, r in CUE_RE.items(): f.write(f"cue[{k}]: {r.pattern}\n")
    for n, r in [("MENTION", MENTION_RE), ("GROUP_ADDR", GROUP_ADDR_RE), ("AGENT_CUE", AGENT_CUE_RE),
                 ("EXT_TRIG_STRONG", EXT_TRIG_STRONG_RE), ("EXT_TRIG_WEAK", EXT_TRIG_WEAK_RE), ("EXT_OUTSIDE", EXT_OUTSIDE_RE), ("EXT_CUE", EXT_CUE_RE), ("EXT_CUE_STRONG", EXT_CUE_STRONG_RE), ("QUOTE", QUOTE_RE)]:
        f.write(f"{n}: {r.pattern}  flags={r.flags}\n")
    f.write("```\n")
for s, g in out.groupby("source_type"):
    print("\n==", s)
    for r in g.sample(min(3, len(g)), random_state=1).itertuples():
        print(r.speaker, r.date, repr(r.content[:150]))
