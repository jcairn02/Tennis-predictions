"""Flashscore's ITF point feeds (work package P13): the feed parser, the link to the handoff copy's records, the
trial's spread, and a whole run against a fake Flashscore (offline; every answer is canned, the folders temporary)."""
import argparse
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import flashscore_points as F  # noqa: E402


def feed(*recs) -> str:
    """A feed in Flashscore's separators from dicts of codes."""
    return F.SEP_R.join(F.SEP_F.join(f"{k}{F.SEP_KV}{v}" for k, v in r.items()) + F.SEP_F for r in recs)


# set 1: two service holds, then a tiebreak 7-5 for home; the record's score is 2-1 (a toy set)
SET1 = [{"HA": "Set 1", "HB": "Point by point - Set 1"},
        {"HC": 1, "HE": 0, "HG": 1, "HK": 1, "HL": "15:0, 30:0, 40:0"},
        {"HC": 1, "HE": 1, "HG": 2, "HK": 2, "HL": "0:15, 15:15, 15:30, 30:30, 40:30 |B1|, 40:40, 40:A |B2|"},
        {"HC": 2, "HD": 7, "HE": 1, "HF": 5, "HK": 1},
        {"HB": "Tiebreak - Set 1"}]
TB = [(1, 0, 1, 1), (1, 1, 2, 2), (2, 1, 2, 1), (3, 1, 1, 1), (3, 2, 1, 2), (4, 2, 2, 1), (5, 2, 2, 1), (5, 3, 1, 2),
      (5, 4, 1, 2), (6, 4, 2, 1), (6, 5, 2, 2), (7, 5, 1, 1)]   # (home, away after, server, winner)
TB_RECS = [{"HC": h, "HE": a, "HG": s, "HK": w, **({"HM": "2,1"} if (h, a) == (6, 4) else {})} for h, a, s, w in TB]
FEED_OK = feed(*SET1, *TB_RECS, {"A1": ""})


def test_point_winner_steps():
    assert F.point_winner("0:0", "15:0") == 1 and F.point_winner("30:30", "30:40") == 2
    assert F.point_winner("40:40", "A:40") == 1 and F.point_winner("A:40", "40:40") == 2   # advantage lost
    assert F.point_winner("40:A", "40:40") == 1 and F.point_winner("40:40", "40:A") == 2
    assert F.point_winner("15:0", "40:0") is None and F.point_winner("15:0", "x") is None    # not a legal step


def test_feed_parse_games_points_tiebreak_and_marks():
    parsed = F.parse_feed(FEED_OK)
    assert (parsed["n_sets"], parsed["n_games"], parsed["score"], parsed["irregular"]) == (1, 3, "2-1", 0)
    g1, g2, tb = parsed["sets"][0]["games"]
    assert [p["winner"] for p in g1["points"]] == [1, 1, 1, 1] and g1["server"] == 1 and not g1["broken"]
    assert [p["winner"] for p in g2["points"]] == [2, 1, 2, 1, 1, 2, 2, 2]   # the last point is the game winner's
    assert tb["tiebreak"] and len(tb["points"]) == 12 and tb["games_after"] == (2, 1)
    assert [p["winner"] for p in tb["points"]] == [w for *_, w in TB]
    rows = F.point_rows("abc", parsed)
    assert len(rows) == parsed["n_points"] == 4 + 8 + 12
    flags = [(r["break_point"], r["set_point"]) for r in rows]
    assert flags[8] == (True, False) and flags[10] == (False, True)        # 40:30 |B1| and 40:A |B2| of game 2
    assert rows[4 + 8 + 9]["set_point"] and rows[4 + 8 + 9]["score_after"] == "6:4"   # the tiebreak's HM 2,1


def test_verdicts_against_the_records_own_score():
    parsed = F.parse_feed(FEED_OK)
    assert F.verdict(parsed, "2-1") == "complete"
    assert F.verdict(parsed, "2-1 6-0") == "short"        # a set missing
    assert F.verdict(parsed, "6-4") == "short"            # games missing
    assert F.verdict(parsed, "1-0") == "other"
    assert F.verdict(parsed, "") == "no score to compare"
    assert F.verdict(F.parse_feed(""), "6-4") == "empty"


