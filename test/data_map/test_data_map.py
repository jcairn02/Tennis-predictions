"""The data map's measurement and build helpers (offline: synthetic rows and the tracked catalog)."""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import build as B  # noqa: E402
from src.eda.data_map import measure as M  # noqa: E402


@pytest.mark.parametrize("name, key", [
    ("Carlos Alcaraz", "alcaraz"), ("C. Alcaraz", "alcaraz"), ("ALCARAZ C.", "alcaraz"),
    ("F. Auger-Aliassime", "aliassime"), ("Felix Auger Aliassime", "aliassime"),
    ("Alex de Minaur", "minaur"), ("A. De Minaur", "minaur"), ("M.Dhamne", "dhamne"),
    ("Botic van de Zandschulp", "zandschulp"), ("Nuñez", "nunez"), (None, ""), ("", "")])
def test_surname_key(name, key):
    assert M.surname_key(name) == key


def test_pair_key_is_symmetric_and_needs_two_names():
    out = M.pair_key(pd.Series(["alcaraz", "sinner", ""]), pd.Series(["sinner", "alcaraz", "tiafoe"]))
    assert out[0] == out[1] == "alcaraz|sinner"
    assert pd.isna(out[2])


@pytest.mark.parametrize("a, b, same", [
    ("Riske", "Alison Riske Amritraj", True),                          # married name added
    ("Wu Tung-Lin", "Tung-Lin Wu", True),                              # surname first
    ("F. MELIGENI RODRIGUE", "Felipe Meligeni Rodrigues Alves", True),  # cut at 20 characters
    ("M. PUCINELLI DE ALME", "Matheus Pucinelli De Almeida", True),
    ("Alex Molcan", "Alex de Minaur", False),                          # a shared first name is not enough
    ("S Sanders", "Storm Hunter", False)])
def test_same_player(a, b, same):
    assert M.same_player(a, b) is same


@pytest.mark.parametrize("a, b, same", [
    ("Storm Sanders", "Storm Hunter", True),                           # married name, same first name
    ("MARIYA KOSTYUK", "Mariia Kostiuk", True),                        # transliteration
    ("D. Gavrilova", "Daria Saville", True), ("Sinner J.", "Jannik Sinner", True),   # initials, either side
    ("Wu Tung-Lin", "Tung-Lin Wu", True), ("Riske", "Alison Riske Amritraj", True),
    ("Maria Camila Osorio Serrano", "Camila Osorio", True),            # two words shared
    ("Mari Osaka", "Naomi Osaka", False), ("Jessica Pieri", "Tatiana Pieri", False),   # sisters
    ("MARY LIU", "Claire Liu", False), ("SITONG CHEN", "Chenting Zhu", False)])
def test_same_first_name(a, b, same):
    assert M.same_first_name(a, b) is same


def test_wta_site_names_and_rounds():
    assert M.wta_site_name("SANDERS, STORM AUS") == "STORM SANDERS"
    assert M.wta_site_name("OSORIO SERRANO, MARIA CAMILA COL") == "MARIA CAMILA OSORIO SERRANO"
    assert M.wta_site_name("LEE, ANN") == "ANN LEE"                     # a three-letter first name stays
    assert M.wta_site_name("Storm Sanders ") == "Storm Sanders"
    m = pd.DataFrame({"pseudo_tournament_id": ["slam"] * 3 + ["w25"] * 2 + ["w25"] * 3,
                      "qpm_flag": ["Q"] * 5 + ["M"] * 3,
                      "round_name": ["R128", "R64", "R32", "R32", "R16", "Q", "S", "R32"]})
    # the site names a qualifying round by its place in the draw: a tournament's first is Q1
    assert list(M.wta_site_rounds(m)) == ["Q1", "Q2", "Q3", "Q1", "Q2", "QF", "SF", "R32"]


def test_universe_keeps_namesakes_apart_and_links_changed_surnames():
    u = M.Universe(pd.Timestamp("2026-09-20"))
    base = _rows(("W", "2019-08-05", "Naomi Osaka", "Tatjana Maria", "T250", "main", "R32", "result"),
                 ("W", "2021-06-28", "Storm Hunter", "Aleksandra Krunic", "GSQ", "qual", "Q2", "result"),
                 ("W", "2021-01-10", "Clara Burel", "Anna Kalinskaya", "GSQ", "qual", "Q2", "result"))   # played in Dubai
    placed = u.add("base", base)
    feed = _rows(("W", "2019-08-12", "Mari Osaka", "Maria Jose Portillo Ramirez", "ITF", "main", "R32", "result"),
                 ("W", "2021-06-28", "Storm Sanders", "Aleksandra Krunic", "GSQ", "qual", "Q2", "result"),
                 ("W", "2021-02-08", "Clara Burel", "Anna Kalinskaya", "GSQ", "qual", None, "result"))   # dated by the Slam
    got = u.add("feed", feed)
    assert got["uid"].iloc[0] not in set(placed["uid"])          # a sister, not the same player
    assert got["uid"].iloc[1] == placed["uid"].iloc[1]          # through the round, after a surname change
    assert got["uid"].iloc[2] == placed["uid"].iloc[2]          # Slam qualifying four weeks early
    assert len(u.matches) == 4


