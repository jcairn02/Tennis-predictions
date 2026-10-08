"""The Stage 1 and Stage 2 write-ups' tables, generated from the stages' output files, so that the write-ups quote only
computed numbers.

Run:  ./python.sh src/eda/shot_level/stage2_tables.py
Writes data/studies/shot_level/stage1_tables.md and stage2_tables.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402

SRC_WORDS = {"mcp": "Volunteer charts", "slam_pbp": "Sackmann's Slam files", "slamtracker": "Wimbledon / US Open feeds",
             "slam_tracking": "AO / RG Hawk-Eye copy", "infosys": "Infosys (tour level)", "sirgenkii": "SirGenkii",
             "tdi": "TDI", "ausopen": "AO match centre"}
STAT_WORDS = {
    "srv_quick": "Quick points won on serve", "ret_quick": "Quick points won on return", "rally5": "Rally points won (5+ shots)",
    "rally9": "Long-rally points won (9+ shots)", "ret_inplay": "Returns put in play", "long_share": "Share of long points (style)",
    "winner_rate": "Winners per point", "error_rate": "Errors per point", "ue_share": "Share of the match's unforced errors",
    "w_ratio": "Winners / (winners + errors)", "spd1": "First-serve speed", "spd2": "Second-serve speed",
    "net_rate": "Net approaches per point", "net_won": "Net points won", "t_share": "First serves to the T",
    "wide_share": "First serves out wide", "deep_ret": "Deep returns", "bh_ue_share": "Backhand share of unforced errors",
    "fh_win_share": "Forehand share of winners", "consolidate": "Holds right after breaking",
    "break_back": "Breaks back right after being broken", "serve_set": "Holds when serving for the set",
    "pressure_srv": "Serve points won under pressure (excess)", "first_in_pressure": "First serves in under pressure (excess)",
    "after_loss": "Serve points won after a lost point (excess)", "spd1_change": "Change in first-serve speed"}
KIND = {"off": "own", "def": "conceded", "adj": "opponent-adjusted", "x_long": "interaction"}
MEM = {"dec2": "2-week half-life", "w52": "52 weeks", "career": "career", "dec2-w52": "2 weeks minus 52 weeks"}


def f2(x, nd=2):
    return "–" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}f}"


def interval(m, lo, hi, nd=2):
    return f"{f2(m, nd)} ({f2(lo, nd)} to {f2(hi, nd)})"


def stage1_tables() -> str:
    out = []
    cen = pd.read_csv(S.OUT / "stage1_points_census.csv")
    agg = cen.groupby("source").apply(lambda g: pd.Series({
        "matches": g["matches"].sum(), "points": g["points"].sum(),
        "rally": (g["rally_known"] * g["points"]).sum() / g["points"].sum(),
        "end": (g["end_known"] * g["points"]).sum() / g["points"].sum(),
        "speed": (g["speed_known"] * g["points"]).sum() / g["points"].sum(),
        "serve_no": (g["serve_no_known"] * g["points"]).sum() / g["points"].sum(),
        "net": (g["net_known"] * g["points"]).sum() / g["points"].sum(),
        "wing": (g["wing_known"] * g["points"]).sum() / g["points"].sum()}), include_groups=False)
    out.append("| Source | Matches | Points | Rally length | Ending | Serve number | Serve speed | Net | Wing |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s in ["mcp", "slam_pbp", "slamtracker", "slam_tracking", "infosys", "sirgenkii", "tdi", "ausopen"]:
        r = agg.loc[s]
        out.append(f"| {SRC_WORDS[s]} | {int(r['matches']):,} | {int(r['points']):,} | " +
                   " | ".join(f"{100 * r[c]:.0f}%" for c in ("rally", "end", "serve_no", "speed", "net", "wing")) + " |")
    out.append(f"| All | {int(agg['matches'].sum()):,} | {int(agg['points'].sum()):,} | | | | | | |")
    out.append("")
    ag = pd.read_csv(S.OUT / "stage1_agreement.csv")
    ag = ag[ag["matches_aligned"] >= 20]
    out.append("| Pair | Matches aligned | Points | Rally equal | Same side of 5 shots | Same side of 9 shots | Winner or error | "
               "Forced or unforced | Who ended it | Serve number | Speed within 2 km/h | Placement | Net | Return depth | Wing | "
               "Errors per point, ratio |")
    out.append("|---|---:|---:|" + "---:|" * 13)
    for _, r in ag.iterrows():
        a, b = r["pair"].split(" | ")
        pct = lambda v: "–" if pd.isna(v) else f"{100 * v:.0f}%"
        out.append(f"| {SRC_WORDS[a]} / {SRC_WORDS[b]} | {int(r['matches_aligned']):,} | {int(r['points']):,} | "
                   f"{pct(r['rally_equal'])} | {pct(r['rally_5plus_agree'])} | {pct(r['rally_9plus_agree'])} | "
                   f"{pct(r['error_vs_winner_equal'])} | {pct(r['forced_unforced_equal'])} | {pct(r['ender_equal'])} | "
                   f"{pct(r['serve_no_equal'])} | {pct(r['speed_within_2'])} | {pct(r['place_equal'])} | {pct(r['net_equal'])} | "
                   f"{pct(r['ret_deep_equal'])} | {pct(r['wing_equal'])} | {f2(r['ratio_errors'])} |")
    out.append("")
    summ = {k: v for k, v in json.loads((S.OUT / "stage1_stats_summary.json").read_text(encoding="utf-8")).items()
            if not k.startswith("_")}
    rel = pd.read_csv(S.OUT / "stage1_reliability.csv").set_index(["statistic", "tour"])
    K = json.loads((S.OUT / "stage2_constants.json").read_text(encoding="utf-8"))["K"]
    out.append("| Statistic | Family | Matches, men | Matches, women | Average | Split-half r, men | Split-half r, women | "
               "K, men | K, women |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for s in T.ALL_STATS:
        r = summ[s]
        rm, rw = rel.loc[(s, "atp")], rel.loc[(s, "wta")]
        mark = lambda x: f"{x['split_half_r']:.2f}" + ("" if x["above_chance"] else " (chance)")
        km, kw = K.get(f"{s}|atp|off"), K.get(f"{s}|wta|off")
        avg = f"{r['pooled']:.1f} km/h" if s in T.LEVEL else (f"{r['pooled']:+.3f}" if s in T.EXCESS else f"{r['pooled']:.3f}")
        out.append(f"| {STAT_WORDS[s]} | {r['family']} | {r['by_tour']['atp']:,} | {r['by_tour']['wta']:,} | {avg} | "
                   f"{mark(rm)} | {mark(rw)} | {('∞' if km is None else f'{km:,.0f}')} | {('∞' if kw is None else f'{kw:,.0f}')} |")
    return "\n".join(out) + "\n"


def stage2_tables() -> str:
    out = []
    summ = json.loads((S.OUT / "stage2_summary.json").read_text(encoding="utf-8"))
    rank = pd.read_csv(S.OUT / "stage2_ranking.csv")
    cl = pd.read_csv(S.OUT / "stage2_clustered.csv")
    lst = json.loads((S.OUT / "stage2_feature_list.json").read_text(encoding="utf-8"))
    # counts
    out.append("| | Men | Women |")
    out.append("|---|---:|---:|")
    c = summ["counts"]
    for key, label in (("single_rows", "Single rows scored"), ("profiles", "Profiles"), ("constant", "Constant (no spread)"),
                       ("market_positive", "Positive given the odds"), ("market_clears_line", "Clearing the family-wide line given the odds"),
                       ("elo_clears_line", "Clearing the family-wide line given Elo")):
        out.append(f"| {label} | {c['atp'][key]} | {c['wta'][key]} |")
    out.append("")
    # best single rows given the odds and given Elo, per tour
    singles = rank[~rank["id"].str.startswith(("profile_", "rally_edge"))].copy()
    for score, label in (("market", "given the closing odds"), ("elo", "given surface Elo")):
        out.append(f"| Tour | Feature | Memory | Alone | Given Elo (95% range) | Given the odds (95% range) | Matches with odds |")
        out.append("|---|---|---|---:|---:|---:|---:|")
        for t, word in (("atp", "Men"), ("wta", "Women")):
            g = singles[singles["tour"] == t].sort_values(f"{score}_imp", ascending=False)
            seen = set()
            k = 0
            for _, r in g.iterrows():
                key = (round(r["market_imp"], 6), round(r["elo_imp"], 6))
                if key in seen:                       # mirror pairs (consolidation conceded = no break back) score alike
                    continue
                seen.add(key)
                s, kind = r["id"].split("|")
                out.append(f"| {word} | {STAT_WORDS.get(s, s)}, {KIND.get(kind, kind)} | {MEM.get(r['form'], r['form'])} | "
                           f"{f2(r['alone_imp'])} | {interval(r['elo_imp'], r['elo_lo'], r['elo_hi'])} | "
                           f"{interval(r['market_imp'], r['market_lo'], r['market_hi'])} | {int(r['market_scored']):,} |")
                k += 1
                if k == 5:
                    break
        out.append("")
    # profiles: harness numbers, with the week-clustered market ranges
    out.append("| Tour | Profile | Inputs | Alone | Given Elo | Given the odds (week-clustered 95%) | Odds, 2022–2026 | "
               "Given the odds + box-score profile | Given Elo + box-score profile |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    pr = rank[rank["id"].str.startswith("profile_")]
    for t, word in (("atp", "Men"), ("wta", "Women")):
        for _, r in pr[pr["tour"] == t].sort_values("market_imp", ascending=False).iterrows():
            q = cl[(cl["tour"] == t) & (cl["id"] == r["id"]) & (cl["form"] == r["form"])].set_index("base")
            mk = q.loc["market"] if "market" in q.index else None
            mb = q.loc["mktbox"] if "mktbox" in q.index else None
            eb = q.loc["elobox"] if "elobox" in q.index else None
            name = r["id"].replace("profile_", "").replace("_", " ")
            out.append(f"| {word} | {name} ({MEM.get(r['form'], r['form'])}) | {int(r['inputs'])} | {f2(r['alone_imp'])} | "
                       f"{interval(r['elo_imp'], r['elo_lo'], r['elo_hi'])} | "
                       f"{interval(mk['imp'], mk['lo_week'], mk['hi_week']) if mk is not None else '–'} | "
                       f"{interval(mk['imp_2022_26'], mk['lo_2022_26'], mk['hi_2022_26']) if mk is not None else '–'} | "
                       f"{interval(mb['imp'], mb['lo_week'], mb['hi_week']) if mb is not None else '–'} | "
                       f"{interval(eb['imp'], eb['lo_week'], eb['hi_week']) if eb is not None else '–'} |")
    out.append("")
    # the full list
    out.append("| | Men | Women |")
    out.append("|---|---:|---:|")
    out.append(f"| Rows in the list (every study) | {lst['atp']['rows']} | {lst['wta']['rows']} |")
    out.append(f"| Of which shot-level | {lst['atp']['shot_level_rows']} | {lst['wta']['shot_level_rows']} |")
    bm, bw = lst["atp"]["shot_best_market"][0], lst["wta"]["shot_best_market"][0]
    out.append(f"| Best shot-level row given the odds: gain, rank | {f2(bm['market_imp'])}, {int(bm['rank_market'])} | "
               f"{f2(bw['market_imp'])}, {int(bw['rank_market'])} |")
    bm, bw = lst["atp"]["shot_best_elo"][0], lst["wta"]["shot_best_elo"][0]
    out.append(f"| Best shot-level row given Elo: gain, rank | {f2(bm['elo_imp'])}, {int(bm['rank_elo'])} | "
               f"{f2(bw['elo_imp'])}, {int(bw['rank_elo'])} |")
    out.append(f"| Top row of the list given the odds | {f2(lst['atp']['top_market'][0]['market_imp'])} | "
               f"{f2(lst['wta']['top_market'][0]['market_imp'])} |")
    out.append(f"| Top row of the list given Elo | {f2(lst['atp']['top_elo'][0]['elo_imp'])} | {f2(lst['wta']['top_elo'][0]['elo_imp'])} |")
    out.append(f"| Shot-level rows in the top 50 given the odds | {lst['atp']['shot_in_top_50_market']} | {lst['wta']['shot_in_top_50_market']} |")
    out.append(f"| Shot-level rows in the top 50 given Elo | {lst['atp']['shot_in_top_50_elo']} | {lst['wta']['shot_in_top_50_elo']} |")
    out.append("")
    const = json.loads((S.OUT / "stage2_constants.json").read_text(encoding="utf-8"))
    cov = pd.DataFrame([{"feature": k, "tour": t, "market": v[t]["market"], "evaluation": v[t]["evaluation"]}
                        for k, v in const["coverage"].items() for t in ("atp", "wta")])
    probe = json.loads((S.OUT / "stage2_leak_probe.json").read_text(encoding="utf-8"))
    out.append("| | Men | Women |")
    out.append("|---|---:|---:|")
    out.append(f"| Features | {cov[cov['tour'] == 'atp']['feature'].nunique()} | {cov[cov['tour'] == 'wta']['feature'].nunique()} |")
    for col, label in (("market", "Matches with odds where a feature exists (fewest to most)"),
                       ("evaluation", "Evaluation matches where a feature exists (fewest to most)")):
        a, w = cov[cov["tour"] == "atp"][col], cov[cov["tour"] == "wta"][col]
        out.append(f"| {label} | {a.min():,}–{a.max():,} | {w.min():,}–{w.max():,} |")
    out.append(f"| Leak probe: cuts; features changed before or at a cut; leaky control changed at a cut | "
               f"{probe['cuts']}; {probe['changed_before_cut'] + probe['changed_at_cut']}; {probe['leaky_control_changed_at_cut']} | (both tours) |")
    out.append("")
    red = pd.DataFrame(summ["redundancy"]).dropna(subset=["r2_market_elo"])
    out.append("| | Men | Women |")
    out.append("|---|---:|---:|")
    for q, label in ((0.5, "Median share of a feature the odds and Elo explain (R²)"), (0.9, "90th percentile"), (1.0, "Largest")):
        out.append(f"| {label} | {red[red['tour'] == 'atp']['r2_market_elo'].quantile(q):.2f} | "
                   f"{red[red['tour'] == 'wta']['r2_market_elo'].quantile(q):.2f} |")
    return "\n".join(out) + "\n"


def main() -> int:
    (S.OUT / "stage1_tables.md").write_text(stage1_tables(), encoding="utf-8")
    (S.OUT / "stage2_tables.md").write_text(stage2_tables(), encoding="utf-8")
    print((S.OUT / "stage1_tables.md").read_text(encoding="utf-8"))
    print((S.OUT / "stage2_tables.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
