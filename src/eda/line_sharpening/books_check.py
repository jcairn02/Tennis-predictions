"""Line sharpening: check the replayed order books.

1. Each `price_change` event carries the exchange's best bid and ask after it. The replay's own best bid and ask
   after applying the same event must equal them.
2. The replayed mid at the end of each minute against Polymarket's minute price history (prices-history), which
   the earlier studies read as the midpoint.

Output: data/studies/line_sharpening/books_check.json

Usage:
    ./python.sh src/eda/line_sharpening/books_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.line_sharpening import books as BK  # noqa: E402
from src.eda.line_sharpening import common as K  # noqa: E402

SAMPLE = 120          # markets for the event-level check
SEED = 20261006


def top_of_book_check(cids: list[str], close: dict[str, float]) -> dict:
    parts = []
    for path in sorted(BK.BOOKS.glob("*.parquet")):
        d = pd.read_parquet(path, columns=["ts", "market", "event_type", "is_token0", "bids", "asks", "price", "size",
                                           "side", "best_bid", "best_ask"],
                            filters=[("is_token0", "==", True), ("event_type", "in", ["book", "price_change"])])
        parts.append(d[d.market.isin(cids)])
    ev = pd.concat(parts, ignore_index=True)
    ev["ts_s"] = K.epoch(ev.ts)
    ev = ev[ev.ts_s.to_numpy() <= ev.market.map(close).to_numpy()].sort_values(["market", "ts_s"], kind="stable")
    # One exchange message can change several levels; each archived row carries the best bid and ask after the
    # whole message. So the comparison is made at the last row of each run of rows with the same timestamp.
    n = agree = n_all = agree_all = 0
    for _, g in ev.groupby("market", sort=False):
        bids, asks, known = {}, {}, False
        ts = g.ts_s.to_numpy()
        last_of_run = np.r_[ts[1:] != ts[:-1], True]
        for i, (et, bj, aj, p, s, sd, bb, ba) in enumerate(zip(g.event_type, g.bids, g.asks, g.price, g["size"],
                                                               g.side, g.best_bid, g.best_ask)):
            if et == "book":
                bids, asks, known = BK.parse_levels(bj), BK.parse_levels(aj), True
                continue
            if not known:
                continue
            book = bids if sd == "BUY" else asks
            p = round(float(p), 4)
            if s > 0:
                book[p] = float(s)
            else:
                book.pop(p, None)
            ok = int(abs((max(bids) if bids else 0.0) - (bb if np.isfinite(bb) else 0.0)) < 1e-6
                     and abs((min(asks) if asks else 1.0) - (ba if np.isfinite(ba) else 1.0)) < 1e-6)
            n_all += 1
            agree_all += ok
            if last_of_run[i]:
                n += 1
                agree += ok
    return {"markets": len(cids), "messages_checked": n, "messages_agree": agree,
            "agree_share": round(agree / n, 5) if n else None,
            "rows_checked": n_all, "rows_agree_share": round(agree_all / n_all, 5) if n_all else None}


def mid_vs_history(bm: pd.DataFrame) -> dict:
    pr = pd.read_parquet(K.OUT / "prices.parquet")
    pr = pr[pr.mkt.isin(bm.mkt.unique())].sort_values(["mkt", "t"])
    v, _ = K.lookup(pr.mkt.to_numpy(), pr.t.to_numpy(), pr.p.to_numpy(), bm.mkt.to_numpy(), bm.t.to_numpy(), max_age=120)
    x = bm.assign(hist_p=v).dropna(subset=["hist_p"])
    diff = (x.hist_p - x.mid).abs()
    tight = x.spread <= 0.10 + 1e-9
    return {"minutes": int(len(x)), "abs_diff_c_median": round(float(100 * diff.median()), 3),
            "within_half_cent_share": round(float((diff <= 0.005 + 1e-9).mean()), 4),
            "within_half_cent_share_spread_le_10c": round(float((diff[tight] <= 0.005 + 1e-9).mean()), 4),
            "within_half_cent_share_spread_gt_10c": round(float((diff[~tight] <= 0.005 + 1e-9).mean()), 4)
            if (~tight).any() else None,
            "spread_gt_10c_share": round(float((~tight).mean()), 4)}


def minute_agreement(bm: pd.DataFrame) -> dict:
    """The replay's best bid and ask at each sampled minute against the exchange's latest (after the repair in
    books.replay). Where they differ, is the replay's quote worse (a level missing from the replay: depth
    understated) or better (a stale level: depth overstated)?"""
    x = bm[bm.ex_bid.notna() & bm.ex_ask.notna()]
    miss = ~x.bbo_match
    worse = miss & ((x.best_bid < x.ex_bid - 1e-9) | (x.best_ask > x.ex_ask + 1e-9))
    better = miss & ((x.best_bid > x.ex_bid + 1e-9) | (x.best_ask < x.ex_ask - 1e-9))
    return {"minutes": int(len(x)), "match_share": round(float(x.bbo_match.mean()), 4),
            "replay_quote_worse_share": round(float(worse.mean()), 4),
            "replay_quote_better_share": round(float(better.mean()), 4)}


def main() -> int:
    pm = pd.read_parquet(K.OUT / "markets.parquet")
    bm = pd.read_parquet(K.OUT / "book_minutes.parquet")
    ids = pm[pm.mkt.isin(bm.mkt.unique())]
    rng = np.random.default_rng(SEED)
    pick = list(rng.choice(ids.condition_id.to_numpy(), size=min(SAMPLE, len(ids)), replace=False))
    out = {"top_of_book": top_of_book_check(pick, dict(zip(pm.condition_id, pm.close_ts))),
           "minute_top_of_book": minute_agreement(bm), "mid_vs_price_history": mid_vs_history(bm)}
    (K.OUT / "books_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
