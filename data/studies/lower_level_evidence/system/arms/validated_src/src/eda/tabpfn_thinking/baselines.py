"""The free comparison models, fitted once on the same training matches as the TabPFN fit (main tour 2013-2021) and
predicting the same test matches (main tour 2022-2026), so that every comparison is on one split.

Linear (per tour, logistic regression without an intercept, as the earlier harness fits it; each input scaled by its
training standard deviation, a missing input set to 0 = "no difference"; antisymmetric by construction):
    elo                     surface Elo's log-odds alone (Elo recalibrated)
    lr_everything           Elo + the "everything" inputs that survive the feature-alpha audit (common.EVERYTHING)
    lr_all                  Elo + all 47 difference inputs (the TabPFN inputs without the match context)
With the closing odds (per tour, trained on the training matches that have odds; the men's 2018 season has none):
    market                  the odds' log-odds alone (the market recalibrated)
    lr_mkt_profile          odds + the 16-input two-week profile (single-fit analogue of the Stage D lead)
    lr_mkt_everything       odds + the everything inputs (the audit's ratings/load/age/surface control block)
    lr_mkt_everything_profile  odds + everything + profile (the audit's "profile + context" forecast)
    lr_mkt_all              odds + all 47 difference inputs
Gradient boosting (sklearn HistGradientBoosting, both tours pooled with the context columns as TabPFN gets them;
trained on every training match in both orientations; forecasts symmetrized; the number of trees chosen by early
stopping on 2020-2021 within the training seasons, then refitted on 2013-2021; constants fixed before any result):
    gbm_additive            the 47 differences, each tree on one input only (curvature without interactions)
    gbm                     all 53 inputs, interactions allowed
    gbm_mkt_additive        the odds' log-odds + the 47 differences, each tree on one input, on the matches with odds
    gbm_mkt                 the odds' log-odds + all 53 inputs, interactions allowed, on the matches with odds
                            (the free non-linear twin of the paid fit)

Writes data/studies/tabpfn_thinking/baselines.parquet (one row per test match: match_id and p_<model>) and
baselines_meta.json (specs, coefficients with standard errors, the boosting's chosen sizes and validation losses).
Run: ./python.sh src/eda/tabpfn_thinking/baselines.py    (a few minutes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402

GBM_PARAMS = dict(learning_rate=0.03, max_leaf_nodes=15, min_samples_leaf=100, l2_regularization=1.0,
                  max_bins=255, random_state=0)
GBM_MAX_ITER = 3000
GBM_VALID_YEARS = (2020, 2021)
LINEAR = {
    "elo": ["elo_logit"],
    "lr_everything": T.EVERYTHING,
    "lr_all": T.DIFF,
}
LINEAR_MKT = {
    "market": [],
    "lr_mkt_profile": T.PROFILE16,
    "lr_mkt_everything": T.EVERYTHING,
    "lr_mkt_everything_profile": T.EVERYTHING + T.PROFILE16,
    "lr_mkt_all": T.DIFF,
}


def load() -> pd.DataFrame:
    f = pd.read_parquet(T.OUT / "frame.parquet")
    f = f[f["split"].isin(["train", "test"])].reset_index(drop=True)
    f["mkt_logit"] = logit(np.clip(f["p_mkt"].to_numpy(dtype="float64"), T.EPS, 1 - T.EPS))
    f.loc[~np.isfinite(f["p_mkt"].to_numpy(dtype="float64")), "mkt_logit"] = np.nan
    return f


def X_of(f: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return np.column_stack([f[f"in_{c}"].to_numpy(dtype="float64") for c in cols]) if cols else np.zeros((len(f), 0))


def linear(f: pd.DataFrame, cols: list[str], with_market: bool) -> tuple[np.ndarray, dict]:
    """Per-tour fit on the training rows, forecast for the test rows (NaN where the model cannot forecast)."""
    p = np.full(len(f), np.nan)
    meta = {}
    for t in T.TOURS:
        tr = ((f["split"] == "train") & (f["tour"] == t)).to_numpy()
        te = ((f["split"] == "test") & (f["tour"] == t)).to_numpy()
        X = X_of(f, cols)
        sd = np.nanstd(X[tr], axis=0) if X.shape[1] else np.zeros(0)
        sd = np.where(sd > 0, sd, 1.0)
        Xs = np.nan_to_num(X / sd, nan=0.0)
        if with_market:
            m = f["mkt_logit"].to_numpy()
            Z = np.column_stack([m, Xs])
            tr = tr & np.isfinite(m)
            te = te & np.isfinite(m)
        else:
            Z = Xs
        b, se = T.fit_logistic(Z[tr], f["a_won"].to_numpy()[tr])
        p[te] = expit(Z[te] @ b)
        names = (["market_logit"] if with_market else []) + list(cols)
        meta[t] = {"train_matches": int(tr.sum()), "test_matches": int(te.sum()),
                   "coef": {n: [float(v), float(s)] for n, v, s in zip(names, b, se)},
                   "scale": {n: float(s) for n, s in zip(cols, sd)}}
    return p, meta


def gbm_fit_predict(f: pd.DataFrame, cols: list[str], additive: bool, with_market: bool) -> tuple[np.ndarray, dict]:
    """Pooled boosting on every training row in both orientations; the test forecast symmetrized."""
    def frame(rows: pd.DataFrame) -> pd.DataFrame:
        X = pd.DataFrame({c: rows[f"in_{c}"].to_numpy(dtype="float64") for c in cols})
        if with_market:
            X["mkt_logit"] = rows["mkt_logit"].to_numpy(dtype="float64")
        return X

    def both(rows: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
        X = frame(rows)
        Xf = T.flip(X)
        if with_market:
            Xf["mkt_logit"] = -X["mkt_logit"]
        y = rows["a_won"].astype(int).to_numpy()
        return pd.concat([X, Xf], ignore_index=True), np.r_[y, 1 - y]

    rows = f.copy()
    if with_market:
        rows = rows[np.isfinite(rows["mkt_logit"].to_numpy())]
    tr_all = rows[rows["split"] == "train"]
    fit_part = tr_all[tr_all["year"] < GBM_VALID_YEARS[0]]
    val_part = tr_all[tr_all["year"] >= GBM_VALID_YEARS[0]]
    names = list(cols) + (["mkt_logit"] if with_market else [])
    cat = [names.index(c) for c in T.CATEGORICAL if c in names]
    cst = [[i] for i in range(len(names))] if additive else None
    params = dict(GBM_PARAMS, categorical_features=cat or None, interaction_cst=cst)
    Xa, ya = both(fit_part)
    Xv, yv = both(val_part)
    est = HistGradientBoostingClassifier(max_iter=GBM_MAX_ITER, early_stopping=False, **params)
    est.fit(Xa, ya)
    val = [float(np.mean(T.ll(pv[:, 1], yv))) for pv in est.staged_predict_proba(Xv)]
    best = int(np.argmin(val)) + 1
    Xt, yt = both(tr_all)
    final = HistGradientBoostingClassifier(max_iter=best, early_stopping=False, **params)
    final.fit(Xt, yt)
    te = rows[rows["split"] == "test"]
    X_te = frame(te)
    X_tf = T.flip(X_te)
    if with_market:
        X_tf["mkt_logit"] = -X_te["mkt_logit"]
    p_sym = T.symmetrize(final.predict_proba(X_te)[:, 1], final.predict_proba(X_tf)[:, 1])
    p = pd.Series(np.nan, index=f.index)
    p.loc[te.index] = p_sym
    meta = {"n_iter": best, "valid_ll_best": val[best - 1], "valid_ll_at_100": val[min(99, len(val) - 1)],
            "train_rows_both_orientations": int(len(yt)), "inputs": names, "additive": additive,
            "asymmetry_mean_abs": float(np.mean(np.abs(final.predict_proba(X_te)[:, 1] - (1 - final.predict_proba(X_tf)[:, 1]))))}
    return p.to_numpy(), meta


def main() -> int:
    f = load()
    te = (f["split"] == "test").to_numpy()
    out = pd.DataFrame({"match_id": f.loc[te, "match_id"].to_numpy()})
    meta = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "gbm_params": GBM_PARAMS,
            "gbm_valid_years": GBM_VALID_YEARS, "models": {}}
    for name, cols in LINEAR.items():
        p, m = linear(f, cols, with_market=False)
        out[f"p_{name}"] = p[te]
        meta["models"][name] = {"kind": "linear", "inputs": cols, "per_tour": m}
        T.log(f"{name}: {len(cols)} inputs")
    for name, cols in LINEAR_MKT.items():
        p, m = linear(f, cols, with_market=True)
        out[f"p_{name}"] = p[te]
        meta["models"][name] = {"kind": "linear + market", "inputs": ["market_logit"] + cols, "per_tour": m}
        T.log(f"{name}: market + {len(cols)} inputs")
    for name, cols, additive, mk in (("gbm_additive", T.DIFF, True, False), ("gbm", T.NAMES, False, False),
                                     ("gbm_mkt_additive", T.DIFF, True, True), ("gbm_mkt", T.NAMES, False, True)):
        p, m = gbm_fit_predict(f, cols, additive, mk)
        out[f"p_{name}"] = p[te]
        meta["models"][name] = {"kind": "boosting", **m}
        T.log(f"{name}: {m['n_iter']} trees, validation log loss {m['valid_ll_best']:.5f}")
    out.to_parquet(T.OUT / "baselines.parquet", index=False)
    T.write_json(T.OUT / "baselines_meta.json", meta)
    T.log(f"wrote baselines.parquet ({len(out):,} test matches, {out.shape[1] - 1} models)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
