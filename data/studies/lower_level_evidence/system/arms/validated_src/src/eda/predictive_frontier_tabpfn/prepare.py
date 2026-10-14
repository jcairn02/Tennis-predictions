"""Freeze the repaired 36-input study and fair, fixed-training logistic controls.

One row per men's match. Training stops at the end of 2025 and testing uses
2026 only. A small forward-validation comparison chooses training history
without using 2026 outcomes. No odds are uploaded.
"""
from __future__ import annotations
import os
for key in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[key] = "1"
import json
import sys
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.predictive_frontier_tabpfn import common as C
from src.eda.predictive_frontier_tabpfn import guard as G
from src.eda.predictive_frontier import score as F
from src.eda.feature_alpha_audit import repair_score as R
from src.eda.feature_alpha_audit import profile_retest as P

DESCRIPTION = (
    "Professional men's tennis singles, ATP only. "
    "One row per match; random player A orientation; target1 means A won/advanced. "
    "All 36 sporting columns reverse sign when A and B are swapped. "
    "NO market prices, player identities or match outcomes are input features. "
    "The first9 sports inputs are surface Elo logit, pre-match serve/return matchup logit, "
    "recent opponent-adjusted total-points form, short-memory serve/return strength, games-weighted Elo, "
    "observed 14day workload difference, surface-familiarity difference, age difference and centered squared-age difference. "
    "The new27 inputs include serve/return point performance minus each player's own expected performance "
    "given own and opposing strength, at28/182day half-lives and their difference; a partially pooled surface "
    "residual correction; effective point exposure and variability interactions; observed recovery/retirement "
    "history; and prior-days event serve residuals interacting with style and Elo. Missing history uses "
    "explicit neutral priors and coverage controls, not guessed injury or rest. "
    "All history is rebuilt using trusted match days; new rolling states use strictly earlier days. "
    "Training ends in2025, future evaluation is2026 only. Optimize probability log loss."
)


STRATEGIES = ("all", "latest6", "latest4")
VALIDATION_YEARS = (2023, 2024, 2025)


def history_mask(frame, validation_year, strategy):
    """Calendar history for a forecast year, never including that year's rows."""
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown training strategy: {strategy}")
    start = 2013 if strategy == "all" else max(2013, validation_year-int(strategy[6:]))
    return frame.year.ge(start) & frame.year.lt(validation_year)


def select_training_history(frame):
    """Select history and ridge using only men's 2023-25 forward log loss.

    This is a logistic proxy for the one TabPFN fit, not evidence that the same
    history is optimal for TabPFN. No final-season labels or inputs are read.
    """
    past = frame.loc[frame.tour.eq("atp") & frame.year.between(2013, 2025)].copy()
    candidates = []
    mask = np.array([col in C.FEATURE_COLUMNS for col in C.SPORTS], dtype=float)
    for strategy in STRATEGIES:
        totals = np.zeros(len(F.GRID))
        folds = [[] for _ in F.GRID]
        n_valid = 0
        for year in VALIDATION_YEARS:
            tr, va = history_mask(past, year, strategy), past.year.eq(year)
            if tr.sum() < 300 or va.sum() == 0:
                raise ValueError(f"Insufficient forward-validation history for {strategy}/{year}")
            x = past.loc[tr, C.SPORTS].to_numpy(dtype=float)
            xv = past.loc[va, C.SPORTS].to_numpy(dtype=float)
            y = past.loc[tr, "a_won"].to_numpy(dtype=float)
            yv = past.loc[va, "a_won"].to_numpy(dtype=float)
            scale = P.rms_scale(x)
            for j, ridge in enumerate(F.GRID):
                beta = P.fit_logistic(x/scale, y, np.zeros(len(y)), mask*ridge)
                loss = P.ll(yv, (xv/scale)@beta)
                totals[j] += loss.sum()
                folds[j].append({"validation_year": year, "train_rows": int(tr.sum()),
                    "train_year_min": int(past.loc[tr, "year"].min()),
                    "train_year_max": int(past.loc[tr, "year"].max()),
                    "validation_rows": int(va.sum()), "log_loss": float(loss.mean())})
            n_valid += int(va.sum())
        for j, ridge in enumerate(F.GRID):
            candidates.append({"strategy": strategy, "penalty": ridge,
                "log_loss": float(totals[j]/n_valid), "validation_rows": n_valid, "folds": folds[j]})
    chosen = min(candidates, key=lambda row: row["log_loss"])
    return {"strategy": chosen["strategy"], "chosen_penalty": chosen["penalty"],
        "validation_years": list(VALIDATION_YEARS), "validation_rows": chosen["validation_rows"],
        "selection_metric": "Pooled match log loss on forward 2023, 2024, 2025 predictions; logistic proxy",
        "selected_training_min_year": int(past.loc[history_mask(past, 2026, chosen["strategy"]), "year"].min()),
        "candidates": candidates}


