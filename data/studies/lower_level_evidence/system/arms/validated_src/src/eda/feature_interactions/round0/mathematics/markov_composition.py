"""Feature interactions, round 0, the mathematics brainstormer: the exact mechanistic calculations behind the MAT- ideas
(docs/studies/feature_interactions/round0/ideas_mathematics.md).

Nothing here reads a match result, and no feature is related to results or prices. Discovery seasons only (<= 2021).
Feature tables are read for their own distributions (the spread of the pair's serve dominance, of posterior variances);
the closing odds of 2013-2021 are read once, for the shape of their own distribution, to turn a log-odds error into
milli-log-loss: a missing log-odds term tau costs about 1/2 E[p(1-p) tau^2] per match (second-order expansion of the log
loss at the truth).

    A  the iid point -> game -> set -> match model, written afresh and checked against
       src/eda/predictability_diagnostic/stage2_iid.py (read-only import) and the textbook hold value
    B  grids: dP/d(pA + pB) at fixed pA - pB; the leverage of the point-level difference by serve dominance and format;
       curvature in the difference; deciding-set rules; the hold scale; the share of sets reaching a tiebreak
    C  the pair's serve dominance hidden by the A - B representation (surface IOS, 2013-2021 training rows) and the
       leverage modulation it implies
    D  the per-statistic surface-IOS profile composed into serve-point probabilities: how far the A - B inputs are from it;
       the second-order (curvature) term and the share the model's prod_<s> columns carry
    E  day-to-day noise (Stage 3's over-dispersion, 2010-2018 constants), its damping of leverage modulations, the Bo5/Bo3
       ratio; volatility and posterior-variance attenuation bounds (Stage 3 ratings' posterior SDs)
    F  de-vigging: the slope a proportional de-vig implies when the margin is loaded by the power rule, Shin's model or
       equally; the 2013-2021 overround distribution

Writes data/studies/feature_interactions/round0/mathematics/: results.json and the CSV tables named below; prints the
markdown tables quoted in the ideas file.
Run: ./python.sh src/eda/feature_interactions/round0/mathematics/markov_composition.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "feature_interactions" / "round0" / "mathematics"
MODEL_FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
SURFACE_FEATURES = ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet"
STAGE4_CONSTANTS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"
STAGE3_SHRINK = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage3_shrinkage.csv"
STAGE3_RATINGS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage3_ratings.parquet"
STAGE1_ODDS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"

DISCOVERY_LAST = 2021                    # no season after 2021 is read anywhere in this script
SURF = {0: "Hard", 1: "Clay", 2: "Grass", 3: "Carpet"}
TOURS = ("atp", "wta")
H = 1e-4                                 # finite-difference step on probabilities / logits
SET_RULES = {"TB7@6": (6, 7), "TB10@6": (6, 10), "TB7@12": (12, 7), "ADV": (None, 0)}
STANDARD = "TB7@6"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def lg(p):
    p = np.clip(np.asarray(p, dtype="float64"), 1e-15, 1 - 1e-15)
    return np.log(p) - np.log1p(-p)


# ------------------------------------------------------------------------------------------------
# A. The iid model

def game(p):
    """P(the server holds) when each serve point is won with probability p."""
    p = np.asarray(p, dtype="float64")
    q = 1.0 - p
    return p ** 4 * (1.0 + 4.0 * q + 10.0 * q * q) + 20.0 * p ** 3 * q ** 3 * (p * p / (p * p + q * q))


def _tb_first(k: int) -> bool:
    """Whether the tiebreak's first server serves point k (0-indexed): one point, then two each."""
    return k == 0 or ((k - 1) // 2) % 2 == 1


def tiebreak(pa, pb, target: int = 7, a_first: bool = True):
    """P(A wins a tiebreak to ``target``, by two). pa, pb: each player's serve-point probability."""
    pa, pb = np.broadcast_arrays(np.asarray(pa, dtype="float64"), np.asarray(pb, dtype="float64"))
    wa, wb = pa, 1.0 - pb                     # A wins a point on A's serve, on B's serve
    won = np.zeros(pa.shape)
    layer = {(0, 0): np.ones(pa.shape)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == target - 1 and j == target - 1:          # from here every two points hold one serve each
                won = won + r * wa * wb / (wa * wb + (1 - wa) * (1 - wb))
                continue
            w = wa if _tb_first(i + j) == a_first else wb
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1.0 - w)):
                if max(ni, nj) >= target and abs(ni - nj) >= 2:
                    if ni > nj:
                        won = won + r * pr
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return won


def set_win(pa, pb, rule: str = STANDARD, a_first: bool = True):
    """P(A wins a set): first to six games by two, a tiebreak at 6-6 (or 12-12), or an advantage set."""
    pa, pb = np.broadcast_arrays(np.asarray(pa, dtype="float64"), np.asarray(pb, dtype="float64"))
    tb_at, tb_pts = SET_RULES[rule]
    ha, hb = game(pa), game(pb)
    won = np.zeros(pa.shape)
    layer = {(0, 0): np.ones(pa.shape)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if tb_at is not None and i == tb_at and j == tb_at:
                won = won + r * tiebreak(pa, pb, tb_pts, a_first=(((i + j) % 2 == 0) == a_first))
                continue
            if tb_at is None and i == j and i >= 5:            # advantage set: a pair of games holds one of each
                won = won + r * ha * (1 - hb) / (ha * (1 - hb) + (1 - ha) * hb)
                continue
            a_serves = ((i + j) % 2 == 0) == a_first
            w = ha if a_serves else 1.0 - hb
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1.0 - w)):
                if max(ni, nj) >= 6 and abs(ni - nj) >= 2:
                    if ni > nj:
                        won = won + r * pr
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return won


