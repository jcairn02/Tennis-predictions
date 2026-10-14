"""R1 design look of the integration strategist: the joint power of the proposed fixed sequence (P1 the information
coefficient of the speed column given the base, then P2 the column arm's calibrated paired gain), on SYNTHETIC outcomes
(same world and real counts as strategist_power.py; no match result is read).

Writes data/studies/serve_speed_tabpfn/design/strategist_power_joint.csv.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/strategist_power_joint.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import strategist_power as P  # noqa: E402

RNG = np.random.default_rng(20261008)
REPS = 2000


def joint(tpl, pool, beta: float, cap: float, struct: float, reps: int = REPS, chunk: int = 250) -> dict:
    g = tpl.reset_index(drop=True)
    n = len(g)
    starts = np.flatnonzero(np.r_[True, g["block"].to_numpy()[1:] != g["block"].to_numpy()[:-1]])
    G = len(starts)
    tq = student_t.ppf(0.975, G - 1)
    season = g["season"].to_numpy()
    pb = np.array([P.COVER[s][0] for s in season])
    p1 = np.array([P.COVER[s][1] for s in season])
    se_seed = np.sqrt(2 / P.K_SEEDS * P.P1MP * P.SEED_SD_1 ** 2 / n)
    p1_pass, p2_pass = [], []
    done = 0
    while done < reps:
        r = min(chunk, reps - done)
        eta = RNG.choice(pool, size=(r, n))
        xa = RNG.normal(0, np.sqrt(P.VAR_X / 2), (r, n))
        xb = RNG.normal(0, np.sqrt(P.VAR_X / 2), (r, n))
        u = RNG.random((r, n))
        both, one = u < pb, (u >= pb) & (u < pb + p1)
        side_a = RNG.random((r, n)) < 0.5
        xo = np.where(both, xa - xb, np.where(one, np.where(side_a, xa, -xb), 0.0))
        y = (RNG.random((r, n)) < expit(eta + beta * (xa - xb))).astype(float)
        has = xo != 0
        sd = P.SEED_SD_1 / np.sqrt(P.K_SEEDS)
        eb = eta + RNG.normal(0, sd, (r, n))
        ea = eta + cap * beta * xo + RNG.normal(0, sd, (r, n)) + struct * RNG.normal(0, 1, (r, n)) * has
        D = P.ll(eb, y) - P.ll(ea, y)
        m, se = D.mean(1), P.block_se(D, starts)
        p2_pass.append(m - tq * np.sqrt(se ** 2 + se_seed ** 2) > 0)
        b = np.zeros(r)
        for _ in range(5):
            p = expit(eb + b[:, None] * xo)
            b += ((y - p) * xo).sum(1) / np.maximum((p * (1 - p) * xo ** 2).sum(1), 1e-12)
        p = expit(eb + b[:, None] * xo)
        info = (p * (1 - p) * xo ** 2).sum(1)
        S = np.add.reduceat((y - p) * xo, starts, axis=1)
        seb = np.sqrt(G / (G - 1) * (S ** 2).sum(1)) / info
        p1_pass.append(b - tq * seb > 0)
        done += r
    a, c = np.concatenate(p1_pass), np.concatenate(p2_pass)
    return {"beta": beta, "capture": cap, "struct": struct, "P1": float(a.mean()), "P2": float(c.mean()),
            "P1_and_P2": float((a & c).mean()), "P2_without_P1": float((c & ~a).mean())}


def main() -> int:
    tpl, pool = P.template(), P.base_eta_pool()
    rows = []
    for beta in (0.0, 0.05, 0.077, 0.09):
        for cap, struct in ((0.25, 0.0), (0.5, 0.0), (0.5, 0.02)):
            rows.append(joint(tpl, pool, beta, cap, struct))
            print({k: round(v, 3) for k, v in rows[-1].items()}, flush=True)
    pd.DataFrame(rows).to_csv(P.OUT / "strategist_power_joint.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
