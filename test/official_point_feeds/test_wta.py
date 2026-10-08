"""The WTA adapter and the verification's replays (offline).

Fixtures are cut from payloads fetched on 24 Sep 2026: calendar pages trimmed to a few editions (2020 with the
pre-2021 tier names and a cancelled event, 2024 with the United Cup); the Washington 2024 match list trimmed to
eight matches (finals, retirements, walkovers, qualifying; BinPacketBase64 emptied); whole point-by-point, stats
and advanced-stats documents for its singles final LS001 and point-by-point for its doubles final LD001; and seven
event logs keeping their first three records whole and, after them, only points, aces, faults and corrections,
with only the fields the parsers read. The logs: 1045/2024/LS001 (2024 conventions), 1002/2020/LS001 (a tiebreak
written with its first server first), 2026/2021/LS001 (a tiebreak written server first), 894/2025/LD006 (a match
tiebreak written with the next point's server first), 808/2022/LS001 (a tiebreak whose points are all written
"0-0"), 1003/2022/LS001 (a correction that replaces a point) and 709/2020/LD029 (doubles with no-ad deciding
points). Their listing rows are in wta_listing_rows.json.
"""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "official_point_feeds"))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import feeds as F  # noqa: E402
from src.ingest.point_sources import wta as W  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402
import verify_wta as V  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def listing() -> dict:
    return {m["MatchID"]: m for m in load("wta_matches_1045_2024.json")["matches"]}


def row(key: str) -> dict:
    return load("wta_listing_rows.json")[key]


# calendar and match list ------------------------------------------------------------
def test_tiers_map_old_and_new_level_names():
    tiers20 = [(e["level"], W.tier_of(e)) for e in load("wta_calendar_2020.json")["content"]]
    assert tiers20[:6] == [("International", "250"), ("Premier 5", "1000"), ("Premier", "500"), ("125K", "125"),
                           ("Grand Slam", "slam"), ("Finals", "finals")]
    tiers24 = [W.tier_of(e) for e in load("wta_calendar_2024.json")["content"]]
    assert tiers24 == ["team", "125", "500", "slam", "500"]  # the United Cup is "team", whatever its level


def test_editions_are_keyed_by_group_and_year_and_the_sample_skips_cancelled_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    folder = tmp_path / "wta" / "calendar"
    folder.mkdir(parents=True)
    for name in ("wta_calendar_2020.json", "wta_calendar_2024.json"):
        year = name[13:17]
        (folder / f"{year}_0.json").write_text((FIXTURES / name).read_text(encoding="utf-8"), encoding="utf-8")
    editions = W.load_editions([2020, 2024])
    assert len(editions) == len({(e["tournament_id"], e["year"]) for e in editions}) == 12
    assert W.calendar_years() == [2020, 2024]  # a run re-stages every year held, not only its own
    washington = next(e for e in editions if e["tournament_id"] == "1045")
    assert (washington["tier"], washington["singles_draw_size"], washington["status"]) == ("500", 28, "past")
    cancelled = [e for e in editions if e["year"] == 2020 and not e["singles_draw_size"]]
    assert len(cancelled) == 1
    cells = dict(W.sample_cells(editions))
    candidates = [e for group in cells.values() for e in group]
    assert cancelled[0] not in candidates
    assert any(e["tier"] == "team" for e in candidates)  # the United Cup lists no draw but is kept
    assert dict(W.sample_cells(editions)) == cells  # seeded: the same order every time


def test_draws_walkovers_and_played_matches():
    m = listing()
    assert {k: W.draw_of(v) for k, v in m.items()} == {
        "LS001": "main_singles", "LS002": "main_singles", "LS010": "main_singles", "LS013": "main_singles",
        "RS004": "qual_singles", "RS005": "qual_singles", "LD001": "main_doubles", "LD005": "main_doubles"}
    assert W.is_walkover(m["LS010"]) and W.is_walkover(m["LD005"]) and not W.is_walkover(m["LS013"])
    assert not W.is_played(m["LS010"]) and W.is_played(m["LS013"]) and W.is_played(m["RS004"])


