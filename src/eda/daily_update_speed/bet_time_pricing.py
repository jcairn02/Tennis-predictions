"""Bet-time pricing speed (docs/studies/daily_update_speed/): how fast the current best model prices a match once its 56
non-price inputs are built, and whether the faster ways give the same numbers. No outcome is scored.

On the current instance (data/studies/current_best_model/template_2026-10-10/), season 2026's model (trained on
2013-2025), seed 0, the decided configuration (serve_speed_tabpfn/common.CONFIG), the 23 matches of the 10 Oct replay
(stored and flipped rows, symmetrised as the stored forecasts are):
    A  as the fits run today: fit, then predict the 23 matches; and a second prediction with the same fitted object
    B  the stored forecast of the same fit (fits/model__2026__seed0.npz, predicted inside the whole season's batch)
    C  fit_mode "fit_with_cache": the training set's keys and values kept; then predictions alone, timed
    D  a price grid: each match's odds input over 91 prices (implied 5% to 95%) in one call; the curve read back at the
       match's own price (linear interpolation in log-odds) against A; whether P(A wins) rises with the price
    --grid-plain (after the first run found C's numbers far from A's): only A and the price grid on the plain fit (E),
       written to bet_time_pricing_grid_plain.json
Writes data/studies/daily_update_speed/bet_time_pricing.json. GPU; one seed (the decided model averages 16).
Run: ./python_tabpfn_local.sh src/eda/daily_update_speed/bet_time_pricing.py [--grid-plain]
"""
from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.model_rebuild import fits as FITS  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.training_window import fits as TWF  # noqa: E402

INSTANCE = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10"
REPLAY = ROOT / "data" / "studies" / "prediction_run" / "replay_2026-10-10_layer"
OUT = ROOT / "data" / "studies" / "daily_update_speed" / "bet_time_pricing.json"
SEASON, SEED = 2026, 0
GRID = np.linspace(logit(0.05), logit(0.95), 91)


def predict(clf, X: pd.DataFrame, P) -> tuple[np.ndarray, float]:
    """Symmetrised P(A wins) of X's matches (stored and flipped rows in one call) and the seconds it took."""
    import torch
    k = len(X)
    t0 = time.monotonic()
    p = clf.predict_proba(pd.concat([X, A.flip(X, P)], ignore_index=True))[:, 1]
    torch.cuda.synchronize()
    return C.symmetrize(p[:k], p[k:]), time.monotonic() - t0


def grid_rows(Xq: pd.DataFrame) -> pd.DataFrame:
    rows = Xq.loc[Xq.index.repeat(len(GRID))].reset_index(drop=True)
    rows["odds_logit"] = np.tile(GRID, len(Xq))
    return rows


def grid_summary(pg: np.ndarray, Xq: pd.DataFrame, pA: np.ndarray) -> dict:
    """The curves read back at each match's own price, and their shape."""
    own = Xq["odds_logit"].to_numpy(dtype=float)
    back = np.array([expit(np.interp(own[i], GRID, logit(pg[i]))) for i in range(len(Xq))])
    steps = np.diff(pg, axis=1)
    return {"interpolated_at_own_price_max_abs_diff_vs_A": float(np.max(np.abs(back - pA))),
            "own_price_inside_grid": int(((own >= GRID[0]) & (own <= GRID[-1])).sum()),
            "falling_steps": int((steps < 0).sum()), "steps": int(steps.size),
            "largest_fall": float(-steps.min()) if (steps < 0).any() else 0.0,
            "largest_step": float(np.max(np.abs(steps)))}


def grid_plain() -> int:
    """A, then the price grid on the same plain fit (no cache): the decided inference path."""
    import torch

    from src.eda.tabpfn_local import runtime
    P = FITS.paths(INSTANCE)
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    X_train, y_train, X_test, ids = A.job_data(frame, cols, SEASON)
    live = set(pd.read_parquet(REPLAY / "live_meta.parquet")["match_id"].astype(str))
    pick = np.isin(ids.astype(str), list(live))
    Xq = X_test[pick].reset_index(drop=True)
    out: dict = {"season": SEASON, "seed": SEED, "train_rows": int(len(X_train)), "matches": int(len(Xq)),
                 "gpu_free_gb_before": round(TWF.wait_for_card(patience_s=1800, processes=True), 1)}
    clf = runtime.classifier(**C.CONFIG, random_state=SEED)
    clf.fit(X_train, y_train)
    pA, t_pred = predict(clf, Xq, P)
    rows = grid_rows(Xq)
    pg, t_grid = predict(clf, rows, P)
    out["A_predict_s"] = round(t_pred, 2)
    out["E_price_grid_plain"] = {"prices": len(GRID), "rows": int(len(rows) * 2), "predict_s": round(t_grid, 2),
                                 **grid_summary(pg.reshape(len(Xq), len(GRID)), Xq, pA)}
    path = OUT.with_name("bet_time_pricing_grid_plain.json")
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


