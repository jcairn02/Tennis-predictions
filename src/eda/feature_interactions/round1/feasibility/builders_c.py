"""Primary columns of families 11-16 (I-051 ... I-091) for G2's result-free checks (see builders_a)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions.round1.feasibility import base as B
from src.eda.feature_interactions.round1.feasibility.builders_a import cellmean, io, price
from src.eda.feature_interactions.round1.feasibility.builders_b import ab, delta1, fame, sty


def fat(P, s, unit="min"):
    """Recovery debt: 3-day kernel of minutes (missing unless the player's last 14 days have every minute) or games."""
    f = P[f"fat_{unit}_3_{s}"].astype(float).to_numpy()
    if unit == "min":
        f = np.where(np.isfinite(P[f"min_14d_{s}"].astype(float).to_numpy()), f, np.nan)
    return f


def age(P, s):
    return P[f"age_{s}"].astype(float).to_numpy()


def I051(P):
    oa, ob = ab(P, "onsite_n")
    return {"on_site": (np.log1p(oa) - np.log1p(ob), "diff")}


def I052(P):
    return {"fat_min": (fat(P, "a") - fat(P, "b"), "diff"), "fat_games": (fat(P, "a", "games") - fat(P, "b", "games"), "diff")}


def I053(P):
    return {"fat_x_age26": (fat(P, "a") * np.maximum(age(P, "a") - 26, 0) - fat(P, "b") * np.maximum(age(P, "b") - 26, 0),
                            "diff")}


def I054(P):
    s = fat(P, "a") + fat(P, "b")
    return {"z_x_sumfat": (price(P) * (s - cellmean(P, s)), "diff")}


def I055(P):
    return {"sign_z_absdfat": (np.sign(price(P)) * np.abs(fat(P, "a") - fat(P, "b")), "diff")}


def I056(P):
    def part(s):
        scare = P[f"prev_deciding_{s}"].astype(float).to_numpy() * P[f"prev_same_event_{s}"].astype(float).to_numpy()
        rest = P[f"rest_min_{s}"].astype(float).to_numpy()
        return scare * ((rest <= 1).astype(float) - (rest >= 2).astype(float))
    return {"scare_rest": (part("a") - part("b"), "diff")}


def I057(P, c=60.0):
    def R(s):
        l7, l28 = P[f"min_7d_{s}"].astype(float).to_numpy(), P[f"min_28d_{s}"].astype(float).to_numpy()
        return np.log((l7 + c) / (l28 / 4 + c))
    return {"acwr": (R("a") - R("b"), "diff")}


def I061(P):
    month = pd.to_datetime(P["tournament_date"]).dt.month.to_numpy()
    d = P["odo_season_a"] * np.maximum(age(P, "a") - 27, 0) - P["odo_season_b"] * np.maximum(age(P, "b") - 27, 0)
    return {"odo_x_age_late": ((month >= 9) * d.to_numpy(float), "diff")}


def I062(P):
    ta, tb = ab(P, "team_load")
    return {"team_load": (ta - tb, "diff")}


def I063(P, kappa=0.01, eta=0.5):
    pa, pb = P["s3_p_serve_a"].to_numpy(float), P["s3_p_serve_b"].to_numpy(float)
    da, db = kappa * fat(P, "a", "games"), kappa * fat(P, "b", "games")
    bo = P["best_of"].to_numpy(float)
    d = B.lg(B.iid_match(pa - da + eta * db, pb - db + eta * da, bo)) - B.lg(B.iid_match(pa, pb, bo))
    return {"fatigue_composed": (d, "diff")}


def I064(P):
    return {"fat_x_sty": (fat(P, "a") * sty(P, "a") - fat(P, "b") * sty(P, "b"), "diff")}


def I065(P):
    ra, rb = ab(P, "spp_mean")
    return {"pace_x_oppfat": (ra * fat(P, "b") - rb * fat(P, "a"), "diff")}


def I066(P):
    ra, rb = ab(P, "spp_mean")
    q = 1 / (1 + np.exp(-price(P)))
    e_min = (1 - (2 * q - 1) ** 2) * (ra + rb) / 2
    return {"emin_x_dsets": (e_min * (P["in_sets_14d"].to_numpy(float)), "diff"),
            "emin_x_dage": (e_min * P["in_age"].to_numpy(float), "diff")}


def I068(P):
    from src.eda.feature_interactions.round1.feasibility.builders_b import shape
    return {"age_x_shape": ((age(P, "a") - 28) * shape(P, "a") - (age(P, "b") - 28) * shape(P, "b"), "diff")}


def I069(P):
    def drift(s):
        ret_share = 1 / (1 + np.exp(-(P[f"s3_return_{s}"].astype(float) - P[f"s3_serve_{s}"].astype(float)).to_numpy()))
        return np.maximum(age(P, s) - 29, 0) * (ret_share - 0.5)
    return {"style_age_drift": (drift("a") - drift("b"), "diff")}


def I070(P):
    def mix(s):
        h = np.maximum(25 - age(P, s), 0) - 0.5 * np.maximum(age(P, s) - 30, 0)
        return (P[f"adjperf_tpw_2w_{s}"].astype(float) - P[f"ztpw_mean52_{s}"].astype(float)).to_numpy() * h
    return {"age_trust_form": (mix("a") - mix("b"), "diff")}


def I071(P):
    m = P["season"].between(2014, 2016).to_numpy()
    lr = np.log(np.concatenate([P["rank_a"].astype(float), P["rank_b"].astype(float)]))
    R = np.concatenate([P["elo_R_a"].astype(float), P["elo_R_b"].astype(float)])
    tour = np.concatenate([P["tour"], P["tour"]])
    g = np.full(len(lr), np.nan)
    for t in ("atp", "wta"):                       # rank -> Elo line, fitted on 2014-2016 rows (no outcome)
        k = np.tile(m, 2) & (tour == t) & np.isfinite(lr) & np.isfinite(R)
        c = np.polyfit(lr[k], R[k], 1)
        g = np.where(tour == t, np.polyval(c, lr) - R, g)
    n = len(P)
    a = (np.concatenate([age(P, "a"), age(P, "b")]) - 27) / 5
    ga = g * a
    return {"rank_vs_elo_x_age": (ga[:n] - ga[n:], "diff")}


def I076(P):
    oa, ob = ab(P, "onsite_n")
    def cold(s, o):
        prev_other = (P[f"prev_same_surface_{s}"].astype(float).to_numpy() == 0) | (P[f"rest_min_{s}"].astype(float).to_numpy() > 10)
        return (o == 0) * prev_other.astype(float)
    return {"rhythm_vs_cold": (oa * cold("b", ob) - ob * cold("a", oa), "diff")}


def I078(P):
    g = (P["level"] != "GS").to_numpy(float)
    return {"home_x_notslam": ((P["home_a"].astype(float) - P["home_b"].astype(float)).to_numpy() * g, "diff")}


def I079(P):
    wca, wcb = (P["entry_a"] == "WC").to_numpy(float), (P["entry_b"] == "WC").to_numpy(float)
    return {"home_x_wc": ((P["home_a"].astype(float).to_numpy() * wca) - (P["home_b"].astype(float).to_numpy() * wcb), "diff")}


def I080(P):
    rk = -np.log(np.fmin(P["rank_a"].astype(float), P["rank_b"].astype(float)).to_numpy())
    lvl = P["in_level"].to_numpy(float)
    rnd = P["in_round"].to_numpy(float)
    def zs(x):
        m = P["season"].between(*B.DISC).to_numpy()
        return (x - np.nanmean(x[m])) / np.nanstd(x[m])
    A = (zs(-lvl) + zs(rnd) + zs(rk)) / 3
    return {"d1_x_negA": (delta1(P) * (-A), "diff")}


def I081(P):
    q = 1 / (1 + np.exp(-price(P)))
    return {"d1_x_lopsided": (delta1(P) * (1 - 4 * q * (1 - q)), "diff")}


def I083(P):
    def fr(s):
        fall = P[f"elo_peak_{s}"].astype(float).to_numpy() - P[f"elo_R_{s}"].astype(float).to_numpy()
        return fame(P, s) * fall
    return {"fame_x_fall": (fr("a") - fr("b"), "diff")}


def I059(P, tau=3.0):
    def run(s):
        w = P[f"prev_event_wins_{s}"].astype(float).to_numpy()
        first = P[f"onsite_n_{s}"].astype(float).to_numpy() == 0
        return np.where(first, w * np.exp(-np.maximum(P[f"rest_min_{s}"].astype(float).to_numpy(), 0) / tau), 0.0)
    return {"deep_run_gap_notravel": (run("a") - run("b"), "diff")}


def I086(P):
    def surprise(s):
        p = P[f"prev_p_own_{s}"].astype(float).to_numpy()
        won = P[f"prev_won_{s}"].astype(float).to_numpy()
        return np.where(won > 0.5, 1 - p, np.nan)
    late = (P["in_round"].to_numpy(float) >= 15).astype(float)
    return {"d_surprise_x_late": ((surprise("a") - surprise("b")) * late, "diff")}


def I089(P):
    top_a, top_b = (P["rank_a"].astype(float) <= 20).to_numpy(float), (P["rank_b"].astype(float) <= 20).to_numpy(float)
    pre = (P["next_slam_days"].to_numpy(float) <= 14) & (P["level"] != "GS").to_numpy()
    return {"top_x_pre_x_late": ((top_a - top_b) * pre * (P["in_round"].to_numpy(float) >= 15), "diff")}


def I084(P):
    T = io(P, "srfO", "spw", "a") + io(P, "srfD", "spw", "a") + io(P, "srfO", "spw", "b") + io(P, "srfD", "spw", "b")
    return {"z_x_SigmaT": (price(P) * (T - cellmean(P, T)), "diff")}


def I087(P):
    w = np.fmin(P["rest_min_a"].astype(float), P["rest_min_b"].astype(float)).to_numpy()
    return {"d1_x_short_window": (delta1(P) * (w <= 1), "diff")}


def I088(P):
    def tau(s):
        title = (P[f"prev_event_title_{s}"].astype(float).to_numpy() > 0.5) & (P[f"onsite_n_{s}"].astype(float).to_numpy() == 0) \
            & (P[f"rest_min_{s}"].astype(float).to_numpy() <= 9)
        return title.astype(float)
    return {"title_x_first": (tau("a") - tau("b"), "diff")}


def I090(P):
    top_a, top_b = (P["rank_a"].astype(float) <= 20).to_numpy(float), (P["rank_b"].astype(float) <= 20).to_numpy(float)
    small = P["level"].isin(["T250", "T500"]).to_numpy() & (P["next_slam_days"].to_numpy(float) <= 8)
    return {"elite_pre_slam": (small * (top_a - top_b), "diff")}


def I091(P):
    n = P["h2h_n_a"].astype(float).to_numpy()
    raw = (P["h2h_w_a"].astype(float).to_numpy() - P["h2h_w_b"].astype(float).to_numpy()) / (n + 1)
    return {"h2h_raw_n3": (raw * (n >= 3), "diff")}


BUILDERS = {"I-051": I051, "I-052": I052, "I-053": I053, "I-054": I054, "I-055": I055, "I-056": I056, "I-057": I057,
            "I-061": I061, "I-062": I062, "I-063": I063, "I-064": I064, "I-065": I065, "I-066": I066, "I-068": I068,
            "I-069": I069, "I-070": I070, "I-071": I071, "I-076": I076, "I-078": I078, "I-079": I079, "I-080": I080,
            "I-081": I081, "I-083": I083, "I-084": I084, "I-087": I087, "I-088": I088, "I-090": I090, "I-091": I091,
            "I-059": I059, "I-086": I086, "I-089": I089}
