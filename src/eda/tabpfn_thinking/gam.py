"""Can a free additive model reproduce the paid fit's gain? (no API call)

The surrogate of TabPFN's adjustment to the price (score.py, "adjustment") is about 96% additive: a smooth curve per
input explains almost all of it, interactions about 2%. If that curvature is where the gain lives, a penalized spline
GAM fitted beside the odds should recover much of it. Per tour, fitted once on the training matches with odds
(2013-2021), scored on the same test matches as TabPFN:

    gam_all       the odds' log-odds and the 47 differences, each through a cubic spline (5 knots on its training
                  quantiles; missing = 0 = no difference), logistic regression with an L2 penalty
    gam_traits    the odds + the 21 IOS offence/defence and product inputs (the group TabPFN leans on most)
    gam_form      the odds + the 16-input two-week profile
    gam_player    the odds + load, surface familiarity and age
Symmetry: fitted on every training match in both orientations without an intercept, forecasts symmetrized. The
penalty is chosen per model and tour from a fixed grid by the log loss on 2020-2021 (fitted on 2013-2019), then the
model is refitted on 2013-2021 with it; nothing is chosen on the test seasons.

Ridge (added after the surrogate showed that about 60% of TabPFN's value for the men is a linear reweighting of the
inputs): a logistic regression without an intercept on the odds' log-odds (unpenalized) and the scaled differences
(L2 penalty lambda, missing = 0), the penalty chosen the same way from RIDGE_GRID:
    ridge_all                the 47 differences
    ridge_everything_profile the 25 differences of the audit's "profile + context" forecast

Writes data/studies/tabpfn_thinking/gam.json.
Run: ./python.sh src/eda/tabpfn_thinking/gam.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import SplineTransformer

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking import score as S  # noqa: E402

GRID = [0.003, 0.01, 0.03, 0.1, 0.3, 1.0]           # inverse penalty C
VALID = (2020, 2021)
MODELS = {"gam_all": T.DIFF, "gam_traits": T.GROUPS["profile_traits"], "gam_form": T.GROUPS["profile_form"],
          "gam_player": T.GROUPS["player"]}


class OddGAM:
    """Splines per input on both orientations; no intercept; L2-penalized logistic regression."""

    def __init__(self, cols: list[str], C: float):
        self.cols, self.C = ["odds_logit"] + cols, C

    def _X(self, F: pd.DataFrame, flip: bool = False) -> np.ndarray:
        X = np.column_stack([F[f"in_{c}"].to_numpy(dtype=float) for c in self.cols])
        X = np.nan_to_num(X / self.sd, nan=0.0)
        return -X if flip else X

    def fit(self, F: pd.DataFrame) -> "OddGAM":
        X = np.column_stack([F[f"in_{c}"].to_numpy(dtype=float) for c in self.cols])
        sd = np.nanstd(X, axis=0)
        self.sd = np.where(sd > 0, sd, 1.0)
        Xa = np.vstack([self._X(F), self._X(F, flip=True)])
        y = F["a_won"].astype(int).to_numpy()
        ya = np.r_[y, 1 - y]
        self.spl = SplineTransformer(n_knots=5, degree=3, knots="quantile", extrapolation="linear").fit(Xa)
        B = np.hstack([Xa, self.spl.transform(Xa)])
        self.lr = LogisticRegression(C=self.C, fit_intercept=False, max_iter=5000, tol=1e-6).fit(B, ya)
        return self

    def predict(self, F: pd.DataFrame) -> np.ndarray:
        out = []
        for flip in (False, True):
            X = self._X(F, flip)
            out.append(self.lr.predict_proba(np.hstack([X, self.spl.transform(X)]))[:, 1])
        return T.symmetrize(out[0], out[1])


RIDGE_GRID = [0.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0]
HALF_LIVES = [None, 1.0, 2.0, 4.0]                  # recency weights 0.5 ** ((last season - year) / half-life)
RIDGE = {"ridge_all": (T.DIFF, "scale", False), "ridge_everything_profile": (T.EVERYTHING + T.PROFILE16, "scale", False),
         "ridge_all_recent": (T.DIFF, "scale", True), "ridge_all_quantile": (T.DIFF, "quantile", False)}


class Transform:
    """Training-only input scaling: 'scale' divides by the standard deviation; 'quantile' maps each difference to a
    normal score through the training distribution of its absolute value, keeping the sign (an odd, monotone,
    outlier-proof transform). Missing = 0 = no difference."""

    def __init__(self, kind: str):
        self.kind = kind

    def fit(self, X: np.ndarray) -> "Transform":
        if self.kind == "scale":
            sd = np.nanstd(X, axis=0)
            self.sd = np.where(sd > 0, sd, 1.0)
        else:
            self.sorted = [np.sort(np.abs(c[np.isfinite(c)])) for c in X.T]
        return self

    def __call__(self, X: np.ndarray) -> np.ndarray:
        from scipy.stats import norm
        if self.kind == "scale":
            return np.nan_to_num(X / self.sd, nan=0.0)
        out = np.zeros_like(X)
        for j, s in enumerate(self.sorted):
            x = X[:, j]
            ok = np.isfinite(x)
            u = (np.searchsorted(s, np.abs(x[ok]), side="right") - 0.5) / max(len(s), 1)
            out[ok, j] = np.sign(x[ok]) * norm.ppf(np.clip(0.5 + 0.5 * u, 0.5, 1 - 1e-6))
        return out


def ridge_fit(F: pd.DataFrame, cols: list[str], lam: float, kind: str = "scale", half_life: float | None = None,
              last: int | None = None):
    """Newton steps for a logistic regression without an intercept, the odds unpenalized, the rest L2-penalized;
    optional recency weights by season."""
    from scipy.special import expit
    X = np.column_stack([F[f"in_{c}"].to_numpy(dtype=float) for c in cols])
    tf = Transform(kind).fit(X)
    Z = np.column_stack([F["in_odds_logit"].to_numpy(dtype=float), tf(X)])
    y = F["a_won"].to_numpy(dtype=float)
    w = np.ones(len(F)) if half_life is None else 0.5 ** ((last - F["year"].to_numpy()) / half_life)
    w = w * len(w) / w.sum()
    pen = np.r_[0.0, np.full(len(cols), lam)] + 1e-8
    beta = np.zeros(Z.shape[1])
    for _ in range(100):
        p = expit(Z @ beta)
        step = np.linalg.solve((Z.T * (w * p * (1 - p))) @ Z + np.diag(pen), Z.T @ (w * (y - p)) - pen * beta)
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return beta, tf


def ridge_predict(F: pd.DataFrame, cols: list[str], beta: np.ndarray, tf: Transform) -> np.ndarray:
    from scipy.special import expit
    X = np.column_stack([F[f"in_{c}"].to_numpy(dtype=float) for c in cols])
    Z = np.column_stack([F["in_odds_logit"].to_numpy(dtype=float), tf(X)])
    return expit(Z @ beta)


def main() -> int:
    fr = pd.read_parquet(T.OUT / "frame.parquet")
    fr = fr[fr["tabpfn_split"].isin(["train", "test"])].reset_index(drop=True)
    f, info = S.load()
    assert info["tabpfn"]
    res = {"grid": GRID, "valid_years": VALID, "chosen": {}, "rows": []}
    for name, cols in MODELS.items():
        p = pd.Series(np.nan, index=fr["match_id"].to_numpy())
        for t in T.TOURS:
            tr = fr[(fr["tabpfn_split"] == "train") & (fr["tour"] == t)]
            te = fr[(fr["tabpfn_split"] == "test") & (fr["tour"] == t)]
            fit_part, val_part = tr[tr["year"] < VALID[0]], tr[tr["year"] >= VALID[0]]
            scores = {}
            for C in GRID:
                g = OddGAM(cols, C).fit(fit_part)
                scores[C] = float(T.ll(g.predict(val_part), val_part["a_won"].to_numpy()).mean())
            best = min(scores, key=scores.get)
            res["chosen"][f"{name}|{t}"] = {"C": best, "valid_ll": scores}
            g = OddGAM(cols, best).fit(tr)
            p.loc[te["match_id"].to_numpy()] = g.predict(te)
            T.log(f"{name} {t}: C {best}")
        f[f"p_{name}"] = f["match_id"].map(p).to_numpy()
    for name, (cols, kind, recent) in RIDGE.items():
        p = pd.Series(np.nan, index=fr["match_id"].to_numpy())
        for t in T.TOURS:
            tr = fr[(fr["tabpfn_split"] == "train") & (fr["tour"] == t)]
            te = fr[(fr["tabpfn_split"] == "test") & (fr["tour"] == t)]
            fit_part, val_part = tr[tr["year"] < VALID[0]], tr[tr["year"] >= VALID[0]]
            scores = {}
            for hl in (HALF_LIVES if recent else [None]):
                for lam in RIDGE_GRID:
                    b, tf = ridge_fit(fit_part, cols, lam, kind, hl, VALID[0] - 1)
                    scores[(lam, hl)] = float(T.ll(ridge_predict(val_part, cols, b, tf),
                                                   val_part["a_won"].to_numpy()).mean())
            lam, hl = min(scores, key=scores.get)
            res["chosen"][f"{name}|{t}"] = {"lambda": lam, "half_life": hl,
                                            "valid_ll": {f"{k[0]}|{k[1]}": v for k, v in scores.items()}}
            b, tf = ridge_fit(tr, cols, lam, kind, hl, T.TRAIN_YEARS[1])
            p.loc[te["match_id"].to_numpy()] = ridge_predict(te, cols, b, tf)
            T.log(f"{name} {t}: lambda {lam}, half-life {hl}")
        f[f"p_{name}"] = f["match_id"].map(p).to_numpy()
    for tname, m in S.subsets(f, with_odds=True):
        for b, mm in [("market", x) for x in list(MODELS) + list(RIDGE)] + \
                     [("lr_mkt_all", "gam_all"), ("gam_all", "tabpfn"), ("lr_mkt_all", "ridge_all")] + \
                     [(x, "tabpfn") for x in RIDGE] + \
                     [(x, "tabpfn") for x in ("gam_traits", "gam_form", "gam_player")]:
            res["rows"].append({"tour": tname, **S.cmp(f, m, b, mm)})
    T.write_json(T.OUT / "gam.json", res)
    for r in res["rows"]:
        T.log(f"{r['tour']:4s} {r['base']:>11s} -> {r['model']:<11s} {r['gain']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] n={r['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
