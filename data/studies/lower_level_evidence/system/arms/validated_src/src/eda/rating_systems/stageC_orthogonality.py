"""Stage C of "rating systems against Elo": is a better base rating still orthogonal to the promising features?

If a new rating is better than Elo only because it carries what the promising features carry, the features add less given
it and the full model gains nothing from the swap. If it is orthogonal to them, the features add as much given it and the
full model keeps the rating's gain. Both readings are tested with the feature-alpha audit's own machinery, imported
unchanged.

Part 1, the ladder (src/eda/feature_alpha_audit/elo_retest.py: walk_predictions, clustered_gain, load_frame). On the
audit's common complete cases (every ladder input present; evaluation-level matches from 2013), annual expanding
logistic fits from 2013 scored from 2019, training-RMS scaling, no intercept, 95% intervals clustered by calendar week.
For each base rating R (surface Elo, Glicko-2 match by match, TrueSkill, Glicko-2 weekly):
    R_calibrated        R's log-odds alone, its slope refitted each season
    R_sr                + the serve and return ratings through the iid model
    R_sr_adjperf        + the 2-week adjperf of total points won
    R_sr_adjperf_ios    + the short-memory IOS points matchup (4 weeks men, 13 weeks women)
    R_sr_adjperf_ios_games  + the games-weighted Elo
    R_full              + sets over 14 days, the first matches on a surface, age and age squared (the audit's full model)
and with Elo and R together as the base (elo+R_calibrated, elo+R_full). Each step against the step before it; each
model against the same step with the Elo base; on the matches with odds, each full model against the raw closing
average (how near the market the enriched forecast gets).

Part 2, the closing line, men (src/eda/feature_alpha_audit/profile_retest.py: load_frame, walk_model, market_calibration,
clustered_interval). On the audit's shared rows (both the average and Pinnacle prices, the 16-input profile and its
controls), the market's log-odds an unpenalised input, the ridge on the others chosen from the two preceding seasons:
    rating_R            R's log-odds given the market (does any rating add to the closing line?)
    profile             the 16-input adjperf / adjdef profile (the audit's profile_ridge, reproduced)
    profile_rating_R    the profile with R as one more input
for R in (Elo, Glicko-2 match by match, TrueSkill), against the raw and calibrated market and against each other.

Part 3, the repaired cohort (src/eda/feature_alpha_audit/repair_score.py; the audit's repairs of 2 Oct 2026): parts 1
and 2 again on the main-tour matches with trusted match dates, every feature rebuilt in match-day order (repaired_part).

Writes, in data/studies/rating_systems/: stageC_ladder_results.csv, stageC_market_results.csv,
stageC_repaired_results.csv, stageC_summary.json.
Run after stageA_ratings.py: ./python.sh src/eda/rating_systems/stageC_orthogonality.py
"""
from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.special import expit, logit  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_alpha_audit import elo_retest as ER  # noqa: E402
from src.eda.feature_alpha_audit import profile_retest as PR  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402

OUT = RC.OUT
RATINGS = OUT / "stageA_ratings.parquet"
LADDER = OUT / "stageC_ladder_results.csv"
MARKET = OUT / "stageC_market_results.csv"
REPAIRED = OUT / "stageC_repaired_results.csv"
SUMMARY = OUT / "stageC_summary.json"
BASES = {"elo": "elo_logit", "glicko_cs": "glicko_cs_logit", "ttt": "ttt_logit", "glicko2m": "glicko2m_logit",
         "trueskill": "trueskill_logit", "glicko2": "glicko2_logit"}
MARKET_RATINGS = ("elo", "glicko_cs", "ttt", "glicko2m", "trueskill")
STEPS = [("calibrated", []), ("sr", [ER.SR]), ("sr_adjperf", [ER.SR, ER.ADJ]), ("sr_adjperf_ios", [ER.SR, ER.ADJ, ER.IOS]),
         ("sr_adjperf_ios_games", [ER.SR, ER.ADJ, ER.IOS, ER.GAMES]),
         ("full", [ER.SR, ER.ADJ, ER.IOS, ER.GAMES] + ER.CONTEXT)]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def rating_logits(match_ids: pd.Series) -> pd.DataFrame:
    names = [b for b in BASES if b != "elo"]
    rt = pd.read_parquet(RATINGS, columns=["match_id"] + [f"p_{s}" for s in names]).set_index("match_id")
    rt = rt.reindex(match_ids)
    out = pd.DataFrame(index=match_ids.index)
    for s in names:
        p = rt[f"p_{s}"].to_numpy(dtype="float64")
        assert np.isfinite(p).all(), s
        out[f"{s}_logit"] = logit(np.clip(p, 1e-12, 1 - 1e-12))
    return out