def reach_tiebreak(pa, pb, a_first: bool = True):
    """P(a standard set reaches 6-6)."""
    pa, pb = np.broadcast_arrays(np.asarray(pa, dtype="float64"), np.asarray(pb, dtype="float64"))
    ha, hb = game(pa), game(pb)
    reach = np.zeros(pa.shape)
    layer = {(0, 0): np.ones(pa.shape)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == 6 and j == 6:
                reach = reach + r
                continue
            a_serves = ((i + j) % 2 == 0) == a_first
            w = ha if a_serves else 1.0 - hb
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1.0 - w)):
                if not (max(ni, nj) >= 6 and abs(ni - nj) >= 2):
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return reach


def match_win(pa, pb, best_of: int = 3, final_rule: str = STANDARD):
    """P(A wins the match). Sets are independent draws (who serves first does not change a set's chance; checked)."""
    s = set_win(pa, pb, STANDARD)
    f = s if final_rule == STANDARD else set_win(pa, pb, final_rule)
    if int(best_of) == 3:
        return s * s + 2 * s * (1 - s) * f
    return s ** 3 + 3 * s ** 3 * (1 - s) + 6 * s * s * (1 - s) ** 2 * f


def L(pa, pb, bo: int = 3, final: str = STANDARD):
    """The match log-odds that A wins."""
    return lg(match_win(pa, pb, bo, final))


def lev_prob(m, bo: int, final: str = STANDARD):
    """dP/dd at d = 0, pA = m + d/2, pB = m - d/2 (per unit of d)."""
    m = np.asarray(m, dtype="float64")
    return (match_win(m + H / 2, m - H / 2, bo, final) - 0.5) / H


def lev_logit(mu, bo: int, final: str = STANDARD):
    """beta_L(mu) = d logit P / d Delta at Delta = 0, with logit pA = mu + Delta/2, logit pB = mu - Delta/2."""
    mu = np.asarray(mu, dtype="float64")
    return L(expit(mu + H / 2), expit(mu - H / 2), bo, final) / H


def dP_ds(m, d, bo: int, final: str = STANDARD, step: float = 1e-4):
    """dP/d(pA + pB) at fixed pA - pB = d, at pA + pB = 2m."""
    up = match_win(m + step + d / 2, m + step - d / 2, bo, final)
    dn = match_win(m - step + d / 2, m - step - d / 2, bo, final)
    return (up - dn) / (4 * step)


def verify() -> dict:
    """The model against the textbook value, stage2_iid (read-only), antisymmetry and first-server independence."""
    from src.eda.predictability_diagnostic import stage2_iid as S2
    rng = np.random.default_rng(1)
    pa, pb = rng.uniform(0.35, 0.85, 400), rng.uniform(0.35, 0.85, 400)
    out = {"hold_at_0.60": float(game(0.6)), "textbook_hold_at_0.60": 0.7357}
    out["max_gap_game"] = float(np.abs(game(pa) - S2.game(pa)).max())
    gaps = []
    for t in (7, 10):
        gaps.append(np.abs(tiebreak(pa, pb, t) - S2.tiebreak(pa, pb, t)).max())
    for rule in SET_RULES:
        gaps.append(np.abs(set_win(pa, pb, rule) - S2.set_win(pa, pb, rule)).max())
        for bo in (3, 5):
            gaps.append(np.abs(match_win(pa, pb, bo, rule) - S2.match_win(pa, pb, bo, rule)).max())
    out["max_gap_vs_stage2_iid"] = float(max(gaps))
    out["max_antisymmetry_gap"] = float(max(np.abs(match_win(pa, pb, bo, r) + match_win(pb, pa, bo, r) - 1).max()
                                            for bo in (3, 5) for r in SET_RULES))
    out["max_first_server_gap"] = float(max(np.abs(set_win(pa, pb, r, True) - set_win(pa, pb, r, False)).max()
                                            for r in SET_RULES))
    ok = (abs(out["hold_at_0.60"] - 0.7357) < 5e-5 and out["max_gap_game"] < 1e-12 and out["max_gap_vs_stage2_iid"] < 1e-12
          and out["max_antisymmetry_gap"] < 1e-12 and out["max_first_server_gap"] < 1e-12)
    out["ok"] = bool(ok)
    if not ok:
        raise RuntimeError(f"iid model check failed: {out}")
    return out


# ------------------------------------------------------------------------------------------------
# B. Grids

# The iid model does not know the tour: on the (m, d) grid women's Bo3 is the same function as men's Bo3, read at the
# women's lower serve dominance (realistic m: men 0.57-0.72, women 0.50-0.64; see the pair-dominance spreads).
FORMATS = [("Bo3 (both tours)", 3, STANDARD), ("Bo5", 5, STANDARD), ("Bo5, 10-point final-set tiebreak", 5, "TB10@6")]
M_GRID = np.round(np.arange(0.50, 0.7401, 0.03), 2)
D_GRID = (0.02, 0.04, 0.06, 0.10)


