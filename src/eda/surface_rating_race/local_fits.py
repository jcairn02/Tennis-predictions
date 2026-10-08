"""Local TabPFN-3.5 fits of the race (GPU, no API tokens): the `tennis-tabpfn-local` env through
src/eda/tabpfn_local/runtime.py (its attention fix and memory cap), the Elo-pieces study's settings (8 estimators,
softmax temperature 0.9, pretraining limits ignored), seeds 0, 1, 2.

For each arm (arms.py), walk-forward season Y in 2019-2026 (training on the main-tour matches with odds of 2013 to Y - 1)
and seed, one fit predicts:

    td      every season-Y match, as stored and with A and B swapped (the scorer symmetrises)
    early   arms with the odds, 2025-2026: the matches with Polymarket prices, odds_logit replaced by the price 24 hours
            before the listed start (the deployment the owner plans: a bet before the close)
    late    the same with the price 30 minutes before the listed start

One fit at a time on the card: before each fit the runner waits until no other process of the local env is running (other
sessions fit on the same GPU) and 12 GB are free. A finished (arm, season, seed) is saved to
data/studies/surface_rating_race/local/ and never refitted.
Run: ./python_tabpfn_local.sh src/eda/surface_rating_race/local_fits.py --arms base,elo_off [--seasons 2019-2026]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_rating_race import arms as A  # noqa: E402
from src.eda.surface_rating_race import common as C  # noqa: E402
from src.eda.tabpfn_local import runtime  # noqa: E402

LOCAL = C.OUT / "local"
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "ignore_pretraining_limits": True}
PRICE_SEASONS = (2025, 2026)
EPS = 1e-6


def other_local_processes() -> list[int]:
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object { $_.CommandLine -like '*tennis-tabpfn-local*' } | ForEach-Object { $_.ProcessId }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                         timeout=120).stdout
    return [int(x) for x in out.split() if x.strip().isdigit() and int(x) != os.getpid()]


def wait_for_card(need_gb: float = 12.0, patience_s: int = 4 * 3600) -> float:
    import torch
    t0, last_note = time.monotonic(), -1e9
    while True:
        others = other_local_processes()
        free = torch.cuda.mem_get_info()[0] / 2**30
        if not others and free >= need_gb:
            return free
        if time.monotonic() - t0 > patience_s:
            raise RuntimeError(f"the card stayed busy for {patience_s} s (other processes {others}, {free:.1f} GB free)")
        if time.monotonic() - last_note > 300:
            C.log(f"waiting for the card: other local-env processes {others}, {free:.1f} GB free")
            last_note = time.monotonic()
        time.sleep(30)


def queries(frame: pd.DataFrame, ep: pd.DataFrame, arm: str, season: int, X_test: pd.DataFrame,
            ids: np.ndarray) -> dict[str, tuple[pd.DataFrame, np.ndarray]]:
    out = {"td": (pd.concat([X_test, A.flip(X_test)], ignore_index=True), ids)}
    if "odds_logit" in X_test.columns and season in PRICE_SEASONS:
        e = ep.set_index("match_id").reindex(ids)
        ok = e["has_early"].fillna(False).to_numpy(bool)
        for name, col in (("early", "p_early_a"), ("late", "p_close_a")):
            Xq = X_test[ok].reset_index(drop=True).copy()
            Xq["odds_logit"] = logit(np.clip(e[col].to_numpy(dtype=float)[ok], EPS, 1 - EPS))
            out[name] = (pd.concat([Xq, A.flip(Xq)], ignore_index=True), ids[ok])
    return out


def main() -> int:
    import torch
    args = sys.argv[1:]
    arms = args[args.index("--arms") + 1].split(",")
    lo, hi = (args[args.index("--seasons") + 1].split("-") if "--seasons" in args else ("2019", "2026"))
    seasons = range(int(lo), int(hi) + 1)
    unknown = [a for a in arms if a not in A.ARMS]
    if unknown:
        raise SystemExit(f"unknown arms {unknown}")
    LOCAL.mkdir(parents=True, exist_ok=True)
    frame = A.load_frame(with_offset=any(a in A.NEEDS_OFFSET_TTT for a in arms),
                         with_sprof=any(a in A.NEEDS_SPROF for a in arms))
    ep = pd.read_parquet(C.EARLY, columns=["match_id", "has_early", "p_early_a", "p_close_a"])
    for arm in arms:
        missing = [c for c in A.ARMS[arm] if not np.isfinite(frame[f"x_{c}"].to_numpy(dtype=float)).any()]
        if missing:
            raise RuntimeError(f"{arm}: inputs without any value: {missing}")
        for season in seasons:
            for seed in C.SEEDS:
                path = LOCAL / f"{arm}__{season}__seed{seed}.npz"
                if path.exists():
                    continue
                X_train, y_train, X_test, ids = A.job_data(frame, arm, season)
                qs = queries(frame, ep, arm, season, X_test, ids)
                names = list(qs)
                X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
                free_gb = wait_for_card()
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
                        "columns": list(X_train.columns), "seconds": round(secs, 1), "gpu_free_gb_before": round(free_gb, 1),
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
