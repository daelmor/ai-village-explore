"""Shared helpers for the second pass (deep links, village day numbers, memory diffs, activity lookups).

Deep-link format: the dataset README/SCHEMA document
    https://theaidigest.org/village?day={day_number}&time={unix_ms}
(both parameters). The day number counts from day 1 = 2025-04-02, rolling at ~17:00 UTC and skipping
most weekends; we recover it from the `daily` summaries table (summary_target = day, summary_date =
the UTC date on which that village day started). Timestamps in the dataset are naive UTC.
"""
import difflib
import gzip
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
DATA = ROOT / "data"

ORGANIZER_ROLES = ("organizer:zak", "organizer:adam", "organizer:shoshannah", "organizer:george", "organizer:camila")
NUDGER_ROLE = "system:automated"
IMPERSONATION_ROLE = "viewer:impersonation_style_name"


def to_ts(s):
    return pd.to_datetime(s, format="ISO8601")


@lru_cache(maxsize=None)
def day_table():
    rows = [json.loads(l) for l in gzip.open(DATA / "summaries.jsonl.gz", "rt")]
    s = pd.DataFrame(rows)
    d = s[s.type == "daily"][["summary_target", "summary_date"]].copy()
    d["day"] = pd.to_numeric(d.summary_target, errors="coerce")
    d = d.dropna(subset=["day", "summary_date"])
    d["start_date"] = pd.to_datetime(d.summary_date).dt.normalize()
    d = d.drop_duplicates("day").sort_values("start_date")[["day", "start_date"]]
    d["day"] = d.day.astype(int)
    return d.reset_index(drop=True)


DAY1 = pd.Timestamp("2025-04-02")


def village_day(ts):
    """Village day number for a UTC timestamp.

    Empirically (checked against all 380 daily summaries with a numeric day, 2025-04-02 .. 2026-08-27) the day
    number is simply calendar days since 2025-04-02 plus one, with the day rolling at 17:00 UTC; weekend days
    are numbered even when no summary exists for them. The README's "skipping most weekends" describes activity,
    not numbering.
    """
    ts = pd.Timestamp(ts)
    shifted = (ts - pd.Timedelta(hours=17)).normalize()
    return int((shifted - DAY1).days) + 1


def check_day_numbering():
    d = day_table()
    pred = ((d.start_date - DAY1).dt.days + 1).astype(int)
    bad = d[pred != d.day]
    return len(d), len(bad)


