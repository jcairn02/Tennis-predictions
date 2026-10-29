"""The ATP Stats Centre's Infosys files of 2025-2026, tour level and Challengers (work package P9 of
docs/studies/gap_downloads/collection-plan.md), kept exactly as served. Decryption happens at staging
(infosys_atp_recent_stage.py), never here.

atptour.com's Stats Centre pages load each match's data from itp-atp-sls.infosys-platforms.com as JSON envelopes
``{lastModified, response, data: null}`` (``response`` is AES ciphertext the page's own script decrypts). Collection and
decryption of these files, every edition, are approved (docs/decisions/2026-10-08-scraping-approved.md).

Routes (the four static files of infosys_atp.py, and the two API routes the plan names for current-season files whose
static copy is not written yet; the host writes its static copies in batches, months after the match):
    keystats         static/prod/stats-plus/<year>/<event>/<MID>/keystats.json    key statistics per set, the speeds
    match-beats      static/prod/match-beats/<year>/<event>/<MID>/data.json       every point, with the serve's speed
    rally-analysis   static/prod/rally-analysis/<year>/<event>/<MID>/data.json    every point by rally length
    court-vision     static/prod/court-vision/<year>/<event>/<MID>/data.json      Hawk-Eye tracking per point
    keystats-api     prod/api/stats-plus/v1/keystats/year/<y>/eventId/<e>/matchId/<MID>
    match-beats-api  prod/api/match-beats/data/year/<y>/eventId/<e>/matchId/<MID>
A missing static file is answered by S3 with HTTP 403 AccessDenied (read as "no such object" only on a route that has
served a file to these headers: the calibration rule of infosys_atp.py); a missing API file with HTTP 404.

The plan: ManTennisData's matches (data/dump/matches/mantennisdata/; refresh it first with
``./python.sh -m src.ingest.public_dump.mantennisdata --commit latest``) of series "atp", "1000" (tour level: the 250s,
500s, Masters, the Finals, the United Cup, the Laver Cup) and "ch" (Challengers) whose event began between --since and
--until, each match's ATP code read from its atptour.com stats link (MS001 the final; QS codes the qualifying;
infosys_atp.load_plan). The Slams are not on this host; rows without a stats link (mostly walkovers) are not asked for.
Events run tour level first, then Challengers, each newest first.

Order of work (each step skips what the receipts already hold):
    calibrate  one file per static route that the host served in the 29 Sep 2026 probe
               (data/studies/gap_sources/atp_statscentre_probe.csv); all four are plan files
    discover   each event's final on the static routes; where none has it, the next code (a semi-final) on key
               statistics and Court Vision; where still none, the final on the API routes (--api)
    expand     each event with a file: per route and family (MS, QS), every code once a file has been seen there,
               until then codes in order until the first --skip-after are all absent (--cold-skip-after on a route
               whose discovery found nothing). The API routes are asked only for codes whose static copy is not
               held, per --api
Nothing another raw folder holds is asked again (``held_elsewhere``): the encrypted backfill's folder
data/raw/point_sources/infosys_atp/ (the P6 data issues' Challenger files of 2021-24 and the backfill's calibration
files, any purpose) and the daily speed collector's 2026 key statistics (data/raw/point_sources/infosys_atp_daily/,
work package P9 step 5); staging reads those from where they are.

One collector per host (the plan's rule 3). The daily speed collector (src/ingest/speed_daily.py, the Windows task at
07:30 local, which also runs on wake when the PC slept through it) and prediction runs' box-score fills
(src/eda/prediction_run/fills.py, inside ``dp.py run_day --refresh`` and ``prediction_run/run.py --refresh``) use this
host. Before every request this collector waits (``HostShare``) while:
    a process whose command line names one of those jobs is running (checked every 20 s);
    the daily collector's receipts were written in the last 5 minutes;
    the local time is inside --quiet-window (default 07:20-08:00, around the daily task's start).

Practice (the decision's): about 2 s between requests plus up to 1 s of jitter, a --max-requests budget, every answer
saved as served (gzipped) with a receipt, nothing fetched twice (a 404 or an S3 "no such object" recorded once as
absent), and a stop and report on any block (feeds.FeedClient: HTTP 429, a challenge page, a redirect, or an
unexpected 403; a connection reset is asked again once after --reset-wait, and stops the run when it repeats), or after
--streak answers in a row without a document (feeds.FailureStreak).

Raw: data/raw/point_sources/infosys_atp_recent/<year>/<event>/<route>/<MID>.json.gz and _receipts.jsonl; run logs in
_logs/. These are the only copies.
Evidence (data/studies/serve_speed_acquisition/):
    infosys_atp_recent_summary.json   the last run: requests, answers by year, series and route, events by outcome
    infosys_atp_recent_events.csv     one row per event in the plan: codes, its outcome, files and absences per route
    runs.jsonl                        one line per run (shared with the study's other adapters)

Usage:
    ./python.sh -m src.ingest.point_sources.infosys_atp_recent --plan-only                 # the plan, no request
    ./python.sh -m src.ingest.point_sources.infosys_atp_recent --events 2025:418,2026:1763 --max-requests 300
    ./python.sh -m src.ingest.point_sources.infosys_atp_recent --max-requests 30000        # the bulk, resumable
    ./python.sh -m src.ingest.point_sources.infosys_atp_recent --stage-only                # decrypt and stage, no HTTP
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F
from src.ingest.point_sources import infosys_atp as A

SOURCE = "infosys_atp_recent"
DECISION = "docs/decisions/2026-10-08-scraping-approved.md"
PLAN_DOC = "docs/studies/gap_downloads/collection-plan.md (P9)"
STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "serve_speed_acquisition"
LOGS = P.raw_path(SOURCE, "_logs")
HOST = A.HOST
HEADERS = A.HEADERS
ROUTES = {
    "keystats": "/static/prod/stats-plus/{year}/{event}/{mid}/keystats.json",
    "match-beats": "/static/prod/match-beats/{year}/{event}/{mid}/data.json",
    "rally-analysis": "/static/prod/rally-analysis/{year}/{event}/{mid}/data.json",
    "court-vision": "/static/prod/court-vision/{year}/{event}/{mid}/data.json",
    "keystats-api": "/prod/api/stats-plus/v1/keystats/year/{year}/eventId/{event}/matchId/{mid}",
    "match-beats-api": "/prod/api/match-beats/data/year/{year}/eventId/{event}/matchId/{mid}",
}
STATIC = ("keystats", "match-beats", "rally-analysis", "court-vision")
API_TWIN = {"keystats": "keystats-api", "match-beats": "match-beats-api"}
TWIN_OF = {v: k for k, v in API_TWIN.items()}
SERIES = ("atp", "1000", "ch")
TOUR_SERIES = A.TOUR_SERIES
# served to these headers on 29 Sep 2026 (data/studies/gap_sources/atp_statscentre_probe.csv): Canada 2026's final
# (key statistics, Court Vision), Shanghai 2025's final (MatchBeats, read in full), Washington 2025's (rally analysis)
CALIBRATION = {"keystats": (2026, 421, "MS001"), "match-beats": (2025, 5014, "MS001"),
               "rally-analysis": (2025, 418, "MS001"), "court-vision": (2026, 421, "MS001")}
GUARD_ROUTES = A.GUARD_ROUTES
API_MODES = ("never", "fallback", "always")
# a body this small is an envelope of an empty document: Court Vision serves {"courtVisionData": []} for events without
# tracking (88 bytes as served; Tokyo 2026's final, 16 Oct 2026). It is kept like any file, but counts as no data
EMPTY_BYTES = 200
EVENT_STATES = ("files", "empty", "unknown", "not asked", "no codes")
OTHER_FOLDERS = {"infosys_atp": P.raw_path("infosys_atp"), "infosys_atp_daily": P.raw_path("infosys_atp_daily")}
DAILY = "infosys_atp_daily"
# the other jobs on this host: (label, a pattern of the command line, at most this old in seconds or None). The daily
# task's own process runs Tennis My Life first and the speed job right after it, so its first 20 minutes count too.
HOST_JOBS = (
    ("the daily speed job", re.compile(r"speed_daily"), None),
    ("the daily task's first 20 minutes", re.compile(r"-m\s+src\.ingest\.scheduled(?!.*--weekly)"), 20 * 60),
    ("a bet-day run's box-score fills", re.compile(r"\brun_day\b.*--refresh"), None),
    ("a prediction run's refresh", re.compile(r"prediction_run[/\\.]run(\.py)?\b.*--refresh"), None),
    ("the 2015-2021 backfill adapter", re.compile(r"point_sources[/\\.]infosys_atp(\.py)?(\s|$)"), None),
    ("the P6 Challenger download", re.compile(r"point_sources[/\\.]infosys_challengers(\.py)?(\s|$)"), None),
)
SELF = re.compile(r"point_sources[/\\.]infosys_atp_recent(\.py)?(\s|$)(?!.*--(stage|plan)-only)")


# --------------------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------------------
def tier(ev: A.Event) -> str:
    return "tour" if ev.series in TOUR_SERIES else "ch"


def load_plan(years: list[int], since: str, until: str, series=SERIES, events: set[tuple[int, int]] | None = None,
              root: Path | None = None) -> list[A.Event]:
    """The plan's events (infosys_atp.load_plan over ``series``), tour level first, then Challengers, each newest
    first. ``events``: only these (year, event id)."""
    plan = A.load_plan(years, since, until, root=root, series=series)
    if events:
        plan = [ev for ev in plan if (ev.year, ev.event) in events]
    return sorted(plan, key=lambda ev: (tier(ev) != "tour", -int(ev.start or 0), -ev.event))


def url_of(year: int, event: int, route: str, mid: str) -> str:
    return HOST + ROUTES[route].format(year=year, event=event, mid=mid)


def dest_of(year: int, event: int, route: str, mid: str) -> Path:
    return P.raw_path(SOURCE, str(year), str(event), route, f"{mid}.json.gz")


def receipt_name(year: int, event: int, route: str, mid: str) -> str:
    return f"{year}/{event}/{route}/{mid}"


def daily_complete() -> set[tuple[int, int, str]] | None:
    """(year, event, MID) of the daily collector's key statistics that its own staging read as a completed match (a
    file fetched while the match was being played is partial, and is asked again here); None when unreadable."""
    try:
        from src.eda.serve_speed_tabpfn.live import staging as ST
        st = ST.read_all()
    except Exception:  # noqa: BLE001 - the collector runs without the live study's tables
        return None
    if st.empty:
        return set()
    st = st[st["source"].eq(DAILY) & st["match_completed"].astype("boolean").fillna(False)]
    return {(int(y), int(e), str(m).upper()) for y, e, m in zip(st["year"], st["event_id"], st["match_code"])}


def held_elsewhere(folders: dict[str, Path] | None = None, complete=daily_complete) -> dict[tuple, str]:
    """(year, event, route, MID) -> folder, for every file another raw folder of this host holds served: the backfill
    folder (any purpose: P6's Challenger files, the calibration files) and the daily collector's key statistics of a
    completed match. A key-statistics file stands for both key-statistics routes (the same document)."""
    folders = OTHER_FOLDERS if folders is None else folders
    out: dict[tuple, str] = {}
    for name, folder in folders.items():
        if not (folder / "_receipts.jsonl").exists():
            continue
        done = complete() if name == DAILY else None
        for rec in receipts_at(folder).all().values():
            if not A.served(rec) or not rec.get("dest") or not (P.PROJECT_ROOT / rec["dest"]).exists():
                continue
            parts = str(rec.get("name", "")).split("/")
            if len(parts) != 4 or not parts[0].isdigit() or not parts[1].isdigit():
                continue
            year, event, route, mid = int(parts[0]), int(parts[1]), parts[2], parts[3].upper()
            if done is not None and (year, event, mid) not in done:
                continue
            out[(year, event, route, mid)] = name
            if route in ("keystats", "keystats-api"):
                out.setdefault((year, event, "keystats-api" if route == "keystats" else "keystats", mid), name)
    return out


def receipts_at(folder: Path):
    from src.ingest.public_dump import common as C
    return C.Receipts(folder.name, root=folder.parent)


class Held:
    """held_elsewhere(), read again whenever another folder's receipts change (the daily collector writes while a
    long run goes on)."""

    def __init__(self, folders: dict[str, Path] | None = None, complete=daily_complete):
        self.folders = OTHER_FOLDERS if folders is None else folders
        self.complete = complete
        self._stamp = None
        self._held: dict[tuple, str] = {}

    def _now_stamp(self):
        out = []
        for folder in self.folders.values():
            try:
                out.append((folder / "_receipts.jsonl").stat().st_mtime_ns)
            except OSError:
                out.append(None)
        return tuple(out)

    def get(self) -> dict[tuple, str]:
        stamp = self._now_stamp()
        if stamp != self._stamp:
            self._held, self._stamp = held_elsewhere(self.folders, self.complete), stamp
        return self._held


# --------------------------------------------------------------------------------------
# sharing the host
# --------------------------------------------------------------------------------------
def cmd_text(cmd) -> str:
    return " ".join(str(c) for c in cmd) if isinstance(cmd, (list, tuple)) else str(cmd or "")


def job_running(procs, jobs=HOST_JOBS, own_pid: int | None = None) -> str | None:
    """The first other job on this host among ``procs`` ((pid, command line, age in seconds) triples), else None."""
    for pid, cmd, age in procs:
        if own_pid is not None and pid == own_pid:
            continue
        text = cmd_text(cmd)
        for label, pattern, max_age in jobs:
            if pattern.search(text) and (max_age is None or age is None or age < max_age):
                return f"{label}, pid {pid}"
    return None


def other_collector(procs, own_pid: int | None = None) -> str | None:
    """Another fetching run of this collector (not --stage-only or --plan-only), else None."""
    for pid, cmd, _ in procs:
        if pid != own_pid and SELF.search(cmd_text(cmd)):
            return f"pid {pid}: {cmd_text(cmd)}"
    return None


def python_procs():
    """(pid, command line, age in seconds) of every running Python process."""
    import psutil
    out, now = [], time.time()
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if "python" in (proc.info["name"] or "").lower():
                out.append((proc.info["pid"], proc.info["cmdline"] or [], now - (proc.info["create_time"] or now)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def parse_window(text: str | None) -> tuple[dt.time, dt.time] | None:
    if not text or text.lower() in ("none", "off", ""):
        return None
    a, b = (dt.time.fromisoformat(x.strip()) for x in text.split("-"))
    return a, b


def in_window(now: dt.datetime, window) -> bool:
    if window is None:
        return False
    a, b = window
    t = now.time()
    return a <= t < b if a <= b else (t >= a or t < b)


class HostShare:
    """Waits before a request while another job uses the host (module docstring)."""

    def __init__(self, window=None, receipts_quiet: float = 300.0, scan_every: float = 20.0, poll: float = 30.0,
                 daily_receipts: Path | None = None, procs=python_procs, now=dt.datetime.now,
                 clock=time.time, sleep=time.sleep, log=P.log):
        self.window = window
        self.receipts_quiet = receipts_quiet
        self.scan_every = scan_every
        self.poll = poll
        self.daily_receipts = daily_receipts if daily_receipts is not None else \
            OTHER_FOLDERS[DAILY] / "_receipts.jsonl"
        self.procs, self.now, self.clock, self.sleep, self.log = procs, now, clock, sleep, log
        self.own_pid = os.getpid()
        self._last_scan = -1e18
        self._job: str | None = None
        self.waited = 0.0
        self.waits: Counter = Counter()

    def busy(self) -> tuple[str, str] | None:
        """(kind, detail) of what holds the host now, else None."""
        if in_window(self.now(), self.window):
            return "quiet window", "the quiet window around the daily task"
        try:
            age = self.clock() - self.daily_receipts.stat().st_mtime
            if age < self.receipts_quiet:
                return "daily receipts", f"the daily collector's receipts were written {age:.0f} s ago"
        except OSError:
            pass
        if self.clock() - self._last_scan >= self.scan_every:
            self._last_scan = self.clock()
            self._job = job_running(self.procs(), own_pid=self.own_pid)
        return ("another job", f"another job on this host is running ({self._job})") if self._job else None

    def wait(self) -> None:
        state, started = self.busy(), self.clock()
        if not state:
            return
        self.log(f"[{SOURCE}] waiting: {state[1]}")
        while state:
            self.waits[state[0]] += 1
            self.sleep(self.poll)
            if self._job:
                self._last_scan = -1e18                                     # re-scan at once while a job was seen
            state = self.busy()
        self.waited += self.clock() - started
        self.log(f"[{SOURCE}] resuming after {self.clock() - started:.0f} s")


class SharedClient(F.FeedClient):
    """The official feeds' client, waiting on HostShare before each request. A connection reset, which the feeds'
    client takes for a block at once, is asked again once after ``reset_wait`` seconds; a second reset in a row stops
    the run (17 Oct 2026: one reset on a 2 MB Court Vision file ended the first bulk run after 11 hours, while the
    host went on serving the daily collector every day)."""

    def __init__(self, *args, share: HostShare | None = None, reset_wait: float = 120.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.share = share
        self.reset_wait = reset_wait
        self.resets = 0

    def get(self, url: str, headers: dict | None = None):
        if self.share is not None:
            self.share.wait()
        try:
            return super().get(url, headers=headers)
        except P.Blocked as err:
            if not str(err).startswith("connection reset") or self.reset_wait <= 0:
                raise
            self.resets += 1
            P.log(f"[{SOURCE}] {err}; asking once more in {self.reset_wait:.0f} s")
            self._sleep(self.reset_wait)
            if self.share is not None:
                self.share.wait()
            return super().get(url, headers=headers)         # a second reset in a row raises Blocked

    def stats(self) -> dict:
        return {**super().stats(), "connection_resets_retried": self.resets}


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
class Run:
    """One run's state: the client, receipts, calibration, the files held elsewhere, and its counts."""

    def __init__(self, client, receipts, cal: A.Calibration, args, held: Held | dict | None = None):
        self.client, self.receipts, self.cal, self.args = client, receipts, cal, args
        self._held = held if held is not None else {}
        self.outcomes: Counter = Counter()
        self.notes: list[dict] = []
        self.streak = F.FailureStreak(limit=args.streak) if getattr(args, "streak", 0) else None

    @property
    def held(self) -> dict[tuple, str]:
        return self._held.get() if isinstance(self._held, Held) else self._held

    def fetch(self, ev: A.Event, route: str, mid: str, purpose: str = "plan") -> dict:
        key = (ev.year, ev.event, route, mid)
        folder = self.held.get(key)
        if folder:
            self.outcomes[f"{ev.year}:{tier(ev)}:{route}:held:{folder}"] += 1
            return {"name": receipt_name(*key), "status": 200, "skipped": True, "held_elsewhere": folder}
        self.cal.current = route
        rec = P.fetch(self.client, url_of(*key), dest_of(*key), self.receipts, name=receipt_name(*key),
                      refresh=self.args.refresh, validator=A.envelope_validator, compress=True, headers=HEADERS,
                      absent=self.cal.not_found,
                      extra={"year": ev.year, "event_id": ev.event, "route": route, "match_id": mid,
                             "series": ev.series, "purpose": purpose})
        if A.served(rec) and not rec.get("skipped"):
            self.cal.ok.add(route)
        self.outcomes[f"{ev.year}:{tier(ev)}:{route}:{A.outcome_of(rec)}"] += 1
        if self.streak is not None:
            self.streak.note(rec)
        return rec


