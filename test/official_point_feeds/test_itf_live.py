"""The ITF live-data API collector: day-list selection, the documents rule, parsing and staging (offline).

Fixtures are cut from answers the collector saved on 8 Oct 2026 (the matches kept whole, the rest left out):
    itf_live_days_cut.json    {list date: a day-list answer cut to a few matches}:
                              2026-09-28  W15 Trelew qualifying: one complete, one stuck at "Scoring Stopped"
                              2026-10-04  W15 Maanshan's final ("COMPLETE"; W-ITF-CHN-2026-034), a qualifying match
                                          of the next week's W15 Maanshan (W-ITF-CHN-2026-035) with no status but a
                                          winner, and W35 Reims's final, a walkover
                              2026-10-08  W35 Las Vegas: a singles match in progress and a doubles match scheduled
    itf_live_stats_cut.json   widgetMatchStats of 6974ac2e (M25 Darwin, first round, 29 Sep 2026: Ethan Cook v Herman
                              Hoeyeraal) cut to six items: Aces for the match and set 1, Double Faults for the match,
                              both sides
    itf_live_points_cut.json  pointByPoint of the same match cut to set 1's first game and its tiebreak (game 13),
                              and set 2's first game
"""
import copy
import datetime as dt
import gzip
import json
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import itf_live as L  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
DAYS = json.loads((FIXTURES / "itf_live_days_cut.json").read_text(encoding="utf-8"))
STATS = json.loads((FIXTURES / "itf_live_stats_cut.json").read_text(encoding="utf-8"))
POINTS = json.loads((FIXTURES / "itf_live_points_cut.json").read_text(encoding="utf-8"))
STATS_ID = "6974ac2e-2d30-4185-8fa0-403f21445b60"
EMPTY_STATS = (b'{"data":[],"meta":{"datasource":"merged","filter":{"matchId":"x"},"include":"statType,side.sidePlayer'
               b'.player.person.images,side.sidePlayer.player.person.country.images,match"}}')
EMPTY_POINTS = b'{"$schema":"https://api.itf-production.sports-data.stadion.io/PointByPointBody.json","data":[]}'
MAANSHAN_FINAL = "e2e19e27-f31d-4602-b819-ac61c3aa2eb4"
MAANSHAN_NO_STATUS = "249db47a-4410-4d8c-9065-17c60707e763"
REIMS_WALKOVER = "08b3283b-8bc9-44dd-9cd2-c0192629462c"
TRELEW_COMPLETE = "1fe902a9-3c0f-41c0-8837-b261adeb81b7"
TRELEW_STOPPED = "27e2fc81-55cf-4b38-ba02-c219f5375897"
VEGAS_LIVE = "d4465447-b2c3-467f-9856-351cfd99e35e"
VEGAS_DOUBLES = "f171e965-9de7-448d-8def-8de42060e9c7"
NOW = dt.datetime(2026, 10, 8, 19, 30, tzinfo=dt.timezone.utc)
TODAY = NOW.date()


def match(match_id: str) -> dict:
    for doc in DAYS.values():
        for _, _, _, m in L.listed(doc):
            if m["id"] == match_id:
                return m
    raise KeyError(match_id)


def state_of(match_id: str, list_date: str) -> dict:
    return {"list_date": list_date, "stamp": "20261008T191636Z", "event_key": "k", "event": {}, "court": "c",
            "match": match(match_id)}


# --------------------------------------------------------------------------------------------- names and window
def test_window_is_the_fifteen_days_the_api_serves_oldest_first():
    days = L.window(TODAY)
    assert days[0] == "2026-09-24" and days[-1] == "2026-10-08" and len(days) == 15


def test_day_names_round_trip_and_other_names_are_not_days():
    name = L.day_name("2026-10-05", "20261008T191636Z")
    assert name == "day/2026-10-05@20261008T191636Z"
    assert L.parse_day_name(name) == ("2026-10-05", "20261008T191636Z")
    assert L.parse_day_name("match/abc/stats") is None
    assert L.day_dest("2026-10-05", "20261008T191636Z").name == "2026-10-05@20261008T191636Z.json.gz"
    assert L.doc_dest("abc", "stats").as_posix().endswith("itf_live/match/abc/stats.json.gz")


