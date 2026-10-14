"""Offline tests for the OddsTrader adapter (no network)."""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import oddstrader as O  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402


def test_month_starts_cross_the_year_and_windows_cover_whole_months():
    assert list(O.month_starts("2024-11", "2025-02")) == [(2024, 11), (2024, 12), (2025, 1), (2025, 2)]
    start_ms, hours = O.month_window(2024, 2)
    assert start_ms == 1706745600000 and hours == 29 * 24  # 1 Feb 2024 00:00 UTC; leap year
    assert O.month_window(2024, 12)[1] == 31 * 24


def test_lines_query_asks_every_book_and_market():
    q = O.lines_query([4746024, 4799158])
    assert "cur: currentLines(paid: [8,131], eid: [4746024,4799158], mtid: [126,396])" in q
    assert 'o8: openingLines(paid: [8], eid: [4746024,4799158], mtid: [126,396], marketTypeLayout: "PARTICIPANTS")' in q
    assert "o131: openingLines(paid: [131]" in q


def test_books_query_asks_every_book_and_pinnacles_opening():
    q = O.books_query([4746024, 4799158])
    ids = ",".join(str(b) for b in range(1, 201))
    assert f"cur: currentLines(paid: [{ids}], eid: [4746024,4799158], mtid: [126])" in q
    assert 'o20: openingLines(paid: [20], eid: [4746024,4799158], mtid: [126], marketTypeLayout: "PARTICIPANTS")' in q
    assert q.startswith("{ ") and q.endswith(" }") and q.count("openingLines") == 1


def test_stage_books_keeps_the_newest_copy_and_names_books(tmp_path, monkeypatch):
    monkeypatch.setattr(O, "RAW", tmp_path / "raw")
    monkeypatch.setattr(O, "DUMP", tmp_path / "dump")
    (tmp_path / "dump").mkdir()
    line = {"mtid": 126, "eid": 1, "paid": 20, "partid": 7, "adj": 0, "ap": -110, "pri": 1.9091, "tim": "1000",
            "iof": False}
    for k, (ap, when) in enumerate(((-110, "2026-10-09T10:00:00+00:00"), (-120, "2026-10-09T11:00:00+00:00"))):
        path = tmp_path / "raw" / "books" / "23" / "2018-01" / f"{k:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"data": {"cur": [dict(line, ap=ap), dict(line, paid=3, partid=8)], "o20": [dict(line, ap=-105)]}}
        path.write_text(json.dumps(doc), encoding="utf-8")
    latest = {"books/23/2018-01/00": {"retrieved_at": "2026-10-09T10:00:00+00:00"},
              "books/23/2018-01/01": {"retrieved_at": "2026-10-09T11:00:00+00:00"}}
    assert O.stage_books(latest) == 3      # Pinnacle last, book 3 last, Pinnacle opening; one copy each
    staged = O.pd.read_parquet(tmp_path / "dump" / "books_lines.parquet")
    pin = staged[(staged["paid"] == 20) & (staged["kind"] == "last")]
    assert pin["ap"].tolist() == [-120] and pin["book"].tolist() == ["Pinnacle"]   # the newer copy
    assert staged.loc[staged["paid"] == 3, "book"].isna().all()                    # unnamed id
    assert staged.loc[staged["kind"] == "open", "ap"].tolist() == [-105]


def test_singles_are_told_from_doubles_by_event_group():
    assert O.is_singles({"eventGroup": {"nam": "French Open Men Singles"}})
    assert not O.is_singles({"eventGroup": {"nam": "US Open Women Doubles"}})
    assert not O.is_singles({"eventGroup": None})


