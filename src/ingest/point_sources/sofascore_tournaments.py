"""SofaScore by tournament: every event of chosen tournament seasons, and the point-by-point record and box score
of the events asked for.

sofascore.py lists by player (a team's match list); this adapter lists by tournament season, as the data map's gap
checks did (src/eda/gap_sources/sofascore_probe.py). The API, client, pacing, block handling, record shapes and
parsers are sofascore.py's and common.py's.

Endpoints (public JSON behind SofaScore's own site; no key):
    /api/v1/category/<id>/scheduled-events/<date>                    a category's events around that day; used to
                                                                     find a season whose ids are not known yet
    /api/v1/unique-tournament/<id>/season/<id>/events/last/<page>    30 events a page, newest first, ``hasNextPage``
    /api/v1/event/<id>/point-by-point, /api/v1/event/<id>/statistics HTTP 404 when absent

Raw layout under data/raw/point_sources/sofascore_tournaments/ (bodies gzipped as received; receipts hash the
body itself):
    days/<category>/<date>.json.gz
    seasons/<utid>_<sid>/events_last_<page>.json.gz
    events/<event_id>/point-by-point.json.gz, statistics.json.gz
    _receipts.jsonl                                   one line per fetch, HTTP 404 included

Staged (data/dump/points/sofascore_tournaments/): events.parquet (every event of every season held, with the
seasons that list it and the outcome of its documents' fetch), points.parquet and statistics.parquet, with the
columns of sofascore.py's tables (``listed_in_seasons`` in place of ``listed_for_teams``). All strings.

Inputs:
    --seasons-file CSV   one row per season: ``utid`` and ``sid``; or, for a season whose ids are not known, blank
                         ids with ``category``, ``year``, ``name_pattern`` (a regular expression for the unique
                         tournament's name) and ``locate_days`` (dates separated by ";"): the day listings are read
                         in turn until one holds an event of that tournament and year.
    --events-file CSV    a column ``event_id``: the events whose point-by-point and statistics are fetched.
    --import-cache DIR   copy the answers of an earlier probe's cache (the layout of sofascore_probe.py) for the
                         seasons asked for and their events, byte for byte, instead of asking again.

Usage (the gap slam_points_ao_rg; files written by src/eda/ao_rg_points/):
    ./python.sh -m src.ingest.point_sources.sofascore_tournaments --seasons-file data/studies/ao_rg_points/sofascore_seasons.csv --import-cache data/raw/gap_sources/sofascore --list-only
    ./python.sh -m src.ingest.point_sources.sofascore_tournaments --seasons-file ... --events-file data/studies/ao_rg_points/sofascore_links.csv
    ./python.sh -m src.ingest.point_sources.sofascore_tournaments --stage-only
    add --browser when SofaScore challenges the plain client (see sofascore.py and browser.py)

SofaScore's terms forbid automated extraction; the owner decided on 23 Sep 2026 to collect regardless, for
non-commercial research (docs/studies/point_shot_sources/README.md#direct-download-24-september-2026). On 29 Sep
2026 the owner asked for the Australian Open and Roland Garros gap and deferred its SofaScore part while SofaScore
blocked the plain client (docs/decisions/2026-09-29-ao-rg-points.md). So far this adapter holds only the gap
probe's answers, imported; src/ingest/point_sources/sofascore_editions.py does the same job by gap (--gap).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P
from src.ingest.point_sources import sofascore as S
from src.ingest.public_dump import common as C

SOURCE = "sofascore_tournaments"
API = S.API
MAX_SEASON_PAGES = 40  # safety stop per season: 1,200 events (a Slam singles season lists about 280)
STUDY_DIR = P.PROJECT_ROOT / "data" / "studies" / "ao_rg_points"
EVENT_COLUMNS = ["listed_in_seasons" if c == "listed_for_teams" else c for c in S.EVENT_COLUMNS]
PARTS = ("point-by-point", "statistics")


# --------------------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------------------
def read_seasons(path: Path) -> list[dict]:
    """The seasons file's rows, ids as ints (None when blank) and ``locate_days`` as a list."""
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row = {k: (v or "").strip() for k, v in row.items()}
            for key in ("utid", "sid", "category"):
                row[key] = int(float(row[key])) if row.get(key) else None
            row["locate_days"] = [d for d in (row.get("locate_days") or "").split(";") if d]
            rows.append(row)
    return rows


