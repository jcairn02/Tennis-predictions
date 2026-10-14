"""TennisLive by event (work package P4): the week catalogs, event kinds, results sections, the token's renewal, the
samples, the women's tour in the player adapter, the data map's loaders, and a whole run against a fake TennisLive
(offline; every answer is canned, and the raw, dump and evidence folders are temporary)."""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import tennislive as TL  # noqa: E402
from src.ingest.point_sources import tennislive_events as E  # noqa: E402

SITE = TL.SITE
FIXTURES = PROJECT_ROOT / "test" / "point_shot_sources" / "fixtures"
TS = lambda day, hour=10: int(pd.Timestamp(f"{day} {hour}:00", tz="UTC").timestamp())  # noqa: E731


def runtime_page(rt: dict) -> str:
    return ("<!DOCTYPE html><html><head><script>window.TENNISLIVE_RUNTIME = " + json.dumps(rt) + ";</script>"
            "</head><body><main></main></body></html>")


def person(pid, name, sets, tour="atp"):
    return {"id": pid, "name": name, "url": f"/{tour}/{name.lower().replace(' ', '-')}/", "seed": "", "flag": "x",
            "setsWon": sum(1 for s in sets if (s.get("score") if isinstance(s, dict) else s) >= 6), "sets": sets,
            "members": []}


def match(pid1, name1, pid2, name2, day, *, sets1=(6, 6), sets2=(3, 4), winner=1, state="finished", end=None,
          event="m25-east-lansing-2026", tour="atp", doubles=False, url=True):
    p1, p2 = person(pid1, name1, list(sets1), tour), person(pid2, name2, list(sets2), tour)
    slug = f"{p1['url'].split('/')[2]}-VS-{p2['url'].split('/')[2]}"
    return {"id": f"games-{tour}-{pid1}-{pid2}-{TS(day)}", "identity": f"{tour}:{pid1}:{pid2}",
            "url": f"/{tour}/match/{slug}/{event}/" if url else "", "state": state, "doubles": doubles,
            "players": [p1, p2], "winnerId": pid1 if winner == 1 else pid2 if winner == 2 else None,
            "setWinners": [0, 0], "endReason": end, "startTimestamp": TS(day), "observedStartedAt": 0,
            "finishedAt": 0, "duration": ""}


def group(stage, matches, *, tid=21960, name="ATP M25 East Lansing", url="/atp-men/m25-east-lansing-2026/",
          tour="atp", rank=0):
    return {"id": f"-{tour}-{tid}-regular-1", "tournamentId": tid, "name": name, "url": url, "tour": tour,
            "info": tour.upper(), "rank": rank, "stage": stage, "stageCode": stage, "startTimes": [""] * len(matches),
            "matches": matches}


LANSING = [
    group("final", [match(1, "Aa Alpha", 2, "Bb Beta", "2026-08-16")]),
    group("semifinal", [match(1, "Aa Alpha", 3, "Cc Gamma", "2026-08-15"),
                        match(2, "Bb Beta", 4, "Dd Delta", "2026-08-15")]),
    group("round_1", [match(1, "Aa Alpha", 5, "Ee Epsilon", "2026-08-12", sets1=[{"score": 7, "detail": 7}, 6],
                            sets2=[{"score": 6, "detail": 4}, 1]),
                      match(6, "Ff Zeta", 7, "Gg Eta", "2026-08-12", state="finished", end="walkover", sets1=[],
                            sets2=[]),
                      match(8, "Hh Theta/Ii Iota", 9, "Jj Kappa/Kk Lambda", "2026-08-12", doubles=True)]),
    group("qualifying", [match(10, "Ll Mu", 11, "Mm Nu", "2026-08-10")]),
    group("qualifying_round_1", [match(10, "Ll Mu", 12, "Nn Xi", "2026-08-09"),
                                 match(11, "Mm Nu", 13, "Oo Omicron", "2026-08-09", end="retired")]),
]
SECTION = {"status": "ok", "section": "results", "data": {"totalCounts": {"singles": 7, "doubles": 1},
                                                          "groups": LANSING}}
ANTALYA = group("round_1", [match(20, "Pp Pi", 21, "Qq Rho", "2026-08-12", url=False, event="")],
                tid=15835, name="ATP M15 Antalya", url="")
CATALOG = [
    {"id": 21960, "name": "M25 East Lansing", "url": "/atp-men/m25-east-lansing-2026/", "tour": "atp", "info": "ATP",
     "rank": 0, "country": "United States"},
    {"id": 17205, "name": "W50 Hamburg", "url": "/wta-women/w50-hamburg-2026/", "tour": "wta", "info": "WTA", "rank": 1},
    {"id": 17999, "name": "Wimbledon (juniors)", "url": "/wta-women/wimbledon-juniors-2026/", "tour": "wta",
     "info": "JUNIOR", "rank": 6},
]
MENU = CATALOG[:2] + [{"id": 15835, "name": "M15 Antalya", "url": "", "tour": "atp", "info": "ATP", "rank": 0,
                       "stageCode": "round_1"}]
