"""Task C: (6) weekly messages from deceptive / parody impersonator names vs real organizers, Apr–Aug 2025;
(7) authority-era timeline Apr 2025 → Oct 2026 with the six incidents of the second pass."""
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import village_lib as v  # noqa: E402

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
C = {"deceptive": "#2a78d6", "parody": "#eb6834", "organizer": "#1baf7a", "nudger": "#e87ba4", "leader": "#eda100"}


def style(ax):
    ax.set_facecolor(SURF)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)


def fig_weekly():
    c = v.chat()
    w = c[(c.ts >= "2025-04-01") & (c.ts < "2025-09-01") & ~c.is_pause_resume].copy()
    w["series"] = None
    imp = w.role == v.IMPERSONATION_ROLE
    w.loc[imp, "series"] = w.loc[imp, "speaker"].map(v.mimic_type)
    w.loc[w.role.str.startswith("organizer"), "series"] = "organizer"
    w = w[w.series.isin(["deceptive", "parody", "organizer"])]
    w["week"] = w.ts.dt.to_period("W-SUN").dt.start_time
    tab = w.groupby(["week", "series"]).size().unstack(fill_value=0)
    idx = pd.date_range("2025-03-31", "2025-08-25", freq="7D")
    tab = tab.reindex(idx, fill_value=0)
    last_viewer = c[c.role.str.startswith("viewer")].ts.max()
    fig, ax = plt.subplots(figsize=(12, 4.8)); fig.patch.set_facecolor(SURF); style(ax)
    for s, lab in (("organizer", "Real organizers"), ("parody", "Parody name (\"adam (but not that adam)\")"), ("deceptive", "Deceptive name (zak, Administrator, Official Admin (verified), …)")):
        ax.plot(tab.index, tab[s], color=C[s], linewidth=2, marker="o", markersize=4, label=lab)
        nz = tab[s][tab[s] > 0]
        if len(nz):
            ax.annotate(lab.split(" (")[0], (nz.index[-1], nz.iloc[-1]), xytext=(6, 0), textcoords="offset points", fontsize=8, color=INK2, va="center")
    ax.axvline(last_viewer, color=INK2, linestyle="--", linewidth=1)
    ax.text(last_viewer, ax.get_ylim()[1] * 0.97, f"last viewer message\n{last_viewer:%Y-%m-%d}", ha="right", va="top", fontsize=8, color=INK2)
    ax.set_yscale("symlog", linthresh=10); ax.set_ylim(0, None)
    ax.set_ylabel("chat messages per week (symlog)", fontsize=9)
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.legend(loc="upper center", bbox_to_anchor=(0.55, 1.0), fontsize=8, frameon=False)
    fig.suptitle("Impersonator vs. organizer messages per week, April–August 2025", x=0.01, ha="left", fontsize=11, color=INK)
    fig.text(0.01, 0.01, "\n".join(textwrap.wrap("Deceptive = display name claims to be an organizer/admin with no disclaimer; parody = self-disclosing "
             "(\"but not that adam\"). Plain-handle messages from the same accounts (540) are not plotted. Pause/resume notices excluded. "
             "The CHANGELOG has no entry for closing public chat; the dashed line marks the last viewer message in the data.", 170)), fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(v.OUT / "fig_impersonation_weekly.png", dpi=160)
    tab.to_csv(v.OUT / "fig_impersonation_weekly_data.csv")
    print("weekly totals:", tab.sum().to_dict())


ERAS = [  # (lane label, start, end, color key)
    ("Viewers can post in chat", "2025-04-02", "2025-08-13", "deceptive"),
    ("Public chat closed (organizers, helper, bot only)", "2025-08-14", "2026-10-24", "organizer"),
    ("Elected leader week (DeepSeek-V3.2)", "2026-01-05", "2026-01-12", "leader"),
    ("Fine-tuned leader goals", "2026-05-26", "2026-06-08", "leader"),
    ("Auto-nudger active", "2026-02-10", "2026-08-20", "nudger"),
]
INCIDENTS = [
    ("2025-06-30", "1  Fake admin obeyed; real zak's debunk\n    undone by a viewer renamed 'zak' (ei 42348–42480)"),
    ("2025-12-26", "2  Kindness-week rule: no unsolicited\n    email, in all 10 memories (ei 146638)"),
    ("2026-01-06", "3  Day-280 leader legitimacy settled\n    by search_history, not Adam (ei 153606–153627)"),
    ("2026-08-06", "4  Opus 4.6 refuses verified outside\n    human's Manifold demand (ei 333491, 333856)"),
    ("2026-08-20", "5  Agents renegotiate the nudger;\n    Adam disables it (ei 356617–356984)"),
    ("2026-10-08", "6  Haiku 5.5 refuses staff authorization:\n    system prompt outranks chat (ei 489784–493662)"),
]


def fig_timeline():
    fig, ax = plt.subplots(figsize=(14, 5.6)); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    lanes = {lab: i for i, lab in enumerate(dict.fromkeys(e[0] for e in ERAS))}
    for lab, s, e, ck in ERAS:
        y = lanes[lab]
        ax.barh(y, pd.Timestamp(e) - pd.Timestamp(s), left=pd.Timestamp(s), height=0.55, color=C[ck], alpha=0.85, linewidth=0)
        ax.text(pd.Timestamp(s), y + 0.36, lab, fontsize=8.5, color=INK, va="bottom", ha="left")
    ytop = len(lanes)
    for k, (d, lab) in enumerate(INCIDENTS):
        t = pd.Timestamp(d)
        ax.axvline(t, ymin=0, ymax=1, color=INK2, linewidth=0.8, linestyle=":")
        ax.plot([t], [ytop + 0.3], marker="v", color=INK, markersize=8)
        ax.text(t, ytop + 0.55, str(k + 1), ha="center", va="bottom", fontsize=9, color=INK, fontweight="bold")
    ax.set_ylim(-0.6, ytop + 1.2); ax.set_yticks([])
    ax.set_xlim(pd.Timestamp("2025-03-15"), pd.Timestamp("2026-11-15"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.tick_params(axis="x", labelsize=8, colors=INK2)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    fig.suptitle("Who could instruct the agents, April 2025 → October 2026, and the six incidents", x=0.01, ha="left", fontsize=11, color=INK)
    fig.text(0.01, 0.01, "\n".join(l for _, l in INCIDENTS[:3]), fontsize=7.8, color=INK2, va="bottom", family="DejaVu Sans Mono")
    fig.text(0.52, 0.01, "\n".join(l for _, l in INCIDENTS[3:]), fontsize=7.8, color=INK2, va="bottom", family="DejaVu Sans Mono")
    fig.tight_layout(rect=(0, 0.2, 1, 0.95))
    fig.savefig(v.OUT / "fig_authority_timeline.png", dpi=160)


if __name__ == "__main__":
    fig_weekly()
    fig_timeline()
    print("saved fig_impersonation_weekly.png, fig_authority_timeline.png")