def test_a_422_is_recorded_as_outside_the_window():
    refused = types.SimpleNamespace(status_code=422, content=b'{"message":"date must be within 14 days of today"}')
    assert L.outside_window(refused).startswith("HTTP 422: ")
    assert L.outside_window(types.SimpleNamespace(status_code=200, content=b"{}")) is None


# --------------------------------------------------------------------------------------------- statuses
def test_statuses_read_from_the_lists():
    assert L.status_of(match(MAANSHAN_FINAL)) == ("complete", "post")      # served as "COMPLETE"
    assert L.is_over(match(MAANSHAN_FINAL)) and not L.is_walkover(match(MAANSHAN_FINAL))
    assert L.is_over(match(REIMS_WALKOVER)) and L.is_walkover(match(REIMS_WALKOVER))
    assert L.status_of(match(MAANSHAN_NO_STATUS)) == ("", "")              # matchStatus null, yet a winner
    assert not L.is_over(match(TRELEW_STOPPED)) and not L.is_over(match(VEGAS_LIVE))
    assert L.is_singles(match(VEGAS_LIVE)) and not L.is_singles(match(VEGAS_DOUBLES))


def test_all_over_needs_every_match_over():
    assert not L.all_over(DAYS["2026-10-04"])                               # the no-status match
    assert not L.all_over(DAYS["2026-10-08"])
    finished = copy.deepcopy(DAYS["2026-10-04"])
    for event in finished["data"].values():
        for court in event["courts"]:
            event["courts"][court] = [m for m in event["courts"][court] if m["id"] != MAANSHAN_NO_STATUS]
    assert L.all_over(finished)
    assert L.all_over({"data": {}})


# --------------------------------------------------------------------------------------------- which days to ask
def test_plan_day():
    cap = {"stamp": "20261008T120000Z"}
    over = {"data": {}}
    assert L.plan_day("2026-10-04", TODAY, None, None, NOW) == "fetch"
    assert L.plan_day("2026-09-24", TODAY, None, None, NOW, refused=True) == "refused"
    # three days old and every match over: settled, whenever it was captured
    assert L.plan_day("2026-10-05", TODAY, cap, over, NOW) == "settled"
    # two days old: asked again once the capture is six hours old
    assert L.plan_day("2026-10-06", TODAY, cap, over, NOW) == "fetch"
    assert L.plan_day("2026-10-06", TODAY, {"stamp": "20261008T170000Z"}, over, NOW) == "fresh"
    # old, but a match is not over: asked again (until it leaves the window)
    assert L.plan_day("2026-10-04", TODAY, cap, DAYS["2026-10-04"], NOW) == "fetch"


# --------------------------------------------------------------------------------------------- which documents
def test_doc_reason():
    # over, ended 4 Oct 05:13 UTC
    assert L.doc_reason(state_of(MAANSHAN_FINAL, "2026-10-04"), TODAY, NOW) == "over"
    just_ended = dt.datetime(2026, 10, 4, 6, 0, tzinfo=dt.timezone.utc)
    assert L.doc_reason(state_of(MAANSHAN_FINAL, "2026-10-04"), dt.date(2026, 10, 4), just_ended) is None
    # walkovers and doubles never; matches still live only once their day is three days old
    assert L.doc_reason(state_of(REIMS_WALKOVER, "2026-10-04"), TODAY, NOW) is None
    doubles = copy.deepcopy(state_of(VEGAS_DOUBLES, "2026-10-04"))
    doubles["match"]["matchStatus"] = copy.deepcopy(match(MAANSHAN_FINAL)["matchStatus"])
    assert L.is_over(doubles["match"]) and L.doc_reason(doubles, TODAY, NOW) is None
    assert L.doc_reason(state_of(TRELEW_STOPPED, "2026-09-28"), TODAY, NOW) == "stale"
    assert L.doc_reason(state_of(TRELEW_STOPPED, "2026-10-07"), TODAY, NOW) is None
    assert L.doc_reason(state_of(MAANSHAN_NO_STATUS, "2026-10-04"), TODAY, NOW) == "stale"
    assert L.doc_reason(state_of(VEGAS_LIVE, "2026-10-08"), TODAY, NOW) is None
    # over without an end time: from the day after its list day
    no_end = copy.deepcopy(state_of(TRELEW_COMPLETE, "2026-10-08"))
    no_end["match"]["actualEndDate"] = None
    assert L.doc_reason(no_end, TODAY, NOW) is None
    no_end["list_date"] = "2026-10-07"
    assert L.doc_reason(no_end, TODAY, NOW) == "over"


