"""Final-test verifier, round 2 (checkpoint 2, R-A): the arm B14 and the three-gain effect size on SYNTHETIC outcomes.

Same DGP, settings, seeds and draw order as synth_power.py (so replicate k of each setting is the same draw as in
synth_replicates.csv). Per replicate: final_test.parameters / primary / effect (now three paired gains); the
pseudo-true gain* of each comparison under the true probabilities; the additivity F_vs_B = F_vs_B14 + B14_vs_B; and
the primary and F-vs-B gain against the earlier run's values (the primary must be unchanged).

    ./python.sh src/eda/feature_interactions/verify_final/b14_synth.py --reps0 2000 --reps 1000
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
from src.eda.feature_interactions.verify_final.synth_power import TARGETS, arg, beta_for, population_gain  # noqa: E402

FT = HN.FT
CMP = ("F_vs_B14", "B14_vs_B", "F_vs_B")


def one(syn: HN.Synth, beta: float, rng: np.random.Generator) -> dict:
    syn.draw(beta, rng)
    params = FT.parameters(syn.xs)
    pr = FT.primary(syn.f, syn.xs, params)
    ef = FT.effect(syn.f, syn.xs, params)
    pt = syn.p[syn.iF]
    lb, lf, l14 = FT.deployed(syn.f, syn.z16, syn.xs, params, b14=True)
    e = {"B": HN.ce(pt, expit(lb)), "F": HN.ce(pt, expit(lf)), "B14": HN.ce(pt, expit(l14))}
    star = {"F_vs_B14": e["B14"] - e["F"], "B14_vs_B": e["B"] - e["B14"], "F_vs_B": e["B"] - e["F"]}
    r = {"b": pr["b"], "lo": pr["lo"], "hi": pr["hi"],
         "add_err": ef["F_vs_B"]["gain"] - ef["F_vs_B14"]["gain"] - ef["B14_vs_B"]["gain"],
         "n_equal": ef["F_vs_B"]["n"] == ef["F_vs_B14"]["n"] == ef["B14_vs_B"]["n"] == len(syn.f),
         "s14_atp25": params[2025]["b14"]["s_atp"], "s_atp25": params[2025]["nudge"]["s_atp"]}
    for c in CMP:
        r[f"{c}_gain"], r[f"{c}_lo"], r[f"{c}_hi"] = ef[c]["gain"], ef[c]["lo"], ef[c]["hi"]
        r[f"{c}_star"] = float(1000 * star[c].mean())
    return r


def summary(d: pd.DataFrame, old: pd.DataFrame | None, target: float, beta: float, pg: float) -> dict:
    s = {"target_mll": target, "beta_per_sd": beta, "population_gain_mll": pg, "reps": len(d),
         "max_abs_additivity_error_mll": float(d["add_err"].abs().max()), "all_n_equal": bool(d["n_equal"].all())}
    for c in CMP:
        g, st, lo, hi = d[f"{c}_gain"], d[f"{c}_star"], d[f"{c}_lo"], d[f"{c}_hi"]
        bias = g - st
        s[c] = {"gain_mean": g.mean(), "gain_star_mean": st.mean(), "bias_mean": bias.mean(),
                "bias_mc_se": bias.std() / np.sqrt(len(d)), "gain_sd": g.std(),
                "covers_gain_star": float(((lo <= st) & (st <= hi)).mean()),
                "interval_above_0": float((lo > 0).mean()), "interval_below_0": float((hi < 0).mean())}
    if old is not None and len(old) >= len(d):
        o = old.iloc[: len(d)].reset_index(drop=True)
        s["primary_vs_round1_max_abs_diff"] = {k: float(np.nanmax(np.abs(d[k].to_numpy() - o[k].to_numpy())))
                                              for k in ("b", "lo", "hi")}
        s["F_vs_B_vs_round1_gain_max_abs_diff"] = float(np.max(np.abs(d["F_vs_B_gain"].to_numpy() - o["gain"].to_numpy())))
    s["slope_b14_minus_nudge_atp25_mean"] = float((d["s14_atp25"] - d["s_atp25"]).mean())
    return s


def main() -> int:
    warnings.simplefilter("ignore")
    reps0, reps = arg("--reps0", 2000), arg("--reps", 1000)
    syn = HN.Synth()
    old_all = pd.read_csv(HN.OUT / "synth_replicates.csv")
    res, rows = [], []
    for i, target in enumerate(TARGETS):
        beta = beta_for(syn, target)
        rng = np.random.default_rng(20261007 + i)
        n = reps0 if target == 0 else reps
        t0 = time.time()
        d = pd.DataFrame([one(syn, beta, rng) for _ in range(n)])
        d["target"] = target
        rows.append(d)
        old = old_all[old_all["target"] == target].reset_index(drop=True)
        s = summary(d, old, target, beta, population_gain(syn, beta))
        s["seconds"] = time.time() - t0
        res.append(s)
        print(json.dumps(s, default=float)[:2400], flush=True)
    pd.concat(rows).to_csv(HN.OUT / "b14_replicates.csv", index=False)
    (HN.OUT / "b14_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