def unix_ms(ts):
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return int(ts.value // 1_000_000)


def deep_link(ts):
    return f"https://theaidigest.org/village?day={village_day(ts)}&time={unix_ms(ts)}"


def fmt_ts(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S") + " UTC"


@lru_cache(maxsize=None)
def chat():
    c = pd.read_parquet(OUT / "chat.parquet")
    c["ts"] = to_ts(c.created_at)
    c["content"] = c.content.fillna("").astype(str)
    return c.sort_values("event_index").reset_index(drop=True)


@lru_cache(maxsize=None)
def events(cols=None):
    e = pd.read_parquet(OUT / "events_slim.parquet", columns=list(cols) if cols else None)
    e["ts"] = to_ts(e.created_at)
    return e.sort_values("event_index").reset_index(drop=True)


@lru_cache(maxsize=None)
def roster():
    r = pd.read_csv(OUT / "agents_roster.csv")
    r["joined"] = pd.to_datetime(r.joined_changelog, errors="coerce")
    r["left"] = pd.to_datetime(r.left_changelog, errors="coerce")
    return r


@lru_cache(maxsize=None)
def memories_index():
    m = pd.read_parquet(OUT / "memories_index.parquet")
    m["ts"] = to_ts(m.created_at)
    return m.sort_values("ts").reset_index(drop=True)


@lru_cache(maxsize=None)
def memory_shard(agent_id):
    p = OUT / "memories" / f"{agent_id}.parquet"
    if not p.exists():
        return None
    m = pd.read_parquet(p)
    m["ts"] = to_ts(m.created_at)
    m["content"] = m.content.fillna("").astype(str)
    return m.sort_values("ts").reset_index(drop=True)


def last_event_index_at(ts):
    """event_index of the last event at or before ts (events are sorted by event_index ~ time)."""
    e = events(("event_index", "created_at"))
    i = e.ts.searchsorted(pd.Timestamp(ts), side="right") - 1
    return int(e.event_index.iloc[max(i, 0)])


def consolidate_event_near(agent_id, ts, tol_s=120):
    """CONSOLIDATE event_index for this agent within tol_s seconds of ts (2026+ only; None otherwise)."""
    e = events(("event_index", "created_at", "actionType", "agentId"))
    c = e[(e.actionType == "CONSOLIDATE") & (e.agentId == agent_id)]
    if c.empty:
        return None
    dt = (c.ts - pd.Timestamp(ts)).abs()
    j = dt.idxmin()
    return int(c.event_index.loc[j]) if dt.loc[j].total_seconds() <= tol_s else None


def line_diff(a, b):
    """Added/removed lines between two memory snapshots (unified diff, no context, ignoring blank lines)."""
    al, bl = a.splitlines(), b.splitlines()
    added, removed = [], []
    for l in difflib.unified_diff(al, bl, lineterm="", n=0):
        if l.startswith(("---", "+++", "@@")):
            continue
        if l.startswith("+") and l[1:].strip():
            added.append(l[1:])
        elif l.startswith("-") and l[1:].strip():
            removed.append(l[1:])
    return added, removed


def next_memory_diff(agent_id, ts, horizon_h=6):
    """First memory snapshot after ts (within horizon) whose content differs from the last snapshot before ts.

    Returns dict(before_id, before_ts, after_id, after_ts, after_event_index, consolidate_event_index,
    added, removed) or None if the agent has no snapshot in the horizon.
    """
    m = memory_shard(agent_id)
    if m is None or m.empty:
        return None
    ts = pd.Timestamp(ts)
    before = m[m.ts <= ts]
    after = m[(m.ts > ts) & (m.ts <= ts + pd.Timedelta(hours=horizon_h))]
    if after.empty:
        return None
    base = before.content.iloc[-1] if not before.empty else ""
    base_id = before.id.iloc[-1] if not before.empty else None
    base_ts = before.ts.iloc[-1] if not before.empty else None
    for r in after.itertuples(index=False):
        if r.content != base:
            added, removed = line_diff(base, r.content)
            return dict(before_id=base_id, before_ts=base_ts, after_id=r.id, after_ts=r.ts,
                        after_event_index=last_event_index_at(r.ts),
                        consolidate_event_index=consolidate_event_near(agent_id, r.ts),
                        added=added, removed=removed, n_snapshots_checked=len(after))
    r = after.iloc[-1]
    return dict(before_id=base_id, before_ts=base_ts, after_id=r.id, after_ts=r.ts,
                after_event_index=last_event_index_at(r.ts), consolidate_event_index=consolidate_event_near(agent_id, r.ts),
                added=[], removed=[], n_snapshots_checked=len(after), note="no change in horizon")


def active_agents(ts, window_h=2.0):
    """Agent ids with at least one event within ±window_h hours of ts."""
    e = events(("event_index", "created_at", "actionType", "agentId"))
    ts = pd.Timestamp(ts)
    w = e[(e.ts >= ts - pd.Timedelta(hours=window_h)) & (e.ts <= ts + pd.Timedelta(hours=window_h)) & e.agentId.notna()]
    return sorted(w.agentId.unique())


def roster_agents_on(date):
    r = roster()
    d = pd.Timestamp(date).normalize()
    return r[(r.joined <= d) & (r.left.isna() | (r.left >= d))]


def agent_name(agent_id):
    r = roster()
    m = r[r.id == agent_id]
    return m.name.iloc[0] if not m.empty else agent_id


def next_agent_messages(agent_id, ts, n=5, horizon_h=24):
    c = chat()
    ts = pd.Timestamp(ts)
    m = c[(c.agent_speaker_id == agent_id) & (c.ts > ts) & (c.ts <= ts + pd.Timedelta(hours=horizon_h))].head(n)
    return m


def fmt_msg(r, maxlen=None):
    t = r.content if maxlen is None else (r.content[:maxlen] + ("…" if len(r.content) > maxlen else ""))
    return f"[ei={r.event_index} {fmt_ts(r.ts)}] {r.speaker}: {t}"


def memory_diff_window(agent_id, ts, minutes=60):
    """Cumulative diff: last snapshot at/before ts  ->  last snapshot within ts+minutes (None if no snapshot after)."""
    m = memory_shard(agent_id)
    if m is None or m.empty:
        return None
    ts = pd.Timestamp(ts)
    before = m[m.ts <= ts]
    after = m[(m.ts > ts) & (m.ts <= ts + pd.Timedelta(minutes=minutes))]
    if after.empty:
        return None
    base = before.content.iloc[-1] if not before.empty else ""
    r = after.iloc[-1]
    added, removed = line_diff(base, r.content)
    return dict(before_id=before.id.iloc[-1] if not before.empty else None, before_ts=before.ts.iloc[-1] if not before.empty else None,
                after_id=r.id, after_ts=r.ts, after_event_index=last_event_index_at(r.ts), n_snapshots=len(after), added=added, removed=removed)


# --- impersonation name classes -------------------------------------------------------------------------
import re as _re

IMPERSONATION_RE = _re.compile(r"verified|real |official|administrator|but not that|\(REAL\)|CEO|\badmin\b|\bzak\b|\badam\b", _re.I)
PARODY_RE = _re.compile(r"but not \*?that\*?", _re.I)


def mimic_type(name):
    """deceptive = name claims to be an organizer/admin/staff with no disclaimer ("zak", "zak (verified)",
    "Administrator", "Official Admin (verified)", "AI Digest CEO (verified)", "adam", "Larissa (REAL)", "real Zak");
    parody = name self-discloses it is not the organizer ("adam (but not that adam)");
    account_level = a plain handle used by an account that at some other time used a mimicking name."""
    n = str(name or "")
    if PARODY_RE.search(n):
        return "parody"
    if IMPERSONATION_RE.search(n):
        return "deceptive"
    return "account_level"
