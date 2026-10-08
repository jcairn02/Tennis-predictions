"""Round 2, mathematics brainstormer: result-free computations behind docs/studies/feature_interactions/round2/
rebuttal_mathematics.md. No a_won, no price against outcomes; seasons <= 2021 only. The match's own serve-point counts are
read as a statistic target (the quantity Stage 3's over-dispersion constants and the IOS fits are built from).

1. V_gap: day noise on the point-level gap. e = logit(realised serve-point rate) - pre-match surface-IOS logit; shared
   conditions cancel in e_A - e_B. The binomial part is simulated exactly (counts redrawn at the expected rates).
   From V_gap: c^2 and the damped Bo5/Bo3 log-odds ratio (Gauss-Hermite on the exact iid chain).
2. B5 precheck: per-player day variance from the player's gap residuals; split-half reliability (players with >= 100
   matches, halves of >= 50), de-noised player and pair CV.
3. I-042: the share of the hazard term's value left when the hazard difference is a free linear control.
Run: ./python.sh src/eda/feature_interactions/round2/mathematics/day_noise_precheck.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "mc", ROOT / "src/eda/feature_interactions/round0/mathematics/markov_composition.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
OUT = ROOT / "data/studies/feature_interactions/round2/mathematics"
OLD = ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/predictability_diagnostic"
RNG = np.random.default_rng(20261006)


def load() -> pd.DataFrame:
    f = pd.read_parquet(M.MODEL_FRAME, columns=["match_id", "tour", "season", "in_surface", "in_best_of",
                                                "in_odds_logit"])
    f = f[f.season <= 2021].reset_index(drop=True)
    sf = pd.read_parquet(M.SURFACE_FEATURES, columns=["match_id"] + [f"srf_{k}_eff_spw_{s}" for k in "OD" for s in "ab"])
    f = f.merge(sf, on="match_id", how="left", validate="one_to_one")
    p = pd.read_parquet(OLD / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "side", "spw_n", "spw_d", "has_box"])
    for side, tag in (("A", "a"), ("B", "b")):
        q = p[p.side == side].drop(columns="side")
        q = q.rename(columns={c: f"{c}_{tag}" for c in ("player_id", "spw_n", "spw_d", "has_box")})
        f = f.merge(q, on="match_id", how="left", validate="one_to_one")
    return f


def residuals(f: pd.DataFrame) -> pd.DataFrame:
    mu = M.mu_rows(f, "spw", M.surface_means())
    xa = mu + f.srf_O_eff_spw_a.to_numpy() - f.srf_D_eff_spw_b.to_numpy()
    xb = mu + f.srf_O_eff_spw_b.to_numpy() - f.srf_D_eff_spw_a.to_numpy()
    na, nb = f.spw_d_a.to_numpy(float), f.spw_d_b.to_numpy(float)
    ka, kb = f.spw_n_a.to_numpy(float), f.spw_n_b.to_numpy(float)
    ok = (f.has_box_a.fillna(False) & f.has_box_b.fillna(False)).to_numpy() & np.isfinite(xa + xb + na + nb + ka + kb)
    ok &= (na >= 30) & (nb >= 30) & (ka <= na) & (kb <= nb) & np.isin(f.in_best_of, [3, 5])
    g = f.loc[ok, ["match_id", "tour", "in_best_of", "player_id_a", "player_id_b", "in_odds_logit"]].copy()
    xa, xb, na, nb, ka, kb = xa[ok], xb[ok], na[ok], nb[ok], ka[ok], kb[ok]
    lr = lambda k, n: M.lg((k + 0.5) / (n + 1))                              # noqa: E731
    g["ea"], g["eb"] = lr(ka, na) - xa, lr(kb, nb) - xb
    sims = []                                                               # exact binomial part, 8 redraws
    for _ in range(8):
        sa, sb = RNG.binomial(na.astype(int), expit(xa)), RNG.binomial(nb.astype(int), expit(xb))
        sims.append(np.column_stack([lr(sa, na) - xa, lr(sb, nb) - xb]))
    S = np.stack(sims)                                                      # (8, n, 2)
    g["bin_gap"] = (S[:, :, 0] - S[:, :, 1]).var(axis=0, ddof=1)            # per-match binomial var of ea - eb
    g["bin_sum"] = (S[:, :, 0] + S[:, :, 1]).var(axis=0, ddof=1)
    return g


def v_gap(g: pd.DataFrame) -> dict:
    out = {}
    for key, sel in (("atp", g.tour.eq("atp")), ("atp_bo3", g.tour.eq("atp") & g.in_best_of.eq(3)),
                     ("atp_bo5", g.tour.eq("atp") & g.in_best_of.eq(5)), ("wta", g.tour.eq("wta"))):
        d, s = (g.ea - g.eb)[sel], (g.ea + g.eb)[sel]
        vg = float(d.var() - g.bin_gap[sel].mean())
        out[key] = {"matches": int(sel.sum()), "var_gap_resid": float(d.var()), "binomial_gap": float(g.bin_gap[sel].mean()),
                    "V_gap": vg, "V_sum": float(s.var() - g.bin_sum[sel].mean()),
                    "cov_ea_eb_excess": float(0.25 * ((s.var() - g.bin_sum[sel].mean()) - vg))}
    return out


def damping(V: float, tour: str) -> dict:
    mu = 0.4888 if tour == "atp" else 0.2414                                # Stage 3 spw means, logit
    res = {}
    for bo in ((3, 5) if tour == "atp" else (3,)):
        b = float(M.lev_logit(mu, bo))
        z = float(M.lg(M.gh_expect_P(mu, 0.05, np.sqrt(max(V, 1e-9)), bo)))
        res[f"bo{bo}"] = {"beta_L": b, "c2": (z / (b * 0.05)) ** 2, "z_at_0.05": z}
    if tour == "atp":
        res["bo5_over_bo3"] = res["bo5"]["z_at_0.05"] / res["bo3"]["z_at_0.05"]
    return res


def b5_precheck(g: pd.DataFrame, vg: dict, min_matches: int = 100, splits: int = 20) -> dict:
    """Per-player day variance: mean over the player's matches of (r^2 - binomial) minus the opponents' average share
    (V_gap / 2), r = the player's own gap residual. Split-half reliability over random halves."""
    out = {}
    for t in ("atp", "wta"):
        h = g[g.tour.eq(t)]
        d = (h.ea - h.eb).to_numpy()
        q = d * d - h.bin_gap.to_numpy()                      # unbiased per-match excess for the pair
        rows = pd.DataFrame({"pid": np.r_[h.player_id_a.to_numpy(), h.player_id_b.to_numpy()], "q": np.r_[q, q]})
        V = vg[t]["V_gap"]
        grp = rows.groupby("pid")["q"]
        n = grp.size()
        keep = n[n >= min_matches].index
        sub = rows[rows.pid.isin(keep)]
        full = sub.groupby("pid")["q"].mean() - V / 2
        rs, covs = [], []
        for _ in range(splits):
            u = RNG.random(len(sub)) < 0.5
            h1 = sub[u].groupby("pid")["q"].mean() - V / 2
            h2 = sub[~u].groupby("pid")["q"].mean() - V / 2
            j = pd.concat([h1, h2], axis=1, keys=["a", "b"]).dropna()
            rs.append(np.corrcoef(j.a, j.b)[0, 1])
            covs.append(np.cov(j.a, j.b)[0, 1])
        r_half = float(np.mean(rs))
        true_var = max(float(np.mean(covs)), 0.0)            # the halves' covariance estimates the true spread
        mean_s2 = float(full.mean())
        cv_player = float(np.sqrt(true_var) / mean_s2) if mean_s2 > 0 else float("nan")
        out[t] = {"players": int(len(keep)), "median_matches": float(n[keep].median()), "mean_sigma2": mean_s2,
                  "half_reliability": r_half, "full_reliability_sb": float(2 * r_half / (1 + r_half)),
                  "true_sd_sigma2": float(np.sqrt(true_var)), "cv_player_denoised": cv_player,
                  "cv_pair_denoised": cv_player / np.sqrt(2), "per_match_sd_of_q": float(np.std(q))}
    return out


