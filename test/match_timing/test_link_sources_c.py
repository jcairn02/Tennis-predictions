"""Sources-C linker (src/eda/match_timing/link_sources_c.py and srcc_*.py): names, rounds, set scores, the identity
linker's passes and guards, venue zones and local days, and the links files' schema (offline, synthetic rows; the last
test reads the written links files when they exist)."""
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.match_timing import srcc_common as K  # noqa: E402
from src.eda.match_timing import srcc_sofascore as SS  # noqa: E402
from src.eda.match_timing import srcc_tdi as TD  # noqa: E402
from src.eda.match_timing import srcc_tz as TZ  # noqa: E402
from src.eda.match_timing import srcc_wta as W  # noqa: E402


def test_name_grades():
    assert K.name_grade("Zhang Zhizhen", "Zhizhen Zhang") == 3                 # words in any order
    assert K.name_grade("Tomás Barrios Vera", "Tomas Barrios Vera") == 3       # accents
    assert K.name_grade("Martin Damm Jr", "Martin Damm") == 3                  # suffix dropped
    assert K.name_grade("Tara Wuerth", "Tara Würth") == 3                      # umlaut written out
    assert K.name_grade("Łukasz Kubot", "Lukasz Kubot") == 3                   # letters NFKD does not fold
    assert K.name_grade("Albert Ramos-Vinolas", "Albert Ramos") == 2           # one name inside the other
    assert K.name_grade("J. Pla Malfeito", "Jaume Pla Malfeito") == 2          # initial + surname
    assert K.name_grade("Aleksandr Shevchenko", "Alexander Shevchenko") == 2   # surname + initial
    assert K.name_grade("Daniel Galan", "Daniel Rincon") == 0                  # a shared given name is no evidence
    assert K.name_grade("Storm Sanders", "Storm Hunter") == 0


def test_round_codes_and_grades():
    codes = [K.round_code(x) for x in ["Round of 16", "Qualification round 1", "Qualification Final", "Qualification",
                                       "R128", "1/8-finals (R16)", "Quarterfinal", "1st Round Qualifying", "Final",
                                       "2nd Round", "Round of 28", "Round of 96", None]]
    assert codes == ["R16", "Q1", "QLAST", "Q?", "R128", "R16", "QF", "Q1", "F", "N2", "R32", "R128", None]
    assert K.round_grade("N2", "R64", 2.0, False, None) == 2
    assert K.round_grade("N2", "QF", float("nan"), False, None) == 0
    assert K.round_grade("QLAST", "Q3", float("nan"), True, 3.0) == 2
    assert K.round_grade("QLAST", "Q2", float("nan"), True, 3.0) == 0
    assert K.round_grade("Q?", "Q2", float("nan"), True, 3.0) == 1
    assert K.round_grade(None, "F", float("nan"), False, None) == 1


def test_set_scores():
    mt = K.s0_sets("7-5 2-6 [10-4]")
    assert mt == ((7, 5), (2, 6), (1, 0, "mt"))
    assert K.sets_equal(((7, 5), (2, 6), (1, 0)), mt)          # the WTA list's 1-0 for a match tiebreak
    assert K.sets_equal(((7, 5), (2, 6), (10, 4)), mt)         # the tiebreak's points
    assert not K.sets_equal(((7, 5), (2, 6), (0, 1)), mt)      # the other side won it
    assert not K.sets_equal(((7, 5), (2, 6)), mt)              # a set missing
    ret = K.s0_sets("6-3 2-1 RET")
    assert K.sets_equal(((6, 3), (2, 1), (0, 0)), ret)         # SofaScore's unplayed 0-0 set
    assert not K.sets_equal(((6, 3),), ret)
    assert not K.sets_equal((), ret)


def stage0_rows():
    """A tiny Stage 0 slice in stage0()'s columns."""
    rows = [
        # (match_id, tour, level, qual, round, round_no, tid, tdate, a, b, a_won, score)
        ("m1", "wta", "T500", False, "QF", None, "2021-2026", "2021-01-31", "Shelby Rogers", "Ashleigh Barty", False,
         "7-5 2-6 [10-4]"),
        ("m2", "wta", "GS", False, "R16", 4.0, "2021-580", "2021-02-08", "Shelby Rogers", "Ashleigh Barty", True,
         "6-3 6-4"),
        ("m3", "wta", "T250", False, "R32", 1.0, "2022-2058", "2022-01-03", "Viktoria Hruncakova", "Olga Govortsova",
         True, "6-1 RET"),
        ("m4", "atp", "CH", False, "R32", 1.0, "2025-111", "2025-03-03", "Juan Perez", "Carlos Lopez", True, "6-4 6-4"),
        ("m5", "atp", "CH", False, "R32", 1.0, "2025-111", "2025-03-03", "Juan Perez", "Carlos Lopez", True, "6-4 6-4"),
    ]
    m = pd.DataFrame(rows, columns=["match_id", "tour", "level", "qualifying", "round", "round_no", "tournament_id",
                                    "tdate", "name_a", "name_b", "a_won", "score"])
    m["tdate"] = pd.to_datetime(m["tdate"])
    m["round_no"] = m["round_no"].astype("float64")
    m["qmax"] = float("nan")
    m["sets_w"] = m["score"].map(K.s0_sets)
    m["player_a_id"] = ["wta:1", "wta:1", "wta:3", "atp:5", "atp:5"]
    m["player_b_id"] = ["wta:2", "wta:2", "wta:4", "atp:6", "atp:6"]
    return m


