"""Exploratory, fixed-ladder retest of promising existing features beyond Elo.

Reuses historical feature values, not their original scoring or null thresholds.
No original study artifacts are changed. Columns/windows were selected after
reading both studies, so this is a robustness check, not an untouched holdout.
Run: ./python.sh src/eda/feature_alpha_audit/elo_retest.py
"""
from __future__ import annotations

import os
for _key in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_key, "1")

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.predictability_diagnostic.stage4_rundown import newton

OUT = ROOT / "data/studies/feature_alpha_audit"
DIAG = ROOT / "data/studies/predictability_diagnostic"
UFC = ROOT / "data/studies/ufc_ideas"
SR = "rating_matchup|single"
ADJ = "adjperf_tpw|decayed"
IOS = "ios_short"
IOS_ATP = "ios_matchup_points|diagnostic: h 4 weeks"
IOS_WTA = "ios_matchup_points|diagnostic: h 13 weeks"
GAMES = "elo_games|single"
CONTEXT = ["sets_14d|single", "surface_first|single", "age|single", "age|single|2"]
# Fixed before this script's first empirical run; the ladder is not optimized.
SPECS = {
    "elo_calibrated": ["elo_logit"],
    "elo_sr": ["elo_logit", SR],
    "elo_sr_adjperf": ["elo_logit", SR, ADJ],
    "elo_sr_ios_short": ["elo_logit", SR, IOS],
    "elo_sr_adjperf_ios_short": ["elo_logit", SR, ADJ, IOS],
    "elo_sr_adjperf_ios_short_games": ["elo_logit", SR, ADJ, IOS, GAMES],
    "elo_sr_adjperf_ios_short_games_load": ["elo_logit", SR, ADJ, IOS, GAMES, CONTEXT[0]],
    "elo_sr_adjperf_ios_short_games_surface": ["elo_logit", SR, ADJ, IOS, GAMES, CONTEXT[1]],
    "elo_sr_adjperf_ios_short_games_age": ["elo_logit", SR, ADJ, IOS, GAMES] + CONTEXT[2:],
    "elo_sr_adjperf_ios_short_games_context": ["elo_logit", SR, ADJ, IOS, GAMES] + CONTEXT,
}
REFERENCES = {
    "elo_calibrated": "elo_raw",
    "elo_sr": "elo_calibrated",
    "elo_sr_adjperf": "elo_sr",
    "elo_sr_ios_short": "elo_sr",
    "elo_sr_adjperf_ios_short": "elo_sr_adjperf",
    "elo_sr_adjperf_ios_short_games": "elo_sr_adjperf_ios_short",
    "elo_sr_adjperf_ios_short_games_load": "elo_sr_adjperf_ios_short_games",
    "elo_sr_adjperf_ios_short_games_surface": "elo_sr_adjperf_ios_short_games",
    "elo_sr_adjperf_ios_short_games_age": "elo_sr_adjperf_ios_short_games",
    "elo_sr_adjperf_ios_short_games_context": "elo_sr_adjperf_ios_short_games",
}


