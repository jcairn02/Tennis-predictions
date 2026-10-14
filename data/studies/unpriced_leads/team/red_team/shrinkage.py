"""R2: how much of a discovery reading should survive? Empirical replication across the whole screened universe
(seasons <= 2024 readings already computed by the team; nothing new is read from outcomes here).

For every screened candidate's orthogonal part (both tours): z_E = the close-lens z on 2013-19, z_L = on 2020-24
(the pool scan stores both; for the builders' candidates they are pooled from the era z's with weights sqrt(n_era)).
* slope of z_L on z_E across candidates (and the mean z_L of candidates with |z_E| >= 2, oriented): replication;
* the persistent true-effect variance from the cross-era covariance, var_true(full) = cov(z_E, z_L) N / sqrt(nE nL),
  and the reliability of a full-discovery z: k = var_true / (var_true + s^2), s = 1.0 and 1.08 (the placebo SD);
  under a normal prior, E[future effect | discovery] = k x discovery, the expected realisation ratio.
Writes shrinkage.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rt_common as R  # noqa: E402

C = R.ROOT / "data" / "studies" / "unpriced_leads"


def era_sizes() -> dict:
    f = R.outcome_free_frame()
    f = f[f["season"].between(2013, 2024)]
    return {e: int(f["season"].between(a, b).sum()) for e, (a, b) in R.ERAS.items()}


def pool_from_eras(df: pd.DataFrame, n: dict, eras: list[str], suffix: str = "") -> np.ndarray:
    num = np.zeros(len(df))
    den = np.zeros(len(df))
    for e in eras:
        z = df[f"z_{e}{suffix}"].to_numpy(float)
        ok = np.isfinite(z)
        num += np.where(ok, z * np.sqrt(n[e]), 0.0)
        den += np.where(ok, n[e], 0.0)
    out = num / np.sqrt(den)
    out[den == 0] = np.nan
    return out


def main() -> int:
    n = era_sizes()
    nE, nL = n["2013-16"] + n["2017-19"], n["2020-22"] + n["2023-24"]
    N = nE + nL
    rows = []
    # the pool scan: eligible both-tour rows, orthogonal parts (diffs and pairs), and raw for comparison
    p = pd.read_csv(C / "pool_scan" / "summary.csv")
    p = p[(p["tour"] == "both") & ~p["unstable"].astype(bool) & ~p["base_dependent"].astype(bool)]
    for _, r in p.iterrows():
        if r["kind"] in ("diff", "pair") and np.isfinite(r.get("z_close_2013_19_orth", np.nan)):
            rows.append({"src": "pool", "name": r["candidate"], "form": "orth", "eligible": bool(r["eligible"]),
                         "zE": r["z_close_2013_19_orth"], "zL": r["z_close_2020_24_orth"], "zF": r["z_pool_orth"]})
        if np.isfinite(r.get("z_close_2013_19", np.nan)):
            rows.append({"src": "pool", "name": r["candidate"], "form": "raw", "eligible": bool(r["eligible"]),
                         "zE": r["z_close_2013_19"], "zL": r["z_close_2020_24"], "zF": r["z_pool"]})
    # the builders: luck, rhythm, extras, market (both tours; names ending __orth are orthogonal parts)
    for src in ("luck", "rhythm", "extras", "market"):
        s = pd.read_csv(C / "candidates" / src / "summary.csv")
        s = s[s["tour"] == "both"]
        if "base" in s.columns:
            s = s[s["base"] == "odds_input"]
        zE = pool_from_eras(s, n, ["2013-16", "2017-19"])
        zL = pool_from_eras(s, n, ["2020-22", "2023-24"])
        for (_, r), a, b in zip(s.iterrows(), zE, zL):
            form = "orth" if str(r["name"]).endswith("__orth") else "raw"
            rows.append({"src": src, "name": r["name"], "form": form, "eligible": True, "zE": a, "zL": b,
                         "zF": r["z_pool"]})
    U = pd.DataFrame(rows)
    U = U[np.isfinite(U["zE"]) & np.isfinite(U["zL"])]
    out = {"era_sizes": n, "nE": nE, "nL": nL}
    for form in ("orth", "raw"):
        for lab, m in (("all", np.ones(len(U), bool)), ("eligible", U["eligible"].to_numpy(bool))):
            V = U[(U["form"] == form).to_numpy() & m]
            zE, zL, zF = V["zE"].to_numpy(float), V["zL"].to_numpy(float), V["zF"].to_numpy(float)
            cov = float(np.cov(zE, zL)[0, 1])
            slope = cov / float(np.var(zE, ddof=1))
            sel = np.abs(zE) >= 2
            vt_full = cov * N / np.sqrt(nE * nL)
            res = {"candidates": int(len(V)), "sd_zE": float(np.std(zE, ddof=1)), "sd_zL": float(np.std(zL, ddof=1)),
                   "sd_zF": float(np.std(zF, ddof=1)), "corr_zE_zL": float(np.corrcoef(zE, zL)[0, 1]),
                   "slope_zL_on_zE": slope, "beta_ratio_late_over_early_implied": slope * np.sqrt(nE / nL),
                   "selected_absZE_ge2": int(sel.sum()),
                   "selected_mean_oriented_zE": float(np.mean(np.abs(zE[sel]))) if sel.any() else None,
                   "selected_mean_oriented_zL": float(np.mean(np.sign(zE[sel]) * zL[sel])) if sel.any() else None,
                   "var_true_full_from_cross_era_cov": vt_full}
            if sel.any():
                # realised share in beta terms for the selected: (mean oriented zL / sqrt(nL)) / (mean |zE| / sqrt(nE))
                res["selected_beta_realisation"] = (res["selected_mean_oriented_zL"] / np.sqrt(nL)) / \
                    (res["selected_mean_oriented_zE"] / np.sqrt(nE))
            for s_ in (1.0, 1.08):
                res[f"k_full_s{s_}"] = vt_full / (vt_full + s_ ** 2) if vt_full > 0 else 0.0
            out[f"{form}_{lab}"] = res
    U.to_csv(R.OUT / "shrinkage_universe.csv", index=False)
    (R.OUT / "shrinkage.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