DATE_PAGE = {"matchesDate": "2026-08-12", "footer": {"weekLabel": "8/10 – Aug 16, 2026"}, "tournamentCatalog": CATALOG,
             "homepageTournamentMenu": MENU, "homepageTournaments": [LANSING[2], ANTALYA],
             "matchCounts": {"all": 4}, "matchesRequestToken": "tok-date"}
HOME = {"matchesRequestToken": "tok-home"}
SECTION_URL = f"{SITE}/api/tournament-section?tour=atp&slug=m25-east-lansing-2026&section=results"
HAMBURG_URL = f"{SITE}/api/tournament-section?tour=wta&slug=w50-hamburg-2026&section=results"


class FakeResponse:
    def __init__(self, status, body, url="http://fake"):
        self.status_code, self.content, self.url = status, body, url
        self.headers = {"content-type": "text/html"}


class FakeClient:
    """Canned answers by URL (anything else is a 404); ``block`` maps a URL to how many times it is refused (as
    P.Client does after its own retry: Blocked); ``tokens`` records the token each API call carried."""

    impersonate = "fake"

    def __init__(self, answers, block=None):
        self.answers, self.block = answers, dict(block or {})
        self.requests, self.urls, self.tokens = 0, [], []

    def get(self, url, headers=None):
        self.requests += 1
        self.urls.append(url)
        if "/api/" in url:
            self.tokens.append((headers or {}).get("X-TennisLive-Token"))
        if self.block.get(url):
            self.block[url] -= 1
            raise P.Blocked(f"HTTP 403 for {url}")
        body = self.answers.get(url)
        if body is None:
            return FakeResponse(404, b"not found", url)
        return FakeResponse(200, body if isinstance(body, bytes) else body.encode("utf-8"), url)

    def stats(self):
        return {"impersonate": self.impersonate, "requests": self.requests}


def answers():
    return {f"{SITE}/2026-08-12/": runtime_page(DATE_PAGE), f"{SITE}/": runtime_page(HOME),
            SECTION_URL: json.dumps(SECTION),
            HAMBURG_URL: json.dumps({"status": "ok", "data": {"groups": []}})}