def test_older_venue_named_singles_groups_count():
    # until mid-2019 tour-level singles groups carry the venue alone; doubles say so and pair players with "/"
    assert O.is_singles({"eventGroup": {"nam": "Rotterdam, Netherlands"}, "des": "Wawrinka S@Federer R"})
    assert O.is_singles({"eventGroup": {"nam": "Miami, USA, Qualifying"}, "des": "Kudla D@Ymer M"})
    assert not O.is_singles({"eventGroup": {"nam": "Rio de Janeiro, Brazil, Double"}, "des": "A B@C D"})
    assert not O.is_singles({"eventGroup": {"nam": "Dubai, UAE"}, "des": "Matkowski M / Qureshi A@Sharan D / Sugita Y"})
    assert not O.is_singles({"eventGroup": {"nam": "US Open Mixed"}, "des": "A B@C D"})


EVENTS_DOC = {"data": {"eventsByDateNew": {"events": [{
    "eid": 4746024, "es": "complete", "dt": 1725818400000, "lid": 23, "des": "Fritz, Taylor@Sinner, Jannik",
    "eventGroup": {"egid": 1, "nam": "US Open Men Singles", "parentid": None, "parentname": None},
    "participants": [
        {"eid": 4746024, "partid": 193050, "ih": True, "rot": 2, "source": {"pid": 265037, "fn": "Jannik", "lnam": "Sinner"}},
        {"eid": 4746024, "partid": 29410, "ih": False, "rot": 1, "source": {"pid": 216069, "fn": "Taylor", "lnam": "Fritz"}}]}]}}}

LINES_DOC = {"data": {
    "cur": [{"mtid": 126, "eid": 4746024, "paid": 8, "partid": 193050, "adj": 0, "ap": -450, "pri": 1.2222,
             "tim": "1725784426000.000000", "iof": False},
            {"mtid": 396, "eid": 4746024, "paid": 8, "partid": 15143, "adj": 40, "ap": 105, "pri": 2.05,
             "tim": "1725819300000.000000", "iof": True}],
    "o8": [{"mtid": 126, "eid": 4746024, "paid": 8, "partid": 193050, "adj": 0, "ap": -375, "pri": 1.2667,
            "tim": "1725679650000.000000", "iof": False}],
    "o131": []}}


def test_event_rows_put_each_player_on_their_side():
    (row,) = O.event_rows(EVENTS_DOC, {"_source": "oddstrader"})
    assert row["tour"] == "ATP" and row["singles"] and row["es"] == "complete"
    assert row["dt_utc"] == "2024-09-08T18:00:00+00:00"
    assert (row["home_partid"], row["home_last"]) == (193050, "Sinner")
    assert (row["away_partid"], row["away_last"]) == (29410, "Fritz")


def test_line_rows_label_kind_book_market_and_total_side():
    rows = O.line_rows(LINES_DOC, {})
    assert [r["kind"] for r in rows] == ["last", "last", "open"]
    last_ml, last_total, open_ml = rows
    assert (last_ml["book"], last_ml["market"], last_ml["ap"]) == ("BetOnline", "match_winner", -450)
    assert last_ml["tim_utc"] == "2024-09-08T08:33:46+00:00" and last_ml["tim_ms"] == 1725784426000
    assert (last_total["market"], last_total["total_side"], last_total["adj"]) == ("total_games", "over", 40)
    assert open_ml["total_side"] is None and open_ml["ap"] == -375


