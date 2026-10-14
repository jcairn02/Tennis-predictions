"""Design scratch (agent 2): what the mechanism gate implies for the match, and the expected size of the effect.
Pure arithmetic on numbers already computed (no data read except the JSON outputs of the other scripts).

1. The sensitivity of the match win probability to one player's serve-point win probability, from the standard
   independent-points Markov model of tennis (games, tiebreak sets, best of 3 and best of 5), at p_A = p_B = 0.64:
   d logit P(match) / d p_A, in log-odds per percentage point of serve points won.
2. The serve-channel log-odds per km/h of the primary column (A - B of f_hat): that sensitivity times the gate's
   serve-points-won coefficient per km/h (modeller_gate_<policy>_atp.json, controls for box-score form).
3. The expected log-loss gain on matches carrying the column, for a coefficient b per SD of a standardised input with
   variance 1: about 0.5 * b^2 * E[p (1 - p)], in milli-log-loss (mLL).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_power.py
Writes data/studies/serve_speed_tabpfn/design/modeller_power.json
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"


def game(p: float) -> float:
    q = 1 - p
    return p ** 4 * (1 + 4 * q + 10 * q * q) + 20 * p ** 3 * q ** 3 * p * p / (1 - 2 * p * q)


def tiebreak(pa: float, pb: float) -> float:
    """A serves the first point, then alternate in pairs; first to 7 by 2."""
    @lru_cache(maxsize=None)
    def f(a: int, b: int) -> float:
        if a >= 7 and a - b >= 2:
            return 1.0
        if b >= 7 and b - a >= 2:
            return 0.0
        if a >= 6 and b >= 6 and a == b:
            # from deuce-like state: two points, one served by each
            w2 = pa * (1 - pb)
            l2 = (1 - pa) * pb
            return w2 / (w2 + l2)
        n = a + b
        a_serves = (n % 4 == 0) or (n % 4 == 3)
        p = pa if a_serves else 1 - pb
        return p * f(a + 1, b) + (1 - p) * f(a, b + 1)
    return f(0, 0)


def set_prob(pa: float, pb: float, a_first: bool) -> float:
    ga, gb = game(pa), game(pb)

    @lru_cache(maxsize=None)
    def s(a: int, b: int) -> float:
        if a >= 6 and a - b >= 2:
            return 1.0
        if b >= 6 and b - a >= 2:
            return 0.0
        if a == 6 and b == 6:
            return tiebreak(pa, pb) if ((a + b) % 2 == 0) == a_first else 1 - tiebreak(pb, pa)
        a_serves = ((a + b) % 2 == 0) == a_first
        w = ga if a_serves else 1 - gb
        return w * s(a + 1, b) + (1 - w) * s(a, b + 1)
    return s(0, 0)


def match_prob(pa: float, pb: float, best_of: int) -> float:
    # who serves first in a set alternates in practice; average over both starts (a close approximation)
    ps = 0.5 * (set_prob(pa, pb, True) + set_prob(pa, pb, False))
    need = best_of // 2 + 1

    @lru_cache(maxsize=None)
    def m(a: int, b: int) -> float:
        if a == need:
            return 1.0
        if b == need:
            return 0.0
        return ps * m(a + 1, b) + (1 - ps) * m(a, b + 1)
    return m(0, 0)


def main() -> None:
    out = {}
    for bo in (3, 5):
        p0, h = 0.64, 0.001
        up, dn = match_prob(p0 + h, p0, bo), match_prob(p0 - h, p0, bo)
        dP = (up - dn) / (2 * h)
        out[f"best_of_{bo}"] = {"dP_dp": dP, "dlogit_per_pp_spw": 4 * dP / 100}
    gate = json.loads((OUT / "modeller_gate_ks_first_atp.json").read_text(encoding="utf-8"))["results"]
    feats = json.loads((OUT / "modeller_features_ks_first.json").read_text(encoding="utf-8"))
    sd_diff = {}
    for r in feats["coverage"]:
        if r["tour"] == "atp" and 2022 <= r["season"] <= 2023:
            sd_diff.setdefault("spd_f", []).append(r["sd_spd_f"])
    sdd = float(np.mean(sd_diff["spd_f"]))
    k3 = out["best_of_3"]["dlogit_per_pp_spw"]
    res = {}
    for subset in ("all", "timed_within_28d"):
        g = gate[f"spw|{subset}"]["f_hat|controls"]
        pp_per_kmh = g["pp_per_sd"] / g["feature_sd"]
        lo, hi = g["ci"][0] / g["feature_sd"], g["ci"][1] / g["feature_sd"]
        b_kmh = k3 * pp_per_kmh
        res[subset] = {"spw_pp_per_kmh": pp_per_kmh, "spw_pp_per_kmh_ci": [lo, hi],
                       "logodds_per_kmh_of_diff": b_kmh, "logodds_per_kmh_ci": [k3 * lo, k3 * hi],
                       "beta_per_sd_of_spd_f": b_kmh * sdd,
                       "mll_gain_per_match_at_beta": 1000 * 0.5 * (b_kmh * sdd) ** 2 * 0.19}
    out["sd_spd_f_men_2022_23"] = sdd
    out["serve_channel"] = res
    out["published_beta_0.09_mll_per_covered_match"] = 1000 * 0.5 * 0.09 ** 2 * 0.19
    (OUT / "modeller_power.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