# ------------------------------------------------------------------------------------------------
# Part 1: the ladder

def ladder_specs() -> tuple[dict, dict]:
    specs, refs = {}, {}
    for base, col in BASES.items():
        prev = None
        for step, cols in STEPS:
            name = f"{base}_{step}"
            specs[name] = [col] + cols
            refs[name] = [f"{base}_{prev}"] if prev else ["elo_raw"]
            if base != "elo":
                refs[name].append(f"elo_{step}")
            prev = step
    for base, col in BASES.items():
        if base == "elo":
            continue
        for step in ("calibrated", "full"):
            name = f"elo+{base}_{step}"
            specs[name] = ["elo_logit", col] + dict(STEPS)[step]
            refs[name] = [f"elo_{step}", f"{base}_{step}"]
    for name in list(specs):
        if name.endswith("_full"):
            refs[name] = list(dict.fromkeys(refs[name] + ["elo_calibrated", f"{name.rsplit('_full', 1)[0]}_calibrated"]))
    return specs, refs


def ladder() -> tuple[pd.DataFrame, dict]:
    f, coverage = ER.load_frame()
    f = pd.concat([f, rating_logits(f["match_id"])], axis=1)
    specs, refs = ladder_specs()
    results = []
    for tour in ("atp", "wta"):
        g = f[f["tour"].eq(tour)].reset_index(drop=True)
        y = g["a_won"].to_numpy(dtype=float)
        weeks = g["week"].to_numpy()
        pred = {"elo_raw": g["p_elo"].to_numpy(dtype=float)}
        for name, cols in specs.items():
            pred[name], _ = ER.walk_predictions(g, cols)
        losses = {k: ER.loss(y, v) for k, v in pred.items()}
        losses["market_raw"] = ER.loss(y, g["p_mkt"].to_numpy(dtype=float))
        for since in (2019, 2022):
            for population in ("all_common", "market_common"):
                mask = g["year"].ge(since).to_numpy().copy()
                if population == "market_common":
                    mask &= np.isfinite(g["p_mkt"].to_numpy(dtype=float))
                for name in specs:
                    rr = list(refs[name]) + (["market_raw"] if population == "market_common" and name.endswith("_full") else [])
                    for ref in dict.fromkeys(rr):
                        r = ER.clustered_gain((losses[ref] - losses[name])[mask], weeks[mask])
                        results.append({"tour": tour, "since": since, "population": population, "model": name,
                                        "reference": ref, **r, "model_logloss": float(np.mean(losses[name][mask])),
                                        "reference_logloss": float(np.mean(losses[ref][mask]))})
        log(f"ladder {tour}: {len(g):,} common matches")
    return pd.DataFrame(results), {"coverage": coverage, "specs": specs, "references": refs}


# ------------------------------------------------------------------------------------------------
# Part 2: the closing line, men