def long_table(g: pd.DataFrame, f: pd.DataFrame) -> pd.DataFrame:
    """One row per player-match: the player's own gap residual r and its binomial variance, in time order."""
    k = g.merge(f[["match_id", "tournament_date", "in_round"]], on="match_id", how="left")
    d = (k.ea - k.eb).to_numpy()
    L = pd.DataFrame({"tour": np.r_[k.tour, k.tour], "pid": np.r_[k.player_id_a, k.player_id_b],
                      "date": np.r_[k.tournament_date, k.tournament_date], "rnd": np.r_[k.in_round, k.in_round],
                      "r": np.r_[d, -d], "b": np.r_[k.bin_gap, k.bin_gap]})
    return L.sort_values(["pid", "date", "rnd"]).reset_index(drop=True)


def persistence(L: pd.DataFrame, vg: dict) -> dict:
    """Lag-j autocovariance of a player's gap residual across his consecutive matches (different opponents): the
    persistent rating error var(delta); the idiosyncratic per-match part is V_gap - 2 cov_1."""
    out = {}
    for t in ("atp", "wta"):
        h = L[L.tour.eq(t)]
        r, pid = h.r.to_numpy(), h.pid.to_numpy()
        res = {}
        for j in (1, 2, 5, 10, 20):
            same = pid[j:] == pid[:-j]
            res[f"cov_lag{j}"] = float(np.mean(r[j:][same] * r[:-j][same]) - np.mean(r) ** 2)
        res["V_idio"] = vg[t]["V_gap"] - 2 * res["cov_lag1"]
        out[t] = res
    return out


