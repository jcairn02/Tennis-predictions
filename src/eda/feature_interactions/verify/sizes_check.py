"""Harness verifier: the effect sizes (leave-one-season-out 2014-2021, forward 2022-2024) on planted effects with
SYNTHETIC outcomes, with bug B1's fix patched in (unpatched, effect_sizes crashes on the held-out 2018 season).
Also a few P1 runs (200 shuffles) at beta = 0 and at Delta = 0.2.

Run: ./python.sh src/eda/feature_interactions/verify/sizes_check.py [--draws 30]
Writes data/studies/feature_interactions/verify/sizes_check.parquet
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions.verify import simlib as V  # noqa: E402
from src.eda.feature_interactions.verify.cols import hypothesis, load_cols  # noqa: E402


def main() -> int:
    warnings.simplefilter("ignore")
    V.patch_nuisance()
    draws = int(sys.argv[sys.argv.index("--draws") + 1]) if "--draws" in sys.argv else 30
    F = S.load(with_model=True)
    F["a_won"] = False                                     # the real results are never used below
    K = load_cols()
    base, rng, rows = V.base_logit(F), np.random.default_rng(77), []
    for name, delta, n_p1 in (("RAND", 0.3, 0), ("S-IOS", 0.3, 0), ("RAND", 0.0, 200), ("S-AGE", 0.2, 200)):
        h = hypothesis(F, K, name)
        xs, Cs, prep = S.prepare(F, h, "model")
        x0 = V.std_disc(F, h.x)
        beta, g = V.calibrate(F, x0, delta, Cs, prep) if delta > 0 else (0.0, {"discovery": 0, "replication": 0})
        for d in range(draws if n_p1 == 0 else 6):
            F["a_won"] = V.draw(F, base + beta * x0, rng)
            r = S.run(F, h, n_p1=n_p1, sizes=n_p1 == 0, seed=int(rng.integers(1 << 30)))
            rows.append({"col": name, "delta": delta, "n_p1": n_p1, "gain_disc_true": 1000 * g["discovery"],
                         "gain_rep_true": 1000 * g["replication"], **{k: v for k, v in r.items() if k.startswith(
                             ("gain_", "lo_", "hi_", "p1_", "widen", "z1", "z2", "z_joint"))}})
        pd.DataFrame(rows).to_parquet(C.OUT / "verify" / "sizes_check.parquet", index=False)
        C.log(f"{name} delta {delta} p1 {n_p1}: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
