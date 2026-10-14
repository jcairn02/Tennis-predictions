"""R4 test verifier: the null and planted-effect tables from verifier_worlds.py's chunks (synthetic outcomes only).

Per (world, beta, capture), pooled over seeds (the s999 smoke chunks are left out):
    P2       mean; the exact expected gain given the replicate's forecasts (mean over replicates = the unconditional
             expectation); G_star (perfect calibration, no seed noise); bias = mean(P2 - expected gain); SD(P2);
             RMS of the registered SE and of the block-only SE; rejection rates (lo > 0, hi < 0) and coverage of the
             conditional and the unconditional expected gain, for the registered (block + seed) interval and the
             block-only interval; power = P(lo > 0)
    S0       mean b, bias b - beta, SD(b), RMS(se), coverage of beta, rejection rates, power
    S10, S13, S14, the decision rows
Monte Carlo SEs: sqrt(p (1 - p) / R) for rates (and 3 / R, the one-sided 95% bound, when a count is 0); SD / sqrt(R)
for means.

Writes data/studies/serve_speed_tabpfn/design/verifier_tables.json and verifier_tables.csv.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_tables.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402

DIR = C.OUT / "design" / "verifier_worlds"
OUT = C.OUT / "design" / "verifier_tables.json"
T32 = float(student_t.ppf(0.975, 32))


def rate(x: pd.Series) -> dict:
    x = x.astype(bool)
    n, p = len(x), float(x.mean())
    return {"rate": p, "mc_se": float(np.sqrt(p * (1 - p) / n)) if 0 < p < 1 else None,
            "upper95_if_zero": 3 / n if p == 0 else None, "count": int(x.sum())}


def mean(x: pd.Series) -> dict:
    return {"mean": float(x.mean()), "mc_se": float(x.std(ddof=1) / np.sqrt(len(x)))}


def summarise(meta: dict, t: pd.DataFrame) -> dict:
    beta, cap = meta["beta"], meta["capture"]
    w = meta["world"]
    if "P2_se" not in t:                                        # w1: derive the SEs from the interval widths
        t["P2_se"] = (t["P2_hi"] - t["P2_lo"]) / (2 * T32)
    t["P2_se_block_derived"] = (t["P2_hi_block_only"] - t["P2_lo_block_only"]) / (2 * T32)
    eg = t["expected_gain"]
    e_bar = float(eg.mean())
    out = {"world": w, "beta": beta, "capture": cap, "reps": int(len(t)), "G_star": meta["G_star"],
           "P2_mean": mean(t["P2"]), "expected_gain_mean": mean(eg), "bias_P2_minus_expected": mean(t["P2"] - eg),
           "sd_P2": float(t["P2"].std(ddof=1)), "sd_P2_minus_expected": float((t["P2"] - eg).std(ddof=1)),
           "rms_se_registered": float(np.sqrt((t["P2_se"] ** 2).mean())),
           "rms_se_block_only": float(np.sqrt((t["P2_se_block_derived"] ** 2).mean())),
           "P2_reject_pos": rate(t["P2_lo"] > 0), "P2_reject_neg": rate(t["P2_hi"] < 0),
           "P2_reject_two_sided": rate((t["P2_lo"] > 0) | (t["P2_hi"] < 0)),
           "P2_block_only_reject_pos": rate(t["P2_lo_block_only"] > 0),
           "P2_block_only_reject_neg": rate(t["P2_hi_block_only"] < 0),
           "P2_block_only_reject_two_sided": rate((t["P2_lo_block_only"] > 0) | (t["P2_hi_block_only"] < 0)),
           "P2_cover_conditional": rate((t["P2_lo"] <= eg) & (eg <= t["P2_hi"])),
           "P2_cover_unconditional": rate((t["P2_lo"] <= e_bar) & (e_bar <= t["P2_hi"])),
           "P2_block_only_cover_conditional": rate((t["P2_lo_block_only"] <= eg) & (eg <= t["P2_hi_block_only"])),
           "P2_block_only_cover_unconditional": rate((t["P2_lo_block_only"] <= e_bar) & (e_bar <= t["P2_hi_block_only"])),
           "P2_cover_G_star": rate((t["P2_lo"] <= meta["G_star"]) & (meta["G_star"] <= t["P2_hi"]))}
    if {"P2_v_seed_base", "P2_v_seed_arm"} <= set(t.columns):
        out["mean_seed_var_share_of_se2"] = float(((t["P2_v_seed_base"] + t["P2_v_seed_arm"]) / t["P2_se"] ** 2).mean())
    if "P2_lo_week" in t:
        out["P2_week_reject_two_sided"] = rate((t["P2_lo_week"] > 0) | (t["P2_hi_week"] < 0))
    if "S0_b" in t:
        if "S0_se" not in t:
            t["S0_se"] = (t["S0_hi"] - t["S0_lo"]) / (2 * T32)
        out.update({"S0_mean": mean(t["S0_b"]), "S0_bias": mean(t["S0_b"] - beta), "S0_sd": float(t["S0_b"].std(ddof=1)),
                    "S0_rms_se": float(np.sqrt((t["S0_se"] ** 2).mean())),
                    "S0_cover_beta": rate((t["S0_lo"] <= beta) & (beta <= t["S0_hi"])),
                    "S0_reject_pos": rate(t["S0_lo"] > 0), "S0_reject_neg": rate(t["S0_hi"] < 0),
                    "S0_reject_two_sided": rate((t["S0_lo"] > 0) | (t["S0_hi"] < 0)),
                    "S10_mean": mean(t["S10_a"]),
                    "S10_expected": cap * beta / (0.9 if w == "w1" else 0.92),
                    "S13_mean": mean(t["S13"]), "S13_reject_pos": rate(t["S13_lo"] > 0),
                    "S14_mean": mean(t["S14"]), "S14_reject_pos": rate(t["S14_lo"] > 0),
                    "S14_reject_neg": rate(t["S14_hi"] < 0),
                    "decision_rows": {str(k): int(v) for k, v in t["decision_row"].value_counts().sort_index().items()}})
    return out


def main() -> int:
    groups: dict = {}
    for path in sorted(DIR.glob("*.json")):
        if "_s999" in path.name:
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        key = (d["world"], d["beta"], d["capture"])
        g = groups.setdefault(key, {"meta": d, "parts": [], "files": []})
        g["parts"].append(pd.DataFrame(d["replicates"]))
        g["files"].append(path.name)
    rows = []
    for key, g in sorted(groups.items()):
        s = summarise(g["meta"], pd.concat(g["parts"], ignore_index=True))
        s["files"] = g["files"]
        rows.append(s)
    C.write_json(OUT, {"what": "null and planted-effect tables of score.py on synthetic outcomes (verifier_worlds.py)",
                       "t_975_32": T32, "rows": rows})
    flat = []
    for r in rows:
        f = {}
        for k, v in r.items():
            if isinstance(v, dict) and ("rate" in v or "mean" in v):
                f[k] = v.get("rate", v.get("mean"))
                f[k + "_mcse"] = v.get("mc_se")
            elif not isinstance(v, (dict, list)):
                f[k] = v
        flat.append(f)
    pd.DataFrame(flat).to_csv(OUT.with_suffix(".csv"), index=False)
    show = ["world", "beta", "capture", "reps", "G_star", "P2_mean", "expected_gain_mean", "bias_P2_minus_expected",
            "sd_P2", "rms_se_registered", "rms_se_block_only", "P2_reject_pos", "P2_reject_neg",
            "P2_block_only_reject_pos", "P2_block_only_reject_neg", "P2_cover_conditional",
            "P2_block_only_cover_conditional", "S0_mean", "S0_sd", "S0_rms_se", "S0_cover_beta", "S0_reject_pos",
            "S0_reject_neg"]
    with pd.option_context("display.width", 300, "display.max_columns", 50):
        print(pd.DataFrame(flat)[[c for c in show if c in pd.DataFrame(flat).columns]].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