def test_surname_words_and_the_link_rule():
    assert F.surname_words("Cunha Winheski de Lima V.") == ["cunha", "winheski", "de", "lima"]
    assert F.surname_words("Lee Y.-H.") == ["lee"]
    handoff = pd.DataFrame([
        {"fs_id": "AAA", "fs_date": "20250318", "tour": "M", "grade": "M15", "fs_tournament": "M15 Monastir",
         "fs_home": "Paul T.", "fs_away": "Opelka R.", "fs_score": "6-4 6-4", "fs_duration": "1:20"},
        {"fs_id": "BBB", "fs_date": "20250319", "tour": "M", "grade": "M25", "fs_tournament": "M25 Monastir",
         "fs_home": "Gima S.", "fs_away": "Varillas J.", "fs_score": "6-1 6-1", "fs_duration": ""},
        {"fs_id": "CCC", "fs_date": "20250320", "tour": "M", "grade": "M15", "fs_tournament": "M15 Monastir",
         "fs_home": "Varillas J.", "fs_away": "Gima S.", "fs_score": "6-2 6-2", "fs_duration": "1:00"},
        {"fs_id": "DDD", "fs_date": "20250501", "tour": "M", "grade": "M15", "fs_tournament": "M15 Antalya",
         "fs_home": "Paul T.", "fs_away": "Opelka R.", "fs_score": "6-0 6-0", "fs_duration": ""}])
    targets = pd.DataFrame([
        {"d": "2025-03-17", "tour": "M", "tname": "M15 Monastir", "name1": "Reilly Opelka", "name2": "Tommy Paul"},
        {"d": "2025-03-17", "tour": "M", "tname": "M15 Monastir", "name1": "Sebastian Gima", "name2": "Juan Pablo Varillas"},
        {"d": "2025-03-17", "tour": "M", "tname": "Monastir", "name1": "Sebastian Gima", "name2": "Juan Pablo Varillas"},
        {"d": "2025-03-17", "tour": "W", "tname": "W15 Monastir", "name1": "Reilly Opelka", "name2": "Tommy Paul"}])
    links = F.link_targets(targets, handoff)
    assert links["fs_id"].tolist()[:2] == ["AAA", "CCC"]          # either order; the grade breaks the Gima tie
    assert links.loc[2, "link_note"] == "tie: 2 records name the pair" and pd.isna(links.loc[2, "fs_id"])
    assert links.loc[3, "link_note"] == "no record names the pair"   # another tour
    assert links.loc[0, "fs_score"] == "6-4 6-4" and links.loc[0, "candidates"] == 1   # Antalya is outside the week


def test_the_trial_spreads_over_months_and_tours():
    linked = pd.DataFrame({"fs_id": [f"id{i}" for i in range(40)], "tour": ["M", "W"] * 20,
                           "fs_date": [f"2025{m:02d}15" for m in range(1, 5) for _ in range(10)]})
    picked = F.trial_sample(linked, 8, seed=1)
    assert len(picked) == 8 and picked.groupby([picked["fs_date"].str[:6], "tour"]).size().eq(1).all()
    assert picked.index.tolist() == F.trial_sample(linked, 8, seed=1).index.tolist()


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self.content, self.url = status, body, "http://fake"
        self.headers = {"content-type": "text/plain"}


class FakeClient:
    impersonate = "fake"

    def __init__(self, answers):
        self.answers, self.requests, self.urls = answers, 0, []

    def get(self, url, headers=None):
        self.requests += 1
        self.urls.append(url)
        return FakeResponse(200, self.answers.get(url, "").encode("utf-8"))

    def stats(self):
        return {"requests": self.requests}