def grids() -> dict:
    rows = []
    for name, bo, fin in FORMATS:
        for m in M_GRID:
            r = {"format": name, "m": float(m), "beta_prob": float(lev_prob(m, bo, fin)),
                 "beta_logitP_per_unit_d": float(4 * lev_prob(m, bo, fin)),
                 "tiebreak_share": float(reach_tiebreak(m, m))}
            for d in D_GRID:
                r[f"P_d{d:.2f}"] = float(match_win(m + d / 2, m - d / 2, bo, fin))
                r[f"dPds_d{d:.2f}"] = float(dP_ds(m, d, bo, fin))
            rows.append(r)
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "grid_prob_scale.csv", index=False)

    # logit scale: beta_L(mu), its slope in mu (the composition's quadratic coefficient h), Bo5/Bo3
    mus = {"men clay": float(np.log(0.6038 / 0.3962)), "men hard": float(np.log(0.6283 / 0.3717)),
           "men grass": float(np.log(0.6553 / 0.3447)), "women clay": float(np.log(0.5500 / 0.4500)),
           "women hard": float(np.log(0.5581 / 0.4419)), "women grass": float(np.log(0.5873 / 0.4127))}
    lrows = []
    for nm, mu in mus.items():
        for bo in ((3, 5) if nm.startswith("men") else (3,)):
            b = float(lev_logit(mu, bo))
            dmu = 1e-3
            h = float((lev_logit(mu + dmu, bo) - lev_logit(mu - dmu, bo)) / (2 * dmu))
            curv = {}
            for D in (0.1, 0.25, 0.5, 0.75, 1.0):
                curv[f"ratio_D{D}"] = float(L(expit(mu + D / 2), expit(mu - D / 2), bo) / (b * D))
            lrows.append({"case": nm, "best_of": bo, "mu": mu, "p_bar": float(expit(mu)), "beta_L": b,
                          "h_dbeta_dmu": h, "rel_per_logit": h / b, "rel_per_0.1_logit": 0.1 * h / b, **curv})
    ltab = pd.DataFrame(lrows)
    ltab.to_csv(OUT / "grid_logit_scale.csv", index=False)
    for nm in ("men clay", "men hard", "men grass"):
        b3 = ltab[(ltab.case == nm) & (ltab.best_of == 3)].beta_L.iloc[0]
        b5 = ltab[(ltab.case == nm) & (ltab.best_of == 5)].beta_L.iloc[0]
        ltab.loc[(ltab.case == nm) & (ltab.best_of == 5), "bo5_over_bo3"] = b5 / b3

    # deciding-set rules
    frows = []
    for nm, bo, mu in (("men Bo5, hard", 5, mus["men hard"]), ("women Bo3, hard", 3, mus["women hard"])):
        m = float(expit(mu))
        for d in (0.02, 0.05):
            base = float(match_win(m + d / 2, m - d / 2, bo, STANDARD))
            for rule in SET_RULES:
                pr = float(match_win(m + d / 2, m - d / 2, bo, rule))
                frows.append({"case": nm, "d": d, "rule": rule, "P": pr, "minus_TB7_pp": 100 * (pr - base),
                              "logit_minus_TB7": float(lg(pr) - lg(base))})
    ftab = pd.DataFrame(frows)
    ftab.to_csv(OUT / "final_set_rules.csv", index=False)

    # the hold scale: d logit(hold) / d logit(p)
    hrows = []
    for p in np.round(np.arange(0.50, 0.7601, 0.02), 2):
        dl = (lg(game(expit(lg(p) + H))) - lg(game(expit(lg(p) - H)))) / (2 * H)
        hrows.append({"p": float(p), "hold": float(game(p)), "dlogit_hold_dlogit_p": float(dl)})
    htab = pd.DataFrame(hrows)
    htab.to_csv(OUT / "hold_scale.csv", index=False)
    return {"prob": tab, "logit": ltab, "final": ftab, "hold": htab, "mus": mus}


# ------------------------------------------------------------------------------------------------
# C, D. Real match character from features only (2013-2021 training rows)

def surface_means() -> dict:
    k = pd.read_csv(STAGE4_CONSTANTS)
    k = k[k["kind"].eq("surface average")]
    return {(r.stat, r.tour, r.surface): float(r.value) for r in k.itertuples(index=False)}


def mu_rows(frame: pd.DataFrame, stat: str, means: dict) -> np.ndarray:
    keys = zip([stat] * len(frame), frame["tour"], frame["in_surface"].map(SURF))
    return lg(np.array([means[k] for k in keys]))


def odds_weights(frame: pd.DataFrame) -> dict:
    """E[p(1-p)] and E[p(1-p) z^2] of the 2013-2021 closing odds, per tour: the weights that turn a log-odds error into
    milli-log-loss. Only the odds' own distribution is used."""
    out = {}
    for t in TOURS:
        z = frame.loc[frame.tour.eq(t), "in_odds_logit"].to_numpy(dtype="float64")
        z = z[np.isfinite(z)]
        p = expit(z)
        w = p * (1 - p)
        # E[(1-p)/p + p/(1-p)] = E[2 cosh z]: the weight of a per-player retirement-hazard term h_B/p - h_A/(1-p)
        out[t] = {"n": int(len(z)), "sd_z": float(z.std()), "E_w": float(w.mean()), "E_wz2": float((w * z * z).mean()),
                  "E_2cosh_z": float(np.mean(2 * np.cosh(z))),
                  "share_abs_z_over_1.5": float(np.mean(np.abs(z) > 1.5)),
                  "share_abs_z_over_2.2": float(np.mean(np.abs(z) > 2.2))}
    return out


def mll_relative(kappa_rms: float, E_wz2: float) -> float:
    """Milli-log-loss value of a missing relative modulation of the log-odds with RMS kappa (independent of z)."""
    return 1000 * 0.5 * E_wz2 * kappa_rms ** 2


def mll_additive(tau_rms: float, E_w: float) -> float:
    return 1000 * 0.5 * E_w * tau_rms ** 2


