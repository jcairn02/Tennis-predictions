"""One LOCAL TabPFN-3.5 fit on the leak-proof refit's exact upload: no thinking, no API tokens, scored the same way.

The leak-proof study (src/eda/tabpfn_leakproof/) made one paid TabPFN-3.5-Thinking fit: 39,918 main-tour training
matches of 2013-2021, and the 23,819 test matches of 2022-2026 predicted in both orientations. This script fits the
open-weight checkpoint tabpfn-v3.5-20260909 on the same rows and the same 54 inputs, with the paid fit's settings except
thinking (8 estimators, softmax temperature 0.9, seed 0, pretraining limits ignored, no categorical hints), on the local
GPU, and scores it like the leak-proof study: per tour, 2022-2026 and each season, against the closing odds recalibrated
on the training matches ("market") and against the paid thinking fit ("thinking"), with paired 95% intervals over
four-week blocks of tournament dates.

Two things differ from the paid fit and one run cannot separate them: thinking (an API-only search over the fit) and the
inference code (the open package here, Prior Labs' hosted engine there).

    ./python_tabpfn_local.sh src/eda/tabpfn_local/leakproof_local.py

Writes data/studies/tabpfn_local/leakproof/: predictions.npz, run.json, results.json, test_predictions.parquet.
"""
from __future__ import annotations

import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_leakproof import common as C  # noqa: E402
from src.eda.tabpfn_local import runtime  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = ROOT / "data" / "studies" / "tabpfn_local" / "leakproof"
# the paid fit's settings (src/eda/tabpfn_leakproof/guard.py CONFIG) without thinking; runtime.classifier() adds the
# checkpoint, the GPU, memory_saving_mode=True and the attention fix
CONFIG = {"n_estimators": 8, "softmax_temperature": 0.9, "random_state": 0, "ignore_pretraining_limits": True}
PAIRS = [("market", "local"), ("thinking", "local")]
WINDOWS = [("2022-2026", 2022, 2026)] + [(str(y), y, y) for y in range(2022, 2027)]


