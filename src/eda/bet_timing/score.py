"""Bet timing, step 3: what betting before the close does to the current best model's edge, and to the money.

Forecasts. Each fit's blocks are symmetrised (the mean of P(A | x) and 1 - P(A | x swapped)) and averaged over seeds
0-3; eta is the log-odds of that mean. The current best model's final forecast for season Y, the same rule for every
block (a bettor applies the decided rule to whatever the model says):
    2020-2023   expit(s_tour,Y eta): the decided calibration, one slope per tour fitted on the stored fits' td forecasts of
                2019 .. Y - 1, seeds 0-3, debut seasons out (serve_speed_tabpfn.score.Scorer.slopes)
    2024-2026   expit(s_tour,Y eta + b_Y spd_L): both stages with the coefficients in force (adaptive/coefficients.json,
                L_weekly; spd_L is 0 for women)
Prices: the margin-free P(A) the model was fed.

Populations. The frame's completed and retired matches (walkovers never reach it), debut seasons out. For an early block
and its venue's close: the matches with both prices whose inputs all existed at the early quote (known_<early>); every
priced match as a sensitivity. Money: completed matches only (a retirement voids the bet).

Measures. Log loss in milli-log-loss; intervals are paired cluster-t intervals over four-week blocks of tournament
dates (the project's convention); ratios use a bootstrap of the same blocks.
    E(t), E(c), S(t), A(t), and E(t) - E(c) = S(t) - A(t)     (common.py)
    inherited = A / S        the share of the early line's error the model inherits
    move: OLS of M = logit p_c - logit p_t on D_t = logit q_t - logit p_t, no intercept: the share of the model's
          disagreement at t that the market closes by the close
    sizing: logistic regression of the result on logit p_t and D_t, no intercept; D_t's coefficient is the realisation of
          the model's disagreement at t (1 right-sized; above 1 the model under-reacts; below 1 it over-reacts)
    resized: walk-forward, season Y's logit q = a logit p_t + b D_t with (a, b) fitted on the seasons before Y (BetOnline)
          or on the other four-week blocks (Polymarket); its gain on the plug-in (+ = resized better); the close is the
          control
    money: the owner's staking rule (to win 1 unit on favourites, d / (2 (d - 1)) on underdogs) on the side with the
          larger expected return when it exceeds the threshold, at BetOnline's opening line with the model fed the
          opening line, against the same at the last line. Realized return per unit staked; CLV, each bet's expected
          return if BetOnline's margin-free last line is the true chance; per 100 matches, paired. Polymarket: $1 at the
          ask (mid + half a cent) with the taker fee of the moment, as the line-sharpening study

Writes data/studies/bet_timing/results.json and the tables in results_*.csv. Reads the results (a_won) here only.
Run: ./python.sh src/eda/bet_timing/score.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402
from src.eda.bet_timing import fits as FT  # noqa: E402
from src.eda.tabpfn_thinking.common import fit_logistic, ll  # noqa: E402

TAUS = (0.0, 0.02, 0.05)
HALF_SPREAD, MAX_ASK = 0.005, 0.99
DRAWS = 2000
H_BINS = [0, 8, 16, 24, 48, np.inf]                      # hours before the listed start of BetOnline's opening line
P_CLIP = (0.005, 0.995)                                   # prices' clip before a logit in the move regression


def seed_of(*parts) -> int:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


# ------------------------------------------------------------------------------------------------
# Forecasts

def etas(seasons=C.SEASONS, seeds=C.SEEDS, price_set: str = "main", blocks=C.BLOCKS) -> pd.DataFrame:
    """match_id -> eta_<block>: the log-odds of the seed mean of the symmetrised forecasts (fits.py's price set)."""
    cols: dict[str, list[pd.Series]] = {b: [] for b in blocks}
    for season in seasons:
        files = [FT.fit_path(season, k, price_set) for k in seeds]
        missing = [f.name for f in files if not f.exists()]
        if missing:
            raise RuntimeError(f"fits missing: {missing}")
        zs = [np.load(f, allow_pickle=False) for f in files]
        try:
            for b in blocks:
                if f"p_{b}" not in zs[0].files:
                    continue
                ids = zs[0][f"ids_{b}"].astype(str)
                per = []
                for z in zs:
                    if not np.array_equal(z[f"ids_{b}"].astype(str), ids):
                        raise RuntimeError(f"{season} {b}: seeds hold different matches")
                    p, n = z[f"p_{b}"], len(ids)
                    per.append(0.5 * (p[:n] + 1.0 - p[n:]))
                cols[b].append(pd.Series(C.lg(np.mean(per, axis=0)), index=ids))
        finally:
            for z in zs:
                z.close()
    out = pd.DataFrame({f"eta_{b}": pd.concat(v) for b, v in cols.items() if v})
    out.index.name = "match_id"
    return out


def calibration(seasons) -> dict:
    """{season: {"s_atp", "s_wta", "b"}}: the decided slopes for 2020-2023 (Scorer.slopes, the stored fits' td forecasts
    of 2019 .. Y - 1) and the speed adjustment's coefficients for 2024-2026."""
    from src.eda.serve_speed_tabpfn import common as SC
    from src.eda.serve_speed_tabpfn import score as S
    coef = C.read_json(C.COEFFICIENTS)["L_weekly"]
    P = SC.DEFAULT
    sc = S.Scorer(S.Bank(P, S.frame_index(P), require_checks=True), S.population(P), S.labels(P))
    out = {}
    for y in seasons:
        if y in C.STAGE2_SEASONS:
            c = coef[str(y)]
            out[y] = {"s_atp": c["s_atp"], "s_wta": c["s_wta"], "b": c["b_shrunk"], "rule": "both stages"}
        else:
            s = sc.slopes("model", y)
            out[y] = {"s_atp": s["atp"], "s_wta": s["wta"], "b": 0.0, "rule": "decided calibration"}
    return out


def final(eta: np.ndarray, tour: np.ndarray, season: np.ndarray, spd: np.ndarray, cal: dict) -> np.ndarray:
    s = np.array([cal[int(y)]["s_atp" if t == "atp" else "s_wta"] for t, y in zip(tour, season)])
    b = np.array([cal[int(y)]["b"] for y in season])
    z = np.where(tour == "atp", spd, 0.0)
    return C.ex(s * eta + b * z)


def load(seasons=C.SEASONS) -> pd.DataFrame:
    x = pd.read_parquet(C.FRAME)
    x["match_id"] = x["match_id"].astype(str)
    x = x[x["season"].isin(seasons)].reset_index(drop=True)
    e = etas(seasons)
    x = x.join(e, on="match_id")
    cal = calibration(seasons)
    tour, season, spd = x["tour"].to_numpy(), x["season"].to_numpy(), x["spd_L"].to_numpy(float)
    for b in C.BLOCKS:
        if f"eta_{b}" in x:
            x[f"q_{b}"] = final(x[f"eta_{b}"].to_numpy(float), tour, season, spd, cal)
    y = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "a_won"])          # THE ONLY READER OF RESULTS
    y["match_id"] = y["match_id"].astype(str)
    x = x.merge(y, on="match_id", how="left", validate="one_to_one")
    x["y"] = x["a_won"].astype(float)
    x.attrs["calibration"] = cal
    return x


