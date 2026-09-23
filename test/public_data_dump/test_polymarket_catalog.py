"""Offline tests for the Polymarket catalog extension normaliser (no network)."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import polymarket_catalog as K  # noqa: E402


def test_normalise_event_matches_census_shape():
    event = {"id": 1065930, "slug": "itf-pavlov1-llorca1-2026-09-23", "title": "W50 Yecla: Kira Pavlova vs Lucia Cortez Llorca",
             "startDate": "2026-09-22T20:15:03Z", "createdAt": "2026-09-22T20:14:17.282897Z", "endDate": "2026-09-30T15:30:00Z",
             "closed": False, "volume": 12.5, "eventDate": "2026-09-23", "startTime": "2026-09-23T15:30:00Z",
             "series": "[{\"id\": \"11634\", \"slug\": \"itf\", \"title\": \"ITF\"}]",
             "tags": [{"id": "864", "label": "Tennis", "slug": "tennis"}], "seriesSlug": "itf",
             "eventMetadata": {"league": "W50 Yecla"}, "sport": {"id": 187, "sport": "itf"},
             "markets": [{"id": "4854042", "question": "W50 Yecla: Kira Pavlova vs Lucia Cortez Llorca",
                          "sportsMarketType": "moneyline", "conditionId": "0xabc", "startDate": "2026-09-22T20:15:04Z",
                          "closedTime": None, "endDate": "2026-09-30T15:30:00Z",
                          "clobTokenIds": "[\"9429\", \"6289\"]", "outcomes": "[\"Kira Pavlova\", \"Lucia Cortez Llorca\"]",
                          "outcomePrices": "[\"0.5\", \"0.5\"]"}]}
    row, markets = K.normalise_event(event, "2026-09-22T21:22:08+00:00")
    assert row["id"] == "1065930" and row["date_basis"] == "startTime"
    assert row["sport_date"] == "2026-09-23T15:30:00+00:00"
    assert row["series"] == [{"id": "11634", "slug": "itf", "title": "ITF"}]
    assert row["market_count"] == 1 and row["catalog"] == "extension" and row["in_sport_window"] is None
    assert row["url"].endswith(event["slug"]) and row["closedTime_derived"] is None
    market = markets[0]
    assert market["clobTokenIds"] == ["9429", "6289"] and market["outcomes"][0] == "Kira Pavlova"
    assert market["event_id"] == "1065930" and market["catalog"] == "extension"
    assert set(K.MARKET_FIELDS) <= set(market)


def test_normalise_event_falls_back_to_slug_date():
    event = {"id": 5, "slug": "atp-a-vs-b-2026-09-15", "title": "x", "series": [], "tags": [], "markets": []}
    row, markets = K.normalise_event(event, "now")
    assert row["date_basis"] == "slug_date" and row["sport_date"] == "2026-09-15T00:00:00+00:00"
    assert markets == [] and row["market_count"] == 0
