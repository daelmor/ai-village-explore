"""Phase 0: profile the downloaded tables and export helper lookups.
Outputs:
  out/human_speakers.csv  - every human speakerId in USER_TALK events with names used,
                            message counts, first/last date, and a provisional role label
  out/agents_roster.csv   - agent id -> name, model_string, joined (created_at), left (from CHANGELOG roster)
  out/inventory_stats.json- row counts / value counts used in INVENTORY.md
Usage: python3 -I scripts/01_inventory_profile.py
"""
import gzip, json, re, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "out"

def load(name):
    with gzip.open(DATA / f"{name}.jsonl.gz", "rt", encoding="utf-8") as f:
        return pd.DataFrame([json.loads(l) for l in f])

stats = {}
ev = pd.read_parquet(OUT / "events_slim.parquet")
stats["events_rows"] = len(ev)
stats["events_actionType"] = ev.actionType.value_counts().to_dict()
stats["events_date_range"] = [ev.created_at.min(), ev.created_at.max()]

# ---- human speakers ----
ut = ev[ev.actionType == "USER_TALK"].copy()
# Provisional role labels. Organizer IDs = accounts that keep posting after public chat
# closed (Sept 2025+) with staff-like content; verified by reading samples in Phase 0.
ORGANIZER_IDS = {
    "195579f5-795d-4394-be46-d3f8f76ca6c1": "organizer:adam",
    "8083b876-648c-4b9f-9b08-e3bbafd47934": "organizer:zak",
    "c85d8e4a-5400-4aad-b36f-dfdbcadedc8c": "organizer:zak",
    "5c0441b4-b697-41a7-86e4-0ace7a1b9974": "organizer:shoshannah",
    "dc1d8731-355b-4788-ae4b-9673e7e2e79e": "organizer:shoshannah",
    "1de4b9f6-9c15-44c2-b4d8-e13ea261e422": "organizer:george",
    "2553e7ec-dc59-42d5-8b58-632404277ecb": "organizer:george",
    "8555e396-19b1-496e-8905-1ef8aff67d69": "organizer:camila",
    "445ab51c-3bb1-4475-a536-67f1924b06cf": "system:automated",
    "48b83f01-aeb9-4c4b-9913-6cf7038c20a0": "whitelisted_helper:larissa",
    "4ea12435-2352-48a6-8d89-ea3ca906e0a9": "whitelisted_helper:larissa",
}
IMPERSONATION = re.compile(r"verified|real |official|administrator|but not that|\(REAL\)|CEO|\badmin\b|\bzak\b|\badam\b", re.I)
g = ut.groupby("speakerId").agg(
    n_messages=("id", "size"),
    names=("speakerName", lambda s: " | ".join(sorted(set(s.fillna(""))))),
    first_seen=("created_at", "min"),
    last_seen=("created_at", "max"),
).reset_index()
g["role"] = g.speakerId.map(ORGANIZER_IDS).fillna("viewer")
g.loc[(g.role == "viewer") & g.names.str.contains(IMPERSONATION), "role"] = "viewer:impersonation_style_name"
g = g.sort_values("n_messages", ascending=False)
g.to_csv(OUT / "human_speakers.csv", index=False)
stats["human_speakers"] = int(len(g))
stats["human_messages_by_role"] = g.groupby("role").n_messages.sum().to_dict()
stats["user_talk_by_month"] = ut.created_at.str[:7].value_counts().sort_index().to_dict()
stats["nudge_messages"] = int(ut.content.str.contains("automated nudge", case=False, na=False).sum())

# ---- agents roster (join from agents table + CHANGELOG roster for 'left') ----
agents = load("agents")
roster = {}
for line in (DATA / "CHANGELOG.md").read_text().splitlines():
    m = re.match(r"^\|\s*(.+?)\s*\|\s*`?([^|`]+?)`?\s*\|\s*([\d-]+)[^|]*\|\s*([^|]+?)\s*\|$", line)
    if m and m.group(1) not in ("Agent", "-----"):
        roster[m.group(1)] = {"joined_changelog": m.group(3), "left_changelog": m.group(4)}
agents["joined_changelog"] = agents.name.map(lambda n: roster.get(n, {}).get("joined_changelog"))
agents["left_changelog"] = agents.name.map(lambda n: roster.get(n, {}).get("left_changelog"))
agents[["id", "name", "model_string", "is_participating", "created_at", "joined_changelog", "left_changelog"]] \
    .sort_values("created_at").to_csv(OUT / "agents_roster.csv", index=False)
stats["agents_rows"] = int(len(agents))

# ---- other small tables ----
for name in ["chat_messages", "summaries", "computer_use_sessions", "village_goals", "agent_goals", "chat_rooms", "claude_code_sessions", "villages"]:
    df = load(name)
    stats[f"{name}_rows"] = int(len(df))
    stats[f"{name}_columns"] = {c: str(df[c].map(lambda v: type(v).__name__).mode()[0]) for c in df.columns}
cm = load("chat_messages")
stats["chat_messages_speaker_type"] = cm.speaker_type.value_counts().to_dict()
stats["chat_messages_room_counts"] = cm.room_id.value_counts().to_dict()
s = load("summaries")
stats["summaries_type"] = s.type.value_counts().to_dict()
cs = load("computer_use_sessions")
stats["computer_use_sessions_asked_to_stop"] = cs.has_been_asked_to_stop.value_counts().to_dict()
stats["manifest"] = json.loads((DATA / "manifest.json").read_text())["rowCounts"]
(OUT / "inventory_stats.json").write_text(json.dumps(stats, indent=2, default=str))
print(json.dumps({k: v for k, v in stats.items() if not k.endswith("_columns")}, indent=1, default=str)[:4000])
