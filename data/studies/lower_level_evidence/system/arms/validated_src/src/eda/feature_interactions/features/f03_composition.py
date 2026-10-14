"""Family 02, composition through the iid point model, as the final family (round-2 rulings MEC-R1, MAT-R4, MEC-R2b)
fixes it: I-008 (weight 2) and block B2 (I-012, I-013; weight 0.5).

I-008  z_spw = logit P_iid(expit(mu + O^spw_A - D^spw_B), expit(mu + O^spw_B - D^spw_A); best-of, deciding-set rule),
       the serve-point surface IOS (srf_O_eff_spw / srf_D_eff_spw, leak-proof) composed through the iid model (Stage 3's
       2010-2018 tour x surface spw averages; the Slams' deciding-set rules of stage2_iid). Tested as its REMAINDER after
       a per-tour least-squares projection on the 58 inputs (intercept, missing indicators) fitted on 2013-2018 rows
       without outcomes, applied to every row (swap-consistent: refitted on the swapped panel the remainder changes sign
       exactly). Sign +, weight 2, slow. Controls: Std = ratings_iid, ios_points_short. Deployment: TabPFN difference
       column z_spw, else nudge. Pre-declared sensitivities (SENSITIVITIES, not hypotheses): z_C1 (the three components
       fi, fw, sw composed), the damped composition (V = 0.154 men / 0.183 women), the link-corrected composition
       (MEC-L1: each serve point expit(mu + O - D + gamma_s O D), gamma_s = 1 - 2 pbar_s), and z_C1 - z_spw (MAT-K1),
       each in the same remainder form.
B2     free points and ace curvature beyond additive IOS, a signed-sum block (each member / its 2014-2021 SD), weight 0.5:
       I-012 (+) the free-point shield x = c_AB - c_BA (MEC-04, declared g): for server P against returner Q, a = expit(
             mu_ace + O^ace_P - D^ace_Q), a0 = expit(mu_ace + O^ace_P), p0 = expit(mu_spw + O^spw_P), r0 = (p0 - a0)/(1 - a0),
             r = expit(logit r0 - k D^spw_Q) with k = pbar(1 - pbar) / ((1 - abar) rbar (1 - rbar)) from the cell
             averages (mean elasticity 1), c = logit(a + (1 - a) r) - (mu_spw + O^spw_P - D^spw_Q). CONTESTED (ruling
             MEC-R2b): its result-free precheck here failed (shield_precheck) and counts as no evidence at M2
       I-013 (+) e_ace = expit(mu_ace + O^ace_A - D^ace_B) - expit(mu_ace + O^ace_B - D^ace_A) (MAT-W1's e_s, aces only)
       Controls: iosO_ace, iosD_ace, prod_ace, Delta D^spw, tau_spw = O^spw_A D^spw_B - O^spw_B D^spw_A (MEC-L1), nearest
       inputs; eta-modulator controls: Sigma D^spw, Sigma g (the shield's elasticity shortfall at the server's own rates),
       Sigma O^ace, Sigma D^ace, centred within tour x surface on 2014-2021 rows. Deployment: TabPFN difference columns.
       Exposed to ace recording faults (rulings R2-measure).

Constants: none tuned (k fixed by the cell averages so that the mean elasticity is 1, as MEC-04 specifies; r0 clipped
to [1e-4, 1 - 1e-4]; V and gamma_s as the rulings fix them). Prechecks (result-free, statistic level, 2013-2018 pool
matches): shield_precheck. Reads no result. Run (diagnostics): ./python.sh src/eda/feature_interactions/features/
f03_composition.py
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

COMPONENTS = ("first_in", "first_won", "second_won")
STD_I008 = ("ratings_iid", "ios_points_short")                 # the final family's controls for I-008
STD_B2 = ("formdef_ace", "iosO_first_won", "form_ace")   # nearest beyond the listed controls: shield formdef_ace
# +0.565; e_ace iosO_first_won +0.769, form_ace +0.672 (diagnostics, 2014-2021)
V_DAMP = {"atp": 0.154, "wta": 0.183}                          # rulings MAT-R6 (N3)


def spw_pair(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return S.pt(P, "spw", "a", "b"), S.pt(P, "spw", "b", "a")


def z_spw(P: pd.DataFrame) -> np.ndarray:
    pa, pb = spw_pair(P)
    return S.match_logit(pa, pb, S.num(P, "best_of"), S.rule(P))


def z_c1(P: pd.DataFrame) -> np.ndarray:
    return S.match_logit(S.comp_serve(P, "a", "b"), S.comp_serve(P, "b", "a"), S.num(P, "best_of"), S.rule(P))


def combine_i008(P: pd.DataFrame) -> dict:
    z = z_spw(P)
    Cm, names = S.pack([(f"in_{n}", S.num(P, f"in_{n}")) for n in STD_I008])
    return {"x": S.resid_on_58(P, z, by_tour=True), "controls": Cm, "control_names": names,
            "tabpfn": {"f03_z_spw": (z, "diff", None)}}


def z_damped(P: pd.DataFrame, n_nodes: int = 15) -> np.ndarray:
    """logit E_u[P_iid] with the point-level gap perturbed by u ~ N(0, V_tour) (I-010's form at the rulings' V)."""
    bo, r = S.num(P, "best_of"), S.rule(P)
    m = S.mu(P, "spw") + 0.5 * (S.ios(P, "srfO", "spw", "a") + S.ios(P, "srfO", "spw", "b")
                                - S.ios(P, "srfD", "spw", "a") - S.ios(P, "srfD", "spw", "b"))
    delta = (S.ios(P, "srfO", "spw", "a") - S.ios(P, "srfD", "spw", "b")) - (S.ios(P, "srfO", "spw", "b") - S.ios(P, "srfD", "spw", "a"))
    V = P["tour"].astype(str).map(V_DAMP).to_numpy(dtype=float)
    nodes, w = np.polynomial.hermite_e.hermegauss(n_nodes)
    acc = np.zeros(len(P))
    for u, wt in zip(nodes, w / w.sum()):
        dd = delta + u * np.sqrt(V)
        acc += wt * expit(S.match_logit(expit(m + dd / 2), expit(m - dd / 2), bo, r))
    return S.lg(acc)


def z_link(P: pd.DataFrame) -> np.ndarray:
    """MEC-L1's link-corrected composition: each serve point expit(mu + O - D + gamma_s O D), gamma_s = 1 - 2 pbar_s."""
    g = 1 - 2 * expit(S.mu(P, "spw"))
    def p(sv, rt):
        O, D = S.ios(P, "srfO", "spw", sv), S.ios(P, "srfD", "spw", rt)
        return expit(S.mu(P, "spw") + O - D + g * O * D)
    return S.match_logit(p("a", "b"), p("b", "a"), S.num(P, "best_of"), S.rule(P))