def calibrate(run: Run, plan_events: dict[tuple[int, int], A.Event], routes: list[str]) -> None:
    """One known-served file per static route, unless the receipts already show that route serving."""
    for route in routes:
        if route not in STATIC or route in run.cal.ok:
            continue
        year, event, mid = CALIBRATION[route]
        ev = plan_events.get((year, event)) or A.Event(year, event, "calibration", "", "", series="")
        rec = run.fetch(ev, route, mid, purpose="calibration")
        if not A.served(rec):
            raise P.Blocked(f"calibration file {receipt_name(year, event, route, mid)} was not served "
                            f"({A.outcome_of(rec)}), so S3's 403 cannot be read on {route}")


def is_empty(rec: dict) -> bool:
    """Served, but an envelope of an empty document (EMPTY_BYTES); a file held elsewhere counts as data."""
    return A.served(rec) and not rec.get("held_elsewhere") and int(rec.get("bytes") or 0) < EMPTY_BYTES


def has_data(rec: dict) -> bool:
    return A.served(rec) and not is_empty(rec)


def static_routes(routes: list[str]) -> list[str]:
    return [r for r in routes if r in STATIC]


def api_routes(routes: list[str], mode: str) -> list[str]:
    return [] if mode == "never" else [API_TWIN[r] for r in routes if r in API_TWIN]


