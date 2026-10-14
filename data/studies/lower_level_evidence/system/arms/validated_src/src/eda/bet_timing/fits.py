"""Bet timing, step 2: the current best model's first stage queried at every price (local TabPFN-3.5 on the GPU, no API
tokens; the `tennis-tabpfn-local` env).

Job (Y, seed): the 58-input model (serve_speed_tabpfn.arms, arm "model"), trained on the frame's matches of 2013 .. Y - 1
with the closing odds as its odds input, as decided. Season Y's matches are queried once as stored and once per price
block with odds_logit replaced by the log-odds of that price (frame.py); every query is stored and then with A and B
swapped (the scorer symmetrises):

    td                 the frame as stored (the market-average close): checked against the stored fits of the same seed
    bol_open           BetOnline's opening line, margin removed proportionally (as the model's own odds input)
    bol_close          BetOnline's last line
    pm_h48 .. pm_m30   Polymarket's price 48 hours .. 30 minutes before the listed start (2025-2026)

A model trained on closing prices and fed the price of the moment is what a bettor before the close would run: no early
prices exist for the training seasons before 2018, so the model cannot be trained on them.

Settings: the decided ones (8 estimators, softmax temperature 0.9, pretraining limits ignored). One fit at a time; before
each fit the runner waits for 12 GB of free card memory only. It must be STARTED only when no other process of the local
env runs (src/eda/bet_timing/run_when_free.sh does that): other sessions' runners wait while any local-env process
exists, so a runner of ours that waited on them in turn would deadlock with them. A finished fit is saved to
data/studies/bet_timing/local/ and never refitted.

    bash src/eda/bet_timing/run_when_free.sh src/eda/bet_timing/fits.py --run [--seasons 2024-2026] [--seeds 0-3]
    bash src/eda/bet_timing/run_when_free.sh src/eda/bet_timing/fits.py --run --set consensus   # consensus.py's prices
    ./python.sh src/eda/bet_timing/fits.py --check      # CPU: each fit's td block against the stored fit of its seed

--set consensus queries the same fits (same training, seeds and settings) with consensus.py's sharp-consensus prices
(C.CONSENSUS_BLOCKS) and saves them to data/studies/bet_timing/local_consensus/; the frame as stored is not re-queried.
"""
from __future__ import annotations

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

from src.eda.bet_timing import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402

ARM = "model"
STORED = {k: SC.DEFAULT.race_local for k in (0, 1, 2)} | {3: SC.DEFAULT.fi_local}   # the stored fits of each seed
CHECK_TOL = 1e-3          # the stored fits had other query blocks; GPU batches may round differently (bfloat16)


# Price sets: (prices file, its blocks, the fits' folder, whether the frame as stored is queried too)
SETS = {"main": (C.FRAME, C.PRICE_BLOCKS, C.LOCAL, True),
        "consensus": (C.CONSENSUS_FRAME, C.CONSENSUS_BLOCKS, C.LOCAL_CONSENSUS, False)}   # consensus.py


def fit_path(season: int, seed: int, price_set: str = "main") -> Path:
    return SETS[price_set][2] / f"{ARM}__{season}__seed{seed}.npz"


def queries(prices: pd.DataFrame, X_test: pd.DataFrame, ids: np.ndarray, blocks=C.PRICE_BLOCKS,
            with_td: bool = True) -> dict[str, tuple[pd.DataFrame, np.ndarray]]:
    """{block: (query rows: stored then swapped, the block's match ids)}; a price block holds the matches it prices."""
    P = SC.DEFAULT
    out = {"td": (pd.concat([X_test, A.flip(X_test, P)], ignore_index=True), ids)} if with_td else {}
    f = prices.set_index("match_id").reindex(ids)
    for b in blocks:
        p = f[f"p_{b}"].to_numpy(dtype=float)
        ok = np.isfinite(p)
        if not ok.any():
            continue
        Xq = X_test[ok].reset_index(drop=True).copy()
        Xq["odds_logit"] = C.lg(p[ok])
        out[b] = (pd.concat([Xq, A.flip(Xq, P)], ignore_index=True), ids[ok])
    return out


def load_prices(path: Path = C.FRAME, blocks=C.PRICE_BLOCKS) -> pd.DataFrame:
    prices = pd.read_parquet(path, columns=["match_id"] + [f"p_{b}" for b in blocks])
    prices["match_id"] = prices["match_id"].astype(str)
    return prices


