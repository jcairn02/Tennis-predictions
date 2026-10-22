"""Offline tests of the corrections the input-data audit applies to named source rows: each action does exactly its
change, and a table that no longer names its row exactly stops the build."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.input_data_audit import corrections as K  # noqa: E402

W = {"ace": "5", "df": "4", "svpt": "56", "1stIn": "36", "1stWon": "30", "2ndWon": "10", "SvGms": "10",
     "bpSaved": "1", "bpFaced": "2"}
L = {"ace": "2", "df": "3", "svpt": "55", "1stIn": "35", "1stWon": "25", "2ndWon": "8", "SvGms": "9",
     "bpSaved": "2", "bpFaced": "5"}


def raw(n: int = 2) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append({"_source_file": "f.csv", "_row": i + 1, "tourney_id": "2015-1", "round": "R32",
                     "winner_name": f"Win {i}", "loser_name": f"Lose {i}", "winner_age": "25.1", "loser_age": "30.2",
                     **{f"w_{k}": v for k, v in W.items()}, **{f"l_{k}": v for k, v in L.items()}})
    return pd.DataFrame(rows, index=[10, 11][:n])


def table(action: str, row: int = 1, **extra) -> pd.DataFrame:
    g = {"tourney_id": "2015-1", "round": "R32", "winner_name": f"Win {row - 1}", "loser_name": f"Lose {row - 1}"}
    return pd.DataFrame([{"action": action, "source_file": "f.csv", "source_row": row, **{**g, **extra}}])


def test_serve_points_take_the_double_faults_on_both_sides_and_nothing_else():
    df, done = K.apply_row_corrections(raw(), table("add_df_to_svpt"))
    assert df.loc[10, "w_svpt"] == "60" and df.loc[10, "l_svpt"] == "58"
    assert df.loc[11, "w_svpt"] == "56"                               # the other row is untouched
    assert list(done["add_df_to_svpt"]) == [10]
    assert (df.loc[10, ["w_df", "w_1stIn", "l_2ndWon"]] == ["4", "36", "8"]).all()


def test_exchange_moves_all_nine_counts():
    df, _ = K.apply_row_corrections(raw(), table("exchange_box", row=2))
    assert [df.loc[11, f"w_{k}"] for k in K.COUNTS] == list(L.values())
    assert [df.loc[11, f"l_{k}"] for k in K.COUNTS] == list(W.values())


def test_service_games_alone_can_be_exchanged():
    df, _ = K.apply_row_corrections(raw(), table("exchange_svgms"))
    assert df.loc[10, "w_SvGms"] == "9" and df.loc[10, "l_SvGms"] == "10"
    assert df.loc[10, "w_svpt"] == "56" and df.loc[10, "l_bpFaced"] == "5"


def test_blank_leaves_the_box_missing():
    df, _ = K.apply_row_corrections(raw(), table("blank_box"))
    assert (df.loc[10, [f"{s}_{k}" for s in "wl" for k in K.COUNTS]] == "").all()


def test_replace_takes_all_eighteen_counts_and_refuses_a_partial_record():
    given = {f"w_{k}": int(v) + 1 for k, v in W.items()} | {f"l_{k}": int(v) + 2 for k, v in L.items()}
    df, _ = K.apply_row_corrections(raw(), table("replace_box", **given))
    assert df.loc[10, "w_svpt"] == "57" and df.loc[10, "l_bpFaced"] == "7" and df.loc[11, "w_svpt"] == "56"
    with pytest.raises(SystemExit, match="eighteen"):
        K.apply_row_corrections(raw(), table("replace_box", **{**given, "l_ace": ""}))


SPLIT_OK = {"w_svpt": 56, "w_ace": 5, "w_df": 4, "w_1stIn": 30, "w_1stWon": 26, "w_2ndWon": 14}   # won 40 -> 40


def test_replace_split_moves_only_the_split_of_the_side_given():
    df, done = K.apply_row_corrections(raw(), table("replace_split", **SPLIT_OK))
    assert (df.loc[10, ["w_1stIn", "w_1stWon", "w_2ndWon"]] == ["30", "26", "14"]).all()
    assert (df.loc[10, ["w_svpt", "w_ace", "w_df", "w_SvGms", "w_bpSaved", "w_bpFaced"]]
            == ["56", "5", "4", "10", "1", "2"]).all()
    assert [df.loc[10, f"l_{k}"] for k in K.COUNTS] == list(L.values())       # the side without values is untouched
    assert [df.loc[11, f"w_{k}"] for k in K.COUNTS] == list(W.values())       # and so is the other row
    assert list(done["replace_split"]) == [10]


def test_replace_split_works_where_another_count_of_the_row_is_blank():
    r = raw()
    r.loc[10, "w_SvGms"] = ""
    df, _ = K.apply_row_corrections(r, table("replace_split", **SPLIT_OK))
    assert df.loc[10, "w_1stIn"] == "30" and df.loc[10, "w_SvGms"] == ""


@pytest.mark.parametrize("bad", [
    {**SPLIT_OK, "w_svpt": 57},                                    # the row no longer reads the guard's serve points
    {**SPLIT_OK, "w_df": 5},                                       # nor its double faults
    {**SPLIT_OK, "w_2ndWon": 15},                                  # serve points won would change
    {**SPLIT_OK, "w_1stIn": ""},                                   # a side given in part
    {k: v for k, v in SPLIT_OK.items() if k != "w_svpt"},          # no serve-point guard
    {**SPLIT_OK, "w_1stIn": 10, "w_1stWon": 12, "w_2ndWon": 28},   # more first-serve points won than first serves in
])
def test_replace_split_stops_the_build_when_a_guard_fails(bad):
    with pytest.raises(SystemExit):
        K.apply_row_corrections(raw(), table("replace_split", **bad))


SETS_OK = {"w_svpt": 56, "l_svpt": 55, "w_SvGms": 11, "l_SvGms": 10, "value": "10/9"}


def test_set_svgms_sets_both_service_games_and_nothing_else():
    df, done = K.apply_row_corrections(raw(), table("set_svgms", **SETS_OK))
    assert df.loc[10, "w_SvGms"] == "11" and df.loc[10, "l_SvGms"] == "10"
    others = [f"{s}_{k}" for s in "wl" for k in K.COUNTS if k != "SvGms"]
    assert (df.loc[10, others] == raw().loc[10, others]).all()
    assert df.loc[11, "w_SvGms"] == "10" and list(done["set_svgms"]) == [10]


def test_set_svgms_fills_service_games_the_source_leaves_blank():
    r = raw()
    r.loc[10, ["w_SvGms", "l_SvGms"]] = ""
    df, _ = K.apply_row_corrections(r, table("set_svgms", **{**SETS_OK, "value": "/"}))
    assert df.loc[10, "w_SvGms"] == "11" and df.loc[10, "l_SvGms"] == "10"


@pytest.mark.parametrize("bad", [
    {**SETS_OK, "value": "11/9"},                                  # the row no longer reads the counts it replaces
    {**SETS_OK, "l_svpt": 54},                                     # nor the guard's serve points
    {**SETS_OK, "value": ""},                                      # the counts it replaces not given
    {k: v for k, v in SETS_OK.items() if k != "w_svpt"},           # no serve-point guard
    {**SETS_OK, "l_SvGms": ""},                                    # a new count missing
])
def test_set_svgms_stops_the_build_when_a_guard_fails(bad):
    with pytest.raises(SystemExit):
        K.apply_row_corrections(raw(), table("set_svgms", **bad))


def test_an_age_and_a_box_fix_can_share_a_row_but_one_field_cannot_be_fixed_twice():
    both = pd.concat([table("set_age", side="loser", value=28.008), table("exchange_box")], ignore_index=True)
    df, done = K.apply_row_corrections(raw(), both)
    assert df.loc[10, "loser_age"] == "28.008" and df.loc[10, "winner_age"] == "25.1" and df.loc[10, "w_ace"] == "2"
    with pytest.raises(SystemExit, match="named twice"):
        K.apply_row_corrections(raw(), pd.concat([table("exchange_box"), table("blank_box")], ignore_index=True))


def test_a_row_whose_names_changed_or_that_is_missing_stops_the_build():
    # since 21 Oct 2026 a correction whose row moved is found by its match (_row_positions); one whose guards name no
    # row of its file, under any row number, still stops the build
    with pytest.raises(SystemExit, match="names no row whose tournament id, round and names equal its guards"):
        K.apply_row_corrections(raw(), table("exchange_box", winner_name="Someone Else"))
    with pytest.raises(SystemExit, match="names no row whose tournament id, round and names equal its guards"):
        K.apply_row_corrections(raw(), table("exchange_box", row=7))


def frames():
    m = pd.DataFrame({"match_id": ["m1", "m2"], "tour": ["wta", "wta"], "player_a_id": ["wta:1", "wta:9"],
                      "player_b_id": ["wta:2", "wta:1"]})
    mp = pd.DataFrame({"match_id": ["m1", "m1", "m2", "m2"], "side": ["A", "B", "A", "B"],
                       "player_id": ["wta:1", "wta:2", "wta:9", "wta:1"],
                       "opponent_id": ["wta:2", "wta:1", "wta:1", "wta:9"],
                       "player_name": ["Ann Lee", "Bo Ma", "Ann Lee", "Ann Lee"]})
    return m, mp


def test_an_alias_moves_the_second_id_and_its_opponents_follow():
    m, mp = frames()
    alias = pd.DataFrame([{"tour": "wta", "from_id": "wta:9", "to_id": "wta:2", "name_key": "ann lee"}])
    m2, mp2, rep = K.apply_id_aliases(m.copy(), mp.copy(), alias, lambda s: s.lower())
    assert rep == [{"tour": "wta", "from_id": "wta:9", "to_id": "wta:2", "rows": 1}]
    assert mp2.loc[2, "player_id"] == "wta:2" and mp2.loc[3, "opponent_id"] == "wta:2"
    assert m2.loc[1, "player_a_id"] == "wta:2" and list(m2["match_id"]) == ["m1", "m2"]


def test_an_alias_that_would_meet_itself_or_another_name_stops_the_build():
    m, mp = frames()
    with pytest.raises(SystemExit, match="both sides"):
        K.apply_id_aliases(m.copy(), mp.copy(), pd.DataFrame(
            [{"tour": "wta", "from_id": "wta:9", "to_id": "wta:1", "name_key": "ann lee"}]), lambda s: s.lower())
    with pytest.raises(SystemExit, match="named"):
        K.apply_id_aliases(m.copy(), mp.copy(), pd.DataFrame(
            [{"tour": "wta", "from_id": "wta:9", "to_id": "wta:2", "name_key": "bo ma"}]), lambda s: s.lower())


def odds():
    return pd.DataFrame({"td_file": ["o.parquet"] * 2, "td_row": [0, 1], "td_winner": ["Murray A.", "Konta J."],
                         "td_loser": ["Raonic M.", "Vekic D."], "td_date_text": ["2016-07-10", "2017-06-18"],
                         "AvgW": [1.26, 4.98], "AvgL": [3.97, 1.17], "MaxW": [1.3, 6.0], "MaxL": [4.36, 1.23],
                         "PSW": [1.27, 5.77], "PSL": [4.36, 1.18]})


BOOKS = {"avg": ("AvgW", "AvgL"), "ps": ("PSW", "PSL"), "max": ("MaxW", "MaxL")}


def test_named_books_exchange_prices_and_others_stay():
    t = pd.DataFrame([{"td_file": "o.parquet", "td_row": 0, "action": "exchange_prices", "books": "avg max",
                       "td_winner": "Murray A.", "td_loser": "Raonic M.", "td_date_text": "2016-07-10"}])
    td, rep = K.apply_odds_corrections(odds(), t, BOOKS)
    assert td.loc[0, ["AvgW", "AvgL", "MaxW", "MaxL"]].tolist() == [3.97, 1.26, 4.36, 1.3]
    assert td.loc[0, ["PSW", "PSL"]].tolist() == [1.27, 4.36] and td.loc[1, "AvgW"] == 4.98
    assert rep == [{"td_file": "o.parquet", "td_row": 0, "books": "avg max"}]


def test_an_odds_row_whose_names_changed_stops_the_build():
    t = pd.DataFrame([{"td_file": "o.parquet", "td_row": 1, "action": "exchange_prices", "books": "avg ps max",
                       "td_winner": "Vekic D.", "td_loser": "Konta J.", "td_date_text": "2017-06-18"}])
    with pytest.raises(SystemExit, match="td_winner"):
        K.apply_odds_corrections(odds(), t, BOOKS)


def test_named_speed_records_are_found_exactly():
    rec = pd.DataFrame({"source": ["handoff_ks", "mantennisdata", "infosys"], "source_key": ["k1", "k2", "k3"],
                        "match_id": ["m1", "m1", "m1"], "side": ["A", "A", "A"]})
    hit = K.speed_exclusions(rec, rec.iloc[[0]])
    assert hit.tolist() == [True, False, False]
    with pytest.raises(SystemExit, match="exactly one"):
        K.speed_exclusions(rec, rec.iloc[[0]].assign(source_key="k9"))


# ------------------------------------------------------------------------------------------- date corrections (14 Oct 2026)
def dated(n: int = 3) -> pd.DataFrame:
    """Raw rows as stage0_build holds them when the corrections run: the source's date text and its parsed tdate."""
    rows = [{"_source_file": "tml/2024_challenger.csv", "_row": 280 + i, "tourney_id": "2024-2847", "round": "R32",
             "winner_name": f"Win {i}", "loser_name": f"Lose {i}", "tourney_date": "20240121"} for i in range(n)]
    df = pd.DataFrame(rows, index=range(50, 50 + n))
    df["tdate"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d")
    return df


def date_table(*idx: int, old: str = "20240121", new: str = "20240226") -> pd.DataFrame:
    return pd.DataFrame([{"fix": "D1", "action": "set_tourney_date", "match_id": f"m{i}",
                          "source_file": "tml/2024_challenger.csv", "tourney_id": "2024-2847", "round": "R32",
                          "winner_name": f"Win {i}", "loser_name": f"Lose {i}", "old_value": old, "value": new}
                         for i in idx])


def test_a_date_correction_finds_its_match_by_identity_not_by_row_number():
    df = dated()
    df["_row"] = [900, 901, 902]                       # the source rewrote its row order: the correction still finds it
    out, rep = K.apply_date_corrections(df, date_table(0, 2))
    assert list(out.loc[[50, 52], "tourney_date"]) == ["20240226", "20240226"]
    assert (out.loc[[50, 52], "tdate"] == pd.Timestamp("2024-02-26")).all()
    assert out.loc[51, "tourney_date"] == "20240121" and out.loc[51, "tdate"] == pd.Timestamp("2024-01-21")
    assert rep["applied"] == 2 and rep["not_found"] == [] and list(rep["rows"]) == [50, 52]


def test_a_date_the_source_already_fixed_is_left_alone_and_reported():
    df = dated()
    df.loc[51, "tourney_date"] = "20240226"            # the source corrected this one itself
    df["tdate"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d")
    out, rep = K.apply_date_corrections(df, date_table(0, 1))
    assert rep["applied"] == 1 and rep["not_found"] == ["m1"]
    assert (out["tdate"] == pd.Timestamp("2024-02-26")).sum() == 2


def test_a_date_correction_that_finds_two_rows_stops_the_build():
    df = pd.concat([dated(1), dated(1).set_axis([60])])
    with pytest.raises(SystemExit):
        K.apply_date_corrections(df, date_table(0))


def test_a_numeric_source_date_column_keeps_its_type():
    df = dated(1)
    df["tourney_date"] = df["tourney_date"].astype("int64")
    out, rep = K.apply_date_corrections(df, date_table(0))
    assert out.loc[50, "tourney_date"] == 20240226 and rep["applied"] == 1
