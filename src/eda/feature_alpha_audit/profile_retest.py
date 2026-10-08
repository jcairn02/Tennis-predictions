"""Bounded ATP profile reanalysis of already-explored historical samples.

No source feature rebuild: chronology defects in the inherited features remain.
Run with ./python.sh src/eda/feature_alpha_audit/profile_retest.py.
Ridge choice for season Y uses out-of-season losses from Y-2 and Y-1 only.
Every such prediction uses a model and uncentered RMS scale fitted before that
validation season. No intercept/centering: swapping sides complements forecasts.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[_v] = "1"

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/studies/feature_alpha_audit"
UFC = ROOT / "data/studies/ufc_ideas"
PD = ROOT / "data/studies/predictability_diagnostic"
STATS = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved",
         "bp_faced_pg", "brk", "bp_conv", "rpw_first", "rpw_second"]
DEF_STATS = ["ace", "df", "first_in", "bp_faced_pg"]
PROFILE = [f"adjperf_{s}|decayed" for s in STATS] + [f"adjdef_{s}|decayed" for s in DEF_STATS]
CONTROLS = ["rating_matchup|single", "sets_14d|single"]
GRID = (0.0, 0.0001, 0.001, 0.01, 0.1)
DEFAULT_LAMBDA = 0.01
STYLE = {"ace", "df", "first_in"}
BREAK = {"hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv"}
MODELS = {
    "profile_unpenalized": (PROFILE, False, False),
    "profile_ridge": (PROFILE, True, False),
    "profile_fixed_market": (PROFILE, True, True),
    "profile_drop_style": ([c for c in PROFILE if c.split("|", 1)[0].split("_", 1)[1] not in STYLE], True, False),
    "profile_drop_break_games": ([c for c in PROFILE if c.split("|", 1)[0].split("_", 1)[1] not in BREAK], True, False),
    "profile_drop_adjdef": ([c for c in PROFILE if c.startswith("adjperf_")], True, False),
    "ratings_load": (CONTROLS, True, False),
    "profile_ratings_load": (PROFILE + CONTROLS, True, False),
}


def log(message: str) -> None:
    print(message, flush=True)


def ll(y: np.ndarray, eta: np.ndarray) -> np.ndarray:
    # Unscored warmup rows deliberately carry NaN predictions.
    with np.errstate(invalid="ignore"):
        return np.logaddexp(0.0, eta) - y * eta


def rms_scale(x: np.ndarray) -> np.ndarray:
    """Training-only RMS; no centering means exact side antisymmetry."""
    scale = np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2, axis=0))
    return np.where(scale > 1e-12, scale, 1.0)


def fit_logistic(x: np.ndarray, y: np.ndarray, offset: np.ndarray,
                 penalty: np.ndarray) -> np.ndarray:
    """Minimize mean logistic loss + half sum(penalty * beta squared)."""
    b = np.zeros(x.shape[1])
    for _ in range(60):
        eta = offset + x @ b
        p = expit(eta)
        grad = x.T @ (p - y) / len(y) + penalty * b
        hess = (x.T * (p * (1 - p))) @ x / len(y)
        hess.flat[::len(b) + 1] += penalty + 1e-10
        step = np.linalg.solve(hess, grad)
        before = ll(y, eta).mean() + np.dot(penalty, b * b) / 2
        fraction = 1.0
        while fraction > 1e-6:
            candidate = b - fraction * step
            after = ll(y, offset + x @ candidate).mean() + np.dot(penalty, candidate * candidate) / 2
            if after <= before + 1e-13:
                break
            fraction *= 0.5
        b = candidate
        if np.max(np.abs(fraction * step)) < 1e-8:
            return b
    raise RuntimeError("logistic fit did not converge")


def pick_lambda(year: np.ndarray, target_year: int, validation_ll: np.ndarray,
                evaluation: np.ndarray, grid=GRID) -> tuple[int, int, list[int]]:
    """Only prior two calendar seasons can choose the target season's penalty."""
    valid = (year < target_year) & (year >= target_year - 2) & evaluation
    valid &= np.isfinite(validation_ll).all(axis=1)
    if valid.sum() < 300:
        return list(grid).index(DEFAULT_LAMBDA), int(valid.sum()), sorted(set(year[valid].tolist()))
    return int(np.argmin(validation_ll[valid].mean(axis=0))), int(valid.sum()), sorted(set(year[valid].tolist()))