def discover(run: Run, ev: A.Event, routes: list[str]) -> dict[str, bool]:
    """Which routes hold data for the event's first code (on GUARD_ROUTES also its second, when no static route has
    the first); the API routes are asked the first code when no static route has data (--api fallback), or always
    (--api always). An empty document is not data."""
    hits = {route: has_data(run.fetch(ev, route, ev.codes[0])) for route in static_routes(routes)}
    if not any(hits.values()) and len(ev.codes) > 1:
        for route in GUARD_ROUTES:
            if route in hits and has_data(run.fetch(ev, route, ev.codes[1])):
                hits[route] = True
    if run.args.api == "always" or (run.args.api == "fallback" and not any(hits.values())):
        for twin in api_routes(routes, run.args.api):
            hits[twin] = has_data(run.fetch(ev, twin, ev.codes[0]))
    return hits


def ask_family(run: Run, ev: A.Event, route: str, codes: list[str], skip_after: int, family: str,
               why: str) -> None:
    """Codes in order; once data has been seen every code is asked, until then the family is given up after
    ``skip_after`` answers without data (absent, or an empty document; 0: never)."""
    misses, seen = 0, False
    for mid in codes:
        rec = run.fetch(ev, route, mid)
        if has_data(rec):
            seen = True
        elif not seen and (A.is_absent(rec) or is_empty(rec)):
            misses += 1
            if skip_after and misses >= skip_after:
                run.notes.append({"event": ev.key, "name": ev.name, "route": route, "family": family,
                                  "reason": f"the first {misses} codes {why} have no data", "last_code": mid})
                return


