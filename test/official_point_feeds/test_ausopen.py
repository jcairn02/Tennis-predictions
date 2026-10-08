"""The Australian Open adapter, the official feeds' client policy and the verification's score replay (offline).

Fixtures are cut from payloads fetched on 24 Sep 2026: whole match-centre documents for MD106 (doubles, a 7-2
tiebreak), MQ122 (a retirement after an 11-9 tiebreak) and MS406 (a walkover), and the women's doubles draw cut
to three matches (a win, a retirement and a walkover). Players' records are trimmed to their name and id fields.
"""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "official_point_feeds"))

from src.ingest.point_sources import ausopen as A  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402
import verify_ausopen as V  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# commentary -------------------------------------------------------------------------
def test_commentary_sentences_map_to_outcome_side_and_role():
    said = A.parse_commentary("Mannarino/Martin lose the point with a Backhand Forced Error")
    assert (said["subject"], said["subject_role"], said["outcome"], said["stroke_side"]) == \
        ("Mannarino/Martin", "loser", "forced_error", "backhand")
    assert said["mapped"] and said["verb_agrees"]
    said = A.parse_commentary("C. Alcaraz wins the point with an Ace")
    assert (said["subject"], said["subject_role"], said["outcome"], said["stroke_side"]) == ("C. Alcaraz", "winner", "ace", None)
    assert A.parse_commentary("N. Djokovic loses the point with a Forehand Unforced Error")["outcome"] == "unforced_error"
    assert A.parse_commentary("A B wins the point with a Service Winner")["outcome"] == "service_winner"
    bare = A.parse_commentary("P. Hon wins the point")  # seen once in WS114: no detail
    assert bare["outcome"] == "unspecified" and bare["mapped"] and bare["stroke_side"] is None
    odd = A.parse_commentary("X wins the point with a Forehand Double Fault")
    assert odd["outcome"] == "unmapped" and not odd["mapped"]
    assert A.parse_commentary("X wins the point with a Double Fault")["verb_agrees"] is False
    assert A.parse_commentary("Medical time-out")["kind"] == "unmapped"
    serve = A.parse_commentary("F. Martin is serving game 13")
    assert serve == {"kind": "serve", "server": "F. Martin", "serve_game": 13}


def test_names_match_without_case_and_with_a_hyphenated_surname_cut():
    # WQ124: the commentary calls her "V. Tomova"; the player record says "V. Tomova-Traycheva"
    teams = [{"players": [{"short_name": "B. Pera", "full_name": "Bernarda Pera", "last_name": "Pera", "uuid": "a"}]},
             {"players": [{"short_name": "V. Tomova-Traycheva", "full_name": "Viktoria Tomova-Traycheva",
                           "last_name": "Tomova-Traycheva", "uuid": "b"}]}]
    forms = A.team_forms(teams)
    assert A.name_team("V. Tomova", forms) == 2 and A.name_team("v.  Tomova-Traycheva", forms) == 2
    assert A.name_team("B. Pera", forms) == 1 and A.name_team("X. Other", forms) is None
    assert A.player_id("V. Tomova", forms, 2) == "b" and A.player_id("V. Tomova", forms, None) is None
    mcdonald = A.team_forms([{"players": [{"short_name": "M. McDonald"}]}, {"players": [{"short_name": "M. Other"}]}])
    assert A.name_team("M. Mcdonald", mcdonald) == 1  # a Wayback capture writes "Mcdonald"
    pair = A.team_forms([{"players": [{"last_name": "Cash"}, {"last_name": "Tracy"}]},
                         {"players": [{"last_name": "Frantzen"}, {"last_name": "Haase"}]}])
    assert A.name_team("Frantzen/Haase", pair) == 2 and A.name_team("Cash/Tracy", pair) == 1


def test_tiebreak_detection_and_server_rotation():
    assert A.is_tiebreak(13, []) and A.is_tiebreak(1, ["0 - 1", "Game"]) and not A.is_tiebreak(4, ["15 - 0", "AD - 40", "Game"])
    assert [A.tiebreak_server(2, n) for n in range(1, 10)] == [2, 1, 1, 2, 2, 1, 1, 2, 2]
    assert A.tiebreak_server(None, 1) is None


