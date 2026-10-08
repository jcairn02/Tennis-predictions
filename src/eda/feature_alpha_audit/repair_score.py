"""Score the frozen shortlist after rebuilding dated-only histories and match format.

This is an exploratory repair validation, not a new holdout. Constants and model
definitions were selected on these historical outcomes. Rebuilding the history
universe changes more than timing, so cached-original comparisons do not isolate
a chronology effect. No original study outputs are overwritten.

Run after repair_features.py:
    ./python.sh src/eda/feature_alpha_audit/repair_score.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

for _name in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.feature_alpha_audit import elo_retest as E
from src.eda.feature_alpha_audit import profile_retest as P

OUT = ROOT / "data/studies/feature_alpha_audit/repairs"
FEATURES = OUT / "repair_features.parquet"
PROFILE_CONTEXT = [E.SR] + E.CONTEXT
PROFILE_MODELS = {
    "profile_ridge": (P.PROFILE, True, False),
    "profile_fixed_market": (P.PROFILE, True, True),
    "context": (PROFILE_CONTEXT, True, False),
    "profile_context": (P.PROFILE + PROFILE_CONTEXT, True, False),
}
WINDOWS = {"post_tuning_2019_2026": (2019, 2026), "recent_2022_2026": (2022, 2026)}
META = ["match_id", "tour", "year", "evaluation", "a_won", "group", "tournament_date"]


def json_safe(value):
    """Write strict JSON, including absent intervals and numpy-valued counters."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_safe(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    return value


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(json_safe(value), indent=2, allow_nan=False), encoding="utf-8")


def load_frame(path: Path = FEATURES) -> pd.DataFrame:
    f = pd.read_parquet(path)
    if f.match_id.duplicated().any():
        raise ValueError("Repaired features must have unique match_id")
    required = META + ["p_elo", "p_mkt"] + P.PROFILE + PROFILE_CONTEXT + [E.ADJ]
    missing = sorted(set(required) - set(f))
    if missing:
        raise ValueError(f"Missing rebuilt inputs: {missing}")
    f["tournament_date"] = pd.to_datetime(f.tournament_date)
    if f.tournament_date.isna().any():
        raise ValueError("Repaired features must carry provider-supported match days")
    if not f.year.eq(f.tournament_date.dt.year).all():
        raise ValueError("Fold year must use the repaired match day")
    odds = pd.read_parquet(P.PD / "stage1_odds.parquet", columns=["match_id", "p_avg_a", "p_ps_a"])
    for col in ("p_avg_a", "p_ps_a"):
        if col in f:
            f = f.drop(columns=col)
    f = f.merge(odds, on="match_id", how="left", validate="one_to_one")
    f["elo_logit"] = logit(f.p_elo.clip(1e-12, 1 - 1e-12))
    return f.sort_values(["tour", "year", "tournament_date", "match_id"], kind="stable").reset_index(drop=True)


def common_cohort(frame: pd.DataFrame, columns: list[str], tour: str,
                  min_year: int = 2010) -> tuple[pd.DataFrame, list[dict]]:
    """All models in a family share complete training and target rows."""
    eligible = frame.tour.eq(tour) & frame.year.ge(min_year)
    if "status" in frame:
        eligible &= frame.status.isin(["completed", "retired"])
    complete = np.isfinite(frame[columns].to_numpy(dtype=float)).all(axis=1)
    keep = eligible & complete
    coverage = []
    for name, (start, stop) in WINDOWS.items():
        target = eligible & frame.evaluation & frame.year.between(start, stop)
        coverage.append({"tour": tour, "window": name, "eligible": int(target.sum()),
                         "common_rows": int((target & complete).sum()),
                         "missing_required_inputs": int((target & ~complete).sum())})
    return frame.loc[keep].copy().reset_index(drop=True), coverage