def static_held(run: Run, ev: A.Event, route: str, mid: str) -> bool:
    """The static file of a code is held with data (here or elsewhere)."""
    key = (ev.year, ev.event, route, mid)
    if key in run.held:
        return True
    rec = run.receipts.get(receipt_name(*key))
    return bool(rec) and has_data(rec) and dest_of(*key).exists()


def expand(run: Run, ev: A.Event, routes: list[str], hits: dict[str, bool]) -> None:
    """Every code of an event with a file (module docstring)."""
    families: dict[str, list[str]] = defaultdict(list)
    for mid in ev.codes:
        families[mid[:2]].append(mid)
    if any(hits.get(r) for r in static_routes(routes)):
        for route in static_routes(routes):
            skip = run.args.skip_after if hits.get(route) else \
                run.args.cv_cold_skip_after if route == "court-vision" else run.args.cold_skip_after
            for family, codes in families.items():
                ask_family(run, ev, route, codes, skip, family, "asked")
    for twin in api_routes(routes, run.args.api):
        skip = run.args.skip_after if hits.get(twin) else run.args.cold_skip_after
        for family, codes in families.items():
            wanted = [m for m in codes if not static_held(run, ev, TWIN_OF[twin], m)]
            if wanted:
                ask_family(run, ev, twin, wanted, skip, family, "without a static copy")