def pair_dominance(frame: pd.DataFrame, means: dict) -> tuple[dict, pd.DataFrame]:
    """The pair's serve dominance on the serve-point logit scale, from the leak-proof surface IOS (spw), and the leverage
    modulation it implies; exact z under the iid model."""
    out = {}
    mu = mu_rows(frame, "spw", means)
    Oa, Ob = frame["srf_O_eff_spw_a"].to_numpy(), frame["srf_O_eff_spw_b"].to_numpy()
    Da, Db = frame["srf_D_eff_spw_a"].to_numpy(), frame["srf_D_eff_spw_b"].to_numpy()
    xa, xb = mu + Oa - Db, mu + Ob - Da
    delta, half_sum_y = xa - xb, (xa + xb) / 2 - mu
    bo = frame["in_best_of"].to_numpy()
    ok = np.isfinite(xa) & np.isfinite(xb) & np.isin(bo, [3, 5])
    z_iid = np.full(len(frame), np.nan)
    z_surf = np.full(len(frame), np.nan)
    b_pair = np.full(len(frame), np.nan)
    b_surf = np.full(len(frame), np.nan)
    for b in (3, 5):
        s = ok & (bo == b)
        z_iid[s] = L(expit(xa[s]), expit(xb[s]), b)
        z_surf[s] = L(expit(mu[s] + delta[s] / 2), expit(mu[s] - delta[s] / 2), b)
        b_pair[s] = lev_logit((xa[s] + xb[s]) / 2, b)
        b_surf[s] = lev_logit(mu[s], b)
    kappa = b_pair / b_surf - 1
    # the same modulation when the point-level difference is read on the probability scale (pA - pB): the leverage
    # dP/dd at the pair's mean serve probability over the leverage at the surface's
    kappa_prob = np.full(len(frame), np.nan)
    for b in (3, 5):
        s = ok & (bo == b)
        m_pair = (expit(xa[s]) + expit(xb[s])) / 2
        kappa_prob[s] = lev_prob(m_pair, b) / lev_prob(expit(mu[s]), b) - 1
    per = pd.DataFrame({"tour": frame["tour"].to_numpy(), "best_of": bo, "surface": frame["in_surface"].to_numpy(),
                        "delta": delta, "half_sum_y": half_sum_y, "mu": mu, "z_iid": z_iid, "z_surf": z_surf,
                        "kappa": kappa, "kappa_prob": kappa_prob, "ok": ok})
    # per-player serve-minus-return style and total strength (player-match rows, both sides)
    O = np.r_[Oa, Ob]
    D = np.r_[Da, Db]
    tt = np.r_[frame["tour"].to_numpy(), frame["tour"].to_numpy()]
    for t in TOURS:
        s = per.ok.to_numpy() & (per.tour.to_numpy() == t)
        sp = np.isfinite(O) & np.isfinite(D) & (tt == t)
        tau = per.z_iid[s] - per.z_surf[s]
        out[t] = {"matches": int(s.sum()),
                  "sd_delta": float(per.delta[s].std()), "sd_half_sum_y": float(per.half_sum_y[s].std()),
                  "sd_mu_surface": float(per.mu[s].std()),
                  "corr_delta_half_sum_y": float(np.corrcoef(per.delta[s], per.half_sum_y[s])[0, 1]),
                  "player_sd_O": float(O[sp].std()), "player_sd_D": float(D[sp].std()),
                  "player_corr_O_D": float(np.corrcoef(O[sp], D[sp])[0, 1]),
                  "player_sd_style_Y": float((O[sp] - D[sp]).std()), "player_sd_total_T": float((O[sp] + D[sp]).std()),
                  "rms_z_iid": float(np.sqrt(np.mean(per.z_iid[s] ** 2))),
                  "rms_tau_pair": float(np.sqrt(np.mean(tau ** 2))),
                  "rel_tau_pair": float(np.sqrt(np.mean(tau ** 2)) / np.sqrt(np.mean(per.z_iid[s] ** 2))),
                  "rms_kappa": float(np.sqrt(np.mean(per.kappa[s] ** 2))),
                  "kappa_p05_p95": [float(np.quantile(per.kappa[s], 0.05)), float(np.quantile(per.kappa[s], 0.95))],
                  "rms_kappa_prob_scale": float(np.sqrt(np.mean(per.kappa_prob[s] ** 2))),
                  "kappa_prob_p05_p95": [float(np.quantile(per.kappa_prob[s], 0.05)),
                                         float(np.quantile(per.kappa_prob[s], 0.95))],
                  "share_bo5": float((per.best_of[s] == 5).mean())}
        m_pair = (expit(xa) + expit(xb))[s] / 2
        out[t]["m_pair_prob_quantiles_05_25_50_75_95"] = [float(np.quantile(m_pair, q))
                                                          for q in (0.05, 0.25, 0.5, 0.75, 0.95)]
        out[t]["abs_d_prob_quantiles_50_90"] = [float(np.quantile(np.abs(expit(xa) - expit(xb))[s], q))
                                                for q in (0.5, 0.9)]
    return out, per


def stage3_true_spread() -> dict:
    """The true between-player spread of opponent-adjusted serve and return points won (Stage 3's method-of-moments
    constants, 2013-2018), on the logit scale, and the pair dominance SD it implies for a given serve-return correlation."""
    k = pd.read_csv(STAGE3_SHRINK)
    out = {}
    for t in TOURS:
        r = {}
        for st in ("spw_adj", "rpw_adj"):
            row = k[(k.stat == st) & (k.tour == t) & (k.surface == "all") & (k.years == "2013-2018")].iloc[0]
            p = float(row["mean"])
            r[st] = {"mean": p, "true_sd_prob": float(row.true_sd), "true_sd_logit": float(row.true_sd) / (p * (1 - p)),
                     "overdispersion": float(row.overdispersion), "units_per_match": float(row.units_per_match)}
        out[t] = r
    return out


