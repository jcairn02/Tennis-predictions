"""Harness verifier, task 2: planted effects on real structure with SYNTHETIC outcomes, through screen.run.

y ~ Bernoulli(sigmoid(a_tour * eta + beta * x0 [+ v_A - v_B])), eta the current best's real log-odds, x0 a real column
standardised on the discovery rows, beta set so that the population-averaged gain over the screen's null design is
Delta (milli-nats); v optional career-long player effects (sd tau, redrawn per draw). The frame's real a_won is
overwritten before any fit and never read.

Run: ./python.sh src/eda/feature_interactions/verify/planted.py --cols RAND,S-IOS --deltas 0,0.1 --draws 100
         [--tau 0.1] [--p1 0] [--tag name] [--seed 1]
Writes data/studies/feature_interactions/verify/planted_<tag>.parquet (one row per draw)
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

KEYS = ("b1", "se1", "se_model1", "se_block1", "se_player1", "se_union1", "z1", "b2", "se2", "se_model2", "se_block2",
        "se_player2", "se_union2", "z2", "z_joint", "p_joint", "filter_pass", "replicates", "widen", "p1_null_sd")


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main() -> int:
    warnings.simplefilter("ignore")
    V.patch_nuisance()
    cols = arg("--cols", "RAND").split(",")
    deltas = [float(d) for d in arg("--deltas", "0,0.1,0.2,0.3").split(",")]
    draws, tau, n_p1 = int(arg("--draws", 100)), float(arg("--tau", 0)), int(arg("--p1", 0))
    tag, seed = arg("--tag", "main"), int(arg("--seed", 1))
    F = S.load(with_model=True)
    F["a_won"] = False                                     # the real results are never used below
    Kc = load_cols()
    base = V.base_logit(F)
    rng = np.random.default_rng(seed)
    out_path = C.OUT / "verify" / f"planted_{tag}.parquet"
    rows = []
    for name in cols:
        h = hypothesis(F, Kc, name)
        h.trait = "none"                                   # P2 is checked separately (p2_check.py)
        xs, Cs, prep = S.prepare(F, h, "model")
        x0 = V.std_disc(F, h.x)
        for delta in deltas:
            beta, g = (V.calibrate(F, x0, delta, Cs, prep) if delta > 0 else
                       (0.0, {"discovery": 0.0, "replication": 0.0, "pooled": 0.0}))
            C.log(f"{name} delta {delta}: beta {beta:.4f}, gains (mLL) " +
                  ", ".join(f"{k} {1000 * v:.3f}" for k, v in g.items()))
            for d in range(draws):
                pe = V.player_effects(F, tau, rng) if tau > 0 else 0.0
                F["a_won"] = V.draw(F, base + beta * x0 + pe, rng)
                r = S.run(F, h, n_p1=n_p1, sizes=False, seed=int(rng.integers(1 << 30)))
                rows.append({"col": name, "delta": delta, "beta": beta, "gain_disc": 1000 * g["discovery"],
                             "gain_rep": 1000 * g["replication"], "gain_pooled": 1000 * g["pooled"], "draw": d,
                             "tau": tau, "n1": r["n1"], "n2": r["n2"], **{k: r.get(k, np.nan) for k in KEYS}})
            pd.DataFrame(rows).to_parquet(out_path, index=False)
    C.log(f"written {out_path.name}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