def test_levels_from_codes_and_names():
    assert M.tour_level_atp("M", "Cincinnati Masters") == "T1000"
    assert M.tour_level_atp("M", "Winston-Salem") == "T250"          # Tennis My Life's 2026 label
    assert M.tour_level_atp("A", "Next Gen Finals") == "FIN"
    assert M.tour_level_atp("A", "Laver Cup") == "TEAM"
    assert M.tour_level_atp("250", "United Cup") == "TEAM"
    assert M.tour_level_atp("D", "Davis Cup WG1 R1: AUT vs BEL") == "TEAM"
    assert M.tour_level_wta("P5", "Dubai") == "T1000"
    assert M.tour_level_wta("I", "Hobart") == "T250"
    assert M.tour_level_wta("W", "Buenos Aires 125") == "CH"
    assert M.tour_level_wta("50+H", "W50+H Macon") == "ITF"
    assert M.tour_level_wta("25", "W25 Sharm El Sheikh") == "ITF"
    assert (M.to_qual("T500"), M.to_qual("GS"), M.to_qual("CH"), M.to_qual(None)) == ("TQ", "GSQ", "CHQ", None)


def test_rounds():
    assert M.canon_round("Round of 32") == "R32"
    assert M.canon_round("qualifying round 2") == "Q2"
    assert M.canon_round("RR") is None
    assert M.slam_round("Q", False) == "QF" and M.slam_round("1", True) == "Q1"
    assert M.slam_round("Final Round", True) == "Q3" and M.slam_round("4th Round", False) == "R16"


def test_last_complete_sunday():
    assert M.last_complete_sunday(datetime(2026, 9, 25)) == pd.Timestamp("2026-09-20")   # Friday
    assert M.last_complete_sunday(datetime(2026, 9, 27)) == pd.Timestamp("2026-09-20")   # Sunday itself
    assert M.last_complete_sunday(datetime(2026, 9, 28)) == pd.Timestamp("2026-09-27")   # Monday


def _rows(*matches):
    cols = ["tour", "d", "name1", "name2", "level", "draw", "round", "grain"]
    return pd.DataFrame([dict(zip(cols, m)) for m in matches])


def test_universe_counts_a_match_once_and_adds_the_rest():
    u = M.Universe(pd.Timestamp("2026-09-20"))
    base = _rows(("M", "2023-03-06", "Carlos Alcaraz", "Jannik Sinner", "T1000", "main", "SF", "stats"),   # Indian Wells
                 ("M", "2023-03-20", "Carlos Alcaraz", "Jannik Sinner", "T1000", "main", "SF", "stats"),   # Miami
                 ("W", "2023-06-26", "Elena Rybakina", "Alison Riske Amritraj", "T250", "main", "R32", "result"))
    placed = u.add("base", base)
    assert len(u.matches) == 3 and placed["uid"].notna().all()
    feed = _rows(("M", "2023-03-12", "C. Alcaraz", "J. Sinner", None, "main", None, "point"),   # dated by the day played
                 ("W", "2023-06-28", "Rybakina", "Riske", None, "main", None, "point"),
                 ("M", "2023-03-12", "C. Alcaraz", "F. Tiafoe", None, "main", None, "shot"))   # on no list
    got = u.add("feed", feed)
    assert got["uid"].iloc[0] == placed["uid"].iloc[0]          # the nearer tournament, not Miami
    assert got["uid"].iloc[1] == placed["uid"].iloc[2]          # through the married name
    assert len(u.matches) == 4                                   # the Tiafoe match joins the list
    assert u.report["feed"]["linked_to_known_match"] == 2 and u.report["feed"]["added_as_new_match"] == 1
    m, _ = M.best_grains(u)
    best = dict(zip(m["uid"], m["best"]))
    assert best[placed["uid"].iloc[0]] == "point" and best[placed["uid"].iloc[1]] == "stats"