def test_latest_state_keeps_the_latest_day_then_capture():
    m = match(TRELEW_COMPLETE)
    early, late = copy.deepcopy(m), copy.deepcopy(m)
    early["matchStatus"] = None

    def doc(x):
        return {"data": {"ev": {"_name": "W15 Trelew", "courts": {"Court 2": [x]}}}}

    captures = {"2026-09-27": [{"day": "2026-09-27", "stamp": "20261008T191636Z", "doc": doc(early)}],
                "2026-09-28": [{"day": "2026-09-28", "stamp": "20261008T191636Z", "doc": doc(early)},
                               {"day": "2026-09-28", "stamp": "20261009T143000Z", "doc": doc(late)}]}
    state = L.latest_state(captures, lambda r: r["doc"])
    assert state[TRELEW_COMPLETE]["list_date"] == "2026-09-28"
    assert state[TRELEW_COMPLETE]["stamp"] == "20261009T143000Z"
    assert L.is_over(state[TRELEW_COMPLETE]["match"])


def test_wanted_selects_and_orders_with_reasons():
    caps = {day: [{"day": day, "stamp": "20261008T191636Z"}] for day in DAYS}
    state = L.latest_state(caps, lambda r: DAYS[r["day"]])
    rows = L.wanted(state, TODAY, NOW)
    assert [(r["match"]["id"], r["reason"]) for r in rows] == [
        (TRELEW_COMPLETE, "over"), (TRELEW_STOPPED, "stale"),         # 28 Sep, both Qualifying Draw R16
        (MAANSHAN_FINAL, "over"), (MAANSHAN_NO_STATUS, "stale")]      # 4 Oct: Main Draw before Qualifying Draw
    # the no-status qualifying match is the next week's W15 Maanshan (same name, its own ITF key)
    assert L.event_order(rows) == ["W-ITF-ARG-2026-010", "W-ITF-CHN-2026-034", "W-ITF-CHN-2026-035"]


# --------------------------------------------------------------------------------------------- records
def test_match_record_flattens_sides_times_and_winner():
    rec = L.match_record(match(MAANSHAN_FINAL))
    assert rec["match_id"] == MAANSHAN_FINAL and rec["draw"] == "Main Draw" and rec["round"] == "Final"
    assert rec["status"] == "COMPLETE" and rec["status_state_type"] == "post"
    assert rec["actual_end_date"] == "2026-10-04T05:13:17Z" and rec["date_start_local"] == "2026-10-04"
    assert rec["sides"] == 2 and rec["winner_side_order"] in (1, 2)
    assert rec[f"side{rec['winner_side_order']}_id"] == rec["winner_side_id"]
    for n in (1, 2):
        assert rec[f"side{n}_players"] and ";" not in rec[f"side{n}_players"]          # singles: one player a side
        assert rec[f"side{n}_sets"].startswith("1:")
        assert rec[f"side{n}_headshot_codes"] is None or rec[f"side{n}_headshot_codes"].isalnum()
    assert rec["extra"] is None


