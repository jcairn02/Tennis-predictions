"""B-MOTIV, calendar effort (round-2 family: signed sum, sign -, weight 0.5, slow through rank; TabPFN difference
columns). Each member divided by its RMS on 2014-2021 and summed as it is: both are declared -, so the block is tested
one-sided negative.

    I-089/I-090 merged (-)  s x Delta top: s = 1[250 or 500] x 1[a Grand Slam main draw of the tour starts within 8
                            days of this match's earliest start] (all rounds; the math audit's merged column; QF-and-later
                            only is a sensitivity), top = 1[Stage 0's rank at the tournament start <= 20] (unranked 0);
                            the indicator uncentred, as the family writes it (Delta top is held)
    I-089 post (-)          Delta post: post = 1[the player reached a Slam quarter-final or better at another event, that
                            match's latest finish at most 21 days before this match's earliest start]

The Slam start days are calendar facts (the earliest tournament date of each Slam main draw in the long table, known
long in advance), read only up to the panel's last day; the 8- and 21-day windows and the top-20 cut are the
originators' (BOD-25, MKT-24), declared before any result. The points-to-defend secondary is deferred (no points table on
disk). Controls: Delta top (the d of the merged column), Std; eta-modulator control s.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import mkt_common as M

PRE_DAYS, POST_DAYS, TOP = 8.0, 21.0, 20.0


def prepare_motiv(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    gs = (H["level"] == "GS").to_numpy() & ~H["qualifying"].astype(bool).to_numpy()
    day = (pd.to_datetime(H["tournament_date"]) - pd.Timestamp("1970-01-01")).dt.days.to_numpy(float)
    starts = pd.DataFrame({"tour": H["tour"].astype(str).to_numpy()[gs], "tid": H["tournament_id"].astype(str).to_numpy()[gs],
                           "d": day[gs]}).groupby(["tour", "tid"])["d"].min().reset_index()
    es = M.num(P, "es")
    nsd = np.full(len(P), np.nan)
    for tr in C.TOURS:
        d = np.sort(starts.loc[starts["tour"] == tr, "d"].to_numpy())
        m = M.tours(P) == tr
        j = np.searchsorted(d, es[m], side="left")
        nsd[m] = np.where(j < len(d), d[np.minimum(j, len(d) - 1)] - es[m], np.nan)
    qf = gs & (H["round_order"].to_numpy(float) >= 15)
    pc = H["pc"].to_numpy()
    lf_q = pd.Series(np.where(qf, H["lf"].to_numpy(float), np.nan)).groupby(pc).ffill().to_numpy()
    tid = H["tournament_id"].astype(str).to_numpy()
    tid_q = pd.Series(np.where(qf, tid, None)).groupby(pc).ffill().to_numpy()
    last_lf, last_tid = M.shift_own(H, lf_q), pd.Series(tid_q).groupby(pc).shift(1).to_numpy()
    gap = H["es"].to_numpy(float) - last_lf
    post = (np.isfinite(gap) & (gap >= 0) & (gap <= POST_DAYS) & (last_tid != tid)).astype(float)
    out = {"nslam_days": nsd}
    out["post_a"], out["post_b"] = M.at_model(H, P, post)
    return out


def pre_slam(P: pd.DataFrame) -> np.ndarray:
    small = P["level"].astype(str).isin(["T250", "T500"]).to_numpy()
    d = M.num(P, "nslam_days")
    return (small & (d >= 0) & (d <= PRE_DAYS)).astype(float)


def combine_bmotiv(P: pd.DataFrame) -> dict:
    ra, rb = M.pair(P, "rank")
    ta, tb = np.where(np.isfinite(ra), ra <= TOP, False).astype(float), np.where(np.isfinite(rb), rb <= TOP, False).astype(float)
    s = pre_slam(P)
    m1 = s * (ta - tb)                                 # the family's column, the indicator uncentred (Delta top held)
    m2 = M.num(P, "post_a") - M.num(P, "post_b")
    x = M.signed_sum([(m1, "+"), (m2, "+")], P, symmetric=False)     # both declared -: the block is tested negative
    Cs, names = M.std_controls(P, x)
    ctrl, cn = M.stack([(ta - tb, "Delta top-20")] + ([(Cs, names)] if names else []))
    return {"x": x, "controls": ctrl, "control_names": cn, "eta_mod_controls": M.centre(s, P)[:, None],
            "eta_mod_names": ["250/500 within 8 days of a Slam"], "members": {"I-089/I-090": m1, "I-089 post": m2},
            "tabpfn": {"elite_pre_slam": (m1, "diff", None), "post_slam": (m2, "diff", None)}}


HYPOTHESES = [
    {"hid": "B-MOTIV", "master": "I-089+I-090", "kind": "S", "sign": "-", "weight": 0.5, "trait": "slow",
     "deployment": "TabPFN diff columns", "anchor": "I", "prepare": prepare_motiv, "combine": combine_bmotiv},
]