def walk_model(frame: pd.DataFrame, cols: list[str], market: str, tune: bool,
               fixed: bool) -> tuple[np.ndarray, list[dict]]:
    x = frame[cols].to_numpy(dtype=float)
    y = frame.a_won.to_numpy(dtype=float)
    years = frame.year.to_numpy()
    ev = frame.evaluation.to_numpy(dtype=bool)
    base = logit(np.clip(frame[market].to_numpy(), 1e-10, 1 - 1e-10))
    grid = GRID if tune else (0.0,)
    eta_all = np.full((len(frame), len(grid)), np.nan)
    loss_all = np.full_like(eta_all, np.nan)
    chosen_eta = np.full(len(frame), np.nan)
    records = []
    for year in sorted(set(years)):
        tr, te = years < year, years == year
        if tr.sum() < 300:
            continue
        scale = rms_scale(x[tr])
        xt, xv = x[tr] / scale, x[te] / scale
        if fixed:
            zt, zv, off = xt, xv, base[tr]
        else:
            zt = np.column_stack([base[tr], xt])
            zv = np.column_stack([base[te], xv])
            off = np.zeros(tr.sum())
        coef = []
        for j, ridge in enumerate(grid):
            pen = np.full(zt.shape[1], ridge)
            if not fixed:
                pen[0] = 0  # market calibration is never penalized
            b = fit_logistic(zt, y[tr], off, pen)
            eta_all[te, j] = zv @ b + (base[te] if fixed else 0)
            loss_all[te, j] = ll(y[te], eta_all[te, j])
            coef.append(b)
        chosen, nv, validation_years = pick_lambda(years, int(year), loss_all, ev) if tune else (0, 0, [])
        chosen_eta[te] = eta_all[te, chosen]
        b = coef[chosen]
        records.append({"year": int(year), "n_train": int(tr.sum()), "n_test": int(te.sum()),
                        "validation_n": nv, "validation_years": validation_years,
                        "lambda": grid[chosen], "market_slope": 1.0 if fixed else float(b[0]),
                        "feature_coefficients_rms": dict(zip(cols, map(float, b if fixed else b[1:]))),
                        "training_rms": dict(zip(cols, map(float, scale)))})
    return chosen_eta, records


def market_calibration(frame: pd.DataFrame, market: str) -> np.ndarray:
    base = logit(np.clip(frame[market].to_numpy(), 1e-10, 1 - 1e-10))
    years, y = frame.year.to_numpy(), frame.a_won.to_numpy(dtype=float)
    eta = np.full(len(frame), np.nan)
    for year in sorted(set(years)):
        tr, te = years < year, years == year
        if tr.sum() >= 300:
            b = fit_logistic(base[tr, None], y[tr], np.zeros(tr.sum()), np.zeros(1))
            eta[te] = base[te] * b[0]
    return eta


def clustered_interval(values: np.ndarray, clusters: np.ndarray) -> dict:
    """Cluster-robust uncertainty of a match-weighted mean paired improvement."""
    values = np.asarray(values, dtype=float)
    ids, inverse = np.unique(np.asarray(clusters, dtype=str), return_inverse=True)
    n, g = len(values), len(ids)
    mean = float(values.mean())
    influence = np.bincount(inverse, weights=values - mean, minlength=g)
    se = np.sqrt(g / (g - 1) * np.dot(influence, influence)) / n if g > 1 else np.nan
    radius = student_t.ppf(0.975, g - 1) * se if g > 1 else np.nan
    return {"clusters": g, "gain_mll": 1000 * mean,
            "lo_mll": float(1000 * (mean - radius)), "hi_mll": float(1000 * (mean + radius))}