# --------------------------------------------------------------------------------------
# evidence
# --------------------------------------------------------------------------------------
def event_state(ev: A.Event, recs: dict[tuple[str, str], dict], held: dict, routes: list[str]) -> str:
    """files: a file is held (here or elsewhere); empty: every discovery answer was "no such object"; unknown: an
    answer was an error; not asked: the discovery is incomplete."""
    if not ev.codes:
        return "no codes"
    if any(has_data(r) for r in recs.values()) or any(k[:2] == (ev.year, ev.event) for k in held):
        return "files"
    asked = [(r, ev.codes[0]) for r in static_routes(routes)]
    if len(ev.codes) > 1:
        asked += [(r, ev.codes[1]) for r in GUARD_ROUTES if r in routes]
    answers = [recs.get(k) for k in asked]
    if any(a is not None and a.get("error") for a in answers):
        return "unknown"
    if all(a is not None and (A.is_absent(a) or is_empty(a)) for a in answers):
        return "empty"
    return "not asked"


def write_evidence(receipts, plan: list[A.Event], routes: list[str], held: dict,
                   study_root: Path | None = None) -> dict:
    """infosys_atp_recent_events.csv from the receipts; returns the summary's counts."""
    study_root = study_root or STUDY_ROOT
    study_root.mkdir(parents=True, exist_ok=True)
    by_event: dict[tuple[int, int], dict[tuple[str, str], dict]] = defaultdict(dict)
    by_year_route: dict[str, Counter] = defaultdict(Counter)
    for name, rec in receipts.all().items():
        parts = name.split("/")
        if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
            by_event[(int(parts[0]), int(parts[1]))][(parts[2], parts[3])] = rec
            c = by_year_route[f"{parts[0]}|{rec.get('series') or '?'}|{parts[2]}"]
            c["files" if has_data(rec) else "empty" if is_empty(rec) else "absent" if A.is_absent(rec)
              else "errors"] += 1
            c["bytes"] += int(rec.get("bytes") or 0) if A.served(rec) else 0
    held_by_event: dict[tuple[int, int], dict] = defaultdict(dict)
    for (year, event, route, mid), folder in held.items():
        held_by_event[(year, event)][(route, mid)] = folder
    rows, states = [], defaultdict(Counter)
    for ev in plan:
        recs = by_event.get((ev.year, ev.event), {})
        state = event_state(ev, recs, {k: v for k, v in held.items() if k[:2] == (ev.year, ev.event)}, routes)
        states[f"{ev.year}|{tier(ev)}"][state] += 1
        here = {mid for (_, mid), r in recs.items() if has_data(r)}
        there = {mid for (_, mid) in held_by_event.get((ev.year, ev.event), {})}
        row = {"year": ev.year, "event_id": ev.event, "name": ev.name, "series": ev.series, "level": ev.level,
               "start": ev.start, "codes": len(ev.codes), "codes_ms": sum(c.startswith("MS") for c in ev.codes),
               "codes_qs": sum(c.startswith("QS") for c in ev.codes), "uncoded_rows": ev.uncoded, "state": state,
               "matches_with_a_file": len(here | there)}
        for route in routes:
            row[f"files_{route}"] = sum(1 for (r, _), x in recs.items() if r == route and has_data(x)) + \
                sum(1 for (r, _) in held_by_event.get((ev.year, ev.event), {}) if r == route)
            row[f"empty_{route}"] = sum(1 for (r, _), x in recs.items() if r == route and is_empty(x))
            row[f"absent_{route}"] = sum(1 for (r, _), x in recs.items() if r == route and A.is_absent(x))
        row["errors"] = sum(1 for x in recs.values() if x.get("error"))
        rows.append(row)
    cols = (["year", "event_id", "name", "series", "level", "start", "codes", "codes_ms", "codes_qs", "uncoded_rows",
             "state", "matches_with_a_file"] + [f"files_{r}" for r in routes] + [f"empty_{r}" for r in routes]
            + [f"absent_{r}" for r in routes] + ["errors"])
    with (study_root / "infosys_atp_recent_events.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return {"events_by_state": {k: {s: c[s] for s in EVENT_STATES if c[s]} for k, c in sorted(states.items())},
            "by_year_series_route": {k: dict(v) for k, v in sorted(by_year_route.items())},
            "matches_in_plan_with_a_file": sum(r["matches_with_a_file"] for r in rows),
            "files_held_elsewhere_in_plan": sum(1 for k in held if any(k[:2] == (ev.year, ev.event) for ev in plan
                                                                         if k[3] in set(ev.codes)))}


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def parse_events(text: str | None) -> set[tuple[int, int]] | None:
    """'2025:418,2026:1763' -> {(2025, 418), (2026, 1763)}."""
    if not text:
        return None
    out = set()
    for part in text.split(","):
        y, _, e = part.strip().partition(":")
        if not e:
            raise SystemExit(f"--events takes year:event pairs, got {part!r}")
        out.add((int(y), int(e)))
    return out


