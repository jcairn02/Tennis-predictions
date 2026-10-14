"""Polymarket's tennis match-winner markets by tournament tier: how many, and how much they traded (market structure,
not results: no outcome or price is read).

Source: the staged catalog (data/dump/odds/polymarket/event_index.parquet, market_index.parquet), built by
src/ingest/public_dump/polymarket_catalog.py from Polymarket's public Gamma API; events listed 10 Sep 2025 - 7 Oct 2026.
The tier is the catalog's own inferred bucket (bucket, bucket_confidence): Challenger / WTA 125 events are inferred
from bare tournament names. Volume is each market's lifetime volume field (USDC), which includes any in-play trading.

Writes data/studies/event_levels/polymarket_tiers.csv and polymarket_tiers.json (source hashes, retrieval span).
Run: ./python.sh src/eda/event_levels/markets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.event_levels import common as C  # noqa: E402

PM = ROOT / "data" / "dump" / "odds" / "polymarket"


def main() -> int:
    e = pd.read_parquet(PM / "event_index.parquet", columns=["id", "bucket", "bucket_confidence", "catalog_retrieved_at"])
    m = pd.read_parquet(PM / "market_index.parquet", columns=["id", "sportsMarketType", "event_id", "volumeNum"])
    m = m[m["sportsMarketType"] == "moneyline"].merge(e.rename(columns={"id": "event_id"}), on="event_id",
                                                      how="left", validate="many_to_one")
    m["volume"] = pd.to_numeric(m["volumeNum"], errors="coerce")
    g = m.groupby("bucket", dropna=False).agg(
        markets=("id", "size"), with_volume=("volume", lambda v: int((v > 0).sum())),
        volume_p25=("volume", lambda v: v.quantile(0.25)), volume_median=("volume", "median"),
        volume_p75=("volume", lambda v: v.quantile(0.75)), volume_total=("volume", "sum"),
        inferred_share=("bucket_confidence", lambda s: float(s.astype(str).str.startswith("inferred").mean())))
    g["share_of_markets"] = g["markets"] / g["markets"].sum()
    g["share_of_volume"] = g["volume_total"] / g["volume_total"].sum()
    g = g.sort_values("markets", ascending=False).reset_index()
    g.to_csv(C.OUT / "polymarket_tiers.csv", index=False)
    C.write_json(C.OUT / "polymarket_tiers.json", {
        "what": "Polymarket match-winner (moneyline) markets by the catalog's inferred tier; lifetime volume (USDC)",
        "sources": {p.name: {"path": str(p.relative_to(ROOT)), "sha256": C.sha256_file(p)}
                    for p in (PM / "event_index.parquet", PM / "market_index.parquet")},
        "catalog_retrieved": [str(e["catalog_retrieved_at"].min()), str(e["catalog_retrieved_at"].max())],
        "moneyline_markets": int(len(m))})
    with pd.option_context("display.width", 250):
        print(g.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