def market_part() -> tuple[pd.DataFrame, dict]:
    f, meta = PR.load_frame()
    f = pd.concat([f, rating_logits(f["match_id"])], axis=1)
    elo = pd.read_parquet(RC.C.OUT / "stage4_features.parquet", columns=["match_id", "p_elo"]).set_index("match_id")
    f["elo_logit"] = logit(np.clip(elo.reindex(f["match_id"])["p_elo"].to_numpy(dtype="float64"), 1e-12, 1 - 1e-12))
    needed = PR.PROFILE + PR.CONTROLS + ["p_avg_a", "p_ps_a"]
    main = f[np.isfinite(f[needed]).all(axis=1)].copy().reset_index(drop=True)
    models = {"profile": PR.PROFILE}
    for base in MARKET_RATINGS:
        models[f"rating_{base}"] = [BASES[base]]
        models[f"profile_rating_{base}"] = PR.PROFILE + [BASES[base]]
    comparators = {"profile": ["raw_market", "calibrated_market"]}
    for base in MARKET_RATINGS:
        comparators[f"rating_{base}"] = ["raw_market", "calibrated_market"]
        comparators[f"profile_rating_{base}"] = ["calibrated_market", f"rating_{base}", "profile"]
    y = main["a_won"].to_numpy(dtype=float)
    windows = {"2013-2026": main["year"] >= 2013, "2019-2026": main["year"] >= 2019, "2022-2026": main["year"] >= 2022}
    rows = []
    for market in ("p_avg_a", "p_ps_a"):
        pred = {"raw_market": logit(np.clip(main[market].to_numpy(), 1e-10, 1 - 1e-10)),
                "calibrated_market": PR.market_calibration(main, market)}
        for name, cols in models.items():
            pred[name], _ = PR.walk_model(main, cols, market, True, False)
            log(f"market part {market} {name}")
        for name, comps in comparators.items():
            for comp in comps:
                gain = PR.ll(y, pred[comp]) - PR.ll(y, pred[name])
                for w, mk in windows.items():
                    use = np.asarray(mk & main["evaluation"] & np.isfinite(gain))
                    if not use.any():
                        continue
                    ci = PR.clustered_interval(gain[use], main["week"].to_numpy()[use])
                    rows.append({"market": market, "model": name, "comparator": comp, "window": w, "n": int(use.sum()),
                                 "model_ll": float(PR.ll(y[use], pred[name][use]).mean()),
                                 "comparator_ll": float(PR.ll(y[use], pred[comp][use]).mean()),
                                 "week_gain_mll": ci["gain_mll"], "week_lo_mll": ci["lo_mll"], "week_hi_mll": ci["hi_mll"],
                                 "weeks": ci["clusters"]})
    meta.update({"rows": int(len(main)), "rows_by_year": {int(k): int(v) for k, v in main.groupby("year").size().items()},
                 "models": models, "comparators": comparators})
    return pd.DataFrame(rows), meta


# ------------------------------------------------------------------------------------------------
# Part 3: the repaired cohort (the feature-alpha audit's repairs of 2 Oct 2026)

