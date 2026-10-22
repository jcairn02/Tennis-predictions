"""Offline tests: the coordinated Stage 0 rebuild's id pairing and link remap, the build's override guard, and the
scheduled downloads' alert rules."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.data_continuity import rebuild_stage0 as R  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.ingest import scheduled as S  # noqa: E402


def stage0(folder: Path, matches: list[tuple], players: list[tuple]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(matches, columns=["match_id", "tour", "tournament_id", "round"]).to_parquet(
        folder / "stage0_matches.parquet", index=False)
    pd.DataFrame(players, columns=["match_id", "player_id", "player_name"]).to_parquet(
        folder / "stage0_match_players.parquet", index=False)


def test_id_map_pairs_by_event_round_and_names(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    stage0(old, [("wta|t1|R32|wta:1|wta:9", "wta", "t1", "R32"), ("wta|t1|R16|wta:1|wta:2", "wta", "t1", "R16"),
                 ("wta|t2|F|wta:5|wta:6", "wta", "t2", "F")],
           [("wta|t1|R32|wta:1|wta:9", "wta:1", "Emma Navarro"), ("wta|t1|R32|wta:1|wta:9", "wta:9", "Eva Lys"),
            ("wta|t1|R16|wta:1|wta:2", "wta:1", "Emma Navarro"), ("wta|t1|R16|wta:1|wta:2", "wta:2", "Ann Li"),
            ("wta|t2|F|wta:5|wta:6", "wta:5", "A B"), ("wta|t2|F|wta:5|wta:6", "wta:6", "C D")])
    # R32: Eva Lys's id changes; R16 unchanged; the t2 final disappears; a new match appears
    stage0(new, [("wta|t1|R32|wta:1|wta:name:eva lys", "wta", "t1", "R32"), ("wta|t1|R16|wta:1|wta:2", "wta", "t1", "R16"),
                 ("wta|t3|F|wta:7|wta:8", "wta", "t3", "F")],
           [("wta|t1|R32|wta:1|wta:name:eva lys", "wta:1", "Emma Navarro"),
            ("wta|t1|R32|wta:1|wta:name:eva lys", "wta:44", "Lys Eva"),
            ("wta|t1|R16|wta:1|wta:2", "wta:1", "Emma Navarro"), ("wta|t1|R16|wta:1|wta:2", "wta:2", "Ann Li"),
            ("wta|t3|F|wta:7|wta:8", "wta:7", "E F"), ("wta|t3|F|wta:7|wta:8", "wta:8", "G H")])
    pairs, unpaired = R.id_map(old, new)
    assert pairs[["old_match_id", "new_match_id"]].values.tolist() == [
        ["wta|t1|R32|wta:1|wta:9", "wta|t1|R32|wta:1|wta:name:eva lys"]]   # name keys ignore token order
    assert unpaired == ["wta|t2|F|wta:5|wta:6"]


def test_id_map_leaves_ambiguous_pairs_alone(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    rows = lambda mid, a, b: [(mid, a, "Same Name"), (mid, b, "Other Name")]  # noqa: E731
    stage0(old, [("m_old", "atp", "t", "R1")], rows("m_old", "atp:1", "atp:2"))
    stage0(new, [("m_new1", "atp", "t", "R1"), ("m_new2", "atp", "t", "R1")],
           rows("m_new1", "atp:3", "atp:4") + rows("m_new2", "atp:5", "atp:6"))
    pairs, unpaired = R.id_map(old, new)
    assert pairs.empty and unpaired == ["m_old"]


def test_remap_rewrites_frozen_links_only(tmp_path, monkeypatch):
    links = tmp_path / "links"
    links.mkdir()
    pd.DataFrame({"match_id": ["a", "b"], "source_key": ["1", "2"]}).to_parquet(links / "live_tennis_api.parquet")
    pd.DataFrame({"match_id": ["a"], "source_key": ["9"]}).to_parquet(links / "wta_api.parquet")   # rebuilt by refresh
    pd.DataFrame({"other": [1]}).to_parquet(links / "flashscore_records.parquet")                  # no match_id
    monkeypatch.setattr(R, "LINKS", links)
    counts = R.remap_frozen(pd.DataFrame({"old_match_id": ["a"], "new_match_id": ["A"]}))
    assert counts == {"live_tennis_api.parquet": 1}
    assert pd.read_parquet(links / "live_tennis_api.parquet")["match_id"].tolist() == ["A", "b"]
    assert pd.read_parquet(links / "wta_api.parquet")["match_id"].tolist() == ["a"]
    assert not list(links.glob("*.part"))


def test_restore_puts_back_only_verified_copies(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "ROOT", tmp_path)
    live = tmp_path / "data" / "t.parquet"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"new")
    kept = tmp_path / "run" / "replaced" / "data" / "t.parquet"
    kept.parent.mkdir(parents=True)
    kept.write_bytes(b"old")
    manifest = [{"path": "data/t.parquet", "bytes": 3, "sha256": R.sha(kept)}]
    (tmp_path / "run" / "replaced" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert R.restore(tmp_path / "run") == 1 and live.read_bytes() == b"old"
    kept.write_bytes(b"tampered")
    live.write_bytes(b"new")
    with pytest.raises(SystemExit, match="does not match"):
        R.restore(tmp_path / "run")
    assert live.read_bytes() == b"new"


def test_build_guards_other_override_tables(tmp_path, monkeypatch):
    def no_build():
        raise AssertionError("the guard did not stop the build")
    monkeypatch.setattr(B, "load_raw", no_build)    # never reach the live tables, whatever happens
    other = tmp_path / "other.csv"
    other.write_text("tour\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="confirm-live-overrides"):
        B.build(None, other)                        # another table into the live folder, unconfirmed
    with pytest.raises(SystemExit, match="missing"):
        B.build(tmp_path / "out", tmp_path / "nope.csv")


def test_decided_override_table_is_the_default():
    assert B.build.__defaults__[1] == B.DECIDED_OVERRIDES
    assert B.DECIDED_OVERRIDES.name == "slam_box_overrides.csv"


def test_canary_flags_compare_first_word(tmp_path, monkeypatch):
    latest = tmp_path / "canary_latest.json"
    latest.write_text(json.dumps({"flags": {"tml": ["STALE (12 days)"], "repo": ["GONE"]}}), encoding="utf-8")
    monkeypatch.setattr(S, "CANARY_LATEST", latest)
    assert S.canary_flags() == {"tml:STALE", "repo:GONE"}


def test_slam_reminder_once_a_week(monkeypatch):
    monkeypatch.setattr(S, "slam_held", lambda folder, year: folder != "wimbledon")
    state: dict = {}
    _, alerts = S.job_slams(state, dt.date(2027, 7, 20))
    assert len(alerts) == 1 and "Wimbledon 2027" in alerts[0]
    assert S.job_slams(state, dt.date(2027, 7, 23))[1] == []          # reminded three days ago
    assert len(S.job_slams(state, dt.date(2027, 7, 27))[1]) == 1      # a week later, again
    assert S.job_slams({}, dt.date(2027, 7, 1))[1] == []              # not finished yet


def test_roland_garros_and_the_infosys_files_are_reminded(monkeypatch):
    """Roland Garros (its own statistics and its Infosys files) and the Australian Open's Infosys files are box-score
    sources since 9 Oct 2026, so each is reminded once its Slam has finished, naming the adapter to run."""
    monkeypatch.setattr(S, "slam_held", lambda folder, year: folder not in ("rolandgarros", "infosys_slams/RG"))
    _, alerts = S.job_slams({}, dt.date(2027, 6, 20))
    assert len(alerts) == 2 and all(a.startswith("Roland Garros") and "2027 has finished" in a for a in alerts)
    assert any("rolandgarros.py" in a for a in alerts) and any("infosys_slams.py" in a for a in alerts)
    assert not any("Roland Garros" in a for a in S.job_slams({}, dt.date(2027, 6, 1))[1])   # not finished on 1 June


def test_tml_alerts_on_repeat_hold_and_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    def fake(text):
        def child(name, args, timeout):
            (tmp_path / "t.log").write_text("=== x\n" + text, encoding="utf-8")
            return {"exit": 1, "seconds": 0.1, "log": "t.log"}
        return child
    held = "[tennis_my_life] held 2026.csv: ragged\n[tennis_my_life] done: 9 staged files, 1 rows, 0 download errors, 1 held\n"
    monkeypatch.setattr(S, "child", fake(held))
    state: dict = {}
    assert S.job_tml(state)[1] == [] and state["tml_held"] == ["2026.csv"]       # first hold: no alert
    assert "held two runs in a row" in S.job_tml(state)[1][0]
    monkeypatch.setattr(S, "child", fake("[tennis_my_life] done: 3 staged files, 1 rows, 2 download errors, 0 held\n"))
    out, alerts = S.job_tml(state)
    assert out["errors"] == 2 and alerts == [] and state["tml_held"] == []      # one failure: the PC may be offline
    monkeypatch.setattr(S, "child", fake("Traceback: manifest unavailable\n"))     # no summary line at all
    assert "two runs in a row" in S.job_tml(state)[1][0]
    monkeypatch.setattr(S, "child", fake("[tennis_my_life] done: 9 staged files, 1 rows, 0 download errors, 0 held\n"))
    assert S.job_tml(state)[1] == [] and state["tml_failed"] is False


def test_offline_canary_raises_nothing(tmp_path, monkeypatch):
    latest = tmp_path / "canary_latest.json"
    monkeypatch.setattr(S, "CANARY_LATEST", latest)
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 0, "seconds": 0.1, "log": "c.log"})
    latest.write_text(json.dumps({"flags": {"a": ["GONE"], "b": ["GONE"], "c": ["GONE"]},
                                  "items": [{"item": x, "status": None} for x in "abc"]}), encoding="utf-8")
    state = {"canary_flags": ["x:GONE"]}
    out, alerts = S.job_canary(state)
    assert out["offline"] and alerts == [] and state["canary_flags"] == ["x:GONE"]
    latest.write_text(json.dumps({"flags": {"a": ["GONE"]}, "items": [{"item": "a", "status": 404},
                                                                     {"item": "b", "status": 200}]}), encoding="utf-8")
    out, alerts = S.job_canary(state)
    assert out["new_flags"] == ["a:GONE"] and "new flag" in alerts[0]


# the weekly lower-level feed (13 Oct 2026, docs/studies/data_gaps_2026/) ------------------------------------------
def test_the_weekly_task_runs_its_own_jobs(monkeypatch, capsys):
    monkeypatch.setattr(S, "STATE", Path("no_such_state.json"))       # no catch-up: each job on its own day
    monkeypatch.setattr(sys, "argv", ["scheduled", "--weekly", "--dry-run"])
    assert S.main() == 0
    day = dt.date.today().weekday()                                    # tennislive every day, the rest on their days
    expected = ["tennislive"] + {S.WTA_POINTS_WEEKDAY: ["wta_points"], S.WTA_SITE_WEEKDAY: ["wta_site"],
                                 S.FEED_WEEKDAY: ["wta", "feed", "coverage", "tml_dates"]}.get(day, [])
    assert json.loads(capsys.readouterr().out)["due"] == expected
    monkeypatch.setattr(sys, "argv", ["scheduled", "--weekly", "--only", "feed,coverage", "--dry-run"])
    S.main()
    assert json.loads(capsys.readouterr().out)["due"] == ["feed", "coverage"]
    monkeypatch.setattr(sys, "argv", ["scheduled", "--dry-run"])
    S.main()
    assert not set(json.loads(capsys.readouterr().out)["due"]) & set(S.WEEKLY_JOBS)   # the daily task never runs them


def test_coverage_alerts_new_gaps_then_every_four_weeks_and_forgets_cleared_ones(tmp_path, monkeypatch):
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(S, "COVERAGE_SUMMARY", summary)
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 3, "seconds": 0.1, "log": "c.log"})
    state: dict = {}
    summary.write_text(json.dumps({"alarm_cell_keys": ["wta ITF matches recent"]}), encoding="utf-8")
    out, alerts = S.job_coverage(state, left=3600)
    assert out["new"] == ["wta ITF matches recent"] and "1 new" in alerts[0]
    assert S.job_coverage(state, left=3600)[1] == []                           # the same gap a week later: quiet
    state["coverage_alarm"]["wta ITF matches recent"] = (dt.date.today() - dt.timedelta(days=28)).isoformat()
    out, alerts = S.job_coverage(state, left=3600)
    assert out["reminded"] == ["wta ITF matches recent"] and "1 lasting" in alerts[0]
    summary.write_text(json.dumps({"alarm_cell_keys": []}), encoding="utf-8")
    assert S.job_coverage(state, left=3600)[1] == [] and state["coverage_alarm"] == {}


def test_a_feed_stopped_by_a_check_alerts_at_once_and_a_failure_the_second_time(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "FEED_RUNS", tmp_path / "runs.jsonl")
    (tmp_path / "runs.jsonl").write_text(json.dumps({"label": "F1", "exit": 4, "why": "the identity screen"}) + "\n",
                                         encoding="utf-8")
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 4, "seconds": 0.1, "log": "f.log"})
    state: dict = {}
    out, alerts = S.job_feed(state, left=3 * 3600)
    assert "stopped at a check (the identity screen)" in alerts[0] and state["feed_failed"] is False
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 1, "seconds": 0.1, "log": "f.log"})
    assert S.job_feed(state, left=3 * 3600)[1] == []                           # one failure: wait a week
    assert "two weeks in a row" in S.job_feed(state, left=3 * 3600)[1][0]
    out, _ = S.job_feed({}, left=60 * 60)                                      # under 75 minutes left: waits
    assert "skipped" in out


def test_a_collector_already_on_the_host_is_not_doubled(monkeypatch):
    monkeypatch.setattr(S, "host_busy", lambda module: 4242)
    monkeypatch.setattr(S, "child", lambda *a, **k: pytest.fail("no second collector may start"))
    state: dict = {}
    out, alerts = S.job_tennislive(state, asked=False, left=3600)
    assert "4242" in out["skipped"] and alerts == []
    out, alerts = S.job_wta(state, asked=False, left=3600)
    assert "4242" in out["skipped"] and alerts == []
    assert "two weeks in a row" in S.job_wta(state, asked=False, left=3600)[1][0]


def test_a_tennislive_block_pauses_the_job_until_asked(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "host_busy", lambda module: None)

    def child(name, args, timeout):
        (tmp_path / "t.log").write_text("=== x\n[tennislive] STOPPED: Blocked: HTTP 403\n", encoding="utf-8")
        return {"exit": 1, "seconds": 0.1, "log": "t.log", "args": args}
    monkeypatch.setattr(S, "child", child)
    state: dict = {}
    out, alerts = S.job_tennislive(state, asked=False, left=3600)
    assert "paused" in alerts[0] and "tennislive_blocked" in state
    assert out["args"][out["args"].index("--weeks") + 1].count("-W") == 2
    out, alerts = S.job_tennislive(state, asked=False, left=3600)
    assert "skipped" in out and "still paused" in alerts[0]


# the WTA API's weekly jobs (work package P2 of docs/studies/gap_downloads/collection-plan.md, 14 Oct 2026) ------------
def test_the_wta_jobs_run_on_their_days_and_catch_up_but_never_on_the_feeds_day():
    monday = dt.date(2026, 10, 19)
    week = {monday + dt.timedelta(days=i): S.weekly_due(monday + dt.timedelta(days=i), None, {}) for i in range(7)}
    assert week[monday] == ["tennislive", "wta_points"]
    assert week[monday + dt.timedelta(days=1)] == ["tennislive", "wta_site"]
    assert week[monday + dt.timedelta(days=2)] == ["tennislive", "wta", "feed", "coverage", "tml_dates"]
    assert all(due == ["tennislive"] for d, due in week.items() if d.weekday() > 2)
    missed = {"wta_points_last": "2026-10-12", "wta_site_last": "2026-10-13"}     # last Monday and Tuesday's runs
    assert S.weekly_due(dt.date(2026, 10, 20), None, missed) == ["tennislive", "wta_points", "wta_site"]  # Monday off
    assert S.weekly_due(dt.date(2026, 10, 21), None, missed) == ["tennislive", "wta", "feed", "coverage",
                                                              "tml_dates"]  # not Wed
    assert S.weekly_due(dt.date(2026, 10, 22), None, missed) == ["tennislive", "wta_points", "wta_site"]
    ran = {"wta_points_last": "2026-10-19", "wta_site_last": "2026-10-20"}
    assert S.weekly_due(dt.date(2026, 10, 22), None, ran) == ["tennislive"]       # ran on their days: nothing to catch
    assert S.weekly_due(dt.date(2026, 10, 22), {"wta_site", "feed"}, ran) == ["wta_site", "feed"]   # asked by name


def _fake_children(tmp_path, monkeypatch, exits, summaries=None, text="[wta] done\n"):
    """child() stand-in: writes each run's log part under ROOT, and the summary a run would write, and records args."""
    monkeypatch.setattr(S, "ROOT", tmp_path)
    monkeypatch.setattr(S, "host_busy", lambda module: None)
    calls = []

    def child(name, args, timeout):
        calls.append({"name": name, "args": args, "timeout": timeout})
        (tmp_path / f"{name}.log").write_text(f"=== {S.now()} x\n{text}", encoding="utf-8")
        for path, summary in (summaries or {}).items():
            year = args[args.index("--player-year") + 1] if "--player-year" in args else None
            if "--stage-only" not in args and (year is None or str(year) in str(path)):
                Path(path).write_text(json.dumps({"started_at": S.now(), **summary}), encoding="utf-8")
        return {"exit": exits.pop(0) if exits else 0, "seconds": 0.1, "log": f"{name}.log"}
    monkeypatch.setattr(S, "child", child)
    return calls


