"""B9a, constitution x own load (math audit block; composite, weight 0.5, slow traits): I-024 height x Fat (-),
I-058 recovery trait x Fat (+), I-061 season odometer x age x autumn (-). Fat is f20's kernel (tau 3 days).

    I-024  two members (the final family): m1 = (h_A - hbar) Fat_A - (h_B - hbar) Fat_B and m2 = (h_A - hbar) (age_A -
           28)+ - (h_B - hbar) (age_B - 28)+; h = Stage 0 height (cm), hbar = the tour's mean on 2014-2021 rows (both
           players). The feasibility audit had failed m2 alone on novelty (R^2 0.958 there); inside the block it is
           tested with its own controls. Height is a fixed trait inside a mixed block: the block GATES on the slow-trait
           widening (variance x 1.25; meta checkpoint 1, R-6 / F-2), and trait_cols = ["height"] lets the batch compute
           the height permutation as a diagnostic of the height members only, never folded into p_joint.
    I-058  Trait_X = the shrunk difference between X's mean points-won residual in his earlier high-Fat matches (Fat >=
           the tour's 80th percentile) and in his low-Fat matches (Fat <= the median), over every earlier match with a
           box score (main tour, Challengers, some team ties). Residual = (points won - expected) / points played,
           expected = serve points x p_serve(X vs that opponent) + return points x (1 - p_serve(opponent vs X)) from
           Stage 3's pre-match ratings (all 872,704 matches; sequential, own order). Shrinkage d tau2 / (tau2 +
           sigma2 (1/n_high + 1/n_low)). Q50, Q80, TAU2 and SIGMA2 are constants estimated on 2013-2018 (statistic
           targets, no price, no forecast) by round2/body/prechecks.py; the split-half reliability gate is there too.
           m = Trait_A Fat_A - Trait_B Fat_B.
    I-061  Odo_X = log((M_X + 300) / (E_X + 300)): M = X's minutes-equivalent load earlier in this season (f20's loads,
           every level), E = the field's mean M for the same tour, week of the year and ranking band (1-20, 21-50,
           51-100, 101-250, other) in the three previous seasons, walk-forward on the clock (lf + 1 <= T_Y); c = 300
           minutes (about three matches) keeps early-season ratios finite. m = 1[month >= 9] (Odo_A (age_A - 27)+ -
           Odo_B (age_B - 27)+), the month of the tournament date.
Block (the final family): x = -z(m1) - z(m2) + z(I-058) - z(I-061), each clipped at the 99th percentile of |m| and
divided by its SD on 2014-2021. I-058's pre-declared gate (split-half reliability above the pure-luck replays', raw
correlations, as declared) PASSES on the corrected history order: r 0.086 on 797 players against replays -0.037,
-0.031, +0.036 (prechecks.py i058; on the pre-22:00 order it was 0.035 against -0.017, also above).
Controls (per member): dh, d(age - 28)+, dFat; dTrait; d[Odo (age - 27)+] (unmodulated), dOdo, d age; the height-
missing and Fat-imputed differences; the nearest inputs. Eta-mod: sum Fat, sum h, sum age, sum Trait, 1[month >= 9], the
missing indicators.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import f20_fatigue as F

# constants fixed on 2013-2018 statistic targets (round2/body/prechecks.py; see round2/builds/body.md)
Q_FAT = {"atp": (3.8919, 4.7157), "wta": (3.8678, 4.6607)}  # Fat median, 80th pct
TAU2, SIGMA2 = 5.669e-05, 5.030e-03    # trait variance (halves' covariance), residual variance
USE_I058 = True    # the gate as declared PASSES: split-half r 0.086 (797 players) > replays -0.011
ODO_C, ODO_YEARS, ODO_MIN_N = 300.0, 3, 30
BANDS = (20, 50, 100, 250)
AGE_KNEE_61, AGE_KNEE_24 = 27.0, 28.0


def residuals(H: pd.DataFrame) -> np.ndarray:
    """Points-won residual per history row (NaN without a box score or a Stage 3 expectation); cached on H."""
    if "pw_resid" not in H.columns:
        s3 = pd.read_parquet(C.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage3_ratings.parquet",
                             columns=["match_id", "p_serve_a", "p_serve_b"],
                             filters=[("year", "<=", int(H["tyear"].max()))])     # no later season is loaded
        s3["match_id"] = s3["match_id"].astype(str)
        s3 = s3.set_index("match_id")
        mid = H["match_id"].astype(str)
        pa, pb = mid.map(s3["p_serve_a"]).to_numpy(float), mid.map(s3["p_serve_b"]).to_numpy(float)
        is_a = (H["side"] == "A").to_numpy()
        ps_self, ps_opp = np.where(is_a, pa, pb), np.where(is_a, pb, pa)
        sd, rd = H["spw_d"].to_numpy(float), H["rpw_d"].to_numpy(float)
        tn, td = H["tpw_n"].to_numpy(float), H["tpw_d"].to_numpy(float)
        ok = H["played"].to_numpy(bool) & (sd > 0) & (rd > 0) & (td > 0) & np.isfinite(ps_self) & np.isfinite(ps_opp)
        expv = sd * ps_self + rd * (1 - ps_opp)
        H["pw_resid"] = np.where(ok, (tn - expv) / np.where(ok, td, 1.0), np.nan)
        H["pw_ps_self"], H["pw_ps_opp"] = ps_self, ps_opp
    return H["pw_resid"].to_numpy(float)


def fat_class(H: pd.DataFrame, q: dict) -> np.ndarray:
    """+1 high-Fat (>= the tour's 80th percentile), -1 low (<= median), 0 between, NaN without a residual."""
    f, _ = F.fat(H)
    tour = H["tour"].astype(str).to_numpy()
    q50 = np.where(tour == "atp", q["atp"][0], q["wta"][0])
    q80 = np.where(tour == "atp", q["atp"][1], q["wta"][1])
    cls = np.where(f >= q80, 1.0, np.where(f <= q50, -1.0, 0.0))
    return np.where(np.isfinite(residuals(H)), cls, np.nan)


def trait_sums(H: pd.DataFrame, q: dict, mask: np.ndarray | None = None) -> dict:
    """Per row, sums over the player's STRICTLY earlier rows (optionally only rows in `mask`): n and sum of residuals
    in high- and low-Fat matches."""
    r = residuals(H)
    cls = fat_class(H, q)
    use = np.isfinite(r) & np.isfinite(cls) & (np.ones(len(H), bool) if mask is None else mask)
    pid = H["pid"].to_numpy()
    out = {}
    for name, c in (("h", 1.0), ("l", -1.0)):
        sel = use & (cls == c)
        n = pd.Series(sel.astype(float)).groupby(pid).cumsum().to_numpy() - sel
        s = pd.Series(np.where(sel, r, 0.0)).groupby(pid).cumsum().to_numpy() - np.where(sel, r, 0.0)
        out[f"n_{name}"], out[f"s_{name}"] = n, s
    return out


def trait(H: pd.DataFrame, q: dict | None = None, tau2: float | None = None, sigma2: float | None = None) -> np.ndarray:
    q = Q_FAT if q is None else q
    tau2 = TAU2 if tau2 is None else tau2
    sigma2 = SIGMA2 if sigma2 is None else sigma2
    T = trait_sums(H, q)
    nh, nl = T["n_h"], T["n_l"]
    ok = (nh > 0) & (nl > 0)
    d = np.where(ok, T["s_h"] / np.maximum(nh, 1) - T["s_l"] / np.maximum(nl, 1), 0.0)
    shrink = np.where(ok, tau2 / (tau2 + sigma2 * (1 / np.maximum(nh, 1) + 1 / np.maximum(nl, 1))), 0.0)
    return d * shrink


def odometer(H: pd.DataFrame) -> np.ndarray:
    """Odo per history row (see the docstring); E is a walk-forward field table on the clock; cached on H."""
    if "odo" not in H.columns:
        load = H["load"].to_numpy(float)
        M = pd.Series(load).groupby([H["pid"].to_numpy(), H["tyear"].to_numpy()]).cumsum().to_numpy() - load
        day = pd.to_datetime(H["t"].to_numpy(), unit="D")
        H["_week"] = np.minimum((day.dayofyear.to_numpy() - 1) // 7, 51).astype(str)
        rank = H["rank"].to_numpy(float)
        band = np.select([rank <= b for b in BANDS], [str(b) for b in BANDS], "other")
        H["_band"] = np.where(np.isfinite(rank), band, "other")
        E = F.walk_forward_ratio(H, M, np.ones(len(H)), np.ones(len(H), bool),
                                 [["tour", "_week", "_band"], ["tour", "_week"], ["tour"]], ODO_YEARS, ODO_MIN_N, np.nan)
        H["odo_M"], H["odo_E"] = M, E
        H["odo"] = np.log((M + ODO_C) / (E + ODO_C))
    return H["odo"].to_numpy(float)


def prepare_b9a(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = F.history(P, L)
    fat3, imp = F.fat(H)
    vals = {"fat": fat3, "imp": imp, "odo": odometer(H)}
    vals["trait"] = trait(H) if USE_I058 else np.zeros(len(H))
    out = {}
    for k, v in vals.items():
        out[f"bd9a_{k}_a"], out[f"bd9a_{k}_b"] = F.at_model(P, H, v)
    return out


def _hbar(P: pd.DataFrame) -> np.ndarray:
    ha, hb = F.ab(P, "height")
    d = F.disc(P)
    tour = P["tour"].astype(str).to_numpy()
    means = {t: np.nanmean(np.r_[ha[d & (tour == t)], hb[d & (tour == t)]]) for t in C.TOURS}
    return np.array([means.get(t, np.nan) for t in tour])


def b9a_members(P: pd.DataFrame) -> dict:
    (fa, fb), (ta, tb), (oa, ob) = F.ab(P, "bd9a_fat"), F.ab(P, "bd9a_trait"), F.ab(P, "bd9a_odo")
    ha, hb = F.ab(P, "height")
    hbar = _hbar(P)
    aa, ag = F.ab(P, "age")
    autumn = (pd.to_datetime(P["tournament_date"]).dt.month.to_numpy() >= 9).astype(float)
    d61 = oa * np.maximum(aa - AGE_KNEE_61, 0) - ob * np.maximum(ag - AGE_KNEE_61, 0)
    ka, kb = np.maximum(aa - AGE_KNEE_24, 0), np.maximum(ag - AGE_KNEE_24, 0)
    out = {"I-024": (ha - hbar) * fa - (hb - hbar) * fb, "I-024 age": (ha - hbar) * ka - (hb - hbar) * kb,
           "I-061": autumn * d61}
    if USE_I058:
        out["I-058"] = ta * fa - tb * fb
    return out | {"_d61": d61, "_autumn": autumn, "_k28": (ka, kb)}


def combine_b9a(P: pd.DataFrame) -> dict:
    M = b9a_members(P)
    signs = {"I-024": -1, "I-024 age": -1, "I-058": +1, "I-061": -1}
    x = F.block(P, [(M[k], signs[k]) for k in signs if k in M])
    (fa, fb), (ta, tb), (oa, ob) = F.ab(P, "bd9a_fat"), F.ab(P, "bd9a_trait"), F.ab(P, "bd9a_odo")
    (ia, ib), (ha, hb) = F.ab(P, "bd9a_imp"), F.ab(P, "height")
    hbar = _hbar(P)
    ka, kb = M["_k28"]
    named = {"height_a-b": np.nan_to_num(ha - hbar) - np.nan_to_num(hb - hbar), "fat_a-b": fa - fb,
             "age28_a-b": ka - kb, "odo_x_age27_a-b": np.nan_to_num(M["_d61"]),
             "odo_a-b": np.nan_to_num(oa) - np.nan_to_num(ob), "in_age": F.col(P, "in_age"),
             "height_missing_a-b": F.miss_diff(ha, hb), "fat_imputed_share_a-b": ia - ib}
    if USE_I058:
        named["trait_a-b"] = ta - tb
    ctrl, names = F.controls(P, named, x, F.NEAREST.get("B9a"))
    mods = [F.centre(P, fa + fb), F.centre(P, np.nan_to_num(ha - hbar) + np.nan_to_num(hb - hbar)),
            F.centre(P, F.col(P, "age_a") + F.col(P, "age_b")), F.centre(P, M["_autumn"]),
            F.centre(P, F.sym_miss(ha, hb)), F.centre(P, (np.fmax(ia, ib) > 0.5).astype(float))]
    if USE_I058:
        mods.append(F.centre(P, ta + tb))
    mods = np.column_stack(mods)
    tab = {f"bd9a_{k.replace('-', '').replace(' ', '_')}": (M[k], "diff", None) for k in signs if k in M}
    return {"x": x, "controls": ctrl, "control_names": names, "eta_mod_controls": mods, "tabpfn": tab}


HYPOTHESES = [
    {"hid": "B9a", "master": "I-024+I-058+I-061" if USE_I058 else "I-024+I-061 (I-058 dropped: precheck)", "kind": "W", "sign": "+", "weight": 0.5, "trait": "slow",
     "trait_cols": ["height"], "deployment": "diff", "prepare": prepare_b9a, "combine": combine_b9a, "family": "04/11",
     "members": {"I-024 (h x Fat)": "-", "I-024 (h x (age - 28)+)": "-", "I-058": "+", "I-061": "-"}},
]