def source(rows):
    s = pd.DataFrame(rows, columns=["sid", "tour", "day", "p1", "p2", "sets", "rnd", "qual", "tid"])
    s["day"] = pd.to_datetime(s["day"])
    return s


def test_linker_passes_and_guards():
    m = stage0_rows()
    src = source([
        # the Yarra Valley QF: match tiebreak written 1-0, the WTA's round number 4 (the AO's R16 is also round 4)
        ("yarra", "wta", "2021-02-05", "Ashleigh Barty", "Shelby Rogers", ((7, 5), (2, 6), (1, 0)), "N4", False,
         "2021-2026"),
        # married name: Stage 0 writes Hruncakova, the source Kuzmova; identical scores and round -> anchor pass
        ("kuz", "wta", "2022-01-04", "Olga Govortsova", "Viktoria Kuzmova", ((1, 6), (0, 0)), "N1", False, None),
        # two identical Stage 0 matches: ambiguous
        ("amb", "atp", "2025-03-04", "Juan Perez", "Carlos Lopez", ((6, 4), (6, 4)), "R32", False, None),
        # nobody of that name
        ("none", "atp", "2025-03-04", "Nobody Here", "Carlos Lopez", ((6, 4), (6, 4)), "R32", False, None),
    ])
    res = K.link(src, m)
    got = dict(zip(res["links"]["sid"], res["links"]["match_id"]))
    assert got["yarra"] == "m1"                                  # not the AO R16 (m2)
    assert got["kuz"] == "m3" and res["links"].set_index("sid").loc["kuz", "pass"] == "anchor"
    assert "amb" not in got and sorted(res["ambiguous"]["amb"]) == ["m4", "m5"]
    assert res["reason"]["amb"].startswith("ambiguous")
    assert res["reason"]["none"] == "no Stage 0 match with both players in the window"


def test_linker_never_takes_another_tournament():
    m = stage0_rows()
    # names, round (on a plausible day) agree with the AO R16, but the source names the Yarra Valley event
    src = source([("x", "wta", "2021-02-09", "Ashleigh Barty", "Shelby Rogers", ((5, 7), (4, 6)), "N4", False,
                   "2021-2026")])
    assert K.link(src, m)["links"].empty
    src = source([("x", "wta", "2021-02-09", "Ashleigh Barty", "Shelby Rogers", ((5, 7), (4, 6)), "N4", False, None)])
    assert K.link(src, m)["links"]["match_id"].tolist() == ["m2"]   # without the id, round + plausible day suffice


def test_round_only_needs_a_plausible_day():
    m = stage0_rows()
    # AO R16 (tournament date 8 Feb): round agrees, scores do not, played 3 days before the main draw -> rejected
    src = source([("x", "wta", "2021-02-05", "Ashleigh Barty", "Shelby Rogers", ((5, 7), (4, 6)), "N4", False, None)])
    assert K.link(src, m)["links"].empty


def test_zones_and_local_days():
    assert TZ.zone_for("AUS", "Melbourne") == "Australia/Melbourne"
    assert TZ.zone_for("AUS", None) is None                     # a multi-zone country needs its city
    assert TZ.zone_for("USA", "Indian Wells") == "America/Los_Angeles"
    assert TZ.zone_for("FRA", "Noumea") == "Pacific/Noumea"     # overseas exception
    assert TZ.zone_for("FRA", "Lyon") == "Europe/Paris"
    assert TZ.zone_for("ESP", "Las Palmas") == "Atlantic/Canary"
    assert TZ.country_code("U.S.A.") == "USA" and TZ.country_code("Korea Republic") == "KOR"
    utc = pd.Series(pd.to_datetime(["2026-01-18 23:30", "2026-01-18 23:30", "2026-03-08 06:30"], utc=True))
    zones = pd.Series(["Australia/Melbourne", "America/New_York", "America/Los_Angeles"])
    got = K.local_day(utc, zones).dt.strftime("%Y-%m-%d").tolist()
    assert got == ["2026-01-19", "2026-01-18", "2026-03-07"]   # +11 h; -5 h; -8 h before the clock change
    assert W.edition_zone("INDIAN WELLS", "CA, UNITED STATES") == "America/Los_Angeles"
    assert W.edition_zone("BUDAPEST", "HUNGARY") == "Europe/Budapest"


