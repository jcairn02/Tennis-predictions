"""B11, on-site rhythm (final family: signed sum, every member declared +, weight 0.5, no trait): I-051's On column (+),
I-075 on-site acclimatisation x novelty of the conditions (+), I-076 event rhythm against a cold start (+). Own matches
only (safe by construction); the regions come from f23's static geography, the indoor statuses from f25.

    on_n_X   X's played matches already at this event (same tournament id; qualifying shares the main draw's id in 98%
             of qualifiers' matches: feasibility audit), strictly before this one
    On_X     log(1 + on_n_X)                                                                      (I-051's On)
    Nov_X    1[surface differs from X's previous event's last match] + 1[indoor status differs, both known]
             + 1[the region differs from the previous event's] (the final family's Nov, rebuttal BOD-R4: the parts
             on disk); altitude dropped (I-077 folded into I-072). Unknown parts count 0; their missing indicators are
             controls
    c_X      1[first match at this event] x 1[X's previous played match was on another surface or > 10 days before]
Members: m1 = On_A - On_B; m2 = On_A Nov_A - On_B Nov_B (I-075, OS = On); m3 = on_n_A c_B - on_n_B c_A (I-076's r_A c_B -
r_B c_A). Each clipped at its 99th percentile of |m| and divided by its SD on 2014-2021, all signed +, summed.
Controls (the union of the members' sets WITHOUT the members themselves): sets_14d, dNov, dc, the parts' missing
indicators, the nearest inputs; eta-mod: sum On, sum Nov, sum on_n, sum c. I-075's dOS and I-076's dr are not controls:
dOS is member m1 itself and dr = d on_n is its linear twin (r 0.9+), which would leave I-051's member unidentified (open
issue for the orchestrator: the union rule and a main-effect member conflict).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions.features import f20_fatigue as F
from src.eda.feature_interactions.features import f23_arrival as G
from src.eda.feature_interactions.features import f25_switch as S

COLD_DAYS = 10.0
STRICT_UNION = False      # True adds I-075's dOS and I-076's dr, which make I-051's member unidentifiable


def per_row_b11(P: pd.DataFrame, H: pd.DataFrame) -> dict:
    G.arrival(H)
    on_n = H["on_n"].to_numpy(float)
    pl = H["pe_last"].to_numpy()
    ok = pl >= 0
    surf = H["surface"].astype(str).to_numpy()
    prev_surf = H["prev_surface"].to_numpy(object)
    s_known = ok & np.array([isinstance(v, str) and v not in ("", "None", "nan") for v in prev_surf])
    sw = np.where(s_known, (surf != prev_surf.astype(str)).astype(float), np.nan)
    ind = S.indoor_status(P, H)
    ind_prev = np.where(ok, ind[np.maximum(pl, 0)], np.nan)
    isw = np.where(np.isfinite(ind) & np.isfinite(ind_prev), (ind != ind_prev).astype(float), np.nan)
    cc = H["trav"].to_numpy(float)                                   # 1[region changed from the previous event]
    nov = np.nan_to_num(sw) + np.nan_to_num(isw) + np.nan_to_num(cc)
    # the cold start: first match here, and the previous played match on another surface or over 10 days before
    k = H["prev_k"].to_numpy()
    kk = np.maximum(k, 0)
    other_surface = (k >= 0) & (surf[kk] != surf)
    long_rest = np.nan_to_num(H["rest"].to_numpy(float), nan=1e9) > COLD_DAYS
    cold = H["first"].to_numpy(float) * (other_surface | long_rest).astype(float)
    return {"on_n": on_n, "nov": nov, "cold": cold, "sw_missing": (~np.isfinite(sw)).astype(float),
            "isw_missing": (~np.isfinite(isw)).astype(float), "cc_missing": (~np.isfinite(cc)).astype(float)}


def prepare_b11(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = F.history(P, L)
    out = {}
    for k, v in per_row_b11(P, H).items():
        out[f"bd11_{k}_a"], out[f"bd11_{k}_b"] = F.at_model(P, H, v)
    return out


def b11_members(P: pd.DataFrame) -> dict:
    (na, nb), (va, vb), (ca, cb) = F.ab(P, "bd11_on_n"), F.ab(P, "bd11_nov"), F.ab(P, "bd11_cold")
    oa, ob = np.log1p(na), np.log1p(nb)
    return {"I-051 On": oa - ob, "I-075": oa * va - ob * vb, "I-076": na * cb - nb * ca}


def combine_b11(P: pd.DataFrame) -> dict:
    M = b11_members(P)
    x = F.block(P, [(M[k], +1) for k in ("I-051 On", "I-075", "I-076")])
    g = lambda k: F.ab(P, f"bd11_{k}")                                   # noqa: E731
    named = {"in_sets_14d": F.col(P, "in_sets_14d"), "nov_a-b": g("nov")[0] - g("nov")[1],
             "cold_a-b": g("cold")[0] - g("cold")[1],
             "surface_switch_missing_a-b": g("sw_missing")[0] - g("sw_missing")[1],
             "indoor_switch_missing_a-b": g("isw_missing")[0] - g("isw_missing")[1],
             "region_change_missing_a-b": g("cc_missing")[0] - g("cc_missing")[1]}
    if STRICT_UNION:                                                 # the literal union rule (see the docstring)
        named["on_a-b"] = np.log1p(g("on_n")[0]) - np.log1p(g("on_n")[1])
        named["r_a-b"] = g("on_n")[0] - g("on_n")[1]
    ctrl, names = F.controls(P, named, x, F.NEAREST.get("B11"))
    (na, nb) = g("on_n")
    mods = np.column_stack([F.centre(P, np.log1p(na) + np.log1p(nb)), F.centre(P, g("nov")[0] + g("nov")[1]),
                            F.centre(P, na + nb), F.centre(P, g("cold")[0] + g("cold")[1])])
    return {"x": x, "controls": ctrl, "control_names": names, "eta_mod_controls": mods,
            "tabpfn": {"bd11_on": (M["I-051 On"], "diff", None), "bd11_on_x_nov": (M["I-075"], "diff", None),
                       "bd11_rhythm_vs_cold": (M["I-076"], "diff", None)}}


# descriptive sensitivities (meta checkpoint 1, R-2 and F-6 interface): B11's pre-declared per-member decomposition, each
# member's standardised column with B11's sign convention (+1), so a B11 result can be attributed to a member only if
# its own column supports it; run once in the batch if its scope includes them, never gating, never in the bundle.
# P carries B11's prepare() columns.
SENSITIVITIES = {f"B11 member {label}": (lambda P, k=key: +1 * F.standardise(P, b11_members(P)[k]))
                 for label, key in (("On", "I-051 On"), ("I-075", "I-075"), ("I-076", "I-076"))}
SENSITIVITY_OF = {name: "B11" for name in SENSITIVITIES}

HYPOTHESES = [
    {"hid": "B11", "master": "I-051(On)+I-075+I-076", "kind": "W", "sign": "+", "weight": 0.5, "trait": "none",
     "deployment": "diff", "prepare": prepare_b11, "combine": combine_b11, "family": "11/14",
     "members": {"I-051 On": "+", "I-075": "+", "I-076": "+"}},
]