def summarize(frame: pd.DataFrame, predictions: dict, sample: str) -> pd.DataFrame:
    y = frame.a_won.to_numpy(dtype=float)
    masks = {"all_2013_2026": frame.year >= 2013, "post_tuning_2019_2026": frame.year >= 2019,
             "recent_2022_2026": frame.year >= 2022, "recent_2024_2026": frame.year >= 2024,
             "post_tuning_2019_2025": frame.year.between(2019, 2025),
             "recent_2022_2025": frame.year.between(2022, 2025)}
    masks.update({f"year_{year}": frame.year == year for year in range(2013, 2027)})
    masks.update({f"level_{level}": (frame.group == level) & (frame.year >= 2019)
                  for level in sorted(frame.group.unique())})
    rows = []
    for market, p in predictions.items():
        for name, eta in p.items():
            if name == "raw_market":
                continue
            comparators = ["raw_market"] if name == "calibrated_market" else ["raw_market", "calibrated_market"]
            if name == "profile_ratings_load":
                comparators += ["ratings_load"]
            if name == "profile_context":
                comparators += ["context"]
            if name == "profile_ridge":
                comparators += [v for v in ("profile_drop_style", "profile_drop_break_games", "profile_drop_adjdef") if v in p]
            for comparator in comparators:
                gain = ll(y, p[comparator]) - ll(y, eta)
                for window, mask in masks.items():
                    use = np.asarray(mask & frame.evaluation & np.isfinite(gain))
                    if not use.any():
                        continue
                    row = {"sample": sample, "market": market, "model": name, "comparator": comparator,
                           "window": window, "n": int(use.sum()),
                           "model_ll": float(ll(y[use], eta[use]).mean()),
                           "comparator_ll": float(ll(y[use], p[comparator][use]).mean())}
                    for cluster in ("event", "week", "block4week"):
                        row.update({f"{cluster}_{k}": v for k, v in clustered_interval(gain[use], frame[cluster].to_numpy()[use]).items()})
                    rows.append(row)
    return pd.DataFrame(rows)


