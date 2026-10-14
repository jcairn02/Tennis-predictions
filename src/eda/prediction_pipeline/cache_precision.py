"""Why TabPFN's cached mode priced differently, and whether it can price exactly (docs/studies/prediction_pipeline/).

The daily-update study (docs/studies/daily_update_speed/, bet_time_pricing.py) found fit_mode="fit_with_cache" prices a
match in about 1 s instead of 41 s, but up to 0.179 away from the decided path. TabPFN 9.1.0's own documentation
(classifier.py, kv_cache_precision): None, the default, "picks the architecture default ('int8' when it can quantize,
e.g. TabPFN-3)": the cached keys and values of the 62,869 training rows are quantized to 8 bits. The hypothesis, fixed
before this run: with kv_cache_precision="auto" (the computed dtype kept) the cached path gives the decided path's
numbers (to the batch noise the same study measured, 3.7e-5).

On the current instance (template_2026-10-10), season 2026's model, seed 0, the decided configuration, the 23 matches
of the 10 Oct replay, symmetrised (stored and swapped rows in one call):
    A        the decided path: fit, predict
    C_int8   fit_with_cache with the default precision (the earlier study's C), for the record
    C_auto   fit_with_cache, kv_cache_precision "auto"; predictions timed; and the 91-price grid of each match in one call
No outcome is scored. GPU, one seed; waits for the card as every runner does.
Writes data/studies/prediction_pipeline/cache_precision.json.
Run: ./python_tabpfn_local.sh src/eda/prediction_pipeline/cache_precision.py
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
OUT = ROOT / "data" / "studies" / "prediction_pipeline" / "cache_precision.json"
SEASON, SEED = 2026, 0
GRID = np.linspace(logit(0.05), logit(0.95), 91)


def predict(clf, X: pd.DataFrame, P) -> tuple[np.ndarray, float]:
    import torch
    k = len(X)
    t0 = time.monotonic()
    p = clf.predict_proba(pd.concat([X, A.flip(X, P)], ignore_index=True))[:, 1]
    torch.cuda.synchronize()
    return C.symmetrize(p[:k], p[k:]), time.monotonic() - t0


def main() -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    P = FITS.paths(INSTANCE)
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    X_train, y_train, X_test, ids = A.job_data(frame, cols, SEASON)
    live = set(pd.read_parquet(REPLAY / "live_meta.parquet")["match_id"].astype(str))
    pick = np.isin(ids.astype(str), list(live))
    Xq = X_test[pick].reset_index(drop=True)
    out: dict = {"instance": str(INSTANCE.relative_to(ROOT)), "season": SEASON, "seed": SEED, "config": C.CONFIG,
                 "train_rows": int(len(X_train)), "matches": int(len(Xq)),
                 "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                 "hypothesis": "kv_cache_precision None = int8 for TabPFN-3; 'auto' keeps the computed dtype and "
                               "should equal the decided path to about 1e-4"}
    out["gpu_free_gb_before"] = round(TWF.wait_for_card(patience_s=1800, processes=True), 1)

    clf = runtime.classifier(**C.CONFIG, random_state=SEED)
    t0 = time.monotonic()
    clf.fit(X_train, y_train)
    pA, tA = predict(clf, Xq, P)
    out["A"] = {"fit_s": round(time.monotonic() - t0 - tA, 2), "predict_s": round(tA, 2)}
    del clf
    torch.cuda.empty_cache()

    for name, prec in (("C_int8", None), ("C_auto", "auto")):
        torch.cuda.reset_peak_memory_stats()
        rec: dict = {"kv_cache_precision": prec}
        try:
            clf = runtime.classifier(**C.CONFIG, random_state=SEED, fit_mode="fit_with_cache", kv_cache_precision=prec)
            t1 = time.monotonic()
            clf.fit(X_train, y_train)
            rec["fit_s"] = round(time.monotonic() - t1, 2)
            pC, tC = predict(clf, Xq, P)
            pC2, tC2 = predict(clf, Xq, P)
            rec.update({"predict_s": [round(tC, 3), round(tC2, 3)],
                        "max_abs_diff_vs_A": float(np.max(np.abs(pC - pA))),
                        "mean_abs_diff_vs_A": float(np.mean(np.abs(pC - pA))),
                        "repeat_max_abs_diff": float(np.max(np.abs(pC2 - pC)))})
            if name == "C_auto":
                rows = Xq.loc[Xq.index.repeat(len(GRID))].reset_index(drop=True)
                rows["odds_logit"] = np.tile(GRID, len(Xq))
                pg, tg = predict(clf, rows, P)
                pg = pg.reshape(len(Xq), len(GRID))
                own = Xq["odds_logit"].to_numpy(dtype=float)
                back = np.array([expit(np.interp(own[i], GRID, logit(pg[i]))) for i in range(len(Xq))])
                steps = np.diff(pg, axis=1)
                rec["price_grid"] = {"prices": len(GRID), "rows": int(len(rows) * 2), "predict_s": round(tg, 2),
                                     "interpolated_at_own_price_max_abs_diff_vs_A": float(np.max(np.abs(back - pA))),
                                     "falling_steps": int((steps < 0).sum()), "steps": int(steps.size)}
            rec["peak_gpu_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
            del clf
        except Exception as e:                          # e.g. out of memory: recorded, not fatal
            rec["error"] = f"{type(e).__name__}: {e}"[:500]
        torch.cuda.empty_cache()
        out[name] = rec
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