@pytest.fixture
def folders(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(F, "STUDY", tmp_path / "studies")
    return tmp_path


def test_a_run_links_fetches_parses_and_stages(folders, monkeypatch):
    rows = [{"fs_id": "AAA", "fs_date": "20250318", "tour": "M", "grade": "M15", "fs_tournament": "M15 Monastir",
             "fs_home": "Paul T.", "fs_away": "Opelka R.", "fs_score": "2-1", "fs_status": "3", "fs_start_ts": "1",
             "fs_end_ts": "2", "fs_duration": "1:20", "handoff_file": "x"},
            {"fs_id": "BBB", "fs_date": "20250410", "tour": "W", "grade": "W35", "fs_tournament": "W35 Reus",
             "fs_home": "Bee A.", "fs_away": "Dee C.", "fs_score": "6-1 6-1", "fs_status": "3", "fs_start_ts": "5",
             "fs_end_ts": "5", "fs_duration": "", "handoff_file": "x"}]
    P.stage_table(F.SOURCE, P.dump_path(F.SOURCE, "handoff_itf.parquet"), F.HANDOFF_COLUMNS,
                  [[r[c] for c in F.HANDOFF_COLUMNS] for r in rows], source_file="x", retrieved_at=None)
    targets = pd.DataFrame([
        {"gap": "itf_points_2025_2026", "edition": "M|M15 Monastir|2025|w12", "uid": "1", "tour": "M", "level": "ITF",
         "draw": "main", "year": "2025", "d": "2025-03-17", "tname": "M15 Monastir", "name1": "Tommy Paul",
         "name2": "Reilly Opelka", "creator": "sackmann", "best": "stats", "sources": "sackmann"},
        {"gap": "itf_points_2025_2026", "edition": "W|W35 Reus|2025|w15", "uid": "2", "tour": "W", "level": "ITF",
         "draw": "main", "year": "2025", "d": "2025-04-07", "tname": "W35 Reus", "name1": "Ann Bee",
         "name2": "Cid Dee", "creator": "sackmann", "best": "stats", "sources": "sackmann"},
        {"gap": "itf_points_2025_2026", "edition": "W|W35 Reus|2025|w15", "uid": "3", "tour": "W", "level": "ITF",
         "draw": "main", "year": "2025", "d": "2025-04-07", "tname": "W35 Reus", "name1": "Nobody Here",
         "name2": "Someone Else", "creator": "sackmann", "best": "stats", "sources": "sackmann"}])
    monkeypatch.setattr(F, "load_targets", lambda gap, window: targets)
    client = FakeClient({F.FEED.format(id="AAA"): FEED_OK})   # BBB answers an empty feed
    monkeypatch.setattr(F, "make_client", lambda args: client)
    parser = argparse.ArgumentParser()
    F.add_arguments(parser)
    summary = F.run(parser.parse_args([]))
    # the record with a duration first (AAA, March), then the one without (BBB, April), though BBB is newer
    assert client.urls == [F.FEED.format(id="AAA"), F.FEED.format(id="BBB")]
    assert summary["all"] == {"targets": 3, "linked": 2, "points_any": 1, "points_complete": 1, "absent": 1,
                              "not_fetched": 0}
    assert summary["duration_proxy"]["duration=yes|record=yes"] == 1
    assert summary["duration_proxy"]["duration=no|record=no"] == 1
    table = pd.read_csv(F.table_path("itf_points_2025_2026", "matches"), dtype=str, keep_default_na=False)
    assert table.set_index("uid").loc["1", "fb_verdict"] == "complete" and table.set_index("uid").loc["2", "feed_status"] == "absent"
    pts = pd.read_parquet(P.dump_path(F.SOURCE, "points.parquet"))
    assert len(pts) == 24 and set(pts["fs_id"]) == {"AAA"}
    matches = pd.read_parquet(P.dump_path(F.SOURCE, "matches.parquet")).set_index("fs_id")
    assert matches.loc["AAA", "fb_verdict"] == "complete" and matches.loc["BBB", "feed_status"] == "absent"
    before = client.requests
    F.run(parser.parse_args([]))   # a rerun asks for nothing: the record and the absence are both on disk
    assert client.requests == before


def test_staging_describes_the_feeds_of_every_extract(folders):
    # P13's ITF extract, and P6's (flashscore_p6.py): men's ATP and Challenger records, graded by Flashscore's category
    itf = {"fs_id": "AAA", "fs_date": "20250318", "tour": "M", "grade": "M15", "fs_tournament": "M15 Monastir",
           "fs_home": "Paul T.", "fs_away": "Opelka R.", "fs_score": "2-1", "fs_status": "3", "fs_start_ts": "1",
           "fs_end_ts": "2", "fs_duration": "1:20", "handoff_file": "x"}
    p6 = [{**itf, "grade": "atp-singles", "fs_tournament": "Elsewhere"},          # an id in both: the ITF row is kept
          {**itf, "fs_id": "CCC", "fs_date": "20190109", "grade": "atp-singles", "fs_tournament": "Sydney",
           "fs_home": "De Minaur A.", "fs_away": "Opelka R.", "fs_status": None, "fs_start_ts": None,
           "fs_end_ts": None}]
    for name, rows in (("handoff_itf.parquet", [itf]), ("handoff_p6.parquet", p6)):
        P.stage_table(F.SOURCE, P.dump_path(F.SOURCE, name), F.HANDOFF_COLUMNS,
                      [[r[c] for c in F.HANDOFF_COLUMNS] for r in rows], source_file="x", retrieved_at=None)
    receipts = P.receipts_for(F.SOURCE)
    F.fetch_feeds(FakeClient({F.FEED.format(id="AAA"): FEED_OK, F.FEED.format(id="CCC"): FEED_OK}), receipts,
                  ["AAA", "CCC"])
    info = F.load_info()
    assert len(info) == 2 and info.set_index("fs_id").loc["AAA", "fs_tournament"] == "M15 Monastir"
    assert F.load_handoff()["fs_id"].tolist() == ["AAA"]      # linking still reads the ITF extract alone
    F.stage(receipts, info)
    m = pd.read_parquet(P.dump_path(F.SOURCE, "matches.parquet")).set_index("fs_id")
    assert (m.loc["CCC", "fs_date"], m.loc["CCC", "grade"], m.loc["CCC", "fs_home"]) == ("20190109", "atp-singles",
                                                                                         "De Minaur A.")
    assert m.loc["CCC", "fb_verdict"] == "complete" and m.loc["AAA", "grade"] == "M15"
