"""I-082, salience-weighted evidence: form earned where nobody watches (MKT-11; math audit family 15, pass, weight 1).

Per player, from his strictly earlier matches (own order, safe by construction), with the two-week profile's decay
(half-life 14 days, best-estimate days) and the originator's evidence constant k = 200 points (the predictive
frontier's, fixed in advance):

    x_c = sum_j d_j n_j z_j / (sum_j d_j n_j + 200),  d_j = 2^(-age_j / 14 days), n_j = points played in match j,
    z_j = the match's opponent-adjusted total points won (Stage B's per-match z_adjperf_tpw, the source of the model's
    adjperf_tpw_2w), over the matches of class c:
        L (low visibility)  Challenger / WTA 125 main draws and qualifying, tour-level and Slam qualifying
        H (high visibility) tour-level main draws (Slams, Finals, 1000s, 500s, 250s); team ties and ITF in neither

Primary x = x_L,A - x_L,B (sign +; a TabPFN difference column). Controls: in_adjperf_tpw_2w (the pooled form, forced),
the nearest form_* input (forced), the three nearest other inputs (Std), the high-visibility analogue x_H,A - x_H,B (for the reported beta_L > beta_H
contrast) and the missing-lower-level indicator (no class-L match with a z in the last 91 days), as A - B. Defined for
every row: a player without class-L evidence has x_L = 0 (the population's centre), flagged by the indicator.
Women's lower-level box scores are thin (WTA 125 is the only lower tier with box scores; ITF has none).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import mkt_common as M

HALF_LIFE, K_POINTS, HAS_DAYS = 14.0, 200.0, 91.0


def stage_b_z(H: pd.DataFrame) -> np.ndarray:
    """Stage B's per-match opponent-adjusted z of total points won, per row of the long table (NaN where absent)."""
    def make():
        z = pd.read_parquet(C.ROOT / "data" / "studies" / "ufc_ideas" / "stageB_adj.parquet",
                            columns=["match_id", "player_id", "z_adjperf_tpw"])
        z["match_id"], z["player_id"] = z["match_id"].astype(str), z["player_id"].astype(str)
        z = z.drop_duplicates(["match_id", "player_id"])
        return H[["match_id", "player_id"]].merge(z, on=["match_id", "player_id"], how="left")["z_adjperf_tpw"] \
            .to_numpy(float)
    return M.cached("stageB_z", (H,), make)


def visibility_class(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    lv = H["level"].astype(str).to_numpy()
    q = H["qualifying"].astype(bool).to_numpy()
    low = (lv == "CH") | (q & np.isin(lv, M.TOUR_LEVELS))
    high = np.isin(lv, M.MAIN_LEVELS) & ~q
    return low, high


def prepare_i082(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    z = stage_b_z(H)
    pts = H["tpw_d"].to_numpy(float)
    ok = np.isfinite(z) & (pts > 0) & H["played"].to_numpy(bool)
    low, high = visibility_class(H)
    out = {}
    for tag, cls in (("salL", low), ("salH", high)):
        m = ok & cls
        w = M.decayed(H, np.where(m, pts, 0.0), HALF_LIFE)
        s = M.decayed(H, np.where(m, pts * z, 0.0), HALF_LIFE)
        out[f"{tag}_a"], out[f"{tag}_b"] = M.at_model(H, P, s / (w + K_POINTS))
    cnt = M.window_sum(H, (ok & low).astype(float), HAS_DAYS)[0]
    out["hasL_a"], out["hasL_b"] = M.at_model(H, P, (cnt > 0).astype(float))
    return out


def combine_i082(P: pd.DataFrame) -> dict:
    la, lb = M.pair(P, "salL")
    ha, hb = M.pair(P, "salH")
    xa, xb = M.pair(P, "hasL")
    x = la - lb
    form = [n for n in M.std_candidates(P) if n.startswith("form_")]
    near_form = [n for n, _ in M.nearest(P, x, 1, exclude=tuple(c for c in M.std_candidates(P) if c not in form))]
    Cs, names = M.std_controls(P, x, force=("adjperf_tpw_2w",) + tuple(near_form))
    ctrl, cn = M.stack([(Cs, names), (ha - hb, "salH diff (high-visibility analogue)"),
                        (xa - xb, "has lower-level evidence, A - B")])
    return {"x": x, "controls": ctrl, "control_names": cn, "tabpfn": {"sal_low": (x, "diff", None)}}


HYPOTHESES = [
    {"hid": "I-082", "master": "I-082", "kind": "W", "sign": "+", "weight": 1.0, "trait": "none",
     "deployment": "TabPFN diff column", "anchor": "I", "prepare": prepare_i082, "combine": combine_i082},
]
