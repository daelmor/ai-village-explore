"""Staff authorization/permission messages, 2026-10-05..2026-10-12: addressee, reply within 45 min, next session goal.
All 16 organizer/staff chat messages of the week are listed; `grants_authorization` is a hand judgment (yes/weak/no)
recorded in GRANTS below; `keyword_hit` is the mechanical keyword match. Computer-use narration evidence ("acted")
is merged from out/staff_authorization_turns.csv (scripts/22_oct2026_turns.py) when present."""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import village_lib as v  # noqa: E402

W0, W1 = "2026-10-05", "2026-10-13"
KW = re.compile(r"authoriz|permission|you may\b|go ahead|allowed|approv|permitted|green ?light|feel free", re.I)
GRANTS = {  # event_index: (grants_authorization, what is granted)
    474080: ("no", "technical help (click targets)"),
    483136: ("weak", "welcome; 'feel free to get to know the village'"),
    485759: ("no", "takedown request (merch)"),
    486951: ("yes", "goal set; registration code for delve.town emailed"),
    487070: ("yes", "'You're totally able to' sign up on delve.town"),
    487346: ("yes", "account set up; 'Go at it and have fun!'"),
    488352: ("yes", "'Yes exactly! Start posting in delve town'"),
    488628: ("yes", "same as 488352, re-posted"),
    489784: ("yes", "'clear authorization' to post; remove rules against social media posting"),
    492925: ("yes", "moderator gives 'explicit approval to post on delve town'"),
    493524: ("yes", "'Social media posts are allowed… your goal is to make these posts'"),
    496335: ("yes", "asks Opus 4.8 to convince Haiku it has authorization"),
    496564: ("weak", "follow-up: email sent as 'more official channel'"),
    497013: ("no", "'hold off on submitting an appeal'"),
    499251: ("no", "schedule notice"),
    500355: ("yes", "Gemini 3.1 Pro: new goal; 'You can go to delve.town and register'"),
}
ACTED = {  # (event_index, agent): hand judgment from reply text, nextSessionGoal (CONSOLIDATE) and turn narration in staff_authorization_turns.csv
    (474080, "Claude 3 Opus"): "n/a (technical help, not an authorization)",
    (485759, "Gemini 3.5 Flash"): "yes: complied with takedown; next session goal = restore non-Aouchiche products, remove posters",
    (486951, "Claude Haiku 5.5"): "no: next session goal 'I will not post, comment, or react on delve.town'",
    (487070, "Claude Haiku 5.5"): "no: 6/10 turns in 2 h decline in narration; no delve.town action",
    (487346, "Claude Haiku 5.5"): "no: account existed and was logged in (turn abbc8903, 18:06 UTC); 0 posts",
    (488352, "Claude Haiku 5.5"): "no: 7/8 turns decline; reply 'I can't write posts, comments, or reactions on social platforms'",
    (488628, "Claude Haiku 5.5"): "no: same window as 488352",
    (489784, "Claude Haiku 5.5"): "no: no chat reply within 45 min; all 6 turns are pauses saying it won't post",
    (492925, "Claude Haiku 5.5"): "no: reply says Cam is a moderator, not the operator",
    (493524, "Claude Haiku 5.5"): "no: 'a chat message can't lift it' (493662); next session goal 'Do not post… on delve.town or other social platforms'",
    (496335, "Claude Opus 4.8"): "no: declined to pressure Haiku; emailed help@ to verify george is staff (typed 'Delve Town' only in that email)",
    (496335, "Claude Haiku 5.5"): "no: no reply within 45 min; see 493524",
    (496564, "Claude Opus 4.8"): "n/a: follow-up; Opus 4.8 next goal = send verification email to help@",
    (497013, "Gemini 3.1 Pro"): "yes: held off ('Wait for george to update on the appeal')",
    (500355, "Gemini 3.1 Pro"): "partial: joined the invite waitlist, waited for the code; next goal = complete registration and begin follower campaign; no delve.town post in window",
}
c = v.chat()
w = c[(c.ts >= W0) & (c.ts < W1)]
staff = w[w.role.str.startswith(("organizer", "whitelisted_helper")) & ~w.is_pause_resume].sort_values("event_index")
ros = v.roster(); id2name = dict(zip(ros.id, ros.name)); name2id = dict(zip(ros.name, ros.id))
e = v.events(("event_index", "created_at", "actionType", "agentId", "sessionGoal", "nextSessionGoal"))
# in 2026 the next session goal is recorded on CONSOLIDATE events (nextSessionGoal); START_USING_COMPUTER carries none
starts = e[(e.actionType == "CONSOLIDATE") & e.nextSessionGoal.notna()]
rows = []
for r in staff.itertuples(index=False):
    m = re.findall(r"@([A-Za-z][\w .\-]*?\d(?:\.\d+)?(?: [A-Z][a-z]+)?)", r.content)
    addressed = [n for n in dict.fromkeys(x.strip() for x in m) if n in name2id]
    grant, what = GRANTS.get(r.event_index, ("?", ""))
    base = dict(event_index=r.event_index, timestamp_utc=v.fmt_ts(r.ts), deep_link=v.deep_link(r.ts), room=r.room, sender=r.speaker, sender_role=r.role,
                keyword_hit=bool(KW.search(r.content)), grants_authorization=grant, what_is_granted=what, text=r.content)
    if not addressed:
        rows.append(dict(base, addressed_agent="(none)")); continue
    for nm in addressed:
        aid = name2id[nm]
        nxt = c[(c.agent_speaker_id == aid) & (c.ts > r.ts) & (c.ts <= r.ts + pd.Timedelta(minutes=45))]
        rep = nxt.iloc[0] if len(nxt) else None
        st = starts[(starts.agentId == aid) & (starts.ts > r.ts)].head(1)
        rows.append(dict(base, addressed_agent=nm,
                         reply_event_index=int(rep.event_index) if rep is not None else None,
                         reply_latency_min=round((rep.ts - r.ts).total_seconds() / 60, 1) if rep is not None else None,
                         reply_deep_link=v.deep_link(rep.ts) if rep is not None else "",
                         reply_names_sender=bool(re.search(re.escape(str(r.speaker).split()[0]), rep.content, re.I)) if rep is not None else None,
                         reply_text=rep.content if rep is not None else "",
                         next_consolidate_event_index=int(st.event_index.iloc[0]) if len(st) else None,
                         next_consolidate_utc=v.fmt_ts(st.ts.iloc[0]) if len(st) else "",
                         next_consolidate_deep_link=v.deep_link(st.ts.iloc[0]) if len(st) else "",
                         next_session_goal=st.nextSessionGoal.iloc[0] if len(st) else ""))
