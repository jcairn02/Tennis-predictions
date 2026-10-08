"""Check that the Data API lists a transaction's taker record first when both parties are requested.

The staged trades (polymarket_trades.py) come from /trades?takerOnly=false, which returns the taker's record and
one per matched maker order but does not label roles; /trades?takerOnly=true returns the takers only. For a
seeded sample of settled moneylines per tournament-type bucket (fewer than 10,000 records, so one page each),
both listings are fetched and the first record of every transaction in the full listing is compared with the
taker listing.

Output: data/studies/polymarket_sharp_money/taker_order_check.json

Usage:
    ./python.sh src/eda/polymarket_sharp_money/check_taker_order.py --per-bucket 3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "polymarket_sharp_money"
TRADES = "https://data-api.polymarket.com/trades"


def key(r: dict) -> tuple:
    return (r["proxyWallet"], r["side"], r["asset"], r["size"], r["price"], r["timestamp"], r["transactionHash"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-bucket", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20260925)
    args = ap.parse_args()
    markets = pd.read_parquet(STUDY / "markets.parquet", columns=["condition_id", "bucket_slug", "status", "n_rec"])
    pool = markets[(markets.status == "decisive") & markets.n_rec.between(50, 9000)]
    sample = pool.sample(frac=1.0, random_state=args.seed).groupby("bucket_slug").head(args.per_bucket)
    session = requests.Session()
    session.headers["User-Agent"] = "tennis-predictions-sharp-money/1.0 (research use; python-requests)"
    rows, totals = [], Counter()
    for m in sample.itertuples():
        both = session.get(TRADES, params={"market": m.condition_id, "takerOnly": "false", "limit": 10000}, timeout=120).json()
        takers = session.get(TRADES, params={"market": m.condition_id, "takerOnly": "true", "limit": 10000}, timeout=120).json()
        taker_keys = Counter(key(r) for r in takers)
        first: dict[str, tuple] = {}
        for r in both:
            first.setdefault(r["transactionHash"], key(r))
        agree = sum(1 for k in first.values() if taker_keys.get(k, 0) > 0)
        per_tx = Counter(r["transactionHash"] for r in takers)
        rows.append({"condition_id": m.condition_id, "bucket": m.bucket_slug, "records": len(both),
                     "transactions": len(first), "first_record_is_taker": agree,
                     "transactions_with_several_taker_records": sum(1 for c in per_tx.values() if c > 1)})
        totals["transactions"] += len(first)
        totals["agree"] += agree
        time.sleep(0.2)
    out = {"retrieved_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "endpoint": TRADES,
           "markets": len(rows), "transactions": totals["transactions"], "first_record_is_taker": totals["agree"],
           "rows": rows}
    (STUDY / "taker_order_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
