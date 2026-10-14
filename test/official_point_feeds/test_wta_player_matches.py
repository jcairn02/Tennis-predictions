"""The WTA adapter's --player-matches mode (work package P2(b) of docs/studies/gap_downloads/collection-plan.md), offline.

The fixture wta_player_matches_331077_cut.json holds seven rows of player 331077's 2026 answer (fetched 11 Oct 2026 with
pageSize=100), whole: a qualifying bye (San Gregorio), a retirement (Kursumlijska Banja 12), Leiria's two qualifying
wins and main-draw loss, and two doubles rows (Leiria, and a walkover at Sheffield).
"""
import csv
import datetime as dt
import gzip
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402
from src.ingest.point_sources import wta as W  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def answer() -> dict:
    return json.loads((FIXTURES / "wta_player_matches_331077_cut.json").read_text(encoding="utf-8"))


def served_rows(doc: dict, receipt: dict | None = None) -> list[dict]:
    receipt = receipt or {"dest": "x", "sha256": "s", "retrieved_at": "2026-10-11T15:00:00+00:00"}
    return [W.player_match_row(doc["player"], m, 0, i, receipt) for i, m in enumerate(doc["matches"])]


def other_side(doc: dict, index: int) -> dict:
    """The same match as the opponent's own answer would list it: sides swapped, the winner flag flipped."""
    m = json.loads(json.dumps(doc["matches"][index]))
    me = doc["player"]
    them = m["opponent"]
    for a, b in (("player_1", "player_2"), ("seed_1", "seed_2"), ("rank_1", "rank_2"), ("entry_type_1", "entry_type_2"),
                 ("points_1", "points_2")):
        m[a], m[b] = m[b], m[a]
    m["winner"] = 1 if m["winner"] == 2 else 2
    m["opponent"] = {k: me[k] for k in W.PERSON_KEYS} | {"metadata": None}
    return {"player": {k: them[k] for k in W.PERSON_KEYS} | {"metadata": None}, "matches": [m]}


class Answer:
    def __init__(self, status, body=b""):
        self.status_code, self.content = status, body
        self.headers, self.url = {"content-type": "application/json"}, "http://x"


class FakeAPI:
    """Answers /players/<id>/matches/ from a dict id -> list of rows, paged as the API pages them."""

    def __init__(self, players: dict[str, list[dict]]):
        self.players, self.urls = players, []

    def get(self, url, headers=None):
        self.urls.append(url)
        pid = url.split("/players/")[1].split("/")[0]
        query = dict(part.split("=") for part in url.split("?")[1].split("&"))
        if pid not in self.players:
            return Answer(404)
        page, size = int(query["page"]), int(query["pageSize"])
        rows = self.players[pid][page * size:(page + 1) * size]
        return Answer(200, json.dumps({"player": {"id": int(pid)}, "matches": rows}).encode())


def single(opp: str, start: str = "2026-09-14", s_d: str = "S") -> dict:
    return {"s_d_flag": s_d, "player_2": opp, "opponent": {"id": int(opp)}, "StartDate": f"{start}T00:00:00+00:00"}


# fetching and the crawl ----------------------------------------------------------------
def test_pages_are_read_until_one_comes_back_short_and_not_asked_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)
    api = FakeAPI({"7": [single(str(1000 + i)) for i in range(W.PLAYER_PAGE_SIZE + 3)]})
    matches, outcome, pages = W.fetch_player_pages(api, receipts, "7", 2026)
    assert (len(matches), outcome, pages) == (W.PLAYER_PAGE_SIZE + 3, "ok", 2)
    assert api.urls == [f"{W.API}/players/7/matches/?year=2026&page={n}&pageSize={W.PLAYER_PAGE_SIZE}" for n in (0, 1)]
    assert W.player_matches_dest("7", 2026, 1).name == "matches_2026_1.json.gz"
    again = W.fetch_player_pages(api, receipts, "7", 2026)  # both pages cached: no request
    assert len(again[0]) == W.PLAYER_PAGE_SIZE + 3 and len(api.urls) == 2
    W.fetch_player_pages(api, receipts, "7", 2026, refresh_before="2000-01-01")  # fetched after the cut: kept
    assert len(api.urls) == 2
    W.fetch_player_pages(api, receipts, "7", 2026, refresh_before="2999-01-01")  # fetched before it: asked again
    assert len(api.urls) == 4
    gone = W.fetch_player_pages(api, receipts, "8", 2026)
    assert gone == ([], "404", 0)


