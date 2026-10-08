"""Offline tests for the one-command odds refresh: step planning and command lines (nothing is run)."""
import datetime as dt
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import refresh_odds as R  # noqa: E402


def test_plan_runs_every_step_but_the_map_by_default_in_order():
    assert R.plan() == ["tennis_data", "catalog", "settle", "prices", "trades", "betfair", "study"]
    assert R.plan(with_map=True)[-1] == "map"
    assert R.plan(skip="tennis_data,betfair") == ["catalog", "settle", "prices", "trades", "study"]
    assert R.plan(only="trades,settle") == ["settle", "trades"]
    with pytest.raises(SystemExit):
        R.plan(only="prices,nope")


def test_commands_carry_today_and_the_season_range():
    now = dt.datetime(2027, 1, 3, 12, 0, tzinfo=dt.timezone.utc)
    trades = R.commands("trades", now)[0]
    assert trades[trades.index("--cutoff") + 1] == "2027-01-03T12:00:00+00:00"
    tennis = R.commands("tennis_data", now)[0]
    assert tennis[tennis.index("--start-year") + 1] == "2026" and tennis[tennis.index("--end-year") + 1] == "2027"
    assert R.commands("settle", now)[0][-1] == "--revisit"
    assert len(R.commands("study", now)) == 2


def test_tennis_data_step_ignores_errors_left_by_earlier_runs(tmp_path, monkeypatch):
    from src.ingest.public_dump import common as C
    monkeypatch.setattr(C, "RAW_ROOT", tmp_path)
    receipts = C.Receipts("tennis_data_couk")
    receipts.record({"name": "atp/2002", "error": "HTTP 404", "retrieved_at": "2026-09-22T21:10:31+00:00"})
    for name in ("atp/2025", "atp/2026", "wta/2025", "wta/2026"):
        receipts.record({"name": name, "status": 200, "retrieved_at": "2026-10-05T23:25:00+00:00"})
    assert R.tennis_data_fetched("2026-10-05T23:24:00+00:00", range(2025, 2027))
    assert not R.tennis_data_fetched("2026-10-05T23:26:00+00:00", range(2025, 2027))   # not fetched in this run
    receipts.record({"name": "wta/2026", "error": "HTTP 500", "retrieved_at": "2026-10-05T23:25:30+00:00"})
    assert not R.tennis_data_fetched("2026-10-05T23:24:00+00:00", range(2025, 2027))
