"""Tests H1-H4 of HYPOTHESIS.md on the tables written by script 02.

Writes out/trend_tests.csv (one row per test: n, Spearman rho, permutation p, definition, scope),
out/cell_tests.csv (one row per goal-period x room cell with >= 4 agents), out/provider_changes.csv
(D1 rate 21 days before / after each provider-specific scaffolding change) and prints a summary.
Usage: ./venv/bin/python3 -I data-scouts/stuck-time/scripts/03_trend.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

rng = np.random.default_rng(0)


def spearman(x, y, n_perm=10000):
    x, y = pd.Series(x).rank().values, pd.Series(y).rank().values
    if len(x) < 4 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan
    rho = np.corrcoef(x, y)[0, 1]
    hits = sum(abs(np.corrcoef(x, rng.permutation(y))[0, 1]) >= abs(rho) - 1e-12 for _ in range(n_perm))
    return rho, (hits + 1) / (n_perm + 1)


ag = pd.read_csv(v.OUT / "agent_stuck.csv", parse_dates=["release", "joined"])
ar = pd.read_csv(v.OUT / "agent_regime.csv", parse_dates=["release", "joined"])
ac = pd.read_csv(v.OUT / "agent_cell.csv", parse_dates=["release", "joined"])
rows = []


def test(label, d, col, scope, definition):
    d = d.dropna(subset=[col, "release"])
    rho, p = spearman(d.release.astype("int64"), d[col])
    rows.append(dict(test=label, scope=scope, definition=definition, measure=col, n_agents=len(d),
                     rho=round(rho, 3) if rho == rho else None, perm_p=round(p, 4) if p == p else None))


el = ag[ag.eligible]
test("H1", el, "d1_per_hour", "all eligible agents", "D1")
test("H1 without Claude 3 Opus", el[el.name != "Claude 3 Opus"], "d1_per_hour", "eligible, old model in new scaffold dropped", "D1")
test("H1 per 1000 work actions", el, "d1_per_1000_work", "all eligible agents", "D1")
test("H1 stuck share of time", el, "stuck_share", "all eligible agents", "D1")
test("H1 join date instead of release", el.assign(release=el.joined), "d1_per_hour", "all eligible agents", "D1")
test("H4", el, "d2_per_hour", "all eligible agents", "D2")
test("H3", el[el.d1_recovered >= 20], "median_recover_s", "eligible with >= 20 recovered episodes", "D1")
test("modality: bash only", el[el.bash_actions >= 500], "d1_bash_per_1000", "eligible with >= 500 bash actions", "D1")
test("modality: GUI only", el[el.gui_actions >= 500], "d1_gui_per_1000", "eligible with >= 500 GUI actions", "D1")
for reg, d in ar[ar.eligible].groupby("regime"):
    test("H2 regime", d, "d1_per_hour", reg, "D1")
    test("H2 regime (D2)", d, "d2_per_hour", reg, "D2")
    test("H2 regime per 1000 work", d, "d1_per_1000_work", reg, "D1")

# --- within goal-period x room cells -------------------------------------------------------------------------
c = ac[ac.active_h >= v.CELL_MIN_HOURS].copy()
cells, pooled = [], []
for cell, d in c.groupby("cell"):
    if len(d) < v.CELL_MIN_AGENTS or d.release.nunique() < 2:
        continue
    rr, pr = d.release.rank(pct=True), d.d1_per_hour.rank(pct=True)
    rho = np.corrcoef(rr, pr)[0, 1] if pr.std() > 0 else np.nan
    cells.append(dict(cell=cell, n_agents=len(d), episodes=int(d.d1_episodes.sum()), active_h=round(d.active_h.sum(), 1),
                      rho=rho, first_turn=d.first_turn.min()))
    if pr.std() > 0:
        pooled.append(pd.DataFrame(dict(rr=rr - rr.mean(), pr=pr - pr.mean(), cell=cell,
                                        regime=v.regime_of(pd.to_datetime(d.first_turn)).values)))
cells = pd.DataFrame(cells).sort_values("first_turn")
cells.to_csv(v.OUT / "cell_tests.csv", index=False)
pp = pd.concat(pooled)
valid = cells.dropna(subset=["rho"])
neg = int((valid.rho < 0).sum())
# pooled within-cell correlation with a permutation that shuffles rates inside each cell
obs = np.corrcoef(pp.rr, pp.pr)[0, 1]
perm = []
for _ in range(2000):
    sh = pp.groupby("cell").pr.transform(lambda s: rng.permutation(s.values))
    perm.append(np.corrcoef(pp.rr, sh)[0, 1])
p_pool = (np.sum(np.abs(perm) >= abs(obs)) + 1) / 2001
rows.append(dict(test="H2 within cells (pooled rank correlation)", scope=f"{len(valid)} cells with >= {v.CELL_MIN_AGENTS} agents; "
                 f"{neg} negative ({neg / len(valid):.0%})", definition="D1", measure="d1_per_hour", n_agents=len(pp),
                 rho=round(obs, 3), perm_p=round(p_pool, 4)))
for reg, d in pp.groupby("regime"):
    if d.cell.nunique() >= 3:
        vc = valid[valid.cell.isin(d.cell.unique())]
        rows.append(dict(test="H2 within cells by regime", scope=f"{reg}: {d.cell.nunique()} cells, {int((vc.rho < 0).sum())} negative",
                         definition="D1", measure="d1_per_hour", n_agents=len(d), rho=round(np.corrcoef(d.rr, d.pr)[0, 1], 3), perm_p=None))
tt = pd.DataFrame(rows)
tt.to_csv(v.OUT / "trend_tests.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 80)
print(tt.to_string(index=False))

# --- provider-specific scaffolding changes: D1 rate 21 days before / after ------------------------------------
ep = pd.read_parquet(v.OUT / "episodes.parquet", columns=["agent_id", "start"])
t = pd.read_parquet(v.OUT / "turn_actions.parquet", columns=["session_id", "agent_id", "created_at"])
t["ts"] = pd.to_datetime(t.created_at, format="ISO8601")
t = t.sort_values(["session_id", "ts"])
t["dt"] = np.where(t.session_id == t.session_id.shift(-1), (t.ts.shift(-1) - t.ts).dt.total_seconds().clip(0, v.GAP_CAP_S), 0.0)
rel = v.release_table().set_index("id")
t["family"] = t.agent_id.map(rel.family); ep["family"] = ep.agent_id.map(rel.family)
CH = [("2025-07-10", "Gemini", "extra reminder to get pixel coordinates"),
      ("2026-02-20", "Gemini", "fix for Gemini 3 Pro stuck sessions; 100-turn cap for all"),
      ("2026-03-26", "Claude", "fixed empty API responses (agents were getting stuck)"),
      ("2026-06-03", "Claude", "parallel tool use disabled"),
      ("2026-09-04", "OpenAI", "failed-screenshot turns replayed instead of stuck sessions (and 09-08 fix)"),
      ("2026-10-01", "ALL", "bash tool rewritten so commands cannot hang")]
out = []
for day, fam, what in CH:
    d0 = pd.Timestamp(day)
    for grp, mask_t, mask_e in [("touched", (t.family == fam) | (fam == "ALL"), (ep.family == fam) | (fam == "ALL")),
                                ("others", (t.family != fam) & (fam != "ALL"), (ep.family != fam) & (fam != "ALL"))]:
        for side, a, b in [("before", d0 - pd.Timedelta(days=21), d0), ("after", d0, d0 + pd.Timedelta(days=21))]:
            h = t[mask_t & (t.ts >= a) & (t.ts < b)].dt.sum() / 3600
            n = int((mask_e & (ep.start >= a) & (ep.start < b)).sum())
            out.append(dict(change=day, provider=fam, what=what, group=grp, side=side, active_h=round(h, 1), d1_episodes=n,
                            d1_per_hour=round(n / h, 3) if h > 0 else None))
pc = pd.DataFrame(out)
pc.to_csv(v.OUT / "provider_changes.csv", index=False)
print(pc.pivot_table(index=["change", "provider", "group"], columns="side", values=["active_h", "d1_episodes", "d1_per_hour"]).to_string())
print(el[["name", "release", "active_h", "work_actions", "bash_share_of_work", "d1_episodes", "d1_per_hour", "d1_per_1000_work",
          "stuck_share", "median_recover_s", "unrecovered_share", "d2_per_hour"]].round(3).to_string(index=False))
