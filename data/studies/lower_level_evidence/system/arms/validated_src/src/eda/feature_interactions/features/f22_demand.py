"""B9b, match demand x fatigue (final family: signed sum, members declared -, +, -; weight 0.5; slow; M-set on): I-063 fatigue composed through the
point model (-), I-065 the opponent who exploits fatigue (+), I-066 expected minutes x the load difference (-).
Fat is f20's kernel (tau 3 days); p_A, p_B are Stage 3's pre-match expected serve-point shares (the panel's
s3_p_serve, all matches; sequential own-order ratings).

    I-063  delta_X = kappa Fat_X; D = logit P_iid(p_A - delta_A + eta delta_B, p_B - delta_B + eta delta_A; best of)
           - logit P_iid(p_A, p_B; best of) (Stage 2's iid model, standard tiebreak sets); member m = -D / kappa: the
           composed shift per unit decrement, positive when A is the more tired (sign -, as the card's "- on dFat").
           KAPPA, ETA from serve- and return-point residuals on 2013-2018 (round2/body/prechecks.py, i063; lambda,
           the within-match growth, is not identifiable from match-level box scores: 0)
    I-065  R_X = X's opponent-adjusted pace: per earlier played match with minutes and points, r = log(seconds per
           point / the walk-forward tour x surface norm of f20), then r1 = r - R0_opp / 2 (R0 = the same decayed mean
           unadjusted, the opponent's pre-match value); R = sum w r1 / (sum w + K), w = 2^(-days / 364). K and the
           split-half reliability gate (>= 0.3) from prechecks.py (i065). Missing without any earlier timed match
           (women before 2016): 0 (the shrinkage prior, average pace) with a missing indicator. m = R_A Fat_B - R_B Fat_A
    I-066  E_min = E_points(|logit q|, best of) x (mpp_A + mpp_B) / 2, q = the de-vigged closing price that A wins
           (used as a modulator only), mpp_X = the norm minutes per point x exp(R_X), E_points interpolated from the
           iid simulator's table EPTS (prechecks.py, i066); m = (E_min - its 2014-2021 mean) (Fat_A - Fat_B)
Block: x = -z63 + z65 - z66. Controls: dFat, 1[bo5] dFat, dR, the R-missing and Fat-imputed differences, the nearest
inputs; eta-mod: s = the iid leverage at (p_A, p_B, best of) (I-063's s eta), sum R, sum Fat, E_min, 1[imputed];
the M-set (eta |eta| per tour) for I-066.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.eda.feature_interactions.features import f20_fatigue as F

# constants fixed on 2013-2018 statistic targets (prechecks.py)
KAPPA, ETA = -0.00274, 1.1814   # estimates; |KAPPA| and ETA clipped to [0, 1] are used
K_PACE = 4.419                     # split-half reliability 0.887 (gate >= 0.3 passed)
PACE_HALF_LIFE = 364.0
# expected points of the iid model at symmetric serve shares around 0.64: |logit P| -> points (best of 3, best of 5)
EPTS = {3: ((0.00, 0.40, 0.81, 1.22, 1.66, 2.13, 2.62, 3.15, 3.72, 4.33, 5.00, 5.70, 6.46, 7.27, 8.13, 9.05),
            (164.22, 162.99, 159.90, 156.24, 151.10, 144.61, 138.47, 131.73, 126.01, 119.99, 114.85, 110.32, 105.99, 102.32, 99.03, 96.22)),
        5: ((0.00, 0.50, 1.01, 1.55, 2.13, 2.75, 3.43, 4.18, 5.00, 5.90, 6.87, 7.92, 9.05, 10.26, 11.55, 12.92),
            (270.20, 268.85, 261.67, 251.88, 239.93, 227.11, 213.97, 202.42, 191.23, 181.70, 173.08, 165.90, 159.76, 153.84, 148.92, 144.38))}


def partner(H: pd.DataFrame) -> np.ndarray:
    """Position of the opponent's row of the same match (-1 when absent); cached on H."""
    if "_partner" not in H.columns:
        mid = H["match_id"].astype(str).to_numpy()
        side = H["side"].astype(str).to_numpy()
        pos = pd.Series(np.arange(len(H)), index=pd.MultiIndex.from_arrays([mid, side]))
        pos = pos[~pos.index.duplicated()]
        other = np.where(side == "A", "B", "A")
        H["_partner"] = pos.reindex(pd.MultiIndex.from_arrays([mid, other])).fillna(-1).to_numpy(int)
    return H["_partner"].to_numpy(int)


