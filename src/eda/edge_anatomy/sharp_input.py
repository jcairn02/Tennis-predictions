"""The current model fed the sharpest close (edge-anatomy study, added 12 Oct 2026 after the sharpest-close check showed
the women's model behind the exchanges in 2026).

Season 2026 only, seeds 0-3, the instance's own training rows (2013-2025) and settings: one TabPFN fit per seed predicts
two query blocks in one call:
    orig   the season's matches as the instance stored them (must equal the instance's stored forecasts: the check)
    sharp  the same matches with the odds input replaced by the exchange consensus: the mean log-odds of Betfair's
           close and Polymarket's price 30 minutes before the listed start where both exist, the one that exists
           otherwise, the instance's own input where neither does
Both blocks are queried as stored and flipped (symmetrised later). Writes data/studies/edge_anatomy/sharp_input/
seed<k>.npz. Queries only: the training labels are seasons <= 2025, and no 2026 result is read here.
Run: ./python_tabpfn_local.sh src/eda/edge_anatomy/sharp_input.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import fits as EF  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.training_window import fits as TWF  # noqa: E402

OUT = E.OUT / "sharp_input"
SEASON = 2026


def sharp_logit(ids: np.ndarray, current: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    o = pd.read_parquet(E.INSTANCE / "odds_sources.parquet", columns=["match_id", "p_bfe", "p_pm_m30"])
    o = o.astype({"match_id": str}).set_index("match_id").reindex(ids)
    eps = C.EPS
    lb = np.log(np.clip(o["p_bfe"].to_numpy(float), eps, 1 - eps) / (1 - np.clip(o["p_bfe"].to_numpy(float), eps, 1 - eps)))
    lp = np.log(np.clip(o["p_pm_m30"].to_numpy(float), eps, 1 - eps) / (1 - np.clip(o["p_pm_m30"].to_numpy(float), eps, 1 - eps)))
    fb, fp = np.isfinite(lb), np.isfinite(lp)
    out = np.where(fb & fp, (lb + lp) / 2, np.where(fb, lb, np.where(fp, lp, current)))
    source = np.where(fb & fp, "both", np.where(fb, "betfair", np.where(fp, "polymarket", "own input")))
    return out, source


def main() -> int:
    import torch

    from src.eda.tabpfn_local import runtime
    frame = EF.load_frame()
    cols = E.input_names()
    X_train, y_train, X_test, ids = A.job_data(frame, cols, SEASON)
    ids = np.asarray(ids).astype(str)
    Xs = X_test.copy()
    Xs["odds_logit"], source = sharp_logit(ids, X_test["odds_logit"].to_numpy(float))
    q_orig = pd.concat([X_test, A.flip(X_test, EF.P)], ignore_index=True)
    q_sharp = pd.concat([Xs, A.flip(Xs, EF.P)], ignore_index=True)
    X_query = pd.concat([q_orig, q_sharp], ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"match_id": ids, "source": source}).to_csv(OUT / "sources.csv", index=False)
    for seed in E.SEEDS:
        path = OUT / f"seed{seed}.npz"
        if path.exists():
            continue
        free = TWF.wait_for_card(patience_s=12 * 3600, processes=False)
        clf = runtime.classifier(**C.CONFIG, random_state=seed)
        t0 = time.monotonic()
        clf.fit(X_train, y_train)
        p = clf.predict_proba(X_query)[:, 1]
        secs = time.monotonic() - t0
        k = len(q_orig)
        stored = E.INSTANCE / "fits" / f"model__{SEASON}__seed{seed}.npz"
        with np.load(stored, allow_pickle=False) as z:
            same = bool(np.array_equal(z["ids_td"].astype(str), ids))
            diff = float(np.abs(E.sym(z["p_td"], len(ids)) - E.sym(p[:k], len(ids))).max()) if same else np.inf
        meta = {"season": SEASON, "seed": seed, "seconds": round(secs, 1), "free_gb": round(free, 1),
                "train_shape": list(X_train.shape), "check_ids_equal": same, "check_max_abs_diff_orig": diff,
                "sources": {s: int((source == s).sum()) for s in np.unique(source)}}
        np.savez(path, p_orig=p[:k], p_sharp=p[k:], ids=ids, meta=np.asarray(json.dumps(meta)))
        E.log(f"seed {seed}: {secs:.0f} s; orig vs stored max |diff| {diff:.2e}")
        del clf
        torch.cuda.empty_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
