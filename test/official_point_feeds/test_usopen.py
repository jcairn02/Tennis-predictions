"""US Open settings for the IBM SlamTracker engine (src/ingest/point_sources/usopen.py) and the US Open behaviour the
shared checks rely on, offline, on fixtures cut from real payloads fetched on 24 Sep 2026 (US Open 2022 MS 1101,
2025 MS 1101, MQ 11101 and 11108, MD 3101, 2026 MS 1101 and MQ 11101)."""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import slamtracker as T  # noqa: E402
from src.ingest.point_sources.usopen import SITE as U  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "official_point_feeds"))
import slamtracker_checks as K  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
EXTRAS = ("distance", "livel2w", "limbtracking", "keymoments", "prematch_l2w")


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# settings -----------------------------------------------------------------------------
def test_site_hosts_years_and_urls():
    assert (U.key, U.source, U.slam, U.lang, U.impersonate) == ("usopen", "usopen", "usopen", "en_US", "chrome")
    assert U.years == [2022, 2023, 2024, 2025, 2026] and set(U.hosts.values()) == {"https://www.usopen.org"}
    assert U.events == ("MS", "WS", "MQ", "WQ", "MD", "WD") and not U.blocked and not U.day_lists
    urls = {f.name: U.url(2026, f.path, f, id="1101") for f in U.feeds}
    assert urls == {
        "history": "https://www.usopen.org/en_US/scores/feeds/2026/slamtracker/history/1101C.json",
        "stats": "https://www.usopen.org/en_US/scores/feeds/2026/matches/complete/1101.json",
        "distance": "https://www.usopen.org/en_US/scores/feeds/2026/slamtracker/distance/1101.dist.json",
        "livel2w": "https://www.usopen.org/clouddata/livel2w/2026/1101C.json",
        "limbtracking": "https://www.usopen.org/clouddata/limbtracking/2026/match/1101.json",
        "keymoments": "https://www.usopen.org/clouddata/keymoments/key_moment/2026/1101.json",
        "prematch_l2w": "https://www.usopen.org/clouddata/likelihood-to-win/2026/1101.json",
    }
    assert T.raw_dest(U, 2026, "distance", urls["distance"]).as_posix().endswith("usopen/2026/distance/1101.dist.json.gz")


def test_feed_filters():
    f = {feed.name: feed for feed in U.feeds}
    assert f["history"].core and f["stats"].core and not any(f[n].core for n in EXTRAS)
    assert f["history"].applies(2022, "MQ", "S") and f["stats"].applies(2026, "MQ", "N")  # every match, walkovers too
    assert f["distance"].applies(2022, "MD", "H") and not f["distance"].applies(2025, "MQ", "S")
    assert f["livel2w"].applies(2025, "MQ", "H") and not f["livel2w"].applies(2024, "MS", "H")
    assert not f["livel2w"].applies(2026, "MS", "S")
    assert f["limbtracking"].applies(2026, "WS", "H") and not f["limbtracking"].applies(2025, "MS", "H")
    assert f["keymoments"].applies(2026, "MS", "H") and not f["keymoments"].applies(2025, "MS", "H")
    assert f["prematch_l2w"].applies(2025, "MQ", "S") and not f["prematch_l2w"].applies(2024, "MS", "H")


# fetching rules -------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status, body=b"", headers=None, url="https://www.usopen.org/x"):
        self.status_code, self.content, self.url = status, body, url
        self.headers = {"content-type": "application/json", **(headers or {})}


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout=None, allow_redirects=True, headers=None):
        self.calls.append((url, allow_redirects))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def client_with(responses):
    client = T.make_client(U, min_interval=0.0, jitter=0.0, max_requests=None)
    client._session = FakeSession(responses)
    return client


