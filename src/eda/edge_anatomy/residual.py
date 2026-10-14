"""A transparent "built around the close" model, and the training window it learns from (the owner's question of
12 Oct 2026: "Maybe I'm doing it wrong by throwing it in a complex non-linear model with a line that is built across
over a decade?").

The anchored residual model: logit P(A wins) = s_atp L 1[men] + s_wta L 1[women] + gamma' x, L = logit(the frame's
margin-free odds input), x = the 49 non-price inputs as A - B differences (per-player pairs as A minus B), plus men's
serve-speed column, each scaled by its training root mean square (0 = no difference; missing = 0); no intercept, so the
forecast is symmetric. The price's slopes are unpenalised; gamma is ridge-penalised with lambda chosen inside the
training window (fitted on the window without its last season, validated on that season, from 10, 100, 1000, 10000; then
refitted on the whole window). For test season Y (2020-2026; 2026 to 28 Jul) the windows are:
    expanding   2013 .. Y - 1, equal weights (the current model's window)
    last4       Y - 4 .. Y - 1
    last2       Y - 2 .. Y - 1
    decay2      2013 .. Y - 1, each season weighted 0.5 ** (age / 2) (a two-season half-life)
Scored against the recalibrated close (analysis.parquet's q_close) and against the current model (q_full, both stages)
on the same matches, debut seasons out; mLL, + = the named forecast better; four-week-block intervals.

Writes data/studies/edge_anatomy/residual_scores.csv, residual_forecasts.parquet and residual_lambdas.csv.
Run: ./python.sh src/eda/edge_anatomy/residual.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import scan as SN  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

TEST = tuple(range(2020, 2027))
LAMBDAS = (10.0, 100.0, 1000.0, 10000.0)
WINDOWS = ("expanding", "last4", "last2", "decay2")


def features(f: pd.DataFrame) -> list[str]:
    return list(SN.diff_inputs())


def matrix(g: pd.DataFrame, cols: list[str], rms: dict[str, float]) -> np.ndarray:
    X = []
    for c in cols:
        x = g[f"in_{c}"].to_numpy(float)
        x = np.where(np.isfinite(x), x, 0.0)
        X.append(x / rms[c] if rms[c] > 0 else x)
    return np.column_stack(X)


def base(g: pd.DataFrame) -> np.ndarray:
    atp = (g["tour"] == "atp").to_numpy()
    L = g["L"].to_numpy()
    return np.column_stack([np.where(atp, L, 0.0), np.where(~atp, L, 0.0)])


def fit_weighted(Z: np.ndarray, y: np.ndarray, w: np.ndarray, lam: np.ndarray, iters: int = 100) -> np.ndarray:
    b = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = expit(Z @ b)
        g = Z.T @ (w * (y - p)) - lam * b
        H = (Z.T * (w * p * (1 - p))) @ Z + np.diag(lam)
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        b += step
        if np.abs(step).max() < 1e-10:
            break
    return b


def window_rows(f: pd.DataFrame, Y: int, window: str) -> tuple[np.ndarray, np.ndarray]:
    s = f["season"].to_numpy()
    if window == "expanding":
        m = s <= Y - 1
        w = np.ones(m.sum())
    elif window == "last4":
        m = (s >= Y - 4) & (s <= Y - 1)
        w = np.ones(m.sum())
    elif window == "last2":
        m = (s >= Y - 2) & (s <= Y - 1)
        w = np.ones(m.sum())
    elif window == "decay2":
        m = s <= Y - 1
        w = 0.5 ** ((Y - 1 - s[m]) / 2.0)
    else:
        raise ValueError(window)
    return m, w


def fit_window(f: pd.DataFrame, Y: int, window: str, cols: list[str]) -> tuple[np.ndarray, dict, float]:
    m, w = window_rows(f, Y, window)
    tr = f[m]
    rms = {c: float(np.sqrt(np.mean(np.where(np.isfinite(tr[f"in_{c}"]), tr[f"in_{c}"], 0.0) ** 2))) for c in cols}
    Z = np.column_stack([base(tr), matrix(tr, cols, rms)])
    y = tr["y"].to_numpy(float)
    last = tr["season"].to_numpy() == tr["season"].max()
    best, best_ll = None, np.inf
    for lam in LAMBDAS:
        pen = np.r_[1e-8, 1e-8, np.full(len(cols), lam)]
        b = fit_weighted(Z[~last], y[~last], w[~last], pen)
        v = float(S.ll(expit(Z[last] @ b), y[last]).mean())
        if v < best_ll:
            best, best_ll = lam, v
    pen = np.r_[1e-8, 1e-8, np.full(len(cols), best)]
    return fit_weighted(Z, y, w, pen), rms, best


def run() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    f = SN.load()
    cols = features(f)
    a = pd.read_parquet(E.OUT / "analysis.parquet").set_index("match_id")
    preds, lams = [], []
    for Y in TEST:
        te = f[f["season"] == Y]
        for window in WINDOWS:
            b, rms, lam = fit_window(f, Y, window, cols)
            q = expit(np.column_stack([base(te), matrix(te, cols, rms)]) @ b)
            preds.append(pd.DataFrame({"match_id": te["match_id"].to_numpy(), "window": window, "q": q}))
            lams.append({"season": Y, "window": window, "lambda": lam, "s_atp": float(b[0]), "s_wta": float(b[1])})
            E.log(f"{Y} {window}: lambda {lam:g}")
    P = pd.concat(preds).pivot(index="match_id", columns="window", values="q")
    P = P.join(a[["season", "tour", "y", "block", "debut", "q_close", "q_full"]], how="inner")
    P = P[~P["debut"]]
    rows = []
    for label, seasons in (("2025-26", (2025, 2026)), ("2020-24", (2020, 2021, 2022, 2023, 2024)),
                           *((str(Y), (Y,)) for Y in TEST)):
        for tour in ("both", "atp", "wta"):
            g = P[P["season"].isin(seasons)]
            if tour != "both":
                g = g[g["tour"] == tour]
            y, blk = g["y"].to_numpy(), g["block"].to_numpy()
            for window in WINDOWS:
                v1 = S.gain(g["q_close"], g[window], y, blk)
                v2 = S.gain(g["q_full"], g[window], y, blk)
                rows.append({"seasons": label, "tour": tour, "window": window, "n": int(len(g)),
                             **{f"vs_close_{k}": v1[k] for k in ("est", "lo", "hi", "p_better")},
                             "vs_close_verdict": S.verdict(v1),
                             **{f"vs_model_{k}": v2[k] for k in ("est", "lo", "hi", "p_better")},
                             "vs_model_verdict": S.verdict(v2)})
            v = S.gain(g["q_close"], g["q_full"], y, blk)
            rows.append({"seasons": label, "tour": tour, "window": "the current model (both stages)",
                         "n": int(len(g)), **{f"vs_close_{k}": v[k] for k in ("est", "lo", "hi", "p_better")},
                         "vs_close_verdict": S.verdict(v)})
    return pd.DataFrame(rows), P.reset_index(), pd.DataFrame(lams)


def main() -> int:
    scores, P, lams = run()
    scores.to_csv(E.OUT / "residual_scores.csv", index=False)
    P.to_parquet(E.OUT / "residual_forecasts.parquet", index=False)
    lams.to_csv(E.OUT / "residual_lambdas.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    sub = scores[scores["seasons"].isin(["2025-26", "2020-24"])]
    print(sub[["seasons", "tour", "window", "n", "vs_close_est", "vs_close_lo", "vs_close_hi", "vs_close_verdict",
               "vs_model_est", "vs_model_lo", "vs_model_hi", "vs_model_verdict"]].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
