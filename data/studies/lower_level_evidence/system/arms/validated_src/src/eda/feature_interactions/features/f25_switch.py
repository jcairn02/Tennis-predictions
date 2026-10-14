"""B-SWITCH, own switch state x own style or age (final family: a 4-df Wald test, weight 0.5, slow trait): I-046 (two-sided),
I-047's surface-signed style column (+) and age column (two-sided), I-050 (+). Also each match's indoor status at every
level that has one (reused by f24's B11).

    shape_X  return-heaviness on spw: (D_X - D_cell) - (O_X - O_cell), the panel's surface-IOS defence and offence on
             the match's surface (srfD_spw, srfO_spw: leak-proof per player), centred by tour x surface on 2014-2021
             rows; Sty_X = -shape_X (serve-heaviness)
    q_X      1[surface matches this season < 3] (pieces' season_n; threshold fixed by the math audit)
    New_X    exp(-n_X / 2) log(1 + layoff_X / 30): n = surface matches this season, layoff = days since the last match
             on this surface (missing -> 1,095 days, the cap); nu = 2 fixed by the math audit
    sgn      +1 grass, -1 clay, 0 hard and carpet (servers adapt to grass, returners to clay: the stated three-way term)
    In_X     exp(-m_X / 2) when X's indoor status has switched: m = X's earlier matches with a known status, counted back
             from the latest, that share this match's status, before one with the other status (0 when none had the
             other status; nu = 2 as I-047's); missing when this match's status is unknown
    indoor   Stage 0's flag (men's main tour) or else tennis-data.co.uk's Court (both tours' main tour, linked through
             Stage 1; matched rows, otherwise the event's majority); Challenger and ITF statuses are unknown

Columns (Wald, 4 df): c1 = q_A shape_A - q_B shape_B (I-046); c2 = sgn (New_A Sty_A - New_B Sty_B) (I-047 style);
c3 = New_A (age_A - 28) - New_B (age_B - 28) (I-047 age); c4 = In_A Sty_A - In_B Sty_B (I-050; women's main tour now
included through tennis-data's Court).
Controls: d srfO_spw, d srfD_spw, surf_season and surf_layoff pair differences, dq, dNew, d(New Sty) (the unsigned
two-way term), d age, dIn, In-missing difference, the nearest inputs; eta-mod: sum q, sum shape, sum New, sum age,
sum In, sgn.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import f20_fatigue as F

NU_NEW, NU_IN, Q_SEASON, LAYOFF_CAP, AGE_C = 2.0, 2.0, 3, 1095.0, 28.0
SGN = {"Grass": 1.0, "Clay": -1.0, "Hard": 0.0, "Carpet": 0.0}


# ------------------------------------------------------------------------------------------------
# indoor status at every level that has one

def _court_by_match(max_season: int) -> pd.Series:
    """tennis-data.co.uk's Court (1 indoor, 0 outdoor) per linked Stage 1 match, seasons <= max_season only."""
    from src.eda.feature_interactions.panel import SOURCES
    o = pd.read_parquet(SOURCES["stage1_odds"], columns=["match_id", "year", "td_file", "td_row"])
    o = o[o["td_file"].notna() & (o["year"].astype(int) <= max_season)]
    parts = []
    for f, g in o.groupby("td_file"):
        court = pd.read_parquet(C.ROOT / str(f), columns=["Court"])["Court"].astype(str).str.strip().str.lower()
        v = court.map({"indoor": 1.0, "outdoor": 0.0}).to_numpy(float)
        parts.append(pd.Series(v[g["td_row"].astype(int).to_numpy()], index=g["match_id"].astype(str).to_numpy()))
    s = pd.concat(parts)
    return s[~s.index.duplicated()]


def indoor_status(P: pd.DataFrame, H: pd.DataFrame) -> np.ndarray:
    """Per history row: 1 indoor, 0 outdoor, NaN unknown (cached on H)."""
    if "indoor_k" not in H.columns:
        s0 = H["indoor"].map({True: 1.0, False: 0.0}).astype(float).to_numpy()
        court = H["match_id"].astype(str).map(_court_by_match(int(P["season"].max()))).to_numpy(float)
        known = np.where(np.isfinite(s0), s0, court)
        ev = pd.Series(known).groupby(H["tournament_id"].astype(str).to_numpy()).transform("mean").to_numpy()
        H["indoor_k"] = np.where(np.isfinite(known), known, np.where(np.isfinite(ev), np.round(ev), np.nan))
    return H["indoor_k"].to_numpy(float)


def indoor_switch(P: pd.DataFrame, H: pd.DataFrame) -> np.ndarray:
    """In per history row (see the module docstring), from the player's strictly earlier known-status rows."""
    if "in_switch" in H.columns:
        return H["in_switch"].to_numpy(float)
    s = indoor_status(P, H)
    pid, s_l = H["pid"].to_numpy().tolist(), s.tolist()
    out = [np.nan] * len(pid)
    prev_p, last, run, switched = -1, None, 0, False
    for i in range(len(pid)):
        if pid[i] != prev_p:
            last, run, switched = None, 0, False
        si = s_l[i]
        if si == si:                                        # known status now
            if last is None:
                out[i] = 0.0
            elif si == last:
                out[i] = math.exp(-run / NU_IN) if switched else 0.0
            else:
                out[i] = 1.0                                # the latest known match had the other status: m = 0
            # update the run with this row (it is earlier for the next rows)
            if last is None or si != last:
                switched, run = last is not None, 1
            else:
                run += 1
            last = si
        prev_p = pid[i]
    H["in_switch"] = out
    return H["in_switch"].to_numpy(float)


