"""Stage 0, part 2: on how many matches could a shot-level feature be scored, and what gain could that detect?

A pre-match feature exists for a match only when both players have earlier matches carrying the shot-level fields it
is built from. For every family of fields (common.FAMILIES), every group of sources and three memories (career, the
last 52 weeks, the last 13 weeks), this script counts, for each match of the earlier studies' pool, how many earlier
matches each player has under the predictability diagnostic's time rule (earlier events and earlier rounds of the same
event: common.asof_sums), and how many matches have at least k for both players (k = 1, 3, 5, 10, 20).

It then turns each count of scorable matches into the smallest improvement in log loss a test on them would detect
(common.mde_milli), with the inflation of the standard error that the earlier studies' own rundowns show.

Nothing here reads who won: the pool is read without its result column, and the inflation factors are read from the
earlier studies' published intervals.

Run:  ./python.sh src/eda/shot_level/stage0_coverage.py
Reads data/studies/shot_level/stage0_source_matches.parquet (stage0_sources.py).
Writes data/studies/shot_level/:
    stage0_coverage.csv        tour x family x source group x memory x k x subset (x season, x level group): matches
                               eligible and covered, and the detectable gain
    stage0_inflation.csv       the earlier rundowns' market rows: observed standard error against the formula's
    stage0_coverage.json       the headline counts, the detectable gains and the inflation summary
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic.stage3_traits import sums_before  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402

FAM = list(S.FAMILIES)
GROUPS = {
    "all": None,
    "charts": ["mcp"],
    "atp_feeds": ["infosys", "court_vision", "sirgenkii", "tdi"],
    "slams": ["slam_pbp", "slamtracker", "slam_tracking", "ausopen"],
    "wta_api": ["wta_advanced"],
}
WINDOWS = {"career": None, "52w": 364, "13w": 91}
KS = (1, 3, 5, 10, 20)
DAY0 = pd.Timestamp("2010-01-01")
POOL_READ = ["match_id", "tour", "year", "group", "evaluation", "p_mkt"]     # no result column
MAIN_TOUR = ("GS", "FIN", "T1000", "T500", "T250")


def load_pool() -> pd.DataFrame:
    """The earlier studies' pool without its result: match, tour, season, level group, evaluation flag, market."""
    from src.eda.ufc_ideas import common as U
    return pd.read_parquet(U.STAGE4_FEATURES, columns=POOL_READ)


def match_families(src: pd.DataFrame) -> pd.DataFrame:
    """One row per Stage 0 match with a linked source: carries_<group>_<family> (bool), over every group."""
    src = src[src["match_id"].notna()].copy()
    out = {}
    for g, members in GROUPS.items():
        part = src if members is None else src[src["source"].isin(members)]
        agg = part.groupby("match_id")[[f"has_{f}" for f in FAM]].max()
        agg["any"] = agg.any(axis=1)
        for f in FAM + ["any"]:
            col = f"has_{f}" if f != "any" else "any"
            out[f"{g}|{f}"] = agg[col]
    return pd.DataFrame(out).fillna(False).astype(bool)


