"""Block B5, the pair's volatility flattens the price (I-028, I-029): price-slope members, s * eta (x_times_eta); a
signed-sum of the two symmetric modulators, each divided by its 2014-2021 SD, both declared negative (folded into the
sum, so the block's sign is +). Weight by the audit's rule from the result-free pair-CV precheck (pair_cv_precheck).

I-029 (-)  s = V_pair / Vbar_c - 1, V_pair = sigma2_A + sigma2_B, sigma2_P = the player's long-memory mean of per-match
           excess squared residuals: x_j = ((u_s^2 - 1/(n_s p_s (1 - p_s))) + (u_r^2 - 1/(n_r p_r (1 - p_r)))) / 2, u_s the
           serve-point logit residual against the surface IOS expectation mu + O_P - D_opp (pre-match, leak-proof), u_r the
           return-side residual (the opponent's serve residual, negated). sigma2_P = (sum_j w_j x_j + K m_t) / (sum_j w_j
           + K), w_j = 2^(-(es - lf_j) / 728 days) over matches released (lf + 1) by the target's es (the clock: the
           residuals use the opponent's ratings), m_t the tour's 2010-2018 mean of x. Vbar_c = the tour x surface mean of
           V_pair on 2014-2021 rows.
I-028 (-)  s = K_pair - Kbar_c, K_pair = kappa_A + kappa_B, kappa_P = the same long-memory shrunk mean of the per-match
           excess variance of P's per-set games share: y_j = s^2_j (the sample variance over the match's sets) minus
           Var_iid(g; h_P, h_O), the iid model's variance of a set's games share at the match's own hold rates h = game(p),
           p = each player's serve-point share in the match (Stage 0 box score), tiebreak sets from the same rates. Sets
           of more than 13 games (advantage deciding sets) drop the match. Own history (safe); the clock is used anyway.
Controls: the M-set and the nearest inputs to s * eta; no s * eta control (the math audit's finding 1).
Constants: half-life 104 weeks (the long end of the IOS memory, fixed in advance), K by method of moments on 2010-2018
player totals (statistics only; eb_constants). Probe-equivalent: probe_check on both measures. Reads no result.
Run (diagnostics, precheck, probe): ./python.sh src/eda/feature_interactions/features/f06_volatility.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402
from src.eda.feature_interactions.history import SET_RE  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as IID  # noqa: E402

HALF_LIFE_DAYS = 728.0
TAU = HALF_LIFE_DAYS / np.log(2.0)
# method-of-moments constants (2010-2018 player totals; eb_constants), in matches, and the tours' mean excesses
# (eb_constants, 2010-2018 pool matches with box scores, players with 10+ matches): I-029 within-player variance per
# match 0.0264 / 0.0241, tau^2 0.00103 / 0.00054; I-028 tau^2 2.8e-6 (men) and below 0 (women: K capped at 10,000)
CONST = {"I-029": {"K": {"atp": 25.7, "wta": 45.0}, "m": {"atp": 0.0715, "wta": 0.0710}},
         "I-028": {"K": {"atp": 266.0, "wta": 10000.0}, "m": {"atp": -0.000128, "wta": -0.000381}}}
# B5 dissolved (final family; rulings "The B5 precheck"): pair_cv_precheck on I-029 gives split-half r 0.279 (men, 508
# players with 50+ matches a half) and 0.225 (women, 197), below the 0.3 gate, and a de-noised pair CV of 0.113 / 0.091
# (0.31 / 0.23 if the mean own day variance is taken as half the serve-x-return cross-product, 0.048 / 0.052): below 0.2
# on the plain reading. I-028 moved to B6 (f13_uncertainty) "if its gate passes": its split-half r is 0.011 (men) and
# 0.154 (women), below 0.3, so it fails too. No hypothesis is registered here; the measures stay importable.
HYPOTHESES: list = []
STAT_COLS = ["spw_n", "spw_d", "rpw_n", "rpw_d", "ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms",
             "bp_saved", "bp_faced", "tpw_n", "tpw_d"]


def serve_return_excess(L: pd.DataFrame) -> np.ndarray:
    """x_j per history row (NaN where the box score or either player's surface IOS is missing)."""
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    H = S.history_ios(L, ["srf_O_eff_spw", "srf_D_eff_spw"])
    m = S.mu(L, "spw", tour, surf)
    out = []
    for n, d, off in ((S.num(L, "spw_n"), S.num(L, "spw_d"), m + H[("own", "srf_O_eff_spw")] - H[("opp", "srf_D_eff_spw")]),
                      (S.num(L, "rpw_d") - S.num(L, "rpw_n"), S.num(L, "rpw_d"),
                       m + H[("opp", "srf_O_eff_spw")] - H[("own", "srf_D_eff_spw")])):
        p = expit(off)
        u = S.lg((n + 0.5) / (d + 1)) - off
        out.append(np.where((d >= 10) & np.isfinite(u), u * u - 1.0 / (d * p * (1 - p)), np.nan))
    ok = (L["status"].astype(str).to_numpy() == "completed") if "status" in L else np.ones(len(L), bool)
    return np.where(ok, 0.5 * (out[0] + out[1]), np.nan)


def _set_dist(ha, hb, pa, pb, a_first: bool) -> dict:
    """P(final set score (i, j)) for A against B with hold rates ha, hb (tiebreak at 6-6 from the point rates)."""
    tb = IID.tiebreak(pa, pb, 7, a_first=a_first)          # game 13 is served by the set's first server
    dist, layer = {}, {(0, 0): np.ones_like(ha)}
    while layer:
        nxt = {}
        for (i, j), r in layer.items():
            if i == 6 and j == 6:
                dist[(7, 6)] = dist.get((7, 6), 0) + r * tb
                dist[(6, 7)] = dist.get((6, 7), 0) + r * (1 - tb)
                continue
            a_serves = ((i + j) % 2 == 0) == a_first
            w = ha if a_serves else 1 - hb
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                if max(ni, nj) >= 6 and abs(ni - nj) >= 2:
                    dist[(ni, nj)] = dist.get((ni, nj), 0) + r * pr
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0) + r * pr
        layer = nxt
    return dist