SENSITIVITIES = {      # pre-declared, never hypotheses: name -> P -> remainder column (same form as the primary)
    "I-008 z_C1": lambda P: S.resid_on_58(P, z_c1(P), by_tour=True),
    "I-008 damped": lambda P: S.resid_on_58(P, z_damped(P), by_tour=True),
    "I-008 link-corrected": lambda P: S.resid_on_58(P, z_link(P), by_tour=True),
    "I-008 z_C1 - z_spw (two-sided)": lambda P: S.resid_on_58(P, z_c1(P) - z_spw(P), by_tour=True),
}
SENSITIVITY_OF = {name: "I-008" for name in SENSITIVITIES}       # each reuses I-008's controls (batch interface)


def shield_core(mu_a, mu_p, Oa, Op, Da, Dp) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MEC-04 for server ratings (Oa, Op) against returner ratings (Da, Dp): (c, g, p_struct), c = logit p_struct -
    the additive IOS logit, g = 1 - the returner elasticity at the server's own rates (the shortfall)."""
    abar, pbar = expit(mu_a), expit(mu_p)
    rbar = (pbar - abar) / (1 - abar)
    k = pbar * (1 - pbar) / ((1 - abar) * rbar * (1 - rbar))
    a0, p0 = expit(mu_a + Oa), expit(mu_p + Op)
    r0 = np.clip((p0 - a0) / (1 - a0), 1e-4, 1 - 1e-4)
    a = expit(mu_a + Oa - Da)
    r = expit(S.lg(r0) - k * Dp)
    ps = a + (1 - a) * r
    c = S.lg(ps) - (mu_p + Op - Dp)
    g = 1 - k * (1 - a0) * r0 * (1 - r0) / (p0 * (1 - p0))          # 1 - d logit p / d(-D) at D = 0
    return c, g, ps


def _shield_parts(P: pd.DataFrame, server: str, ret: str) -> tuple[np.ndarray, np.ndarray]:
    """(c_{server -> returner}, g_server) on the panel."""
    c, g, _ = shield_core(S.mu(P, "ace"), S.mu(P, "spw"), S.ios(P, "srfO", "ace", server),
                          S.ios(P, "srfO", "spw", server), S.ios(P, "srfD", "ace", ret), S.ios(P, "srfD", "spw", ret))
    return c, g


def shield(P: pd.DataFrame) -> np.ndarray:
    return _shield_parts(P, "a", "b")[0] - _shield_parts(P, "b", "a")[0]


def e_ace(P: pd.DataFrame) -> np.ndarray:
    return S.pt(P, "ace", "a", "b") - S.pt(P, "ace", "b", "a")


