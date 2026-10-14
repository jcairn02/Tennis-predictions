"""The candidate's fits: the current best model's fit on the candidate frame (arm.py), as the lean review fitted its arms.

Every job is model_rebuild/fits.py's (the serve-speed harness's job data, 8 estimators, softmax temperature 0.9,
pretraining limits ignored, random state = the seed; season Y trained on the frame's matches of 2013 .. Y - 1), with two
predict calls on the fitted model, as lean_review/fits.py makes them:
    "td"    the season's matches as stored and with A and B swapped, fed the close (the frame's odds input)
    "open"  the matches with Pinnacle's opening line (lean_review/common.opening_prices), fed that line instead, stored
            and swapped
Seasons 2019-2024, seeds 0-3. The base needs no new fit: the lean review's arm A2 holds the same jobs on the same frame
but for in_indoor (data/studies/lean_review/arms/A2/fits/).

    --check  CPU only, no fit, no result read: each season's job here equals A2's but for the indoor column (training
             rows, labels, query ids, and the opening-fed queries), and A2's stored fits carry the fingerprint of A2's job,
             so the pair differs in the indoor input alone. Writes data/studies/indoor_fill/check.json
    --run    the fits, one at a time, each after free card memory is seen (data/studies/indoor_fill/arm/fits/)
Run: ./python.sh src/eda/indoor_fill/fits.py --check
     bash src/eda/bet_timing/run_when_free.sh src/eda/indoor_fill/fits.py --run
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
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lean_review import common as L  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402

OUT = ROOT / "data" / "studies" / "indoor_fill"
ARM = OUT / "arm"
LABEL = "indoor"                       # this study's arm, in each fit's meta
SEASONS, SEEDS = L.SEASONS, L.SEEDS    # 2019-2024, 0-3


def paths() -> C.Paths:
    return C.DEFAULT.with_(model_frame=ARM / "model_frame.parquet", model_inputs=ARM / "model_inputs.json",
                           local=ARM / "fits", fi_local=L.NOWHERE, race_local=L.NOWHERE, checks=L.NOWHERE)


def fit_path(season: int, seed: int) -> Path:
    return ARM / "fits" / f"model__{season}__seed{seed}.npz"


class Arm:
    """A frame, its inputs and opening prices, loaded once (lean_review.fits.Arm, for any frame)."""

    def __init__(self, P: C.Paths, n_inputs: int = 57):
        self.P = P
        self.cols = A.arm_inputs("model", P)
        if len(self.cols) != n_inputs:
            raise RuntimeError(f"{P.model_inputs}: {len(self.cols)} inputs, expected {n_inputs}")
        self.frame = A.load_frame([], P, labels=True)
        if not A.check_flip(self.frame, self.cols, P):
            raise RuntimeError(f"{P.model_frame}: flip is not an involution")
        op = L.opening_prices(self.frame)
        self.p_open = pd.Series(op["p_open"].to_numpy(float), index=op["match_id"].to_numpy())

    def job(self, season: int):
        X_train, y_train, X_test, ids = A.job_data(self.frame, self.cols, season)
        qs = {"td": (pd.concat([X_test, A.flip(X_test, self.P)], ignore_index=True), ids)}
        p = self.p_open.reindex(ids.astype(str)).to_numpy(float)
        ok = np.isfinite(p)
        Xo = X_test[ok].reset_index(drop=True).copy()
        Xo["odds_logit"] = logit(np.clip(p[ok], C.EPS, 1 - C.EPS))
        qs["open"] = (pd.concat([Xo, A.flip(Xo, self.P)], ignore_index=True), ids[ok])
        return X_train, y_train, qs


def stored_meta(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return json.loads(str(z["meta"]))


def check() -> dict:
    cand, base = Arm(paths()), Arm(L.paths("A2"))
    if cand.cols != base.cols:
        raise SystemExit("the candidate's input list differs from A2's")
    others = [c for c in cand.cols if c != "indoor"]
    rows = []
    for season in SEASONS:
        Xc, yc, qc = cand.job(season)
        Xb, yb, qb = base.job(season)
        r = {"season": season, "train_shape": list(Xc.shape), "labels_equal": bool(np.array_equal(yc, yb)),
             "other_columns_equal": bool(np.array_equal(Xc[others].to_numpy(), Xb[others].to_numpy(), equal_nan=True)),
             "indoor_changed_train": int((~np.isclose(Xc["indoor"].fillna(-1), Xb["indoor"].fillna(-1))).sum())}
        for blk in ("td", "open"):
            r[f"{blk}_ids_equal"] = bool(np.array_equal(qc[blk][1].astype(str), qb[blk][1].astype(str)))
            r[f"{blk}_other_columns_equal"] = bool(np.array_equal(qc[blk][0][others].to_numpy(),
                                                                  qb[blk][0][others].to_numpy(), equal_nan=True))
        fp = C.fingerprint(Xb, yb, qb["td"][0])
        stored = [stored_meta(L.fits_dir("A2") / f"model__{season}__seed{k}.npz") for k in SEEDS]
        r["a2_stored_fingerprints_equal"] = all(m.get("fingerprint") == fp and m.get("columns") == base.cols
                                                for m in stored)
        rows.append(r)
    keys = [k for k in rows[0] if k.endswith("_equal")]
    out = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "seasons": rows,
           "all_ok": all(r[k] for r in rows for k in keys)}
    C.write_json(OUT / "check.json", out)
    C.log(f"check: {len(rows)} seasons; the jobs differ from A2's in the indoor column only and A2's fits match: "
          f"{out['all_ok']}")
    return out


def run() -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    from src.eda.training_window.fits import wait_for_card
    if not C.read_json(OUT / "check.json").get("all_ok"):
        raise SystemExit("run --check first")
    a = Arm(paths())
    frame_sha = C.sha256_file(paths().model_frame)
    (ARM / "fits").mkdir(parents=True, exist_ok=True)
    for season in SEASONS:
        todo = [k for k in SEEDS if not fit_path(season, k).exists()]
        if not todo:
            continue
        X_train, y_train, qs = a.job(season)
        for seed in todo:
            path = fit_path(season, seed)
            free_gb = wait_for_card(patience_s=12 * 3600, processes=False)
            clf = runtime.classifier(**C.CONFIG, random_state=seed)
            torch.cuda.reset_peak_memory_stats()
            t0 = time.monotonic()
            clf.fit(X_train, y_train)
            p_td = clf.predict_proba(qs["td"][0])
            t1 = time.monotonic()
            p_open = clf.predict_proba(qs["open"][0])
            t2 = time.monotonic()
            for p in (p_td, p_open):
                if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(p).all():
                    raise RuntimeError(f"{path.name}: invalid probabilities")
            payload = {"p_td": p_td[:, 1], "ids_td": qs["td"][1].astype(str),
                       "p_open": p_open[:, 1], "ids_open": qs["open"][1].astype(str)}
            meta = {"arm": "model", "indoor_fill_arm": LABEL, "season": season, "seed": seed, "kind": "fit",
                    "frame": "the Pinnacle-first instance with in_indoor filled (src/eda/indoor_fill/arm.py)",
                    "config": {**C.CONFIG, "random_state": seed}, "train_shape": list(X_train.shape),
                    "train_seasons": [C.TRAIN_FROM, season - 1],
                    "query_rows": {n: int(len(q[0])) for n, q in qs.items()}, "columns": list(X_train.columns),
                    "fingerprint": C.fingerprint(X_train, y_train, qs["td"][0]),
                    "fingerprint_open": C.fingerprint(X_train, y_train, qs["open"][0]),
                    "model_frame_sha256": frame_sha, "seconds_fit_td": round(t1 - t0, 1),
                    "seconds_open": round(t2 - t1, 1), "gpu_free_gb_before": round(free_gb, 1),
                    "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                    "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
            tmp.replace(path)
            C.log(f"{path.name}: fit+td {t1 - t0:.0f} s, open {t2 - t1:.0f} s, train {X_train.shape}, "
                  f"queries {meta['query_rows']}")
            del clf
            torch.cuda.empty_cache()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.check:
        return 0 if check()["all_ok"] else 1
    return run()


if __name__ == "__main__":
    sys.exit(main())
