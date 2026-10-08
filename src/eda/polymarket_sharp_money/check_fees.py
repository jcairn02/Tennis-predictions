"""Check the study's taker-fee model against the cash Polymarket actually moved.

The trades feed carries book prices only. build_positions.py charges a taker either the shares missing from a
BUY (fee taken in shares) or, from FEE_CASH_START (measured by calibrate_fees.py), rate * p * (1 - p) USDC per
share on fee-charging markets. This is an independent sample drawn after that calibration. The wallet activity feed
(https://data-api.polymarket.com/activity) reports `usdcSize`, the cash that changed hands, so for a sample of
taker fills the modelled cash (book value +/- modelled USDC fee) can be compared with it.

Sample: taker fills of at least $20 at 5-95c, stratified by fee schedule, side and month, drawn with a fixed
seed from the staged trades. Output: data/studies/polymarket_sharp_money/fee_check.json (every checked fill).

Usage:
    ./python.sh src/eda/polymarket_sharp_money/check_fees.py --per-stratum 4
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_positions as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "polymarket_sharp_money"
ACTIVITY = "https://data-api.polymarket.com/activity"


def sample_fills(per_stratum: int, seed: int) -> pd.DataFrame:
    markets = pd.read_parquet(STUDY / "markets.parquet", columns=["condition_id", "fee_type", "fee_rate"])
    frames = []
    for path in sorted(B.TRADES_DIR.glob("*.parquet")):
        if path.name == "wallets.parquet":
            continue
        f = pd.read_parquet(path, columns=["condition_id", "tx_hash", "seq", "proxy_wallet", "side", "size", "price",
                                           "timestamp"])
        f = B.add_roles(f)
        f = f[f.is_taker & (f["size"] * f["price"] >= 20) & f["price"].between(*B.CONTESTED)]
        frames.append(f)
    fills = pd.concat(frames).merge(markets, on="condition_id")
    fills["fee_type"] = fills.fee_type.fillna("none")
    fills["month"] = pd.to_datetime(fills.timestamp, unit="s").dt.strftime("%Y-%m")
    fills["in_shares"] = fills.share_fee > 0
    shuffled = fills.sample(frac=1.0, random_state=seed)
    return shuffled.groupby(["fee_type", "side", "month", "in_shares"]).head(per_stratum)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-stratum", type=int, default=4)
    ap.add_argument("--seed", type=int, default=20260926)  # not calibrate_fees.py's seed: an independent sample
    args = ap.parse_args()
    sample = sample_fills(args.per_stratum, args.seed)
    session = requests.Session()
    session.headers["User-Agent"] = "tennis-predictions-sharp-money/1.0 (research use; python-requests)"
    rows = []
    for r in sample.itertuples():
        params = {"user": r.proxy_wallet, "start": int(r.timestamp), "end": int(r.timestamp), "limit": 100,
                  "type": "TRADE"}
        try:
            got = session.get(ACTIVITY, params=params, timeout=60).json()
        except (requests.RequestException, ValueError) as err:
            rows.append({"tx_hash": r.tx_hash, "error": repr(err)})
            continue
        hits = [a for a in got if a.get("transactionHash") == r.tx_hash and a.get("side") == r.side]
        if len(hits) != 1:
            rows.append({"tx_hash": r.tx_hash, "error": f"{len(hits)} matching activity rows"})
            continue
        a = hits[0]
        cash = float(a["usdcSize"])
        book = float(a["size"]) * float(a["price"])
        charged = r.share_fee == 0 and r.timestamp >= B.FEE_CASH_START
        usdc_fee = r.size_gross * r.fee_rate * r.price * (1 - r.price) if charged else 0.0
        modelled = book + usdc_fee if r.side == "BUY" else book - usdc_fee
        rows.append({"tx_hash": r.tx_hash, "fee_type": r.fee_type, "month": r.month, "side": r.side,
                     "price": r.price, "shares_trades_feed": r.size, "shares_activity": float(a["size"]),
                     "fee_in_shares": float(r.share_fee), "cash_activity": cash, "book_value": book,
                     "cash_modelled": modelled, "error_usdc": modelled - cash,
                     "error_per_share": (modelled - cash) / float(a["size"])})
        time.sleep(0.15)
    checked = pd.DataFrame([x for x in rows if "error" not in x])
    ok = (checked.error_per_share.abs() <= 1e-4) if len(checked) else pd.Series(dtype=bool)
    summary = {"retrieved_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "endpoint": ACTIVITY,
               "sampled": int(len(sample)), "checked": int(len(checked)),
               "not_found": [x for x in rows if "error" in x],
               "within_0.0001_usdc_per_share": int(ok.sum()),
               "by_fee_type": checked.assign(ok=ok).groupby("fee_type").ok.agg(["size", "sum"]).to_dict("index")
               if len(checked) else {},
               "largest_errors": checked.reindex(checked.error_per_share.abs().sort_values(ascending=False).index)
               .head(10).to_dict("records") if len(checked) else [],
               "rows": checked.to_dict("records")}
    (STUDY / "fee_check.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("rows", "largest_errors")}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
