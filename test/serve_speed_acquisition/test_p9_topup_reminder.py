"""The scheduled task's P9 top-up reminder (src/ingest/scheduled.py, job p9_topup), offline: its due date from
ManTennisData's calendar, the weekly notices from 1 December, the daily reminders from the due date, once a day, and
the end once a full run started on or after the due date is recorded and staged."""
import datetime as dt
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import scheduled as SC  # noqa: E402


def calendar(path: Path, finishes: dict[str, str]) -> Path:
    ids = list(finishes)
    pq.write_table(pa.table({"id": ids, "series_id": ["ch" if "-3" in i else "atp" for i in ids],
                             "finish_dtm": [finishes[i] for i in ids]}), path)
    return path


def setup(tmp_path, monkeypatch, finishes=None):
    cal = calendar(tmp_path / "cal.parquet", finishes or {"2026-339": "20260111", "2026-3203": "20261220",
                                                          "2027-339": "20270110"})
    monkeypatch.setattr(SC, "P9_CALENDAR", cal)
    monkeypatch.setattr(SC, "P9_FULL_RUNS", tmp_path / "full_runs.jsonl")
    monkeypatch.setattr(SC, "P9_STAGED", tmp_path / "stage_summary.json")


def day(m, d):
    return dt.date(2026, m, d) if m >= 10 else dt.date(2027, m, d)


def test_the_due_date_is_the_seasons_last_finish_plus_eight_days(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    assert SC.p9_due() == (dt.date(2026, 12, 28), dt.date(2026, 12, 20))      # the next season's events not counted
    monkeypatch.setattr(SC, "P9_CALENDAR", tmp_path / "missing.parquet")
    assert SC.p9_due() == SC.P9_FALLBACK_DUE                                   # an unreadable calendar never fails


def test_nothing_before_december_then_weekly_notices_then_daily_reminders(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    state: dict = {}
    assert SC.job_p9_topup(state, day(11, 30))[1] == []
    days = [day(12, d) for d in (1, 2, 7, 8, 14, 15, 22, 27)]
    alerts = {d: SC.job_p9_topup(state, d)[1] for d in days}
    assert [d.day for d, a in alerts.items() if a] == [1, 8, 15, 22]             # weekly before the due date
    assert "due on Mon 28 Dec" in alerts[day(12, 1)][0] and "they end on 20 Dec" in alerts[day(12, 1)][0]
    out, a = SC.job_p9_topup(state, day(12, 28))
    assert out["due"] == "2026-12-28" and "due today" in a[0] and "repeats every day" in a[0]
    assert SC.job_p9_topup(state, day(12, 28))[1] == []                          # once a day
    assert "(2 days ago)" in SC.job_p9_topup(state, day(12, 30))[1][0]
    assert SC.job_p9_topup(state, day(1, 5))[1]                                  # and on, until it is done


def test_it_stops_for_good_once_a_full_run_after_the_due_date_is_staged(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    state: dict = {}
    early = {"started_at": "2026-12-02T15:00:00+00:00", "finished_at": "2026-12-02T16:00:00+00:00"}
    SC.P9_FULL_RUNS.write_text(json.dumps(early) + "\n", encoding="utf-8")
    SC.P9_STAGED.write_text(json.dumps({"finished_at": "2026-12-02T16:40:00+00:00"}), encoding="utf-8")
    assert SC.job_p9_topup(state, day(12, 29))[1]                    # a run before the season's end is not the top-up
    run = {"started_at": "2026-12-29T15:00:00+00:00", "finished_at": "2026-12-29T15:50:00+00:00"}
    with SC.P9_FULL_RUNS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(run) + "\n")
    assert SC.job_p9_topup(state, day(12, 30))[1]                    # recorded, but not staged after it yet
    SC.P9_STAGED.write_text(json.dumps({"finished_at": "2026-12-29T16:30:00+00:00"}), encoding="utf-8")
    out, a = SC.job_p9_topup(state, day(12, 31))
    assert a == [] and out["done"] == {"run_started": run["started_at"], "staged_at": "2026-12-29T16:30:00+00:00"}
    assert state["p9_topup_done"] and SC.job_p9_topup(state, day(2, 1)) == ({"done": state["p9_topup_done"]}, [])


def test_the_job_is_one_of_the_daily_jobs():
    source = Path(SC.__file__).read_text(encoding="utf-8")
    assert '"canary", "p9_topup", "slams", "tdi"' in source and 'job == "p9_topup"' in source