# match-centre documents -------------------------------------------------------------
def test_point_rows_of_a_doubles_match_with_a_tiebreak():
    payload = load("ausopen_match_centre_MD106.json")
    rows = A.point_rows(payload)
    assert len(rows) == 123 and [r["seq"] for r in rows] == list(range(1, 124))
    assert all(r["mapped"] for r in rows) and all(r["subject_team"] == r["subject_name_team"] for r in rows)
    first = rows[0]
    assert (first["entry_id"], first["set"], first["game"], first["point"]) == ("MD106-001-001-001", 1, 1, 1)
    assert (first["game_server_name"], first["game_server_team"], first["utc"]) == ("A. Olivetti", 1, "2026-01-21 00:12:26")
    assert first["game_server_player_id"] is not None
    tiebreak = [r for r in rows if r["set"] == 2 and r["game"] == 13]
    assert len(tiebreak) == 9 and all(r["tiebreak"] for r in tiebreak)
    assert [r["point_server_team"] for r in tiebreak] == [2, 1, 1, 2, 2, 1, 1, 2, 2]
    assert [r["score"] for r in tiebreak][:4] == ["0 - 1", "1 - 1", "2 - 1", "1 - 3"]  # written server first
    last = rows[-1]
    assert (last["type"], last["outcome"], last["stroke_side"], last["subject_team"]) == ("match", "winner", "forehand", 1)
    # every ace and double fault falls on a point served by the side that hit it
    served = [r for r in rows if r["outcome"] in ("ace", "double_fault")]
    assert served and all(r["subject_team"] == r["point_server_team"] for r in served)


def test_statistics_rows_and_the_ace_reconciliation():
    payload = load("ausopen_match_centre_MD106.json")
    stats = A.stat_rows(payload)
    assert {r["group"] for r in stats} == {"key_stats", "serve_stats", "rally_stats"}
    assert {r["set"] for r in stats} == {"1", "2", "All"}
    aces = [r for r in stats if r["group"] == "key_stats" and r["stat"] == "Aces"]
    assert [(r["set"], r["team1_primary"], r["team2_primary"]) for r in aces] == [("1", 6, 1), ("2", 9, 0), ("All", 15, 1)]
    rows = A.point_rows(payload)
    for period, t1, t2 in (("1", 6, 1), ("2", 9, 0)):
        counted = [sum(1 for r in rows if str(r["set"]) == period and r["outcome"] == "ace" and r["subject_team"] == team)
                   for team in (1, 2)]
        assert counted == [t1, t2]


def test_match_records_points_empty_and_absent():
    assert A.document_record({"status": 200}, load("ausopen_match_centre_MD106.json")) == ("points", None)
    assert A.document_record({"status": 200}, load("ausopen_match_centre_MS406.json")) == ("empty", "walkover: no point was played")
    # the API's answer to an unknown match id, as the research notes report it (32 bytes, HTTP 200)
    record, reason = A.document_record({"status": 200}, {"message": "match id not found"})
    assert record == "absent" and "match id not found" in reason
    assert A.document_record({"status": 403, "absent": "API Gateway: x"}, None) == ("absent", "API Gateway: x")
    assert A.document_record({"status": 404}, None) == ("absent", "HTTP 404")
    assert A.document_record({"error": "HTTP 500"}, None) == ("error", "HTTP 500")
    assert A.document_record({"status": 200}, None) == ("error", "the saved file is missing")
    assert A.document_record(None, None) == ("not fetched", None)


def test_document_rows_carry_provenance_and_counts():
    payload = load("ausopen_match_centre_MQ122.json")
    receipt = {"status": 200, "sha256": "abc", "retrieved_at": "2026-09-24T18:00:00+00:00"}
    info, points, stats = A.document_rows(payload, receipt, "data/raw/x.json", {"record_key": "2026/MQ122", "route": "api"})
    assert (info["record"], info["points"], info["serve_entries"], info["sets_with_points"]) == ("points", 110, 15, 2)
    assert info["stats_sets"] == "1;2;All" and info["unexpected_entry_types"] is None
    assert all(p["record_key"] == "2026/MQ122" and p["source_sha256"] == "abc" for p in points + stats)
    assert set(A.POINT_COLUMNS) >= set(points[0]) and set(A.STAT_COLUMNS) >= set(stats[0])


