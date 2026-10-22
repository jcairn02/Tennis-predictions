"""Section B of the notebook: getting the newest data.

Most downloads already run by themselves: a Windows scheduled task runs `python -m src.ingest.scheduled` every day at
07:30 (Tennis My Life, the ATP serve speeds, the ITF live data; the canary and TDI on Mondays; docs/decisions/
2026-10-06-download-cadence.md), and a second one at 12:00 the lower-level feed (TennisLive daily; the WTA API, the
feed's snapshot and the coverage alarm on Wednesdays; docs/decisions/2026-10-13-lower-level-feed.md: lower_level_feed,
feed_status). These functions run the same jobs by hand, and the refreshes nothing schedules: the
odds history (tennis-data.co.uk, OddsTrader's BetOnline and Pinnacle lines), the WTA API's timeline, and the
coordinated rebuild of the shared tables (Stage 0, Stage 1's odds, the timeline).

Each function runs the project's own command line (src/ingest/, src/eda/data_continuity/) through runner.run_step, so
pacing, receipts, raw copies and the stop-on-block rules are the adapters' own (docs/decisions/
2026-10-08-scraping-approved.md). Nothing here edits another study's code or tables directly.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from . import config as CFG
from .runner import Step, StepResult, run_step, run_steps

SCHEDULED_JOBS = ("tml", "speeds", "itf", "canary", "slams", "tdi")


# --- what the scheduled task did --------------------------------------------------------------------------------------
def scheduled_runs(last: int = 7) -> list[dict]:
    """The scheduled task's latest runs (data/raw/_scheduled/runs.jsonl), most recent last."""
    path = CFG.SCHEDULED / "runs.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[-last:]


def held_tml_files() -> list[str]:
    """Tennis My Life files held for review, as NAME@SHA12 (the form --accept-held takes). A held version that is now
    the current copy has been accepted (its copy stays in held/ as the record) and is not listed."""
    held = CFG.TML_RAW / "held"
    out = []
    for f in sorted(held.glob("*.csv")) if held.exists() else []:
        parts = f.name.split(".")
        if len(parts) == 3:                      # 2022_challenger.d95fa0a4bf8a.csv
            current = CFG.TML_RAW / f"{parts[0]}.csv"
            if current.exists() and hashlib.sha256(current.read_bytes()).hexdigest()[:12] == parts[1]:
                continue                         # accepted: the held version is the current copy
            if current.exists() and current.stat().st_mtime > f.stat().st_mtime:
                continue                         # superseded: a newer copy has been accepted since (21 Oct 2026)
            out.append(f"{parts[0]}.csv@{parts[1]}")
    return out


def paused_jobs() -> dict:
    """Jobs the scheduled task has paused after a block (state.json: itf_blocked, tdi_blocked). A run asked for by name
    lifts a pause when it gets through, so these functions refuse a paused job unless override_pause=True: back off and
    report (docs/decisions/2026-10-08-scraping-approved.md)."""
    path = CFG.SCHEDULED / "state.json"
    if not path.exists():
        return {}
    state = json.loads(path.read_text(encoding="utf-8"))
    return {k.replace("_blocked", ""): v for k, v in state.items() if k.endswith("_blocked") and v}


def _refuse_paused(jobs, override: bool) -> None:
    hit = {j: v for j, v in paused_jobs().items() if j in set(jobs)}
    if hit and not override:
        raise RuntimeError(f"paused after a block: {hit}. Look at the job's log first; override_pause=True tries anyway "
                           "(and lifts the pause if it gets through).")


def last_run_of(job: str) -> dt.datetime | None:
    """When the scheduled task (or a manual run of it) last ran a job SUCCESSFULLY: for Tennis My Life, no download
    error (a held file exits 1 but the other files came down); for the others, exit 0 (review V1, item 12)."""
    for r in reversed(scheduled_runs(last=30)):
        j = r.get("jobs", {}).get(job)
        if not isinstance(j, dict):
            continue
        ok = j.get("errors", 0) == 0 and j.get("exit") in (0, 1) if job == "tml" else j.get("exit") == 0
        if ok:
            return dt.datetime.fromisoformat(r["started_at"]).astimezone()
    return None


def ran_today(job: str = "tml", day: dt.date | None = None) -> bool:
    """Whether the scheduled task (or a manual run of it) ran a job on this day (local date of its start)."""
    day = day or dt.date.today()
    for r in reversed(scheduled_runs(last=20)):
        started = dt.datetime.fromisoformat(r["started_at"]).astimezone().date()
        if started == day and job in r.get("jobs", {}):
            return True
    return False


