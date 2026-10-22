"""The ATP Stats Centre's Infosys files of 2015 to mid-October 2021, downloaded still encrypted. Nothing is decrypted.

atptour.com's Stats Centre pages load each match's data from itp-atp-sls.infosys-platforms.com as JSON envelopes
``{lastModified, response, data: null}``: ``response`` is AES ciphertext (base64) that the page's own script decrypts
in the visitor's browser. Decrypted third-party copies (the Hugging Face handoff) hold such files for the 2018 ATP
Finals and for Washington in August 2021, before atptour.com showed any per-match speed (18 October 2021). That is a
lead for the ATP's 2015-20 serve-speed gap (docs/studies/serve_speed_acquisition/README.md, sections 1 and 6).

The owner's instruction for this download (8 Oct 2026): "Acquire this speed data and download it. DO NOT DECRYPT IT.
I just want the encrypted files on my computer." So this module neither decrypts nor stages. Each envelope is saved
exactly as served (gzipped), and the inventory reads only the envelope's plain fields. The collection itself is
approved by docs/decisions/2026-10-08-scraping-approved.md, whose "Clarified" section keeps these files encrypted until
the owner says otherwise.

How collection is run (that decision's practice): about 2 s between requests plus up to 1 s of jitter, a
--max-requests budget, everything cached with a receipt and nothing fetched twice, and a stop and report on any block
(feeds.FeedClient: HTTP 429, a challenge page, a redirect, a connection reset, or a 403 other than S3's "no such
object" answer on a route that has already served a file to the same headers). Requests carry the Origin and Referer
of atptour.com's Stats Centre page, with Chrome's TLS fingerprint.

Routes (static files; the four whose documented contents carry serve speed):
    keystats        static/prod/stats-plus/<year>/<event>/<MID>/keystats.json   key statistics per set: Max Speed,
                                                                               1st and 2nd Serve Average Speed and the
                                                                               box score
    match-beats     static/prod/match-beats/<year>/<event>/<MID>/data.json     MatchBeats: every point, with the
                                                                               serve's speed
    rally-analysis  static/prod/rally-analysis/<year>/<event>/<MID>/data.json  every point by rally length, with the
                                                                               serve's speed and direction
    court-vision    static/prod/court-vision/<year>/<event>/<MID>/data.json    Hawk-Eye tracking per point
What the files hold is documented (Infosys's main.js and the decrypted copies of 2021-24); it is not seen here.

The plan covers every ATP tour-level singles match in ManTennisData (data/dump/matches/mantennisdata/, the plain CSVs
of msolonskyi/ManTennisData) whose event began between --since and --until. The default window is 1 Jan 2015 to
17 Oct 2021, the day before atptour.com's pages began to show speeds. Each match's ATP code is read from its
atptour.com stats link: MS001 is the final, MS002-003 the semi-finals, and so on; QS codes are the qualifying.
* Tour level is ManTennisData's series "atp" and "1000": the 250s, 500s, Masters, the ATP and Next Gen Finals, the ATP
  Cup and the Laver Cup.
* Left out: the Slams (not on the ATP's host), the Olympics, Davis Cup and Challengers. The Hugging Face crawl asked
  for every Challenger of 2015-19 and kept none.
* Matches without a stats link (mostly walkovers) are not asked for.

Order of work (each step skips what the receipts already hold):
    calibrate  one file per route that the host is known to serve (CALIBRATION), so that S3's 403 can be read as
               "no such object" on that route
    discover   each event's first code (the final) on every route. Where no route has it, the next code (a
               semi-final) is asked on key statistics and Court Vision before the event counts as empty
    expand     each event with a file, per route and per family (MS, QS): every code once a file has been seen;
               until then, codes in order until the first --skip-after are all absent
Years run in --years order (default 2020, 2019, 2018, 2017, 2016, 2015, 2021): the 2015-20 gap first.

Raw (data/raw/point_sources/infosys_atp/<year>/<event>/<route>/<MID>.json.gz): the envelope as served, gzipped, with
_receipts.jsonl. These are the only copies.
Evidence (data/studies/serve_speed_acquisition/):
    infosys_atp_summary.json   the last run: requests, answers by year and route, events by outcome, routes given up
    infosys_atp_events.csv     one row per event in the plan: codes, the discovery's outcome, files and absences per route
    infosys_atp_files.csv      one row per file held: event, match code, route, bytes, SHA-256, and the envelope's plain
                               lastModified and ciphertext length
    runs.jsonl                 one line per run (shared with the study's other adapters)

Usage:
    ./python.sh -m src.ingest.point_sources.infosys_atp                           # the whole window
    ./python.sh -m src.ingest.point_sources.infosys_atp --phase discover          # calibrate and discover only
    ./python.sh -m src.ingest.point_sources.infosys_atp --years 2018 --events 605 --max-requests 30
    ./python.sh -m src.ingest.point_sources.infosys_atp --inventory-only          # no HTTP; rewrite the evidence
"""
from __future__ import annotations

