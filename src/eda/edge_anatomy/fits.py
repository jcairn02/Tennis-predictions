"""Family-ablation refits of the current best model's stage 1, for the edge-anatomy study (12 Oct 2026).

Each arm is the current instance's TabPFN-3.5 (data/studies/current_best_model/template_2026-10-10/, read-only) with
only its input list changed (common.arms()): the ladder L1..L5 (price; + context; + ratings; + schedule and body; +
box-score form) and the full model without one family (drop_context, drop_ratings, drop_schedule, drop_form, drop_ios).
The full model is the instance's own stored fits.

Everything else is the instance's recipe, as src/eda/model_rebuild/fits.py runs it: the decided config (8 estimators,
softmax temperature 0.9, pretraining limits ignored), season Y trained on the frame's matches of 2013 .. Y - 1, the
season's matches queried as stored and with A and B swapped ("td"; no Polymarket blocks). Training labels are seasons
<= Y - 1 only, so no result of the sealed holdout (from 29 Jul 2026) is ever used; those labels are blanked on loading
anyway.

--repro first refits the full model for one (season, seed) and compares it with the instance's stored fit: the runner
must reproduce the instance before its arms are read.

Writes data/studies/edge_anatomy/fits/<arm>__<season>__seed<k>.npz (p_td: stored then flipped orientation; ids_td;
meta) and repro.json. A fit already on disk is never redone.
Run: ./python_tabpfn_local.sh src/eda/edge_anatomy/fits.py [--repro] [--arms L1,L2,...] [--seasons 2019-2026]
                                                            [--seeds 0-3]
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

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.model_rebuild import fits as MRF  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.training_window import fits as TWF  # noqa: E402

P = MRF.paths(E.INSTANCE)


def span(text: str) -> list[int]:
    a, _, b = text.partition("-")
    return list(range(int(a), int(b or a) + 1))


def load_frame() -> pd.DataFrame:
    frame = A.load_frame([], P, labels=True)
    frame["a_won"] = frame["a_won"].astype("float64")
    sealed = (frame["tournament_date"] >= E.SEALED_FROM).to_numpy()
    frame.loc[sealed, "a_won"] = np.nan          # never a training row (season 2026 is the last); blanked regardless
    return frame


def fit_one(frame: pd.DataFrame, cols: list[str], season: int, seed: int, frame_sha: str) -> tuple[dict, dict]:
    import torch

    from src.eda.tabpfn_local import runtime
    X_train, y_train, X_test, ids = A.job_data(frame, cols, season)
    if not np.isin(y_train, [0, 1]).all():
        raise RuntimeError("a training label is not 0/1")
    X_query = pd.concat([X_test, A.flip(X_test, P)], ignore_index=True)
    free_gb = TWF.wait_for_card(patience_s=12 * 3600, processes=False)
    clf = runtime.classifier(**C.CONFIG, random_state=seed)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.monotonic()
    clf.fit(X_train, y_train)
    proba = clf.predict_proba(X_query)
    secs = time.monotonic() - t0
    if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
        raise RuntimeError("invalid probabilities")
    payload = {"p_td": proba[:, 1], "ids_td": np.asarray(ids).astype(str)}
    meta = {"season": season, "seed": seed, "config": {**C.CONFIG, "random_state": seed},
            "train_shape": list(X_train.shape), "train_seasons": [C.TRAIN_FROM, season - 1],
            "query_rows": int(len(X_query)), "columns": list(X_train.columns),
            "fingerprint": C.fingerprint(X_train, y_train, X_query), "model_frame_sha256": frame_sha,
            "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
            "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
    del clf
    torch.cuda.empty_cache()
    return payload, meta


def save(path: Path, payload: dict, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
    tmp.replace(path)


def repro(frame: pd.DataFrame, frame_sha: str, season: int = 2025, seed: int = 0) -> dict:
    """Refit the full model for (season, seed) and compare with the instance's stored fit."""
    cols = E.arms()["full"]
    path = E.fit_path("full", season, seed)
    if not path.exists():
        payload, meta = fit_one(frame, cols, season, seed, frame_sha)
        save(path, {**payload}, {**meta, "arm": "full", "kind": "repro"})
    with np.load(path, allow_pickle=False) as z:
        p_new, ids_new = z["p_td"], z["ids_td"].astype(str)
    stored = E.INSTANCE / "fits" / f"model__{season}__seed{seed}.npz"
    with np.load(stored, allow_pickle=False) as z:
        p_old, ids_old = z["p_td"], z["ids_td"].astype(str)
        meta_old = json.loads(str(z["meta"]))
    k = len(ids_new)
    same_ids = bool(np.array_equal(ids_new, ids_old))
    d = np.abs(E.sym(p_new, k) - E.sym(p_old, k)) if same_ids else np.array([np.inf])
    out = {"season": season, "seed": seed, "same_ids": same_ids, "matches": int(k),
           "max_abs_diff": float(d.max()), "mean_abs_diff": float(d.mean()),
           "stored_columns_equal": meta_old.get("columns") == cols,
           "stored_train_shape": meta_old.get("train_shape"), "passed": bool(same_ids and d.max() < 1e-6)}
    E.write_json(E.OUT / "repro.json", out)
    E.log(f"repro {season} seed {seed}: max |diff| {out['max_abs_diff']:.2e}, passed {out['passed']}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repro", action="store_true")
    ap.add_argument("--arms", default="L1,L2,L3,L4,L5,drop_context,drop_ratings,drop_schedule,drop_form,drop_ios")
    ap.add_argument("--seasons", default="2019-2026")
    ap.add_argument("--seeds", default="0-3")
    a = ap.parse_args()
    frame = load_frame()
    names = E.input_names()
    if not A.check_flip(frame, names, P):
        raise SystemExit("flip is not an involution")
    frame_sha = C.sha256_file(P.model_frame)
    if a.repro:
        r = repro(frame, frame_sha)
        if not r["passed"]:
            E.log("the reproduction differs from the stored fit: arms not run")
            return 1
    arm_cols = E.arms()
    for arm in [s for s in a.arms.split(",") if s]:
        cols = arm_cols[arm]
        for season in span(a.seasons):
            for seed in span(a.seeds):
                path = E.fit_path(arm, season, seed)
                if path.exists():
                    continue
                payload, meta = fit_one(frame, cols, season, seed, frame_sha)
                save(path, payload, {**meta, "arm": arm, "kind": "fit"})
                E.log(f"{path.name}: {meta['seconds']:.0f} s, train {tuple(meta['train_shape'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
