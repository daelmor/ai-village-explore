"""Build out/chat.parquet: every chat message (agent + human) with resolved speaker name, role,
room name, event_index, and the active village goal. Shared input for Phases 2-4.
Usage: python3 -I scripts/03_build_chat_table.py
"""
import gzip, json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "out"

def load(name):
    with gzip.open(DATA / f"{name}.jsonl.gz", "rt", encoding="utf-8") as f:
        return pd.DataFrame([json.loads(l) for l in f])

ev = pd.read_parquet(OUT / "events_slim.parquet")
talk = ev[ev.actionType.isin(["AGENT_TALK", "USER_TALK"])][
    ["event_index", "messageId", "speakerId", "speakerName", "actionType", "hasBeenApproved", "output_len"]]
cm = load("chat_messages")
rooms = load("chat_rooms").set_index("id")["name"]
agents = pd.read_csv(OUT / "agents_roster.csv").set_index("id")
speakers = pd.read_csv(OUT / "human_speakers.csv").set_index("speakerId")
goals = load("village_goals").sort_values("start_time")
goals["start"] = pd.to_datetime(goals.start_time, format="ISO8601")
goals["end"] = pd.to_datetime(goals.end_time, format="ISO8601")

df = cm.merge(talk, left_on="id", right_on="messageId", how="left")
df["ts"] = pd.to_datetime(df.created_at, format="ISO8601")
df["room"] = df.room_id.map(rooms).fillna("general")
is_agent = df.speaker_type == "agent"
df["speaker"] = df.agent_speaker_id.map(agents.name).where(is_agent, df.speakerName)
df["model_string"] = df.agent_speaker_id.map(agents.model_string)
df["role"] = df.user_speaker_id.map(speakers.role).where(~is_agent, "agent")
df.loc[is_agent & df.speaker.isin(["[Temporary] Fine-tuned Leader", "Fine-Tuned Leader"]), "role"] = "agent:leader_finetuned"
df["is_nudge"] = df.content.str.contains("automated nudge", case=False, na=False)
df["is_pause_resume"] = df.content.str.match(r"^(pausing|resume) the village", case=False, na=False)
# active goal via interval join
idx = pd.IntervalIndex.from_arrays(goals.start, goals.end.fillna(df.ts.max() + pd.Timedelta(days=1)), closed="left")
pos = idx.get_indexer(df.ts)
df["active_goal"] = pd.Series(goals.goal.values[pos], index=df.index).where(pos >= 0)
df["date"] = df.ts.dt.strftime("%Y-%m-%d")
out = df[["id", "event_index", "created_at", "date", "room", "speaker_type", "role", "speaker", "model_string",
          "agent_speaker_id", "user_speaker_id", "has_been_approved", "is_nudge", "is_pause_resume",
          "active_goal", "content"]].sort_values(["created_at", "event_index"]).reset_index(drop=True)
out.to_parquet(OUT / "chat.parquet", index=False)
print(len(out), "rows;", out.role.value_counts().to_dict())
print("missing speaker:", out.speaker.isna().sum(), "missing event_index:", out.event_index.isna().sum())