import argparse
import base64
import binascii
import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import feeds as F

SOURCE = "infosys_atp"
IMPERSONATE = "chrome"
INSTRUCTION = ("Owner, 8 Oct 2026: \"Acquire this speed data and download it. DO NOT DECRYPT IT. I just want the "
               "encrypted files on my computer.\"")
DECISION = "docs/decisions/2026-10-08-scraping-approved.md"
STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "serve_speed_acquisition"
MTD_ROOT = P.PROJECT_ROOT / "data" / "dump" / "matches" / "mantennisdata"
HOST = "https://itp-atp-sls.infosys-platforms.com"
HEADERS = {"Origin": "https://www.atptour.com", "Referer": "https://www.atptour.com/",
           "Accept": "application/json, text/plain, */*"}
ROUTES = {
    "keystats": "/static/prod/stats-plus/{year}/{event}/{mid}/keystats.json",
    "match-beats": "/static/prod/match-beats/{year}/{event}/{mid}/data.json",
    "rally-analysis": "/static/prod/rally-analysis/{year}/{event}/{mid}/data.json",
    "court-vision": "/static/prod/court-vision/{year}/{event}/{mid}/data.json",
}
# A file per route that the host served to these headers in earlier probes: keystats 2025/352/MS001 (Paris 2025
# final) on 7 Oct 2026 (serve_speed_sources lane A1); the other three 2022/605/MS001 (ATP Finals 2022 final) on
# 24 Sep 2026 (data/studies/granular_data_leads/probe_logs/A_tour_probe_log.tsv).
CALIBRATION = {"keystats": (2025, 352, "MS001"), "match-beats": (2022, 605, "MS001"),
               "rally-analysis": (2022, 605, "MS001"), "court-vision": (2022, 605, "MS001")}
GUARD_ROUTES = ("keystats", "court-vision")  # the two routes the decrypted copies hold for 2018
TOUR_SERIES = ("atp", "1000")
# atptour.com's three link forms: /scores/2018/339/QS012/match-stats?isLive=False,
# /scores/match-stats/archive/2019/6116/MS014 and /scores/stats-centre/archive/2021/9428/ms052
CODE_RX = re.compile(r"/scores/(?:[a-z-]+/archive/)?(\d{4})/(\d+)/([A-Za-z]{2}\d{3})(?=[/?#]|$)")
DEFAULT_YEARS = "2020,2019,2018,2017,2016,2015,2021"
S3_DENIED = b"<Code>AccessDenied</Code>"
EVENT_STATES = ("files", "empty", "unknown", "not asked", "no codes")


# --------------------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------------------
@dataclass
class Event:
    year: int
    event: int
    name: str
    level: str
    start: str
    codes: list[str] = field(default_factory=list)  # MS then QS, each from its last round: MS001, MS002, ...
    uncoded: int = 0  # tour-level rows without a usable stats link (mostly walkovers): not asked for
    series: str = ""  # ManTennisData's series_id ("atp", "1000", "ch")

    @property
    def key(self) -> str:
        return f"{self.year}/{self.event}"