def profile_composition(frame: pd.DataFrame, means: dict) -> tuple[dict, dict]:
    """Section D: the serve-point probability composed from the surface-IOS first serves in, first- and second-serve
    points won (p = fi fw + (1 - fi) sw), against what the A - B inputs can express."""
    stats = ("first_in", "first_won", "second_won")
    bo = frame["in_best_of"].to_numpy()
    x = {}
    mu = {}
    for s in stats:
        mu[s] = mu_rows(frame, s, means)
        Oa, Ob = frame[f"srf_O_eff_{s}_a"].to_numpy(), frame[f"srf_O_eff_{s}_b"].to_numpy()
        Da, Db = frame[f"srf_D_eff_{s}_a"].to_numpy(), frame[f"srf_D_eff_{s}_b"].to_numpy()
        x[s] = (mu[s] + Oa - Db, mu[s] + Ob - Da)             # A serving to B, B serving to A

    def comp(xfi, xfw, xsw):
        fi = expit(xfi)
        return fi * expit(xfw) + (1 - fi) * expit(xsw)

    p_ab = comp(x["first_in"][0], x["first_won"][0], x["second_won"][0])
    p_ba = comp(x["first_in"][1], x["first_won"][1], x["second_won"][1])
    xs = {s: (mu[s] + (x[s][0] - x[s][1]) / 2, mu[s] - (x[s][0] - x[s][1]) / 2) for s in stats}   # sums set to the mean
    q_ab = comp(xs["first_in"][0], xs["first_won"][0], xs["second_won"][0])
    q_ba = comp(xs["first_in"][1], xs["first_won"][1], xs["second_won"][1])
    fi0, fw0, sw0 = expit(mu["first_in"]), expit(mu["first_won"]), expit(mu["second_won"])
    m0 = fi0 * fw0 + (1 - fi0) * sw0
    lin = ((fw0 - sw0) * fi0 * (1 - fi0) * (x["first_in"][0] - x["first_in"][1])
           + fi0 * fw0 * (1 - fw0) * (x["first_won"][0] - x["first_won"][1])
           + (1 - fi0) * sw0 * (1 - sw0) * (x["second_won"][0] - x["second_won"][1]))
    ok = np.isfinite(p_ab) & np.isfinite(p_ba) & np.isin(bo, [3, 5])
    dp = p_ab - p_ba
    z_exact, z_sumfree, z_lev = (np.full(len(frame), np.nan) for _ in range(3))
    for b in (3, 5):
        s = ok & (bo == b)
        z_exact[s] = L(p_ab[s], p_ba[s], b)
        z_sumfree[s] = L(q_ab[s], q_ba[s], b)
        z_lev[s] = L(m0[s] + dp[s] / 2, m0[s] - dp[s] / 2, b)
    # the composed points-level difference against the surface IOS of serve points won itself
    mu_spw = mu_rows(frame, "spw", means)
    xa = mu_spw + frame["srf_O_eff_spw_a"].to_numpy() - frame["srf_D_eff_spw_b"].to_numpy()
    xb = mu_spw + frame["srf_O_eff_spw_b"].to_numpy() - frame["srf_D_eff_spw_a"].to_numpy()
    out = {}
    tour = frame["tour"].to_numpy()
    for t in TOURS:
        s = ok & (tour == t) & np.isfinite(xa) & np.isfinite(xb)
        rms = lambda v: float(np.sqrt(np.mean(np.asarray(v)[s] ** 2)))   # noqa: E731
        out[t] = {"matches": int(s.sum()), "rms_dp": rms(dp), "rms_dp_minus_linear": rms(dp - lin),
                  "rms_dp_minus_sumfree": rms(dp - (q_ab - q_ba)),
                  "rms_pair_mean_p_minus_m0": rms((p_ab + p_ba) / 2 - m0),
                  "rms_z_exact": rms(z_exact), "rms_z_exact_minus_sumfree": rms(z_exact - z_sumfree),
                  "rms_z_exact_minus_lev": rms(z_exact - z_lev), "rms_z_lev_minus_sumfree": rms(z_lev - z_sumfree),
                  "corr_logit_dp_composed_vs_spw_ios": float(np.corrcoef(lg(p_ab[s]) - lg(p_ba[s]), (xa - xb)[s])[0, 1]),
                  "corr_pair_mean_composed_vs_spw_ios": float(np.corrcoef(((lg(p_ab) + lg(p_ba)) / 2)[s],
                                                                          ((xa + xb) / 2)[s])[0, 1])}
    # second-order term per statistic: x_A'^2 - x_B'^2 = (O_A^2 - O_B^2) - (D_A^2 - D_B^2) + 2 prod
    quad = {}
    for s in ("ace", "df", "first_in", "first_won", "second_won", "hold"):
        Oa, Ob = frame[f"srf_O_eff_{s}_a"].to_numpy(), frame[f"srf_O_eff_{s}_b"].to_numpy()
        Da, Db = frame[f"srf_D_eff_{s}_a"].to_numpy(), frame[f"srf_D_eff_{s}_b"].to_numpy()
        m = mu_rows(frame, s, means)
        xa_, xb_ = Oa - Db, Ob - Da                                # centred matchup logits
        prod = Oa * (-Db) - Ob * (-Da)                             # the model's prod_<s>
        sq = (Oa ** 2 - Ob ** 2) - (Da ** 2 - Db ** 2)             # the within-player squares the model lacks
        ident = np.nanmax(np.abs((xa_ ** 2 - xb_ ** 2) - (sq + 2 * prod)))
        for t in TOURS:
            s_ = (tour == t) & np.isfinite(xa_) & np.isfinite(xb_)
            pbar = expit(m[s_])
            e = expit(m[s_] + xa_[s_]) - expit(m[s_] + xb_[s_])                       # probability-scale edge
            e1 = pbar * (1 - pbar) * (xa_[s_] - xb_[s_])
            nl = e - e1                                                               # the non-linear part
            X1 = prod[s_][:, None]
            X2 = np.column_stack([prod[s_], sq[s_]])
            w1 = pbar * (1 - pbar) * (1 - 2 * pbar) / 2
            r2 = lambda X: float(1 - np.sum((nl - X @ np.linalg.lstsq(X, nl, rcond=None)[0]) ** 2) / np.sum(nl ** 2))  # noqa: E731
            quad[f"{s}|{t}"] = {"identity_max_gap": float(ident), "p_bar": float(pbar.mean()),
                                "rms_edge": float(np.sqrt(np.mean(e ** 2))),
                                "rms_nonlinear": float(np.sqrt(np.mean(nl ** 2))),
                                "rel_nonlinear": float(np.sqrt(np.mean(nl ** 2)) / np.sqrt(np.mean(e ** 2))),
                                "r2_nonlinear_on_prod": r2(X1), "r2_nonlinear_on_prod_and_squares": r2(X2),
                                "r2_nonlinear_on_2nd_order": r2((w1 * (sq[s_] + 2 * prod[s_]))[:, None]),
                                "sd_prod": float(np.std(prod[s_])), "sd_squares": float(np.std(sq[s_])),
                                "corr_prod_squares": float(np.corrcoef(prod[s_], sq[s_])[0, 1])}
    return out, quad