def make_client(args, cal: A.Calibration, share: HostShare | None):
    return SharedClient(A.IMPERSONATE, not_found=cal.not_found, min_interval=args.min_interval, jitter=args.jitter,
                        max_requests=args.max_requests, timeout=args.timeout, share=share,
                        reset_wait=args.reset_wait)


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    years = A.parse_years(args.years)
    routes = [r.strip() for r in args.routes.split(",")] if args.routes else list(STATIC)
    unknown = [r for r in routes if r not in STATIC]
    if unknown:
        raise SystemExit(f"unknown routes {unknown}; known: {', '.join(STATIC)} (the API twins follow --api)")
    series = tuple(s.strip() for s in args.series.split(","))
    plan = load_plan(years, args.since, args.until or dt.date.today().strftime("%Y%m%d"), series,
                     parse_events(args.events))
    if args.limit:
        plan = plan[:args.limit]
    if not (args.plan_only or args.stage_only or args.no_share):
        other = other_collector(python_procs(), own_pid=os.getpid())
        if other:
            P.log(f"[{SOURCE}] not started: another run of this collector is fetching ({other}); one per host")
            return {"refused": other}
    receipts = P.receipts_for(SOURCE)
    holder = Held()
    held = holder.get()
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "decision": DECISION,
               "plan_doc": PLAN_DOC, "decrypted": False, "years": years, "series": list(series), "routes": routes,
               "api": args.api, "events_selected": len(plan), "matches_selected": sum(len(ev.codes) for ev in plan),
               "rows_without_a_code": sum(ev.uncoded for ev in plan),
               "codes_by_tier": dict(Counter(f"{ev.year}|{tier(ev)}" for ev in plan for _ in ev.codes)),
               "held_elsewhere": dict(Counter(held.values()))}
    if args.plan_only:
        P.log(f"[{SOURCE}] plan: {len(plan)} events, {summary['matches_selected']} codes; "
              f"{json.dumps(summary['codes_by_tier'])}")
        return summary
    if args.newer_format and not args.stage_only:
        run_newer(args, summary, receipts, holder)
    elif not args.stage_only:
        cal = A.Calibration(receipts)
        share = HostShare(window=parse_window(args.quiet_window)) if not args.no_share else None
        client = make_client(args, cal, share)
        r = Run(client, receipts, cal, args, holder)
        try:
            calibrate(r, {(ev.year, ev.event): ev for ev in plan}, routes)
            for i, ev in enumerate(plan, 1):
                if not ev.codes:
                    continue
                before = client.requests
                hits = discover(r, ev, routes)
                if any(hits.values()):
                    expand(r, ev, routes, hits)
                P.log(f"[{SOURCE}] {i}/{len(plan)} {ev.key} {ev.series} {ev.name}: {len(ev.codes)} codes; "
                      + (", ".join(k for k, h in hits.items() if h) or "no file") +
                      f"; {client.requests - before} requests; requests={client.requests}")
        except (P.Blocked, P.BudgetExhausted, F.Stopped, KeyboardInterrupt) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[{SOURCE}] STOPPED: {stop}")
        summary["client"] = client.stats()
        summary["host_share"] = {"waited_seconds": round(share.waited, 1), "polls": dict(share.waits)} if share else None
        summary["fetch_outcomes"] = dict(sorted(r.outcomes.items()))
        summary["families_given_up"] = len(r.notes)
        summary["families_given_up_examples"] = r.notes[:40]
    if not (args.newer_format and not args.stage_only):
        summary.update(write_evidence(receipts, plan, routes + api_routes(routes, "always"), holder.get()))
        errors = [x for x in receipts.all().values() if x.get("error")]
        summary["receipts"] = len(receipts.all())
        summary["receipts_with_errors"] = len(errors)
        summary["error_examples"] = [{"name": x["name"], "error": x["error"]} for x in errors[:20]]
    if not args.no_stage and (args.stage_only or not summary.get("stopped", "").startswith(("Blocked", "Stopped"))):
        from src.ingest.point_sources import infosys_atp_recent_stage as S
        try:
            summary["staged"] = S.stage(plan_years=years)
        except Exception as err:  # the fetches are done and kept whatever staging does
            summary["staging_failed"] = f"{type(err).__name__}: {err}"
            P.log(f"[{SOURCE}] STAGING FAILED ({summary['staging_failed']}); rerun with --stage-only")
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("infosys_atp_recent_summary.json", summary, root=STUDY_ROOT)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    if record_full_run(summary, args):
        P.log(f"[{SOURCE}] a full run of the plan: recorded in {P.rel(FULL_RUNS)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--years", default="2025,2026", help="comma list or ranges (default 2025,2026)")
    parser.add_argument("--since", default="20250101", help="first event start date, YYYYMMDD (default 20250101)")
    parser.add_argument("--until", default=None, help="last event start date, YYYYMMDD (default: today)")
    parser.add_argument("--series", default=",".join(SERIES), help=f"ManTennisData series (default {','.join(SERIES)})")
    parser.add_argument("--events", help="only these events, as year:event pairs (2025:418,2026:1763)")
    parser.add_argument("--limit", type=int, default=0, help="only the plan's first N events")
    parser.add_argument("--routes", help=f"static routes, comma list (default: all of {','.join(STATIC)})")
    parser.add_argument("--api", choices=API_MODES, default="fallback",
                        help="the API routes: never; fallback (default: an event whose discovery found no static "
                             "file, and codes without a static copy in an event with a file); always")
    parser.add_argument("--max-requests", type=int, default=15000, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0, help="up to this many extra seconds, drawn at random")
    parser.add_argument("--timeout", type=int, default=60, help="seconds per request (Court Vision files run to MBs)")
    parser.add_argument("--reset-wait", type=float, default=120.0,
                        help="after a connection reset, ask once more after this many seconds; a second reset in a "
                             "row stops the run (0: stop at the first, the feeds' client's own rule)")
    parser.add_argument("--skip-after", type=int, default=8,
                        help="give a route's family up when its first N codes are all absent (0: never)")
    parser.add_argument("--cold-skip-after", type=int, default=8,
                        help="the same, on a route whose discovery found no data for the event")
    parser.add_argument("--cv-cold-skip-after", type=int, default=3,
                        help="the same for Court Vision: tracking is published for a whole event's show courts (in "
                             "the 2018-21 files every event with it had it for its first 8 main-draw codes), so an "
                             "event whose final and semi-finals lack it publishes none (default 3)")
    parser.add_argument("--streak", type=int, default=400,
                        help="stop after this many answers in a row without a document (0: never)")
    parser.add_argument("--quiet-window", default="07:20-08:00",
                        help="local HH:MM-HH:MM without requests, around the daily task (default 07:20-08:00; off)")
    parser.add_argument("--no-share", action="store_true", help="do not wait for the host's other jobs (tests)")
    parser.add_argument("--refresh", action="store_true", help="fetch files already held (and absences) again")
    parser.add_argument("--newer-format", action="store_true",
                        help="ask the API's MatchBeats (the newer format) of every match whose static copy is in the "
                             "older one, one request each, from a target list frozen at the first such run "
                             "(owner, 27 Oct 2026); --limit takes the first N targets")
    parser.add_argument("--plan-only", action="store_true", help="print the plan's size and stop (no HTTP)")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP: rewrite the evidence, decrypt and stage")
    parser.add_argument("--no-stage", action="store_true", help="fetch only")


