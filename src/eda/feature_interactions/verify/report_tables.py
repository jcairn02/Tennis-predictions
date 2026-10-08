"""Harness verifier: markdown tables for meta/harness_verification.md from the summary CSVs and the P2 / effect-size
draws (run summarise.py first). Prints to stdout; one table per --table argument (planted, null, wald, p2, sizes).

Run: ./python.sh src/eda/feature_interactions/verify/report_tables.py --table planted
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402

V = C.OUT / "verify"
Z34 = norm.isf(0.05 / 34)


def f2(x):
    return "–" if pd.isna(x) else f"{x:.2f}"


def planted():
    S = pd.read_csv(V / "summary_planted.csv")
    print("| Column | Δ = 0.1: power z₁ > 1.96 | Δ = 0.1: joint Holm-34 | Δ = 0.2: power | Δ = 0.2: joint | Δ = 0.3: joint | mean z₁ ÷ theory (Δ = 0.2) |")
    print("|---|---|---|---|---|---|---|")
    for col, g in S.groupby("col", sort=False):
        r = {d: g[g.delta == d].iloc[0] for d in (0.1, 0.2, 0.3)}
        print(f"| {col} | {f2(r[0.1].pow196)} ({f2(r[0.1].pow196_theory)}) | {f2(r[0.1].det34)} ({f2(r[0.1].det34_theory)}) | "
              f"{f2(r[0.2].pow196)} ({f2(r[0.2].pow196_theory)}) | {f2(r[0.2].det34)} ({f2(r[0.2].det34_theory)}) | "
              f"{f2(r[0.3].det34)} ({f2(r[0.3].det34_theory)}) | {f2(r[0.2].mean_z1 / r[0.2].z1_theory)} |")
    m = S.groupby("delta")[["pow196", "pow196_theory", "det34", "det34_theory", "det40"]].mean()
    for d, r in m.iterrows():
        print(f"| **mean, Δ = {d}** | power {f2(r.pow196)} ({f2(r.pow196_theory)}) | joint {f2(r.det34)} ({f2(r.det34_theory)}); "
              f"Holm-40 {f2(r.det40)} | | | | |")


def null():
    S = pd.read_csv(V / "summary_null.csv")
    print("| Column | Draws | SD z₁ | SD z_joint | z_joint > 1.645 (5%) | abs(z_joint) > 1.96 (5%) | z_joint > 2.326 (1%) | filter + replication + z_joint > 1.645 | full gate at Holm-34 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for _, r in S.iterrows():
        print(f"| {r.col} | {r.draws} | {f2(r.sd_z1)} | {f2(r.sd_zj)} | {r.fpr_one_5:.3f} | {r.fpr_two_5:.3f} | {r.fpr_one_1:.3f} | "
              f"{r.fpr_gate_one_5:.3f} | {r.fpr_holm34:.3f} |")
    tot = S.draws.sum()
    w = lambda c: (S[c] * S.draws).sum() / tot  # noqa: E731
    print(f"| **all ({tot} draws)** | | | {f2(np.sqrt((S.sd_zj ** 2 * S.draws).sum() / tot))} | {w('fpr_one_5'):.3f} | "
          f"{w('fpr_two_5'):.3f} | {w('fpr_one_1'):.3f} | {w('fpr_gate_one_5'):.3f} | {w('fpr_holm34'):.4f} |")


def wald():
    S = pd.read_csv(V / "summary_wald.csv")
    print(S.round(3).to_string(index=False))


def p2():
    for name in ("p2_UFIX_nop2_t010", "p2_UFIX_p2_t010", "p2_HEIGHT_t010"):
        p = V / f"{name}.parquet"
        if not p.exists():
            continue
        d = pd.read_parquet(p)
        z = d.z_joint
        row = {"run": name, "draws": len(d), "sd_zj": z.std(), "fpr_one_5_normal": (z > 1.645).mean(),
               "fpr_two_5_normal": (z.abs() > 1.96).mean()}
        if "null_sd" in d:
            row.update({"mean_perm_sd": d.null_sd.mean(), "fpr_one_5_max_count": (np.maximum(d.p_normal, d.p2_mirror) < 0.05).mean(),
                        "fpr_one_5_sdcal": (norm.sf(z / np.maximum(1, d.null_sd)) < 0.05).mean(),
                        "harness_equals_mirror": bool(np.isclose(d.p2_harness.iloc[0], d.p2_mirror.iloc[0]))})
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()})


def sizes():
    d = pd.read_parquet(V / "sizes_check.parquet")
    s = d[d.n_p1 == 0].groupby(["col", "delta"])
    print(s[["gain_disc_true", "gain_disc_both", "lo_disc_both", "hi_disc_both", "gain_rep_true", "gain_repl_both",
             "lo_repl_both", "hi_repl_both"]].mean().round(3).to_string())
    print(s[["gain_disc_both", "gain_repl_both"]].agg(["std", "size"]).round(3).to_string())
    p = d[d.n_p1 > 0]
    print(p.groupby(["col", "delta"])[["p1_null_sd", "widen", "z1"]].agg(["mean", "min", "max"]).round(3).to_string())


if __name__ == "__main__":
    {"planted": planted, "null": null, "wald": wald, "p2": p2, "sizes": sizes}[sys.argv[sys.argv.index("--table") + 1]]()
