"""Step 5: pair-level measures (meme x agent) and the per-meme summary, exactly as defined in HYPOTHESIS.md.

Level of every count: (meme, agent) pairs, unless a column name says otherwise.

Reads   memes.csv, stance_coding.csv (optional, hand coding), out/<tag>_origins.csv, out/<tag>_memory_agent.csv,
        out/<tag>_memory_daily.csv, out/<tag>_memory_lines.csv, out/<tag>_chat_hits.csv, out/<tag>_action_hits.csv,
        core/out/memories_index.parquet, core/out/chat.parquet
Writes  out/<tag>_agent.csv        one row per (meme, agent with >=1 snapshot): cohort flags, placebo, A1/A7/A30/durable,
                                   latency, retention, chat uptake, stated action, late-joiner carriage
        out/<tag>_summary.csv      one row per meme with numerators and denominators
        out/<tag>_first_lines.csv  the first matching memory line of every adopter pair (input to hand coding)
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/05_measures.py [--memes other.csv --tag bg]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--memes", default=str(v.MEMES))
ap.add_argument("--tag", default="meme")
a = ap.parse_args()
tag = a.tag
D7, D30, D1 = pd.Timedelta(days=7), pd.Timedelta(days=30), pd.Timedelta(days=1)

M = pd.read_csv(a.memes, keep_default_na=False)
if "status" in M.columns:
    M = M[M.status == "keep"].reset_index(drop=True)
O = pd.read_csv(v.OUT / f"{tag}_origins.csv", keep_default_na=False)
O["t0"] = pd.to_datetime(O.origin_utc.str.replace(" UTC", ""))
MA = pd.read_csv(v.OUT / f"{tag}_memory_agent.csv")
for col in ("last_before_origin_ts", "first_after_ts", "last_after_ts"):
    MA[col] = pd.to_datetime(MA[col], format="ISO8601")
MD = pd.read_csv(v.OUT / f"{tag}_memory_daily.csv")
MD["last_match_ts"] = pd.to_datetime(MD.last_match_ts, format="ISO8601")
CH = pd.read_csv(v.OUT / f"{tag}_chat_hits.csv", keep_default_na=False)
CH["ts"] = pd.to_datetime(CH.utc.str.replace(" UTC", ""))
AH = pd.read_csv(v.OUT / f"{tag}_action_hits.csv", keep_default_na=False)
AH["ts"] = pd.to_datetime(AH.utc.str.replace(" UTC", ""))

idx = v.memories_index()
snaps = {aid: g.ts.values for aid, g in idx.groupby("agent_id")}  # sorted (index is sorted by ts)
names = idx.drop_duplicates("agent_id").set_index("agent_id").agent.to_dict()
c = v.chat_clean()
c = c[c.speaker_type == "agent"]


def has_snap(aid, lo, hi):
    s = snaps[aid]
    i = s.searchsorted(np.datetime64(lo), side="left")
    return i < len(s) and s[i] <= np.datetime64(hi)


rows = []
for o in O.itertuples():
    t0 = o.t0
    ma = MA[MA.meme_id == o.meme_id].set_index("agent_id")
    md = MD[(MD.meme_id == o.meme_id) & (MD.last_match_ts > t0) & (MD.last_match_ts <= t0 + D30)]
    dur = md.groupby("agent_id").date.nunique()
    ch = CH[(CH.meme_id == o.meme_id) & (CH.ts > t0) & (CH.ts <= t0 + D7) & (CH.agent_speaker_id != "")]
    ch1 = ch.groupby("agent_speaker_id").event_index.min()
    ah = AH[(AH.meme_id == o.meme_id) & (AH.ts > t0) & (AH.ts <= t0 + D7)]
    ah1 = ah.groupby("agent_id").event_index.min()
    room = c[(c.room == o.origin_room) & (c.ts >= t0 - D7) & (c.ts <= t0 + D7)].agent_speaker_id.unique()
    for aid, s in snaps.items():
        first_snap, last_snap = pd.Timestamp(s[0]), pd.Timestamp(s[-1])
        originator = aid == o.origin_agent_id
        r = dict(meme_id=o.meme_id, agent_id=aid, agent=names[aid], family=v.family(names[aid]), originator=originator,
                 cohort7=(not originator) and has_snap(aid, t0, t0 + D7),
                 cohort30=(not originator) and has_snap(aid, t0, t0 + D30),
                 in_origin_room=aid in room, late_joiner=(not originator) and first_snap > t0 + D7,
                 agent_first_snapshot=first_snap, agent_last_snapshot=last_snap)
        r["cohort_room"] = r["cohort7"] and r["in_origin_room"]
        g = ma.loc[aid] if aid in ma.index else None
        lb = g.last_before_origin_ts if g is not None else pd.NaT
        r["pre_ever"] = g is not None and g.n_match_before_origin > 0
        r["pre30"] = bool(pd.notna(lb) and lb >= t0 - D30)
        fa = g.first_after_ts if g is not None else pd.NaT
        la = g.last_after_ts if g is not None else pd.NaT
        r["carrier_ever"] = bool(pd.notna(fa))
        r["first_match_ts"], r["first_match_id"] = fa, (g.first_after_id if g is not None else None)
        r["last_match_ts"], r["last_match_id"] = la, (g.last_after_id if g is not None else None)
        r["latency_h"] = round((fa - t0) / pd.Timedelta(hours=1), 2) if pd.notna(fa) else np.nan
        r["A1"] = bool(pd.notna(fa) and fa <= t0 + D1)
        r["A7"] = bool(pd.notna(fa) and fa <= t0 + D7)
        r["A30"] = bool(pd.notna(fa) and fa <= t0 + D30)
        r["A7_durable"] = bool(r["A7"] and dur.get(aid, 0) >= 2)
        r["retention_days"] = round((la - fa) / D1, 2) if pd.notna(fa) else np.nan
        r["censored"] = bool(pd.notna(la) and la >= last_snap - D1)
        r["observable_7d"] = bool(pd.notna(fa) and last_snap >= fa + D7)
        r["held_7d"] = bool(r["observable_7d"] and la >= fa + D7)
        r["observable_30d"] = bool(pd.notna(fa) and last_snap >= fa + D30)
        r["held_30d"] = bool(r["observable_30d"] and la >= fa + D30)
        r["C7"] = aid in ch1.index
        r["C7_first_event_index"] = ch1.get(aid, np.nan)
        r["S7"] = aid in ah1.index
        r["S7_first_event_index"] = ah1.get(aid, np.nan)
        rows.append(r)
P = pd.DataFrame(rows)

# hand-coded stance of the first matching memory line (false claims: endorses / corrects / neutral)
stance_file = v.CASE / "stance_coding.csv"
if tag == "meme" and stance_file.exists():
    S = pd.read_csv(stance_file, keep_default_na=False)[["meme_id", "agent_id", "stance"]]
    P = P.merge(S, on=["meme_id", "agent_id"], how="left")
else:
    P["stance"] = np.nan
P.to_csv(v.OUT / f"{tag}_agent.csv", index=False)

# first matching line per adopter pair (the text behind first_match_id)
L = pd.read_csv(v.OUT / f"{tag}_memory_lines.csv", keep_default_na=False)
ad = P[P.carrier_ever & ~P.originator][["meme_id", "agent_id", "agent", "first_match_id", "first_match_ts", "cohort7", "A7", "late_joiner"]]
fl = ad.merge(L[["meme_id", "agent_id", "line", "first_id", "last_ts", "n_snap", "n_dates"]],
              left_on=["meme_id", "agent_id", "first_match_id"], right_on=["meme_id", "agent_id", "first_id"], how="left")
fl = fl.rename(columns={"last_ts": "line_last_ts", "n_snap": "line_n_snapshots", "n_dates": "line_n_dates"}).drop(columns="first_id")
fl["link"] = fl.first_match_ts.map(v.deep_link)
fl.sort_values(["meme_id", "first_match_ts"]).to_csv(v.OUT / f"{tag}_first_lines.csv", index=False)


def pct(n, d):
    return round(100 * n / d, 1) if d else np.nan


summ = []
for o in O.itertuples():
    p = P[P.meme_id == o.meme_id]
    m = M[M.meme_id == o.meme_id].iloc[0]
    co, co30, cr = p[p.cohort7], p[p.cohort30], p[p.cohort_room]
    ad7 = co[co.A7]
    car = p[p.carrier_ever & ~p.originator]
    lj = p[p.late_joiner]
    row = dict(meme_id=o.meme_id, origin_utc=o.origin_utc, origin_event_index=o.origin_event_index, origin_speaker=o.origin_speaker,
               origin_room=o.origin_room, n_cohort7=len(co), placebo_pre30=int(co.pre30.sum()), placebo_pre_ever=int(co.pre_ever.sum()),
               originator_pre30=int(p[p.originator].pre30.sum()),
               n_A1=int(co.A1.sum()), n_A7=int(co.A7.sum()), n_A7_durable=int(co.A7_durable.sum()),
               n_cohort30=len(co30), n_A30=int(co30.A30.sum()), n_cohort_room=len(cr), n_A7_room=int(cr.A7.sum()),
               n_C7=int(co.C7.sum()), n_S7=int(co.S7.sum()),
               A1_pct=pct(co.A1.sum(), len(co)), A7_pct=pct(co.A7.sum(), len(co)), A7_durable_pct=pct(co.A7_durable.sum(), len(co)),
               A30_pct=pct(co30.A30.sum(), len(co30)), A7_room_pct=pct(cr.A7.sum(), len(cr)),
               C7_pct=pct(co.C7.sum(), len(co)), S7_pct=pct(co.S7.sum(), len(co)),
               median_latency_h=round(ad7.latency_h.median(), 2) if len(ad7) else np.nan,
               n_carriers_ever=len(car), n_obs7=int(car.observable_7d.sum()), n_held7=int(car.held_7d.sum()),
               n_obs30=int(car.observable_30d.sum()), n_held30=int(car.held_30d.sum()),
               held7_pct=pct(car.held_7d.sum(), car.observable_7d.sum()), held30_pct=pct(car.held_30d.sum(), car.observable_30d.sum()),
               median_retention_days=round(car.retention_days.median(), 1) if len(car) else np.nan,
               n_late_joiners=len(lj), n_late_carriers=int(lj.carrier_ever.sum()),
               last_match_utc=str(car.last_match_ts.max())[:16] if len(car) else "",
               lifetime_days=round((car.last_match_ts.max() - o.t0) / D1, 1) if len(car) else np.nan)
    for k in ("label", "origin_type", "kind", "truth"):
        if k in M.columns:
            row[k] = m[k]
    summ.append(row)
S = pd.DataFrame(summ)
S.to_csv(v.OUT / f"{tag}_summary.csv", index=False)
pd.set_option("display.width", 250)
cols = ["meme_id", "origin_utc", "origin_speaker", "n_cohort7", "placebo_pre30", "placebo_pre_ever", "originator_pre30", "n_A1", "n_A7",
        "n_A7_durable", "n_A30", "n_cohort30", "n_C7", "n_S7", "median_latency_h", "n_held7", "n_obs7", "n_held30", "n_obs30",
        "n_late_carriers", "n_late_joiners", "lifetime_days"]
print(S[cols].to_string(index=False))
