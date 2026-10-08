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