def test_draw_matches_and_their_descriptive_fields():
    draw = load("ausopen_draw_WD.json")
    lookup = A.draw_lookup(draw)
    rows = {m["match_id"]: A.match_meta(m, lookup) for m in draw["matches"]}
    assert set(rows) == {"WD101", "WD111", "WD205"}
    won = rows["WD101"]
    assert (won["match_status"], won["team1_score"], won["team2_score"], won["winner_team"]) == ("CMP", "6 6", "3 4", 1)
    assert won["round_name"] == "1st Round" and ";" in won["team1_names"] and won["team1_tour_ids"].count(";") == 1
    assert (rows["WD111"]["match_status"], rows["WD111"]["team1_score"], rows["WD111"]["team2_score"]) == ("RET", "5", "0")
    assert (rows["WD205"]["match_status"], rows["WD205"]["team1_score"], rows["WD205"]["winner_team"]) == ("W/O", None, 1)
    wd111 = next(m for m in draw["matches"] if m["match_id"] == "WD111")
    unfilled = {**wd111, "teams": [None, wd111["teams"][1]]}  # a place not yet filled, as in archived draws
    row = A.match_meta(unfilled, lookup)
    assert "team1_names" not in row and row["team2_score"] == "0" and row["match_id"] == "WD111"
    mc = A.match_meta(load("ausopen_match_centre_MD106.json"), {})  # a match-centre document carries its players inline
    assert (mc["team1_names"], mc["team1_score"], mc["team2_score"]) == ("Theo Arribage;Albano Olivetti", "6 7(7)", "3 6(2)")


def test_wayback_capture_list_keeps_one_row_per_content():
    payload = [["timestamp", "original", "statuscode", "mimetype", "length", "digest"],
               ["20240128132209", "https://prod-scores-api.ausopen.com/match-centre/MS701", "200", "application/json", "9", "AAA"],
               ["20240128140000", "https://prod-scores-api.ausopen.com/match-centre/MS701", "200", "application/json", "9", "AAA"],
               ["20240129000000", "https://prod-scores-api.ausopen.com/match-centre/MS701?x=1", "200", "application/json", "9", "BBB"]]
    rows = A.cdx_rows(payload)
    assert [(r["timestamp"], r["match_id"]) for r in rows] == [("20240128132209", "MS701"), ("20240129000000", "MS701")]
    assert A.cdx_rows([]) == []
    assert A.wayback_dest("20240128132209", "MS701").name == "20240128132209_MS701.json"


# the official feeds' client -----------------------------------------------------------
class FakeResponse:
    def __init__(self, status, body=b"{}", headers=None):
        self.status_code = status
        self.content = body
        self.headers = {"content-type": "application/json", **(headers or {})}
        self.url = "http://x"


class FakeSession:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def get(self, url, timeout=None, headers=None, allow_redirects=True):
        self.calls.append({"url": url, "allow_redirects": allow_redirects})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def _client(answers, not_found=None) -> F.FeedClient:
    client = F.FeedClient("test", not_found=not_found, min_interval=0.0, jitter=0.0, session=FakeSession(answers))
    client._sleep = lambda seconds: setattr(client, "slept", client.slept + seconds)  # no real waiting
    return client


GATEWAY_403 = FakeResponse(403, b'{"message":"Missing Authentication Token"}',
                           {"x-amzn-errortype": "MissingAuthenticationTokenException"})


def test_gateway_not_found_is_an_answer_and_other_refusals_stop_at_once():
    assert A.gateway_not_found(GATEWAY_403).startswith("API Gateway")
    assert A.gateway_not_found(FakeResponse(403, b'{"message":"Missing Authentication Token"}')).startswith("API Gateway")
    assert A.gateway_not_found(FakeResponse(403, b'{"message":"Forbidden"}')) is None
    assert A.gateway_not_found(FakeResponse(200)) is None
    client = _client([GATEWAY_403], not_found=A.gateway_not_found)
    assert client.get("http://x/a").status_code == 403 and client.not_found_answers == 1
    assert client._session.calls[0]["allow_redirects"] is False
    for answer, message in ((FakeResponse(403, b'{"message":"Forbidden"}'), "HTTP 403"),
                            (FakeResponse(429), "HTTP 429"),
                            (FakeResponse(302, b"", {"location": "/robots.txt"}), "redirect to '/robots.txt'"),
                            (FakeResponse(200, b"", {"cf-mitigated": "challenge"}), "Cloudflare challenge"),
                            (FakeResponse(202, b"", {"x-amzn-waf-action": "challenge"}), "AWS WAF"),
                            (FakeResponse(200, b"<html><title>Access Denied</title>", {"content-type": "text/html"}), "challenge page"),
                            (ConnectionError("curl: (56) Recv failure: Connection was reset"), "connection reset")):
        client = _client([answer], not_found=A.gateway_not_found)
        with pytest.raises(P.Blocked, match=message):
            client.get("http://x/a")
        assert len(client._session.calls) == 1 and client.slept == 0  # no retry, no waiting


