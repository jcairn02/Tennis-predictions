"""ITF live-data API (Stadion): every ITF World Tennis Tour match of the last 14 days, its statistics and its points.

Collected under the owner's decision of 8 Oct 2026 (docs/decisions/2026-10-08-scraping-approved.md), as work
package P1 of docs/studies/gap_downloads/collection-plan.md. The API is the one behind the ITF's "World Tennis Tour
Live" and "Live Match Centre" pages (the widget SDK at widgets.itf-production.sports-data.stadion.io); it takes no
credentials and has no robots.txt. Research: data/studies/gap_sources/research_notes/C_itf_listings.md.

Endpoints (https://api.itf-production.sports-data.stadion.io/):
    custom/wttCompleteMatchList/<YYYY-MM-DD>   every World Tennis Tour match of that day (singles and doubles, main
                                               draw and qualifying), grouped by event and court: the event (name, ITF
                                               key tennisId, grade, dates, surface, venue), draw, round, status
                                               (matchStatus.stateType "post" once over), winnerSideId, set scores,
                                               duration, dateStartLocal, actualEndDate, scheduleText, court and the
                                               match id. HTTP 422 "date must be within 14 days of today" otherwise
    custom/widgetMatchStats/<match id>         per side, per set and for the match: 34 statistic types (40 at higher
                                               grades); "data": [] (212 bytes) when the match has none. Each item
                                               repeats the match, with actualStartDate and actualEndDate
    custom/pointByPoint/<match id>             every point by set and game: server, outcome (ACE, DOUBLE_FAULT, POINT
                                               ...), the game and set score after it; "data": [] (96 bytes) when none
Only the day list is date-limited: the per-match endpoints answered for 2025 match ids on 29 Sep 2026.

Raw layout under data/raw/point_sources/itf_live/ (every answer gzipped as served, never overwritten):
    day/<date>@<run>.json.gz         one capture of a day list, named by the run that asked (UTC, YYYYMMDDTHHMMSSZ).
                                     A day is asked again on each run until it is SETTLE_DAYS old and every match on
                                     it is over; each capture is its own file, so earlier states (a schedule, a
                                     match moved to another day) stay on disk. (The plan's day/<date>.json.gz would
                                     have to be overwritten by each new capture.)
    match/<id>/stats.json.gz         widgetMatchStats, asked once
    match/<id>/points.json.gz        pointByPoint, asked once
    _receipts.jsonl                  one line per request (URL, time, status, bytes, SHA-256); answers copied in from
                                     the gap-sources research (--import-research) are marked "imported"
    _run.lock                        held by the running process (an OS lock: released when the process ends)
    _logs/                           the background and scheduled runs' output

Each run: the day lists from 14 days before today (UTC) to today, oldest first, each unless it is settled or was
captured less than --refetch-hours ago; then statistics and points, oldest list day first, for every singles match
of any day list held, not yet asked, that (doc_reason):
    is over (status stateType "post") and ended at least --settle-hours ago, or
    sits on a day at least SETTLE_DAYS old without ever reaching an over status (scoring stopped, no status).
Each match's latest listed state counts (its latest list day, then latest capture). Doubles: the lists only. A
walkover has no points played, so neither document is asked for it.

Staged (data/dump/points/itf_live/, every column a string, with provenance): events (one row per event, from its
latest capture), matches (every row of every day-list capture, with its list date and capture time; ``latest`` marks
each match's latest state), documents (one row per statistics or points answer: status, whether it holds data, its
counts, and the times the statistics answer repeats, actualStartDate among them), statistics (one row per statistic,
side and period) and points (one row per point, the two sides' views side by side). Each answer is parsed once: its
rows wait in _cache/ (keyed by receipt name and SHA-256), so a staging parses only new answers and takes seconds.
Every table is written to a .part file and renamed into place. Reports in data/studies/official_point_feeds/:
itf_live_summary.json and a line in runs.jsonl per run.

Usage:
    ./python.sh -m src.ingest.point_sources.itf_live --max-requests 6500                # a run (resumes when rerun)
    ./python.sh -m src.ingest.point_sources.itf_live --days-only --max-requests 30      # the day lists only
    ./python.sh -m src.ingest.point_sources.itf_live --no-days --limit 3 --max-requests 300   # a trial: 3 events
    ./python.sh -m src.ingest.point_sources.itf_live --stage-only                       # rebuild the tables, no HTTP
    ./python.sh -m src.ingest.point_sources.itf_live --import-research --max-requests 4500
        # copy in the research's answers of 29 Sep 2026 (the day lists of 15-29 Sep: 15-23 Sep are listed nowhere
        # else now), then fetch the statistics and points of their matches
Exit codes: 0 when the run ends normally or uses up its budget, 2 when the site refused it (a block: HTTP 403 or
429 after common.Client's back-off, or a challenge), 3 when another run holds the lock (nothing was asked), 1
otherwise (five fetches in a row without a document, failed staging, a crash).
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import gzip
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P

SOURCE = "itf_live"
API = "https://api.itf-production.sports-data.stadion.io/"
DECISION = "docs/decisions/2026-10-08-scraping-approved.md"
IMPERSONATE = "chrome"
HEADERS = {"Accept": "application/json, text/plain, */*", "Accept-Language": "en-GB,en;q=0.9"}
WINDOW_DAYS = 14   # the day list answers 422 for a date more than 14 days before today
SETTLE_DAYS = 3    # a day this old whose matches are all over is not asked again
REFETCH_HOURS = 6  # a day list captured less than this long ago is not asked again by a resumed run
SETTLE_HOURS = 2   # a match's documents are asked once it ended at least this long before the run
DOCS = {"stats": "widgetMatchStats", "points": "pointByPoint"}
STUDY = P.PROJECT_ROOT / "data" / "studies" / "official_point_feeds"
LOCK = P.raw_path(SOURCE, "_run.lock")
LOGS = P.raw_path(SOURCE, "_logs")


# --------------------------------------------------------------------------------------
# day lists: names, selection (pure functions; tested offline)
# --------------------------------------------------------------------------------------
def run_stamp(now: dt.datetime | None = None) -> str:
    return (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")


def stamp_time(stamp: str) -> dt.datetime:
    return dt.datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)


def day_url(day: str) -> str:
    return f"{API}custom/wttCompleteMatchList/{day}"


def doc_url(kind: str, match_id: str) -> str:
    return f"{API}custom/{DOCS[kind]}/{match_id}"


def day_name(day: str, stamp: str) -> str:
    return f"day/{day}@{stamp}"


def parse_day_name(name: str) -> tuple[str, str] | None:
    """day/2026-10-05@20261008T191500Z -> ("2026-10-05", "20261008T191500Z"); None for other names."""
    if not name.startswith("day/") or "@" not in name:
        return None
    day, stamp = name[4:].split("@", 1)
    return day, stamp


def day_dest(day: str, stamp: str) -> Path:
    return P.raw_path(SOURCE, "day", f"{day}@{stamp}.json.gz")


def doc_name(match_id: str, kind: str) -> str:
    return f"match/{match_id}/{kind}"


def doc_dest(match_id: str, kind: str) -> Path:
    return P.raw_path(SOURCE, "match", match_id, f"{kind}.json.gz")


def window(today: dt.date, days: int = WINDOW_DAYS) -> list[str]:
    """The days the day list serves, oldest first: today - days .. today."""
    return [(today - dt.timedelta(days=n)).isoformat() for n in range(days, -1, -1)]


def outside_window(response) -> str | None:
    """The API's refusal of a date outside its window (HTTP 422), recorded as an absence, not an error."""
    if response.status_code == 422:
        return "HTTP 422: " + response.content[:200].decode("utf-8", "replace")
    return None


