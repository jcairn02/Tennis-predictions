"""TennisExplorer's match odds below the tour level: Challengers, WTA 125s and ITF (main draws and qualifying), every
listed book's match-winner prices with their history, Pinnacle's among them (work package P11 of
docs/studies/gap_downloads/collection-plan.md; report in docs/studies/gap_downloads/README.md).

The tour-level adapter (src/ingest/tennisexplorer.py) keeps the tour's main draws, whose staging the model's odds input
reads. This one keeps everything below, in its own folders, so a lower-level page never reaches that staging.

The site's pages (server-rendered HTML, no login, no key):
    /results/?type=<atp|wta>-single&year=&month=&day=   a day's singles results: every match with its event header,
                                                        the two players, the books' average last price (two columns)
                                                        and its match-detail id
    /calendar/<atp-men|wta-women>/<year>/               the year's events with the site's type ("main", "lower",
                                                        "exhibitions"): main-typed events are the tour adapter's
    /match-detail/?id=<id>                              a match: per book each side's last price, every change with its
                                                        time and the opening with its time (tennisexplorer.parse_match)
Times on the site are Europe/Berlin's (summer time observed), stored in UTC.

A run goes day by day, newest first, from --until back to --since: the day's two results pages (asked again while
they are under FINAL_AFTER_DAYS old), then the page of every in-scope match the day lists with prices, not yet on disk.
In scope: men's ITF (the site lumps them as "Futures <year>", without an event page), and every event whose calendar
type is not "main" or whose slug names a Challenger, except exhibitions, leagues, team and UTR events. A match listed
without prices has no book on its page and is not asked. Each stop leaves the newest days done.

Collected under the owner's decision of 8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md) through the project's
client (src/ingest/point_sources/common.py): one request at a time, paced (2.5 s plus up to 1 s by default: the pace the
tour adapter has held for hours without a refusal), every answer gzipped with a receipt, nothing asked twice, a budget
per run, a stop on a block (HTTP 403 or 429, a challenge page). Before every request it waits while the tour-level
adapter runs (the daily pinnacle_closes job, a backfill): one collector per host (the plan's shared rule 3).

Raw (gitignored): data/raw/tennisexplorer_lower/{day/<atp|wta>/<YYYY>/<YYYY-MM-DD>.html.gz, calendar/<tour>_<year>.html.gz,
    matches/<id // 10000>/<id>.html.gz}, _receipts.jsonl, _logs/.
Staged (gitignored, data/dump/odds/tennisexplorer_lower/, one Parquet file per month and table, every column a string,
    with provenance): listed/ (every singles row of every day page), matches/ (one row per match page), odds/ (one row
    per match and book: each side's last price, opening and its time, number of changes, time of the last change),
    moves/ (every change). A month's files are rebuilt only when its raw pages changed.
Evidence (counts, never prices): data/studies/gap_downloads/tennisexplorer_lower_summary.json and runs.jsonl.

    ./python.sh -m src.ingest.tennisexplorer_lower --since 2026-10-01 --until 2026-10-07 --max-requests 300   (a trial)
    ./python.sh -m src.ingest.tennisexplorer_lower --since 2025-01-01 --max-requests 30000    (a run; rerun to resume)
    ./python.sh -m src.ingest.tennisexplorer_lower --stage-only                                (no HTTP)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest import tennisexplorer as T                    # noqa: E402
from src.ingest.point_sources import common as P              # noqa: E402
from src.ingest.public_dump import common as C                # noqa: E402

SOURCE = "tennisexplorer_lower"
RAW = C.PROJECT_ROOT / "data" / "raw" / SOURCE
DUMP = C.DUMP_ROOT / "odds" / SOURCE
STUDY = C.PROJECT_ROOT / "data" / "studies" / "gap_downloads"
BASE = "https://www.tennisexplorer.com"
TYPES = {"atp": "atp-single", "wta": "wta-single"}
FINAL_AFTER_DAYS = 3                 # a day page fetched this many days after its day is final
OUT_OF_SCOPE = re.compile(r"(?:exhibition|invitational|bundesliga|nationalliga|extraliga|league|liga|asian-games|"
                          r"olympic|davis-cup|billie-jean-king|united-cup|hopman|laver-cup|utr-|pro-series|"
                          r"next-gen|team)")
CHALLENGER = re.compile(r"(?:challenger|-chall$)")
HOST_WAIT = 60                       # seconds between checks while the tour-level adapter uses the host
HOST_WAIT_MAX = 6 * 3600             # a wait longer than this ends the run (to be resumed)


class HostBusy(RuntimeError):
    """The tour-level adapter held the host for longer than HOST_WAIT_MAX."""


# --------------------------------------------------------------------------------------------------------------------
# parsers
# --------------------------------------------------------------------------------------------------------------------
def day_rows(html: str, day: dt.date, tour: str) -> list[dict]:
    """A day's results page -> one row per listed singles match: its match-detail id, the listed time (Berlin), the
    event header and link, both players as listed ('Surname I.') with their page slugs, the two average prices as
    shown, and whether both are shown."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    tab = soup.select_one("table.result")
    if tab is None:
        return []
    rows = tab.select("tr")
    out, event, ehref = [], None, None
    for i, tr in enumerate(rows):
        if "head" in (tr.get("class") or []):
            tn = tr.select_one("td.t-name")
            a = tn.find("a", href=True) if tn is not None else None
            event = tn.get_text(" ", strip=True) if tn is not None else None
            ehref = a.get("href") if a is not None else None
            continue
        info = tr.find("a", href=re.compile(r"match-detail/\?id=\d+"))
        if info is None or not re.fullmatch(r"r\d+", tr.get("id") or "") or i + 1 >= len(rows):
            continue
        p1, p2 = tr.select_one("td.t-name a"), rows[i + 1].select_one("td.t-name a")
        t = tr.select_one("td.time")
        tm = re.search(r"\d{1,2}:\d{2}", t.get_text(" ", strip=True)) if t is not None else None
        prices = [td.get_text(strip=True) for td in tr.select("td.coursew, td.course")]
        priced = len(prices) >= 2 and all(re.fullmatch(r"\d+(?:\.\d+)?", x or "") for x in prices[:2])
        out.append({"te_id": int(re.search(r"id=(\d+)", info["href"]).group(1)), "day": day.isoformat(), "tour": tour,
                    "time_berlin": tm.group(0) if tm else None, "event": event, "event_href": ehref,
                    "p1": p1.get_text(strip=True) if p1 is not None else None,
                    "p1_slug": p1.get("href") if p1 is not None else None,
                    "p2": p2.get_text(strip=True) if p2 is not None else None,
                    "p2_slug": p2.get("href") if p2 is not None else None,
                    "avg1": prices[0] if priced else None, "avg2": prices[1] if priced else None, "priced": priced})
    return out


