"""Stage 1 of the shot-level study: the point adapters' conventions and the per-match statistics, on hand-made points
whose answers are worked out by hand.

Run: ./python.sh -m pytest test/shot_level/test_stage1.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import points as P  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402

E = P.END


# ------------------------------------------------------------------------------------------------
# Point conventions

@pytest.mark.parametrize("first, second, expected", [
    # serve wide, forehand return, backhand, forehand winner by the server on shot 4? No: shots are serve (1), f (2,
    # returner), b (3, server), f* (4, returner): a winner by the returner
    ("4f2b3f1*", None, dict(rally=4, end=E["winner"], ender_rel=2, place=3, wing=1)),
    # an ace down the T
    ("6*", None, dict(rally=1, end=E["ace"], ender_rel=1, place=1)),
    # an unreturnable serve: a forced error by the returner on shot 2
    ("5#", None, dict(rally=2, end=E["forced"], ender_rel=2, place=2)),
    # second serve; a short return (depth 7), then the server's backhand slice error on shot 3
    ("4n", "5f37s1@", dict(rally=3, end=E["unforced"], ender_rel=1, serve_no=2, ret_deep=0, wing=2)),
    # double fault
    ("6d", "4w", dict(rally=0, end=E["df"], ender_rel=1, serve_no=2)),
    # deep return (9); the server comes in (+) and wins with a backhand volley on shot 5? shots: f19 (2), f+ (3), b (4),
    # z* (5): the volley on shot 5 is the server's
    ("4f19f+1b2z3*", None, dict(rally=5, end=E["winner"], ender_rel=1, ret_deep=1, srv_net=1)),
])
def test_mcp_parse(first, second, expected):
    rally, end, rel, sn, place, rdeep, wing, srv_net, ret_net = P.mcp_parse(first, second)
    got = dict(rally=rally, end=end, ender_rel=rel, serve_no=sn, place=place, ret_deep=rdeep, wing=wing, srv_net=srv_net)
    for k, v in expected.items():
        assert got[k] == v, (k, got)


def test_sentence_parts():
    end, wins, wing = P.sentence_parts(pd.Series([
        "A. Gray loses the point with a forehand forced error",
        "E. Lys wins the point with an ace",
        "J. Niemeier loses the point with a backhand unforced error",
        "A. Kalinskaya wins the point with a forehand winner",
        "X wins the point"]))
    assert list(end) == [E["forced"], E["ace"], E["unforced"], E["winner"], 0]
    assert list(wins) == [0, 1, 0, 1, 1]
    assert list(wing) == [1, 0, 2, 1, 0]


def test_shot_points_to_schema():
    """Infosys / SirGenkii layout: the server follows from the ending shot's parity; a serve won without an ace becomes
    a forced error by the returner on shot 2."""
    d = pd.DataFrame({"key": "m", "set_no": 1, "game_label": 1, "point": [1, 2, 3, 4], "serve_no": [1, 1, 2, 1],
                      "shot": [1, 1, 2, 5], "team": [1, 1, 2, 1], "won": [True, True, False, True],
                      "end": [E["ace"], 0, E["unforced"], E["winner"]], "speed": np.nan, "net1": 0, "net2": 0})
    out = P.shot_points_to_schema(d)
    assert list(out["server"]) == [1, 1, 1, 1]
    assert list(out["winner"]) == [1, 1, 1, 1]
    assert list(out["end"]) == [E["ace"], E["forced"], E["unforced"], E["winner"]]
    assert list(out["ender"]) == [1, 2, 2, 1]
    assert list(out["rally"]) == [1, 2, 2, 5]


# ------------------------------------------------------------------------------------------------
# Per-match statistics

def one_match() -> pd.DataFrame:
    rows = [  # server, winner, rally, end, ender, serve_no, speed, place, net1, net2, ret_deep, wing
        (1, 1, 1, E["ace"], 1, 1, 200, 1, 0, 0, -1, 0),
        (1, 2, 0, E["df"], 1, 2, np.nan, 0, 0, 0, -1, 0),
        (1, 1, 2, E["forced"], 2, 1, 190, 3, 0, 0, -1, 0),
        (1, 1, 3, E["winner"], 1, 1, 180, 1, 0, 0, 1, 1),
        (1, 2, 2, E["winner"], 2, 2, 150, 2, 0, 0, -1, 2),
        (1, 2, 6, E["unforced"], 1, 1, 185, 3, 1, 0, 0, 2),
        (2, 2, 9, E["forced"], 1, 1, 170, 1, 0, 1, 1, 1),
        (2, 1, 4, E["unforced"], 2, 2, 140, 2, 0, 0, 0, 1),
        (2, 2, 1, E["ace"], 2, 1, 175, 3, 0, 0, -1, 0),
        (2, 1, 10, E["winner"], 1, 1, 172, 1, 0, 0, 1, 1),
    ]
    df = pd.DataFrame(rows, columns=["server", "winner", "rally", "end", "ender", "serve_no", "speed", "place", "net1",
                                     "net2", "ret_deep", "wing"])
    df.insert(0, "match_id", "m1")
    df["seq"] = np.arange(len(df))
    df["set_no"], df["game_key"] = 1, 0
    return df


def test_match_stats_by_hand():
    st = T.match_stats(one_match()).set_index("side")
    a, b = st.loc["A"], st.loc["B"]
    rate = lambda r, s: (r[f"{s}_n"], r[f"{s}_d"])
    assert rate(a, "srv_quick") == (1, 3)          # serve points with the return in play: 4, 5, 6; won quickly: 4
    assert rate(a, "ret_quick") == (1, 3)          # return points in play: 7, 8, 10; won within 4 shots: 8
    assert rate(a, "rally5") == (1, 3)             # 5+ shots: 6, 7, 10; A won 10
    assert rate(a, "rally9") == (1, 2)
    assert rate(a, "ret_inplay") == (3, 3)         # B's serves that were neither aces nor double faults: 7, 8, 10
    assert rate(a, "long_share") == (3, 9)
    assert rate(a, "winner_rate") == (2, 10)
    assert rate(a, "error_rate") == (2, 10)
    assert rate(a, "ue_share") == (1, 2)
    assert rate(a, "w_ratio") == (2, 4)
    assert rate(a, "spd1") == (755, 4)
    assert rate(a, "spd2") == (150, 1)
    assert rate(a, "net_rate") == (1, 10) and rate(a, "net_won") == (0, 1)
    assert rate(b, "net_won") == (1, 1)
    assert rate(a, "t_share") == (2, 4) and rate(a, "wide_share") == (2, 4)
    assert rate(a, "deep_ret") == (2, 3)
    assert rate(a, "bh_ue_share") == (1, 1) and rate(a, "fh_win_share") == (2, 2)
    assert rate(b, "srv_quick") == (0, 3)


def test_gates_drop_partial_matches():
    """A match where most rally lengths are unknown carries no rally statistic."""
    m = one_match()
    m.loc[[0, 2, 3, 4, 5], "rally"] = -1
    st = T.match_stats(m).set_index("side")
    assert st.loc["A", "srv_quick_d"] == 0 and st.loc["A", "rally5_d"] == 0
    assert st.loc["A", "winner_rate_d"] == 10           # the ending family is unaffected


# ------------------------------------------------------------------------------------------------
# The point sequence

def two_sets() -> pd.DataFrame:
    """Set 1, 6-3 to A: A holds, A breaks, A holds (consolidates), B holds, A is broken, A breaks back, A holds,
    B holds, A holds serving for the set at 5-3. Set 2, 6-0 to A: three breaks, each consolidated, the last hold
    serving for the set at 5-0. Every game is four straight points to its winner."""
    games = [(1, 1), (2, 1), (1, 1), (2, 2), (1, 2), (2, 1), (1, 1), (2, 2), (1, 1),
             (2, 1), (1, 1), (2, 1), (1, 1), (2, 1), (1, 1)]
    rows, gk = [], 0
    for i, (srv, win) in enumerate(games):
        set_no = 1 if i < 9 else 2
        for _ in range(4):
            rows.append(("m2", set_no, gk, srv, win, 1))
        gk += 1
    df = pd.DataFrame(rows, columns=["match_id", "set_no", "game_key", "server", "winner", "serve_no"])
    df["seq"] = np.arange(len(df))
    return df


def test_sequence_by_hand():
    gf = T.game_frame(two_sets())
    assert T.sequence_ok(gf).all()
    st = T.sequence_stats(two_sets()).set_index("side")
    a, b = st.loc["A"], st.loc["B"]
    assert (a["consolidate_n"], a["consolidate_d"]) == (5, 5)
    assert (a["break_back_n"], a["break_back_d"]) == (1, 1)
    assert (a["serve_set_n"], a["serve_set_d"]) == (2, 2)
    assert (b["consolidate_n"], b["consolidate_d"]) == (0, 1)
    assert (b["break_back_n"], b["break_back_d"]) == (0, 5)
    assert b["serve_set_d"] == 0
    # A's serve points: 8 games x 4, 28 won; the one break point A faced was lost
    assert a["pressure_srv_d"] == 1 and a["pressure_srv_n"] == pytest.approx(0 - 28 / 32)
    assert a["after_loss_d"] == 3 and a["after_loss_n"] == pytest.approx(3 * (0 - 28 / 32))
    assert a["first_in_pressure_d"] == 1 and a["first_in_pressure_n"] == pytest.approx(0.0)


def test_sequence_rejects_a_missing_game():
    df = two_sets()
    # without B's hold at 1-2 and A's hold for the set at 5-3, set 1 reads 5-2: not a finished set, and not the last
    # set (the last set may be unfinished in a retirement)
    df = df[~df["game_key"].isin([3, 8])].copy()
    df["seq"] = np.arange(len(df))
    gf = T.game_frame(df)
    assert not T.sequence_ok(gf).all()
