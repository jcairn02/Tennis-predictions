"""Harness verifier, task 4: wall time of screen.run on the real frame size (synthetic outcomes, a random column).

Run: ./python.sh src/eda/feature_interactions/verify/timing.py
Writes data/studies/feature_interactions/verify/timing.json
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions.verify import simlib as V  # noqa: E402


def main() -> int:
    warnings.simplefilter("ignore")
    V.patch_nuisance()               # bug B1: unpatched, effect_sizes crashes on the held-out 2018 season (no men)
    F = S.load(with_model=True)
    rng = np.random.default_rng(1)
    F["a_won"] = V.draw(F, V.base_logit(F), rng)            # synthetic outcomes: the real ones are never used here
    x = rng.normal(size=len(F))
    Cm = rng.normal(size=(len(F), 3))
    h = S.Hypothesis("timing", x, Cm, ["c1", "c2", "c3"])
    out = {"rows": len(F)}
    xs, Cs, prep = S.prepare(F, h, "model")
    disc = (F["window"] == "discovery").to_numpy()
    t0 = time.perf_counter()
    for _ in range(5):
        S.coef_test(F, disc, xs, Cs, "model", prep)
    out["coef_test_disc_s"] = (time.perf_counter() - t0) / 5
    for label, kw in (("run_p1_0_nosizes", dict(n_p1=0, sizes=False)), ("run_p1_0_sizes", dict(n_p1=0, sizes=True)),
                      ("run_p1_200_sizes", dict(n_p1=200, sizes=True))):
        t0 = time.perf_counter()
        r = S.run(F, h, **kw)
        out[label + "_s"] = time.perf_counter() - t0
        out[label + "_p1_sd"] = r.get("p1_null_sd")
    X = rng.normal(size=(len(F), 4))
    t0 = time.perf_counter()
    S.run_wald(F, "timing_wald", X, Cm, n_p1=200)
    out["run_wald_k4_p1_200_s"] = time.perf_counter() - t0
    C.write_json(C.OUT / "verify" / "timing.json", out)
    C.log(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