def load_frame() -> tuple[pd.DataFrame, dict]:
    cols = ["match_id", "tour", "year", "evaluation", "group", "a_won", "p_mkt"] + PROFILE
    f = pd.read_parquet(UFC / "stageD_profile_features.parquet", columns=cols)
    f = f[f.tour.eq("atp")].copy()
    controls = pd.read_parquet(PD / "stage4_features.parquet", columns=["match_id"] + CONTROLS)
    f = f.merge(controls, on="match_id", how="left", validate="one_to_one")
    odds = pd.read_parquet(PD / "stage1_odds.parquet", columns=["match_id", "p_avg_a", "p_ps_a", "td_date"])
    f = f.merge(odds, on="match_id", how="left", validate="one_to_one")
    matches = pd.read_parquet(PD / "stage0_matches.parquet", columns=["match_id", "tournament_id", "tournament_date"])
    f = f.merge(matches, on="match_id", how="left", validate="one_to_one")
    f["event"] = f.tournament_id.astype(str) + "|" + f.tournament_date.dt.strftime("%Y-%m-%d")
    f["week"] = f.tournament_date.dt.to_period("W-SUN").astype(str)
    f["block4week"] = ((f.tournament_date - pd.Timestamp("2010-01-04")).dt.days // 28).astype(str)
    both = np.isfinite(f.p_mkt) & np.isfinite(f.p_avg_a)
    meta = {"atp_pool_rows": len(f), "stored_p_mkt_vs_p_avg_max_abs": float(np.abs(f.loc[both, "p_mkt"] - f.loc[both, "p_avg_a"]).max()),
            "missing_p_mkt_but_avg": int((~np.isfinite(f.p_mkt) & np.isfinite(f.p_avg_a)).sum()),
            "tournament_date_is_not_match_time": True,
            "known_limitations": ["Inherited feature chronology is not repaired in this model-only retest.",
                                  "2010-2018 feature hyperparameters/population constants selected using that interval.",
                                  "2019-2026 outcomes have already informed profile selection; no untouched holdout.",
                                  "Pointwise cluster intervals do not adjust for historical or current model selection.",
                                  "Clustering by tournament-start week does not model all across-week player dependence.",
                                  "Four-week non-overlapping calendar clusters are an uncertainty sensitivity, not an independence guarantee.",
                                  "Archived bookmaker probabilities are not proven timestamped executable closing quotes."]}
    return f.sort_values(["year", "tournament_date", "match_id"]).reset_index(drop=True), meta


def main() -> None:
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    config = {"scope": "ATP selected-historical-sample diagnostic, no untouched holdout",
              "ridge_grid_mean_loss": GRID, "default_lambda_before_300_validation_rows": DEFAULT_LAMBDA,
              "validation": "latest two calendar seasons strictly before each target season; train before each validation season",
              "scaling": "training-only uncentered RMS, no intercept; penalty excludes market slope",
              "cluster_intervals": "paired match-weighted mean, cluster robust SE with G/(G-1), Student t 95%",
              "main_sample": "same matches with both average and Pinnacle odds and all profile/conditioning features",
              "models": {k: {"cols": c, "ridge_selected": r, "market_offset_fixed": o} for k, (c, r, o) in MODELS.items()}}
    (OUT / "profile_plan.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    f, metadata = load_frame()
    original = f[np.isfinite(f[PROFILE + ["p_mkt"]]).all(axis=1)].copy().reset_index(drop=True)
    eta, fit = walk_model(original, PROFILE, "p_mkt", False, False)
    original_preds = {"p_mkt": {"raw_market": logit(original.p_mkt.to_numpy()),
                               "calibrated_market": market_calibration(original, "p_mkt"), "profile_unpenalized": eta}}
    orig_summary = summarize(original, original_preds, "original_average_rows")
    orig_summary.to_csv(OUT / "profile_reproduction.csv", index=False)
    log("Original profile reproduction: " + str(orig_summary.query("model == 'profile_unpenalized' and comparator == 'calibrated_market' and window == 'all_2013_2026'")[["n", "week_gain_mll", "week_lo_mll", "week_hi_mll"]].to_dict("records")))
    needed = PROFILE + CONTROLS + ["p_avg_a", "p_ps_a"]
    main = f[np.isfinite(f[needed]).all(axis=1)].copy().reset_index(drop=True)
    metadata.update({"original_rows": len(original), "common_rows_including_warmup": len(main),
                     "common_rows_by_year": main.groupby("year").size().to_dict()})
    predictions, coefficients, symmetry = {}, {}, {}
    for market in ("p_avg_a", "p_ps_a"):
        predictions[market] = {"raw_market": logit(main[market].to_numpy()), "calibrated_market": market_calibration(main, market)}
        coefficients[market] = {}
        for name, (cols, tune, fixed) in MODELS.items():
            eta, records = walk_model(main, cols, market, tune, fixed)
            predictions[market][name] = eta
            coefficients[market][name] = records
            finite = np.isfinite(eta)
            symmetry[f"{market}/{name}"] = float(np.abs(expit(eta[finite]) + expit(-eta[finite]) - 1).max())
            s = summarize(main, {market: predictions[market]}, "shared_average_pinnacle_rows")
            s.to_csv(OUT / "profile_results.csv", index=False)
            recent = s.query("model == @name and comparator == 'calibrated_market' and window == 'post_tuning_2019_2026'")
            log(f"{time.monotonic() - start:.1f}s {market} {name}: " + str(recent[["n", "week_gain_mll", "week_lo_mll", "week_hi_mll"]].to_dict("records")))
    results = summarize(main, predictions, "shared_average_pinnacle_rows")
    results.to_csv(OUT / "profile_results.csv", index=False)
    save = main[["match_id", "year", "group", "event", "week", "block4week", "evaluation", "a_won"]].copy()
    for market, models in predictions.items():
        for name, eta in models.items():
            save[f"{market}|{name}"] = expit(eta)
    save.to_parquet(OUT / "profile_predictions.parquet", index=False)
    (OUT / "profile_coefficients.json").write_text(json.dumps(coefficients, indent=2), encoding="utf-8")
    metadata["probability_complement_arithmetic_check"] = symmetry
    metadata["feature_side_swap_check"] = "Code audit: stageB_adjperf.Ctx.pool_values returns val_a - val_b; inherited features not rebuilt. Tests independently swap supplied feature/market signs."
    metadata["elapsed_seconds"] = time.monotonic() - start
    (OUT / "profile_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    log(f"Complete in {metadata['elapsed_seconds']:.1f}s")


def chronology_sensitivity(path: Path) -> None:
    """Same-row refits of original versus calendar-week-normalized frozen profiles.

    This is an event-date sensitivity, not a repair of fortnight overlap, actual
    match-time availability, or round-robin observations. No retuned features.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    original, _ = load_frame()
    corrected = pd.read_parquet(path, columns=["match_id"] + PROFILE).set_index("match_id")
    corrected = corrected.reindex(original.match_id).reset_index()
    needed = PROFILE + CONTROLS + ["p_avg_a", "p_ps_a"]
    eligible = np.isfinite(original[needed]).all(axis=1) & np.isfinite(corrected[PROFILE]).all(axis=1)
    original = original[eligible].copy().reset_index(drop=True)
    corrected = corrected[eligible].copy().reset_index(drop=True)
    frames = {"original_dates": original, "calendar_week_dates": original.copy()}
    frames["calendar_week_dates"][PROFILE] = corrected[PROFILE]
    rows, coef = [], {}
    save = original[["match_id", "year", "group", "event", "week", "block4week", "evaluation", "a_won"]].copy()
    for source, frame in frames.items():
        predictions, coef[source] = {}, {}
        for market in ("p_avg_a", "p_ps_a"):
            predictions[market] = {"raw_market": logit(frame[market].to_numpy()),
                                   "calibrated_market": market_calibration(frame, market)}
            coef[source][market] = {}
            for name in ("profile_ridge", "profile_fixed_market", "ratings_load", "profile_ratings_load"):
                cols, tune, fixed = MODELS[name]
                eta, records = walk_model(frame, cols, market, tune, fixed)
                predictions[market][name] = eta
                coef[source][market][name] = records
                log(f"Chronology sensitivity {source} {market} {name}")
            for name, eta in predictions[market].items():
                save[f"{source}|{market}|{name}"] = expit(eta)
        rows.append(summarize(frame, predictions, source))
    pd.concat(rows, ignore_index=True).to_csv(OUT / "profile_chronology_results.csv", index=False)
    save.to_parquet(OUT / "profile_chronology_predictions.parquet", index=False)
    (OUT / "profile_chronology_coefficients.json").write_text(json.dumps(coef, indent=2), encoding="utf-8")


def context_sensitivity() -> None:
    """One follow-up conditioning test requested after inspecting initial results."""
    OUT.mkdir(parents=True, exist_ok=True)
    frame, _ = load_frame()
    extras = ["surface_first|single", "age|single", "age|single|2"]
    context = CONTROLS + extras
    source = pd.read_parquet(PD / "stage4_features.parquet", columns=["match_id"] + extras)
    frame = frame.merge(source, on="match_id", how="left", validate="one_to_one")
    frame = frame[np.isfinite(frame[PROFILE + context + ["p_avg_a", "p_ps_a"]]).all(axis=1)].reset_index(drop=True)
    (OUT / "profile_context_plan.json").write_text(json.dumps({
        "status": "follow-up diagnostic after initial profile retest; not an untouched holdout",
        "context_features": context, "profile": PROFILE,
        "question": "does the profile add beyond market, SR rating, recent sets, surface familiarity, and age quadratic?",
        "ridge_and_scaling": "identical prior-season-only nested selection to main retest"}, indent=2), encoding="utf-8")
    predictions, coef = {}, {}
    save = frame[["match_id", "year", "group", "event", "week", "block4week", "evaluation", "a_won"]].copy()
    for market in ("p_avg_a", "p_ps_a"):
        predictions[market] = {"raw_market": logit(frame[market].to_numpy()),
                               "calibrated_market": market_calibration(frame, market)}
        coef[market] = {}
        for name, cols in (("context", context), ("profile_context", PROFILE + context)):
            eta, records = walk_model(frame, cols, market, True, False)
            predictions[market][name] = eta
            coef[market][name] = records
            log(f"Context sensitivity {market} {name}")
        for name, eta in predictions[market].items():
            save[f"{market}|{name}"] = expit(eta)
    summarize(frame, predictions, "shared_context_rows").to_csv(OUT / "profile_context_results.csv", index=False)
    save.to_parquet(OUT / "profile_context_predictions.parquet", index=False)
    (OUT / "profile_context_coefficients.json").write_text(json.dumps(coef, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chronology-features", type=Path)
    parser.add_argument("--context", action="store_true")
    args = parser.parse_args()
    if args.chronology_features:
        chronology_sensitivity(args.chronology_features)
    elif args.context:
        context_sensitivity()
    else:
        main()