def b5_first_difference(L: pd.DataFrame, per: dict, min_pairs: int = 50, splits: int = 20) -> dict:
    """Per-player day variance from non-overlapping consecutive pairs: q = (r1 - r2)^2/2 - (b1 + b2)/2 removes the
    slowly varying rating error; minus the opponents' share V_idio/2. Split-half over pairs."""
    out = {}
    for t in ("atp", "wta"):
        h = L[L.tour.eq(t)].copy()
        h["k"] = h.groupby("pid").cumcount()
        a, b = h[h.k % 2 == 0].reset_index(drop=True), h[h.k % 2 == 1].reset_index(drop=True)
        a = a[a.groupby("pid").cumcount() < b.groupby("pid").size().reindex(a.pid).fillna(0).to_numpy()]
        m = a.merge(b, on=["pid"], suffixes=("1", "2"), how="inner")
        m = m[m.k2 == m.k1 + 1]
        q = 0.5 * (m.r1 - m.r2) ** 2 - 0.5 * (m.b1 + m.b2)
        P = pd.DataFrame({"pid": m.pid.to_numpy(), "q": q.to_numpy()})
        n = P.groupby("pid").size()
        P = P[P.pid.isin(n[n >= 2 * min_pairs].index)]
        V = per[t]["V_idio"]
        full = P.groupby("pid")["q"].mean() - V / 2
        rs, covs = [], []
        for _ in range(splits):
            u = RNG.random(len(P)) < 0.5
            j = pd.concat([P[u].groupby("pid")["q"].mean(), P[~u].groupby("pid")["q"].mean()], axis=1,
                          keys=["x", "y"]).dropna() - V / 2
            rs.append(np.corrcoef(j.x, j.y)[0, 1])
            covs.append(np.cov(j.x, j.y)[0, 1])
        tv = max(float(np.mean(covs)), 0.0)
        out[t] = {"players": int(P.pid.nunique()), "median_pairs": float(n[n >= 2 * min_pairs].median()),
                  "mean_sigma2": float(full.mean()), "half_reliability": float(np.mean(rs)),
                  "true_sd_sigma2": float(np.sqrt(tv)), "cv_player_denoised": float(np.sqrt(tv) / full.mean()),
                  "cv_pair_denoised": float(np.sqrt(tv) / full.mean() / np.sqrt(2))}
    return out


