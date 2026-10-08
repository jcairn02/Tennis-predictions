"""R1 design look of the integration strategist, follow-up to strategist_power.py: nudge variants and seed counts, on
SYNTHETIC outcomes (no match result is read; the real data used are the same counts, blocks and base forecast
distribution as strategist_power.py).

    F_mle     walk-forward maximum-likelihood b_Y (feature interactions' B-INJ nudge): b_Y ~ N(beta, SE_Y^2)
    F_shrunk  the same estimate shrunk toward 0 by a prior N(0, TAU^2): b_Y * TAU^2 / (TAU^2 + SE_Y^2)
    F_fixed   a coefficient fixed before the test at B_FIXED (no fitting)
    A_k       the TabPFN column arm with capture c, compared with k seeds per side (16 or 32), seed variance added

Writes data/studies/serve_speed_tabpfn/design/strategist_power_nudge.csv.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/strategist_power_nudge.py
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import strategist_power as P  # noqa: E402

TAU, B_FIXED = 0.05, 0.05
REPS = 2000
RNG = np.random.default_rng(7102026)


def run(tpl, pool, beta: float, cap: float, reps: int = REPS, chunk: int = 250) -> dict:
    g = tpl.reset_index(drop=True)
    n = len(g)
    starts = np.flatnonzero(np.r_[True, g["block"].to_numpy()[1:] != g["block"].to_numpy()[:-1]])
    G = len(starts)
    tq = student_t.ppf(0.975, G - 1)
    season = g["season"].to_numpy()
    pb = np.array([P.COVER[s][0] for s in season])
    p1 = np.array([P.COVER[s][1] for s in season])
    se_tr = np.array([P.SE_TRAIN["bayes"][s] for s in season])
    out = {k: [] for k in ("lo_A16", "lo_A32", "gain_A16", "gain_A32", "gain_Fmle", "lo_Fmle", "gain_Fshr", "lo_Fshr",
                           "gain_Ffix", "lo_Ffix")}
    done = 0
    seasons = sorted(set(season))
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
        for k in (16, 32):
            sd = P.SEED_SD_1 / np.sqrt(k)
            eb = eta + RNG.normal(0, sd, (r, n))
            ea = eta + cap * beta * xo + RNG.normal(0, sd, (r, n))
            D = P.ll(eb, y) - P.ll(ea, y)
            m, se = D.mean(1), P.block_se(D, starts)
            se_seed = np.sqrt(2 / k * P.P1MP * P.SEED_SD_1 ** 2 / n)
            out[f"gain_A{k}"].append(1000 * m)
            out[f"lo_A{k}"].append(1000 * (m - tq * np.sqrt(se ** 2 + se_seed ** 2)))
        eb = eta + RNG.normal(0, P.SEED_SD_1 / 4, (r, n))
        lb = P.ll(eb, y)
        draws = {s: RNG.normal(beta, P.SE_TRAIN["bayes"][s], r) for s in seasons}
        b_mle = np.stack([draws[s] for s in season], axis=1)              # one b per (rep, season), per row
        shrink = TAU ** 2 / (TAU ** 2 + se_tr ** 2)
        for name, b in (("Fmle", b_mle), ("Fshr", b_mle * shrink[None, :]), ("Ffix", np.full((r, n), B_FIXED))):
            D = lb - P.ll(eb + b * xo, y)
            m, se = D.mean(1), P.block_se(D, starts)
            out[f"gain_{name}"].append(1000 * m)
            out[f"lo_{name}"].append(1000 * (m - tq * se))
        done += r
    R = {k: np.concatenate(v) for k, v in out.items()}
    row = {"beta": beta, "capture": cap}
    for name in ("A16", "A32", "Fmle", "Fshr", "Ffix"):
        row[f"{name}_gain"] = float(R[f"gain_{name}"].mean())
        row[f"{name}_sd"] = float(R[f"gain_{name}"].std())
        row[f"{name}_power"] = float((R[f"lo_{name}"] > 0).mean())
    return row


def main() -> int:
    tpl = P.template()
    pool = P.base_eta_pool()
    rows = []
    for beta, cap in product((0.0, 0.05, 0.077, 0.09), (0.25, 0.5)):
        rows.append(run(tpl, pool, beta, cap))
        print({k: round(v, 3) for k, v in rows[-1].items()}, flush=True)
    pd.DataFrame(rows).to_csv(P.OUT / "strategist_power_nudge.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
