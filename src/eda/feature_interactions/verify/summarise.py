"""Harness verifier: tables from the simulation outputs (planted_*.parquet, wald_*.parquet, p2_*.parquet) against the
critique's tables 1.4 and 1.5 and the normal theory at this frame's sizes.

Run: ./python.sh src/eda/feature_interactions/verify/summarise.py
Writes data/studies/feature_interactions/verify/summary_*.csv
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2, ncx2, norm
from scipy.stats import f as fdist

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402

V = C.OUT / "verify"
Z34, Z40 = norm.isf(0.05 / 34), norm.isf(0.05 / 40)
CRIT = {0.1: (0.78, 0.53), 0.2: (0.96, 0.90), 0.3: (np.nan, 0.99)}   # table 1.4 power at 1.96; 1.5 joint Holm


def theory(n1, n2, g1, g2, zline=Z34, m=400_000, seed=0):
    rng = np.random.default_rng(seed)
    z1 = rng.normal(np.sqrt(2 * n1 * g1 / 1000), 1, m)
    z2 = rng.normal(np.sqrt(2 * n2 * g2 / 1000), 1, m)
    zj = (np.sqrt(n1) * z1 + np.sqrt(n2) * z2) / np.sqrt(n1 + n2)
    return float(((z1 > 1) & (z2 > 0.67) & (zj > zline)).mean()), float(norm.sf(1.96 - np.sqrt(2 * n1 * g1 / 1000)))


def planted(D: pd.DataFrame) -> pd.DataFrame:
    D = D.assign(det34=D.filter_pass & D.replicates & (D.z_joint > Z34),
                 det40=D.filter_pass & D.replicates & (D.z_joint > Z40), pow196=D.z1 > 1.96)
    out = []
    for (col, delta), g in D.groupby(["col", "delta"], sort=False):
        t34, t196 = theory(g.n1.iloc[0], g.n2.iloc[0], g.gain_disc.iloc[0], g.gain_rep.iloc[0])
        cp, cj = CRIT.get(delta, (np.nan, np.nan))
        out.append({"col": col, "delta": delta, "draws": len(g), "beta": g.beta.iloc[0], "gain_disc": g.gain_disc.iloc[0],
                    "gain_rep": g.gain_rep.iloc[0], "pow196": g.pow196.mean(), "pow196_theory": t196, "crit_14": cp,
                    "det34": g.det34.mean(), "det34_theory": t34, "det40": g.det40.mean(), "crit_15": cj,
                    "mean_z1": g.z1.mean(), "z1_theory": np.sqrt(2 * g.n1.iloc[0] * g.gain_disc.iloc[0] / 1000),
                    "sd_z1": g.z1.std(), "b1_over_beta": g.b1.mean() / g.beta.iloc[0] if g.beta.iloc[0] else np.nan,
                    "se_ratio": (g.se1 / g.se_model1).mean()})
    return pd.DataFrame(out)


def nulls(D: pd.DataFrame) -> pd.DataFrame:
    out = []
    for col, g in D[D.delta == 0].groupby("col", sort=False):
        out.append({"col": col, "draws": len(g), "sd_z1": g.z1.std(), "sd_z2": g.z2.std(), "sd_zj": g.z_joint.std(),
                    "mean_zj": g.z_joint.mean(), "fpr_one_5": (g.z_joint > 1.645).mean(),
                    "fpr_two_5": (g.z_joint.abs() > 1.96).mean(), "fpr_one_1": (g.z_joint > 2.326).mean(),
                    "fpr_gate_one_5": (g.filter_pass & g.replicates & (g.z_joint > 1.645)).mean(),
                    "fpr_holm34": (g.filter_pass & g.replicates & (g.z_joint > Z34)).mean(),
                    "se_ratio": (g.se1 / g.se_model1).mean()})
    return pd.DataFrame(out)


def wald(D: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (blk, delta), g in D.groupby(["block", "delta"], sort=False):
        k, n = g.k.iloc[0], g.n1.iloc[0] + g.n2.iloc[0]
        crit = chi2.isf(0.05 / 34, k)
        lam = 2 * n * g.gain_pooled.iloc[0] / 1000
        row = {"block": blk, "k": k, "delta": delta, "draws": len(g),
               "det34": (g.filter_pass & g.replicates & (g.p_joint < 0.05 / 34)).mean(),
               "joint34": (g.p_joint < 0.05 / 34).mean(), "joint34_theory": ncx2.sf(crit, k, lam) if lam > 0 else 0.05 / 34,
               "filter": g.filter_pass.mean(), "replicates": g.replicates.mean(), "mean_W1_over_k": (g.W1 / k).mean(),
               "fpr_joint_5": (g.p_joint < 0.05).mean()}
        if "W_union" in g and g["W_union"].notna().all():
            G = 128                                            # four-week blocks in 2014-2024
            wmin = g[["W_block", "W_player", "W_union"]].min(axis=1)
            p_fix = fdist.sf(wmin / k * (G - k) / (G - 1), k, G - k)
            row["fpr_joint_5_fix"] = float((p_fix < 0.05).mean())
            row["det34_fix"] = float((g.filter_pass & g.replicates & (p_fix < 0.05 / 34)).mean())
            row["joint34_fix"] = float((p_fix < 0.05 / 34).mean())
            for c in ("model", "block", "player", "union"):
                row[f"Wj_{c}_over_k"] = (g[f"W_{c}"] / k).mean()
            row["trace_pick"] = g.trace_pick.value_counts().to_dict()
            row["trace_vs_minW"] = float((g.W_joint > g[["W_block", "W_player", "W_union"]].min(axis=1) * 1.0001).mean())
            row["union_not_pd"] = float((g.union_min_eig <= 0).mean())
        out.append(row)
    return pd.DataFrame(out)


def main() -> int:
    warnings.simplefilter("ignore")
    pl = [pd.read_parquet(p) for p in sorted(V.glob("planted_*.parquet")) if "smoke" not in p.name]
    if pl:
        D = pd.concat(pl, ignore_index=True)
        D0 = D[D.tau == 0]
        planted(D0[D0.delta > 0]).to_csv(V / "summary_planted.csv", index=False)
        nulls(D0).to_csv(V / "summary_null.csv", index=False)
        for tau, g in D[D.tau > 0].groupby("tau"):
            nulls(g).to_csv(V / f"summary_null_tau{tau}.csv", index=False)
    wl = [pd.read_parquet(p) for p in sorted(V.glob("wald_*.parquet")) if "smoke" not in p.name]
    if wl:
        wald(pd.concat(wl, ignore_index=True)).to_csv(V / "summary_wald.csv", index=False)
    C.log("summaries written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