def test_archived_draws_pick_the_most_complete_copy_and_link_point_captures():
    header = ["timestamp", "original", "statuscode", "mimetype", "length", "digest"]
    cdx = [header,
           ["20230206000000", "https://prod-scores-api.ausopen.com/event/220756/draws", "200", "application/json", "9", "A"],
           ["20230118000000", "https://prod-scores-api.ausopen.com/event/220756/draws", "200", "application/json", "9", "B"],
           ["20230119000000", "https://prod-scores-api.ausopen.com/event/220756/draws", "200", "application/json", "9", "B"],
           ["20260115000000", "https://prod-scores-api.ausopen.com/event/257391/draws", "200", "application/json", "9", "C"]]
    rows = A.draw_capture_rows(cdx)  # one per content; the current edition's draw, held live, is left out
    assert [(r["nid"], r["timestamp"]) for r in rows] == [("220756", "20230206000000"), ("220756", "20230118000000")]
    draw = load("ausopen_draw_WD.json")  # a finished draw: a win, a retirement and a walkover
    early = json.loads(json.dumps(draw))
    for match in early["matches"]:
        match["match_status"] = {"abbr": "SCH"}
    copies = [{"timestamp": "20260121000000", "payload": early}, {"timestamp": "20260120000000", "payload": draw}]
    assert A.finished_matches(draw) == 3 and A.draw_of_record(copies)["timestamp"] == "20260120000000"
    assert A.draw_year(draw, "20240101000000") == 2026 and A.draw_year({}, "20240101000000") == 2024
    captures = [{"record": "points", "match_status": "IPR", "points": "40", "record_key": "a"},
                {"record": "points", "match_status": "CMP", "points": "30", "record_key": "b"},
                {"record": "absent", "record_key": "c"}]
    assert A.best_points_capture(captures)["record_key"] == "b" and A.best_points_capture(captures[2:]) is None


def test_a_wayback_redirect_to_another_capture_is_recorded_not_followed():
    asked = "https://web.archive.org/web/20210214021224id_/https://prod-scores-api.ausopen.com/match-centre/MS403"
    moved = FakeResponse(302, b"", {"location": "https://web.archive.org/web/20210214061641id_/"
                                                "https://prod-scores-api.ausopen.com/match-centre/MS403"})
    moved.url = asked
    assert A.wayback_moved(moved) == "Wayback redirects this capture to capture 20210214061641 (not followed)"
    client = _client([moved], not_found=A.wayback_moved)
    assert client.get(asked).status_code == 302 and client._session.calls[0]["allow_redirects"] is False
    elsewhere = FakeResponse(302, b"", {"location": "https://web.archive.org/web/20210214061641id_/https://example.com/x"})
    elsewhere.url = asked
    robots = FakeResponse(302, b"", {"location": "/robots.txt"})
    robots.url = asked
    for answer in (elsewhere, robots):  # another URL, or not a capture: still a stop
        assert A.wayback_moved(answer) is None
        with pytest.raises(P.Blocked, match="redirect"):
            _client([answer], not_found=A.wayback_moved).get(asked)


def test_server_errors_and_timeouts_are_retried_then_left_to_fetch():
    client = _client([FakeResponse(503), TimeoutError("timed out"), FakeResponse(200, b'{"ok": 1}')])
    assert client.get("http://x/a").status_code == 200 and client.retried == 2 and client.slept == 15
    client = _client([FakeResponse(500)] * 4)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        client.get("http://x/a")
    client = _client([FakeResponse(200)])
    client.max_requests = 0
    with pytest.raises(P.BudgetExhausted):
        client.get("http://x/a")


def test_fetch_records_the_gateway_answer_as_absent_and_does_not_ask_again(tmp_path):
    receipts = C.Receipts("unit", root=tmp_path)
    dest = tmp_path / "unit" / "doc.json"
    client = _client([GATEWAY_403], not_found=A.gateway_not_found)
    first = P.fetch(client, "http://x/a", dest, receipts, name="a", absent=A.gateway_not_found)
    assert first["status"] == 403 and first["absent"].startswith("API Gateway") and not first.get("error")
    assert not dest.exists()
    again = P.fetch(client, "http://x/a", dest, receipts, name="a", absent=A.gateway_not_found)
    assert again.get("skipped") and len(client._session.calls) == 1


