"""Step 1 of the production-integrity plan (docs/decisions/2026-10-22-production-integrity-plan.md; master pipeline
process log, Part 10): the four false or blind signals.

    * STATUS showed only the latest scheduled run, so a morning alert vanished once an afternoon job ran;
    * serve-speed freshness was read from a form file rewritten every day and from the job's exit code;
    * the canary's known flags could not be acknowledged;
    * (the owner's session-start hook: the owner's own settings, not tested here).

Fast and offline: fixture records in tmp_path, except one test that reads the real acknowledgment file
(data/studies/data_continuity/canary_acknowledged.json) to check each entry names a flag the canary can give.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest import health as H  # noqa: E402
from src.ingest import scheduled as S  # noqa: E402
from src.pipeline import config as CFG  # noqa: E402
from src.pipeline import overview as OV  # noqa: E402

UTC = dt.timezone.utc


def _runs(tmp_path, monkeypatch, runs: list[dict]) -> None:
    (tmp_path / "runs.jsonl").write_text("\n".join(json.dumps(r) for r in runs) + "\n", encoding="utf-8")
    monkeypatch.setattr(CFG, "SCHEDULED", tmp_path)


def test_a_morning_alert_stays_on_status_after_an_afternoon_run(tmp_path, monkeypatch):
    """The bug: STATUS read only the last run, here the afternoon's, so the morning's alert was invisible."""
    _runs(tmp_path, monkeypatch, [
        {"started_at": "2026-10-22T14:30:00+00:00", "jobs": {"tml": {"exit": 1}, "speeds": {"exit": 0}},
         "alerts": ["Tennis My Life download failed two runs in a row"]},
        {"started_at": "2026-10-22T20:22:00+00:00", "jobs": {"event_country": {"exit": 0}}, "alerts": []}])
    d = OV.downloads(now=dt.datetime(2026, 10, 22, 21, 0, tzinfo=UTC))
    assert [a["alert"] for a in d["alerts"]] == ["Tennis My Life download failed two runs in a row"]
    assert len(d["runs_24h"]) == 2 and d["jobs"]["tml"]["result"] == 1 and d["jobs"]["event_country"]["result"] == 0


def test_repeated_alerts_are_said_once_and_old_ones_drop(tmp_path, monkeypatch):
    _runs(tmp_path, monkeypatch, [
        {"started_at": "2026-10-10T14:30:00+00:00", "jobs": {}, "alerts": ["old"]},
        {"started_at": "2026-10-21T14:30:00+00:00", "jobs": {}, "alerts": ["held"]},
        {"started_at": "2026-10-20T14:30:00+00:00", "jobs": {}, "alerts": ["held"]},     # appended out of order
        {"started_at": "2026-10-22T14:30:00+00:00", "jobs": {}, "alerts": ["held"]}])
    d = OV.downloads(now=dt.datetime(2026, 10, 22, 21, 0, tzinfo=UTC))
    assert [(a["alert"], a["times"]) for a in d["alerts"]] == [("held", 3)]
    assert d["alerts"][0]["at"].startswith("10-22")


def _speed_rec(newest: str | None, planned: int, staged: int, status: str = "ran") -> dict:
    return {"run_at": "2026-10-22T14:30:17+00:00", "collector": {"status": status, "plan_requests": planned,
                                                                  "staged": staged},
            "form": {"latest_reading": newest}}


def test_speed_freshness_comes_from_the_newest_reading():
    today = dt.date(2026, 10, 22)
    assert H.speed_status(today, _speed_rec("2026-10-21", 24, 9))["status"] == "ok"
    stale = H.speed_status(today, _speed_rec("2026-10-08", 24, 0))
    assert stale["status"] == "stale" and stale["age_days"] == 14 and "STALE" in stale["line"]
    assert H.speed_status(today, _speed_rec("2026-10-21", 24, 0))["status"] == "empty"
    assert H.speed_status(today, _speed_rec("2026-10-08", 0, 0))["status"] == "ok"      # nothing to collect (off-season)
    assert H.speed_status(today, _speed_rec("2026-10-21", 0, 0, status="disabled (live/collector.json)"))[
        "status"] == "off"
    assert H.speed_status(today, {})["status"] == "unknown"


def test_speed_alerts_say_empty_the_second_time_and_stale_every_three_days():
    state, today = {}, dt.date(2026, 10, 22)
    empty = H.speed_status(today, _speed_rec("2026-10-21", 24, 0))
    assert S.speeds_alerts(empty, state, today) == []                          # once can be the ATP not ready yet
    assert "staged nothing" in S.speeds_alerts(empty, state, today)[0]        # twice: said
    stale = H.speed_status(today, _speed_rec("2026-10-08", 24, 0))
    assert any("14 days old" in a for a in S.speeds_alerts(stale, state, today))
    assert not any("days old" in a for a in S.speeds_alerts(stale, state, today + dt.timedelta(days=1)))
    assert any("days old" in a for a in S.speeds_alerts(stale, state, today + dt.timedelta(days=3)))
    ok = H.speed_status(today, _speed_rec("2026-10-21", 24, 9))
    assert S.speeds_alerts(ok, state, today) == [] and "speeds_stale_said" not in state


def test_canary_flags_split_into_open_acknowledged_and_lapsed(tmp_path, monkeypatch):
    known = tmp_path / "canary_acknowledged.json"
    known.write_text(json.dumps({"acknowledged": [
        {"flag": "a:GONE", "until": "2027-01-31", "why": "", "by": ""},
        {"flag": "b:GONE", "until": "2026-10-01", "why": "", "by": ""}]}), encoding="utf-8")
    monkeypatch.setattr(H, "CANARY_KNOWN", known)
    g = H.canary_split({"a:GONE", "b:GONE", "c:REVISED"}, H.canary_known(dt.date(2026, 10, 22)))
    assert g == {"acknowledged": ["a:GONE"], "lapsed": ["b:GONE"], "open": ["c:REVISED"]}


def _not_canary_flags(known) -> list[str]:
    """The acknowledged flags the canary could never give: an item it does not watch, or a word its flags never start
    with."""
    from src.eda.data_continuity import canary as CY
    items = {w[0] for w in CY.WATCH}
    words = {"GONE", "STALE", "SHRANK", "REVISED", "TERMS", "ARCHIVE", "UNARCHIVED"}   # canary.flags' first words
    return sorted(f for f in known if f.partition(":")[0] not in items or f.partition(":")[2] not in words)


def test_the_acknowledged_flags_are_real_canary_flags():
    """Each acknowledgment names a flag the canary can give (a typo would acknowledge nothing). One that has cleared
    since is no error: it waits, unused, until its date (sackmann_tennis_atp:ARCHIVE cleared on 26 Oct 2026, when
    Software Heritage answered again)."""
    assert _not_canary_flags(H.canary_known()) == []
    assert _not_canary_flags({"sackmann_tennis_atp:GONNE": {}, "sackmann_tenis_atp:GONE": {},
                              "tml_manifest:SHRANK": {}}) == ["sackmann_tenis_atp:GONE", "sackmann_tennis_atp:GONNE"]


def test_status_lists_runs_by_when_they_were_made(tmp_path, monkeypatch):
    for name, made in (("live_2026-10-14_123349", "2026-10-14T193349Z"), ("live_2026-10-21_203628", "2026-10-22T033628Z")):
        (tmp_path / name).mkdir()
        (tmp_path / name / "run.json").write_text(json.dumps({"created_at": made}), encoding="utf-8")
    (tmp_path / "live_2026-10-14_123349" / "touched").write_text("x", encoding="utf-8")   # a cleanup touched it last
    monkeypatch.setattr(CFG, "DAILY_RUNS", tmp_path)
    assert [r["run"] for r in OV.prediction_runs()] == ["live_2026-10-14_123349", "live_2026-10-21_203628"]