# --- the scheduled jobs, by hand ---------------------------------------------------------------------------------------
def scheduled_downloads(only: list[str] | tuple[str, ...] | None = None, *, force_canary: bool = False,
                        plan_only: bool = False, override_pause: bool = False, dry_run: bool = False) -> StepResult:
    """Run the daily download task now (all due jobs, or `only` some of them: tml, speeds, itf, canary, slams, tdi).

    plan_only: the task prints which jobs are due and stops. A held Tennis My Life file makes the task exit 1; that is
    reported, not raised (see held_tml_files()). A job paused after a block is refused when named in `only`, unless
    override_pause=True (unnamed, the task itself skips it)."""
    args: list[str] = ["-m", "src.ingest.scheduled", "--no-notify"]
    if only:
        bad = set(only) - set(SCHEDULED_JOBS)
        if bad:
            raise ValueError(f"unknown jobs {sorted(bad)}; known: {SCHEDULED_JOBS}")
        _refuse_paused(only, override_pause)
        args += ["--only", ",".join(only)]
    if force_canary:
        args.append("--force-canary")
    if plan_only:
        args.append("--dry-run")
    res = run_step(Step("scheduled_downloads", args, ok_codes=(0, 1)), dry_run=dry_run)
    if res.returncode == 1:
        print("NOTE: the task exited 1 (a held file or a failed job). Held Tennis My Life files:", held_tml_files() or "none")
    return res


def refresh_results(*, dry_run: bool = False) -> StepResult:
    """Tennis My Life now: the results and box scores Stage 0 is built from (the scheduled 'tml' job)."""
    return scheduled_downloads(only=["tml"], dry_run=dry_run)


def accept_held_tml(version: str, *, dry_run: bool = False) -> StepResult:
    """Let one reviewed, held Tennis My Life file through (version = NAME@SHA12 from held_tml_files()).

    The review (the owner, 13 Oct 2026; docs/decisions/2026-10-13-tml-lower-level-revisions.md):
    src/eda/tml_revisions/held_check.py builds Stage 0 in a scratch tree with and without the held version and lists
    every match it changes. Accept it when every change is a cleanup (a duplicate removed, a match restored to its own
    event or date, a key rebuilt, an id, score or box score corrected) and no main-tour match changes; otherwise it
    stays held and goes to the owner. Accepted, Tennis My Life's own lower-level changes are listed by the history
    check (tml_lower) and refuse no template build."""
    name = version.split("@")[0]
    if any(k in name for k in ("challenger", "qual", "itf", "futures")):
        print(f"NOTE: {name} is lower-level data: accept it only after src/eda/tml_revisions/held_check.py has listed "
              "every change it makes (decision of 13 Oct 2026).")
    return run_step(Step("accept_held_tml", ["-m", "src.ingest.public_dump.tennis_my_life", "--start-year", "2000",
                                             "--accept-held", version]), dry_run=dry_run)


def refresh_speeds(days_back: int = 1, *, max_requests: int | None = None, dry_run: bool = False) -> StepResult:
    """The ATP serve speeds (src/ingest/speed_daily.py): the rounds played on the last `days_back` days, the live
    panel and each player's 28-day speed form, which stage 2 reads. Run it after the results (it plans from them).
    After missed days, raise days_back (the daily job looks back one day only)."""
    if max_requests is None:
        max_requests = 200 * max(1, days_back)
    return run_step(Step("refresh_speeds", ["src/ingest/speed_daily.py", "--days-back", str(days_back),
                                            "--max-requests", str(max_requests)]), dry_run=dry_run)


def refresh_timeline_sources(*, tdi: bool = True, wta: bool = True, wta_from: str | None = None,
                             override_pause: bool = False, dry_run: bool = False) -> list[StepResult]:
    """Exact match days for the leak-proof timeline: TDI's forward capture (the last ten days' listings) and the WTA
    API's editions since `wta_from` (default: 21 days ago), then the WTA tables restaged (the timeline reads the staged
    copy). Without them the newest rounds get date windows instead of exact days. TDI is refused while the scheduled
    task has it paused after a block (override_pause=True tries anyway)."""
    steps = []
    if tdi:
        _refuse_paused(["tdi"], override_pause)
        steps.append(Step("tdi_recent", ["-m", "src.ingest.point_sources.tdi", "--recent", "10",
                                         "--max-requests", "1000"], note="about 20 minutes"))
    if wta:
        start = wta_from or (dt.date.today() - dt.timedelta(days=21)).isoformat()
        year = start[:4]
        years = year if year == str(dt.date.today().year) else f"{year}-{dt.date.today().year}"
        steps.append(Step("wta_events", ["-m", "src.ingest.point_sources.wta", "--years", years, "--from-date", start,
                                         "--tiers", "1000,500,250,125,finals", "--endpoints", "events",
                                         "--max-requests", "3000", "--stop-after-absences", "150", "--no-stage"]))
        steps.append(Step("wta_stage", ["-m", "src.ingest.point_sources.wta", "--stage-only", "--years", years]))
    return run_steps(steps, dry_run=dry_run)