def code_of(url) -> tuple[int, int, str] | None:
    """(year, event id, match code) from an atptour.com match-stats or Stats Centre link, else None."""
    m = CODE_RX.search(url or "")
    return (int(m.group(1)), int(m.group(2)), m.group(3).upper()) if m else None


def code_order(mid: str) -> tuple[int, str, int]:
    """The main draw before qualifying, each from its last round: MS001 (the final), MS002 ... then QS001 ..."""
    return ({"MS": 0, "QS": 1}.get(mid[:2], 2), mid[:2], int(mid[2:]))


def load_plan(years: list[int], since: str, until: str, events: set[int] | None = None,
              root: Path | None = None, series=TOUR_SERIES) -> list[Event]:
    """Every event of ManTennisData's ``series`` (default: tour level) and ``years`` that began in [since, until]
    (YYYYMMDD), with its match codes, in ``years`` order and then by start date. Work package P9
    (infosys_atp_recent.py) adds the Challengers ("ch")."""
    import pyarrow.parquet as pq

    root = root or MTD_ROOT
    tours = pq.read_table(root / "atp_tournaments.parquet",
                          columns=["id", "name", "series_id", "series_category_id", "start_dtm"]).to_pylist()
    meta = {t["id"]: t for t in tours if t["series_id"] in series and since <= (t["start_dtm"] or "") <= until}
    plan: list[Event] = []
    for year in years:
        path = root / f"atp_matches_{year}.parquet"
        if not path.exists():
            raise SystemExit(f"{P.rel(path)} is missing: download ManTennisData's season first "
                             f"(./python.sh -m src.ingest.public_dump.mantennisdata --years {year})")
        by_event: dict[str, Event] = {}
        codes: dict[str, set[str]] = defaultdict(set)
        for row in pq.read_table(path, columns=["tournament_id", "stats_url"]).to_pylist():
            t = meta.get(row["tournament_id"])
            if t is None:
                continue
            event = int(str(row["tournament_id"]).split("-")[1])
            if events and event not in events:
                continue
            ev = by_event.setdefault(row["tournament_id"], Event(year, event, t["name"], t["series_category_id"],
                                                                  t["start_dtm"], series=t["series_id"]))
            code = code_of(row["stats_url"])
            if code is None or code[:2] != (year, event):  # no link, or a link to another event (none seen)
                ev.uncoded += 1
            else:
                codes[row["tournament_id"]].add(code[2])
        for tid, ev in by_event.items():
            ev.codes = sorted(codes[tid], key=code_order)
        plan.extend(sorted(by_event.values(), key=lambda e: (e.start, e.event)))
    return plan


def parse_years(text: str) -> list[int]:
    years = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            years.extend(range(a, b + 1))
        elif part:
            years.append(int(part))
    return list(dict.fromkeys(years))


def url_of(year: int, event: int, route: str, mid: str) -> str:
    return HOST + ROUTES[route].format(year=year, event=event, mid=mid)


def dest_of(year: int, event: int, route: str, mid: str) -> Path:
    return P.raw_path(SOURCE, str(year), str(event), route, f"{mid}.json.gz")


def receipt_name(year: int, event: int, route: str, mid: str) -> str:
    return f"{year}/{event}/{route}/{mid}"


# --------------------------------------------------------------------------------------
# answers
# --------------------------------------------------------------------------------------
def served(receipt: dict) -> bool:
    return receipt.get("status") == 200 and not receipt.get("error")


def is_absent(receipt: dict) -> bool:
    return not receipt.get("error") and (bool(receipt.get("absent")) or receipt.get("status") == 404)


def outcome_of(receipt: dict) -> str:
    what = receipt.get("error") and "error" or receipt.get("absent") and "absent" or str(receipt.get("status"))
    return what + (":cached" if receipt.get("skipped") else "")


