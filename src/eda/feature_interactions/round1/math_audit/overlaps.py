"""Round-1 mathematical audit: overlaps between candidates and with their own M2 controls (result-free, seasons <= 2021).

    ./python.sh src/eda/feature_interactions/round1/math_audit/overlaps.py

Writes data/studies/feature_interactions/round1/math_audit/overlaps.json. Only features and prices are regressed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.math_audit import candidates as CB  # noqa: E402
from src.eda.feature_interactions.round1.math_audit.common_audit import (OUT, design58, load_panel, num,  # noqa: E402
                                                                        r2_on, resid_sd, surface_means)


def corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return round(float(np.corrcoef(a[ok], b[ok])[0, 1]), 3)


def main() -> int:
    P = load_panel()
    means = surface_means()
    C, _, AUX = CB.build(P, means)
    C2, _ = CB.build2(P, means, AUX)
    C.update(C2)
    X = design58(P)
    z = num(P, "in_odds_logit")
    bo5 = (num(P, "in_best_of") == 5).astype(float)
    rat = num(P, "in_ratings_iid")
    tour = P["tour"].astype(str).to_numpy()
    out = {}
    # per-tour residual SD on the 58 inputs, in the column's own units (match log-odds for C columns)
    for name in ("I-008 z_C1", "I-001 z*kappa", "I-002 comp", "I-012 shield", "I-013 e_ace", "I-014 x", "I-016 x"):
        out[f"resid_sd_58|{name}"] = {t: round(resid_sd(X, C[name], tour == t), 4) for t in ("atp", "wta")}
    # I-006: L given its M2 controls (1[bo5] x price, 1[bo5] x ratings_iid)
    X6 = np.column_stack([X, bo5 * z, bo5 * rat])
    out["I-006 L: r2 on 58 + bo5*z + bo5*ratings_iid (men)"] = round(r2_on(X6, C["I-006 L"], tour == "atp"), 4)
    out["I-006 L: resid sd given those (men, Bo5 rows)"] = round(resid_sd(X6, C["I-006 L"], (tour == "atp") & (bo5 == 1)), 4)
    # I-002 comp given I-001's column (and kappa x price): the part of comp not already in the price-leverage term
    k = AUX["kappa"]
    X2 = np.column_stack([X, z * k])
    out["I-002 comp: r2 on 58 + z*kappa"] = round(r2_on(X2, C["I-002 comp"]), 3)
    out["corr(I-001, I-002)"] = corr(C["I-001 z*kappa"], C["I-002 comp"])
    # I-008: its residual on the 58 inputs against the leverage and exposure columns
    res8 = np.full(len(P), np.nan)
    ok = np.isfinite(C["I-008 z_C1"])
    b, *_ = np.linalg.lstsq(X[ok], C["I-008 z_C1"][ok], rcond=None)
    res8[ok] = C["I-008 z_C1"][ok] - X[ok] @ b
    for other in ("I-001 z*kappa", "I-002 comp", "I-014 x", "I-015 E2", "I-012 shield", "I-013 e_ace"):
        out[f"corr(resid I-008, {other})"] = corr(res8, C[other])
    out["corr(I-012 shield, I-013 e_ace)"] = corr(C["I-012 shield"], C["I-013 e_ace"])
    out["corr(I-014, I-015)"] = corr(C["I-014 x"], C["I-015 E2"])
    out["corr(I-016, I-015)"] = corr(C["I-016 x"], C["I-015 E2"])
    # I-048 against the surface-IOS deviation placebo (R2 sdev)
    out["corr(I-048 E, plain dE)"] = corr(C["I-048 E"], C["I-048 plain dE (R2 placebo)"])
    Xe = np.column_stack([X, C["I-048 plain dE (R2 placebo)"]])
    out["I-048 E: r2 on 58 + plain dE"] = round(r2_on(Xe, C["I-048 E"]), 3)
    # slope-family modulators: how correlated are they (price x s columns)?
    fam = ["I-001 z*kappa", "I-034 z*|d1|", "I-036 z*O", "I-037 z*a", "I-049 z*E", "I-054 z*S", "I-084 z*T"]
    out["corr matrix of price-slope columns"] = {a: {b_: corr(C[a], C[b_]) for b_ in fam} for a in fam}
    out["corr(I-036 z*O, I-084 z*T)"] = corr(C["I-036 z*O"], C["I-084 z*T"])
    # I-053 / I-024 / I-070 / I-068 overlaps (age family)
    out["corr(I-068, I-046)"] = corr(C["I-068 x"], C["I-046 x"])
    out["corr(I-071 x, I-071 dg)"] = corr(C["I-071 x"], C["I-071 dg"])
    out["corr(I-080, I-034 z*|d1|)"] = corr(C["I-080 d1*(-A)"], C["I-034 z*|d1|"])
    (OUT / "overlaps.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k_: v for k_, v in out.items() if k_ != "corr matrix of price-slope columns"}, indent=0))
    for a, row in out["corr matrix of price-slope columns"].items():
        print(a.ljust(16), " ".join(f"{v:+.2f}" for v in row.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
