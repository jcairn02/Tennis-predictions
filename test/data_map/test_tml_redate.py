"""The data map's repair of Tennis My Life's misdated Challenger editions (measure.repair_tml_dates): a row whose own
match Sackmann's files (else TennisLive's listings) list more than 10 days away takes that date and name, so that the
other row links to it instead of joining the map as a second match. Offline; every frame is made here."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M  # noqa: E402


def rows(*items, tour="M", draw="main"):
    out = []
    for tname, d, n1, n2, rnd, score, tid in items:
        out.append({"tour": tour, "d": pd.Timestamp(d), "year": pd.Timestamp(d).year, "name1": n1, "name2": n2,
                    "tname": tname, "round": rnd, "draw": draw, "score": score, "tid": tid, "level": "CH",
                    "grain": "result"})
    return pd.DataFrame(out)


def test_words_and_games():
    assert M.event_words("ATP Tenerife 3 Challenger") == frozenset({"tenerife"}) == M.event_words("Tenerife 1")
    assert M.event_words("Biella 6 CH") == frozenset({"biella"}) and M.event_words("Open") == frozenset()
    assert M.set_games("7-6(5) 3-6 6-4") == (13, 9, 10) and M.set_games("6-3 2-1 RET") == (9, 3)
    assert M.set_games("4-6 7-5 [10-8]") == (10, 12, 18) and M.set_games("W/O") == ()


def test_a_misdated_edition_takes_its_twins_date_and_name():
    # Tennis My Life files Biella 6 of 2021 under Biella 1's date; Sackmann has it on 17 May
    tml = rows(("Biella 1", "2021-02-14", "Holger Rune", "Gastao Elias", "R16", "6-3 7-6(3)", "2021-9503"),
               ("Biella 1", "2021-02-14", "Aa Alpha", "Bb Beta", "R32", "6-1 6-1", "2021-7085"))   # Biella 1's own
    sack = rows(("Biella 6 CH", "2021-05-17", "Holger Rune", "Gastao Elias", "R16", "6-3 7-6(3)", "2021-9503"),
                ("Biella 1 CH", "2021-02-08", "Aa Alpha", "Bb Beta", "R32", "6-1 6-1", "2021-7085"))
    fixed, rep = M.repair_tml_dates(tml, [("sackmann", sack)])
    assert fixed.loc[0, "d"] == pd.Timestamp("2021-05-17") and fixed.loc[0, "tname"] == "Biella 6 CH"
    assert fixed.loc[1, "d"] == pd.Timestamp("2021-02-14") and fixed.loc[1, "tname"] == "Biella 1"   # 6 days: kept
    assert rep[["source", "tname_was", "tname", "days"]].values.tolist() == [["sackmann", "Biella 1", "Biella 6 CH",
                                                                              92]]
    # ... and the map then holds the match once: Sackmann's row links to the repaired one
    u = M.Universe(pd.Timestamp("2021-12-31"))
    u.add("tml", fixed)
    before = len(u.matches)
    u.add("sackmann", sack)
    assert len(u.matches) == before == 2 and u.report["sackmann"]["added_as_new_match"] == 0


def test_the_event_must_agree_and_the_twin_be_unique():
    # another city's event, by name and id: not the same match
    tml = rows(("Poprad Tatry", "2018-06-23", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "2018-1"))
    other = rows(("Bratislava CH", "2018-11-05", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "2018-2"))
    assert M.repair_tml_dates(tml, [("sackmann", other)])[1].empty
    # the same id agrees even when the names do not (Tennis My Life's 'Dallas' rows of Irving 2018)
    same_id = other.assign(tid="2018-1")
    assert M.repair_tml_dates(tml, [("sackmann", same_id)])[1]["tname"].tolist() == ["Bratislava CH"]
    # twins at two editions: ambiguous, left alone
    two = rows(("Biella 3 CH", "2021-03-08", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "x"),
               ("Biella 6 CH", "2021-05-17", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "y"))
    t2 = rows(("Biella 1", "2021-02-14", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "z"))
    assert M.repair_tml_dates(t2, [("sackmann", two)])[1].empty
    # another score or round is another match
    assert M.repair_tml_dates(t2, [("sackmann", two.iloc[[1]].assign(score="6-4 6-3"))])[1].empty
    assert M.repair_tml_dates(t2, [("sackmann", two.iloc[[1]].assign(round="R16"))])[1].empty
    # more than a year away: not this season's edition
    assert M.repair_tml_dates(t2, [("sackmann", two.iloc[[1]].assign(d=pd.Timestamp("2022-05-17")))])[1].empty


def test_the_downloads_keep_the_merged_copies_keys():
    # one match the map now holds once, at Biella 6's date; the frozen lists know it by Tennis My Life's old key too
    matches = pd.DataFrame({"uid": [7, 8], "tour": "M", "tname": ["Biella 6 CH", "Biella 1"],
                            "d": pd.to_datetime(["2021-05-17", "2021-02-14"]), "name1": ["Holger Rune", "Aa Alpha"],
                            "name2": ["Gastao Elias", "Bb Beta"], "draw": "main"})
    aliases = pd.DataFrame({"tour": ["M", "M"], "tname": ["Biella 1", "Biella 1"],
                            "d": pd.to_datetime(["2021-02-14", "2021-02-14"]), "name1": ["Holger Rune", "Aa Alpha"],
                            "name2": ["Gastao Elias", "Bb Beta"], "draw": "main", "uid": [7, 9]})
    idx = M.placement_index(matches, aliases.iloc[[0]])
    assert idx["M|Biella 1|2021-02-14|Holger Rune|Gastao Elias"] == 7 == idx["M|Biella 6 CH|2021-05-17|Holger Rune|Gastao Elias"]
    # an alias naming another match's key: the key places neither
    idx = M.placement_index(matches, aliases)
    assert "M|Biella 1|2021-02-14|Aa Alpha|Bb Beta" not in idx.index
    assert M.placement_index(matches, aliases.iloc[[0]], with_draw=True).index[0].endswith("|main")
    # the SofaScore placement reads them: a frozen row under the old key finds the merged match
    rows = pd.DataFrame({"event_id": ["11"]})
    frozen = pd.DataFrame({"tour": ["M"], "tname": ["Biella 1"], "d": ["2021-02-14"], "name1": ["Holger Rune"],
                           "name2": ["Gastao Elias"], "creator": ["tml"], "event_id": ["11"]})
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "sofascore_x_matches.csv"
        frozen.to_csv(path, index=False)
        assert M.sofascore_edition_uids(rows, matches, [path], aliases=aliases.iloc[[0]]).tolist() == [7]
        assert pd.isna(M.sofascore_edition_uids(rows, matches, [path]).iloc[0])   # without it: unplaced


def test_a_row_found_at_its_own_date_is_never_moved():
    # the pair met in the same round with the same score at both editions: the near one is the row's own match
    tml = rows(("Biella 1", "2021-02-14", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "a"))
    refs = rows(("Biella 1 CH", "2021-02-08", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "a"),
                ("Biella 6 CH", "2021-05-17", "Aa Alpha", "Bb Beta", "R32", "6-4 6-4", "b"))
    assert M.repair_tml_dates(tml, [("sackmann", refs.iloc[[1]]), ("tennislive_listed", refs.iloc[[0]])])[1].empty


def test_tennislive_for_the_editions_sackmann_lacks_and_the_event_follows():
    # Tenerife 3 of 2024 under Tenerife 1's date; Sackmann lacks the event, TennisLive lists it (player 1 first)
    tml = rows(("Tenerife 1", "2024-01-21", "Mikhail Kukushkin", "Matteo Gigante", "F", "6-2 2-0 RET", "2024-2847"),
               ("Tenerife 1", "2024-01-21", "Matteo Gigante", "Alejandro Moro Canas", "QF", "7-6(3) 7-5", "2024-2847"),
               ("Tenerife 1", "2024-01-21", "Martin Landaluce", "Lukas Neumayer", "QF", "6-3 6-3", "2024-2847"))
    listed = rows(("Tenerife 3 Challenger", "2024-02-26", "Matteo Gigante", "Mikhail Kukushkin", "F", "2-6 0-2",
                   "atp:1"),
                  ("Tenerife 3 Challenger", "2024-02-26", "Alejandro Moro Canas", "Matteo Gigante", "QF",
                   "6-7(3) 5-7", "atp:1"))
    fixed, rep = M.repair_tml_dates(tml, [("sackmann", rows()), ("tennislive_listed", listed)])
    assert fixed["d"].eq(pd.Timestamp("2024-02-26")).all() and fixed["tname"].eq("Tenerife 3 Challenger").all()
    # the final and Gigante's quarter-final are found; Landaluce v Neumayer moves with its event (2 of 3 found)
    assert sorted(rep["source"]) == ["event", "tennislive_listed", "tennislive_listed"]
    assert rep.loc[rep["source"].eq("event"), "name1"].tolist() == ["Martin Landaluce"]
    # an event half of whose rows were not found stays where it is but for the found rows
    more = pd.concat([tml, tml.assign(name1=["X1 Y", "X2 Y", "X3 Y"], name2=["Z1 W", "Z2 W", "Z3 W"])],
                     ignore_index=True)
    fixed, rep = M.repair_tml_dates(more, [("tennislive_listed", listed)])
    assert len(rep) == 2 and set(rep["source"]) == {"tennislive_listed"}
