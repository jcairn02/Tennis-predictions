"""The non-thinking twin of the paid fit: the local open checkpoint (tabpfn-v3.5-20260909) on exactly this study's upload
(build_frame.py: the same 39,918 training rows, 58 inputs and 53,022 query rows), with the paid fit's settings except
thinking (8 estimators, softmax temperature 0.9, pretraining limits ignored, no categorical hints), on the local GPU.
Seeds 0-3; seed 0 mirrors the paid fit's random_state. No API tokens.

One fit at a time on the card (the rating race's wait_for_card: no other process of the local env, 12 GB free). A
finished seed is saved to data/studies/tabpfn_thinking58/local/seed<k>.npz with the upload's fingerprint and never
refitted.

    ./python_tabpfn_local.sh src/eda/tabpfn_thinking58/local_twin.py
"""
from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_rating_race.local_fits import wait_for_card  # noqa: E402
from src.eda.tabpfn_local import runtime  # noqa: E402
from src.eda.tabpfn_thinking58 import common as C  # noqa: E402

CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}


def main() -> int:
    import torch

    X_train, y_train, X_query, _, manifest = C.load_upload()
    C.LOCAL.mkdir(parents=True, exist_ok=True)
    for seed in C.TWIN_SEEDS:
        path = C.LOCAL / f"seed{seed}.npz"
        if path.exists():
            continue
        free_gb = wait_for_card()
        clf = runtime.classifier(**CONFIG, random_state=seed)
        torch.cuda.reset_peak_memory_stats()
        t0 = time.monotonic()
        clf.fit(X_train, y_train)
        proba = clf.predict_proba(X_query)
        secs = time.monotonic() - t0
        if [int(c) for c in clf.classes_] != [0, 1] or proba.shape != (len(X_query), 2) or not np.isfinite(proba).all() \
                or not np.allclose(proba.sum(axis=1), 1.0, atol=1e-6):
            raise RuntimeError(f"{path.name}: invalid probabilities")
        meta = {"seed": seed, "config": {**CONFIG, "random_state": seed}, "input_fingerprint": manifest["input_fingerprint"],
                "train_shape": list(X_train.shape), "query_shape": list(X_query.shape), "seconds": round(secs, 1),
                "gpu_free_gb_before": round(free_gb, 1), "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
        tmp = path.with_name(path.name + ".tmp.npz")
        np.savez(tmp, meta=np.asarray(json.dumps(meta)), p_a=proba[:, 1])
        tmp.replace(path)
        C.log(f"{path.name}: {secs:.0f} s, peak {meta['peak_gpu_gb']} GB")
        del clf
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