def test_wta_points_asks_every_endpoint_of_five_weeks_and_stages_a_run_cut_short(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "WTA_SUMMARY", tmp_path / "wta_summary.json")
    calls = _fake_children(tmp_path, monkeypatch, ["timeout", 0], {tmp_path / "wta_summary.json": {
        "client": {"requests": 812}, "fetch_outcomes": {"events:200": 150}}})
    state: dict = {}
    out, alerts = S.job_wta_points(state, asked=False, left=3 * 3600)
    args = calls[0]["args"]
    assert args[args.index("--endpoints") + 1] == S.WTA_POINTS_ENDPOINTS and "--no-stage" not in args
    since = dt.date.fromisoformat(args[args.index("--from-date") + 1])
    assert (dt.date.today() - since).days == 35 and args[args.index("--years") + 1].endswith(str(dt.date.today().year))
    assert "--stage-only" in calls[1]["args"] and out["staged"] == 0             # the timeout's staging
    assert out["requests"] == 812 and alerts == [] and state["wta_points_failed"] is True
    assert state["wta_points_last"] == dt.date.today().isoformat()
    calls = _fake_children(tmp_path, monkeypatch, [1], {tmp_path / "wta_summary.json": {
        "stopped": "BudgetExhausted: request budget of 2500 used up"}})
    assert S.job_wta_points(state, asked=False, left=3 * 3600)[1] == [] and state["wta_points_failed"] is False
    _fake_children(tmp_path, monkeypatch, [1], text="[wta] STOPPED: Blocked: HTTP 429\n")
    out, alerts = S.job_wta_points(state, asked=False, left=3 * 3600)
    assert "paused" in alerts[0] and "wta_points_blocked" in state
    out, alerts = S.job_wta_points(state, asked=False, left=3 * 3600)
    assert "skipped" in out and "still paused" in alerts[0]
    out, _ = S.job_wta_points({}, asked=False, left=25 * 60)                    # too little time: tomorrow
    assert "skipped" in out