def read_event_ids(path: Path) -> list[int]:
    """Distinct event ids of the file's ``event_id`` column, in file order (blank rows skipped)."""
    out, seen = [], set()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            value = (row.get("event_id") or "").strip()
            if not value:
                continue
            eid = int(float(value))
            if eid not in seen:
                seen.add(eid)
                out.append(eid)
    return out


def season_key(utid, sid) -> str:
    return f"{int(utid)}_{int(sid)}"


# --------------------------------------------------------------------------------------
# the raw folder
# --------------------------------------------------------------------------------------
def season_pages(key: str) -> list[tuple[int, Path]]:
    """(page, path) of a season's listing pages on disk, in page order."""
    folder = P.raw_path(SOURCE, "seasons", key)
    pages = []
    for path in folder.glob("events_last_*.json.gz"):
        try:
            pages.append((int(path.name[len("events_last_"):-len(".json.gz")]), path))
        except ValueError:
            continue
    return sorted(pages)


def held_seasons() -> list[str]:
    root = P.raw_path(SOURCE, "seasons")
    return sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []


def load_season_events(keys: list[str] | None = None) -> dict[int, dict]:
    """Every event listed in the seasons held (or in ``keys``), keyed by event id, with the seasons and pages that
    list it and the first listing file."""
    events: dict[int, dict] = {}
    for key in keys if keys is not None else held_seasons():
        for page, path in season_pages(key):
            for event in P.read_json(path).get("events") or []:
                entry = events.setdefault(event["id"], {"event": event, "seasons": [], "pages": [], "file": P.rel(path)})
                if key not in entry["seasons"]:
                    entry["seasons"].append(key)
                entry["pages"].append(f"{key}:{page}")
    return events


def event_doc_path(event_id, part: str) -> Path:
    return P.raw_path(SOURCE, "events", str(event_id), f"{part}.json.gz")


# --------------------------------------------------------------------------------------
# importing an earlier probe's answers
# --------------------------------------------------------------------------------------
def _probe_name_map(name: str) -> tuple[str, Path] | None:
    """The probe's receipt name -> (this adapter's receipt name, destination), for the kinds imported."""
    m = re.fullmatch(r"season/(\d+_\d+)/last_(\d+)", name)
    if m:
        return (f"seasons/{m.group(1)}/events_last_{m.group(2)}",
                P.raw_path(SOURCE, "seasons", m.group(1), f"events_last_{m.group(2)}.json.gz"))
    m = re.fullmatch(r"events/(\d+)/(point-by-point|statistics)", name)
    if m:
        return name, event_doc_path(m.group(1), m.group(2))
    m = re.fullmatch(r"category/(\d+)/(\d{4}-\d{2}-\d{2})", name)
    if m:
        return (f"days/{m.group(1)}/{m.group(2)}", P.raw_path(SOURCE, "days", m.group(1), f"{m.group(2)}.json.gz"))
    return None