def repaired_part() -> tuple[pd.DataFrame, dict]:
    """The audit's repaired shortlist (src/eda/feature_alpha_audit/repair_score.py: load_frame, common_cohort,
    comparison_rows): main-tour matches with trusted match dates only, every feature rebuilt in match-day order. The
    same ladder with each base, and (men) the profile against both closing prices with each rating as an input.

    The bases: the repairs' own rebuilt Elo (from dated main-tour history only: a reference, as it sees far less
    history than the others), Stage 1's surface Elo, and this study's ratings, both from the full 2010-2026 history
    under the event-start time rule. For filtering ratings that rule passes no result between players (a rating moves
    only with the player's own matches), so it cannot carry the overlapping-event leak the repairs removed; TrueSkill
    Through Time's smoothing can (stageC_summary.json, "repaired", "note")."""
    from src.eda.feature_alpha_audit import repair_score as RS
    f = RS.load_frame()
    f = pd.concat([f, rating_logits(f["match_id"])], axis=1)
    s1 = pd.read_parquet(RC.C.OUT / "stage1_baselines.parquet", columns=["match_id", "p_elo_surf_ret"]).set_index("match_id")
    f["elo_s1_logit"] = logit(np.clip(s1.reindex(f["match_id"])["p_elo_surf_ret"].to_numpy(dtype="float64"), 1e-12, 1 - 1e-12))
    bases = {"elo_repaired": "elo_logit", "elo": "elo_s1_logit", **{b: c for b, c in BASES.items() if b not in ("elo", "glicko2")}}
    steps = [("calibrated", []), ("sr", [ER.SR]), ("sr_adjperf", [ER.SR, ER.ADJ]), ("sr_adjperf_ios", [ER.SR, ER.ADJ, ER.IOS]),
             ("sr_adjperf_ios_games", [ER.SR, ER.ADJ, ER.IOS, ER.GAMES]),
             ("full", [ER.SR, ER.ADJ, ER.IOS, ER.GAMES] + ER.CONTEXT)]
    specs, pairs = {}, []
    for b, col in bases.items():
        prev = None
        for st, cols in steps:
            name = f"{b}_{st}"
            specs[name] = [col] + cols
            pairs.append((name, f"{b}_{prev}" if prev else "elo_s1_raw"))
            if b != "elo":
                pairs.append((name, f"elo_{st}"))
            prev = st
        if b not in ("elo", "elo_repaired"):
            specs[f"elo+{b}_full"] = ["elo_s1_logit", col] + steps[-1][1]
            pairs += [(f"elo+{b}_full", "elo_full"), (f"elo+{b}_full", f"{b}_full")]
    needed = list(dict.fromkeys(c for cols in specs.values() for c in cols))
    rows, coverage = [], []
    for tour in ("atp", "wta"):
        g, cv = RS.common_cohort(f, needed, tour, min_year=2013)
        coverage += cv
        pred = {"elo_s1_raw": expit(g["elo_s1_logit"].to_numpy(dtype=float))}
        for name, cols in specs.items():
            pred[name], _ = ER.walk_predictions(g, cols)
        rows += RS.comparison_rows(g, pred, pairs, study="ladder", tour=tour, market="none", population="all_common")
        log(f"repaired ladder {tour}: {len(g):,} common rows")
    # the men's profile against both closing prices, with each rating as an input
    profile_needed = PR.PROFILE + RS.PROFILE_CONTEXT + ["p_avg_a", "p_ps_a"] + [c for b, c in bases.items() if b != "elo_repaired"]
    g, cv = RS.common_cohort(f, profile_needed, "atp")
    coverage += [{**c, "family": "profile"} for c in cv]
    models = {"profile": PR.PROFILE}
    for b in MARKET_RATINGS:
        models[f"rating_{b}"] = [bases[b]]
        models[f"profile_rating_{b}"] = PR.PROFILE + [bases[b]]
    for market in ("p_avg_a", "p_ps_a"):
        pred = {"raw_market": g[market].to_numpy(dtype=float), "calibrated_market": expit(PR.market_calibration(g, market))}
        for name, cols in models.items():
            eta, _ = PR.walk_model(g, cols, market, True, False)
            pred[name] = expit(eta)
        pairs_m = [("profile", "calibrated_market")]
        for b in MARKET_RATINGS:
            pairs_m += [(f"rating_{b}", "calibrated_market"), (f"profile_rating_{b}", "profile"),
                        (f"profile_rating_{b}", f"rating_{b}")]
        rows += RS.comparison_rows(g, pred, pairs_m, study="market", tour="atp", market=market,
                                   population="shared_average_pinnacle")
        log(f"repaired market part {market}: {len(g):,} rows")
    meta = {"source": "src/eda/feature_alpha_audit/repair_score.py (load_frame, common_cohort, comparison_rows)",
            "frame": str(RS.FEATURES.relative_to(ROOT)), "rows": int(len(f)), "coverage": coverage, "specs": specs,
            "windows": RS.WINDOWS,
            "intervals": "lo_mll / hi_mll: four-week calendar blocks of the match day; week_*: calendar weeks",
            "note": "Stage 1's Elo and this study's ratings come from the full 2010-2026 history under the event-start "
                    "time rule. A filtering rating (Elo, Glicko, TrueSkill, the correlated-surface ratings) moves only "
                    "with the player's own matches, so an overlapping event's later rounds cannot reach another "
                    "player's rating; TrueSkill Through Time re-scores opponents and can carry them across (small, "
                    "not measured here)."}
    return pd.DataFrame(rows), meta


def main() -> int:
    lad, lmeta = ladder()
    lad.to_csv(LADDER, index=False)
    log(f"wrote {LADDER.name} ({len(lad)} rows)")
    mk, mmeta = market_part()
    mk.to_csv(MARKET, index=False)
    log(f"wrote {MARKET.name} ({len(mk)} rows)")
    rep, rmeta = repaired_part()
    rep.to_csv(REPAIRED, index=False)
    log(f"wrote {REPAIRED.name} ({len(rep)} rows)")
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "ladder": {**lmeta, "train_from": 2013, "score_from": 2019,
                          "interval": "paired calendar-week cluster-robust t (elo_retest.clustered_gain)"},
               "market": {**{k: v for k, v in mmeta.items() if k != "known_limitations"},
                          "known_limitations_from_the_audit": mmeta.get("known_limitations"),
                          "ridge_grid": list(PR.GRID), "interval": "calendar-week cluster-robust t (profile_retest.clustered_interval)"},
               "repaired": rmeta, "shared_code": RC.dependency_hashes(), "seconds": round(time.time() - T0, 1)}
    SUMMARY.write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    show = lad[(lad["since"] == 2022) & lad["population"].eq("all_common")]
    print(show[["tour", "model", "reference", "n", "gain_mll", "lo_mll", "hi_mll"]].to_string(index=False))
    show = mk[mk["window"].eq("2019-2026")]
    print(show[["market", "model", "comparator", "n", "week_gain_mll", "week_lo_mll", "week_hi_mll"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
