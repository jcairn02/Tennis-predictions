"""Price-slope rows of the market lens (round-2 family, docs/studies/feature_interactions/round2/hypothesis_family.md):
the price's slope s * eta with s symmetric; x_times_eta (the batch forms s * eta per base), M-set on, never s * eta as
a control (math audit, finding 1). "Fitted jointly" = the other rows' modulators enter as eta-modulator controls.

    I-036  (+, w 1, slow)    O = max(log rank_A, log rank_B) - the tour's median (2014-2021 rows); unranked = 1500 plus
                             a flag. Joint with I-084, B-FLB, B-LEVER (f02_leverage's modulators, imported)
    I-084  (+, w 0.5, slow)  (Sigma R - mean)/SD, Sigma R = R_A + R_B overall Elo (centred per tour). Controls: eta x level
                             (level indicators), joint with I-036 and B-FLB
    I-049  (+, w 0.5)        E = 1[min(n_A, n_B) < 3] (matches on this surface this season), centred. Joint with B6's
                             BOD-C2 (Sigma log1p rest) and I-054 (Sigma Fat, f20's kernel)
    B-FLB  (+, w 0.5)        LIT-1 + MAT-L1: L = 1[not the event's first main-draw round] (the draw's first round from its
                             size; a Finals round robin is its first stage), HP = 1[Slam or Tour Finals]; each centred
                             and standardised on 2014-2021, summed (both +). Joint with I-036, I-084, B-LEVER

Std: the three inputs nearest to s * eta (2014-2021 rows; odds_logit excluded). Pinnacle (anchor reruns of I-036 [A/I],
I-049 [I/A], B-FLB [A?]) covers 99.5% of 2013-2024 rows and ends in January 2026. No result is read.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import mkt_common as M

UNRANKED = 1500.0
EARLY_N = 3


def prepare_slopes(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    out = dict(M.body_fat(P, L))
    out["rest_a"], out["rest_b"] = M.at_model(H, P, M.rest_played(H))
    for spec in _lever_specs():
        if spec.get("prepare"):
            out.update(spec["prepare"](P, L))
    return out


# ------------------------------------------------------------------------------------------------ modulators

def obscurity(P: pd.DataFrame) -> np.ndarray:
    ra, rb, _, _ = M.ranks_fixed(P, UNRANKED)
    O = np.maximum(np.log(ra), np.log(rb))
    t, d = M.tours(P), M.disc(P)
    for tr in C.TOURS:
        m = t == tr
        O[m] = O[m] - np.median(O[m & d])
    return O


def unranked_flag(P: pd.DataFrame) -> np.ndarray:
    _, _, ua, ub = M.ranks_fixed(P, UNRANKED)
    return M.centre(np.maximum(ua, ub), P)


def prominence(P: pd.DataFrame) -> np.ndarray:
    ra, rb = M.pair(P, "elo_R")
    return M.zsym(ra + rb, P)


def early(P: pd.DataFrame) -> np.ndarray:
    na, nb = M.pair(P, "surf_season_n")
    e = (np.minimum(na, nb) < EARLY_N).astype(float)
    e[~(np.isfinite(na) & np.isfinite(nb))] = np.nan
    return M.centre(e, P)


def sum_fat(P: pd.DataFrame) -> np.ndarray:
    fa, fb = M.pair(P, "bd_fat")
    return M.centre(fa + fb, P)


def sum_rest(P: pd.DataFrame) -> np.ndarray:
    ra, rb = M.pair(P, "rest")
    return M.centre(np.log1p(np.maximum(ra, 0.0)) + np.log1p(np.maximum(rb, 0.0)), P)


def later_round(P: pd.DataFrame) -> np.ndarray:
    r, ds = M.num(P, "in_round"), M.num(P, "draw_size")
    first = np.select([ds >= 96, ds >= 48, ds >= 28, ds >= 12], [11.0, 12.0, 13.0, 14.0], 15.0)
    return np.where(r == 10, 0.0, (r > first).astype(float))


def high_profile(P: pd.DataFrame) -> np.ndarray:
    return P["level"].astype(str).isin(["GS", "FIN"]).to_numpy().astype(float)


def flb_parts(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    return M.zsym(later_round(P), P), M.zsym(high_profile(P), P)


def _lever_specs() -> list:
    """B-LEVER's rows in f02_leverage (the structure analyst's): the block if present, else its members I-001, I-006."""
    from src.eda.feature_interactions.features import f02_leverage as LV
    specs = {s["hid"]: s for s in LV.HYPOTHESES}
    return [specs["B-LEVER"]] if "B-LEVER" in specs else [specs[h] for h in ("I-001", "I-006") if h in specs]


def lever_mods(P: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """B-LEVER's symmetric modulators (its x columns, as f02 builds them) for the joint fits."""
    cols, names = [], []
    for spec in _lever_specs():
        x = np.asarray(spec["combine"](P)["x"], float).reshape(len(P), -1)
        for j in range(x.shape[1]):
            cols.append(x[:, j])
            names.append(f"B-LEVER {spec['hid']}[{j}]")
    return np.column_stack(cols), names


