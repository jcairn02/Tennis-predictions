"""tennis-data.co.uk season workbooks (register PUB014 / PUB015 / tennis_data_odds): ATP (2000+) and
WTA (2007+) main-tour results with set scores and closing bookmaker odds. Primary public source of
the odds branch.

Acquisition routes, tried in order and recorded per file in the receipts:
  1. live     https://www.tennis-data.co.uk/<year>[w]/<year>.xls|xlsx  (on 22 Sep 2026 every workbook
              path returned a Sedo/IONOS domain-parking page with HTTP 404 while the index pages still
              listed the files; the route stays first so a repaired site is used automatically)
  2. wayback  newest HTTP 200 capture in the Internet Archive (CDX lookup, ``id_`` raw download)
  3. local    the inherited June 2026 workbooks under data/raw/tennis_data_couk/ (2024-2026 only)

Staging partitions each season by the verbatim tournament-type column ("Series" for ATP, "Tier" for
WTA): data/dump/odds/tennis_data_couk/<tour>/<series_slug>/<year>.parquet.

Usage:
    ./python.sh -m src.ingest.public_dump.tennis_data_couk --start-year 2010
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "tennis_data_couk"
SITE = "https://www.tennis-data.co.uk"
FIRST_YEAR = {"atp": 2000, "wta": 2007}
LEGACY_ROOT = C.PROJECT_ROOT / "data" / "raw" / "tennis_data_couk"
CDX_URL = "http://web.archive.org/cdx/search/cdx"
INDEX_PAGES = {"alldata.php": "alldata.php.html", "alldataw.php": "alldataw.php.html", "notes.txt": "notes.txt"}
ALL_ROUTES = ("live", "wayback", "local")


def ext_for(year: int) -> str:
    return "xls" if year <= 2012 else "xlsx"


def segment(tour: str, year: int) -> str:
    return f"{year}w" if tour == "wta" else str(year)


def live_url(tour: str, year: int) -> str:
    return f"{SITE}/{segment(tour, year)}/{year}.{ext_for(year)}"


def wayback_url(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def wayback_captures(original_url: str, sess=None, retries: int = 4) -> list[dict]:
    """Newest-first list of HTTP 200 captures for a URL from the CDX API.

    The CDX service intermittently answers 503 or an empty body; those are retried with backoff
    and raised only after the last attempt, so an outage is reported rather than read as
    "never archived"."""
    params = {"url": original_url, "output": "json", "fl": "timestamp,statuscode,length,digest",
              "filter": "statuscode:200"}
    sess = sess or C.session()
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = sess.get(CDX_URL, params=params, timeout=60)
            if response.status_code != 200:
                raise RuntimeError(f"CDX HTTP {response.status_code}")
            text = response.text.strip()
            if not text:
                raise RuntimeError("CDX returned an empty body")
            rows = response.json()
            captures = [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []
            captures.sort(key=lambda c: c["timestamp"], reverse=True)
            return captures
        except (RuntimeError, ValueError) as err:
            last_error = err
        except Exception as err:  # network errors from requests
            last_error = err
        if attempt < retries:
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"CDX lookup failed after {retries + 1} attempts: {last_error}")


def acquire(tour: str, year: int, receipts: C.Receipts, refresh: bool, routes=ALL_ROUTES) -> dict:
    name = f"{tour}/{year}"
    dest = C.raw_path(SOURCE, tour, f"{year}.{ext_for(year)}")
    previous = receipts.get(name)
    if dest.exists() and previous and not previous.get("error") and not refresh:
        return {**previous, "skipped": True}
    url = live_url(tour, year)
    attempts = []
    if "live" in routes:
        receipt = C.download(url, dest, receipts, name=name, refresh=True, validator=C.workbook_magic,
                             extra={"route": "live"})
        if not receipt.get("error"):
            return receipt
        attempts.append(f"live: {receipt['error']}")
    if "wayback" in routes:
        try:
            captures = wayback_captures(url)
        except Exception as err:  # CDX outage should not stop the local fallback
            captures = []
            attempts.append(f"wayback lookup: {type(err).__name__}: {err}")
        for capture in captures[:3]:
            receipt = C.download(wayback_url(capture["timestamp"], url), dest, receipts, name=name, refresh=True,
                                 validator=C.workbook_magic,
                                 extra={"route": "wayback", "wayback_timestamp": capture["timestamp"],
                                        "wayback_digest": capture["digest"], "original_url": url,
                                        "wayback_captures_200": len(captures)})
            if not receipt.get("error"):
                return receipt
            attempts.append(f"wayback {capture['timestamp']}: {receipt['error']}")
        if not captures and "wayback lookup" not in " ".join(attempts):
            attempts.append("wayback: no HTTP 200 capture")
    if "local" in routes:
        for candidate in (LEGACY_ROOT / tour / f"{year}.xlsx", LEGACY_ROOT / tour / f"{year}.xls"):
            if not candidate.exists():
                continue
            body = candidate.read_bytes()
            problem = C.workbook_magic(body)
            if problem:
                attempts.append(f"local {candidate.name}: {problem}")
                continue
            dest = C.raw_path(SOURCE, tour, f"{year}{candidate.suffix.lower()}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            mtime = dt.datetime.fromtimestamp(candidate.stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")
            return receipts.record({"name": name, "url": url, "dest": C.rel(dest), "retrieved_at": C.utc_now_iso(),
                                    "route": "local_snapshot", "local_path": C.rel(candidate), "local_mtime": mtime,
                                    "bytes": len(body), "sha256": C.sha256_bytes(body), "attempts": attempts})
    return receipts.record({"name": name, "url": url, "dest": C.rel(dest), "retrieved_at": C.utc_now_iso(),
                            "error": "; ".join(attempts) or "no acquisition route enabled", "attempts": attempts})


def stage_workbook(tour: str, year: int, receipt: dict) -> list[dict]:
    dest = C.PROJECT_ROOT / receipt["dest"]
    sheet, header, rows, workbook_meta = C.read_workbook(dest)
    partition_col = next((c for c in ("Series", "Tier") if c in header), None)
    col_index = header.index(partition_col) if partition_col else None
    groups: dict = {}
    for number, fields in enumerate(rows, start=1):
        value = fields[col_index] if col_index is not None and col_index < len(fields) else None
        groups.setdefault(value, []).append((number, fields))
    for stale in C.dump_path("odds", SOURCE, tour).glob(f"*/{year}.parquet*"):
        stale.unlink()
    staged = []
    for value, group in groups.items():
        out = C.dump_path("odds", SOURCE, tour, C.slugify(value), f"{year}.parquet")
        prov = C.Provenance(SOURCE, receipt["dest"], receipt.get("sha256"), receipt.get("retrieved_at"),
                            {"_route": receipt.get("route"), "_wayback_timestamp": receipt.get("wayback_timestamp"),
                             "_partition_column": partition_col, "_partition_value": value, "_sheet": sheet})
        stats = C.stage_rows(header, iter(group), out, prov)
        stats["source_path"] = receipt["dest"]
        meta = C.staged_meta("odds", SOURCE, out, receipt, stats, tour=tour, year=year, route=receipt.get("route"),
                             wayback_timestamp=receipt.get("wayback_timestamp"), local_path=receipt.get("local_path"),
                             partition_column=partition_col, partition_value=value, workbook=workbook_meta)
        staged.append(meta)
    return staged


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    routes = tuple(r.strip() for r in getattr(args, "tdcouk_routes", ",".join(ALL_ROUTES)).split(",") if r.strip())
    for page, filename in INDEX_PAGES.items():
        C.download(f"{SITE}/{page}", C.raw_path(SOURCE, "docs", filename), receipts, name=f"docs/{page}",
                   refresh=True, validator=C.not_html if page.endswith(".txt") else None)
    staged, skipped = [], []
    for tour in ("atp", "wta"):
        first = max(args.start_year, FIRST_YEAR[tour])
        if args.start_year < FIRST_YEAR[tour]:
            skipped.append({"path": f"{tour}/{args.start_year}-{FIRST_YEAR[tour] - 1}",
                            "reason": f"provider publishes {tour.upper()} files from {FIRST_YEAR[tour]}"})
        for year in C.years(first, args.end_year):
            receipt = acquire(tour, year, receipts, args.refresh, routes)
            if receipt.get("error"):
                C.log(f"[{SOURCE}] FAIL {tour} {year}: {receipt['error']}")
                continue
            already = any(C.dump_path("odds", SOURCE, tour).glob(f"*/{year}.parquet"))
            if already and receipt.get("skipped") and not args.refresh:
                continue
            metas = stage_workbook(tour, year, receipt)
            staged.extend(metas)
            C.log(f"[{SOURCE}] {tour} {year} via {receipt.get('route')}: "
                  f"{sum(m['rows'] for m in metas)} rows into {len(metas)} tournament-type partitions")
    return C.summarize(receipts, staged, skipped)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-year", type=int, default=C.DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=C.DEFAULT_END_YEAR)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--tdcouk-routes", default=",".join(ALL_ROUTES),
                        help="comma list from live,wayback,local in the order to try")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done: {summary['staged_files']} staged files, {summary['staged_rows']:,} rows, "
          f"{len(summary['errors'])} download errors")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