def test_expected_missing_uses_draw_sizes_and_the_last_season():
    end = pd.Timestamp("2026-09-20")                             # ISO week 38
    rows = [{"tour": "W", "level": "GSQ", "year": 2026, "d": pd.Timestamp("2026-01-10")}] * 336
    for wk in range(1, 39):
        rows += [{"tour": "M", "level": "ITF", "year": 2025, "d": pd.Timestamp.fromisocalendar(2025, wk, 1)}] * 100
        if wk <= 22:
            rows += [{"tour": "M", "level": "ITF", "year": 2026, "d": pd.Timestamp.fromisocalendar(2026, wk, 1)}] * 100
    out = M.expected_missing(pd.DataFrame(rows), end).set_index(["tour", "level", "year"])["missing"]
    assert out[("W", "GSQ", 2026)] == 448 - 336                  # four Slams' qualifying, 112 matches each
    assert out[("M", "ITF", 2026)] == 100 * (38 - 22)            # the weeks after the files stop


def test_catalog_is_sound():
    assert B.check_catalog(B.load_catalog()) == []


def test_catalog_check_reads_the_universe():
    cat = {"datasets": [], "methods": [], "universe": {
        "routes": [{"id": "collect_now"}],
        "sources": [{"id": "s", "route": "maybe", "select": {"tours": ["M"], "levels": ["ITF"]},
                     "shares": {"points": 0.5}}]}}
    problems = B.check_catalog(cat)
    for text in ("unknown route 'maybe'", "select needs tours, levels and years", "unknown grain 'points'"):
        assert any(text in p for p in problems), text


def test_held_counts_each_match_once_per_dataset_and_method():
    held = pd.DataFrame({"uid": [1, 1, 1, 2], "tour": "M", "year": [2024, 2024, 2024, 2025],
                         "dataset": ["sofascore", "sofascore_editions", "tml", "tml"],
                         "how": ["browser_scrape", "browser_scrape", "site_files", "site_files"]})
    assert sorted(B.method_matches(held), key=lambda r: r["how"]) == [
        {"how": "browser_scrape", "matches": 1}, {"how": "site_files", "matches": 2}]
    years = {(r["dataset"], r["year"]): r["matches"] for r in B.dataset_years(held)}
    assert years == {("sofascore", 2024): 1, ("sofascore_editions", 2024): 1, ("tml", 2024): 1, ("tml", 2025): 1}


def test_locked_counts_read_only_file_names(tmp_path, monkeypatch):
    for route, code in (("match-beats", "ms001"), ("court-vision", "ms001"), ("match-beats", "qs001"),
                        ("rally-analysis", "ms002")):
        folder = tmp_path / "raw" / "point_sources" / "infosys_atp" / "2019" / "0339" / route
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{code}.json.gz").write_bytes(b"encrypted")
    monkeypatch.setattr(B, "DATA", tmp_path)
    monkeypatch.setattr(B, "_tml_levels", lambda: {(2019, "0339"): "T250"})
    got = {(r["level"], r["grain"]): r["matches"] for r in B.locked_counts()}
    assert got == {("T250", "point"): 1, ("T250", "shot"): 1, ("TQ", "point"): 1}


def test_live_progress_reads_only_running_downloads(tmp_path, monkeypatch):
    (tmp_path / "data" / "raw" / "x").mkdir(parents=True)
    (tmp_path / "data" / "raw" / "x" / "a.json").write_text("{}")
    monkeypatch.setattr(B, "PROJECT_ROOT", tmp_path)
    cat = {"datasets": [{"id": "x", "status": "downloading", "raw": "data/raw/x/"},
                        {"id": "y", "status": "on_disk", "raw": "data/raw/y/"}]}
    live = B.live_progress(cat)["datasets"]
    assert set(live) == {"x"} and live["x"]["files_on_disk"] == 1 and live["x"]["last_write"]


def test_render_embeds_the_data_once():
    full, fragment = B.render({"x": "</script>"})
    assert full.startswith("<!doctype html>") and "<title>Tennis Data Map</title>" in full
    assert "/*__DATA__*/" not in full and '"x":"<\\/script>"' in full
    assert "<!doctype" not in fragment.lower() and "<head>" not in fragment


