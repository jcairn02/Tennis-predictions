"""IBM SlamTracker adapter (Wimbledon settings) and its checks, offline, on fixtures cut from real payloads
(Wimbledon 2025 MS 1101 and 1107, 2019 MD 3101, 2019 MS 1101; fetched 24 Sep 2026)."""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402
from src.ingest.point_sources import slamtracker as T  # noqa: E402
from src.ingest.point_sources.wimbledon import WIMBLEDON as W  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "official_point_feeds"))
import slamtracker_checks as K  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# parsing ------------------------------------------------------------------------------
def test_draw_refs_keep_every_field_and_write_scores():
    refs = T.draw_refs(load("wimbledon_draw_2025_MS.json"), 2025, "MS")
    assert [r.match_id for r in refs] == ["1101", "1107"] and {r.level for r in refs} == {"H"}
    first, retired = refs
    assert (first.year, first.event, first.listed_in) == (2025, "MS", ["draw"])
    assert first.entry["team1.displayNameA"] == "J. Sinner" and first.entry["team2.idA"] == "atpn0bg"
    assert first.entry["roundNameShort"] == "R1" and first.entry["statusCode"] == "D"
    assert first.entry["score_text"] == "6-4 6-3 6-0"
    assert retired.entry["status"] == "Retired" and retired.entry["score_text"] == "7-6(8) 3-1"  # the loser's tiebreak points
    assert isinstance(first.entry["scores.sets"], list)  # lists stay leaves (JSON text when staged)


def test_doubles_draw_keeps_both_players_of_a_team():
    ref = T.draw_refs(load("wimbledon_draw_2019_MD.json"), 2019, "MD")[0]
    assert ref.match_id == "3101"
    assert (ref.entry["team1.displayNameA"], ref.entry["team1.displayNameB"]) == ("L. Kubot", "M. Melo")


def test_history_rows_markers_are_not_points_and_keys_differ_by_year():
    new, old = T.history_rows(load("wimbledon_history_2025_1101.json")), T.history_rows(load("wimbledon_history_2019_1101.json"))
    assert [r["PointNumber"] for r in new] == ["0X", "0Y", "1", "2", "3", "153"]
    assert [T.is_point(r) for r in new] == [False, False, True, True, True, True]
    assert new[0]["EpochTimeStart"] == "0" and new[2]["EpochTimeStart"] == "1751371689"
    assert len(new[0]) == 57 and len(old[0]) == 52
    assert set(new[0]) - set(old[0]) == {"CourtIndicator", "TeamOrientStart", "TeamOrientEnd", "P1SetsWon", "P2SetsWon"}
    assert set(old[0]) <= set(new[0])
    assert T.history_rows({"odd": [{"PointNumber": "1"}]}) == [{"PointNumber": "1"}] and T.history_rows(None) == []


def test_statistics_rows_are_long_form_with_meta():
    rows = T.statistics_rows(load("wimbledon_stats_2025_1101.json"))
    by = {(r["section"], r["period"], r["team"], r["key"]): r["value"] for r in rows}
    assert by[("meta", None, None, "file.epoch")] == 1774539955 and by[("meta", None, None, "match_id")] == "1101"
    assert by[("meta", None, None, "statsLevel")] == "K" and by[("meta", None, None, "team1.displayNameA")] == "J. Sinner"
    assert by[("base_stats", "match", "team_1", "t_f_srv_in")] == 38
    assert by[("base_stats", "set_1", "team_1", "t_f_srv_in")] is not None
    assert by[("distance_run", "match", "team_1", None)] == ["1806.7 m", "5927.5 ft"]
    assert P.s(by[("distance_run", "match", "team_1", None)]) == '["1806.7 m", "5927.5 ft"]'


def test_extra_documents_stage_as_rows_or_paths():
    kind, rows = T.document_rows(load("wimbledon_livel2w_2025_1101.json"))
    assert kind == "rows" and [r["point_number"] for r in rows] == [1, 2, 3]
    assert rows[0]["player_one_tour_id"] == "atps0ag" and rows[0]["created_epoch"] == 1751371714
    kind, rows = T.document_rows(load("wimbledon_tz_2025_1101.json"))
    paths = {r["path"]: r["value"] for r in rows}
    assert kind == "paths" and paths["players.p1.last_name"] == "Sinner"
    assert paths["insights.in_attack.match.set1.p1"] == 30 and paths["insights.in_attack.match.set4"] is None