def test_wta_site_refreshes_recent_players_and_alerts_a_growing_lag(tmp_path, monkeypatch):
    template = tmp_path / "wta_player_matches_{year}_summary.json"
    monkeypatch.setattr(S, "WTA_SITE_SUMMARY", template)
    today = dt.date.today()
    newest = (today - dt.timedelta(days=10)).isoformat()
    summaries = {str(template).format(year=y): {"players_asked": 4467, "client": {"requests": 2366},
                                                "evidence": {"results": 32465, "itf_last_start": newest}}
                 for y in (today.year - 1, today.year)}
    calls = _fake_children(tmp_path, monkeypatch, [], summaries)
    state: dict = {}
    out, alerts = S.job_wta_site(state, asked=False, left=3 * 3600)
    args = calls[0]["args"]
    assert "--player-matches" in args and args[args.index("--refresh-rotation") + 1] == str(S.WTA_SITE_ROTATION)
    assert args[args.index("--refresh-active-since") + 1] == (today - dt.timedelta(days=S.WTA_SITE_ACTIVE)).isoformat()
    assert args[args.index("--refresh-before") + 1] <= S.now()
    years = [c["args"][c["args"].index("--player-year") + 1] for c in calls]
    assert years == sorted({str((today - dt.timedelta(days=S.WTA_SITE_ACTIVE)).year), str(today.year)})
    assert alerts == [] and out["lag_days"] == 10 and state["wta_site_failed"] is False
    late = (today - dt.timedelta(days=S.WTA_SITE_LAG + 3)).isoformat()            # the website stopped listing
    for s in summaries.values():
        s["evidence"]["itf_last_start"] = late
    _fake_children(tmp_path, monkeypatch, [], summaries)
    out, alerts = S.job_wta_site(state, asked=False, left=3 * 3600)
    assert "newest ITF edition" in alerts[0] and state["wta_site_lag_alerted"] == today.isoformat()
    assert S.job_wta_site(state, asked=False, left=3 * 3600)[1] == []              # a week later: quiet
    state["wta_site_lag_alerted"] = (today - S.WTA_SITE_REMIND).isoformat()
    assert "newest ITF edition" in S.job_wta_site(state, asked=False, left=3 * 3600)[1][0]   # every four weeks
    _fake_children(tmp_path, monkeypatch, [1, 1, 1, 1], summaries)
    assert S.job_wta_site(state, asked=False, left=3 * 3600)[1][1:] == []          # one failure: wait a week
    assert "two weeks in a row" in S.job_wta_site(state, asked=False, left=3 * 3600)[1][-1]
    out, _ = S.job_wta_site({}, asked=False, left=35 * 60)                         # too little time: tomorrow
    assert "skipped" in out


