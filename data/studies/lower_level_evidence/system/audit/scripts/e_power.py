"""Role E (red team), CP1: the selection rule's false-switch rate and the readings' power, before any reading.

Inputs are the first run's published intervals (data/studies/lower_level_evidence/candidates/results/pairs.csv) and the
frame's match counts; nothing of this run is read. Writes audit/power_cp1.json.
"""
import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

OUT = Path(__file__).resolve().parents[1] / "power_cp1.json"
rng = np.random.default_rng(1)
res = {"false_switch": {}, "ref_fallback": {}, "challenger_qualifies": {}, "holdout": {}}
z90 = norm.ppf(0.90)
for rho in (0.0, 0.3, 0.5, 0.7, 0.9):
    n = 7
    C = np.full((n, n), rho)
    np.fill_diagonal(C, 1.0)
    z = rng.multivariate_normal(np.zeros(n), C, size=400000)
    res["false_switch"][str(rho)] = float((z.max(axis=1) >= z90).mean())
for g in (0.02, 0.05, 0.08, 0.10):
    for se in (0.035, 0.045):
        res["ref_fallback"][f"gain {g}, se {se}"] = {"P(REF selected)": float(norm.cdf(-g / se)),
                                                     "P(dev better)": float(1 - norm.cdf(1.96 - g / se))}
for d in (0.02, 0.05, 0.10):
    for se in (0.03, 0.10):
        res["challenger_qualifies"][f"true gain over SYS {d}, se {se}"] = float(1 - norm.cdf(z90 - d / se))
# holdout and pooled SEs scaled from FP vs the reference, men, dev (se 0.0406 on 11,672 matches)
se_dev, n_dev = 0.040571, 11672
for name, n in (("holdout 2025-2026 men (2,620 + 2,190)", 4810), ("pooled 2020-2026 men", 16482)):
    se = se_dev * np.sqrt(n_dev / n)
    res["holdout"][name] = {"se": float(se), "half_width_95": float(1.96 * se),
                            "P(better | true +0.083)": float(1 - norm.cdf(1.96 - 0.083 / se)),
                            "P(P(better) >= 0.80 | true +0.083)": float(1 - norm.cdf(norm.ppf(0.80) - 0.083 / se))}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