def test_a_refresh_can_be_kept_to_players_active_since_a_date(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)
    api = FakeAPI({"7": [single("8", start="2026-07-20")], "9": [single("8", start="2026-09-21")]})
    for pid in ("7", "9"):
        W.fetch_player_pages(api, receipts, pid, 2026)
    assert not W.active_since("7", 2026, "2026-08-01") and W.active_since("9", 2026, "2026-08-01")
    assert not W.active_since("5", 2026, "2026-08-01")  # nothing on disk
    for pid in ("7", "9"):
        W.fetch_player_pages(api, receipts, pid, 2026, refresh_before="2999-01-01", refresh_active_since="2026-08-01")
    assert [u.split("/players/")[1].split("/")[0] for u in api.urls] == ["7", "9", "9"]  # idle since July: kept


def test_a_weekly_refresh_reaches_idle_players_in_rotation(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)
    idle = {str(pid): [single("8", start="2026-07-20")] for pid in range(100, 112)}
    api = FakeAPI(idle)
    for pid in idle:
        W.fetch_player_pages(api, receipts, pid, 2026)
    before = "2026-10-20T10:00:00+00:00"                   # ISO week 43
    due = [pid for pid in idle if W.refresh_due(pid, 2026, before, "2026-09-01", rotation=6)]
    assert due == [pid for pid in idle if (int(pid) + 43) % 6 == 0] and len(due) == 2
    assert not any(W.refresh_due(pid, 2026, before, "2026-09-01") for pid in idle)   # no rotation: idle ones wait
    assert all(W.refresh_due(pid, 2026, before, None) for pid in idle)               # no activity test: everyone
    assert not W.refresh_due("100", 2026, None, "2026-09-01", rotation=6)            # no refresh at all
    calls = len(api.urls)
    for pid in idle:
        W.fetch_player_pages(api, receipts, pid, 2026, refresh_before="2999-01-01T00:00:00",
                             refresh_active_since="2026-09-01", refresh_rotation=6)
    week = dt.date(2999, 1, 1).isocalendar()[1]
    assert len(api.urls) - calls == sum((int(pid) + week) % 6 == 0 for pid in idle)


def test_a_new_year_starts_from_the_previous_years_players(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "PLAYER_STUDY", tmp_path / "study")
    monkeypatch.setattr(W, "KAGGLE", tmp_path / "kaggle")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    (tmp_path / "kaggle").mkdir()
    pd.DataFrame({"pseudo_tournament_id": [1], "year": [2026], "startDate": ["2026-03-02"], "level": ["ITF"]}
                 ).to_csv(tmp_path / "kaggle" / "tournaments.csv", index=False)
    pd.DataFrame({"pseudo_tournament_id": [1], "player_1": [331077]}).to_csv(tmp_path / "kaggle" / "matches.csv",
                                                                          index=False)
    results = tmp_path / "dump" / "wta" / "player_results"
    results.mkdir(parents=True)
    pd.DataFrame({"level": ["ITF", "ITF", "WTA 250"], "winner_id": ["332174", "331077", "999"],
                  "loser_id": ["331077", None, "998"]}).to_parquet(results / "2026.parquet", index=False)
    seeds, info = W.frozen_seeds(2027)                    # the copy has no 2027 row: 2026's ITF players
    assert seeds == ["331077", "332174"] and info["seeded_from"].endswith("player_results/2026.parquet")
    assert W.frozen_seeds(2027)[0] == seeds                # frozen
    assert W.frozen_seeds(2026)[0] == ["331077"]          # a year the copy reaches: its players, as before


