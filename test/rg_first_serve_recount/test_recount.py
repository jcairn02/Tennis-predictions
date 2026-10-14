"""Offline tests of the Roland-Garros first-serve recount: the point recounts, the name links and the classes that
decide which rows are proposed."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.rg_first_serve_recount import link as L  # noqa: E402
from src.eda.rg_first_serve_recount import propose as PR  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402


# ----------------------------------------------------------------------------------- counting
def point(server, serve, scorer, result="W"):
    return {"server": server, "serve": serve, "scorer": scorer, "result": result}


def test_matchbeats_recount_counts_points_by_server_and_serve():
    game1 = [point("1", 1, "1"), point("1", 2, "2"), point("1", 2, "2", "DF"), point("1", 1, "1", "A"),
             point("1", 1, "2")]
    game2 = [point("2", 2, "2"), point("2", 1, "1")]
    doc = {"playerData": {"tm1Ply1Name": "A.ONE", "tm2Ply1Name": "B.TWO"},
           "setData": [{"set": 1, "gameData": [{"game": 1, "pointData": game1}, {"game": 2, "pointData": game2}]}]}
    one, two = S._mb_counts(doc)
    assert (one["svpt"], one["first_in"], one["first_won"], one["second_won"], one["ace"], one["df"]) == (5, 3, 2, 0, 1, 1)
    assert (two["svpt"], two["first_in"], two["first_won"], two["second_won"], two["sv_gms"]) == (2, 1, 0, 1, 1)
    assert one["serve_other"] == 0 and one["points_total"] == 7


def test_service_games_leave_out_tiebreak_games():
    """sv_gms counts every game a player served in; sv_gms_regular leaves out a tiebreak (both players serve in it),
    Sackmann's convention of 2022-2025."""
    games = [{"game": 1, "pointData": [point("1", 1, "1")]}, {"game": 2, "pointData": [point("2", 1, "2")]},
             {"game": 13, "pointData": [point("1", 1, "1"), point("2", 1, "1"), point("2", 2, "2")]}]
    doc = {"playerData": {}, "setData": [{"set": 1, "gameData": games}]}
    one, two = S._mb_counts(doc)
    assert (one["sv_gms"], one["sv_gms_regular"], one["tb_games"]) == (2, 1, 1)
    assert (two["sv_gms"], two["sv_gms_regular"], two["tb_games"]) == (2, 1, 1)
    assert one["served_first"] and not two["served_first"]


def test_service_games_leave_out_the_unfinished_game_and_follow_the_tiebreak_flag():
    """A retirement's game in progress (isGameComplete false) does not count; nor does a flagged tiebreak, even one
    whose recorded points all have one server."""
    games = [{"game": 1, "isTieBreak": False, "isGameComplete": True, "pointData": [point("2", 1, "2")]},
             {"game": 13, "isTieBreak": True, "isGameComplete": True, "pointData": [point("1", 1, "1")]},
             {"game": 14, "isTieBreak": False, "isGameComplete": False, "pointData": [point("1", 1, "1")]}]
    one, two = S._mb_counts({"playerData": {}, "setData": [{"set": 1, "gameData": games}]})
    assert (one["sv_gms_regular"], two["sv_gms_regular"]) == (0, 1)
    assert one["tb_games"] == 1 and one["unfinished_games"] == 1 and two["served_first"]


def test_the_first_server_is_proven_only_by_an_unbroken_alternation_from_set_one():
    def doc(servers, first_game=1):
        games = [{"game": first_game + i, "isTieBreak": False, "isGameComplete": True,
                  "pointData": [point(s, 1, s)]} for i, s in enumerate(servers)]
        return {"playerData": {}, "setData": [{"set": 1, "gameData": games}]}
    assert S._mb_counts(doc(["1", "2", "1", "2"]))[0]["alternation_ok"]
    assert not S._mb_counts(doc(["1", "2", "2", "1"]))[0]["alternation_ok"]      # a game out of turn (or missing)
    assert not S._mb_counts(doc(["2", "1"], first_game=3))[0]["alternation_ok"]  # the file starts mid-set
    tb = {"game": 3, "isTieBreak": True, "isGameComplete": True,
          "pointData": [point("1", 1, "1"), point("2", 1, "2"), point("2", 1, "2")]}
    games = [{"game": 1, "pointData": [point("1", 1, "1")]}, {"game": 2, "pointData": [point("2", 1, "2")]}, tb]
    nxt = {"set": 2, "gameData": [{"game": 1, "pointData": [point("2", 1, "2")]}]}
    assert S._mb_counts({"playerData": {}, "setData": [{"set": 1, "gameData": games}, nxt]})[0]["alternation_strict"]


def test_a_repeated_game_passes_the_keyed_check_but_not_the_strict_one():
    """AO 2024 Griekspoor d. Safiullin: a game stored twice merges under its number, so the alternation holds, but
    the strict check sees the repeat."""
    games = [{"game": 1, "pointData": [point("1", 1, "1")]}, {"game": 2, "pointData": [point("2", 1, "2")]},
             {"game": 2, "pointData": [point("2", 1, "1")]}, {"game": 3, "pointData": [point("1", 1, "1")]}]
    one = S._mb_counts({"playerData": {}, "setData": [{"set": 1, "gameData": games}]})[0]
    assert one["alternation_ok"] and not one["alternation_strict"]