def test_wta_site_reads_the_newest_copy_and_adds_each_api_match_once(tmp_path, monkeypatch):
    """P2(b): the WTA API's player-matches results join the Kaggle copy's rows; a match both hold is kept once."""
    root, api = tmp_path / "bwandowando", tmp_path / "player_results"
    root.mkdir()
    api.mkdir()
    monkeypatch.setattr(M, "WTA_SITE", root)
    monkeypatch.setattr(M, "WTA_SITE_API", api)
    monkeypatch.setattr(M, "CACHE", tmp_path / "cache")
    tournaments = pd.DataFrame({"pseudo_tournament_id": [11, 12], "title": ["WTT W50 - LEIRIA, PORTUGAL", "OLD"],
                                "startDate": ["2026-08-31", "2026-01-05"], "level": ["ITF", "ITF"],
                                "tournamentGroupId": [4826, 2403]})
    matches = pd.DataFrame({"pseudo_match_id": [1, 2], "pseudo_tournament_id": [11, 11], "reason_code": ["W", "W"],
                            "round_name": ["R32", "R32"], "qpm_flag": ["Q", "M"],
                            "team_name_1": ["WALKER,  BRANDY  USA", "MORTENSEN,  REBECCA MUNK  DEN"],
                            "team_name_2": ["MORTENSEN,  REBECCA MUNK  DEN", "KINOSHITA,  HAYU  JPN"],
                            "scores": ["7-6(3)  6-1", "6-0  7-5"]})
    tournaments.to_csv(root / "tournaments.csv", index=False)
    matches.to_csv(root / "matches.csv", index=False)
    assert len(M.load_wta_site(refresh=True)) == 2
    results = pd.DataFrame({"tournament_group_id": ["4826", "4826", "9999"],
                            "start_date": ["2026-08-31", "2026-08-31", "2026-09-21"],
                            "title": ["WTT W50 - LEIRIA, PORTUGAL"] * 2 + ["WTT W35 - YECLA, SPAIN"],
                            "level": ["ITF"] * 3, "qpm_flag": ["M", "Q", "M"], "round_name": ["R32", "R16", "R32"],
                            "winner_name": ["Hayu Kinoshita", "Rebecca Munk Mortensen", "Sofia Rojas"],
                            "loser_name": ["Rebecca Munk Mortensen", "Maria Toma", "Rebecca Munk Mortensen"]})
    results.to_parquet(api / "2026.parquet", index=False)
    out = M.load_wta_site()  # the API file changes the signature: the cache is rebuilt
    assert len(out) == 4     # Leiria's main-draw R32 is the copy's; its qualifying R16 and Yecla are new
    assert sorted(out["round"]) == ["Q1", "Q2", "R32", "R32"]  # the R16 is Leiria's second qualifying round
    assert sorted(out["level"]) == ["ITF", "ITF", "ITFQ", "ITFQ"]
    v30 = root / "v30"
    v30.mkdir()
    tournaments.to_csv(v30 / "tournaments.csv", index=False)
    matches.iloc[:1].to_csv(v30 / "matches.csv", index=False)
    assert M.wta_site_folder() == v30 and len(M.load_wta_site()) == 4  # the API row now fills the main-draw match


def test_wta_site_leaves_out_the_copys_misfiled_editions(tmp_path, monkeypatch):
    """The copy's last ten editions (7-14 Sep 2026) file their matches under the wrong editions (P6 data issues, 14 Oct
    2026): their listings are left out, and the WTA API's row places the match under its true edition."""
    root, api = tmp_path / "bwandowando", tmp_path / "player_results"
    root.mkdir()
    api.mkdir()
    monkeypatch.setattr(M, "WTA_SITE", root)
    monkeypatch.setattr(M, "WTA_SITE_API", api)
    monkeypatch.setattr(M, "CACHE", tmp_path / "cache")
    montreux, guiyang = 163248187558, 322715938447
    assert {montreux, guiyang} <= M.WTA_SITE_MISFILED
    pd.DataFrame({"pseudo_tournament_id": [montreux, guiyang],
                  "title": ["Montreux Nestlé Open - Montreux, SUI", "WTT W50 - GUIYANG, CHINA"],
                  "startDate": ["2026-09-07"] * 2, "level": ["WTA 125", "ITF"],
                  "tournamentGroupId": [1112, 4209]}).to_csv(root / "tournaments.csv", index=False)
    pd.DataFrame({"pseudo_match_id": [1], "pseudo_tournament_id": [montreux], "reason_code": ["W"],
                  "round_name": ["R32"], "qpm_flag": ["M"], "team_name_1": ["WANG,  YAFAN  CHN"],
                  "team_name_2": ["ASTAKHOVA,  ALEKSANDRA  RUS"],
                  "scores": ["7-6(5)  7-5"]}).to_csv(root / "matches.csv", index=False)
    assert len(M.load_wta_site(refresh=True)) == 0          # the copy's listing alone: left out
    pd.DataFrame({"tournament_group_id": ["4209"], "start_date": ["2026-09-07"], "title": ["WTT W50 - GUIYANG, CHINA"],
                  "level": ["ITF"], "qpm_flag": ["M"], "round_name": ["R32"], "winner_name": ["Yafan Wang"],
                  "loser_name": ["Aleksandra Astakhova"]}).to_parquet(api / "2026.parquet", index=False)
    out = M.load_wta_site()
    assert len(out) == 1 and out["tname"].iloc[0] == "WTT W50 - GUIYANG, CHINA" and out["level"].iloc[0] == "ITF"