def var_iid_share(pa, pb) -> np.ndarray:
    """Var of a set's games share for A under iid at serve-point rates pa, pb (both first servers averaged)."""
    pa, pb = np.clip(np.asarray(pa, float), 0.05, 0.95), np.clip(np.asarray(pb, float), 0.05, 0.95)
    ha, hb = IID.game(pa), IID.game(pb)
    m1 = m2 = 0.0
    for first in (True, False):
        for (i, j), pr in _set_dist(ha, hb, pa, pb, first).items():
            g = i / (i + j)
            m1 = m1 + 0.5 * pr * g
            m2 = m2 + 0.5 * pr * g * g
    return m2 - m1 * m1


def set_share_excess(L: pd.DataFrame) -> np.ndarray:
    """y_j per history row: the sample variance of the row player's per-set games share over the match's sets minus the
    iid variance at the match's own serve-point rates (completed matches with 2+ sets of at most 13 games)."""
    won = L["won"].astype(bool).to_numpy()
    shares, ok = [], np.zeros(len(L), bool)
    var = np.full(len(L), np.nan)
    for i, (sc, w) in enumerate(zip(L["score"].to_numpy(), won)):
        if not isinstance(sc, str):
            continue
        g = []
        for a, b, _ in SET_RE.findall(sc):
            a, b = int(a), int(b)
            if a + b > 13 or a + b == 0:
                g = None
                break
            g.append(a / (a + b) if w else b / (a + b))
        if g and len(g) >= 2:
            var[i] = float(np.var(g, ddof=1))
    p_own = S.num(L, "spw_n") / S.num(L, "spw_d")
    p_opp = (S.num(L, "rpw_d") - S.num(L, "rpw_n")) / S.num(L, "rpw_d")
    good = np.isfinite(var) & np.isfinite(p_own) & np.isfinite(p_opp) & (S.num(L, "spw_d") >= 20) \
        & (L["status"].astype(str).to_numpy() == "completed")
    out = np.full(len(L), np.nan)
    out[good] = var[good] - var_iid_share(p_own[good], p_opp[good])
    return out


