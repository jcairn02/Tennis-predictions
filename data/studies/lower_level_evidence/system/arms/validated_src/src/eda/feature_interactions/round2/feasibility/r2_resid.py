"""Check the residual remedy for the composition columns (result-free): project z_C1 (I-008) and z_spw (its R4 form)
on the 58 inputs per tour, fitted on 2014-2018 (the panel starts in 2014), applied unchanged to 2019-2021 and
2022-2024; report the remainder's SD out of the fit. Writes data/studies/feature_interactions/round2/feasibility/r2_resid.json.
Run: ./python.sh src/eda/feature_interactions/round2/feasibility/r2_resid.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402
from src.eda.feature_interactions.round1.feasibility import builders_a as BA  # noqa: E402

OUT = B.C.OUT / "round2" / "feasibility"


def main() -> int:
    P = pd.read_parquet(B.OUT / "_panel_aug.parquet").drop(columns=["a_won"])
    cols = {"z_C1": BA.I008(P)["z_C1"][0]}
    mu = B.mean_logit(P, "spw")
    pa = expit(mu + BA.io(P, "srfO", "spw", "a") - BA.io(P, "srfD", "spw", "b"))
    pb = expit(mu + BA.io(P, "srfO", "spw", "b") - BA.io(P, "srfD", "spw", "a"))
    cols["z_spw"] = B.lg(B.iid_match(pa, pb, BA.bo(P)))
    res = {}
    for name, x in cols.items():
        for t in ("atp", "wta"):
            mt = (P["tour"] == t).to_numpy()
            X = np.column_stack([np.ones(int(mt.sum())), B.input_matrix(P.loc[mt])])
            y = np.asarray(x, float)[mt]
            seas = P.loc[mt, "season"].to_numpy()
            fit = (seas <= 2018) & np.isfinite(y)
            beta, *_ = np.linalg.lstsq(X[fit], y[fit], rcond=None)
            rem = y - X @ beta
            r = {"r2_fit": round(float(1 - rem[fit].var() / y[fit].var()), 4)}
            for tag, (lo, hi) in (("sd_2014_18", (2014, 2018)), ("sd_2019_21", (2019, 2021)), ("sd_2022_24", (2022, 2024))):
                k = (seas >= lo) & (seas <= hi) & np.isfinite(rem)
                r[tag] = round(float(rem[k].std()), 4)
            res[f"{name}_{t}"] = r
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "r2_resid.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
