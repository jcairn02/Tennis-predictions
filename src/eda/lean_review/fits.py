"""The lean review's T2: local TabPFN-3.5 fits of the four arms (common.py) on the Pinnacle-first instance.

Every job is the current best model's fit (src/eda/model_rebuild/fits.py: the serve-speed harness's job data, 8
estimators, softmax temperature 0.9, pretraining limits ignored, random state = the seed; season Y trained on the frame's
matches of 2013 .. Y - 1), on the arm's inputs, with two predict calls on the same fitted model:

    1. "td"    the season's matches as stored and with A and B swapped: model_rebuild/fits.py's one call, unchanged, so
               A0's predictions reproduce the instance's stored fits (amendment C of the lean review)
    2. "open"  the matches with Pinnacle's opening line (common.opening_prices), odds_logit replaced by its margin-free
               log-odds, stored and swapped: a separate call, made after the first

Seasons 2019-2024, seeds 0-3. Fits are written to data/studies/lean_review/arms/<arm>/fits/model__<Y>__seed<k>.npz (the
harness's layout, so serve_speed_tabpfn.forecasts reads their "td" block) and never redone. After every A0 fit its td
block is compared with the instance's stored fit; a difference above REPRO_TOL stops the run.

    --check   CPU only, no fit, no result read: writes the arms' input lists, checks the flip, and compares every A0
              job's fingerprint (training rows, labels, close-fed queries) with the instance's stored fit's. check.json
    --run     the fits (one at a time; waits for free card memory before each)
    --repro   A0's td predictions against the instance's stored fits, all 24 jobs: repro.json

Run: ./python.sh src/eda/lean_review/fits.py --check
     bash src/eda/bet_timing/run_when_free.sh src/eda/lean_review/fits.py --run [--arms A0,A1,A2,A3]
     ./python.sh src/eda/lean_review/fits.py --repro
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

REPRO_TOL = 1e-12          # amendment C: "to machine precision"
STORED = L.INSTANCE / "fits"


def fit_path(arm: str, season: int, seed: int) -> Path:
    return L.fits_dir(arm) / f"model__{season}__seed{seed}.npz"


def stored_path(season: int, seed: int) -> Path:
    return STORED / f"model__{season}__seed{seed}.npz"


class Arm:
    """One arm's frame, inputs and opening prices, loaded once."""

    def __init__(self, arm: str):
        self.arm = arm
        L.write_inputs(arm)
        self.P = L.paths(arm)
        self.cols = A.arm_inputs("model", self.P)
        if len(self.cols) != 58 - len(L.ARMS[arm]):
            raise RuntimeError(f"{arm}: {len(self.cols)} inputs, expected {58 - len(L.ARMS[arm])}")
        self.frame = A.load_frame([], self.P, labels=True)
        if not A.check_flip(self.frame, self.cols, self.P):
            raise RuntimeError(f"{arm}: flip is not an involution")
        op = L.opening_prices(self.frame)
        self.p_open = pd.Series(op["p_open"].to_numpy(float), index=op["match_id"].to_numpy())

    def job(self, season: int):
        """(X_train, y_train, {block: (X_query, ids)}) for one season."""
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
    out = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "arms": {}, "a0_fingerprints": []}
    for arm in L.ARMS:
        a = Arm(arm)
        rows = {}
        for season in L.SEASONS:
            X_train, y_train, qs = a.job(season)
            rows[str(season)] = {"train": list(X_train.shape), "td_rows": len(qs["td"][0]),
                                 "open_rows": len(qs["open"][0]), "open_share": round(len(qs["open"][1]) /
                                                                                      len(qs["td"][1]), 3)}
            if arm == "A0":
                fp = C.fingerprint(X_train, y_train, qs["td"][0])
                for seed in L.SEEDS:
                    meta = stored_meta(stored_path(season, seed))
                    out["a0_fingerprints"].append({"season": season, "seed": seed, "equal": meta.get("fingerprint") == fp,
                                                   "columns_equal": meta.get("columns") == a.cols,
                                                   "train_shape_equal": meta.get("train_shape") == list(X_train.shape)})
        out["arms"][arm] = {"inputs": len(a.cols), "dropped": L.ARMS[arm], "seasons": rows}
    out["all_ok"] = bool(out["a0_fingerprints"]) and all(r["equal"] and r["columns_equal"] and r["train_shape_equal"]
                                                         for r in out["a0_fingerprints"])
    L.OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(L.OUT / "check.json", out)
    C.log(f"check: {len(out['a0_fingerprints'])} A0 jobs, fingerprints equal to the stored fits: {out['all_ok']}")
    return out


