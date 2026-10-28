"""Nudger 'pause-again' rate on the current 1,997 (nudge, addressee) pairs: is the addressee's FIRST non-talk event
after the nudge a PAUSE or WAIT? (Recomputes the first-pass 41.8% with the second-pass nudge definition.)
Non-talk = any event by the agent with actionType not in {AGENT_TALK}. Horizon: 120 min after the nudge."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import village_lib as v  # noqa: E402

HORIZON_MIN = 120
n = pd.read_csv(v.OUT / "nudger_stats.csv")
n = n[n.addressed_agent_id.notna()].copy()
n["ts"] = pd.to_datetime(n.timestamp_utc.str.replace(" UTC", ""))
e = v.events(("event_index", "created_at", "actionType", "agentId"))
e = e[e.agentId.notna() & (e.actionType != "AGENT_TALK")].sort_values("ts")
by_agent = {a: g for a, g in e.groupby("agentId")}
rows = []
for r in n.itertuples(index=False):
    g = by_agent.get(r.addressed_agent_id)
    nxt_type, nxt_ei, nxt_lat = None, None, None
    if g is not None:
        i = g.ts.searchsorted(r.ts, side="right")
        if i < len(g) and (g.ts.iloc[i] - r.ts) <= pd.Timedelta(minutes=HORIZON_MIN):
            nxt_type, nxt_ei, nxt_lat = g.actionType.iloc[i], int(g.event_index.iloc[i]), round((g.ts.iloc[i] - r.ts).total_seconds() / 60, 1)
    rows.append(dict(next_nontalk_event_type=nxt_type, next_nontalk_event_index=nxt_ei, next_nontalk_latency_min=nxt_lat,
                     pause_again=(nxt_type in ("PAUSE", "WAIT")) if nxt_type else None))
R = pd.concat([n.drop(columns=["ts"]).reset_index(drop=True), pd.DataFrame(rows)], axis=1)
R.to_csv(v.OUT / "nudger_stats.csv", index=False)
has = R.pause_again.notna()
pa = R.loc[has, "pause_again"].astype(bool)
# bootstrap by nudge
rng = np.random.default_rng(0)
g = R[has].groupby("event_index").pause_again.agg(["sum", "size"])
idx = rng.integers(0, len(g), size=(2000, len(g)))
rates = g["sum"].values[idx].sum(1) / g["size"].values[idx].sum(1)
print(f"pairs with a non-talk event within {HORIZON_MIN} min: {has.sum()} / {len(R)}")
print(f"pause-again (first non-talk event is PAUSE/WAIT): {pa.sum()} / {has.sum()} = {pa.mean():.1%}  (95% CI {np.percentile(rates,2.5):.1%}–{np.percentile(rates,97.5):.1%})")
print("next event type distribution:", R.next_nontalk_event_type.value_counts(dropna=False).to_dict())
print("pause-again by misfire:", R[has].groupby("misfire").pause_again.agg(["mean", "size"]).round(3).to_dict())
print("pause-again by reply_class:", R[has].groupby("reply_class").pause_again.agg(["mean", "size"]).round(3).to_dict())