def event_key(href: str | None) -> tuple[str, int] | None:
    """'/lisbon-challenger/2026/atp-men/' -> ('lisbon-challenger', 2026)."""
    m = re.match(r"^/([^/]+)/(\d{4})/(?:atp-men|wta-women)/$", href or "")
    return (m.group(1), int(m.group(2))) if m else None


def in_scope(row: dict, types: dict) -> tuple[bool, str]:
    """Whether a listed match is this collector's, and why. ``types`` maps (tour, slug, year) to the calendar's type."""
    event = row.get("event") or ""
    key = event_key(row.get("event_href"))
    if key is None:
        if row["tour"] == "atp" and re.match(r"^futures\b", event.strip(), re.I):
            return True, "men's ITF (Futures)"
        return False, "no event page"
    slug, year = key
    kind = types.get((row["tour"], slug, year))
    if OUT_OF_SCOPE.search(slug):
        return False, "exhibition, league, team or UTR event"
    if kind == "exhibitions":
        return False, "exhibition"
    if CHALLENGER.search(slug):
        return True, "Challenger"
    if kind == "main":
        return False, "tour level (the tour adapter's)"
    if kind is None:
        if re.search(r"(?:^|-)itf(?:-|$)", slug) or re.search(r"\bITF\b", event):
            return True, "ITF (not on the calendar)"
        return False, "not on the calendar"
    return True, "lower"


