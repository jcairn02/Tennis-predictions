"""EXPLORATORY, after the one-shot test (ledger row 13): why did the elosum arm's development gain not carry over to
2025-2026? One process suspect, checked descriptively; nothing here is confirmatory.

The suspect: Elo inflation. The raw sum R_A + R_B drifts upward over the seasons, so test-season pairs sit at the top
of, or beyond, the range TabPFN was trained on.

    1. Result-free: the Elo sum's mean by tour and season, and the share of each season's matches above the training
       rows' 95th and 99th percentiles (training = 2013 .. Y-1, per tour).
    2. Reads 2025-2026 results: H2's paired gain (the arm against the model, seeds 0-7 each, decided calibration) by
       pair-strength fifth (edges per tour on 2014-2021) and for the matches above the training 95th percentile.

    ./python.sh src/eda/pair_strength/explore_test.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.pair_strength import common as C  # noqa: E402
from src.eda.pair_strength import final_test as FT  # noqa: E402


def main() -> int:
    warnings.simplefilter("ignore")
    allf = FT.frame(range(2013, 2027), with_results=False, with_players=False)
    v, t, s = allf["pr_elo_sum"].to_numpy(float), allf["tour"].to_numpy(), allf["season"].to_numpy()
    out = {"mean_by_tour_season": allf.groupby(["tour", "season"])["pr_elo_sum"].mean().round(1).unstack().to_dict()}
    beyond = {}
    for Y in (2022, 2023, 2024, 2025, 2026):
        for tour in C.TOURS:
            tr = (t == tour) & (s < Y)
            te = (t == tour) & (s == Y)
            q95, q99 = np.quantile(v[tr], [0.95, 0.99])
            beyond[f"{tour} {Y}"] = {"share_above_train_q95": float((v[te] > q95).mean()),
                                     "share_above_train_q99": float((v[te] > q99).mean())}
    out["beyond_training_range"] = beyond
    C.log(f"beyond training range: {beyond}")
    # reads 2025-2026 results (exploratory)
    f = FT.population(with_results=True)
    K = FT.constants()
    A = FT.deployed_arms(f)
    tour = f["tour"].to_numpy()
    edges = {}
    dev = FT.frame(range(2014, 2022), with_results=False, with_players=False)
    for tr in C.TOURS:
        edges[tr] = np.quantile(dev.loc[dev["tour"] == tr, "pr_elo_sum"], [0.2, 0.4, 0.6, 0.8])
    q = np.where(tour == "atp", np.digitize(f["pr_elo_sum"], edges["atp"]), np.digitize(f["pr_elo_sum"], edges["wta"]))
    out["H2_by_fifth"] = {f"fifth {b + 1}": FT.paired_test(f, A["model"]["p"], A[FT.ARM]["p"], q == b) for b in range(5)}
    hi = np.zeros(len(f), bool)
    for Y in FT.TEST:
        for tr in C.TOURS:
            q95 = np.quantile(v[(t == tr) & (s < Y)], 0.95)
            k = (f["season"] == Y).to_numpy() & (tour == tr)
            hi[k] = f["pr_elo_sum"].to_numpy(float)[k] > q95
    out["H2_above_train_q95"] = FT.paired_test(f, A["model"]["p"], A[FT.ARM]["p"], hi)
    out["H2_below_train_q95"] = FT.paired_test(f, A["model"]["p"], A[FT.ARM]["p"], ~hi)
    for k, r in {**out["H2_by_fifth"], "above q95": out["H2_above_train_q95"],
                 "below q95": out["H2_below_train_q95"]}.items():
        C.log(f"H2 {k:10s} n {r['n']:5d} {r['gain']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]")
    out["key"] = ("EXPLORATORY (after the pre-registered run). Gains in mLL per match, positive = the elosum arm has the "
                  "lower log loss (better); 95% intervals over four-week blocks; spanning 0 = tie")
    C.write_json(C.OUT / "final" / "explore_test.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