def fixed_logistic(frame, columns, penalized, ridge):
    """Fit the frozen pre-2026 history and selected ridge; forecast 2026 once."""
    train = frame[frame.split.eq("train")]
    test = frame[frame.split.eq("test")]
    if not train.year.between(2013, 2025).all() or not test.year.eq(2026).all() or not frame.tour.eq("atp").all():
        raise ValueError("Fixed chronological split violated")
    x = train[columns].to_numpy(dtype=float)
    y = train.a_won.to_numpy(dtype=float)
    xtest = test[columns].to_numpy(dtype=float)
    mask = np.array([col in penalized for col in columns], dtype=float)
    ridge = ridge if penalized else 0.
    scale = P.rms_scale(x)
    beta = P.fit_logistic(x/scale, y, np.zeros(len(y)), mask*ridge)
    pred = expit((xtest/scale)@beta)
    return pred, {"columns": columns, "n_train": len(train), "n_test": len(test),
        "train_years": sorted(train.year.unique().tolist()), "chosen_penalty": ridge,
        "training_rms": scale.tolist(), "beta": beta.tolist()}


def market_calibration(frame, column):
    train = frame[frame.split.eq("train") & np.isfinite(frame[column])]
    test = frame[frame.split.eq("test")]
    x = logit(train[column].clip(1e-10, 1-1e-10).to_numpy())
    beta = P.fit_logistic(x[:, None], train.a_won.to_numpy(dtype=float), np.zeros(len(train)), np.zeros(1))
    p = expit(logit(test[column].clip(1e-10, 1-1e-10).to_numpy()) * beta[0])
    return p, {"column": column, "n_train": len(train), "slope": float(beta[0]), "train_year_max": int(train.year.max())}


def build_frame():
    base = R.load_frame()
    extra = pd.read_parquet(F.OUT / "frontier_features.parquet")
    frame = base.merge(extra, on="match_id", how="left", validate="one_to_one")
    frame, coverage = R.common_cohort(frame, C.SPORTS, "atp", min_year=2013)
    frame = frame.sort_values(["tournament_date", "match_id"], kind="stable").reset_index(drop=True)
    if not frame.scheduled_format_supported.all():
        raise ValueError("Unsupported pre-match format entered the common sporting cohort")
    if not frame.year.between(2013, 2026).all() or frame.tournament_date.max() > pd.Timestamp("2026-10-02"):
        raise ValueError("Unexpected/future source date")
    frame["split"] = np.where(frame.year.lt(2026), "train", "test")
    if frame.match_id.duplicated().any() or not np.isfinite(frame[C.SPORTS].to_numpy()).all():
        raise ValueError("Invalid common model frame")
    return frame, coverage