def compare_td(arm: str, season: int, seed: int) -> dict:
    """A0's td block against the instance's stored fit: same ids, max |difference|."""
    with np.load(fit_path(arm, season, seed), allow_pickle=False) as a, \
            np.load(stored_path(season, seed), allow_pickle=False) as b:
        same = bool(np.array_equal(a["ids_td"].astype(str), b["ids_td"].astype(str)))
        diff = float(np.abs(a["p_td"] - b["p_td"]).max()) if same else float("inf")
    return {"season": season, "seed": seed, "same_ids": same, "max_abs_diff": diff,
            "passed": bool(same and diff <= REPRO_TOL)}


def repro() -> dict:
    rows = [compare_td("A0", s, k) for s in L.SEASONS for k in L.SEEDS if fit_path("A0", s, k).exists()]
    out = {"tolerance": REPRO_TOL, "jobs": rows, "complete": len(rows) == len(L.SEASONS) * len(L.SEEDS),
           "passed": bool(rows) and len(rows) == len(L.SEASONS) * len(L.SEEDS) and all(r["passed"] for r in rows),
           "max_abs_diff": max((r["max_abs_diff"] for r in rows), default=None)}
    C.write_json(L.OUT / "repro.json", out)
    C.log(f"repro: {len(rows)} A0 jobs, passed {out['passed']}, max |diff| {out['max_abs_diff']}")
    return out


def run(arms: list[str]) -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    from src.eda.training_window.fits import wait_for_card
    if not C.read_json(L.OUT / "check.json").get("all_ok"):
        raise SystemExit("run --check first: A0's jobs must equal the instance's stored fits")
    frame_sha = C.sha256_file(L.FRAME)
    for arm in arms:
        a = Arm(arm)
        L.fits_dir(arm).mkdir(parents=True, exist_ok=True)
        for season in L.SEASONS:
            todo = [k for k in L.SEEDS if not fit_path(arm, season, k).exists()]
            if not todo:
                continue
            X_train, y_train, qs = a.job(season)
            for seed in todo:
                path = fit_path(arm, season, seed)
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
                        raise RuntimeError(f"{arm} {path.name}: invalid probabilities")
                payload = {"p_td": p_td[:, 1], "ids_td": qs["td"][1].astype(str),
                           "p_open": p_open[:, 1], "ids_open": qs["open"][1].astype(str)}
                meta = {"arm": "model", "lean_review_arm": arm, "dropped": L.ARMS[arm], "season": season, "seed": seed,
                        "kind": "fit", "frame": "Pinnacle-first instance (lean review T2)",
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
                C.log(f"{arm} {path.name}: fit+td {t1 - t0:.0f} s, open {t2 - t1:.0f} s, train {X_train.shape}, "
                      f"queries {meta['query_rows']}")
                del clf
                torch.cuda.empty_cache()
                if arm == "A0":
                    r = compare_td(arm, season, seed)
                    if not r["passed"]:
                        raise SystemExit(f"A0 {season} seed {seed} does not reproduce the stored fit: {r}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--repro", action="store_true")
    ap.add_argument("--arms", default="A0,A1,A2,A3")
    a = ap.parse_args()
    if a.check:
        return 0 if check()["all_ok"] else 1
    if a.repro:
        return 0 if repro()["passed"] else 1
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    bad = [x for x in arms if x not in L.ARMS]
    if bad:
        raise SystemExit(f"unknown arms {bad}")
    return run(arms)


if __name__ == "__main__":
    sys.exit(main())