def test_matches_table_puts_open_and_close_on_sides_and_flags_only_bad_closes():
    full = {"data": {
        "cur": [{"mtid": 126, "eid": 4746024, "paid": 8, "partid": 193050, "adj": 0, "ap": -450, "pri": 1.2222, "tim": "1725784426000", "iof": False},
                {"mtid": 126, "eid": 4746024, "paid": 8, "partid": 29410, "adj": 0, "ap": 360, "pri": 4.6, "tim": "1725784426000", "iof": False},
                {"mtid": 396, "eid": 4746024, "paid": 8, "partid": 15143, "adj": 40, "ap": 105, "pri": 2.05, "tim": "1725819342000", "iof": True},
                {"mtid": 396, "eid": 4746024, "paid": 8, "partid": 15144, "adj": 40, "ap": -135, "pri": 1.7407, "tim": "1725819342000", "iof": True}],
        "o8": [{"mtid": 126, "eid": 4746024, "paid": 8, "partid": 193050, "adj": 0, "ap": -375, "pri": 1.2667, "tim": "1725679650000", "iof": False},
               {"mtid": 126, "eid": 4746024, "paid": 8, "partid": 29410, "adj": 0, "ap": 305, "pri": 4.05, "tim": "1725679650000", "iof": False}]}}
    events = O.pd.DataFrame(O.event_rows(EVENTS_DOC, {}))
    (row,) = O.matches_table(events, O.pd.DataFrame(O.line_rows(full, {}))).to_dict("records")
    assert (row["mw_open_home"], row["mw_open_away"], row["mw_open_overround"]) == (-375, 305, 1.0364)
    assert (row["mw_close_home"], row["mw_close_away"], row["mw_close_overround"]) == (-450, 360, 1.0356)
    assert row["mw_close_utc"] == "2024-09-08T08:33:46+00:00" and row["mw_close_after_listed_min"] == -566.2
    assert not row["mw_close_uncertain"] and not row["mw_open_uncertain"]
    assert (row["tg_close_line"], row["tg_close_over"], row["tg_close_under"]) == (40, 105, -135)
    assert row["tg_close_after_listed_min"] == 15.7 and row["tg_close_off_board"] and not row["tg_close_uncertain"]
    assert O.pd.isna(row["tg_open_line"]) and not row["tg_open_uncertain"]  # no opening total: absent, not flagged
    late = {"data": {"cur": [dict(r, tim="1725830000000") for r in full["data"]["cur"][:2]], "o8": []}}
    (row,) = O.matches_table(events, O.pd.DataFrame(O.line_rows(late, {}))).to_dict("records")
    assert row["mw_close_after_listed_min"] == 193.3 and row["mw_close_uncertain"]  # stamped 3 h after the listing


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self.content, self.headers = status, body, {"Content-Type": "application/json"}


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls, self.headers = list(responses), 0, {}

    def get(self, *args, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


def make_client(tmp_path, monkeypatch, responses, budget=5):
    monkeypatch.setattr(O, "PAUSE", 0.0)
    monkeypatch.setattr(O.random, "random", lambda: 0.0)
    client = O.Client(C.Receipts("oddstrader", root=tmp_path), budget)
    client.sess = FakeSession(responses)
    return client


@pytest.mark.parametrize("status,body", [(403, b"Forbidden"), (429, b""), (200, b"<html>challenge</html>"),
                                         (200, json.dumps({"data": {"h1": None}, "errors": [{"path": ["h1"]}]}).encode())])
def test_client_stops_on_blocks_and_errors_and_keeps_a_receipt(tmp_path, monkeypatch, status, body):
    client = make_client(tmp_path, monkeypatch, [FakeResponse(status, body)])
    with pytest.raises(O.Stop):
        client.fetch("events/23/2024-09", "{ q }", tmp_path / "x.json")
    assert client.receipts.get("events/23/2024-09")["error"]
    assert not (tmp_path / "x.json").exists()


def test_client_reuses_a_good_response_and_respects_the_budget(tmp_path, monkeypatch):
    good = json.dumps(LINES_DOC).encode()
    client = make_client(tmp_path, monkeypatch, [FakeResponse(200, good)], budget=1)
    dest = tmp_path / "lines.json"
    assert client.fetch("lines/23/2024-09/00", "{ q }", dest) == LINES_DOC
    assert client.fetch("lines/23/2024-09/00", "{ q }", dest) == LINES_DOC  # from disk, no request
    assert client.sess.calls == 1
    assert client.fetch("lines/23/2024-09/01", "{ q }", tmp_path / "other.json") is None  # budget spent