def two_level(vg: dict, per: dict, sets3: float = 2.37, sets5: float = 3.85) -> dict:
    """Split the men's idiosyncratic noise into a match-constant part V_d and a per-set part V_s from
    V_gap(bo) = V_d + V_s / mean sets (Bo3 vs Bo5), then the exact two-level damping: sets independent given the day."""
    pers = 2 * per["atp"]["cov_lag1"]
    vs = (vg["atp_bo3"]["V_gap"] - vg["atp_bo5"]["V_gap"]) / (1 / sets3 - 1 / sets5)
    vd = vg["atp_bo3"]["V_gap"] - vs / sets3 - pers
    t, w = np.polynomial.hermite.hermgauss(24)
    w = w / np.sqrt(np.pi)

    def z(mu, dlt, bo):
        ud = np.sqrt(2 * max(vd, 1e-9)) * t
        us = np.sqrt(2 * max(vs, 1e-9)) * t
        D = dlt + ud[:, None] + us[None, :]
        s = (M.set_win(expit(mu + D / 2), expit(mu - D / 2)) * w[None, :]).sum(axis=1)
        pm = s * s * (3 - 2 * s) if bo == 3 else s ** 3 * (10 - 15 * s + 6 * s * s)
        return float(M.lg((pm * w).sum()))
    mu, dm = 0.4888, 0.02
    out = {"V_d_match_constant": vd, "V_s_per_set": vs, "persistent_pair_part": pers}
    out["bo5_over_bo3"] = z(mu, 0.05, 5) / z(mu, 0.05, 3)
    for bo in (3, 5):
        num = (np.log(z(mu + dm, 0.05, bo)) - np.log(z(mu - dm, 0.05, bo))) / (2 * dm)
        den = (np.log(M.lev_logit(mu + dm, bo)) - np.log(M.lev_logit(mu - dm, bo))) / (2 * dm)
        out[f"dominance_damping_bo{bo}"] = float(num / den)
    return out


def pair_persistence(g: pd.DataFrame, f: pd.DataFrame, per: dict) -> dict:
    """Covariance of the gap residual across consecutive meetings of the same pair (one fixed orientation), against
    twice the player-level lag covariance: the excess is a stable pair-specific (matchup) deviation."""
    k = g.merge(f[["match_id", "tournament_date", "in_round"]], on="match_id", how="left")
    lo = np.minimum(k.player_id_a.astype(str), k.player_id_b.astype(str))
    sign = np.where(k.player_id_a.astype(str) == lo, 1.0, -1.0)
    k = k.assign(pair=lo + "|" + np.maximum(k.player_id_a.astype(str), k.player_id_b.astype(str)),
                 r=sign * (k.ea - k.eb)).sort_values(["pair", "tournament_date", "in_round"])
    out = {}
    for t in ("atp", "wta"):
        h = k[k.tour.eq(t)]
        r, pr = h.r.to_numpy(), h.pair.to_numpy()
        same = pr[1:] == pr[:-1]
        c = float(np.mean(r[1:][same] * r[:-1][same]))
        out[t] = {"consecutive_meetings": int(same.sum()), "pairs_with_repeat": int(pd.Series(pr[1:][same]).nunique()),
                  "cov_same_pair": c, "player_level_part": 2 * per[t]["cov_lag1"],
                  "pair_specific_var": c - 2 * per[t]["cov_lag1"],
                  "se_cov": float(np.std(r[1:][same] * r[:-1][same]) / np.sqrt(same.sum()))}
    return out


def dominance_by_season() -> dict:
    """SD of the pair's serve dominance (half the sum of the two matchup logits minus the surface mean), by season
    2013-2024 (features only)."""
    f = pd.read_parquet(M.MODEL_FRAME, columns=["match_id", "tour", "season", "in_surface"])
    f = f[f.season <= 2024]
    sf = pd.read_parquet(M.SURFACE_FEATURES, columns=["match_id"] + [f"srf_{k}_eff_spw_{s}" for k in "OD" for s in "ab"])
    f = f.merge(sf, on="match_id", how="left")
    hy = 0.5 * ((f.srf_O_eff_spw_a - f.srf_D_eff_spw_a) + (f.srf_O_eff_spw_b - f.srf_D_eff_spw_b))
    return {t: {int(y): float(hy[(f.tour == t) & (f.season == y)].std()) for y in range(2013, 2025)} for t in ("atp", "wta")}


