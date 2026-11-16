"""Stuck episodes under the fixed definition D1 and the single alternative D2 (see HYPOTHESIS.md).

Reads out/turn_actions.parquet (script 01). Writes:
  out/episodes.parquet      every D1 episode (git-ignored): agent, session, start/recovery turn ids and times, length,
                            action kind, signature, excerpt, recovered flag, time to recover, stuck seconds, cell
  out/episodes_d2.parquet   every D2 stretch (git-ignored)
  out/agent_stuck.csv       one row per agent: active hours, work actions, D1/D2 episodes, rates, recovery, release date
  out/agent_regime.csv      the same per agent x scaffolding regime
  out/agent_cell.csv        the same per agent x cell (goal period x room; the last goal period split by ISO week)
  out/kind_breakdown.csv    D1 episodes and work actions by action kind group and regime
Usage: ./venv/bin/python3 -I data-scouts/stuck-time/scripts/02_episodes.py
"""
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

t = pd.read_parquet(v.OUT / "turn_actions.parquet", columns=["turn_id", "session_id", "agent_id", "created_at", "kind", "sig", "excerpt"])
t["ts"] = pd.to_datetime(t.created_at, format="ISO8601")
t = t.sort_values(["session_id", "ts", "turn_id"]).reset_index(drop=True)
rel = v.release_table()
cc_ids = set(rel[rel.model_string.fillna("").str.startswith("claude-code::")].id)
t = t[t.agent_id.notna() & ~t.agent_id.isin(cc_ids)].reset_index(drop=True)
print(f"{len(t):,} turns, {t.session_id.nunique():,} sessions, {t.agent_id.nunique()} agents", flush=True)

# --- active time: gap to the next turn of the same session, capped ----------------------------------------
nxt = t.ts.shift(-1)
same = t.session_id == t.session_id.shift(-1)
t["dt"] = np.where(same, (nxt - t.ts).dt.total_seconds().clip(lower=0, upper=v.GAP_CAP_S), 0.0)
t["cls"] = np.where(t.kind.isin(v.WORK), "work", np.where(t.kind.isin(v.NEUTRAL), "neutral", "break"))
t["kgroup"] = t.kind.map(v.kind_group)

# --- cells: goal period (last one split by ISO week) x room ------------------------------------------------
goals = pd.DataFrame([json.loads(l) for l in gzip.open(v.DATA / "village_goals.jsonl.gz", "rt")])
goals["start"] = pd.to_datetime(goals.start_time, format="ISO8601")
goals = goals.sort_values("start").reset_index(drop=True)
gi = np.searchsorted(goals.start.values, t.ts.values, side="right") - 1
t["period"] = ["G%02d" % i for i in gi]
last = "G%02d" % (len(goals) - 1)
iso = t.ts.dt.strftime("%G-W%V")
t.loc[t.period == last, "period"] = last + "/" + iso[t.period == last]
t["regime"] = v.regime_of(t.ts)

c = v.chat()
c = c[c.speaker_type == "agent"][["agent_speaker_id", "ts", "room"]].copy()
ci = np.searchsorted(goals.start.values, c.ts.values, side="right") - 1
c["period"] = ["G%02d" % i for i in ci]
ciso = c.ts.dt.strftime("%G-W%V")
c.loc[c.period == last, "period"] = last + "/" + ciso[c.period == last]
room = (c.groupby(["agent_speaker_id", "period"]).room.agg(lambda s: s.value_counts().index[0])
        .rename("room").reset_index().rename(columns={"agent_speaker_id": "agent_id"}))

# --- D1: runs of >= MIN_RUN consecutive work actions with one signature (neutral skipped, breaks end a run) --
nn = t[t.cls != "neutral"].copy()
new_run = (nn.session_id != nn.session_id.shift()) | (nn.sig != nn.sig.shift()) | (nn.cls == "break") | (nn.cls.shift() == "break")
nn["run"] = new_run.cumsum()
runs = nn[nn.cls == "work"].groupby("run").agg(
    agent_id=("agent_id", "first"), session_id=("session_id", "first"), sig=("sig", "first"), kind=("kind", "first"),
    kgroup=("kgroup", "first"), n=("turn_id", "size"), start_turn=("turn_id", "first"), start=("ts", "first"),
    last_repeat_turn=("turn_id", "last"), last_repeat=("ts", "last"), excerpt=("excerpt", "first"),
    period=("period", "first"), regime=("regime", "first"), first_idx=("turn_id", lambda s: s.index[0]),
    last_idx=("turn_id", lambda s: s.index[-1])).reset_index(drop=True)
