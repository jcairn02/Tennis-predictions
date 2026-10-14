"""B-REPUTE, the price anchors on reputation that lags the state (math audit block; composite, weight 1; slow trait).

    I-071 (-) rank anchoring x career trajectory: Delta(g a), g = e_hat(log rank) - Elo (ranked better than rated), the
              line e_hat fitted per tour by least squares of overall Elo on log rank over the 2013-2018 panel rows (both
              players; no outcome), a = (age - 27)/5; an unranked player takes Stage 1's rank (one below the worst seen on
              the tour in earlier seasons) and an indicator
    I-083 (-) fallen-star premium: Delta(F R), F = log(1 + titles + Slam QF-or-better events, strictly earlier, since
              2010), R = career-peak overall Elo to date - current Elo (>= 0; the peak over the player's own rows since
              2010, every level, the current pre-match rating included)
    I-055 (-) the favourite's hidden fatigue: sign(eta) |Delta Fat| (the round-2 family: the base's favourite; Fat is
              I-052's kernel from the body analyst's f20_fatigue, one Fat in the family)

Round-2 family: signed sum, sign -, weight 1, slow. Each member is divided by its RMS on the 2014-2021 rows and the
three are summed as they are (all declared -, so the block is tested one-sided negative). I-055 depends on the base's
eta, so the block is returned as x_of_eta (the batch evaluates it per base); x is its eta_model version. Controls (per
member): Delta g, Delta Elo (elo_overall), Delta age, the unranked indicator A - B, Delta F, Delta R, Delta Fat and its
imputed-share difference, Std; eta-modulator controls Sigma g, Sigma a, Sigma F, Sigma R, |Delta Fat| (so the step,
not a slope change, is tested for I-055) and LIT-2 (fitted jointly: sign(eta_model) dF x eta is LIT-2's |eta| dF at the
model base); the M-set (I-055's). TabPFN: I-071's and I-083's difference columns.

LIT-2 (+, weight 0.5, slow; rulings, new): |eta| dF, the fame asymmetry deepening with the lopsidedness (Abinzano; van
Rheenen), x_of_eta; controls dF, the M-set, Std and B-REPUTE's x (its eta_model version: fitted jointly, opposite sign
to I-083, corr about 0.50).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import mkt_common as M


def prepare_repute(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    rka, rkb, ua, ub = M.ranks(P, H)
    out = {"rkf_a": rka, "rkf_b": rkb, "unr_a": ua, "unr_b": ub}
    out["fame_a"], out["fame_b"] = M.at_model(H, P, M.fame(H))
    e = M.elo_rows(H)
    peak = pd.Series(e).groupby(H["pc"].to_numpy()).cummax().to_numpy()
    out["peak_a"], out["peak_b"] = M.at_model(H, P, peak)
    out.update(M.body_fat(P, L))                       # I-052's Fat from f20_fatigue: one Fat in the family
    return out


def rank_gap(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """g = e_hat(log rank) - Elo for A and B; e_hat per tour from the 2013-2018 rows, ranked players only."""
    lra, lrb = np.log(M.num(P, "rkf_a")), np.log(M.num(P, "rkf_b"))
    ea, eb = M.pair(P, "elo_R")
    ua, ub = M.pair(P, "unr")
    t, m0 = M.tours(P), M.tune(P)
    ga, gb = np.full(len(P), np.nan), np.full(len(P), np.nan)
    for tr in C.TOURS:
        m = t == tr
        x = np.r_[lra[m & m0 & (ua == 0)], lrb[m & m0 & (ub == 0)]]
        y = np.r_[ea[m & m0 & (ua == 0)], eb[m & m0 & (ub == 0)]]
        ok = np.isfinite(x) & np.isfinite(y)
        c1, c0 = np.polyfit(x[ok], y[ok], 1)
        ga[m], gb[m] = c0 + c1 * lra[m] - ea[m], c0 + c1 * lrb[m] - eb[m]
    return ga, gb


def ages(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    out = []
    for s in ("a", "b"):
        v = M.num(P, f"age_pl_{s}")
        out.append(np.where(np.isfinite(v), v, M.num(P, f"age_{s}")))
    return out[0], out[1]


def repute_parts(P: pd.DataFrame) -> dict:
    ga, gb = rank_gap(P)
    aa, ab = ages(P)
    sa, sb = (aa - 27.0) / 5.0, (ab - 27.0) / 5.0
    Fa, Fb = M.pair(P, "fame")
    ea, eb = M.pair(P, "elo_R")
    Ra, Rb = np.maximum(M.num(P, "peak_a") - ea, 0.0), np.maximum(M.num(P, "peak_b") - eb, 0.0)
    fa, fb = M.pair(P, "bd_fat")
    return {"m71": ga * sa - gb * sb, "m83": Fa * Ra - Fb * Rb, "adfat": np.abs(fa - fb), "ga": ga, "gb": gb,
            "sa": sa, "sb": sb, "Fa": Fa, "Fb": Fb, "Ra": Ra, "Rb": Rb, "fa": fa, "fb": fb}


def brepute_x_of_eta(P: pd.DataFrame):
    q, d = repute_parts(P), M.disc(P)

    def x_of_eta(e, rows):
        """The block for a base's eta (I-055's sign(eta)); members summed as they are (family sign -)."""
        m55 = np.sign(np.asarray(e, float)) * q["adfat"][rows]
        return M.signed_sum_masked([(q["m71"][rows], "+"), (q["m83"][rows], "+"), (m55, "+")], d[rows], symmetric=False)
    return x_of_eta, q


def lit2_mod(P: pd.DataFrame) -> np.ndarray:
    """LIT-2's column |eta| dF written as an eta-modulator, s = sign(eta_model) dF (symmetric): exact at the model base."""
    return np.sign(M.eta(P)) * (M.num(P, "fame_a") - M.num(P, "fame_b"))


