"""Summarise the surface-IOS tuning grid (tune.py): for every tour, statistic and half-life, how much each surface
penalty improves the forecast of the statistic in the next match over the pooled IOS, 2013-2018.

Gains are milli-log-loss per unit of the statistic (per serve point, per service game, ...), positive = the surface
model forecasts the statistic better, with paired 95% intervals clustered in four-week blocks (ratio estimator: the
difference in summed log loss over the summed units, block by block). Two references:

    vs_pooled_same_h   the surface model against the pooled IOS at the same half-life (the surface effect alone)
    vs_current         against today's pooled IOS (Stage B's tuned half-life): what replacing today's input would do

The chosen setting per tour and statistic: among the surface variants at today's half-life (a shared penalty, or a
return-only one), the one with the best vs_current gain over all surfaces; today's pooled IOS when none beats it. The
runs at twice the half-life are reported as evidence about memory but never chosen, so that the surface arm differs
from today's inputs only by its surface terms.

Writes data/studies/surface_ios/tuning_summary.csv and tuning_choice.json. build_features.py reads the IOS constants
registry, not tuning_choice.json: a new choice changes no input until it is added as a version and activated
(src/eda/ios_constants/registry.py --add ID --surface-from data/studies/surface_ios/tuning_choice.json).
Run: ./python.sh src/eda/surface_ios/summarise_tuning.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402

TUNE = C.OUT / "tuning"
BLOCK_ORIGIN = np.datetime64("2010-01-04").astype("datetime64[D]").astype(np.int64)


def ratio_gain(ll_base, ll_new, units, block) -> dict:
    d = ll_base - ll_new
    labels, ix = np.unique(block, return_inverse=True)
    Db = np.bincount(ix, weights=d)
    Ub = np.bincount(ix, weights=units)
    U = Ub.sum()
    g = Db.sum() / U
    G = len(labels)
    se = np.sqrt(G / (G - 1) * np.sum((Db - g * Ub) ** 2)) / U
    q = student_t.ppf(0.975, G - 1)
    return {"gain": 1000 * g, "lo": 1000 * (g - q * se), "hi": 1000 * (g + q * se)}


def _inf(v) -> float:
    return np.inf if v is None else float(v)


def main() -> int:
    runs = [json.loads(line) for line in (TUNE / "runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    R = pd.DataFrame([{"tour": r["tour"], "stat": r["stat"], "h_mult": r["h_mult"],
                       "variant": r.get("variant", "shared"),
                       "kE_mult": _inf(r.get("kE_mult", r["ks_mult"])), "kF_mult": _inf(r.get("kF_mult", r["ks_mult"])),
                       "tag": r["tag"], "h": r["h"], "kappa": r["kappa"], "seconds": r["seconds"],
                       "not_converged": r["solver"]["not_converged"],
                       "better_all": r["score"]["all"]["better_milli_per_unit"],
                       "better_main_tour": r["main_tour"]["better_milli_per_unit"]} for r in runs])
    pooled = ~np.isfinite(R["kE_mult"]) & ~np.isfinite(R["kF_mult"])
    R.loc[pooled, "variant"] = "pooled"
    R["ks_mult"] = np.where(R["variant"] == "shared", R["kE_mult"], np.inf)
    tds = {t: C.load_tour(t) for t in ("atp", "wta")}
    rows = []
    for (tour, stat), g in R.groupby(["tour", "stat"]):
        td = tds[tour]
        units = td["stats"][stat]["d"]
        block = (td["day"] - BLOCK_ORIGIN) // 28
        lls = {}
        for r in g.itertuples():
            z = np.load(TUNE / f"ll_{r.tag}.npz")
            lls[(r.h_mult, r.kE_mult, r.kF_mult)] = (z["rows"], z["ll"])
        cur_rows, cur_ll = lls.get((1.0, np.inf, np.inf), (None, None))
        for r in g.itertuples():
            rr, ll = lls[(r.h_mult, r.kE_mult, r.kF_mult)]
            rec = {"tour": tour, "stat": stat, "h_mult": r.h_mult, "variant": r.variant, "ks_mult": r.ks_mult,
                   "kE_mult": r.kE_mult, "kF_mult": r.kF_mult, "h": r.h, "kappa": r.kappa,
                   "not_converged": r.not_converged}
            for ref_name, ref in (("vs_pooled_same_h", lls.get((r.h_mult, np.inf, np.inf))),
                                  ("vs_current", (cur_rows, cur_ll))):
                if ref is None or ref[0] is None:
                    continue
                if not np.array_equal(ref[0], rr):
                    raise RuntimeError(f"{r.tag}: scored rows differ from the reference's")
                for surf_name, code in (("all", None), ("hard", 1), ("clay", 2), ("grass", 3)):
                    m = np.ones(len(rr), dtype=bool) if code is None else (td["surf"][rr] == code)
                    if m.sum() < 50:
                        continue
                    x = ratio_gain(ref[1][m], ll[m], units[rr][m], block[rr][m])
                    for k, v in x.items():
                        rec[f"{ref_name}|{surf_name}|{k}"] = v
            rows.append(rec)
    S = pd.DataFrame(rows).sort_values(["tour", "stat", "h_mult", "variant", "kE_mult", "kF_mult"])
    S.to_csv(C.OUT / "tuning_summary.csv", index=False)
    choice = {}
    fin = lambda v: None if not np.isfinite(v) else float(v)  # noqa: E731
    for (tour, stat), g in S.groupby(["tour", "stat"]):
        # the surface arm changes only the surface terms: today's half-life, the best surface variant, or today's
        # pooled values when no surface variant beats them (the h x 2 runs are evidence about memory, not candidates)
        cur = g[(g["h_mult"] == 1.0) & (g["variant"] == "pooled")].iloc[0]
        cand = g[(g["h_mult"] == 1.0) & (g["variant"] != "pooled")]
        best = cand.loc[cand["vs_current|all|gain"].idxmax()] if len(cand) else cur
        if best["vs_current|all|gain"] <= 0:
            best = cur
        choice[f"{tour}|{stat}"] = {"h_mult": float(best["h_mult"]), "variant": best["variant"],
                                    "ks_mult": fin(best["ks_mult"]), "kE_mult": fin(best["kE_mult"]),
                                    "kF_mult": fin(best["kF_mult"]), "h": best["h"], "kappa": float(best["kappa"]),
                                    "gain_vs_current_all": float(best["vs_current|all|gain"]),
                                    "gain_vs_current_lo": float(best["vs_current|all|lo"]),
                                    "gain_vs_current_hi": float(best["vs_current|all|hi"]),
                                    "gain_vs_current_clay": float(best.get("vs_current|clay|gain", np.nan)),
                                    "gain_vs_current_grass": float(best.get("vs_current|grass|gain", np.nan)),
                                    "gain_vs_current_hard": float(best.get("vs_current|hard|gain", np.nan)),
                                    "current_h": cur["h"]}
    C.jdump(choice, C.OUT / "tuning_choice.json")
    cols = ["tour", "stat", "h_mult", "variant", "kE_mult", "kF_mult", "vs_pooled_same_h|all|gain", "vs_pooled_same_h|all|lo",
            "vs_pooled_same_h|all|hi", "vs_current|all|gain", "vs_current|clay|gain", "vs_current|grass|gain",
            "vs_current|hard|gain"]
    with pd.option_context("display.width", 250, "display.max_rows", 400):
        print(S[[c for c in cols if c in S]].round(3).to_string(index=False))
        print(pd.DataFrame(choice).T.round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