def test_flatten_and_set_scores_edge_cases():
    assert T.flatten({"a": {"b": 1, "c": {}}, "d": [1]}) == {"a.b": 1, "a.c": {}, "d": [1]}
    assert T.flatten(5) == {"value": 5}
    six_seven = [[{"score": 6, "scoreDisplay": "6", "tiebreakDisplay": "5"}, {"score": 7, "scoreDisplay": "7", "tiebreakDisplay": "7"}]]
    assert T.set_scores(six_seven) == "6-7(5)"
    assert T.set_scores([[{"score": 7, "scoreDisplay": "7", "tiebreakDisplay": "7"}, {"score": 5, "scoreDisplay": "5"}]]) == "7-5"
    assert T.set_scores(None) is None


# settings -----------------------------------------------------------------------------
def test_wimbledon_urls_hosts_and_feed_filters():
    history, stats = W.feed("history"), W.feed("stats")
    assert W.url(2025, history.path, history, id="1101") == \
        "https://2025.wimbledon.com/en_GB/scores/feeds/2025/slamtracker/history/1101C.json"
    assert W.url(2019, stats.path, stats, id="12101") == "https://2025.wimbledon.com/en_GB/scores/feeds/2019/matches/complete/12101.json"
    assert W.url(2026, history.path, history, id="1101").startswith("https://www.wimbledon.com/en_GB/scores/feeds/2026/")
    l2w, tz = W.feed("livel2w"), W.feed("tz")
    assert W.url(2025, l2w.path, l2w, id="1101") == "https://2025.wimbledon.com/clouddata/livel2w/2025/1101C.json"
    assert l2w.applies(2025, "MS") and l2w.applies(2026, "LS") and not l2w.applies(2024, "MS") and not l2w.applies(2025, "QS")
    assert tz.applies(2024, "LS") and not tz.applies(2026, "MS") and not tz.applies(2025, "MD")
    assert history.applies(2019, "RS", "S") and history.core and not l2w.core
    assert not T.Feed("x", "/x", levels=frozenset({"H"})).applies(2025, "MQ", "S")
    assert T.raw_dest(W, 2025, "history", "https://h/x/1101C.json").as_posix().endswith("wimbledon/2025/history/1101C.json.gz")
    assert "draws/2026/MS" in W.blocked and "draws/2026/LS" in W.blocked and 2026 in W.day_lists
    assert W.years == [2019, 2021, 2022, 2023, 2024, 2025, 2026]


def test_plan_puts_matches_missing_from_sackmann_first_newest_year_first():
    refs = [T.MatchRef(2019, "MS", "1101"), T.MatchRef(2019, "QS", "11101"), T.MatchRef(2025, "MS", "1101"),
            T.MatchRef(2019, "MS", "1102")]
    held = {2019: {"1101", "1102"}}
    order = [(h, y, e, [r.match_id for r in g]) for h, y, e, g in T.plan_groups(W, refs, held, "new-first")]
    assert order == [(False, 2025, "MS", ["1101"]), (False, 2019, "QS", ["11101"]), (True, 2019, "MS", ["1101", "1102"])]
    assert [(y, e) for _, y, e, _ in T.plan_groups(W, refs, held, "calendar")] == [(2019, "MS"), (2019, "QS"), (2025, "MS")]


def test_event_days_name_day_files_and_filter_by_event():
    payload = load("wimbledon_eventDays_2026.json")
    assert T.event_days(payload) == [1, 8, 21]
    assert T.event_days(payload, ["MS"]) == [8, 21] and T.event_days(payload, ["QS"]) == [1]
    assert T.event_days(payload, ["XX"]) == [] and T.event_days(None) == []