@pytest.fixture
def folders(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump" / "points")      # as data/dump/points/, the map's DUMP/points
    monkeypatch.setattr(E, "STUDY", tmp_path / "studies")
    monkeypatch.setattr(E, "SAMPLES_CSV", tmp_path / "studies" / "tennislive_samples.csv")
    monkeypatch.setattr(TL, "SAMPLES_CSV", tmp_path / "studies" / "tennislive_samples.csv")
    monkeypatch.setattr(E, "MAP_MATCHES", tmp_path / "map" / "matches.parquet")
    return tmp_path


# weeks ------------------------------------------------------------------------------------------
def test_weeks():
    assert E.parse_week("2026-W27") == dt.date(2026, 6, 29) and E.parse_week("2018-W01") == dt.date(2018, 1, 1)
    with pytest.raises(ValueError):
        E.parse_week("2026-27")
    assert E.last_complete_week(dt.date(2026, 10, 8)) == dt.date(2026, 9, 28)      # a Thursday
    assert E.last_complete_week(dt.date(2026, 10, 5)) == dt.date(2026, 9, 28)      # a Monday: last week is over
    assert E.wednesdays(dt.date(2026, 6, 29), dt.date(2026, 7, 13)) == [dt.date(2026, 7, 1), dt.date(2026, 7, 8),
                                                                        dt.date(2026, 7, 15)]
    days = E.week_days(dt.date(2026, 8, 10))
    assert days[0] == dt.date(2026, 8, 8) and days[-1] == dt.date(2026, 8, 16) and len(days) == 9
    with pytest.raises(SystemExit):
        E.week_range("2026-W27:2026-W52", dt.date(2026, 10, 8))
    assert E.week_range(None, dt.date(2026, 10, 8)) == (dt.date(2018, 1, 1), dt.date(2026, 9, 28))


# parsing --------------------------------------------------------------------------------------
def test_calendar_page_and_events():
    cal = E.parse_calendar(runtime_page(DATE_PAGE))
    assert (cal["date"], cal["week_label"], cal["match_count"], cal["token"]) == ("2026-08-12", "8/10 – Aug 16, 2026",
                                                                                 4, "tok-date")
    events = E.collect_events([(dt.date(2026, 8, 10), E.light(cal))])
    assert set(events) == {"atp:21960", "wta:17205", "wta:17999", "atp:15835"}
    lansing, antalya = events["atp:21960"], events["atp:15835"]
    assert (lansing["url"], lansing["slug"], lansing["kind"], lansing["first_week"]) == (
        "/atp-men/m25-east-lansing-2026/", "m25-east-lansing-2026", "itf", "2026-08-10")
    assert lansing["in_catalog"] and lansing["in_menu"] and lansing["wednesday_matches"] == 3
    assert antalya["url"] is None and antalya["kind"] == "itf" and antalya["name"] == "M15 Antalya"
    assert antalya["wednesday_matches"] == 1 and not antalya["in_catalog"]
    assert events["wta:17999"]["kind"] == "junior"
    assert [ev["key"] for ev in E.targets_of(events, E.KINDS)] == ["wta:17205", "atp:21960"]
    assert [ev["key"] for ev in E.pageless_of(events, E.KINDS)] == ["atp:15835"]
    assert E.pageless_days([antalya])[0] == dt.date(2026, 8, 8)


@pytest.mark.parametrize("tour, rank, name, info, kind", [
    ("atp", 0, "M15 Monastir", "ATP", "itf"),
    ("atp", 0, "Italy F31 (Santa Margherita Di Pula)", "ATP", "itf"),
    ("atp", 1, "Cordenons Challenger", "ATP", "challenger"),
    ("atp", 1, "M25+H Kazan", "ATP", "itf"),
    ("wta", 0, "Gyeongsan", "WTA", "itf"),                    # 2018: the city only
    ("wta", 1, "Barcelona", "WTA", "itf"),
    ("wta", 1, "W35 Aix-les-Bains", "WTA", "itf"),
    ("wta", 1, "W25+H Calvi", "WTA", "itf"),
    ("wta", 1, "Hall of Fame Open - Newport", "WTA", "wta125"),
    ("wta", 2, "Athens Open - Athens", "WTA", "tour"),
    ("atp", 3, "Cincinnati Open - Cincinnati", "ATP", "tour"),
    ("atp", 4, "Wimbledon - London", "ATP", "slam"),
    ("atp", 3, "Nitto ATP Finals - Turin", "ATP", "finals"),
    ("wta", 2, "WTA Elite Trophy - Zhuhai", "WTA", "finals"),
    ("atp", 5, "Davis Cup, World Group, SF, ITA-BEL 2-0", "ATP", "team"),
    ("atp", 2, "United Cup - Sydney", "ATP", "team"),
    ("wta", 6, "All Lower level tournaments", "WTA", "other"),
    ("atp", 6, "Wimbledon (juniors)", "JUNIOR", "junior"),
    ("atp", None, "Somewhere", "ATP", "other"),
])
def test_event_kinds(tour, rank, name, info, kind):
    assert E.event_kind(tour, rank, name, info) == kind


def test_event_urls():
    assert E.norm_url("/atp-men/m25-poznan-2026/") == "/atp-men/m25-poznan-2026/"
    assert E.norm_url("/atp-men/m25-poznan-2026/#results") == "/atp-men/m25-poznan-2026/"
    assert E.norm_url("https://www.tennislive.net/wta-women/w50-hamburg-2026/") == "/wta-women/w50-hamburg-2026/"
    assert E.norm_url("C:/Program Files/Git/atp-men/m25-figueira-da-foz-2026/") == "/atp-men/m25-figueira-da-foz-2026/"
    assert E.norm_url("atp-men/m25-poznan-2026") == "/atp-men/m25-poznan-2026/"
    assert E.norm_url("") is None and E.norm_url(None) is None and E.norm_url("/atp/match/a-VS-b/x/") is None
    name, dest = E.section_target("/wta-women/w50-hamburg-2026/")
    assert name == "tournaments/wta-women/w50-hamburg-2026/results"
    assert dest.as_posix().endswith("tennislive/tournaments/wta-women/w50-hamburg-2026__results.json.gz")


def test_section_validator():
    assert E.section_validator(b'{"status": "ok", "data": {}}') is None
    assert E.section_validator(b"<html>").startswith("response is not JSON")
    assert E.section_validator(b'{"status": "error", "error": "Invalid request token"}').startswith("refused")
    assert E.section_validator(b'{"status": "error", "error": "Tournament not found"}').startswith("status not ok")


def test_a_section_is_final_once_its_matches_are_over_or_a_week_old():
    done = {"data": {"groups": [{"matches": [{"state": "finished", "startTimestamp": TS("2026-08-16")}]}]}}
    open_ = {"data": {"groups": [{"matches": [{"state": "finished", "startTimestamp": TS("2026-08-15")},
                                              {"state": "scheduled", "startTimestamp": TS("2026-08-16")}]}]}}
    assert E.section_settled(done, "2026-08-16T12:00:00+00:00")
    assert not E.section_settled(open_, "2026-08-16T12:00:00+00:00")
    assert E.section_settled(open_, "2026-08-24T12:00:00+00:00")
    assert not E.section_settled(open_, None)


def test_scores_rounds_and_results():
    assert E.score_text([{"score": 7, "detail": 8}, 1, 6], [{"score": 6, "detail": 6}, 6, 3]) == "7-6(6) 1-6 6-3"
    assert E.score_text([], [1]) is None
    codes = ["final", "semifinal", "quarterfinal", "round_2", "round_1", "qualifying", "qualifying_round_2",
             "qualifying_round_1"]
    assert E.round_codes(codes) == {"final": "F", "semifinal": "SF", "quarterfinal": "QF", "round_2": "R16",
                                    "round_1": "R32", "qualifying": "Q3", "qualifying_round_2": "Q2",
                                    "qualifying_round_1": "Q1"}
    assert E.round_codes(["round_1", "round_2", "round_3", "quarterfinal", "qualifying"]) == {
        "round_1": "R64", "round_2": "R32", "round_3": "R16", "quarterfinal": "QF", "qualifying": "Q1"}
    # a 'match' group of round 0 opens a 128-player qualifying draw (USA F5, 2018): four qualifying rounds
    assert E.stage_key("match", 0) == "qualifying_round_0" and E.stage_key("match", 20) == "match"
    assert E.stage_key("round_robin", 8) == "round_robin" and E.stage_key("round_1", 4) == "round_1"
    assert E.round_codes([E.stage_key("match", 0), "qualifying_round_1", "qualifying_round_2", "qualifying"]) == {
        "qualifying_round_0": "Q1", "qualifying_round_1": "Q2", "qualifying_round_2": "Q3", "qualifying": "Q4"}
    pre = group("match", [match(30, "Rr Sigma", 31, "Ss Tau", "2026-08-08")])
    pre["roundId"] = 0
    rows = E.section_rows({"data": {"groups": [pre, LANSING[3]]}}, {"key": "atp:21960", "url": None, "kind": "itf",
                                                                    "rank": 0, "tour": "atp", "tl_id": 21960}, {})
    assert [(r["stage_code"], r["draw"], r["round"]) for r in rows] == [("match", "qualifying", "Q1"),
                                                                        ("qualifying", "qualifying", "Q2")]
    assert E.played({"state": "finished", "winnerId": 1, "players": []})
    assert E.played({"state": "finished", "endReason": "retired", "winnerId": 1})
    assert not E.played({"state": "finished", "endReason": "walkover", "winnerId": 1})
    assert not E.played({"state": "scheduled", "players": [{"sets": [1]}]})


def test_section_rows():
    ev = {"key": "atp:21960", "url": "/atp-men/m25-east-lansing-2026/", "tl_id": 21960, "kind": "itf", "rank": 0,
          "tour": "atp"}
    rows = E.section_rows(SECTION, ev, {"source_file": "f", "source_sha256": "s", "retrieved_at": "t"})
    assert len(rows) == 9 and set(rows[0]) == set(E.LISTED_COLUMNS)
    final = rows[0]
    assert (final["round"], final["draw"], final["discipline"], final["winner_side"], final["played"]) == (
        "F", "main", "singles", 1, True)
    assert (final["player1_name"], final["player2_name"], final["score"]) == ("Aa Alpha", "Bb Beta", "6-3 6-4")
    assert final["url"] == "/atp/match/aa-alpha-VS-bb-beta/m25-east-lansing-2026/" and final["source_file"] == "f"
    r1 = rows[3]
    assert (r1["round"], r1["score"], r1["player1_sets"]) == ("R16", "7-6(4) 6-1", "7(7) 6")
    walkover, doubles = rows[4], rows[5]
    assert walkover["played"] is False and walkover["end_reason"] == "walkover"
    assert doubles["discipline"] == "doubles" and doubles["player1_members"] is None
    quals = [r for r in rows if r["draw"] == "qualifying"]
    assert [r["round"] for r in quals] == ["Q2", "Q1", "Q1"] and quals[2]["played"] is True   # a retirement counts
    counts = {}
    E.tally_event(counts, rows)
    assert counts == {"singles_main": 5, "singles_main_played": 4, "singles_qualifying": 3,
                      "singles_qualifying_played": 3, "doubles": 1, "first_start_utc": "2026-08-09 10:00",
                      "last_start_utc": "2026-08-16 10:00"}


def test_day_rows_keep_a_match_once():
    ev = {"key": "atp:15835", "url": None, "kind": "itf", "rank": 0, "tour": "atp", "tl_id": 15835}
    m = ANTALYA["matches"][0]
    later = {**m, "state": "finished"}
    rows = E.day_rows([("2026-08-12", ANTALYA, {"source_file": "a"}),
                       ("2026-08-13", {**ANTALYA, "matches": [later]}, {"source_file": "b"})], ev)
    assert len(rows) == 1 and rows[0]["listed_from"] == "date page 2026-08-13" and rows[0]["url"] is None


# samples ----------------------------------------------------------------------------------------
def pool_frame():
    rows = []
    for tour in ("atp", "wta"):
        for e in range(5):
            for k in range(3):
                year = 2019 + (e % 2)
                rows.append({"event_key": f"{tour}:{e}", "tour": tour, "url": f"/{tour}/match/m{e}-{k}/x/",
                             "day": f"{year}-05-0{k + 1}", "year": year})
    return pd.DataFrame(rows)


def test_samples_are_seeded_one_per_event_and_spread_over_years():
    pool = pool_frame()
    a = E.draw_sample(pool, "s", seed=1, per_tour=4)
    assert a.equals(E.draw_sample(pool, "s", seed=1, per_tour=4))            # seeded: the same draw again
    assert len(a) == 8 and a.groupby("tour").size().tolist() == [4, 4]
    events = a["url"].str.extract(r"/match/m(\d)-")[0]
    assert events.groupby(a["tour"]).nunique().tolist() == [4, 4]            # one match per event while events last
    many = E.draw_sample(pool, "s", seed=1, per_tour=7)                       # 5 events: two give a second match
    assert many.groupby("tour").size().tolist() == [7, 7]
    by_year = E.draw_sample(pool, "s", seed=1, per_tour=4, years=[2019, 2020])
    assert by_year.groupby(["tour", "stratum"]).size().tolist() == [2, 2, 2, 2]
    listed = pd.DataFrame({"event_key": ["e1", "e1", "e2", "e3"], "discipline": "singles", "played": "TRUE",
                           "url": ["/a/", "/b/", None, "/c/"], "draw": ["main", "qualifying", "main", "main"],
                           "start_utc": ["2026-06-02 10:00", "2026-06-01 10:00", "2026-07-01 10:00", None],
                           "tour": "atp"})
    events = pd.DataFrame({"key": ["e1", "e2", "e3"], "kind": ["itf", "itf", "itf"],
                           "first_week": ["2026-06-01", "2026-06-29", "2026-05-25"]})
    main = E.sample_pool(listed, events, E.SAMPLES["itf_main_since_june_2026"])
    assert main["url"].tolist() == ["/a/"]                                    # no page, or before June, is left out
    qual = E.sample_pool(listed, events, E.SAMPLES["itf_qualifying_2019_2026"])
    assert qual["url"].tolist() == ["/b/"]


def test_page_record_against_the_listed_score():
    html = (FIXTURES / "tennislive_match.html").read_text(encoding="utf-8")
    rec = E.page_record(html, "5-7 6-0 6-1")
    assert rec["pbp_available"] and rec["points_listed"] == 50 and rec["record_games"] == "12"
    assert rec["score_games"] == "12 6 7" and rec["verdict"] == "other shortfall" and rec["stats_available"]
    assert rec["point_game_share"] == round(12 / 25, 3)
    nodata = E.page_record((FIXTURES / "tennislive_match_nodata.html").read_text(encoding="utf-8"), "6-1 6-1")
    assert nodata["verdict"] == "no points" and not nodata["stats_available"]


# fetching: the session token ---------------------------------------------------------------------
def test_a_refused_token_opens_one_new_session_then_stops(folders):
    receipts = P.receipts_for(E.SOURCE)
    ev = {"key": "atp:21960", "url": "/atp-men/m25-east-lansing-2026/", "slug": "m25-east-lansing-2026",
          "tour": "atp", "tl_id": 21960}
    client = FakeClient(answers(), block={SECTION_URL: 1})
    session = E.Session(client, receipts)
    session.token = "stale"
    r = E.fetch_section(client, receipts, session, ev)
    assert r["status"] == 200 and session.opened == 1 and client.tokens == ["stale", "tok-home"]
    assert client.urls == [SECTION_URL, f"{SITE}/", SECTION_URL]
    before = client.requests
    assert E.fetch_section(client, receipts, session, ev)["skipped"] and client.requests == before   # final: kept
    twice = FakeClient(answers(), block={HAMBURG_URL: 2})
    session = E.Session(twice, receipts)
    with pytest.raises(P.Blocked):
        E.fetch_section(twice, receipts, session, {**ev, "key": "wta:17205", "url": "/wta-women/w50-hamburg-2026/",
                                                   "slug": "w50-hamburg-2026", "tour": "wta"})


def test_an_unfinished_event_is_fetched_again(folders):
    receipts = P.receipts_for(E.SOURCE)
    ev = {"key": "atp:21960", "url": "/atp-men/m25-east-lansing-2026/", "slug": "m25-east-lansing-2026",
          "tour": "atp", "tl_id": 21960}
    live = json.loads(json.dumps(SECTION))
    live["data"]["groups"][0]["matches"][0]["state"] = "live"
    live["data"]["groups"][0]["matches"][0]["startTimestamp"] = int(dt.datetime.now(dt.timezone.utc).timestamp())
    client = FakeClient({**answers(), SECTION_URL: json.dumps(live)})
    session = E.Session(client, receipts)
    E.fetch_section(client, receipts, session, ev)
    client.answers[SECTION_URL] = json.dumps(SECTION)
    r = E.fetch_section(client, receipts, session, ev)
    assert not r.get("skipped") and client.urls.count(SECTION_URL) == 2


def test_answers_that_never_come_stop_the_run(folders):
    stalls = E.Stalls(limit=2)
    timeout = {"status": None, "error": "RuntimeError: Timeout: Failed to perform, curl: (28) Operation timed out"}
    stalls.note(timeout)
    stalls.note({"status": 200})                        # an answer in between resets the count
    stalls.note(timeout)
    stalls.note({"status": 404})
    stalls.note({"status": None, "error": "response is not JSON"})   # an answer that failed validation is no stall
    stalls.note(timeout)
    with pytest.raises(P.Blocked):
        stalls.note(timeout)

    class Silent(FakeClient):
        def get(self, url, headers=None):
            self.requests += 1
            raise RuntimeError("Timeout: Failed to perform, curl: (28) Operation timed out after 30010 milliseconds")

    client = Silent({})
    samples = pd.DataFrame({"sample": ["s"] * 3, "url": [f"/atp/match/a{n}-VS-b/x-2026/" for n in range(3)]})
    with pytest.raises(P.Blocked):
        E.fetch_samples(client, P.receipts_for(E.SOURCE), samples)
    assert client.requests == 2                          # stopped after the second page without an answer


# the player adapter: the women's tour -------------------------------------------------------------
def test_players_by_tour(folders):
    assert TL.player_ref("wta:anna-siskova") == ("wta", "anna-siskova")
    assert TL.player_ref("brandon-holt") == ("atp", "brandon-holt") and TL.player_ref("x", "wta") == ("wta", "x")
    assert TL.player_parts("atp", "a") == ("players", "a") and TL.player_parts("wta", "b") == ("players", "wta", "b")
    assert TL.player_key("wta", "b") == "wta:b" and TL.player_key("atp", "a") == "a"
    page = runtime_page({"playerLiveRequestToken": "tok", "playerDetailName": "Anna Siskova",
                         "playerDetailStatisticsPreload": {"careerRows": [{"year": 2026}, {"year": 2025}]}})
    listing = {"status": "ok", "data": {"total": 1, "limit": 60, "groups": [
        {"name": "WTA W50 Hamburg", "url": "/wta-women/w50-hamburg-2026/", "tour": "wta",
         "matches": [match(1, "Anna Siskova", 2, "Rasheeda Mcadoo", "2026-08-16", tour="wta", event="w50-hamburg-2026")]}]}}
    api = f"{SITE}/api/player-matches?tour=wta&slug=anna-siskova&discipline=singles&year=2026&surface=all&offset=0"
    client = FakeClient({f"{SITE}/wta/anna-siskova/": page, api: json.dumps(listing)})
    receipts = P.receipts_for(TL.SOURCE)
    info = TL.fetch_player_index(client, receipts, "anna-siskova", seasons=["2026"], refresh=False, this_year=2026,
                                 tour="wta")
    assert info["tour"] == "wta" and info["matches_listed"] == 1 and client.urls == [f"{SITE}/wta/anna-siskova/", api]
    assert client.tokens == ["tok"]
    assert P.raw_path(TL.SOURCE, "players", "wta", "anna-siskova", "matches_2026_0.json").exists()
    assert TL.players_on_disk() == [("wta", "anna-siskova")]
    rows = TL.load_index(TL.players_on_disk())
    assert len(rows) == 1 and rows[0]["player_tour"] == "wta" and rows[0]["url"].startswith("/wta/match/")


# a run against the fake site, and the map's loaders -----------------------------------------------
def test_run_lists_stages_and_feeds_the_map(folders, monkeypatch):
    client = FakeClient(answers())
    monkeypatch.setattr(E, "make_client", lambda args: client)
    parser = argparse.ArgumentParser()
    E.add_arguments(parser)
    summary = E.run(parser.parse_args(["--weeks", "2026-W33:2026-W33", "--pageless-days", "--no-pages"]))
    assert not summary.get("stopped")
    assert summary["fetch_outcomes"] == {"calendar:200": 1, "day:200:cached": 1, "day:404": 8, "results:200": 2}
    assert client.urls[:3] == [f"{SITE}/2026-08-12/", HAMBURG_URL, SECTION_URL]     # newest first: Hamburg is rank 1
    assert all(t == "tok-date" for t in client.tokens)                               # the date page's session
    ev = pd.read_parquet(P.dump_path(E.SOURCE, "events.parquet")).set_index("key")
    assert ev.loc["atp:21960", "section_status"] == "200" and ev.loc["atp:21960", "singles_qualifying_played"] == "3"
    assert ev.loc["atp:15835", "section_status"] == "no tournament page" and ev.loc["atp:15835", "day_pages"] == "1"
    assert pd.isna(ev.loc["wta:17999", "section_status"])                             # a junior event: not listed
    listed = pd.read_parquet(P.dump_path(E.SOURCE, "listed.parquet"))
    assert len(listed) == 10 and listed["listed_from"].value_counts().to_dict() == {"results section": 9,
                                                                                    "date page 2026-08-12": 1}
    assert (folders / "studies" / "tennislive_events.csv.gz").exists()
    assert (folders / "studies" / "runs.jsonl").exists() and summary["events"]["section_status"]["200"] == 2
    assert not (folders / "studies" / "tennislive_samples.csv").exists()               # a partial run draws none
    rerun = E.run(parser.parse_args(["--weeks", "2026-W33:2026-W33", "--no-pages"]))
    assert rerun["fetch_outcomes"] == {"calendar:200:cached": 1, "results:200:cached": 2}

    monkeypatch.setattr(M, "DUMP", folders / "dump")
    rows = M.load_tennislive_listed()
    assert len(rows) == 8                       # 7 played singles of East Lansing, 1 of Antalya; no walkover or doubles
    assert set(rows["tour"]) == {"M"} and set(rows["level"]) == {"ITF", "ITFQ"}
    assert rows.loc[rows["draw"].eq("qual"), "level"].eq("ITFQ").all() and rows["grain"].eq("result").all()
    assert rows["tname"].iloc[0] == "M25 East Lansing" and rows["d"].notna().all()


def test_a_run_of_later_weeks_keeps_the_earlier_weeks_staged(folders, monkeypatch):
    """A --weeks run fetches its own weeks but stages every week on disk (13 Oct 2026: a --weeks run once restaged only
    its own two weeks over the shared listing)."""
    later = {"matchesDate": "2026-08-19", "footer": {"weekLabel": "8/17 – Aug 23, 2026"}, "tournamentCatalog": [],
             "homepageTournamentMenu": [], "homepageTournaments": [], "matchCounts": {"all": 0},
             "matchesRequestToken": "tok-date-2"}
    client = FakeClient({**answers(), f"{SITE}/2026-08-19/": runtime_page(later)})
    monkeypatch.setattr(E, "make_client", lambda args: client)
    parser = argparse.ArgumentParser()
    E.add_arguments(parser)
    E.run(parser.parse_args(["--weeks", "2026-W33:2026-W33", "--no-pages"]))
    first = pd.read_parquet(P.dump_path(E.SOURCE, "listed.parquet"))
    assert len(first) == 10
    summary = E.run(parser.parse_args(["--weeks", "2026-W34:2026-W34", "--no-pages"]))
    assert summary["fetch_outcomes"] == {"calendar:200": 1}                  # only the later week was fetched
    listed = pd.read_parquet(P.dump_path(E.SOURCE, "listed.parquet"))
    assert len(listed) == 10 and set(listed["event_key"]) == set(first["event_key"])   # the earlier week stays staged
    ev = pd.read_parquet(P.dump_path(E.SOURCE, "events.parquet")).set_index("key")
    assert ev.loc["atp:21960", "section_status"] == "200"


def test_map_levels_of_listed_matches(folders, monkeypatch):
    dump = folders / "dump" / "points" / "tennislive"
    dump.mkdir(parents=True)
    base = {"discipline": "singles", "junior": "FALSE", "played": "TRUE", "player1_name": "A B", "player2_name": "C D",
            "start_utc": "2024-05-08 10:00", "round": "R16", "tour": "atp"}
    rows = [{**base, "event_key": "atp:1", "event_name": "ATP M15 X", "event_kind": "itf", "event_rank": "0",
             "match_id": "a", "draw": "qualifying"},
            {**base, "event_key": "atp:2", "event_name": "ATP Y Challenger", "event_kind": "challenger",
             "event_rank": "1", "match_id": "b", "draw": "main"},
            {**base, "event_key": "atp:3", "event_name": "ATP Z Open - Z", "event_kind": "tour", "event_rank": "3",
             "match_id": "c", "draw": "qualifying"},
            {**base, "event_key": "atp:3", "event_name": "ATP Z Open - Z", "event_kind": "tour", "event_rank": "3",
             "match_id": "c", "draw": "qualifying"},                                    # the same match twice: once
            {**base, "event_key": "atp:4", "event_name": "ATP Davis Cup", "event_kind": "team", "event_rank": "5",
             "match_id": "d", "draw": "main"},                                          # not a listed kind
            {**base, "event_key": "atp:1", "event_name": "ATP M15 X", "event_kind": "itf", "event_rank": "0",
             "match_id": "e", "draw": "main", "played": "FALSE"}]                       # a walkover
    pd.DataFrame(rows).to_parquet(dump / "listed.parquet")
    pd.DataFrame({"key": ["atp:1", "atp:2", "atp:3", "atp:4"], "first_week": ["2024-05-06"] * 4}).to_parquet(
        dump / "events.parquet")
    monkeypatch.setattr(M, "DUMP", folders / "dump")
    out = M.load_tennislive_listed().reset_index(drop=True)
    assert out["group"].tolist() == ["atp:1", "atp:2", "atp:3"]
    assert out["level"].tolist()[0] == "ITFQ" and out["level"].iloc[1:].isna().all()     # others: from the map
    assert out["level_fallback"].tolist()[1:] == ["CH", "T1000"] and pd.isna(out["level_fallback"].iloc[0])
    assert out["draw"].tolist() == ["qual", "main", "qual"] and out["d"].dt.hour.eq(0).all()
    assert out["d"].dt.strftime("%Y-%m-%d").tolist() == ["2024-05-06"] * 3          # each event's Monday


def test_map_dates_by_monday_and_reads_slams(folders, monkeypatch):
    dump = folders / "dump" / "points" / "tennislive"
    dump.mkdir(parents=True)
    base = {"discipline": "singles", "junior": "FALSE", "played": "TRUE", "player1_name": "A B", "player2_name": "C D",
            "round": None, "tour": "wta"}
    rows = [{**base, "event_key": "wta:1", "event_name": "WTA W15 X", "event_kind": "itf", "event_rank": "0",
             "match_id": "q", "draw": "qualifying", "start_utc": "2024-05-04 10:00"},       # the Saturday before
            {**base, "event_key": "wta:1", "event_name": "WTA W15 X", "event_kind": "itf", "event_rank": "0",
             "match_id": "f", "draw": "main", "start_utc": "2024-05-12 10:00"},             # the final, Sunday
            {**base, "event_key": "wta:2", "event_name": "WTA Wimbledon - London", "event_kind": "slam",
             "event_rank": "4", "match_id": "s", "draw": "main", "start_utc": "2024-07-10 12:00"},   # its third week
            {**base, "event_key": "wta:2", "event_name": "WTA Wimbledon - London", "event_kind": "slam",
             "event_rank": "4", "match_id": "t", "draw": "qualifying", "start_utc": None}]
    pd.DataFrame(rows).to_parquet(dump / "listed.parquet")
    pd.DataFrame({"key": ["wta:1", "wta:2"], "first_week": ["2024-05-06", "2024-06-24"]}).to_parquet(
        dump / "events.parquet")
    monkeypatch.setattr(M, "DUMP", folders / "dump")
    out = M.load_tennislive_listed().reset_index(drop=True)
    assert out["d"].dt.strftime("%Y-%m-%d").tolist() == ["2024-05-06", "2024-05-06", "2024-07-08", "2024-06-24"]
    assert out["level"].tolist() == ["ITFQ", "ITF", "GS", "GSQ"] and out["level_fallback"].isna().all()


def test_map_reads_the_tour_from_the_page_url(folders, monkeypatch):
    dump = folders / "dump" / "points" / "tennislive"
    dump.mkdir(parents=True)
    base = {"doubles": "FALSE", "end_reason": None, "reference_utc": "2026-08-16 10:00", "player1_name": "A B",
            "player2_name": "C D", "tournament_name": "W50 Hamburg", "stage": "final", "tournament_rank": "1"}
    pd.DataFrame([{**base, "url": "/wta/match/a-b-VS-c-d/w50-hamburg-2026/", "listed_for_slugs": None,
                   "sampled_in": "itf_main_since_june_2026"},
                  {**base, "url": "/atp/match/e-f-VS-g-h/m25-x-2026/", "listed_for_slugs": "brandon-holt",
                   "sampled_in": None}]).to_parquet(dump / "matches.parquet")
    pd.DataFrame({"url": ["/wta/match/a-b-VS-c-d/w50-hamburg-2026/"]}).to_parquet(dump / "points.parquet")
    pd.DataFrame({"url": ["/atp/match/e-f-VS-g-h/m25-x-2026/"]}).to_parquet(dump / "statistics.parquet")
    monkeypatch.setattr(M, "DUMP", folders / "dump")
    careers, samples = M.load_tennislive(), M.load_tennislive(sampled=True)
    assert careers[["tour", "grain"]].values.tolist() == [["M", "stats"]]
    assert samples[["tour", "grain"]].values.tolist() == [["W", "point"]]


def test_the_week_in_progress_is_read_to_yesterday_and_staged(folders, monkeypatch):
    """--through-yesterday (13 Oct 2026): the week in progress is read day by day up to yesterday (never today's page),
    its events come from its latest page until its Wednesday page exists, and staging holds it."""
    monday_page = {**DATE_PAGE, "matchesDate": "2026-08-10", "matchesRequestToken": "tok-mon"}
    client = FakeClient({**answers(), f"{SITE}/2026-08-10/": runtime_page(monday_page)})
    monkeypatch.setattr(E, "make_client", lambda args: client)
    monkeypatch.setitem(E.TODAY, "day", dt.date(2026, 8, 11))          # a Tuesday: only Monday's page exists
    parser = argparse.ArgumentParser()
    E.add_arguments(parser)
    with pytest.raises(SystemExit):                                     # without the flag: complete weeks only
        E.run(parser.parse_args(["--weeks", "2026-W33:2026-W33", "--no-pages"]))
    summary = E.run(parser.parse_args(["--weeks", "2026-W33:2026-W33", "--through-yesterday", "--no-pages"]))
    assert f"{SITE}/2026-08-10/" in client.urls and f"{SITE}/2026-08-11/" not in client.urls
    assert f"{SITE}/2026-08-12/" not in client.urls                    # Wednesday is in the future
    listed = pd.read_parquet(P.dump_path(E.SOURCE, "listed.parquet"))
    assert "atp:21960" in set(listed["event_key"])                     # the week in progress is staged
    assert summary["staged_range"].endswith("2026-08-10 (every week on disk)")