def profile_vs_spw(f: pd.DataFrame) -> dict:
    """Statistic target: log loss per serve point of the match's realised serve points under (a) the surface IOS of serve
    points won and (b) the per-statistic composition p = fi fw + (1 - fi) sw from the surface IOS components; plus the
    best logit blend chosen on 2013-2017 and scored on 2018-2021. Lower log loss is better."""
    means = M.surface_means()
    cols = ["match_id"] + [f"srf_{k}_eff_{s}_{x}" for s in ("first_in", "first_won", "second_won") for k in "OD"
                           for x in "ab"]
    h = f.merge(pd.read_parquet(M.SURFACE_FEATURES, columns=cols), on="match_id", how="left")
    mu = {s: M.mu_rows(h, s, means) for s in ("spw", "first_in", "first_won", "second_won")}
    rows = []
    for srv, ret in (("a", "b"), ("b", "a")):
        x = mu["spw"] + h[f"srf_O_eff_spw_{srv}"] - h[f"srf_D_eff_spw_{ret}"]
        c = {s: expit(mu[s] + h[f"srf_O_eff_{s}_{srv}"] - h[f"srf_D_eff_{s}_{ret}"]) for s in ("first_in", "first_won",
                                                                                              "second_won")}
        pc = c["first_in"] * c["first_won"] + (1 - c["first_in"]) * c["second_won"]
        rows.append(pd.DataFrame({"tour": h.tour, "season": h.season, "k": h[f"spw_n_{srv}"], "n": h[f"spw_d_{srv}"],
                                  "has": h[f"has_box_{srv}"], "xa": x, "xc": M.lg(pc), "x0": mu["spw"]}))
    R = pd.concat(rows, ignore_index=True)
    R = R[R.has.fillna(False) & (R.n >= 30) & (R.k <= R.n) & np.isfinite(R.xa + R.xc)]

    def ll(x, k, n):
        p = expit(x)
        return float(-(k * np.log(p) + (n - k) * np.log(1 - p)).sum() / n.sum())
    out = {}
    for t in ("atp", "wta"):
        Q = R[R.tour.eq(t)]
        tr, te = Q[Q.season <= 2017], Q[Q.season >= 2018]
        grid = np.linspace(0, 1, 21)
        best = grid[int(np.argmin([ll((1 - a) * tr.xa + a * tr.xc, tr.k, tr.n) for a in grid]))]
        r = {"serve_matches": int(len(te))}
        for nm, x in (("surface_mean", te.x0), ("spw_ios", te.xa), ("composed_profile", te.xc),
                      ("blend", (1 - best) * te.xa + best * te.xc)):
            r[nm] = ll(x, te.k, te.n)
        r["blend_weight_on_profile"] = float(best)
        r["gain_milli_per_point_profile_vs_spw"] = 1000 * (r["spw_ios"] - r["composed_profile"])
        r["gain_milli_per_point_blend_vs_spw"] = 1000 * (r["spw_ios"] - r["blend"])
        out[t] = r
    return out


def form_factor_share() -> dict:
    """Eigenvalue shares of the correlation matrix of the 16 two-week profile inputs (A - B), 2013-2021 rows."""
    cols = [c for c in pd.read_parquet(M.MODEL_FRAME).columns if c.startswith("in_form")]
    f = pd.read_parquet(M.MODEL_FRAME, columns=["tour", "season"] + cols)
    out = {}
    for t in ("atp", "wta"):
        X = f[(f.tour == t) & (f.season <= 2021)][cols].dropna()
        ev = np.sort(np.linalg.eigvalsh(np.corrcoef(X.to_numpy().T)))[::-1]
        out[t] = {"rows": int(len(X)), "share_1": float(ev[0] / ev.sum()), "share_1_3": float(ev[:3].sum() / ev.sum()),
                  "eig_top5": [float(v) for v in ev[:5]]}
    return out