def fit_predict(X_train: pd.DataFrame, y_train: np.ndarray, X_query: pd.DataFrame) -> tuple[np.ndarray, dict]:
    import torch

    clf = runtime.classifier(**CONFIG)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.monotonic()
    clf.fit(X_train, y_train)
    t_fit = time.monotonic() - t0
    proba = clf.predict_proba(X_query)
    t_all = time.monotonic() - t0
    if [int(c) for c in clf.classes_] != [0, 1] or proba.shape != (len(X_query), 2) or not np.isfinite(proba).all() \
            or not np.allclose(proba.sum(axis=1), 1.0, atol=1e-6):
        raise RuntimeError("invalid probabilities")
    run = {"checkpoint": clf.model_path, "config": CONFIG, "device": torch.cuda.get_device_name(0),
           "memory_saving_mode": clf.memory_saving_mode, "memory_fraction_cap": runtime.MEMORY_FRACTION,
           "versions": {"tabpfn": version("tabpfn"), "torch": torch.__version__},
           "train_shape": list(X_train.shape), "query_shape": list(X_query.shape),
           "fit_seconds": round(t_fit, 1), "fit_predict_seconds": round(t_all, 1),
           "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2)}
    return proba[:, 1], run


def frame(ids: pd.DataFrame, p_a: np.ndarray) -> pd.DataFrame:
    """The local forecast, symmetrised, beside the leak-proof study's market and thinking forecasts."""
    n = len(ids) // 2
    match = ids["match_id"].to_numpy()
    if not np.array_equal(match[:n], match[n:]):
        raise RuntimeError("the second half of the query is not the first half's matches swapped")
    new = pd.DataFrame({"match_id": match[:n], "p_local_orig": p_a[:n], "p_local_flip": p_a[n:],
                        "p_local": T.symmetrize(p_a[:n], p_a[n:])})
    old = pd.read_parquet(C.OUT / "test_predictions.parquet",
                          columns=["match_id", "tour", "year", "tournament_date", "a_won", "p_market", "p_leakproof"])
    f = old.rename(columns={"p_leakproof": "p_thinking"}).merge(new, on="match_id", how="inner", validate="one_to_one")
    if len(f) != n or f[["p_market", "p_thinking", "p_local"]].isna().any().any():
        raise RuntimeError("the local fit's query rows are not the leak-proof study's test matches")
    return f


def agreement(g: pd.DataFrame) -> dict:
    a, b = g["p_thinking"].to_numpy(), g["p_local"].to_numpy()
    la, lb = logit(np.clip(a, T.EPS, 1 - T.EPS)), logit(np.clip(b, T.EPS, 1 - T.EPS))
    d = np.abs(a - b)
    gap = np.abs(g["p_local_orig"].to_numpy() - (1 - g["p_local_flip"].to_numpy()))
    return {"matches": int(len(g)), "log_odds_correlation": float(np.corrcoef(la, lb)[0, 1]),
            "mean_abs_prob_diff": float(d.mean()), "p90_abs_prob_diff": float(np.quantile(d, 0.9)),
            "favourite_changes": int(((a > 0.5) != (b > 0.5)).sum()), "local_orientation_gap_mean": float(gap.mean())}


def score(f: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    rows = []
    for tour in ("atp", "wta", "both"):
        g0 = f if tour == "both" else f[f["tour"] == tour]
        for label, lo, hi in WINDOWS:
            g = g0[g0["year"].between(lo, hi)]
            if g.empty:
                continue
            y, dates = g["a_won"].to_numpy(), g["tournament_date"].to_numpy()
            for base, model in PAIRS:
                c = T.compare(T.ll(g[f"p_{base}"].to_numpy(), y), T.ll(g[f"p_{model}"].to_numpy(), y), dates)
                rows.append({"tour": tour, "window": label, "base": base, "model": model, "matches": c["n"],
                             "gain": c["gain"], "lo": c["lo"], "hi": c["hi"], "week_lo": c["week_lo"],
                             "week_hi": c["week_hi"]})
    R = pd.DataFrame(rows)
    groups = list(f.groupby("tour")) + [("both", f)]
    res = {"key": "milli-log-loss; positive = the second-named forecast (local) has the lower log loss, i.e. is "
                  "better; a 95% interval spanning 0 is a tie",
           "log_loss": {tour: {name: float(T.ll(g[f"p_{name}"].to_numpy(), g["a_won"].to_numpy()).mean())
                               for name in ("market", "thinking", "local")} for tour, g in groups},
           "comparisons": R.to_dict("records"), "agreement_with_thinking": {tour: agreement(g) for tour, g in groups}}
    return res, R


def main() -> int:
    X_train, y_train, X_query, ids, manifest = C.load_upload()
    C.log(f"upload verified: X_train {X_train.shape}, X_query {X_query.shape}, fingerprint "
          f"{manifest['input_fingerprint'][:16]}...")
    p_a, run = fit_predict(X_train, y_train.astype("int64"), X_query)
    run["input_fingerprint"] = manifest["input_fingerprint"]
    C.log(f"fit {run['fit_seconds']} s, fit + predict {run['fit_predict_seconds']} s, peak VRAM {run['peak_vram_gb']} GB")
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT / "predictions.npz", p_a=p_a, match_id=ids["match_id"].to_numpy(),
             orientation=ids["orientation"].to_numpy())
    C.write_json(OUT / "run.json", run)
    f = frame(ids, p_a)
    res, R = score(f)
    C.write_json(OUT / "results.json", res)
    f.to_parquet(OUT / "test_predictions.parquet", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(R[R["window"].isin(["2022-2026", "2026"])].round(2).to_string(index=False))
        print(pd.DataFrame(res["agreement_with_thinking"]).round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