def comparison_rows(frame: pd.DataFrame, predictions: dict[str, np.ndarray],
                    pairs: list[tuple[str, str]], **labels) -> list[dict]:
    """Every comparison is a paired loss difference on exactly the same rows."""
    y = frame.a_won.to_numpy(dtype=float)
    losses = {name: E.loss(y, values) for name, values in predictions.items()}
    days = (frame.tournament_date.to_numpy(dtype="datetime64[D]") - np.datetime64("2010-01-04")).astype(int)
    rows = []
    for model, baseline in dict.fromkeys(pairs):
        delta = losses[baseline] - losses[model]
        for window, (start, stop) in WINDOWS.items():
            keep = frame.year.between(start, stop).to_numpy() & frame.evaluation.to_numpy(dtype=bool) & np.isfinite(delta)
            if not keep.any():
                continue
            primary = P.clustered_interval(delta[keep], days[keep] // 28)
            week = P.clustered_interval(delta[keep], days[keep] // 7)
            rows.append({**labels, "model": model, "comparator": baseline, "window": window,
                         "n": int(keep.sum()), **primary,
                         **{f"week_{k}": v for k, v in week.items()},
                         "model_ll": float(losses[model][keep].mean()),
                         "comparator_ll": float(losses[baseline][keep].mean()),
                         "first_match_day": str(frame.tournament_date[keep].min().date()),
                         "last_match_day": str(frame.tournament_date[keep].max().date()),
                         "positive_clustered_interval": bool(primary["gain_mll"] > 0 and primary["lo_mll"] > 0)})
    return rows


def ladder_specs(columns) -> tuple[dict, dict, list[str]]:
    """Frozen sequential ladder; never substitute archived values for missing rebuilds."""
    available = set(columns)
    specs = {"elo_calibrated": ["elo_logit"]}
    references = {"elo_calibrated": "elo_raw"}
    current, inputs, omitted = "elo_calibrated", ["elo_logit"], []
    for suffix, block in (("sr", [E.SR]), ("adjperf", [E.ADJ]), ("ios_short", [E.IOS]),
                          ("games", [E.GAMES]), ("context", E.CONTEXT)):
        missing = [col for col in block if col not in available]
        if missing:
            if suffix not in ("ios_short", "games"):
                raise ValueError(f"Missing required ladder block {suffix}: {missing}")
            omitted.extend(missing)
            continue
        name = ("elo" if current == "elo_calibrated" else current) + "_" + suffix
        inputs = inputs + block
        specs[name], references[name], current = inputs.copy(), current, name
    return specs, references, omitted


def score_profile(frame: pd.DataFrame, out: Path) -> tuple[pd.DataFrame, dict]:
    needed = P.PROFILE + PROFILE_CONTEXT + ["p_avg_a", "p_ps_a"]
    g, coverage = common_cohort(frame, needed, "atp")
    if g.empty:
        raise ValueError("No common repaired ATP profile/market rows")
    save = g[META].copy()
    results, coefficients = [], {}
    for market in ("p_avg_a", "p_ps_a"):
        predictions = {"raw_market": g[market].to_numpy(dtype=float),
                       "calibrated_market": expit(P.market_calibration(g, market))}
        coefficients[market] = {}
        for model, (cols, tune, fixed) in PROFILE_MODELS.items():
            eta, records = P.walk_model(g, cols, market, tune, fixed)
            predictions[model], coefficients[market][model] = expit(eta), records
            print(f"Profile {market}: {model}, {len(g):,} common rows", flush=True)
        pairs = [("calibrated_market", "raw_market")]
        for model in PROFILE_MODELS:
            pairs += [(model, "raw_market"), (model, "calibrated_market")]
        pairs += [("profile_context", "context")]
        results += comparison_rows(g, predictions, pairs, study="profile", tour="atp", market=market,
                                   population="shared_average_pinnacle_profile_context")
        for name, values in predictions.items():
            save[f"{market}|{name}"] = values
    save.to_parquet(out / "profile_predictions.parquet", index=False)
    pd.DataFrame(results).to_csv(out / "profile_results.csv", index=False)
    write_json(out / "profile_coefficients.json", coefficients)
    return save, {"coverage": coverage, "common_rows_including_training": len(g), "results": results}


def score_elo(frame: pd.DataFrame, out: Path) -> tuple[pd.DataFrame, dict]:
    specs, references, omitted = ladder_specs(frame.columns)
    needed = list(dict.fromkeys(c for cols in specs.values() for c in cols))
    results, coverage, saves, coefficients = [], [], [], []
    for tour in ("atp", "wta"):
        g, cv = common_cohort(frame, needed, tour, min_year=2013)
        coverage += cv
        if g.empty:
            continue
        predictions = {"elo_raw": g.p_elo.to_numpy(dtype=float)}
        for name, cols in specs.items():
            predictions[name], fitted = E.walk_predictions(g, cols)
            coefficients += [{"tour": tour, "model": name, **r} for r in fitted]
        pairs = []
        for model in specs:
            pairs += [(model, references[model]), (model, "elo_raw")]
            if model != "elo_calibrated":
                pairs.append((model, "elo_calibrated"))
        results += comparison_rows(g, predictions, pairs, study="elo", tour=tour, market="none", population="all_common")
        for market in ("p_avg_a", "p_ps_a"):
            has = np.isfinite(g[market].to_numpy(dtype=float))
            gm = g.loc[has].copy().reset_index(drop=True)
            if gm.empty:
                continue
            pm = {name: values[has] for name, values in predictions.items()}
            pm["raw_market"] = gm[market].to_numpy(dtype=float)
            pm["calibrated_market"] = expit(P.market_calibration(gm, market))
            market_pairs = [(name, base) for name in specs for base in ("raw_market", "calibrated_market")]
            results += comparison_rows(gm, pm, market_pairs, study="elo", tour=tour, market=market, population="market_common")
        save = g[META + ["p_avg_a", "p_ps_a"]].copy()
        for name, values in predictions.items():
            save[name] = values
        saves.append(save)
        print(f"Elo {tour}: {len(g):,} common rows, {len(specs)} frozen models", flush=True)
    save = pd.concat(saves, ignore_index=True)
    save.to_parquet(out / "elo_predictions.parquet", index=False)
    pd.DataFrame(results).to_csv(out / "elo_results.csv", index=False)
    write_json(out / "elo_coefficients.json", coefficients)
    return save, {"coverage": coverage, "specifications": specs, "references": references,
                  "omitted_unrebuilt_columns": omitted, "results": results}


def compare_cached(rebuilt: pd.DataFrame, cached: pd.DataFrame, pairs: list[tuple[str, str]],
                   study: str, cache_name: str) -> list[dict]:
    """Paired same-ID change; history universe/cohort/model changes are inseparable."""
    if cached.match_id.duplicated().any() or rebuilt.match_id.duplicated().any():
        raise ValueError("Cached comparisons require unique match_id")
    overlap = rebuilt.match_id.isin(cached.match_id)
    g = rebuilt.loc[overlap].copy().reset_index(drop=True)
    old = cached.set_index("match_id").reindex(g.match_id).reset_index()
    if "a_won" in old and not np.array_equal(g.a_won.to_numpy(), old.a_won.to_numpy()):
        raise ValueError("Cached and rebuilt outcomes/orientations do not agree")
    rows = []
    for new_col, old_col in pairs:
        if new_col not in g or old_col not in old:
            continue
        for tour in sorted(g.tour.unique()):
            take = g.tour.eq(tour).to_numpy()
            pred = {"rebuilt": g[new_col].to_numpy(dtype=float)[take],
                    "cached_original": old[old_col].to_numpy(dtype=float)[take]}
            recs = comparison_rows(g.loc[take].reset_index(drop=True), pred, [("rebuilt", "cached_original")],
                                   study=study, tour=tour, feature_model=new_col, cache=cache_name,
                                   interpretation="combined_repair_and_history_universe_change_not_timing_only")
            rows += recs
    return rows


def main(features: Path = FEATURES, out: Path = OUT) -> dict:
    started = time.monotonic()
    out.mkdir(parents=True, exist_ok=True)
    frame = load_frame(features)
    protocol = {
        "status": "exploratory frozen-shortlist repair validation; no untouched holdout",
        "feature_file": str(features), "feature_sha256": hashlib.sha256(features.read_bytes()).hexdigest(),
        "profile_models": PROFILE_MODELS, "profile_tour": "atp",
        "ridge": {"grid": P.GRID, "default": P.DEFAULT_LAMBDA,
                  "selection": "prior two calendar seasons; their own fits precede their validation season"},
        "profile_training": "all prior available years; common rows for all features and both markets",
        "elo_training": "annual expanding from 2013; scoring from 2019; training-only RMS; no intercept",
        "windows": WINDOWS, "interval": "paired four-week provider-match-day cluster t, calendar-week sensitivity",
        "limits": ["Frozen pre-2019 feature constants and shortlist already selected on historical outcomes.",
                   "The dated-only history universe changes opposition, exposure and cohort as well as chronology.",
                   "Provider match days and same-event round order are not verified match-end or quote times.",
                   "Pointwise intervals do not adjust selection or establish independent calendar blocks.",
                   "Published bookmaker rows are not proven executable closing quotes; no returns measured."]}
    provenance_path = features.with_name("repair_features_summary.json")
    if provenance_path.exists():
        build = json.loads(provenance_path.read_text(encoding="utf-8"))
        if build.get("output_sha256") != protocol["feature_sha256"]:
            raise ValueError("Feature file does not match its build summary; wait for the completed rebuild")
        protocol["feature_build"] = build
    protocol["scoring_source_sha256"] = {str(Path(module).resolve().relative_to(ROOT)): hashlib.sha256(Path(module).read_bytes()).hexdigest()
                                           for module in (__file__, P.__file__, E.__file__)}
    write_json(out / "scoring_protocol.json", protocol)
    profile, profile_summary = score_profile(frame, out)
    elo, elo_summary = score_elo(frame, out)
    pd.DataFrame(profile_summary["results"] + elo_summary["results"]).to_csv(out / "repair_results.csv", index=False)
    cached_rows = []
    original = out.parent
    for name, fresh, study, pairlist in (
        ("profile_predictions.parquet", profile, "profile", [(f"{m}|{v}", f"{m}|{v}")
         for m in ("p_avg_a", "p_ps_a") for v in ("profile_ridge", "profile_fixed_market", "calibrated_market")]),
        ("profile_context_predictions.parquet", profile, "profile_context", [(f"{m}|{v}", f"{m}|{v}")
         for m in ("p_avg_a", "p_ps_a") for v in ("context", "profile_context")]),
        ("elo_predictions.parquet", elo, "elo", [(c, c) for c in elo_summary["specifications"]]),
    ):
        path = original / name
        if path.exists():
            cached_rows += compare_cached(fresh, pd.read_parquet(path), pairlist, study, name)
    pd.DataFrame(cached_rows).to_csv(out / "cached_same_match_comparisons.csv", index=False)
    summary = {"protocol": protocol, "profile": profile_summary, "elo": elo_summary,
               "cached_same_match_comparisons": cached_rows, "seconds": time.monotonic() - started}
    write_json(out / "scoring_summary.json", summary)
    print(f"Completed repaired scoring in {summary['seconds']:.1f}s", flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=FEATURES)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    main(args.features, args.out)