ep = runs[runs.n >= v.MIN_RUN].copy()

# recovery: first later work action of the session with a different signature
wk = t[t.cls == "work"]
w_idx = wk.index.values
w_sess = wk.session_id.values
w_sig = wk.sig.values
chg = np.r_[True, (w_sess[1:] != w_sess[:-1]) | (w_sig[1:] != w_sig[:-1])]
wrun = np.cumsum(chg)                       # work-only runs (breaks do not split these)
starts = np.flatnonzero(chg)                # position (in wk) where each work-only run starts
pos_of_idx = pd.Series(np.arange(len(w_idx)), index=w_idx)
rec_idx = []
for last_i, sess in zip(ep.last_idx.values, ep.session_id.values):
    p = pos_of_idx[last_i]
    r = wrun[p]                             # 1-based id of the work-only run holding the episode's last action
    q = starts[r] if r < len(starts) else None   # start of the next work-only run
    rec_idx.append(int(w_idx[q]) if q is not None and w_sess[q] == sess else -1)
rec_idx = np.array(rec_idx)
ok = rec_idx >= 0
ep["recovered"] = ok
ep["recovery_turn"] = np.where(ok, t.turn_id.values[np.where(ok, rec_idx, 0)], None)
ep["recovery"] = pd.to_datetime(np.where(ok, t.ts.values[np.where(ok, rec_idx, 0)], np.datetime64("NaT")))
ep["recover_s"] = (ep.recovery - ep.start).dt.total_seconds()
# stuck seconds: capped gaps from the first repeated action up to recovery (or to the last repeat)
cum = np.r_[0.0, np.cumsum(t.dt.values)]
end_idx = np.where(ok, rec_idx, ep.last_idx.values)
ep["stuck_s"] = cum[end_idx] - cum[ep.first_idx.values]
ep = ep.merge(rel[["id", "name"]].rename(columns={"id": "agent_id", "name": "agent"}), on="agent_id", how="left")
ep["link"] = ep.start.map(v.deep_link)
ep.drop(columns=["first_idx", "last_idx"]).to_parquet(v.OUT / "episodes.parquet")
print(f"D1 episodes: {len(ep):,}; recovered in session: {ep.recovered.mean():.3f}", flush=True)

# --- D2: stretches where every window of 8 work actions holds <= 2 signatures --------------------------------
wd = nn.copy()
wd["seg"] = ((wd.session_id != wd.session_id.shift()) | (wd.cls == "break") | (wd.cls.shift() == "break")).cumsum()
wd = wd[wd.cls == "work"]
codes = pd.factorize(wd.sig)[0].astype(np.int64)
seg = wd.seg.values
W = v.D2_WINDOW
if len(codes) >= W:
    win = np.sort(np.lib.stride_tricks.sliding_window_view(codes, W), axis=1)
    nd = (np.diff(win, axis=1) != 0).sum(1) + 1
    good = (nd <= v.D2_MAX_SIGS) & (seg[: len(seg) - W + 1] == seg[W - 1:])
    d = np.zeros(len(codes) + 1, dtype=np.int64)
    gs = np.flatnonzero(good)
    np.add.at(d, gs, 1); np.add.at(d, gs + W, -1)
    marked = np.cumsum(d)[:-1] > 0
else:
    marked = np.zeros(len(codes), dtype=bool)
wd["marked"] = marked
wd["stretch"] = ((wd.marked != wd.marked.shift()) | (wd.seg != wd.seg.shift())).cumsum()
d2 = wd[wd.marked].groupby("stretch").agg(agent_id=("agent_id", "first"), session_id=("session_id", "first"),
                                          n=("turn_id", "size"), n_sigs=("sig", "nunique"), start_turn=("turn_id", "first"),
                                          start=("ts", "first"), end=("ts", "last"), period=("period", "first"),
                                          regime=("regime", "first"), kgroup=("kgroup", "first")).reset_index(drop=True)
