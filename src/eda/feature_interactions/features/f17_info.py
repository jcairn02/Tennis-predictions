"""B-INFO, where the market knows less the disagreement weighs more (round-2 family: signed sum, sign +, weight 1,
slow through I-080's rank part; TabPFN difference columns or nudge). No result is read: Delta1 and F are rescaled to the
price's SD (no outcome, no fit on the price), and the result-fitted nudge index N is gone with I-081 and I-087
(withdrawn: rulings MKT-R1, MKT-R2).

    I-080 (+)  Delta1 x (-A): Delta1 = the points view (ratings_iid) minus the results view (offset Elo), each rescaled
               to the price's SD within tour on 2013-2018 (I-034's card); A, the attention index, the mean of four
               components each standardised on the 2013-2018 rows (the originator's window): level (250 = 0, 500 = 1,
               1000 = 2, Slam or Finals = 3), round depth (first round 0, final 1, round robin 0.5), star power
               -min(log rank), crowding -log(1 + the other tour-level main-draw matches of both tours on the same day)
    C-2 (+)    (F - z) x O_min: F = c x (elo_overall + elo_surf_offset), c = SD(price)/SD(offset Elo) per tour on 2014-2018
               (the fit-free Elo forecast of MKT-R4), z the price; O_min = log(min(rank_A, rank_B)) centred per tour on
               2014-2021, the better-ranked player's obscurity (Stage 1's unranked rule, a flag)
    INFO-2 (+) s x Delta(w_q s_q): s = 1[the draw's first main-draw round and exactly one player is a fresh qualifier or
               lucky loser (entry Q/LL, a qualifying match already played at this event, rest <= 1 day)]; w_q s_q = sum
               n z / (sum n + 200) over his earlier qualifying matches at this event (Stage B's per-match z of total
               points won, n points played; 0 for the direct entrant)

Each member divided by its RMS on 2014-2021, summed (all +). Controls: Delta1, F - z, the linear Delta(w_q s_q), I-082's
column and I-076's column (the on-site rhythm, f24_onsite), Std; eta-modulator controls A, O_min, the INFO-2 flag and
the both-unranked flag (each member's s x eta).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions.features import mkt_common as M

QK = 200.0                      # INFO-2's evidence constant (points), the frontier's, as I-082


def prepare_info(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    from src.eda.feature_interactions.features import f24_onsite as ONS
    from src.eda.feature_interactions.features.f12_salience import prepare_i082, stage_b_z
    H = M.hist(L, P)
    rka, rkb, ua, ub = M.ranks(P, H)
    out = {"rkf_a": rka, "rkf_b": rkb, "unr_a": ua, "unr_b": ub}
    es = M.num(P, "es")
    out["crowd_n"] = pd.Series(es).map(pd.Series(es).value_counts()).to_numpy(float) - 1.0
    # INFO-2: on-site qualifying evidence (this event's earlier qualifying matches), w/(w + 200) shrunk
    z, pts = stage_b_z(H), H["tpw_d"].to_numpy(float)
    q = H["qualifying"].astype(bool).to_numpy() & H["played"].to_numpy(bool)
    ok = q & np.isfinite(z) & (pts > 0)
    keys = [H["pc"].to_numpy(), H["tournament_id"].astype(str).to_numpy()]
    cum = {}
    for name, v in (("w", np.where(ok, pts, 0.0)), ("s", np.where(ok, pts * z, 0.0)), ("n", q.astype(float))):
        cum[name] = pd.Series(v).groupby(keys).cumsum().to_numpy() - v          # strictly earlier at this event
    out["qform_a"], out["qform_b"] = M.at_model(H, P, cum["s"] / (cum["w"] + QK))
    out["qn_a"], out["qn_b"] = M.at_model(H, P, cum["n"])
    out["rest_a"], out["rest_b"] = M.at_model(H, P, M.rest_played(H))
    out.update({k: v for k, v in prepare_i082(P, L).items() if k.startswith("salL")})
    out.update(ONS.prepare_b11(P, L))
    return out


def _std_tune(v: np.ndarray, P: pd.DataFrame) -> np.ndarray:
    ok = M.tune(P) & np.isfinite(v)
    return (v - v[ok].mean()) / v[ok].std()


def attention(P: pd.DataFrame) -> np.ndarray:
    lvl = pd.Series(P["level"].astype(str)).map(M.LEVEL_SCORE).to_numpy(float)
    star = -np.minimum(np.log(M.num(P, "rkf_a")), np.log(M.num(P, "rkf_b")))
    crowd = -np.log1p(M.num(P, "crowd_n"))
    comps = [lvl, M.round_depth(P), star, crowd]
    return np.mean(np.column_stack([_std_tune(c, P) for c in comps]), axis=1)


def info2_flag(P: pd.DataFrame) -> np.ndarray:
    """s = 1[the draw's first main-draw round] x 1[exactly one player is a fresh qualifier or lucky loser: entry Q/LL, a
    qualifying match already played at this event, at most one day since his previous played match]."""
    r, ds = M.num(P, "in_round"), M.num(P, "draw_size")
    first = np.select([ds >= 96, ds >= 48, ds >= 28, ds >= 12], [11.0, 12.0, 13.0, 14.0], 15.0)
    fresh = []
    for side in ("a", "b"):
        q = P[f"entry_{side}"].astype(str).isin(["Q", "LL"]).to_numpy()
        fresh.append(q & (M.num(P, f"qn_{side}") >= 1) & (M.num(P, f"rest_{side}") <= 1.0))
    return ((r == first) & (fresh[0] ^ fresh[1])).astype(float)


def combine_binfo(P: pd.DataFrame) -> dict:
    from src.eda.feature_interactions.features import f24_onsite as ONS
    d1, z = M.delta1(P), M.zmkt(P)
    A = attention(P)
    m80 = d1 * (-A)
    F = M.elo_forecast(P)
    lo = np.log(np.minimum(M.num(P, "rkf_a"), M.num(P, "rkf_b")))
    O_min = M.centre(lo, P)
    mc2 = (F - z) * O_min
    s = info2_flag(P)
    dq = np.where(s > 0, M.num(P, "qform_a") - M.num(P, "qform_b"), 0.0)
    dq_lin = np.nan_to_num(M.num(P, "qform_a") - M.num(P, "qform_b"))
    mi2 = s * dq
    x = M.signed_sum([(m80, "+"), (mc2, "+"), (mi2, "+")], P, symmetric=False)
    sal = M.num(P, "salL_a") - M.num(P, "salL_b")
    i076 = ONS.b11_members(P)["I-076"]
    Cs, names = M.std_controls(P, x)
    ctrl, cn = M.stack([(d1, "Delta1"), (F - z, "F - z (fit-free Elo forecast minus price)"),
                        (dq_lin, "Delta on-site qualifying form (INFO-2 linear)"), (sal, "I-082 column"),
                        (i076, "I-076 column")] + ([(Cs, names)] if names else []))
    unr = np.minimum(M.num(P, "unr_a"), M.num(P, "unr_b"))
    E, en = M.stack([(M.centre(A, P), "attention A"), (O_min, "O_min"), (M.centre(s, P), "INFO-2 flag"),
                     (M.centre(unr, P), "both unranked")])
    return {"x": x, "controls": ctrl, "control_names": cn, "eta_mod_controls": E, "eta_mod_names": en,
            "members": {"I-080": m80, "C-2": mc2, "INFO-2": mi2},
            "tabpfn": {"d1_x_negA": (m80, "diff", None), "info2_qform": (mi2, "diff", None),
                       "info2_flag": (s, "context", None)}}


HYPOTHESES = [
    {"hid": "B-INFO", "master": "I-080+C-2+INFO-2", "kind": "S", "sign": "+", "weight": 1.0, "trait": "slow",
     "deployment": "TabPFN diff columns or nudge", "anchor": "I", "prepare": prepare_info, "combine": combine_binfo},
]