def import_cache(cache: Path, receipts: C.Receipts, keys: set[str]) -> dict:
    """Copy the probe's answers for the seasons ``keys``: their listing pages, the documents of their events and
    the day listings that name them. Bodies are copied byte for byte (the probe gzipped them as this adapter does)
    and checked against the probe's SHA-256; 404 answers are imported as answers. A name this adapter already
    holds is left alone, and failed or unreadable answers are not imported (they are asked again)."""
    old = C.Receipts(cache.name, root=cache.parent)
    wanted_events: set[str] = set()
    counts = Counter()
    for pass_kind in ("season", "rest"):
        if pass_kind == "rest":  # the events of every page now held for these seasons, imported earlier or now
            wanted_events = {str(eid) for eid in load_season_events(sorted(keys))}
        for name, rec in sorted(old.all().items()):
            mapped = _probe_name_map(name)
            if mapped is None:
                continue
            new_name, dest = mapped
            kind = name.split("/", 1)[0]
            if (pass_kind == "season") != (kind == "season"):
                continue
            if kind == "season" and name.split("/")[1] not in keys:
                continue
            if kind == "events" and name.split("/")[1] not in wanted_events:
                continue
            if receipts.get(new_name):
                counts[f"{kind}:already held"] += 1
                continue
            if rec.get("error") or rec.get("status") not in (200, 404):
                counts[f"{kind}:not imported ({rec.get('error') or rec.get('status')})"] += 1
                continue
            source = P.PROJECT_ROOT / rec["dest"]
            if kind == "category":  # only the days that list an event of an imported season
                if rec.get("status") != 200 or not source.exists():
                    continue
                seasons_named = {season_key(S._dig(e, ("tournament", "uniqueTournament", "id")) or 0,
                                            S._dig(e, ("season", "id")) or 0)
                                 for e in P.read_json(source).get("events") or []}
                if not seasons_named & keys:
                    continue
            new = {**rec, "name": new_name, "dest": P.rel(dest), "imported_from": rec["dest"],
                   "imported_at": P.utc_now_iso()}
            if rec.get("status") == 200:
                if not source.exists():
                    counts[f"{kind}:not imported (file missing)"] += 1
                    continue
                body = gzip.decompress(source.read_bytes()) if rec.get("compressed") else source.read_bytes()
                if rec.get("sha256") and P.sha256_bytes(body) != rec["sha256"]:
                    counts[f"{kind}:not imported (hash differs)"] += 1
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                if rec.get("compressed"):
                    shutil.copyfile(source, dest)
                else:
                    dest.write_bytes(gzip.compress(body))
                new["compressed"] = True
            receipts.record(new)
            counts[f"{kind}:{rec.get('status')}"] += 1
    return dict(sorted(counts.items()))


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def locate_season(client: P.Client, receipts, row: dict) -> dict | None:
    """Find a season from its category's day listings: the first day holding an event whose unique tournament name
    matches ``name_pattern`` and whose season year is ``year``."""
    pattern = re.compile(row["name_pattern"])
    for day in row["locate_days"]:
        dest = P.raw_path(SOURCE, "days", str(row["category"]), f"{day}.json.gz")
        rec = P.fetch(client, f"{API}/category/{row['category']}/scheduled-events/{day}", dest, receipts,
                      name=f"days/{row['category']}/{day}", validator=P.json_validator, compress=True,
                      extra={"category": row["category"], "day": day})
        if rec.get("status") != 200 or rec.get("error"):
            continue
        hits = Counter()
        for e in P.read_json(dest).get("events") or []:
            ut = S._dig(e, ("tournament", "uniqueTournament")) or {}
            season = e.get("season") or {}
            if pattern.search(ut.get("name") or "") and str(season.get("year")) == str(row["year"]):
                hits[(ut.get("id"), season.get("id"), ut.get("name"), season.get("name"))] += 1
        if hits:
            (utid, sid, ut_name, season_name), n = hits.most_common(1)[0]
            return {"utid": utid, "sid": sid, "ss_tournament": ut_name, "ss_season": season_name,
                    "located_by": f"days/{row['category']}/{day}", "locate_hits": n}
    return None


def fetch_season(client: P.Client, receipts, key: str, *, refresh: bool = False) -> dict:
    """A season's listing pages until the API says there is no next page (or answers 404)."""
    utid, sid = key.split("_")
    pages = events = 0
    note = ""
    for page in range(MAX_SEASON_PAGES):
        dest = P.raw_path(SOURCE, "seasons", key, f"events_last_{page}.json.gz")
        rec = P.fetch(client, f"{API}/unique-tournament/{utid}/season/{sid}/events/last/{page}", dest, receipts,
                      name=f"seasons/{key}/events_last_{page}", refresh=refresh, validator=P.json_validator,
                      compress=True, extra={"utid": int(utid), "sid": int(sid), "page": page})
        if rec.get("status") == 404:
            note = f"404 after page {page - 1}"
            break
        if rec.get("error"):
            note = f"page {page}: {rec['error']}"
            break
        body = P.read_json(dest)
        pages += 1
        events += len(body.get("events") or [])
        if not body.get("hasNextPage"):
            note = f"hasNextPage false at page {page}"
            break
    else:
        note = f"stopped at the {MAX_SEASON_PAGES}-page safety limit"
    return {"season": key, "pages": pages, "events_listed": events, "end": note}