def test_the_wta_jobs_command_lines_parse_in_the_adapter(tmp_path, monkeypatch):
    import argparse
    from src.ingest.point_sources import wta as W

    def parsed(args):
        parser = argparse.ArgumentParser()
        W.add_arguments(parser)
        assert args[:2] == ["-m", "src.ingest.point_sources.wta"]
        return parser.parse_args(args[2:])
    monkeypatch.setattr(S, "WTA_SUMMARY", tmp_path / "wta_summary.json")
    monkeypatch.setattr(S, "WTA_SITE_SUMMARY", tmp_path / "s_{year}.json")
    calls = _fake_children(tmp_path, monkeypatch, ["timeout"])
    S.job_wta_points({}, asked=False, left=3 * 3600)
    first, staging = (parsed(c["args"]) for c in calls)
    assert first.max_requests == S.WTA_POINTS_BUDGET and first.endpoints.count(",") == 4 and not first.no_stage
    assert staging.stage_only and staging.years == first.years
    calls = _fake_children(tmp_path, monkeypatch, ["timeout"])
    S.job_wta_site({}, asked=False, left=3 * 3600)
    crawl, staging = (parsed(c["args"]) for c in calls[:2])
    assert crawl.player_matches and crawl.refresh_rotation == S.WTA_SITE_ROTATION and crawl.refresh_before
    assert staging.player_matches and staging.stage_only and staging.player_year == crawl.player_year


