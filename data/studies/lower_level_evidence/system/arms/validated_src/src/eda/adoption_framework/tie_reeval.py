"""Scratch: what the "tie" readings in the docs hold, and what adoption thresholds trade.

Part 1: one-sided P(candidate better) = Phi(est / SE), SE = half-width / 2.0 (the docs' t intervals have ~50-60 blocks).
Part 2: analytic expected outcomes of adopting when z_obs > c, for a mix of real / null / harmful candidates.
"""
import numpy as np
from scipy.stats import norm

R = [  # label, estimate, lo, hi  (mLL per match; + = candidate better)
    ("speed backfill vs reference, men 2020-24", 0.027, -0.073, 0.128),
    ("speed backfill vs reference, both tours", 0.014, -0.073, 0.102),
    ("rebuilt vs previous model, both, 2022-26", 0.03, -0.13, 0.20),
    ("surface IOS profile, with close, men", 0.07, -0.11, 0.26),
    ("surface IOS profile, with close, both", 0.01, -0.10, 0.13),
    ("offset Elo, with close, men (in model)", 0.05, -0.20, 0.31),
    ("offset Elo, with close, women (in model)", -0.21, -0.48, 0.07),
    ("offset Elo, with close, both (in model)", -0.07, -0.24, 0.10),
    ("event share as 59th input, both", 0.06, -0.10, 0.23),
    ("+ Challenger rows vs current, both", -0.48, -1.09, 0.14),
    ("+ Challenger rows vs current, men", -0.91, -1.89, 0.08),
    ("men 16-input profile vs close 2022-26", 0.93, -0.00, 1.86),
    ("speed adj vs base, men 2020-24 (pre-fix)", -0.30, -0.68, 0.08),
    ("speed effect per unit, pooled 2019-24", 0.030, -0.020, 0.080),
]
print("Part 1: P(candidate better), one-sided, flat prior")
for lab, est, lo, hi in R:
    se = (hi - lo) / 2 / 2.0
    p = norm.cdf(est / se)
    print(f"  {lab:44s} {est:+.3f} [{lo:+.3f}, {hi:+.3f}]  SE {se:.3f}  P(better) {p:.2f}")


def outcome(mix, c, sigma, cost_null=0.0):
    """mix: list of (count, true gain in SE units). Adopt when z_obs > c. Returns expected totals in mLL."""
    adopted = nulls = true = meas = 0.0
    real_meas = real_true = 0.0
    for n, m in mix:
        pa = 1 - norm.cdf(c - m)
        adopted += n * pa
        e_meas = sigma * (m * pa + norm.pdf(c - m))
        e_true = sigma * m * pa
        meas += n * e_meas
        true += n * e_true
        if m == 0:
            nulls += n * pa
            true -= n * pa * cost_null
        if m > 0:
            real_meas += n * e_meas
            real_true += n * e_true
    return adopted, nulls, true, meas, meas - true, (real_meas / real_true if real_true else np.nan)


sigma = 0.08  # mLL: a typical same-model swap at the close (02_contamination: 0.06-0.10)
scen = {
    "A: 20 ideas, 30% real at +1 SE (+0.08), 60% null, 10% harmful at -1 SE": [(6, 1.0), (12, 0.0), (2, -1.0)],
    "B: 20 ideas, 30% real at +2 SE (+0.16), 60% null, 10% harmful at -1 SE": [(6, 2.0), (12, 0.0), (2, -1.0)],
    "C: 20 ideas, 10% real at +1 SE, 80% null, 10% harmful at -1 SE (fishing)": [(2, 1.0), (16, 0.0), (2, -1.0)],
}
TH = [("95% interval clears 0 (P>0.975)", 1.96), ("P>0.90", 1.2816), ("P>0.80 (~rebuild's 1 SE)", 0.8416),
      ("P>0.75", 0.6745), ("P>0.50 (sign only)", 0.0)]
print(f"\nPart 2: expected totals over the 20 decisions, SE {sigma} mLL per decision")
for name, mix in scen.items():
    for cost in (0.0, 0.02):
        print(f"\n  {name}; cost per adopted null {cost} mLL")
        print(f"    {'rule':30s} {'adopted':>7s} {'nulls in':>8s} {'true gain':>9s} {'backtest':>8s} {'inflation':>9s} {'real exagg.':>11s}")
        for lab, c in TH:
            a, nl, t, m, inf, ex = outcome(mix, c, sigma, cost)
            print(f"    {lab:30s} {a:7.1f} {nl:8.1f} {t:+9.3f} {m:+8.3f} {inf:+9.3f} {ex:10.1f}x")

# Monte Carlo check of scenario A at P>0.80
rng = np.random.default_rng(0)
mix = np.r_[np.full(6, 1.0), np.zeros(12), np.full(2, -1.0)]
z = mix + rng.standard_normal((200_000, 20))
ad = z > 0.8416
print("\nMC check, scenario A, P>0.80, cost 0: true", round(float((ad * mix * sigma).sum(1).mean()), 3),
      "backtest", round(float((ad * z * sigma).sum(1).mean()), 3))