def _months(spec) -> list[str]:
    if spec in (None, "auto"):
        today = dt.date.today().replace(day=1)
        prev = (today - dt.timedelta(days=1)).replace(day=1)
        return [prev.strftime("%Y-%m"), today.strftime("%Y-%m")]
    return [spec] if isinstance(spec, str) else list(spec)


def refresh_odds_history(*, tennis_data: bool = True, oddstrader_months="auto", dry_run: bool = False) -> list[StepResult]:
    """The odds history the training frame reads: tennis-data.co.uk's workbooks (Pinnacle's closes to July 2025) and
    OddsTrader's lines (BetOnline's, and Pinnacle's where listed). A month OddsTrader already holds is fetched again
    only by name, so each month is pulled with --refresh-month (default: last month and this month)."""
    steps = []
    if tennis_data:
        steps.append(Step("tennis_data", ["-m", "src.ingest.refresh_odds", "--only", "tennis_data"]))
    for m in _months(oddstrader_months) if oddstrader_months else []:
        steps.append(Step(f"oddstrader_{m}", ["-m", "src.ingest.oddstrader", "--from", m, "--to", m,
                                              "--refresh-month", m]))
    return run_steps(steps, dry_run=dry_run)


def rebuild_shared_tables(*, confirm: bool = False, skip_ttt: bool = False, expect: str | Path | None = None,
                          dry_run: bool = False) -> StepResult | None:
    """The coordinated rebuild of the repository's shared tables (src/eda/data_continuity/rebuild_stage0.py): Stage 0,
    Stage 1's odds, the link remap, the timeline, the leak-proof features and TrueSkill (about 50 minutes; skip_ttt
    leaves TrueSkill's 30 for later). Other sessions read these tables, so it refuses unless confirm=True: check first
    that no study or build is reading them. The script keeps every file it replaces (restore: --restore <stamp>).

    The daily prediction does not need it: each prediction run builds its own Stage 0 in a sandbox."""
    if not confirm and not dry_run:
        print("Refused: this rewrites shared tables other sessions read. Check that none is running, then call "
              "rebuild_shared_tables(confirm=True).")
        return None
    args = ["src/eda/data_continuity/rebuild_stage0.py"]
    if skip_ttt:
        args.append("--skip-ttt")
    if expect:
        args += ["--expect", str(expect)]
    return run_step(Step("rebuild_shared_tables", args, note="about 50 minutes"), dry_run=dry_run, echo=True)


# --- the lower-level feed and the coverage alarm (13 Oct 2026, docs/studies/data_gaps_2026/) --------------------------
FEED_JOBS = ("tennislive", "wta", "feed", "coverage")
COVERAGE_WEEKLY = CFG.ROOT / "data" / "studies" / "data_gaps_2026" / "coverage" / "weekly" / "summary.json"
FEED_RUNS = CFG.ROOT / "data" / "studies" / "data_gaps_2026" / "feed" / "runs.jsonl"


def lower_level_feed(only: list[str] | tuple[str, ...] | None = None, *, override_pause: bool = False,
                     dry_run: bool = False) -> StepResult:
    """The lower-level feed's task by hand (src/ingest/scheduled.py --weekly; the Windows task "Tennis predictions -
    lower-level feed" runs it every day at 12:00, TennisLive daily and the rest on Wednesdays): TennisLive's listings to
    yesterday, the WTA API's last five weeks, the feed's snapshot (about 50 minutes) and the coverage check. `only` picks
    jobs among FEED_JOBS. The levels Tennis My Life does not publish (ITF, WTA 125, women's qualifying, men's Challenger
    qualifying) reach every build and prediction run through this feed (docs/decisions/2026-10-13-lower-level-feed.md)."""
    jobs = list(only or FEED_JOBS)
    bad = set(jobs) - set(FEED_JOBS)
    if bad:
        raise ValueError(f"unknown jobs {sorted(bad)}; known: {FEED_JOBS}")
    _refuse_paused([j for j in jobs if j in ("tennislive", "wta")], override_pause)
    return run_step(Step("lower_level_feed", ["-m", "src.ingest.scheduled", "--weekly", "--no-notify", "--only",
                                              ",".join(jobs)], ok_codes=(0, 1), note="up to an hour with the feed"),
                    dry_run=dry_run)