def test_sets_text_and_headshot_code():
    sets = [{"setNumber": 2, "setScore": 7, "setTieBreakScore": 5}, {"setNumber": 1, "setScore": 6, "setTieBreakScore": 0}]
    assert L.sets_text(sets) == "1:6/0 2:7/5"
    assert L.sets_text([]) is None
    person = {"images": [{"description": "flagRound", "url": "x/FRA"},
                         {"description": "headshot", "url": "https://assetbank.itf-production.sports-data.stadion.io/POD1488593"}]}
    assert L.headshot_code(person) == "POD1488593"
    assert L.headshot_code({}) is None


def test_stat_rows_periods_sides_and_values():
    rows = L.stat_rows(STATS, STATS_ID)
    assert len(rows) == 6
    got = {(r["stat"], r["period"], r["side_order"]): r["value"] for r in rows}
    assert got[("Aces", "match", 2)] == 12 and got[("Aces", "match", 1)] == 6
    assert got[("Double Faults", "match", 1)] == 5 and got[("Double Faults", "match", 2)] == 10
    assert got[("Aces", "set 1", 1)] == 1 and got[("Aces", "set 1", 2)] == 7
    assert all(r["match_id"] == STATS_ID and r["stat_source_name"] for r in rows)
    assert L.stat_rows(json.loads(EMPTY_STATS), "x") == []


def test_stats_answer_carries_the_actual_start():
    f = L.stats_match_fields(STATS)
    assert f["actual_start_date"] == "2026-09-29T09:33:15Z" and f["actual_end_date"]
    assert L.stats_match_fields(json.loads(EMPTY_STATS)) == {}


def test_point_rows_put_the_two_views_side_by_side():
    rows = L.point_rows(POINTS, STATS_ID)
    assert len(rows) == 6 + 10 + 4 == sum(1 for _ in rows)
    assert all(r["consistent"] for r in rows)
    first_game = [r for r in rows if r["set_number"] == 1 and r["game_number"] == 1]
    assert {r["server_side_order"] for r in first_game} == {1}           # side 1 serves the first game
    tiebreak = [r for r in rows if r["game_number"] == 13]
    assert len(tiebreak) == 10 and {r["server_side_order"] for r in tiebreak} == {1, 2}
    assert tiebreak[-1]["winner_side_order"] == 1                         # "7 - 6 won by E Cook" (side 1)
    assert [r["point_index"] for r in tiebreak] == list(range(1, 11))
    assert L.point_counts(POINTS) == (2, 3, 20)
    assert L.point_rows(json.loads(EMPTY_POINTS), "x") == [] and L.point_counts(json.loads(EMPTY_POINTS)) == (0, 0, 0)


def test_point_rows_flag_views_that_disagree():
    doc = copy.deepcopy(POINTS)
    doc["data"][0]["games"][0]["sides"][1]["points"][0]["pointWon"] = not doc["data"][0]["games"][0]["sides"][1]["points"][0]["pointWon"]
    rows = L.point_rows(doc, STATS_ID)
    assert not rows[0]["consistent"] and rows[0]["winner_side_order"] is None
    assert all(r["consistent"] for r in rows[1:])


def test_event_tour_and_main_draw_week():
    assert L.event_tour({"tennisId": "W-ITF-CHN-2026-034"}, []) == "W"
    assert L.event_tour({"_name": "M25 Darwin"}, []) == "M"
    assert L.event_tour({"_name": "Davis Cup"}, ["men", "men", "women"]) == "M"
    assert L.main_draw_week("2026-09-27T00:00:00Z") == "2026-W40"       # Sunday qualifying, main draw week 40
    assert L.main_draw_week("2026-09-28T00:00:00Z") == "2026-W40"       # a Monday start (US events)
    assert L.main_draw_week(None) is None