# ------------------------------------------------------------------------------------------------
# E. Day-to-day noise, volatility, posterior uncertainty

def gh_expect_P(mu: float, delta: float, sd: float, bo: int, n: int = 48) -> float:
    """E over u ~ N(0, sd^2) of P(match) with logit pA = mu + (delta + u)/2, logit pB = mu - (delta + u)/2."""
    t, w = np.polynomial.hermite.hermgauss(n)
    u = np.sqrt(2.0) * sd * t
    pr = match_win(expit(mu + (delta + u) / 2), expit(mu - (delta + u) / 2), bo)
    return float(np.sum(w * pr) / np.sqrt(np.pi))


def day_noise(spread: dict) -> dict:
    out = {}
    for t in TOURS:
        sv, rt = spread[t]["spw_adj"], spread[t]["rpw_adj"]
        # excess (beyond binomial) variance of one match's opponent-adjusted rate, logit scale: (od - 1) / (n p (1 - p))
        ex_s = (sv["overdispersion"] - 1) / (sv["units_per_match"] * sv["mean"] * (1 - sv["mean"]))
        ex_r = (rt["overdispersion"] - 1) / (rt["units_per_match"] * rt["mean"] * (1 - rt["mean"]))
        both = (ex_s + ex_r) / 2                   # = server's day variance + returner's day variance (+ conditions)
        mu = float(np.log(sv["mean"] / (1 - sv["mean"])))
        res = {"excess_var_serve_logit": ex_s, "excess_var_return_logit": ex_r, "sigma_s2_plus_sigma_r2": both,
               "mu_all_surfaces": mu, "cases": []}
        for rho, theta in ((0.0, 0.0), (0.5, 0.0), (0.0, 0.5)):
            vday = 2 * both * (1 - theta) * (1 + rho)      # var of the day noise on Delta (equal serve/return SDs)
            for bo in ((3, 5) if t == "atp" else (3,)):
                b = float(lev_logit(mu, bo))
                se = b * np.sqrt(vday)
                c2 = 1 / (1 + np.pi * se ** 2 / 8)
                dlt = 0.05
                zpre = lg(gh_expect_P(mu, dlt, np.sqrt(vday), bo))
                c_exact = float(zpre / (b * dlt))
                # exact damping of a leverage modulation: d ln z_pre / d mu over d ln beta_L / d mu
                dm = 0.02
                zp_up = lg(gh_expect_P(mu + dm, dlt, np.sqrt(vday), bo))
                zp_dn = lg(gh_expect_P(mu - dm, dlt, np.sqrt(vday), bo))
                b_up, b_dn = float(lev_logit(mu + dm, bo)), float(lev_logit(mu - dm, bo))
                damp = float(((np.log(zp_up) - np.log(zp_dn)) / (2 * dm)) / ((np.log(b_up) - np.log(b_dn)) / (2 * dm)))
                res["cases"].append({"rho_serve_return_day": rho, "conditions_share": theta, "best_of": bo,
                                     "var_day_delta": vday, "sd_day_delta": float(np.sqrt(vday)), "beta_L": b,
                                     "sd_match_logit_noise": float(se), "c2_probit": float(c2),
                                     "c_exact": c_exact, "c2_exact": c_exact ** 2, "damping_exact": damp})
        if t == "atp":                              # Bo5 / Bo3 log-odds ratio, without and with day noise
            ratio = {}
            for rho, theta in ((0.0, 0.0), (0.5, 0.0)):
                vday = 2 * both * (1 - theta) * (1 + rho)
                for dlt in (0.05, 0.3):
                    z3 = lg(gh_expect_P(mu, dlt, np.sqrt(vday), 3))
                    z5 = lg(gh_expect_P(mu, dlt, np.sqrt(vday), 5))
                    z3n = L(expit(mu + dlt / 2), expit(mu - dlt / 2), 3)
                    z5n = L(expit(mu + dlt / 2), expit(mu - dlt / 2), 5)
                    ratio[f"rho{rho}_delta{dlt}"] = {"no_noise": float(z5n / z3n), "with_noise": float(z5 / z3)}
            res["bo5_over_bo3"] = ratio
        out[t] = res
    return out