def main() -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    if "--grid-plain" in sys.argv[1:]:
        return grid_plain()
    P = FITS.paths(INSTANCE)
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    X_train, y_train, X_test, ids = A.job_data(frame, cols, SEASON)
    live = set(pd.read_parquet(REPLAY / "live_meta.parquet")["match_id"].astype(str))
    pick = np.isin(ids.astype(str), list(live))
    Xq, qids = X_test[pick].reset_index(drop=True), ids[pick].astype(str)
    out: dict = {"instance": str(INSTANCE.relative_to(ROOT)), "season": SEASON, "seed": SEED, "config": C.CONFIG,
                 "train_rows": int(len(X_train)), "inputs": len(cols), "matches": int(len(Xq)),
                 "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                 "device": torch.cuda.get_device_name(0)}
    out["gpu_free_gb_before"] = round(TWF.wait_for_card(patience_s=1800, processes=True), 1)

    # A: as today
    clf = runtime.classifier(**C.CONFIG, random_state=SEED)
    t0 = time.monotonic()
    clf.fit(X_train, y_train)
    t_fit = time.monotonic() - t0
    pA, t_pred = predict(clf, Xq, P)
    pA2, t_pred2 = predict(clf, Xq, P)
    out["A_today"] = {"fit_s": round(t_fit, 2), "predict_s": round(t_pred, 2), "second_predict_s": round(t_pred2, 2),
                      "second_predict_max_abs_diff": float(np.max(np.abs(pA2 - pA)))}

    # B: the stored forecast (the same fit, predicted inside the season's whole batch)
    with np.load(INSTANCE / "fits" / f"model__{SEASON}__seed{SEED}.npz", allow_pickle=False) as z:
        p_td, ids_td = z["p_td"], z["ids_td"].astype(str)
    K = len(ids_td)
    stored = pd.Series(C.symmetrize(p_td[:K], p_td[K:]), index=ids_td).reindex(qids).to_numpy()
    out["B_stored_vs_A_max_abs_diff"] = float(np.max(np.abs(stored - pA)))
    del clf
    torch.cuda.empty_cache()

    # C: the training set cached
    clf_c, pC = None, None
    try:
        torch.cuda.reset_peak_memory_stats()
        clf_c = runtime.classifier(**C.CONFIG, random_state=SEED, fit_mode="fit_with_cache")
        t0 = time.monotonic()
        clf_c.fit(X_train, y_train)
        torch.cuda.synchronize()
        t_fit_c = time.monotonic() - t0
        times = []
        for _ in range(3):
            pC, t = predict(clf_c, Xq, P)
            times.append(round(t, 3))
        _, t_one = predict(clf_c, Xq.iloc[:1].reset_index(drop=True), P)
        out["C_cached"] = {"fit_s": round(t_fit_c, 2), "predict_23_s": times, "predict_1_s": round(t_one, 3),
                           "max_abs_diff_vs_A": float(np.max(np.abs(pC - pA))),
                           "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)}
    except Exception as e:                       # noqa: BLE001  (recorded: the cache may not fit or may not apply)
        out["C_cached"] = {"error": f"{type(e).__name__}: {e}"[:2000]}
        clf_c = None
        torch.cuda.empty_cache()

    # D: the price grid (on the cached model when it worked, else a plain fit)
    model = clf_c
    if model is None:
        model = runtime.classifier(**C.CONFIG, random_state=SEED)
        model.fit(X_train, y_train)
    rows = Xq.loc[Xq.index.repeat(len(GRID))].reset_index(drop=True)
    rows["odds_logit"] = np.tile(GRID, len(Xq))
    pg, t_grid = predict(model, rows, P)
    pg = pg.reshape(len(Xq), len(GRID))
    own = Xq["odds_logit"].to_numpy(dtype=float)
    back = np.array([expit(np.interp(own[i], GRID, logit(pg[i]))) for i in range(len(Xq))])
    steps = np.diff(pg, axis=1)
    out["D_price_grid"] = {"prices": len(GRID), "rows": int(len(rows) * 2), "predict_s": round(t_grid, 2),
                           "on": "cached" if clf_c is not None else "plain fit",
                           "interpolated_at_own_price_max_abs_diff_vs_A": float(np.max(np.abs(back - pA))),
                           "own_price_inside_grid": int(((own >= GRID[0]) & (own <= GRID[-1])).sum()),
                           "falling_steps": int((steps < 0).sum()), "steps": int(steps.size),
                           "largest_step": float(np.max(np.abs(steps)))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
