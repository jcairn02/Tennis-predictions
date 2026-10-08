"""Offline tests for the Betfair historical-data adapter: request bodies and the stream parser (synthetic stream
in the documented Exchange Stream format; no account, no network)."""
import datetime as dt
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import betfair_history as BF  # noqa: E402

RUNNERS = [{"id": 11, "name": "Jannik Sinner", "status": "ACTIVE", "sortPriority": 1},
           {"id": 22, "name": "Carlos Alcaraz", "status": "ACTIVE", "sortPriority": 2}]


def definition(**changes):
    d = {"eventId": "35000001", "eventName": "Sinner v Alcaraz", "marketType": "MATCH_ODDS",
         "marketTime": "2026-01-01T12:00:00.000Z", "openDate": "2026-01-01T12:00:00.000Z", "inPlay": False,
         "status": "OPEN", "runners": RUNNERS}
    d.update(changes)
    return d


STREAM = [
    {"op": "connection", "connectionId": "x"},
    {"op": "mcm", "pt": 1767265200000, "mc": [{"id": "1.1", "marketDefinition": definition(),
                                               "rc": [{"id": 11, "ltp": 1.8}, {"id": 22, "ltp": 2.2}]}]},
    {"op": "mcm", "pt": 1767265260000, "mc": [{"id": "1.1", "rc": [
        {"id": 11, "ltp": 1.75, "tv": 1000.0, "batb": [[0, 1.74, 100.0], [1, 1.73, 20.0]], "batl": [[0, 1.76, 50.0]]}]}]},
    {"op": "mcm", "pt": 1767265320000, "mc": [{"id": "1.1", "rc": [{"id": 11, "batb": [[0, 1.73, 20.0], [1, 1.72, 0]]}]}]},
    {"op": "mcm", "pt": 1767268800000, "mc": [{"id": "1.1", "marketDefinition": definition(inPlay=True),
                                               "rc": [{"id": 11, "ltp": 1.5}]}]},
    {"op": "mcm", "pt": 1767276000000, "mc": [{"id": "1.1", "marketDefinition": definition(
        inPlay=True, status="CLOSED", settledTime="2026-01-01T15:00:00.000Z",
        runners=[dict(RUNNERS[0], status="WINNER"), dict(RUNNERS[1], status="LOSER")])}]},
]


def test_parser_keeps_each_runner_state_and_the_market_state_at_the_time():
    ticks, runners = BF.parse_stream(json.dumps(m) for m in STREAM)
    assert len(ticks) == 5
    assert [t["ltp"] for t in ticks] == [1.8, 2.2, 1.75, 1.75, 1.5]
    t = ticks[2]
    assert (t["back1"], t["back1_size"], t["lay1"], t["lay1_size"], t["tv"]) == (1.74, 100.0, 1.76, 50.0, 1000.0)
    assert (ticks[3]["back1"], ticks[3]["back1_size"]) == (1.73, 20.0)       # level 0 replaced, level 1 emptied
    assert [t["in_play"] for t in ticks] == [False, False, False, False, True]
    assert {r["runner_name"]: r["runner_status"] for r in runners} == {"Jannik Sinner": "WINNER",
                                                                      "Carlos Alcaraz": "LOSER"}
    assert runners[0]["market_time"] == "2026-01-01T12:00:00.000Z" and runners[0]["market_status"] == "CLOSED"


def test_listing_requests_cover_each_month_once():
    months = list(BF.month_ranges(dt.date(2025, 12, 15), dt.date(2026, 2, 10)))
    assert months == [(dt.date(2025, 12, 15), dt.date(2025, 12, 31)), (dt.date(2026, 1, 1), dt.date(2026, 1, 31)),
                      (dt.date(2026, 2, 1), dt.date(2026, 2, 10))]
    body = BF.file_list_body("basic", dt.date(2026, 1, 1), dt.date(2026, 1, 31))
    assert body["plan"] == "Basic Plan" and body["sport"] == "Tennis" and body["marketTypesCollection"] == ["MATCH_ODDS"]
    assert (body["fromDay"], body["toDay"], body["toMonth"], body["toYear"]) == (1, 31, 1, 2026)


def test_file_month_and_bz2_check():
    assert BF.file_month(("xds_nfs", "edp_processed", "BASIC", "2025", "Jan", "1", "29775353", "1.17.bz2")) == "2025-01"
    assert BF.file_month(("BASIC", "1.17.bz2")) == "unknown"
    assert BF.bz2_magic(b"BZh91AY") is None and BF.bz2_magic(b"<html>") is not None
