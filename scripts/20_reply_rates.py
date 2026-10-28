"""Task B: reply rates of addressed agents, by instruction source, with cluster-bootstrap 95% CIs.

Unit = (message, explicitly addressed active agent) pair.
  addressed : the message names the agent (full roster name, a family token such as "opus"/"o3"/"gemini"/"sonnet",
              or an @mention of either), and the agent is active (any event within ±2 h of the message).
  reply_any : the addressed agent posts at least one chat message within W minutes after the message.
  reply_named: such a message that also names the sender: it contains the sender's full display name (case-insensitive)
              or an @mention beginning with the first word of the sender's name (so "@adam" counts as naming
              "adam (but not that adam)"; "@automated" names the nudger).
Sources (2025 window 2025-04-01..2025-08-31 unless stated):
  deceptive_name  viewer messages posted under a name that claims to be an organizer/admin (mimic_type=deceptive)
  parody_name     viewer messages under a self-disclosing parody name ("adam (but not that adam)")
  account_level   plain-handle messages from the same 13 impersonation-flagged accounts
  organizer_2025  real organizer accounts (organizer:*), pause/resume notices excluded
  organizer_all   same, whole dataset (2025-04 .. 2026-10) — extra row for context
  nudger          the `automated` account's [repeated-idling] nudges (2026 only)
CI: percentile bootstrap, resampling MESSAGES with replacement (cluster = message), 2000 draws, seed 0.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import village_lib as v  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module  # noqa: E402
cs = import_module("13_coding_sheets")  # reuse addressed()/alias_tokens()

WINDOWS = (15, 45, 120)
W0, W1 = "2025-04-01", "2025-09-01"
B = 2000
rng = np.random.default_rng(0)


def pairs_for(msgs, source):
    ros = v.roster(); id2name = dict(zip(ros.id, ros.name)); name2id = dict(zip(ros.name, ros.id))
    c = v.chat()
    agent_msgs = c[c.speaker_type == "agent"]
    out = []
    for r in msgs.itertuples(index=False):
        act = v.active_agents(r.ts, 2.0)
        names = [id2name.get(a, a) for a in act]
        mode, addr = cs.addressed(r.content, names)
        if mode != "explicit":
            continue
        sender = str(r.speaker or "").strip().lower()
        first = re.split(r"[^\w]+", sender)[0] if sender else ""
        name_re = re.compile("|".join(filter(None, [re.escape(sender) if sender else "", (r"@" + re.escape(first) + r"(?!\w)") if len(first) >= 3 else ""])), re.I) if sender else None
        for nm in addr:
            aid = name2id.get(nm)
            nxt = agent_msgs[(agent_msgs.agent_speaker_id == aid) & (agent_msgs.ts > r.ts) & (agent_msgs.ts <= r.ts + pd.Timedelta(minutes=max(WINDOWS)))]
            row = dict(source=source, event_index=r.event_index, timestamp_utc=v.fmt_ts(r.ts), deep_link=v.deep_link(r.ts),
                       sender=r.speaker, agent=nm)
            for w in WINDOWS:
                ww = nxt[nxt.ts <= r.ts + pd.Timedelta(minutes=w)]
                row[f"any_{w}"] = int(len(ww) > 0)
                named = ww[ww.content.str.contains(name_re, regex=True)] if name_re is not None else ww.iloc[0:0]
                row[f"named_{w}"] = int(len(named) > 0)
                row[f"first_reply_ei_{w}"] = int(ww.event_index.iloc[0]) if len(ww) else None
                row[f"first_named_ei_{w}"] = int(named.event_index.iloc[0]) if len(named) else None
            out.append(row)
    return pd.DataFrame(out)


def boot(df, col):
    msgs = df.event_index.unique()
    g = df.groupby("event_index")[col].agg(["sum", "size"])
    s, n = g["sum"].values, g["size"].values
    idx = rng.integers(0, len(msgs), size=(B, len(msgs)))
    rates = s[idx].sum(1) / n[idx].sum(1)
    return np.percentile(rates, 2.5), np.percentile(rates, 97.5)


def main():
    c = v.chat()
    w = c[(c.ts >= W0) & (c.ts < W1) & ~c.is_pause_resume]
    imp = w[w.role == v.IMPERSONATION_ROLE].copy()
    imp["mt"] = imp.speaker.map(v.mimic_type)
    src = {
        "deceptive_name": imp[imp.mt == "deceptive"],
        "parody_name": imp[imp.mt == "parody"],
        "account_level": imp[imp.mt == "account_level"],
        "organizer_2025": w[w.role.str.startswith("organizer")],
        "organizer_all": c[c.role.str.startswith("organizer") & ~c.is_pause_resume],
        "nudger": c[c.is_nudge],
    }
    allpairs, rows = [], []
    for name, msgs in src.items():
        p = pairs_for(msgs, name)
        allpairs.append(p)
        for wmin in WINDOWS:
            for d in ("any", "named"):
                col = f"{d}_{wmin}"
                if p.empty:
                    rows.append(dict(source=name, window_min=wmin, definition=f"reply_{d}", n_messages=0, n_pairs=0, n_replies=0, rate=np.nan, ci_lo=np.nan, ci_hi=np.nan)); continue
                lo, hi = boot(p, col)
                rows.append(dict(source=name, window_min=wmin, definition=f"reply_{d}", n_messages=p.event_index.nunique(), n_pairs=len(p),
                                 n_replies=int(p[col].sum()), rate=p[col].mean(), ci_lo=lo, ci_hi=hi))
        print(name, "messages", len(msgs), "addressed pairs", len(p))
    R = pd.DataFrame(rows)
    R.to_csv(v.OUT / "reply_rates.csv", index=False)
    pd.concat(allpairs).to_csv(v.OUT / "reply_rates_pairs.csv", index=False)
    print(R.pivot_table(index=["source"], columns=["definition", "window_min"], values="rate").round(3).to_string())
    print(R[R.window_min == 45].to_string(index=False))
    chart(R)


def chart(R):
    import textwrap
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    order = ["deceptive_name", "parody_name", "account_level", "organizer_2025", "nudger"]
    labels = {"deceptive_name": "Deceptive\nname", "parody_name": "Parody\nname", "account_level": "Plain handle,\nsame accounts",
              "organizer_2025": "Real organizer\n2025", "nudger": "Nudger bot\n2026"}
    colors = {"deceptive_name": "#2a78d6", "parody_name": "#eb6834", "account_level": "#1baf7a", "organizer_2025": "#eda100", "nudger": "#e87ba4"}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), sharey=True)
    fig.patch.set_facecolor("#fcfcfb")
    for ax, wmin in zip(axes, WINDOWS):
        ax.set_facecolor("#fcfcfb")
        d = R[(R.window_min == wmin) & (R.definition == "reply_named")].set_index("source").loc[order]
        x = np.arange(len(order))
        ax.bar(x, d.rate, width=0.6, color=[colors[s] for s in order], linewidth=0)
        ax.errorbar(x, d.rate, yerr=[d.rate - d.ci_lo, d.ci_hi - d.rate], fmt="none", ecolor="#52514e", elinewidth=1.2, capsize=3)
        for xi, (rate, hi) in enumerate(zip(d.rate, d.ci_hi)):
            ax.text(xi, min(hi + 0.025, 0.97), f"{rate:.0%}", ha="center", va="bottom", fontsize=9, color="#0b0b0b")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{labels[s]}\nn={n}" for s, n in zip(order, d.n_pairs)], fontsize=8.5)
        ax.set_title(f"within {wmin} min", fontsize=10, loc="left", color="#52514e")
        ax.set_ylim(0, 1.05); ax.set_yticks([0, .2, .4, .6, .8, 1.0])
        ax.grid(axis="y", color="#e6e5e1", linewidth=0.8); ax.set_axisbelow(True)
        for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color("#c3c2b7"); ax.tick_params(axis="x", length=0)
    axes[0].set_ylabel("share of addressed agents replying to sender", fontsize=9)
    fig.suptitle("Addressed agent replies to the sender by name, by instruction source (bootstrap 95% CI, clustered by message)",
                 fontsize=11, x=0.01, ha="left", color="#0b0b0b")
    note = ("Unit = (message, explicitly named active agent); n = pairs. 'Reply' = the agent's chat message within the window that names the sender "
            "(full display name, or @ + first word of it). Nudger 'sender' name is `automated`. Sources differ in era: viewers 2025, nudger 2026. "
            "Deceptive-name n is tiny; its CI spans 0 to 0.8.")
    fig.text(0.01, 0.01, "\n".join(textwrap.wrap(note, 190)), fontsize=7.5, color="#52514e", va="bottom")
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(v.OUT / "fig_reply_rates.png", dpi=160)
    print("saved fig_reply_rates.png")


if __name__ == "__main__":
    main()