d2.to_parquet(v.OUT / "episodes_d2.parquet")
print(f"D2 stretches: {len(d2):,}", flush=True)


# --- per-agent tables --------------------------------------------------------------------------------------
def table(keys):
    g = t.groupby(keys)
    a = g.agg(active_h=("dt", lambda s: s.sum() / 3600), turns=("turn_id", "size"), first_turn=("ts", "min"), last_turn=("ts", "max"))
    a["work_actions"] = t[t.cls == "work"].groupby(keys).size()
    a["bash_actions"] = t[t.kgroup == "bash"].groupby(keys).size()
    a["gui_actions"] = t[(t.cls == "work") & (t.kgroup != "bash")].groupby(keys).size()
    e = ep.groupby(keys)
    a["d1_episodes"] = e.size()
    a["d1_bash"] = ep[ep.kgroup == "bash"].groupby(keys).size()
    a["d1_gui"] = ep[ep.kgroup != "bash"].groupby(keys).size()
    a["d1_recovered"] = e.recovered.sum()
    a["stuck_h"] = e.stuck_s.sum() / 3600
    a["median_recover_s"] = ep[ep.recovered].groupby(keys).recover_s.median()
    a["median_run_len"] = e.n.median()
    a["d2_stretches"] = d2.groupby(keys).size()
    a = a.fillna({k: 0 for k in ["work_actions", "bash_actions", "gui_actions", "d1_episodes", "d1_bash", "d1_gui",
                                 "d1_recovered", "stuck_h", "d2_stretches"]}).reset_index()
    a["d1_per_hour"] = a.d1_episodes / a.active_h
    a["d1_per_1000_work"] = 1000 * a.d1_episodes / a.work_actions.where(a.work_actions > 0)
    a["d1_bash_per_1000"] = 1000 * a.d1_bash / a.bash_actions.where(a.bash_actions > 0)
    a["d1_gui_per_1000"] = 1000 * a.d1_gui / a.gui_actions.where(a.gui_actions > 0)
    a["stuck_share"] = a.stuck_h / a.active_h
    a["unrecovered_share"] = 1 - a.d1_recovered / a.d1_episodes.where(a.d1_episodes > 0)
    a["d2_per_hour"] = a.d2_stretches / a.active_h
    a["bash_share_of_work"] = a.bash_actions / a.work_actions.where(a.work_actions > 0)
    a = a.merge(rel[["id", "name", "model_string", "family", "joined", "release", "release_source"]].rename(columns={"id": "agent_id"}),
                on="agent_id", how="left")
    return a


ag = table(["agent_id"])
ag["eligible"] = (ag.active_h >= v.MIN_HOURS) & (ag.work_actions >= v.MIN_WORK)
ag.sort_values("release").to_csv(v.OUT / "agent_stuck.csv", index=False)
ar = table(["agent_id", "regime"])
ar["eligible"] = (ar.active_h >= v.MIN_HOURS) & (ar.work_actions >= v.MIN_WORK)
ar.sort_values(["regime", "release"]).to_csv(v.OUT / "agent_regime.csv", index=False)
ac = table(["agent_id", "period"]).merge(room, on=["agent_id", "period"], how="left")
ac["room"] = ac.room.fillna("general")
ac["cell"] = ac.period + "|" + ac.room
ac.sort_values(["cell", "release"]).to_csv(v.OUT / "agent_cell.csv", index=False)

kb = (t[t.cls == "work"].groupby(["regime", "kgroup"]).size().rename("work_actions").reset_index()
      .merge(ep.groupby(["regime", "kgroup"]).agg(d1_episodes=("n", "size"), median_len=("n", "median"),
                                                  recovered=("recovered", "mean")).reset_index(), how="left"))
kb["d1_per_1000_work"] = 1000 * kb.d1_episodes / kb.work_actions
kb.to_csv(v.OUT / "kind_breakdown.csv", index=False)
tot_h = t.dt.sum() / 3600
print(f"active hours {tot_h:,.0f}; work actions {(t.cls == 'work').sum():,}; D1/h {len(ep) / tot_h:.3f}; "
      f"stuck share {ep.stuck_s.sum() / 3600 / tot_h:.4f}; eligible agents {int(ag.eligible.sum())} of {len(ag)}")
