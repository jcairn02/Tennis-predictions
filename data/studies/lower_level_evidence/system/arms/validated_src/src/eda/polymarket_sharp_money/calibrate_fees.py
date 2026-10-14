"""Measure the taker fee Polymarket actually charged on tennis moneylines, week by week.

The market metadata carries each market's current fee schedule (sports_fees_v2: rate 0.03; v3: 0.05), not what
was charged when a trade happened. A first check (check_fees.py) found January 2026 "v2" trades charged nothing,
April 2026 SELLs nothing in cash (BUYs paid in shares instead), and some July "v2" trades the v3 rate. So the
rate is measured: for sampled taker fills, the wallet activity feed's cash (usdcSize) against the book value
gives the USDC fee, and implied rate = fee per share / (p * (1 - p)), the documented formula's shape.

Sample: per ISO week x fee label x side, up to --per-cell taker fills of >= $20 at 5-95c whose fee was not taken
in shares (those need no calibration: the shortfall is in the trade records). Fixed seed.
Output: data/studies/polymarket_sharp_money/fee_timeline.json (every observation plus per-cell medians).

Usage:
    ./python.sh src/eda/polymarket_sharp_money/calibrate_fees.py --per-cell 4
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_positions as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "polymarket_sharp_money"
ACTIVITY = "https://data-api.polymarket.com/activity"


def candidates(seed: int, per_cell: int) -> pd.DataFrame:
    markets = pd.read_parquet(STUDY / "markets.parquet", columns=["condition_id", "fee_type"])
    frames = []
    for path in sorted(B.TRADES_DIR.glob("*.parquet")):
        if path.name == "wallets.parquet":
            continue
        f = pd.read_parquet(path, columns=["condition_id", "tx_hash", "seq", "proxy_wallet", "side", "size", "price",
                                           "timestamp"])
        f = B.add_roles(f)
        frames.append(f[f.is_taker & (f.share_fee == 0) & (f["size"] * f["price"] >= 20)
                        & f["price"].between(*B.CONTESTED)])
    fills = pd.concat(frames).merge(markets, on="condition_id")
    fills["fee_type"] = fills.fee_type.fillna("none")
    fills = fills[fills.timestamp >= pd.Timestamp("2026-01-01", tz="UTC").timestamp()]
    fills["week"] = pd.to_datetime(fills.timestamp, unit="s").dt.strftime("%G-W%V")
    return fills.sample(frac=1.0, random_state=seed).groupby(["week", "fee_type", "side"]).head(per_cell)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cell", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260925)
    args = ap.parse_args()
    sample = candidates(args.seed, args.per_cell)
    session = requests.Session()
    session.headers["User-Agent"] = "tennis-predictions-sharp-money/1.0 (research use; python-requests)"
    obs, missing, errors = [], 0, []
    for r in sample.itertuples():
        params = {"user": r.proxy_wallet, "start": int(r.timestamp), "end": int(r.timestamp), "limit": 100,
                  "type": "TRADE"}
        got = None
        for attempt in range(4):
            try:
                got = session.get(ACTIVITY, params=params, timeout=60).json()
            except (requests.RequestException, ValueError) as err:
                got = {"error": repr(err)}
            if isinstance(got, list):
                break
            time.sleep(2 * (attempt + 1))
        if not isinstance(got, list):
            missing += 1
            errors.append(str(got)[:200])
            continue
        hits = [a for a in got if a.get("transactionHash") == r.tx_hash and a.get("side") == r.side]
        if len(hits) != 1:
            missing += 1
            continue
        a = hits[0]
        shares, price, cash = float(a["size"]), float(a["price"]), float(a["usdcSize"])
        fee = (cash - shares * price) if r.side == "BUY" else (shares * price - cash)
        obs.append({"week": r.week, "timestamp": int(r.timestamp), "fee_type": r.fee_type, "side": r.side,
                    "price": price, "shares": shares, "fee_usdc": fee,
                    "implied_rate": fee / (shares * price * (1 - price))})
        time.sleep(0.12)
    o = pd.DataFrame(obs)
    cells = (o.groupby(["week", "fee_type", "side"]).implied_rate
             .agg(n="size", median="median", min="min", max="max").reset_index())
    out = {"retrieved_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "endpoint": ACTIVITY,
           "sampled": int(len(sample)), "observed": int(len(o)), "not_found": missing, "errors": errors[:20],
           "cells": cells.to_dict("records"), "observations": o.to_dict("records")}
    (STUDY / "fee_timeline.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 400)
    print(cells.round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
