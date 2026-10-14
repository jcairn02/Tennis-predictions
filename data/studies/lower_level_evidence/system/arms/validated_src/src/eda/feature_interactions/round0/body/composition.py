"""Round 0, body-and-schedule brainstormer: how the point -> game -> set -> match composition modulates a fatigue
decrement. Pure model arithmetic with Stage 2's iid model (read-only import); no match data, no outcomes, no odds.

Prints, for a few serve-point probabilities and both formats:
  * hold probability and its slope d hold / d p;
  * S_A = d logit P(A wins match) / d p_A and S_B = -d logit P(A wins) / d p_B (finite differences);
  * the expected number of points and sets (Monte Carlo with Stage 2's simulator, fixed seed);
  * the logit change when A's serve-point probability falls by delta = 0.01 for the whole match.

Run: ./python.sh src/eda/feature_interactions/round0/body/composition.py
Writes: data/studies/feature_interactions/round0/body/composition.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.predictability_diagnostic import stage2_iid as I  # noqa: E402  (read-only import)

OUT = ROOT / "data/studies/feature_interactions/round0/body"
H = 1e-4


def logit(x):
    x = np.clip(x, 1e-12, 1 - 1e-12)
    return np.log(x / (1 - x))


def main() -> None:
    res: dict = {"hold": {}, "matchups": []}
    for p in [0.55, 0.60, 0.62, 0.64, 0.66, 0.70, 0.75]:
        h = float(I.game(p))
        slope = float((I.game(p + H) - I.game(p - H)) / (2 * H))
        res["hold"][f"{p:.2f}"] = {"hold": round(h, 4), "d_hold_dp": round(slope, 3)}
    pairs = [(0.64, 0.64), (0.70, 0.70), (0.58, 0.58), (0.66, 0.62), (0.70, 0.60), (0.60, 0.70), (0.62, 0.56),
             (0.56, 0.56), (0.60, 0.60)]
    for pa, pb in pairs:
        for bo in (3, 5):
            p = float(I.match_win(pa, pb, best_of=bo))
            sa = float((logit(I.match_win(pa + H, pb, best_of=bo)) - logit(I.match_win(pa - H, pb, best_of=bo))) / (2 * H))
            sb = float(-(logit(I.match_win(pa, pb + H, best_of=bo)) - logit(I.match_win(pa, pb - H, best_of=bo))) / (2 * H))
            d01 = float(logit(I.match_win(pa - 0.01, pb, best_of=bo)) - logit(p))
            n = 4000
            sim = I.simulate(np.full(n, pa), np.full(n, pb), np.full(n, bo), np.full(n, I.STANDARD, dtype=object),
                             seed=7)
            pts = None
            for key in ("served", "svpt", "serve_points", "points"):
                if key in sim:
                    pts = sim[key]
                    break
            exp_pts = float(np.asarray(pts).sum(axis=1).mean()) if pts is not None else None
            res["matchups"].append({"pa": pa, "pb": pb, "best_of": bo, "P_A": round(p, 4),
                                    "S_A": round(sa, 2), "S_B": round(sb, 2),
                                    "dlogit_if_pa_minus_0.01": round(d01, 4),
                                    "dP_if_pa_minus_0.01": round(float(I.match_win(pa - 0.01, pb, best_of=bo)) - p, 4),
                                    "expected_points_mc": None if exp_pts is None else round(exp_pts, 1),
                                    "sim_keys": sorted(sim.keys()) if pts is None else None})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "composition.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
