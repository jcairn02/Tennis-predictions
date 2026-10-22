"""Offline tests of the lead's pieces of the source-reconciliation study: the serving-order simulation, the Slam
point recount on synthetic matches (both score encodings), the identities, the three-way vote classes, and the odds
re-check's log-odds mean. No data file is read."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.source_reconciliation import box_engine as E  # noqa: E402
from src.eda.source_reconciliation import lead_check_odds as O  # noqa: E402
from src.eda.source_reconciliation import lead_slam_pbp as S  # noqa: E402


def test_serving_order_counts_hand_worked_scores():
    # (games won by winner, by loser, tiebreaks won by each, sets, service games if the winner served first)
    assert E.games_from_score("6-1 6-7(5) 6-3") == (18, 11, 0, 1, 3, 15, 13)
    assert E.games_from_score("6-4 7-6(5)") == (13, 10, 1, 0, 2, 11, 11)
    assert E.games_from_score("6-3 2-6 7-6(7)") == (15, 15, 1, 0, 3, 15, 14)
    assert E.games_from_score("4-6 7-5 6-4") == (17, 15, 0, 0, 3, 16, 16)
    # a match tiebreak in lieu of a third set: one game for its winner, no service game
    assert E.games_from_score("6-4 3-6 [10-8]") == (10, 10, 1, 0, 3, 10, 9)


def _points(sets, encoding="reset"):
    """Synthetic Slam points. sets: list of games, each (server, winner) with the game won to love by its winner.
    encoding 'reset': the archive writes 0-0 after a game's last point and fills GameWinner (most editions);
    'game': it writes GAME as the winner's score and leaves GameWinner blank (AO/RG 2018-2021)."""
    rows, pn = [], 0
    for s, games in enumerate(sets, start=1):
        for g, (server, winner) in enumerate(games, start=1):
            for k, label in enumerate(["15", "30", "40", "END"], start=1):
                pn += 1
                last = label == "END"
                if last:
                    w_score = "GAME" if encoding == "game" else "0"
                    l_score = "0"
                else:
                    w_score, l_score = label, "0"
                p1, p2 = (w_score, l_score) if winner == 1 else (l_score, w_score)
                if last and encoding == "reset":
                    p1, p2 = "0", "0"
                rows.append({"SetNo": s, "GameNo": g, "PointNumber": pn, "PointServer": server, "PointWinner": winner,
                             "P1Score": p1, "P2Score": p2,
                             "GameWinner": (winner if (last and encoding == "reset") else (0 if encoding == "reset" else "")),
                             "ServeNumber": 1, "P1Ace": 0, "P2Ace": 0, "P1DoubleFault": 0, "P2DoubleFault": 0})
    return pd.DataFrame(rows)


def _six_love_set(first_server):
    other = 2 if first_server == 1 else 1
    return [((first_server if i % 2 == 0 else other), 1) for i in range(6)]


def test_slam_recount_of_a_double_bagel_both_encodings():
    sets = [_six_love_set(1), _six_love_set(1)]       # player 1 wins every game; six games, so P1 serves first again
    for enc in ("reset", "game"):
        rc = S.recount_match(_points(sets, enc))
        assert rc["sets"] == [(6, 0), (6, 0)], enc
        assert rc["games_without_winner"] == 0, enc
        assert (rc["p1_sv_gms"], rc["p2_sv_gms"]) == (6.0, 6.0), enc
        # player 2 broken in each of his six games, each at 0-40 down: one break point faced, none saved
        assert (rc["p2_bp_faced"], rc["p2_bp_saved"]) == (6.0, 0.0), enc
        assert (rc["p1_bp_faced"], rc["p1_bp_saved"]) == (0.0, 0.0), enc
        assert (rc["p1_svpt"], rc["p2_svpt"]) == (24.0, 24.0), enc
        assert rc["p1_first_in"] == 24.0 and rc["serve_number_from"] == "ServeNumber", enc