def main():
    if (C.THINKING / "fit_slot.json").exists() or (C.THINKING / "request.json").exists():
        raise RuntimeError("Paid study already bound; do not rebuild its frozen upload")
    C.UPLOAD.mkdir(parents=True, exist_ok=True)
    # Preserve the rejected, never-dispatched preparation before replacing it.
    old_manifest = C.OUT / "manifest.json"
    archive = C.OUT / "superseded_pooled_preparation.zip"
    if old_manifest.exists() and "tour_code" in json.loads(old_manifest.read_text())["names"]:
        if archive.exists():
            raise RuntimeError("Superseded archive already exists; inspect before overwriting")
        paths = [old_manifest, C.OUT/"frame.parquet", C.OUT/"baselines.parquet", C.OUT/"baselines_meta.json",
                 *sorted(C.UPLOAD.glob("*"))]
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
            for path in paths:
                z.write(path, str(path.relative_to(C.OUT)))
    source_paths = [R.FEATURES, F.OUT / "frontier_features.parquet", P.PD / "stage1_odds.parquet",
                    F.OUT / "predictions.parquet"]
    before = {str(p.relative_to(ROOT)): C.sha256_file(p) for p in source_paths}
    frame, coverage = build_frame()
    selection = select_training_history(frame)
    selected_train = history_mask(frame, 2026, selection["strategy"])
    frame.loc[frame.year.lt(2026) & ~selected_train, "split"] = "unused_history"
    test = frame[frame.split.eq("test")].copy()
    baselines = test[["match_id"]].copy()
    records = {}
    for tour in ("atp",):
        part = frame[frame.tour.eq(tour)]
        rows = test.tour.eq(tour).to_numpy()
        records[tour] = {}
        for name, columns, penalized in [("logistic_strong_fixed", C.STRONG, []),
                ("logistic_combined_fixed", C.SPORTS, C.FEATURE_COLUMNS)]:
            pred, record = fixed_logistic(part, columns, penalized, selection["chosen_penalty"])
            baselines.loc[rows, name] = pred
            records[tour][name] = record
        for name, column in [("average_calibrated", "p_avg_a"), ("pinnacle_calibrated", "p_ps_a")]:
            pred, record = market_calibration(part, column)
            baselines.loc[rows, name] = pred
            records[tour][name] = record
        print(f"{tour}: train {part.split.eq('train').sum():,}; test {rows.sum():,}; fixed ridge {records[tour]['logistic_combined_fixed']['chosen_penalty']}", flush=True)
    old = pd.read_parquet(F.OUT / "predictions.parquet")
    old = old[old.route.eq("elo")].set_index("match_id").reindex(test.match_id)
    if not np.array_equal(old.a_won.to_numpy(), test.a_won.to_numpy()):
        raise ValueError("Annual prediction identity/orientation mismatch")
    baselines["logistic_combined_annual"] = old.combined.to_numpy()
    if not np.isfinite(baselines[["logistic_strong_fixed", "logistic_combined_fixed", "logistic_combined_annual"]]).all().all():
        raise ValueError("Missing primary comparator prediction")
    X = frame[C.SPORTS].rename(columns=C.RENAMES).astype(float)
    X_train = X[frame.split.eq("train")].reset_index(drop=True)
    y_train = frame.loc[frame.split.eq("train"), "a_won"].to_numpy(dtype=np.int64)
    X_test = X[frame.split.eq("test")].reset_index(drop=True)
    X_query = pd.concat([X_test, C.flip(X_test)], ignore_index=True)
    ids = pd.DataFrame({"match_id": np.tile(test.match_id.to_numpy(), 2),
                        "orientation": np.repeat([0, 1], len(test))})
    frame.to_parquet(C.OUT / "frame.parquet", index=False, compression="zstd")
    baselines.to_parquet(C.OUT / "baselines.parquet", index=False)
    X_train.to_parquet(C.UPLOAD / "X_train.parquet", index=False)
    np.save(C.UPLOAD / "y_train.npy", y_train)
    X_query.to_parquet(C.UPLOAD / "X_query.parquet", index=False)
    ids.to_parquet(C.UPLOAD / "query_ids.parquet", index=False)
    C.write_json(C.OUT / "baselines_meta.json", records)
    after = {str(p.relative_to(ROOT)): C.sha256_file(p) for p in source_paths}
    if before != after:
        raise RuntimeError("A source changed during preparation")
    artifacts = [C.OUT / "frame.parquet", C.OUT / "baselines.parquet", C.OUT / "baselines_meta.json",
                  *[C.UPLOAD / n for n in ("X_train.parquet", "y_train.npy", "X_query.parquet", "query_ids.parquet")]]
    manifest = {"study_date": "2026-10-02", "input_sha256": C.fingerprint(X_train, y_train, X_query),
        "source_sha256": before, "artifact_sha256": {str(p.relative_to(C.OUT)): C.sha256_file(p) for p in artifacts},
        "code_sha256": {str(p.relative_to(ROOT)): C.sha256_file(p) for p in (Path(__file__), Path(C.__file__), Path(G.__file__))},
        "names": C.NAMES, "sports_source_columns": C.SPORTS, "fit_description": DESCRIPTION,
        "config": G.CONFIG, "shapes": {"X_train": list(X_train.shape), "X_query": list(X_query.shape)},
        "counts": frame.groupby(["split", "tour"]).size().rename("matches").reset_index().to_dict("records"),
        "coverage": coverage, "train_selection": selection, "protocol": {
            "authorized_budget": "one Thinking fit and one prediction request; saved receipts prevent repetitions",
            "model": "TabPFN3.5 Thinking; high effort; log_loss; 8 estimators requested; seed0",
            "inputs": "36 exact frontier sporting columns; men only; no prices/dates/IDs/labels in X",
            "train": f"ATP {selection['selected_training_min_year']}-2025; strategy {selection['strategy']}",
            "test": "ATP2026 only, through available2026-08-02; no test labels uploaded",
            "comparison": "logistic uses identical training/test rows and same36 sports inputs",
            "baseline_penalty": "original9 coefficients unpenalized; new27 ridge and training history picked on forward2023/24/25 predictions only",
            "annual_reference": "cached original36-input logistic for2026 uses all2013-2025 training and its previously selected ridge",
            "symmetry": "one query contains original and flipped A/B inputs; average p(A) and 1-p(A swapped)",
            "markets": "raw and selected-pre2026-training slope-calibrated Average/Pinnacle on identical finite-quote test subsets",
            "uncertainty": "paired four-week calendar-block95% intervals; single fit uncertainty not covered",
            "time_col": "omitted to keep exact sporting inputs; internal Thinking validation not guaranteed chronological",
            "limitations": ["Features/years previously selected and inspected; not untouched holdout",
                "Training history selection uses logistic validation as a proxy; one TabPFN fit cannot establish its optimal history",
                "Sporting aggregates update using allowed earlier test matches while fitted model weights stay frozen",
                "Dated-only coverage; ATP2018 largely absent;2026 partial; exact quote/publication times unverified",
                "Onefit/seed/split; no executable betting returns"]}}
    C.write_json(C.OUT / "manifest.json", manifest)
    C.load_upload()
    print(f"Frozen upload: train {X_train.shape}; query {X_query.shape}; {len(test):,} distinct test matches", flush=True)


if __name__ == "__main__":
    main()