# ------------------------------------------------------------------------------------------------
# Statistics

def mean_ci(v: np.ndarray, clusters: np.ndarray, scale: float = 1000.0) -> dict:
    """Mean with a cluster-sandwich SE (G / (G - 1)) and t on G - 1 degrees of freedom, times scale."""
    v = np.asarray(v, float)
    labels, ix = np.unique(clusters, return_inverse=True)
    G, n = len(labels), len(v)
    m = float(v.mean())
    infl = np.bincount(ix, weights=v - m)
    se = float(np.sqrt(G / (G - 1) * infl @ infl) / n) if G > 1 else np.nan
    r = student_t.ppf(0.975, G - 1) * se if G > 1 else np.nan
    return {"est": scale * m, "lo": scale * (m - r), "hi": scale * (m + r), "n": int(n), "blocks": int(G)}


def ratio_boot(num: np.ndarray, den: np.ndarray, clusters: np.ndarray, seed: int) -> dict:
    """sum(num) / sum(den) with a 95% bootstrap interval over the clusters."""
    labels, ix = np.unique(clusters, return_inverse=True)
    sn, sd = np.bincount(ix, weights=num), np.bincount(ix, weights=den)
    rng = np.random.default_rng(seed)
    w = rng.multinomial(len(labels), np.full(len(labels), 1.0 / len(labels)), size=DRAWS).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = (w @ sn) / (w @ sd)
    lo, hi = np.nanpercentile(r, [2.5, 97.5])
    return {"est": float(sn.sum() / sd.sum()), "lo": float(lo), "hi": float(hi)}