def eb_constants(L: pd.DataFrame, x: np.ndarray, years=(2010, 2018)) -> dict:
    """Per tour: the mean excess m, the within-player variance per match and the between-player variance tau^2 of the
    players' true mean (method of moments), K = within / tau^2 in matches."""
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    out = {}
    for t in ("atp", "wta"):
        k = (yr >= years[0]) & (yr <= years[1]) & (L["tour"].astype(str).to_numpy() == t) & np.isfinite(x)
        df = pd.DataFrame({"p": L["player_id"].astype(str).to_numpy()[k], "x": x[k]})
        g = df.groupby("p")["x"].agg(["mean", "var", "size"])
        g = g[g["size"] >= 10]
        within = float(np.average(g["var"], weights=g["size"] - 1))
        between = float(np.var(g["mean"]))
        tau2 = between - float(np.mean(within / g["size"]))
        out[t] = {"m": float(df["x"].mean()), "within": within, "tau2": tau2,
                  "K": float(within / tau2) if tau2 > 0 else float("inf"), "players": int(len(g))}
    return out


def player_state(P: pd.DataFrame, L: pd.DataFrame, x: np.ndarray, key: str) -> tuple[np.ndarray, np.ndarray]:
    """The long-memory shrunk mean of x for side A and side B of every panel match, on the clock (released lf + 1 by
    the match's es), decayed with the 104-week half-life, shrunk with K towards the tour's mean m."""
    ok = np.isfinite(x)
    ids = pd.Index(pd.unique(np.r_[L["player_id"].astype(str).to_numpy(), P["player_a_id"].astype(str).to_numpy(),
                                   P["player_b_id"].astype(str).to_numpy()]))
    src = ids.get_indexer(L["player_id"].astype(str).to_numpy()[ok])
    rel = S.num(L, "lf")[ok] + 1.0
    V = np.column_stack([x[ok], np.ones(ok.sum())])
    K = P["tour"].astype(str).map(CONST[key]["K"]).to_numpy(dtype=float)
    m = P["tour"].astype(str).map(CONST[key]["m"]).to_numpy(dtype=float)
    out = []
    for col in ("player_a_id", "player_b_id"):
        sm = S.clock_sum(src, rel, V, ids.get_indexer(P[col].astype(str)), S.num(P, "es"), tau=TAU)
        out.append((sm[:, 0] + K * m) / (sm[:, 1] + K))
    return out[0], out[1]


def pair_cv_precheck(L: pd.DataFrame, x: np.ndarray, years=(2010, 2018), min_half: int = 50) -> dict:
    """The audit's rule for B5's weight (result-free): per player, matches alternated by own order into two halves
    (2010-2018); the split-half correlation of the halves' mean excess (players with 50+ matches a half); the de-noised
    between-player variance = the covariance of the two halves; per-player CV = its root over the mean excess; the pair
    CV = per-player CV / sqrt 2 (independent players)."""
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    out = {}
    for t in ("atp", "wta"):
        k = (yr >= years[0]) & (yr <= years[1]) & (L["tour"].astype(str).to_numpy() == t) & np.isfinite(x)
        df = pd.DataFrame({"p": L["player_id"].astype(str).to_numpy()[k], "k": L["k"].to_numpy()[k], "x": x[k]})
        df = df.sort_values(["p", "k"])
        df["half"] = df.groupby("p").cumcount() % 2
        g = df.groupby(["p", "half"])["x"].agg(["mean", "size"]).unstack()
        g = g[(g[("size", 0)] >= min_half) & (g[("size", 1)] >= min_half)]
        h0, h1 = g[("mean", 0)].to_numpy(), g[("mean", 1)].to_numpy()
        cov = float(np.cov(h0, h1)[0, 1])
        mean = float(np.mean(np.r_[h0, h1]))
        cv = float(np.sqrt(max(cov, 0.0)) / mean) if mean > 0 else float("nan")
        out[t] = {"players": int(len(g)), "split_half_r": float(np.corrcoef(h0, h1)[0, 1]), "mean": mean,
                  "true_between_sd": float(np.sqrt(max(cov, 0.0))), "cv_player": cv, "cv_pair": cv / np.sqrt(2)}
    return out


def weight_rule(pre: dict) -> tuple[float, str]:
    """The audit's fixed rule: pair CV >= 0.3 with split-half >= 0.3 -> 2; CV 0.2-0.3 -> 1; else dropped (0)."""
    cv = min(v["cv_pair"] for v in pre.values())
    r = min(v["split_half_r"] for v in pre.values())
    cv_pooled = float(np.average([v["cv_pair"] for v in pre.values()], weights=[v["players"] for v in pre.values()]))
    r_pooled = float(np.average([v["split_half_r"] for v in pre.values()], weights=[v["players"] for v in pre.values()]))
    note = f"pair CV min {cv:.3f} / pooled {cv_pooled:.3f}; split-half min {r:.3f} / pooled {r_pooled:.3f}"
    if r_pooled < 0.3 or cv_pooled < 0.2:
        return 0.0, note
    return (2.0 if cv_pooled >= 0.3 else 1.0), note