# I-012's result-free precheck (shield_precheck, 2013-2018) failed here: the returner elasticity does not fall with the
# server's ace share (observed slope of the residual on D x ace: men -0.009, SE 0.076; women +0.023, SE 0.277; the shield
# predicts -1.13 and -1.17 on the same rows) and p_struct forecasts serve points worse than the additive IOS (-0.23 and
# -0.07 milli per point, lower log loss is better). The round-2 ruling MEC-R2b (CONTESTED) puts it back: the joint fit
# with the link term O.D is the theory-consistent gate; B2 drops to weight 0.5, tau_spw becomes a control, and the
# precheck counts as no evidence at M2. Set False to drop the member again.
KEEP_I012 = True


def tau_spw(P: pd.DataFrame) -> np.ndarray:
    """MEC-L1's link column O^spw_A D^spw_B - O^spw_B D^spw_A (= -prod_spw), a B2 control."""
    return S.ios(P, "srfO", "spw", "a") * S.ios(P, "srfD", "spw", "b") - S.ios(P, "srfO", "spw", "b") * S.ios(P, "srfD", "spw", "a")


def combine_b2(P: pd.DataFrame) -> dict:
    ea = e_ace(P)
    members = [(ea, "+")]
    cols = [(f"in_{n}", S.num(P, f"in_{n}")) for n in ("iosO_ace", "iosD_ace", "prod_ace") + STD_B2]
    sums = [S.ios(P, "srfO", "ace", "a") + S.ios(P, "srfO", "ace", "b"),
            S.ios(P, "srfD", "ace", "a") + S.ios(P, "srfD", "ace", "b")]
    tab = {"f03_e_ace": (ea, "diff", None)}
    if KEEP_I012:
        sh = shield(P)
        members.append((sh, "+"))
        cols += [("dD_spw", S.ios(P, "srfD", "spw", "a") - S.ios(P, "srfD", "spw", "b")), ("tau_spw", tau_spw(P))]
        ga, gb = _shield_parts(P, "a", "b")[1], _shield_parts(P, "b", "a")[1]
        sums += [S.ios(P, "srfD", "spw", "a") + S.ios(P, "srfD", "spw", "b"), ga + gb]
        tab["f03_shield"] = (sh, "diff", None)
    Cm, names = S.pack(cols)
    E = np.column_stack([S.centre_disc(P, s_) for s_ in sums])
    return {"x": S.signed_block(P, members), "controls": Cm, "control_names": names, "eta_mod_controls": E,
            "tabpfn": tab}


HYPOTHESES = [
    {"hid": "I-008", "master": "I-008", "kind": "C", "sign": "+", "weight": 2.0, "trait": "slow",
     "deployment": "diff", "family": "02", "prepare": None, "combine": combine_i008, "sensitivities": SENSITIVITIES},
    {"hid": "B2", "master": "I-013" if not KEEP_I012 else "I-012+I-013", "kind": "C", "sign": "+", "weight": 0.5, "trait": "slow",
     "deployment": "diff", "family": "02", "prepare": None, "combine": combine_b2},
]


def _wls(X, y, w, groups):
    """Weighted least squares with player-clustered standard errors (result-free statistic regressions)."""
    XtW = X.T * w
    A = np.linalg.inv(XtW @ X)
    beta = A @ (XtW @ y)
    u = (X * (w * (y - X @ beta))[:, None])
    g = pd.DataFrame(u).groupby(groups).sum().to_numpy()
    V = A @ (g.T @ g) @ A
    return beta, np.sqrt(np.diag(V))