def test_the_evidence_names_the_newest_itf_edition(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "PLAYER_STUDY", tmp_path)
    results = [{"level": "ITF", "start_date": d, "qpm_flag": "M", "rows": 2, "winners_agree": True,
                "winner_id": "1", "loser_id": "2"} for d in ("2026-09-14", "2026-10-05", "")]
    results.append({**results[0], "level": "WTA 1000", "start_date": "2026-10-12"})
    ev = W.player_evidence(2026, {}, results, "2026-09-07")
    assert ev["itf_last_start"] == "2026-10-05" and ev["itf_after_last_start"] == "2026-10-05"


def test_the_crawl_adds_singles_opponents_wave_by_wave_until_none_is_new(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)
    api = FakeAPI({"10": [single("20"), single("30"), single("90", s_d="D")],   # 90: a doubles opponent only
                   "20": [single("10"), single("40")], "30": [single("10")], "40": [single("20"), single("50")],
                   "90": [single("91")]})                                       # 50 is unknown to the API
    asked = W.crawl_players(api, receipts, ["10"], 2026)
    assert {p: a["wave"] for p, a in asked.items()} == {"10": 0, "20": 1, "30": 1, "40": 2, "50": 3}
    assert asked["50"]["outcome"] == "404" and asked["10"]["new_opponents"] == 2 and asked["10"]["singles"] == 2
    assert "90" not in asked  # doubles rows add nobody
    calls = len(api.urls)
    assert W.crawl_players(api, receipts, ["10"], 2026) == asked and len(api.urls) == calls  # replayed from the cache
    assert list(W.crawl_players(api, receipts, ["10"], 2026, limit=2)) == ["10", "20"]


def test_an_unknown_player_is_an_empty_answer_recorded_once_and_byes_are_never_crawled(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)

    class EmptyFor(FakeAPI):  # the API answers an unknown id with HTTP 200 and an empty body (player 2, 11 Oct 2026)
        def get(self, url, headers=None):
            if "/players/2/" in url:
                self.urls.append(url)
                return Answer(200, b"")
            return super().get(url, headers)

    bye = {"s_d_flag": "S", "reason_code": "B", "player_2": "1", "opponent": {"id": 1}, "StartDate": "2026-03-16"}
    api = EmptyFor({"10": [single("2"), bye]})
    assert W.opponent_id(bye) is None and W.opponent_id({"player_2": "BYE"}) is None
    asked = W.crawl_players(api, receipts, ["10"], 2026)
    assert asked["2"]["outcome"] == "absent" and "1" not in asked
    assert receipts.get("players/2/2026/matches/0")["absent"] == "empty answer: no such player"
    calls = len(api.urls)
    W.crawl_players(api, receipts, ["10"], 2026)
    assert len(api.urls) == calls  # the absent answer is final, like a 404


def test_a_zero_budget_replays_the_cache_and_stops_at_the_first_new_page(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)
    api = FakeAPI({"10": [single("20")], "20": [single("10")]})
    W.fetch_player_pages(api, receipts, "10", 2026)
    offline = W.make_client(0, 0, 0)
    with pytest.raises(P.BudgetExhausted):  # 10 is cached; 20 would need a request
        W.crawl_players(offline, receipts, ["10"], 2026)


def test_seeds_are_the_players_the_kaggle_copy_lists_at_that_years_itf_events(tmp_path):
    pd.DataFrame({"pseudo_tournament_id": [1, 2, 3, 4], "year": [2026, 2026, 2025, 2025],
                  "startDate": ["2026-03-02", "2026-03-02", "2025-12-29", "2026-01-05"],
                  "level": ["ITF", "WTA 250", "ITF", "ITF"]}).to_csv(tmp_path / "tournaments.csv", index=False)
    # perspective_player_id is the copy's own label (small numbers on most 2026 ITF rows), not a WTA id: unused
    pd.DataFrame({"pseudo_tournament_id": [1, 1, 2, 3, 4, 1], "perspective_player_id": [150, 150, 23, 8, 9, 150],
                  "player_1": [331077, 332174, 324673, 327137, 330000, 1]}
                 ).to_csv(tmp_path / "matches.csv", index=False)
    assert W.kaggle_seed_players(2026, tmp_path) == ["330000", "331077", "332174"]  # 330000: a 2025 edition
    #                                                    starting in 2026; 1 is the API's bye placeholder