def status_of(match: dict) -> tuple[str, str]:
    """(status name, stateType) of a listed match, lower-cased: ("complete", "post"), ("walkover", "post") ..."""
    status = match.get("matchStatus") or {}
    return str(status.get("_name") or status.get("name") or "").strip().lower(), \
        str(status.get("stateType") or "").strip().lower()


def is_over(match: dict) -> bool:
    return status_of(match)[1] == "post"


def is_walkover(match: dict) -> bool:
    return status_of(match)[0] == "walkover"


def discipline(match: dict) -> dict:
    return match.get("_drawDiscipline") or {}


def is_singles(match: dict) -> bool:
    return str(discipline(match).get("type") or "").strip().lower() == "singles"


def listed(doc: dict):
    """(event key, event without its courts, court name, match) for every match of a day list, in list order."""
    for key, event in ((doc or {}).get("data") or {}).items():
        if not isinstance(event, dict):
            continue
        head = {k: v for k, v in event.items() if k != "courts"}
        for court, matches in (event.get("courts") or {}).items():
            for match in matches or []:
                if isinstance(match, dict):
                    yield key, head, court, match


def all_over(doc: dict) -> bool:
    """Whether every match of a day list is over (an empty list counts as over)."""
    return all(is_over(m) for _, _, _, m in listed(doc))


def day_captures(receipts: dict) -> dict[str, list[dict]]:
    """Saved captures of each day list, oldest first: day -> [receipt, ...] (status 200, no error, file present)."""
    out: dict[str, list[dict]] = {}
    for name, receipt in receipts.items():
        parsed = parse_day_name(name)
        if not parsed or receipt.get("status") != 200 or receipt.get("error"):
            continue
        if not day_dest(*parsed).exists():
            continue
        out.setdefault(parsed[0], []).append({**receipt, "day": parsed[0], "stamp": parsed[1]})
    for caps in out.values():
        caps.sort(key=lambda r: r["stamp"])
    return out


def plan_day(day: str, today: dt.date, latest: dict | None, latest_doc: dict | None, now: dt.datetime,
             refetch_hours: float = REFETCH_HOURS, settle_days: int = SETTLE_DAYS, refused: bool = False) -> str:
    """Whether to ask for a day list on this run: "fetch", "settled" (old enough and every match over), "fresh"
    (captured less than refetch_hours ago) or "refused" (never captured, and the API has answered 422 for it: its
    window only moves forward, so it never serves that day again)."""
    if latest is None or latest_doc is None:
        return "refused" if refused else "fetch"
    if (today - dt.date.fromisoformat(day)).days >= settle_days and all_over(latest_doc):
        return "settled"
    if now - stamp_time(latest["stamp"]) < dt.timedelta(hours=refetch_hours):
        return "fresh"
    return "fetch"


def latest_state(captures: dict[str, list[dict]], read) -> dict[str, dict]:
    """Each match's latest listed state, from every saved capture: match id -> {list_date, stamp, event_key, event,
    court, match}. A match listed on several days keeps the state of its latest list day, then latest capture.
    ``read(receipt)`` returns a capture's document."""
    out: dict[str, dict] = {}
    for day in sorted(captures):
        for receipt in captures[day]:
            doc = read(receipt)
            for key, event, court, match in listed(doc):
                mid = match.get("id")
                if mid:
                    out[str(mid)] = {"list_date": day, "stamp": receipt["stamp"], "event_key": key, "event": event,
                                     "court": court, "match": match}
    return out


