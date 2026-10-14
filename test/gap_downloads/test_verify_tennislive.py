"""The check of TennisLive's listed results against the result files: set scores, verdicts and the nearest row."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M  # noqa: E402
from src.eda.gap_downloads import verify_tennislive as VT  # noqa: E402


def test_listed_sets_put_the_winner_first():
    assert VT.listed_sets("7-6(6) 1-6 6-3", "1") == [(7, 6), (1, 6), (6, 3)]
    assert VT.listed_sets("3-6 6-4 4-6", "2") == [(6, 3), (4, 6), (6, 4)]
    assert VT.listed_sets(None, "1") == []


def frame(rows):
    f = pd.DataFrame(rows)
    f["event_kind"] = f.get("event_kind", "itf")
    f["round"] = f.get("round", None)
    f["k1"], f["k2"] = f["player1_name"].map(M.surname_key), f["player2_name"].map(M.surname_key)
    f["pair"] = M.pair_key(f["k1"], f["k2"])
    f["day"] = pd.to_datetime(f["day"])
    return f


def test_check_takes_the_nearest_row_of_the_same_draw_and_judges_it():
    listed = frame([
        {"event_key": "e1", "match_id": "a", "tour": "M", "draw": "main", "day": "2024-05-08", "winner_side": "2",
         "score": "4-6 6-7(3)", "player1_name": "Ab Cd", "player2_name": "Ef Gh", "end_reason": None},
        {"event_key": "e1", "match_id": "b", "tour": "M", "draw": "qual", "day": "2024-05-05", "winner_side": "1",
         "score": "6-1 2-0", "player1_name": "Ij Kl", "player2_name": "Mn Op", "end_reason": "retired"},
        {"event_key": "e1", "match_id": "c", "tour": "M", "draw": "main", "day": "2024-05-09", "winner_side": "1",
         "score": "6-1 6-1", "player1_name": "Qr St", "player2_name": "Uv Wx", "end_reason": None},
        {"event_key": "e1", "match_id": "d", "tour": "M", "draw": "main", "day": "2024-05-09", "winner_side": "1",
         "score": "6-1 6-1", "player1_name": "Yz Ab", "player2_name": "Cd Ef", "end_reason": None}])
    official = pd.DataFrame([
        {"tour": "M", "draw": "main", "d": "2024-05-06", "tourney_name": "M15 X", "winner_name": "Ef Gh",
         "loser_name": "Ab Cd", "score": "6-4 7-6(3)", "official": "sackmann"},
        {"tour": "M", "draw": "main", "d": "2023-05-06", "tourney_name": "M15 X", "winner_name": "Ab Cd",
         "loser_name": "Ef Gh", "score": "6-0 6-0", "official": "sackmann"},          # a year earlier: outside
        {"tour": "M", "draw": "qual", "d": "2024-05-06", "tourney_name": "M15 X", "winner_name": "Ij Kl",
         "loser_name": "Mn Op", "score": "6-1 2-0 RET", "official": "sackmann"},
        {"tour": "M", "draw": "main", "d": "2024-05-06", "tourney_name": "M15 X", "winner_name": "Uv Wx",
         "loser_name": "Qr St", "score": "1-6 1-6", "official": "sackmann"}])
    official["d"] = pd.to_datetime(official["d"])
    official["round"] = None
    official["kw"], official["kl"] = official["winner_name"].map(M.surname_key), official["loser_name"].map(M.surname_key)
    official["pair"] = M.pair_key(official["kw"], official["kl"])
    out = VT.check(listed, official).set_index("match_id")
    assert out.loc["a", "verdict"] == "agrees" and out.loc["a", "official_score"] == "6-4 7-6(3)"
    assert out.loc["b", "verdict"] == "agrees"                    # a retirement, the same games
    assert out.loc["c", "verdict"] == "winner differs"
    assert out.loc["d", "verdict"] == "no official row"
    summary = VT.summarize(out.assign(year=2024).reset_index())
    assert summary["verdicts"] == {"agrees": 2, "winner differs": 1, "no official row": 1}


def test_verdicts_for_retirements_reversed_scores_and_the_week():
    base = {"k1": "a", "k2": "b", "kw": "a", "winner_side": "1", "official": "tml"}
    assert VT.verdict({**base, "score": "6-1", "end_reason": "retired", "official_score": "6-1 0-0 RET"}) == "agrees"
    assert VT.verdict({**base, "score": "6-4 6-7(4) 6-1", "end_reason": None,
                       "official_score": "4-6 7-6(4) 1-6"}) == "winner agrees, official score written loser first"
    assert VT.verdict({**base, "score": "6-2 6-3", "end_reason": None, "official_score": "7-5 6-1"}) == \
        "winner agrees, score differs"
    # a match tiebreak: the files bracket it, TennisLive writes it as a set
    assert VT.verdict({**base, "score": "4-6 7-5 10-5", "end_reason": None, "official_score": "4-6 7-5 [10-5]"}) == "agrees"
    listed = frame([{"event_key": "e", "match_id": "x", "tour": "M", "draw": "main", "day": "2024-05-15",
                     "winner_side": "1", "score": "6-1 6-1", "player1_name": "Ab Cd", "player2_name": "Ef Gh",
                     "end_reason": None}])
    official = pd.DataFrame([{"tour": "M", "draw": "main", "d": pd.Timestamp("2024-05-06"), "tourney_name": "M15 X",
                              "winner_name": "Ef Gh", "loser_name": "Ab Cd", "score": "6-1 6-1", "official": "sackmann",
                              "round": None}])
    official["kw"], official["kl"] = official["winner_name"].map(M.surname_key), official["loser_name"].map(M.surname_key)
    official["pair"] = M.pair_key(official["kw"], official["kl"])
    # the previous week's meeting at a weekly venue is not this match
    assert VT.check(listed, official)["verdict"].tolist() == ["no official row"]
    assert VT.check(listed.assign(event_kind="slam"), official)["verdict"].tolist() == ["winner differs"]
    # nor is a meeting in another round, where both name the round
    same_week = official.assign(d=pd.Timestamp("2024-05-13"))
    assert VT.check(listed.assign(round="R16"), same_week.assign(round="QF"))["verdict"].tolist() == ["no official row"]
    assert VT.check(listed.assign(round="R16"), same_week.assign(round="R16"))["verdict"].tolist() == ["winner differs"]
    # nor a namesake: the same surnames with another first name (brothers, the many Wangs)
    other = same_week.assign(winner_name="Xy Gh")
    assert VT.check(listed, other)["verdict"].tolist() == ["no official row"]
