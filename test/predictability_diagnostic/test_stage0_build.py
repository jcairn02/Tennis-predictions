"""Stage 0 build helpers (src/eda/predictability_diagnostic/stage0_build.py), offline on synthetic rows.

Includes the parts of src/eda/merge_feasibility/scan.py that Stage 0 reuses (scan.py is unapproved
scaffold code, so what is reused is tested here), and the two flaws of it that Stage 0 corrects.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402


# ------------------------------------------------------------------------------------------------
# What Stage 0 reuses from scan.py

@pytest.mark.parametrize("a, b", [("Zhang Zhizhen", "Zhizhen Zhang"), ("Jo-Wilfried Tsonga", "Jo Wilfried TSONGA"),
                                  ("Nuñez", "Nunez"), ("Felix Auger-Aliassime", "Auger Aliassime Felix")])
def test_scan_name_key_ignores_order_accents_case_and_punctuation(a, b):
    assert S.name_key(a) == S.name_key(b)


def test_scan_pair_is_symmetric_and_blank_without_two_names():
    a, b = pd.Series(["x", "y", ""]), pd.Series(["y", "x", "z"])
    out = S.pair_of(a, b)
    assert out[0] == out[1] == "x|y" and out[2] == ""


def frame(rows, cols):
    return pd.DataFrame(rows, columns=cols)


def test_scan_link_and_resolve_take_the_nearest_week_and_flag_ties():
    left = frame([("atp", "R32", "a|b", "2024-01-01"), ("atp", "R32", "a|b", "2024-01-08"),
                  ("atp", "R32", "c|d", "2024-01-01"), ("atp", "R32", "c|d", "2024-01-15")],
                 ["tour", "round", "pair", "tdate"]).assign(tdate=lambda f: pd.to_datetime(f["tdate"]))
    right = frame([("atp", "R32", "a|b", "2024-01-07"), ("atp", "R32", "c|d", "2024-01-08"),
                   ("atp", "R32", "e|f", "2024-01-08")],
                  ["tour", "round", "pair", "date"]).assign(date=lambda f: pd.to_datetime(f["date"]))
    n, unique = S.resolve(S.link(left, right, ["tour", "round", "pair"]), window=(-10, 10))
    assert unique.set_index("ri").loc[0, "li"] == 1        # 1 day beats 6 days
    assert n.loc[1] == 2 and 1 not in set(unique["ri"])    # 7 days either way: ambiguous
    assert 2 not in n.index                                 # no candidate


def test_scan_anchor_links_one_identical_player_and_flags_two():
    cols = ["tour", "tid", "round", "wkey", "lkey"]
    sack = frame([("atp", "2024-1", "R32", "alcaraz carlos", "sinner jannik"),
                  ("atp", "2024-1", "R16", "alcaraz carlos", "ruud casper"),
                  ("atp", "2024-2", "R32", "ruud casper", "fritz taylor")], cols)
    tml = frame([("atp", "2024-1", "R32", "alcaraz carlos", "jannik sinner x"),    # spelling variant
                 ("atp", "2024-2", "R32", "fritz taylor", "ruud casper"),          # exact, other order
                 ("atp", "2024-3", "R32", "alcaraz carlos", "nobody")], cols)
    n, unique = S.anchor_links(sack, tml)
    got = unique.set_index("ri")["li"].to_dict()
    assert got == {0: 0, 1: 2}


def test_anchor_candidates_keep_what_scan_keeps():
    cols = ["tour", "tid", "round", "wkey", "lkey", "tdate"]
    sack = frame([("atp", "2010-1", "R32", "a", "b", "2010-01-04"), ("atp", "2010-1", "R32", "a", "c", "2010-10-04")], cols)
    tml = frame([("atp", "2010-1", "R32", "a", "x", "2010-01-10")], cols)
    for f in (sack, tml):
        f["tdate"] = pd.to_datetime(f["tdate"])
    n, _ = S.anchor_links(sack, tml)
    cand = B.anchor_candidates(sack, tml)
    assert n.loc[0] == 2                    # scan.py: two candidates, dropped as ambiguous
    assert sorted(cand["gap"]) == [-267, 6]  # ours keeps both, with their date gaps, for pick() to judge


# ------------------------------------------------------------------------------------------------
# Choosing links

def rows(data):
    f = pd.DataFrame(data, columns=["rid", "tid", "tourney_name", "score"])
    return f.set_index("rid", drop=False)


def test_pick_prefers_the_same_event_to_the_nearest_week():
    # a pair met in R32 at Mons (TML dated by its Sunday) and at Rennes a week later; Sackmann holds Rennes
    t = rows([(1, "2010-3350", "Mons", "6-2 3-6 6-0"), (2, "2010-3503", "Rennes", "6-0 4-6 6-3")])
    s = rows([(10, "2010-3503", "Rennes CH", "6-0 4-6 6-3")])
    cand = pd.DataFrame({"ri": [1, 2], "li": [10, 10], "gap": [-1, 6]})
    kept, amb = B.pick(cand, t, s)
    assert kept.set_index("ri")["li"].to_dict() == {2: 10} and len(amb) == 0


def test_pick_accepts_a_misdated_edition_only_with_the_same_scores():
    # TML dates all six Forli events of 2022 by the first; the ids and scores still agree
    t = rows([(1, "2022-9810", "Forli 1", "6-7(5) 6-2 6-3"), (2, "2022-9810", "Forli 1", "6-4 6-4")])
    s = rows([(10, "2022-9810", "Forli 5 CH", "6-7(5) 6-2 6-3"), (11, "2022-9810", "Forli 5 CH", "7-5 6-1")])
    cand = pd.DataFrame({"ri": [1, 2], "li": [10, 11], "gap": [-43, -43]})
    kept, _ = B.pick(cand, t, s)
    assert kept.set_index("ri")["li"].to_dict() == {1: 10}


def test_pick_gives_each_sackmann_row_to_one_tml_row():
    t = rows([(1, "E", "Rome", "6-4 6-4"), (2, "E", "Rome", "6-4 6-4")])
    s = rows([(10, "E", "Rome CH", "6-4 6-4")])
    kept, _ = B.pick(pd.DataFrame({"ri": [1, 2], "li": [10, 10], "gap": [0, 3]}), t, s)
    assert list(kept["ri"]) == [1]


# ------------------------------------------------------------------------------------------------
# Scores

@pytest.mark.parametrize("score, status", [
    ("6-4 6-3", "completed"), ("6-4 3-1 RET", "retired"), ("6-1 4-3 RET+H64", "retired"), ("5-0 ret.", "retired"),
    ("6-3 0-0 Ret'd", "retired"), ("W/O", "walkover"), ("Walkover", "walkover"), ("6-2 1-0 W/O", "walkover_after_play"),
    ("BYE", "bye"), ("6-4 5-2 DEF", "defaulted"), ("6-3 6-7(5) 2-1 Def.", "defaulted"),
    ("2-1 Played and abandoned", "abandoned"), ("2-2 WEA", "abandoned"), ("", "unknown"), ("&nbsp;", "unknown"),
    ("UNK", "unknown"), ("May-00", "unknown")])
def test_status_markers(score, status):
    assert B.status_of(*B.tokens_of(score)) == status


@pytest.mark.parametrize("score, short, expect", [
    # sets_w, sets_l, games_w, games_l, tb_w, tb_l, std_tb, bracket, short_like, last_done
    ("6-4 3-6 7-6(5)", False, (2, 1, 16, 16, 1, 0, 1, False, False, True)),
    ("6-3 6-4 RET", False, (2, 0, 12, 7, 0, 0, 0, False, False, True)),
    ("6-4 3-1 RET", False, (1, 0, 9, 5, 0, 0, 0, False, False, False)),
    ("6-3 3-6 [10-8]", False, (2, 1, 9, 9, 1, 0, 0, True, False, True)),
    ("6-7(15) 7-6(2) [10-7]", False, (2, 1, 13, 13, 2, 1, 2, True, False, True)),
    ("4-2 4-3(5) 4-1", True, (3, 0, 12, 6, 1, 0, 1, False, True, True)),
    ("7-6(5) 6-7(3) 13-12(4)", False, (2, 1, 26, 25, 2, 1, 3, False, False, True)),
    ("6-2 7-6", False, (2, 0, 13, 8, 1, 0, 1, False, False, True)),
])
def test_score_counts(score, short, expect):
    assert B.score_counts(score, short) == expect


def test_set_scores_ignore_tiebreak_points():
    assert B.set_scores("6-2 7-6(0)") == B.set_scores("6-2 7-6")
    assert B.set_scores("6-2 7-6") != B.set_scores("6-2 6-7")


# ------------------------------------------------------------------------------------------------
# Levels

@pytest.mark.parametrize("source, tour, code, name, level", [
    ("sackmann", "atp", "A", "Atp Cup", "TEAM"), ("sackmann", "atp", "A", "Rio Olympics", "TEAM"),
    ("sackmann", "atp", "A", "NextGen Finals", "FIN"), ("sackmann", "atp", "A", "Tour Finals", "FIN"),
    ("sackmann", "atp", "A", "Doha", "T250"), ("sackmann", "atp", "M", "Rome Masters", "T1000"),
    ("sackmann", "atp", "D", "Davis Cup WG R1: ESP vs GER", "TEAM"), ("sackmann", "atp", "S", "USA F1", "ITF"),
    ("sackmann", "atp", "15", "M15 Monastir", "ITF"), ("sackmann", "atp", "C", "Rimini CH", "CH"),
    ("tml", "atp", "M", "Winston-Salem", "T250"), ("tml", "atp", "M", "Monte Carlo", "T1000"),
    ("tml", "atp", "A", "World Team Championship", "TEAM"), ("tml", "atp", "500", "Basel", "T500"),
    ("sackmann", "wta", "W", "Buenos Aires 125", "CH"), ("sackmann", "wta", "W", "WTA Finals", "FIN"),
    ("sackmann", "wta", "50+H", "W50+H Leipzig", "ITF"), ("sackmann", "wta", "PM", "Beijing", "T1000"),
    ("sackmann", "wta", "C", "Newport Beach", "CH"), ("tml", "wta", "P5", "Cincinnati", "T1000"),
    ("tml", "wta", "A", "United Cup", "TEAM"), ("tml", "wta", "A", "Prague Open", "T250"),
    ("sackmann", "wta", "F", "Zhuhai", "FIN"), ("sackmann", "wta", "D", "BJK Cup Qualifiers", "TEAM")])
def test_level_rules(source, tour, code, name, level):
    df = pd.DataFrame({"source": [source], "tour": [tour], "code": [code], "tourney_name": [name]})
    assert B.rule_levels(df)["level"].iloc[0] == level


def test_ambiguous_sackmann_codes_are_marked_for_tml():
    df = pd.DataFrame({"source": ["sackmann"] * 3, "tour": ["atp", "wta", "atp"], "code": ["A", "P", "G"],
                       "tourney_name": ["Basel", "Wuhan", "Wimbledon"]})
    assert list(B.rule_levels(df)["refine"]) == [True, True, False]


# ------------------------------------------------------------------------------------------------
# Box scores

BOX_W = {"ace": "5", "df": "2", "svpt": "60", "1stIn": "38", "1stWon": "28", "2ndWon": "12", "SvGms": "10",
         "bpSaved": "2", "bpFaced": "3"}
BOX_L = {"ace": "3", "df": "4", "svpt": "65", "1stIn": "40", "1stWon": "25", "2ndWon": "10", "SvGms": "9",
         "bpSaved": "3", "bpFaced": "6"}


def box_row(score="6-4 6-3", w=None, l=None, status="completed"):
    w, l = dict(BOX_W, **(w or {})), dict(BOX_L, **(l or {}))
    sw, sl, gw, gl, tw, tl, tb, *_ = B.score_counts(score, False)
    row = {"rid": 1, "score": score, "status": status, "status_detail": status, "games_w": gw, "games_l": gl,
           "std_tb": tb}
    row.update({f"w_{k}": v for k, v in w.items()})
    row.update({f"l_{k}": v for k, v in l.items()})
    return row


def boxes(*rows):
    df = pd.DataFrame(list(rows))
    df["rid"] = np.arange(len(df))
    return B.box_scores(df)


def test_box_consistent_is_kept_and_blank_or_zero_is_missing():
    blank = {k: "" for k in BOX_W}
    zero = {k: "0" for k in BOX_W}
    out = boxes(box_row(), box_row(w=blank, l=blank), box_row(w=zero), box_row(l=blank))
    assert list(out["box_status"]) == ["full", "blank", "all_zero", "one_side"]
    assert list(out["has_box"]) == [True, False, False, False]
    assert out.loc[1:, "w_svpt"].isna().all()


@pytest.mark.parametrize("w, check", [({"1stIn": "61"}, "B1"), ({"1stWon": "39"}, "B2"), ({"2ndWon": "23"}, "B3"),
                                      ({"bpSaved": "4"}, "B4"), ({"df": "23"}, "B6"), ({"ace": "41"}, "B7")])
def test_box_failing_a_check_is_dropped(w, check):
    out = boxes(box_row(w=w))
    assert out["box_status"].iloc[0] == "failed_check" and not out["has_box"].iloc[0]


def test_service_games_either_way_of_counting_tiebreaks():
    # 7-6 6-4: 23 games, one tiebreak; 22 service games without it, 23 with it
    excl = boxes(box_row("7-6(4) 6-4", w={"SvGms": "11"}, l={"SvGms": "11"}))
    incl = boxes(box_row("7-6(4) 6-4", w={"SvGms": "12"}, l={"SvGms": "11"}))
    assert excl["has_box"].iloc[0] and incl["has_box"].iloc[0]
    wrong = boxes(box_row("7-6(4) 6-4", w={"SvGms": "5"}, l={"SvGms": "4"}))
    assert wrong["box_status"].iloc[0] == "no_svgms" and np.isnan(wrong["w_sv_gms"].iloc[0])
    assert wrong["w_svpt"].iloc[0] == 60                      # the other counts are kept


def test_too_few_points_for_the_games_played_drops_the_box():
    out = boxes(box_row("6-4 6-3", w={"svpt": "20", "1stIn": "12", "1stWon": "9", "2ndWon": "4", "ace": "1",
                                      "df": "1"}, l={"svpt": "22", "1stIn": "12", "1stWon": "8", "2ndWon": "4",
                                                     "ace": "1", "df": "1"}))
    assert out["box_status"].iloc[0] == "failed_check"


# ------------------------------------------------------------------------------------------------
# Repeats, and who advanced

def repeat_rows(data):
    cols = ["rid", "tour", "tid", "ekey", "round", "winner_id", "loser_id", "wkey", "lkey", "tourney_date", "score",
            "w_svpt", "status"]
    return pd.DataFrame(data, columns=cols)


def test_repeats_keep_one_copy_and_drop_contradictions():
    df = repeat_rows([
        (1, "wta", "E", "E", "Q1", "1", "2", "a", "b", "20240101", "6-1 6-1", "", "completed"),
        (2, "wta", "E", "E", "Q1", "1", "2", "a", "b", "20240101", "6-1 6-1", "40", "completed"),   # has a box
        (3, "atp", "F", "F", "Q3", "3", "4", "c", "d", "20240101", "6-3 6-4", "", "completed"),
        (4, "atp", "F", "F", "Q3", "4", "3", "d", "c", "20240101", "7-6 6-2", "", "completed"),     # other winner
        (5, "wta", "G", "G", "R32", "5", "6", "e", "f", "20240108", "6-0 6-1", "", "completed"),
        (6, "wta", "H", "H", "R32", "5", "6", "e", "f", "20240108", "6-0 6-1", "", "completed")])  # copied event
    out = B.drop_repeats(df, "test")
    assert sorted(out["rid"]) == [2, 5]


def progression_rows(data):
    df = pd.DataFrame(data, columns=["tour", "tid", "round", "pid_w", "pid_l", "level"])
    return df


def test_progression_finds_who_advanced():
    df = progression_rows([("atp", "E", "R16", "a", "b", "T250"), ("atp", "E", "R16", "c", "d", "T250"),
                           ("atp", "E", "QF", "b", "c", "T250"),          # b plays on: the R16 labels are swapped
                           ("atp", "E", "F", "b", "x", "T250"),           # a final: nothing to check
                           ("atp", "T", "R16", "p", "q", "TEAM"), ("atp", "T", "QF", "q", "r", "TEAM")])
    assert list(B.progression(df)) == ["loser", "winner", "", "", "", ""]


def test_swap_sides_exchanges_everything_recorded_per_player():
    cols = [f"winner_{b}" for b in B.BIO] + [f"loser_{b}" for b in B.BIO] + \
           [f"w_{c}" for c in C.BOX_SOURCE_NAMES.values()] + [f"l_{c}" for c in C.BOX_SOURCE_NAMES.values()] + \
           ["wkey", "lkey", "pid_w", "pid_l"]
    df = pd.DataFrame([{c: ("W" if c.startswith(("winner_", "w_", "wkey", "pid_w")) else "L") for c in cols}] * 2)
    out = B.swap_sides(df.copy(), pd.Series([True, False]))
    assert (out.loc[0, [c for c in cols if c.startswith(("winner_", "w_"))]] == "L").all()
    assert (out.loc[1, [c for c in cols if c.startswith(("winner_", "w_"))]] == "W").all()


# ------------------------------------------------------------------------------------------------
# Sides

def test_side_depends_on_the_match_id_only():
    ids = [f"atp|2024-{i}|R32|atp:{i}|atp:{i + 1}" for i in range(4000)]
    low = np.array([C.side_is_low(x) for x in ids])
    assert low.dtype == bool and 0.46 < low.mean() < 0.54
    assert [C.side_is_low(x) for x in ids[:50]] == list(low[:50])    # deterministic
