"""The daily task's lower-level odds job and P11's comparison reminder (src/ingest/scheduled.py, job_lower_odds and
p11_compare_reminder; added 22 Oct 2026 at the owner's request): what they run and their alert rules. Offline: the
child processes and the process list are faked."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.ingest import scheduled as S  # noqa: E402


def fake(tmp_path, seen: list, lower_text: str = '{"match_pages_new": 7}\n', lower_exit: int = 0, ready_exit: int = 1):
    def child(name, args, timeout):
        seen.append((name, args, timeout))
        log = tmp_path / f"{name}.log"
        log.write_text("=== x\n" + (lower_text if name == "lower_odds" else "{}\n"), encoding="utf-8")
        code = lower_exit if name == "lower_odds" else ready_exit
        return {"exit": code, "seconds": 0.1, "log": log.name}
    return child


def names(seen):
    return [n for n, _, _ in seen]


def test_a_usual_day_asks_the_last_three_weeks(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "host_busy", lambda module: None)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, seen))
    state: dict = {}
    out, alerts = S.job_lower_odds(state, asked=False)
    assert names(seen) == ["p11_compare_ready", "lower_odds"]
    _, args, timeout = seen[1]
    since = (dt.date.today() - dt.timedelta(days=S.LOWER_ODDS_DAYS)).isoformat()
    assert args[:2] == ["-m", "src.ingest.tennisexplorer_lower"] and args[args.index("--since") + 1] == since
    assert args[args.index("--max-requests") + 1] == str(S.LOWER_ODDS_BUDGET) and timeout <= S.LOWER_ODDS_TIMEOUT
    assert out["match_pages"] == 7 and alerts == [] and state["lower_odds_failed"] is False


def test_skipped_while_the_backfill_holds_the_site(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "host_busy", lambda module: 4242 if module == "src.ingest.tennisexplorer_lower" else None)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, seen))
    out, alerts = S.job_lower_odds({}, asked=False)
    assert "backfill" in out["skipped"] and alerts == [] and names(seen) == ["p11_compare_ready"]


def test_a_budget_stop_is_not_a_failure_and_a_refusal_pauses(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "host_busy", lambda module: None)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, seen, lower_exit=3))
    state: dict = {}
    assert S.job_lower_odds(state, asked=False)[1] == [] and state["lower_odds_failed"] is False
    monkeypatch.setattr(S, "child", fake(tmp_path, seen, "[tennisexplorer_lower] STOPPED: match_1: HTTP 403\n", 2))
    _, alerts = S.job_lower_odds(state, asked=False)
    assert "paused" in alerts[0] and "lower_odds_blocked" in state
    before = names(seen).count("lower_odds")
    out, alerts = S.job_lower_odds(state, asked=False)                  # paused: not asked, no repeat alert yet
    assert "skipped" in out and alerts == [] and names(seen).count("lower_odds") == before
    monkeypatch.setattr(S, "child", fake(tmp_path, seen))
    S.job_lower_odds(state, asked=True)                                 # asked by name: tries, and lifts the pause
    assert "lower_odds_blocked" not in state


def test_an_offline_morning_alerts_only_the_second_time(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "host_busy", lambda module: None)
    seen: list = []
    text = "[tennisexplorer_lower] STOPPED: 10 failed answers in a row (last: day_atp: ConnectionError)\n"
    monkeypatch.setattr(S, "child", fake(tmp_path, seen, text, 2))
    state: dict = {}
    assert S.job_lower_odds(state, asked=False)[1] == [] and "lower_odds_blocked" not in state
    assert "two runs in a row" in S.job_lower_odds(state, asked=False)[1][0]


def test_crowded_out_waits_a_day(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "host_busy", lambda module: None)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, seen))
    state: dict = {}
    out, alerts = S.job_lower_odds(state, asked=False, left=S.LOWER_ODDS_SPARE + 60)
    assert "skipped" in out and alerts == [] and "lower_odds" not in names(seen)
    assert "crowded out two runs in a row" in S.job_lower_odds(state, asked=False, left=60)[1][0]


def test_the_comparison_reminder_weekly_until_done(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, seen, ready_exit=1))
    state: dict = {}
    assert S.p11_compare_reminder(state) == []                          # not ready yet
    monkeypatch.setattr(S, "child", fake(tmp_path, seen, ready_exit=0))
    first = S.p11_compare_reminder(state)
    assert len(first) == 1 and "comparison can be run now" in first[0] and "p11_compare_reminded" in state
    assert S.p11_compare_reminder(state) == []                          # reminded this week already
    state["p11_compare_reminded"] = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=8)).isoformat()
    assert len(S.p11_compare_reminder(state)) == 1                       # a week later, again
    monkeypatch.setattr(S, "child", fake(tmp_path, seen, ready_exit=3))
    assert S.p11_compare_reminder(state) == [] and state["p11_compare_done"] is True
    asked = len(seen)
    assert S.p11_compare_reminder(state) == [] and len(seen) == asked   # done: never checked again


def test_a_broken_check_alerts_the_second_time(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    seen: list = []
    monkeypatch.setattr(S, "child", fake(tmp_path, seen, ready_exit="timeout"))
    state: dict = {}
    assert S.p11_compare_reminder(state) == []
    assert "failed two runs in a row" in S.p11_compare_reminder(state)[0]


def test_the_daily_task_lists_it(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scheduled", "--dry-run"])
    S.main()
    due = json.loads(capsys.readouterr().out)["due"]
    assert due.index("lower_odds") == due.index("pinnacle_closes") + 1
