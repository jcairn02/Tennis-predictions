"""Polymarket tennis order-book events from the PMXT public archive (v2), hour by hour.

PMXT (https://archive.pmxt.dev/docs/v2-data-overview) records Polymarket's CLOB WebSocket market channel for
every live asset and publishes one Parquet file per UTC hour at
    https://r2v2.pmxt.dev/polymarket_orderbook_<YYYY-MM-DDTHH>.parquet
sorted by (market, asset_id, timestamp_received). Event types: `book` (a full snapshot, sent after each trade
and on subscription), `price_change` (the new aggregate size at one price level, with the best bid and ask
after it), `last_trade_price` and `tick_size_change`. Observed on 6 Oct 2026: files exist from 2026-04-13T19
to 2026-08-10T00 (later hours answer 404; the index page archive.pmxt.dev refused connections), 100-530 MB
each, 48-90 row groups of ~1M rows, no page index. Tennis is 0.06-3% of rows.

Only the columns needed to replay a book are read, over HTTP range requests (about 70% of each file's bytes):
timestamp_received, market, event_type, asset_id, bids, asks, price, size, side, best_bid, best_ask. Rows are
kept when `market` is a tennis moneyline condition id in the staged index (data/dump/odds/polymarket/
market_index.parquet) and either (a) the event is on the market's first outcome token (token0), or (b) it is a
`last_trade_price` event on either token. The two tokens' books mirror each other (token1's bids are 1 - token0's
asks, same sizes; checked on Wimbledon 2026 hours), so token0 carries the whole book; the receipt counts both
tokens' price_change rows per hour so the mirror can be checked.

Layout:
    data/raw/public_dump/pmxt_books/_receipts.jsonl        one receipt per hour (url, size, ETag, counts)
    data/dump/odds/polymarket/books_pmxt/<hour>.parquet    kept rows of that hour

The archive's own files are not kept (only the tennis rows), so a re-run fetches them again.
Rights: public HTTPS, no credentials; PMXT's hosted-API plans are personal-use and the SDK's MIT licence does not
by itself license the data (source register, `pmxt`). Kept for this project's research only.

Usage:
    ./python.sh -m src.ingest.public_dump.pmxt_books --start 2026-07-31T00 --end 2026-08-04T00 --workers 4
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "pmxt_books"
URL = "https://r2v2.pmxt.dev/polymarket_orderbook_{hour}.parquet"
INDEX = C.PROJECT_ROOT / "data" / "dump" / "odds" / "polymarket" / "market_index.parquet"
OUT_DIR = C.PROJECT_ROOT / "data" / "dump" / "odds" / "polymarket" / "books_pmxt"
COLUMNS = ["timestamp_received", "market", "event_type", "asset_id", "bids", "asks", "price", "size", "side",
           "best_bid", "best_ask"]
OUT_SCHEMA = pa.schema([
    ("ts", pa.timestamp("ms", tz="UTC")), ("market", pa.string()), ("event_type", pa.string()),
    ("asset_id", pa.string()), ("is_token0", pa.bool_()), ("bids", pa.string()), ("asks", pa.string()),
    ("price", pa.float64()), ("size", pa.float64()), ("side", pa.string()), ("best_bid", pa.float64()),
    ("best_ask", pa.float64()),
])


class HttpRange(io.RawIOBase):
    """Seekable read-only file over HTTP range requests (enough for pyarrow's Parquet reader)."""

    def __init__(self, url: str, sess: requests.Session, retries: int = 5):
        self.url, self.sess, self.retries = url, sess, retries
        head = sess.head(url, timeout=60)
        self.status = head.status_code
        self.size = int(head.headers.get("Content-Length", 0)) if head.ok else 0
        self.etag = head.headers.get("ETag")
        self.last_modified = head.headers.get("Last-Modified")
        self.pos, self.fetched, self.requests = 0, 0, 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.size, self.pos + n) - 1
        for attempt in range(self.retries):
            try:
                r = self.sess.get(self.url, headers={"Range": f"bytes={self.pos}-{end}"}, timeout=180)
                r.raise_for_status()
                data = r.content
                if len(data) != end - self.pos + 1:
                    raise requests.RequestException(f"short read {len(data)} of {end - self.pos + 1}")
                break
            except requests.RequestException:
                if attempt == self.retries - 1:
                    raise
                time.sleep(3 * (attempt + 1))
        self.pos += len(data)
        self.fetched += len(data)
        self.requests += 1
        return data

    def readinto(self, buffer) -> int:
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def tennis_tokens() -> tuple[pa.Array, pa.Array]:
    """Condition ids (as the archive's 66-byte binary) and first-outcome token ids of every tennis moneyline."""
    mi = pd.read_parquet(INDEX, columns=["conditionId", "sportsMarketType", "clobTokenIds"])
    mi = mi[(mi.sportsMarketType == "moneyline") & mi.conditionId.notna()].drop_duplicates("conditionId")
    token0 = [json.loads(t)[0] if isinstance(t, str) and t.startswith("[") else None for t in mi.clobTokenIds]
    ids = pa.array([c.encode() for c in mi.conditionId], type=pa.binary(66))
    return ids, pa.array([t for t in token0 if t], type=pa.string())