def book_rows(te_id: int, parsed: dict) -> tuple[list[dict], list[dict]]:
    """A parsed match page's books -> (one row per book: each side's last price, opening and its time, number of
    changes and the time of the last change; one row per change, the openings flagged)."""
    orows, mrows = [], []
    for book, sides in parsed["books"].items():
        o = {"te_id": te_id, "book": book}
        for k in ("k1", "k2"):
            sd = sides[k]
            last_t = max((w for w, _ in sd["moves"] if w is not None), default=None)
            o.update({f"{k}_last": sd["last"], f"{k}_open": sd["open"][1] if sd["open"] else None,
                      f"{k}_open_t": sd["open"][0].isoformat() if sd["open"] and sd["open"][0] else None,
                      f"{k}_n_moves": len(sd["moves"]), f"{k}_last_t": last_t.isoformat() if last_t else None})
            for w, v in sd["moves"]:
                mrows.append({"te_id": te_id, "book": book, "side": k, "t_utc": w.isoformat() if w else None,
                              "odds": v, "opening": False})
            if sd["open"]:
                mrows.append({"te_id": te_id, "book": book, "side": k,
                              "t_utc": sd["open"][0].isoformat() if sd["open"][0] else None, "odds": sd["open"][1],
                              "opening": True})
        orows.append(o)
    return orows, mrows


# --------------------------------------------------------------------------------------------------------------------
# paths and the client
# --------------------------------------------------------------------------------------------------------------------
def day_path(tour: str, day: dt.date) -> Path:
    return RAW / "day" / tour / f"{day.year}" / f"{day.isoformat()}.html.gz"


def calendar_path(tour: str, year: int) -> Path:
    return RAW / "calendar" / f"{tour}_{year}.html.gz"


def match_path(te_id: int) -> Path:
    return RAW / "matches" / f"{te_id // 10000:04d}" / f"{te_id}.html.gz"


def te_validator(body: bytes):
    problem = P.html_validator(body)
    if problem:
        return problem
    head = body[:30000].lower()
    if b"captcha" in head or b"cf-chl" in head or b"<title>tennis explorer" not in head:
        return "not a TennisExplorer page (a challenge page?)"
    return None


def tour_adapter_running() -> int | None:
    """The pid of a running tour-level TennisExplorer client, or None: the adapter (python -m src.ingest.tennisexplorer,
    which the daily pinnacle_closes job and the backfills run) or the model's odds step, which refreshes the site
    in-process (src/eda/current_best_model/odds_input.py)."""
    try:
        import psutil
    except ImportError:
        return None
    me = psutil.Process().pid
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = p.info["cmdline"] or []
            if p.info["pid"] == me or "python" not in (p.info["name"] or "").lower():
                continue
            if "src.ingest.tennisexplorer" in cmd or any(str(c).replace("\\", "/").endswith("odds_input.py") for c in cmd):
                return p.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