def test_the_map_and_the_feed_leave_out_the_same_misfiled_editions():
    from src.eda.lower_level_evidence import candidate_stage0 as F
    assert M.WTA_SITE_MISFILED == F.WTA_SITE_MISFILED and len(M.WTA_SITE_MISFILED) == 10


def test_infosys_challengers_rows_take_the_copys_day_and_the_atp_ids(tmp_path, monkeypatch):
    """The ATP's Challenger point files (staged on their own, 14 Oct 2026): a code with points or rally entries is a
    point row dated by the copy's match day (else Stage 0's tournament date), a qualifying code falls back to CHQ, and
    a code with neither is left out."""
    folder = tmp_path / "points" / "infosys_challengers"
    folder.mkdir(parents=True)
    monkeypatch.setattr(M, "DUMP", tmp_path)
    pd.DataFrame({"year": ["2022", "2022", "2023"], "event_id": ["9695", "9695", "2877"],
                  "match_id": ["MS022", "QS003", "MS020"], "family": ["MS", "QS", "MS"],
                  "round_from_code": ["R32", None, "R32"], "points": ["183", "0", "0"], "rally_entries": ["90", "0", "0"],
                  "p1_id": ["h0dz", "a111", "b222"], "p1_name": ["G. Heide", "A. One", "B. Two"],
                  "p1_last_name": ["Heide", None, None], "p2_id": ["l0aa", "c333", "d444"],
                  "p2_name": ["A. Lingua Lavallen", "C. Three", "D. Four"], "p2_last_name": ["Lingua Lavallen", None, None],
                  "copy_match_date": ["2022-04-26", None, None],
                  "stage0_tournament_date": ["2022-04-25", "2022-04-25", "2023-04-24"]}).to_parquet(
        folder / "matches.parquet", index=False)
    out = M.load_infosys_challengers()
    assert len(out) == 1                                   # the two codes without points or rally entries are left out
    r = out.iloc[0]
    assert str(r["d"])[:10] == "2022-04-26" and r["grain"] == "point" and r["level_fallback"] == "CH"
    assert r["name1"] == "Heide" and r["draw"] == "main"


@pytest.mark.parametrize("value, name", [('["Bernarda PERA"]', "Bernarda PERA"), ("Kaja JUVAN", "Kaja JUVAN"),
                                         ("[]", "[]"), ("", ""), (None, "")])
def test_first_listed(value, name):
    assert M.first_listed(value) == name


def test_rolandgarros_rows_are_played_codes_dated_by_their_schedule_day(tmp_path, monkeypatch):
    """Roland-Garros's own statistics (16 Oct 2026): a played code with statistics is a stats row at GS or GSQ, dated by
    its schedule day, else the day it ended, else the main draw's first day; walkovers and absent codes are left out."""
    folder = tmp_path / "points" / "rolandgarros"
    folder.mkdir(parents=True)
    monkeypatch.setattr(M, "DUMP", tmp_path)
    pd.DataFrame({
        "year": ["2026", "2026", "2026", "2026", "2026"], "match_id": ["SM008", "QD040", "QD041", "SD100", "QD127"],
        "tour": ["M", "W", "W", "W", "W"], "draw": ["main", "qual", "qual", "main", "qual"],
        "round_from_code": ["R16", "Q2", "Q2", "R128", "Q1"], "answer": ["ok", "ok", "ok", "ok", "absent"],
        "date_schedule": ["20260531", "", "", "20260525", ""],
        "end_timestamp": ["1780245000000", "1779465600000", "", "", ""],
        "a_names": ['["Jannik SINNER"]', '["Diane PARRY"]', '["Kaja JUVAN"]', '["Anna BLINKOVA"]', None],
        "b_names": ['["Carlos ALCARAZ"]', '["Leolia JEANJEAN"]', '["Katie SWAN"]', '["Mirra ANDREEVA"]', None],
        "a_end_cause": ["", "r.", "", "", ""], "b_end_cause": ["", "", "", "w/o.", ""],
        "has_statistics": ["TRUE", "TRUE", "TRUE", "FALSE", ""]}).to_parquet(folder / "matches.parquet", index=False)
    out = M.load_rolandgarros({(2026, "RG"): pd.Timestamp("2026-05-24")}).reset_index(drop=True)
    assert len(out) == 3                                   # the walkover and the absent code are left out
    assert list(out["level"]) == ["GS", "GSQ", "GSQ"] and list(out["draw"]) == ["main", "qual", "qual"]
    assert [str(d)[:10] for d in out["d"]] == ["2026-05-31", "2026-05-22", "2026-05-24"]
    assert set(out["grain"]) == {"stats"} and out["name2"].iloc[1] == "Leolia JEANJEAN"   # a retirement is played
    assert set(out["slam"]) == {"RG"}