def fetch_event_docs(client: P.Client, receipts, event_id: int, *, parts=PARTS, refresh: bool = False) -> dict:
    return {part: P.fetch(client, f"{API}/event/{event_id}/{part}", event_doc_path(event_id, part), receipts,
                          name=f"events/{event_id}/{part}", refresh=refresh, validator=P.json_validator,
                          compress=True, extra={"event_id": event_id, "part": part})
            for part in parts}


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def stage(receipts) -> dict:
    """events.parquet, points.parquet and statistics.parquet from every season and event document on disk."""
    events = load_season_events()
    event_rows, point_rows, stat_rows = [], [], []
    for event_id, entry in sorted(events.items(), key=lambda kv: -(kv[1]["event"].get("startTimestamp") or 0)):
        row = S.flatten_event(entry["event"])
        row.update(listed_in_seasons=";".join(entry["seasons"]), listed_pages=";".join(entry["pages"]),
                   listing_file=entry["file"])
        pbp_rec = receipts.get(f"events/{event_id}/point-by-point") or {}
        row.update(pbp_status=pbp_rec.get("error") or pbp_rec.get("status"),
                   pbp_retrieved_at=pbp_rec.get("retrieved_at"), pbp_sha256=pbp_rec.get("sha256"))
        pbp_path = event_doc_path(event_id, "point-by-point")
        if pbp_rec.get("status") == 200 and not pbp_rec.get("error") and pbp_path.exists():
            pbp = P.read_json(pbp_path).get("pointByPoint") or []
            shape = S.pbp_shape(pbp)
            row.update(pbp_sets=shape["sets"], pbp_games=shape["games"], pbp_points=shape["points"])
            for r in S.point_rows(event_id, pbp):
                r.update(source_file=P.rel(pbp_path), source_sha256=pbp_rec.get("sha256"),
                         retrieved_at=pbp_rec.get("retrieved_at"))
                point_rows.append(r)
        stats_rec = receipts.get(f"events/{event_id}/statistics") or {}
        row.update(stats_status=stats_rec.get("error") or stats_rec.get("status"),
                   stats_retrieved_at=stats_rec.get("retrieved_at"), stats_sha256=stats_rec.get("sha256"))
        stats_path = event_doc_path(event_id, "statistics")
        if stats_rec.get("status") == 200 and not stats_rec.get("error") and stats_path.exists():
            statistics = P.read_json(stats_path).get("statistics") or []
            row["stats_periods"] = ";".join(str(p.get("period")) for p in statistics)
            for r in S.statistic_rows(event_id, statistics):
                r.update(source_file=P.rel(stats_path), source_sha256=stats_rec.get("sha256"),
                         retrieved_at=stats_rec.get("retrieved_at"))
                stat_rows.append(r)
        event_rows.append(row)
    now = P.utc_now_iso()
    out = {}
    for name, columns, rows in (("events", EVENT_COLUMNS, event_rows), ("points", S.POINT_COLUMNS, point_rows),
                                ("statistics", S.STAT_COLUMNS, stat_rows)):
        dest = P.dump_path(SOURCE, f"{name}.parquet")
        table = [[P.s(r.get(c)) for c in columns] for r in rows]
        stats = P.stage_table(SOURCE, dest, columns, table, source_file=P.rel(P.raw_path(SOURCE)), retrieved_at=now)
        out[name] = {"rows": stats["rows"], "dest": stats["dest"], "bytes": stats["bytes"]}
        P.log(f"[{SOURCE}] staged {stats['dest']}: {stats['rows']:,} rows")
    return out


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def make_client(args):
    if args.browser:
        from src.ingest.point_sources import browser as B

        return B.BrowserClient(args.browser, origin=S.SITE, url_map={S.API_HOST + "/": S.SITE + "/"},
                               token_key="sofa.captcha.token", min_interval=args.min_interval, jitter=args.jitter,
                               max_requests=args.max_requests, headers={"Accept": "*/*"})
    return P.Client(S.IMPERSONATE, min_interval=args.min_interval, jitter=args.jitter,
                    max_requests=args.max_requests, headers=dict(S.HEADERS))