def hidden_level_recovery() -> dict:
    """How much of the pair's serve dominance (a symmetric sum the A - B frame 'cannot see') a flexible model recovers
    from the 58 inputs: 3-fold CV R^2 of gradient boosting (features only, 2013-2021), against linear OLS."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import cross_val_score
    fr = pd.read_parquet(M.MODEL_FRAME)
    fr = fr[fr.season <= 2021].reset_index(drop=True)
    X = fr[[c for c in fr.columns if c.startswith("in_")]].to_numpy(float)
    sf = pd.read_parquet(M.SURFACE_FEATURES, columns=["match_id"] + [f"srf_{k}_eff_spw_{s}" for k in "OD" for s in "ab"])
    s = fr[["match_id"]].merge(sf, on="match_id", how="left")
    y = 0.5 * ((s.srf_O_eff_spw_a - s.srf_D_eff_spw_a) + (s.srf_O_eff_spw_b - s.srf_D_eff_spw_b)).to_numpy()
    out = {}
    for t in ("atp", "wta"):
        m = (fr.tour == t).to_numpy() & np.isfinite(y)
        keep = [j for j in range(X.shape[1]) if np.unique(X[m, j][np.isfinite(X[m, j])]).size >= 2]
        Xt = np.nan_to_num(X[m][:, keep], nan=0.0)
        Xa = np.column_stack([Xt, np.abs(Xt)])                       # even functions let a linear model see sums
        gb = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=0)
        out[t] = {"rows": int(m.sum()),
                  "r2_linear": float(cross_val_score(LinearRegression(), Xt, y[m], cv=3, scoring="r2").mean()),
                  "r2_linear_with_abs": float(cross_val_score(LinearRegression(), Xa, y[m], cv=3, scoring="r2").mean()),
                  "r2_boosting": float(cross_val_score(gb, X[m][:, keep], y[m], cv=3, scoring="r2").mean())}
    return out


def hazard_shares(g: pd.DataFrame) -> dict:
    """Value of tau = -dh(1 + cosh z) - (sum h - 2 hbar) sinh z per sigma_h^2, in full and with dh a free linear
    control (weighted projection), on the 2013-2021 price distribution."""
    out = {}
    f = pd.read_parquet(M.MODEL_FRAME, columns=["tour", "season", "in_odds_logit"])
    f = f[f.season <= 2021]
    for t in ("atp", "wta"):
        z = f.loc[f.tour.eq(t), "in_odds_logit"].dropna().to_numpy()
        w = expit(z) * (1 - expit(z))
        A, ch = 1 + np.cosh(z), np.cosh(z)
        full = float(np.mean(ch))                            # = E[w (A^2 + sinh^2)] -> value sigma_h^2 E[cosh z]
        a_w = 0.5 / w.mean()
        dh_left = float(np.mean(A) / 2 - 0.25 / w.mean())    # E[w (A - a_w)^2]
        sum_part = float(np.mean((ch - 1) / 2))
        out[t] = {"E_cosh": full, "dh_part_full": float(np.mean(A) / 2), "dh_part_left": dh_left,
                  "sum_part": sum_part, "share_left": (dh_left + sum_part) / full,
                  "mll_full_at_1pp": 1000 * 1e-4 * full, "mll_left_at_1pp": 1000 * 1e-4 * (dh_left + sum_part)}
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    f = load()
    g = residuals(f)
    vg = v_gap(g)
    L = long_table(g, pd.read_parquet(M.MODEL_FRAME, columns=["match_id", "tournament_date", "in_round", "season"])
                   .query("season <= 2021"))
    per = persistence(L, vg)
    res = {"note": "result-free; seasons <= 2021; statistic target = the match's own serve-point counts", "v_gap": vg,
           "residual_means": {t: [float(g.ea[g.tour.eq(t)].mean()), float(g.eb[g.tour.eq(t)].mean())] for t in ("atp", "wta")}}
    res["damping"] = {t: {"raw": damping(vg[t]["V_gap"], t), "minus_0.013": damping(vg[t]["V_gap"] - 0.013, t)}
                      for t in ("atp", "wta")}
    res["b5_precheck"] = b5_precheck(g, vg)
    res["persistence"] = per
    res["damping_idio"] = {t: damping(per[t]["V_idio"], t) for t in ("atp", "wta")}
    res["b5_first_difference"] = b5_first_difference(L, per)
    res["two_level_men"] = two_level(vg, per)
    res["pair_persistence"] = pair_persistence(g, pd.read_parquet(M.MODEL_FRAME, columns=["match_id", "tournament_date",
                                                                                          "in_round"]), per)
    res["dominance_sd_by_season"] = dominance_by_season()
    res["profile_vs_spw"] = profile_vs_spw(f)
    res["form_factor_share"] = form_factor_share()
    res["hazard_shares"] = hazard_shares(g)
    (OUT / "day_noise_precheck.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