def combine_brepute(P: pd.DataFrame) -> dict:
    x_of_eta, q = brepute_x_of_eta(P)
    allr = np.arange(len(P))
    x = x_of_eta(M.eta(P), allr)
    ia, ib = M.pair(P, "bd_fatimp")
    Cs, names = M.std_controls(P, x, force=("elo_overall", "age"))
    ctrl, cn = M.stack([(q["ga"] - q["gb"], "Delta g"), (M.num(P, "unr_a") - M.num(P, "unr_b"), "unranked, A - B"),
                        (q["Fa"] - q["Fb"], "Delta F"), (q["Ra"] - q["Rb"], "Delta R"), (q["fa"] - q["fb"], "Delta Fat"),
                        (ia - ib, "Fat imputed share, A - B")] + ([(Cs, names)] if names else []))
    E, en = M.stack([(M.centre(q["ga"] + q["gb"], P), "Sigma g"), (M.centre(q["sa"] + q["sb"], P), "Sigma a"),
                     (M.centre(q["Fa"] + q["Fb"], P), "Sigma F"), (M.centre(q["Ra"] + q["Rb"], P), "Sigma R"),
                     (M.centre(q["adfat"], P), "|Delta Fat|"), (lit2_mod(P), "LIT-2 (joint)")])
    return {"x": x, "x_of_eta": x_of_eta, "x_market": x_of_eta(M.zmkt(P), allr), "m_set": True, "controls": ctrl,
            "control_names": cn, "eta_mod_controls": E, "eta_mod_names": en,
            "members": {"I-071": q["m71"], "I-083": q["m83"], "I-055": np.sign(M.eta(P)) * q["adfat"]},
            "tabpfn": {"rank_vs_elo_x_age": (q["m71"], "diff", None), "fame_x_fall": (q["m83"], "diff", None)}}


def combine_lit2(P: pd.DataFrame) -> dict:
    """LIT-2: |eta| dF (sign +), fitted jointly with B-REPUTE (its eta_model-version x as a control)."""
    dF = M.num(P, "fame_a") - M.num(P, "fame_b")

    def x_of_eta(e, rows):
        return np.abs(np.asarray(e, float)) * dF[rows]
    allr = np.arange(len(P))
    x = x_of_eta(M.eta(P), allr)
    xr, _ = brepute_x_of_eta(P)
    Cs, names = M.std_controls(P, x)
    ctrl, cn = M.stack([(dF, "Delta F"), (xr(M.eta(P), allr), "B-REPUTE (joint)")] + ([(Cs, names)] if names else []))
    return {"x": x, "x_of_eta": x_of_eta, "x_market": x_of_eta(M.zmkt(P), allr), "m_set": True, "controls": ctrl,
            "control_names": cn, "tabpfn": {}}


HYPOTHESES = [
    {"hid": "B-REPUTE", "master": "I-071+I-083+I-055", "kind": "W", "sign": "-", "weight": 1.0, "trait": "slow",
     "deployment": "TabPFN diff columns or nudge", "anchor": "I", "prepare": prepare_repute, "combine": combine_brepute},
    {"hid": "LIT-2", "master": "LIT-2", "kind": "M", "sign": "+", "weight": 0.5, "trait": "slow", "deployment": "nudge",
     "anchor": "I", "prepare": prepare_repute, "combine": combine_lit2},
]
