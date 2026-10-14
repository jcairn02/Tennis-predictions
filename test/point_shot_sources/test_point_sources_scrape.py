"""Parsers, caching rules and staging shapes of the point-source adapters (offline, on small fixtures)."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import sofascore as S  # noqa: E402
from src.ingest.point_sources import tennislive as T  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    path = FIXTURES / name
    return json.loads(path.read_text(encoding="utf-8")) if name.endswith(".json") else path.read_text(encoding="utf-8")


# SofaScore --------------------------------------------------------------------------
def test_sofascore_point_rows_follow_match_order_and_flag_tiebreaks():
    pbp = load("sofascore_point_by_point.json")["pointByPoint"]
    assert S.pbp_shape(pbp) == {"sets": 3, "games": 32, "points": 164, "games_per_set": [13, 9, 10]}
    rows = S.point_rows(16306516, pbp)
    assert len(rows) == 164
    first = rows[0]
    assert (first["set"], first["game"], first["point"]) == (1, 1, 1)
    assert (first["home_point"], first["away_point"], first["serving"], first["scoring"]) == ("0", "15", 2, 2)
    order = [(r["set_index"], r["game_index"], r["point"]) for r in rows]
    assert order == sorted(order)
    tiebreak = [r for r in rows if r["tiebreak"]]
    assert len(tiebreak) == 12 and {(r["set"], r["game"]) for r in tiebreak} == {(1, 13)}
    assert tiebreak[-1]["home_point"] == "7" and tiebreak[-1]["away_point"] == "5"


def test_sofascore_flatten_event_and_doubles_detection():
    events = load("sofascore_team_events.json")["events"]
    singles, doubles = events
    row = S.flatten_event(singles)
    assert row["event_id"] == 16306516 and row["category_name"] == "Challenger" and row["season_year"] == "2026"
    assert (row["home_name"], row["away_name"], row["first_to_serve"]) == ("Gustavo Heide", "Jan Choinski", 2)
    assert (row["home_set1"], row["away_set1"], row["home_tb1"], row["away_tb1"]) == (7, 6, 7, 5)
    assert row["start_utc"] == "2026-06-18 14:05" and row["doubles"] is False
    assert set(S.EVENT_COLUMNS) >= set(row)
    assert S.is_doubles(doubles) and S.flatten_event(doubles)["home_sub_ids"] == "105607;244420"
    assert S.wanted(singles, singles_only=True, since_year=None, until_year=None, statuses=None)
    assert not S.wanted(doubles, singles_only=True, since_year=None, until_year=None, statuses=None)
    assert not S.wanted(singles, singles_only=True, since_year=2027, until_year=None, statuses=None)
    assert not S.wanted(singles, singles_only=True, since_year=None, until_year=None, statuses={"canceled"})


def test_sofascore_statistic_rows_keep_every_item():
    statistics = load("sofascore_statistics.json")["statistics"]
    rows = S.statistic_rows(16306516, statistics)
    assert len(rows) == 20 and {r["period"] for r in rows} == {"ALL"}
    aces = next(r for r in rows if r["key"] == "aces")
    assert (aces["home"], aces["away"], aces["group"]) == ("7", "9", "Service")


# shared client / caching ------------------------------------------------------------
class FakeResponse:
    def __init__(self, status, body=b"{}"):
        self.status_code = status
        self.content = body
        self.headers = {"content-type": "application/json"}
        self.url = "http://x"


class FakeClient:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = 0

    def get(self, url, headers=None):
        self.calls += 1
        status = self.statuses.pop(0)
        return FakeResponse(status, b'{"ok": true}' if status == 200 else b"")


def test_fetch_treats_404_as_terminal_and_reuses_200(tmp_path):
    receipts = C.Receipts("unit", root=tmp_path)
    dest = tmp_path / "unit" / "doc.json"
    client = FakeClient([404, 200, 500, 200])
    first = P.fetch(client, "http://x/a", dest, receipts, name="a")
    assert first["status"] == 404 and not dest.exists() and client.calls == 1
    again = P.fetch(client, "http://x/a", dest, receipts, name="a")
    assert again.get("skipped") and client.calls == 1  # a 404 is not asked again
    refreshed = P.fetch(client, "http://x/a", dest, receipts, name="a", refresh=True, validator=P.json_validator)
    assert refreshed["status"] == 200 and dest.read_bytes() == b'{"ok": true}' and client.calls == 2
    cached = P.fetch(client, "http://x/a", dest, receipts, name="a")
    assert cached.get("skipped") and client.calls == 2
    failed = P.fetch(client, "http://x/b", tmp_path / "unit" / "b.json", receipts, name="b")
    assert failed["error"] == "HTTP 500" and client.calls == 3
    retried = P.fetch(client, "http://x/b", tmp_path / "unit" / "b.json", receipts, name="b")
    assert retried["status"] == 200 and client.calls == 4  # an error is retried on the next run


def test_validators_and_string_form():
    assert P.json_validator(b"  {\"a\": 1}") is None and P.json_validator(b"<html>") is not None
    assert P.html_validator(b"<!DOCTYPE html><html><head><title>Just a moment...</title>") == "Cloudflare challenge page"
    assert P.html_validator(b"<html><body>ok</body></html>") is None
    assert P.s(True) == "TRUE" and P.s(None) is None and P.s(7) == "7" and P.s({"b": 1, "a": 2}) == '{"a": 2, "b": 1}'


# TennisLive -------------------------------------------------------------------------
def test_tennislive_match_page_parses_games_points_markers_and_statistics():
    parsed = T.parse_match_page(load("tennislive_match.html"))
    meta = parsed["meta"]
    assert meta["score"] == "5-7 6-0 6-1" and meta["best_of"] == 3 and meta["winner_id"] == 47566
    assert (meta["player1_name"], meta["player2_name"]) == ("Brandon Holt", "Inaki Montes-De La Torre")
    assert (meta["date_shown"], meta["round_shown"], meta["surface_shown"]) == ("11/13/2023", "1st round", "indoor hard")
    assert meta["pbp_available"] and not meta["pbp_unavailable_notice"]
    assert (meta["sets_listed"], meta["games_listed"], meta["points_listed"], meta["first_server_index"]) == (1, 12, 50, 0)
    games = [g for g in parsed["games"] if g["game"] > 0]
    assert [g["game"] for g in games] == list(range(1, 13))
    g1 = games[0]
    assert (g1["before"], g1["after"], g1["server_index"], g1["server_name"]) == ("0-0", "0-1", 1, "Inaki Montes-De La Torre")
    assert [p["state"] for p in g1["points"]] == ["0-15", "15-15", "15-30", "15-40", "30-40"]
    assert g1["outcome"] == "Inaki Montes-De La Torre wins the game" and not g1["tiebreak"]
    assert T.winner_index(g1["outcome"], meta["player_names"]) == 1
    g2 = games[1]
    assert g2["points"][3]["markers"] == ["Break point"] and g2["label"] == "Serve lost"
    assert (games[-1]["before"], games[-1]["after"]) == ("5-6", "5-7")
    stats = parsed["statistics"]
    assert len(stats) == 8 and stats[0]["name"] == "First serve"
    assert (stats[0]["player1_value"], stats[0]["player1_detail"], stats[0]["player2_value"]) == ("70%", "49/70", "62%")
    assert stats[-1]["name"] == "Aces" and (stats[-1]["player1_value"], stats[-1]["player2_value"]) == ("3", "2")


def test_tennislive_page_without_records_is_flagged():
    meta = T.parse_match_page(load("tennislive_match_nodata.html"))["meta"]
    assert not meta["pbp_available"] and meta["pbp_unavailable_notice"]
    assert not meta["stats_available"] and meta["stats_unavailable_notice"]
    assert T.runtime_object("<html>no runtime</html>") == {}


def test_tennislive_index_rows_and_paths():
    payload = load("tennislive_player_matches.json")
    rows = T.index_rows("brandon-holt", "2023", payload, "players/brandon-holt/matches_2023_0.json")
    assert len(rows) == 2 and {r["slug"] for r in rows} == {"brandon-holt"} and {r["season"] for r in rows} == {"2023"}
    assert all(T.match_path_parts(r["url"]) for r in rows) and all(r["state"] == "finished" for r in rows)
    assert all(r["tournament_name"] == "ATP Champaign Challenger" for r in rows)
    assert T._sets([{"score": 7, "detail": 7}, 5, 4]) == "7(7) 5 4" and T._sets(None) is None
    parts = T.match_path_parts("/atp/match/a-b-VS-c-d/some-open-2024/")
    assert parts == ("atp", "a-b-VS-c-d", "some-open-2024")
    assert T.match_dest("/atp/match/a-b-VS-c-d/some-open-2024/").as_posix().endswith("matches/atp/a-b-VS-c-d/some-open-2024.html.gz")
    assert T.match_path_parts("/atp/brandon-holt/") is None


# SofaScore code inference ------------------------------------------------------------
def test_point_winner_and_game_point_derivation():
    sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "point_shot_sources"))
    import sofascore_codes as K

    assert K.point_winner(("0", "0"), ("15", "0"), False) == 1
    assert K.point_winner(("30", "40"), ("40", "40"), False) == 1
    assert K.point_winner(("40", "40"), ("40", "A"), False) == 2
    assert K.point_winner(("A", "40"), ("40", "40"), False) == 2
    assert K.point_winner(("3", "2"), ("3", "3"), True) == 2
    assert K.point_winner(("0", "0"), ("30", "0"), False) is None
    assert K.game_point_for(("40", "15"), False) == {1}
    assert K.game_point_for(("40", "A"), False) == {2}
    assert K.game_point_for(("40", "40"), False) == set()
    assert K.game_point_for(("6", "5"), True) == {1} and K.game_point_for(("6", "6"), True) == set()
    assert K.set_point_for((5, 3), 1, False) and not K.set_point_for((5, 4), 2, False)
    assert K.set_point_for((6, 6), 2, True)


def test_tennislive_opening_game_without_points_is_still_a_game():
    block = ('<div class="tl-progress-game"><div><span>Serve lost</span></div><div><div><span>{before} '
             '<span aria-hidden="true">→</span></span><strong>{after}</strong></div><div><span>A B serves</span>'
             '<span data-progress-server-ball data-player-index="0"></span></div>{points}</div><div></div></div>')
    points = ('<div>0-15 <span aria-hidden="true">·</span> 15-15 <span aria-hidden="true">→</span> '
              '<span data-progress-outcome>A B wins the game</span></div>')
    html = ('<html><head></head><body><main><section data-set-panel="2">'
            + block.format(before="0-0", after="0-0", points="")      # start marker
            + block.format(before="0-0", after="1-0", points="")      # a game whose points are missing
            + block.format(before="1-0", after="2-0", points=points)  # a normal game
            + "</section></main></body></html>")
    parsed = T.parse_match_page(html)
    games = parsed["games"]
    assert [g["game"] for g in games] == [0, 1, 2]
    assert games[1]["points"] == [] and games[1]["outcome"] is None and (games[1]["before"], games[1]["after"]) == ("0-0", "1-0")
    assert parsed["meta"]["games_listed"] == 2 and parsed["meta"]["games_without_points"] == 1
    assert parsed["meta"]["points_listed"] == 2 and parsed["meta"]["first_server_index"] == 0


def test_verification_completeness_categories():
    sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "point_shot_sources"))
    import verify_scrape as V

    assert V.completeness([12, 6, 7], [12, 6, 7]) == "exact"
    assert V.completeness([9, 8, 2], [9, 8, 3]) == "unfinished game listed"      # retirement, game in progress listed
    assert V.completeness([6], [6, 1]) == "unfinished game listed"
    assert V.completeness([13, 10, 16], [13, 10, 1]) == "match tiebreak as one game"
    assert V.completeness([13, 12, 8], [14]) == "short"
    assert V.completeness([10, 9], [11, 9]) == "long"
    assert V.completeness([10, 9], None) is None and V.complete([10, 9], [10, 9]) is True
    assert V.period("ITF main draw", 2025) == "2025" and V.period("Challenger main draw", 2025) == "2025-26"
    assert V.period("ITF main draw", 2019) == "2019-21"


# captcha token and refusals -----------------------------------------------------------
def _jwt(claims: dict) -> str:
    import base64

    part = lambda obj: base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")
    return f"{part({'alg': 'HS256', 'typ': 'JWT'})}.{part(claims)}.signature"


def test_captcha_token_file_is_decoded_and_expiry_checked(tmp_path):
    import time

    assert S.load_captcha_token(tmp_path / "missing.txt") is None
    live = _jwt({"exp": int(time.time()) + 3600, "sub": "captcha"})
    path = tmp_path / "_captcha_token.txt"
    path.write_text(f'"{live}"\n', encoding="utf-8")  # pasted with the console's quotes and a newline
    info = S.load_captcha_token(path)
    assert info["token"] == live and info["claims"]["sub"] == "captcha" and not info["expired"]
    assert info["expires_at"].endswith("UTC")
    path.write_text(_jwt({"exp": int(time.time()) - 60}), encoding="utf-8")
    assert S.load_captcha_token(path)["expired"] is True
    path.write_text("not-a-jwt", encoding="utf-8")
    odd = S.load_captcha_token(path)
    assert odd["token"] == "not-a-jwt" and odd["claims"] == {} and "not a decodable JWT" in odd["problem"]
    assert P.refusal_reason(FakeResponse(403, b'{"error": {"code": 403, "reason": "jwt:expired"}}')) == "jwt:expired"
    assert P.refusal_reason(FakeResponse(403, b"")) is None


class FakeSession:
    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.calls = 0

    def get(self, url, timeout=None, headers=None):
        self.calls += 1
        return FakeResponse(403, self.bodies.pop(0))


def _client(bodies) -> P.Client:
    client = P.Client.__new__(P.Client)
    client._session, client.impersonate, client._headers, client.block_retries = FakeSession(bodies), "test", {}, 1
    client.min_interval, client.jitter, client.max_requests, client.timeout, client.retries = 0.0, 0.0, None, 1, 3
    client.requests = client.retried = 0
    client.slept = client._last = 0.0
    client._sleep = lambda seconds: setattr(client, "slept", client.slept + seconds)  # no real waiting
    return client


def test_client_stops_at_once_on_a_rejected_token_and_after_one_challenge_retry():
    import pytest

    rejected = _client([b'{"error": {"code": 403, "reason": "jwt:expired"}}'])
    with pytest.raises(P.Blocked, match="captcha token was rejected"):
        rejected.get("http://x/a")
    assert rejected._session.calls == 1 and rejected.slept == 0
    challenged = _client([b'{"error": {"code": 403, "reason": "challenge"}}'] * 2)
    with pytest.raises(P.Blocked, match=r"HTTP 403 \(challenge\) .* after 2 attempts"):
        challenged.get("http://x/a")
    assert challenged._session.calls == 2 and challenged.slept == 60


def test_a_closed_chrome_window_stops_the_run():
    import pytest
    from src.ingest.point_sources import browser as B

    class ClosedPage:
        url = "https://www.sofascore.com/tennis"

        def evaluate(self, *args):
            raise RuntimeError("Page.evaluate: Target page, context or browser has been closed")

    class LivePage(ClosedPage):
        def evaluate(self, js, arg):
            return {"status": 200, "headers": {}, "body": "{}", "url": arg["url"]}

    class Browser:
        def __init__(self, pages):
            self.contexts = [type("Context", (), {"pages": pages})()] if pages else []

    session = B.PageSession.__new__(B.PageSession)
    session.origin, session.url_map, session.token_key = "https://www.sofascore.com", {}, None
    session.page, session._browser = ClosedPage(), Browser([LivePage()])   # the tab alone was closed: a new one
    assert session._evaluate("https://www.sofascore.com/api/v1/x", {}, 5)["status"] == 200
    session.page, session._browser = ClosedPage(), Browser([])             # the whole window was closed: stop
    with pytest.raises(P.Blocked, match="window with the debugging port was closed"):
        session._evaluate("https://www.sofascore.com/api/v1/x", {}, 5)
    client = _client([])
    client._session = session                                              # the client lets the stop through
    with pytest.raises(P.Blocked, match="window with the debugging port was closed"):
        client.get("https://api.sofascore.com/api/v1/x")
    assert client.requests == 1 and client.slept == 0


def test_browser_transport_pure_parts():
    from src.ingest.point_sources import browser as B

    assert B.allowed_headers({"Accept": "*/*", "Referer": "x", "Origin": "y", "X-Captcha": "t"}) == {"Accept": "*/*", "X-Captcha": "t"}
    session = B.PageSession.__new__(B.PageSession)
    session.url_map = {"https://api.sofascore.com/": "https://www.sofascore.com/"}
    assert session._rewrite("https://api.sofascore.com/api/v1/event/1/statistics") == "https://www.sofascore.com/api/v1/event/1/statistics"
    assert session._rewrite("https://other.example/x") == "https://other.example/x"
    response = B.BrowserResponse(404, {"Content-Type": "application/json"}, '{"error": 1}', "https://www.sofascore.com/api/v1/x")
    assert response.status_code == 404 and response.headers["content-type"] == "application/json"
    assert response.content == b'{"error": 1}' and response.url.endswith("/x")
    import time

    assert B.is_challenge(403, '{"error": {"code": 403, "reason": "challenge"}}') is True
    assert B.is_challenge(403, '{"error": {"code": 403, "reason": "jwt:expired"}}') is False
    assert B.is_challenge(404, '{"error": {"code": 404}}') is False
    assert B.token_expired(None) is True and B.token_expired("opaque") is False
    assert B.token_expired(_jwt({"exp": int(time.time()) - 5})) is True
    assert B.token_expired(_jwt({"exp": int(time.time()) + 3600})) is False