def ols_cluster(y: np.ndarray, X: np.ndarray, clusters: np.ndarray) -> dict:
    """OLS without intercept, CR1 cluster-robust covariance, t on G - 1 (serve_speed_tabpfn.score.ols_cluster)."""
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    e = y - X @ beta
    labels, ix = np.unique(clusters, return_inverse=True)
    g = len(labels)
    S = np.zeros((g, k))
    np.add.at(S, ix, X * e[:, None])
    V = XtX_inv @ (S.T @ S) @ XtX_inv * (g / (g - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    tq = student_t.ppf(0.975, g - 1)
    return {"beta": beta.tolist(), "se": se.tolist(), "lo": (beta - tq * se).tolist(), "hi": (beta + tq * se).tolist(),
            "n": int(n), "clusters": int(g)}


def logit_cluster(Z: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> dict:
    """Logistic regression without intercept (the harness's Newton fit) with a cluster-sandwich covariance."""
    beta, _ = fit_logistic(Z, y)
    p = C.ex(Z @ beta)
    Hinv = np.linalg.inv((Z.T * (p * (1 - p))) @ Z)
    labels, ix = np.unique(clusters, return_inverse=True)
    g = len(labels)
    S = np.zeros((g, Z.shape[1]))
    np.add.at(S, ix, Z * (y - p)[:, None])
    V = Hinv @ (S.T @ S) @ Hinv * (g / (g - 1))
    se = np.sqrt(np.diag(V))
    tq = student_t.ppf(0.975, g - 1)
    return {"beta": beta.tolist(), "se": se.tolist(), "lo": (beta - tq * se).tolist(), "hi": (beta + tq * se).tolist(),
            "n": int(len(y)), "clusters": int(g)}


# ------------------------------------------------------------------------------------------------
# The decomposition, the move and the sizing

def population(x: pd.DataFrame, early: str, close: str, known: bool = True) -> np.ndarray:
    m = (~x["debut_season"].astype(bool)).to_numpy() & x["y"].notna().to_numpy()
    for b in (early, close):
        m &= np.isfinite(x[f"p_{b}"].to_numpy(float)) & np.isfinite(x[f"q_{b}"].to_numpy(float))
    if known:
        m &= x[f"known_{early}"].to_numpy(bool)
    return m


def recalibrated(p: np.ndarray, y: np.ndarray, blk: np.ndarray, tour: np.ndarray) -> np.ndarray:
    """The price recalibrated out of sample: one slope per tour on its log-odds (no intercept), fitted on the other
    four-week blocks (the project compares models with a recalibrated price; this is the sensitivity)."""
    z = C.lg(np.clip(p, *P_CLIP))
    out = np.full(len(p), np.nan)
    for k in np.unique(blk):
        for t in np.unique(tour):
            tr, te = (blk != k) & (tour == t), (blk == k) & (tour == t)
            if te.any():
                beta, _ = fit_logistic(z[tr][:, None], y[tr])
                out[te] = C.ex(beta[0] * z[te])
    return out


def decompose(x: pd.DataFrame, early: str, close: str, mask: np.ndarray, label: str) -> dict:
    g = x[mask]
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    L = {k: ll(g[k].to_numpy(float), y) for k in (f"p_{early}", f"p_{close}", f"q_{early}", f"q_{close}")}
    pe, pc, qe, qc = (L[f"p_{early}"], L[f"p_{close}"], L[f"q_{early}"], L[f"q_{close}"])
    tour = g["tour"].to_numpy() if "tour" in g else np.zeros(len(g))
    pe_r = ll(recalibrated(g[f"p_{early}"].to_numpy(float), y, blk, tour), y)
    pc_r = ll(recalibrated(g[f"p_{close}"].to_numpy(float), y, blk, tour), y)
    hours = (float(g["h_bol_open"].median()) if early == "bol_open" else C.PM_HORIZONS.get(early, np.nan) / 60.0)
    out = {"label": label, "early": early, "close": close, "matches": int(mask.sum()), "early_hours_median": hours,
           "log_loss": {"price_early": float(pe.mean()), "price_close": float(pc.mean()),
                        "model_early": float(qe.mean()), "model_close": float(qc.mean())},
           "E_early": mean_ci(pe - qe, blk), "E_close": mean_ci(pc - qc, blk),
           "S_softness": mean_ci(pe - pc, blk), "A_model_loss": mean_ci(qe - qc, blk),
           "net_E_early_minus_E_close": mean_ci((pe - qe) - (pc - qc), blk),
           "model_early_vs_price_close": mean_ci(pc - qe, blk),
           "inherited_share": ratio_boot(qe - qc, pe - pc, blk, seed_of(label, early, "inherit")),
           "recalibrated_prices": {"E_early": mean_ci(pe_r - qe, blk), "E_close": mean_ci(pc_r - qc, blk),
                                   "S_softness": mean_ci(pe_r - pc_r, blk),
                                   "net_E_early_minus_E_close": mean_ci((pe_r - qe) - (pc_r - qc), blk)}}
    if "q_td" in g and np.isfinite(g["q_td"]).all():
        Ltd = ll(g["p_td"].to_numpy(float), y) - ll(g["q_td"].to_numpy(float), y)
        out["E_average_close_td"] = mean_ci(Ltd, blk)
    lp_e = C.lg(np.clip(g[f"p_{early}"], *P_CLIP))
    lp_c = C.lg(np.clip(g[f"p_{close}"], *P_CLIP))
    D_e = C.lg(g[f"q_{early}"]) - lp_e
    D_c = C.lg(g[f"q_{close}"]) - lp_c
    out["move_toward_model"] = ols_cluster(lp_c - lp_e, D_e[:, None], blk)
    out["move_sd_logit"], out["disagreement_sd_logit"] = float(np.std(lp_c - lp_e)), float(np.std(D_e))
    out["sizing_early"] = logit_cluster(np.column_stack([lp_e, D_e]), y, blk)
    out["sizing_close"] = logit_cluster(np.column_stack([lp_c, D_c]), y, blk)
    return out


def resized(x: pd.DataFrame, early: str, close: str, mask: np.ndarray, scheme: str) -> dict:
    """Out-of-sample re-sizing of the plug-in at each moment: logit q = a logit p + b D, fitted walk-forward by season
    (scheme "season", from the second season with data) or on the other four-week blocks ("block")."""
    out = {"scheme": scheme}
    g = x[mask].reset_index(drop=True)
    y, blk, season = g["y"].to_numpy(float), g["block"].to_numpy(), g["season"].to_numpy()
    for b in (early, close):
        lp = C.lg(np.clip(g[f"p_{b}"], *P_CLIP))
        Z = np.column_stack([lp, C.lg(g[f"q_{b}"]) - lp])
        q_new = np.full(len(g), np.nan)
        coefs = {}
        if scheme == "season":
            for s in sorted(set(season))[1:]:
                tr, te = season < s, season == s
                beta, _ = fit_logistic(Z[tr], y[tr])
                q_new[te] = C.ex(Z[te] @ beta)
                coefs[int(s)] = [round(float(v), 4) for v in beta]
        else:
            for k in np.unique(blk):
                tr, te = blk != k, blk == k
                beta, _ = fit_logistic(Z[tr], y[tr])
                q_new[te] = C.ex(Z[te] @ beta)
        ok = np.isfinite(q_new)
        gain = ll(g[f"q_{b}"].to_numpy(float)[ok], y[ok]) - ll(q_new[ok], y[ok])
        out[b] = {"gain_resized_over_plugin": mean_ci(gain, blk[ok]), "coefficients_by_season": coefs or None}
    return out


# ------------------------------------------------------------------------------------------------
# Money

def back(q: np.ndarray, d_a: np.ndarray, d_b: np.ndarray, tau: float):
    """Side (1 = A, 0 = B, -1 = no bet) with the larger expected return q d - 1, if above tau."""
    ev_a, ev_b = q * d_a - 1.0, (1.0 - q) * d_b - 1.0
    side = np.where(ev_a >= ev_b, 1, 0)
    ev = np.where(side == 1, ev_a, ev_b)
    side = np.where(np.isfinite(ev) & (ev > tau), side, -1)
    return side, np.where(side == 1, d_a, d_b), ev


def book_bets(g: pd.DataFrame, block: str, tau: float, q_col: str | None = None) -> pd.DataFrame:
    """The owner's staking at a BetOnline line, with the model fed that line (or the forecast in q_col); CLV against
    BetOnline's margin-free last line."""
    side, d, ev = back(g[q_col or f"q_{block}"].to_numpy(float), g[f"{block}_a"].to_numpy(float),
                       g[f"{block}_b"].to_numpy(float), tau)
    bet = side >= 0
    stake = np.where(bet, C.stake(np.where(bet, d, 2.0)), 0.0)
    won = np.where(side == 1, g["y"].to_numpy(), 1.0 - g["y"].to_numpy())
    pc = np.where(side == 1, g["p_bol_close"].to_numpy(float), 1.0 - g["p_bol_close"].to_numpy(float))
    pt = np.where(side == 1, g[f"p_{block}"].to_numpy(float), 1.0 - g[f"p_{block}"].to_numpy(float))
    return pd.DataFrame({"bet": bet, "stake": stake, "profit": np.where(bet, stake * (won * d - 1.0), 0.0),
                         "clv": np.where(bet, stake * (pc * d - 1.0), 0.0),
                         "fair": np.where(bet, stake * (pt * d - 1.0), 0.0), "ev": np.where(bet, ev, np.nan),
                         "fav": bet & (pt >= 0.5)})


def money_summary(s: pd.DataFrame, blk: np.ndarray, label: str) -> dict:
    n = len(s)
    return {"bets": int(s["bet"].sum()), "matches": int(n), "staked": float(s["stake"].sum()),
            "profit_units": float(s["profit"].sum()),
            "roi": ratio_boot(s["profit"].to_numpy(), s["stake"].to_numpy(), blk, seed_of(label, "roi")),
            "clv_roi": ratio_boot(s["clv"].to_numpy(), s["stake"].to_numpy(), blk, seed_of(label, "clv")),
            "fair_roi": float(s["fair"].sum() / s["stake"].sum()) if s["stake"].sum() > 0 else None,
            "claimed_ev": float(np.nanmean(s["ev"])) if s["bet"].any() else None,
            "profit_per_100": mean_ci(s["profit"].to_numpy(), blk, 100.0),
            "clv_per_100": mean_ci(s["clv"].to_numpy(), blk, 100.0)}


def money_betonline(x: pd.DataFrame, mask: np.ndarray, label: str) -> dict:
    g = x[mask & x["status"].eq("completed").to_numpy()].reset_index(drop=True)
    for kind in ("open", "close"):
        g[f"bol_{kind}_a"], g[f"bol_{kind}_b"] = g[f"bol_{kind}_a"].astype(float), g[f"bol_{kind}_b"].astype(float)
    blk = g["block"].to_numpy()
    out = {"label": label, "matches": int(len(g))}
    for tau in TAUS:
        so, sc = book_bets(g, "bol_open", tau), book_bets(g, "bol_close", tau)
        out[f"tau_{tau}"] = {
            "open": money_summary(so, blk, f"{label}|{tau}|open"),
            "close": money_summary(sc, blk, f"{label}|{tau}|close"),
            "open_minus_close_profit_per_100": mean_ci(so["profit"].to_numpy() - sc["profit"].to_numpy(), blk, 100.0),
            "open_minus_close_clv_per_100": mean_ci(so["clv"].to_numpy() - sc["clv"].to_numpy(), blk, 100.0),
            "open_favourites_clv_roi": ratio_boot(so["clv"].where(so["fav"], 0).to_numpy(),
                                                  so["stake"].where(so["fav"], 0).to_numpy(), blk,
                                                  seed_of(label, tau, "favclv")) if so["fav"].any() else None,
            "open_underdogs_clv_roi": ratio_boot(so["clv"].where(so["bet"] & ~so["fav"], 0).to_numpy(),
                                                 so["stake"].where(so["bet"] & ~so["fav"], 0).to_numpy(), blk,
                                                 seed_of(label, tau, "dogclv")) if (so["bet"] & ~so["fav"]).any()
            else None}
    return out


def pm_bets(g: pd.DataFrame, block: str, tau: float, close: str = "pm_m30", q_col: str | None = None) -> pd.DataFrame:
    """$1 at the ask with the fee of the moment (line_sharpening.timing_bets.decide), with the model fed that price (or
    the forecast in q_col); CLV against the 30-minute mid."""
    q, p = g[q_col or f"q_{block}"].to_numpy(float), g[f"p_{block}"].to_numpy(float)
    fee = g[f"fee_{block}"].to_numpy(float)
    ask_a, ask_b = np.minimum(p + HALF_SPREAD, MAX_ASK), np.minimum(1 - p + HALF_SPREAD, MAX_ASK)
    fa, fb = fee * (1 - ask_a), fee * (1 - ask_b)
    ev_a, ev_b = q / ask_a - 1 - fa, (1 - q) / ask_b - 1 - fb
    side = np.where(ev_a >= ev_b, 1, 0)
    ev = np.where(side == 1, ev_a, ev_b)
    bet = np.isfinite(ev) & (ev > tau)
    ask, f = np.where(side == 1, ask_a, ask_b), np.where(side == 1, fa, fb)
    won = np.where(side == 1, g["y"].to_numpy(), 1 - g["y"].to_numpy())
    pc = np.where(side == 1, g[f"p_{close}"].to_numpy(float), 1 - g[f"p_{close}"].to_numpy(float))
    pt = np.where(side == 1, p, 1 - p)
    return pd.DataFrame({"bet": bet, "stake": bet.astype(float), "profit": np.where(bet, won / ask - 1 - f, 0.0),
                         "clv": np.where(bet, pc / ask - 1 - f, 0.0), "fair": np.where(bet, pt / ask - 1 - f, 0.0),
                         "ev": np.where(bet, ev, np.nan), "fav": bet & (pt >= 0.5)})


def money_polymarket(x: pd.DataFrame, early: str, mask: np.ndarray, label: str) -> dict:
    g = x[mask & x["status"].eq("completed").to_numpy()].reset_index(drop=True)
    blk = g["block"].to_numpy()
    out = {"label": label, "early": early, "matches": int(len(g))}
    for tau in (0.0, 0.02):
        se, sc = pm_bets(g, early, tau), pm_bets(g, "pm_m30", tau)
        out[f"tau_{tau}"] = {"early": money_summary(se, blk, f"{label}|{tau}|{early}"),
                             "close": money_summary(sc, blk, f"{label}|{tau}|pm_m30"),
                             "early_minus_close_profit_per_100": mean_ci(se["profit"].to_numpy() -
                                                                         sc["profit"].to_numpy(), blk, 100.0),
                             "early_minus_close_clv_per_100": mean_ci(se["clv"].to_numpy() - sc["clv"].to_numpy(),
                                                                      blk, 100.0)}
    return out


def venues(x: pd.DataFrame) -> dict:
    """The two venues on the same matches (2025-2026: both priced, inputs known at BetOnline's opening and at
    Polymarket's 24-hour quote): which price is sharper, and the model's edge over each."""
    m = (~x["debut_season"].astype(bool) & x["y"].notna() & x["known_bol_open"] & x["known_pm_h24"]).to_numpy().copy()
    for b in ("bol_open", "bol_close", "pm_h24", "pm_m30", "td"):
        m &= np.isfinite(x[f"p_{b}"].to_numpy(float)) & np.isfinite(x[f"q_{b}"].to_numpy(float))
    g = x[m]
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    L = {f"{k}_{b}": ll(g[f"{k}_{b}"].to_numpy(float), y) for k in ("p", "q")
         for b in ("bol_open", "bol_close", "pm_h24", "pm_m30", "td")}
    return {"matches": int(m.sum()), "bol_open_hours_median": float(g["h_bol_open"].median()),
            "betonline_close_minus_polymarket_close": mean_ci(L["p_bol_close"] - L["p_pm_m30"], blk),
            "betonline_open_minus_polymarket_24h": mean_ci(L["p_bol_open"] - L["p_pm_h24"], blk),
            **{f"E_{b}": mean_ci(L[f"p_{b}"] - L[f"q_{b}"], blk)
               for b in ("bol_open", "bol_close", "pm_h24", "pm_m30", "td")},
            "keys": "price differences: + = the second-named price sharper; E: + = the model better than that price"}


# ------------------------------------------------------------------------------------------------
# Run

def strata(x: pd.DataFrame, mask: np.ndarray) -> dict[str, np.ndarray]:
    level = x["level"].to_numpy()
    h = x["h_bol_open"].to_numpy(float)
    out = {"all": mask, "men": mask & (x["tour"] == "atp").to_numpy(), "women": mask & (x["tour"] == "wta").to_numpy(),
           "slams_and_1000s": mask & np.isin(level, [0, 1, 2]), "500s_and_250s": mask & np.isin(level, [3, 4]),
           "openers": mask & x["opener"].to_numpy(bool), "later_rounds": mask & ~x["opener"].to_numpy(bool),
           "2020-2024": mask & (x["season"] <= 2024).to_numpy(), "2025-2026": mask & (x["season"] >= 2025).to_numpy()}
    for s in sorted(x["season"].unique()):
        out[f"season_{s}"] = mask & (x["season"] == s).to_numpy()
    for lo, hi in zip(H_BINS[:-1], H_BINS[1:]):
        out[f"open_{lo}-{hi}h"] = mask & (h > lo) & (h <= hi)
    return out


def flat(rows: list[dict]) -> pd.DataFrame:
    recs = []
    for r in rows:
        rec = {"label": r["label"], "early": r["early"], "matches": r["matches"]}
        for k in ("E_early", "E_close", "S_softness", "A_model_loss", "net_E_early_minus_E_close",
                  "model_early_vs_price_close", "E_average_close_td"):
            if k in r:
                rec.update({f"{k}": round(r[k]["est"], 3), f"{k}_lo": round(r[k]["lo"], 3),
                            f"{k}_hi": round(r[k]["hi"], 3)})
        rec["inherited_share"] = round(r["inherited_share"]["est"], 3)
        rec["inherited_lo"], rec["inherited_hi"] = (round(r["inherited_share"]["lo"], 3),
                                                    round(r["inherited_share"]["hi"], 3))
        mv = r["move_toward_model"]
        rec["move_slope"], rec["move_lo"], rec["move_hi"] = (round(mv["beta"][0], 3), round(mv["lo"][0], 3),
                                                             round(mv["hi"][0], 3))
        for t in ("early", "close"):
            sz = r[f"sizing_{t}"]
            rec[f"realisation_{t}"] = round(sz["beta"][1], 3)
            rec[f"realisation_{t}_lo"], rec[f"realisation_{t}_hi"] = round(sz["lo"][1], 3), round(sz["hi"][1], 3)
            rec[f"price_slope_{t}"] = round(sz["beta"][0], 3)
        recs.append(rec)
    return pd.DataFrame(recs)


def main() -> int:
    args = sys.argv[1:]
    seasons = C.SEASONS
    if "--seasons" in args:                     # a partial run (e.g. before every season's fits exist): its own files
        a, _, b = args[args.index("--seasons") + 1].partition("-")
        seasons = tuple(range(int(a), int(b) + 1))
    suffix = "" if seasons == C.SEASONS else f"_{min(seasons)}_{max(seasons)}"
    x = load(seasons)
    res = {"seasons": list(seasons), "calibration": {str(k): v for k, v in x.attrs["calibration"].items()},
           "decomposition": [], "resized": [], "money_betonline": [], "money_polymarket": []}
    # BetOnline: opening line against the last line, every stratum; the primary population is "known"
    for known in (True, False):
        base = population(x, "bol_open", "bol_close", known)
        tag = "known" if known else "all_priced"
        for name, m in strata(x, base).items():
            if m.sum() >= 300:
                res["decomposition"].append(decompose(x, "bol_open", "bol_close", m, f"betonline|{tag}|{name}"))
        res["resized"].append({"label": f"betonline|{tag}", **resized(x, "bol_open", "bol_close", base, "season")})
        res["resized"].append({"label": f"betonline|{tag}|blocks",
                               **resized(x, "bol_open", "bol_close", base, "block")})
        res["money_betonline"].append(money_betonline(x, base, f"betonline|{tag}"))
        if known:
            for name in ("men", "women", "2020-2024", "2025-2026"):
                res["money_betonline"].append(money_betonline(x, strata(x, base)[name], f"betonline|{tag}|{name}"))
    # Polymarket: each horizon against the 30-minute price
    for early in [b for b in C.PM_HORIZONS if b != "pm_m30"]:
        for known in (True, False):
            base = population(x, early, "pm_m30", known)
            tag = "known" if known else "all_priced"
            if base.sum() < 300:
                continue
            res["decomposition"].append(decompose(x, early, "pm_m30", base, f"polymarket|{tag}|all"))
            if known:
                for name in ("men", "women", "slams_and_1000s", "500s_and_250s", "openers", "later_rounds"):
                    m = strata(x, base)[name]
                    if m.sum() >= 300:
                        res["decomposition"].append(decompose(x, early, "pm_m30", m, f"polymarket|{tag}|{name}"))
                res["resized"].append({"label": f"polymarket|{tag}|{early}|blocks",
                                       **resized(x, early, "pm_m30", base, "block")})
                res["money_polymarket"].append(money_polymarket(x, early, base, f"polymarket|{tag}"))
    # a common panel: the matches priced at 24, 12, 6, 3 and 1 hours, known at 24 hours
    panel = population(x, "pm_h24", "pm_m30", True)
    for b in ("pm_h12", "pm_h6", "pm_h3", "pm_h1"):
        panel &= np.isfinite(x[f"p_{b}"].to_numpy(float))
    res["polymarket_panel"] = [decompose(x, b, "pm_m30", panel, "polymarket|panel_24h")
                               for b in ("pm_h24", "pm_h12", "pm_h6", "pm_h3", "pm_h1")] if panel.sum() >= 300 else []
    res["venues_same_matches"] = venues(x)
    table = flat(res["decomposition"] + res["polymarket_panel"])
    table.to_csv(C.OUT / f"results_decomposition{suffix}.csv", index=False)
    C.write_json(C.OUT / f"results{suffix}.json", res)
    with pd.option_context("display.width", 250, "display.max_columns", 40):
        print(table[["label", "early", "matches", "E_early", "E_close", "S_softness", "A_model_loss",
                     "net_E_early_minus_E_close", "net_E_early_minus_E_close_lo", "net_E_early_minus_E_close_hi",
                     "inherited_share", "move_slope", "realisation_early", "realisation_close"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