def test_missing_files_are_absent_and_never_asked_again(tmp_path, monkeypatch):
    """A missing /clouddata/ file answers 302 to /notfound, a missing feed file HTTP 404 with an HTML page (pilot)."""
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("usopen", root=tmp_path)
    notfound = FakeResponse(302, headers={"location": "https://www.usopen.org/notfound", "content-type": "text/html"})
    missing = FakeResponse(404, b"<!DOCTYPE html>\n\n<html>\n\t<head>", {"content-type": "text/html"})
    client = client_with([notfound, missing])
    l2w = T.fetch_match_feed(client, receipts, U, U.feed("livel2w"), 2026, "11101", event="MQ")
    dist = T.fetch_match_feed(client, receipts, U, U.feed("distance"), 2024, "11101", event="MQ")
    assert T.outcome(l2w) == "absent" and l2w["absent"] == "HTTP 302 redirect to https://www.usopen.org/notfound"
    assert T.outcome(dist) == "absent" and dist["status"] == 404
    again = [T.fetch_match_feed(client, receipts, U, U.feed(name), year, "11101", event="MQ")
             for name, year in (("livel2w", 2026), ("distance", 2024))]
    assert all(r.get("skipped") for r in again) and len(client._session.calls) == 2
    assert all(allow is False for _, allow in client._session.calls)  # redirects are never followed


def test_other_redirects_resets_and_403_stop_the_run():
    with pytest.raises(P.Blocked, match="robots.txt"):
        client_with([FakeResponse(302, headers={"location": "https://www.usopen.org/robots.txt"})]).get("https://www.usopen.org/a")
    with pytest.raises(P.Blocked, match="2024.usopen.org"):
        client_with([FakeResponse(301, headers={"location": "https://2024.usopen.org/en_US/b"})]).get("https://www.usopen.org/b")
    with pytest.raises(P.Blocked, match="connection reset"):
        client_with([ConnectionResetError("Connection was reset")]).get("https://www.usopen.org/c")
    with pytest.raises(P.Blocked, match="HTTP 403"):
        client_with([FakeResponse(403, b"Access Denied", {"content-type": "text/html"})]).get("https://www.usopen.org/d")


# payloads -------------------------------------------------------------------------------
def test_history_keys_differ_by_year_and_markers_are_not_points():
    old, new = T.history_rows(load("usopen_history_2022_1101.json")), T.history_rows(load("usopen_history_2026_1101.json"))
    assert [r["PointNumber"] for r in old] == ["0X", "0Y", "1", "2", "145"]
    assert [T.is_point(r) for r in new] == [False, False, True, True, True]
    assert len(old[0]) == 52 and len(new[0]) == 57
    assert set(new[0]) - set(old[0]) == {"PointID", "CourtIndicator", "TeamOrientStart", "TeamOrientEnd", "P1SetsWon", "P2SetsWon"}
    assert set(old[0]) - set(new[0]) == {"ChallengeWon"}  # present 2022-2025, gone in 2026
    assert new[2]["PointID"] == "010101" and old[0]["EpochTimeStart"] == "0" and old[2]["EpochTimeStart"] == "1661789611"


def test_a_full_data_draw_entry_can_come_with_an_empty_history():
    """2025 MQ 11101 is "H" in the draw and "S" in its own statistics file; its history holds only the markers."""
    refs = {r.match_id: r for r in T.draw_refs(load("usopen_draw_2025_MQ.json"), 2025, "MQ")}
    assert (refs["11101"].level, refs["11108"].level) == ("H", "S")
    assert refs["11101"].entry["team1.displayNameA"] == "A. Cazaux" and refs["11108"].entry["status"] == "Completed"
    rows = T.history_rows(load("usopen_history_2025_11101.json"))
    assert [r["PointNumber"] for r in rows] == ["0X", "0Y"] and not any(T.is_point(r) for r in rows)


