"""The daily task's Pinnacle-closes job (src/ingest/scheduled.py, job_pinnacle_closes; added 21 Oct 2026 at the owner's
request): what it runs, and its alert rules. Offline: the child process is faked."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.ingest import scheduled as S  # noqa: E402


def fake(tmp_path, text: str, code: int, seen: list):
    def child(name, args, timeout):
        seen.append((name, args, timeout))
        (tmp_path / "p.log").write_text("=== x\n" + text, encoding="utf-8")
        return {"exit": code, "seconds": 0.1, "log": "p.log"}
    return child


def test_a_usual_day_fetches_three_weeks_and_restages(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, "[tennisexplorer] matches: 12 pages fetched\n", 0, seen))
    state: dict = {}
    out, alerts = S.job_pinnacle_closes(state, asked=False)
    name, args, timeout = seen[0]
    since = (dt.date.today() - dt.timedelta(days=S.PINNACLE_DAYS)).isoformat()
    assert name == "pinnacle_closes" and args[:2] == ["-m", "src.ingest.tennisexplorer"]
    assert {"--calendar", "--events", "--matches", "--stage"} <= set(args) and args[args.index("--since") + 1] == since
    assert args[args.index("--max") + 1] == str(S.PINNACLE_BUDGET) and timeout <= S.PINNACLE_TIMEOUT
    assert out["match_pages"] == 12 and alerts == [] and state["pinnacle_closes_failed"] is False


def test_a_refusal_pauses_until_a_run_by_name_gets_through(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, "[tennisexplorer] STOPPED: match_1: HTTP 403 (a block)\n", 2, seen))
    state: dict = {}
    _, alerts = S.job_pinnacle_closes(state, asked=False)
    assert "paused" in alerts[0] and "pinnacle_closes_blocked" in state
    out, alerts = S.job_pinnacle_closes(state, asked=False)              # paused: nothing asked, no repeat alert yet
    assert "skipped" in out and alerts == [] and len(seen) == 1
    monkeypatch.setattr(S, "child", fake(tmp_path, "[tennisexplorer] matches: 3 pages fetched\n", 0, seen))
    S.job_pinnacle_closes(state, asked=True)                             # asked by name: tries, and lifts the pause
    assert "pinnacle_closes_blocked" not in state and len(seen) == 2


def test_an_offline_morning_alerts_only_the_second_time(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    seen: list = []
    text = "[tennisexplorer] STOPPED: calendar_atp_2026: ConnectionError: no route (0 requests sent)\n"
    monkeypatch.setattr(S, "child", fake(tmp_path, text, 2, seen))
    state: dict = {}
    assert S.job_pinnacle_closes(state, asked=False)[1] == [] and "pinnacle_closes_blocked" not in state
    assert "two runs in a row" in S.job_pinnacle_closes(state, asked=False)[1][0]


def test_crowded_out_by_the_other_jobs_waits_a_day(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "child", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run")))
    state: dict = {}
    out, alerts = S.job_pinnacle_closes(state, asked=False, left=S.PINNACLE_SPARE + 60)
    assert "skipped" in out and alerts == []
    assert "crowded out two runs in a row" in S.job_pinnacle_closes(state, asked=False, left=60)[1][0]


def test_the_daily_task_lists_it(monkeypatch, capsys):
    import json
    monkeypatch.setattr(sys, "argv", ["scheduled", "--dry-run"])
    S.main()
    assert "pinnacle_closes" in json.loads(capsys.readouterr().out)["due"]
