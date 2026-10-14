"""The link check's verdicts: a SofaScore event against the official winner and score (offline, synthetic)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import verify_links as V  # noqa: E402
from src.ingest.point_sources import sofascore_editions as E  # noqa: E402

RESULT_COLUMNS = ["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"]


def write_results(root: Path, rel: str, rows) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=RESULT_COLUMNS).to_parquet(path)


def result_files(root: Path) -> None:
    write_results(root, "tennis_my_life/atp_challenger/2025_challenger.parquet",
                  [("Maia", "20251124", "R32", "Ann Bee", "Cid Dee", "6-4 6-4")])
    write_results(root, "tennis_my_life/atp_qualifying/2025_atp_quali.parquet",   # qualifying whatever the round
                  [("Houston", "20250331", "R32", "Jan Struff", "Ugo Ray", "6-2 6-2")])
    write_results(root, "sackmann_archive/atp/atp_matches_qual_chall_2025.parquet",
                  [("Maia", "20251124", "R32", "Ann Bee", "Cid Dee", "6-3 6-3"),
                   ("Maia", "20251124", "Q1", "Eve Fox", "Gus Hil", "7-5 6-1")])
    write_results(root, "sackmann_archive/atp/atp_matches_qual_chall_2017.parquet",    # before the map's years
                  [("Maia", "20171120", "R32", "Old Man", "Older Man", "6-0 6-0")])


def event(home, away, home_sets, away_sets, winner=1):
    hs = {f"period{n}": g for n, g in enumerate(home_sets, 1)}
    aw = {f"period{n}": g for n, g in enumerate(away_sets, 1)}
    return {"homeTeam": {"name": home}, "awayTeam": {"name": away}, "homeScore": hs, "awayScore": aw,
            "winnerCode": winner}


def test_scores_are_read_winner_first():
    assert V.tml_sets("6-7(2) 7-6(3) 7-5 RET") == [(6, 7), (7, 6), (7, 5)]
    assert V.ss_sets(event("Ann Bee", "Cid Dee", [4, 6], [6, 3], winner=2)) == [(6, 4), (3, 6)]


def test_verdicts():
    basel = event("Reilly Opelka", "Botic Van de Zandschulp", [6, 6], [4, 4])
    assert V.compare(basel, "Reilly Opelka", "6-4 6-4") == "agrees"
    assert V.compare(basel, "Botic van de Zandschulp", "6-4 6-4") == "winner differs"
    retired = event("Ann Bee", "Cid Dee", [6, 0], [3, 0])   # SofaScore adds the set never started
    assert V.compare(retired, "Ann Bee", "6-3 RET") == "agrees"
    assert V.compare(event("Ann Bee", "Cid Dee", [], [], winner=2), "Cid Dee", "4-3 RET") == \
        "winner agrees, SofaScore lists no score"
    assert V.compare(event("Ann Bee", "Cid Dee", [7, 5], [6, 4]), "Ann Bee", "7-6(3) 5-7 6-3") == \
        "winner agrees, score differs"
    # a default ends the match like a retirement: SofaScore's unstarted 0-0 set is left aside (Adelaide 2022)
    assert V.compare(event("Laslo Djere", "Corentin Moutet", [4, 7, 0], [6, 5, 0]), "Laslo Djere", "4-6 7-5 DEF") == \
        "agrees"
    # winner code 3 (a retirement SofaScore gives no winner) or none (cancelled): no winner to compare
    assert V.compare(event("Ann Bee", "Cid Dee", [4], [1], winner=3), "Ann Bee", "4-1 RET") == "SofaScore lists no winner"
    assert V.compare(event("Ann Bee", "Cid Dee", [], [], winner=None), "Ann Bee", "6-2 6-2") == "SofaScore lists no winner"


def test_official_rows_read_both_result_files_tennis_my_life_first(tmp_path, monkeypatch):
    result_files(tmp_path)
    monkeypatch.setattr(V, "RESULTS", tmp_path)
    rows = {tuple(r[:5]): (r[5], r[6]) for r in V.official_rows().itertuples(index=False)}
    assert rows == {("Maia", "2025-11-24", "Ann Bee", "Cid Dee", "main"): ("6-4 6-4", "tml"),
                    ("Houston", "2025-03-31", "Jan Struff", "Ugo Ray", "qual"): ("6-2 6-2", "tml"),
                    ("Maia", "2025-11-24", "Eve Fox", "Gus Hil", "qual"): ("7-5 6-1", "sackmann")}
    assert set(V.official_rows({"Houston"})["tourney_name"]) == {"Houston"}


def test_check_reports_the_file_read_and_targets_it_cannot_check(tmp_path, monkeypatch):
    result_files(tmp_path)
    monkeypatch.setattr(V, "RESULTS", tmp_path)
    d = pd.Timestamp("2025-11-24")
    targets = pd.DataFrame([
        {"gap": "g", "edition": "M|Maia|2025|w48", "uid": i, "tour": "M", "level": lv, "draw": dr, "year": 2025,
         "d": d, "tname": "Maia", "name1": a, "name2": b, "creator": cr, "best": "stats", "sources": cr}
        for i, (lv, dr, a, b, cr) in enumerate([("CH", "main", "Ann Bee", "Cid Dee", "tml"),
                                                ("CHQ", "qual", "Eve Fox", "Gus Hil", "sackmann"),
                                                ("CH", "main", "Hal Ivy", "Jo Kay", "api_tennis"),
                                                ("CH", "main", "Lu May", "Ned Oz", "tml")])])
    monkeypatch.setattr(E, "load_targets", lambda gap, refresh: (targets[E.TARGET_COLUMNS], "test targets"))
    monkeypatch.setattr(E, "known_matches", lambda t: t[["tour", "tname", "year", "d", "name1", "name2"]])
    linked = {1: event("Ann Bee", "Cid Dee", [6, 6], [4, 4]), 2: event("Gus Hil", "Eve Fox", [5, 1], [7, 6], winner=2),
              3: event("Hal Ivy", "Jo Kay", [6], [0])}
    rows = [{**t, "listed": i < 3, "event_id": i + 1 if i < 3 else None}
            for i, t in enumerate(targets.to_dict(orient="records"))]
    monkeypatch.setattr(E, "list_and_link", lambda *a, **k: ([], rows, linked))
    frame, summary = V.check("g")
    assert frame["verdict"].tolist() == ["agrees", "agrees", "no official row", "not linked"]
    assert frame["official"].fillna("none").tolist() == ["tml", "sackmann", "none", "none"]
    assert summary["no_official_row_by_creator"] == {"api_tennis": 1}
    assert summary["by_official_file"]["sackmann"] == {"agrees": 1}


def test_the_itf_gaps_link_check_is_written_gzipped(tmp_path, monkeypatch):
    frame = pd.DataFrame({"d": [pd.Timestamp("2024-01-01").date()], "edition": ["W|W15 Monastir|2024|w01"], "uid": [1],
                          "verdict": ["agrees"]})
    summary = {"verdicts": {"agrees": 1}, "no_official_row_by_creator": {}, "events_linked_by_two_targets": []}
    monkeypatch.setattr(V, "check", lambda gap: (frame, summary))
    monkeypatch.setattr(E, "STUDY", tmp_path)
    monkeypatch.setattr(sys, "argv", ["verify_links.py", "--gap", "itf_detail"])
    assert V.main() == 0
    written = tmp_path / "sofascore_itf_detail_link_check.csv.gz"
    assert written.read_bytes()[:2] == b"\x1f\x8b" and pd.read_csv(written)["verdict"].tolist() == ["agrees"]
    assert (tmp_path / "sofascore_itf_detail_link_check.json").exists()
