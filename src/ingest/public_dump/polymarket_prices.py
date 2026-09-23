"""Polymarket tennis price histories (odds branch), organised by inferred tournament type.

Market catalog: the 10 Sep 2026 Gamma census saved under data/studies/tennis_data_audit/polymarket/
(events.jsonl, markets.jsonl.gz) is re-organised into two index tables; nothing is re-fetched from
Gamma. Price history: for every selected market the FIRST outcome token's minute-level chart prices
come from the public legacy CLOB endpoint
https://clob.polymarket.com/prices-history?market=<token>&startTs=<s>&endTs=<e>&fidelity=1.
On 22 Sep 2026 that endpoint answered bounded windows of up to 14 days and returned an empty history
for 21-day or unbounded requests, so each market's life is split into <= 13-day chunks.

Tournament-type buckets reuse the name-based classifier of the tier-terrain study
(src/eda/tennis_data_audit/measure_tier_terrain.py). They are inferred labels and are stored next to
the provider's own series/league fields so they can be re-derived later.

Layout:
    data/raw/public_dump/polymarket_prices/_receipts.jsonl            one line per request
    data/raw/public_dump/polymarket_prices/bodies/<bucket>.jsonl.gz   raw response bodies (append-only)
    data/dump/odds/polymarket/event_index.parquet, market_index.parquet
    data/dump/odds/polymarket/price_history/<bucket>/<YYYY-MM>.parquet   (month = event sporting date)

Usage:
    ./python.sh -m src.ingest.public_dump.polymarket_prices --buckets main-tour
    ./python.sh -m src.ingest.public_dump.polymarket_prices --buckets all --workers 4 --rps 6
    ./python.sh -m src.ingest.public_dump.polymarket_prices --no-fetch --rebuild-parquet
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import importlib.util
import json
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "polymarket_prices"
INDEX_SOURCE = "polymarket"
CENSUS_DIR = C.PROJECT_ROOT / "data" / "studies" / "tennis_data_audit" / "polymarket"
EVENTS_FILE = CENSUS_DIR / "events.jsonl"
MARKETS_FILE = CENSUS_DIR / "markets.jsonl.gz"
CENSUS_NOTE = "Gamma census snapshot retrieved 2026-09-10 (data/studies/tennis_data_audit/polymarket/request-manifest.json)"
CLASSIFIER = C.PROJECT_ROOT / "src" / "eda" / "tennis_data_audit" / "measure_tier_terrain.py"
CLOB_URL = "https://clob.polymarket.com/prices-history"
MAX_WINDOW = 13 * 86400
MARGIN = 3600

BUCKET_SLUGS = {
    "Grand Slam singles (main draw)": "slam_main",
    "Tournament-winner futures (mostly Slams)": "outrights",
    "Grand Slam qualifying": "slam_qualifying",
    "Grand Slam juniors": "slam_juniors",
    "Tour Finals (ATP/WTA/Next Gen)": "tour_finals",
    "Masters 1000 / WTA 1000 (main draw)": "tour_1000",
    "ATP 500 / WTA 500 (main draw)": "tour_500",
    "ATP 250 / WTA 250 (main draw)": "tour_250",
    "Main-tour qualifying (1000/500/250)": "tour_qualifying",
    "Challenger / WTA 125 (inferred from bare names)": "challenger_125_inferred",
    "ITF World Tennis Tour": "itf",
    "Doubles (all tiers)": "doubles",
    "Team events & exhibitions": "team_exhibition",
    "Props, exact-score wrappers & other": "other",
}
GROUPS = {
    "main-tour": ["slam_main", "slam_qualifying", "tour_finals", "tour_1000", "tour_500", "tour_250", "tour_qualifying"],
    "rest": ["doubles", "slam_juniors", "outrights", "team_exhibition", "other"],
    "lower": ["challenger_125_inferred", "itf"],
}
GROUPS["all"] = GROUPS["main-tour"] + GROUPS["rest"] + GROUPS["lower"]

PRICE_SCHEMA = pa.schema([
    ("event_id", pa.string()), ("event_slug", pa.string()), ("market_id", pa.string()),
    ("condition_id", pa.string()), ("token_id", pa.string()), ("outcome", pa.string()),
    ("bucket", pa.string()), ("sport_date", pa.string()),
    ("t", pa.int64()), ("p", pa.float64()),
    ("window_start", pa.int64()), ("window_end", pa.int64()),
    ("_source", pa.string()), ("_retrieved_at", pa.string()), ("_sha256", pa.string()),
])


# --------------------------------------------------------------------------------------
# census loading and classification
# --------------------------------------------------------------------------------------
def load_classifier():
    spec = importlib.util.spec_from_file_location("measure_tier_terrain", CLASSIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classify


def is_cfb(event: dict) -> bool:
    return any(s.get("slug") == "cfb-2025" for s in event.get("series") or []) or \
        ((event.get("sport") or {}).get("sport") == "cfb")


def extension_paths() -> tuple[Path, Path]:
    return (C.raw_path("polymarket_catalog", "events_extension.jsonl"),
            C.raw_path("polymarket_catalog", "markets_extension.jsonl.gz"))


def load_events(classify, now: int | None = None) -> dict[str, dict]:
    """Census events plus any catalog-extension events (polymarket_catalog.py). Extension events have
    no stored window flag: they count as in-window once their sporting date has passed."""
    now = now or int(time.time())
    events = {}

    def add(event, catalog):
        event.setdefault("catalog", catalog)
        event["_cfb"] = is_cfb(event)
        if event.get("in_sport_window") is None:
            sport = parse_ts(event.get("sport_date"))
            event["in_sport_window"] = bool(sport and sport <= now)
        bucket = tour = detail = confidence = None
        if event.get("in_sport_window") and not event["_cfb"] and event.get("sport_date"):
            bucket, tour, detail, confidence = classify(event)
        event.update(_bucket=bucket, _bucket_slug=BUCKET_SLUGS.get(bucket), _tour=tour,
                     _detail=detail, _confidence=confidence)
        events[event["id"]] = event

    with EVENTS_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            add(json.loads(line), "census")
    ext_events, _ = extension_paths()
    if ext_events.exists():
        with ext_events.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    add(json.loads(line), "extension")
    return events


def iter_markets(events: dict | None = None):
    """Census markets, then extension markets. Extension market window flags follow their event."""
    with gzip.open(MARKETS_FILE, "rt", encoding="utf-8") as handle:
        for line in handle:
            market = json.loads(line)
            market.setdefault("catalog", "census")
            yield market
    _, ext_markets = extension_paths()
    if ext_markets.exists():
        with gzip.open(ext_markets, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    market = json.loads(line)
                    if market.get("in_sport_window") is None and events is not None:
                        market["in_sport_window"] = bool((events.get(market["event_id"]) or {}).get("in_sport_window"))
                    yield market


def parse_ts(value) -> int | None:
    if not value:
        return None
    text = str(value).strip().replace(" ", "T")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if re.search(r"[+-]\d{2}$", text):
        text += ":00"
    try:
        return int(dt.datetime.fromisoformat(text).timestamp())
    except ValueError:
        return None


def market_window(market: dict, event: dict, now: int) -> tuple[int, int] | None:
    starts = [parse_ts(market.get(k)) for k in ("startDate", "acceptingOrdersTimestamp", "createdAt")]
    starts = [s for s in starts if s]
    ends = [parse_ts(market.get(k)) for k in ("closedTime", "endDate")]
    ends = [e for e in ends if e]
    sport = parse_ts(event.get("sport_date"))
    start = min(starts) if starts else (sport - 3 * 86400 if sport else None)
    end = ends[0] if ends else (sport + 7 * 86400 if sport else None)
    if start is None or end is None:
        return None
    start -= MARGIN
    end = min(end + MARGIN, now)
    return (start, end) if end > start else None


def chunk_window(start: int, end: int, max_span: int = MAX_WINDOW) -> list[tuple[int, int]]:
    chunks, cursor = [], start
    while cursor < end:
        stop = min(cursor + max_span, end)
        chunks.append((cursor, stop))
        cursor = stop
    return chunks


def resolve_buckets(spec: str) -> list[str]:
    out = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if item in GROUPS:
            out.extend(GROUPS[item])
        elif item in BUCKET_SLUGS.values():
            out.append(item)
        else:
            raise ValueError(f"unknown bucket or group: {item}; choose from {sorted(GROUPS)} or {sorted(BUCKET_SLUGS.values())}")
    seen, ordered = set(), []
    for slug in out:
        if slug not in seen:
            seen.add(slug)
            ordered.append(slug)
    return ordered


NAME_PREFIX = re.compile(r'^\{"name": "([^"]+)"')
GZIP_MAGIC = b"\x1f\x8b\x08"


def iter_body_lines(path: Path, report: dict | None = None):
    """Yield complete text lines from a possibly damaged multi-member gzip file.

    Bodies files get one gzip member appended per run. A run killed mid-write leaves a truncated
    member that gzip.open cannot read past, even though the members appended afterwards are intact.
    This reader decompresses member by member, streams complete lines, drops the partial tail of a
    damaged member and resynchronises on the next gzip header. ``report['damaged_members']``
    receives the count of damaged members; their lost requests are re-fetched by the resume logic."""
    import codecs
    import zlib

    data = path.read_bytes()
    pos, damaged, previous_ok = 0, 0, True
    while 0 <= pos < len(data):
        pos = data.find(GZIP_MAGIC, pos)
        if pos < 0:
            break
        decompressor = zlib.decompressobj(31)
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        cursor, buffer, failed = pos, "", False
        try:
            while cursor < len(data) and not decompressor.eof:
                chunk = data[cursor:cursor + (1 << 16)]
                cursor += len(chunk)
                buffer += decoder.decode(decompressor.decompress(chunk))
                *lines, buffer = buffer.split("\n")
                for line in lines:
                    if line:
                        yield line
        except zlib.error:
            failed = True
        if decompressor.eof and not failed:
            pos = cursor - len(decompressor.unused_data)
            previous_ok = True
        else:
            # damaged or truncated member (an error, or the data ran out before the end-of-stream
            # marker, possibly after swallowing following members as garbage): scan for the next
            # header after this one. A run of false-positive headers inside the damaged bytes counts
            # as one damaged region.
            if previous_ok:
                damaged += 1
            previous_ok = False
            pos += 1
    if report is not None:
        report["damaged_members"] = report.get("damaged_members", 0) + damaged


def names_with_bodies(bodies_dir: Path | None = None) -> set[str]:
    """Request names whose raw body is actually stored. A killed run can leave a receipt without a
    body (or a damaged gzip member), so resume logic trusts this set, not receipts alone."""
    bodies_dir = bodies_dir or C.raw_path(SOURCE, "bodies")
    names: set[str] = set()
    for path in bodies_dir.glob("*.jsonl.gz") if bodies_dir.exists() else []:
        report: dict = {}
        for line in iter_body_lines(path, report):
            if not NAME_PREFIX.match(line) or not line.rstrip().endswith("}"):
                continue
            try:  # a damaged member can emit garbage that still starts like a record; only valid JSON counts
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and record.get("name") and "body" in record:
                names.add(record["name"])
        if report.get("damaged_members"):
            C.log(f"[{SOURCE}] WARNING {path.name}: {report['damaged_members']} damaged gzip member(s); "
                  f"requests without a stored body will be re-fetched")
    return names


def select_jobs(events, markets, buckets, market_types, limit, receipts, refresh, now, stored: set[str] | None = None):
    jobs, markets_per_bucket, skipped = [], Counter(), Counter()
    selected_markets = 0
    for market in markets:
        if not market.get("in_sport_window"):
            continue
        if (market.get("sportsMarketType") or "None") not in market_types:
            continue
        event = events.get(market["event_id"])
        if not event or event["_cfb"] or not event["_bucket_slug"]:
            skipped["event without bucket"] += 1
            continue
        if event["_bucket_slug"] not in buckets:
            continue
        tokens = market.get("clobTokenIds") or []
        if not tokens:
            skipped["market without token"] += 1
            continue
        window = market_window(market, event, now)
        if not window:
            skipped["market without usable dates"] += 1
            continue
        chunks = chunk_window(*window)
        selected_markets += 1
        markets_per_bucket[event["_bucket_slug"]] += 1
        for index, (start, end) in enumerate(chunks):
            name = f"{market['id']}/{index}"
            previous = receipts.get(name)
            if previous and not previous.get("error") and not refresh and (stored is None or name in stored):
                skipped["already fetched"] += 1
                continue
            jobs.append({"name": name, "market_id": market["id"], "condition_id": market.get("conditionId"),
                         "token_id": tokens[0], "outcome": (market.get("outcomes") or [None])[0],
                         "event_id": event["id"], "event_slug": event["slug"], "bucket": event["_bucket_slug"],
                         "sport_date": event.get("sport_date"), "start": start, "end": end, "chunks": len(chunks)})
        if limit and selected_markets >= limit:
            break
    order = {slug: i for i, slug in enumerate(buckets)}
    jobs.sort(key=lambda j: (order[j["bucket"]], j["sport_date"] or "", j["market_id"], j["name"]))
    return jobs, markets_per_bucket, skipped


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, rps: float):
        self.min_interval = 1.0 / max(rps, 0.1)
        self.lock = threading.Lock()
        self.next_time = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            delay = self.next_time - now
            self.next_time = max(now, self.next_time) + self.min_interval
        if delay > 0:
            time.sleep(delay)


def fetch_job(job: dict, limiter: RateLimiter):
    url = f"{CLOB_URL}?market={job['token_id']}&startTs={job['start']}&endTs={job['end']}&fidelity=1"
    sess = C.session()
    error = None
    for attempt in range(5):
        limiter.wait()
        try:
            response = sess.get(url, timeout=60)
        except requests.RequestException as err:
            error = f"{type(err).__name__}: {err}"
            time.sleep(2 ** attempt)
            continue
        if response.status_code == 200:
            return job, url, 200, response.text, None
        error = f"HTTP {response.status_code}"
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(2 * 2 ** attempt)
            continue
        return job, url, response.status_code, None, error
    return job, url, None, None, error


def run_fetch(jobs: list[dict], workers: int, rps: float, receipts: C.Receipts) -> dict:
    limiter = RateLimiter(rps)
    bodies_dir = C.raw_path(SOURCE, "bodies")
    bodies_dir.mkdir(parents=True, exist_ok=True)
    handles: dict = {}
    stats = Counter()
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for job, url, status, text, error in pool.map(lambda j: fetch_job(j, limiter), jobs):
                receipt = {"name": job["name"], "url": url, "market_id": job["market_id"], "token_id": job["token_id"],
                           "event_id": job["event_id"], "bucket": job["bucket"], "start": job["start"], "end": job["end"],
                           "retrieved_at": C.utc_now_iso(), "status": status}
                if error:
                    receipt["error"] = error
                    stats["errors"] += 1
                else:
                    try:
                        points = len(json.loads(text).get("history", []))
                    except (ValueError, AttributeError):
                        points = None
                        receipt["error"] = "body is not a JSON history"
                        stats["errors"] += 1
                    receipt.update(bytes=len(text), sha256=C.sha256_bytes(text.encode("utf-8")), points=points)
                    if points is not None:
                        handle = handles.get(job["bucket"])
                        if handle is None:
                            handle = gzip.open(bodies_dir / f"{job['bucket']}.jsonl.gz", "at", encoding="utf-8")
                            handles[job["bucket"]] = handle
                        record = {**receipt, "condition_id": job["condition_id"], "outcome": job["outcome"],
                                  "event_slug": job["event_slug"], "sport_date": job["sport_date"], "body": text}
                        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                        stats["ok"] += 1
                        stats["points"] += points
                        if points == 0:
                            stats["empty"] += 1
                receipts.record(receipt)
                stats["done"] += 1
                if stats["done"] % 250 == 0 or stats["done"] == len(jobs):
                    elapsed = time.monotonic() - started
                    rate = stats["done"] / elapsed if elapsed else 0
                    remaining = (len(jobs) - stats["done"]) / rate if rate else float("inf")
                    C.log(f"[{SOURCE}] {stats['done']}/{len(jobs)} requests, {stats['ok']} ok, {stats['empty']} empty, "
                          f"{stats['errors']} errors, {stats['points']:,} points, {rate:.1f} req/s, ~{remaining / 60:.0f} min left")
    finally:
        for handle in handles.values():
            handle.close()
    stats["seconds"] = round(time.monotonic() - started, 1)
    return dict(stats)


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def build_index(events: dict, out_dir: Path) -> list[dict]:
    """Slim event and market index tables from the census, with the inferred bucket attached."""
    event_header = ["id", "slug", "title", "url", "sport_date", "date_basis", "in_sport_window",
                    "metadata_trading_overlap", "createdAt", "startDate", "closedTime_derived", "closed", "volume",
                    "market_count", "series_slugs", "league", "sport", "tags", "gameId", "is_cfb", "bucket",
                    "bucket_slug", "bucket_tour", "bucket_detail", "bucket_confidence", "catalog", "catalog_retrieved_at"]

    def event_row(e):
        league = (e.get("eventMetadata") or {}).get("league")
        return [e.get("id"), e.get("slug"), e.get("title"), e.get("url"), e.get("sport_date"), e.get("date_basis"),
                e.get("in_sport_window"), e.get("metadata_trading_overlap"), e.get("createdAt"), e.get("startDate"),
                e.get("closedTime_derived"), e.get("closed"), e.get("volume"), e.get("market_count"),
                ",".join(s.get("slug", "") for s in e.get("series") or []), league,
                json.dumps(e.get("sport"), ensure_ascii=False) if e.get("sport") else None,
                json.dumps(e.get("tags"), ensure_ascii=False) if e.get("tags") else None, e.get("gameId"),
                e["_cfb"], e["_bucket"], e["_bucket_slug"], e["_tour"], e["_detail"], e["_confidence"],
                e.get("catalog"), e.get("catalog_retrieved_at") or (CENSUS_NOTE if e.get("catalog") == "census" else None)]

    ext_events, ext_markets = extension_paths()
    extension_note = f" plus extension {C.rel(ext_events)}" if ext_events.exists() else ""
    prov = C.Provenance(INDEX_SOURCE, C.rel(EVENTS_FILE) + extension_note, C.sha256_file(EVENTS_FILE), CENSUS_NOTE)
    events_out = out_dir / "event_index.parquet"
    stats = C.stage_rows(event_header, ((i + 1, event_row(e)) for i, e in enumerate(events.values())), events_out, prov)
    stats["source_path"] = C.rel(EVENTS_FILE) + extension_note
    metas = [C.staged_meta("odds", INDEX_SOURCE, events_out, {"url": "https://gamma-api.polymarket.com/events (census + extension)",
             "sha256": prov.sha256, "retrieved_at": CENSUS_NOTE}, stats,
             note="census re-organised (+ post-census extension rows, catalog column); bucket columns are inferred")]

    market_header = ["id", "question", "slug", "conditionId", "questionID", "sportsMarketType", "line", "gameStartTime",
                     "eventStartTime", "startDate", "endDate", "createdAt", "closedTime", "closed", "volume", "volumeNum",
                     "groupItemTitle", "gameId", "teamAID", "teamBID", "event_id", "event_slug", "in_sport_window",
                     "outcomes", "outcomePrices", "clobTokenIds", "token0", "bucket_slug", "catalog", "catalog_retrieved_at"]

    def market_rows():
        for i, m in enumerate(iter_markets(events)):
            event = events.get(m.get("event_id")) or {}
            tokens = m.get("clobTokenIds") or []
            yield i + 1, [m.get("id"), m.get("question"), m.get("slug"), m.get("conditionId"), m.get("questionID"),
                          m.get("sportsMarketType"), m.get("line"), m.get("gameStartTime"), m.get("eventStartTime"),
                          m.get("startDate"), m.get("endDate"), m.get("createdAt"), m.get("closedTime"), m.get("closed"),
                          m.get("volume"), m.get("volumeNum"), m.get("groupItemTitle"), m.get("gameId"), m.get("teamAID"),
                          m.get("teamBID"), m.get("event_id"), m.get("event_slug"), m.get("in_sport_window"),
                          json.dumps(m.get("outcomes"), ensure_ascii=False), json.dumps(m.get("outcomePrices")),
                          json.dumps(tokens), tokens[0] if tokens else None, event.get("_bucket_slug"),
                          m.get("catalog"), m.get("catalog_retrieved_at") or (CENSUS_NOTE if m.get("catalog") == "census" else None)]

    extension_note = f" plus extension {C.rel(ext_markets)}" if ext_markets.exists() else ""
    prov = C.Provenance(INDEX_SOURCE, C.rel(MARKETS_FILE) + extension_note, C.sha256_file(MARKETS_FILE), CENSUS_NOTE)
    markets_out = out_dir / "market_index.parquet"
    stats = C.stage_rows(market_header, market_rows(), markets_out, prov)
    stats["source_path"] = C.rel(MARKETS_FILE) + extension_note
    metas.append(C.staged_meta("odds", INDEX_SOURCE, markets_out, {"url": "https://gamma-api.polymarket.com/markets (census + extension)",
                 "sha256": prov.sha256, "retrieved_at": CENSUS_NOTE}, stats,
                 note="census re-organised (+ post-census extension rows, catalog column); token0 is the first outcome token"))
    return metas


def rebuild_parquet(receipts: C.Receipts, buckets: list[str] | None, out_dir: Path) -> list[dict]:
    """Rebuild price_history/<bucket>/<YYYY-MM>.parquet from the raw bodies. The latest receipt per
    request name decides which stored body is current; multi-chunk markets are merged and deduplicated."""
    latest = {name: r for name, r in receipts.all().items() if not r.get("error")}
    chunk_count: Counter = Counter()
    for name in latest:
        chunk_count[name.split("/")[0]] += 1
    bodies_dir = C.raw_path(SOURCE, "bodies")
    metas = []
    for path in sorted(bodies_dir.glob("*.jsonl.gz")):
        bucket = path.name[: -len(".jsonl.gz")]
        if buckets and bucket not in buckets:
            continue
        bucket_dir = out_dir / "price_history" / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        for stale in bucket_dir.glob("*.parquet*"):
            stale.unlink()
        writers: dict[str, pq.ParquetWriter] = {}
        buffers: dict[str, list] = defaultdict(list)
        summary: dict[str, Counter] = defaultdict(Counter)
        pending: dict[str, list] = defaultdict(list)  # multi-chunk markets

        def emit(month: str, rows: list):
            buffers[month].extend(rows)
            if len(buffers[month]) >= 250_000:
                flush(month)

        def flush(month: str):
            rows = buffers[month]
            if not rows:
                return
            columns = list(zip(*rows))
            table = pa.Table.from_arrays([pa.array(col, field.type) for col, field in zip(columns, PRICE_SCHEMA)],
                                         schema=PRICE_SCHEMA)
            if month not in writers:
                writers[month] = pq.ParquetWriter(bucket_dir / f"{month}.parquet", PRICE_SCHEMA, compression="zstd")
            writers[month].write_table(table)
            buffers[month] = []

        def rows_from(record: dict, history: list):
            month = (record.get("sport_date") or "unknown")[:7]
            rows = [(record["event_id"], record.get("event_slug"), record["market_id"], record.get("condition_id"),
                     record["token_id"], record.get("outcome"), bucket, record.get("sport_date"), int(point["t"]),
                     float(point["p"]), record["start"], record["end"], SOURCE, record["retrieved_at"], record.get("sha256"))
                    for point in history]
            return month, rows

        report: dict = {}
        for line in iter_body_lines(path, report):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # partial line from an interrupted run
            current = latest.get(record["name"])
            if not current or current.get("retrieved_at") != record.get("retrieved_at"):
                continue  # superseded or failed request
            history = json.loads(record["body"]).get("history", [])
            market_id = record["market_id"]
            summary["markets"][market_id] += 1
            if chunk_count[market_id] > 1:
                pending[market_id].append((record, history))
                continue
            month, rows = rows_from(record, history)
            summary["points"][month] += len(rows)
            emit(month, rows)
        if report.get("damaged_members"):
            C.log(f"[{SOURCE}] WARNING {path.name}: {report['damaged_members']} damaged gzip member(s) skipped")
        for market_id, parts in pending.items():
            merged, seen = [], set()
            for record, history in sorted(parts, key=lambda item: item[0]["start"]):
                for point in history:
                    if point["t"] not in seen:
                        seen.add(point["t"])
                        merged.append(point)
            month, rows = rows_from(parts[0][0], merged)
            summary["points"][month] += len(rows)
            emit(month, rows)
        for month in list(buffers):
            flush(month)
        for month, writer in writers.items():
            writer.close()
            dest = bucket_dir / f"{month}.parquet"
            meta = {"branch": "odds", "source": INDEX_SOURCE, "dest": C.rel(dest), "bucket": bucket, "month": month,
                    "rows": summary["points"][month], "bytes": dest.stat().st_size,
                    "columns": PRICE_SCHEMA.names, "url": CLOB_URL, "retrieved_at": "see _retrieved_at column",
                    "note": "first outcome token only; minute chart prices; t is Unix seconds UTC"}
            C.write_meta(dest, meta)
            metas.append(meta)
        C.log(f"[{SOURCE}] rebuilt {bucket}: {len(summary['markets'])} markets, "
              f"{sum(summary['points'].values()):,} points, {len(writers)} month files")
    return metas


# --------------------------------------------------------------------------------------
def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    classify = load_classifier()
    events = load_events(classify)
    C.log(f"[{SOURCE}] catalog: {sum(e.get('catalog') == 'census' for e in events.values())} census events, "
          f"{sum(e.get('catalog') == 'extension' for e in events.values())} extension events")
    out_dir = C.dump_path("odds", INDEX_SOURCE)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {"source": SOURCE}
    if not args.no_index:
        metas = build_index(events, out_dir)
        summary["index"] = [{"dest": m["dest"], "rows": m["rows"]} for m in metas]
        C.log(f"[{SOURCE}] index: " + ", ".join(f"{m['dest']} {m['rows']:,} rows" for m in metas))
    buckets = resolve_buckets(args.buckets)
    if not args.no_fetch:
        now = int(time.time())
        market_types = {t.strip() for t in args.market_types.split(",") if t.strip()}
        stored = names_with_bodies()
        jobs, per_bucket, skipped = select_jobs(events, iter_markets(events), buckets, market_types, args.limit,
                                                receipts, args.refresh, now, stored)
        C.log(f"[{SOURCE}] buckets {buckets}: {sum(per_bucket.values())} markets selected "
              f"({dict(per_bucket)}); {len(jobs)} requests to make; skipped {dict(skipped)}")
        summary.update(markets_selected=sum(per_bucket.values()), markets_per_bucket=dict(per_bucket),
                       requests_planned=len(jobs), skipped=dict(skipped))
        if jobs:
            summary["fetch"] = run_fetch(jobs, args.workers, args.rps, receipts)
    if not args.no_rebuild:
        metas = rebuild_parquet(receipts, buckets if args.rebuild_selected_only else None, out_dir)
        summary["price_files"] = len(metas)
        summary["price_points"] = sum(m["rows"] for m in metas)
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["request_errors"] = len(errors)
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--buckets", default="main-tour",
                        help="comma list of groups (main-tour, rest, lower, all) and/or bucket slugs")
    parser.add_argument("--market-types", default="moneyline", help="comma list of Gamma sportsMarketType values")
    parser.add_argument("--limit", type=int, default=0, help="stop after this many selected markets (0 = no limit)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rps", type=float, default=6.0, help="global request rate cap")
    parser.add_argument("--refresh", action="store_true", help="re-fetch requests that already succeeded")
    parser.add_argument("--no-index", action="store_true", help="skip rebuilding event/market index tables")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--no-rebuild", action="store_true", help="skip rebuilding price Parquet from bodies")
    parser.add_argument("--rebuild-selected-only", action="store_true", help="rebuild only the selected buckets")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.STUDY_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = C.STUDY_ROOT / "polymarket_runs.jsonl"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"finished_at": C.utc_now_iso(), **summary}, ensure_ascii=False) + "\n")
    C.log(f"[{SOURCE}] done: {json.dumps({k: v for k, v in summary.items() if k != 'index'}, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