def pace(H: pd.DataFrame, K: float | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(R1 opponent-adjusted pace, evidence weight sum, raw per-match r) per history row; strictly earlier rows."""
    K = K_PACE if K is None else K
    key = f"_pace_{K:g}"
    if key not in H.columns:
        mins, pts = H["minutes"].to_numpy(float), H["tpw_d"].to_numpy(float)
        ok = H["played"].to_numpy(bool) & np.isfinite(mins) & (mins >= F.MIN_VALID[0]) & (mins <= F.MIN_VALID[1]) \
            & np.isfinite(pts) & (pts > 0)
        r = np.where(ok, np.log(np.where(ok, mins / pts, 1.0) / H["mpp"].to_numpy(float)), np.nan)
        pid, t = H["pid"].to_numpy(), H["t"].to_numpy(float)
        tau = PACE_HALF_LIFE / math.log(2.0)
        den = F.decayed_sum(pid, t, ok.astype(float), tau)
        R0 = F.decayed_sum(pid, t, np.where(ok, r, 0.0), tau) / (den + K)
        p = partner(H)
        r0_opp = np.where(p >= 0, R0[np.maximum(p, 0)], 0.0)
        r1 = np.where(ok, r - 0.5 * r0_opp, np.nan)
        H[key] = F.decayed_sum(pid, t, np.where(ok, r1, 0.0), tau) / (den + K)
        H[key + "_w"], H[key + "_r"] = den, r1
    return H[key].to_numpy(float), H[key + "_w"].to_numpy(float), H[key + "_r"].to_numpy(float)


def prepare_b9b(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = F.history(P, L)
    fat3, imp = F.fat(H)
    R, w, _ = pace(H)
    vals = {"fat": fat3, "imp": imp, "pace": np.where(w > 0, R, np.nan), "mpp": H["mpp"].to_numpy(float)}
    out = {}
    for k, v in vals.items():
        out[f"bd9b_{k}_a"], out[f"bd9b_{k}_b"] = F.at_model(P, H, v)
    return out


def _iid_logit(pa, pb, bo):
    from src.eda.predictability_diagnostic import stage2_iid as M
    pa, pb = np.clip(pa, 0.02, 0.98), np.clip(pb, 0.02, 0.98)
    out = np.full(len(pa), np.nan)
    ok = np.isfinite(pa) & np.isfinite(pb)
    p = M.match_win_by(pa[ok], pb[ok], np.where(bo[ok] == 5, 5, 3), np.full(int(ok.sum()), "TB7@6"))
    out[ok] = np.log(np.clip(p, 1e-9, 1 - 1e-9) / np.clip(1 - p, 1e-9, 1))
    return out


def composed(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(I-063's member -D/kappa, the leverage s) from the panel's columns."""
    pa, pb = F.ab(P, "s3_p_serve")
    fa, fb = F.ab(P, "bd9b_fat")
    bo = F.col(P, "best_of")
    k, e = abs(KAPPA), min(max(ETA, 0.0), 1.0)
    da, db = k * fa, k * fb
    base = _iid_logit(pa, pb, bo)
    D = _iid_logit(pa - da + e * db, pb - db + e * da, bo) - base
    h = 0.005
    lev = (_iid_logit(pa + h, pb - h, bo) - _iid_logit(pa - h, pb + h, bo)) / (4 * h)
    return -D / k, lev


def e_points(P: pd.DataFrame) -> np.ndarray:
    z = np.abs(F.col(P, "in_odds_logit"))
    bo = F.col(P, "best_of")
    out = np.full(len(P), np.nan)
    for b in (3, 5):
        xs, ys = np.asarray(EPTS[b][0], float), np.asarray(EPTS[b][1], float)
        m = (np.where(bo == 5, 5, 3) == b) & np.isfinite(z)
        out[m] = np.interp(z[m], xs, ys)
    return out


def b9b_members(P: pd.DataFrame) -> dict:
    fa, fb = F.ab(P, "bd9b_fat")
    ra, rb = F.ab(P, "bd9b_pace")
    ra0, rb0 = np.nan_to_num(ra), np.nan_to_num(rb)
    m63, lev = composed(P)
    ma, mb = F.ab(P, "bd9b_mpp")
    emin = e_points(P) * (ma * np.exp(ra0) + mb * np.exp(rb0)) / 2
    emin_c = F.centre(P, emin)
    return {"I-063": m63, "I-065": ra0 * fb - rb0 * fa, "I-066": emin_c * (fa - fb), "_lev": lev, "_emin": emin_c}


def combine_b9b(P: pd.DataFrame) -> dict:
    M = b9b_members(P)
    x = F.block(P, [(M["I-063"], -1), (M["I-065"], +1), (M["I-066"], -1)])
    (fa, fb), (ra, rb), (ia, ib) = F.ab(P, "bd9b_fat"), F.ab(P, "bd9b_pace"), F.ab(P, "bd9b_imp")
    bo5 = (F.col(P, "best_of") == 5).astype(float)
    named = {"fat_a-b": fa - fb, "bo5_x_fat_a-b": bo5 * (fa - fb), "pace_a-b": np.nan_to_num(ra) - np.nan_to_num(rb),
             "pace_missing_a-b": F.miss_diff(ra, rb), "fat_imputed_share_a-b": ia - ib}
    ctrl, names = F.controls(P, named, x, F.NEAREST.get("B9b"))
    mods = np.column_stack([F.centre(P, M["_lev"]), F.centre(P, np.nan_to_num(ra) + np.nan_to_num(rb)),
                            F.centre(P, fa + fb), M["_emin"], F.centre(P, (np.fmax(ia, ib) > 0.5).astype(float))])
    return {"x": x, "controls": ctrl, "control_names": names, "eta_mod_controls": mods, "m_set": True,
            "tabpfn": {"bd9b_fat_composed": (M["I-063"], "diff", None), "bd9b_pace_x_oppfat": (M["I-065"], "diff", None),
                       "bd9b_emin_x_dfat": (M["I-066"], "diff", None)}}


HYPOTHESES = [
    {"hid": "B9b", "master": "I-063+I-065+I-066", "kind": "C", "sign": "+", "weight": 0.5, "trait": "slow",
     "deployment": "diff", "prepare": prepare_b9b, "combine": combine_b9b, "family": "12",
     "members": {"I-063": "-", "I-065": "+", "I-066": "-"}},
]
