"""Final-test verifier, step 2: size, power, coverage and bias of final_test's primary and effect size on SYNTHETIC
outcomes (harness.py: real eta_B and x, y ~ Bernoulli(expit(a_tour eta_B + beta x)), every season 2014-2026).

Each replicate draws all 2014-2026 outcomes, then runs the real final_test.parameters (walk-forward nudge from 2014 and
calibration from 2019, seasons up to Y-1), final_test.primary and final_test.effect. Pseudo-true values per replicate:
b* = the encompassing coefficient fitted on the true probabilities in place of y (same deviation, same fitted nudge);
gain* = the expected paired log-loss gain of the deployed F over the deployed B under the true probabilities.
beta is set so that the population gain (the oracle F over the best-calibrated B without x, on the 8,520 test matches)
is 0, 0.1, 0.2 and 0.5 mLL.

    ./python.sh src/eda/feature_interactions/verify_final/synth_power.py --reps0 2000 --reps 1000 --subsets 1000
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.verify_final import harness as HN  # noqa: E402

FT, TT, T = HN.FT, HN.TT, HN.T
TARGETS = (0.0, 0.1, 0.2, 0.5)


def arg(name: str, default: int) -> int:
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def population_gain(syn: HN.Synth, beta: float) -> float:
    f, p = syn.f, syn.p_true(beta)[syn.iF]
    q = np.full(len(f), np.nan)
    for t in ("atp", "wta"):
        k = (f["tour"] == t).to_numpy()
        a, _ = T.fit_logistic(syn.z16[k][:, None], p[k])
        q[k] = expit(a[0] * syn.z16[k])
    return float(1000 * np.mean(HN.ce(p, q) - HN.ce(p, p)))


def beta_for(syn: HN.Synth, target: float) -> float:
    if target == 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if population_gain(syn, mid) < target else (lo, mid)
    return 0.5 * (lo + hi)


def one(syn: HN.Synth, beta: float, rng: np.random.Generator, subsets: dict | None = None) -> dict:
    syn.draw(beta, rng)
    params = FT.parameters(syn.xs)
    pr = FT.primary(syn.f, syn.xs, params)
    ef = FT.effect(syn.f, syn.xs, params)
    pt = syn.p[syn.iF]
    lb8, lf8 = FT.deployed(syn.f, syn.z8, syn.xs, params)
    b_star = TT.encompassing(syn.f.assign(a_won=pt), syn.z0, lf8 - lb8)["b"]
    lb, lf = FT.deployed(syn.f, syn.z16, syn.xs, params)
    g_star = float(1000 * np.mean(HN.ce(pt, expit(lb)) - HN.ce(pt, expit(lf))))
    r = {"b": pr["b"], "se": pr["se"], "lo": pr["lo"], "hi": pr["hi"], "p1": pr["p_one_sided"], "p2": pr["p_two_sided"],
         "df": pr["df"], "b_star": b_star, "gain": ef["gain"], "g_lo": ef["lo"], "g_hi": ef["hi"], "g_star": g_star,
         "bn25": params[2025]["nudge"]["b"], "bn26": params[2026]["nudge"]["b"],
         "s_atp25": params[2025]["nudge"]["s_atp"], "cal_atp25": params[2025]["cal"]["atp"]}
    for name, mask in (subsets or {}).items():
        g = syn.f[mask].reset_index(drop=True)
        q = FT.primary(g, syn.xs, params)
        r[f"sub_{name}_p2"], r[f"sub_{name}_lo"], r[f"sub_{name}_df"] = q["p_two_sided"], q["lo"], q["df"]
    return r


def summary(d: pd.DataFrame, beta: float, target: float, pop_gain: float) -> dict:
    n = len(d)
    rej2 = (d["lo"] > 0) | (d["hi"] < 0)
    cover_b = (d["lo"] <= d["b_star"]) & (d["b_star"] <= d["hi"])
    cover_g = (d["g_lo"] <= d["g_star"]) & (d["g_star"] <= d["g_hi"])
    bias = d["gain"] - d["g_star"]
    out = {"target_mll": target, "beta_per_sd": beta, "population_gain_mll": pop_gain, "reps": n,
           "two_sided_rejection": float(rej2.mean()), "interval_above_0": float((d["lo"] > 0).mean()),
           "interval_below_0": float((d["hi"] < 0).mean()), "one_sided_p_below_05": float((d["p1"] < 0.05).mean()),
           "b_median": float(d["b"].median()), "b_star_median": float(d["b_star"].median()),
           "b_interval_covers_b_star": float(cover_b.mean()),
           "nudge_b_mean_2025": float(d["bn25"].mean()), "nudge_b_sd_2025": float(d["bn25"].std()),
           "gain_mean": float(d["gain"].mean()), "gain_star_mean": float(d["g_star"].mean()),
           "gain_bias_mean": float(bias.mean()), "gain_bias_mc_se": float(bias.std() / np.sqrt(n)),
           "gain_sd": float(d["gain"].std()), "gain_interval_covers_gain_star": float(cover_g.mean()),
           "gain_interval_above_0": float((d["g_lo"] > 0).mean())}
    for c in [c for c in d.columns if c.startswith("sub_") and c.endswith("_p2")]:
        nm = c[4:-3]
        out[f"subset_{nm}_two_sided_rejection"] = float((d[c] < 0.05).mean())
        out[f"subset_{nm}_df"] = int(d[f"sub_{nm}_df"].iloc[0])
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    reps0, reps, nsub = arg("--reps0", 2000), arg("--reps", 1000), arg("--subsets", 1000)
    syn = HN.Synth()
    f = syn.f
    subsets = {"atp": (f["tour"] == "atp").to_numpy(), "wta": (f["tour"] == "wta").to_numpy(),
               "2025": (f["season"] == 2025).to_numpy(), "2026": (f["season"] == 2026).to_numpy(),
               "TMLclean": ~FT.tml_exposed(f["match_id"])}
    rows, res = [], []
    for i, target in enumerate(TARGETS):
        beta = beta_for(syn, target)
        pg = population_gain(syn, beta)
        rng = np.random.default_rng(20261007 + i)
        n = reps0 if target == 0 else reps
        t0 = time.time()
        d = pd.DataFrame([one(syn, beta, rng, subsets if (target == 0 and k < nsub) else None) for k in range(n)])
        d["target"] = target
        rows.append(d)
        s = summary(d, beta, target, pg)
        s["seconds"] = time.time() - t0
        res.append(s)
        print(json.dumps(s, default=float)[:1500], flush=True)
    HN.OUT.mkdir(parents=True, exist_ok=True)
    pd.concat(rows).to_csv(HN.OUT / "synth_replicates.csv", index=False)
    (HN.OUT / "synth_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
