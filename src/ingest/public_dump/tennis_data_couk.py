"""tennis-data.co.uk season workbooks (register PUB014 / PUB015 / tennis_data_odds): ATP (2000+) and
WTA (2007+) main-tour results with set scores and closing bookmaker odds. Primary public source of
the odds branch.

Acquisition routes, tried in order and recorded per file in the receipts:
  1. live     the workbook link on the provider's listing page, data.php. The relaunched site (seen
              5 Oct 2026) serves workbooks under an unannounced directory, e.g.
              /hrjk-85HytOjkhth76j_ygh4jf7/2026w/2026.xlsx, answers 404 on the old
              /<year>[w]/<year>.xls|xlsx paths and redirects alldata.php and alldataw.php to data.php.
              A season the listing does not link is tried at its old path. (On 22 Sep 2026 every
              workbook path returned a Sedo/IONOS domain-parking page with HTTP 404.)
  2. wayback  newest HTTP 200 capture of the old path in the Internet Archive (CDX lookup, ``id_``
              raw download)
  3. local    the inherited June 2026 workbooks under data/raw/tennis_data_couk/ (2024-2026 only)

A refresh that replaces a workbook with different bytes keeps the replaced file and its receipt under
data/raw/public_dump/tennis_data_couk/superseded/<tour>/: data/raw is not under version control, and
earlier studies were built on those bytes.

Staging partitions each season by the verbatim tournament-type column ("Series" for ATP, "Tier" for
WTA): data/dump/odds/tennis_data_couk/<tour>/<series_slug>/<year>.parquet.

Usage:
    ./python.sh -m src.ingest.public_dump.tennis_data_couk --start-year 2010
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "tennis_data_couk"
SITE = "https://www.tennis-data.co.uk"
FIRST_YEAR = {"atp": 2000, "wta": 2007}
LEGACY_ROOT = C.PROJECT_ROOT / "data" / "raw" / "tennis_data_couk"
CDX_URL = "http://web.archive.org/cdx/search/cdx"
LISTING_PAGE = "data.php"
INDEX_PAGES = {LISTING_PAGE: "data.php.html", "notes.txt": "notes.txt"}
# a season link: any directory prefix, then <year>[w]/<year>.xls|xlsx, e.g. hrjk-.../2026w/2026.xlsx
WORKBOOK_LINK = re.compile(r"""href\s*=\s*["']?([^"'\s>]*?(\d{4})(w?)/\2\.xlsx?)(?=["'\s>])""", re.IGNORECASE)
ALL_ROUTES = ("live", "wayback", "local")


def ext_for(year: int) -> str:
    return "xls" if year <= 2012 else "xlsx"


def segment(tour: str, year: int) -> str:
    return f"{year}w" if tour == "wta" else str(year)


def legacy_url(tour: str, year: int) -> str:
    """The pre-relaunch path: what the Internet Archive holds captures of."""
    return f"{SITE}/{segment(tour, year)}/{year}.{ext_for(year)}"


def listed_urls(html: str, base: str) -> dict[tuple[str, int], str]:
    """(tour, year) -> absolute URL of every season workbook the listing page links."""
    links: dict[tuple[str, int], str] = {}
    for match in WORKBOOK_LINK.finditer(html):
        links.setdefault(("wta" if match.group(3) else "atp", int(match.group(2))), urljoin(base, match.group(1)))
    return links


def read_listing(receipts: C.Receipts) -> dict[tuple[str, int], str]:
    """Workbook links from this run's copy of the listing page; empty when that fetch failed."""
    receipt = receipts.get(f"docs/{LISTING_PAGE}")
    if not receipt or receipt.get("error"):
        return {}
    html = (C.PROJECT_ROOT / receipt["dest"]).read_text(encoding="utf-8", errors="replace")
    return listed_urls(html, receipt.get("final_url") or receipt["url"])


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


def acquire(tour: str, year: int, receipts: C.Receipts, refresh: bool, routes=ALL_ROUTES,
            listing: dict | None = None) -> dict:
    name = f"{tour}/{year}"
    url = (listing or {}).get((tour, year)) or legacy_url(tour, year)
    dest = C.raw_path(SOURCE, tour, f"{year}{Path(urlparse(url).path).suffix.lower()}")
    previous = receipts.get(name)
    if dest.exists() and previous and not previous.get("error") and not refresh:
        return {**previous, "skipped": True}
    old = dest.read_bytes() if dest.exists() else None
    receipt = fetch_routes(name, tour, year, url, dest, receipts, routes)
    return keep_superseded(old if receipt.get("dest") == C.rel(dest) else None, previous, receipt)


def keep_superseded(old: bytes | None, previous: dict | None, receipt: dict) -> dict:
    """Keep the bytes a download replaced, beside their receipt, when the new file differs."""
    if old is None or receipt.get("error") or receipt.get("sha256") == C.sha256_bytes(old):
        return receipt
    old_sha = C.sha256_bytes(old)
    previous = previous if previous and previous.get("sha256") == old_sha else {}
    stamp = previous.get("wayback_timestamp") or re.sub(r"\D", "", previous.get("retrieved_at", ""))[:14] or "unknown"
    dest = C.PROJECT_ROOT / receipt["dest"]
    kept = C.raw_path(SOURCE, "superseded", dest.parent.name,
                      f"{dest.stem}.{previous.get('route', 'unknown')}-{stamp}.{old_sha[:12]}{dest.suffix}")
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_bytes(old)
    C.write_meta(kept, {"sha256": old_sha, "bytes": len(old), "receipt": previous or None, "replaced_by": receipt})
    C.log(f"[{SOURCE}] {receipt['name']} changed; kept the replaced file as {C.rel(kept)}")
    return {**receipt, "superseded": C.rel(kept)}


def fetch_routes(name: str, tour: str, year: int, url: str, dest: Path, receipts: C.Receipts, routes) -> dict:
    original = legacy_url(tour, year)
    attempts = []
    if "live" in routes:
        receipt = C.download(url, dest, receipts, name=name, refresh=True, validator=C.workbook_magic,
                             extra={"route": "live"})
        if not receipt.get("error"):
            return receipt
        attempts.append(f"live: {receipt['error']}")
    if "wayback" in routes:
        try:
            captures = wayback_captures(original)
        except Exception as err:  # CDX outage should not stop the local fallback
            captures = []
            attempts.append(f"wayback lookup: {type(err).__name__}: {err}")
        for capture in captures[:3]:
            receipt = C.download(wayback_url(capture["timestamp"], original), dest, receipts, name=name,
                                 refresh=True, validator=C.workbook_magic,
                                 extra={"route": "wayback", "wayback_timestamp": capture["timestamp"],
                                        "wayback_digest": capture["digest"], "original_url": original,
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
    listing = read_listing(receipts)
    C.log(f"[{SOURCE}] {len(listing)} workbook links on {LISTING_PAGE}"
          + ("" if listing else "; trying the old /<year>[w]/ paths"))
    staged, skipped = [], []
    for tour in ("atp", "wta"):
        first = max(args.start_year, FIRST_YEAR[tour])
        if args.start_year < FIRST_YEAR[tour]:
            skipped.append({"path": f"{tour}/{args.start_year}-{FIRST_YEAR[tour] - 1}",
                            "reason": f"provider publishes {tour.upper()} files from {FIRST_YEAR[tour]}"})
        for year in C.years(first, args.end_year):
            receipt = acquire(tour, year, receipts, args.refresh, routes, listing)
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
