"""B6, transient uncertainty flattens the price (round-2 family: signed sum, sign -, weight 1, slow; nudge). Symmetric
modulators of the price's slope, each centred per tour and standardised on the 2014-2021 rows and summed as they are
(every member is declared -, so the block is tested one-sided negative: the same test as signing each member and
testing +); x_times_eta (the batch forms s * eta), M-set on, never s * eta among the controls (math audit, finding 1).

    I-033 flux     F_pair = sum over the two players of (form - l*)^2: form = adjperf_tpw_2w (the model's two-week
                   opponent-adjusted points form), l* = r * l52 his 52-week level on the form's own scale: l52 = sum z /
                   (n + K3) over his box-score matches of the last 364 days, r = W / (W + K3) the form's shrinkage factor
                   (W the two-week decayed match count; Stage B's tpw constants: half-life 2 weeks, K3 = 10 men, 20
                   women). So form - l* = r (raw two-week mean - l52), free of the shrinkage gap
    BOD-L2 career stage  Sigma |age - 28.5| (Stage 0's pre-match age)
    U_rest (I-054 + BOD-C2, the rulings' addendum)  R^2 - its mean (per tour, 2014-2021), R = [std Sigma log1p(rest) -
                   std Sigma Fat] / sqrt 2, each standardised per tour on 2014-2021: rest = days since the player's previous
                   played match at any level, Fat = I-052's kernel from the body analyst's f20_fatigue (one Fat in the
                   family). The two linear columns correlate -0.944 and are both declared -, so they enter as one
                   pre-declared U (flatter at both ends of one rest axis); R x eta is an eta-modulator control, so U_rest
                   is identified by curvature alone. The separate linear columns are sensitivities
    I-028 within-match excess variance: DROPPED by its pre-declared gate (split-half reliability >= 0.3): pooled 0.051
                   on the corrected history order (0.011 men, 508 players with 50+ matches a half; 0.154 women, 198; 0.108 /
                   -0.005 at 25+ a half), 2010-2018, with the structure analyst's measure (f06_volatility.set_share_excess);
                   between-player variance ~ 0 (`i028_gate`)
    I-034 withdrawn (rulings MKT-R3)

Controls (the family's): Delta Fat and its imputed-share difference (f20), the M-set, Std (nearest to x * eta);
eta-modulator controls: R (the rest axis's linear slope), I-049's early-surface indicator (fitted jointly), and the
missingness rule's indicators (1[imputed Fat share > 0.5], each member's missing indicator).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions.features import mkt_common as M
from src.eda.feature_interactions.features.f10_price_slopes import early
from src.eda.feature_interactions.features.f12_salience import stage_b_z

K3 = {"atp": 10.0, "wta": 20.0}
H3_DAYS, L52_DAYS, AGE_STABLE = 14.0, 364.0, 28.5


def prepare_b6(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    z = stage_b_z(H)
    has = np.isfinite(z) & H["played"].to_numpy(bool)
    k3 = np.where(H["tour"].astype(str).to_numpy() == "atp", K3["atp"], K3["wta"])
    W = M.decayed(H, has.astype(float), H3_DAYS)
    s52, _ = M.window_sum(H, np.where(has, z, 0.0), L52_DAYS)
    n52, _ = M.window_sum(H, has.astype(float), L52_DAYS)
    out = dict(M.body_fat(P, L))
    out["shr_a"], out["shr_b"] = M.at_model(H, P, W / (W + k3))
    out["l52_a"], out["l52_b"] = M.at_model(H, P, s52 / (n52 + k3))
    out["rest_a"], out["rest_b"] = M.at_model(H, P, M.rest_played(H))
    return out


def flux_pair(P: pd.DataFrame) -> np.ndarray:
    out = 0.0
    for s in ("a", "b"):
        out = out + (M.num(P, f"adjperf_tpw_2w_{s}") - M.num(P, f"shr_{s}") * M.num(P, f"l52_{s}")) ** 2
    return out


def std_tour(v: np.ndarray, P: pd.DataFrame) -> np.ndarray:
    """Centred and divided by the SD, per tour, on the 2014-2021 rows."""
    v = np.asarray(v, float)
    out = np.full(len(v), np.nan)
    t, d = M.tours(P), M.disc(P)
    for tr in np.unique(t):
        m = t == tr
        ok = m & d & np.isfinite(v)
        out[m] = (v[m] - v[ok].mean()) / v[ok].std()
    return out


def rest_axis(P: pd.DataFrame) -> np.ndarray:
    """R = [std Sigma log1p(rest) - std Sigma Fat] / sqrt 2 (each standardised per tour on 2014-2021): one rest axis,
    long rest at one end, recent load at the other (the two columns correlate -0.944 once multiplied by eta)."""
    fa, fb = M.pair(P, "bd_fat")
    ra, rb = M.pair(P, "rest")
    rest = np.log1p(np.maximum(ra, 0.0)) + np.log1p(np.maximum(rb, 0.0))
    return (std_tour(rest, P) - std_tour(fa + fb, P)) / np.sqrt(2.0)


def b6_members(P: pd.DataFrame) -> dict:
    """I-033, BOD-L2 and U_rest = R^2 - its mean (per tour, 2014-2021): I-054 and BOD-C2 as one U-shaped member."""
    aa, ab = M.pair(P, "age")
    R = rest_axis(P)
    return {"I-033": flux_pair(P), "BOD-L2": np.abs(aa - AGE_STABLE) + np.abs(ab - AGE_STABLE),
            "U_rest (I-054 + BOD-C2)": M.centre(R ** 2, P)}


def combine_b6(P: pd.DataFrame) -> dict:
    mem = b6_members(P)
    x = M.signed_sum([(v, "+") for v in mem.values()], P, symmetric=True)
    fa, fb = M.pair(P, "bd_fat")
    ia, ib = M.pair(P, "bd_fatimp")
    Cs, names = M.std_controls(P, x * M.eta(P))
    ctrl, cn = M.stack([(fa - fb, "Delta Fat"), (ia - ib, "Fat imputed share, A - B")] + ([(Cs, names)] if names else []))
    R = rest_axis(P)
    mods = [(M.centre(R, P), "R, the rest axis's linear slope"), (early(P), "I-049 early surface (joint)"),
            (M.centre((np.fmax(ia, ib) > 0.5).astype(float), P), "Fat imputed")]
    mods += [(M.centre((~np.isfinite(v)).astype(float), P), f"{k} missing") for k, v in mem.items() if (~np.isfinite(v)).any()]
    E, en = M.stack(mods)
    return {"x": x, "x_times_eta": True, "m_set": True, "controls": ctrl, "control_names": cn,
            "eta_mod_controls": E, "eta_mod_names": en, "members": mem,
            "tabpfn": {"flux_pair": (mem["I-033"], "context", None), "age_dist_pair": (mem["BOD-L2"], "context", None),
                       "rest_axis": (R, "context", None)}}


def i028_gate(L: pd.DataFrame, years=(2010, 2018)) -> dict:
    """I-028's pre-declared result-free gate (math audit: split-half reliability >= 0.3, MAT's threshold), computed with
    the structure analyst's measure and split-half routine (f06_volatility: the per-match excess variance of the
    player's per-set games share beyond the iid at the match's own serve rates; halves by own-order parity). The member
    drops from B6 when the pooled split-half correlation is below 0.3 (it is: see the build note)."""
    from src.eda.feature_interactions.features import f06_volatility as V
    yr = pd.to_datetime(L["tournament_date"]).dt.year
    Lw = L[yr.between(*years).to_numpy()].reset_index(drop=True)
    x = V.set_share_excess(Lw)
    out = {f"min_half_{m}": V.pair_cv_precheck(Lw, x, years=years, min_half=m) for m in (50, 25)}
    pre = out["min_half_50"]
    r = float(np.average([v["split_half_r"] for v in pre.values()], weights=[v["players"] for v in pre.values()]))
    out["pooled_split_half_r"], out["passes"] = r, bool(r >= 0.3)
    return out


HYPOTHESES = [
    {"hid": "B6", "master": "I-033+BOD-L2+U_rest(I-054+BOD-C2)", "kind": "U", "sign": "-", "weight": 1.0, "trait": "slow",
     "deployment": "nudge", "anchor": "I/U", "prepare": prepare_b6, "combine": combine_b6},
]