def run(seasons, seeds, price_set: str = "main") -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    from src.eda.training_window.fits import wait_for_card
    P = SC.DEFAULT
    prices_path, blocks, folder, with_td = SETS[price_set]
    cols = A.arm_inputs(ARM, P)
    if len(cols) != 58 or "odds_logit" not in cols:
        raise RuntimeError("the model's 58 inputs, odds included, are expected")
    frame = A.load_frame([], P, labels=True)
    if not A.check_flip(frame, cols, P):
        raise RuntimeError("flip is not an involution")
    prices = load_prices(prices_path, blocks)
    frame_sha, prices_sha = C.sha256_file(C.MODEL_FRAME), C.sha256_file(prices_path)
    folder.mkdir(parents=True, exist_ok=True)
    for season in seasons:
        todo = [k for k in seeds if not fit_path(season, k, price_set).exists()]
        if not todo:
            continue
        X_train, y_train, X_test, ids = A.job_data(frame, cols, season)
        qs = queries(prices, X_test, ids.astype(str), blocks, with_td)
        names = list(qs)
        if not names:
            continue
        X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
        for seed in todo:
            path = fit_path(season, seed, price_set)
            free_gb = wait_for_card(need_gb=12.0, patience_s=12 * 3600, processes=False)
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
            meta = {"arm": ARM, "season": season, "seed": seed, "config": {**C.CONFIG, "random_state": seed},
                    "train_shape": list(X_train.shape), "train_seasons": [C.TRAIN_FROM, season - 1],
                    "query_rows": {n: int(len(qs[n][0])) for n in names}, "columns": list(X_train.columns),
                    "model_frame_sha256": frame_sha, "prices_sha256": prices_sha, "seconds": round(secs, 1),
                    "gpu_free_gb_before": round(free_gb, 1),
                    "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                    "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
            tmp.replace(path)
            C.log(f"{path.name}: {secs:.0f} s, peak {meta['peak_gpu_gb']} GB, queries {meta['query_rows']}")
            del clf
            torch.cuda.empty_cache()
    return 0


def check() -> dict:
    """Each saved fit's td block against the stored fit of the same season and seed (the rating race's seeds 0-2, feature
    interactions' seed 3): same ids in the same order, and the probabilities equal to within CHECK_TOL."""
    rows = []
    for path in sorted(C.LOCAL.glob(f"{ARM}__*__seed*.npz")):
        meta = json.loads(str(np.load(path, allow_pickle=False)["meta"]))
        season, seed = meta["season"], meta["seed"]
        stored = STORED[seed] / path.name
        with np.load(path, allow_pickle=False) as a, np.load(stored, allow_pickle=False) as b:
            same_ids = bool(np.array_equal(a["ids_td"].astype(str), b["ids_td"].astype(str)))
            d = np.abs(a["p_td"] - b["p_td"]) if same_ids else np.array([np.inf])
        rows.append({"season": season, "seed": seed, "stored": str(stored.relative_to(ROOT)), "same_ids": same_ids,
                     "max_abs_diff": float(d.max()), "mean_abs_diff": float(d.mean()),
                     "ok": same_ids and float(d.max()) <= CHECK_TOL})
    out = {"what": "each fit's td block (the frame as stored) against the stored fit of the same season and seed",
           "tolerance": CHECK_TOL, "fits": len(rows), "all_ok": bool(rows) and all(r["ok"] for r in rows),
           "rows": rows}
    C.write_json(C.OUT / "fits_check.json", out)
    return out


def parse_range(text: str) -> tuple[int, ...]:
    a, _, b = text.partition("-")
    return tuple(range(int(a), int(b) + 1)) if b else tuple(int(x) for x in text.split(","))


def main() -> int:
    args = sys.argv[1:]
    if "--check" in args:
        r = check()
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=1))
        for row in r["rows"]:
            print(row)
        return 0 if r["all_ok"] else 1
    if "--run" in args:
        seasons = parse_range(args[args.index("--seasons") + 1]) if "--seasons" in args else C.SEASONS[::-1]
        seeds = parse_range(args[args.index("--seeds") + 1]) if "--seeds" in args else C.SEEDS
        price_set = args[args.index("--set") + 1] if "--set" in args else "main"
        return run(seasons, seeds, price_set)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