def envelope_validator(body: bytes):
    """None when the body is an Infosys envelope ``{lastModified, response, ...}``, else the problem. Only its keys
    are looked at."""
    problem = P.json_validator(body)
    if problem:
        return problem
    try:
        doc = json.loads(body)
    except ValueError:
        return "response is not JSON"
    if isinstance(doc, dict) and ("lastModified" in doc or "response" in doc):
        return None
    return "not an Infosys envelope" + (f" (keys {sorted(doc)[:6]})" if isinstance(doc, dict) else "")


def utc_of(ms) -> str | None:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return None


def envelope_facts(doc) -> dict:
    """The envelope's plain fields, for the inventory: lastModified, the ciphertext's length in base64 characters,
    whether it is a whole number of 16-byte AES blocks, and whether ``data`` is null. Nothing is decrypted."""
    doc = doc if isinstance(doc, dict) else {}
    text = doc.get("response") or ""
    try:
        n = len(base64.b64decode(text + "=" * (-len(text) % 4), validate=True)) if text else 0
    except (binascii.Error, ValueError):
        n = -1
    return {"last_modified": doc.get("lastModified"), "last_modified_utc": utc_of(doc.get("lastModified")),
            "response_chars": len(text), "aes_blocks_whole": n > 0 and n % 16 == 0,
            "data_null": "data" in doc and doc["data"] is None}


class Calibration:
    """The routes that have served a file to these headers. Only there is S3's HTTP 403 AccessDenied read as "no such
    object"; on any other route it is a refusal, and the run stops (feeds.FeedClient)."""

    def __init__(self, receipts):
        self.ok: set[str] = set()
        for name, rec in receipts.all().items():
            parts = name.split("/")
            if len(parts) == 4 and served(rec):
                self.ok.add(parts[2])
        self.current: str | None = None

    def not_found(self, response) -> str | None:
        if response.status_code == 403 and S3_DENIED in response.content[:4096] and self.current in self.ok:
            return "S3 AccessDenied on a calibrated route: no such object"
        return None


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def make_client(args, cal: Calibration):
    return F.FeedClient(IMPERSONATE, not_found=cal.not_found, min_interval=args.min_interval, jitter=args.jitter,
                        max_requests=args.max_requests, timeout=args.timeout)


def fetch_one(client, receipts, cal: Calibration, year: int, event: int, route: str, mid: str, args,
              outcomes: Counter, purpose: str = "plan") -> dict:
    cal.current = route
    receipt = P.fetch(client, url_of(year, event, route, mid), dest_of(year, event, route, mid), receipts,
                      name=receipt_name(year, event, route, mid), refresh=args.refresh, validator=envelope_validator,
                      compress=True, headers=HEADERS, absent=cal.not_found,
                      extra={"year": year, "event_id": event, "route": route, "match_id": mid, "purpose": purpose})
    if served(receipt):
        cal.ok.add(route)
    outcomes[f"{year}:{route}:{outcome_of(receipt)}"] += 1
    return receipt


def calibrate(client, receipts, cal: Calibration, routes: list[str], args, outcomes: Counter) -> None:
    for route in routes:
        if route in cal.ok:
            continue
        year, event, mid = CALIBRATION[route]
        receipt = fetch_one(client, receipts, cal, year, event, route, mid, args, outcomes, purpose="calibration")
        if not served(receipt):
            raise P.Blocked(f"calibration file {receipt_name(year, event, route, mid)} was not served "
                            f"({outcome_of(receipt)}), so S3's 403 cannot be read on {route}")