def test_sample_matches_take_the_final_another_and_one_per_draw():
    m = list(listing().values())
    edition = {"tournament_id": "1045", "year": 2024, "tier": "500"}
    picks = W.sample_matches(edition, m)
    assert [p[0]["MatchID"] for p in picks][:1] == ["LS001"]
    assert picks[0][1] == W.ENDPOINTS and picks[1][1] == W.ENDPOINTS
    assert picks[1][0]["MatchID"] in ("LS002", "LS013")  # never the walkover LS010
    assert {W.draw_of(p[0]) for p in picks[2:]} == {"qual_singles", "main_doubles"}
    assert all(p[1] == W.POINT_ENDPOINTS for p in picks[2:])
    assert W.sample_matches(edition, m) == picks
    light = W.sample_matches({**edition, "tier": "slam"}, m)
    assert [p[1] for p in light] == [W.POINT_ENDPOINTS + ("stats",), W.POINT_ENDPOINTS]
    assert W.sample_matches(edition, [m_ for m_ in m if not W.is_played(m_)]) == []


# documents --------------------------------------------------------------------------
def test_point_rows_keep_the_feed_and_the_set_result():
    rows = W.point_rows("1045", 2024, "LS001", load("wta_pbp_1045_2024_LS001.json"))
    assert len(rows) == 181 and [r["point_number"] for r in rows] == list(range(1, 182))
    first = rows[0]
    assert (first["set"], first["game"], first["server"], first["point_winner"]) == (1, 1, "B", "A")
    assert (first["game_score_a"], first["game_score_b"], first["timestamp"]) == ("15", "0", "2024-08-04T18:38:25Z")
    assert (first["set_score_a"], first["set_score_b"]) == (1, 6)  # the set's final score, from the first point on
    doubles = W.point_rows("1045", 2024, "LD001", load("wta_pbp_1045_2024_LD001.json"))
    assert all(r["server"] == "" for r in doubles)
    assert (doubles[76]["game_score_a"], doubles[76]["game_score_b"], doubles[76]["set_tb_a"]) == ("7", "0", 7)


def test_event_stats_and_advanced_rows():
    events = load("wta_events_1045_2024_LS001.json")
    rows = W.event_rows("1045", 2024, "LS001", events)
    assert len(rows) == len(events["Events"])
    assert (rows[0]["name"], rows[0]["reason"], rows[0]["umpire_id"]) == ("StateIndicator", "OnCourt", "NOU6759135")
    assert isinstance(rows[0]["attributes"], dict)
    stats = W.stats_rows("1045", 2024, "LS001", load("wta_stats_1045_2024_LS001.json"))
    assert [r["setnum"] for r in stats] == [0, 1, 2, 3] and stats[0]["acesb"] == 5
    adv = W.long_rows("1045", 2024, "LS001", load("wta_advanced_1045_2024_LS001.json"))
    paths = {r["path"]: r["value"] for r in adv}
    assert paths["teamA.matchTotal.shotStats.aces"] == 2 and paths["status"] == "Match Finished"
    assert "teamA.sets[0].serveStats.faultReasons.net" in paths
    assert W.has_points(load("wta_pbp_1045_2024_LS001.json")) and W.has_points(events)
    assert not W.has_points({"points": []}) and not W.has_points({"Events": []}) and not W.has_points([])


# fetching rules ---------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status, body=b""):
        self.status_code = status
        self.content = body
        self.headers = {"content-type": "application/json"}
        self.url = "http://x"


class FakeClient:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def get(self, url, headers=None):
        self.calls += 1
        return self.answers.pop(0)


def test_documents_are_gzipped_404s_are_final_and_statuses_read_back(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)
    client = FakeClient([FakeResponse(200, b'{"points": [1]}'), FakeResponse(404)])
    ok = W.fetch_endpoint(client, receipts, "1045", 2024, "LS001", "point-by-point", refresh=False)
    gone = W.fetch_endpoint(client, receipts, "1045", 2024, "LS001", "win-probability-momentum", refresh=False)
    assert ok["status"] == 200 and W.endpoint_dest("1045", 2024, "LS001", "point-by-point").name == "point-by-point.json.gz"
    assert P.read_json(W.endpoint_dest("1045", 2024, "LS001", "point-by-point")) == {"points": [1]}
    assert gone["status"] == 404 and client.calls == 2
    again = W.fetch_endpoint(client, receipts, "1045", 2024, "LS001", "win-probability-momentum", refresh=False)
    assert again.get("skipped") and client.calls == 2
    assert W.endpoint_status(receipts, "1045", 2024, "LS001", "point-by-point") == "200"
    assert W.endpoint_status(receipts, "1045", 2024, "LS001", "win-probability-momentum") == "404"
    assert W.endpoint_status(receipts, "1045", 2024, "LS001", "stats") is None