def loss(y, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def walk_predictions(frame, columns, train_from=2013, score_from=2019):
    """Annual expanding fits; scale by training RMS without centering A-B inputs."""
    X = frame[columns].to_numpy(dtype=float)
    y = frame.a_won.to_numpy(dtype=float)
    years = frame.year.to_numpy(dtype=int)
    result = np.full(len(frame), np.nan)
    coefficients = []
    for year in sorted(set(years[years >= score_from])):
        tr = (years >= train_from) & (years < year)
        te = years == year
        if tr.sum() < 300:
            continue
        rms = np.sqrt(np.mean(X[tr] ** 2, axis=0))
        rms = np.where(rms > 1e-12, rms, 1.)
        info = {}
        beta = newton((X[tr] / rms)[None], y[tr], np.zeros((1, len(columns))), info=info)[0]
        if not bool(info["converged"][0]):
            raise RuntimeError(f"Nonconverged {year}: {columns}")
        result[te] = expit((X[te] / rms) @ beta)
        coefficients.append({"season": int(year), "training_rows": int(tr.sum()),
                             "test_rows": int(te.sum()), "columns": columns,
                             "training_rms": rms.tolist(), "standardized_beta": beta.tolist()})
    return result, coefficients


def clustered_gain(delta, weeks):
    """95% calendar-week cluster-robust interval for the paired mean (milliLL)."""
    delta = np.asarray(delta, dtype=float)
    weeks = np.asarray(weeks)
    keep = np.isfinite(delta)
    delta, weeks = delta[keep], weeks[keep]
    n = len(delta)
    if not n:
        return {"n": 0, "weeks": 0, "gain_mll": None, "lo_mll": None, "hi_mll": None}
    mean = float(delta.mean())
    residuals = pd.Series(delta - mean).groupby(weeks).sum().to_numpy()
    groups = len(residuals)
    se = np.sqrt(groups / (groups - 1) * np.sum(residuals ** 2)) / n if groups > 1 else np.nan
    radius = float(student_t.ppf(.975, groups - 1) * se) if groups > 1 else np.nan
    return {"n": n, "weeks": groups, "gain_mll": 1000 * mean,
            "lo_mll": 1000 * (mean - radius), "hi_mll": 1000 * (mean + radius)}


def load_frame(min_year=2013):
    features = list(dict.fromkeys(c for cols in SPECS.values() for c in cols if c != "elo_logit"))
    base = ["match_id", "tour", "year", "evaluation", "group", "status", "a_won", "p_elo", "p_mkt", "order"]
    from_diag = [c for c in features if c not in (ADJ, IOS)]
    f = pd.read_parquet(DIAG / "stage4_features.parquet", columns=base + from_diag)
    for file, columns in (("stageB_adj_features.parquet", [ADJ]), ("stageB_ios_features.parquet", [IOS_ATP, IOS_WTA])):
        f = f.merge(pd.read_parquet(UFC / file, columns=["match_id"] + columns), on="match_id", validate="one_to_one")
    f[IOS] = np.where(f.tour.eq("atp"), f[IOS_ATP], f[IOS_WTA])
    dates = pd.read_parquet(DIAG / "stage0_matches.parquet", columns=["match_id", "tournament_date"])
    f = f.merge(dates, on="match_id", validate="one_to_one")
    f["week"] = pd.to_datetime(f.tournament_date).dt.to_period("W-SUN").astype(str)
    f["elo_logit"] = logit(f.p_elo.clip(1e-12, 1 - 1e-12))
    eligible = f.year.ge(min_year) & f.status.isin(["completed", "retired"])
    # The stage4 table is already evaluation-level; evaluation is false in warmup.
    selected = eligible & np.isfinite(f[features + ["elo_logit"]].to_numpy(dtype=float)).all(axis=1)
    coverage = []
    for tour in ("atp", "wta"):
        for since in (2019, 2022):
            target = eligible & f.tour.eq(tour) & f.year.ge(since)
            coverage.append({"tour": tour, "since": since, "eligible": int(target.sum()),
                             "common_rows": int((target & selected).sum())})
    return f.loc[selected].sort_values(["tour", "year", "order"]).reset_index(drop=True), coverage


def sensitivity_checks():
    """Descriptive attribution checks, added after seeing the first ladder run."""
    f, _ = load_frame(min_year=2010)
    m = pd.read_parquet(DIAG / "stage0_matches.parquet", columns=["match_id", "tour", "best_of", "format",
                       "tournament_id", "tournament_date", "level", "qualifying"])
    mp = pd.read_parquet(DIAG / "stage0_match_players.parquet", columns=["match_id", "sets_won_n"])
    maximum_sets = mp.groupby("match_id").sets_won_n.max()
    m["score_bo5"] = m.match_id.map(maximum_sets).ge(3)
    # Drop whole event editions if any record has a nonstandard format or an
    # outcome-derived bo5 override, not just the individual offending match.
    m["event_key"] = m.tour.astype(str) + "|" + m.tournament_id.astype(str) + "|" + m.tournament_date.astype(str)
    bad = ~m.format.eq("standard") | (m.score_bo5 & ~m.best_of.eq(5))
    bad_events = set(m.loc[bad, "event_key"])
    m["format_safe"] = ~m.event_key.isin(bad_events)
    f = f.merge(m[["match_id", "format_safe"]], on="match_id", validate="one_to_one")
    out = []
    for tour in ("atp", "wta"):
        for scenario, train_from, safe in (("train_2010", 2010, False), ("train_2013", 2013, False),
                                           ("exclude_format_event_editions", 2013, True)):
            g = f[f.tour.eq(tour) & (f.format_safe if safe else True)].reset_index(drop=True)
            models = {"elo": ["elo_logit"], "elo_age": ["elo_logit"] + CONTEXT[2:],
                      "strong": SPECS["elo_sr_adjperf_ios_short_games"],
                      "context": SPECS["elo_sr_adjperf_ios_short_games_context"]}
            losses = {}
            for name, cols in models.items():
                p, _ = walk_predictions(g, cols, train_from=train_from)
                losses[name] = loss(g.a_won.to_numpy(dtype=float), p)
            for since in (2019, 2022):
                idx = g.year.ge(since).to_numpy()
                for model, reference in (("elo_age", "elo"), ("context", "strong"), ("context", "elo")):
                    out.append({"tour": tour, "scenario": scenario, "since": since, "model": model,
                                "reference": reference, **clustered_gain((losses[reference] - losses[model])[idx],
                                                                        g.week.to_numpy()[idx])})
    pd.DataFrame(out).to_csv(OUT / "elo_sensitivities.csv", index=False)
    (OUT / "elo_format_audit.json").write_text(json.dumps({
        "source_matches_with_bo5_override": int((m.score_bo5 & ~m.best_of.eq(5) & m.format.eq("standard")).sum()),
        "event_editions_removed": len(bad_events),
        "common_rows_removed": int((~f.format_safe).sum()),
        "method": "Sensitivity drops entire tournament editions containing any nonstandard format or score-derived bo5 override.",
        "limitation": "This is an outcome-audited sensitivity subset, not a deployable inclusion rule or a repaired forecast. Stored short-IOS diagnostics have no per-player rates to rebuild format cheaply."}, indent=2), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = {"status": "exploratory robustness retest, selected from already inspected studies",
                "train_from": 2013, "score_from": 2019, "specifications": SPECS, "references": REFERENCES,
                "short_ios": "original studies' shortlisted diagnostics: ATP 4 weeks, WTA 13 weeks; evaluation years were already inspected",
                "revision": "Initial check used 4 weeks on both tours. Parent requested the original tour-specific shortlist before seeing revised results. Individual context ablations added after initial combined-block result for attribution, without selecting a winner.",
                "adjperf": "existing decayed total-points variant; both tours' frozen h3 is 2 weeks",
                "cohort": "common complete cases across every ladder feature, both training and test",
                "baseline": "raw Elo and annual slope-calibrated Elo; no intercept because A/B is arbitrary",
                "interval": "paired calendar-week cluster robust t intervals; no selection or multiple-testing adjustment",
                "limits": ["Historical tournament dates and format derivation are inherited unchanged.",
                           "These are pointwise historical intervals, not confirmation of selected ideas.",
                           "Calendar-week clustering does not capture serial player dependence across weeks.",
                           "The market subset is not executable quote history; no profitability measured."]}
    (OUT / "elo_protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    f, coverage = load_frame()
    results, coefs, predictions = [], [], []
    for tour in ("atp", "wta"):
        g = f[f.tour.eq(tour)].reset_index(drop=True)
        pred = {"elo_raw": g.p_elo.to_numpy(dtype=float)}
        for name, cols in SPECS.items():
            pred[name], fitted = walk_predictions(g, cols)
            coefs += [{"tour": tour, "model": name, **c} for c in fitted]
        y = g.a_won.to_numpy(dtype=float)
        losses = {name: loss(y, values) for name, values in pred.items()}
        losses["market_raw"] = loss(y, g.p_mkt.to_numpy(dtype=float))
        pg = g[["match_id", "tour", "year", "week", "a_won", "p_mkt"]].copy()
        for name, values in pred.items():
            pg[name] = values
        predictions.append(pg[pg.year.ge(2019)])
        for since in (2019, 2022):
            for population in ("all_common", "market_common"):
                mask = g.year.ge(since).to_numpy().copy()
                if population == "market_common":
                    mask &= np.isfinite(g.p_mkt.to_numpy(dtype=float))
                for name in SPECS:
                    references = [REFERENCES[name], "elo_raw", "elo_calibrated"]
                    if population == "market_common":
                        references.append("market_raw")
                    for reference in dict.fromkeys(references):
                        if name == reference:
                            continue
                        r = clustered_gain((losses[reference] - losses[name])[mask], g.week.to_numpy()[mask])
                        results.append({"tour": tour, "since": since, "population": population,
                                        "model": name, "reference": reference, **r,
                                        "model_logloss": float(np.mean(losses[name][mask])),
                                        "reference_logloss": float(np.mean(losses[reference][mask]))})
        print(f"{tour}: {len(g):,} common training/test matches", flush=True)
    pd.DataFrame(results).to_csv(OUT / "elo_results.csv", index=False)
    pd.DataFrame(coverage).to_csv(OUT / "elo_coverage.csv", index=False)
    pd.concat(predictions, ignore_index=True).to_parquet(OUT / "elo_predictions.parquet", index=False)
    (OUT / "elo_coefficients.json").write_text(json.dumps(coefs, indent=2), encoding="utf-8")
    (OUT / "elo_summary.json").write_text(json.dumps({"protocol": protocol, "coverage": coverage,
                                                      "results": results}, indent=2), encoding="utf-8")
    shown = pd.DataFrame(results)
    shown = shown[(shown.since == 2022) & shown.population.eq("all_common")]
    shown = shown[shown.apply(lambda row: row.reference == REFERENCES[row.model], axis=1)]
    print(shown[["tour", "model", "reference", "n", "gain_mll", "lo_mll", "hi_mll"]].to_string(index=False))
    sensitivity_checks()


if __name__ == "__main__":
    main()