def test_tml_dates_alerts_a_new_misdated_edition_then_every_four_weeks_and_forgets_acknowledged_ones(tmp_path,
                                                                                                        monkeypatch):
    """The weekly Tennis My Life date check (14 Oct 2026): exit 3 with a new edition alerts at once, not again the next
    week, again after four; an edition gone from the summary's "new" (added to the known list) is forgotten."""
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(S, "TML_DATES_SUMMARY", summary)
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 3, "seconds": 0.1, "log": "t.log"})
    state: dict = {}
    summary.write_text(json.dumps({"misdated": 68, "new": ["atp|2026-9001|Lima|20260601"]}), encoding="utf-8")
    out, alerts = S.job_tml_dates(state, left=3600)
    assert len(alerts) == 1 and "Lima" in alerts[0] and out["new"] == ["atp|2026-9001|Lima|20260601"]
    out, alerts = S.job_tml_dates(state, left=3600)
    assert alerts == [] and out["new"] == []
    state["tml_dates_alerted"]["atp|2026-9001|Lima|20260601"] = (dt.date.today() - dt.timedelta(days=28)).isoformat()
    out, alerts = S.job_tml_dates(state, left=3600)
    assert len(alerts) == 1 and out["reminded"] == ["atp|2026-9001|Lima|20260601"]
    summary.write_text(json.dumps({"misdated": 68, "new": []}), encoding="utf-8")
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 0, "seconds": 0.1, "log": "t.log"})
    out, alerts = S.job_tml_dates(state, left=3600)
    assert alerts == [] and state["tml_dates_alerted"] == {}
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 1, "seconds": 0.1, "log": "t.log"})
    assert S.job_tml_dates(state, left=3600)[1] == []                  # one failure: no alert
    assert len(S.job_tml_dates(state, left=3600)[1]) == 1              # the second in a row alerts