def feed_status() -> dict:
    """The feed's current snapshot (accepted.json), its last run (feed/runs.jsonl) and the coverage alarm of the last
    check (coverage/weekly/summary.json): the cells whose matches or box scores fell below 70% of the same months one
    and two years earlier."""
    out: dict = {}
    acc = CFG.ROOT / "data" / "studies" / "current_best_model" / "accepted_additions" / "accepted.json"
    if acc.exists():
        cur = json.loads(acc.read_text(encoding="utf-8"))
        out["packages"], out["feeds"] = cur.get("packages", []), cur.get("feeds", {})
    if FEED_RUNS.exists():
        rows = [json.loads(x) for x in FEED_RUNS.read_text(encoding="utf-8").splitlines() if x.strip()]
        if rows:
            out["last_feed_run"] = {k: rows[-1].get(k) for k in ("label", "exit", "why", "finished_at", "snapshot")}
    if COVERAGE_WEEKLY.exists():
        s = json.loads(COVERAGE_WEEKLY.read_text(encoding="utf-8"))
        out["coverage"] = {"as_of": s.get("as_of"), "alarm": s.get("alarm_cells", []),
                           "acknowledged": s.get("acknowledged", [])}
    return out


# --- the two usual sequences ---------------------------------------------------------------------------------------------
def morning_refresh(*, max_age_hours: float = 6, dry_run: bool = False) -> dict:
    """Before a bet: box scores first. The 07:30 task normally did it; results or serve speeds last fetched more than
    `max_age_hours` ago are fetched again now (results, then speeds: stage 2 reads each player's speed form, and an
    evening slate, e.g. the Asian swing, comes about 12 hours after the 07:30 run). Reports held files and alerts.
    The prediction run itself downloads Tennis My Life again and fills recent WTA gaps (its --refresh), not speeds."""
    now = dt.datetime.now().astimezone()
    out = {"ran": []}
    for job in ("tml", "speeds"):
        last = last_run_of(job)
        out[f"{job}_last_run"] = last.isoformat(timespec="minutes") if last else None
        if last is None or (now - last).total_seconds() > max_age_hours * 3600:
            out["ran"].append(job)
    if out["ran"]:
        print(f"Fetched more than {max_age_hours:g} h ago (or never): {out['ran']}; running now.")
        scheduled_downloads(only=out["ran"], dry_run=dry_run)
    else:
        print(f"Results and speeds were fetched within the last {max_age_hours:g} h.")
    last = scheduled_runs(last=1)
    if last:
        out["last_run"] = {"started": last[-1].get("started_at"),
                           "exits": {j: v.get("exit") for j, v in last[-1].get("jobs", {}).items()
                                     if isinstance(v, dict) and "exit" in v},
                           "alerts": last[-1].get("alerts", [])}
        for a in out["last_run"]["alerts"]:
            print("ALERT:", a)
    out["held_tml"] = held_tml_files()
    if out["held_tml"]:
        print("Held Tennis My Life files (kept out until reviewed):", ", ".join(out["held_tml"]))
    out["feed"] = feed_status()
    feeds = out["feed"].get("feeds") or {}
    print("Lower-level feed:", ", ".join(f"{k} {v}" for k, v in feeds.items()) or "none accepted yet")
    for cell in (out["feed"].get("coverage") or {}).get("alarm", [])[:12]:
        print("COVERAGE:", cell)
    from .train import show_model_age
    out["model_age"] = show_model_age()            # the owner's timer (20 Oct 2026): how old the training rows are
    return out


def weekly_update(*, timeline: bool = True, odds: bool = True, rebuild: bool = False, confirm_rebuild: bool = False,
                  dry_run: bool = False) -> dict:
    """Before a model rebuild (or weekly): results and speeds, the timeline sources, the odds history, then (only when
    asked, with confirm_rebuild=True) the shared tables' rebuild. R2's ordered sequence (process log, 09:38)."""
    out = {"downloads": scheduled_downloads(only=["tml", "speeds"], dry_run=dry_run)}
    if timeline:
        out["timeline"] = refresh_timeline_sources(dry_run=dry_run)
    if odds:
        out["odds"] = refresh_odds_history(dry_run=dry_run)
    if rebuild:
        out["rebuild"] = rebuild_shared_tables(confirm=confirm_rebuild, dry_run=dry_run)
    return out
