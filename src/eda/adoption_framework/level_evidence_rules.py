"""Operating characteristics of the level-evidence study's decision rules: as registered, and as amended under the
owner's decision of 9 Oct 2026 (adoption by change class). Reads no data: every input is a standard error the study
itself wrote down before any score (D_verification.md:59-63; preregistration_addition_3.md section 6).

Men. delta = SYS's true gain over REF (mLL, + = SYS better), assumed the same in every stratum except falsification
(where SYS moves nothing, so its true effect is 0 there).
"""
import numpy as np
from scipy.stats import norm

rng = np.random.default_rng(20261009)
N = 200_000
SE_DEV, SE_HOLD, SE_POOL = 0.035, 0.063, 0.067 / 1.96
RHO_HP = np.sqrt(4810 / (11672 + 4810))  # holdout share of the pooled 2020-26 men's matches
TOL = 0.10  # harm tolerance (mLL): the Roland Garros rule's form

# Addition 2 section 3: eight men's holdout readings, Holm-corrected; SEs approximate (strata 0.13-0.20 per D).
STRATA_SE = np.array([0.085, 0.095, 0.13, 0.075, 0.13, 0.075, 0.20, 0.065])
FALSIFICATION = 6


def holm_worse(est, se):
    """True where any of the readings is 'worse' after Holm at family-wise 5% (two-sided p-values)."""
    z = est / se
    p = 2 * norm.sf(np.abs(z))
    order = np.argsort(p, axis=1)
    p_sorted = np.take_along_axis(p, order, axis=1)
    m = p.shape[1]
    thresholds = 0.05 / (m - np.arange(m))
    passed = p_sorted <= thresholds
    # Holm stops at the first failure
    stop = np.cumprod(passed, axis=1).astype(bool)
    rejected_sorted = stop
    rejected = np.zeros_like(rejected_sorted)
    np.put_along_axis(rejected, order, rejected_sorted, axis=1)
    return (rejected & (est < 0)).any(axis=1)


def harm(est, se):
    return (est < -TOL) & (est + 1.96 * se < 0)


print("SYS for men: P(the rule recommends SYS)")
print(f"{'true gain':>10} | {'registered':>10} | {'amended':>8} | amended's harm flags: dev / holdout / Holm")
for delta in (-0.20, -0.10, -0.05, 0.0, 0.04, 0.083, 0.12):
    z = rng.standard_normal((N, 3))
    e_dev = delta + SE_DEV * z[:, 0]
    e_h = delta + SE_HOLD * z[:, 1]
    e_p = delta + SE_POOL * (RHO_HP * z[:, 1] + np.sqrt(1 - RHO_HP**2) * z[:, 2])
    mu = np.full(len(STRATA_SE), delta)
    mu[FALSIFICATION] = 0.0
    strata = mu + STRATA_SE * rng.standard_normal((N, len(STRATA_SE)))
    holm = holm_worse(strata, STRATA_SE)
    # registered: step 2 of the selection (REF if P(better than REF) < 0.50 on dev), then the recommendation
    kept_dev = norm.cdf(e_dev / SE_DEV) >= 0.50
    better_h = e_h / SE_HOLD > 1.96
    pb80 = norm.cdf(e_h / SE_HOLD) >= 0.80
    better_p = e_p / SE_POOL > 1.96
    registered = kept_dev & (better_h | (pb80 & better_p & ~holm))
    # amended: SYS unless harm on dev (fallback), on the holdout primary, or a Holm-worse stratum
    h_dev, h_hold = harm(e_dev, SE_DEV), harm(e_h, SE_HOLD)
    amended = ~h_dev & ~h_hold & ~holm
    print(f"{delta:+10.3f} | {registered.mean():10.2f} | {amended.mean():8.2f} | "
          f"{h_dev.mean():.3f} / {h_hold.mean():.3f} / {holm.mean():.3f}")

for n_ch, note in ((7, "as registered"), (5, "erratum 1: R_S2 and SYS_S2 report-only")):
    print(f"\nSelection on dev: P(switch away from SYS), {n_ch} challengers ({note}), SE 0.035 each against SYS")
    print(f"{'world':>34} | {'rho':>4} | registered (P>=0.90) | amended ('better')")
    for label, gains in (("no challenger truly differs", np.zeros(n_ch)),
                         ("one challenger truly +0.10", np.r_[0.10, np.zeros(n_ch - 1)])):
        for rho in (0.0, 0.5, 0.9):
            common = rng.standard_normal((N, 1))
            own = rng.standard_normal((N, n_ch))
            e = gains + 0.035 * (np.sqrt(rho) * common + np.sqrt(1 - rho) * own)
            z = e / 0.035
            reg = (norm.cdf(z) >= 0.90).any(axis=1)
            amd = (z > 1.96).any(axis=1)
            print(f"{label:>34} | {rho:4.1f} | {reg.mean():20.2f} | {amd.mean():.2f}")

print("\nNew data through the system (NEW_SYS_BOTH vs SYS_BOTH), men, dev SE ~0.03: P(harm flag)")
for d in (0.0, -0.05, -0.10, -0.15, -0.20):
    e = d + 0.03 * rng.standard_normal(N)
    print(f"  true {d:+.2f}: {harm(e, 0.03).mean():.3f}")