def extract(table: pa.Table, ids: pa.Array, token0: pa.Array) -> tuple[pa.Table, dict]:
    """Tennis rows to keep from one row group, and per-token price_change counts for the mirror check."""
    tennis = table.filter(pc.is_in(table["market"], value_set=ids))
    if tennis.num_rows == 0:
        return tennis, {}
    is0 = pc.is_in(tennis["asset_id"], value_set=token0)
    pchg = pc.equal(tennis["event_type"], "price_change")
    counts = {"pc_token0": int(pc.sum(pc.and_(pchg, is0)).as_py() or 0),
              "pc_token1": int(pc.sum(pc.and_(pchg, pc.invert(is0))).as_py() or 0)}
    keep = pc.or_(is0, pc.equal(tennis["event_type"], "last_trade_price"))
    return tennis.append_column("is_token0", is0).filter(keep), counts


def to_out(t: pa.Table) -> pa.Table:
    cols = {
        "ts": t["timestamp_received"].cast(pa.timestamp("ms", tz="UTC")),
        "market": t["market"].cast(pa.binary()).cast(pa.string()),
        "event_type": t["event_type"], "asset_id": t["asset_id"], "is_token0": t["is_token0"],
        "bids": t["bids"], "asks": t["asks"],
    }
    for name in ("price", "size", "best_bid", "best_ask"):
        cols[name] = t[name].cast(pa.float64())
    cols["side"] = t["side"]
    return pa.table(cols).select(OUT_SCHEMA.names).cast(OUT_SCHEMA)


def fetch_hour(hour: str, ids: pa.Array, token0: pa.Array) -> dict:
    t0 = time.time()
    url = URL.format(hour=hour)
    f = HttpRange(url, C.session())
    receipt = {"name": hour, "url": url, "status": f.status, "bytes": f.size, "etag": f.etag,
               "last_modified": f.last_modified, "retrieved_at": C.utc_now_iso()}
    if f.status != 200:
        return receipt
    pf = pq.ParquetFile(f, pre_buffer=True)
    parts, rows_total, counts = [], 0, {"pc_token0": 0, "pc_token1": 0}
    for i in range(pf.metadata.num_row_groups):
        rg = pf.read_row_group(i, columns=COLUMNS)
        rows_total += rg.num_rows
        kept, c = extract(rg, ids, token0)
        for k, v in c.items():
            counts[k] += v
        if kept.num_rows:
            parts.append(to_out(kept))
    out = pa.concat_tables(parts) if parts else OUT_SCHEMA.empty_table()
    dest = OUT_DIR / f"{hour}.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".parquet.tmp")
    pq.write_table(out, tmp, compression="zstd")
    tmp.replace(dest)
    receipt.update(rows_total=rows_total, rows_kept=out.num_rows,
                   markets_kept=len(set(out["market"].to_pylist())) if out.num_rows else 0,
                   fetched=f.fetched, requests=f.requests, seconds=round(time.time() - t0, 1),
                   dest=C.rel(dest), done=True, **counts)
    return receipt


def hours(start: str, end: str) -> list[str]:
    rng = pd.date_range(pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC"), freq="h", inclusive="left")
    return [h.strftime("%Y-%m-%dT%H") for h in rng]


def run(args) -> dict:
    receipts = C.Receipts(SOURCE)
    todo = [h for h in hours(args.start, args.end) if not (receipts.get(h) or {}).get("done")]
    C.log(f"{len(todo)} hours to fetch ({args.start} to {args.end}, {args.workers} workers)")
    ids, token0 = tennis_tokens()
    summary = {"hours": 0, "missing": 0, "rows_kept": 0, "fetched": 0}
    with ThreadPoolExecutor(args.workers) as ex:
        for rec in ex.map(lambda h: fetch_hour(h, ids, token0), todo):
            receipts.record(rec)
            summary["hours"] += 1
            if not rec.get("done"):
                summary["missing"] += 1
                C.log(f"{rec['name']}: HTTP {rec['status']}")
                continue
            summary["rows_kept"] += rec["rows_kept"]
            summary["fetched"] += rec["fetched"]
            C.log(f"{rec['name']}: kept {rec['rows_kept']:,} rows of {rec['rows_total']:,} "
                  f"({rec['markets_kept']} markets), fetched {rec['fetched'] / 1e6:.0f} MB in {rec['seconds']} s")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--start", required=True, help="first hour, e.g. 2026-07-31T00 (UTC)")
    parser.add_argument("--end", required=True, help="hour after the last one (exclusive)")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