def _named(rows, *tnames):
    rows["tname"] = list(tnames)
    return rows


def test_infosys_slams_rows_carry_their_slam_and_full_names(tmp_path, monkeypatch):
    """The AO and RG Infosys match centres (16 Oct 2026): a code with points is a point row and one with set statistics
    only a stats row, named in full and dated by its match day, else its Slam's first day; a code with neither is left
    out. Placed within its edition, a qualifying match the map lacks is added, not given to the pair's meeting at the
    event before (the generic passes' 40-day Slam qualifying window reaches it)."""
    folder = tmp_path / "points" / "infosys_slams"
    folder.mkdir(parents=True)
    monkeypatch.setattr(M, "DUMP", tmp_path)
    pd.DataFrame({
        "slam": ["AO", "AO", "RG"], "year": ["2025", "2025", "2026"], "tour": ["W", "W", "W"],
        "draw": ["main", "qual", "qual"], "round_from_code": ["R128", "Q1", "Q1"], "points": ["150", "0", "0"],
        "keystats_sets": ["2", "2", "0"], "match_date": ["2025-01-13", None, None],
        "p1_first_name": ["Xiyu", "Yafan", "A"], "p1_last_name": ["Wang", "Wang", "One"],
        "p1_name": ["X. Wang", "Y. Wang", "A. One"], "p2_first_name": ["Julia", "Talia", "B"],
        "p2_last_name": ["Grabher", "Gibson", "Two"], "p2_name": ["J. Grabher", "T. Gibson", "B. Two"]}).to_parquet(
        folder / "matches.parquet", index=False)
    starts = {(2025, "AO"): pd.Timestamp("2025-01-12")}
    out = M.load_infosys_slams(starts).reset_index(drop=True)
    assert len(out) == 2                                   # the code with neither points nor statistics is left out
    assert list(out["grain"]) == ["point", "stats"] and set(out["slam"]) == {"AO"}
    assert list(out["name1"]) == ["Xiyu Wang", "Yafan Wang"]
    assert [str(d)[:10] for d in out["d"]] == ["2025-01-13", "2025-01-12"]
    u = M.Universe(pd.Timestamp("2025-12-28"))
    known = u.add("tml", _named(_rows(("W", "2025-01-12", "Xiyu Wang", "Julia Grabher", "GS", "main", "R128", "result"),
                                      ("W", "2025-01-06", "Yafan Wang", "Talia Gibson", "T500", "main", "R32", "result")),
                                "Australian Open", "Adelaide"))
    got = u.add("infosys_slams", out)
    assert got["uid"].iloc[0] == known["uid"].iloc[0] and u.report["infosys_slams"]["added_as_new_match"] == 1
    assert known["uid"].iloc[1] not in set(got["uid"])     # not the pair's meeting at Adelaide


def test_slam_rows_are_placed_within_their_own_edition():
    """A Grand Slam row takes the copy of its match nearest its own day, never a meeting of the pair at another event,
    and a match the map lacks joins it; between two copies on one day, the first known."""
    u = M.Universe(pd.Timestamp("2026-10-11"))
    known = u.add("tml", _named(_rows(
        ("M", "2026-05-31", "Jannik Sinner", "Carlos Alcaraz", "GS", "main", "R16", "point"),     # the day played
        ("W", "2026-06-08", "Kaja Juvan", "Katie Swan", "T250", "main", "R32", "result")),       # Nottingham
        "Roland Garros", "Nottingham"))
    copy = u.matches[u.matches["uid"].eq(known["uid"].iloc[0])].assign(uid=99, d=pd.Timestamp("2026-05-24"))
    u.matches = pd.concat([u.matches, copy], ignore_index=True)    # a second copy, dated by the event's start
    rg = _rows(("M", "2026-05-31", "Jannik SINNER", "Carlos ALCARAZ", "GS", "main", "R16", "stats"),
               ("W", "2026-05-20", "Kaja JUVAN", "Katie SWAN", "GSQ", "qual", "Q2", "stats"),     # no copy on the map
               ("W", "2026-05-22", "Diane PARRY", "Leolia JEANJEAN", "GSQ", "qual", "Q3", "stats"))
    got = u.add("rolandgarros", rg.assign(slam="RG"))
    assert got["uid"].iloc[0] == known["uid"].iloc[0]
    assert u.report["rolandgarros"]["linked_to_known_match"] == 1 and u.report["rolandgarros"]["added_as_new_match"] == 2
    assert known["uid"].iloc[1] not in set(got["uid"]) and 99 not in set(got["uid"])
    assert list(u.matches.loc[u.matches["creator"].eq("rolandgarros"), "level"]) == ["GSQ", "GSQ"]
    later = u.add("sackmann", rg.iloc[:1].assign(d="2026-05-24"))   # dated by the event's start: the copy of that day
    assert later["uid"].iloc[0] == 99


