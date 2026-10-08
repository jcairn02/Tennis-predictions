"""Bounded new-feature search on repaired history; all tuning uses earlier seasons.

Run after features.py using ./python.sh. This is exploratory reused history.
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[_key] = "1"
import hashlib
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.feature_alpha_audit import repair_score as R
from src.eda.feature_alpha_audit import profile_retest as P
from src.eda.feature_alpha_audit import elo_retest as E

OUT = ROOT / "data/studies/predictive_frontier"
GRID = (0.0001, 0.001, 0.01, 0.1)
STRONG = E.SPECS["elo_sr_adjperf_ios_short_games_context"]
MARKET_CONTEXT = P.PROFILE + [E.SR] + E.CONTEXT
WINDOWS = {"2019_onward": (2019, 2026), "2022_onward": (2022, 2026),
           "2019_2025": (2019, 2025), "2024_2025": (2024, 2025)}


def walk(frame, columns, penalized, grid=GRID):
    """Fit annual expanding models, selecting ridge on prior two OOS seasons.

    RMS scales are fitted inside each annual fit. All inputs must be odd under
    A/B exchange. Baseline coefficients are unpenalized in the Elo route.
    """
    x = frame[columns].to_numpy(dtype=float)
    y = frame.a_won.to_numpy(dtype=float)
    years = frame.year.to_numpy(dtype=int)
    evaluation = frame.evaluation.to_numpy(dtype=bool)
    if not np.isfinite(x).all():
        raise ValueError("All model inputs must be finite; no implicit imputation")
    grid = tuple(grid) if penalized else (0.,)
    mask = np.array([col in penalized for col in columns], dtype=float)
    pred = np.full(len(frame), np.nan)
    losses = np.full((len(frame), len(grid)), np.nan)
    records = []
    for year in sorted(set(years)):
        tr, te = years < year, years == year
        if tr.sum() < 300:
            continue
        scale = P.rms_scale(x[tr])
        xt, xv = x[tr] / scale, x[te] / scale
        bs, ps = [], []
        for j, ridge in enumerate(grid):
            b = P.fit_logistic(xt, y[tr], np.zeros(tr.sum()), mask * ridge)
            eta = xv @ b
            losses[te, j] = P.ll(y[te], eta)
            bs.append(b)
            ps.append(expit(eta))
        if len(grid) > 1:
            chosen, nv, vy = P.pick_lambda(years, int(year), losses, evaluation, grid)
        else:
            chosen, nv, vy = 0, 0, []
        pred[te] = ps[chosen]
        records.append({"year": int(year), "n_train": int(tr.sum()), "n_test": int(te.sum()),
                        "validation_n": nv, "validation_years": vy, "ridge": grid[chosen],
                        "columns": columns, "rms": scale.tolist(), "beta": bs[chosen].tolist()})
    return pred, records


def select_past(frame, predictions):
    """Annual model choice uses earlier OOS losses; no retrospective best pick."""
    names = list(predictions)
    if names[0] != "baseline":
        raise ValueError("Baseline must be first, for fallback and deterministic ties")
    y, years = frame.a_won.to_numpy(dtype=float), frame.year.to_numpy(dtype=int)
    p = np.column_stack([predictions[name] for name in names])
    loss = np.column_stack([E.loss(y, p[:, j]) for j in range(len(names))])
    result = np.full(len(frame), np.nan)
    records = []
    for year in sorted(set(years)):
        valid = (years < year) & (years >= year - 2) & frame.evaluation.to_numpy(dtype=bool)
        valid &= np.isfinite(loss).all(axis=1)
        j = int(np.argmin(loss[valid].mean(axis=0))) if valid.sum() >= 300 else 0
        result[years == year] = p[years == year, j]
        records.append({"year": int(year), "selected": names[j], "validation_n": int(valid.sum()),
                        "validation_years": sorted(set(years[valid].tolist()))})
    return result, records


def interval(delta, clusters):
    value = P.clustered_interval(delta, clusters)
    n = len(delta)
    ids, inv = np.unique(clusters, return_inverse=True)
    influence = np.bincount(inv, weights=delta - delta.mean())
    se = np.sqrt(len(ids) / (len(ids)-1) * (influence @ influence)) / n if len(ids) > 1 else np.nan
    value["p_two_sided"] = (float(2 * student_t.sf(abs(delta.mean()/se), len(ids)-1)) if se > 0
                            else (1. if np.all(delta == 0) else np.nan))
    return value


def comparisons(frame, predictions, pairs, **labels):
    losses = {name: E.loss(frame.a_won.to_numpy(dtype=float), p) for name, p in predictions.items()}
    day = (frame.tournament_date.to_numpy(dtype="datetime64[D]") - np.datetime64("2010-01-04")).astype(int)
    windows = {**WINDOWS, **{f"year_{year}": (year, year) for year in range(2019, 2027)}}
    result = []
    for model, baseline in dict.fromkeys(pairs):
        delta = losses[baseline] - losses[model]
        for window, (start, stop) in windows.items():
            keep = frame.year.between(start, stop).to_numpy() & frame.evaluation.to_numpy(dtype=bool)
            keep &= np.isfinite(delta)
            if not keep.any():
                continue
            result.append({**labels, "model": model, "comparator": baseline, "window": window,
                           "n": int(keep.sum()), **interval(delta[keep], day[keep]//28),
                           **{f"week_{k}": v for k,v in P.clustered_interval(delta[keep], day[keep]//7).items()},
                           "model_ll": float(losses[model][keep].mean()),
                           "comparator_ll": float(losses[baseline][keep].mean()),
                           "first_day": str(frame.tournament_date[keep].min().date()),
                           "last_day": str(frame.tournament_date[keep].max().date())})
    return result


def holm(pvalues):
    p = np.asarray(pvalues, dtype=float)
    if not np.isfinite(p).all():
        raise ValueError("Cannot adjust undefined p-values")
    order = np.argsort(p)
    adjusted = np.empty(len(p))
    adjusted[order] = np.minimum(1., np.maximum.accumulate(p[order] * np.arange(len(p), 0, -1)))
    return adjusted


def main():
    from src.eda.predictive_frontier.features import FEATURE_GROUPS
    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    groups = {**FEATURE_GROUPS, "combined": list(dict.fromkeys(c for cols in FEATURE_GROUPS.values() for c in cols))}
    feature_path = OUT / "frontier_features.parquet"
    protocol = {"status": "exploratory reuse of previously inspected history; no untouched holdout",
                "created_before_scores": True, "date": "2026-10-02", "groups": groups,
                "elo_baseline": STRONG, "market_baseline": MARKET_CONTEXT, "extension_grid": GRID,
                "market_baseline_grid": P.GRID,
                "numerical_revision": "First run failed before any candidate scores: unpenalized redundant momentum/level columns did not converge. Extensions require strictly positive ridge; cached baselines retain their original grid.",
                "elo_penalty": "new inputs only; all nine existing coefficients unpenalized",
                "market_penalty": "all features penalized equally; market calibration unpenalized",
                "selection": "ridge and family selected using prior two OOS calendar seasons; fallback baseline family",
                "windows": WINDOWS, "primary": "Pinnacle and market-free Elo, each tour, 2019 onward, versus strong baseline",
                "multiple_testing": "Holm correction across 28 primary tests: six extensions plus past-only selector, two tours, two routes",
                "average_market": "sensitivity on identical common Pinnacle/Average rows",
                "uncertainty": "paired four-week calendar cluster t; weekly sensitivity; reused-history intervals descriptive",
                "training": {"elo": "2013 onward", "market": "2010 onward"},
                "hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in (R.FEATURES, feature_path, P.PD / "stage1_odds.parquet",
                                        Path(__file__).with_name("features.py"), Path(__file__))}}
    R.write_json(OUT / "protocol.json", protocol)
    frame = R.load_frame()
    new = pd.read_parquet(feature_path)
    frame = frame.merge(new, on="match_id", how="left", validate="one_to_one")
    cols = groups["combined"]
    if not np.isfinite(frame[cols].to_numpy(dtype=float)).all():
        raise ValueError("Missing new feature rows")
    results, saves, coefficients, selections, coverage, reproduction = [], [], [], [], [], []
    for tour in ("atp", "wta"):
        for route in ("elo", "pinnacle", "average"):
            base = STRONG if route == "elo" else ["market_logit"] + MARKET_CONTEXT
            needed = STRONG if route == "elo" else MARKET_CONTEXT + ["p_avg_a", "p_ps_a"]
            g, cv = R.common_cohort(frame, needed, tour, min_year=2013 if route == "elo" else 2010)
            coverage.extend([{**r, "route": route} for r in cv])
            if route != "elo":
                g["market_logit"] = logit(g["p_ps_a" if route == "pinnacle" else "p_avg_a"].clip(1e-10, 1-1e-10))
            penalty = [] if route == "elo" else MARKET_CONTEXT
            pred = {}
            pred["baseline"], records = walk(g, base, penalty, grid=P.GRID)
            coefficients.extend([{"tour": tour, "route": route, "model": "baseline", **r} for r in records])
            # Exact cached comparator check: compares IDs, outcomes, values; no reuse in training.
            if route == "elo":
                old = pd.read_parquet(R.OUT / "elo_predictions.parquet")
                old = old[old.tour.eq(tour)].set_index("match_id")
                expected = old["elo_sr_adjperf_ios_short_games_context"].reindex(g.match_id).to_numpy()
                take = np.isfinite(expected) & g.year.ge(2019).to_numpy()
                if not np.array_equal(take, np.isfinite(pred["baseline"]) & g.year.ge(2019).to_numpy()):
                    raise ValueError("Elo baseline target coverage changed")
                if not np.array_equal(old.a_won.reindex(g.match_id).to_numpy()[take], g.a_won.to_numpy()[take]):
                    raise ValueError("Elo baseline target labels changed")
                error = float(np.max(np.abs(expected[take] - pred["baseline"][take])))
                if error > 2e-6:
                    raise ValueError(f"Elo baseline reproduction differs: {error}")
                reproduction.append({"tour": tour, "route": route, "n": int(take.sum()), "max_abs_error": error})
            elif tour == "atp":
                old = pd.read_parquet(R.OUT / "profile_predictions.parquet").set_index("match_id")
                name = "p_ps_a" if route == "pinnacle" else "p_avg_a"
                expected = old[f"{name}|profile_context"].reindex(g.match_id).to_numpy()
                take = np.isfinite(expected)
                if not np.array_equal(take, np.isfinite(pred["baseline"])):
                    raise ValueError("Market baseline target coverage changed")
                if not np.array_equal(old.a_won.reindex(g.match_id).to_numpy()[take], g.a_won.to_numpy()[take]):
                    raise ValueError("Market baseline target labels changed")
                error = float(np.max(np.abs(expected[take] - pred["baseline"][take])))
                if error > 2e-6:
                    raise ValueError(f"Market baseline reproduction differs: {error}")
                reproduction.append({"tour": tour, "route": route, "n": int(take.sum()), "max_abs_error": error})
            for name, extra in groups.items():
                pred[name], records = walk(g, base + extra, penalty + extra)
                coefficients.extend([{"tour": tour, "route": route, "model": name, **r} for r in records])
                print(f"{tour} {route}: {name}", flush=True)
            pred["past_selected"], selected = select_past(g, pred)
            selections.extend([{"tour": tour, "route": route, **r} for r in selected])
            pairs = [(name, "baseline") for name in (*groups, "past_selected")]
            if route == "elo":
                pred["raw_pinnacle"] = g.p_ps_a.to_numpy(dtype=float)
                pairs.extend((name, "raw_pinnacle") for name in ("baseline", *groups, "past_selected"))
            else:
                pred["raw_market"] = expit(g.market_logit.to_numpy())
                pred["calibrated_market"], _ = walk(g, ["market_logit"], [])
                pairs.extend((name, cmp) for name in ("baseline", *groups, "past_selected")
                             for cmp in ("raw_market", "calibrated_market"))
            results.extend(comparisons(g, pred, pairs, tour=tour, route=route))
            save = g[["match_id", "tour", "year", "tournament_date", "evaluation", "a_won"]].copy()
            save["route"] = route
            for name, p in pred.items():
                save[name] = p
            saves.append(save)
    result = pd.DataFrame(results)
    primary = result.route.isin(["elo", "pinnacle"]) & result.window.eq("2019_onward") & result.comparator.eq("baseline")
    if primary.sum() != 28:
        raise ValueError(f"Expected 28 primary comparisons, got {primary.sum()}")
    result.loc[primary, "holm_p_28_primary"] = holm(result.loc[primary, "p_two_sided"])
    result.to_csv(OUT / "results.csv", index=False)
    pd.concat(saves, ignore_index=True).to_parquet(OUT / "predictions.parquet", index=False, compression="zstd")
    pd.DataFrame(coverage).to_csv(OUT / "coverage.csv", index=False)
    R.write_json(OUT / "coefficients.json", coefficients)
    R.write_json(OUT / "selections.json", selections)
    R.write_json(OUT / "summary.json", {"protocol": protocol, "primary_results": result[primary].to_dict("records"),
                                       "baseline_reproduction": reproduction, "coverage": coverage,
                                       "seconds": time.monotonic() - started})
    print(result[primary][["tour", "route", "model", "n", "gain_mll", "lo_mll", "hi_mll", "holm_p_28_primary"]].to_string(index=False))


if __name__ == "__main__":
    main()