def test_extras_stage_as_rows_or_paths():
    kind, rows = T.document_rows(load("usopen_distance_2026_1101.json"))
    paths = {r["path"]: r["value"] for r in rows}
    assert kind == "paths" and paths["teams.team1.1"] == ["707.1 m", "2319.8 ft"]
    assert paths["teams.team2.5"] == ["3761.2 m", "12340.0 ft"]  # cumulative metres run, per set
    kind, rows = T.document_rows(load("usopen_livel2w_2025_1101.json"))
    assert kind == "rows" and [r["point_number"] for r in rows] == [1, 2, 3] and rows[0]["player_one_tour_id"] == "atps0ag"
    kind, rows = T.document_rows(load("usopen_keymoments_2026_1101.json"))
    assert kind == "rows" and [r["point_number"] for r in rows] == ["26", "33"] and rows[0]["moment_type"] == "pbp"
    kind, rows = T.document_rows(load("usopen_prematch_l2w_2026_1101.json"))
    paths = {r["path"]: r["value"] for r in rows}
    assert kind == "paths" and paths["predicted_winner"] == "atpz355"
    assert paths["likelihood_to_win"] + paths["opponent_likelihood_to_win"] == pytest.approx(1)
    kind, rows = T.document_rows(load("usopen_limbtracking_2026_1101.json"))
    paths = {r["path"]: r["value"] for r in rows}
    assert kind == "paths" and paths["atpz355.match_summary.total_serves"] == 207
    assert paths["atpz355.match_summary.standout_metrics.effectiveness.avg_ball_speed_mph"] == 126.07


# checks ---------------------------------------------------------------------------------
def test_epoch_start_jump_is_reported_while_end_stays_in_order():
    """2026 MQ 11101: from point 32, EpochTimeStart jumps to an exact hour and then a day ahead; EpochTimeEnd is fine."""
    rows = load("usopen_history_2026_11101_epochs.json")
    assert [r["PointNumber"] for r in rows] == ["30", "31", "32", "33", "34"]
    result = K.epoch_problems([r["EpochTimeStart"] for r in rows], [r["EpochTimeEnd"] for r in rows])
    assert result["filled"] and not result["in_order"]
    assert (result["end_before_start"], result["end_backwards"], result["start_backwards"]) == (3, 0, 0)
    assert int(rows[2]["EpochTimeStart"]) % 3600 == 0


def test_sentences_doubles_team_actor_and_unmapped_text():
    ref = T.draw_refs(load("usopen_draw_2025_MD.json"), 2025, "MD")[0]
    names = K.side_names({f"entry.{k}": v for k, v in ref.entry.items()})
    parsed = K.parse_sentence("A. Erler/R. Galloway wins the point with a forehand smash winner")  # 2025 MD 3101, point 1
    assert (parsed["actor"], parsed["stroke"], parsed["outcome"]) == ("A. Erler/R. Galloway", "forehand smash", "winner")
    assert K.actor_side(parsed["actor"], names) == 2  # PointWinner 2 in the feed
    assert K.parse_sentence("S. Nagal wins the point") is None  # 2026 MQ 11101, point 31: no shot named, so unmapped
    odd = K.parse_sentence("G. Simon wins the point with a forehand forced error")  # 2022 MQ 11107, point 163
    assert odd["actor_won"] and odd["outcome"] not in K.WIN_OUTCOMES  # counted as "verb and outcome disagree"


def test_l2w_file_generated_after_the_match_is_a_replay():
    """The 2025 MS 1101 likelihood-to-win file was written on 23 Jul 2026, eleven months after the match."""
    created = [r["created_epoch"] for r in load("usopen_livel2w_2025_1101.json")]
    ends = [r["EpochTimeEnd"] for r in load("usopen_history_2025_1101.json") if T.is_point(r)]
    assert ends == ["1756228301", "1756234208"]
    assert K.l2w_kind(created, ends) == "replay"
    assert K.l2w_kind(created, []) == "unknown"  # 2025 MQ 11101: likelihood rows, but a history without points
