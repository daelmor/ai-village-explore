"""Phase 0: download docs and text tables from aidigestorg/ai-village into ./data.
Never downloads anything under images/. Auth comes from `hf auth login`.
Usage: python3 -I scripts/00_download.py [--big]   (--big also fetches agent_memories, 3 GB)
"""
import os, sys, pathlib
from huggingface_hub import hf_hub_download

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = ["README.md", "SCHEMA.md", "CHANGELOG.md", "manifest.json", "example.py",
         "agents.jsonl.gz", "villages.jsonl.gz", "village_goals.jsonl.gz", "agent_goals.jsonl.gz",
         "chat_rooms.jsonl.gz", "claude_code_sessions.jsonl.gz", "summaries.jsonl.gz",
         "chat_messages.jsonl.gz", "computer_use_sessions.jsonl.gz", "events.jsonl.gz"]
if "--big" in sys.argv:
    FILES.append("agent_memories.jsonl.gz")
for f in FILES:
    assert not f.startswith("images/")
    p = hf_hub_download("aidigestorg/ai-village", f, repo_type="dataset", local_dir=str(ROOT / "data"))
    print(f"{os.path.getsize(p):>14,}  {f}")