def posterior_uncertainty(frame: pd.DataFrame, dn: dict) -> dict:
    """Stage 3 ratings' pre-match posterior SDs (serve and return, both players): the variance of the points-level
    difference Delta = S_A + R_A - S_B - R_B, and the attenuation spread it implies beside the day noise."""
    r = pd.read_parquet(STAGE3_RATINGS, columns=["match_id", "year", "sd_serve_a", "sd_serve_b", "sd_return_a",
                                                 "sd_return_b"])
    r = r[r.year <= DISCOVERY_LAST]
    j = frame[["match_id", "tour"]].merge(r, on="match_id", how="left")
    v = (j.sd_serve_a ** 2 + j.sd_serve_b ** 2 + j.sd_return_a ** 2 + j.sd_return_b ** 2).to_numpy()
    out = {"joined_share": float(np.isfinite(v).mean())}
    for t in TOURS:
        s = np.isfinite(v) & (j.tour.to_numpy() == t)
        vt = v[s]
        case = [c for c in dn[t]["cases"] if c["best_of"] == 3 and c["rho_serve_return_day"] == 0.0
                and c["conditions_share"] == 0.0][0]
        b, vday = case["beta_L"], case["var_day_delta"]
        k = np.pi / 8
        for label, vd in (("no_day_noise", 0.0), ("with_day_noise", vday)):
            att = 1 / np.sqrt(1 + k * b * b * (vd + vt))
            kap = att / att.mean() - 1
            out[f"{t}|{label}"] = {"matches": int(s.sum()), "v_median": float(np.median(vt)),
                                   "v_p10": float(np.quantile(vt, 0.1)), "v_p90": float(np.quantile(vt, 0.9)),
                                   "v_p99": float(np.quantile(vt, 0.99)), "rms_kappa": float(np.sqrt(np.mean(kap ** 2))),
                                   "kappa_p01": float(np.quantile(kap, 0.01))}
    return out


# ------------------------------------------------------------------------------------------------
# F. De-vigging

def quotes(p: float, M: float, rule: str) -> tuple[float, float]:
    """The bookmaker's implied probabilities (1/odds) for true p and overround 1 + M under a margin-loading rule."""
    if rule == "power":
        a = brentq(lambda a: p ** a + (1 - p) ** a - (1 + M), 0.2, 1.0)
        return p ** a, (1 - p) ** a
    if rule == "shin":
        def tot(zz):
            return (np.sqrt(zz * p + (1 - zz) * p * p) + np.sqrt(zz * (1 - p) + (1 - zz) * (1 - p) ** 2)) ** 2
        zz = brentq(lambda zz: tot(zz) - (1 + M), 1e-12, 0.9)
        pi_ = 1 + M
        return float(np.sqrt(pi_ * (zz * p + (1 - zz) * p * p))), float(np.sqrt(pi_ * (zz * (1 - p) + (1 - zz) * (1 - p) ** 2)))
    if rule == "equal":
        return p + M / 2, 1 - p + M / 2
    raise KeyError(rule)


def devig(frame: pd.DataFrame) -> dict:
    rows = []
    for rule in ("power", "shin", "equal"):
        for M in (0.03, 0.05, 0.058, 0.07, 0.10):
            for z in (0.5, 1.0, 1.5, 2.0, 3.0):
                p = float(expit(z))
                qa, qb = quotes(p, M, rule)
                zp = float(lg(qa / (qa + qb)))
                rows.append({"rule": rule, "margin": M, "z_true": z, "z_proportional": zp, "slope_needed": z / zp})
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "devig_slopes.csv", index=False)
    o = pd.read_parquet(STAGE1_ODDS, columns=["match_id", "year", "overround_avg", "avg_coherent", "p_avg_a", "p_ps_a",
                                              "ps_coherent"])
    o = o[(o.year <= DISCOVERY_LAST) & o.avg_coherent.fillna(False)]
    j = frame[["match_id", "tour"]].merge(o, on="match_id", how="left")
    out = {"table": rows, "overround": {}, "avg_vs_pinnacle": {}}
    for t in TOURS:                              # the average close against Pinnacle's: a bound on its measurement noise
        s = (j.tour == t).to_numpy() & j.ps_coherent.fillna(False).to_numpy() & np.isfinite(j.p_ps_a.to_numpy())
        za, zp = lg(j.p_avg_a.to_numpy()[s]), lg(j.p_ps_a.to_numpy()[s])
        dd = za - zp
        lam = 1 - (dd.var() / 2) / za.var()     # reliability of z_avg if half the gap's variance is its own noise
        out["avg_vs_pinnacle"][t] = {"matches": int(s.sum()), "sd_gap": float(dd.std()), "mean_gap": float(dd.mean()),
                                     "slope_zps_on_zavg": float(np.polyfit(za, zp, 1)[0]),
                                     "reliability_if_half_noise": float(lam)}
    for t in TOURS:
        m = (j.overround_avg - 1).to_numpy()[(j.tour == t).to_numpy()]
        m = m[np.isfinite(m)]
        res = {"matches": int(len(m)), "mean": float(m.mean()), "sd": float(m.std()),
               "q05": float(np.quantile(m, 0.05)), "q50": float(np.quantile(m, 0.5)), "q95": float(np.quantile(m, 0.95))}
        for rule in ("power", "shin"):          # slope needed at |z| = 1 as a function of the match's margin
            grid = np.linspace(max(0.005, float(np.quantile(m, 0.001))), float(np.quantile(m, 0.999)), 40)
            sl = np.array([1.0 / float(lg(quotes(float(expit(1.0)), g, rule)[0] /
                                          sum(quotes(float(expit(1.0)), g, rule)))) for g in grid])
            b = np.interp(m, grid, sl)
            kap = b / b.mean() - 1
            res[f"{rule}_slope_mean"] = float(b.mean())
            res[f"{rule}_rms_kappa"] = float(np.sqrt(np.mean(kap ** 2)))
        out["overround"][t] = res
    out["joined_share"] = float(np.isfinite(j.overround_avg).mean())
    return out