def test_failure_streak_counts_only_fresh_answers_without_documents():
    streak = F.FailureStreak(3)
    streak.note({"name": "a", "status": 404})
    streak.note({"name": "b", "status": 403, "absent": "gateway"})
    streak.note({"name": "c", "status": 404, "skipped": True})  # cached: ignored
    streak.note({"name": "d", "status": 200})  # a document: the count restarts
    streak.note({"name": "e", "error": "HTTP 500"})
    streak.note({"name": "f", "status": 404})
    with pytest.raises(F.Stopped, match="3 fetches in a row"):
        streak.note({"name": "g", "status": 404})
    F.FailureStreak(0).note({"name": "h", "status": 404})  # 0 never stops


def test_summaries_can_be_written_to_another_study(tmp_path):
    path = P.write_summary("x_summary.json", {"source": "x", "matches_selected": 3}, root=tmp_path / "study")
    assert path == tmp_path / "study" / "x_summary.json" and json.loads(path.read_text(encoding="utf-8"))["source"] == "x"
    line = json.loads((tmp_path / "study" / "runs.jsonl").read_text(encoding="utf-8").strip())
    assert line["source"] == "x" and line["matches_selected"] == 3
    assert F.STUDY_ROOT.as_posix().endswith("data/studies/official_point_feeds")


# score replay (verification) ----------------------------------------------------------
def _winners(payload):
    return [r["winner"] for r in A.point_rows(payload)]


def test_replay_reproduces_a_finished_doubles_match():
    payload = load("ausopen_match_centre_MD106.json")
    result = V.replay(_winners(payload), sets_to_win=2)
    assert result["sets"] == [(6, 3, None, None), (7, 6, 7, 2)] and result["winner"] == 1
    assert result["finished_at"] == 122
    meta = A.match_meta(payload, {})
    official = V.official_sets(meta["team1_score"], meta["team2_score"])
    assert official == [(6, 3, None, None), (7, 6, 7, 2)]
    assert V.score_differences(result, official, winner_team=1, complete=True) == []
    ends = [s["ends"] for s in result["per_point"]]
    assert ends.count("match") == 1 and ends.count("set") == 1 and ends.count("game") == 20
    flipped = _winners(payload)
    flipped[-1] = 2  # the last point to the other side: the tiebreak is no longer over
    different = V.score_differences(V.replay(flipped, 2), official, winner_team=1, complete=True)
    assert different and "do not finish the match" in different[0]


def test_replay_of_a_retirement_stops_inside_the_unfinished_set():
    payload = load("ausopen_match_centre_MQ122.json")
    result = V.replay(_winners(payload), sets_to_win=2)
    assert result["sets"] == [(6, 7, 9, 11)] and result["finished_at"] is None
    assert result["current_games"] == (0, 1)
    meta = A.match_meta(payload, {})
    official = V.official_sets(meta["team1_score"], meta["team2_score"])
    assert official == [(6, 7, 9, 11), (0, 1, None, None)]
    assert V.score_differences(result, official, winner_team=2, complete=False) == []
    assert V.score_differences(result, official[:1], winner_team=2, complete=False) == \
        ["the replay has set 2 at 0-1; the draw lists no such set"]


def test_games_score_readings():
    # MS701, set 4, game 12: team 2 serving at 5-6 (team 1 leads 6-5); team 1 wins the match 7-5 on the last point
    during = {"games_before": (6, 5), "games_after": (6, 5)}
    assert V.games_score_readings("5 - 6", winner=1, server=2, state=during) == ["server_first_after", "server_first_before"]
    last = {"games_before": (6, 5), "games_after": (7, 5)}
    assert V.games_score_readings("7 - 5", winner=1, server=2, state=last) == ["team_order_after", "winner_first_after"]
    assert V.games_score_readings(None, 1, 2, last) == ["missing"] and V.games_score_readings("0 - 0", 1, 2, last) == ["none"]


