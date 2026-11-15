"""Figure: repetition episodes (D1) against model release date, one panel per denominator.

Three small multiples, one series each (eligible agents): all work actions per active hour, GUI actions only per
1,000 GUI actions, bash actions only per 1,000 bash actions. Log y axis; agents with zero episodes sit on the
bottom rule. Writes out/fig_stuck_vs_release.png and out/fig_stuck_vs_release_data.csv (the table view).
Usage: ./venv/bin/python3 -I data-scouts/stuck-time/scripts/06_figure.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import case_lib as v  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE, INK, INK2, GRID, BLUE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
ag = pd.read_csv(v.OUT / "agent_stuck.csv", parse_dates=["release"])
tt = pd.read_csv(v.OUT / "trend_tests.csv")
el = ag[ag.eligible].copy()
panels = [("d1_per_hour", "All work actions\nepisodes per active hour", el, "H1"),
          ("d1_gui_per_1000", "GUI actions only\nepisodes per 1,000 GUI actions", el[el.gui_actions >= 500], "modality: GUI only"),
          ("d1_bash_per_1000", "Bash commands only\nepisodes per 1,000 bash commands", el[el.bash_actions >= 500], "modality: bash only")]
LABEL = {"d1_per_hour": ["Claude 3.5 Sonnet", "Grok 4", "Gemini 2.5 Pro", "Claude Fable 5.1", "Muse Spark 1.3", "Claude Opus 4.7"],
         "d1_gui_per_1000": ["Claude 3.5 Sonnet", "Grok 4", "Gemini 2.5 Pro"],
         "d1_bash_per_1000": ["Muse Spark 1.3", "Claude Fable 5.1", "Gemini 4 Argon", "DeepSeek-V4-Pro"]}
fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), facecolor=SURFACE)
for ax, (col, title, d, test) in zip(axes, panels):
    d = d.dropna(subset=[col])
    pos = d[d[col] > 0]
    floor = pos[col].min() / 3
    y = d[col].where(d[col] > 0, floor)
    ax.set_facecolor(SURFACE)
    ax.scatter(d.release, y, s=64, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_yscale("log")
    ax.axhline(floor, color=GRID, lw=1, zorder=1)
    ax.text(d.release.min(), floor * 1.12, "zero episodes", color=INK2, fontsize=8, va="bottom")
    for n in LABEL[col]:
        r = d[d.name == n]
        if len(r):
            ax.annotate(n, (r.release.iloc[0], y[r.index[0]]), xytext=(6, -13) if (n, col) == ("Claude Fable 5.1", "d1_per_hour") else (6, 5), textcoords="offset points", fontsize=8, color=INK2)
    t = tt[tt.test == test].iloc[0]
    ax.set_title(f"{title}\nSpearman ρ = {t.rho:+.2f}, p = {t.perm_p:.3f}, {int(t.n_agents)} agents", fontsize=10, color=INK, loc="left")
    ax.grid(True, which="major", color=GRID, lw=0.8, zorder=0)
    ax.tick_params(colors=INK2, labelsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_xlabel("model release date (join date for 2026 models)", fontsize=8, color=INK2)
fig.suptitle("Repetition episodes (5+ identical actions in a row) by model release date: the decline is in GUI actions, not in bash",
             fontsize=11, color=INK, x=0.01, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(v.OUT / "fig_stuck_vs_release.png", dpi=140, facecolor=SURFACE)
el[["name", "family", "release", "release_source", "active_h", "work_actions", "d1_episodes", "d1_per_hour", "d1_gui_per_1000",
    "d1_bash_per_1000"]].sort_values("release").round(4).to_csv(v.OUT / "fig_stuck_vs_release_data.csv", index=False)
print("figure written")
