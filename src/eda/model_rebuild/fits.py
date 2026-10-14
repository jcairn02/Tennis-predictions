"""Local TabPFN-3.5 fits of the current best model (docs/decisions/2026-10-08-current-best-model.md) on a built frame.

The base model's fits as the serve-speed study's runner makes them (src/eda/serve_speed_tabpfn/local_fits.py: its
job_data, queries and the local classifier with its CONFIG: 8 estimators, softmax temperature 0.9, pretraining limits
ignored), for the arm "model" (the inputs of model_inputs.json) on the frame in --out (default data/studies/
model_rebuild, the build of 8 Oct 2026; a later build: the folder run_chain.py --collect wrote). The list must be the
chain's 58 or the template's 57 (current_best_model/template_inputs.py: ios_points_short dropped on 9 Oct 2026):

    job (season Y, seed k)   trains on the frame's matches of 2013 .. Y - 1, predicts season Y as stored and with A and
                             B swapped ("td"), and, in 2025-2026, at Polymarket's 24-hour and 30-minute prices where the
                             current frame's matches have one ("early", "late")
    seasons 2019-2026 (2019-2021 feed the speed adjustment's walk-forward coefficients), seeds 0-3 (the current model's
    calibration and coefficient seeds); --seeds 4-15 adds the seeds the decided adjustment averages when it applies

The runner's guard ("the base arm is reused, never refitted") protects the CURRENT model's fits; these are new fits of a
new frame, written apart, in <out>/fits/<arm>__<season>__seed<k>.npz with the runner's metadata
(the frame's SHA-256 included). A fit already on disk is never redone. One fit at a time on the card: each fit waits,
as the other studies' runners wait (training_window.fits.wait_for_card), until no other local-env process runs and 12 GB
are free.

Run: ./python_tabpfn_local.sh src/eda/model_rebuild/fits.py [--out <folder>] [--seeds 0-3] [--seasons 2019-2026]
     (--seasons defaults to 2019 through the frame's last season)
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import template_inputs as TI  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import local_fits as LF  # noqa: E402
from src.eda.training_window import fits as TWF  # noqa: E402  (wait_for_card: the shared card's turn-taking)

OUT = ROOT / "data" / "studies" / "model_rebuild"


def paths(out: Path = OUT) -> C.Paths:
    """The serve-speed study's paths pointed at a built frame and its fit folder (never another study's fits)."""
    return C.DEFAULT.with_(model_frame=out / "model_frame.parquet", model_inputs=out / "model_inputs.json",
                           local=out / "fits", fi_local=out / "no_fits_here", race_local=out / "no_fits_here")


PATHS = paths()


def span(text: str) -> list[int]:
    a, _, b = text.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main() -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", default="0-3")
    ap.add_argument("--seasons", default=None,
                    help="default: 2019 to the frame's last season (2019-2026 until 10 Oct 2026, a fixed default)")
    ap.add_argument("--out", default=str(OUT), help="the built frame's folder (model_frame.parquet, model_inputs.json)")
    ap.add_argument("--wait-memory-only", action="store_true",
                    help="before each fit wait only for free memory on the card, not for other local-env processes "
                         "to exit: two runners that each wait for the other to exit never start (seen 9 Oct 2026). "
                         "Start such a run with src/eda/bet_timing/run_when_free.sh, which waits for the card first")
    a = ap.parse_args()
    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    P = paths(out)
    arm = "model"
    cols = A.arm_inputs(arm, P)
    try:
        list_kind = TI.kind(cols)
    except ValueError as e:
        raise SystemExit(f"the rebuilt frame's input list: {e}")
    C.log(f"input list: {list_kind} ({len(cols)} inputs)")
    frame = A.load_frame([], P, labels=True)
    if not A.check_flip(frame, cols, P):
        raise SystemExit("flip is not an involution")
    ep = LF.early_frame(P)
    frame_sha = C.sha256_file(P.model_frame)
    P.local.mkdir(parents=True, exist_ok=True)
    seasons = span(a.seasons) if a.seasons else list(range(2019, int(frame["season"].max()) + 1))
    for season in seasons:
        for seed in span(a.seeds):
            path = P.local / f"{arm}__{season}__seed{seed}.npz"
            if path.exists():
                continue
            X_train, y_train, X_test, ids = A.job_data(frame, cols, season)
            qs = LF.queries(ep, season, X_test, ids, P)
            names = list(qs)
            X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
            free_gb = TWF.wait_for_card(patience_s=12 * 3600, processes=not a.wait_memory_only)
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
            meta = {"arm": arm, "season": season, "seed": seed, "kind": "fit", "frame": "rebuilt (model_rebuild)",
                    "config": {**C.CONFIG, "random_state": seed}, "train_shape": list(X_train.shape),
                    "train_seasons": [C.TRAIN_FROM, season - 1], "query_rows": {n: int(len(qs[n][0])) for n in names},
                    "columns": list(X_train.columns), "input_list": list_kind,
                    "fingerprint": C.fingerprint(X_train, y_train, X_query),
                    "model_frame_sha256": frame_sha, "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                    "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                    "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
            tmp.replace(path)
            C.log(f"{path.name}: {secs:.0f} s, train {X_train.shape}, queries {meta['query_rows']}")
            del clf
            torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