def test_the_newest_kaggle_copy_is_read_and_versions_never_overwrite_each_other(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "KAGGLE", tmp_path)
    assert W.kaggle_folder() == tmp_path
    for v in ("v30", "v31", "vX"):
        (tmp_path / v).mkdir()
    (tmp_path / "v30" / "matches.csv").write_text("x", encoding="utf-8")
    assert W.kaggle_folder() == tmp_path / "v30"  # v31 holds no matches.csv yet
    sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "gap_sources"))
    import wta_site_kaggle as K
    monkeypatch.setattr(K, "RAW", tmp_path)
    assert K.version_dir(29, None) == tmp_path and K.version_dir(29, 29) == tmp_path
    assert K.version_dir(30, 29) == tmp_path / "v30"
    assert K.newest_dir() == tmp_path / "v30"


# staging ---------------------------------------------------------------------------------
def test_a_served_row_is_flattened_with_the_asked_player_and_the_opponent():
    rows = served_rows(answer())
    leiria = rows[3]  # main draw R32, lost to Kinoshita
    assert (leiria["asked_id"], leiria["asked_lastName"], leiria["opponent_id"], leiria["opponent_lastName"]) == \
           (331077, "Mortensen", 332174, "Kinoshita")
    assert (leiria["tournament_title"], leiria["tournament_group_id"], leiria["tourn_nbr"], leiria["tournament_start"],
            leiria["tournament_end"]) == ("WTT W50 - LEIRIA, PORTUGAL", 4826, "4826", "2026-08-31", "2026-09-06")
    assert leiria["page_file"] == "x" and leiria["page_sha256"] == "s" and leiria["other"] is None
    a, b = W.row_sides(leiria)
    assert (a["id"], b["id"], b["name"]) == ("331077", "332174", "Hayu Kinoshita")
    assert str(leiria["winner"]) == "2" and leiria["scores"] == "6-0  7-5"


def test_the_edition_is_keyed_by_the_tournament_objects_group_id():
    # tourn_nbr is fixed-width: ' 901' for group 901 (the Australian Open); 100 of 541 editions of 2026 (11 Oct)
    assert W.group_id({"tourn_nbr": " 901", "tournament_group_id": 901}) == "901"
    assert W.group_id({"tourn_nbr": " 609"}) == "609" and W.group_id({}) == ""
    rows = served_rows(answer())
    padded = [{**r, "tourn_nbr": f" {r['tourn_nbr']}"} for r in rows]  # as a three-digit group would come
    results, plain = W.player_results(padded), W.player_results(rows)
    assert [r["tournament_group_id"] for r in results] == [r["tournament_group_id"] for r in plain]
    assert [r["match_key"] for r in results] == [r["match_key"] for r in plain]
    assert all(r["tournament_group_id"] == str(int(r["tournament_group_id"])) for r in results)


def test_names_come_from_the_draw_sheet_when_the_opponent_object_is_missing():
    row = served_rows(answer())[2]  # Leiria qualifying R32 v Walker
    row = {**row, "opponent_id": None, "opponent_firstName": None, "opponent_lastName": None, "player_2": ""}
    a, b = W.row_sides(row)
    assert b["id"] is None and (b["last"], b["first"]) == ("WALKER", "BRANDY")
    assert W.name_key("Cortez Llorca") == W.name_key("CORTEZ LLORCA,") == "cortezllorca"
    assert W.team_parts("CORTEZ LLORCA,  LUCIA  ESP") == ("CORTEZ LLORCA", "LUCIA")