def history_counts(mp: pd.DataFrame, carries: pd.DataFrame) -> dict[str, np.ndarray]:
    """For each player-match row: the number of the player's earlier matches carrying each (group, family), under the
    time rule, over the career and over the last 52 and 13 weeks."""
    cols = list(carries.columns)
    ind = carries.reindex(mp["match_id"]).fillna(False).to_numpy(dtype="float64")
    tmp = mp[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    names = [f"_c{i}" for i in range(len(cols))]
    for i, n in enumerate(names):
        tmp[n] = ind[:, i]
    career = C.asof_sums(tmp, names).to_numpy()
    out = {"career": career}
    pcode = pd.factorize(mp["player_id"])[0].astype("int64")
    day = ((mp["tournament_date"] - DAY0).dt.days).to_numpy().astype("int64")
    for w, span in WINDOWS.items():
        if span is None:
            continue
        old = sums_before(pcode, day, ind, pcode, day - span)
        out[w] = career - old
    return {"cols": cols, **out}


def covered_table(pool: pd.DataFrame, mp: pd.DataFrame, hist: dict) -> pd.DataFrame:
    """Per pool match, the smaller of its two players' counts for every (window, group|family)."""
    a = mp[mp["side"].eq("A")].set_index("match_id")
    b = mp[mp["side"].eq("B")].set_index("match_id")
    ia = pd.Series(np.flatnonzero(mp["side"].eq("A").to_numpy()), index=a.index)
    ib = pd.Series(np.flatnonzero(mp["side"].eq("B").to_numpy()), index=b.index)
    ra, rb = ia.reindex(pool["match_id"]).to_numpy(), ib.reindex(pool["match_id"]).to_numpy()
    assert not (np.isnan(ra.astype("float64")).any() or np.isnan(rb.astype("float64")).any())
    frames = {}
    for w in WINDOWS:
        h = hist[w]
        frames[w] = np.minimum(h[ra.astype(int)], h[rb.astype(int)])
    return frames


REPAIR_DATES = ROOT / "data/studies/feature_alpha_audit/repairs/repair_date_audit.parquet"


def repaired_rows(mp: pd.DataFrame, carries: pd.DataFrame, pool: pd.DataFrame) -> list[dict]:
    """Coverage under the feature-alpha audit's repaired time rule (docs/studies/feature_alpha_audit/repairs.md): only
    matches with an accepted provider match day count, as history and as targets, and history is ordered by that day
    (earlier days, and earlier rounds of the same event on the same day). Targets: accepted evaluation matches with
    odds. Same families, groups, memories and k as the original rule; no result is read."""
    if not REPAIR_DATES.exists():
        return []
    ra = pd.read_parquet(REPAIR_DATES, columns=["match_id", "accepted", "match_date"])
    ok = ra[ra["accepted"].fillna(False).astype(bool)].set_index("match_id")["match_date"]
    sub = mp[mp["match_id"].isin(ok.index)].copy()
    sub["tournament_date"] = pd.to_datetime(sub["match_id"].map(ok))
    sub = sub.reset_index(drop=True)
    hist = history_counts(sub, carries)
    pl = pool[pool["match_id"].isin(ok.index)].reset_index(drop=True)
    mins = covered_table(pl, sub, hist)
    ev = pl["evaluation"].to_numpy(dtype=bool) & pl["p_mkt"].notna().to_numpy()
    yr, tour = pl["year"].to_numpy(), pl["tour"].to_numpy()
    subsets = {"repaired_market": ev & (yr >= C.EVAL_YEARS[0]), "repaired_market_2019_26": ev & (yr >= 2019),
               "repaired_market_2022_26": ev & (yr >= 2022)}
    out = []
    for w in WINDOWS:
        mn = mins[w]
        for j, col in enumerate(hist["cols"]):
            g, f = col.split("|")
            for k in KS:
                cov = mn[:, j] >= k
                for t in C.TOURS:
                    for sname, sm in subsets.items():
                        m = sm & (tour == t)
                        out.append({"tour": t, "group": g, "family": f, "window": w, "k": k, "subset": sname,
                                    "season": "all", "level_group": "all", "eligible": int(m.sum()),
                                    "covered": int((m & cov).sum())})
    return out


def inflation() -> tuple[pd.DataFrame, dict]:
    """How much wider the earlier rundowns' market intervals are than the formula's, on rows with a positive gain.

    For a feature whose true gain is G nats, the formula's standard error of the mean per-match gain over n matches is
    sqrt(2 G / n). The ratio of the observed standard error ((hi - lo) / 3.92) to sqrt(2 imp / n) is read for every
    market row with imp > 0.1 milli-log-loss in the earlier studies' rankings, and, for the week-clustered intervals,
    from the feature-alpha audit's market rows."""
    rows = []
    srcs = [("predictability_diagnostic stage 4", ROOT / "data/studies/predictability_diagnostic/stage4_ranking.csv")]
    for p in sorted((ROOT / "data/studies/ufc_ideas").glob("stage*_ranking.csv")):
        srcs.append((f"ufc_ideas {p.stem.replace('_ranking', '')}", p))
    for name, p in srcs:
        if not p.exists():
            continue
        r = pd.read_csv(p)
        need = {"market_imp", "market_lo", "market_hi", "market_scored", "inputs"}
        if not need <= set(r.columns):
            continue
        r = r[(r["market_imp"] > 0.1) & (r["market_scored"] > 1000)].copy()
        se_obs = (r["market_hi"] - r["market_lo"]) / 3.92 / 1000
        se_formula = np.sqrt(2 * r["market_imp"] / 1000 / r["market_scored"])
        rows.append(pd.DataFrame({"source": name, "tour": r["tour"], "id": r["id"], "form": r.get("form"),
                                  "inputs": r["inputs"], "n": r["market_scored"], "imp": r["market_imp"],
                                  "se_observed": se_obs * 1000, "se_formula": se_formula * 1000,
                                  "ratio": se_obs / se_formula, "interval": "independent matches"}))
    audit = ROOT / "data/studies/feature_alpha_audit/profile_results.csv"
    if audit.exists():
        # the audit's market comparisons (men's profile models against calibrated average or Pinnacle lines), with
        # intervals clustered by tournament-start calendar week; whole windows only (not single seasons or levels)
        a = pd.read_csv(audit)
        a = a[~a["window"].astype(str).str.match(r"^(year|level)_") & (a["week_gain_mll"] > 0.1) & (a["n"] > 1000)].copy()
        se_obs = (a["week_hi_mll"] - a["week_lo_mll"]) / 3.92 / 1000
        se_formula = np.sqrt(2 * a["week_gain_mll"] / 1000 / a["n"])
        rows.append(pd.DataFrame({"source": "feature_alpha_audit profile_results", "tour": "atp",
                                  "id": a["model"] + " vs " + a["comparator"], "form": a["window"], "inputs": np.nan,
                                  "n": a["n"], "imp": a["week_gain_mll"], "se_observed": se_obs * 1000,
                                  "se_formula": se_formula * 1000, "ratio": se_obs / se_formula,
                                  "interval": "clustered by week"}))
    t = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    summ = {}
    if not t.empty:
        one = t[(t["inputs"] == 1) & t["interval"].eq("independent matches")]
        many = t[(t["inputs"] > 1) & t["interval"].eq("independent matches")]
        clus = t[t["interval"].eq("clustered by week")]
        summ = {"single_input_rows": int(len(one)), "single_input_median_ratio": float(one["ratio"].median()) if len(one) else None,
                "single_input_q75_ratio": float(one["ratio"].quantile(0.75)) if len(one) else None,
                "multi_input_rows": int(len(many)), "multi_input_median_ratio": float(many["ratio"].median()) if len(many) else None,
                "clustered_rows": int(len(clus)), "clustered_median_ratio": float(clus["ratio"].median()) if len(clus) else None}
    return t, summ


def main() -> int:
    S.log("reading the source matches and Stage 0")
    src = pd.read_parquet(S.OUT / "stage0_source_matches.parquet")
    carries = match_families(src)
    S.log(f"  {len(carries)} Stage 0 matches carry some shot-level data")
    mp = C.load_match_players(["match_id", "player_id", "side"])
    pool = load_pool()
    S.log(f"  {len(mp)} player-match rows; pool {len(pool)} matches")
    hist = history_counts(mp, carries)
    cols = hist["cols"]
    S.log(f"  history counts for {len(cols)} (group, family) columns")
    mins = covered_table(pool, mp, hist)

    ev = pool["evaluation"].to_numpy(dtype=bool)
    mkt = ev & pool["p_mkt"].notna().to_numpy()
    yr = pool["year"].to_numpy()
    grp = pool["group"].astype(str).to_numpy()
    tour = pool["tour"].to_numpy()
    in_eval_years = yr >= C.EVAL_YEARS[0]
    subsets = {"evaluation": ev & in_eval_years, "market": mkt & in_eval_years,
               "market_2022_26": mkt & (yr >= 2022)}
    # the WTA's box-score features are scored from 2019 in the earlier studies; shot-level features likewise start late
    p = pool["p_mkt"].to_numpy(dtype="float64")
    out = []
    for w in WINDOWS:
        mn = mins[w]
        for j, col in enumerate(cols):
            g, f = col.split("|")
            for k in KS:
                cov = mn[:, j] >= k
                for t in C.TOURS:
                    tt = tour == t
                    for sname, sm in subsets.items():
                        m = sm & tt
                        out.append({"tour": t, "group": g, "family": f, "window": w, "k": k, "subset": sname,
                                    "season": "all", "level_group": "all", "eligible": int(m.sum()),
                                    "covered": int((m & cov).sum())})
                        if sname == "market" and k in (1, 3, 5) and w in ("career", "52w"):
                            for y in range(C.EVAL_YEARS[0], C.EVAL_YEARS[-1] + 1):
                                my = m & (yr == y)
                                if my.sum():
                                    out.append({"tour": t, "group": g, "family": f, "window": w, "k": k, "subset": sname,
                                                "season": str(y), "level_group": "all", "eligible": int(my.sum()),
                                                "covered": int((my & cov).sum())})
                        if sname == "evaluation" and k in (1, 3, 5) and w in ("career", "52w"):
                            for lg in sorted(set(grp[m])):
                                ml = m & (grp == lg)
                                out.append({"tour": t, "group": g, "family": f, "window": w, "k": k, "subset": sname,
                                            "season": "all", "level_group": lg, "eligible": int(ml.sum()),
                                            "covered": int((ml & cov).sum())})
    S.log("  original rule done; the audit's repaired rule")
    out.extend(repaired_rows(mp, carries, pool))
    cov = pd.DataFrame(out)
    cov["share"] = cov["covered"] / cov["eligible"].where(cov["eligible"] > 0)
    infl_t, infl = inflation()
    one = infl.get("single_input_median_ratio") or 1.0
    many = infl.get("multi_input_median_ratio") or one
    clus = infl.get("clustered_median_ratio") or one
    cov["mde_ideal"] = S.mde_milli(cov["covered"])
    cov["mde_single_input"] = S.mde_milli(cov["covered"], inflation=one)
    cov["mde_profile"] = S.mde_milli(cov["covered"], inflation=many)
    cov["mde_profile_clustered"] = S.mde_milli(cov["covered"], inflation=max(many, clus))
    # a family-wide line over about 40 rows (Bonferroni, two-sided 5%): z = 3.23
    cov["mde_family_wide"] = S.mde_milli(cov["covered"], z_crit=3.23, inflation=one)
    cov.to_csv(S.OUT / "stage0_coverage.csv", index=False)
    if not infl_t.empty:
        infl_t.to_csv(S.OUT / "stage0_inflation.csv", index=False)
    # the market's own spread on the market subset (not needed by the formula; reported for the simulation check)
    v = {t: float(np.nanmean((p * (1 - p))[subsets["market"] & (tour == t)])) for t in C.TOURS}
    head = cov[(cov["season"] == "all") & (cov["level_group"] == "all")]
    summary = {"inflation": infl, "market_v": v, "z": {"single": 1.96, "family_wide_40_rows": 3.23, "power": 0.8416},
               "repaired_rule_source": str(REPAIR_DATES.relative_to(ROOT)) if REPAIR_DATES.exists() else None,
               "stage0_matches_with_shot_data": int(len(carries)),
               "headline": head[head["subset"].isin(["market", "market_2022_26"]) & head["k"].isin([1, 3, 5, 10])
                                & head["family"].isin(FAM + ["any"])].to_dict("records")}
    (S.OUT / "stage0_coverage.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    S.log(f"wrote stage0_coverage.csv ({len(cov)} rows), stage0_inflation.csv, stage0_coverage.json")
    show = head[(head["group"] == "all") & (head["subset"] == "market") & (head["window"] == "52w") & (head["k"] == 3)]
    print(show[["tour", "family", "eligible", "covered", "share", "mde_single_input", "mde_profile"]].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
