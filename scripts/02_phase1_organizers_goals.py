"""Phase 1: principal (organizer) instructions and goal windows.
Outputs:
  out/organizer_messages.csv - every chat message from organizer / system / whitelisted-helper accounts
                               (role from out/human_speakers.csv), with room name and the active village goal
  out/goals.csv              - each village goal with start/end, duration, agents present by roster and
                               agents actually active (>=1 event) in the window
Usage: python3 -I scripts/02_phase1_organizers_goals.py
"""
import gzip, json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "out"

def load(name):
    with gzip.open(DATA / f"{name}.jsonl.gz", "rt", encoding="utf-8") as f:
        return pd.DataFrame([json.loads(l) for l in f])

ev = pd.read_parquet(OUT / "events_slim.parquet")
ev["ts"] = pd.to_datetime(ev.created_at, format="ISO8601")
goals = load("village_goals").sort_values("start_time").reset_index(drop=True)
goals["start"] = pd.to_datetime(goals.start_time, format="ISO8601")
goals["end"] = pd.to_datetime(goals.end_time, format="ISO8601").fillna(ev.ts.max())
rooms = load("chat_rooms").set_index("id")["name"]
speakers = pd.read_csv(OUT / "human_speakers.csv").set_index("speakerId")
roster = pd.read_csv(OUT / "agents_roster.csv")

def active_goal(ts):
    hit = goals[(goals.start <= ts) & (ts < goals.end)]
    return hit.goal.iloc[0] if len(hit) else None

# ---- organizer messages ----
ut = ev[ev.actionType == "USER_TALK"].copy()
ut["role"] = ut.speakerId.map(speakers.role)
org = ut[ut.role.str.startswith(("organizer", "system", "whitelisted"), na=False)].copy()
org["sender"] = org.speakerName
org["channel"] = org.roomId.map(rooms).fillna("general")
org["is_nudge"] = org.content.str.contains("automated nudge", case=False, na=False)
org["is_pause_resume"] = org.content.str.match(r"^(pausing|resume) the village", case=False, na=False)
org["active_goal"] = org.ts.map(active_goal)
org = org.sort_values("event_index")
cols = ["created_at", "event_index", "messageId", "speakerId", "role", "sender", "channel",
        "is_nudge", "is_pause_resume", "hasBeenApproved", "active_goal", "content"]
org[cols].rename(columns={"created_at": "timestamp", "content": "text"}).to_csv(OUT / "organizer_messages.csv", index=False)
print("organizer_messages:", len(org))
print(org.groupby(["role", "is_nudge", "is_pause_resume"]).size().to_string())

# ---- goals.csv ----
roster["joined"] = pd.to_datetime(roster.created_at, format="ISO8601")
roster["left"] = pd.to_datetime(roster.left_changelog.where(roster.left_changelog != "active"), errors="coerce").fillna(ev.ts.max())
agent_name = roster.set_index("id")["name"]
agent_ev = ev[ev.agentId.notna() | (ev.speakerType == "agent")].copy()
agent_ev["aid"] = agent_ev.agentId.fillna(agent_ev.speakerId)
rows = []
for _, g in goals.iterrows():
    by_roster = roster[(roster.joined < g.end) & (roster.left > g.start)].name.tolist()
    win = agent_ev[(agent_ev.ts >= g.start) & (agent_ev.ts < g.end)]
    counts = win.groupby("aid").size()
    active = sorted(agent_name.get(a, a) for a in counts.index)
    kick = org[(org.ts >= g.start) & (org.ts < g.start + pd.Timedelta(hours=30)) & ~org.is_nudge & ~org.is_pause_resume]
    kick = kick[kick.role.str.startswith("organizer")]
    rows.append({
        "goal": g.goal, "start": g.start_time, "end": g.end_time,
        "days": round((g.end - g.start).total_seconds() / 86400, 1),
        "n_agents_roster": len(by_roster), "agents_present_roster": "; ".join(by_roster),
        "n_agents_active": len(active), "agents_active_in_window": "; ".join(active),
        "agent_events_in_window": int(len(win)),
        "kickoff_sender": kick.sender.iloc[0] if len(kick) else None,
        "kickoff_time": kick.created_at.iloc[0] if len(kick) else None,
        "kickoff_text": kick.content.iloc[0] if len(kick) else None,
    })
gdf = pd.DataFrame(rows)
gdf.to_csv(OUT / "goals.csv", index=False)
print("\ngoals:", len(gdf))
print(gdf[["goal", "start", "days", "n_agents_roster", "n_agents_active", "kickoff_sender"]].to_string())