def test_the_linker_keeps_slam_matches_and_other_events_apart():
    """A Slam row does not take the pair's meeting at another event when the two tie on the generic passes' dates
    (the 2021 Australian Open quarter-final Djokovic-Zverev and their ATP Cup match six days earlier), and a row of
    another level does not take a Slam match (the Challenger of the week after the US Open)."""
    u = M.Universe(pd.Timestamp("2021-12-26"))
    known = u.add("tml", _named(_rows(
        ("M", "2021-02-08", "Novak Djokovic", "Alexander Zverev", "GS", "main", "QF", "result"),
        ("M", "2021-02-02", "Novak Djokovic", "Alexander Zverev", "TEAM", "main", "RR", "result"),
        ("M", "2019-08-26", "Denis Istomin", "Mischa Zverev", "GSQ", "qual", "Q2", "result")),
        "Australian Open", "ATP Cup", "US Open"))
    sack = u.add("sackmann", _rows(("M", "2021-02-08", "N. Djokovic", "A. Zverev", "GS", "main", "QF", "stats"),
                                   ("M", "2019-09-09", "Denis Istomin", "Mischa Zverev", "CH", "main", "R32", "stats")))
    assert sack["uid"].iloc[0] == known["uid"].iloc[0]
    assert sack["uid"].iloc[1] not in set(known["uid"]) and u.report["sackmann"]["added_as_new_match"] == 1


def test_slam_rows_with_hidden_first_names_or_no_level_join_their_match():
    """The WTA's lists write surnames only ('Sherif Ahmed Abdelaziz'); api-tennis gives Slam rows no level and writes
    'H. Hsu Yu': both join the known match of their edition."""
    u = M.Universe(pd.Timestamp("2024-12-29"))
    known = u.add("tml", _named(_rows(("W", "2024-05-26", "Madison Keys", "Mayar Sherif", "GS", "main", "R64", "point"),
                                      ("M", "2023-01-16", "Alex de Minaur", "Yu Hsiou Hsu", "GS", "main", "R128", "point")),
                                "Roland Garros", "Australian Open"))
    lists = u.add("wta_lists", _rows(("W", "2024-05-30", "Keys", "Sherif Ahmed Abdelaziz", "GS", "main", None, "stats")))
    api = u.add("api_tennis", _named(_rows(("M", "2023-01-17", "H. Hsu Yu", "A. De Minaur", None, "main", None, "result")),
                                     "Australian Open"))
    assert lists["uid"].iloc[0] == known["uid"].iloc[0] and api["uid"].iloc[0] == known["uid"].iloc[1]
    assert len(u.matches) == 2


def test_a_slam_match_a_source_lists_twice_under_two_spellings_joins_once():
    u = M.Universe(pd.Timestamp("2026-10-11"))
    u.add("tml", _named(_rows(("M", "2026-05-24", "Jannik Sinner", "Carlos Alcaraz", "GS", "main", "R128", "point")),
                        "Roland Garros"))
    got = u.add("wta_site", _rows(("W", "2026-05-18", "IRENE BURILLO", "VIKTORIYA TOMOVA", "GSQ", "qual", "Q1", "result"),
                                  ("W", "2026-05-18", "Viktoria Tomova-Traycheva", "Irene Burillo", "GSQ", "qual", "Q1",
                                   "result")))
    assert got["uid"].nunique() == 1 and int(u.matches["creator"].eq("wta_site").sum()) == 1


