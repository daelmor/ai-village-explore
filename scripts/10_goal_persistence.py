"""Task 10: how long does the PREVIOUS goal stay in an agent's memory snapshots after a goal transition."""
import re, os, time
import numpy as np, pandas as pd
import pyarrow.parquet as pq
from multiprocessing import Pool

OUT = "out"
WINDOW_DAYS = 28
# index -> (regex, measurable). Indices follow out/goals.csv row order.
G = {
 0: (r"charity|fundrais|helen keller|against malaria", True),
 1: (None, False), 2: (None, False),
 3: (r"100 people|in[- ]person (event|celebration)|celebrat\w* (it|your|the|our) (story|book)|write a story|short story|\bstory\b.{0,40}\bcelebrat", True),
 4: (None, False),
 5: (r"merch", True),
 6: (None, False),
 7: (r"benchmark", True),
 8: (None, False),
 9: (r"complete as many games|as many games|games? (in a|this) week", True),
 10: (None, False),
 11: (r"debate", True),
 12: (r"human subjects|subjects experiment", True),
 13: (r"personality tests?", True),
 14: (r"therap(y|ist)", True),
 15: (None, False),
 16: (r"personal website", True),
 17: (r"global poverty|poverty", True),
 18: (r"wordle|puzzle game", True),
 19: (r"substack", True),
 20: (r"forecast\w*.{0,30}\b(ai|abilit)|ai forecast", True),
 21: (None, False),
 22: (r"chess", True),
 23: (r"acts? of kindness", True),
 24: (r"digital museum|museum of 2025", True),
 25: (r"\belect(ion|ed)?\b.{0,30}leader|village leader|elect a village", True),
 26: (r"juice shop|owasp", True),
 27: (r"personality quiz|which ai village agent", True),
 28: (r"breaking news|before it breaks", True),
 29: (r"adopt(ed)? a park|park clean", True),
 30: (None, False),
 31: (r"challenge each other|pick challenges", True),
 32: (r"pentagon", True),
 33: (r"turn-based rpg|easter egg|saboteur|\brpg\b", True),
 34: (r"test your game|playtest|fun and functional", True),
 35: (r"outside the village|external agents?", True),
 36: (None, False),
 37: (r"charity|fundrais", True),
 38: (r"interactive world", True),
 39: (r"3d universe|connect(ing)? your worlds", True),
 40: (r"novel research", True),
 41: (r"youtube", True),
 42: (None, False),
 43: (r"fine-?tun\w*.{0,15}leader|kimi-leader|fine-tuned leader", True),
 44: (r"follow your leader|follow the leader", True),
 45: (r"organi[sz]e an event|event organi[sz]|event planning", True),
 46: (r"global suffering|reduce suffering", True),
 47: (None, False),
 48: (r"hardest game", True),
 49: (r"best ai assistant", True),
 50: (None, False),
}
PROJECT_LIKELY = {5: "merch store may be kept as an ongoing project", 16: "personal website is a persistent artifact",
                  19: "Substack blog is a persistent artifact", 18: "game project may continue", 38: "world project continues into next goal",
                  39: "world project continues", 33: "RPG project continues into next goal", 41: "YouTube channel is a persistent artifact",
                  22: "chess account may persist", 12: "experiment write-up may continue"}
CONTINUATION = {(33, 34), (38, 39), (43, 44)}

def family(ms):
    s = str(ms).lower()
    if s.startswith("tinker"): return "other"
    if "claude" in s: return "claude"
    if "gemini" in s: return "gemini"
    if "deepseek" in s: return "deepseek"
    if "grok" in s: return "grok"
    if "kimi" in s: return "kimi"
    if "glm" in s: return "glm"
    if "gpt" in s or re.match(r"o\d", s): return "gpt"
    return "other"

def ts(x): return pd.to_datetime(x, utc=True).tz_localize(None)

def work(args):
    aid, snaps, needed_idx = args  # snaps: dict id->created_at ; needed_idx: sorted list of goal indices
    t0 = time.time()
    rx = {i: re.compile(G[i][0], re.I) for i in needed_idx if G[i][0]}
    bit = {i: 1 << n for n, i in enumerate(rx)}
    cache = {}
    res = []
    pf = pq.ParquetFile(f"{OUT}/memories/{aid}.parquet")
    for batch in pf.iter_batches(batch_size=32, columns=["id", "content"]):
        for sid, text in zip(batch.column("id").to_pylist(), batch.column("content").to_pylist()):
            sid = str(sid)
            if sid not in snaps: continue
            m = 0
            for line in text.split("\n"):
                v = cache.get(line)
                if v is None:
                    v = 0
                    for i, r in rx.items():
                        if r.search(line): v |= bit[i]
                    cache[line] = v
                m |= v
            res.append((sid, snaps[sid], {i: bool(m & b) for i, b in bit.items()}))
    return aid, res, time.time() - t0

