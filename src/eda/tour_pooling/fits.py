"""The tour-pooling study's local TabPFN-3.5 fits (docs/studies/tour_pooling/design.md; arms in common.py).

The current instance's recipe (src/eda/model_rebuild/fits.py): runtime.classifier with serve_speed_tabpfn.common.CONFIG
(8 estimators, softmax temperature 0.9, pretraining limits ignored), seeds 0-3, seasons 2019-2026, season Y trained on
2013 .. Y - 1, the query as stored and swapped (td). Only the training rows, the query rows and the arm's inputs change.

Writes data/studies/tour_pooling/fits/<arm>__<tour>__<Y>__seed<k>.npz (tour atp, wta, or both for a both-tour model):
p_td, ids_td and the meta (the frame's SHA-256, the training rows by tour and season, the draw). A fit on disk is never
redone. One fit at a time on the card: start the runner with src/eda/bet_timing/run_when_free.sh, which waits until no
tennis-tabpfn-local process runs; the runner then waits for free card memory only.

    ./python.sh src/eda/tour_pooling/fits.py --arm split --plan          # CPU: the jobs' training rows, nothing fitted
    ./python.sh src/eda/tour_pooling/fits.py --arm borrowsim --prepare   # CPU: the similarity draw's cache
    bash src/eda/bet_timing/run_when_free.sh src/eda/tour_pooling/fits.py --arm split [--seeds 0-3] [--seasons 2019-2026]
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

from src.eda.model_rebuild.fits import span  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.tour_pooling import common as C  # noqa: E402


def plan(frame: pd.DataFrame, arm: str, seasons, seeds) -> pd.DataFrame:
    rows = []
    t, s = frame["tour"].to_numpy(), frame["season"].to_numpy()
    for season in seasons:
        for seed in seeds:
            for tour in C.model_tours(arm):
                tr = C.train_mask(frame, arm, tour, season, seed)
                te = C.query_mask(frame, tour, season)
                rows.append({"arm": arm, "tour": tour, "season": season, "seed": seed, "train_rows": int(tr.sum()),
                             "train_atp": int((tr & (t == "atp")).sum()), "train_wta": int((tr & (t == "wta")).sum()),
                             "train_last_season": int(s[tr].max()), "query_rows": int(te.sum()),
                             "done": C.fit_path(arm, tour, season, seed).exists()})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", required=True, choices=sorted(C.ARMS))
    ap.add_argument("--seeds", default="0-3")
    ap.add_argument("--seasons", default="2019-2026")
    ap.add_argument("--plan", action="store_true", help="print the jobs' training rows; fit nothing")
    ap.add_argument("--prepare", action="store_true", help="borrowsim: build the similarity draw's cache on the CPU")
    a = ap.parse_args()
    seasons, seeds = span(a.seasons), span(a.seeds)
    frame = C.load_frame(labels=True)
    cols = C.inputs(a.arm)
    if not SA.check_flip(frame, cols, C.P):
        raise SystemExit("flip is not an involution")
    if a.plan:
        pd.set_option("display.width", 200)
        print(plan(frame, a.arm, seasons, seeds).to_string(index=False))
        return 0
    if a.prepare:
        for season in seasons:
            for tour in C.TOURS:
                C.sim_inclusion(frame, tour, season)
                meta = C.read_json(C.sim_path(tour, season).with_suffix(".json"))
                C.log(f"borrowsim {tour} {season}: AUC {meta['auc_out_of_fold']:.3f}, expected borrowed "
                      f"{meta['expected_borrowed']:.0f} of {meta['n_other']}, effective n {meta['effective_n']:.0f}")
        return 0

    import torch

    from src.eda.tabpfn_local import runtime
    from src.eda.training_window import fits as TWF  # wait_for_card: the shared card's turn-taking
    frame_sha = C.sha256_file(C.P.model_frame)
    C.FITS.mkdir(parents=True, exist_ok=True)
    for season in seasons:
        for seed in seeds:
            for tour in C.model_tours(a.arm):
                path = C.fit_path(a.arm, tour, season, seed)
                if path.exists():
                    continue
                X_train, y_train, X_query, ids, tr = C.job_data(frame, a.arm, tour, season, seed)
                free_gb = TWF.wait_for_card(patience_s=12 * 3600, processes=False)
                clf = runtime.classifier(**C.SC.CONFIG, random_state=seed)
                torch.cuda.reset_peak_memory_stats()
                t0 = time.monotonic()
                clf.fit(X_train, y_train)
                proba = clf.predict_proba(X_query)
                secs = time.monotonic() - t0
                if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
                    raise RuntimeError(f"{path.name}: invalid probabilities")
                by = frame.loc[tr].groupby(["tour", "season"]).size()
                meta = {"arm": a.arm, "tour": tour, "season": season, "seed": seed, "kind": "fit",
                        "study": "tour_pooling", "config": {**C.SC.CONFIG, "random_state": seed},
                        "train_shape": list(X_train.shape),
                        "train_rows_by_tour_season": {f"{k[0]} {int(k[1])}": int(v) for k, v in by.items()},
                        "query_rows": {"td": int(len(ids))}, "columns": list(X_train.columns),
                        "draw": {"seed": C.DRAW_SEED, "arm_code": C.ARM_CODE[a.arm], "tour_code": C.TOUR_CODE[tour],
                                 "share": C.BORROW_SHARE.get(a.arm),
                                 "sim_cache_sha256": (C.sha256_file(C.sim_path(tour, season))
                                                      if a.arm == "borrowsim" else None)},
                        "fingerprint": C.SC.fingerprint(X_train, y_train, X_query),
                        "model_frame": str(C.P.model_frame.relative_to(C.ROOT)), "model_frame_sha256": frame_sha,
                        "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                        "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                        "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                        "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
                tmp = path.with_name(path.name + ".tmp.npz")
                np.savez(tmp, meta=np.asarray(json.dumps(meta)), p_td=proba[:, 1], ids_td=ids.astype(str))
                tmp.replace(path)
                C.log(f"{path.name}: {secs:.0f} s, train {X_train.shape}, query {len(ids)}")
                del clf
                torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
