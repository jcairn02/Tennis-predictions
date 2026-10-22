"""Step 7: the local TabPFN-3.5 fits of the three arms (preregistration.md, "Arms").

    M0  today's model: the instance's main-draw rows of 2013 .. Y - 1, exactly its own fits' training rows and order
        (serve_speed_tabpfn/arms.job_data on its frame)
    M1  pooled: M0's rows, then the priced qualifying rows of 2018 .. Y - 1
    M2  separate: the priced qualifying rows of 2018 .. Y - 1 only
Settings: serve_speed_tabpfn/common.CONFIG (8 estimators, softmax temperature 0.9, pretraining limits ignored), the
local classifier (tabpfn_local/runtime), random_state = seed. Inputs: the instance's 57 (model_inputs.json order); the
qualifying rows' odds input is the log-odds of their closing price (prices.py: Pinnacle's, else BetOnline's).

Each fit (arm, season Y, seed k) queries, each block as stored and then with A and B swapped (serve_speed_tabpfn's
flip), each block in its own predict_proba call: the season-Y main-draw matches ("main"; M0 and M1 only, in the frame's
order, as the instance's fits ask their "td" block) and the season-Y priced qualifying matches ("qual"). One call per
block since 22 Oct 2026, 08:05: in one call a row's forecast moved by up to 1.2e-4 with the other rows asked beside it
(diag_m0.py), and asked alone M0's main block reproduced the instance's stored fit bit for bit. Written to
data/studies/qualifying_targets/local/<arm>__<Y>__seed<k>.npz (p_<block>, ids_<block>, meta). A fit on disk is not redone.
One fit at a time on the card (training_window/fits.wait_for_card).

The check (pre-registered): M0's "main" block must reproduce the instance's stored fit (its "td" block) for the same
season and seed; --check-m0 runs one fit (2019, seed 0) and compares before the batch.

Run: ./python_tabpfn_local.sh src/eda/qualifying_targets/fits.py [--arms M0,M1,M2] [--seasons 2019-2026] [--seeds 0-3]
     ./python_tabpfn_local.sh src/eda/qualifying_targets/fits.py --check-m0
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

from src.eda.model_rebuild import fits as MF  # noqa: E402  (paths of a built instance)
from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402
from src.eda.training_window import fits as TWF  # noqa: E402

QUAL_TRAIN_FROM = C.FIRST_SEASON


def span(text: str) -> list[int]:
    a, _, b = text.partition("-")
    return list(range(int(a), int(b or a) + 1))


def load() -> tuple:
    P = MF.paths(C.INSTANCE)
    cols = A.arm_inputs("model", P)
    main = A.load_frame([], P, labels=True)
    q = pd.read_parquet(C.FRAME)
    pr = pd.read_parquet(C.PRICES, columns=["match_id", "p_close", "close_source"])
    q = q.merge(pr, on="match_id", how="left", validate="one_to_one")
    q = q[np.isfinite(q["p_close"].to_numpy(float))].copy()
    q["in_odds_logit"] = logit(np.clip(q["p_close"].to_numpy(float), SC.EPS, 1 - SC.EPS))
    q = q.sort_values(["season", "tournament_date", "match_id"]).reset_index(drop=True)
    if q["match_id"].duplicated().any():
        raise SystemExit("duplicate qualifying rows")
    return P, cols, main, q


def job(arm: str, season: int, P, cols, main: pd.DataFrame, q: pd.DataFrame):
    Xm, Xq = A.matrix(main, cols), A.matrix(q, cols)
    tr_m = main["season"].between(SC.TRAIN_FROM, season - 1).to_numpy()
    tr_q = q["season"].between(QUAL_TRAIN_FROM, season - 1).to_numpy()
    ym = main.loc[tr_m, "a_won"].astype("int64").to_numpy()
    yq = q.loc[tr_q, "a_won"].astype("int64").to_numpy()
    if arm == "M0":
        X_train, y_train, n_q = Xm[tr_m], ym, 0
    elif arm == "M1":
        X_train, y_train, n_q = pd.concat([Xm[tr_m], Xq[tr_q]], ignore_index=True), np.r_[ym, yq], int(tr_q.sum())
    elif arm == "M2":
        X_train, y_train, n_q = Xq[tr_q], yq, int(tr_q.sum())
    else:
        raise KeyError(arm)
    X_train = X_train.reset_index(drop=True)
    blocks = {}
    if arm != "M2":
        te = (main["season"] == season).to_numpy()
        Xt = Xm[te].reset_index(drop=True)
        blocks["main"] = (pd.concat([Xt, A.flip(Xt, P)], ignore_index=True), main.loc[te, "match_id"].to_numpy())
    te = (q["season"] == season).to_numpy()
    Xt = Xq[te].reset_index(drop=True)
    blocks["qual"] = (pd.concat([Xt, A.flip(Xt, P)], ignore_index=True), q.loc[te, "match_id"].to_numpy())
    return X_train, y_train, n_q, blocks


def fit_one(arm: str, season: int, seed: int, P, cols, main, q, shas: dict, wait_memory_only: bool = False) -> Path:
    import torch

    from src.eda.tabpfn_local import runtime
    path = C.LOCAL / f"{arm}__{season}__seed{seed}.npz"
    if path.exists():
        return path
    X_train, y_train, n_q, blocks = job(arm, season, P, cols, main, q)
    names = list(blocks)
    X_query = pd.concat([blocks[n][0] for n in names], ignore_index=True)
    free_gb = TWF.wait_for_card(patience_s=12 * 3600, processes=not wait_memory_only)
    clf = runtime.classifier(**SC.CONFIG, random_state=seed)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.monotonic()
    clf.fit(X_train, y_train)
    # one predict_proba call per block (22 Oct 2026, diag_m0.py): a row's forecast moves by up to 1.2e-4 with the
    # other rows of its call, so each block is asked on its own, as the instance asked its main block
    payload = {}
    for n in names:
        proba = clf.predict_proba(blocks[n][0])
        if [int(c) for c in clf.classes_] != [0, 1] or not np.isfinite(proba).all():
            raise RuntimeError(f"{path.name}: invalid probabilities")
        payload[f"p_{n}"] = proba[:, 1]
        payload[f"ids_{n}"] = blocks[n][1].astype(str)
    secs = time.monotonic() - t0
    meta = {"arm": arm, "season": season, "seed": seed, "config": {**SC.CONFIG, "random_state": seed},
            "train_shape": list(X_train.shape), "train_rows_qualifying": n_q,
            "train_seasons_main": [SC.TRAIN_FROM, season - 1] if arm != "M2" else None,
            "train_seasons_qualifying": [QUAL_TRAIN_FROM, season - 1] if arm != "M0" else None,
            "query_rows": {n: int(len(blocks[n][0])) for n in names}, "query_calls": "one predict_proba call per block",
            "columns": list(X_train.columns),
            "fingerprint": SC.fingerprint(X_train, y_train, X_query), **shas, "seconds": round(secs, 1),
            "gpu_free_gb_before": round(free_gb, 1), "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
            "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
            "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
    C.LOCAL.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
    tmp.replace(path)
    C.log(f"{path.name}: {secs:.0f} s, train {X_train.shape} (qualifying {n_q}), queries {meta['query_rows']}")
    del clf
    torch.cuda.empty_cache()
    return path


def check_m0(path: Path, season: int, seed: int) -> dict:
    """M0's main block against the instance's stored fit (its td block) for the same season and seed."""
    with np.load(path, allow_pickle=False) as z:
        p, ids = z["p_main"], z["ids_main"]
    with np.load(C.INSTANCE / "fits" / f"model__{season}__seed{seed}.npz", allow_pickle=False) as z:
        ps, ids_s = z["p_td"], z["ids_td"]
    same_ids = bool(np.array_equal(ids.astype(str), ids_s.astype(str)))
    d = np.abs(p - ps) if same_ids and len(p) == len(ps) else np.array([np.inf])
    return {"season": season, "seed": seed, "same_ids": same_ids, "rows": int(len(p)), "max_abs_diff": float(d.max()),
            "equal_exactly": bool(same_ids and np.array_equal(p, ps))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", default=",".join(C.ARMS))
    ap.add_argument("--seasons", default="2019-2026")
    ap.add_argument("--seeds", default="0-3")
    ap.add_argument("--check-m0", action="store_true", help="one M0 fit (2019, seed 0) against the instance's, then stop")
    ap.add_argument("--wait-memory-only", action="store_true")
    a = ap.parse_args()
    P, cols, main_frame, q = load()
    if len(cols) != 57:
        raise SystemExit(f"{len(cols)} inputs: the template's 57 expected")
    shas = {"instance_frame_sha256": C.sha256_file(P.model_frame), "qual_frame_sha256": C.sha256_file(C.FRAME),
            "prices_sha256": C.sha256_file(C.PRICES)}
    C.log(f"inputs {len(cols)}; main rows {len(main_frame):,}; priced qualifying rows {len(q):,}")
    if a.check_m0:
        path = fit_one("M0", 2019, 0, P, cols, main_frame, q, shas, a.wait_memory_only)
        r = check_m0(path, 2019, 0)
        C.write_json(C.OUT / "m0_check_2019_seed0.json", r)
        C.log(f"M0 check: {r}")
        return 0 if r["same_ids"] and r["max_abs_diff"] <= 1e-6 else 6
    arms = a.arms.split(",")
    for season in span(a.seasons):
        for seed in span(a.seeds):
            for arm in arms:
                fit_one(arm, season, seed, P, cols, main_frame, q, shas, a.wait_memory_only)
    checks = [check_m0(C.LOCAL / f"M0__{s}__seed{k}.npz", s, k) for s in span(a.seasons) for k in span(a.seeds)
              if (C.LOCAL / f"M0__{s}__seed{k}.npz").exists()]
    C.write_json(C.OUT / "m0_checks.json", checks)
    C.log(f"M0 checks: max abs diff {max(c['max_abs_diff'] for c in checks):.2e} over {len(checks)} fits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
