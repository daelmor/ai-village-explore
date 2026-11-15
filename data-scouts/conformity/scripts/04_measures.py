"""Headline measures and baselines of HYPOTHESIS.md from out/decisions.csv and out/positions.csv.

Writes out/measures.csv (every rate with numerator, denominator, level and scope), out/agent_dissent.csv
(per-agent positions, dissents, base rate) and out/dissents.csv (every initial dissent with its rows, for
hand-checking what happened to it afterwards).
Usage: ./venv/bin/python3 -I data-scouts/conformity/scripts/04_measures.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

rng = np.random.default_rng(0)
D = pd.read_csv(v.OUT / "decisions.csv")
P = pd.read_csv(v.OUT / "positions.csv")
D = D[(D.n_positions >= 3) & D.winner.notna() & (D.winner != "")].copy()
P = P[(P.check == "ok") & ~P.abstain.astype(bool) & P.decision_id.isin(D.decision_id)].copy()
for col in ("dissent", "abandoned_in_window", "self", "initial_agrees", "final_agrees"):
    P[col] = P[col].astype(bool)
for col in ("unanimous_final", "never_contested", "first_position_won"):
    D[col] = D[col].astype(bool)
D["formal"] = D.kind.isin(["vote", "accusation"])
FU = pd.read_csv(v.CASE / "dissent_followup.csv")   # hand-read: what each unresolved dissenter did later that day
rows = []


def rate(label, num, den, level, scope):
    rows.append(dict(measure=label, numerator=int(num), denominator=int(den), rate=round(num / den, 4) if den else None,
                     level=level, scope=scope))


def binom_p_ge(k, n, p):
    """Exact one-sided binomial P(X >= k)."""
    from math import comb
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def block(scope, d):
    p = P[P.decision_id.isin(d.decision_id)]
    n = len(d)
    if n == 0:
        return
    rate("unanimous (final positions)", d.unanimous_final.sum(), n, "decision", scope)
    rate("never contested (initial positions)", d.never_contested.sum(), n, "decision", scope)
    rate("initial dissent", p.dissent.sum(), len(p), "position", scope)
    rate("initial dissent, self-interested excluded", p[~p.self].dissent.sum(), len(p[~p.self]), "position", scope)
    rate("first stated position won", d.first_position_won.sum(), n, "decision", scope)
    exp = d.winner_share_final.mean()
    rows.append(dict(measure="first position won: chance baseline (mean winner share of final positions)", numerator=None,
                     denominator=n, rate=round(exp, 4), level="decision", scope=scope))
    rows.append(dict(measure="first position won: exact binomial p vs baseline", numerator=None, denominator=n,
                     rate=round(binom_p_ge(int(d.first_position_won.sum()), n, exp), 4), level="decision", scope=scope))
    nd = int(p.dissent.sum())
    rate("dissent abandoned inside the coded window", p.abandoned_in_window.sum(), nd, "position", scope)
    fu = p[p.dissent & ~p.abandoned_in_window].merge(FU, on=["decision_id", "agent"], how="left")
    rate("dissent abandoned the same day (window + hand-read follow-up)",
         p.abandoned_in_window.sum() + (fu.same_day == "deferred").sum(), nd, "position", scope)
    # baseline 1: independent agents at their own dissent rates
    a = P.groupby("agent").agg(n=("dissent", "size"), k=("dissent", "sum"), family=("family", "first"))
    famrate = P.groupby("family").dissent.mean()
    a["d"] = np.where(a.n >= 5, a.k / a.n, a.family.map(famrate))
    pj = np.array([np.prod(1 - a.d.reindex(p[p.decision_id == i].agent).values) for i in d.decision_id])
    sims = (rng.random((10000, len(pj))) < pj).mean(1)
    lo, hi = np.percentile(sims, [2.5, 97.5])
    rows.append(dict(measure="never contested: expected if agents dissented independently at their own rates", numerator=None,
                     denominator=n, rate=round(pj.mean(), 4), level="decision", scope=f"{scope}; 95% simulated interval {lo:.3f}-{hi:.3f}"))


block("all decisions", D)
block("formal votes and accusations", D[D.formal])
block("accusations (saboteur game)", D[D.kind == "accusation"])
block("votes (elections, polls)", D[D.kind == "vote"])
block("proposals (accept / reject)", D[D.kind == "proposal"])
for y, d in D.groupby("year"):
    block(f"year {int(y)}", d)
block("7 or more positions", D[D.n_positions >= 7])
block("3 to 6 positions", D[D.n_positions < 7])
M = pd.DataFrame(rows)
M.to_csv(v.OUT / "measures.csv", index=False)

a = P.groupby(["agent", "family"]).agg(positions=("dissent", "size"), dissents=("dissent", "sum"),
                                       abandoned_in_window=("abandoned_in_window", "sum")).reset_index()
a["dissent_rate"] = (a.dissents.astype(float) / a.positions).round(3)
a.sort_values("positions", ascending=False).to_csv(v.OUT / "agent_dissent.csv", index=False)
f = P.groupby("family").agg(positions=("dissent", "size"), dissents=("dissent", "sum"))
f["rate"] = (f.dissents.astype(float) / f.positions).round(3)

dz = P[P.dissent].merge(D[["decision_id", "kind", "question", "winner", "n_positions", "goal"]], on="decision_id")
dz[["decision_id", "kind", "question", "winner", "n_positions", "agent", "self", "initial_option", "initial_ei", "final_option",
    "final_ei", "abandoned_in_window", "utc", "link", "initial_quote", "final_quote"]].sort_values("initial_ei").to_csv(
    v.OUT / "dissents.csv", index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 95); pd.set_option("display.max_rows", 200)
print(M.to_string(index=False))
print(f.to_string())
print("decisions by kind:", D.kind.value_counts().to_dict(), "| positions:", len(P), "| agents:", P.agent.nunique(),
      "| median positions per decision:", D.n_positions.median(), "| median present:", D.n_present.median())