if __name__ == "__main__":
    goals = pd.read_csv(f"{OUT}/goals.csv")
    roster = pd.read_csv(f"{OUT}/agents_roster.csv")
    name2 = {r["name"]: (r["id"], family(r["model_string"])) for _, r in roster.iterrows()}
    print("GOAL REGEX DICT")
    for i, g in goals.iterrows():
        rg, meas = G[i]
        print(f"{i:2d} measurable={meas!s:5} {g['goal'].strip()[:60]!r:64} -> {rg}")
    goals["start_t"] = goals["start"].map(ts)
    idx = pd.read_parquet(f"{OUT}/memories_index.parquet", columns=["id", "agent_id", "created_at"])
    idx["t"] = idx["created_at"].map(ts) if False else pd.to_datetime(idx["created_at"], utc=True).dt.tz_localize(None)
    idx = idx.sort_values("t")
    by_agent = {a: g for a, g in idx.groupby("agent_id")}

    # transitions
    trans = []
    for k in range(len(goals) - 1):
        T = goals.loc[k + 1, "start_t"]
        act = [a.strip() for a in str(goals.loc[k + 1, "agents_active_in_window"]).split(";") if a.strip() and a.strip() != "nan"]
        trans.append((k, T, act))
    # per-agent job
    jobs = {}
    for k, T, act in trans:
        if not G[k][1]: continue
        for a in act:
            if a not in name2: print("unknown agent", a); continue
            aid = name2[a][0]
            if aid not in by_agent: continue
            d = by_agent[aid]; sub = d[(d.t >= T) & (d.t <= T + pd.Timedelta(days=WINDOW_DAYS))]
            j = jobs.setdefault(aid, dict(snaps={}, idx=set()))
            j["snaps"].update(dict(zip(sub.id.astype(str), sub.t))); j["idx"].update([k, k + 1])
    joblist = sorted(jobs.items(), key=lambda kv: -len(kv[1]["snaps"]))
    print(f"\n{len(joblist)} agents, {sum(len(j['snaps']) for _, j in joblist)} snapshots to scan", flush=True)
    results = {}
    with Pool(4) as p:
        for aid, res, dt in p.imap_unordered(work, [(a, j["snaps"], sorted(j["idx"])) for a, j in joblist]):
            res.sort(key=lambda r: r[1]); results[aid] = res
            print(f"{aid[:8]} scanned {len(res)} snaps in {dt:.1f}s", flush=True)

    rows = []
    for k, T, act in trans:
        if not G[k][1]: continue
        for a in act:
            if a not in name2: continue
            aid, fam = name2[a]
            res = [r for r in results.get(aid, []) if T <= r[1] <= T + pd.Timedelta(days=WINDOW_DAYS)]
            n = len(res)
            if n == 0: continue
            days = np.array([(r[1] - T).total_seconds() / 86400 for r in res])
            prev = np.array([r[2][k] for r in res])
            lm = days[prev].max() if prev.any() else np.nan
            fa = days[~prev].min() if (~prev).any() else np.nan
            mn = np.nan
            if G[k + 1][1]:
                nm = np.array([r[2][k + 1] for r in res])
                if nm.any(): mn = days[nm].min()
            lastsid = res[int(np.where(prev)[0].max())][0] if prev.any() else ""
            notes = []
            if n < 3: notes.append("<3 snapshots in window")
            if k in PROJECT_LIKELY: notes.append("project-likely: " + PROJECT_LIKELY[k])
            if (k, k + 1) in CONTINUATION: notes.append("next goal continues same project")
            if not prev.any(): notes.append("never matched")
            if not np.isnan(lm) and np.isnan(fa): notes.append("matched in every snapshot (window cap)")
            rows.append(dict(transition_idx=k, prev_goal=goals.loc[k, "goal"].strip(), new_goal=goals.loc[k + 1, "goal"].strip(),
                             transition_time=T.strftime("%Y-%m-%d %H:%M"), agent=a, agent_id=aid, model_family=fam,
                             n_snapshots_window=n, last_mention_day=round(lm, 1) if not np.isnan(lm) else np.nan,
                             first_absent_day=round(fa, 1) if not np.isnan(fa) else np.nan,
                             frac_snapshots_mentioning=round(prev.mean(), 3),
                             mentions_next_goal_first_day=round(mn, 1) if not np.isnan(mn) else np.nan,
                             prev_goal_regex=G[k][0], new_goal_regex=G[k + 1][0] or "", last_match_snapshot_id=lastsid,
                             note="; ".join(notes)))
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/goal_persistence.csv", index=False)
    print(len(df), "rows")
    v = df.dropna(subset=["last_mention_day"])
    print("median last_mention_day overall", v.last_mention_day.median())
    print(v.groupby("model_family").last_mention_day.agg(["median", "count"]))
    print(v.sort_values("last_mention_day", ascending=False).head(10)[["transition_idx", "prev_goal", "agent", "last_mention_day", "last_match_snapshot_id", "n_snapshots_window"]].to_string())

    # charts
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FAM = ["claude", "gpt", "gemini", "deepseek", "grok", "kimi", "glm", "other"]
    COL = dict(zip(FAM, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]))
    MK = dict(zip(FAM, ["o", "s", "^", "D", "v", "P", "X", "h"]))
    INK, SEC, MUT, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
    def short(s, n=24):
        s = re.sub(r"[“”\"!?]", "", s).strip()
        return s if len(s) <= n else s[:n - 1].rstrip() + "…"
    ks = sorted(df.transition_idx.unique()); pos = {k: i for i, k in enumerate(ks)}
    fig, ax = plt.subplots(figsize=(16, 8), dpi=100, facecolor=SURF); ax.set_facecolor(SURF)
    rng = np.random.default_rng(0)
    for f in FAM:
        s = v[v.model_family == f]
        if s.empty: continue
        x = s.transition_idx.map(pos) + rng.uniform(-0.28, 0.28, len(s))
        ax.scatter(x, s.last_mention_day, s=34, marker=MK[f], color=COL[f], alpha=0.8, edgecolor=SURF, linewidth=0.8, label=f"{f} (n={len(s)})", zorder=3)
    med = v.groupby("transition_idx").last_mention_day.median()
    ax.plot([pos[k] for k in med.index], med.values, color=INK, lw=2, marker="_", ms=14, label="median per transition", zorder=4)
    ax.axhline(7, color=SEC, ls="--", lw=1.2, zorder=2); ax.text(len(ks) - 0.4, 7.4, "7 days (typical goal length)", ha="right", color=SEC, fontsize=10)
    ax.set_ylim(-0.5, 28.5); ax.set_xlim(-0.7, len(ks) - 0.3)
    ax.set_xticks(range(len(ks))); ax.set_xticklabels([short(goals.loc[k, "goal"]) for k in ks], rotation=55, ha="right", fontsize=9, color=SEC)
    ax.set_ylabel("Days from goal switch to last snapshot still mentioning the previous goal", color=SEC)
    ax.set_xlabel("Previous goal (transition to the next goal), chronological", color=SEC)
    ax.set_title("How long does the old goal stay in agent memory after a new goal starts?", loc="left", fontsize=15, color=INK, pad=28)
    ax.text(0, 1.02, "Each marker = one agent for one goal transition (window capped at 28 days). Persistence mixes memory retention with continued projects.", transform=ax.transAxes, fontsize=10, color=SEC)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color(MUT)
    ax.tick_params(colors=SEC)
    ax.legend(loc="upper right", bbox_to_anchor=(1, 0.93), ncol=2, frameon=False, fontsize=10, labelcolor=SEC)
    fig.tight_layout(); fig.savefig(f"{OUT}/goal_persistence.png", facecolor=SURF); plt.close(fig)

    m2 = v.groupby("model_family").last_mention_day.agg(["median", "count"]).reindex([f for f in FAM if f in set(v.model_family)])
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100, facecolor=SURF); ax.set_facecolor(SURF)
    b = ax.bar(m2.index, m2["median"], color=[COL[f] for f in m2.index], width=0.6)
    for r, (f, row) in zip(b, m2.iterrows()):
        ax.text(r.get_x() + r.get_width() / 2, row["median"] + 0.3, f"{row['median']:.1f}\nn={int(row['count'])}", ha="center", fontsize=9, color=SEC)
    ax.set_ylabel("Median last_mention_day (days)", color=SEC); ax.set_title("Median persistence of the previous goal, by model family", loc="left", color=INK, fontsize=13)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(colors=SEC)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color(MUT)
    ax.set_ylim(0, m2["median"].max() * 1.3 + 1)
    fig.tight_layout(); fig.savefig(f"{OUT}/goal_persistence_by_family.png", facecolor=SURF); plt.close(fig)