def discover(client, receipts, cal: Calibration, ev: Event, routes: list[str], args, outcomes: Counter) -> dict:
    """Which routes hold the event's first code; when none does, which hold its second (on GUARD_ROUTES only)."""
    hits = {route: served(fetch_one(client, receipts, cal, ev.year, ev.event, route, ev.codes[0], args, outcomes))
            for route in routes}
    if not any(hits.values()) and len(ev.codes) > 1:
        for route in GUARD_ROUTES:
            if route in routes and served(fetch_one(client, receipts, cal, ev.year, ev.event, route, ev.codes[1],
                                                    args, outcomes)):
                hits[route] = True
    return hits


def expand(client, receipts, cal: Calibration, ev: Event, routes: list[str], args, outcomes: Counter) -> list[dict]:
    """Every code of an event with a file. Per route and family, codes are asked in order until the first
    --skip-after are all absent; once a file has been seen there, every code is asked. Returns the families given up."""
    families: dict[str, list[str]] = defaultdict(list)
    for mid in ev.codes:
        families[mid[:2]].append(mid)
    notes = []
    for route in routes:
        for family, codes in families.items():
            misses, seen = 0, False
            for mid in codes:
                receipt = fetch_one(client, receipts, cal, ev.year, ev.event, route, mid, args, outcomes)
                if served(receipt):
                    seen = True
                elif not seen and is_absent(receipt):
                    misses += 1
                    if args.skip_after and misses >= args.skip_after:
                        notes.append({"event": ev.key, "name": ev.name, "route": route, "family": family,
                                      "reason": f"the first {misses} codes are absent", "last_code": mid})
                        break
    return notes


# --------------------------------------------------------------------------------------
# evidence (plain fields only)
# --------------------------------------------------------------------------------------
def event_names(root: Path | None = None) -> dict[tuple[int, int], tuple[str, str, str]]:
    """(year, event id) -> (name, level, start) for every ManTennisData event, calibration files' events included."""
    import pyarrow.parquet as pq

    path = (root or MTD_ROOT) / "atp_tournaments.parquet"
    if not path.exists():
        return {}
    out = {}
    for t in pq.read_table(path, columns=["id", "name", "series_category_id", "start_dtm"]).to_pylist():
        year, _, event = str(t["id"]).partition("-")
        if year.isdigit() and event.isdigit():
            out[(int(year), int(event))] = (t["name"], t["series_category_id"], t["start_dtm"])
    return out


def event_state(ev: Event, recs: dict[tuple[str, str], dict], routes: list[str]) -> str:
    """files: a file is held; empty: the discovery's every answer was "no such object"; unknown: an answer was an
    error; not asked: the discovery is incomplete."""
    if not ev.codes:
        return "no codes"
    if any(served(r) for r in recs.values()):
        return "files"
    asked = [(route, ev.codes[0]) for route in routes]
    if len(ev.codes) > 1:
        asked += [(route, ev.codes[1]) for route in GUARD_ROUTES if route in routes]
    answers = [recs.get(key) for key in asked]
    if any(a is not None and a.get("error") for a in answers):
        return "unknown"
    if all(a is not None and is_absent(a) for a in answers):
        return "empty"
    return "not asked"