# ------------------------------------------------------------------------------------------------
# B-SWITCH

def prepare_switch(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = F.history(P, L)
    ia, ib = F.at_model(P, H, indoor_switch(P, H))
    return {"bdsw_in_a": ia, "bdsw_in_b": ib}


def _cell_centred(P: pd.DataFrame, a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Both players' values centred by the tour x surface mean of 2014-2021 rows (both players pooled)."""
    key = P["tour"].astype(str).to_numpy() + "|" + P["surface"].astype(str).to_numpy()
    d = F.disc(P)
    m = pd.Series(np.r_[a[d], b[d]]).groupby(np.r_[key[d], key[d]]).mean()
    mu = pd.Series(key).map(m).to_numpy(float)
    return a - mu, b - mu


def switch_parts(P: pd.DataFrame) -> dict:
    Oa, Ob = _cell_centred(P, *F.ab(P, "ios_srfO_spw"))
    Da, Db = _cell_centred(P, *F.ab(P, "ios_srfD_spw"))
    sha, shb = Da - Oa, Db - Ob
    na, nb = F.ab(P, "surf_season_n")
    la, lb = [np.minimum(np.nan_to_num(v, nan=LAYOFF_CAP), LAYOFF_CAP) for v in F.ab(P, "surf_days_since")]
    newa, newb = np.exp(-na / NU_NEW) * np.log1p(la / 30.0), np.exp(-nb / NU_NEW) * np.log1p(lb / 30.0)
    qa, qb = (na < Q_SEASON).astype(float), (nb < Q_SEASON).astype(float)
    aa, ag = F.ab(P, "age")
    ina, inb = F.ab(P, "bdsw_in")
    sgn = P["surface"].astype(str).map(SGN).fillna(0.0).to_numpy(float)
    return dict(sha=sha, shb=shb, newa=newa, newb=newb, qa=qa, qb=qb, aa=aa, ag=ag, ina=ina, inb=inb, sgn=sgn)


def combine_switch(P: pd.DataFrame) -> dict:
    s = switch_parts(P)
    c1 = s["qa"] * s["sha"] - s["qb"] * s["shb"]
    two = s["newa"] * (-s["sha"]) - s["newb"] * (-s["shb"])
    c2 = s["sgn"] * two
    c3 = s["newa"] * (s["aa"] - AGE_C) - s["newb"] * (s["ag"] - AGE_C)
    c4 = s["ina"] * (-s["sha"]) - s["inb"] * (-s["shb"])
    X = np.column_stack([c1, c2, c3, c4])
    named = {"srfO_spw_a-b": F.col(P, "ios_srfO_spw_a") - F.col(P, "ios_srfO_spw_b"),
             "srfD_spw_a-b": F.col(P, "ios_srfD_spw_a") - F.col(P, "ios_srfD_spw_b"),
             "surf_season_a-b": F.col(P, "in_surf_season_a") - F.col(P, "in_surf_season_b"),
             "surf_layoff_a-b": F.col(P, "in_surf_layoff_a") - F.col(P, "in_surf_layoff_b"),
             "q_a-b": s["qa"] - s["qb"], "new_a-b": s["newa"] - s["newb"], "new_x_sty_a-b": two,
             "in_age": F.col(P, "in_age"),
             "indoor_switch_a-b": np.nan_to_num(s["ina"]) - np.nan_to_num(s["inb"]),
             "indoor_switch_missing_a-b": F.miss_diff(s["ina"], s["inb"])}
    ctrl, names = F.controls(P, named, X, F.NEAREST.get("B-SWITCH"))
    mods = np.column_stack([F.centre(P, s["qa"] + s["qb"]), F.centre(P, s["sha"] + s["shb"]),
                            F.centre(P, s["newa"] + s["newb"]), F.centre(P, s["aa"] + s["ag"]),
                            F.centre(P, np.nan_to_num(s["ina"]) + np.nan_to_num(s["inb"])), F.centre(P, s["sgn"])])
    return {"x": X, "controls": ctrl, "control_names": names, "eta_mod_controls": mods,
            "tabpfn": {"bdsw_early_shape": (c1, "diff", None), "bdsw_new_sty_sgn": (c2, "diff", None),
                       "bdsw_new_age": (c3, "diff", None), "bdsw_in_sty": (c4, "diff", None)}}


HYPOTHESES = [
    {"hid": "B-SWITCH", "master": "I-046+I-047+I-047+I-050", "kind": "W", "sign": "two", "weight": 0.5,
     "trait": "slow", "deployment": "diff", "wald": True, "prepare": prepare_switch, "combine": combine_switch,
     "family": "10", "members": {"I-046": "two", "I-047 style x sgn": "+", "I-047 age": "two", "I-050": "+"}},
]
