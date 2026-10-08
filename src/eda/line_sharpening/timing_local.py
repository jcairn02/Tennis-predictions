"""Line sharpening, step 5b: the current best model's forecasts at the early market and at the close (local TabPFN-3.5,
GPU, no API tokens; the `tennis-tabpfn-local` env through src/eda/tabpfn_local/runtime.py).

The current best (docs/studies/meta_stack/README.md) is the local TabPFN-3.5 on the closing odds plus 53 inputs: the
surface-Elo study's `base` arm, trained on the main-tour matches with odds of 2013-2025, 8 estimators, softmax
temperature 0.9, seeds 0, 1, 2 (src/eda/surface_elo_pieces/early_price_local.py, whose settings are copied). Its 2026
matches are queried four times, every query as stored and then with A and B swapped:

    td        the frame as stored (tennis-data closing odds): the check against the earlier fits
    early1c   odds_logit replaced by the Polymarket price at the early market ($300 within 1c; timing_frame.py)
    early2c   the same at the looser early market ($300 within 2c)
    close     the same at the main close

One fit at a time; a finished seed is saved to data/studies/line_sharpening/local/ and never refitted.
Run: ./python_tabpfn_local.sh src/eda/line_sharpening/timing_local.py
"""
from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import arms as A  # noqa: E402
from src.eda.surface_elo_pieces import build_frames as BF  # noqa: E402
from src.eda.surface_elo_pieces import common as SC  # noqa: E402
from src.eda.tabpfn_local import runtime  # noqa: E402

OUT = ROOT / "data" / "studies" / "line_sharpening"
LOCAL = OUT / "local"
SEASON, ARM, SEEDS = 2026, "base", (0, 1, 2)
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}
QUERIES = ("early1c", "early2c", "close")
EPS = 1e-6


def queries(frame: pd.DataFrame, tf: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, np.ndarray]]:
    te = (frame["season"] == SEASON).to_numpy()
    X = BF.matrix(frame, ARM)[te].reset_index(drop=True)
    ids = frame.loc[te, "match_id"].to_numpy()
    out = {"td": (pd.concat([X, A.flip(X)], ignore_index=True), ids)}
    t = tf.set_index("match_id").reindex(ids)
    for name in QUERIES:
        p = t[f"p_{name}"].to_numpy(dtype=float)
        ok = np.isfinite(p)
        Xq = X[ok].reset_index(drop=True).copy()
        Xq["odds_logit"] = logit(np.clip(p[ok], EPS, 1 - EPS))
        out[name] = (pd.concat([Xq, A.flip(Xq)], ignore_index=True), ids[ok])
    return out


def main() -> int:
    import torch
    LOCAL.mkdir(parents=True, exist_ok=True)
    frame = pd.read_parquet(SC.OUT / "frame.parquet")
    tf = pd.read_parquet(OUT / "timing_frame.parquet", columns=["match_id"] + [f"p_{q}" for q in QUERIES])
    for seed in SEEDS:
        path = LOCAL / f"{ARM}__{SEASON}__seed{seed}.npz"
        if path.exists():
            print(f"{path.name}: saved, skipped", flush=True)
            continue
        X_train, y_train, _, _ = BF.job_data(frame, ARM, SEASON)
        qs = queries(frame, tf)
        names = list(qs)
        X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
        clf = runtime.classifier(**CONFIG, random_state=seed)
        torch.cuda.reset_peak_memory_stats()
        t0 = time.monotonic()
        clf.fit(X_train, y_train)
        proba = clf.predict_proba(X_query)
        secs = time.monotonic() - t0
        if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
            raise RuntimeError(f"{path.name}: invalid probabilities")
        p = proba[:, 1]
        payload, start = {}, 0
        for n in names:
            k = len(qs[n][0])
            payload[f"p_{n}"] = p[start:start + k]
            payload[f"ids_{n}"] = qs[n][1].astype(str)
            start += k
        meta = {"arm": ARM, "season": SEASON, "seed": seed, "config": {**CONFIG, "random_state": seed},
                "train_shape": list(X_train.shape), "query_rows": {n: int(len(qs[n][0])) for n in names},
                "columns": list(X_train.columns), "seconds": round(secs, 1),
                "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                "device": torch.cuda.get_device_name(0)}
        tmp = path.with_name(path.name + ".tmp.npz")
        np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
        tmp.replace(path)
        print(f"{path.name}: {secs:.0f} s, peak {meta['peak_gpu_gb']} GB, queries {meta['query_rows']}", flush=True)
        del clf
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
