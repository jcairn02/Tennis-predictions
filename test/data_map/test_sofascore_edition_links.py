"""The map places the by-edition SofaScore rows on the matches its adapter linked them to (offline, synthetic)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M  # noqa: E402


def test_adapter_links_beat_a_meeting_the_week_before(tmp_path):
    links = tmp_path / "sofascore_atp_points_2025_matches.csv"
    pd.DataFrame({"tour": "M", "tname": ["Mallorca", "Mallorca", "Halle", "Rotterdam", "Rotterdam"],
                  "d": ["2026-06-24", "2026-06-25", "2026-06-19", "2026-02-09", "2026-02-13"],
                  "name1": ["Ann Bee", "Cid Dee", "Eve Eff", "Ugo Humbert", "Ugo Humbert"],
                  "name2": ["Gus Hay", "Ivo Jay", "Kim Ell", "Chris Oconnell", "Chris O'Connell"],
                  "creator": ["tml", "tml", "tml", "sackmann", "tml"],
                  "event_id": ["11", None, "33", "55", "55"]}).to_csv(links, index=False)
    # 2026 matches are dated by the day played: the pair also met at Eastbourne five days earlier, which the
    # generic link would prefer (|5 - 3| < |0 - 3|); Halle's key names two matches, so it places neither;
    # Rotterdam's match is in the map twice (two spellings), and Tennis My Life's row takes the event
    matches = pd.DataFrame({"uid": [1, 2, 3, 4, 5, 6, 7], "tour": "M",
                            "tname": ["Mallorca", "Mallorca", "Eastbourne", "Halle", "Halle", "Rotterdam", "Rotterdam"],
                            "d": pd.to_datetime(["2026-06-24", "2026-06-25", "2026-06-19", "2026-06-19", "2026-06-19",
                                                 "2026-02-09", "2026-02-13"]),
                            "name1": ["Ann Bee", "Cid Dee", "Ann Bee", "Eve Eff", "Eve Eff", "Ugo Humbert",
                                      "Ugo Humbert"],
                            "name2": ["Gus Hay", "Ivo Jay", "Gus Hay", "Kim Ell", "Kim Ell", "Chris Oconnell",
                                      "Chris O'Connell"]})
    rows = pd.DataFrame({"event_id": ["11", "22", "33", "44", "55"]})
    got = M.sofascore_edition_uids(rows, matches, paths=[links])
    assert got.iloc[0] == 1 and got.iloc[1:4].isna().all() and got.iloc[4] == 7
    assert M.sofascore_edition_uids(rows, matches, paths=[]).isna().all()
    # a gap's list frozen before its first run (no link columns yet) is read without error and places nothing
    frozen = tmp_path / "sofascore_wta_2018_points_matches.csv"
    pd.DataFrame({"gap": ["wta_2018_points"], "tour": ["W"], "tname": ["Halle"], "d": ["2026-06-19"],
                  "name1": ["Eve Eff"], "name2": ["Kim Ell"], "creator": ["tml"]}).to_csv(frozen, index=False)
    assert M.sofascore_edition_uids(rows, matches, paths=[links, frozen]).equals(got)


def test_the_gzipped_itf_lists_are_read_too(tmp_path, monkeypatch):
    folder = tmp_path / "studies" / "gap_downloads"
    folder.mkdir(parents=True)
    pd.DataFrame({"tour": ["W"], "tname": ["W15 Monastir"], "d": ["2024-01-01"], "name1": ["Ann Bee"],
                  "name2": ["Cid Dee"], "creator": ["sackmann"], "event_id": ["77"]}).to_csv(
        folder / "sofascore_itf_detail_matches.csv.gz", index=False)
    matches = pd.DataFrame({"uid": [5], "tour": ["W"], "tname": ["W15 Monastir"], "d": pd.to_datetime(["2024-01-01"]),
                            "name1": ["Ann Bee"], "name2": ["Cid Dee"]})
    monkeypatch.setattr(M, "DATA", tmp_path)
    assert M.sofascore_edition_uids(pd.DataFrame({"event_id": ["77", "78"]}), matches).tolist()[0] == 5


def test_flashscore_feeds_are_placed_on_the_targets_linked(tmp_path):
    table = tmp_path / "flashscore_itf_points_2025_2026_matches.csv.gz"
    pd.DataFrame({"tour": ["M", "M", "W"], "tname": ["M15 Monastir", "M15 Monastir", "W35 Reus"],
                  "d": ["2025-03-17", "2025-03-17", "2025-04-07"], "name1": ["Tommy Paul", "Tom Paul", "Ann Bee"],
                  "name2": ["Reilly Opelka", "Reilly Opelka", "Cid Dee"], "fs_id": ["AAA", "AAA", ""]}).to_csv(
        table, index=False)
    # the map holds Paul v Opelka twice (two spellings): the feed is credited to both copies
    matches = pd.DataFrame({"uid": [1, 2, 3], "tour": ["M", "M", "W"], "year": [2025, 2025, 2025],
                            "tname": ["M15 Monastir", "M15 Monastir", "W35 Reus"],
                            "d": pd.to_datetime(["2025-03-17", "2025-03-17", "2025-04-07"]),
                            "name1": ["Tommy Paul", "Tom Paul", "Ann Bee"],
                            "name2": ["Reilly Opelka", "Reilly Opelka", "Cid Dee"]})
    rows = pd.DataFrame({"fs_id": ["AAA", "ZZZ"], "tour": "M", "d": pd.to_datetime(["2025-03-19", "2025-03-20"]),
                         "name1": ["Paul T.", "Who X."], "name2": ["Opelka R.", "Else Y."], "tname": "M15 Monastir"})
    got = M.flashscore_point_uids(rows, matches, paths=[table])
    placed = got.dropna(subset=["preset_uid"])
    assert sorted(placed["preset_uid"].astype(int)) == [1, 2] and set(placed["fs_id"]) == {"AAA"}
    assert placed["d"].eq(pd.Timestamp("2025-03-17")).all() and set(placed["name1"]) == {"Tommy Paul", "Tom Paul"}
    assert got.loc[got["fs_id"].eq("ZZZ"), "preset_uid"].isna().all()   # a feed no target named stays unplaced
    assert len(M.flashscore_point_uids(rows, matches, paths=[])) == 2


def test_p6s_flashscore_links_are_read_and_the_refused_ones_left_out(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "DATA", tmp_path)
    p13 = tmp_path / "studies" / "gap_downloads" / "flashscore_itf_points_2025_2026_matches.csv.gz"
    p6 = tmp_path / "studies" / "p6_data_issues" / "flashscore" / "fetch_matches.csv.gz"
    for p in (p13, p6):
        p.parent.mkdir(parents=True)
    pd.DataFrame({"tour": ["M"], "tname": ["M15 Monastir"], "d": ["2025-03-17"], "name1": ["Tommy Paul"],
                  "name2": ["Reilly Opelka"], "fs_id": ["AAA"]}).to_csv(p13, index=False)
    # one feed linked to two targets; the link check refused the borrowed one (Galan shares only "Daniel")
    pd.DataFrame({"tour": ["M", "M"], "tname": ["Barcelona", "Monterrey"], "d": ["2019-04-22", "2019-04-07"],
                  "name1": ["Marcel Granollers", "Marcel Granollers"], "name2": ["Daniel Evans", "Daniel Elahi Galan"],
                  "fs_id": ["BBB", "BBB"], "level": ["TQ", "CH"], "link_refused": [False, True]}).to_csv(p6, index=False)
    matches = pd.DataFrame({"uid": [1, 2, 3], "tour": "M", "year": [2025, 2019, 2019],
                            "tname": ["M15 Monastir", "Barcelona", "Monterrey"],
                            "d": pd.to_datetime(["2025-03-17", "2019-04-22", "2019-04-07"]),
                            "name1": ["Tommy Paul", "Marcel Granollers", "Marcel Granollers"],
                            "name2": ["Reilly Opelka", "Daniel Evans", "Daniel Elahi Galan"]})
    rows = pd.DataFrame({"fs_id": ["AAA", "BBB"], "tour": "M", "d": pd.to_datetime(["2025-03-19", "2019-04-23"]),
                         "name1": ["Paul T.", "Granollers M."], "name2": ["Opelka R.", "Evans D."],
                         "tname": ["M15 Monastir", "Barcelona"]})
    got = M.flashscore_point_uids(rows, matches)          # the default tables: P13's and P6's
    assert sorted(zip(got["fs_id"], got["preset_uid"].astype(int))) == [("AAA", 1), ("BBB", 2)]


def test_p6s_flashscore_records_leave_level_and_draw_to_their_match(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "DUMP", tmp_path)
    path = tmp_path / "points" / "flashscore_points" / "matches.parquet"
    path.parent.mkdir(parents=True)
    pd.DataFrame({"fs_id": ["AAA", "BBB", "CCC"], "tour": "M", "fs_date": ["20250318", "20190422", "20190422"],
                  "grade": ["M15", "atp-singles", "challenger-men-singles"], "fs_tournament": ["M15 Monastir", "Barcelona", "Monterrey"],
                  "fs_home": ["Paul T.", "Granollers M.", "Galan D. E."], "fs_away": ["Opelka R.", "Evans D.", "Kicker N."],
                  "feed_status": "200", "fb_points": ["120", "150", "0"]}).to_parquet(path)
    got = M.load_flashscore_points().set_index("fs_id")
    assert list(got.index) == ["AAA", "BBB"]                 # a feed without points is left out
    assert (got.loc["AAA", "level"], got.loc["AAA", "draw"]) == ("ITF", "main")
    assert got.loc["BBB", ["level", "draw"]].isna().all() and got.loc["BBB", "d"] == pd.Timestamp("2019-04-22")


def test_wta_125_category_is_a_womens_challenger_level():
    # SofaScore's category 871 is named 'WTA 125' (observed 9 Oct 2026); unmapped, its records would be dropped
    assert (M.SOFASCORE_TOUR["WTA 125"], M.SOFASCORE_FALLBACK["WTA 125"]) == ("W", "CH")
