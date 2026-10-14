"""C1 and C4 of the edge-anatomy study: which of the model's inputs carry information beyond the closing price, era by
era, and whether that information shrinks as the market learns.

The frame: the current instance's (data/studies/current_best_model/template_2026-10-10/model_frame.parquet), every
season 2013 - 28 Jul 2026 (rows from 29 Jul 2026 are filtered out before the result column is read), debut seasons out.
The price: the frame's odds input (Pinnacle first), margin-free.

Every fit is a logistic regression without an intercept (a symmetric forecast) whose baseline is the close with one free
slope per tour, fitted jointly with the tested term(s) inside the era:
    logit P(A wins) = s_atp L 1[men] + s_wta L 1[women] + beta' x,       L = logit(price)
so beta measures what x knows beyond the best linearly calibrated close of that era. Inputs that are A - B differences
enter as they are; the per-player pairs (surf_season, surf_layoff) as A minus B; men's serve-speed column (stage 2's
spd_L_B) as one more input. Each is scaled by its root mean square in the era (0 = no difference between the players, so
the scaling keeps the symmetry); a missing value is 0. Context inputs cannot move a symmetric forecast alone: they enter
as modifiers of the price's slope (L x indicator), the context family's test.

    inputs    one input at a time: beta (log-odds per RMS unit), its cluster-robust z (four-week blocks), the in-sample
              gain over the era's calibrated close (mLL, + = with the input better) minus its expected overfit 1/(2n)
    families  each family as a block (ratings, schedule and body, box-score form, IOS profile, context slopes, every
              non-price input): the in-sample gain minus k/(2n), and the cross-fitted gain (five folds of four-week
              blocks inside the era, the block ridge-penalised: 5 per coefficient, nearly unpenalised, and 1000, about one
              coefficient's Fisher information, as a sensitivity) with its interval. The cluster-robust Wald test is kept
              only for blocks of at most 5 coefficients: with 20-50 blocks per era a larger block's cluster covariance
              is near-singular (seen on the first run, 12 Oct 2026: absurd and negative chi-squares)
    learning  per input: the recent era's beta against the earlier eras' pooled beta (the difference and its z)
Eras: 2013-16, 2017-19, 2020-22, 2023-24, 2025-26 (to 28 Jul 2026); both tours, men, women.

Writes data/studies/edge_anatomy/scan_inputs.csv, scan_families.csv, scan_learning.csv.
Run: ./python.sh src/eda/edge_anatomy/scan.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402

ERAS = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022), "2023-24": (2023, 2024),
        "2025-26": (2025, 2026)}
PAIRS = {"surf_season": ("surf_season_a", "surf_season_b"), "surf_layoff": ("surf_layoff_a", "surf_layoff_b")}


def load() -> pd.DataFrame:
    names = E.input_names()
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt", "odds_input", "a_won"] + \
        [f"in_{n}" for n in names]
    f = pd.read_parquet(E.INSTANCE / "model_frame.parquet", columns=cols,
                        filters=[("tournament_date", "<", E.SEALED_FROM)])
    if f["tournament_date"].max() >= E.SEALED_FROM:
        raise RuntimeError("a sealed result was read")
    f["match_id"] = f["match_id"].astype(str)
    f = f[~f["debut_season"].astype(bool)].copy()
    sp = pd.read_parquet(E.SPEED, columns=["match_id", "spd_L_B"]).astype({"match_id": str}).set_index("match_id")
    f["in_speed"] = sp["spd_L_B"].reindex(f["match_id"]).to_numpy(float)
    f.loc[f["tour"] == "wta", "in_speed"] = 0.0
    for k, (a, b) in PAIRS.items():
        f[f"in_{k}"] = f[f"in_{a}"] - f[f"in_{b}"]
    f["y"] = f["a_won"].astype(float)
    f["L"] = S.lg(f["p_mkt"])
    f["block"] = SC.blocks(f["tournament_date"].to_numpy(), 28)
    return f.reset_index(drop=True)


def diff_inputs() -> dict[str, str]:
    """Input (as tested) -> its family, the price and context excluded."""
    out = {}
    for fam, members in E.FAMILIES.items():
        if fam in ("price", "context"):
            continue
        for c in members:
            if c.endswith("_a") or c.endswith("_b"):
                stem = c[:-2]
                out[stem] = fam
            else:
                out[c] = fam
    out["speed"] = "stage 2 (speed)"
    return out


def base_cols(g: pd.DataFrame) -> np.ndarray:
    atp = (g["tour"] == "atp").to_numpy()
    L = g["L"].to_numpy()
    cols = []
    if atp.any():
        cols.append(np.where(atp, L, 0.0))
    if (~atp).any():
        cols.append(np.where(~atp, L, 0.0))
    return np.column_stack(cols)


def scaled(g: pd.DataFrame, c: str) -> np.ndarray:
    x = g[f"in_{c}"].to_numpy(float)
    x = np.where(np.isfinite(x), x, 0.0)
    rms = float(np.sqrt(np.mean(x ** 2)))
    return x / rms if rms > 0 else x


def fit_block(B: np.ndarray, X: np.ndarray, y: np.ndarray, blk: np.ndarray) -> dict:
    """Base B alone and B + X: the in-sample gain (mLL, + = with X better, minus k/(2n)), X's coefficients, their
    cluster-robust covariance and Wald chi-square."""
    n, k = len(y), X.shape[1]
    zero = np.zeros(n)
    b0, _ = S.fit_offset(B, y, zero)
    Z = np.column_stack([B, X])
    b1, H1 = S.fit_offset(Z, y, zero)
    ll0 = S.ll(1 / (1 + np.exp(-(B @ b0))), y).mean()
    ll1 = S.ll(1 / (1 + np.exp(-(Z @ b1))), y).mean()
    V = S.cluster_cov(Z, y, zero, b1, H1, blk)[-k:, -k:]
    beta = b1[-k:]
    try:
        w = float(beta @ np.linalg.solve(V, beta))
    except np.linalg.LinAlgError:
        w = np.nan
    return {"gain": 1000 * (ll0 - ll1) - 1000 * k / (2 * n), "gain_raw": 1000 * (ll0 - ll1), "beta": beta,
            "se": np.sqrt(np.clip(np.diag(V), 0, None)), "wald": w, "k": k, "n": n}


FOLDS, RIDGE = 5, 5.0
RIDGE_STRONG = 1000.0       # a sensitivity: near the Fisher information of one coefficient (n p (1 - p))


def crossfit(B: np.ndarray, X: np.ndarray, y: np.ndarray, blk: np.ndarray, ridge: float = RIDGE) -> dict:
    """The block's information beyond the era's calibrated close, cross-fitted inside the era: the four-week blocks are
    dealt into FOLDS folds in calendar order (block k to fold k mod FOLDS); each fold is forecast by the base and by the
    base + X fitted on the other folds (X ridge-penalised, RIDGE per coefficient on RMS-scaled inputs; the price's
    slopes unpenalised). Returns the held-out gain (mLL, + = with X better) with its interval over the blocks."""
    from scipy.special import expit
    ub = np.unique(blk)
    fold = np.searchsorted(ub, blk) % FOLDS
    n = len(y)
    p0, p1 = np.empty(n), np.empty(n)
    Z = np.column_stack([B, X])
    lam = np.r_[np.full(B.shape[1], 1e-8), np.full(X.shape[1], ridge)]
    zero = np.zeros(n)
    for k in range(FOLDS):
        tr, te = fold != k, fold == k
        b0, _ = S.fit_offset(B[tr], y[tr], zero[tr])
        b1, _ = S.fit_offset(Z[tr], y[tr], zero[tr], ridge=lam)
        p0[te] = expit(B[te] @ b0)
        p1[te] = expit(Z[te] @ b1)
    return S.gain(p0, p1, y, blk)


def context_X(g: pd.DataFrame) -> np.ndarray:
    """The price's slope modified by context: L x indicator, one column per non-reference level of each context."""
    L = g["L"].to_numpy()
    cols = []
    for c, ref in (("in_level", 4.0), ("in_surface", 0.0), ("in_best_of", 3.0), ("in_indoor", 0.0)):
        v = g[c].to_numpy()
        for lev in sorted(set(v[np.isfinite(v)])):
            if lev == ref:
                continue
            ind = (v == lev).astype(float)
            if ind.sum() >= 50:
                cols.append(L * ind)
    r = g["in_round"].to_numpy()
    for grp in ((15.0, 16.0, 17.0, 10.0),):
        cols.append(L * np.isin(r, grp).astype(float))
    return np.column_stack(cols)


