"""P3, the known-null placebo set (plan.md, adopting the critique's section 6, item 10): features from earlier studies
that tied at the close in more than one design and are not among the 58 inputs. Each is built and screened exactly like
a hypothesis, but sits outside the multiplicity family. If more than one passes the screen's G4 (joint test after the
filter and replication rules, at the hypotheses' Holm threshold), the screen is miscalibrated: stop and investigate.

    KN-TTTOFF     the surface-offset TTT's offset part of z, (o_A - o_B) / c, c = sqrt(2 + s2_A + so2_A + s2_B + so2_B)
                  (rating race: ttt_off ties elo_off at the close, -0.01 [-0.12, +0.10]; ttt_off vs base -0.06)
    KN-SDEV       the surface-IOS study's R2: the eight surface deviations (E_A - E_B, F_A - F_B) of spw, hold, first_won,
                  ace (tied with the odds, -0.06 [-0.18, +0.07]); a Wald block, 8 df
    KN-SNET       the same study's P1 net shift, dnet_spw (tied, +0.03 [-0.06, +0.11]; equal to its placebo)
    KN-ELOSURF    surface-only Elo's log-odds (the Elo-pieces study's literal arm, tied -0.08 [-0.26, +0.10])
    KN-TTTLOGIT   the decided TTT's log-odds (rating race: ttt_blend vs base -0.09 [-0.21, +0.04])
    KN-SURFCAREER log(1 + career surface matches), A - B (the literal arm's pair; tied)

Reads no results. The decided TTT is read from the pre-rebuild copy of match_timing/ttt_timed.parquet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.panel import OLD

L10 = np.log(10) / 400
PRIORITY = ("spw", "hold", "first_won", "ace")


def _none(P, L):
    return {}


def comb_tttoff(P):
    c = np.sqrt(2 + P["ttt_s2_a"] + P["ttt_so2_a"] + P["ttt_s2_b"] + P["ttt_so2_b"])
    return {"x": ((P["ttt_off_a"] - P["ttt_off_b"]) / c).to_numpy(float), "controls": None, "control_names": []}


def comb_sdev(P):
    cols = [P[f"ios_srf{k}_{s}_a"] - P[f"ios_srf{k}_{s}_b"] for s in PRIORITY for k in ("E", "F")]
    return {"x": np.column_stack(cols).astype(float), "controls": None, "control_names": []}


def comb_snet(P):
    eff = (P["ios_srfO_spw_a"] - P["ios_srfO_spw_b"]) + (P["ios_srfD_spw_a"] - P["ios_srfD_spw_b"])
    cur = (P["ios_curO_spw_a"] - P["ios_curO_spw_b"]) + (P["ios_curD_spw_a"] - P["ios_curD_spw_b"])
    return {"x": (eff - cur).to_numpy(float), "controls": None, "control_names": []}


def prep_elosurf(P, L):
    t = pd.read_parquet(C.ROOT / "data" / "studies" / "surface_elo_pieces" / "pieces.parquet",
                        columns=["match_id", "S_a", "S_b", "R_a", "R_b"])
    t["match_id"] = t["match_id"].astype(str)
    t = P[["match_id"]].merge(t, on="match_id", how="left", validate="one_to_one")
    s_a = np.where(np.isfinite(t["S_a"]), t["S_a"], t["R_a"])
    s_b = np.where(np.isfinite(t["S_b"]), t["S_b"], t["R_b"])
    return {"elo_surface_a": s_a, "elo_surface_b": s_b}


def comb_elosurf(P):
    return {"x": (L10 * (P["elo_surface_a"] - P["elo_surface_b"])).to_numpy(float), "controls": None,
            "control_names": []}


def prep_tttlogit(P, L):
    t = pd.read_parquet(OLD / "match_timing" / "ttt_timed.parquet", columns=["match_id", "p_ttt_timed"])
    t["match_id"] = t["match_id"].astype(str)
    p = P[["match_id"]].merge(t, on="match_id", how="left", validate="one_to_one")["p_ttt_timed"].to_numpy(float)
    z = np.log(np.clip(p, 1e-9, 1 - 1e-9) / np.clip(1 - p, 1e-9, 1))
    return {"ttt_half_a": z / 2, "ttt_half_b": -z / 2}            # A's and B's halves: A - B gives the log-odds


def comb_tttlogit(P):
    return {"x": (P["ttt_half_a"] - P["ttt_half_b"]).to_numpy(float), "controls": None, "control_names": []}


def comb_surfcareer(P):
    return {"x": (np.log1p(P["elo_NS_a"]) - np.log1p(P["elo_NS_b"])).to_numpy(float), "controls": None,
            "control_names": []}


def _spec(hid, combine, prepare=_none, wald=False, sign="two"):
    return {"hid": hid, "master": "P3", "kind": "known-null", "sign": sign, "weight": 1.0, "trait": "none",
            "deployment": "none", "wald": wald, "prepare": prepare, "combine": combine, "placebo": True}


HYPOTHESES = [
    _spec("KN-TTTOFF", comb_tttoff),
    _spec("KN-SDEV", comb_sdev, wald=True),
    _spec("KN-SNET", comb_snet),
    _spec("KN-ELOSURF", comb_elosurf, prep_elosurf),
    _spec("KN-TTTLOGIT", comb_tttlogit, prep_tttlogit),
    _spec("KN-SURFCAREER", comb_surfcareer),
]
