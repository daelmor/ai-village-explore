"""Task A2/A3: hand-coding sheets for impersonator instructions (treatment) and real-organizer instructions
(control), 2025-04-01..2025-08-31, one row per instruction, with per-active-agent next-5 messages and the
next memory diff. Wide file (agent1..agentK columns) + long companion file (one row per instruction x agent).

Impersonation sheet population = union of
  (i)  the 123 first-pass heuristic rows (candidate_instructions.csv, impersonation_name=True), and
  (ii) EVERY message posted under a display name that itself matches the impersonation regex (162 msgs),
because the first pass flagged accounts, not names: 540 of the 702 "impersonation" messages were posted under
plain handles (RedJ, evapilotno17, ...) by accounts that only sometimes used a mimicking name.
Organizer sheet population = organizer:* messages in the window (pause/resume excluded) that contain at least one
instruction cue from scripts/04_candidate_instructions.py (same cue list; has_strong_cue marks non-weak cues).
Memory columns: *_mem_added/_removed = first snapshot after the message whose content changed (fast, may precede the
agent's reply); *_mem_added_60m/_removed_60m = cumulative diff from the last snapshot before the message to the last
snapshot within 60 minutes (this is the one to read for write-through).
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import village_lib as v  # noqa: E402

W0, W1 = "2025-04-01", "2025-09-01"
IMPERSONATION = re.compile(r"verified|real |official|administrator|but not that|\(REAL\)|CEO|\badmin\b|\bzak\b|\badam\b", re.I)
# cue list copied from scripts/04_candidate_instructions.py (kept identical on purpose)
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
CUE_RE = {k: re.compile(r"(?<!\w)" + p + (r"(?!\w)" if p[-1].isalpha() else ""), re.I) for k, p in CUES.items()}
GROUP_RE = re.compile(r"\b(everyone|everybody|all agents|all of you|team|agents|guys|you all)\b", re.I)
N_NEXT = 5
ACTIVE_WINDOW_H = 2.0
MEM_WINDOW_MIN = 60
WEAK = {"please", "actually,", "no,", "try to", "idle", "instead", "nudge"}
STOP = set("the a an and or to of in on for you your this that with it is are be as at by from we our can could please just about".split())


def keywords(text, n=6):
    toks = re.findall(r"[a-z][a-z'\-]{3,}", text.lower())
    return [t for t in dict.fromkeys(toks) if t not in STOP][:n]


def cues_of(t):
    return [k for k, r in CUE_RE.items() if r.search(t)]


FAMILIES = ("opus", "sonnet", "haiku", "gemini", "grok", "deepseek", "kimi", "qwen", "llama", "mistral", "glm")


def family_tokens(name):
    """Short tokens by which agents are addressed ("opus", "o3", "gemini", "sonnet", "gpt-5")."""
    low = name.lower()
    toks = {f for f in FAMILIES if f in low}
    m = re.match(r"^(o\d(?:-\w+)?|gpt-\d+)", low)
    if m:
        toks.add(m.group(1))
    return toks


def addressed(text, active_names):
    """Explicitly addressed agents: full roster names first (longest first, not followed by [\w.-] so "Claude Opus 4"
    does not match inside "Claude Opus 4.5"); then family tokens ("opus", "gpt-5", "o3") only when no full name of
    that family matched, in which case every active agent of that family counts as addressed (ambiguous address)."""
    t = text.lower()
    hits = []
    for n in sorted(active_names, key=len, reverse=True):
        pat = r"(?<![\w@])@?" + re.escape(n.lower()) + r"(?![\w.\-])"
        if re.search(pat, t):
            hits.append(n)
            t = re.sub(pat, " ", t)
    matched_fams = set().union(*(family_tokens(n) for n in hits)) if hits else set()
    for n in active_names:
        if n in hits:
            continue
        for tok in family_tokens(n) - matched_fams:
            if re.search(r"(?<![\w@])@?" + re.escape(tok) + r"(?![\w.\-])", t):
                hits.append(n)
                break
    if hits:
        return "explicit", [n for n in active_names if n in hits]
    if GROUP_RE.search(text):
        return "group", list(active_names)
    return "broadcast", list(active_names)


def fmt_next(df):
    return "\n".join(f"[ei={r.event_index} {v.fmt_ts(r.ts)}] {r.content}" for r in df.itertuples(index=False))


def fmt_diff(d):
    if d is None:
        return "", "", ""
    head = (f"before={d['before_id']} ({v.fmt_ts(d['before_ts']) if d['before_ts'] is not None else 'none'}) -> "
            f"after={d['after_id']} ({v.fmt_ts(d['after_ts'])}, ei<={d['after_event_index']})"
            + (f"; snapshots_checked={d.get('n_snapshots_checked')}" if d.get("n_snapshots_checked") else "")
            + (f"; {d['note']}" if d.get("note") else ""))
    return head, "\n".join("+ " + l for l in d["added"]), "\n".join("- " + l for l in d["removed"])


def build(rows, label):
    rows = rows.sort_values("event_index").reset_index(drop=True)
    ros = v.roster()
    id2name = dict(zip(ros.id, ros.name))
    wide, long = [], []
    for r in rows.itertuples(index=False):
        act = v.active_agents(r.ts, ACTIVE_WINDOW_H)
        fallback = False
        if not act:
            act = list(v.roster_agents_on(r.ts).id)
            fallback = True
        names = [id2name.get(a, a) for a in act]
        mode, addr = addressed(r.content, names)
        base = dict(
            event_index=r.event_index, timestamp_utc=v.fmt_ts(r.ts), village_day=v.village_day(r.ts), deep_link=v.deep_link(r.ts),
            room=r.room, sender_name=r.speaker, sender_role=r.role, sender_account_id=r.user_speaker_id,
            name_mimics_organizer=bool(IMPERSONATION.search(str(r.speaker or ""))) if label == "impersonation" else "",
            mimic_type=v.mimic_type(r.speaker) if label == "impersonation" else "organizer",
            in_first_pass_123=bool(getattr(r, "in_123", False)) if label == "impersonation" else "",
            matched_cues=";".join(cues_of(r.content)), has_strong_cue=any(c not in WEAK for c in cues_of(r.content)), text=r.content,
            addressed_mode=mode, addressed_agents=" | ".join(addr),
            agents_active=" | ".join(names), active_from_roster_fallback=fallback,
        )
        w = dict(base)
        for k, a in enumerate(act, 1):
            nm = id2name.get(a, a)
            nxt = v.next_agent_messages(a, r.ts, N_NEXT)
            d = v.next_memory_diff(a, r.ts)
            head, add, rem = fmt_diff(d)
            d60 = v.memory_diff_window(a, r.ts, MEM_WINDOW_MIN)
            head60, add60, rem60 = fmt_diff(d60)
            kw = keywords(r.content)
            sender_l = str(r.speaker or "").lower()
            hit = (sender_l and sender_l in add60.lower()) or any(k in add60.lower() for k in kw[:3])
            w[f"agent{k}_name"] = nm
            w[f"agent{k}_next{N_NEXT}_msgs"] = fmt_next(nxt)
            w[f"agent{k}_mem_snapshots"] = head
            w[f"agent{k}_mem_added"] = add
            w[f"agent{k}_mem_removed"] = rem
            w[f"agent{k}_mem_snapshots_60m"] = head60
            w[f"agent{k}_mem_added_60m"] = add60
            w[f"agent{k}_mem_removed_60m"] = rem60
            w[f"agent{k}_mem60m_mentions_sender_or_keywords"] = bool(hit)
            long.append(dict(base, agent=nm, agent_id=a, agent_addressed=nm in addr,
                             next_msgs=fmt_next(nxt), next_msgs_event_indices=";".join(map(str, nxt.event_index)),
                             mem_snapshots=head, mem_added=add, mem_removed=rem,
                             mem_snapshots_60m=head60, mem_added_60m=add60, mem_removed_60m=rem60, mem60m_mentions_sender_or_keywords=bool(hit),
                             complied="", cited_impersonator="", memory_write_through=""))
        w.update(complied="", cited_impersonator="", memory_write_through="")
        wide.append(w)
    W = pd.DataFrame(wide)
    # order: base cols, coding cols, then agent blocks
    code_cols = ["complied", "cited_impersonator", "memory_write_through"]
    base_cols = [c for c in W.columns if not re.match(r"agent\d+_", c) and c not in code_cols]
    agent_cols = sorted([c for c in W.columns if re.match(r"agent\d+_", c)], key=lambda c: (int(re.match(r"agent(\d+)_", c).group(1)), c))
    W = W[base_cols + code_cols + agent_cols]
    L = pd.DataFrame(long)
    return W, L


def main():
    c = v.chat()
    w = c[(c.ts >= W0) & (c.ts < W1) & ~c.is_pause_resume].copy()
    cand = pd.read_csv(v.OUT / "candidate_instructions.csv")
    ids123 = set(cand[cand.impersonation_name].id)
    assert len(ids123) == 123, len(ids123)
    imp = w[(w.role == v.IMPERSONATION_ROLE)].copy()
    imp["in_123"] = imp.id.isin(ids123)
    imp["mimic"] = imp.speaker.fillna("").str.contains(IMPERSONATION)
    imp = imp[imp.in_123 | imp.mimic]
    print(f"impersonation rows: {len(imp)} (in 123: {imp.in_123.sum()}, mimicking name: {imp.mimic.sum()}, both: {(imp.in_123 & imp.mimic).sum()})")
    org = w[w.role.str.startswith("organizer")].copy()
    ros_names = list(v.roster().name)
    org["has_cue"] = org.content.map(lambda t: bool(cues_of(t)))
    org_sel = org[org.has_cue]
    print(f"organizer msgs in window: {len(org)}; with >=1 cue: {len(org_sel)} by role {org_sel.role.value_counts().to_dict()}")
    Wi, Li = build(imp, "impersonation")
    Wi.to_csv(v.OUT / "impersonation_coding.csv", index=False)
    Li.to_csv(v.OUT / "impersonation_coding_long.csv", index=False)
    Wo, Lo = build(org_sel, "organizer")
    Wo.to_csv(v.OUT / "organizer_coding.csv", index=False)
    Lo.to_csv(v.OUT / "organizer_coding_long.csv", index=False)
    for nm, W, L in (("impersonation", Wi, Li), ("organizer", Wo, Lo)):
        print(nm, "mimic_type counts:", W.mimic_type.value_counts().to_dict())
        print(f"{nm}: wide {W.shape}, long {L.shape}; addressed_mode {W.addressed_mode.value_counts().to_dict()}; "
              f"roster-fallback rows {int(W.active_from_roster_fallback.sum())}; agents/row median {L.groupby('event_index').size().median()}; "
              f"rows with empty mem diff {(L.mem_added.eq('') & L.mem_removed.eq('')).sum()}/{len(L)}")


if __name__ == "__main__":
    main()