def run(args) -> dict:
    P.configure_stdout()
    started = time.time()
    receipts = P.receipts_for(SOURCE)
    summary = {"source": SOURCE, "started_at": P.utc_now_iso(), "args": vars(args), "seasons": [], "located": []}
    seasons = read_seasons(Path(args.seasons_file)) if args.seasons_file else []
    keys = {season_key(r["utid"], r["sid"]) for r in seasons if r["utid"] and r["sid"]}
    if args.import_cache:
        summary["imported"] = import_cache(Path(args.import_cache), receipts, keys)
        P.log(f"[{SOURCE}] imported from {args.import_cache}: {summary['imported']}")
    event_ids = read_event_ids(Path(args.events_file)) if args.events_file else []
    client = None
    outcomes = Counter()
    try:
        if not args.stage_only:
            client = make_client(args)
            for row in seasons:
                if row["utid"] and row["sid"]:
                    continue
                found = locate_season(client, receipts, row)
                summary["located"].append({"edition": row.get("edition"), "found": found})
                P.log(f"[{SOURCE}] located {row.get('edition')}: {found}")
                if found:
                    row.update(utid=found["utid"], sid=found["sid"])
            for row in seasons:
                if not (row["utid"] and row["sid"]):
                    continue
                info = fetch_season(client, receipts, season_key(row["utid"], row["sid"]), refresh=args.refresh_listings)
                info["edition"] = row.get("edition")
                summary["seasons"].append(info)
                P.log(f"[{SOURCE}] {row.get('edition') or info['season']}: {info['pages']} pages, "
                      f"{info['events_listed']} events ({info['end']}); requests={client.requests}")
            if not args.list_only:
                for n, event_id in enumerate(event_ids, 1):
                    for part, rec in fetch_event_docs(client, receipts, event_id, refresh=args.refresh).items():
                        outcomes[f"{part}:{rec.get('error') or rec.get('status')}" + (":cached" if rec.get("skipped") else "")] += 1
                    if n % 50 == 0 or n == len(event_ids):
                        P.log(f"[{SOURCE}] {n}/{len(event_ids)} events; requests={client.requests}; "
                              + ", ".join(f"{k}={v}" for k, v in sorted(outcomes.items())))
    except (P.Blocked, P.BudgetExhausted) as stop:
        summary["stopped"] = f"{type(stop).__name__}: {stop}"
        P.log(f"[{SOURCE}] STOPPED: {stop}")
    summary["events_selected"] = len(event_ids)
    summary["fetch_outcomes"] = dict(sorted(outcomes.items()))
    if client is not None:
        summary["client"] = client.stats()
        if hasattr(client, "close"):
            client.close()
    if not args.no_stage:
        summary["staged"] = stage(receipts)
    held = {eid for eid in event_ids if (receipts.get(f"events/{eid}/point-by-point") or {}).get("status") in (200, 404)}
    summary["events_selected_answered"] = len(held)
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["finished_at"] = P.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    path = P.write_summary("sofascore_summary.json", summary, root=Path(args.study_dir))
    P.log(f"[{SOURCE}] summary written to {P.rel(path)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--seasons-file", help="CSV of seasons (utid, sid; or category, year, name_pattern, locate_days)")
    parser.add_argument("--events-file", help="CSV with an event_id column: the events whose documents are fetched")
    parser.add_argument("--import-cache", help="an earlier probe's cache folder (e.g. data/raw/gap_sources/sofascore)")
    parser.add_argument("--list-only", action="store_true", help="locate and list the seasons; fetch no event documents")
    parser.add_argument("--max-requests", type=int, help="stop after this many HTTP requests")
    parser.add_argument("--min-interval", type=float, default=1.2, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=0.8)
    parser.add_argument("--refresh", action="store_true", help="refetch event documents already on disk (404s included)")
    parser.add_argument("--refresh-listings", action="store_true", help="refetch the season listing pages")
    parser.add_argument("--stage-only", action="store_true", help="no HTTP; rebuild the Parquet tables and summary")
    parser.add_argument("--no-stage", action="store_true", help="fetch only; skip the Parquet rebuild")
    parser.add_argument("--study-dir", default=str(STUDY_DIR), help="where the run summary and runs.jsonl go")
    parser.add_argument("--browser", nargs="?", const="http://localhost:9222", metavar="CDP_URL",
                        help="make the requests inside a Chrome tab reached over the DevTools Protocol at this URL "
                             "(bare flag: http://localhost:9222); see src/ingest/point_sources/browser.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    return 1 if summary.get("stopped") else 0


if __name__ == "__main__":
    sys.exit(main())