# --------------------------------------------------------------------------------------
# the newer MatchBeats format (owner, 27 Oct 2026: "Fetch the newer point-file format: yes")
# --------------------------------------------------------------------------------------
NEWER_FIELDS = ("firstServer", "lastHitter", "serveClassId", "tm1Shot", "tm2Shot", "pointDuration", "tm1AtNet",
                "tm2AtNet")
NEWER_TARGETS = STUDY_ROOT / "infosys_atp_recent_newer_targets.csv.gz"
FULL_RUNS = STUDY_ROOT / "infosys_atp_recent_full_runs.jsonl"


def older_format_targets(dump: Path | None = None) -> list[tuple[int, int, str, str, str]]:
    """(year, event, MID, series, tournament start) of every match whose MatchBeats came from the static copy and none
    of whose points carries the newer fields (NEWER_FIELDS): the matches the API's copy brings in the newer format.
    Read from the staged tables; newest tournament first."""
    import pandas as pd
    from src.ingest.point_sources import infosys_atp_recent_stage as S
    dump = dump or S.P.dump_path(SOURCE)
    pts = pd.read_parquet(dump / "points.parquet", columns=["year", "event_id", "match_id", "route", "other_fields"])
    st = pts[pts["route"].eq("match-beats")]
    newer = st["other_fields"].fillna("").str.contains("|".join(NEWER_FIELDS[:3]))
    older = newer.groupby([st["year"], st["event_id"], st["match_id"]]).any()
    older = older[~older].reset_index()[["year", "event_id", "match_id"]]
    m = pd.read_parquet(dump / "matches.parquet", columns=["year", "event_id", "match_id", "series", "tournament_start"])
    t = older.merge(m, on=["year", "event_id", "match_id"], how="left")
    t = t.sort_values(["tournament_start", "event_id", "match_id"], ascending=[False, True, True])
    return [(int(y), int(e), str(mid), str(s or ""), str(d or "")) for y, e, mid, s, d in
            zip(t["year"], t["event_id"], t["match_id"], t["series"], t["tournament_start"])]