# --------------------------------------------------------------------------------------------- the daily job
def test_daily_job_alerts_on_two_failures_and_pauses_on_a_block(tmp_path, monkeypatch):
    from src.ingest import scheduled as S

    monkeypatch.setattr(S, "ITF_SUMMARY", tmp_path / "itf_live_summary.json")
    codes, calls, timeouts = iter([0, 1, 3, 1, 2, 0, 0]), [], []

    def child(name, argv, timeout):
        calls.append(argv)
        timeouts.append(timeout)
        return {"exit": next(codes), "seconds": 1.0, "log": "data/raw/_scheduled/logs/2026-10-09_itf.log"}

    monkeypatch.setattr(S, "child", child)
    state = {}
    assert S.job_itf(state, asked=False)[1] == [] and state["itf_failed"] is False      # exit 0
    assert S.job_itf(state, asked=False)[1] == [] and state["itf_failed"] is True       # one failure: no alert
    assert S.job_itf(state, asked=False)[1] == [] and state["itf_failed"] is True       # exit 3: another run, a skip
    assert "two runs in a row" in S.job_itf(state, asked=False)[1][0]                    # the second failure
    assert "refused the collector" in S.job_itf(state, asked=False)[1][0]                # exit 2: a block
    assert "itf_blocked" in state and len(calls) == 5
    out, alerts = S.job_itf(state, asked=False)                                          # paused: nothing asked
    assert out["skipped"].startswith("paused") and alerts == [] and len(calls) == 5
    state["itf_blocked"]["at"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=4)).isoformat(timespec="seconds")
    assert "still paused" in S.job_itf(state, asked=False)[1][0] and len(calls) == 5     # a reminder every 3 days
    assert S.job_itf(state, asked=False)[1] == []                                        # not again the same day
    assert S.job_itf(state, asked=True)[1] == [] and "itf_blocked" not in state          # asked by name: tried, lifted
    assert calls[-1][:2] == ["-m", "src.ingest.point_sources.itf_live"] and "--max-requests" in calls[-1]
    monday = dt.date.today().weekday() == 0
    assert "--no-stage" not in calls[-1]                                                 # tables rebuilt every run
    assert timeouts[-1] == S.ITF_TIMEOUT                                                 # a full task: 80 minutes
    # later in the task: the run stops in time for the jobs after it, and does not start with under 3 minutes
    S.job_itf(state, asked=False, left=60 * 60)
    assert timeouts[-1] == 60 * 60 - S.ITF_SPARE - (S.ITF_MONDAY_AFTER if monday else 0)
    out, alerts = S.job_itf(state, asked=False, left=S.ITF_SPARE + 60 + (S.ITF_MONDAY_AFTER if monday else 0))
    assert out["skipped"].endswith("of the task's time left") and alerts == [] and state["itf_failed"] is True
    assert "too little time two runs in a row" in S.job_itf(state, asked=False, left=0)[1][0]
    assert len(calls) == 7


# --------------------------------------------------------------------------------------------- fetching and staging
class FakeResponse:
    def __init__(self, status, body, url):
        self.status_code, self.content, self.url = status, body, url
        self.headers = {"content-type": "application/json"}


class FakeSession:
    """The API as the fixtures show it: 24 Sep refused (422), the three cut days served, other days empty."""

    def __init__(self):
        self.calls = []

    def get(self, url, timeout=None, headers=None):
        self.calls.append(url)
        tail = url.split("/custom/", 1)[1]
        kind, key = tail.split("/", 1)
        if kind == "wttCompleteMatchList":
            if key == "2026-09-24":
                return FakeResponse(422, b'{"message":"date must be within 14 days of today"}', url)
            return FakeResponse(200, json.dumps(DAYS.get(key, {"data": {}})).encode(), url)
        if kind == "widgetMatchStats":
            return FakeResponse(200, json.dumps(STATS).encode() if key == MAANSHAN_FINAL else EMPTY_STATS, url)
        return FakeResponse(200, json.dumps(POINTS).encode() if key == MAANSHAN_FINAL else EMPTY_POINTS, url)