@pytest.mark.parametrize("row, known, placed", [
    (("Valentin Royer", "Marc Polmans", "Q1", "GSQ"),                       # first names alone never place
     [(1, "Valentin Vacherot", "Marc-Andrea Huesler", "Q1", "GSQ")], None),
    (("Cori Gauff", "Mayar Sherif", "R64", "GS"),                            # a nickname, the same round
     [(1, "Coco Gauff", "Mayar Sherif Ahmed Abdelaziz", "R64", "GS")], 1),
    (("Xiyu Wang", "Julia Grabher", None, "GS"),                             # namesakes: the first name decides
     [(1, "Yafan Wang", "Julia Grabher", "R64", "GS"), (2, "Xiyu Wang", "Julia Grabher", "R128", "GS")], 2),
    (("Von Deichmann", "Klimovicova", None, "GSQ"),                          # surnames only (the WTA's lists)
     [(1, "Kathinka Von Deichmann", "Linda Klimovicova", "Q1", "GSQ")], 1),
    (("Cori Gauff", "Sorana Cirstea", None, "GS"),                           # a nickname, no round
     [(1, "Coco Gauff", "Sorana Cirstea", "R64", "GS")], 1),
    (("Paula Badosa", "Denisa Allertova", "Q1", "GSQ"),                      # a changed surname, the same round
     [(1, "Paula Badosa Gibert", "Denisa Satralova", "Q1", "GSQ")], 1),
    (("Erika Andreeva", "Aryna Sabalenka", "R128", "GS"),                     # sisters: the round and the first name
     [(1, "Mirra Andreeva", "Aryna Sabalenka", "QF", "GS"), (2, "Erika Andreeva", "Aryna Sabalenka", "R128", "GS")], 2),
    (("Katie Boulter", "Tatjana Maria", "R128", "GS"),                       # a surname that is another's first name
     [(1, "Katie Volynets", "Maria Lourdes Carle", "R128", "GS")], None),
    (("Radu Albot", "Michael Mmoh", "Q3", "GSQ"),                            # a mislabelled round (SofaScore's copy)
     [(1, "Radu Albot", "Roberto Marcora", "Q1", "GSQ"), (2, "Radu Albot", "Michael Mmoh", "Q2", "GSQ")], 2),
    (("Radu Albot", "Joao Sousa", "F", "GSQ"),                               # 'Final' for the qualifying's last round
     [(1, "Radu Albot", "Joao Sousa", "Q3", "GSQ")], 1),
    (("Sobolieva", "Belgraver", None, "GSQ"),                                # a transliteration, a letter apart
     [(1, "Anastasiya Soboleva", "Julie Belgraver", "Q2", "GSQ")], 1),
    (("Kiki Bertens", "J. Görges", "QF", "GS"),                              # 'Görges' / 'Goerges'
     [(1, "Julia Goerges", "Kiki Bertens", "QF", "GS")], 1),
    (("Xinyu Wang", "Julia Grabher", None, "GS"),                            # surnames under five letters: never
     [(1, "Xinyu Wong", "Julia Grabher", "R64", "GS")], None),
    (("Radu Albot", "Joao Sousa", "R64", "GS"),                              # qualifying filed as main draw
     [(1, "Radu Albot", "Joao Sousa", "Q3", "GSQ")], 1),
    (("Radu Albot", "Joao Sousa", "Q3", "GSQ"),                              # a qualifier who met again in the draw
     [(1, "Radu Albot", "Joao Sousa", "R128", "GS"), (2, "Radu Albot", "Joao Sousa", "Q3", "GSQ")], 2)])
def test_slam_place_needs_a_surname_for_each_player(row, known, placed):
    d = pd.Timestamp("2026-05-25")
    got = M.slam_place(*row, d, [(*k, d) for k in known])
    assert (pd.isna(got) and placed is None) or got == placed


def test_slam_editions_by_own_slam_name_or_window():
    starts = {(2020, "USO"): pd.Timestamp("2020-08-31"), (2020, "RG"): pd.Timestamp("2020-09-27"),
              (2021, "AO"): pd.Timestamp("2021-02-08")}
    frame = pd.DataFrame({"d": pd.to_datetime(["2020-09-11", "2020-09-23", "2020-09-01", "2021-01-11", "2020-12-01",
                                               "2021-01-10", "2020-09-05"]),
                          "year": [2020, 2020, 2020, 2021, 2020, 2021, 2020],
                          "tname": [None, None, "Roland Garros", None, None, "Doha Aus Open Qualies", "Us Open"],
                          "slam": [None] * 7})
    # the nearest first day of the windows that hold it; a name decides ("Aus Open" is not the US Open); the 2021
    # AO's qualifying six weeks early
    assert list(M.slam_editions(frame, starts)) == ["USO", "RG", "RG", "AO", None, "AO", "USO"]