def shield_precheck(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Statistic level, result-free (MEC-04's kill test 1, as the audit kept it), on 2013-2018 pool matches (every
    level the surface IOS covers; serve points of each player-match, at least 20):
    (a) the serve-point logit residual against the additive IOS regressed on D_returner and D_returner x (the server's
        ace rate - the mean), weighted by serve points, player-clustered SE: the shield predicts a positive interaction;
        the same regression on the model's own correction c gives the slope the shield predicts;
    (b) the per-point log loss of p_struct against the additive IOS (milli per serve point; lower is better): the
        originator kills below a 0.02 milli gain."""
    L = S.cut_history(L, P)
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    H = S.history_ios(L, ["srf_O_eff_spw", "srf_D_eff_spw", "srf_O_eff_ace", "srf_D_eff_ace"])
    n, d = S.num(L, "spw_n"), S.num(L, "spw_d")
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    m_spw, m_ace = S.mu(L, "spw", tour, surf), S.mu(L, "ace", tour, surf)
    Op, Dp = H[("own", "srf_O_eff_spw")], H[("opp", "srf_D_eff_spw")]
    Oa, Da = H[("own", "srf_O_eff_ace")], H[("opp", "srf_D_eff_ace")]
    c, _, ps = shield_core(m_ace, m_spw, Oa, Op, Da, Dp)
    a = expit(m_ace + Oa)
    ok = (yr >= 2013) & (yr <= 2018) & (d >= 20) & np.isfinite(c) & np.isfinite(Dp)
    res = S.lg((n + 0.5) / (d + 1)) - (m_spw + Op - Dp)
    p_add = expit(m_spw + Op - Dp)
    out = {}
    for t in ("atp", "wta"):
        k = ok & (tour == t)
        ac = a[k] - np.average(a[k], weights=d[k])
        X = np.column_stack([np.ones(k.sum()), Dp[k], Dp[k] * ac])
        grp = L["player_id"].astype(str).to_numpy()[k]
        b_obs, se_obs = _wls(X, res[k], d[k], grp)
        b_mod, _ = _wls(X, c[k], d[k], grp)
        ll = {}
        for name, p_ in (("additive", p_add[k]), ("struct", np.clip(ps[k], 1e-6, 1 - 1e-6))):
            ll[name] = float(-np.sum(n[k] * np.log(p_) + (d[k] - n[k]) * np.log(1 - p_)) / np.sum(d[k]))
        out[t] = {"rows": int(k.sum()), "slope_D_obs": float(b_obs[1]),
                  "slope_DxAce_obs": float(b_obs[2]), "se_DxAce_obs_clustered": float(se_obs[2]),
                  "slope_DxAce_predicted_by_shield": float(b_mod[2]),
                  "logloss_per_point_additive": ll["additive"], "logloss_per_point_struct": ll["struct"],
                  "gain_milli_per_point_struct": 1000 * (ll["additive"] - ll["struct"])}
    return out


def diagnostics(P: pd.DataFrame, L: pd.DataFrame | None = None) -> dict:
    d, atp = S.disc(P), S.is_atp(P)
    z, zc = z_spw(P), z_c1(P)
    x = combine_i008(P)["x"]
    rep = P["season"].between(2022, 2024).to_numpy()
    late = P["season"].between(2019, 2021).to_numpy()
    out = {"I-008": {"corr_zspw_ratings_iid": float(np.corrcoef(z[d], S.num(P, "in_ratings_iid")[d])[0, 1]),
                     "corr_zspw_zC1": float(np.corrcoef(z[d], zc[d])[0, 1]),
                     "r2_zspw_on_58": S.r2_on_58(P, z), "r2_remainder_on_58": S.r2_on_58(P, x),
                     "remainder_sd": {w: {t: float(np.nanstd(x[m & (atp if t == "atp" else ~atp)])) for t in ("atp", "wta")}
                                      for w, m in (("2014-2021", d), ("2019-2021", late), ("2022-2024", rep))},
                     "nearest_remainder": S.nearest(P, x, 4)}}
    from src.eda.feature_interactions.features.f02_leverage import lever_columns
    k_eta = lever_columns(P)[:, 0] * S.num(P, "eta_model")
    ok = d & np.isfinite(k_eta) & np.isfinite(x)
    out["I-008"]["corr_remainder_with_kappa_pair_eta"] = float(np.corrcoef(x[ok], k_eta[ok])[0, 1])
    out["I-008 sensitivities"] = {}
    for name, fn in SENSITIVITIES.items():
        v = fn(P)
        out["I-008 sensitivities"][name] = {"sd_disc_atp": float(np.nanstd(v[d & atp])), "sd_disc_wta": float(np.nanstd(v[d & ~atp])),
                                            "corr_with_primary": float(np.corrcoef(np.nan_to_num(v[d]), np.nan_to_num(x[d]))[0, 1])}
    sh, ea, tau = shield(P), e_ace(P), tau_spw(P)
    blk = combine_b2(P)["x"]
    out["B2"] = {"r2_shield": S.r2_on_58(P, sh), "r2_e_ace": S.r2_on_58(P, ea), "r2_block": S.r2_on_58(P, blk),
                 "r2_tau_spw": S.r2_on_58(P, tau), "corr_shield_tau": float(np.corrcoef(sh[d], tau[d])[0, 1]),
                 "corr_members": float(np.corrcoef(sh[d], ea[d])[0, 1]),
                 "nearest_shield": S.nearest(P, sh, 3), "nearest_e_ace": S.nearest(P, ea, 3),
                 "nearest_block": S.nearest(P, blk, 4)}
    if L is not None:
        out["B2"]["shield_precheck_2013_2018"] = shield_precheck(P, L)
    return out


if __name__ == "__main__":
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)
    res = diagnostics(P, long_table())
    print(S.write_diag("f03_composition", res))
    for k, v in res.items():
        print(k, v)
