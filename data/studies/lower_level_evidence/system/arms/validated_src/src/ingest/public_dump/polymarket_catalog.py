"""Polymarket catalog extension: tennis events created AFTER the saved Gamma census.

The audited census (data/studies/tennis_data_audit/polymarket/, snapshot 2026-09-10) is never
modified. This adapter pages https://gamma-api.polymarket.com/events?tag_id=864 newest-first and keeps
every event whose id is above the highest id already known (census or a previous extension run). Raw
pages are stored with receipts; normalised rows use the same fields as the census
(src/eda/tennis_data_audit/polymarket_census.py) so polymarket_prices can merge both catalogs.

An event captured before its matches finished keeps its open markets in the catalog: no result, no close
time. --revisit fetches again every event with a match-winner market that the staged index
(data/dump/odds/polymarket/, built by polymarket_prices.py) still shows open, once its sporting date is
--settle-hours past, and appends the current rows to the same files with catalog "revisit".
polymarket_prices.py then uses the latest row of each event and market.

Layout:
    data/raw/public_dump/polymarket_catalog/pages/<run>/<offset>.json     raw pages (revisits: <run>-revisit)
    data/raw/public_dump/polymarket_catalog/events_extension.jsonl         normalised events (append-only)
    data/raw/public_dump/polymarket_catalog/markets_extension.jsonl.gz     normalised markets (append-only)

Usage:
    ./python.sh -m src.ingest.public_dump.polymarket_catalog
    ./python.sh -m src.ingest.public_dump.polymarket_catalog --revisit
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "polymarket_catalog"
GAMMA = "https://gamma-api.polymarket.com"
CENSUS_EVENTS = C.PROJECT_ROOT / "data" / "studies" / "tennis_data_audit" / "polymarket" / "events.jsonl"
TENNIS_TAG = 864
PAGE_SIZE = 100
INDEX_DIR = C.PROJECT_ROOT / "data" / "dump" / "odds" / "polymarket"
REVISIT_BATCH = 50   # event ids per /events request; checked with batches of 3 and 50 on 5 Oct 2026
SETTLE_HOURS = 6.0
MARKET_FIELDS = ("id", "question", "slug", "conditionId", "questionID", "sportsMarketType", "line", "gameStartTime",
                 "eventStartTime", "startDate", "endDate", "createdAt", "closedTime", "closed", "volume", "volumeNum",
                 "resolutionSource", "description", "umaResolutionStatus", "feesEnabled", "feeType", "feeSchedule",
                 "acceptingOrders", "acceptingOrdersTimestamp", "groupItemTitle", "gameId", "teamAID", "teamBID")


def events_path() -> Path:
    return C.raw_path(SOURCE, "events_extension.jsonl")


def markets_path() -> Path:
    return C.raw_path(SOURCE, "markets_extension.jsonl.gz")


def parse_date(value):
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=dt.timezone.utc) if parsed.tzinfo is None else parsed
    except ValueError:
        return None


def unpack(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return value or []


def normalise_event(event: dict, retrieved_at: str, catalog: str = "extension") -> tuple[dict, list[dict]]:
    """Same row shape as the census, plus catalog provenance."""
    eid = str(event["id"])
    slug = event.get("slug", "")
    date_match = re.search(r"(20\d\d-\d\d-\d\d)", slug)
    dates = {"startTime": event.get("startTime"), "eventDate": event.get("eventDate"),
             "slug_date": date_match.group(1) if date_match else None, "endDate": event.get("endDate")}
    time_field, event_time = next(((k, parse_date(v)) for k, v in dates.items() if parse_date(v)), (None, None))
    closed = parse_date(event.get("closedTime"))
    if not closed:
        closes = [parse_date(m.get("closedTime")) for m in event.get("markets", [])]
        closed = max((x for x in closes if x), default=None)
    series = [{"id": s.get("id"), "slug": s.get("slug"), "title": s.get("title")} for s in unpack(event.get("series"))]
    row = {"id": eid, "slug": slug, "title": event.get("title"), "url": "https://polymarket.com/event/" + slug,
           "dates": dates, "date_basis": time_field, "sport_date": event_time.isoformat() if event_time else None,
           "in_sport_window": None, "metadata_trading_overlap": None,
           "createdAt": event.get("createdAt"), "startDate": event.get("startDate"),
           "closedTime_derived": closed.isoformat() if closed else None,
           "closed": event.get("closed"), "volume": event.get("volume"), "series": series,
           "tags": [{"id": t.get("id"), "label": t.get("label"), "slug": t.get("slug")} for t in unpack(event.get("tags"))],
           "gameId": event.get("gameId"), "seriesSlug": event.get("seriesSlug"),
           "eventMetadata": event.get("eventMetadata"), "sport": event.get("sport"),
           "market_count": len(event.get("markets", [])), "catalog": catalog, "catalog_retrieved_at": retrieved_at}
    markets = []
    for m in event.get("markets", []):
        mr = {k: m.get(k) for k in MARKET_FIELDS}
        mr.update({"event_id": eid, "event_slug": slug, "in_sport_window": None,
                   "outcomes": unpack(m.get("outcomes")), "outcomePrices": unpack(m.get("outcomePrices")),
                   "clobTokenIds": unpack(m.get("clobTokenIds")), "catalog": catalog,
                   "catalog_retrieved_at": retrieved_at})
        markets.append(mr)
    return row, markets


def known_max_id() -> tuple[int, int]:
    """(highest census id, highest id already in the extension file)."""
    census_max = 0
    with CENSUS_EVENTS.open(encoding="utf-8") as handle:
        for line in handle:
            census_max = max(census_max, int(json.loads(line)["id"]))
    extension_max = 0
    if events_path().exists():
        with events_path().open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    extension_max = max(extension_max, int(json.loads(line)["id"]))
    return census_max, extension_max


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    census_max, extension_max = known_max_id()
    boundary = max(census_max, extension_max)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    C.log(f"[{SOURCE}] census max id {census_max}, extension max id {extension_max}; fetching ids > {boundary}")
    new_events, new_markets, pages = [], [], 0
    cursor = None
    seen_cursors = set()
    # /events rejects offsets beyond 2,000, so the keyset endpoint is paged newest-first instead.
    for page_number in range(args.max_pages):
        params = {"tag_id": TENNIS_TAG, "order": "id", "ascending": "false", "limit": PAGE_SIZE}
        if cursor:
            params["after_cursor"] = cursor
        url = f"{GAMMA}/events/keyset?" + urllib.parse.urlencode(params)
        dest = C.raw_path(SOURCE, "pages", run_id, f"{page_number:04d}.json")
        receipt = C.download(url, dest, receipts, name=f"pages/{run_id}/{page_number:04d}.json", refresh=True,
                             validator=C.not_html, extra={"run_id": run_id, "boundary": boundary})
        if receipt.get("error"):
            raise RuntimeError(f"Gamma keyset page {page_number} failed: {receipt['error']}")
        result = json.loads(dest.read_text(encoding="utf-8"))
        page = result.get("events", [])
        pages += 1
        if not page:
            break
        ids = [int(e["id"]) for e in page]
        for event in page:
            if int(event["id"]) > boundary:
                row, markets = normalise_event(event, receipt["retrieved_at"])
                new_events.append(row)
                new_markets.extend(markets)
        if page_number % 10 == 0:
            C.log(f"[{SOURCE}] page {page_number}: ids {max(ids)}..{min(ids)}, {len(new_events)} new events so far")
        cursor = result.get("next_cursor")
        if min(ids) <= boundary or not cursor:
            break
        if cursor in seen_cursors:
            raise RuntimeError("Gamma keyset pagination repeated a cursor")
        seen_cursors.add(cursor)
    else:
        C.log(f"[{SOURCE}] WARNING page limit reached before the census boundary; extension is incomplete")
    if new_events:
        with events_path().open("a", encoding="utf-8") as handle:
            for row in new_events:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        with gzip.open(markets_path(), "at", encoding="utf-8") as handle:
            for row in new_markets:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    sport_dates = sorted(e["sport_date"] for e in new_events if e.get("sport_date"))
    summary = {"source": SOURCE, "run_id": run_id, "pages": pages, "boundary_id": boundary,
               "new_events": len(new_events), "new_markets": len(new_markets),
               "sport_date_min": sport_dates[0] if sport_dates else None,
               "sport_date_max": sport_dates[-1] if sport_dates else None,
               "extension_file_events": sum(1 for _ in events_path().open(encoding="utf-8")) if events_path().exists() else 0}
    C.log(f"[{SOURCE}] {json.dumps(summary)}")
    return summary


def revisit_targets(events: pd.DataFrame, markets: pd.DataFrame, now: float,
                    settle_hours: float = SETTLE_HOURS) -> list[str]:
    """Event ids to fetch again: an event with a match-winner market the staged index still shows open
    (closed is not "True"), whose sporting date is at least settle_hours before now."""
    open_ids = markets.loc[(markets.sportsMarketType == "moneyline") & markets.closed.ne("True"), "event_id"]
    sport = pd.to_datetime(events.drop_duplicates("id", keep="last").set_index("id").sport_date, utc=True,
                           errors="coerce").reindex(open_ids.dropna().unique())
    due = sport <= pd.Timestamp(now, unit="s", tz="UTC") - pd.Timedelta(hours=settle_hours)
    return sorted(str(i) for i in sport.index[due.to_numpy()])


def revisit(args) -> dict:
    """Fetch the current rows of events captured with open match-winner markets and append them."""
    receipts = C.Receipts(SOURCE)
    events = pd.read_parquet(INDEX_DIR / "event_index.parquet", columns=["id", "sport_date"])
    markets = pd.read_parquet(INDEX_DIR / "market_index.parquet", columns=["event_id", "sportsMarketType", "closed"])
    targets = revisit_targets(events, markets, time.time(), args.settle_hours)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-revisit"
    C.log(f"[{SOURCE}] revisit: {len(targets)} events with open match-winner markets {args.settle_hours:g}+ hours "
          "past their sporting date")
    rows, market_rows = [], []
    for batch_number, first in enumerate(range(0, len(targets), REVISIT_BATCH)):
        batch = targets[first:first + REVISIT_BATCH]
        url = f"{GAMMA}/events?" + urllib.parse.urlencode([("id", i) for i in batch] + [("limit", len(batch))])
        dest = C.raw_path(SOURCE, "pages", run_id, f"{batch_number:04d}.json")
        receipt = C.download(url, dest, receipts, name=f"pages/{run_id}/{batch_number:04d}.json", refresh=True,
                             validator=C.not_html, extra={"run_id": run_id, "revisit_ids": len(batch)})
        if receipt.get("error"):
            raise RuntimeError(f"Gamma revisit batch {batch_number} failed: {receipt['error']}")
        for event in json.loads(dest.read_text(encoding="utf-8")):
            row, event_markets = normalise_event(event, receipt["retrieved_at"], catalog="revisit")
            rows.append(row)
            market_rows.extend(event_markets)
    if rows:
        with events_path().open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        with gzip.open(markets_path(), "at", encoding="utf-8") as handle:
            for row in market_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    moneylines = [m for m in market_rows if m.get("sportsMarketType") == "moneyline"]
    summary = {"source": SOURCE, "run_id": run_id, "mode": "revisit", "targets": len(targets),
               "events_returned": len(rows), "markets_written": len(market_rows),
               "moneylines_now_closed": sum(bool(m.get("closed")) for m in moneylines),
               "moneylines_still_open": sum(not m.get("closed") for m in moneylines)}
    C.log(f"[{SOURCE}] {json.dumps(summary)}")
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-pages", type=int, default=400, help="safety cap on Gamma pages per run")
    parser.add_argument("--revisit", action="store_true",
                        help="fetch again the events whose match-winner markets the staged index shows open")
    parser.add_argument("--settle-hours", type=float, default=SETTLE_HOURS,
                        help="revisit only events at least this many hours past their sporting date")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    args = parser.parse_args()
    revisit(args) if args.revisit else run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