def run() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    f = load()
    tested = diff_inputs()
    rows_in, rows_fam = [], []
    for era, (a, b) in ERAS.items():
        for tour in ("both", "atp", "wta"):
            g = f[f["season"].between(a, b)]
            if tour != "both":
                g = g[g["tour"] == tour]
            y, blk = g["y"].to_numpy(), g["block"].to_numpy()
            B = base_cols(g)
            for c, fam in tested.items():
                if c == "speed" and tour == "wta":
                    continue
                r = fit_block(B, scaled(g, c)[:, None], y, blk)
                z = float(r["beta"][0] / r["se"][0]) if r["se"][0] > 0 else np.nan
                rows_in.append({"era": era, "tour": tour, "input": c, "family": fam, "n": r["n"],
                                "beta": float(r["beta"][0]), "se": float(r["se"][0]), "z": z, "gain": r["gain"]})
            fams = {fam: [c for c, f2 in tested.items() if f2 == fam] for fam in set(tested.values())}
            fams["every non-price input"] = [c for c in tested if not (c == "speed" and tour == "wta")]
            for fam, members in fams.items():
                members = [c for c in members if not (c == "speed" and tour == "wta")]
                if not members:
                    continue
                X = np.column_stack([scaled(g, c) for c in members])
                r = fit_block(B, X, y, blk)
                cf = crossfit(B, X, y, blk)
                cs = crossfit(B, X, y, blk, RIDGE_STRONG)
                rows_fam.append({"era": era, "tour": tour, "family": fam, "k": r["k"], "n": r["n"],
                                 "gain_corrected": r["gain"], "gain_raw": r["gain_raw"],
                                 **{f"cf_{a}": cf[a] for a in ("est", "lo", "hi", "p_better")},
                                 "cf_verdict": S.verdict(cf),
                                 **{f"cfs_{a}": cs[a] for a in ("est", "lo", "hi", "p_better")},
                                 "cfs_verdict": S.verdict(cs),
                                 "wald_small_k_only": r["wald"] if r["k"] <= 5 else np.nan,
                                 "p_small_k_only": float(chi2.sf(r["wald"], r["k"])) if r["k"] <= 5 else np.nan})
            Xc = context_X(g)
            r = fit_block(B, Xc, y, blk)
            cf = crossfit(B, Xc, y, blk)
            cs = crossfit(B, Xc, y, blk, RIDGE_STRONG)
            rows_fam.append({"era": era, "tour": tour, "family": "context (price slope by context)", "k": r["k"],
                             "n": r["n"], "gain_corrected": r["gain"], "gain_raw": r["gain_raw"],
                             **{f"cf_{a}": cf[a] for a in ("est", "lo", "hi", "p_better")},
                             "cf_verdict": S.verdict(cf),
                             **{f"cfs_{a}": cs[a] for a in ("est", "lo", "hi", "p_better")},
                             "cfs_verdict": S.verdict(cs), "wald_small_k_only": np.nan, "p_small_k_only": np.nan})
            E.log(f"{era} {tour}: {len(g):,} matches")
    ins, fam = pd.DataFrame(rows_in), pd.DataFrame(rows_fam)
    learn = []
    for (tour, c), h in ins.groupby(["tour", "input"]):
        rec = h[h["era"] == "2025-26"]
        old = h[h["era"] != "2025-26"]
        if rec.empty or old.empty:
            continue
        w = 1 / old["se"] ** 2
        b_old = float((w * old["beta"]).sum() / w.sum())
        se_old = float(np.sqrt(1 / w.sum()))
        b_new, se_new = float(rec["beta"].iloc[0]), float(rec["se"].iloc[0])
        learn.append({"tour": tour, "input": c, "family": rec["family"].iloc[0], "beta_2013_24": b_old,
                      "se_2013_24": se_old, "z_2013_24": b_old / se_old, "beta_2025_26": b_new, "se_2025_26": se_new,
                      "z_2025_26": b_new / se_new, "change": b_new - b_old,
                      "z_change": (b_new - b_old) / np.sqrt(se_new ** 2 + se_old ** 2)})
    return ins, fam, pd.DataFrame(learn)


def main() -> int:
    ins, fam, learn = run()
    ins.to_csv(E.OUT / "scan_inputs.csv", index=False)
    fam.to_csv(E.OUT / "scan_families.csv", index=False)
    learn.to_csv(E.OUT / "scan_learning.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    print(fam.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
