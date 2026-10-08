"""Rule 10 of plan.md ("Fixed at M1"): Tweedie shrinkage of the screened members' z, and the expected gain the
pre-registration states (checkpoint 2, R-E: written as a script so it reproduces).

    z      each of the 34 members' one-sided joint p (model base, screen_results.csv) mapped to z = Phi^-1(1 - p): for a
           single-coefficient row this is its z_joint in the declared direction; the five Wald rows (two-sided, F
           reference) enter through the same map of their p
    f      scipy.stats.gaussian_kde(z, bw_method="silverman"): the kernel SD is SciPy's Silverman factor (3n/4)^(-1/5)
           times the sample SD of z (the factor 0.523 at n = 34 is not itself the bandwidth)
    z_hat  z + d/dz log f(z) (central difference, h = 1e-4)
    gain   1000 max(z_hat, 0)^2 / (2 x 50,087) mLL, the population gain whose expected coefficient z is z_hat on the
           screen's 50,087 matches; times the capture slope (1 for a nudge)
Sensitivity: the two textbook Silverman bandwidths, 0.9 min(SD, IQR/1.34) n^(-1/5) and 1.06 SD n^(-1/5).
Writes data/studies/feature_interactions/final/shrinkage.json. Run: ./python.sh src/eda/feature_interactions/shrinkage.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde, norm

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402

N_SCREEN = 50087
H = 1e-4
# the final-test verifier's synthetic power of the primary as coded (meta/final_test_verification.md)
POWER_CURVE = {0.0: 0.0235, 0.1: 0.16, 0.2: 0.34, 0.5: 0.74}


def tweedie(z: np.ndarray, bandwidth: float | None = None) -> np.ndarray:
    """z_hat at every z; bandwidth = the kernel SD (None: SciPy's Silverman rule)."""
    if bandwidth is None:
        kde = gaussian_kde(z, bw_method="silverman")
    else:
        kde = gaussian_kde(z, bw_method=bandwidth / np.std(z, ddof=1))
    return z + (np.log(kde(z + H)) - np.log(kde(z - H))) / (2 * H)


def power_at(gain: float) -> float:
    g = np.array(sorted(POWER_CURVE))
    return float(np.interp(gain, g, [POWER_CURVE[k] for k in g]))


def main() -> int:
    R = pd.read_csv(C.OUT / "hypotheses" / "screen_results.csv")
    M = R[R["base"] == "model"].reset_index(drop=True)
    z = norm.isf(M["p_joint"].clip(1e-15, 1 - 1e-15).to_numpy(float))
    n, sd = len(z), float(np.std(z, ddof=1))
    iqr = float(np.subtract(*np.percentile(z, [75, 25])))
    bws = {"scipy_silverman": (3 * n / 4) ** (-1 / 5) * sd,
           "silverman_0.9_min": 0.9 * min(sd, iqr / 1.34) * n ** (-1 / 5),
           "silverman_1.06_sd": 1.06 * sd * n ** (-1 / 5)}
    i = int(np.flatnonzero(M["hid"].to_numpy() == "B-INJ")[0])
    out = {"members": n, "z_sd": sd, "rule": "scipy_silverman", "bandwidths": bws, "B-INJ": {"z": float(z[i])},
           "power_curve_used": POWER_CURVE}
    for name, bw in bws.items():
        zh = tweedie(z, None if name == "scipy_silverman" else bw)
        gain = 1000 * max(zh[i], 0.0) ** 2 / (2 * N_SCREEN)
        out["B-INJ"][name] = {"bandwidth": bw, "z_hat": float(zh[i]), "expected_gain_mll": gain,
                              "power_at_gain": power_at(gain)}
    C.write_json(C.OUT / "final" / "shrinkage.json", out)
    r = out["B-INJ"]
    C.log(f"B-INJ z {r['z']:.3f}; " + "; ".join(f"{k}: bw {v['bandwidth']:.3f}, z_hat {v['z_hat']:.3f}, gain "
                                                 f"{v['expected_gain_mll']:.3f} mLL, power {v['power_at_gain']:.2f}"
                                                 for k, v in r.items() if isinstance(v, dict)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
