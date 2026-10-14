"""Bet timing, step 2b: does training the model on the price of the bet beat the plug-in? (local TabPFN-3.5 on the
GPU, no API tokens; the `tennis-tabpfn-local` env).

The decided model trains on closing prices, because no early prices exist for most of its training seasons. OddsTrader
holds BetOnline's opening line from 2018, so two arms can be trained on the same rows and differ only in their odds input:

    line_close   odds_logit = BetOnline's last line (margin-free), as the decided model trains on a close
    line_open    odds_logit = BetOnline's opening line

For test season Y both train on the frame's matches of 2018 .. Y - 1 that have both lines, with every input existing at
the opening quote (frame.py's known_bol_open), and are queried on season Y's matches of the same kind: "open" with the
opening line in the odds input (both arms), "close" with the last line (line_close). line_close fed the opening line is
the plug-in; line_open fed the opening line is the model a bettor could train if early prices existed for every
training season. Same 58 inputs, the decided settings, seeds 0-3; test seasons 2021-2026; queries stored and swapped.
One fit at a time; started and waiting as fits.py is. Saved to data/studies/bet_timing/local_lines/, never refitted.

    bash src/eda/bet_timing/run_when_free.sh src/eda/bet_timing/fits_lines.py --run [--seasons 2021-2026] [--seeds 0-3]
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

LOCAL = C.OUT / "local_lines"
ARMS = {"line_close": "p_bol_close", "line_open": "p_bol_open"}      # arm -> the training rows' odds input
QUERIES = {"line_close": ("open", "close"), "line_open": ("open",)}
TEST_SEASONS = tuple(range(2021, 2027))
FIRST = min(C.FRAME_SEASONS)


def fit_path(arm: str, season: int, seed: int) -> Path:
    return LOCAL / f"{arm}__{season}__seed{seed}.npz"


def eligible(prices: pd.DataFrame) -> pd.Index:
    """Matches with both BetOnline lines whose inputs all existed at the opening quote."""
    ok = (prices["known_bol_open"].astype(bool) & np.isfinite(prices["p_bol_open"]) &
          np.isfinite(prices["p_bol_close"]))
    return pd.Index(prices.loc[ok, "match_id"].astype(str))


def job_data(frame: pd.DataFrame, prices: pd.DataFrame, cols: list[str], arm: str, season: int):
    """(X_train, y_train, {query: (X stored then swapped, ids)}) for one arm and test season."""
    P = SC.DEFAULT
    keep = frame["match_id"].isin(eligible(prices)).to_numpy()
    pr = prices.set_index("match_id")
    tr = keep & frame["season"].between(FIRST, season - 1).to_numpy()
    te = keep & (frame["season"] == season).to_numpy()
    X_train = A.matrix(frame[tr], cols).reset_index(drop=True)
    X_train["odds_logit"] = C.lg(pr.loc[frame.loc[tr, "match_id"], ARMS[arm]].to_numpy(float))
    y_train = frame.loc[tr, "a_won"].astype("int64").to_numpy()
    ids = frame.loc[te, "match_id"].to_numpy().astype(str)
    X_test = A.matrix(frame[te], cols).reset_index(drop=True)
    qs = {}
    for q in QUERIES[arm]:
        Xq = X_test.copy()
        Xq["odds_logit"] = C.lg(pr.loc[ids, f"p_bol_{q}"].to_numpy(float))
        qs[q] = (pd.concat([Xq, A.flip(Xq, P)], ignore_index=True), ids)
    return X_train, y_train, qs


def run(seasons, seeds) -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    from src.eda.training_window.fits import wait_for_card
    P = SC.DEFAULT
    cols = A.arm_inputs("model", P)
    frame = A.load_frame([], P, labels=True)
    prices = pd.read_parquet(C.FRAME, columns=["match_id", "p_bol_open", "p_bol_close", "known_bol_open"])
    prices["match_id"] = prices["match_id"].astype(str)
    prices_sha = C.sha256_file(C.FRAME)
    LOCAL.mkdir(parents=True, exist_ok=True)
    for season in seasons:
        for arm in ARMS:
            todo = [k for k in seeds if not fit_path(arm, season, k).exists()]
            if not todo:
                continue
            X_train, y_train, qs = job_data(frame, prices, cols, arm, season)
            names = list(qs)
            X_query = pd.concat([qs[n][0] for n in names], ignore_index=True)
            for seed in todo:
                path = fit_path(arm, season, seed)
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
                meta = {"arm": arm, "odds_input": ARMS[arm], "season": season, "seed": seed,
                        "config": {**C.CONFIG, "random_state": seed}, "train_shape": list(X_train.shape),
                        "train_seasons": [FIRST, season - 1], "query_rows": {n: int(len(qs[n][0])) for n in names},
                        "columns": list(X_train.columns), "prices_sha256": prices_sha, "seconds": round(secs, 1),
                        "gpu_free_gb_before": round(free_gb, 1),
                        "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                        "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
                        "device": torch.cuda.get_device_name(0)}
                tmp = path.with_name(path.name + ".tmp.npz")
                np.savez(tmp, meta=np.asarray(json.dumps(meta)), **payload)
                tmp.replace(path)
                C.log(f"{path.name}: {secs:.0f} s, train {X_train.shape[0]}, queries {meta['query_rows']}")
                del clf
                torch.cuda.empty_cache()
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--run" in args:
        from src.eda.bet_timing.fits import parse_range
        seasons = parse_range(args[args.index("--seasons") + 1]) if "--seasons" in args else TEST_SEASONS
        seeds = parse_range(args[args.index("--seeds") + 1]) if "--seeds" in args else C.SEEDS
        return run(seasons, seeds)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