def test_replay_rules_deciding_set_tiebreak_and_score_text():
    # best of three at one set all: the deciding-set tiebreak runs to 10
    six_all = [1, 1, 1, 1, 2, 2, 2, 2] * 6  # twelve games, each side holding
    one_set = [1] * 24  # 6-0 to side 1
    lost_set = [2] * 24
    tiebreak = [1] * 7 + [2] * 3 + [1] * 3
    result = V.replay(one_set + lost_set + six_all + tiebreak, sets_to_win=2)
    assert result["sets"][:2] == [(6, 0, None, None), (0, 6, None, None)]
    assert result["sets"][2] == (7, 6, 10, 3) and result["winner"] == 1
    early = V.replay(one_set + [1] * 7, sets_to_win=2)  # a set, then a game and 40-0 in the next
    assert early["sets"] == [(6, 0, None, None)] and early["current_games"] == (1, 0)
    assert early["current_points"] == (3, 0) and early["finished_at"] is None
    assert V.score_text((1, 0), 1, False) == "15 - 0" and V.score_text((1, 0), 2, False) == "0 - 15"
    assert V.score_text((4, 3), 1, False) == "AD - 40" and V.score_text((3, 4), 1, False) == "40 - AD"
    assert V.score_text((3, 3), 2, False) == "40 - 40" and V.score_text((5, 2), 2, True) == "2 - 5"
    assert V.score_text((1, 0), None, False) is None
    assert V.rules("A") == {"sets_to_win": 3} and V.rules("B") == V.rules("C") == {"sets_to_win": 2}
    assert V.rules("D") == {"sets_to_win": 2, "no_ad": True, "match_tiebreak": True}


def test_replay_of_no_ad_games_and_a_match_tiebreak():
    deuce_then_one = [1, 1, 1, 2, 2, 2, 1]  # 40-40, then the deciding point
    assert V.replay(deuce_then_one, **V.rules("D"))["per_point"][-1]["ends"] == "game"
    assert V.replay(deuce_then_one, **V.rules("B"))["per_point"][-1]["ends"] is None  # advantage only
    set_to_1, set_to_2 = [1] * 24, [2] * 24
    result = V.replay(set_to_1 + set_to_2 + [1] * 9 + [2] * 7 + [1], **V.rules("D"))  # a 10-7 match tiebreak
    assert result["sets"] == [(6, 0, None, None), (0, 6, None, None), (1, 0, 10, 7)] and result["winner"] == 1
    assert V.official_sets("6 0 1(10)", "0 6 0(7)") == result["sets"]


def _staged(payload):
    """A match-centre document as the verification reads it back from the staged tables (strings)."""
    rows = [{k: P.s(v) for k, v in r.items()} for r in A.point_rows(payload)]
    meta = {k: P.s(v) for k, v in A.match_meta(payload, {}).items()}
    meta["scoring_format"] = payload["event"]["scoring_format"]
    return meta, V.pd.DataFrame(rows)


def test_the_checks_name_the_feed_defects_seen_in_2026():
    payload = load("ausopen_match_centre_MD106.json")
    meta, points = _staged(payload)
    clean: list = []
    result = V.check_replay("x", meta, points, clean)
    assert clean == [] and result["final_score_reproduced"] and result["serve_lines_contradicted"] == 0
    # a superseded game-ending entry left in place (as in MS159, MQ203, WD105)
    assert points.iloc[3]["type"] == "game"  # game 1 is won to love
    doubled = V.pd.concat([points.iloc[:4], points.iloc[3:4], points.iloc[4:]], ignore_index=True)
    found: list = []
    V.check_replay("x", meta, doubled, found)
    assert {"extra_game_end_entries", "final_score"} <= {f["check"] for f in found}
    # the first game's serve line naming the receiver (as in WQ159, MD121)
    swapped = points.copy()
    first_game = (swapped["set"] == "1") & (swapped["game"] == "1")
    swapped.loc[first_game, ["game_server_team", "point_server_team"]] = "2"
    found = []
    V.check_replay("x", meta, swapped, found)
    assert [f["check"] for f in found if f["check"] == "serve_line_contradicted"] == ["serve_line_contradicted"]
    # the match point typed as a serve line (as in MD109)
    typed = json.loads(json.dumps(payload))
    typed["commentary"][0]["type"] = "serve"
    found = []
    assert V.serve_lines_inside_games("x", typed, found) == 1 and found[0]["check"] == "serve_line_inside_game"
    assert V.timestamp_steps(V.pd.DataFrame({"timestamp": ["10", "70", "40", "90", None, "95"]})) == [30]
