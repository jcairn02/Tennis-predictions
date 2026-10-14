"""Local TabPFN-3.5 fits of the centred arm, after one reproduction fit of the base (gate G4).

The fits are the serve-speed study's runner (src/eda/serve_speed_tabpfn/local_fits.py: its frame, flip, expanding-window
job data, query blocks td / early / late, settings and memory wait), unchanged except for the frame it reads:

    repro   "model" 2025 seed 0 on the model frame (surface_rating_race/model/model_frame.parquet). It must equal the rating
            race's stored fit (data/studies/surface_rating_race/local/model__2025__seed0.npz) within 1e-6 in every block
            (G4), or nothing else is fitted
    cprod   the same 58 inputs on arm_frame.parquet (products.py: the 7 products centred, every other column identical),
            seasons 2019-2026, seeds 0-3, trained on 2013 .. Y - 1

The base arm's own forecasts are the stored ones (seeds 0-2 the rating race's, 3 feature interactions'), as the serve-
speed study reuses them. Fits are written to data/studies/ios_product_centring/local/ (the reproduction to local/repro/)
and never refitted. Refuses to start unless gates G1, G2 and G6 passed.
Run: ./python_tabpfn_local.sh src/eda/ios_product_centring/fits.py [--seasons 2019-2026] [--seeds 0,1,2,3]
     (--repro-only: G4 alone, before the centred products exist)
"""
from __future__ import annotations

import dataclasses
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.ios_product_centring import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402
from src.eda.serve_speed_tabpfn import local_fits as SL  # noqa: E402

ARM = "cprod"
SEASONS = tuple(range(2019, 2027))
SEEDS = (0, 1, 2, 3)
REPRO = ("model", 2025, 0)
ARM_FRAME = C.OUT / "arm_frame.parquet"


def paths(arm: str) -> SC.Paths:
    """The serve-speed study's paths, with the model frame swapped for the centred arm's frame when arm is cprod."""
    return SC.DEFAULT if arm == "model" else dataclasses.replace(SC.DEFAULT, model_frame=ARM_FRAME)


def gates_passed(names=("g1_reference.json", "g2_products.json", "g6_symmetry.json")) -> dict:
    return {n: bool((C.CHECKS / n).exists() and C.read_json(C.CHECKS / n).get("passed") is True) for n in names}


def out_path(arm: str, season: int, seed: int) -> Path:
    name = f"{arm}__{season}__seed{seed}.npz"
    return C.LOCAL / "repro" / name if arm == "model" else C.LOCAL / name


def fit_one(arm: str, season: int, seed: int, frame: pd.DataFrame, ep: pd.DataFrame, P: SC.Paths) -> Path:
    import torch

    from src.eda.tabpfn_local import runtime
    path = out_path(arm, season, seed)
    if path.exists():
        return path
    cols = SA.arm_inputs("model", P)                       # the 58 inputs, in the model's order
    X_train, y_train, X_test, ids = SA.job_data(frame, cols, season)
    qs = SL.queries(ep, season, X_test, ids, P)
    names = list(qs)
    X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
    free_gb = SL.wait_for_memory()
    clf = runtime.classifier(**SC.CONFIG, random_state=seed)
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
    meta = {"arm": arm, "season": season, "seed": seed, "config": {**SC.CONFIG, "random_state": seed},
            "train_shape": list(X_train.shape), "train_seasons": [SC.TRAIN_FROM, season - 1],
            "query_rows": {n: int(len(qs[n][0])) for n in names}, "columns": list(X_train.columns),
            "fingerprint": SC.fingerprint(X_train, y_train, X_query), "frame": str(P.model_frame),
            "frame_sha256": C.sha256(P.model_frame), "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
            "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
    tmp.replace(path)
    C.log(f"{path.name}: {secs:.0f} s, peak {meta['peak_gpu_gb']} GB, queries {meta['query_rows']}")
    del clf
    torch.cuda.empty_cache()
    return path


def main() -> int:
    args = sys.argv[1:]
    seasons = SEASONS
    if "--seasons" in args:
        lo, hi = args[args.index("--seasons") + 1].split("-")
        seasons = tuple(range(int(lo), int(hi) + 1))
    seeds = tuple(int(s) for s in args[args.index("--seeds") + 1].split(",")) if "--seeds" in args else SEEDS
    repro_only = "--repro-only" in args              # G4 alone: it reads no centred product, so no gate is needed
    gates = gates_passed()
    if not repro_only and not all(gates.values()):
        raise SystemExit(f"gates not passed: {gates}")
    ep = SL.early_frame(SC.DEFAULT)

    # G4: the runner reproduces a stored base fit
    arm, season, seed = REPRO
    P0 = paths("model")
    frame0 = SA.load_frame([], P0, labels=True)
    new = fit_one(arm, season, seed, frame0, ep, P0)
    g4 = SL.compare_fit_files(new, SC.DEFAULT.race_local / new.name, SC.REPRO_TOL)
    g4 = {"what": "G4: this study's runner reproduces the rating race's stored base fit", "tolerance": SC.REPRO_TOL,
          "job": {"arm": arm, "season": season, "seed": seed}, **g4}
    C.jdump(g4, C.CHECKS / "g4_repro.json")
    C.log(f"G4 {'PASS' if g4['passed'] else 'FAIL'}: {g4['blocks']}")
    if not g4["passed"]:
        return 1
    if repro_only:
        return 0
    del frame0

    # the centred arm
    P1 = paths(ARM)
    frame1 = SA.load_frame([], P1, labels=True)
    base = pd.read_parquet(SC.DEFAULT.model_frame, columns=["match_id", "season"])
    if not np.array_equal(frame1["match_id"].to_numpy(), base["match_id"].astype(str).to_numpy()):
        raise RuntimeError("the arm frame's rows differ from the model frame's")
    cols = SA.arm_inputs("model", P1)
    if not SA.check_flip(frame1, cols, P1):
        raise RuntimeError("the arm frame's flip is not an involution")
    for season in seasons:
        for seed in seeds:
            fit_one(ARM, season, seed, frame1, ep, P1)
    C.log("all centred-arm fits done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