class Fetcher:
    ERRORS_IN_A_ROW = 10             # failed answers in a row (the site down, the PC offline) end the run

    def __init__(self, max_requests: int | None, min_interval: float, jitter: float, busy=tour_adapter_running,
                 client=None, sleep=time.sleep):
        self.receipts = C.Receipts(SOURCE, root=RAW.parent)
        self.client = client or P.Client("chrome", min_interval=min_interval, jitter=jitter, max_requests=max_requests,
                                         headers={"Accept-Language": "en-US,en;q=0.9"})
        self.busy, self.sleep = busy, sleep
        self.outcomes: Counter = Counter()
        self.waited = 0.0
        self.errors_in_a_row = 0

    def wait_host(self) -> None:
        waited, pid = 0.0, self.busy()
        while pid:
            if waited == 0:
                C.log(f"[{SOURCE}] {C.utc_now_iso()} the tour-level adapter runs (pid {pid}): waiting")
            if waited >= HOST_WAIT_MAX:
                raise HostBusy(f"the tour-level adapter held the host for {waited / 3600:.1f} h")
            self.sleep(HOST_WAIT)
            waited += HOST_WAIT
            pid = self.busy()
        self.waited += waited

    def get(self, name: str, url: str, dest: Path, refresh: bool = False) -> dict:
        previous = self.receipts.get(name)
        if not refresh and previous and not previous.get("error") and (
                (previous.get("status") == 200 and dest.exists()) or previous.get("status") == 404):
            self.outcomes["cached"] += 1
            return {**previous, "skipped": True}
        self.wait_host()
        r = P.fetch(self.client, url, dest, self.receipts, name=name, refresh=refresh, validator=te_validator,
                    compress=True)
        err = str(r.get("error") or "")
        self.outcomes[str(r.get("status")) if not err else f"error {r.get('status')}"] += 1
        if err and (r.get("status") in (403, 429) or "HTTP 429" in err or "HTTP 403" in err or "challenge" in err):
            raise P.Blocked(f"{name}: {err}")                 # back off and report; never retried in a loop
        self.errors_in_a_row = self.errors_in_a_row + 1 if err else 0
        if self.errors_in_a_row >= self.ERRORS_IN_A_ROW:
            raise P.Blocked(f"{self.errors_in_a_row} failed answers in a row (last: {name}: {err})")
        return r


# --------------------------------------------------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------------------------------------------------
def fetched_on(dest: Path) -> dt.date | None:
    return dt.datetime.fromtimestamp(dest.stat().st_mtime, dt.timezone.utc).date() if dest.exists() else None


def calendar_types(f: Fetcher | None, years: set[int], today: dt.date) -> dict:
    """(tour, slug, year) -> the calendar's type. With a fetcher, a calendar is asked when missing, and again (once a
    day) until a copy fetched after its year's end is on disk."""
    types = {}
    for year in sorted(years):
        for tour, path_tour in T.TOURS.items():
            dest = calendar_path(tour, year)
            got = fetched_on(dest)
            final = got is not None and got > dt.date(year, 12, 31) + dt.timedelta(days=FINAL_AFTER_DAYS)
            if f is not None and not final and (got is None or got < today):
                f.get(f"calendar_{tour}_{year}", f"{BASE}/calendar/{path_tour}/{year}/", dest, refresh=got is not None)
            if dest.exists():
                for r in T.parse_calendar(T.read_raw(dest), tour, year):
                    types[(tour, r["slug"], year)] = r["type"]
    return types


def done_days() -> set[str]:
    """Days whose two results pages are final and whose every in-scope priced match page was answered: skipped by later
    runs without reading their pages (data/raw/tennisexplorer_lower/_state/done_days.txt, one ISO date a line)."""
    path = RAW / "_state" / "done_days.txt"
    return set(path.read_text(encoding="utf-8").split()) if path.exists() else set()


def mark_done(day: dt.date) -> None:
    path = RAW / "_state" / "done_days.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as h:
        h.write(day.isoformat() + "\n")