def frozen_targets(path: Path | None = None, dump: Path | None = None) -> list[tuple[int, int, str, str, str]]:
    """The newer-format targets, frozen at the first run (a later staging takes the newer copies, so a fresh reading
    would shrink the list as the pass goes)."""
    import csv
    import gzip
    path = path or NEWER_TARGETS
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
            return [(int(r["year"]), int(r["event_id"]), r["match_id"], r["series"], r["tournament_start"])
                    for r in csv.DictReader(fh)]
    targets = older_format_targets(dump)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "event_id", "match_id", "series", "tournament_start"])
        w.writerows(targets)
    return targets


def run_newer(args, summary: dict, receipts, holder: Held) -> dict:
    """The API's MatchBeats of every frozen target, one request each; staging chooses the copy
    (infosys_atp_recent_stage.choose_matchbeats)."""
    targets = frozen_targets()
    if args.limit:
        targets = targets[:args.limit]
    summary.update(mode="newer-format", targets=len(targets), targets_file=P.rel(NEWER_TARGETS),
                   owner="27 Oct 2026: \"Fetch the newer point-file format: yes\"")
    cal = A.Calibration(receipts)
    share = HostShare(window=parse_window(args.quiet_window)) if not args.no_share else None
    client = make_client(args, cal, share)
    r = Run(client, receipts, cal, args, holder)
    names = [receipt_name(y, e, "match-beats-api", mid) for y, e, mid, _, _ in targets]
    try:
        for i, (year, event, mid, series, start) in enumerate(targets, 1):
            ev = A.Event(year, event, "", "", start, series=series)
            r.fetch(ev, "match-beats-api", mid, purpose="newer format")
            if i % 500 == 0 or i == len(targets):
                P.log(f"[{SOURCE}] newer format {i}/{len(targets)} ({year}/{event}/{mid}); requests={client.requests}")
    except (P.Blocked, P.BudgetExhausted, F.Stopped, KeyboardInterrupt) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] STOPPED: {stop}")
    summary["client"] = client.stats()
    summary["host_share"] = {"waited_seconds": round(share.waited, 1), "polls": dict(share.waits)} if share else None
    summary["fetch_outcomes"] = dict(sorted(r.outcomes.items()))
    recs = [receipts.get(n) for n in names]
    summary["answers"] = dict(Counter("not asked" if x is None else "data" if has_data(x) else "empty" if is_empty(x)
                                      else "absent" if A.is_absent(x) else "error" for x in recs))
    errors = [x for x in recs if x is not None and x.get("error")]
    summary["receipts"] = len(receipts.all())
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": x["name"], "error": x["error"]} for x in errors[:20]]
    return summary


def record_full_run(summary: dict, args, path: Path | None = None) -> bool:
    """Append a finished full-plan run (no --events or --limit, the plan done) to FULL_RUNS: the scheduled task's 2026
    top-up reminder reads it (src/ingest/scheduled.py, job p9_topup). Returns whether it was recorded."""
    path = path or FULL_RUNS
    if summary.get("stopped") or args.events or args.limit or getattr(args, "newer_format", False) \
            or args.stage_only or args.plan_only or summary.get("finished_at") is None:
        return False
    try:
        import pyarrow.parquet as pq
        commit = pq.read_table(A.MTD_ROOT / "atp_tournaments.parquet", columns=["commit"]).column(0)[0].as_py()
    except Exception:  # noqa: BLE001 - the record is still useful without it
        commit = None
    line = {"started_at": summary["started_at"], "finished_at": summary["finished_at"],
            "events_selected": summary.get("events_selected"), "matches_selected": summary.get("matches_selected"),
            "until": args.until or dt.date.today().strftime("%Y%m%d"), "mantennisdata_commit": commit,
            "requests": (summary.get("client") or {}).get("requests")}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")
    return True


EXIT = {"done": 0, "other": 1, "blocked": 2, "budget": 3, "refused": 4, "errors": 5}


def exit_code(summary: dict) -> int:
    """0 the plan is done; 3 the run's budget is used up (rerun to go on); 5 done, but some answers were errors (a
    rerun asks them again); 2 a block or a streak without documents (stop and report); 4 not started (another run
    of this collector holds the host); 1 anything else (an interruption)."""
    if summary.get("refused"):
        return EXIT["refused"]
    if summary.get("finished_at") is None:                      # --plan-only
        return EXIT["done"]
    stopped = summary.get("stopped") or ""
    if stopped.startswith("BudgetExhausted"):
        return EXIT["budget"]
    if stopped.startswith(("Blocked", "Stopped")):
        return EXIT["blocked"]
    if stopped or summary.get("staging_failed"):
        return EXIT["other"]
    return EXIT["errors"] if summary.get("receipts_with_errors") else EXIT["done"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    if summary.get("finished_at") is not None:
        P.log(f"[{SOURCE}] done in {summary['seconds']} s; {summary['receipts_with_errors']} receipts with errors"
              + (f"; stopped: {summary['stopped']}" if summary.get("stopped") else ""))
    return exit_code(summary)


if __name__ == "__main__":
    sys.exit(main())
