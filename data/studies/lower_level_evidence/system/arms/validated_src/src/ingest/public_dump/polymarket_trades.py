"""Polymarket tennis moneyline trade fills, both counterparties, from the public Data API.

Market list: every moneyline in the staged index (data/dump/odds/polymarket/market_index.parquet, built by
polymarket_prices.py from the 10 Sep 2026 census plus the catalog extension) whose event is in the sporting
window, has an inferred bucket, and started on or before --cutoff. Nothing is re-fetched from Gamma.

Fills: https://data-api.polymarket.com/trades?market=<conditionId>&takerOnly=false&limit=10000, newest first.
takerOnly=false returns one record per party: the taker's aggregated fill and one record per matched maker
order, each on the asset and side of that party's own order (a maker's complementary BUY of the other outcome
appears as such, on the same transaction hash). The API caps offset at 10,000, so a full page is continued
with end=<oldest timestamp on the page>. Checked on 25 Sep 2026: `end` and `start` are inclusive, so rows
of the boundary second come back and merge_pages removes them as a multiset. Documented limit: 200 requests
per 10 s on /trades, enforced by throttling rather than rejection.

Layout:
    data/raw/public_dump/polymarket_trades/_receipts.jsonl            one line per page, one per finished market
    data/raw/public_dump/polymarket_trades/bodies/<bucket>.jsonl.gz   raw response bodies (append-only)
    data/dump/odds/polymarket/trades/<bucket>.parquet                 merged fills, JSON number types kept
    data/dump/odds/polymarket/trades/wallets.parquet                  wallet display fields (latest seen)

A market whose completed fetch ran before it closed (the index shows it open, or closing after the fetch
finished) is fetched again on the next run; the rebuild uses the latest complete fetch of each market.

The fills table keeps the API's own types (numbers stay numbers) and drops the market-level display fields
(title, slug, icon, eventSlug), which repeat the index and stay in the raw bodies. `seq` is the record's
position in the merged newest-first list of its market. The API lists the taker's record first within each
transaction: on 25 Sep 2026 that matched takerOnly=true in 3,617 of 3,617 transactions across 8 markets
from four tiers, so `seq` lets an analysis recover maker/taker roles.

Usage:
    ./python.sh -m src.ingest.public_dump.polymarket_trades --buckets all --workers 6 --rps 12
    ./python.sh -m src.ingest.public_dump.polymarket_trades --no-fetch          (rebuild Parquet from bodies)
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.parse
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C
from src.ingest.public_dump.polymarket_prices import RateLimiter, iter_body_lines, parse_ts, resolve_buckets

SOURCE = "polymarket_trades"
DATA_API = "https://data-api.polymarket.com/trades"
INDEX_DIR = C.PROJECT_ROOT / "data" / "dump" / "odds" / "polymarket"
OUT_DIR = INDEX_DIR / "trades"
PAGE_SIZE = 10_000
MAX_PAGES = 400
DEFAULT_CUTOFF = "2026-09-21T23:59:59+00:00"

TRADE_SCHEMA = pa.schema([
    ("condition_id", pa.string()), ("asset", pa.string()), ("outcome_index", pa.int8()),
    ("outcome", pa.string()), ("side", pa.string()), ("size", pa.float64()), ("price", pa.float64()),
    ("timestamp", pa.int64()), ("proxy_wallet", pa.string()), ("tx_hash", pa.string()),
    ("seq", pa.int32()), ("bucket", pa.string()), ("fetch_id", pa.string()), ("_retrieved_at", pa.string()),
])
WALLET_FIELDS = ("name", "pseudonym", "bio", "profileImage")


def record_key(row: dict) -> tuple:
    """Identity of one fill record for boundary de-duplication (identical twins are kept by counting)."""
    return (row.get("proxyWallet"), row.get("side"), row.get("asset"), row.get("size"), row.get("price"),
            row.get("timestamp"), row.get("transactionHash"), row.get("outcomeIndex"))


def merge_pages(pages: list[tuple[int | None, list[dict]]]) -> list[dict]:
    """Merge newest-first pages fetched with an inclusive `end` cursor.

    ``pages`` is [(end, rows), ...] in fetch order; page k > 0 was requested with end = the oldest timestamp
    on page k - 1. Its rows at that second repeat rows already taken, unless page k - 1 was cut inside the
    second, so they are removed as a multiset: each earlier copy cancels one repeat, extra copies are kept."""
    out: list[dict] = []
    for index, (end, rows) in enumerate(pages):
        if index == 0 or end is None:
            out.extend(rows)
            continue
        seen = Counter(record_key(r) for r in out if r.get("timestamp") == end)
        for row in rows:
            if row.get("timestamp") == end:
                key = record_key(row)
                if seen[key] > 0:
                    seen[key] -= 1
                    continue
            out.append(row)
    return out


# --------------------------------------------------------------------------------------
# market selection
# --------------------------------------------------------------------------------------
def load_markets(cutoff: str) -> pd.DataFrame:
    events = pd.read_parquet(INDEX_DIR / "event_index.parquet", columns=["id", "sport_date", "bucket_slug"])
    markets = pd.read_parquet(INDEX_DIR / "market_index.parquet",
                              columns=["id", "conditionId", "sportsMarketType", "event_id", "in_sport_window", "volumeNum",
                                       "closed", "closedTime"])
    markets = markets[(markets.sportsMarketType == "moneyline") & (markets.in_sport_window == "True")]
    markets = markets.merge(events.rename(columns={"id": "event_id", "bucket_slug": "bucket"}), on="event_id", how="left")
    stamp = pd.to_datetime(markets.sport_date, utc=True, errors="coerce")
    markets = markets[markets.bucket.notna() & markets.conditionId.notna() & (stamp <= pd.Timestamp(cutoff))]
    return markets.drop_duplicates("conditionId").reset_index(drop=True)


def completed_markets(receipts: C.Receipts) -> dict[str, dict]:
    return {name: r for name, r in receipts.all().items() if "/" not in name and r.get("complete")}


def fetched_before_close(markets: pd.DataFrame, done: dict[str, dict]) -> pd.Series:
    """Completed markets whose fetch ran while they could still trade, so later fills are missing: the index
    shows them open, or closing after the fetch finished. Needs columns conditionId, closed, closedTime."""
    fetched = markets.conditionId.map(lambda c: parse_ts((done.get(c) or {}).get("retrieved_at")))
    closed_at = markets.closedTime.map(parse_ts)
    fetched, closed_at = pd.to_numeric(fetched), pd.to_numeric(closed_at)
    return fetched.notna() & (markets.closed.ne("True") | (closed_at > fetched))


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def get_page(url: str, limiter: RateLimiter) -> tuple[int | None, str | None, str | None]:
    sess = C.session()
    error = None
    for attempt in range(6):
        limiter.wait()
        try:
            response = sess.get(url, timeout=120)
        except requests.RequestException as err:
            error = f"{type(err).__name__}: {err}"
            time.sleep(2 ** attempt)
            continue
        if response.status_code == 200:
            return 200, response.text, None
        error = f"HTTP {response.status_code}: {response.text[:200]}"
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(2 * 2 ** attempt)
            continue
        return response.status_code, None, error
    return None, None, error


def fetch_market(job: dict, limiter: RateLimiter, page_size: int = PAGE_SIZE):
    """All pages of one market. Returns (job, pages, error); pages carry the raw body text."""
    pages, end = [], None
    for number in range(MAX_PAGES):
        params = {"market": job["condition_id"], "takerOnly": "false", "limit": page_size, "offset": 0}
        if end is not None:
            params["end"] = end
        url = f"{DATA_API}?{urllib.parse.urlencode(params)}"
        status, text, error = get_page(url, limiter)
        if error:
            return job, pages, error
        try:
            rows = json.loads(text)
        except ValueError:
            return job, pages, "body is not JSON"
        if not isinstance(rows, list):
            return job, pages, f"body is not a JSON list: {text[:200]}"
        pages.append({"page": number, "end": end, "url": url, "status": status, "retrieved_at": C.utc_now_iso(),
                      "rows": len(rows), "text": text})
        if len(rows) < page_size:
            return job, pages, None
        oldest = min(int(r["timestamp"]) for r in rows)
        if end is not None and oldest >= end:
            return job, pages, f"window did not advance: {page_size} rows within one second at {end}"
        end = oldest
    return job, pages, f"more than {MAX_PAGES} pages"


def run_fetch(jobs: list[dict], workers: int, rps: float, receipts: C.Receipts) -> dict:
    limiter = RateLimiter(rps)
    bodies_dir = C.raw_path(SOURCE, "bodies")
    bodies_dir.mkdir(parents=True, exist_ok=True)
    handles: dict = {}
    stats = Counter()
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for job, pages, error in pool.map(lambda j: fetch_market(j, limiter), jobs):
                fetch_id = uuid.uuid4().hex[:12]
                handle = handles.get(job["bucket"])
                if handle is None and pages:
                    handle = gzip.open(bodies_dir / f"{job['bucket']}.jsonl.gz", "at", encoding="utf-8")
                    handles[job["bucket"]] = handle
                for page in pages:
                    name = f"{job['condition_id']}/{page['page']}"
                    receipt = {"name": name, "url": page["url"], "status": page["status"], "retrieved_at": page["retrieved_at"],
                               "rows": page["rows"], "bytes": len(page["text"]), "end": page["end"], "fetch_id": fetch_id,
                               "sha256": C.sha256_bytes(page["text"].encode("utf-8")), "bucket": job["bucket"]}
                    record = {**receipt, "condition_id": job["condition_id"], "page": page["page"], "body": page["text"]}
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    receipts.record(receipt)
                    stats["pages"] += 1
                    stats["rows_raw"] += page["rows"]
                market_receipt = {"name": job["condition_id"], "bucket": job["bucket"], "market_id": job["market_id"],
                                  "fetch_id": fetch_id, "pages": len(pages), "rows_raw": sum(p["rows"] for p in pages),
                                  "retrieved_at": C.utc_now_iso(), "complete": error is None}
                if error:
                    market_receipt["error"] = error
                    stats["errors"] += 1
                if handle is not None:
                    handle.flush()
                receipts.record(market_receipt)
                stats["markets"] += 1
                if stats["markets"] % 500 == 0 or stats["markets"] == len(jobs):
                    elapsed = time.monotonic() - started
                    rate = stats["markets"] / elapsed if elapsed else 0
                    remaining = (len(jobs) - stats["markets"]) / rate if rate else float("inf")
                    C.log(f"[{SOURCE}] {stats['markets']}/{len(jobs)} markets, {stats['pages']} pages, "
                          f"{stats['rows_raw']:,} rows, {stats['errors']} errors, {rate:.1f} markets/s, "
                          f"~{remaining / 60:.0f} min left")
    finally:
        for handle in handles.values():
            handle.close()
    stats["seconds"] = round(time.monotonic() - started, 1)
    return dict(stats)


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def rebuild_parquet(receipts: C.Receipts, buckets: list[str] | None = None) -> list[dict]:
    """Rebuild trades/<bucket>.parquet from raw bodies. For each market, only the pages of the fetch named by
    its latest complete market receipt are used; pages are merged with merge_pages."""
    complete = completed_markets(receipts)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wallets: dict[str, tuple] = {}
    metas = []
    for path in sorted(C.raw_path(SOURCE, "bodies").glob("*.jsonl.gz")):
        bucket = path.name[: -len(".jsonl.gz")]
        if buckets and bucket not in buckets:
            continue
        dest = OUT_DIR / f"{bucket}.parquet"
        writer = pq.ParquetWriter(dest, TRADE_SCHEMA, compression="zstd")
        buffer: list[tuple] = []
        pending: dict[tuple, dict] = defaultdict(dict)  # (cid, fetch_id) -> {page: (end, rows, retrieved_at)}
        counts = Counter()

        def flush():
            if buffer:
                columns = list(zip(*buffer))
                writer.write_table(pa.Table.from_arrays(
                    [pa.array(col, field.type) for col, field in zip(columns, TRADE_SCHEMA)], schema=TRADE_SCHEMA))
                buffer.clear()

        def emit(cid: str, fetch_id: str, parts: dict):
            ordered = [parts[k] for k in sorted(parts)]
            rows = merge_pages([(end, rows) for end, rows, _ in ordered])
            retrieved = ordered[-1][2]
            counts["markets"] += 1
            counts["rows"] += len(rows)
            counts["boundary_duplicates"] += sum(len(r) for _, r, _ in ordered) - len(rows)
            for seq, r in enumerate(rows):
                buffer.append((cid, r.get("asset"), r.get("outcomeIndex"), r.get("outcome"), r.get("side"),
                               float(r["size"]), float(r["price"]), int(r["timestamp"]), r.get("proxyWallet"),
                               r.get("transactionHash"), seq, bucket, fetch_id, retrieved))
                wallet = r.get("proxyWallet")
                if wallet:
                    previous = wallets.get(wallet)
                    if previous is None or int(r["timestamp"]) >= previous[0]:
                        wallets[wallet] = (int(r["timestamp"]),) + tuple(r.get(f) for f in WALLET_FIELDS)
            if len(buffer) >= 500_000:
                flush()

        report: dict = {}
        for line in iter_body_lines(path, report):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid, fetch_id = record["condition_id"], record["fetch_id"]
            done = complete.get(cid)
            if not done or done.get("fetch_id") != fetch_id:
                counts["superseded_or_incomplete_pages"] += 1
                continue
            pending[(cid, fetch_id)][record["page"]] = (record["end"], json.loads(record["body"]), record["retrieved_at"])
            if len(pending[(cid, fetch_id)]) == done["pages"]:
                emit(cid, fetch_id, pending.pop((cid, fetch_id)))
        flush()
        writer.close()
        if pending:
            counts["markets_missing_pages"] = len(pending)
        if report.get("damaged_members"):
            C.log(f"[{SOURCE}] WARNING {path.name}: {report['damaged_members']} damaged gzip member(s) skipped")
        meta = {"branch": "odds", "source": "polymarket", "dest": C.rel(dest), "bucket": bucket, **counts,
                "bytes": dest.stat().st_size, "columns": TRADE_SCHEMA.names, "url": DATA_API,
                "retrieved_at": "see _retrieved_at column",
                "note": "takerOnly=false fills (taker and each matched maker order); size in shares, price in USDC per "
                        "share of `asset`; timestamp is Unix seconds UTC; boundary-second repeats removed by merge_pages"}
        C.write_meta(dest, meta)
        metas.append(meta)
        C.log(f"[{SOURCE}] rebuilt {bucket}: {counts['markets']:,} markets, {counts['rows']:,} fills")
    if wallets:
        table = pa.table({"proxy_wallet": list(wallets),
                          "last_seen_ts": [v[0] for v in wallets.values()],
                          **{f: [v[i + 1] for v in wallets.values()] for i, f in enumerate(WALLET_FIELDS)}})
        pq.write_table(table, OUT_DIR / "wallets.parquet", compression="zstd")
    return metas


# --------------------------------------------------------------------------------------
def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    buckets = resolve_buckets(args.buckets)
    summary: dict = {"source": SOURCE, "cutoff": args.cutoff}
    if not args.no_fetch:
        markets = load_markets(args.cutoff)
        markets = markets[markets.bucket.isin(buckets)]
        done = completed_markets(receipts)
        order = {slug: i for i, slug in enumerate(buckets)}
        early = fetched_before_close(markets, done)
        todo = markets[~markets.conditionId.isin(done) | args.refresh | early]
        todo = todo.assign(_o=todo.bucket.map(order)).sort_values(["_o", "sport_date", "id"])
        if args.limit:
            todo = todo.head(args.limit)
        jobs = [{"condition_id": r.conditionId, "market_id": r.id, "bucket": r.bucket} for r in todo.itertuples()]
        C.log(f"[{SOURCE}] {len(markets)} markets selected in {buckets}; {len(markets) - len(todo)} already complete; "
              f"{len(jobs)} to fetch ({int(early.sum())} again: fetched before the market closed)")
        summary.update(markets_selected=len(markets), markets_to_fetch=len(jobs), markets_refetch=int(early.sum()))
        if jobs:
            summary["fetch"] = run_fetch(jobs, args.workers, args.rps, receipts)
    if not args.no_rebuild:
        metas = rebuild_parquet(receipts, buckets if args.rebuild_selected_only else None)
        summary["staged"] = {m["bucket"]: {"markets": m.get("markets", 0), "rows": m.get("rows", 0)} for m in metas}
    return summary


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--buckets", default="all", help="comma list of groups (main-tour, rest, lower, all) and/or bucket slugs")
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF, help="latest event sporting date to include (ISO, UTC)")
    parser.add_argument("--limit", type=int, default=0, help="fetch at most this many markets (0 = all)")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--rps", type=float, default=12.0, help="global request rate cap (documented limit 20/s)")
    parser.add_argument("--refresh", action="store_true", help="re-fetch markets that already completed")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--no-rebuild", action="store_true")
    parser.add_argument("--rebuild-selected-only", action="store_true")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.STUDY_ROOT.mkdir(parents=True, exist_ok=True)
    with (C.STUDY_ROOT / "polymarket_runs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"finished_at": C.utc_now_iso(), **summary}, ensure_ascii=False) + "\n")
    C.log(f"[{SOURCE}] done: {json.dumps(summary, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