# ------------------------------------------------------------------------------------------------

def md(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---:" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    res: dict = {"note": "mechanistic; no match result read; seasons <= 2021 only"}
    res["verify"] = verify()
    log(f"iid model verified: {res['verify']}")

    g = grids()
    log("grids done")

    means = surface_means()
    cols = ["match_id", "tour", "season", "in_surface", "in_best_of", "in_odds_logit"]
    f = pd.read_parquet(MODEL_FRAME, columns=cols)
    f = f[f.season <= DISCOVERY_LAST].reset_index(drop=True)
    stats = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold")
    sf_cols = ["match_id"] + [f"srf_{k}_eff_{s}_{side}" for s in stats for k in ("O", "D") for side in ("a", "b")]
    sf = pd.read_parquet(SURFACE_FEATURES, columns=sf_cols)
    f = f.merge(sf, on="match_id", how="left", validate="one_to_one")
    res["rows_2013_2021"] = int(len(f))
    res["surface_ios_joined_share"] = float(np.isfinite(f["srf_O_eff_spw_a"]).mean())
    res["odds_weights"] = odds_weights(f)
    log(f"training rows {len(f):,}; surface IOS joined {res['surface_ios_joined_share']:.4f}")

    pdm, per = pair_dominance(f, means)
    res["pair_dominance"] = pdm
    for t in TOURS:
        w = res["odds_weights"][t]
        pdm[t]["mll_if_price_ignores_pair_dominance"] = mll_relative(pdm[t]["rms_kappa"], w["E_wz2"])
        pdm[t]["mll_if_price_ignores_pair_dominance_prob_scale"] = mll_relative(pdm[t]["rms_kappa_prob_scale"], w["E_wz2"])
        pdm[t]["ratio_sd_market_z_over_rms_z_iid"] = w["sd_z"] / pdm[t]["rms_z_iid"]
        # retirement hazard: tau = (h_B - hbar)/p - (h_A - hbar)/(1 - p); E[w tau^2] = sd_h^2 E[2 cosh z]
        pdm[t]["mll_retirement_hazard_sd"] = {f"{sd_h}": 1000 * 0.5 * sd_h ** 2 * w["E_2cosh_z"]
                                              for sd_h in (0.005, 0.01, 0.02)}
    res["stage3_true_spread"] = stage3_true_spread()
    log("pair dominance done")

    comp, quad = profile_composition(f, means)
    res["profile_composition"], res["second_order"] = comp, quad
    log("profile composition done")

    dn = day_noise(res["stage3_true_spread"])
    res["day_noise"] = dn
    res["posterior_uncertainty"] = posterior_uncertainty(f, dn)
    for t in TOURS:
        w = res["odds_weights"][t]
        for key in (f"{t}|no_day_noise", f"{t}|with_day_noise"):
            pu = res["posterior_uncertainty"][key]
            pu["mll_if_price_ignores"] = mll_relative(pu["rms_kappa"], w["E_wz2"])
        vol = {}
        for case in dn[t]["cases"]:
            if case["best_of"] != 3:
                continue
            c2 = case["c2_exact"]
            key = f"rho{case['rho_serve_return_day']}_cond{case['conditions_share']}"
            vol[key] = {f"cv{cv}": mll_relative(0.5 * (1 - c2) * cv, w["E_wz2"]) for cv in (0.1, 0.2, 0.3, 0.5)}
            vol[key]["c2"] = c2
            vol[key]["pair_dominance_mll_damped"] = pdm[t]["mll_if_price_ignores_pair_dominance"] * c2 ** 2
        res[f"volatility_{t}"] = vol
    log("day noise, volatility, posterior uncertainty done")

    res["devig"] = devig(f)
    for t in TOURS:
        o = res["devig"]["overround"][t]
        w = res["odds_weights"][t]
        for rule in ("power", "shin"):
            o[f"{rule}_mll_if_one_slope"] = mll_relative(o[f"{rule}_rms_kappa"], w["E_wz2"])
    log("de-vig done")

    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist")
                                                 else str(o)), encoding="utf-8")

    # ---- markdown tables for the ideas file
    tab = g["prob"]
    print("\n## dP/ds at fixed d (s = pA + pB), and the leverage dP/dd at d = 0\n")
    for name, _, _ in FORMATS:
        t_ = tab[tab.format == name][["m", "tiebreak_share", "beta_prob"] + [f"P_d{d:.2f}" for d in D_GRID]
                                     + [f"dPds_d{d:.2f}" for d in D_GRID]]
        print(f"\n### {name}\n")
        print(md(t_))
    print("\n## logit scale\n")
    print(md(g["logit"]))
    print("\n## deciding-set rules\n")
    print(md(g["final"], "{:.4f}"))
    print("\n## hold scale\n")
    print(md(g["hold"]))
    print("\n## results.json (abridged)\n")
    for k in ("verify", "odds_weights", "pair_dominance", "profile_composition", "posterior_uncertainty"):
        print(k, json.dumps(res[k], indent=1, default=str))
    print("second_order", json.dumps(res["second_order"], indent=1))
    print("day_noise", json.dumps(res["day_noise"], indent=1))
    for t in TOURS:
        print(f"volatility_{t}", json.dumps(res[f"volatility_{t}"], indent=1))
    print("devig overround", json.dumps(res["devig"]["overround"], indent=1), res["devig"]["joined_share"])
    print("avg vs pinnacle", json.dumps(res["devig"]["avg_vs_pinnacle"], indent=1))
    print(md(pd.DataFrame(res["devig"]["table"]).query("z_true in (1.0, 2.0)")))
    print("stage3_true_spread", json.dumps(res["stage3_true_spread"], indent=1))
    log("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
