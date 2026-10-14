"""Primary columns of families 06-10 (I-028 ... I-050) for G2's result-free checks (see builders_a)."""
from __future__ import annotations

import numpy as np

from src.eda.feature_interactions.round1.feasibility import base as B
from src.eda.feature_interactions.round1.feasibility.builders_a import cellmean, io, price


def ab(P, c):
    return P[f"{c}_a"].astype(float).to_numpy(), P[f"{c}_b"].astype(float).to_numpy()


def I029(P):
    va, vb = ab(P, "ztpw_var52")
    v = va + vb
    return {"z_x_Vpair": (price(P) * (v / cellmean(P, v) - 1.0), "diff")}


def I030(P):
    va, vb = ab(P, "ztpw_var52")
    v = np.sqrt(np.maximum(va, 0)) ** 2 + np.sqrt(np.maximum(vb, 0)) ** 2
    return {"z_x_V": (price(P) * (v - cellmean(P, v)), "diff")}


def _form_star_gap(P, s, K=4.0):
    w = P[f"w_2w_{s}"].astype(float).to_numpy()
    r = w / (w + K)
    return (1 - r) * (P[f"ztpw_mean52_{s}"].astype(float).to_numpy() - P[f"adjperf_tpw_2w_{s}"].astype(float).to_numpy())


def I031(P):
    return {"d_reanchor": (_form_star_gap(P, "a") - _form_star_gap(P, "b"), "diff")}


def I032(P, K=20.0):
    ra, rb = ab(P, "elo_NS")
    ra, rb = ra / (ra + K), rb / (rb + K)
    rbar = 2 * ra * rb / np.maximum(ra + rb, 1e-9)
    net = (io(P, "srfO", "spw", "a") + io(P, "srfD", "spw", "a")) - (io(P, "srfO", "spw", "b") + io(P, "srfD", "spw", "b"))
    return {"net_x_rbar": (net * rbar, "diff")}


def I033(P):
    fa = P["ztpw_mean52_a"].astype(float) - P["adjperf_tpw_2w_a"].astype(float)
    fb = P["ztpw_mean52_b"].astype(float) - P["adjperf_tpw_2w_b"].astype(float)
    F = (fa ** 2 + fb ** 2).to_numpy()
    return {"z_x_flux": (price(P) * (F - cellmean(P, F)), "diff")}


def delta1(P):
    return P["in_ratings_iid"].to_numpy(float) - (P["in_elo_overall"].to_numpy(float) + P["in_elo_surf_offset"].to_numpy(float))


def I034(P):
    return {"z_x_absD1": (price(P) * np.abs(delta1(P)), "diff")}


def I035(P):
    a, b = 1.0 / P["avg_a"].astype(float).to_numpy(), 1.0 / P["avg_b"].astype(float).to_numpy()
    Q, pi = a + b, a / (a + b)
    pS = np.clip(pi + (Q - 1) * (pi - 0.5), 1e-4, 1 - 1e-4)
    return {"shin_gap": (B.lg(pS) - B.lg(pi), "diff")}


def I036(P):
    ra, rb = ab(P, "rank")
    big = np.nanmax(np.concatenate([ra, rb])) + 1
    O = np.maximum(np.log(np.where(np.isfinite(ra), ra, big)), np.log(np.where(np.isfinite(rb), rb, big)))
    return {"z_x_obscure": (price(P) * (O - cellmean(P, O, ("tour",))), "diff")}


def I037(P):
    a = 1.0 - (1.0 / P["max_a"].astype(float) + 1.0 / P["max_b"].astype(float)).to_numpy()
    return {"z_x_arb": (price(P) * a, "diff")}


def fame(P, s):
    return np.log1p(P[f"titles_before_{s}"].astype(float) + P[f"slam_qf_before_{s}"].astype(float)).to_numpy()


def I038(P):
    a, b = 1.0 / P["max_a"].astype(float).to_numpy(), 1.0 / P["max_b"].astype(float).to_numpy()
    k = B.lg(a / (a + b)) - price(P)
    fam = (np.sign(k) == -np.sign(fame(P, "a") - fame(P, "b"))).astype(float)
    return {"k_x_fam": (k * fam, "diff"), "k_x_notfam": (k * (1 - fam), "diff")}


def I039(P):
    return {"sharp_minus_avg": (B.lg(P["p_ps_a"].astype(float)) - price(P), "diff")}


def I040(P):
    adj = P["eta"].to_numpy(float) - price(P)
    ra, rb = ab(P, "elo_NS")
    c = np.log1p(np.minimum(ra, rb))
    return {"c_x_adj": (adj * (c - cellmean(P, c)), "diff")}