def test_day_lists_merge_with_draws(tmp_path):
    receipts = C.Receipts("unit", root=tmp_path)
    for name, fixture in (("days/2026/day_8", "wimbledon_day_2026_8.json"), ("draws/2026/MS", "wimbledon_draw_2025_MS.json")):
        receipts.record({"name": name, "status": 200, "dest": str(FIXTURES / fixture)})
    site = T.Site("unit", "unit", "wimbledon", "en_GB", {2026: "https://h"}, ("MS", "LS"), (), day_lists=frozenset({2026}))
    days = T.day_refs(site, receipts, 2026)
    assert [(r.event, r.match_id, r.listed_in) for r in days] == [("MS", "1101", ["days"]), ("LS", "2101", ["days"])]
    assert days[0].entry["day_file"] == "days/2026/day_8" and days[0].level == "H"
    listed = {r.match_id: r for r in T.listed_matches(site, receipts, [2026], ["MS", "LS"])}
    assert listed["1101"].listed_in == ["draw", "days"] and listed["1101"].entry["day_file"] == "days/2026/day_8"
    assert listed["1107"].listed_in == ["draw"] and listed["2101"].listed_in == ["days"]
    assert [r.match_id for r in T.listed_matches(site, receipts, [2026], ["LS"])] == ["2101"]


# fetching rules -------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status, body=b"", headers=None, url="https://h/x"):
        self.status_code, self.content, self.url = status, body, url
        self.headers = {"content-type": "application/json", **(headers or {})}


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout=None, allow_redirects=True, headers=None):
        self.calls.append((url, allow_redirects))
        return self.responses.pop(0)


def feed_client(responses):
    client = T.make_client(W, min_interval=0.0, jitter=0.0, max_requests=None)
    client._session = FakeSession(responses)
    return client


def test_notfound_redirect_is_an_answer_other_redirects_and_403_are_blocks():
    absolute = FakeResponse(302, headers={"location": "https://2025.wimbledon.com/notfound"})
    assert T.notfound_redirect(absolute) == "HTTP 302 redirect to https://2025.wimbledon.com/notfound"
    assert T.notfound_redirect(FakeResponse(301, headers={"location": "/notfound/"})) is not None
    assert T.notfound_redirect(FakeResponse(302, headers={"location": "/robots.txt"})) is None
    assert T.notfound_redirect(FakeResponse(200)) is None
    client = feed_client([absolute])
    assert client.get("https://h/a").status_code == 302 and client._session.calls == [("https://h/a", False)]
    with pytest.raises(P.Blocked, match="robots.txt"):
        feed_client([FakeResponse(302, headers={"location": "https://www.wimbledon.com/robots.txt"})]).get("https://h/b")
    with pytest.raises(P.Blocked, match="HTTP 403"):
        feed_client([FakeResponse(403, b"<Error><Code>AccessDenied</Code></Error>", {"content-type": "application/xml"})]).get("https://h/c")


def test_fetch_records_notfound_as_absent_and_never_asks_again(tmp_path, monkeypatch):
    receipts = C.Receipts("unit", root=tmp_path)
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    site = T.Site("unit", "unit", "wimbledon", "en_GB", {2025: "https://h"}, ("MS",), (T.history_feed(),))
    client = feed_client([FakeResponse(302, headers={"location": "https://h/notfound"}),
                          FakeResponse(200, json.dumps(load("wimbledon_history_2025_1101.json")).encode())])
    first = T.fetch_match_feed(client, receipts, site, site.feed("history"), 2025, "1101", event="MS")
    assert first["absent"].startswith("HTTP 302") and T.outcome(first) == "absent" and not Path(first["dest"]).exists()
    again = T.fetch_match_feed(client, receipts, site, site.feed("history"), 2025, "1101", event="MS")
    assert again.get("skipped") and len(client._session.calls) == 1  # a terminal answer is not asked again
    other = T.fetch_match_feed(client, receipts, site, site.feed("history"), 2025, "1102", event="MS")
    assert T.outcome(other) == "ok" and other["compressed"] and (tmp_path / "unit" / "2025" / "history" / "1102C.json.gz").exists()
    assert T.history_rows(T.cached_json(other))[0]["PointNumber"] == "0X"


def test_non_json_answers_describe_themselves():
    assert T.json_body(b'{"a": 1}') is None and T.json_body(b"  [1]") is None
    assert T.json_body(b"") == "response is not JSON: 0 bytes, starting b''"
    assert T.json_body(b"<html>x</html>").startswith("response is not JSON: 14 bytes, starting b'<html>")