def test_a_receipt_line_cut_short_is_skipped_and_the_next_one_starts_fresh(tmp_path):
    path = tmp_path / "unit" / "_receipts.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text('{"name": "a", "status": 200}\n{"name": "b", "sta', encoding="utf-8")  # a write cut short
    receipts = C.Receipts("unit", root=tmp_path)
    assert receipts.unreadable_lines == 1 and receipts.get("a") == {"name": "a", "status": 200}
    assert receipts.get("b") is None  # its fetch is simply done again
    receipts.record({"name": "c", "status": 404})
    again = C.Receipts("unit", root=tmp_path)
    assert again.get("c") == {"name": "c", "status": 404} and again.unreadable_lines == 1


def test_a_document_is_written_whole_then_renamed(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("wta", root=tmp_path)
    client = FakeClient([FakeResponse(200, b'{"Events": []}')])
    W.fetch_endpoint(client, receipts, "1045", 2024, "LS001", "events", refresh=False)
    folder = W.endpoint_dest("1045", 2024, "LS001", "events").parent
    assert [p.name for p in folder.iterdir()] == ["events.json.gz"]  # no .part left behind


def test_only_an_approved_batch_runs_and_it_fills_the_selection(monkeypatch):
    parser = __import__("argparse").ArgumentParser()
    W.add_arguments(parser)
    args = parser.parse_args(["--batch", "B1", "--years", "2021", "--max-requests", "10"])
    batch = W.apply_batch(args)
    assert batch["status"] == "approved"
    assert (args.years, args.endpoints, args.tiers, args.draws) == ("2021", "events", "1000,500,250,125,finals", None)
    monkeypatch.setattr(W, "BATCHES", W.BATCHES + [{**W.BATCHES[-1], "id": "BX", "status": "planned",
                                                    "approved_on": None}])
    with pytest.raises(SystemExit):
        W.apply_batch(parser.parse_args(["--batch", "BX", "--max-requests", "10"]))
    with pytest.raises(SystemExit):
        W.apply_batch(parser.parse_args(["--batch", "B1", "--years", "2018", "--max-requests", "10"]))
    with pytest.raises(SystemExit):
        W.apply_batch(parser.parse_args(["--batch", "B1", "--sample", "--max-requests", "10"]))
    covered = {e for b in W.BATCHES for e in b["endpoints"]}
    assert covered == set(W.ENDPOINTS)  # the plan scopes every endpoint


def test_a_queued_run_waits_and_does_not_follow_a_block(tmp_path):
    summary = tmp_path / "wta_summary.json"
    assert W.previous_hard_stop(summary) is None  # no earlier run
    for stopped, hard in ((None, False), ("BudgetExhausted: request budget of 40000 used up", False),
                          ("Blocked: HTTP 429 (rate limited) for https://x", True),
                          ("TooManyAbsences: 150 fetches in a row brought no document", True),
                          ("TooManyErrors: 5 fetches in a row brought no document", True)):
        summary.write_text(json.dumps({"stopped": stopped}), encoding="utf-8")
        assert bool(W.previous_hard_stop(summary)) is hard, stopped
    started = __import__("time").time()
    W.wait_for_process(2 ** 31 - 1)  # no such process: returns at once
    assert __import__("time").time() - started < 5
    assert next(b for b in W.BATCHES if b["id"] == "B2")["status"] == "approved"  # owner, 25 Sep 2026
    later = [b for b in W.BATCHES if b["id"] not in ("B1", "B2")]
    assert {(b["status"], b["approved_on"]) for b in later} == {("approved", "2026-09-29")}  # owner: "B3 etc..."


def test_each_batch_sets_its_own_absence_limit_unless_the_command_does():
    parser = __import__("argparse").ArgumentParser()
    W.add_arguments(parser)

    def limit(*argv):
        args = parser.parse_args([*argv, "--max-requests", "10"])
        W.apply_batch(args)
        return args.stop_after_absences

    assert limit("--batch", "B1") == 150 and limit("--batch", "B3") == 1500
    assert limit("--batch", "B8") == 0  # off: months without point-by-point
    assert limit("--batch", "B8", "--years", "2022-2024", "--stop-after-absences", "400") == 400
    assert limit("--years", "2024") == W.ABSENCES_DEFAULT  # a hand-picked slice
    assert all(isinstance(b["absences"], int) and b["absences"] >= 0 for b in W.BATCHES)
    with pytest.raises(F.Stopped):  # the limit reaches the streak: 0 never stops, anything else does
        streak = F.FailureStreak(limit("--batch", "B4"))
        for _ in range(400):
            W.note(F.FailureStreak(5), streak, {"name": "x", "status": 404})
    streak = F.FailureStreak(limit("--batch", "B8"))
    for _ in range(5000):
        W.note(F.FailureStreak(5), streak, {"name": "x", "status": 404})


def test_errors_pause_a_run_but_absences_stop_it():
    errors, absences = F.FailureStreak(1), F.FailureStreak(1)
    with pytest.raises(W.TooManyErrors):
        W.note(errors, absences, {"name": "x", "error": "ConnectionError"})
    with pytest.raises(W.TooManyAbsences):
        W.note(F.FailureStreak(1), absences, {"name": "x", "status": 404})


def test_404s_count_as_absences_not_errors():
    errors, absences = F.FailureStreak(2), F.FailureStreak(3)
    for _ in range(2):
        W.note(errors, absences, {"name": "x", "status": 404})
    assert (errors.count, absences.count) == (0, 2)
    W.note(errors, absences, {"name": "x", "status": 200})
    assert (errors.count, absences.count) == (0, 0)
    W.note(errors, absences, {"name": "x", "status": 404, "skipped": True})  # cached answers do not count
    assert absences.count == 0
    W.note(errors, absences, {"name": "x", "error": "HTTP 500"})
    with pytest.raises(F.Stopped):
        W.note(errors, absences, {"name": "x", "error": "HTTP 500"})
    for _ in range(2):
        W.note(errors, absences, {"name": "x", "status": 404})
    with pytest.raises(F.Stopped):
        W.note(errors, absences, {"name": "x", "status": 404})


def test_every_networked_run_needs_a_budget_and_years():
    parser = __import__("argparse").ArgumentParser()
    W.add_arguments(parser)
    with pytest.raises(SystemExit):
        W.run(parser.parse_args(["--years", "2024"]))
    with pytest.raises(SystemExit):
        W.run(parser.parse_args(["--max-requests", "5"]))
    assert W.parse_years("2020-2022,2026") == [2020, 2021, 2022, 2026] and W.parse_years(None) == []


# verification: point-by-point -------------------------------------------------------
def test_derived_winners_correct_the_point_winner_field():
    rows = W.point_rows("1045", 2024, "LS001", load("wta_pbp_1045_2024_LS001.json"))
    winners = V.derived_winners(rows)
    assert None not in winners
    assert [r["point_number"] for r, w in zip(rows, winners) if r["point_winner"] != w] == [89, 160]
    assert (rows[88]["game_score_a"], rows[88]["game_score_b"]) == ("40", "40")  # from advantage A: B won it
    doubles = W.point_rows("1045", 2024, "LD001", load("wta_pbp_1045_2024_LD001.json"))
    assert [r["point_number"] for r, w in zip(doubles, V.derived_winners(doubles)) if r["point_winner"] != w] == [71]


def test_point_by_point_replays_to_the_listed_scores():
    m = listing()
    singles = V.replay(V.derived_winners(W.point_rows("1045", 2024, "LS001", load("wta_pbp_1045_2024_LS001.json"))),
                       doubles=False)
    assert [(s["a"], s["b"]) for s in singles["sets"]] == [(1, 6), (6, 4), (4, 6)] and singles["winner"] == "B"
    assert V.score_differences(singles, V.listing_result(m["LS001"])) == []
    doubles = V.replay(V.derived_winners(W.point_rows("1045", 2024, "LD001", load("wta_pbp_1045_2024_LD001.json"))),
                       doubles=True)
    assert V.score_differences(doubles, V.listing_result(m["LD001"])) == []
    assert (doubles["sets"][0]["tb_a"], doubles["sets"][0]["tb_b"]) == (7, 0)


def test_replay_rules():
    # singles: advantage; a set to 6-4
    game = ["A"] * 3 + ["B"] * 3 + ["A", "B", "A", "A"]  # deuce, advantage lost, then won
    assert V.replay(game, doubles=False)["games"] == [1, 0]
    assert V.replay(["A", "A", "A", "B", "B", "B", "B"], doubles=True)["games"] == [0, 1]  # no-ad: 4th point wins
    tb_set = (["A"] * 4 + ["B"] * 4) * 6 + ["A"] * 7  # 6-6, then a 7-0 tiebreak
    r = V.replay(tb_set, doubles=False)
    assert (r["sets"][0]["a"], r["sets"][0]["b"], r["sets"][0]["tb_a"], r["sets"][0]["tb_b"]) == (7, 6, 7, 0)
    six_love = ["A"] * 24
    r = V.replay(six_love + ["B"] * 24 + ["A"] * 9 + ["B"] * 2 + ["A"], doubles=True)  # 6-0, 0-6, match tiebreak 10-2
    assert r["finished"] and r["sets"][2] == {"a": 1, "b": 0, "tb_a": 10, "tb_b": 2} and r["winner"] == "A"
    assert V.replay(six_love * 2 + ["A"], doubles=False)["extra_points"] == 1
    assert V.replay(["A", None, "B"], doubles=False)["stopped"] == "point 2: winner unknown"


def test_listing_results_and_retirements():
    m = listing()
    assert V.listing_result(m["LS001"])["winner"] == "B" and V.listing_result(m["LS001"])["how"] == "played"
    rakhimova = V.listing_result(m["RS004"])  # "[5]K. Rakhimova d S. Vickery 6-3,1-0 Ret'd", Winner 5
    assert (rakhimova["winner"], rakhimova["how"], [(s["a"], s["b"]) for s in rakhimova["sets"]]) == \
        ("B", "retired", [(3, 6), (0, 1)])
    assert V.listing_result(m["LS010"])["how"] == "walkover"
    retired = {"sets": [{"a": 3, "b": 6, "tb_a": None, "tb_b": None}], "games": [0, 1], "finished": False,
               "extra_points": 0, "winner": None, "points": [0, 0]}
    assert V.score_differences(retired, rakhimova) == []
    assert V.score_differences({**retired, "games": [1, 0]}, rakhimova)
    assert V.listing_result(row("709/2020/LD029"))["sets"][1] == {"a": 6, "b": 1, "tb_loser": None}


def test_result_strings_and_self_contradicting_listings():
    assert V.result_string_sets("[4]A. Kontaveit d L. Siegemund 7-6(6),2-1") == [(7, 6), (2, 1)]
    assert V.result_string_sets("R. Montgomery d [4]O. Jabeur  W/O") == []
    m = listing()
    assert V.listing_consistent(m["LS001"]) is True  # "P. Badosa d M. Bouzkova 6-1,4-6,6-4", B won
    assert V.listing_consistent(m["RS004"]) is True  # a retirement, B won
    assert V.listing_consistent(m["LS010"]) is None  # a walkover: no sets written
    # 800/2020/LS010: the fields read 6-4 6-4, the result string 7-6(6),2-1 (what the umpire's log replays to)
    broken = {**m["LS001"], "ResultString": "[4]A. Kontaveit d L. Siegemund 7-6(6),2-1", "Winner": "2",
              "ScoreSet1A": "6", "ScoreSet1B": "4", "ScoreSet2A": "6", "ScoreSet2B": "4", "ScoreSet3A": "", "ScoreSet3B": ""}
    assert V.listing_consistent(broken) is False


def _point(index: int, score: str, server: str) -> dict:
    return {"Index": index, "Name": "Point", "Attributes": {"type": "Point", "score": score, "server": server}}


def test_a_doubles_game_stays_whole_when_the_log_swaps_the_serving_partner():
    teams = {"a1": "A", "a2": "A", "b1": "B", "b2": "B"}  # as 1050/2026/LD006: SwapServer after the first point
    log = {"Events": [_point(1, "15-0", "b1"), {"Index": 2, "Name": "SwapServer", "Attributes": {}},
                      _point(3, "15-15", "b2"), _point(4, "30-15", "b2"), _point(5, "40-15", "b2"),
                      _point(6, "game", "b2"), _point(7, "15-0", "a1")]}
    assert [len(g["records"]) for g in V.event_games(log)] == [1, 4, 1]  # cut by player: one game read as two
    assert [len(g["records"]) for g in V.event_games(log, teams)] == [5, 1]
    points, games = V.event_points(log, teams)
    assert [(g["finished"], g["winner"]) for g in games] == [(True, "B"), (False, "A")]


def test_an_unwritten_tiebreak_that_play_goes_on_from_is_finished_with_its_winner_open():
    teams = {"a": "A", "b": "B"}  # as 1160/2026/LS016's second set: ten points written "0-0", then the third set
    tiebreak = [_point(i, "0-0", "ab"[(i // 2) % 2]) for i in range(1, 11)]
    after = [_point(20 + i, score, "b") for i, score in enumerate(["15-0", "30-0", "40-0", "game"])]
    points, games = V.event_points({"Events": tiebreak + after}, teams)
    assert [(g["tiebreak"], g["finished"], g["winner"]) for g in games] == [(True, True, None), (False, True, "B")]
    points, games = V.event_points({"Events": tiebreak}, teams)  # the log's last game: left unfinished
    assert [(g["tiebreak"], g["finished"]) for g in games] == [(True, False)]


def test_a_bare_2019_log_is_counted_and_timed_but_not_replayed():
    stamp = "2019-04-01T12:32:{:02d}.083+00:00"
    bare = [{"Index": 1, "Name": "StateIndicator", "Attributes": {"reason": "OnCourt"}, "Timestamp": stamp.format(0)}]
    bare += [{"Index": i, "Name": name, "Set": 1, "Game": 1, "Timestamp": stamp.format(i)}  # as 804/2019/LS036
             for i, name in enumerate(["Point", "Fault", "Point", "Ace", "Fault", "Fault", "Point"], 2)]
    assert V.is_bare_log(bare) and not V.is_bare_log(load("wta_events_1045_2024_LS001.json")["Events"])
    assert not V.is_bare_log(bare[:1])  # no point record at all: an empty log, not a bare one
    row, missed = {}, []
    V.check_bare_log(bare, {"setnum": 0, "acesa": 1, "acesb": 0}, row, lambda check, detail: missed.append(check))
    assert (row["events_form"], row["events_point_records"], row["events_fault_records"], row["events_aces"]) == \
        ("bare", 4, 3, 1)
    assert row["events_check"] == V.BARE_CHECK and "events_score_reproduced" not in row
    assert row["events_timestamps_in_order"] and row["events_aces_agree"] and missed == []
    V.check_bare_log(bare, {"setnum": 0, "acesa": 2, "acesb": 1}, row, lambda check, detail: missed.append(check))
    assert missed == ["events vs box score"] and row["events_aces_agree"] is False


def test_record_types_come_from_the_attributes():
    # Brisbane 2020's logs shift Name by one record; Attributes.type fits the scores
    shifted = {"Name": "Let", "Attributes": {"type": "Point", "score": "game"}}
    assert V.kind(shifted) == "Point" and V.kind({"Name": "Ace", "Attributes": {}}) == "Ace"


def test_timestamps():
    ok = V.timestamp_check(["2024-08-04T18:38:25Z", "2024-08-04T18:38:25Z", "2024-08-04T18:39:19Z"])
    assert ok["in_order"] and ok["max_gap_seconds"] == 54
    bad = V.timestamp_check(["2024-08-04T18:38:25Z", "2024-08-04T18:38:24Z", None])
    assert not bad["in_order"] and bad["decreases"] == 1 and bad["missing"] == 1


# verification: the umpire's event log -----------------------------------------------
def events_replay(key: str, *, doubles: bool = False):
    tid, year, mid = key.split("/")
    points, games = V.event_points(load(f"wta_events_{tid}_{year}_{mid}.json"), V.teams_of(row(key)))
    return points, games, V.replay_games(games, doubles=doubles)


def test_event_log_points_aces_double_faults_and_serve_numbers():
    events = load("wta_events_1045_2024_LS001.json")
    teams = V.teams_of(listing()["LS001"])
    points, games = V.event_points(events, teams)
    kinds = [p["kind"] for p in points]
    assert (len(points), kinds.count("ace"), kinds.count("double_fault")) == (181, 7, 12)  # the box score's 7 and 12
    assert sum(1 for p in points if p["kind"] != "double_fault" and not p["first_serve"]) == 60
    pbp = V.derived_winners(W.point_rows("1045", 2024, "LS001", load("wta_pbp_1045_2024_LS001.json")))
    assert [p["winner"] for p in points] == pbp  # the log agrees with point-by-point on every point
    result = V.replay_games(games, doubles=False)
    assert V.score_differences(result, V.listing_result(listing()["LS001"])) == []


def test_tiebreaks_are_read_in_whichever_orientation_the_log_used():
    for key, how, doubles in (("1002/2020/LS001", "first", False), ("2026/2021/LS001", "server", False),
                              ("894/2025/LD006", "next", True)):
        points, games, result = events_replay(key, doubles=doubles)
        assert {p["tiebreak_orientation"] for p in points if p["tiebreak"]} == {how}, key
        if any(g["winner"] is None and g["finished"] for g in games):  # the doubles match's no-ad deciding points
            resolved, fits = V.resolve_unknown_games(games, V.listing_result(row(key)), doubles=doubles)
            assert resolved is not None, key
            result = V.replay_games(resolved, doubles=doubles)
        assert V.score_differences(result, V.listing_result(row(key))) == [], key
    # the match tiebreak read with the next point's server first: the same states as point-by-point's 1-0 ... 10-6
    points, games, _ = events_replay("894/2025/LD006", doubles=True)
    assert games[-1]["tb"] == (10, 6) and games[-1]["winner"] == "A"
    assert [p["winner"] for p in points if p["tiebreak"]] == list("ABBAAAABABABABAA")


def test_unwritten_tiebreak_scores_and_a_game_record_ending_the_tiebreak():
    points, games, result = events_replay("808/2022/LS001")
    tiebreak = next(g for g in games if g["tiebreak"])
    assert tiebreak["tb"] is None and tiebreak["finished"] and tiebreak["winner"] == "B"
    assert V.score_differences(result, V.listing_result(row("808/2022/LS001"))) == []


def test_a_correction_replaces_the_point_before_it_only_when_the_next_one_redoes_it():
    records = V.scoring_records(load("wta_events_1003_2022_LS001.json"))
    texts = [V._text(r) for r in records]
    i = texts.index("40-15")
    assert texts[i - 1] == "30-15"  # "30-30" was voided by the correction and redone as an ace
    points, games, result = events_replay("1003/2022/LS001")
    assert V.score_differences(result, V.listing_result(row("1003/2022/LS001"))) == []
    kept = V.scoring_records(load("wta_events_1045_2024_LS001.json"))
    assert len(kept) == 181  # its correction only preceded a let: nothing voided
    assert V.one_point_apart("30-15", "40-15") and not V.one_point_apart("30-30", "40-15")
    assert V.one_point_apart("advantage in", "deuce") and V.one_point_apart("game", "0-15")


def test_no_ad_deciding_points_are_resolved_against_the_listing_and_flagged():
    points, games, result = events_replay("709/2020/LD029", doubles=True)
    unknown = [g for g in games if g["winner"] is None and g["finished"]]
    assert len(unknown) == 2 and result["stopped"]
    resolved, fits = V.resolve_unknown_games(games, V.listing_result(row("709/2020/LD029")), doubles=True)
    assert resolved is not None and fits == 1
    assert V.score_differences(V.replay_games(resolved, doubles=True), V.listing_result(row("709/2020/LD029"))) == []


def test_tiebreak_scores_and_segmentation():
    assert V.is_tiebreak_score("1-0") and V.is_tiebreak_score("0-0") and V.is_tiebreak_score("10-8")
    assert not V.is_tiebreak_score("15-0") and not V.is_tiebreak_score("40-30") and not V.is_tiebreak_score("game")
    assert V.continues_tiebreak("7-6", "7-7") and V.continues_tiebreak("0-0", "0-0") and V.continues_tiebreak("5-6", "game")
    assert not V.continues_tiebreak("8-6", "15-0") and not V.continues_tiebreak("7-5", "1-0")
    assert V.parse_event_score("advantage out", tiebreak=False) == (3, 4) and V.parse_event_score("30-15", tiebreak=False) == (2, 1)
