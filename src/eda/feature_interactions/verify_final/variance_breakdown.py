"""Final-test verifier: why the primary is conservative on synthetic outcomes. The same replicates as synth_power's
design (harness DGP), recording inside tabpfn_tests.encompassing the three clustered variances (block, shared player,
union; the code takes the largest) and the model-based (inverse-Hessian) variance, and the two-sided 95% rejection rate
under each, on t with G - 1 df (the code's reference). Synthetic outcomes only.

    ./python.sh src/eda/feature_interactions/verify_final/variance_breakdown.py --reps 1000
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.verify_final import harness as HN  # noqa: E402
from src.eda.feature_interactions.verify_final.synth_power import beta_for  # noqa: E402

FT, TT, S = HN.FT, HN.TT, HN.S
ORIG_CV, ORIG_FIT = S.clustered_variances, S.fit
REC = {}


def cv(u, block, pa, pb):
    v = ORIG_CV(u, block, pa, pb)
    REC["v"] = v
    return v


def fit(Z, y, *a, **k):
    out = ORIG_FIT(Z, y, *a, **k)
    REC["Hinv_jj"] = float(np.linalg.inv(out[2])[-1, -1])
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 1000
    syn = HN.Synth()
    res = []
    for i, target in enumerate((0.0, 0.5)):
        beta = beta_for(syn, target)
        rng = np.random.default_rng(99 + i)
        rows = []
        for _ in range(reps):
            syn.draw(beta, rng)
            params = FT.parameters(syn.xs)
            S.clustered_variances, S.fit = cv, fit
            pr = FT.primary(syn.f, syn.xs, params)
            S.clustered_variances, S.fit = ORIG_CV, ORIG_FIT
            bz = pr["b"] * pr["sd_dev"]                       # coefficient on dev / sd_dev
            r = {k: bz / np.sqrt(v) for k, v in REC["v"].items()}
            r["model"] = bz / np.sqrt(REC["Hinv_jj"])
            r["max_of_three"] = pr["t"]
            r["df"] = pr["df"]
            r["ratio_max_to_model_var"] = max(REC["v"].values()) / REC["Hinv_jj"]
            r["argmax"] = max(REC["v"], key=REC["v"].get)
            rows.append(r)
        d = pd.DataFrame(rows)
        crit = student_t.ppf(0.975, d["df"].iloc[0])
        s = {"target_mll": target, "reps": reps, "t_crit": crit}
        for k in ("block", "player", "union", "max_of_three", "model"):
            s[f"reject_{k}"] = float((d[k].abs() > crit).mean())
            s[f"sd_t_{k}"] = float(d[k].std())
        s["median_var_ratio_max_over_model"] = float(d["ratio_max_to_model_var"].median())
        s["argmax_share"] = d["argmax"].value_counts(normalize=True).to_dict()
        res.append(s)
        print(json.dumps(s, default=float), flush=True)
    (HN.OUT / "variance_breakdown.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
