"""Step 9: the pre-registered comparisons (H1-H6) on the hand-picked memes, and the base rate from the
mechanically drawn background terms.

Level: per-meme rates are (adopter pairs / cohort pairs) of one meme; group statistics are means of per-meme rates;
pooled rates are sums of pairs. Permutation tests shuffle the meme labels (10,000 draws, two-sided, seed 0);
the family test shuffles family labels among the cohort agents of each meme.

Reads   out/meme_summary.csv, out/meme_agent.csv, out/bg_summary.csv, out/bg_agent.csv, out/bg_origins.csv
Writes  out/contrasts.csv          H2, H3, H5 under A7, A1, A30, A7-durable, A7-room, plus held-30d (exploratory)
        out/contrasts_family.csv   H4: pair-level A7 and A30 by model family, within-meme permutation
        out/background_rate.csv    background terms: adoption, latency and retention, overall and by origin year
        out/background_terms.csv   per background term: eligibility and rates
        out/background_by_agent.csv   background A1 per agent, with family and join date
        out/background_by_group.csv   background A1 by model family, and by join cohort on the terms coined from 2026-07-24
Usage:  ./venv/bin/python3 -I data-scouts/memetic-spread/scripts/09_contrasts.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402

rng = np.random.default_rng(0)
S = pd.read_csv(v.OUT / "meme_summary.csv", keep_default_na=False, na_values=[""])
P = pd.read_csv(v.OUT / "meme_agent.csv")
S["traceable"] = S.placebo_pre30 == 0
S["year"] = S.origin_utc.str[:4]
S["human_origin"] = S.origin_type.isin(["organizer", "viewer"])
S["held30_pct"] = 100 * S.n_held30 / S.n_obs30.where(S.n_obs30 > 0)
print("memes:", len(S), "| traceable (pre-origin placebo = 0):", int(S.traceable.sum()), "| not:", S[~S.traceable].meme_id.tolist())
print("H1  median per-meme A7 among traceable memes:", S[S.traceable].A7_pct.median(), "%  (pooled pairs",
      int(S[S.traceable].n_A7.sum()), "/", int(S[S.traceable].n_cohort7.sum()), ")")
late = S[S.traceable & (S.n_late_carriers > 0)]
print("H6  traceable memes with >=1 late-joiner carrier (regex level, before the precision read):", len(late), "of", int(S.traceable.sum()))


def perm(a, b, n=10000):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan, len(a), len(b)
    obs = a.mean() - b.mean()
    x = np.concatenate([a, b])
    hits = 0
    for _ in range(n):
        rng.shuffle(x)
        hits += abs(x[:len(a)].mean() - x[len(a):].mean()) >= abs(obs) - 1e-12
    return round(obs, 1), round(hits / n, 3), len(a), len(b)


COMP = {"H2 false vs true (claims and rules with a truth value)": (lambda d: d[d.truth == "false"], lambda d: d[d.truth == "true"]),
        "H3 agent-originated vs human-originated": (lambda d: d[~d.human_origin], lambda d: d[d.human_origin]),
        "H5 origin 2026 vs 2025": (lambda d: d[d.year == "2026"], lambda d: d[d.year == "2025"])}
MEAS = ["A7_pct", "A1_pct", "A30_pct", "A7_durable_pct", "A7_room_pct", "C7_pct", "held30_pct"]
rows = []
for sample, d in (("traceable memes", S[S.traceable]), ("all kept memes (sensitivity)", S)):
    for cname, (fa, fb) in COMP.items():
        for m in MEAS:
            a, b = fa(d), fb(d)
            diff, p, na, nb = perm(a[m], b[m])
            rows.append(dict(sample=sample, comparison=cname, measure=m, n_memes_a=na, n_memes_b=nb,
                             mean_a=round(a[m].mean(), 1), mean_b=round(b[m].mean(), 1), diff_points=diff, perm_p=p,
                             pre_registered=m != "held30_pct"))
C = pd.DataFrame(rows)
C.to_csv(v.OUT / "contrasts.csv", index=False)
pd.set_option("display.width", 250)
print(C[C["sample"] == "traceable memes"].drop(columns="sample").to_string(index=False))

# --- H4: family, within meme ----------------------------------------------------------------------------
tr = set(S[S.traceable].meme_id)
fam_rows = []
for col, coh in (("A7", "cohort7"), ("A30", "cohort30")):
    q = P[P.meme_id.isin(tr) & P[coh]][["meme_id", "family", col]].copy()
    for f in sorted(q.family.unique()):
        memes_f = q[q.family == f].meme_id.unique()
        qq = q[q.meme_id.isin(memes_f)]
        inn, out = qq[qq.family == f][col], qq[qq.family != f][col]
        if len(inn) < 8 or len(out) < 8:
            continue
        obs = 100 * (inn.mean() - out.mean())
        hits = 0
        groups = [g for _, g in qq.groupby("meme_id")]
        for _ in range(2000):
            di = []
            do = []
            for g in groups:
                lab = rng.permutation(g.family.values)
                di.append(g[col].values[lab == f])
                do.append(g[col].values[lab != f])
            di, do = np.concatenate(di), np.concatenate(do)
            hits += abs(100 * (di.mean() - do.mean())) >= abs(obs) - 1e-12
        fam_rows.append(dict(measure=col, family=f, n_memes=len(memes_f), pairs_family=len(inn), adopters_family=int(inn.sum()),
                             pct_family=round(100 * inn.mean(), 1), pairs_others=len(out), adopters_others=int(out.sum()),
                             pct_others=round(100 * out.mean(), 1), diff_points=round(obs, 1), perm_p=round(hits / 2000, 3)))
F = pd.DataFrame(fam_rows)
F.to_csv(v.OUT / "contrasts_family.csv", index=False)
print(F.to_string(index=False))

# --- background rate --------------------------------------------------------------------------------------
if (v.OUT / "bg_summary.csv").exists():
    B = pd.read_csv(v.OUT / "bg_summary.csv")
    BP = pd.read_csv(v.OUT / "bg_agent.csv")
    BO = pd.read_csv(v.OUT / "bg_origins.csv", keep_default_na=False)
    B = B.merge(BO[["meme_id", "n_chat_messages", "n_agent_speakers"]], on="meme_id")
    others_pre = BP[BP.pre_ever & ~BP.originator].groupby("meme_id").size()
    B["others_with_term_before_origin"] = B.meme_id.map(others_pre).fillna(0).astype(int)
    B["eligible"] = (B.others_with_term_before_origin == 0) & (B.n_cohort7 > 0)
    B["year"] = B.origin_utc.str[:4]
    B.to_csv(v.OUT / "background_terms.csv", index=False)
    E = B[B.eligible]
    lat = BP[BP.meme_id.isin(E.meme_id) & BP.cohort7 & BP.A7]

    def block(name, d):
        l = lat[lat.meme_id.isin(d.meme_id)].latency_h
        boot = [100 * (s.n_A1.sum() / s.n_cohort7.sum()) for s in (d.sample(len(d), replace=True, random_state=i) for i in range(2000))]
        return dict(sample=name, n_terms=len(d), cohort_pairs=int(d.n_cohort7.sum()), median_cohort=d.n_cohort7.median(),
                    A1_pairs=int(d.n_A1.sum()), A1_pct=round(100 * d.n_A1.sum() / d.n_cohort7.sum(), 1),
                    A1_ci_lo=round(np.percentile(boot, 2.5), 1), A1_ci_hi=round(np.percentile(boot, 97.5), 1),
                    A7_pairs=int(d.n_A7.sum()), A7_pct=round(100 * d.n_A7.sum() / d.n_cohort7.sum(), 1),
                    A7_room_pct=round(100 * d.n_A7_room.sum() / d.n_cohort_room.sum(), 1) if d.n_cohort_room.sum() else np.nan,
                    cohort_room_pairs=int(d.n_cohort_room.sum()),
                    per_term_A7_median=d.A7_pct.median(), terms_with_zero_A7=int((d.n_A7 == 0).sum()),
                    median_latency_min=round(60 * l.median(), 1), latency_p75_min=round(60 * l.quantile(.75), 1),
                    A7_durable_pairs=int(d.n_A7_durable.sum()), A7_durable_pct=round(100 * d.n_A7_durable.sum() / d.n_cohort7.sum(), 1),
                    C7_pairs=int(d.n_C7.sum()), C7_pct=round(100 * d.n_C7.sum() / d.n_cohort7.sum(), 1),
                    S7_pairs=int(d.n_S7.sum()), S7_pct=round(100 * d.n_S7.sum() / d.n_cohort7.sum(), 1),
                    adopters_gone_within_1d_pct=round(100 * (lat[lat.meme_id.isin(d.meme_id)].retention_days < 1).mean(), 1),
                    adopters_still_matching_30d_pct=round(100 * (lat[lat.meme_id.isin(d.meme_id)].retention_days >= 30).mean(), 1),
                    held7=int(d.n_held7.sum()), obs7=int(d.n_obs7.sum()), held7_pct=round(100 * d.n_held7.sum() / d.n_obs7.sum(), 1),
                    held30=int(d.n_held30.sum()), obs30=int(d.n_obs30.sum()), held30_pct=round(100 * d.n_held30.sum() / d.n_obs30.sum(), 1))

    R = pd.DataFrame([block("all eligible background terms", E), block("origin 2025", E[E.year == "2025"]), block("origin 2026", E[E.year == "2026"]),
                      block("2026, after rooms (>= 2026-02-25)", E[E.origin_utc >= "2026-02-25"]),
                      *[block("origin quarter " + k, g) for k, g in E.groupby(pd.PeriodIndex(pd.to_datetime(E.origin_utc.str.replace(" UTC", "")), freq="Q").astype(str))],
                      block("used in chat by the coiner only", E[E.n_agent_speakers <= 1]),
                      block("used in chat by >= 2 agents", E[E.n_agent_speakers >= 2])])
    R.to_csv(v.OUT / "background_rate.csv", index=False)
    print("background terms:", len(B), "| eligible (new to every other agent's memory):", len(E))
    print(R.T.to_string())

    # background adoption by receiver: family, agent, and join cohort on the same late-2026 terms
    q = BP[BP.meme_id.isin(E.meme_id) & BP.cohort7].copy()
    joined = v.roster().set_index("name").joined
    q["joined"] = q.agent.map(joined)
    q["t0"] = pd.to_datetime(q.meme_id.map(E.set_index("meme_id").origin_utc).str.replace(" UTC", ""))
    A = q.groupby(["family", "agent"]).agg(pairs=("A1", "size"), A1=("A1", "sum"), joined=("joined", "first")).reset_index()
    A["A1_pct"] = (100 * A.A1 / A.pairs).round(1)
    A.sort_values("joined").to_csv(v.OUT / "background_by_agent.csv", index=False)
    G = q.groupby("family").agg(pairs=("A1", "size"), A1=("A1", "sum"), agents=("agent", "nunique"), terms=("meme_id", "nunique")).reset_index()
    G.insert(0, "split", "model family, all eligible terms")
    late = q[q.t0 >= "2026-07-24"].copy()
    late["family"] = np.where(late.joined < "2026-01-01", "joined 2025", np.where(late.joined < "2026-07-01", "joined 2026-H1", "joined 2026-H2"))
    H = late.groupby("family").agg(pairs=("A1", "size"), A1=("A1", "sum"), agents=("agent", "nunique"), terms=("meme_id", "nunique")).reset_index()
    H.insert(0, "split", "join cohort, terms coined from 2026-07-24")
    G = pd.concat([G, H]).rename(columns={"family": "group"})
    G["A1_pct"] = (100 * G.A1 / G.pairs).round(1)
    G.to_csv(v.OUT / "background_by_group.csv", index=False)
    print(G.to_string(index=False))
    per = late.groupby(["meme_id", "family"]).A1.mean().unstack()
    d = (per["joined 2025"] - per["joined 2026-H2"]).dropna()
    print("late-2026 terms:", len(d), "| veterans higher on", int((d > 0).sum()), "| newcomers higher on", int((d < 0).sum()))
    big = A[A.pairs >= 15]
    print("agents with >= 15 pairs:", len(big), "| A1 range", big.A1_pct.min(), "-", big.A1_pct.max())
