"""Local TabPFN-3.5 fits of the arm "elosum": the current best's 58 inputs plus the pair's overall Elo sum R_A + R_B
(one context column, unchanged when A and B swap; the same column as the levels arm's lv_elo and I-084's modulator,
before standardisation). Settings, walk-forward design and payload as src/eda/feature_interactions/local_fits.py
(8 estimators, softmax temperature 0.9, pretraining limits ignored; season Y trained on 2013 .. Y-1 with results, each
season's matches predicted as stored and with A and B swapped; for 2025-2026 also the Polymarket queries "early" (the
price 24 hours before the listed start in place of odds_logit) and "late" (30 minutes)).

The placebo arm "elosum_perm" (--arm elosum_perm) replaces the column by the same values permuted within tour x
season (one fixed permutation, seed 20261007): the same distribution, no link to the match.

Reads no result of a predicted season: a season's fit trains only on earlier seasons. Writes
data/studies/pair_strength/local/<arm>__<season>__seed<k>.npz, never refitting a finished file.

Runs in the `tennis-tabpfn-local` env, started through src/eda/pair_strength/launch_when_free.sh (it waits until no
other local-env process is alive, the card's sharing rule):
    bash src/eda/pair_strength/launch_when_free.sh --seasons 2014-2024 --seeds 0-2
    bash src/eda/pair_strength/launch_when_free.sh --seasons 2025-2026 --seeds 0-7
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

from src.eda.feature_interactions import common as FC  # noqa: E402
from src.eda.feature_interactions.arms import base_inputs  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

ARM = "elosum"
OUT = ROOT / "data" / "studies" / "pair_strength" / "local"
PIECES = ROOT / "data" / "studies" / "surface_elo_pieces" / "pieces.parquet"
PRICE_SEASONS = (2025, 2026)


def load_frame(permuted: bool = False) -> tuple[pd.DataFrame, list[str], dict[str, str], dict[str, str]]:
    """The model frame with in_elo_sum = R_A + R_B (Elo pieces, the same ratings as in_elo_overall); with permuted,
    the placebo: the column permuted within tour x season (seed 20261007)."""
    f = pd.read_parquet(FC.MODEL_FRAME)
    f["match_id"] = f["match_id"].astype(str)
    p = pd.read_parquet(PIECES, columns=["match_id", "R_a", "R_b"])
    p["match_id"] = p["match_id"].astype(str)
    g = f[["match_id"]].merge(p, on="match_id", how="left", validate="one_to_one")
    f["in_elo_sum"] = (g["R_a"] + g["R_b"]).to_numpy(float)
    if not np.isfinite(f["in_elo_sum"]).all():
        raise RuntimeError("matches without an Elo sum")
    check = f["in_elo_overall"].to_numpy(float) - (g["R_a"] - g["R_b"]).to_numpy(float) * np.log(10) / 400
    if np.nanmax(np.abs(check)) > 1e-6:
        raise RuntimeError("the Elo pieces disagree with the model's elo_overall input")
    if permuted:
        rng = np.random.default_rng(20261007)
        v = f["in_elo_sum"].to_numpy(float).copy()
        for _, ix in f.groupby(["tour", "season"]).indices.items():
            v[ix] = v[ix[rng.permutation(len(ix))]]
        f["in_elo_sum"] = v
    names, kinds, partners = base_inputs()
    cols = names + ["elo_sum"]
    kinds = {**kinds, "elo_sum": "context"}
    return f, cols, kinds, partners


def flip(X: pd.DataFrame, kinds: dict[str, str], partners: dict[str, str]) -> pd.DataFrame:
    """The same matches with A and B swapped: differences negated, pairs exchanged, context (elo_sum too) unchanged."""
    out = X.copy()
    anti = [c for c in X.columns if kinds[c] == "diff"]
    out[anti] = -X[anti]
    for c in X.columns:
        if kinds[c] == "pair":
            out[c] = X[partners[c]].to_numpy()
    return out


def matrix(f: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame({c: f[f"in_{c}"].to_numpy(dtype="float64") for c in cols})


def wait_for_memory(need_gb: float = 12.0, patience_s: int = 6 * 3600) -> float:
    import torch
    t0, last = time.monotonic(), -1e9
    while True:
        free = torch.cuda.mem_get_info()[0] / 2**30
        if free >= need_gb:
            return free
        if time.monotonic() - t0 > patience_s:
            raise RuntimeError(f"under {need_gb} GB free for {patience_s} s ({free:.1f} GB)")
        if time.monotonic() - last > 300:
            FC.log(f"waiting for GPU memory: {free:.1f} GB free")
            last = time.monotonic()
        time.sleep(20)


def main() -> int:
    import torch
    from src.eda.tabpfn_local import runtime
    args = sys.argv[1:]
    lo, hi = (args[args.index("--seasons") + 1].split("-") if "--seasons" in args else ("2014", "2024"))
    spec = args[args.index("--seeds") + 1] if "--seeds" in args else "0-2"
    a, _, b = spec.partition("-")
    seeds = tuple(range(int(a), int(b) + 1)) if b else tuple(int(s) for s in spec.split(","))
    arm = args[args.index("--arm") + 1] if "--arm" in args else ARM
    if arm not in (ARM, f"{ARM}_perm"):
        raise SystemExit(f"unknown arm {arm}")
    OUT.mkdir(parents=True, exist_ok=True)
    f, cols, kinds, partners = load_frame(permuted=arm.endswith("_perm"))
    X_all = matrix(f, cols)
    if not np.allclose(flip(flip(X_all, kinds, partners), kinds, partners).to_numpy(), X_all.to_numpy(), equal_nan=True):
        raise RuntimeError("flip is not an involution")
    ep = pd.read_parquet(FC.EARLY, columns=["match_id", "has_early", "p_early_a", "p_close_a"])
    ep["match_id"] = ep["match_id"].astype(str)
    for season in range(int(lo), int(hi) + 1):
        tr = f["season"].between(FC.TRAIN_FROM, season - 1).to_numpy()
        te = (f["season"] == season).to_numpy()
        X_train, y_train = X_all[tr].reset_index(drop=True), f.loc[tr, "a_won"].astype("int64").to_numpy()
        X_test, ids = X_all[te].reset_index(drop=True), f.loc[te, "match_id"].to_numpy()
        qs = {"td": (pd.concat([X_test, flip(X_test, kinds, partners)], ignore_index=True), ids)}
        if season in PRICE_SEASONS:
            e = ep.set_index("match_id").reindex(ids)
            ok = e["has_early"].fillna(False).to_numpy(bool)
            for name, col in (("early", "p_early_a"), ("late", "p_close_a")):
                Xq = X_test[ok].reset_index(drop=True).copy()
                Xq["odds_logit"] = logit(np.clip(e[col].to_numpy(dtype=float)[ok], FC.EPS, 1 - FC.EPS))
                qs[name] = (pd.concat([Xq, flip(Xq, kinds, partners)], ignore_index=True), ids[ok])
        names = list(qs)
        X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
        for seed in seeds:
            path = OUT / f"{arm}__{season}__seed{seed}.npz"
            if path.exists():
                continue
            free_gb = wait_for_memory()
            clf = runtime.classifier(**FC.CONFIG, random_state=seed)
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
            meta = {"arm": arm, "season": season, "seed": seed, "config": {**FC.CONFIG, "random_state": seed},
                    "train_shape": list(X_train.shape), "query_rows": {n: int(len(qs[n][0])) for n in names},
                    "columns": list(X_train.columns), "fingerprint": T.fingerprint(X_train, y_train, X_query),
                    "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
                    "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                    "checkpoint": str(clf.model_path), "device": torch.cuda.get_device_name(0)}
            tmp = path.with_name(path.name + ".tmp.npz")
            np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
            tmp.replace(path)
            FC.log(f"{path.name}: {secs:.0f} s, peak {meta['peak_gpu_gb']} GB, queries {meta['query_rows']}")
            del clf
            torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
