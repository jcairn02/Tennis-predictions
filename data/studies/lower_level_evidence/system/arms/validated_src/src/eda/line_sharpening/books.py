"""Line sharpening, step 2: replay the PMXT order books of the sample block and measure, minute by minute, what
could be bet at market on each side.

The archive's token0 events (src/ingest/public_dump/pmxt_books.py) are replayed per market in arrival order: a
`book` event replaces the whole book, a `price_change` sets one level's aggregate size (0 removes it). The book
is unknown until the market's first snapshot in the block. At the end of every minute before the close
(build.py) the book gives:
    mid, spread                      from the best bid and ask of outcome 0 (player A)
    vwap_a_<X>, vwap_b_<X>           average price of a market buy of $X of A (taking A's asks) and of B (taking
                                     A's bids, at 1 - bid), NaN if the book cannot fill it
    cap_a_<d>, cap_b_<d>             the most $ a market buy can take while its average price stays within d of
                                     that side's mid (B's mid is 1 - mid)
A side is "bettable at $X within d" when vwap - side mid <= d; a market is bettable when both sides are.

Inputs:  data/dump/odds/polymarket/books_pmxt/*.parquet, data/studies/line_sharpening/markets.parquet
Outputs: data/studies/line_sharpening/book_minutes.parquet, book_summary.json

Usage:
    ./python.sh src/eda/line_sharpening/books.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.line_sharpening import common as K  # noqa: E402

BOOKS = K.PM_DIR / "books_pmxt"
SIZES = (100, 300, 1000)          # $ bet sizes
DELTAS = (0.01, 0.02)             # allowed average price above the side's mid


def parse_levels(text) -> dict[float, float]:
    if not isinstance(text, str) or not text:
        return {}
    return {round(float(p), 4): float(s) for p, s in json.loads(text) if float(s) > 0}


def buy_side(prices: np.ndarray, sizes: np.ndarray, mid: float) -> dict:
    """Market buy taking levels in ascending price order. Returns the VWAP for each $ size and the largest $
    whose VWAP stays within each delta of `mid`."""
    out = {}
    if len(prices) == 0 or not np.isfinite(mid):
        for x in SIZES:
            out[f"vwap_{x}"] = np.nan
        for d in DELTAS:
            out[f"cap_{int(d * 100)}"] = 0.0
        return out
    cost = np.cumsum(prices * sizes)
    shares = np.cumsum(sizes)
    for x in SIZES:
        k = np.searchsorted(cost, x, side="left")
        if k >= len(cost):
            out[f"vwap_{x}"] = np.nan
            continue
        c0 = cost[k - 1] if k else 0.0
        s0 = shares[k - 1] if k else 0.0
        out[f"vwap_{x}"] = x / (s0 + (x - c0) / prices[k])
    vwap_full = cost / shares
    for d in DELTAS:
        lim = mid + d
        k = int(np.searchsorted(vwap_full, lim + 1e-12, side="right"))   # levels fully takeable
        c0 = cost[k - 1] if k else 0.0
        s0 = shares[k - 1] if k else 0.0
        if k < len(prices):            # level k cannot be taken whole, so its price is above the limit
            extra = min(sizes[k], max(0.0, (lim * s0 - c0) / (prices[k] - lim)))
            c0 += prices[k] * extra
        out[f"cap_{int(d * 100)}"] = float(c0)
    return out


def snapshot(bids: dict, asks: dict) -> dict | None:
    if not bids or not asks:
        return None
    bp = np.array(sorted(bids, reverse=True))
    ap = np.array(sorted(asks))
    bb, ba = bp[0], ap[0]
    mid = (bb + ba) / 2
    a = buy_side(ap, np.array([asks[p] for p in ap]), mid)
    b = buy_side(1.0 - bp, np.array([bids[p] for p in bp]), 1.0 - mid)
    row = {"best_bid": bb, "best_ask": ba, "mid": mid, "spread": ba - bb}
    row.update({f"{k.split('_')[0]}_a_{k.split('_')[1]}": v for k, v in a.items()})
    row.update({f"{k.split('_')[0]}_b_{k.split('_')[1]}": v for k, v in b.items()})
    return row


def replay(ev: pd.DataFrame, grid: np.ndarray, repair: bool = True) -> tuple[list[dict], dict]:
    """Replay one market's token0 events (sorted) and sample the book at the end of each grid minute.

    Each price_change row carries the exchange's best bid and ask after its message (0 and 1 when a side is
    empty). The archive sometimes lacks the rows that removed levels (a market maker pulling its quotes shows as
    a jump in the exchange's best bid or ask with no removal rows), which would leave stale quotes in the replay
    and overstate depth. With `repair`, levels better than the exchange's best are deleted after every row.
    Each sampled minute records whether the replay's best bid and ask equal the exchange's latest (`bbo_match`),
    so a missing addition (which cannot be repaired) is visible."""
    bids: dict[float, float] = {}
    asks: dict[float, float] = {}
    known = False
    rows, gi = [], 0
    stats = {"rows": 0, "repairs": 0}
    ts = ev.ts_s.to_numpy()
    et = ev.event_type.to_numpy()
    pr, sz, sd = ev.price.to_numpy(), ev["size"].to_numpy(), ev.side.to_numpy()
    bj, aj = ev.bids.to_numpy(), ev.asks.to_numpy()
    has_bbo = "best_bid" in ev
    xb_all = ev.best_bid.to_numpy() if has_bbo else None
    xa_all = ev.best_ask.to_numpy() if has_bbo else None
    ex_bid = ex_ask = np.nan
    n = len(ev)
    i = 0
    while gi < len(grid):
        g = grid[gi]
        while i < n and ts[i] <= g:
            if et[i] == "book":
                bids, asks, known = parse_levels(bj[i]), parse_levels(aj[i]), True
                ex_bid = max(bids) if bids else 0.0
                ex_ask = min(asks) if asks else 1.0
            elif et[i] == "price_change" and known:
                stats["rows"] += 1
                book = bids if sd[i] == "BUY" else asks
                p = round(float(pr[i]), 4)
                if sz[i] > 0:
                    book[p] = float(sz[i])
                else:
                    book.pop(p, None)
                if has_bbo and np.isfinite(xb_all[i]) and np.isfinite(xa_all[i]):
                    ex_bid, ex_ask = float(xb_all[i]), float(xa_all[i])
                    if repair:
                        if bids and max(bids) > ex_bid + 1e-9:
                            bids = {q: s for q, s in bids.items() if q <= ex_bid + 1e-9}
                            stats["repairs"] += 1
                        if asks and min(asks) < ex_ask - 1e-9:
                            asks = {q: s for q, s in asks.items() if q >= ex_ask - 1e-9}
                            stats["repairs"] += 1
            i += 1
        if known:
            snap = snapshot(bids, asks)
            if snap is not None:
                snap["t"] = g
                snap["ex_bid"], snap["ex_ask"] = ex_bid, ex_ask
                snap["bbo_match"] = bool(abs(snap["best_bid"] - ex_bid) < 1e-6 and abs(snap["best_ask"] - ex_ask) < 1e-6)
                rows.append(snap)
        gi += 1
    return rows, stats


def load_events(close: dict[str, float]) -> pd.DataFrame:
    """Token0 book and level-change events of the given markets up to each market's close (in-play rows,
    the bulk of the archive, are dropped file by file)."""
    parts = []
    for path in sorted(BOOKS.glob("*.parquet")):
        d = pd.read_parquet(path, columns=["ts", "market", "event_type", "is_token0", "bids", "asks", "price", "size",
                                           "side", "best_bid", "best_ask"],
                            filters=[("is_token0", "==", True), ("event_type", "in", ["book", "price_change"])])
        d = d[d.market.isin(close.keys())]
        d["ts_s"] = K.epoch(d.ts)
        d = d[d.ts_s.to_numpy() <= d.market.map(close).to_numpy()]
        parts.append(d.drop(columns=["ts", "is_token0"]))
    ev = pd.concat(parts, ignore_index=True)
    return ev.sort_values(["market", "ts_s"], kind="stable")


def replay_markets(job: tuple) -> tuple[list[dict], dict]:
    """Worker: replay a chunk of markets. job = (list of (condition_id, mkt, lo, hi))."""
    specs = job
    ev = load_events({c: hi for c, _, _, hi in specs})
    rows, stats = [], {"rows": 0, "repairs": 0}
    by = {c: (m, lo, hi) for c, m, lo, hi in specs}
    for cid, g in ev.groupby("market", sort=False):
        m, lo, hi = by[cid]
        grid = np.arange(np.ceil(lo / 60) * 60, hi, 60.0)
        out, st = replay(g, grid)
        for k in stats:
            stats[k] += st[k]
        for r in out:
            r["mkt"] = m
            rows.append(r)
    return rows, stats


def main() -> int:
    from concurrent.futures import ProcessPoolExecutor

    hours = sorted(p.stem for p in BOOKS.glob("*.parquet"))
    block0 = pd.Timestamp(hours[0], tz="UTC").timestamp()
    block1 = pd.Timestamp(hours[-1], tz="UTC").timestamp() + 3600
    pm = pd.read_parquet(K.OUT / "markets.parquet")
    pm = pm[(pm.close_ts > block0) & (pm.created_ts < block1) & pm.p_close.notna()]
    specs = [(c, int(m), max(block0, cr), min(block1, cl))
             for c, m, cr, cl in zip(pm.condition_id, pm.mkt, pm.created_ts, pm.close_ts)]
    chunks = [specs[k::12] for k in range(12)]
    rows, stats = [], {"rows": 0, "repairs": 0}
    with ProcessPoolExecutor(12) as ex:
        for r, st in ex.map(replay_markets, chunks):
            rows.extend(r)
            for k in stats:
                stats[k] += st[k]
    out = pd.DataFrame(rows).sort_values(["mkt", "t"], kind="stable")
    out.to_parquet(K.OUT / "book_minutes.parquet", index=False)
    cover = pm.assign(complete=(pm.created_ts >= block0) & (pm.close_ts <= block1))
    summary = {"block": [hours[0], hours[-1]], "hours": len(hours), "markets_in_block": int(len(pm)),
               "markets_with_book": int(out.mkt.nunique()) if len(out) else 0,
               "complete_lives": int(cover.complete.sum()),
               "complete_by_tier": cover[cover.complete].tier.value_counts().to_dict(),
               "book_minutes": int(len(out)), "price_changes_replayed": stats["rows"],
               "repairs": stats["repairs"], "minutes_bbo_match_share": round(float(out.bbo_match.mean()), 4)}
    (K.OUT / "book_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