def test_olympic_play_by_play_codes_the_serve_in_each_result():
    p = pd.DataFrame({"unit": "U", "server": ["a"] * 6 + ["b"],
                      "result": ["PS1", "PR1", "A1", "PS2", "PR2", "DF", "A2"]})
    c = S.count_olympic_points(p).set_index("athlete_code")
    assert c.loc["a", ["svpt", "first_in", "first_won", "second_won", "ace", "df"]].tolist() == [6, 3, 2, 1, 1, 1]
    assert c.loc["b", ["first_in", "second_won", "ace"]].tolist() == [0, 1, 1]


def test_fractions_as_the_site_prints_them():
    assert S.frac("58/95 (61%)") == (58.0, 95.0)
    assert np.isnan(S.frac(None)[0]) and np.isnan(S.frac("-")[1])


# ----------------------------------------------------------------------------------- names
def test_names_match_in_any_order_and_across_spellings():
    assert L.name_score(S.nkey("DJOKOVIC Novak"), S.nkey("Novak Djokovic")) == 3
    assert L.name_score(S.nkey("P.CARRENOBUSTA"), S.nkey("Pablo Carreno Busta")) >= 1
    assert L.name_score(S.nkey("Felix AUGER-ALIASSIME"), S.nkey("Felix Auger Aliassime")) == 3
    assert L.name_score(S.nkey("Li TU"), S.nkey("Li Tu")) == 3
    assert L.name_score(S.nkey("Anastasiia SOBOLIEVA"), S.nkey("Anastasiya Soboleva")) == 2   # transliteration
    assert L.name_score(S.nkey("Thomas FAUREL"), S.nkey("T. Farquhar")) == 0                  # another player
    assert L.name_score(S.nkey("Mirra Andreeva"), S.nkey("Erika Andreeva")) == 1      # a surname only: weak
    assert L.name_score(S.nkey("Botic van de Zandschulp"), S.nkey("Tallon Griekspoor")) == 0


def test_a_match_is_placed_only_on_a_unique_best_pair():
    s0m = pd.DataFrame({"match_id": ["m1", "m2"], "event": "RG", "year": 2022, "tour": "W", "draw": "main",
                        "round": "R32", "key_a": ["mirra andreeva", "erika andreeva"],
                        "key_b": ["aryna sabalenka", "aryna sabalenka"], "pid_a": ["a1", "a2"], "pid_b": ["b", "b"]})
    src = pd.DataFrame({"event": "RG", "year": [2022], "tour": "W", "draw": "main", "round": "R32",
                        "name1": ["aryna sabalenka"], "name2": ["mirra andreeva"]})
    out = L.place(src, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")
    assert out["match_id"].iloc[0] == "m1" and out["a_is"].iloc[0] == "2"
    src2 = src.assign(name2="andreeva")                                  # both sisters fit equally: not placed
    assert pd.isna(L.place(src2, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")["match_id"].iloc[0])


def test_slots_pair_by_name_not_by_position():
    left = pd.DataFrame({"year": 2022, "match_id": "SM001", "slot": [1, 2], "nk": ["casper ruud", "rafael nadal"]})
    right = pd.DataFrame({"year": 2022, "match_id": "SM001", "team": ["A", "B"], "nk": ["rafael nadal", "casper ruud"]})
    p = L.pair_slots(left, right, ["year", "match_id"], "nk", "nk", "slot", "team").set_index("slot")
    assert p.loc[1, "team"] == "B" and p.loc[2, "team"] == "A"


# ----------------------------------------------------------------------------------- classes
def frame(**over):
    base = {"match_id": "m", "event": "RG", "raw_svpt": 80, "off_svpt": 80, "raw_ace": 3, "off_ace": 3, "raw_df": 2,
            "off_df": 2, "raw_bp_faced": 4, "off_bp_faced": 4, "raw_bp_saved": 2, "off_bp_saved": 2,
            "raw_first_in": 56, "off_first_in": 50, "raw_first_won": 40, "off_first_won": 37,
            "raw_second_won": 12, "off_second_won": 15, "off_ok": True}
    return pd.DataFrame([{**base, **over}])


def cls(**over):
    return PR.classify(frame(**over)).iloc[0]


def test_classes_separate_the_split_from_other_differences():
    a = cls()
    assert a["cls"] == "split" and a["sign"] == "+" and a["proposed"] and a["proposal_class"] == "A"
    b = cls(raw_df=1)                                                     # one double fault fewer as well
    assert b["cls"] == "split_other" and b["proposal_class"] == "B"
    assert cls(raw_svpt=70)["cls"] == "points" and not cls(raw_svpt=70)["proposed"]
    assert cls(raw_second_won=13)["cls"] == "points"                      # serve points won differ
    assert cls(raw_first_in=50, raw_first_won=37, raw_second_won=15)["cls"] == "equal"
    assert cls(raw_first_in=50, raw_first_won=37, raw_second_won=15, raw_ace=4)["cls"] == "other"
    assert cls(off_ok=False)["cls"] == "no_record"
    assert cls(raw_first_in=48, raw_first_won=35, raw_second_won=17)["sign"] == "-"


def test_the_venues_other_record_can_veto_a_row():
    f = frame(mb_svpt=80, mb_first_in=50, mb_first_won=37, mb_second_won=15)
    assert PR.classify(f).iloc[0]["second_channel"] == "agrees"
    f = frame(mb_svpt=80, mb_first_in=52, mb_first_won=38, mb_second_won=14)          # complete and different
    r = PR.classify(f).iloc[0]
    assert r["second_channel"] == "contradicts" and not r["proposed"]
    f = frame(mb_svpt=75, mb_first_in=45, mb_first_won=33, mb_second_won=14)          # misses points
    assert PR.classify(f).iloc[0]["second_channel"] == "incomplete" and PR.classify(f).iloc[0]["proposed"]
