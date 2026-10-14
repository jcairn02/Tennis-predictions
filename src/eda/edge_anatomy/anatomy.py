"""C2 of the edge-anatomy study: what the current model's disagreements with the close are made of, and which parts came
true.

Reads analysis.parquet (data.py). For each window (2025 - 28 Jul 2026; 2020-2024) and tour, debut seasons out:
    d_s1 = logit(stage 1, calibrated) - logit(recalibrated price): TabPFN's own disagreement;
    d_s2 = logit(both stages) - logit(stage 1, calibrated): the men's serve-speed offset (0 for women).

1. The surrogate (no result read). d_s1 is regressed by least squares on the model's inputs, grouped:
       price shape  L, L|L|, L^3 (L = the recalibrated price's log-odds): TabPFN re-drawing the price's curve;
       context      L x the context indicators (level, surface, best of five, indoor, late rounds);
       ratings, schedule and body, box-score form, IOS profile: the RMS-scaled A - B inputs (missing = 0).
   R^2, and each group's Shapley share of it (every subset of the six groups fitted: 64 regressions).
   The group's part of the disagreement is d_f = X_f b_f from the full surrogate; the rest, e = d_s1 - sum d_f, is
   what the surrogate cannot write as a sum of linear terms (interactions, non-linearity).
2. Which parts came true (results read). logit P = logit(price) + sum_f r_f d_f + r_e e + r_2 d_s2: r = 1, the part is
   right-sized; 0, it is noise; above 1, the model under-uses it. Cluster-robust SEs (four-week blocks).
3. What each part is worth as the model uses it: the gain lost when the part is removed from the final forecast,
   1000 x mean(LL(expit(logit q - d_f)) - LL(q)), + = the part helps, with its interval over blocks.

Writes data/studies/edge_anatomy/anatomy_parts.csv and anatomy_shapley.csv.
Run: ./python.sh src/eda/edge_anatomy/anatomy.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

WINDOWS = {"2025-26": (2025, 2026), "2020-24": (2020, 2021, 2022, 2023, 2024),
           "2025": (2025,), "2026": (2026,)}     # 2025 and 2026 apart: added after the first read (process log)
GROUPS = ("price shape", "context", "ratings", "schedule", "form", "ios")


def design(g: pd.DataFrame) -> dict[str, np.ndarray]:
    L = S.lg(g["q_close"].to_numpy())
    out = {"price shape": np.column_stack([L, L * np.abs(L), L ** 3])}
    ctx = []
    for c, ref in (("in_level", 4.0), ("in_surface", 0.0), ("in_best_of", 3.0), ("in_indoor", 0.0)):
        v = g[c].to_numpy()
        for lev in sorted(set(v[np.isfinite(v)])):
            if lev != ref and (v == lev).sum() >= 50:
                ctx.append(L * (v == lev))
    ctx.append(L * np.isin(g["in_round"].to_numpy(), (15.0, 16.0, 17.0, 10.0)))
    out["context"] = np.column_stack(ctx)
    for fam in ("ratings", "schedule", "form", "ios"):
        cols = []
        members = E.FAMILIES[fam]
        done = set()
        for c in members:
            if c.endswith("_a") or c.endswith("_b"):
                stem = c[:-2]
                if stem in done:
                    continue
                done.add(stem)
                x = g[f"in_{stem}_a"].to_numpy(float) - g[f"in_{stem}_b"].to_numpy(float)
            else:
                x = g[f"in_{c}"].to_numpy(float)
            x = np.where(np.isfinite(x), x, 0.0)
            rms = float(np.sqrt(np.mean(x ** 2)))
            cols.append(x / rms if rms > 0 else x)
        out[fam] = np.column_stack(cols)
    return out


def ols(X: np.ndarray, d: np.ndarray) -> tuple[np.ndarray, float]:
    b, *_ = np.linalg.lstsq(X, d, rcond=None)
    r = d - X @ b
    return b, 1 - float(r @ r) / float(d @ d)          # no intercept: d is antisymmetric, R^2 about 0


def shapley(parts: dict[str, np.ndarray], d: np.ndarray) -> dict[str, float]:
    names = list(parts)
    r2 = {}
    for k in range(len(names) + 1):
        for sub in itertools.combinations(names, k):
            r2[sub] = 0.0 if not sub else ols(np.column_stack([parts[s] for s in sub]), d)[1]
    m = len(names)
    out = {}
    from math import factorial
    for n in names:
        v = 0.0
        others = [x for x in names if x != n]
        for k in range(m):
            for sub in itertools.combinations(others, k):
                w = factorial(k) * factorial(m - k - 1) / factorial(m)
                with_n = tuple(x for x in names if x in sub or x == n)
                v += w * (r2[with_n] - r2[tuple(x for x in names if x in sub)])
        out[n] = v
    return out


def run() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_parquet(E.OUT / "analysis.parquet")
    df = df[(df["season"] >= 2020) & ~df["debut"]]
    rows, shap_rows = [], []
    for wname, window in WINDOWS.items():
        for tour in ("atp", "wta"):
            g = df[df["season"].isin(window) & (df["tour"] == tour)].reset_index(drop=True)
            y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
            Lc = S.lg(g["q_close"].to_numpy())
            d1 = S.lg(g["q_full_s1"].to_numpy()) - Lc
            d2 = S.lg(g["q_full"].to_numpy()) - S.lg(g["q_full_s1"].to_numpy())
            parts = design(g)
            X = np.column_stack([parts[k] for k in GROUPS])
            b, r2 = ols(X, d1)
            comps, start = {}, 0
            for k in GROUPS:
                w = parts[k].shape[1]
                comps[k] = parts[k] @ b[start:start + w]
                start += w
            comps["unexplained (interactions, non-linear)"] = d1 - X @ b
            if tour == "atp":
                comps["stage 2 (speed offset)"] = d2
            sh = shapley(parts, d1)
            for k, v in sh.items():
                shap_rows.append({"window": wname, "tour": tour, "group": k, "shapley_r2": v, "r2_total": r2,
                                  "sd_d_s1": float(np.std(d1))})
            names = list(comps)
            Z = np.column_stack([comps[k] for k in names])
            r, H = S.fit_offset(Z, y, Lc)
            V = S.cluster_cov(Z, y, Lc, r, H, blk)
            q = g["q_full"].to_numpy()
            lq = S.lg(q)
            total = S.gain(g["q_close"], q, y, blk)
            for i, k in enumerate(names):
                worth = S.mean_ci(S.ll(expit(lq - comps[k]), y) - S.ll(q, y), blk)
                rows.append({"window": wname, "tour": tour, "part": k, "sd": float(np.std(comps[k])),
                             "r": float(r[i]), "r_se": float(np.sqrt(V[i, i])),
                             **{f"worth_{a}": worth[a] for a in ("est", "lo", "hi", "p_better")},
                             "worth_verdict": S.verdict(worth), "total_gain": total["est"], "n": int(len(g))})
            E.log(f"{wname} {tour}: R2 {r2:.3f}, total gain {total['est']:+.2f}")
    return pd.DataFrame(rows), pd.DataFrame(shap_rows)


def main() -> int:
    parts, shap = run()
    parts.to_csv(E.OUT / "anatomy_parts.csv", index=False)
    shap.to_csv(E.OUT / "anatomy_shapley.csv", index=False)
    pd.set_option("display.width", 250)
    print(parts.round(3).to_string(index=False))
    print(shap.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
