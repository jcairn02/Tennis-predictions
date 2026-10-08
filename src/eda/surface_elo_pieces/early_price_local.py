"""Local TabPFN-3.5 fits for the early-price test (plan: docs/studies/surface_elo_pieces/early_price_plan.md). GPU, no API
tokens; runs in the `tennis-tabpfn-local` env through src/eda/tabpfn_local/runtime.py (its attention fix and memory cap).

For each walk-forward season Y in 2025 and 2026 (training on the main-tour matches with odds of 2013 to Y - 1, exactly
the confirmation's jobs) and seeds 0, 1, 2:

    base_noodds, primary_noodds   fitted without the odds; every season-Y match predicted as stored and swapped
    base, primary                 fitted with the closing odds, as in the confirmation; every season-Y match predicted
                                  with the tennis-data close (the agreement check against the paid API's forecasts),
                                  and the matches with Polymarket prices predicted with odds_logit replaced by the price
                                  24 hours before the listed start ("early") and by the price 30 minutes before ("close")

Settings: the confirmation's (8 estimators, softmax temperature 0.9, pretraining limits ignored), the seed varying.
One fit at a time. A finished (season, arm, seed) is saved to data/studies/surface_elo_pieces/local/ and never refitted.
Run: ./python_tabpfn_local.sh src/eda/surface_elo_pieces/early_price_local.py
"""
from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import arms as A  # noqa: E402
from src.eda.surface_elo_pieces import build_frames as BF  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.tabpfn_local import runtime  # noqa: E402

LOCAL = C.OUT / "local"
SEASONS = (2025, 2026)
SEEDS = (0, 1, 2)
ARMS = ("base_noodds", "primary_noodds", "base", "primary")
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}
EPS = 1e-6


def queries(frame: pd.DataFrame, ep: pd.DataFrame, arm: str, season: int) -> dict[str, tuple[pd.DataFrame, np.ndarray]]:
    """Named query blocks (each: the matches as stored, then swapped) and their match ids."""
    te = (frame["season"] == season).to_numpy()
    X = BF.matrix(frame, arm)[te].reset_index(drop=True)
    ids = frame.loc[te, "match_id"].to_numpy()
    out = {"td": (pd.concat([X, A.flip(X)], ignore_index=True), ids)}
    if "odds_logit" in X.columns:
        e = ep.set_index("match_id").reindex(ids)
        ok = e["has_early"].fillna(False).to_numpy(bool)
        for name, col in (("early", "p_early_a"), ("close", "p_close_a")):
            Xq = X[ok].reset_index(drop=True).copy()
            Xq["odds_logit"] = logit(np.clip(e[col].to_numpy(dtype=float)[ok], EPS, 1 - EPS))
            out[name] = (pd.concat([Xq, A.flip(Xq)], ignore_index=True), ids[ok])
    return out


def main() -> int:
    import torch
    LOCAL.mkdir(parents=True, exist_ok=True)
    frame = pd.read_parquet(C.OUT / "frame.parquet")
    ep = pd.read_parquet(C.OUT / "early_price_frame.parquet", columns=["match_id", "has_early", "p_early_a", "p_close_a"])
    for season in SEASONS:
        for arm in ARMS:
            for seed in SEEDS:
                path = LOCAL / f"{arm}__{season}__seed{seed}.npz"
                if path.exists():
                    C.log(f"{path.name}: saved, skipped")
                    continue
                X_train, y_train, _, _ = BF.job_data(frame, arm, season)
                qs = queries(frame, ep, arm, season)
                names = list(qs)
                X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
                clf = runtime.classifier(**CONFIG, random_state=seed)
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
                meta = {"arm": arm, "season": season, "seed": seed, "config": {**CONFIG, "random_state": seed},
                        "train_shape": list(X_train.shape), "query_rows": {n: int(len(qs[n][0])) for n in names},
                        "columns": list(X_train.columns), "seconds": round(secs, 1),
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


if __name__ == "__main__":
    sys.exit(main())
