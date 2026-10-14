"""Run the surface-IOS study's TabPFN fits LOCALLY: the open-weight TabPFN-3.5 checkpoint (tabpfn-v3.5-20260909) on
this machine's GPU, no API tokens (the owner raised concern about API costs on 6 Oct 2026, relayed by another session,
which added that the offline model could be used instead; no rule is recorded, so paid calls are left for the owner to
approve).

Every slot of the locked plan (plan.py: arm x seed x test season) gets one fit and one prediction, from the uploads that
dispatch.py --prepare wrote and fingerprinted. The settings are the paid fits' (8 estimators, softmax temperature 0.9,
the slot's seed, pretraining limits ignored, no categorical hints); src/eda/tabpfn_local/runtime.py adds the checkpoint,
the GPU, memory_saving_mode and the attention fix. Each slot's probabilities are saved with the slot's fingerprint, so a
rerun skips finished slots and a changed upload is refused.

    ./python_tabpfn_local.sh src/eda/surface_ios/run_local.py [--slots a,b,...]

Writes data/studies/surface_ios/local/<slot>.npz and local/runs.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import plan as PL  # noqa: E402
from src.eda.surface_ios.dispatch import UPLOADS, load_slot  # noqa: E402

LOCAL = C.OUT / "local"
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}


def wait_for_gpu(need_gb: float = 12.0, patience_s: int = 3600) -> float:
    """Other sessions may run local fits on the same card (each process is capped at 85%, not the card): wait until
    ``need_gb`` is free, at most ``patience_s`` seconds. Returns the free memory in GB."""
    import torch

    t0 = time.monotonic()
    while True:
        free, _ = torch.cuda.mem_get_info()
        if free / 2**30 >= need_gb:
            return free / 2**30
        if time.monotonic() - t0 > patience_s:
            raise RuntimeError(f"only {free / 2**30:.1f} GB free on the GPU after {patience_s} s")
        C.log(f"waiting for GPU memory: {free / 2**30:.1f} GB free")
        time.sleep(30)


def fit_predict(X_train: pd.DataFrame, y: np.ndarray, X_query: pd.DataFrame, seed: int) -> tuple[np.ndarray, dict]:
    import gc

    import torch

    from src.eda.tabpfn_local import runtime

    free_gb = wait_for_gpu()
    clf = runtime.classifier(**CONFIG, random_state=int(seed))
    torch.cuda.reset_peak_memory_stats()
    t0 = time.monotonic()
    clf.fit(X_train, y)
    proba = clf.predict_proba(X_query)
    secs = time.monotonic() - t0
    if [int(c) for c in clf.classes_] != [0, 1] or proba.shape != (len(X_query), 2) or not np.isfinite(proba).all() \
            or not np.allclose(proba.sum(axis=1), 1.0, atol=1e-6):
        raise RuntimeError("invalid probabilities")
    run = {"checkpoint": str(clf.model_path), "config": {**CONFIG, "random_state": int(seed)},
           "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
           "fit_predict_seconds": round(secs, 1), "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
           "gpu_free_gb_before": round(free_gb, 1)}
    del clf
    gc.collect()
    torch.cuda.empty_cache()
    return proba[:, 1], run


def fit_predict_by_surface(X_train: pd.DataFrame, y: np.ndarray, X_query: pd.DataFrame,
                           seed: int) -> tuple[np.ndarray, dict]:
    """One sub-model per surface group (plan.SURFACE_GROUPS on the model's surface column), each trained on that
    surface's training matches only and predicting that surface's query rows; the predictions are stitched back in the
    query's order."""
    p_a = np.full(len(X_query), np.nan)
    runs = {}
    for name, codes in PL.SURFACE_GROUPS.items():
        tr = X_train["surface"].isin(codes).to_numpy()
        q = X_query["surface"].isin(codes).to_numpy()
        if not q.any():
            continue
        p, run = fit_predict(X_train[tr].reset_index(drop=True), y[tr], X_query[q].reset_index(drop=True), seed)
        p_a[q] = p
        runs[name] = {**run, "train_rows": int(tr.sum()), "query_rows": int(q.sum())}
    if np.isnan(p_a).any():
        raise RuntimeError("a query row's surface has no sub-model")
    return p_a, {"by_surface": runs,
                 "fit_predict_seconds": round(sum(r["fit_predict_seconds"] for r in runs.values()), 1),
                 "peak_vram_gb": max(r["peak_vram_gb"] for r in runs.values())}


def load_local(slot: str, fingerprint: str, n_rows: int) -> np.ndarray:
    with np.load(LOCAL / f"{slot}.npz", allow_pickle=False) as z:
        if str(z["input_fingerprint"]) != fingerprint:
            raise RuntimeError(f"{slot}: saved predictions belong to another upload")
        p = z["p_a"]
    if len(p) != n_rows:
        raise RuntimeError(f"{slot}: saved predictions have the wrong length")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", default="")
    ap.add_argument("--phase", default="", help="validation or test: only that phase's slots")
    ap.add_argument("--arms", default="", help="comma-separated arms: only those arms' slots")
    a = ap.parse_args()
    manifest = json.loads((UPLOADS / "manifest.json").read_text(encoding="utf-8"))
    if manifest["plan_sha256"] != PL.plan_hash():
        raise RuntimeError("the plan changed after the uploads were prepared; rerun dispatch.py --prepare")
    slots = [s for s in a.slots.split(",") if s] or list(manifest["slots"])
    if a.phase:
        slots = [s for s in slots if manifest["slots"][s]["phase"] == a.phase]
    if a.arms:
        keep = set(a.arms.split(","))
        slots = [s for s in slots if manifest["slots"][s]["arm"] in keep]
    LOCAL.mkdir(parents=True, exist_ok=True)
    for slot in slots:
        out = LOCAL / f"{slot}.npz"
        m = manifest["slots"][slot]
        if out.exists():
            load_local(slot, m["input_fingerprint"], m["query_rows"])
            C.log(f"{slot}: saved, skipped")
            continue
        X_train, y, X_query, m = load_slot(slot, manifest)
        if PL.ARMS[m["arm"]].get("by_surface"):
            p_a, run = fit_predict_by_surface(X_train, y.astype("int64"), X_query, m["seed"])
        else:
            p_a, run = fit_predict(X_train, y.astype("int64"), X_query, m["seed"])
        np.savez(out, p_a=p_a, input_fingerprint=np.asarray(m["input_fingerprint"]), slot=np.asarray(slot))
        rec = {"slot": slot, **run, "train_shape": list(X_train.shape), "query_shape": list(X_query.shape),
               "input_fingerprint": m["input_fingerprint"],
               "finished_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
        with (LOCAL / "runs.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        C.log(f"{slot}: {run['fit_predict_seconds']} s, peak {run['peak_vram_gb']} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