def test_a_saved_document_that_does_not_parse_is_read_as_none_and_recorded(tmp_path):
    import gzip

    bad = tmp_path / "2701.json.gz"
    bad.write_bytes(gzip.compress(b'{"match_id": 2701, "p1_id": "wta324166", "p2_id": "wta320760"", "x": 1}'))
    receipt = {"name": "prematch_l2w/2025/2701", "status": 200, "dest": bad.as_posix()}
    T.UNREADABLE.pop(bad.as_posix(), None)
    assert T.cached_json(receipt) is None and T.is_unreadable(receipt)
    assert T.UNREADABLE[bad.as_posix()][0] == "prematch_l2w/2025/2701"
    assert "JSONDecodeError" in T.UNREADABLE[bad.as_posix()][1]
    assert not T.is_unreadable({"name": "x", "status": 200, "dest": "elsewhere"}) and not T.is_unreadable(None)


def test_staging_goes_on_past_an_unreadable_document(tmp_path, monkeypatch):
    import gzip

    import pyarrow.parquet as pq

    monkeypatch.setattr(P, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(P, "DUMP_ROOT", tmp_path / "dump")
    site = T.Site("unit", "unit", "unit", "en_GB", {2025: "https://h"}, ("MS",), (T.history_feed(), T.stats_feed()))
    receipts = C.Receipts("unit", root=tmp_path / "raw")
    files = {"draws/2025/MS": ("draws", "MS.json.gz", json.dumps(load("wimbledon_draw_2025_MS.json")).encode()),
             "history/2025/1101": ("history", "1101C.json.gz", json.dumps(load("wimbledon_history_2025_1101.json")).encode()),
             "history/2025/1107": ("history", "1107C.json.gz", b'[{"PointNumber": "0X""}]')}  # saved, but broken
    for name, (folder, file, body) in files.items():
        dest = T.P.raw_path("unit", "2025", folder, file)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(gzip.compress(body))
        receipts.record({"name": name, "status": 200, "dest": P.rel(dest)})
    out = T.stage(site, receipts, years=[2025])
    assert out["points"]["rows"] == 6 and list(out["unreadable"]) == ["history/2025/1107"]
    rows = {r["match_id"]: r for r in pq.read_table(tmp_path / "dump" / "unit" / "matches.parquet").to_pylist()}
    assert rows["1101"]["history_outcome"] == "ok" and rows["1101"]["history_points"] == "4"
    assert rows["1107"]["history_outcome"] == "unreadable" and rows["1107"]["history_points"] is None
    assert rows["1101"]["stats_outcome"] == "not requested"


def test_blocked_names_are_never_requested():
    client = feed_client([])
    receipt = T.fetch_draw(client, None, W, 2026, "MS")
    assert receipt["blocked"].startswith("302 to /robots.txt") and receipt["skipped"] and client._session.calls == []
    assert T.outcome(receipt) == "blocked" and T.outcome(None) == "not requested"
    assert T.outcome({"status": 404}) == "absent" and T.outcome({"status": 200}) == "ok" and T.outcome({"error": "x"}) == "error"


def test_failure_streak_counts_documentless_fetches():
    streak = F.FailureStreak(2)
    streak.note({"status": 404})
    streak.note({"status": 200})
    streak.note({"skipped": True, "status": 404})
    streak.note({"absent": "HTTP 302"})
    with pytest.raises(F.Stopped):
        streak.note({"error": "HTTP 500"})


# checks -------------------------------------------------------------------------------
def test_sentences_parse_into_stroke_and_outcome():
    s = K.parse_sentence("L. Nardi loses the point with a forehand forced error")
    assert (s["actor"], s["situation"], s["stroke"], s["side"], s["stroke_type"], s["outcome"], s["actor_won"]) == \
        ("L. Nardi", "loses the point", "forehand", "forehand", "groundstroke", "forced error", False)
    s = K.parse_sentence("J. Sinner wins the match with a service winner")
    assert (s["stroke"], s["outcome"], s["actor_won"]) == ("serve", "service winner", True)
    s = K.parse_sentence("A. De Minaur saves the break point with a backhand volley winner")
    assert (s["actor"], s["stroke"], s["stroke_type"], s["outcome"]) == ("A. De Minaur", "backhand volley", "volley", "winner")
    s = K.parse_sentence("N. Djokovic fails to convert the break point with a forehand unforced error")
    assert (s["situation"], s["outcome"], s["actor_won"]) == ("fails to convert the break point", "unforced error", False)
    assert K.parse_sentence("N. Djokovic loses the point with a double fault")["outcome"] == "double fault"
    assert K.parse_sentence("J. Sinner wins the game with an ace")["stroke"] == "serve"
    assert K.parse_sentence("Players arrive on court.") is None and K.parse_sentence(None) is None
    assert K.parse_sentence("J. Sinner wins the point with a forehand miracle") is None
    assert K.parse_sentence("S. Hsieh/J. Ostapenko wins the point") is None  # doubles sentences mostly name no shot


def test_situation_is_read_with_or_without_a_shot():
    s = K.parse_situation("S. Hsieh/J. Ostapenko wins the point")
    assert (s["actor"], s["situation"], s["actor_won"]) == ("S. Hsieh/J. Ostapenko", "wins the point", True)
    s = K.parse_situation("R. Hijikata/D. Pel saves the break point.")
    assert (s["actor"], s["situation"]) == ("R. Hijikata/D. Pel", "saves the break point")
    s = K.parse_situation("L. Nardi loses the point with a forehand forced error")
    assert (s["actor"], s["situation"], s["actor_won"]) == ("L. Nardi", "loses the point", False)
    assert K.parse_situation("J. Sinner wins the point with a forehand")["situation"] == "wins the point"
    assert K.parse_situation("Players warming up.") is None and K.parse_situation("") is None


def test_sentence_checks_on_fixture_points():
    rows = [r for r in load("wimbledon_history_2025_1101.json") if T.is_point(r)]
    names = {1: {"J. Sinner", "Sinner"}, 2: {"L. Nardi", "Nardi"}}
    for row in rows:
        parsed = K.parse_sentence(row["Sentence"])
        side = K.actor_side(parsed["actor"], names)
        implied = side if parsed["actor_won"] else 3 - side
        assert implied == int(row["PointWinner"])


def test_doubles_teams_resolve_as_the_sentences_write_them():
    ref = T.draw_refs(load("wimbledon_draw_2019_MD.json"), 2019, "MD")[0]
    names = K.side_names({f"entry.{k}": v for k, v in ref.entry.items()})
    assert "L. Kubot/M. Melo" in names[1] and "Kubot/Melo" in names[1] and "M. Melo" in names[1]
    assert K.actor_side("L. Kubot/M. Melo", names) == 1
    oconnell = {1: {"C. O'Connell", "O'Connell"}, 2: {"T. Machac", "Machac"}}
    assert K.actor_side("C.O'Connell", oconnell) == 1 and K.actor_side("T Machac", oconnell) == 2  # 2021 QS 11316's slip
    assert K.actor_side("C. O''Connell", oconnell) == 1 and K.actor_side("C. O’Connell", oconnell) == 1  # US Open 2026
    assert K.actor_side("Someone Else", oconnell) is None
    singles = K.side_names({"entry.team1.displayNameA": "J. Sinner", "entry.team1.lastNameA": "Sinner",
                            "entry.team2.displayNameA": "L. Nardi", "entry.team1.displayNameB": None})
    assert singles == {1: {"J. Sinner", "Sinner"}, 2: {"L. Nardi"}}


def test_l2w_files_are_live_or_replays():
    ends = ["1751371695", "1751378181"]  # 2025 MS 1101: first and last point
    assert K.l2w_kind(["1751371714", "1751378200"], ends) == "live"
    assert K.l2w_kind(["1784850360", "1784850480"], ends) == "replay"  # written a year later
    assert K.l2w_kind([], ends) == "unknown" and K.l2w_kind(["1751371714"], ["0"]) == "unknown"


def test_result_is_replayed_from_each_sets_last_point():
    def pt(set_no, winner, g1, g2, n):
        return {"SetNo": set_no, "PointWinner": winner, "P1GamesWon": g1, "P2GamesWon": g2, "EpochTimeStart": str(n),
                "EpochTimeEnd": str(n + 5), "P1Score": "0", "P2Score": "0", "Sentence": f"p{n}", "SetWinner": "0"}
    match = [pt("1", "1", 5, 4, 1), pt("1", "1", 6, 4, 2), pt("2", "2", 3, 5, 3), pt("2", "1", 3, 5, 4),  # counter lags
             pt("3", "1", 5, 2, 5), dict(pt("3", "1", 5, 2, 6), Sentence="X wins the match with an ace")]  # and at match point
    got = K.result_from_points(match)
    assert (got["sets_1"], got["sets_2"], got["sets_played"], got["winner"]) == (3, 0, 3, "1")  # SetWinner flags unused
    assert got["ends_on_match_point"]
    early = match[:5]  # stops at 5-2 in set 3 (2021 LS 2128 stops mid-set): the unfinished set counts for nobody
    assert (K.result_from_points(early)["sets_1"], K.result_from_points(early)["ends_on_match_point"]) == (2, False)
    repeated = match[:2] + [dict(match[1])] + match[2:]  # 2025 MS 1201 repeats one point row
    assert K.result_from_points(repeated)["repeated_rows"] == 1
    assert K.set_complete(7, 6) and K.set_complete(12, 13) and K.set_complete("6", "3") and not K.set_complete(5, 3)
    assert not K.set_complete(None, 2)
    listed = [[{"score": 4}, {"score": 6}], [{"score": 6}, {"score": 3}], [{"score": 12}, {"score": 13}]]
    assert K.sets_from_score(listed) == (1, 2, 3)  # 2021 MD 3110's score, whose listing says 1-1


def test_first_difference_and_epoch_problems():
    assert K.first_difference(["1", "2"], ["1", "2"]) is None
    assert K.first_difference(["1", "2", "1"], ["1", "1", "1"]) == 1 and K.first_difference(["1"], ["1", "2"]) == 1
    t = 1_751_371_689  # 2025 MS 1101, point 1
    at = lambda *xs: [str(t + x) for x in xs]
    ok = K.epoch_problems(at(10, 20, 30), at(15, 25, 35))
    assert ok["filled"] and ok["in_order"] and ok["overlaps_previous"] == 0
    bad = K.epoch_problems([at(10)[0], "0", at(5)[0]], at(15, 25, 12))
    assert bad["start_missing"] == 1 and not bad["filled"] and bad["start_backwards"] == 1 and bad["end_backwards"] == 1
    assert K.epoch_problems(at(10, 12), at(14, 16))["overlaps_previous"] == 1
    assert K.epoch_problems(["10", "20"], ["15", "25"])["start_implausible"] == 2  # not Unix times of this century
    # Wimbledon 2025 MS 1113: +86,446 s mid-set (the spurious day), then the real overnight suspension of 67,507 s
    jumped = K.epoch_problems(["1751393403", "1751479843", "1751484871"], ["1751393443", "1751479889", "1751552378"])
    assert jumped["day_jumps"] == 1 and jumped["first_day_jump_at_point"] == 2 and jumped["gaps_over_1h"] == 1
    assert jumped["in_order"]  # the order check alone does not see it
    assert K.listing_bin(86_430) == "last point a day after the listing" and K.listing_bin(-30) == "within 10 minutes"
    assert K.listing_bin(-848_292).startswith("listing later") and K.listing_bin(16_563).startswith("last point later")
    assert jumped["last_gap_s"] == 1751552378 - 1751479889
    # Wimbledon 2026 MS 1127 from point 202: EpochTimeEnd is no Unix time; it is not filled and not ordered
    broken = K.epoch_problems(["1782826345", "1782826397"], ["1782826300", "93089"])
    assert (broken["end_implausible"], broken["start_implausible"], broken["filled"], broken["end_backwards"]) == (1, 0, False, 0)
    # a whole-hour offset is the listing's (US Open 2026: 5 h) only when the history's clock is consistent
    assert K.listing_bin(17_990).startswith("listing 5 h early") and K.listing_bin(17_990, consistent=False).startswith("last point later")
    assert K.listing_bin(83_120, consistent=False).startswith("last point later")  # Wimbledon 2024 MS 1138 steps back
    assert K.listing_bin(16_563).startswith("last point later")  # the 2025 final: 4 h 36 min, not whole hours
