"""Operating characteristics of the level-evidence system's pre-registered recommendation rule,
and the learning-curve value of extra training rows. Numbers only from the docs; reads no data.

SPEC section 8 (docs/studies/lower_level_evidence/system/SPEC.md:243-247): recommend SELECTED if
  (a) holdout primary 'better' (95% CI clears 0), or
  (b) holdout unresolved with P(better) >= 0.80 AND pooled 2020-26 'better' AND no secondary worse.
SEs from D_verification.md:59-61 (resolution = 1.96 SE): holdout 0.063; pooled 0.067/1.96.
"""
import numpy as np
from scipy.stats import norm

rng = np.random.default_rng(0)
n = 400_000
se_h, se_p = 0.063, 0.067 / 1.96
# holdout ~4,810 of ~16,500 pooled men's matches (11,672 in 2020-24 + 4,810) -> corr ~ sqrt(share)
rho = np.sqrt(4810 / (11672 + 4810))
p_no_secondary_worse = 0.9  # assumption: Holm's eight flag only large harm (D_verification:80)

print(f"corr(holdout, pooled) ~ {rho:.2f}")
print("true gain | P(recommend) | P(holdout 'better') | P(P(better)>=0.8)")
for delta in (-0.05, 0.0, 0.02, 0.04, 0.083, 0.12):
    z = rng.standard_normal((n, 2))
    e_h = delta + se_h * z[:, 0]
    e_p = delta + se_p * (rho * z[:, 0] + np.sqrt(1 - rho**2) * z[:, 1])
    better_h = e_h / se_h > 1.96
    pb_h = norm.cdf(e_h / se_h) >= 0.80
    better_p = e_p / se_p > 1.96
    sec_ok = rng.random(n) < p_no_secondary_worse
    rec = better_h | (pb_h & better_p & sec_ok)
    print(f"{delta:+.3f}     | {rec.mean():.2f}         | {better_h.mean():.2f}               | {pb_h.mean():.2f}")

# New data, men: dev SE 0.03-0.04 (D_verification:59). 'Holding the model back' only if it reads 'better'.
print("\nNEW_ASIS vs REF, men, dev: P(reads 'better') for a true gain d")
for d in (0.0, 0.005, 0.01, 0.02):
    for se in (0.03, 0.04):
        print(f"  d={d:.3f} se={se:.2f}: {1 - norm.cdf(1.96 - d / se):.3f}")

# Sign rule ('points the right way') for a below-resolution effect
print("\nP(estimate > 0) for true gain d at SE s (the sign rule's hit rate)")
for d, s in ((0.01, 0.04), (0.03, 0.04), (0.01, 0.01), (0.0003, 0.01)):
    print(f"  d={d}, s={s}: {norm.cdf(d / s):.2f}")

# Learning curve from training_window (README lines 63-66, 83-86): loss increase (mLL) when training on a
# random fraction r of the rows (2024 sizes: 29,737 / 22,190 / 14,840 of 50,003).
r = np.array([29737, 22190, 14840]) / 50003
dl = np.array([0.01, 0.07, 0.30])
print("\nLearning curve fits: loss increase = A * (r^-a - 1); marginal value of extra rows at N ~ 60,249")
for a in (0.5, 1.0, 2.0, 3.5):
    basis = r ** -a - 1
    A = (basis @ dl) / (basis @ basis)  # least squares through the three points
    slope = A * a  # d(loss)/d(r) at r = 1, per unit fraction of the data
    for rows in (100, 2000, 4500):
        f = rows / 60249
        print(f"  a={a}: A={A:.4f}, +{rows:>5} rows -> {slope * f:.5f} mLL", end="")
        print(f"   (fit: {np.round(A * basis, 3)})" if rows == 100 else "")
