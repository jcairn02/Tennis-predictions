"""Every scraper keeps the match-time fields its source sends (docs/decisions/2026-10-05-match-timing.md): the start,
whether a start is only scheduled, the end where the source gives one, and the court or venue.

Run: ./python.sh -m pytest test/match_timing/test_scrape_times.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.ingest.point_sources import ausopen as AO  # noqa: E402
from src.ingest.point_sources import sofascore as SS  # noqa: E402
from src.ingest.point_sources import tennislive as TL  # noqa: E402
from src.ingest.point_sources import wta as W  # noqa: E402


def test_sofascore_keeps_the_last_set_start_the_last_change_and_the_venue():
    event = {"id": 1, "slug": "a-b", "startTimestamp": 1781790000,
             "time": {"period1": 4265, "period2": 2135, "period3": 3034, "currentPeriodStartTimestamp": 1781798071},
             "changes": {"changes": ["time.period3"], "changeTimestamp": 1781801145},
             "venue": {"name": "Court 1", "city": {"name": "Halle"}, "country": {"alpha3": "DEU", "name": "Germany"}},
             "homeTeam": {"id": 10, "name": "A"}, "awayTeam": {"id": 11, "name": "B"},
             "status": {"type": "finished"}}
    row = SS.flatten_event(event)
    assert row["start_timestamp"] == 1781790000
    assert row["current_period_start_timestamp"] == 1781798071 and row["change_timestamp"] == 1781801145
    assert (row["venue_name"], row["venue_city"], row["venue_country"]) == ("Court 1", "Halle", "DEU")
    assert set(SS.EVENT_COLUMNS) >= set(row)


def test_wta_keeps_whether_its_list_time_is_only_scheduled():
    for key in ("MatchTimeStamp", "estimatedStartTime", "isEstimatedStartTime", "Venue"):
        assert key in W.MATCH_KEYS and key in W.MATCH_COLUMNS
    m = {"MatchID": "MS001", "MatchTimeStamp": "2025-01-06T05:00:00+00:00", "estimatedStartTime": True,
         "isEstimatedStartTime": True, "Venue": {"id": "1582", "name": "Court 13"}}
    row = W.match_row({"tournament_id": "901", "year": 2025, "tier": "slam"}, m, {}, {})
    assert row["isEstimatedStartTime"] is True and row["Venue"] == {"id": "1582", "name": "Court 13"}


def test_ausopen_archived_draws_keep_the_actual_start_and_duration():
    for key in ("date", "actual_start_time", "duration", "court_name", "session"):
        assert key in AO.ARCHIVED_DRAW_COLUMNS


def test_tennislive_keeps_the_sidebar_start():
    assert "start_shown" in TL.MATCH_COLUMNS and "date_shown" in TL.MATCH_COLUMNS
