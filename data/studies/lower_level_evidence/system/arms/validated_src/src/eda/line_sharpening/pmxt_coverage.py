"""Line sharpening: how much of Polymarket tennis the PMXT order-book archive holds, hour by hour.

For every STEP-th hour of the archive's life (2026-04-13T19 to 2026-08-10T00), only the `market` column of the
hourly file is read (about 2.5 MB of each 100-530 MB file, over HTTP range requests) and compared with the
tennis moneylines that our own trade record (data/dump/odds/polymarket/trades/) shows trading in that hour.
A market traded in an hour but absent from the archive's file is a gap.

Outputs (data/studies/line_sharpening/):
    pmxt_coverage.jsonl          one line per audited hour (resumable: audited hours are skipped)
    pmxt_coverage_summary.json   overall share, hours under 95%, file sizes

Usage:
    ./python.sh src/eda/line_sharpening/pmxt_coverage.py            (every 8th hour)
    ./python.sh src/eda/line_sharpening/pmxt_coverage.py --step 1   (every hour)
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.line_sharpening import common as K  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump.pmxt_books import URL, HttpRange  # noqa: E402

FIRST, LAST = "2026-04-13T19:00", "2026-08-10T00:00"
OUT = K.OUT / "pmxt_coverage.jsonl"


def traded_by_hour() -> pd.DataFrame:
    t0 = int(pd.Timestamp(FIRST, tz="UTC").timestamp())
    t1 = int(pd.Timestamp(LAST, tz="UTC").timestamp()) + 3600
    parts = []
    for f in sorted((K.PM_DIR / "trades").glob("*.parquet")):
        if f.name == "wallets.parquet":
            continue
        d = pd.read_parquet(f, columns=["condition_id", "timestamp"],
                            filters=[("timestamp", ">=", t0), ("timestamp", "<", t1)])
        d["hour"] = d.timestamp // 3600
        parts.append(d[["condition_id", "hour"]].drop_duplicates().assign(bucket=f.stem))
    return pd.concat(parts, ignore_index=True)


def audit(hour: pd.Timestamp, traded: pd.DataFrame) -> dict:
    key = hour.strftime("%Y-%m-%dT%H")
    f = HttpRange(URL.format(hour=key), C.session())
    rec = {"hour": key, "status": f.status, "bytes": f.size}
    want = traded[traded.hour == int(hour.timestamp()) // 3600]
    rec["tennis_traded"] = int(want.condition_id.nunique())
    if f.status != 200:
        return rec
    col = pq.ParquetFile(f, pre_buffer=True).read(columns=["market"])["market"].unique().to_pylist()
    present = {m.decode() if isinstance(m, bytes) else m for m in col}
    hit = want.condition_id.isin(present)
    rec.update(platform_markets=len(present), tennis_traded_present=int(want[hit].condition_id.nunique()),
               by_bucket=want.assign(hit=hit).groupby("bucket").hit.agg(["size", "sum"]).astype(int)
               .to_dict(orient="index"), fetched=f.fetched)
    return rec


def summarise() -> dict:
    d = pd.DataFrame([json.loads(x) for x in OUT.read_text().splitlines() if x.strip()]).sort_values("hour")
    ok = d[d.status == 200]
    share = ok.tennis_traded_present / ok.tennis_traded
    low = ok[share < 0.95]
    out = {"hours_audited": int(len(d)), "hours_missing_file": int((d.status != 200).sum()),
           "tennis_markets_traded": int(ok.tennis_traded.sum()),
           "present_in_archive": int(ok.tennis_traded_present.sum()),
           "present_share": round(float(ok.tennis_traded_present.sum() / ok.tennis_traded.sum()), 4),
           "hours_under_95pct": int(len(low)), "hours_with_none": int((ok.tennis_traded_present == 0).sum()),
           "low_hours": low[["hour", "tennis_traded", "tennis_traded_present"]].to_dict(orient="records"),
           "file_mb_mean": round(float(ok.bytes.mean() / 1e6), 1),
           "archive_tb_estimate": round(float(ok.bytes.mean() * len(pd.date_range(FIRST, LAST, freq="h")) / 1e12), 2)}
    (K.OUT / "pmxt_coverage_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=8)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    hours = pd.date_range(FIRST, LAST, freq="h", tz="UTC")[::args.step]
    done = set()
    if OUT.exists():
        done = {json.loads(x)["hour"] for x in OUT.read_text().splitlines() if x.strip()}
    todo = [h for h in hours if h.strftime("%Y-%m-%dT%H") not in done]
    if todo:
        traded = traded_by_hour()
        with cf.ThreadPoolExecutor(args.workers) as ex, OUT.open("a") as out:
            for rec in ex.map(lambda h: audit(h, traded), todo):
                out.write(json.dumps(rec) + "\n")
                out.flush()
    s = summarise()
    print(json.dumps({k: v for k, v in s.items() if k != "low_hours"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