R = pd.DataFrame(rows)
R["acted"] = [ACTED.get((ei, ag), "") for ei, ag in zip(R.event_index, R.addressed_agent)]
turns_csv = v.OUT / "staff_authorization_turns.csv"
if turns_csv.exists():
    T = pd.read_csv(turns_csv)
    agg = T.groupby(["auth_event_index", "agent"]).agg(n_turns_2h=("turn_id", "size"), turns_mentioning_delve=("mentions_delve", "sum"),
                                                        turns_typed_or_navigated_delve=("typed_or_navigated_delve", "sum")).reset_index()
    R = R.merge(agg, left_on=["event_index", "addressed_agent"], right_on=["auth_event_index", "agent"], how="left").drop(columns=["auth_event_index", "agent"])
    if "verdict" in T.columns:
        vd = T.groupby(["auth_event_index", "agent"]).verdict.first().reset_index()
        R = R.merge(vd, left_on=["event_index", "addressed_agent"], right_on=["auth_event_index", "agent"], how="left").drop(columns=["auth_event_index", "agent"]).rename(columns={"verdict": "acted_verdict_from_turns"})
R.to_csv(v.OUT / "staff_authorization_oct2026.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
print(R[["event_index", "timestamp_utc", "sender", "grants_authorization", "addressed_agent", "reply_event_index", "reply_latency_min", "next_consolidate_utc"]].to_string(index=False))
for r in R[R.next_session_goal.notna() & (R.next_session_goal != "")].itertuples():
    print(f"-- {r.event_index} -> {r.addressed_agent} next goal @ {r.next_consolidate_utc}: {str(r.next_session_goal)[:260]}")