def write_evidence(receipts, plan: list[Event], routes: list[str], study_root: Path | None = None) -> dict:
    """infosys_atp_events.csv and infosys_atp_files.csv, from the receipts and the saved files' plain fields; returns
    the summary's counts."""
    study_root = study_root or STUDY_ROOT
    study_root.mkdir(parents=True, exist_ok=True)
    by_event: dict[tuple[int, int], dict[tuple[str, str], dict]] = defaultdict(dict)
    for name, rec in receipts.all().items():
        parts = name.split("/")
        if len(parts) == 4 and parts[0].isdigit() and parts[1].isdigit():
            by_event[(int(parts[0]), int(parts[1]))][(parts[2], parts[3])] = rec
    names = event_names()
    in_plan = {(ev.year, ev.event): ev for ev in plan}

    file_rows, by_year_route = [], defaultdict(Counter)
    for (year, event), recs in sorted(by_event.items()):
        name, level, start = names.get((year, event), (None, None, None))
        for (route, mid), rec in sorted(recs.items()):
            c = by_year_route[f"{year}|{route}"]
            c["files" if served(rec) else "absent" if is_absent(rec) else "errors"] += 1
            path = dest_of(year, event, route, mid)
            if not served(rec) or not path.exists():
                continue
            c["bytes"] += int(rec.get("bytes") or 0)
            c["stored_bytes"] += path.stat().st_size
            try:
                facts = envelope_facts(P.read_json(path))
            except (OSError, ValueError) as err:
                facts = {"last_modified": None, "last_modified_utc": None, "response_chars": None,
                         "aes_blocks_whole": False, "data_null": None, "read_error": f"{type(err).__name__}: {err}"}
            file_rows.append({"year": year, "event_id": event, "event_name": name, "level": level, "start": start,
                              "match_id": mid, "family": mid[:2], "route": route,
                              "purpose": rec.get("purpose") or ("plan" if (year, event) in in_plan else "other"),
                              "bytes": rec.get("bytes"), "stored_bytes": path.stat().st_size, "sha256": rec.get("sha256"),
                              **facts, "retrieved_at": rec.get("retrieved_at"), "path": P.rel(path)})
    file_cols = ["year", "event_id", "event_name", "level", "start", "match_id", "family", "route", "purpose", "bytes",
                 "stored_bytes", "sha256", "last_modified", "last_modified_utc", "response_chars", "aes_blocks_whole",
                 "data_null", "read_error", "retrieved_at", "path"]
    with (study_root / "infosys_atp_files.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=file_cols)
        w.writeheader()
        w.writerows({c: r.get(c) for c in file_cols} for r in file_rows)

    event_rows, states = [], defaultdict(Counter)
    for ev in plan:
        recs = by_event.get((ev.year, ev.event), {})
        state = event_state(ev, recs, routes)
        states[str(ev.year)][state] += 1
        row = {"year": ev.year, "event_id": ev.event, "name": ev.name, "level": ev.level, "start": ev.start,
               "codes": len(ev.codes), "codes_ms": sum(c.startswith("MS") for c in ev.codes),
               "codes_qs": sum(c.startswith("QS") for c in ev.codes), "uncoded_rows": ev.uncoded, "state": state,
               "matches_with_a_file": len({mid for (_, mid), r in recs.items() if served(r)})}
        for route in routes:
            row[f"files_{route}"] = sum(1 for (r, _), x in recs.items() if r == route and served(x))
            row[f"absent_{route}"] = sum(1 for (r, _), x in recs.items() if r == route and is_absent(x))
        row["errors"] = sum(1 for x in recs.values() if x.get("error"))
        event_rows.append(row)
    event_cols = (["year", "event_id", "name", "level", "start", "codes", "codes_ms", "codes_qs", "uncoded_rows",
                   "state", "matches_with_a_file"] + [f"files_{r}" for r in routes] + [f"absent_{r}" for r in routes]
                  + ["errors"])
    with (study_root / "infosys_atp_events.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=event_cols)
        w.writeheader()
        w.writerows(event_rows)

    return {
        "events_by_state": {y: {s: c[s] for s in EVENT_STATES if c[s]} for y, c in sorted(states.items())},
        "events_with_files": [f"{r['year']}/{r['event_id']} {r['name']}: "
                              + ", ".join(f"{route} {r[f'files_{route}']}" for route in routes if r[f"files_{route}"])
                              for r in event_rows if r["state"] == "files"],
        "by_year_route": {k: dict(v) for k, v in sorted(by_year_route.items())},
        "files_held": len(file_rows),
        "files_held_in_plan": sum(r["purpose"] == "plan" for r in file_rows),
        "bytes_served": sum(int(r["bytes"] or 0) for r in file_rows),
        "bytes_stored": sum(int(r["stored_bytes"] or 0) for r in file_rows),
        "files_not_whole_aes_blocks": sum(not r["aes_blocks_whole"] for r in file_rows),
    }


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    years = parse_years(args.years)
    routes = [r.strip() for r in args.routes.split(",")] if args.routes else list(ROUTES)
    unknown = [r for r in routes if r not in ROUTES]
    if unknown:
        raise SystemExit(f"unknown routes {unknown}; known: {', '.join(ROUTES)}")
    events = {int(e) for e in args.events.split(",")} if args.events else None
    plan = load_plan(years, args.since, args.until, events)
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "instruction": INSTRUCTION,
               "decision": DECISION, "decrypted": False, "years": years, "routes": routes,
               "events_selected": len(plan), "matches_selected": sum(len(ev.codes) for ev in plan),
               "rows_without_a_code": sum(ev.uncoded for ev in plan)}
    outcomes, notes = Counter(), []
    if not args.inventory_only:
        cal = Calibration(receipts)
        client = make_client(args, cal)
        try:
            calibrate(client, receipts, cal, routes, args, outcomes)
            with_files = []
            for i, ev in enumerate(plan, 1):
                if not ev.codes:
                    continue
                hits = discover(client, receipts, cal, ev, routes, args, outcomes)
                if any(hits.values()):
                    with_files.append(ev)
                P.log(f"[{SOURCE}] discover {i}/{len(plan)} {ev.key} {ev.name}: "
                      + (", ".join(r for r, h in hits.items() if h) or "no file") + f"; requests={client.requests}")
            summary["events_with_files_found"] = len(with_files)
            if args.phase == "all":
                for i, ev in enumerate(with_files, 1):
                    before = client.requests
                    notes.extend(expand(client, receipts, cal, ev, routes, args, outcomes))
                    P.log(f"[{SOURCE}] expand {i}/{len(with_files)} {ev.key} {ev.name}: {len(ev.codes)} codes, "
                          f"{client.requests - before} requests; requests={client.requests}")
        except (P.Blocked, P.BudgetExhausted, KeyboardInterrupt) as stop:
            summary["stopped"] = f"{type(stop).__name__}: {stop}"
            P.log(f"[{SOURCE}] STOPPED: {stop}")
        summary["client"] = client.stats()
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    summary["families_given_up"] = notes
    summary.update(write_evidence(receipts, plan, routes))
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts"] = len(receipts.all())
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("infosys_atp_summary.json", summary, root=STUDY_ROOT)
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--years", default=DEFAULT_YEARS, help=f"comma list or ranges, in run order (default {DEFAULT_YEARS})")
    parser.add_argument("--since", default="20150101", help="first event start date, YYYYMMDD (default 20150101)")
    parser.add_argument("--until", default="20211017", help="last event start date, YYYYMMDD (default 20211017)")
    parser.add_argument("--events", help="comma list of ATP event ids (default: every tour-level event)")
    parser.add_argument("--routes", help=f"comma list (default: all of {','.join(ROUTES)})")
    parser.add_argument("--phase", choices=("discover", "all"), default="all",
                        help="discover: calibrate and ask each event's final only; all: then expand (default)")
    parser.add_argument("--max-requests", type=int, default=15000, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0, help="up to this many extra seconds, drawn at random")
    parser.add_argument("--timeout", type=int, default=60, help="seconds per request (Court Vision files run to MBs)")
    parser.add_argument("--skip-after", type=int, default=8,
                        help="give a route's family (MS or QS) up when its first N codes are all absent (0: never)")
    parser.add_argument("--refresh", action="store_true", help="fetch files already held (and absences) again")
    parser.add_argument("--inventory-only", action="store_true", help="no HTTP; rewrite the evidence from the receipts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    P.log(f"[{SOURCE}] done in {summary['seconds']} s; {summary['files_held_in_plan']} files held in the plan; "
          f"{summary['receipts_with_errors']} receipts with errors"
          + (f"; stopped: {summary['stopped']}" if summary.get("stopped") else ""))
    return 1 if summary.get("stopped") or summary["receipts_with_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