def I041(P):
    adj = P["eta"].to_numpy(float) - price(P)
    return {"adj_cubed": (adj ** 3, "diff")}


def I042(P):
    ha, hb = ab(P, "ret_rate_730")
    p = 1.0 / (1.0 + np.exp(-price(P)))
    return {"tau_hazard": (hb / p - ha / (1 - p), "diff")}


def rust(P, s, nu=3.0):
    U = np.log1p(np.maximum(P[f"layoff_days_{s}"].astype(float).to_numpy() - 28, 0) / 30.0)
    return np.nan_to_num(U * np.exp(-P[f"n_since_layoff_{s}"].astype(float).to_numpy() / nu))


def I043(P):
    return {"rust": (rust(P, "a") - rust(P, "b"), "diff")}


def I044(P):
    def inj(s):
        flag = (np.nan_to_num(P[f"layoff_injury_{s}"].astype(float).to_numpy()) > 0.5) \
            & (np.nan_to_num(P[f"layoff_days_{s}"].astype(float).to_numpy()) >= 56) \
            & (np.nan_to_num(P[f"n_since_layoff_{s}"].astype(float).to_numpy(), nan=99) <= 2)
        e = P[f"elo_R_{s}"].astype(float).to_numpy()
        return flag * (e - cellmean(P, 0.5 * (P["elo_R_a"] + P["elo_R_b"]).to_numpy(), ("tour",)))
    return {"inj_return": (inj("a") - inj("b"), "diff")}


def I045(P):
    oa, ob = ab(P, "onsite_n")
    return {"both_onsite": (((oa >= 1) & (ob >= 1)).astype(float), "context")}


def shape(P, s):
    d, o = io(P, "srfD", "spw", s), io(P, "srfO", "spw", s)
    return (d - cellmean(P, d)) - (o - cellmean(P, o))


def I046(P):
    qa, qb = [(P[f"surf_season_n_{s}"].astype(float).to_numpy() < 3).astype(float) for s in "ab"]
    return {"g_early": (qa * shape(P, "a") - qb * shape(P, "b"), "diff")}


def new_state(P, s, nu=3.0):
    return np.exp(-P[f"surf_season_n_{s}"].astype(float).to_numpy() / nu) \
        * np.log1p(np.minimum(np.nan_to_num(P[f"surf_days_since_{s}"].astype(float).to_numpy(), nan=1095), 1095) / 30.0)


def sty(P, s):
    return P[f"s3_serve_{s}"].astype(float).to_numpy() - P[f"s3_return_{s}"].astype(float).to_numpy()


def I047(P):
    return {"new_x_sty": (new_state(P, "a") * sty(P, "a") - new_state(P, "b") * sty(P, "b"), "diff"),
            "new_x_age": (new_state(P, "a") * (P["age_a"].astype(float) - 28).to_numpy()
                          - new_state(P, "b") * (P["age_b"].astype(float) - 28).to_numpy(), "diff")}


def I048(P, k=20.0, theta=180.0):
    def part(s):
        n = P[f"elo_NS_{s}"].astype(float).to_numpy()
        lay = np.nan_to_num(P[f"surf_days_since_{s}"].astype(float).to_numpy(), nan=1095)
        w = n / (n + k) * np.exp(-lay / theta)
        return (1 - w) * (io(P, "srfE", "spw", s) + io(P, "srfF", "spw", s))
    return {"stale_dev": (part("a") - part("b"), "diff")}


def I049(P):
    E = (np.minimum(P["surf_season_n_a"].astype(float), P["surf_season_n_b"].astype(float)) < 3).to_numpy(float)
    return {"z_x_early": (price(P) * E, "diff")}


def I050(P):
    def flip(s):
        now = P["indoor"].map({True: 1.0, False: 0.0}).astype(float).to_numpy()
        prev = P[f"prev_indoor_{s}"].astype(float).to_numpy()
        return (now != prev).astype(float) * np.where(np.isfinite(now) & np.isfinite(prev), 1.0, np.nan)
    return {"inout_x_sty": (flip("a") * sty(P, "a") - flip("b") * sty(P, "b"), "diff")}


BUILDERS = {"I-029": I029, "I-030": I030, "I-031": I031, "I-032": I032, "I-033": I033, "I-034": I034, "I-035": I035,
            "I-036": I036, "I-037": I037, "I-038": I038, "I-039": I039, "I-040": I040, "I-041": I041, "I-042": I042,
            "I-043": I043, "I-044": I044, "I-045": I045, "I-046": I046, "I-047": I047, "I-048": I048, "I-049": I049,
            "I-050": I050}