def test_gap_links_read_every_gap_once(tmp_path):
    cols = ["gap", "uid", "event_id", "tour", "d", "name1", "name2", "ss_round"]
    files = {"atp_points_2025": [["atp_points_2025", "7", "11", "M", "2025-01-06", "Ann Bee", "Cid Dee", "Final"]],
             "tour_points_rest": [["tour_points_rest", "7", "22", "W", "2019-01-07", "Eve Fox", "Gus Hil", "Round of 32"],
                                  ["tour_points_rest", "8", None, "W", "2019-01-07", "Ivy Jo", "Kay Lu", None]],
             # an overlapping gap lists the same target again
             "atp_points_2018_2020": [["atp_points_2018_2020", "7", "22", "W", "2019-01-07", "Eve Fox", "Gus Hil",
                                       "Round of 32"]]}
    for gap, rows in files.items():
        pd.DataFrame(rows, columns=cols).to_csv(tmp_path / f"sofascore_{gap}_matches.csv", index=False)
    # a list frozen before its first run has no link columns yet
    pd.DataFrame({"gap": ["wta_2018_points"], "uid": ["9"], "tour": ["W"], "d": ["2018-01-01"], "name1": ["A B"],
                  "name2": ["C D"]}).to_csv(tmp_path / "sofascore_wta_2018_points_matches.csv", index=False)
    g = SS.gap_links(tmp_path)
    assert sorted(g["event_id"]) == ["11", "22"]
    # uid 7 of two map builds stays two keys
    assert sorted("uid:" + g["gap"] + ":" + g["uid"]) == ["uid:atp_points_2018_2020:7", "uid:atp_points_2025:7"]
    # the ITF gaps' lists are gzipped
    pd.DataFrame([["itf_detail", "3", "33", "W", "2024-01-01", "Ann Bee", "Cid Dee", "Final"]], columns=cols).to_csv(
        tmp_path / "sofascore_itf_detail_matches.csv.gz", index=False)
    assert sorted(SS.gap_links(tmp_path)["event_id"]) == ["11", "22", "33"]


def test_source_place_parsers():
    assert SS.place("Australian Open, Melbourne, Australia, Qualifying") == ("AUS", "melbourne")
    assert SS.place("Manacor, Singles M-ITF-ESP-02A") == ("ESP", "manacor")
    assert SS.place("Spain F30, Singles") == ("ESP", None)
    assert SS.place("Coquimbo 2, Chile, Qualifying") == ("CHI", "coquimbo")
    assert TD.place_zone("Cincinnati, OH, U.S.A.")[2] == "America/New_York"
    assert TD.place_zone("Porto, Potugal")[2] == "Europe/Lisbon"
    assert TD.tdi_sets("1:6 2:2 3:6", "1:4 2:6 3:4") == ((6, 4), (2, 6), (6, 4))


def test_write_links_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(K, "LINKS", tmp_path)
    f = pd.DataFrame({"match_id": ["a", "b"], "source_key": ["k1", "k2"],
                      "date_local": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                      "start_utc": [pd.Timestamp("2024-01-02 10:00", tz="UTC"), pd.NaT],
                      "date_basis": ["local", "utc_date"], "link_method": ["x", "y"],
                      "score_agrees": [True, None], "round_agrees": [None, False]})
    path = K.write_links(f, "demo", flag=False)
    t = pq.read_table(path)
    assert t.schema.names == K.LINK_COLUMNS
    assert str(t.schema.field("date_local").type) == "date32[day]"
    assert str(t.schema.field("start_utc").type) == "timestamp[ms, tz=UTC]"
    back = t.to_pandas()
    assert back["source"].tolist() == ["demo", "demo"] and back["score_agrees"].isna().tolist() == [False, True]
    with pytest.raises(AssertionError):
        K.write_links(pd.concat([f, f]), "dup", flag=False)      # one row per Stage 0 match


@pytest.mark.parametrize("name", ["tennis_data", "wta_api", "sofascore", "slam_feeds", "tdi", "sirgenkii"])
def test_written_links_files(name):
    path = K.LINKS / f"{name}.parquet"
    if not path.exists():
        pytest.skip("links not built yet")
    t = pq.read_table(path)
    assert t.schema.names == K.LINK_COLUMNS
    d = t.to_pandas()
    assert not d["match_id"].duplicated().any() and not d["source_key"].duplicated().any()
    assert set(d["date_basis"].unique()) <= {"local", "utc_date"} and (d["source"] == name).all()
    assert d["date_local"].notna().all()