def run(since: dt.date, until: dt.date, f: Fetcher, today: dt.date | None = None, max_days: int | None = None) -> dict:
    """Day by day, newest first: the two results pages, then each in-scope priced match's page not on disk. A day is
    marked done once its results pages are final and each of its pages has an answer (a page or a recorded 404)."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    until = min(until, today - dt.timedelta(days=1))
    days = [until - dt.timedelta(days=i) for i in range((until - since).days + 1)]
    if max_days is not None:
        days = days[:max_days]
    done = done_days()
    todo = [d for d in days if d.isoformat() not in done]
    types = calendar_types(f, {d.year for d in todo} | {d.year - 1 for d in todo if d.month == 1}, today)
    out = {"days": 0, "days_done_before": len(days) - len(todo), "listed": 0, "in_scope": 0, "priced": 0,
           "match_pages_new": 0, "last_day": None, "finished": False, "stopped": None}
    try:
        for day in todo:
            rows, final = [], True
            for tour, typ in TYPES.items():
                dest = day_path(tour, day)
                got = fetched_on(dest)
                stale = got is not None and got < day + dt.timedelta(days=FINAL_AFTER_DAYS) and got < today
                f.get(f"day_{tour}_{day.isoformat()}", f"{BASE}/results/?type={typ}&year={day.year}"
                      f"&month={day.month:02d}&day={day.day:02d}", dest, refresh=stale)
                got = fetched_on(dest)
                final = final and got is not None and got >= day + dt.timedelta(days=FINAL_AFTER_DAYS)
                if dest.exists():
                    rows += day_rows(T.read_raw(dest), day, tour)
            out["days"] += 1
            out["listed"] += len(rows)
            answered = True
            for r in rows:
                ok, _ = in_scope(r, types)
                if not ok:
                    continue
                out["in_scope"] += 1
                if not r["priced"]:
                    continue
                out["priced"] += 1
                dest = match_path(r["te_id"])
                before = dest.exists()
                got = f.get(f"match_{r['te_id']}", f"{BASE}/match-detail/?id={r['te_id']}", dest)
                out["match_pages_new"] += int(dest.exists() and not before)
                answered = answered and not got.get("error")
            if final and answered:
                mark_done(day)
            out["last_day"] = day.isoformat()
            if out["days"] % 7 == 0:
                C.log(f"[{SOURCE}] {C.utc_now_iso()} back to {day}: {out['match_pages_new']} new match pages, "
                      f"{f.client.requests} requests")
        out["finished"] = True
    except (P.Blocked, P.BudgetExhausted, HostBusy) as stop:
        out["stopped"] = f"{type(stop).__name__}: {stop}"
        C.log(f"[{SOURCE}] STOPPED: {stop}")
    return out


# --------------------------------------------------------------------------------------------------------------------
# staging: one file per month and table, rebuilt when the month's raw pages changed
# --------------------------------------------------------------------------------------------------------------------
def stage(months: set[str] | None = None, force: bool = False) -> dict:
    """Rebuild the staged months whose raw day or match pages are newer than their files (or every month: force)."""
    receipts = C.Receipts(SOURCE, root=RAW.parent)
    by_month: dict[str, list[Path]] = {}
    for p in sorted((RAW / "day").glob("*/*/*.html.gz")):
        by_month.setdefault(p.name.split(".")[0][:7], []).append(p)
    years = {int(m[:4]) for m in by_month} | {int(m[:4]) - 1 for m in by_month}
    types = calendar_types(None, years, dt.datetime.now(dt.timezone.utc).date())
    out = Counter()
    for month, files in sorted(by_month.items()):
        if months and month not in months:
            continue
        rows = []
        for p in files:
            tour = p.parent.parent.name
            day = dt.date.fromisoformat(p.name.split(".")[0])
            rec = receipts.get(f"day_{tour}_{day.isoformat()}") or {}
            for r in day_rows(T.read_raw(p), day, tour):
                ok, why = in_scope(r, types)
                r.update(in_scope=ok, scope=why, raw=C.rel(p), sha256=rec.get("sha256"),
                         retrieved_at=rec.get("retrieved_at"))
                rows.append(r)
        newest = max(p.stat().st_mtime for p in files)
        ids = {r["te_id"] for r in rows}
        pages = [match_path(i) for i in ids if match_path(i).exists()]
        newest = max([newest] + [p.stat().st_mtime for p in pages])
        target = DUMP / "listed" / f"{month}.parquet"
        if not force and target.exists() and target.stat().st_mtime >= newest:
            out["months_unchanged"] += 1
            continue
        mrows, orows, vrows = [], [], []
        for p in pages:
            te_id = int(p.name.split(".")[0])
            try:
                d = T.parse_match(T.read_raw(p))
            except ValueError as err:
                out["unparsed"] += 1
                C.log(f"[{SOURCE}] {p.name}: {err}")
                continue
            rec = receipts.get(f"match_{te_id}") or {}
            mrows.append({"te_id": te_id, **{k: v for k, v in d.items() if k != "books"}, "n_books": len(d["books"]),
                          "has_pinnacle": "Pinnacle" in d["books"], "raw": C.rel(p), "sha256": rec.get("sha256"),
                          "retrieved_at": rec.get("retrieved_at")})
            o, v = book_rows(te_id, d)
            orows += o
            vrows += v
        for name, table in (("listed", rows), ("matches", mrows), ("odds", orows), ("moves", vrows)):
            path = DUMP / name / f"{month}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(table)
            df = df.astype("string") if len(df) else df
            tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
            df.to_parquet(tmp, index=False)
            tmp.replace(path)
            out[f"{name}_rows"] += len(df)
        out["months_rebuilt"] += 1
    return dict(out)


def summary() -> dict:
    """Counts by month (never prices): listed, in scope, priced, match pages, with Pinnacle, with times."""
    files = sorted((DUMP / "listed").glob("*.parquet"))
    out = {}
    for p in files:
        month = p.stem
        lst = pd.read_parquet(p)
        if lst.empty:
            continue
        m = pd.read_parquet(DUMP / "matches" / p.name) if (DUMP / "matches" / p.name).exists() else pd.DataFrame()
        o = pd.read_parquet(DUMP / "odds" / p.name) if (DUMP / "odds" / p.name).exists() else pd.DataFrame()
        pin = o[o.book.eq("Pinnacle")] if len(o) else o
        out[month] = {"listed": int(len(lst)), "priced": int(lst.priced.eq("True").sum()),
                      "match_pages": int(len(m)),
                      "with_pinnacle": int(m.has_pinnacle.eq("True").sum()) if len(m) else 0,
                      "pinnacle_timed": int((pin.k1_open_t.notna() | pin.k1_last_t.notna()).sum()) if len(pin) else 0}
    return out


# --------------------------------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--since", type=dt.date.fromisoformat, default=dt.date(2018, 1, 1))
    ap.add_argument("--until", type=dt.date.fromisoformat, default=None, help="default: yesterday (UTC)")
    ap.add_argument("--max-requests", type=int, default=10_000)
    ap.add_argument("--max-days", type=int, help="only the newest N days of the span (a trial)")
    ap.add_argument("--min-interval", type=float, default=2.5)
    ap.add_argument("--jitter", type=float, default=1.0)
    ap.add_argument("--stage-only", action="store_true", help="no HTTP: rebuild the changed months and the summary")
    ap.add_argument("--no-stage", action="store_true")
    ap.add_argument("--force-stage", action="store_true", help="rebuild every month")
    a = ap.parse_args(argv)
    P.configure_stdout()
    started = C.utc_now_iso()
    result, client = {}, None
    if not a.stage_only:
        f = Fetcher(a.max_requests, a.min_interval, a.jitter)
        until = a.until or (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1))
        result = run(a.since, until, f, max_days=a.max_days)
        client = {**f.client.stats(), "outcomes": dict(f.outcomes), "host_wait_seconds": f.waited}
        C.log(f"[{SOURCE}] {json.dumps(result)}")
    staged = stage(force=a.force_stage) if not a.no_stage else {}
    STUDY.mkdir(parents=True, exist_ok=True)
    data = {"source": SOURCE, "started_at": started, "finished_at": C.utc_now_iso(), "client": client,
            "run": result, "staged": staged, "by_month": summary() if not a.no_stage else None,
            "stopped": result.get("stopped")}
    P.write_summary(f"{SOURCE}_summary.json", data, root=STUDY)
    stopped = result.get("stopped") or ""
    # 0 the span is done; 3 the budget is used up; 4 the tour adapter held the host too long; 2 a block; 1 otherwise
    if a.stage_only or (result.get("finished") and not stopped):
        return 0
    return {"BudgetExhausted": 3, "HostBusy": 4, "Blocked": 2}.get(stopped.split(":")[0], 1)


if __name__ == "__main__":
    sys.exit(main())
