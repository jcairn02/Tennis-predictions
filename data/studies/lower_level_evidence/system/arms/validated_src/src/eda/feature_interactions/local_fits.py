"""Local TabPFN-3.5 fits of this study (GPU, no API tokens; env `tennis-tabpfn-local`, through
src/eda/tabpfn_local/runtime.py), with the rating race's settings: 8 estimators, softmax temperature 0.9, pretraining
limits ignored, seeds 0, 1, 2.

For each arm (arms.py) and walk-forward season Y (training on the main-tour matches with odds of 2013 to Y - 1), one fit
per seed predicts:

    td      every season-Y match, as stored and with A and B swapped (the scorer symmetrises)
    early   arms with the odds, 2025-2026: the matches with Polymarket prices, odds_logit replaced by the price 24 hours
            before the listed start
    late    the same with the price 30 minutes before the listed start

Sharing the card with other sessions. The rating race's runner waits while any other process of the local env exists,
so this runner must not be alive while one of those runs: start it through launch_when_free.sh, which waits until no
local-env process is left. Once running, it waits only for 12 GB of free GPU memory before each fit (a runner started
after it waits for it, so the two never wait on each other).

A finished (arm, season, seed) is saved to data/studies/feature_interactions/local/ with its input fingerprint and never
refitted.
Run: ./python_tabpfn_local.sh src/eda/feature_interactions/local_fits.py --arms model[,...] [--seasons 2014-2024] [--seeds 0-5]
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

from src.eda.feature_interactions import arms as A  # noqa: E402
from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.tabpfn_local import runtime  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

PRICE_SEASONS = (2025, 2026)


def wait_for_memory(need_gb: float = 12.0, patience_s: int = 6 * 3600) -> float:
    import torch
    t0, last_note = time.monotonic(), -1e9
    while True:
        free = torch.cuda.mem_get_info()[0] / 2**30
        if free >= need_gb:
            return free
        if time.monotonic() - t0 > patience_s:
            raise RuntimeError(f"under {need_gb} GB free for {patience_s} s ({free:.1f} GB)")
        if time.monotonic() - last_note > 300:
            C.log(f"waiting for GPU memory: {free:.1f} GB free")
            last_note = time.monotonic()
        time.sleep(20)


def queries(ep: pd.DataFrame, season: int, X_test: pd.DataFrame, ids: np.ndarray) -> dict:
    out = {"td": (pd.concat([X_test, A.flip(X_test)], ignore_index=True), ids)}
    if "odds_logit" in X_test.columns and season in PRICE_SEASONS:
        e = ep.set_index("match_id").reindex(ids)
        ok = e["has_early"].fillna(False).to_numpy(bool)
        for name, col in (("early", "p_early_a"), ("late", "p_close_a")):
            Xq = X_test[ok].reset_index(drop=True).copy()
            Xq["odds_logit"] = logit(np.clip(e[col].to_numpy(dtype=float)[ok], C.EPS, 1 - C.EPS))
            out[name] = (pd.concat([Xq, A.flip(Xq)], ignore_index=True), ids[ok])
    return out


def main() -> int:
    import torch
    args = sys.argv[1:]
    arms = args[args.index("--arms") + 1].split(",")
    lo, hi = (args[args.index("--seasons") + 1].split("-") if "--seasons" in args else ("2014", "2026"))
    seasons = range(int(lo), int(hi) + 1)
    if "--seeds" in args:                    # "0-5" or "3,4,5"
        spec = args[args.index("--seeds") + 1]
        a, _, b = spec.partition("-")
        seeds = tuple(range(int(a), int(b) + 1)) if b else tuple(int(s) for s in spec.split(","))
    else:
        seeds = C.SEEDS
    C.LOCAL.mkdir(parents=True, exist_ok=True)
    extra = sorted({c for a in arms for c in A.arm_inputs(a) if c not in A.base_inputs()[0]})
    frame = A.load_frame(extra)
    ep = pd.read_parquet(C.EARLY, columns=["match_id", "has_early", "p_early_a", "p_close_a"])
    for arm in arms:
        cols = A.arm_inputs(arm)
        if not A.check_flip(frame, cols):
            raise RuntimeError(f"{arm}: flip is not an involution")
        empty = [c for c in cols if not np.isfinite(frame[f"in_{c}"].to_numpy(dtype=float)).any()]
        if empty:
            raise RuntimeError(f"{arm}: inputs without any value: {empty}")
        for season in seasons:
            for seed in seeds:
                path = C.LOCAL / f"{arm}__{season}__seed{seed}.npz"
                if path.exists():
                    continue
                X_train, y_train, X_test, ids = A.job_data(frame, cols, season)
                qs = queries(ep, season, X_test, ids)
                names = list(qs)
                X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
                free_gb = wait_for_memory()
                clf = runtime.classifier(**C.CONFIG, random_state=seed)
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
                meta = {"arm": arm, "season": season, "seed": seed, "config": {**C.CONFIG, "random_state": seed},
                        "train_shape": list(X_train.shape), "query_rows": {n: int(len(qs[n][0])) for n in names},
                        "columns": list(X_train.columns), "fingerprint": T.fingerprint(X_train, y_train, X_query),
                        "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                        "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                        "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                        "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
                tmp = path.with_name(path.name + ".tmp.npz")
                np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
                tmp.replace(path)
                C.log(f"{path.name}: {secs:.0f} s, peak {meta['peak_gpu_gb']} GB, queries {meta['query_rows']}")
                del clf
                torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
