"""Result-free proxy columns for the master-list candidates, built from the player panel (seasons <= 2021).

Each builder returns an array aligned with the panel rows. Diff columns change sign when A and B swap; a few builders
return a context (symmetric) column, marked in KIND. Construction constants are declared here, fixed without results.
The price z = in_odds_logit stands in for the screen's offset eta in price-modulation columns (the screen uses eta).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import expit

from src.eda.feature_interactions.round1.math_audit.common_audit import lg, mu_rows, num, pair
from src.eda.feature_interactions.round0.mathematics import markov_composition as MC


def _ios(P, k, s):
    return pair(P, f"ios_{k}_{s}")


def _cell_centre(P, v):
    key = P["tour"].astype(str) + "|" + P["in_surface"].astype(str)
    return v - pd.Series(v).groupby(key.to_numpy()).transform("mean").to_numpy()


def build(P: pd.DataFrame, means: dict) -> tuple[dict, dict, dict]:
    z = num(P, "in_odds_logit")
    bo = num(P, "in_best_of")
    tour = P["tour"].astype(str).to_numpy()
    men = tour == "atp"
    C, KIND, AUX = {}, {}, {}
    # --- family 01: serve dominance (spw surface IOS) ---
    mu = mu_rows(P, "spw", means)
    Oa, Ob = _ios(P, "srfO", "spw")
    Da, Db = _ios(P, "srfD", "spw")
    xa, xb = mu + Oa - Db, mu + Ob - Da
    ok = np.isfinite(xa) & np.isfinite(xb) & np.isin(bo, [3, 5])
    kappa, comp = np.full(len(P), np.nan), np.full(len(P), np.nan)
    for b in (3, 5):
        s = ok & (bo == b)
        kappa[s] = MC.lev_logit((xa[s] + xb[s]) / 2, b) / MC.lev_logit(mu[s], b) - 1
        pa, pb = expit(xa[s]), expit(xb[s])
        m0, g = expit(mu[s]), pa - pb
        comp[s] = MC.L(pa, pb, b) - MC.L(m0 + g / 2, m0 - g / 2, b)
    kappa_c = _cell_centre(P, kappa)
    C["I-001 z*kappa"] = z * kappa_c
    C["I-002 comp"] = comp
    C["I-003 m_pair"], KIND["I-003 m_pair"] = (xa + xb) / 2 - mu, "context"
    AUX["kappa"] = kappa_c
    # --- I-006: Bo5 leverage column from Stage 3's serve-point probabilities ---
    psa, psb = pair(P, "s3_p_serve")
    u, v = np.full(len(P), np.nan), np.full(len(P), np.nan)
    ok6 = np.isfinite(psa) & np.isfinite(psb) & np.isin(bo, [3, 5])
    for b in (3, 5):
        s = ok6 & (bo == b)
        u[s] = MC.L(psa[s], psb[s], b)
        v[s] = MC.L(psa[s], psb[s], 3)
    C["I-006 L"] = np.where(bo == 5, u - v, 0.0)
    C["I-006 bo5*z"] = np.where(bo == 5, z, 0.0)
    AUX["u"], AUX["v"] = u, v
    # --- I-008: the surface-IOS profile composed through the iid model ---
    x = {}
    for s_ in ("first_in", "first_won", "second_won"):
        m_ = mu_rows(P, s_, means)
        oa, ob = _ios(P, "srfO", s_)
        da, db = _ios(P, "srfD", s_)
        x[s_] = (m_ + oa - db, m_ + ob - da)

    def cp(i):
        fi = expit(x["first_in"][i])
        return fi * expit(x["first_won"][i]) + (1 - fi) * expit(x["second_won"][i])
    pab, pba = cp(0), cp(1)
    zc1 = np.full(len(P), np.nan)
    okc = np.isfinite(pab) & np.isfinite(pba) & np.isin(bo, [3, 5])
    for b in (3, 5):
        s = okc & (bo == b)
        zc1[s] = MC.L(pab[s], pba[s], b)
    C["I-008 z_C1"] = zc1
    # I-015: second-serve exposure E_2 (A's second-serve points lost per serve point minus B's)
    fiab, fiba = expit(x["first_in"][0]), expit(x["first_in"][1])
    swab, swba = expit(x["second_won"][0]), expit(x["second_won"][1])
    C["I-015 E2"] = (1 - fiab) * (1 - swab) - (1 - fiba) * (1 - swba)
    # I-014: exposure x the returner's second-serve specialisation (MEC-06), cell averages from Stage 3's means
    fib, fwb, swb = (expit(mu_rows(P, s_, means)) for s_ in ("first_in", "first_won", "second_won"))
    w1, w2 = fwb * (1 - fwb), swb * (1 - swb)
    Dfwa, Dfwb = _ios(P, "srfD", "first_won")
    Dswa, Dswb = _ios(P, "srfD", "second_won")
    ca, cb = w2 * Dswa - w1 * Dfwa, w2 * Dswb - w1 * Dfwb
    pbar = fib * fwb + (1 - fib) * swb
    C["I-014 x"] = ((fib - fiba) * ca - (fib - fiab) * cb) / (pbar * (1 - pbar))
    # I-016: second-serve risk index x the opponent's second-serve return
    Odfa, Odfb = _ios(P, "srfO", "df")
    Oswa, Oswb = _ios(P, "srfO", "second_won")

    def zc(v_):
        return _cell_centre(P, v_) / np.nanstd(v_)
    rho_a, rho_b = zc(Odfa) + zc(Oswa), zc(Odfb) + zc(Oswb)
    C["I-016 x"] = rho_a * Dswb - rho_b * Dswa
    # I-012: free-point shield (MEC-04), aces as the free points
    mua = mu_rows(P, "ace", means)
    Oaa, Oab = _ios(P, "srfO", "ace")
    Daa, Dab = _ios(P, "srfD", "ace")
    abar, pspw = expit(mua), expit(mu)
    rbar = (pspw - abar) / (1 - abar)
    kk = pspw * (1 - pspw) / ((1 - abar) * rbar * (1 - rbar))

    def corr_term(Os_ace, Os_spw, Dr_ace, Dr_spw):
        a0, p0 = expit(mua + Os_ace), expit(mu + Os_spw)
        r0 = np.clip((p0 - a0) / (1 - a0), 1e-4, 1 - 1e-4)
        a = expit(mua + Os_ace - Dr_ace)
        r = expit(lg(r0) - kk * Dr_spw)
        return lg(a + (1 - a) * r) - lg(expit(mu + Os_spw - Dr_spw))
    C["I-012 shield"] = corr_term(Oaa, Oa, Dab, Db) - corr_term(Oab, Ob, Daa, Da)
    # I-013: probability-scale edges (curvature) for ace, df, hold, first_won
    for s_ in ("ace", "df", "hold", "first_won"):
        m_ = mu_rows(P, s_, means)
        oa, ob = _ios(P, "srfO", s_)
        da, db = _ios(P, "srfD", s_)
        C[f"I-013 e_{s_}"] = expit(m_ + oa - db) - expit(m_ + ob - da)
    return C, KIND, AUX


def build2(P: pd.DataFrame, means: dict, AUX: dict) -> tuple[dict, dict]:
    """Families 04-16: physique, reliability, price-state, switching, load, age, rank and attention proxies."""
    z = num(P, "in_odds_logit")
    tour = P["tour"].astype(str).to_numpy()
    C, KIND = {}, {}
    ha, hb = pair(P, "height")
    agea, ageb = pair(P, "age")
    ra, rb = pair(P, "rank")
    sa, sb = pair(P, "sets_14d")
    na, nb = pair(P, "surf_season_n")
    la, lb = pair(P, "surf_days_since")
    Ra, Rb = pair(P, "elo_R")
    NSa, NSb = pair(P, "elo_NS")
    hbar = np.nanmean(np.r_[ha, hb])
    Oswa, Oswb = pair(P, "ios_srfO_second_won")
    # I-022 kick second serve x a short returner (heights centred on the panel mean)
    C["I-022 x"] = Oswa * (hbar - hb) - Oswb * (hbar - ha)
    # I-023 height prior for thin histories: beta_h from established players, seasons <= 2018 (no outcomes)
    Oace_a, Oace_b = pair(P, "ios_srfO_ace")
    spa, spb = pair(P, "s3_serve_pts")
    est = (num(P, "season") <= 2018)
    hh = np.r_[ha[est], hb[est]]
    oo = np.r_[Oace_a[est], Oace_b[est]]
    nn = np.r_[spa[est], spb[est]]
    m = np.isfinite(hh) & np.isfinite(oo) & (nn >= 5000)
    beta_h = float(np.polyfit(hh[m] - hbar, oo[m], 1)[0])
    Kh = 1000.0
    wa_, wb_ = Kh / (spa + Kh), Kh / (spb + Kh)
    C["I-023 x"] = wa_ * (beta_h * (ha - hbar) - Oace_a) - wb_ * (beta_h * (hb - hbar) - Oace_b)
    # I-024 height x age hinge, height x load (sets_14d stands in for Fat)
    C["I-024 h_age"] = (ha - hbar) * np.clip(agea - 28, 0, None) - (hb - hbar) * np.clip(ageb - 28, 0, None)
    C["I-024 h_load"] = (ha - hbar) * sa - (hb - hbar) * sb
    # I-032 evidence weight: harmonic mean of n/(n + K) over surface matches rated (K = 20 matches)
    K = 20.0
    r_a, r_b = NSa / (NSa + K), NSb / (NSb + K)
    rbar = 2 * r_a * r_b / (r_a + r_b)
    KIND["I-032 rbar"] = "context"
    C["I-032 rbar"] = rbar
    dT = (pair(P, "ios_srfO_spw")[0] + pair(P, "ios_srfD_spw")[0]) - (pair(P, "ios_srfO_spw")[1] + pair(P, "ios_srfD_spw")[1])
    C["I-032 dIOS*rbar"] = dT * (rbar - np.nanmean(rbar))
    # I-034 conflict: Delta1 = points view - results view, each scaled to the price's SD within tour (no outcomes)
    rat = num(P, "in_ratings_iid")
    elo = num(P, "in_elo_overall") + num(P, "in_elo_surf_offset")
    d1 = np.full(len(P), np.nan)
    for t in ("atp", "wta"):
        s = tour == t
        d1[s] = rat[s] * np.nanstd(z[s]) / np.nanstd(rat[s]) - elo[s] * np.nanstd(z[s]) / np.nanstd(elo[s])
    AUX["d1"] = d1
    C["I-034 z*|d1|"] = z * (np.abs(d1) - np.nanmean(np.abs(d1)))
    # I-035 margin-aware de-vig (additive = Shin for two outcomes)
    qa, qb = 1 / num(P, "avg_a"), 1 / num(P, "avg_b")
    Q = qa + qb
    pi = qa / Q
    pS = np.clip(pi + (Q - 1) * (pi - 0.5), 0.005, 0.995)
    C["I-035 shin_gap"] = lg(pS) - lg(pi)
    AUX["Q"] = Q
    # I-036 obscurity: the lower-ranked player's log rank minus the tour median (unranked -> 1500)
    lra, lrb = np.log(np.where(np.isfinite(ra), ra, 1500)), np.log(np.where(np.isfinite(rb), rb, 1500))
    O = np.maximum(lra, lrb)
    for t in ("atp", "wta"):
        s = tour == t
        O[s] = O[s] - np.median(O[s])
    C["I-036 z*O"] = z * O
    # I-037 arbitrage margin, I-038 best-price skew
    ma, mb = num(P, "max_a"), num(P, "max_b")
    a = 1 - (1 / ma + 1 / mb)
    AUX["arb"] = a
    C["I-037 z*a"] = z * (a - np.nanmean(a))
    pmax = (1 / ma) / (1 / ma + 1 / mb)
    C["I-038 k"] = lg(pmax) - lg(pi)
    # I-046 early season x return-heavy shape; I-047 graded switch state x style and x age
    Oa, Ob = pair(P, "ios_srfO_spw")
    Da, Db = pair(P, "ios_srfD_spw")
    key = P["tour"].astype(str) + "|" + P["in_surface"].astype(str)

    def cc(v):
        return v - pd.Series(v).groupby(key.to_numpy()).transform("mean").to_numpy()
    sha, shb = cc(Da) - cc(Oa), cc(Db) - cc(Ob)            # return-heaviness
    qa_, qb_ = (na < 3).astype(float), (nb < 3).astype(float)
    C["I-046 x"] = qa_ * sha - qb_ * shb
    nu = 2.0
    newa, newb = np.exp(-na / nu) * np.log1p(la / 30), np.exp(-nb / nu) * np.log1p(lb / 30)
    C["I-047 sty"] = newa * (-sha) - newb * (-shb)
    C["I-047 age"] = newa * (agea - 28) - newb * (ageb - 28)
    # I-048 staleness-weighted surface deviation (spw offence and defence): w = n/(n+10) * exp(-layoff/180)
    wa, wb = NSa / (NSa + 10) * np.exp(-la / 180), NSb / (NSb + 10) * np.exp(-lb / 180)
    Ea, Eb = pair(P, "ios_srfE_spw")
    Fa, Fb = pair(P, "ios_srfF_spw")
    C["I-048 E"] = (1 - wa) * Ea - (1 - wb) * Eb
    C["I-048 F"] = (1 - wa) * Fa - (1 - wb) * Fb
    C["I-048 plain dE (R2 placebo)"] = Ea - Eb
    # I-049 early season x price
    E = (np.minimum(na, nb) < 3).astype(float)
    AUX["early"] = E
    C["I-049 z*E"] = z * (E - E.mean())
    # I-053 age x load (sets_14d for Fat); I-054 both tired x price; I-055 favourite's fatigue asymmetry
    C["I-053 x"] = sa * np.clip(agea - 26, 0, None) - sb * np.clip(ageb - 26, 0, None)
    S = sa + sb
    C["I-054 z*S"] = z * (S - np.nanmean(S))
    C["I-055 x"] = np.sign(z) * np.abs(sa - sb)
    # I-068 age x return-heavy shape; I-070 age-weighted short-minus-long
    C["I-068 x"] = (agea - 28) * sha - (ageb - 28) * shb
    tpa, tpb = pair(P, "adjperf_tpw_2w")
    La, Lb = Oa + Da, Ob + Db
    sd_s, sd_l = np.nanstd(np.r_[tpa, tpb]), np.nanstd(np.r_[La, Lb])
    h = lambda ag: np.clip(25 - ag, 0, None) - 0.5 * np.clip(ag - 30, 0, None)   # noqa: E731
    C["I-070 x"] = (tpa / sd_s - La / sd_l) * h(agea) - (tpb / sd_s - Lb / sd_l) * h(ageb)
    # I-071 rank anchoring: g = e_hat(log rank) - Elo (fit per tour, seasons <= 2018, no outcomes), x = d(g * a)
    ga, gb = np.full(len(P), np.nan), np.full(len(P), np.nan)
    for t in ("atp", "wta"):
        s = tour == t
        x_ = np.r_[lra[s & est], lrb[s & est]]
        y_ = np.r_[Ra[s & est], Rb[s & est]]
        ok = np.isfinite(x_) & np.isfinite(y_)
        c1, c0 = np.polyfit(x_[ok], y_[ok], 1)
        ga[s], gb[s] = (c0 + c1 * lra[s]) - Ra[s], (c0 + c1 * lrb[s]) - Rb[s]
    C["I-071 x"] = ga * (agea - 27) / 5 - gb * (ageb - 27) / 5
    C["I-071 dg"] = ga - gb
    # I-080 attention x Delta1: A = mean of standardised level score, round depth, star power
    lvl = num(P, "in_level")
    lvl_score = np.select([lvl <= 1, lvl == 2, lvl == 3], [3.0, 2.0, 1.0], 0.0)
    rnd = num(P, "in_round")
    star = -np.minimum(lra, lrb)
    std = lambda v: (v - np.nanmean(v)) / np.nanstd(v)   # noqa: E731
    A = (std(lvl_score) + std(rnd) + std(star)) / 3
    C["I-080 d1*(-A)"] = d1 * (-A)
    # I-084 prominence: the pair's overall Elo sum x price
    T = Ra + Rb
    C["I-084 z*T"] = z * (T - np.nanmean(T)) / np.nanstd(T)
    return C, KIND