def cross_product_mean(L: pd.DataFrame, years=(2010, 2018)) -> dict:
    """The mean of u_s * u_r (serve residual times return residual of the same player and match): if one day form
    moves a player's serve and return together, its expectation is sigma2_A + sigma2_B, free of the binomial part and
    (nearly) of rating error; half of it is the mean own day variance. For the CV's denominator (information)."""
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    H = S.history_ios(L, ["srf_O_eff_spw", "srf_D_eff_spw"])
    m = S.mu(L, "spw", tour, surf)
    n, d = S.num(L, "spw_n"), S.num(L, "spw_d")
    rn, rd = S.num(L, "rpw_d") - S.num(L, "rpw_n"), S.num(L, "rpw_d")
    us = S.lg((n + 0.5) / (d + 1)) - (m + H[("own", "srf_O_eff_spw")] - H[("opp", "srf_D_eff_spw")])
    ur = -(S.lg((rn + 0.5) / (rd + 1)) - (m + H[("opp", "srf_O_eff_spw")] - H[("own", "srf_D_eff_spw")]))
    ok = (yr >= years[0]) & (yr <= years[1]) & np.isfinite(us) & np.isfinite(ur) & (d >= 10) & (rd >= 10)
    return {t: float(np.mean((us * ur)[ok & (tour == t)])) for t in ("atp", "wta")}


def prepare_volatility(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Per-player long-memory states of both measures (f06_s29_a/_b, f06_k28_a/_b), for B6 or a restored B5."""
    L = S.cut_history(L, P)
    s29a, s29b = player_state(P, L, serve_return_excess(L), "I-029")
    k28a, k28b = player_state(P, L, set_share_excess(L), "I-028")
    return {"f06_s29_a": s29a, "f06_s29_b": s29b, "f06_k28_a": k28a, "f06_k28_b": k28b}


def i029_modulator(P: pd.DataFrame) -> np.ndarray:
    v = S.num(P, "f06_s29_a") + S.num(P, "f06_s29_b")
    d, k = S.disc(P), S.cell_keys(P)
    cm = pd.Series(k).map(pd.Series(v[d]).groupby(k[d]).mean()).to_numpy(dtype=float)
    return v / cm - 1.0


def i028_modulator(P: pd.DataFrame) -> np.ndarray:
    """K_pair - Kbar_c (centred within tour x surface on 2014-2021 rows): I-028's s for B6's s * eta."""
    return S.centre_disc(P, S.num(P, "f06_k28_a") + S.num(P, "f06_k28_b"))


def probe(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Probe-equivalent for I-029's clock-built state (residuals use the opponent's ratings): results of matches that
    surely started after each cut day reversed; no panel match starting by the cut may move."""
    L = S.cut_history(L, P)

    def build(LL):
        a, b = player_state(P, LL, serve_return_excess(LL), "I-029")
        return np.column_stack([a, b])
    return S.probe_check(build, L, P, STAT_COLS)


def diagnostics(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    Lc = S.cut_history(L, P)
    x29, x28 = serve_return_excess(Lc), set_share_excess(Lc)
    return {"eb_I-029": eb_constants(Lc, x29), "eb_I-028": eb_constants(Lc, x28),
            "pair_cv_I-029": pair_cv_precheck(Lc, x29), "rule_I-029": weight_rule(pair_cv_precheck(Lc, x29)),
            "split_half_I-028": pair_cv_precheck(Lc, x28), "cross_product_mean": cross_product_mean(Lc),
            "coverage_rows": {"x29": float(np.isfinite(x29).mean()), "x28": float(np.isfinite(x28).mean())},
            "probe_I-029": probe(P, L)}


if __name__ == "__main__":
    import json
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)
    res = diagnostics(P, long_table())
    print(S.write_diag("f06_volatility", res))
    print(json.dumps(res, indent=1, default=str)[:4000])