@pytest.fixture
def roots(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    return tmp_path


def args(**kw):
    base = dict(no_days=False, days_only=False, refetch_hours=6.0, settle_hours=2.0, ids=None, events=None,
                limit=None, min_interval=0.0, jitter=0.0, max_requests=100)
    return types.SimpleNamespace(**{**base, **kw})


def run(session, stamp):
    receipts = P.receipts_for(L.SOURCE)
    client = P.Client("chrome", session=session, min_interval=0, jitter=0, max_requests=100)
    return L.run_fetch(args(), receipts, stamp, client=client)


def test_a_run_asks_each_day_once_and_each_document_once(roots):
    session = FakeSession()
    first = run(session, "20261008T193000Z")
    days = [c for c in session.calls if "wttCompleteMatchList" in c]
    docs = [c for c in session.calls if "wttCompleteMatchList" not in c]
    assert len(days) == 15 and first["outcomes"]["day:absent"] == 1 and first["outcomes"]["day:200"] == 14
    # the documents: the Maanshan final and Trelew's complete match (over), Trelew's stuck match and the
    # no-status Maanshan match (stale); not the walkover, the doubles or the match in progress
    asked = sorted({c.rsplit("/", 1)[1] for c in docs})
    assert asked == sorted([MAANSHAN_FINAL, MAANSHAN_NO_STATUS, TRELEW_COMPLETE, TRELEW_STOPPED])
    assert len(docs) == 8 and first["stopped"] is None
    saved = L.doc_dest(MAANSHAN_FINAL, "stats")
    assert json.loads(gzip.decompress(saved.read_bytes())) == STATS                 # kept as served, gzipped
    # an hour later: every day is settled, fresh or refused, and every document held
    again = FakeSession()
    second = run(again, "20261008T203000Z")
    assert again.calls == [] and second["outcomes"].get("day:refused") == 1


def test_five_fetches_in_a_row_without_a_document_stop_the_run(roots):
    class Broken(FakeSession):
        def get(self, url, timeout=None, headers=None):
            self.calls.append(url)
            return FakeResponse(200, b"<html>maintenance</html>", url)

    session = Broken()
    result = run(session, "20261008T193000Z")
    assert len(session.calls) == 5 and result["outcomes"] == {"day:error": 5}
    assert result["stopped"].startswith("failures: 5 fetches in a row failed")


def test_the_research_answers_are_copied_in_once_with_their_receipts(roots, monkeypatch):
    research = roots / "research"
    folder = research / "other" / L.RESEARCH_HOST
    (folder / "widgetMatchStats").mkdir(parents=True)
    day_body = json.dumps(DAYS["2026-09-28"]).encode()
    (folder / "wttCompleteMatchList_2026-09-28.json").write_bytes(day_body)
    (folder / "widgetMatchStats" / f"{STATS_ID}.json").write_bytes(EMPTY_STATS)
    (folder / "wttCompleteMatchList_2026-09-14.json").write_bytes(b'{"title":"date must be within 14 days"}')
    lines = [
        {"name": "wttCompleteMatchList_2026-09-28.json", "host": L.RESEARCH_HOST, "status": 200,
         "retrieved_at": "2026-09-29T17:36:25Z", "url": L.day_url("2026-09-28"), "sha256": P.sha256_bytes(day_body)},
        {"name": f"widgetMatchStats/{STATS_ID}.json", "host": L.RESEARCH_HOST, "status": 200,
         "retrieved_at": "2026-09-29T18:01:00Z", "url": L.doc_url("stats", STATS_ID), "sha256": "not the file's"},
        {"name": "wttCompleteMatchList_2026-09-14.json", "host": L.RESEARCH_HOST, "status": 422,
         "retrieved_at": "2026-09-29T17:36:10Z"},
        {"name": "stadion/custom_wttCompleteMatchList_2025-03-17__20250323034420.json", "host": "web.archive.org",
         "status": 200, "retrieved_at": "2026-09-29T17:50:00Z"},
    ]
    (research / "_receipts.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
    monkeypatch.setattr(L, "RESEARCH", research)
    receipts = P.receipts_for(L.SOURCE)
    assert L.import_research(receipts) == {"imported day": 1, "hash differs from its receipt": 1}
    r = receipts.get(L.day_name("2026-09-28", "20260929T173625Z"))
    assert r["imported"] and r["retrieved_at"] == "2026-09-29T17:36:25+00:00" and r["status"] == 200
    assert gzip.decompress(L.day_dest("2026-09-28", "20260929T173625Z").read_bytes()) == day_body
    assert (folder / "wttCompleteMatchList_2026-09-28.json").exists()                  # copied, not moved
    assert L.import_research(P.receipts_for(L.SOURCE))["already held"] == 1
    # an imported list is a capture like any other: its played matches' documents are asked for
    state = L.latest_state(L.day_captures(P.receipts_for(L.SOURCE).all()), L.read_capture)
    assert {s["match"]["id"] for s in L.wanted(state, TODAY, NOW)} == {TRELEW_COMPLETE, TRELEW_STOPPED}


def test_staging_rebuilds_every_table_from_raw(roots):
    run(FakeSession(), "20261008T193000Z")
    out = L.stage_all()
    m = pd.read_parquet(P.dump_path(L.SOURCE, "matches.parquet"))
    listed = sum(1 for doc in DAYS.values() for _ in L.listed(doc))
    assert out["matches"] == len(m) == listed and m["latest"].eq("TRUE").sum() == listed
    assert set(m.columns) >= set(L.MATCH_COLUMNS) and m["list_date"].notna().all() and m["capture"].notna().all()
    assert m.loc[m["match_id"].eq(MAANSHAN_FINAL), "actual_end_date"].item() == "2026-10-04T05:13:17Z"
    ev = pd.read_parquet(P.dump_path(L.SOURCE, "events.parquet"))
    assert sorted(ev["tennis_id"]) == sorted({e["tennisId"] for doc in DAYS.values() for e in doc["data"].values()})
    st = pd.read_parquet(P.dump_path(L.SOURCE, "statistics.parquet"))
    assert len(st) == 6 and set(st["match_id"]) == {STATS_ID}
    pts = pd.read_parquet(P.dump_path(L.SOURCE, "points.parquet"))
    assert len(pts) == 20 and pts["consistent"].eq("TRUE").all()
    docs = pd.read_parquet(P.dump_path(L.SOURCE, "documents.parquet"))
    assert len(docs) == 8 and docs["has_data"].eq("TRUE").sum() == 2
    start = docs.loc[docs["match_id"].eq(MAANSHAN_FINAL) & docs["kind"].eq("stats"), "actual_start_date"].item()
    assert start == "2026-09-29T09:33:15Z"
    # every column a string, with the dump's provenance columns
    assert all(str(t) in ("object", "string", "str") for c, t in m.dtypes.items() if not c.startswith("_") or c == "_source")
    assert {"_source", "_source_file", "_retrieved_at"} <= set(m.columns)
    assert list(st.columns) == L.STAT_COLUMNS + [n for n, _ in P.C.PROVENANCE_FIELDS]
    assert st["_row"].tolist() == list(range(1, 7))
    # every answer was parsed once: a second staging reads the cache and writes the same tables
    assert out["documents_parsed"] == 8                                     # the empty answers too
    again = L.stage_all()
    assert again["documents_parsed"] == 0 and again["statistics"] == 6 and again["points"] == 20
    st2 = pd.read_parquet(P.dump_path(L.SOURCE, "statistics.parquet"))
    pd.testing.assert_frame_equal(st.drop(columns=["_retrieved_at"]), st2.drop(columns=["_retrieved_at"]))
    # an answer asked again with other content is parsed again, and only its new rows are kept
    receipts = P.receipts_for(L.SOURCE)
    name = L.doc_name(MAANSHAN_FINAL, "stats")
    trimmed = {**STATS, "data": STATS["data"][:2]}
    body = json.dumps(trimmed).encode()
    L.doc_dest(MAANSHAN_FINAL, "stats").write_bytes(gzip.compress(body))
    receipts.record({**receipts.get(name), "sha256": P.sha256_bytes(body), "bytes": len(body)})
    third = L.stage_all()
    assert third["documents_parsed"] == 1 and third["statistics"] == 2
    docs = pd.read_parquet(P.dump_path(L.SOURCE, "documents.parquet"))
    assert docs.loc[docs["match_id"].eq(MAANSHAN_FINAL) & docs["kind"].eq("stats"), "items"].item() == "2"
