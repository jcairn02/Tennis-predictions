"""The point-sequence study: replay rules, servers, the SofaScore server fix, the marcosjn2 tie-break trailing point,
Sackmann's strings, linking orientation and the official-score check, on small hand-made sequences whose answers are
worked out by hand.

Run: ./python.sh -m pytest test/point_sequence/test_point_sequence.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import adapters as A  # noqa: E402
from src.eda.point_sequence import build as B  # noqa: E402
from src.eda.point_sequence import replay as R  # noqa: E402


def game(w: int) -> list[int]:
    """A game won to love by player w."""
    return [w] * 4


def to_six_all() -> list[int]:
    """Twelve love games, alternately won: 6-6."""
    out = []
    for k in range(12):
        out += game(1 if k % 2 == 0 else 2)
    return out


TOUR = {"best_of": 3, "best_of_certain": True, "format": "standard", "year": 2024, "level": "T250"}


# ------------------------------------------------------------------------------------------------
# Replay rules

def test_straight_sets_complete_and_score_text():
    pts = game(1) * 12
    r = R.replay(pts)
    assert r.status == "complete" and r.winner == 1 and r.stop == 48
    assert R.score_text(r.sets) == "6-0 6-0"
    assert r.set_no[0] == 1 and r.set_no[-1] == 2 and r.game_no[-1] == 6 and r.pt_no[-1] == 4


def test_deuce_game_needs_two_clear():
    # 40-40, advantage player 2, deuce, then player 1 wins two: a 10-point game
    g = [1, 1, 1, 2, 2, 2, 2, 1, 1, 1]
    r = R.replay(g + game(1) * 5 + game(1) * 6)
    assert r.status == "complete"
    assert r.pt_no[9] == 10 and r.game_idx[9] == 0 and r.game_idx[10] == 1


def test_tiebreak_to_seven_with_two_clear():
    # 6-6, then a tie-break that reaches 6-6 and ends 8-6; the second set 6-0
    tb = [1, 2] * 6 + [1, 1]
    r = R.replay(to_six_all() + tb + game(1) * 6)
    assert r.status == "complete"
    assert r.sets[0] == (7, 6, 8, 6)
    assert R.score_text(r.sets) == "7-6(6) 6-0"
    assert r.is_tb[48:62].all() and not r.is_tb[47] and not r.is_tb[62]


def test_final_set_ten_point_tiebreak_at_a_slam():
    first = to_six_all() + [1] * 7                    # 7-6(0)
    second = game(2) * 6                              # 0-6
    ao2023 = {"best_of": 3, "best_of_certain": True, "slam": "AO", "year": 2023}
    # 6-6 in the third, then a 10-point tie-break: 4-4, then six straight points, 10-4
    full10 = first + second + to_six_all() + [1, 2] * 4 + [1] * 6
    r = R.replay_match(full10, ao2023)
    assert r.status == "complete" and r.primary and r.rule.final == "tb10" and r.sets[2] == (7, 6, 10, 4)
    # under the 7-point rule the same points end the tie-break at 7-4 and leave three points after the match
    assert R.replay(full10, R.Rules(3, "tb")).status == "overlong"
    # a deciding tie-break that stops at 7-4: incomplete under the Slam's rule; at a Slam the other deciding-set rules
    # are fallbacks, so it completes under the 7-point rule, flagged as not the first candidate (build.py then trusts
    # it only if the official score agrees)
    seven = first + second + to_six_all() + [1, 2] * 4 + [1] * 3
    s = R.replay_match(seven, ao2023)
    assert s.status == "complete" and not s.primary and s.rule.final == "tb" and s.sets[2] == (7, 6, 7, 4)


def test_advantage_final_set_and_wimbledon_twelve_all():
    base = to_six_all() + [1] * 7 + game(2) * 6
    adv = base + to_six_all() + game(1) * 2                     # 8-6 in the third
    r = R.replay_match(adv, {"best_of": 3, "best_of_certain": True, "slam": "RG", "year": 2018})
    assert r.status == "complete" and r.rule.final == "adv" and r.sets[2] == (8, 6, None, None)
    w12 = base + to_six_all() + to_six_all() + [2] * 7          # 12-12, then a 7-point tie-break
    r = R.replay_match(w12, {"best_of": 3, "best_of_certain": True, "slam": "W", "year": 2019})
    assert r.status == "complete" and r.rule.final == "tb12" and r.sets[2] == (12, 13, 0, 7)


def test_tour_match_is_not_rescued_by_an_unusual_rule():
    # a tour match whose deciding-set tie-break is followed by a stray point: under 7-point tie-breaks it is overlong;
    # an advantage deciding set would make it "complete" (8-6), but that rule cannot apply at a tour event
    seq = to_six_all() + [1] * 7 + game(2) * 6 + to_six_all() + [1] * 7 + [1]
    r = R.replay_match(seq, TOUR)
    assert r.status == "overlong" and r.rule.final == "tb"
    loose = R.replay_match(seq, {"best_of": 3, "best_of_certain": False})
    assert loose.status == "complete" and not loose.primary


def test_best_of_five_and_points_after_the_end():
    seq = game(1) * 18
    assert R.replay_match(seq, {"best_of": 5, "best_of_certain": True}).status == "complete"
    assert R.replay_match(seq, TOUR).status == "overlong"
    r = R.replay(seq + [1], R.Rules(5))
    assert r.status == "overlong" and r.stop == 72


def test_partial_retirement_and_unknown_winner():
    seq = game(1) * 6 + game(2) * 2 + [1, 1]
    r = R.replay(seq)
    assert r.status == "partial" and r.games == (0, 2) and r.points == (2, 0)
    assert R.score_text(r.sets, r.games, 1, partial=True) == "6-0 0-2"
    u = R.replay([1, 1, 0, 1])
    assert u.status == "unknown" and u.stop == 2 and u.set_no[2] == -1


def test_match_tiebreak_format():
    seq = game(1) * 6 + game(2) * 6 + [2, 1] * 8 + [2, 2]           # 6-0 0-6 [8-10]
    r = R.replay_match(seq, {"best_of": 3, "best_of_certain": True, "format": "match_tiebreak"})
    assert r.status == "complete" and r.winner == 2 and r.sets[2] == (0, 1, 8, 10)
    assert R.score_text(r.sets) == "6-0 0-6 [8-10]"


def test_short_sets_no_ad():
    # sets to four with a tie-break at 3-3 and a deciding point at deuce
    s = []
    for k in range(6):
        s += game(1 if k % 2 == 0 else 2)
    s += [1] * 7                                       # 4-3(0)
    deciding_point_game = [1, 1, 1, 2, 2, 2, 1]        # 40-40, then one point decides
    seq = s + (deciding_point_game + game(1) * 3) * 2
    r = R.replay_match(seq, {"best_of": 5, "best_of_certain": True, "format": "short_sets"})
    assert r.status == "complete" and r.rule.no_ad and R.score_text(r.sets) == "4-3(0) 4-0 4-0"


def test_rule_servers_alternate_by_game_and_in_tiebreaks():
    tb = [1, 2, 1, 2, 1, 2, 1, 1, 1, 1]                 # 3-3, then four straight: 7-3 in ten points
    r = R.replay(to_six_all() + tb + game(2))
    assert r.sets[0] == (7, 6, 7, 3)
    srv = R.rule_servers(r.game_idx, r.pt_no, r.is_tb, 1)
    assert srv[0] == 1 and srv[4] == 2 and srv[47] == 2
    # the tie-break (game 13 of the match) is served first by player 1, then 2, 2, 1, 1, 2, 2, 1, 1, 2
    assert srv[48:58].tolist() == [1, 2, 2, 1, 1, 2, 2, 1, 1, 2]
    # the next set's first game is served by the player who received first in the tie-break
    assert srv[58:62].tolist() == [2, 2, 2, 2]
    s0, agree = R.best_first_server(r.game_idx, r.pt_no, r.is_tb, 3 - srv)
    assert s0 == 2 and agree == 1.0


def test_boundary_mismatches_count_disagreeing_game_starts():
    derived = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    assert R.boundary_mismatches(derived, np.array([5, 5, 5, 5, 6, 6, 6, 6]), 8) == 0
    assert R.boundary_mismatches(derived, np.array([5, 5, 5, 6, 6, 6, 6, 6]), 8) == 2


# ------------------------------------------------------------------------------------------------
# SofaScore: games, the implied last point, and the server fix

def test_sofascore_regular_game_implies_its_last_point():
    states = [("15", "0", 0), ("30", "0", 1), ("40", "0", 0)]
    w, codes, note = A._sofa_game(states, False, 1)
    assert w == [1, 1, 1, 1] and codes == [0, 1, 0, 0] and note == "ok"
    # a game whose listed states stop at deuce cannot end on the implied point: flagged, not repaired
    w, _, note = A._sofa_game([("40", "40", 0)], False, 2)
    assert note == "unended"


def test_sofascore_tiebreak_lists_its_last_state_or_implies_it():
    tb = [(str(h), str(a), 0) for h, a in [(1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)]]
    w, _, note = A._sofa_game(tb, True, 1)
    assert w == [1, 2, 1, 1, 1, 1, 1, 1] and note == "ok"
    w, _, note = A._sofa_game(tb[:-1], True, 1)
    assert w[-1] == 1 and len(w) == 8 and note == "implied"


def test_sofascore_server_fix_follows_the_alternation_not_a_shifted_field():
    # four games of one point each for brevity; the per-game field of game 3 names the NEXT game's server (2 instead
    # of 1); an ace is coded in game 3, won by player 1
    gidx = np.array([0, 1, 2, 3])
    is_tb = np.zeros(4, int)
    pt = np.ones(4, int)
    field = np.array([1, 2, 2, 2])
    srv, s0, agree = A.derive_servers(gidx, is_tb, pt, field, field, 0)
    assert s0 == 1 and srv.tolist() == [1, 2, 1, 2] and agree == 0.75
    ace_winner = 1
    assert srv[2] == ace_winner and field[2] != ace_winner


def test_sofascore_tiebreak_servers_come_from_the_rules():
    # a tie-break as game 12 of the match (index 12): its first server is the match's first server; the field on a
    # tie-break is ignored
    gidx = np.array([12] * 6)
    pt = np.arange(1, 7)
    srv, s0, _ = A.derive_servers(gidx, np.ones(6, int), pt, np.array([2] * 6), np.zeros(6, int), 0)
    assert s0 == 1 and srv.tolist() == [1, 2, 2, 1, 1, 2]


# ------------------------------------------------------------------------------------------------
# marcosjn2: the trailing tie-break point

def _record(sets: list[list[tuple]], winner: str = "1") -> dict:
    return {"key": "m1", "meta": {"event_id": 1, "gender": "M", "date": "2020-02-03"},
            "tournament": {"name": "Somewhere", "unique_name": "Somewhere", "points": 250, "ground_type": "Hard"},
            "round": {"name": "Round of 32"},
            "players": {"home": {"name": "Ann Home"}, "away": {"name": "Bea Away"}},
            "sequence": {"match_winner": winner, "sets": [
                {"set_number": i + 1, "set_winner": "1", "game_sequence": "",
                 "games": [{"game_number": j + 1, "is_tiebreak": tb, "server_side": side, "point_sequence": ps,
                            "game_winner": gw} for j, (ps, tb, side, gw) in enumerate(s)]}
                for i, s in enumerate(sets)]}}


def test_marcosjn2_drops_the_trailing_tiebreak_point_only(tmp_path):
    games = []
    for k in range(12):
        games.append(("1111" if k % 2 == 0 else "0000", False, "home" if k % 2 == 0 else "away",
                      "1" if k % 2 == 0 else "0"))
    tb_trailing = ("1111111" + "1", True, "away", "1")       # 7-0, then the appended extra point to the winner
    second = [("1111", False, "away" if k % 2 == 0 else "home", "1") for k in range(6)]
    path = tmp_path / "m.jsonl"
    path.write_text(json.dumps(_record([games + [tb_trailing], second])) + "\n", encoding="utf-8")
    P, rows = A._marcosjn2_file(str(path))
    assert rows[0]["tb_trailing_dropped"] == 1
    assert rows[0]["n_points"] == 48 + 7 + 24
    r = R.replay(P["winner"])
    assert r.status == "complete" and R.score_text(r.sets) == "7-6(0) 6-0"
    # the tie-break's servers follow the rules (first server: player 1), not its 'away' field
    tb = slice(48, 55)
    assert P["server"][tb].tolist() == [1, 2, 2, 1, 1, 2, 2]


def test_marcosjn2_keeps_a_tiebreak_without_the_extra_point(tmp_path):
    games = [("1111" if k % 2 == 0 else "0000", False, "home" if k % 2 == 0 else "away", "1" if k % 2 == 0 else "0")
             for k in range(12)]
    path = tmp_path / "m.jsonl"
    path.write_text(json.dumps(_record([games + [("1111111", True, "home", "1")]])) + "\n", encoding="utf-8")
    _, rows = A._marcosjn2_file(str(path))
    assert rows[0]["tb_trailing_dropped"] == 0 and rows[0]["n_points"] == 55


# ------------------------------------------------------------------------------------------------
# Sackmann's strings

def test_sackmann_string_servers_and_tiebreak_segments():
    pts, note = A.parse_pbp_string("SSSS;RRRR.S/RR/SS")
    assert note == "ok"
    a = np.array(pts)
    # game 1 served by server1 (won), game 2 by server2 (lost: player 1 won), the tie-break's first server is
    # server1 (game index 2), then server2 for two points, then server1
    assert a[:, 5].tolist() == [1] * 4 + [2] * 4 + [1, 2, 2, 1, 1]
    assert a[:, 6].tolist() == [1] * 4 + [1] * 4 + [1, 1, 1, 1, 1]
    assert a[8:, 3].tolist() == [1] * 5 and a[:8, 3].tolist() == [0] * 8
    pts, _ = A.parse_pbp_string("ASDR")
    assert [p[7] for p in pts] == [1, 0, 2, 0]           # ace, plain, double fault, plain


# ------------------------------------------------------------------------------------------------
# Linking orientation and the rebuilt ids

def _universe() -> pd.DataFrame:
    from src.eda.shot_level import common as S
    u = pd.DataFrame({"uid": [0, 1], "match_id": ["m-a", "m-b"], "tour": ["M", "M"],
                      "year": [2024, 2024], "d": pd.to_datetime(["2024-03-04", "2024-03-04"]),
                      "level": ["T250", "T250"], "draw": ["main", "main"], "round": ["R32", "R16"],
                      "tname": ["X", "X"], "id_a": ["1", "3"], "id_b": ["2", "4"],
                      "name1": ["Carlos Alcaraz", "Jannik Sinner"], "name2": ["Felix Auger-Aliassime", "Casper Ruud"],
                      "creator": "stage0"})
    return S.prepare(u).drop(columns=["rid"]).reset_index(drop=True)


def test_linker_orientation_by_names():
    from src.eda.shot_level import common as S
    lk = S.Stage0Linker(_universe())
    rows = pd.DataFrame({"tour": ["M", "M", "M"], "d": pd.to_datetime(["2024-03-06", "2024-03-08", "2024-05-01"]),
                         "name1": ["C. Alcaraz", "Casper Ruud", "Carlos Alcaraz"],
                         "name2": ["F. Auger Aliassime", "J. Sinner", "Felix Auger-Aliassime"],
                         "round": [None, None, None], "level": [None, None, None], "draw": ["main", "main", "main"]})
    out = lk.link(rows)
    assert out["match_id"].tolist()[:2] == ["m-a", "m-b"]
    assert out["a1"].tolist()[:2] == [True, False]
    assert pd.isna(out["match_id"].iloc[2])                      # two months later: outside the window


def test_rebuilt_ids_are_mapped_back_and_flipped_sides_flip_the_orientation():
    mid = pd.Series(["new-1", "new-2", "same", None], dtype=object)
    a1 = pd.Series([True, True, False, None], dtype=object)
    new2old = {"new-1": "old-1", "new-2": "old-2"}
    flip = {"new-1": False, "new-2": True}
    m, o, mapped, flipped = B.map_links(mid, a1, new2old, flip)
    assert m.tolist()[:3] == ["old-1", "old-2", "same"] and m.iloc[3] is None
    assert o.tolist()[:3] == [True, False, False] and o.iloc[3] is None
    assert mapped.tolist() == [True, True, False, False] and flipped.tolist() == [False, True, False, False]


# ------------------------------------------------------------------------------------------------
# The official-score check

def test_parse_official_scores():
    sets, early = B.parse_official("6-7(3) 6-3 [10-8]", "match_tiebreak")
    assert sets == [(6, 7, 3, False), (6, 3, None, False), (10, 8, None, True)] and not early
    sets, early = B.parse_official("6-3 5-4 RET", "standard")
    assert sets == [(6, 3, None, False), (5, 4, None, False)] and early


def test_score_check_orientation_retirement_and_prefix():
    view = pd.DataFrame({"match_id": ["x", "y", "z"], "score": ["6-4 7-6(5)", "6-3 5-4 RET", "6-4 6-4"],
                         "status": ["completed", "retired", "completed"], "a_won": [False, True, True],
                         "format": ["standard"] * 3})
    seqm = pd.DataFrame({
        "match_id": ["x", "y", "z"],
        "a1": [True, True, True],
        "replay": ["complete", "partial", "partial"],
        "replay_winner": [2, 0, 0],
        # x: source player 1 is side A and lost 4-6 6-7(5); y: retired at 6-3 5-4; z: the record stops at 6-4 3-2
        "sets_json": [json.dumps([[4, 6, None, None], [6, 7, 5, 7]]), json.dumps([[6, 3, None, None]]),
                      json.dumps([[6, 4, None, None]])],
        "cur_games": ["0-0", "5-4", "3-2"], "status": ["complete", "partial", "partial"]})
    out = B.score_check(seqm, view)
    assert out["score_check"].tolist() == ["exact", "exact", "prefix_of_official"]
    wrong = seqm.iloc[[0]].assign(replay_winner=1)
    assert B.score_check(wrong, view)["score_check"].iloc[0] == "winner_differs"
    # Stage 0 without the tie-break loser's points ('7-6') does not contradict a replayed 7-6(5); a different number does
    bare = view.assign(score=["6-4 7-6", "6-3 5-4 RET", "6-4 6-4"])
    assert B.score_check(seqm.iloc[[0]], bare)["score_check"].iloc[0] == "exact"
    other = view.assign(score=["6-4 7-6(3)", "6-3 5-4 RET", "6-4 6-4"])
    assert B.score_check(seqm.iloc[[0]], other)["score_check"].iloc[0] == "tb_points_differ"
