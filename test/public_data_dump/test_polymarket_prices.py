"""Offline tests for the Polymarket price-history job planning (no network)."""
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import polymarket_prices as P  # noqa: E402


def test_parse_ts_accepts_gamma_formats():
    assert P.parse_ts("2025-09-18T22:16:38.415208Z") == 1758233798
    assert P.parse_ts("2025-09-19 13:37:22+00") == 1758289042
    assert P.parse_ts("2025-09-26T05:00:00Z") == 1758862800
    assert P.parse_ts(None) is None and P.parse_ts("garbage") is None


def test_market_window_uses_earliest_start_and_closed_time_with_margins():
    market = {"startDate": "2025-09-18T22:16:38Z", "acceptingOrdersTimestamp": "2025-09-18T22:16:16Z",
              "createdAt": "2025-09-18T22:10:00Z", "closedTime": "2025-09-19 13:37:22+00", "endDate": "2025-09-26T05:00:00Z"}
    start, end = P.market_window(market, {"sport_date": "2025-09-19T05:00:00+00:00"}, now=2_000_000_000)
    assert start == P.parse_ts("2025-09-18T22:10:00Z") - 3600
    assert end == P.parse_ts("2025-09-19 13:37:22+00") + 3600


def test_market_window_falls_back_to_end_date_and_sport_date_and_caps_at_now():
    market = {"startDate": None, "acceptingOrdersTimestamp": None, "createdAt": None, "closedTime": None,
              "endDate": "2025-09-26T05:00:00Z"}
    event = {"sport_date": "2025-09-19T05:00:00+00:00"}
    start, end = P.market_window(market, event, now=P.parse_ts("2025-09-22T00:00:00Z"))
    assert start == P.parse_ts("2025-09-19T05:00:00Z") - 3 * 86400 - 3600
    assert end == P.parse_ts("2025-09-22T00:00:00Z")
    assert P.market_window({"startDate": "2025-09-30T00:00:00Z", "closedTime": "2025-09-19 00:00:00+00"}, event, 2_000_000_000) is None


def test_chunk_window_splits_long_lives():
    assert P.chunk_window(0, 10) == [(0, 10)]
    chunks = P.chunk_window(0, 30 * 86400)
    assert chunks[0] == (0, 13 * 86400) and chunks[-1][1] == 30 * 86400 and len(chunks) == 3


def test_resolve_buckets_groups_and_dedupes():
    assert P.resolve_buckets("main-tour")[0] == "slam_main"
    assert P.resolve_buckets("itf,itf,slam_main") == ["itf", "slam_main"]
    assert P.resolve_buckets("all")[-1] == "itf" and len(P.resolve_buckets("all")) == len(P.BUCKET_SLUGS)
    with pytest.raises(ValueError):
        P.resolve_buckets("nope")


def test_select_jobs_filters_and_skips_done(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("polymarket_prices")
    events = {"e1": {"id": "e1", "slug": "atp-a-vs-b", "sport_date": "2025-09-19T05:00:00+00:00", "_cfb": False,
                     "_bucket_slug": "tour_250"},
              "e2": {"id": "e2", "slug": "itf-c-vs-d", "sport_date": "2025-09-20T05:00:00+00:00", "_cfb": False,
                     "_bucket_slug": "itf"},
              "e3": {"id": "e3", "slug": "cfb", "sport_date": "2025-09-20T05:00:00+00:00", "_cfb": True, "_bucket_slug": None}}
    base = {"in_sport_window": True, "sportsMarketType": "moneyline", "startDate": "2025-09-18T22:00:00Z",
            "closedTime": "2025-09-19 13:00:00+00", "conditionId": "0x1", "outcomes": ["A", "B"], "clobTokenIds": ["t1", "t2"]}
    markets = [{**base, "id": "m1", "event_id": "e1"}, {**base, "id": "m2", "event_id": "e2"},
               {**base, "id": "m3", "event_id": "e3"}, {**base, "id": "m4", "event_id": "e1", "sportsMarketType": "tennis_set_winner"},
               {**base, "id": "m5", "event_id": "e1", "in_sport_window": False}, {**base, "id": "m6", "event_id": "e1", "clobTokenIds": []}]
    receipts.record({"name": "m1/0", "status": 200})
    jobs, per_bucket, skipped = P.select_jobs(events, markets, ["tour_250", "itf"], {"moneyline"}, 0, receipts, False, 2_000_000_000)
    assert [j["name"] for j in jobs] == ["m2/0"] and jobs[0]["token_id"] == "t1" and jobs[0]["outcome"] == "A"
    assert per_bucket == {"tour_250": 1, "itf": 1}
    assert skipped["already fetched"] == 1 and skipped["event without bucket"] == 1 and skipped["market without token"] == 1
    jobs_refresh, _, _ = P.select_jobs(events, markets, ["tour_250"], {"moneyline"}, 0, receipts, True, 2_000_000_000)
    assert [j["name"] for j in jobs_refresh] == ["m1/0"]


def test_rate_limiter_spaces_requests():
    limiter = P.RateLimiter(rps=50)
    started = time.monotonic()
    for _ in range(5):
        limiter.wait()
    assert time.monotonic() - started >= 0.07