def test_slam_recount_leaves_the_split_blank_without_a_serve_number():
    p = _points([_six_love_set(1)], "reset")
    p["ServeNumber"] = 0                                 # 'not recorded' in the archive
    rc = S.recount_match(p)
    assert np.isnan(rc["p1_first_in"]) and rc["serve_number_from"] == ""


def _long(rows):
    f = pd.DataFrame(rows)
    for c in ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_won"]:
        if c not in f:
            f[c] = np.nan
    return f


def test_identities_pass_a_consistent_box_and_catch_exchanged_service_games():
    # 6-4 6-4 (winner first): winner serves 10, loser 10; loser broken twice, winner never
    m = pd.DataFrame({"match_id": ["m"], "status": ["completed"], "score": ["6-4 6-4"], "sv_gms_incl_tb": [pd.NA]})
    g = E.games_from_score("6-4 6-4")
    m["g_w"], m["g_l"], m["tb_w"], m["tb_l"], _, m["sv_wf_w"], m["sv_wf_l"] = g
    good = _long([{"reader": "r", "match_id": "m", "player_id": "w", "won": True, "sv_gms": 10, "bp_faced": 1,
                   "bp_saved": 1, "o_sv_gms": 10, "o_bp_faced": 3, "o_bp_saved": 1},
                  {"reader": "r", "match_id": "m", "player_id": "l", "won": False, "sv_gms": 10, "bp_faced": 3,
                   "bp_saved": 1, "o_sv_gms": 10, "o_bp_faced": 1, "o_bp_saved": 1}])
    out = E.identities(good, m)
    assert out["I1"].tolist() == [True, True] and out["I2"].tolist() == [True, True]
    # 6-1 6-7(5) 6-3: the serving order gives 15 / 13; the pair exchanged still fits a first server (I2) but breaks
    # the games identity (I1)
    m2 = pd.DataFrame({"match_id": ["n"], "status": ["completed"], "score": ["6-1 6-7(5) 6-3"],
                       "sv_gms_incl_tb": [pd.NA]})
    g = E.games_from_score("6-1 6-7(5) 6-3")
    m2["g_w"], m2["g_l"], m2["tb_w"], m2["tb_l"], _, m2["sv_wf_w"], m2["sv_wf_l"] = g
    # winner 18 games: 15 served - 0 broken + 3 breaks of the loser = 18 (no tiebreak won); loser 11: 13 - 3 + 0 + 1
    ok = _long([{"reader": "r", "match_id": "n", "player_id": "w", "won": True, "sv_gms": 15, "bp_faced": 2,
                 "bp_saved": 2, "o_sv_gms": 13, "o_bp_faced": 5, "o_bp_saved": 2},
                {"reader": "r", "match_id": "n", "player_id": "l", "won": False, "sv_gms": 13, "bp_faced": 5,
                 "bp_saved": 2, "o_sv_gms": 15, "o_bp_faced": 2, "o_bp_saved": 2}])
    assert E.identities(ok, m2)["I1"].tolist() == [True, True]
    swapped = ok.copy()
    swapped["sv_gms"], swapped["o_sv_gms"] = ok["o_sv_gms"], ok["sv_gms"]
    res = E.identities(swapped, m2)
    assert res["I2"].tolist() == [True, True] and res["I1"].tolist() == [False, False]


def test_log_odds_mean_of_the_available_prices():
    f = pd.DataFrame({"a": [0.6, 0.6, np.nan], "b": [0.6, np.nan, np.nan], "c": [0.8, np.nan, 0.3]})
    got = O.mean_logit(f, ["a", "b", "c"])
    z = (2 * np.log(0.6 / 0.4) + np.log(0.8 / 0.2)) / 3
    assert abs(got.iloc[0] - 1 / (1 + np.exp(-z))) < 1e-12
    assert abs(got.iloc[1] - 0.6) < 1e-12 and abs(got.iloc[2] - 0.3) < 1e-12
