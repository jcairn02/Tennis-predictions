"""When does the market price each statistic? The edge-anatomy study's line-move view (added 12 Oct 2026, after the
first results; process log).

For each of the model's non-price inputs (as scan.py tests them) and BetOnline's two lines on the same matches (the
bet-timing study's frame, data/studies/bet_timing/frame.parquet: the opening line, a median 24-38 hours before the start,
and the last line, both margin-free; matches whose inputs all existed at the opening, both lines coherent):
    beyond the opening   logit P(A wins) = s_tour logit(open) + b_open x        (logistic, no intercept)
    the move             logit(close) - logit(open) = a_tour logit(open) + b_move x   (least squares, no intercept)
    beyond the close     logit P(A wins) = s_tour logit(close) + b_close x      (logistic, no intercept)
x is RMS-scaled in the window (0 = no difference between the players; missing = 0); z-scores are cluster-robust over
four-week blocks. Reading: a statistic the opening line already prices has b_open about 0; one the market learns by the
close has b_open and b_move of the same sign and b_close about 0 (an edge only for early bets); one the close still
misses has b_close away from 0 (an edge at any time). Windows 2020-2024 and 2025 - 28 Jul 2026; men, women. The
results of the sealed holdout are not read (analysis.parquet ends on 28 Jul 2026).

Writes data/studies/edge_anatomy/linemove.csv and linemove_model.csv (the same three fits for the current model's
whole disagreement with the close, as a sanity check: the model saw the close, so its b_move is not an early-bet test).
Run: ./python.sh src/eda/edge_anatomy/linemove.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import scan as SN  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

BT = E.ROOT / "data" / "studies" / "bet_timing" / "frame.parquet"
WINDOWS = {"2020-24": (2020, 2024), "2025-26": (2025, 2026)}


def load() -> pd.DataFrame:
    a = pd.read_parquet(E.OUT / "analysis.parquet")
    a = a[(a["season"] >= 2020) & ~a["debut"]].copy()
    for k, (x, z) in SN.PAIRS.items():
        a[f"in_{k}"] = a[f"in_{x}"] - a[f"in_{z}"]
    a["in_speed"] = np.where(a["tour"] == "wta", 0.0, a["spd"])
    bt = pd.read_parquet(BT, columns=["match_id", "p_bol_open", "p_bol_close", "ok_bol_open", "ok_bol_close",
                                      "known_bol_open", "h_bol_open"]).astype({"match_id": str})
    m = a.merge(bt, on="match_id", how="inner")
    keep = m["ok_bol_open"].astype(bool) & m["ok_bol_close"].astype(bool) & m["known_bol_open"].astype(bool) & \
        np.isfinite(m["p_bol_open"]) & np.isfinite(m["p_bol_close"])
    m = m[keep.to_numpy()].copy()
    m["Lo"] = S.lg(m["p_bol_open"])
    m["Lc"] = S.lg(m["p_bol_close"])
    m["move"] = m["Lc"] - m["Lo"]
    return m.reset_index(drop=True)


def ols_cluster(X: np.ndarray, y: np.ndarray, blk: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    labels, ix = np.unique(blk, return_inverse=True)
    Sg = np.zeros((len(labels), X.shape[1]))
    np.add.at(Sg, ix, X * r[:, None])
    G = len(labels)
    V = G / (G - 1) * XtXi @ (Sg.T @ Sg) @ XtXi
    return b, np.sqrt(np.diag(V))


def tour_cols(g: pd.DataFrame, col: str) -> np.ndarray:
    atp = (g["tour"] == "atp").to_numpy()
    L = g[col].to_numpy()
    if atp.all() or (~atp).all():
        return L[:, None]
    return np.column_stack([np.where(atp, L, 0.0), np.where(~atp, L, 0.0)])


def logit_z(B: np.ndarray, x: np.ndarray, y: np.ndarray, blk: np.ndarray) -> tuple[float, float]:
    Z = np.column_stack([B, x])
    zero = np.zeros(len(y))
    b, H = S.fit_offset(Z, y, zero)
    V = S.cluster_cov(Z, y, zero, b, H, blk)
    return float(b[-1]), float(np.sqrt(V[-1, -1]))


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    m = load()
    tested = SN.diff_inputs()
    rows, model_rows = [], []
    for wname, (lo, hi) in WINDOWS.items():
        for tour in ("atp", "wta"):
            g = m[m["season"].between(lo, hi) & (m["tour"] == tour)]
            y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
            Bo, Bc = tour_cols(g, "Lo"), tour_cols(g, "Lc")
            for c, fam in tested.items():
                if c == "speed" and tour == "wta":
                    continue
                x = SN.scaled(g, c)
                bo, so = logit_z(Bo, x, y, blk)
                bc, sc = logit_z(Bc, x, y, blk)
                bm, sm = ols_cluster(np.column_stack([Bo, x]), g["move"].to_numpy(), blk)
                rows.append({"window": wname, "tour": tour, "input": c, "family": fam, "n": int(len(g)),
                             "b_open": bo, "z_open": bo / so, "b_move": float(bm[-1]), "z_move": float(bm[-1] / sm[-1]),
                             "b_close": bc, "z_close": bc / sc})
            d = S.lg(g["q_full"].to_numpy()) - S.lg(g["q_close"].to_numpy())
            dn = d / np.sqrt(np.mean(d ** 2))
            bo, so = logit_z(Bo, dn, y, blk)
            bc, sc = logit_z(Bc, dn, y, blk)
            bm, sm = ols_cluster(np.column_stack([Bo, dn]), g["move"].to_numpy(), blk)
            model_rows.append({"window": wname, "tour": tour, "n": int(len(g)), "b_open": bo, "z_open": bo / so,
                               "b_move": float(bm[-1]), "z_move": float(bm[-1] / sm[-1]), "b_close": bc,
                               "z_close": bc / sc, "median_hours_open": float(g["h_bol_open"].median())})
            E.log(f"{wname} {tour}: {len(g):,} matches")
    return pd.DataFrame(rows), pd.DataFrame(model_rows)


def main() -> int:
    rows, model_rows = run()
    rows.to_csv(E.OUT / "linemove.csv", index=False)
    model_rows.to_csv(E.OUT / "linemove_model.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 300)
    print(model_rows.round(3).to_string(index=False))
    sel = rows[(rows["z_open"].abs() >= 2) | (rows["z_close"].abs() >= 2) | (rows["z_move"].abs() >= 2.5)]
    print(sel.round(3).sort_values(["window", "tour", "family", "input"]).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