def parse_utc(value) -> dt.datetime | None:
    """An ISO time of the API ("2026-09-19T14:37:02Z", fractions allowed) as an aware UTC datetime, else None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def doc_reason(s: dict, today: dt.date, now: dt.datetime, settle_days: int = SETTLE_DAYS,
               settle_hours: float = SETTLE_HOURS) -> str | None:
    """Why a listed match's statistics and points are asked for, or None when they are not (yet):
    "over"     a singles match whose status is over (stateType "post") and not a walkover, which ended at least
               settle_hours before the run (its actualEndDate; without one, its list day is before today);
    "stale"    a singles match on a list day at least settle_days old that never reached an over status (scoring
               stopped, or no status at all): its partial record is the last the feed will hold.
    Walkovers (no points played) and doubles are never asked for."""
    m = s["match"]
    if not is_singles(m) or is_walkover(m):
        return None
    if is_over(m):
        ended = parse_utc(m.get("actualEndDate"))
        if ended is not None:
            return "over" if now - ended >= dt.timedelta(hours=settle_hours) else None
        return "over" if dt.date.fromisoformat(s["list_date"]) < today else None
    return "stale" if (today - dt.date.fromisoformat(s["list_date"])).days >= settle_days else None


def wanted(state: dict[str, dict], today: dt.date, now: dt.datetime, settle_hours: float = SETTLE_HOURS) -> list[dict]:
    """The listed matches whose documents are asked for (doc_reason), oldest list day first, then by event key,
    draw, round order and id; each with its ``reason``."""
    rows = []
    for s in state.values():
        reason = doc_reason(s, today, now, settle_hours=settle_hours)
        if reason:
            rows.append({**s, "reason": reason})
    return sorted(rows, key=lambda s: (s["list_date"], str(s["event"].get("tennisId") or s["event_key"]),
                                       str(s["match"].get("_drawName") or ""), s["match"].get("_roundOrder") or 0,
                                       str(s["match"]["id"])))


def event_order(rows: list[dict]) -> list[str]:
    """Event keys (ITF tennisId, else the list's key) in the order their first wanted match comes."""
    seen: dict[str, None] = {}
    for s in rows:
        seen.setdefault(str(s["event"].get("tennisId") or s["event_key"]), None)
    return list(seen)


def read_capture(receipt: dict) -> dict:
    return P.read_json(day_dest(receipt["day"], receipt["stamp"]))


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
class LockHeld(RuntimeError):
    """Another run holds _run.lock."""


class FailureStreak(RuntimeError):
    """FAILURE_STREAK fetches in a row brought no document (the network is down, or the API is failing)."""


FAILURE_STREAK = 5


class Streak:
    """Counts fetches in a row that brought no document (an error receipt), and stops the run at the limit."""

    def __init__(self, limit: int = FAILURE_STREAK):
        self.limit, self.count = limit, 0

    def note(self, receipt: dict) -> None:
        self.count = self.count + 1 if receipt.get("error") else 0
        if self.count >= self.limit:
            raise FailureStreak(f"{self.count} fetches in a row failed, the last: {receipt.get('error')} "
                                f"({receipt.get('url')})")


@contextlib.contextmanager
def run_lock():
    """One fetching run at a time: an OS lock on _run.lock, released when this process ends however it ends."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK, "a+b")
    locked = False
    try:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            raise LockHeld(f"another ITF live run is fetching (it holds {P.rel(LOCK)}); let it finish first")
        yield
    finally:
        if locked and os.name == "nt":
            import msvcrt
            handle.seek(0)
            with contextlib.suppress(OSError):
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        handle.close()


def fetch_days(client, receipts, stamp: str, today: dt.date, now: dt.datetime, refetch_hours: float,
               outcomes: Counter, log_days: list, streak: Streak) -> None:
    every = receipts.all()
    captures = day_captures(every)
    refused = {parse_day_name(name)[0] for name, r in every.items() if parse_day_name(name) and r.get("absent")}
    for day in window(today):
        caps = captures.get(day) or []
        latest = caps[-1] if caps else None
        doc = read_capture(latest) if latest else None
        decision = plan_day(day, today, latest, doc, now, refetch_hours, refused=day in refused)
        if decision != "fetch":
            outcomes[f"day:{decision}"] += 1
            log_days.append({"day": day, "decision": decision, "latest_capture": latest["stamp"] if latest else None})
            continue
        r = P.fetch(client, day_url(day), day_dest(day, stamp), receipts, name=day_name(day, stamp),
                    validator=P.json_validator, compress=True, absent=outside_window,
                    extra={"kind": "day", "day": day, "run": stamp})
        state = "absent" if r.get("absent") else "error" if r.get("error") else str(r.get("status"))
        outcomes[f"day:{state}"] += 1
        matches = None
        if state == "200":
            doc = read_capture({"day": day, "stamp": stamp})
            matches = sum(1 for _ in listed(doc))
        log_days.append({"day": day, "decision": "fetch", "state": state, "bytes": r.get("bytes"), "matches": matches,
                         "absent": r.get("absent"), "error": r.get("error")})
        P.log(f"[{SOURCE}] day {day}: {state} {r.get('bytes') or ''} bytes, {matches} matches"
              + (f" ({r.get('absent') or r.get('error')})" if state != "200" else ""))
        streak.note(r)


def fetch_docs(client, receipts, rows: list[dict], outcomes: Counter, streak: Streak) -> None:
    done = 0
    for s in rows:
        mid = str(s["match"]["id"])
        for kind in DOCS:
            r = P.fetch(client, doc_url(kind, mid), doc_dest(mid, kind), receipts, name=doc_name(mid, kind),
                        validator=P.json_validator, compress=True,
                        extra={"kind": kind, "match_id": mid, "list_date": s["list_date"],
                               "event": s["event"].get("tennisId")})
            state = "absent" if r.get("status") == 404 or r.get("absent") else "error" if r.get("error") \
                else str(r.get("status"))
            outcomes[f"{kind}:{state}{':cached' if r.get('skipped') else ''}"] += 1
            if not r.get("skipped"):
                streak.note(r)
        done += 1
        if done % 100 == 0:
            P.log(f"[{SOURCE}] documents: {done} of {len(rows)} matches; requests so far {client.requests}")


def run_fetch(args, receipts, stamp: str, client=None) -> dict:
    client = client or P.Client(IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter,
                                max_requests=args.max_requests, headers=HEADERS)
    now = stamp_time(stamp)
    today = now.date()
    outcomes, log_days, stopped = Counter(), [], None
    selected = {}
    streak = Streak()
    try:
        if not args.no_days:
            fetch_days(client, receipts, stamp, today, now, args.refetch_hours, outcomes, log_days, streak)
        if not args.days_only:
            state = latest_state(day_captures(receipts.all()), read_capture)
            every = wanted(state, today, now, args.settle_hours)
            events = event_order(every)
            if args.ids:
                ids = args.ids.split(",")
                missing = [i for i in ids if i not in state]
                if missing:
                    raise SystemExit(f"--ids not on any day list held: {', '.join(missing)}")
                rows = [{**state[i], "reason": "asked"} for i in ids]
            elif args.events:
                keep = set(args.events.split(","))
                rows = [s for s in every if str(s["event"].get("tennisId") or s["event_key"]) in keep]
            elif args.limit:
                keep = set(events[:args.limit])
                rows = [s for s in every if str(s["event"].get("tennisId") or s["event_key"]) in keep]
            else:
                rows = every
            todo = [s for s in rows if any(not done_doc(receipts.get(doc_name(str(s["match"]["id"]), k)))
                                           for k in DOCS)]
            selected = {"matches_listed": len(state), "wanted": len(every),
                        "wanted_by_reason": dict(Counter(s["reason"] for s in every)),
                        "events_with_wanted_matches": len(events), "selected": len(rows), "to_ask": len(todo)}
            P.log(f"[{SOURCE}] documents: {len(rows)} matches selected, {len(todo)} with a document to ask")
            fetch_docs(client, receipts, todo, outcomes, streak)
    except P.Blocked as err:
        stopped = f"blocked: {err}"
    except P.BudgetExhausted as err:
        stopped = f"budget: {err}"
    except FailureStreak as err:
        stopped = f"failures: {err}"
    return {"client": client.stats(), "outcomes": dict(sorted(outcomes.items())), "days": log_days,
            "selection": selected, "stopped": stopped}


def done_doc(receipt: dict | None) -> bool:
    """A per-match document that needs no request: saved (200) or a terminal absence (404)."""
    if not receipt or receipt.get("error"):
        return False
    if receipt.get("status") == 404 or receipt.get("absent"):
        return True
    return receipt.get("status") == 200 and (P.PROJECT_ROOT / receipt["dest"]).exists()


# --------------------------------------------------------------------------------------
# the gap-sources research's answers from this API (29 Sep 2026)
# --------------------------------------------------------------------------------------
RESEARCH = P.PROJECT_ROOT / "data" / "raw" / "gap_sources" / "itf"
RESEARCH_HOST = "api.itf-production.sports-data.stadion.io"


def research_receipts() -> dict[str, dict]:
    """The research's receipts (data/raw/gap_sources/itf/_receipts.jsonl, src/eda/gap_sources/itf_http.py), the
    latest per name; a line cut short is skipped."""
    out = {}
    path = RESEARCH / "_receipts.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("name"):
                out[r["name"]] = r
    return out


def research_target(name: str, retrieved_at: str) -> tuple[str, Path, dict] | None:
    """Where one of the research's answers goes in this collector's layout: (receipt name, dest, extra fields).
    A day list keeps its capture time as its run label."""
    if name.startswith("wttCompleteMatchList_") and name.endswith(".json"):
        day = name[len("wttCompleteMatchList_"):-len(".json")]
        stamp = run_stamp(parse_utc(retrieved_at))
        return day_name(day, stamp), day_dest(day, stamp), {"kind": "day", "day": day, "run": stamp}
    for prefix, kind in (("widgetMatchStats/", "stats"), ("pointByPoint/", "points")):
        if name.startswith(prefix) and name.endswith(".json"):
            mid = name[len(prefix):-len(".json")]
            return doc_name(mid, kind), doc_dest(mid, kind), {"kind": kind, "match_id": mid}
    return None


def import_research(receipts) -> dict:
    """Copy the research's 200 answers from this API beside the collector's own, gzipped, each with a receipt marked
    ``imported`` that keeps the research's URL, capture time and SHA-256 (checked against the file). The research
    session read the day lists of 15-29 Sep 2026 on 29 Sep: 15-23 Sep have left the API's window since, so its copies
    are their only listing. The files stay where they are; an answer already imported is left alone."""
    out = Counter()
    for name, r in sorted(research_receipts().items()):
        if r.get("host") != RESEARCH_HOST or r.get("status") != 200 or r.get("problem"):
            continue
        target = research_target(name, r.get("retrieved_at"))
        if target is None:
            out["not a day list or match document"] += 1
            continue
        new_name, dest, extra = target
        if done_doc(receipts.get(new_name)):
            out["already held"] += 1                  # imported before, or fetched by this collector itself
            continue
        source = RESEARCH / "other" / RESEARCH_HOST / name
        if not source.exists():
            out["file missing"] += 1
            continue
        body = source.read_bytes()
        if P.sha256_bytes(body) != r.get("sha256"):
            out["hash differs from its receipt"] += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(gzip.compress(body))
        os.replace(part, dest)
        taken = parse_utc(r.get("retrieved_at"))
        receipts.record({"name": new_name, "url": r.get("url"), "dest": P.rel(dest),
                         "retrieved_at": taken.isoformat(timespec="seconds") if taken else r.get("retrieved_at"),
                         **extra, "status": 200, "content_type": r.get("content_type"), "final_url": r.get("final_url"),
                         "bytes": len(body), "sha256": r.get("sha256"), "compressed": True, "imported": True,
                         "imported_from": P.rel(source)})
        out[f"imported {extra['kind']}"] += 1
    return dict(out)


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    P.configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-requests", type=int, help="request budget of this run (required unless --stage-only)")
    ap.add_argument("--min-interval", type=float, default=2.0)
    ap.add_argument("--jitter", type=float, default=1.0)
    ap.add_argument("--refetch-hours", type=float, default=REFETCH_HOURS)
    ap.add_argument("--days-only", action="store_true", help="the day lists only")
    ap.add_argument("--no-days", action="store_true", help="no day lists: documents for the lists already held")
    ap.add_argument("--limit", type=int, help="documents for the first N events only (a trial)")
    ap.add_argument("--events", help="documents for these ITF event keys only (comma list)")
    ap.add_argument("--ids", help="documents for these listed match ids, whatever their status (comma list; a probe)")
    ap.add_argument("--settle-hours", type=float, default=SETTLE_HOURS,
                    help="ask a match's documents once it ended at least this long ago")
    ap.add_argument("--stage-only", action="store_true", help="rebuild the staged tables from raw; no HTTP")
    ap.add_argument("--no-stage", action="store_true", help="skip staging after fetching")
    ap.add_argument("--import-research", action="store_true",
                    help="first copy in the gap-sources research's answers from this API (no HTTP); with "
                         "--max-requests, then fetch as usual")
    args = ap.parse_args(argv)
    if not args.stage_only and not args.max_requests and not args.import_research:
        ap.error("--max-requests is required for a fetching run")
    stamp = run_stamp()
    started = P.utc_now_iso()
    t0 = time.time()
    summary: dict = {"source": SOURCE, "run": stamp, "started_at": started, "decision": DECISION,
                     "argv": sys.argv[1:] if argv is None else argv}
    code = 0
    result = None
    if not args.stage_only:
        try:
            with run_lock():
                receipts = P.receipts_for(SOURCE)
                if args.import_research:
                    summary["imported"] = import_research(receipts)
                    P.log(f"[{SOURCE}] research answers: {summary['imported']}")
                if args.max_requests:
                    result = run_fetch(args, receipts, stamp)
        except LockHeld as err:
            P.log(f"[{SOURCE}] {err}")
            return 3
    if result:
        summary.update(result)
        summary["fetch_outcomes"] = result["outcomes"]
        if result["stopped"] and result["stopped"].startswith("blocked"):
            code = 2
        elif result["stopped"] and result["stopped"].startswith("failures"):
            code = 1
        P.log(f"[{SOURCE}] fetch: {result['client']['requests']} requests; {result['outcomes']}"
              + (f"; stopped ({result['stopped']})" if result["stopped"] else ""))
    if not args.no_stage:
        try:
            summary["staged"] = stage_all()
        except Exception as err:  # noqa: BLE001 - recorded; the raw files are safe
            summary["staged"] = {"error": f"{type(err).__name__}: {err}"}
            P.log(f"[{SOURCE}] staging failed: {err}")
            code = code or 1
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - t0, 1)
    if result:
        P.write_summary("itf_live_summary.json", summary, root=STUDY)
    return code


# --------------------------------------------------------------------------------------
# staging (pure record builders, tested offline; stage_all writes the tables)
# --------------------------------------------------------------------------------------
EVENT_COLUMNS = [
    "event_key", "tennis_id", "event_id", "name", "tour", "grade", "event_order", "start_date", "end_date",
    "main_draw_week", "surface", "country", "country_iso", "first_list_date", "last_list_date", "list_dates",
    "captures", "latest_capture", "matches", "singles", "doubles", "singles_main", "singles_qualifying",
    "singles_over", "event_json", "source_file", "sha256", "retrieved_at",
]
SIDE_FIELDS = ["id", "seeding", "score", "players", "player_ids", "person_ids", "headshot_codes", "countries",
               "wtt_ranks", "singles_seeding_ranks", "doubles_seeding_ranks", "sets"]
MATCH_COLUMNS = [
    "list_date", "capture", "latest", "event_key", "event_tennis_id", "event_name", "court_key", "match_id",
    "match_tennis_id", "discipline", "gender", "match_type", "draw", "round", "round_order", "order_in_round",
    "order_in_schedule", "schedule_text", "date_start_local", "actual_start_date", "actual_end_date", "duration",
    "status", "status_display", "status_state_type", "status_updated_at", "winner_side_id", "winner_side_order",
    "current_server_side_id", "is_live_streamed", "court_name", "court_id", "updated_at",
    *[f"side{n}_{f}" for n in (1, 2) for f in SIDE_FIELDS], "sides", "extra", "source_file", "sha256", "retrieved_at",
]
STAT_COLUMNS = [
    "match_id", "item_id", "stat", "stat_display", "stat_source_name", "stat_grouping", "stat_display_type",
    "stat_lower_is_better", "stat_abbreviation", "stat_type_id", "set_number", "period", "side_id", "side_order",
    "side_players", "side_player_codes", "value", "value_display", "created_at", "updated_at", "extra",
    "source_file", "sha256", "retrieved_at",
]
POINT_SIDE_FIELDS = ["id", "players", "player_codes", "game_won", "point", "game_score_after", "is_server",
                     "point_won", "outcome", "set_score_before", "set_score_after"]
POINT_COLUMNS = [
    "match_id", "set_number", "set_index", "game_number", "game_index", "game_annotation", "point_number",
    "point_index", "server_side_order", "winner_side_order", "outcome", "sides_listing", "consistent",
    *[f"side{n}_{f}" for n in (1, 2) for f in POINT_SIDE_FIELDS], "extra", "source_file", "sha256", "retrieved_at",
]
DOCUMENT_COLUMNS = [
    "match_id", "kind", "list_date", "event_tennis_id", "url", "status", "absent", "error", "retrieved_at", "bytes",
    "sha256", "has_data", "items", "stat_types", "periods", "sets", "games", "points", "match_tennis_id",
    "actual_start_date", "actual_end_date", "duration", "date_start_local", "official_id", "match_updated_at",
    "match_status_id", "scoring_type_id", "source_file",
]
MATCH_KEYS = {"_drawDiscipline", "_drawName", "_roundName", "_roundOrder", "actualEndDate", "actualStartDate",
              "court", "currentServerSideId", "dateStartLocal", "duration", "id", "isLiveStreamed", "matchStatus",
              "orderInRound", "orderInSchedule", "scheduleText", "sides", "tennisId", "updatedAt", "winnerSideId"}
STAT_KEYS = {"_admin_name", "_name", "createdAt", "deletedAt", "id", "match", "matchId", "set", "setId", "setNumber",
             "side", "sideId", "statType", "statTypeId", "updatedAt", "value", "valueDisplay"}
POINT_KEYS = {"_point", "gameScoreAfterePoint", "isServer", "outcome", "pointNumber", "pointWon", "setScoreAfterPoint",
              "setScoreBeforePoint"}


def joined(values) -> str | None:
    """Semicolon list of the values' string forms (None as empty), or None when there are none."""
    values = list(values)
    return ";".join("" if v is None else P.s(v) for v in values) if values else None


def headshot_code(person: dict) -> str | None:
    """The last part of the person's headshot image URL (".../POD1488593" -> "POD1488593"), else None."""
    for image in person.get("images") or []:
        if isinstance(image, dict) and image.get("description") == "headshot" and image.get("url"):
            return str(image["url"]).rstrip("/").rsplit("/", 1)[-1]
    return None


def sets_text(side_sets) -> str | None:
    """A side's sets as "1:6/0 2:5/0 3:7/5" (set number : games / tiebreak points), in set order."""
    items = sorted((x for x in side_sets or [] if isinstance(x, dict)), key=lambda x: x.get("setNumber") or 0)
    return " ".join(f"{x.get('setNumber')}:{x.get('setScore')}/{x.get('setTieBreakScore')}" for x in items) or None


def side_record(side: dict | None) -> dict:
    side = side or {}
    entries = [e for e in side.get("sidePlayer") or [] if isinstance(e, dict)]
    players = [e.get("player") or {} for e in entries]
    persons = [p.get("person") or {} for p in players]
    return {
        "id": side.get("id"), "seeding": side.get("seeding"), "score": P.s(side.get("score")),
        "players": joined(p.get("_name") for p in players),
        "player_ids": joined(e.get("playerId") or p.get("id") for e, p in zip(entries, players)),
        "person_ids": joined(q.get("id") for q in persons),
        "headshot_codes": joined(headshot_code(q) for q in persons),
        "countries": joined((q.get("country") or {}).get("ISOcode") for q in persons),
        "wtt_ranks": joined(p.get("wttRank") for p in players),
        "singles_seeding_ranks": joined(p.get("singlesSeedingRank") for p in players),
        "doubles_seeding_ranks": joined(p.get("doublesSeedingRank") for p in players),
        "sets": sets_text(side.get("sideSets")),
    }


def match_record(match: dict) -> dict:
    """One listed match flattened: identity, draw, status, every time field, both sides; unknown keys in ``extra``."""
    status, court = match.get("matchStatus") or {}, match.get("court") or {}
    sides = sorted((s for s in match.get("sides") or [] if isinstance(s, dict)), key=lambda s: s.get("sideOrder") or 0)
    by_order = {s.get("sideOrder"): s for s in sides}
    winner = match.get("winnerSideId")
    winner_order = next((s.get("sideOrder") for s in sides if winner and s.get("id") == winner), None)
    disc = discipline(match)
    out = {
        "match_id": match.get("id"), "match_tennis_id": match.get("tennisId"), "discipline": disc.get("_name"),
        "gender": disc.get("gender"), "match_type": disc.get("type"), "draw": match.get("_drawName"),
        "round": match.get("_roundName"), "round_order": match.get("_roundOrder"),
        "order_in_round": match.get("orderInRound"), "order_in_schedule": match.get("orderInSchedule"),
        "schedule_text": match.get("scheduleText"), "date_start_local": match.get("dateStartLocal"),
        "actual_start_date": match.get("actualStartDate"), "actual_end_date": match.get("actualEndDate"),
        "duration": match.get("duration"), "status": status.get("_name") or status.get("name"),
        "status_display": status.get("displayName"), "status_state_type": status.get("stateType"),
        "status_updated_at": status.get("updatedAt"), "winner_side_id": winner, "winner_side_order": winner_order,
        "current_server_side_id": match.get("currentServerSideId"), "is_live_streamed": match.get("isLiveStreamed"),
        "court_name": court.get("_name") or court.get("name"), "court_id": court.get("id"),
        "updated_at": match.get("updatedAt"), "sides": len(sides),
    }
    for n in (1, 2):
        for field, value in side_record(by_order.get(n)).items():
            out[f"side{n}_{field}"] = value
    extra = {k: v for k, v in match.items() if k not in MATCH_KEYS}
    if len(sides) > 2 or any(s.get("sideOrder") not in (1, 2) for s in sides):
        extra["sides_unplaced"] = [s for s in sides if s.get("sideOrder") not in (1, 2)] or sides[2:]
    out["extra"] = extra or None
    return out


def event_tour(event: dict, genders) -> str | None:
    """M or W: the ITF key's first letter ("M-ITF-..."), else the name's ("W35 Reims"), else the matches' gender."""
    for text in (event.get("tennisId"), event.get("_name")):
        if isinstance(text, str) and text[:1] in ("M", "W") and (text[1:2] == "-" or text[1:2].isdigit()):
            return text[:1]
    genders = Counter(g for g in genders if g)
    if genders:
        return "W" if genders.most_common(1)[0][0] == "women" else "M"
    return None


def main_draw_week(start: str | None) -> str | None:
    """ITF events are listed from their qualifying weekend; the main draw's ISO week is that of start + 2 days."""
    try:
        y, w, _ = (dt.date.fromisoformat(str(start)[:10]) + dt.timedelta(days=2)).isocalendar()
    except ValueError:
        return None
    return f"{y}-W{w:02d}"


def stat_rows(doc: dict, match_id: str) -> list[dict]:
    """One row per statistic item of a widgetMatchStats answer (stat type, side, set or match)."""
    out = []
    for item in (doc or {}).get("data") or []:
        if not isinstance(item, dict):
            continue
        st, side = item.get("statType") or {}, item.get("side") or {}
        entries = [e for e in side.get("sidePlayer") or [] if isinstance(e, dict)]
        players = [e.get("player") or {} for e in entries]
        set_no = item.get("setNumber")
        out.append({
            "match_id": item.get("matchId") or match_id, "item_id": item.get("id"), "stat": item.get("_name"),
            "stat_display": st.get("displayName"), "stat_source_name": st.get("sourceName"),
            "stat_grouping": st.get("grouping"), "stat_display_type": st.get("displayType"),
            "stat_lower_is_better": st.get("lowerIsBetter"), "stat_abbreviation": st.get("abbreviation"),
            "stat_type_id": item.get("statTypeId") or st.get("id"), "set_number": set_no,
            "period": "match" if set_no in (None, "", 0) else f"set {set_no}",
            "side_id": item.get("sideId") or side.get("id"), "side_order": side.get("sideOrder"),
            "side_players": joined(p.get("_name") for p in players),
            "side_player_codes": joined(p.get("tennisId") or (p.get("person") or {}).get("tennisId") for p in players),
            "value": item.get("value"), "value_display": item.get("valueDisplay"),
            "created_at": item.get("createdAt"), "updated_at": item.get("updatedAt"),
            "extra": {k: v for k, v in item.items() if k not in STAT_KEYS} or None,
        })
    return out


def stats_match_fields(doc: dict) -> dict:
    """The match object the statistics items repeat: its time fields and ids (from the first item that has one)."""
    for item in (doc or {}).get("data") or []:
        m = item.get("match") if isinstance(item, dict) else None
        if isinstance(m, dict):
            return {"match_tennis_id": m.get("tennisId"), "actual_start_date": m.get("actualStartDate"),
                    "actual_end_date": m.get("actualEndDate"), "duration": m.get("duration"),
                    "date_start_local": m.get("dateStartLocal"), "official_id": m.get("officialId"),
                    "match_updated_at": m.get("updatedAt"), "match_status_id": m.get("matchStatusId"),
                    "scoring_type_id": m.get("scoringTypeId")}
    return {}


def point_rows(doc: dict, match_id: str) -> list[dict]:
    """One row per point of a pointByPoint answer. Each game lists every point once per side, from that side's
    view; the two views are placed side by side (by side order), matched on the point's place in the game and its
    pointNumber. ``consistent`` says the views agree: both present, one server, one winner, the same outcome."""
    out = []
    for set_index, st in enumerate((doc or {}).get("data") or [], 1):
        if not isinstance(st, dict):
            continue
        for game_index, game in enumerate(st.get("games") or [], 1):
            if not isinstance(game, dict):
                continue
            views: dict[tuple, dict[int, tuple]] = {}
            order: list[tuple] = []
            sides = [s for s in game.get("sides") or [] if isinstance(s, dict)]
            for position, side in enumerate(sides, 1):
                info = side.get("side") or {}
                side_no = info.get("sideOrder") if info.get("sideOrder") in (1, 2) else position
                seen = Counter()
                for point in side.get("points") or []:
                    if not isinstance(point, dict):
                        continue
                    number = point.get("pointNumber")
                    seen[number] += 1
                    key = (number, seen[number])
                    if key not in views:
                        views[key] = {}
                        order.append(key)
                    views[key][side_no] = (side, info, point)
            for point_index, key in enumerate(order, 1):
                row = {"match_id": match_id, "set_number": st.get("setNumber"), "set_index": set_index,
                       "game_number": game.get("gameNumber"), "game_index": game_index,
                       "game_annotation": game.get("gameAnnotation"), "point_number": key[0],
                       "point_index": point_index}
                extra = {}
                for n in (1, 2):
                    side, info, point = views[key].get(n, ({}, {}, {}))
                    players = [p for p in info.get("sidePlayer") or [] if isinstance(p, dict)]
                    row.update({
                        f"side{n}_id": info.get("id"),
                        f"side{n}_players": joined(" ".join(x for x in (p.get("firstName"), p.get("lastName")) if x)
                                                   for p in players),
                        f"side{n}_player_codes": joined(p.get("tennisId") for p in players),
                        f"side{n}_game_won": side.get("gameWon"), f"side{n}_point": point.get("_point"),
                        f"side{n}_game_score_after": point.get("gameScoreAfterePoint"),
                        f"side{n}_is_server": point.get("isServer"), f"side{n}_point_won": point.get("pointWon"),
                        f"side{n}_outcome": point.get("outcome"),
                        f"side{n}_set_score_before": point.get("setScoreBeforePoint"),
                        f"side{n}_set_score_after": point.get("setScoreAfterPoint"),
                    })
                    more = {k: v for k, v in point.items() if k not in POINT_KEYS}
                    if more:
                        extra[f"side{n}"] = more
                present = sorted(views[key])
                servers = [n for n in present if views[key][n][2].get("isServer") is True]
                winners = [n for n in present if views[key][n][2].get("pointWon") is True]
                outcomes = {views[key][n][2].get("outcome") for n in present}
                row.update({
                    "server_side_order": servers[0] if len(servers) == 1 else None,
                    "winner_side_order": winners[0] if len(winners) == 1 else None,
                    "outcome": next(iter(outcomes)) if len(outcomes) == 1 else None,
                    "sides_listing": len(present),
                    "consistent": present == [1, 2] and len(servers) == 1 and len(winners) == 1 and len(outcomes) == 1,
                    "extra": extra or None,
                })
                out.append(row)
    return out


def point_counts(doc: dict) -> tuple[int, int, int]:
    """(sets, games, points) of a pointByPoint answer, each point counted once (the larger side's list)."""
    sets = games = points = 0
    for st in (doc or {}).get("data") or []:
        if not isinstance(st, dict):
            continue
        sets += 1
        for game in st.get("games") or []:
            if isinstance(game, dict):
                games += 1
                points += max((len(s.get("points") or []) for s in game.get("sides") or [] if isinstance(s, dict)),
                              default=0)
    return sets, games, points


def as_row(record: dict, columns: list[str]) -> list:
    return [P.s(record.get(c)) for c in columns]


def stage_table_atomic(name: str, columns: list[str], rows, *, source_file: str, retrieved_at: str) -> dict:
    """common.stage_table, written to <name>.parquet.part and renamed into place: a run stopped while staging (the
    daily job's time limit) leaves the previous table, never a truncated one."""
    dest = P.dump_path(SOURCE, f"{name}.parquet")
    part = dest.with_name(dest.name + ".part")
    prov = P.C.Provenance(SOURCE, source_file, None, retrieved_at, None)
    stats = P.C.stage_rows(columns, ((i + 1, r) for i, r in enumerate(rows)), part, prov)
    os.replace(part, dest)
    P.C.write_meta(dest, {"branch": "points", "source": SOURCE, "dest": P.rel(dest), "rows": stats["rows"],
                          "columns": stats["columns"], "bytes": dest.stat().st_size, "source_path": source_file,
                          "retrieved_at": retrieved_at})
    return stats


def stage_all() -> dict:
    """Rebuild the staged tables from the raw files (no HTTP)."""
    receipts = P.receipts_for(SOURCE).all()
    captures = day_captures(receipts)
    now = P.utc_now_iso()
    folder = P.rel(P.raw_path(SOURCE))
    out = {}

    def stage(name, columns, rows):
        out[name] = stage_table_atomic(name, columns, rows, source_file=folder, retrieved_at=now)["rows"]

    # day lists: every row of every capture; the latest state of each match flagged
    match_rows, latest_at, events = [], {}, {}
    for day in sorted(captures):
        for receipt in captures[day]:
            doc = read_capture(receipt)
            src = P.rel(day_dest(day, receipt["stamp"]))
            for key, event, court, match in listed(doc):
                rec = match_record(match)
                rec.update(list_date=day, capture=receipt["stamp"], event_key=key, event_tennis_id=event.get("tennisId"),
                           event_name=event.get("_name"), court_key=court, source_file=src,
                           sha256=receipt.get("sha256"), retrieved_at=receipt.get("retrieved_at"))
                match_rows.append(rec)
                if rec["match_id"]:
                    latest_at[rec["match_id"]] = len(match_rows) - 1
                ev = events.setdefault(event.get("tennisId") or key, {"captures": set(), "days": set()})
                ev.update(head=event, key=key, receipt=receipt, src=src)  # the latest capture's (sorted by day, stamp)
                ev["captures"].add((day, receipt["stamp"]))
                ev["days"].add(day)
    latest_rows = set(latest_at.values())
    for i, rec in enumerate(match_rows):
        rec["latest"] = i in latest_rows
    stage("matches", MATCH_COLUMNS, [as_row(r, MATCH_COLUMNS) for r in match_rows])

    event_rows = []
    by_event = {}
    for i in sorted(latest_rows):
        rec = match_rows[i]
        by_event.setdefault(rec["event_tennis_id"] or rec["event_key"], []).append(rec)
    for ek, ev in sorted(events.items()):
        head, mine = ev["head"], by_event.get(ek, [])
        singles = [r for r in mine if str(r["match_type"] or "").lower() == "singles"]
        country = (head.get("venue") or {}).get("country") or {}
        event_rows.append(as_row({
            "event_key": ev["key"], "tennis_id": head.get("tennisId"), "event_id": head.get("id"),
            "name": head.get("_name"), "tour": event_tour(head, (r["gender"] for r in mine)),
            "grade": (head.get("eventCategory") or {}).get("type"),
            "event_order": (head.get("eventCategory") or {}).get("eventOrder"),
            "start_date": head.get("startDate"), "end_date": head.get("endDate"),
            "main_draw_week": main_draw_week(head.get("startDate")),
            "surface": (head.get("surface") or {}).get("_name"), "country": country.get("_name"),
            "country_iso": country.get("ISOcode"), "first_list_date": min(ev["days"]), "last_list_date": max(ev["days"]),
            "list_dates": ";".join(sorted(ev["days"])), "captures": len(ev["captures"]),
            "latest_capture": ev["receipt"]["stamp"], "matches": len(mine), "singles": len(singles),
            "doubles": len(mine) - len(singles),
            "singles_main": sum(str(r["draw"] or "").lower().startswith("main") for r in singles),
            "singles_qualifying": sum("qualif" in str(r["draw"] or "").lower() for r in singles),
            "singles_over": sum(str(r["status_state_type"] or "").lower() == "post" for r in singles),
            "event_json": head, "source_file": ev["src"], "sha256": ev["receipt"].get("sha256"),
            "retrieved_at": ev["receipt"].get("retrieved_at")}, EVENT_COLUMNS))
    stage("events", EVENT_COLUMNS, event_rows)

    # per-match documents: each held answer is parsed once (the cache), the tables written from the cache
    latest_by_id = {match_rows[i]["match_id"]: match_rows[i] for i in latest_rows}
    docs = {name: r for name, r in receipts.items() if name.startswith("match/") and name.count("/") == 2}
    held = {name: r.get("sha256") for name, r in docs.items()
            if r.get("status") == 200 and not r.get("error") and doc_dest(*name.split("/")[1:]).exists()}
    owner, fields, parsed = update_cache(held, docs)
    doc_rows = []
    for name, receipt in sorted(docs.items()):
        _, mid, kind = name.split("/")
        rec = document_record(mid, kind, receipt, latest_by_id.get(mid))
        if name in held:
            rec.update({k: v for k, v in fields[(name, held[name])].items() if k not in KEY_COLUMNS})
        doc_rows.append(as_row(rec, DOCUMENT_COLUMNS))
    stage("documents", DOCUMENT_COLUMNS, doc_rows)
    for kind, name, columns in (("stats", "statistics", STAT_COLUMNS), ("points", "points", POINT_COLUMNS)):
        out[name] = write_from_cache(name, kind, columns, owner, source_file=folder, retrieved_at=now)
    out["documents_parsed"] = parsed
    out["day_captures"] = sum(len(c) for c in captures.values())
    out["list_days"] = len(captures)
    P.log(f"[{SOURCE}] staged: {out}")
    return out


def document_record(match_id: str, kind: str, receipt: dict, listed_row: dict | None) -> dict:
    """A documents-table row from the receipt and the match's latest listing; the answer's own fields come from
    parse_document (through the cache)."""
    return {"match_id": match_id, "kind": kind,
            "list_date": (listed_row or {}).get("list_date") or receipt.get("list_date"),
            "event_tennis_id": (listed_row or {}).get("event_tennis_id") or receipt.get("event"),
            "url": receipt.get("url"), "status": receipt.get("status"), "absent": receipt.get("absent"),
            "error": receipt.get("error"), "retrieved_at": receipt.get("retrieved_at"), "bytes": receipt.get("bytes"),
            "sha256": receipt.get("sha256"), "source_file": receipt.get("dest")}


# --------------------------------------------------------------------------------------
# the parse cache: data/dump/points/itf_live/_cache/
# --------------------------------------------------------------------------------------
KEY_COLUMNS = ["_doc", "_doc_sha256"]          # the answer's receipt name and SHA-256
FIELD_COLUMNS = ["has_data", "items", "stat_types", "periods", "sets", "games", "points", "match_tennis_id",
                 "actual_start_date", "actual_end_date", "duration", "date_start_local", "official_id",
                 "match_updated_at", "match_status_id", "scoring_type_id"]
ROW_COLUMNS = {"stats": STAT_COLUMNS, "points": POINT_COLUMNS}


def parse_document(kind: str, match_id: str, doc) -> tuple[list[dict], dict]:
    """(rows, fields) of one held answer: its statistic or point rows, and its own fields for the documents table."""
    if kind == "stats":
        rows = stat_rows(doc, match_id)
        fields = {"items": len(rows), "stat_types": len({r["stat"] for r in rows}),
                  "periods": len({r["period"] for r in rows}), **stats_match_fields(doc)}
    else:
        rows = point_rows(doc, match_id)
        sets, games, points = point_counts(doc)
        fields = {"items": len(rows), "sets": sets, "games": games, "points": points}
    fields["has_data"] = bool(doc.get("data")) if isinstance(doc, dict) else False
    return rows, fields


def cache_parts(what: str, columns: list[str]):
    """(part label, table) of each cache part of ``what`` ("<kind>_rows" or "<kind>_fields"), oldest first. A part
    written with other columns (an older layout) is skipped, so its answers are parsed again."""
    for path in sorted(P.dump_path(SOURCE, "_cache", what).glob("*.parquet")):
        import pyarrow.parquet as pq

        table = pq.read_table(path)
        if table.column_names == KEY_COLUMNS + columns:
            yield path.stem, table


def write_strings_atomic(path: Path, columns: list[str], rows: list[list]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.table({c: pa.array([r[i] for r in rows], pa.string()) for i, c in enumerate(columns)})
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    pq.write_table(table, part, compression="zstd")
    os.replace(part, path)


def update_cache(held: dict[str, str], receipts: dict) -> tuple[dict, dict, int]:
    """Parse the held answers the cache lacks (by receipt name and SHA-256) into a new cache part, and return
    (owner, fields, parsed): for each held answer, the part its rows are taken from (the first part that has it, so
    two stagings at once cannot double it), its fields, and how many answers were parsed now."""
    fields, owner = {}, {}
    for kind in ROW_COLUMNS:
        for label, table in cache_parts(f"{kind}_fields", FIELD_COLUMNS):
            for row in table.to_pylist():
                key = (row["_doc"], row["_doc_sha256"])
                if key not in owner and held.get(key[0]) == key[1]:
                    owner[key], fields[key] = label, row
    label = f"{run_stamp()}_{os.getpid()}"
    new_rows, new_fields, parsed = {k: [] for k in ROW_COLUMNS}, {k: [] for k in ROW_COLUMNS}, 0
    for name, sha in sorted(held.items()):
        if (name, sha) in owner:
            continue
        _, mid, kind = name.split("/")
        path = doc_dest(mid, kind)
        rows, found = parse_document(kind, mid, P.read_json(path))
        receipt = receipts[name]
        for r in rows:
            r.update(source_file=P.rel(path), sha256=sha, retrieved_at=receipt.get("retrieved_at"))
            new_rows[kind].append([name, sha] + as_row(r, ROW_COLUMNS[kind]))
        new_fields[kind].append([name, sha] + [P.s(found.get(c)) for c in FIELD_COLUMNS])
        owner[(name, sha)] = label
        fields[(name, sha)] = dict(zip(KEY_COLUMNS + FIELD_COLUMNS, new_fields[kind][-1]))
        parsed += 1
    for kind in ROW_COLUMNS:
        if new_fields[kind]:      # rows first: a part's fields are the sign that its rows are complete
            write_strings_atomic(P.dump_path(SOURCE, "_cache", f"{kind}_rows", f"{label}.parquet"),
                                 KEY_COLUMNS + ROW_COLUMNS[kind], new_rows[kind])
            write_strings_atomic(P.dump_path(SOURCE, "_cache", f"{kind}_fields", f"{label}.parquet"),
                                 KEY_COLUMNS + FIELD_COLUMNS, new_fields[kind])
    return owner, fields, parsed


def write_from_cache(name: str, kind: str, columns: list[str], owner: dict, *, source_file: str,
                     retrieved_at: str) -> int:
    """The <name> table from the cache parts, one part at a time: each held answer's rows from the part that owns
    it, with the dump's provenance columns; written to .part and renamed into place. Returns the rows written."""
    import numpy as np
    import pyarrow as pa
    import pyarrow.parquet as pq

    dest = P.dump_path(SOURCE, f"{name}.parquet")
    part = dest.with_name(dest.name + ".part")
    schema = pa.schema([pa.field(c, pa.string()) for c in columns] + [pa.field(n, t) for n, t in P.C.PROVENANCE_FIELDS])

    def same(value, n):
        return pa.array(np.full(n, value, dtype=object), pa.string())

    dest.parent.mkdir(parents=True, exist_ok=True)
    writer = pq.ParquetWriter(part, schema, compression="zstd")
    total = 0
    try:
        for label, table in cache_parts(f"{kind}_rows", columns):
            keep = [owner.get((d, s)) == label for d, s in zip(table.column("_doc").to_pylist(),
                                                              table.column("_doc_sha256").to_pylist())]
            table = table.filter(pa.array(keep, pa.bool_()))
            n = table.num_rows
            if not n:
                continue
            arrays = [table.column(c).combine_chunks() for c in columns]
            arrays += [same(SOURCE, n), same(source_file, n), pa.array(np.arange(total + 1, total + n + 1), pa.int64()),
                       same("ok", n), pa.nulls(n, pa.string()), pa.nulls(n, pa.string()), same(retrieved_at, n)]
            writer.write_table(pa.Table.from_arrays(arrays, schema=schema))
            total += n
    finally:
        writer.close()
    os.replace(part, dest)
    P.C.write_meta(dest, {"branch": "points", "source": SOURCE, "dest": P.rel(dest), "rows": total,
                          "columns": columns, "bytes": dest.stat().st_size, "source_path": source_file,
                          "retrieved_at": retrieved_at, "built_from": P.rel(P.dump_path(SOURCE, "_cache", f"{kind}_rows"))})
    return total


if __name__ == "__main__":
    sys.exit(main())