# ------------------------------------------------------------------------------------------------ rows

def _slope(P, s, mods: list[tuple[np.ndarray, str]], tabpfn) -> dict:
    Cs, names = M.std_controls(P, s * M.eta(P))
    E, en = M.stack(mods)
    return {"x": s, "x_times_eta": True, "m_set": True, "controls": Cs if names else None, "control_names": names,
            "eta_mod_controls": E, "eta_mod_names": en, "tabpfn": tabpfn}


def combine_i036(P: pd.DataFrame) -> dict:
    O = obscurity(P)
    L_, HP = flb_parts(P)
    lv, ln = lever_mods(P)
    return _slope(P, O, [(unranked_flag(P), "unranked flag"), (prominence(P), "I-084"), (L_, "B-FLB L"),
                         (HP, "B-FLB HP"), (lv, ln)], {"obscurity": (O, "context", None)})


def combine_i084(P: pd.DataFrame) -> dict:
    lvl, lvn = M.level_dummies(P)
    L_, HP = flb_parts(P)
    return _slope(P, prominence(P), [(lvl, lvn), (obscurity(P), "I-036"), (L_, "B-FLB L"), (HP, "B-FLB HP")], {})


def combine_i049(P: pd.DataFrame) -> dict:
    E = early(P)
    return _slope(P, E, [(sum_rest(P), "B6 BOD-C2"), (sum_fat(P), "B6 I-054")], {"early_surface": (E, "context", None)})


def combine_bflb(P: pd.DataFrame) -> dict:
    L_, HP = flb_parts(P)
    s = M.signed_sum([(later_round(P), "+"), (high_profile(P), "+")], P, symmetric=True)
    lv, ln = lever_mods(P)
    out = _slope(P, s, [(obscurity(P), "I-036"), (prominence(P), "I-084"), (lv, ln)], {})
    out["members"] = {"LIT-1/MAT-L1 L": L_, "LIT-1 HP": HP}
    return out


HYPOTHESES = [
    {"hid": "I-036", "master": "I-036", "kind": "M", "sign": "+", "weight": 1.0, "trait": "slow", "deployment": "nudge",
     "anchor": "A/I", "prepare": prepare_slopes, "combine": combine_i036},
    {"hid": "I-084", "master": "I-084", "kind": "M", "sign": "+", "weight": 0.5, "trait": "slow", "deployment": "nudge",
     "anchor": "", "prepare": prepare_slopes, "combine": combine_i084},
    {"hid": "I-049", "master": "I-049", "kind": "M", "sign": "+", "weight": 0.5, "trait": "none", "deployment": "nudge",
     "anchor": "I/A", "prepare": prepare_slopes, "combine": combine_i049},
    {"hid": "B-FLB", "master": "LIT-1+MAT-L1", "kind": "M", "sign": "+", "weight": 0.5, "trait": "none",
     "deployment": "nudge", "anchor": "A/I", "prepare": prepare_slopes, "combine": combine_bflb},
]
