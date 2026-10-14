"""Choose the primary surface arm from the validation phase (2019-2021) and pre-register the test's power, by the rule
locked after the audit (docs/studies/surface_ios/strategy.md, section 7), before any 2022-2026 result of a surface arm:

    primary = the candidate (plan.CANDIDATES: sprof, sdev, snet1) with the largest gain over `base` pooled over
              2019-2021, both tours, on recalibrated forecasts cross-fitted by season (score.py, metric "recal");
              R1 (`sprof`) if no candidate is ahead of base.

Power (the audit's must-fix 3): from the primary's validation comparison, the paired block SE scaled to the test's
number of matches, plus the seeds' variance, gives the minimum effect the test detects with 80% power at the 5% level:
MDE = (1.96 + 0.84) x SE_total.

Reads data/studies/surface_ios/results.csv and test_predictions.parquet; writes primary.json.
Run: ./python.sh src/eda/surface_ios/choose_primary.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import plan as PL  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

DEFAULT = "sprof"


def main() -> int:
    R = pd.read_csv(C.OUT / "results.csv")
    v = R[(R["metric"] == "recal") & (R["base"] == "base") & R["model"].isin(PL.CANDIDATES)
          & (R["window"] == "2019-2021")]
    both = v[v["tour"] == "both"].set_index("model")
    if set(both.index) != set(PL.CANDIDATES):
        raise RuntimeError(f"the validation results lack a candidate: {set(PL.CANDIDATES) - set(both.index)}")
    best = both["gain"].idxmax()
    primary = best if both.loc[best, "gain"] > 0 else DEFAULT
    # power, from the primary's validation comparison
    q = pd.read_parquet(C.OUT / "test_predictions.parquet")
    n_val = int(q["year"].between(2019, 2021).sum())
    n_test = int(q["year"].between(2022, 2026).sum())
    r = both.loc[primary]
    se_block_test = float(r["se_block"]) * np.sqrt(n_val / n_test)
    se_total = float(np.sqrt(se_block_test ** 2 + r["se_seed"] ** 2))
    vq = q[q["year"].between(2019, 2021)]
    dz = logit(np.clip(vq[f"q_{primary}"], T.EPS, 1 - T.EPS)) - logit(np.clip(vq["q_base"], T.EPS, 1 - T.EPS))
    out = {"rule": "largest pooled 2019-2021 gain over base, both tours, recalibrated and cross-fitted by season; "
                   "sprof if none is ahead",
           "validation_gains_both_tours": both[["gain", "lo", "hi", "lo_seed", "hi_seed"]].to_dict("index"),
           "primary": primary, "secondary": [a for a in PL.CANDIDATES if a != primary],
           "power": {"validation_matches": n_val, "test_matches": n_test,
                     "se_block_validation": float(r["se_block"]), "se_block_test_scaled": se_block_test,
                     "se_seed": float(r["se_seed"]), "se_total_test": se_total,
                     "mde_80pct_5pct": 2.80 * se_total,
                     "sd_logit_difference_validation": float(np.std(dz)),
                     "mean_abs_prob_difference_validation": float(np.mean(np.abs(vq[f"q_{primary}"] - vq["q_base"])))},
           "validation_table": v[["tour", "model", "matches", "gain", "lo", "hi", "lo_seed", "hi_seed",
                                  "verdict"]].to_dict("records")}
    C.jdump(out, C.OUT / "primary.json")
    with pd.option_context("display.width", 200):
        print(v[["tour", "model", "matches", "gain", "lo_seed", "hi_seed", "verdict"]].round(3).to_string(index=False))
        print(pd.Series(out["power"]).round(4).to_string())
    C.log(f"primary arm: {primary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
