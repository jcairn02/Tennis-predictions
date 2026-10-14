"""R2 power and error-rate checks (no outcome is read; inputs: registration/power.json, resolution.json, the
red team's outcome_free_checks.json and shrinkage.json).

1. Look A power with the registered test as coded (t on G - 1 = 20 df; noncentral t) against the registry's normal
   approximation, at realisation factors 1, 0.5, 0.25 and at the empirical k of the screened universe (shrinkage.json),
   with the window's RMS change of each score (look.py rescales to the window's RMS);
2. Look B (about 5,100 matches) and the A + B combination at the same factors;
3. the chance of at least one false "confirmed" for H0 when it is read at Look A, at Look B and on A + B, each at
   one-sided 0.05 (simulation under the null), and with simple alternatives (Look A only; a Pocock-type split).
Writes power_check.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import nct, norm, t as student_t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
REG = ROOT / "data" / "studies" / "unpriced_leads" / "registration"


def main() -> int:
    pw = json.loads((REG / "power.json").read_text(encoding="utf-8"))
    ofc = json.loads((HERE / "outcome_free_checks.json").read_text(encoding="utf-8"))
    shr = json.loads((HERE / "shrinkage.json").read_text(encoding="utf-8"))
    G = ofc["lookA_blocks_G"]
    df = G - 1
    tcrit = float(student_t.ppf(0.95, df))
    se_a, se_b = pw["se_look_a"], pw["se_look_b_5100"]
    se_ab = float(1 / np.sqrt(1 / se_a ** 2 + 1 / se_b ** 2))
    ks = {"full": 1.0, "half": 0.5, "quarter": 0.25,
          "k_empirical_low": shr["orth_all"]["selected_beta_realisation"],
          "k_empirical_high": shr["orth_eligible"]["k_full_s1.0"]}
    rms = ofc["rms_disc_vs_lookA_both"]
    names = {"omnibus": "omnibus", "Luck read as skill": "G1", "The post-Slam letdown": "G2",
             "Fast courts amplify big servers": "G3", "Status over-priced, low-visibility form under-priced": "G4",
             "Rhythm the singles record misses": "G5"}
    out = {"lookA_G": G, "t_crit_one_sided_05": tcrit, "t_crit_holm_first_01": float(student_t.ppf(0.99, df)),
           "se_a": se_a, "se_b": se_b, "se_a_plus_b": se_ab, "scores": {}}
    for key, gid in names.items():
        b = pw[key]["beta_discovery"]
        ratio = rms[gid]["ratio"]
        e = {"beta_discovery": b, "rms_ratio_lookA_over_disc": ratio}
        for lab, k in ks.items():
            za = b * k * ratio / se_a
            zb = b * k / se_b
            zab = b * k / se_ab
            e[lab] = {"k": k, "expected_z_A": za,
                      "power_A_normal_1645": float(norm.sf(1.645 - za)),
                      "power_A_t20": float(nct.sf(tcrit, df, za)),
                      "power_A_holm_first_t20": float(nct.sf(student_t.ppf(0.99, df), df, za)),
                      "expected_z_B": zb, "power_B_normal": float(norm.sf(1.645 - zb)),
                      "expected_z_AB": zab, "power_AB_normal": float(norm.sf(1.645 - zab))}
        out["scores"][gid] = e
    # 3. error rate across looks (H0 under the null), independent A and B, weights ~ 1/SE
    rng = np.random.default_rng(1)
    n = 2_000_000
    za, zb = rng.standard_normal(n), rng.standard_normal(n)
    wa, wb = 1 / se_a, 1 / se_b
    zab = (wa * za + wb * zb) / np.sqrt(wa ** 2 + wb ** 2)
    c = 1.645
    out["false_confirm_under_null"] = {
        "A_only": float(np.mean(za > c)),
        "A_or_B": float(np.mean((za > c) | (zb > c))),
        "A_or_B_or_AB": float(np.mean((za > c) | (zb > c) | (zab > c))),
        "A_or_AB": float(np.mean((za > c) | (zab > c)))}
    # a two-look group-sequential split with the same boundary at A and at A+B (Pocock-type) giving 0.05 overall
    lo, hi = 1.645, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if np.mean((za > mid) | (zab > mid)) > 0.05:
            lo = mid
        else:
            hi = mid
    out["pocock_type_boundary_A_and_AB"] = {"z": hi, "one_sided_p": float(norm.sf(hi))}
    # an O'Brien-Fleming-type pair: stringent at A (z 2.5), then the A+B boundary that keeps 0.05 overall
    zA = 2.5
    lo, hi = 1.645, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if np.mean((za > zA) | (zab > mid)) > 0.05:
            lo = mid
        else:
            hi = mid
    out["obf_type_A_2.5_then_AB"] = {"z_A": zA, "z_AB": hi, "one_sided_p_AB": float(norm.sf(hi))}
    (HERE / "power_check.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "scores"}, indent=1))
    for gid, e in out["scores"].items():
        print(gid, f"ratio {e['rms_ratio_lookA_over_disc']:.3f}",
              {lab: (round(v["expected_z_A"], 2), round(v["power_A_normal_1645"], 2), round(v["power_A_t20"], 2),
                     round(v["power_AB_normal"], 2)) for lab, v in e.items() if isinstance(v, dict)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
