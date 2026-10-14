"""The local TabPFN-3.5 fits this study adds to the surface-IOS study's (GPU, no API tokens; env tennis-tabpfn-local).

The surface-IOS study fitted both models (base: with the closing odds; noodds: without) in the windows 2019-2026, each
trained on 2013 to the season before and queried on that season. This study needs two more kinds of forecast:

    the earlier out-of-sample seasons 2014-2018     both models, trained on 2013 to the season before (walk-forward),
                                                    to measure how the meta-model's weights move from season to season
    the hold-out design (noodds only)               a model trained on 2013 to T and queried on T+1 up to T+4 (to 2021
                                                    at most): the meta-learner is fitted on its forecasts of the first
                                                    seasons and the last is scored, as a textbook train/hold-out split
                                                    would. Validation seasons only; no 2022-2026 match is queried

One fit per (model, last training season T, seed): noodds for T = 2013-2019 queried on T+1..min(T+4, 2021); base for
T = 2013-2017 queried on T+1. The fits with T = 2018 and 2019 repeat the surface-IOS windows of 2019 and 2020 on their
first season: forecasts.py checks that they agree. Settings and the fit routine are the surface-IOS study's
(src/eda/surface_ios/run_local.py: 8 estimators, softmax temperature 0.9, pretraining limits ignored, the seed varying,
through src/eda/tabpfn_local/runtime.py). A finished fit is saved with its input fingerprint and never refitted.

    ./python_tabpfn_local.sh src/eda/meta_stack/run_local.py [--slots a,b] [--arms noodds,base]

Writes data/studies/meta_stack/local/<slot>.npz and local/runs.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.meta_stack import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

LAST_QUERY = max(C.VAL)          # the hold-out fits never query a test season


def slots() -> dict[str, dict]:
    out = {}
    for t in range(C.FIRST_TRAIN, 2020):
        q = tuple(range(t + 1, min(t + 4, LAST_QUERY) + 1))
        for k in C.SEEDS:
            out[f"noodds_t{t}_s{k}"] = {"arm": "noodds", "train_to": t, "query": q, "seed": k}
    for t in range(C.FIRST_TRAIN, 2018):
        for k in C.SEEDS:
            out[f"base_t{t}_s{k}"] = {"arm": "base", "train_to": t, "query": (t + 1,), "seed": k}
    return out


def input_names(f: pd.DataFrame) -> list[str]:
    """The model's inputs in the frame's (the arm's) order."""
    return [c[3:] for c in f.columns if c.startswith("in_")]


def frames(f: pd.DataFrame, train_to: int, query: tuple[int, ...]):
    """Training rows 2013..train_to; the query seasons' matches as stored, then with A and B swapped (every input but
    the match context negated, as the surface-IOS uploads)."""
    names = input_names(f)
    X = pd.DataFrame({n: f[f"in_{n}"].to_numpy(dtype="float64") for n in names})
    tr = f["year"].between(C.FIRST_TRAIN, train_to).to_numpy()
    te = f["year"].isin(query).to_numpy()
    X_train = X[tr].reset_index(drop=True)
    y = f.loc[tr, "a_won"].astype("int64").to_numpy()
    X_q = X[te].reset_index(drop=True)
    flipped = X_q.copy()
    anti = [n for n in names if n not in set(T.CONTEXT)]
    flipped[anti] = -X_q[anti]
    X_query = pd.concat([X_q, flipped], ignore_index=True)
    return X_train, y, X_query, f.loc[te, "match_id"].to_numpy()


def load(slot: str) -> tuple[np.ndarray, np.ndarray, str]:
    """(match ids, P(A wins) as stored then swapped, input fingerprint) of a saved fit."""
    with np.load(C.LOCAL / f"{slot}.npz", allow_pickle=False) as z:
        return z["match_id"].astype(str), z["p_a"], str(z["input_fingerprint"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slots", default="")
    ap.add_argument("--arms", default="")
    a = ap.parse_args()
    from src.eda.surface_ios import run_local as RL     # the current best's fit routine and settings

    plan = slots()
    names = [s for s in a.slots.split(",") if s] or list(plan)
    if a.arms:
        names = [s for s in names if plan[s]["arm"] in set(a.arms.split(","))]
    C.LOCAL.mkdir(parents=True, exist_ok=True)
    cache: dict[str, pd.DataFrame] = {}
    for slot in names:
        spec = plan[slot]
        f = cache.setdefault(spec["arm"], pd.read_parquet(C.ARM_FRAMES[spec["arm"]]))
        X_train, y, X_query, ids = frames(f, spec["train_to"], spec["query"])
        fp = T.fingerprint(X_train, y, X_query)
        out = C.LOCAL / f"{slot}.npz"
        if out.exists():
            if load(slot)[2] != fp:
                raise RuntimeError(f"{slot}: saved forecasts belong to other inputs")
            C.log(f"{slot}: saved, skipped")
            continue
        p_a, run = RL.fit_predict(X_train, y, X_query, spec["seed"])
        np.savez(out, p_a=p_a, match_id=np.asarray(ids, dtype=str), input_fingerprint=np.asarray(fp),
                 slot=np.asarray(slot))
        rec = {"slot": slot, **spec, **run, "train_shape": list(X_train.shape), "query_shape": list(X_query.shape),
               "input_fingerprint": fp, "finished_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
        with (C.LOCAL / "runs.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        C.log(f"{slot}: train {X_train.shape}, query {X_query.shape}, {run['fit_predict_seconds']} s, "
              f"peak {run['peak_vram_gb']} GB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