def test_results_keep_each_played_single_once():
    doc = answer()
    rows = served_rows(doc)
    rows += served_rows(other_side(doc, 3))                      # Kinoshita's own row of the Leiria R32
    orphan = served_rows(other_side(doc, 2))[0]                  # Walker's row of the qualifying R32, without the
    orphan.update(opponent_id=None, opponent_firstName=None, opponent_lastName=None, player_2="")  # opponent's id
    walkover = {**rows[2], "reason_code": "D", "scores": ""}
    results = W.player_results(rows + [orphan, walkover])
    by_round ={(r["start_date"], r["qpm_flag"], r["round_name"]): r for r in results}
    assert set(by_round) == {("2026-07-27", "M", "R32"), ("2026-08-31", "Q", "R32"), ("2026-08-31", "Q", "R16"),
                             ("2026-08-31", "M", "R32")}  # the bye, the doubles rows and the walkover are left out
    main = by_round[("2026-08-31", "M", "R32")]
    assert (main["winner_id"], main["loser_id"], main["rows"], main["listed_by"], main["winners_agree"]) == \
           ("332174", "331077", 2, "331077;332174", True)
    assert (main["winner_name"], main["loser_name"], main["scores"]) == ("Hayu Kinoshita", "Rebecca Munk Mortensen",
                                                                         "6-0  7-5")
    qual = by_round[("2026-08-31", "Q", "R32")]
    assert (qual["winner_id"], qual["loser_id"], qual["rows"]) == ("331077", "331255", 2)  # the orphan joined by name
    retired = by_round[("2026-07-27", "M", "R32")]
    assert (retired["reason_code"], retired["winner_id"], retired["scores"]) == ("R", "331077", "6-0")
    assert all(r["level"] == "ITF" for r in results)


def test_staging_writes_every_served_row_and_one_row_per_played_match(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(P, "PROJECT_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path / "raw")
    pages = {"331077": answer(), "332174": other_side(answer(), 3)}
    api = FakeAPI({pid: doc["matches"] for pid, doc in pages.items()})
    for pid in pages:
        W.fetch_player_pages(api, receipts, pid, 2026)
    for pid, doc in pages.items():  # the fake API sends a bare player object: put the real one back
        dest = W.player_matches_dest(pid, 2026, 0)
        dest.write_bytes(gzip.compress(json.dumps(doc).encode()))
    (tmp_path / "raw" / "wta" / "players" / "331077" / "matches_2026.json.gz").write_bytes(b"trial, unpaged")
    receipts.record({"name": "players/331077/2026/matches", "status": 200, "dest": "raw/wta/players/331077/"
                     "matches_2026.json.gz"})  # a trial answer at the unpaged path is never staged
    staged, results = W.stage_player_matches(2026, receipts)
    every = pd.read_parquet(tmp_path / "dump" / "wta" / "player_matches" / "2026.parquet")
    played = pd.read_parquet(tmp_path / "dump" / "wta" / "player_results" / "2026.parquet")
    assert len(every) == 8 and staged["player_matches"]["rows"] == 8
    assert len(played) == len(results) == 4 and set(every["asked_id"]) == {"331077", "332174"}
    import pyarrow.parquet as pq
    for table in ("player_matches", "player_results"):
        schema = pq.read_schema(tmp_path / "dump" / "wta" / table / "2026.parquet")
        assert {str(f.type) for f in schema if f.name != "_row"} == {"string"}  # every column a string
        assert len(schema.names) == len(set(schema.names))  # no name twice (the reader refuses that)


def test_a_player_run_needs_a_budget(monkeypatch):
    parser = __import__("argparse").ArgumentParser()
    W.add_arguments(parser)
    with pytest.raises(SystemExit):
        W.run(parser.parse_args(["--player-matches", "--players", "1"]))
    args = parser.parse_args(["--player-matches", "--max-requests", "5"])
    assert args.player_since == "2026-09-07" and args.refresh_before is None and not args.refresh_seeds
    assert W.is_played_single({"s_d_flag": "S", "reason_code": "W", "winner": 1, "player_2": "5"})
    for bad in ({"reason_code": "B"}, {"reason_code": "D"}, {"reason_code": "UNP"}, {"reason_code": "V"},
                {"winner": None}, {"s_d_flag": "D"}, {"player_2": "BYE"}):
        assert not W.is_played_single({"s_d_flag": "S", "reason_code": "W", "winner": 1, "player_2": "5", **bad})
    assert F.FailureStreak(0).limit == 0