def test_the_feed_alerts_on_new_two_draw_flags_and_never_fails_for_them(tmp_path, monkeypatch):
    """The feed's run records its two-draws comparison (14 Oct 2026); job_feed alerts when it names new flags, and the
    feed's exit code is untouched."""
    runs = tmp_path / "runs.jsonl"
    monkeypatch.setattr(S, "FEED_RUNS", runs)
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 0, "seconds": 0.1, "log": "f.log"})
    runs.write_text(json.dumps({"label": "F1", "exit": 0, "why": "advanced", "two_draws": {"new": 0}}) + "\n",
                    encoding="utf-8")
    out, alerts = S.job_feed({}, left=3 * 3600)
    assert alerts == [] and out["exit"] == 0
    runs.write_text(json.dumps({"label": "F2", "exit": 0, "why": "advanced",
                                "two_draws": {"new": 2, "new_examples": ["wta:1 2026-09-07: A | B"],
                                              "file": "x_new.csv"}}) + "\n", encoding="utf-8")
    out, alerts = S.job_feed({}, left=3 * 3600)
    assert len(alerts) == 1 and "2 new" in alerts[0] and out["exit"] == 0


def test_the_id_map_works_when_no_match_id_changed(tmp_path):
    """A rebuild whose new Stage 0 keeps every match id (the date correction of 14 Oct 2026 changes no id) pairs nothing
    and leaves nothing unpaired; the empty name map once made the key's text + number fail."""
    m = pd.DataFrame({"match_id": ["a|1|R32|p1|p2", "a|1|F|p1|p3"], "tour": ["atp", "atp"],
                      "tournament_id": ["2024-2847", "2024-2847"], "round": ["R32", "F"]})
    p = pd.DataFrame({"match_id": ["a|1|R32|p1|p2", "a|1|R32|p1|p2", "a|1|F|p1|p3", "a|1|F|p1|p3"],
                      "player_name": ["One", "Two", "One", "Three"]})
    for name in ("old", "new"):
        (tmp_path / name).mkdir()
        m.to_parquet(tmp_path / name / "stage0_matches.parquet", index=False)
        p.to_parquet(tmp_path / name / "stage0_match_players.parquet", index=False)
    pairs, unpaired = R.id_map(tmp_path / "old", tmp_path / "new")
    assert pairs.empty and unpaired == []
