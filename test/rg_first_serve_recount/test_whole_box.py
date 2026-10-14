"""Offline tests of whole_box.py: Stage 0's checks on an official box, and where its service games come from."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.rg_first_serve_recount import whole_box as WB  # noqa: E402


def match(sv_gms=(10, 10), svpt=(70, 70), score="6-4 6-4", status="completed", **extra) -> pd.DataFrame:
    """One match's two player rows with an official box (off_*) that passes every check unless changed."""
    rows = []
    for i in range(2):
        r = {"match_id": "m1", "score": score, "status": status, "off_ace": 2, "off_df": 2, "off_svpt": svpt[i],
             "off_first_in": 40, "off_first_won": 30, "off_second_won": 15, "off_sv_gms": sv_gms[i],
             "off_bp_saved": 1, "off_bp_faced": 2}
        r.update({k: v[i] for k, v in extra.items()})
        rows.append(r)
    return pd.DataFrame(rows)


def test_a_consistent_box_passes_every_check():
    assert not WB.stage0_checks(match(), "off").any().any()


def test_service_games_off_by_more_than_one_fail_b5_either_way_of_counting_tiebreaks():
    assert WB.stage0_checks(match(sv_gms=(8, 8)), "off")["B5"].all()
    assert not WB.stage0_checks(match(sv_gms=(10, 11)), "off")["B5"].any()           # within one
    tb = match(sv_gms=(12, 12), score="7-6(5) 7-6(3)")                                 # 26 games, 2 tiebreaks
    assert not WB.stage0_checks(tb, "off")["B5"].any()


def test_too_few_serve_points_for_the_games_fail_b9_unless_retired():
    short = match(svpt=(40, 40))                                                       # 80 < 4.5 x 20
    assert WB.stage0_checks(short, "off")["B9"].all()
    assert not WB.stage0_checks(match(svpt=(40, 40), score="6-4 2-1 RET", status="retired"), "off")["B9"].any()


def test_a_first_serve_count_above_serve_points_fails_b1_for_the_match():
    m = match()
    m.loc[0, "off_first_in"] = 80
    out = WB.stage0_checks(m, "off")
    assert out["B1"].all()                     # a match's check: both player rows carry it


def test_service_games_from_the_score_and_the_first_server():
    assert WB.score_sv_gms("6-4 6-4", True) == (10.0, 10.0)
    assert WB.score_sv_gms("7-6(5) 6-4", True) == (11.0, 11.0)          # the tiebreak takes a turn, uncounted
    assert WB.score_sv_gms("6-4 2-1 RET", True) == (7.0, 6.0)           # the unfinished game is not in the score
    assert WB.score_sv_gms("6-4 2-1 RET", False) == (6.0, 7.0)
    assert np.isnan(WB.score_sv_gms("W/O", True)[0])


def test_service_games_come_from_matchbeats_then_the_score_then_the_row_then_blank():
    sides = dict(raw_side=("w", "l"), mb_served_first=(True, False))
    base = dict(mb_svpt=(70, 70), api_svpt=(70, 70), **sides)
    m = match(sv_gms=(np.nan, np.nan), mb_sv_gms_regular=(10, 10), raw_sv_gms=(9, 9), **base)
    out = WB.official_sv_gms(m)
    assert out["sv_gms_from"].eq("matchbeats").all() and out["off_sv_gms"].tolist() == [10, 10]
    incomplete = dict(mb_svpt=(69, 70), api_svpt=(70, 70))                  # MatchBeats misses a point
    m = match(sv_gms=(np.nan, np.nan), mb_sv_gms_regular=(10, 10), raw_sv_gms=(0, 0), **incomplete, **sides)
    out = WB.official_sv_gms(m)
    assert out["sv_gms_from"].eq("derived").all() and out["off_sv_gms"].tolist() == [10, 10]
    m = match(sv_gms=(np.nan, np.nan), mb_sv_gms_regular=(10, 10), raw_sv_gms=(10, 10), **incomplete,
              raw_side=("w", "l"), mb_served_first=(np.nan, np.nan))       # nobody known to serve first
    out = WB.official_sv_gms(m)
    assert out["sv_gms_from"].eq("row").all() and out["off_sv_gms"].tolist() == [10, 10]
    m = match(sv_gms=(np.nan, np.nan), mb_sv_gms_regular=(7, 7), raw_sv_gms=(0, 0), score="6-4 6-4 6-4",
              mb_svpt=(70, 70), api_svpt=(70, 70), raw_side=("w", "l"), mb_served_first=(np.nan, np.nan))
    out = WB.official_sv_gms(m)                                             # neither fits 30 games
    assert out["sv_gms_from"].eq("none").all() and out["off_sv_gms"].isna().all()
