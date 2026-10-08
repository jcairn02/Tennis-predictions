"""Line sharpening: check the listed and validated starts of play, and both closes, against official first points.

Known first points (2026 main tour): the match-timing study's links (data/studies/match_timing/links/) from TDI
(ATP tour, first point), the Grand Slams' feeds (first point) and the WTA API (first point). A Polymarket market
reaches them through its tennis-data row (sharp_benchmark matches.parquet) -> the staged row's position ->
links/tennis_data.parquet's match_id.

Output: data/studies/line_sharpening/starts_check.json

Usage:
    ./python.sh src/eda/line_sharpening/starts_check.py
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

LINKS = ROOT / "data" / "studies" / "match_timing" / "links"
TD = ROOT / "data" / "dump" / "odds" / "tennis_data_couk"
SOURCES = ("tdi", "slam_feeds", "wta_api")


def known_starts() -> pd.DataFrame:
    """condition_id -> official first point (epoch s) and its source."""
    m = pd.read_parquet(ROOT / "data" / "studies" / "sharp_benchmark" / "matches.parquet",
                        columns=["td_file", "td_row", "condition_id", "level"])
    keys = []
    for f in sorted(TD.glob("*/*/202[56].parquet")):
        d = pd.read_parquet(f, columns=["_source_file", "_row"])
        keys.append(pd.DataFrame({"td_file": d["_source_file"].astype(str), "td_row": d["_row"].astype(int),
                                  "source_key": f.relative_to(ROOT).as_posix() + "#"
                                  + pd.Series(np.arange(len(d))).astype(str)}))
    m = m[m.condition_id.notna()].assign(td_row=lambda x: x.td_row.astype(int)).merge(
        pd.concat(keys), on=["td_file", "td_row"], how="left")
    m = m.merge(pd.read_parquet(LINKS / "tennis_data.parquet", columns=["match_id", "source_key"]), on="source_key")
    first = []
    for src in SOURCES:
        d = pd.read_parquet(LINKS / f"{src}.parquet", columns=["match_id", "start_utc"])
        first.append(d[d.start_utc.notna()].assign(source=src))
    first = pd.concat(first)
    first["first_point"] = K.epoch(pd.to_datetime(first.start_utc, utc=True))
    first = first.sort_values("source").drop_duplicates("match_id")
    return m.merge(first[["match_id", "first_point", "source"]], on="match_id")[["condition_id", "first_point", "source"]]


def q(s: pd.Series) -> dict:
    return {f"p{int(x * 100)}": round(float(s.quantile(x)), 1) for x in (0.05, 0.25, 0.5, 0.75, 0.95)}


def main() -> int:
    pm = pd.read_parquet(K.OUT / "markets.parquet")
    k = known_starts().merge(pm, on="condition_id")
    # Keep matches whose official first point is within a day of the listed start (a later first point is a
    # match moved to another day, where the official clock and the listing describe different events).
    k = k[(k.first_point - k.start_ts).abs() <= 24 * 3600]
    out = {"markets": int(len(k)), "by_source": k.source.value_counts().to_dict(),
           "by_level": k.level.value_counts().to_dict()}
    listed = (k.first_point - k.start_ts) / 60
    out["first_point_minus_listed_min"] = q(listed)
    out["listed_within_5_min"] = round(float((listed.abs() <= 5).mean()), 3)
    v = k[k.play_ts.notna()]
    err = (v.play_ts - v.first_point) / 60
    out["validated_found"] = round(float(k.play_ts.notna().mean()), 3)
    out["validated_minus_first_point_min"] = q(err)
    out["validated_within_5_min"] = round(float((err.abs() <= 5).mean()), 3)
    out["validated_within_15_min"] = round(float((err.abs() <= 15).mean()), 3)
    out["validated_late_over_15_min"] = round(float((err > 15).mean()), 3)
    out["validated_early_over_15_min"] = round(float((err < -15).mean()), 3)
    for name, col in (("main_close", "close_ts"), ("extended_close", "close_ext_ts")):
        lead = (k.first_point - k[col]) / 60
        out[name] = {"after_first_point_share": round(float((lead < 0).mean()), 4),
                     "after_first_point_markets": int((lead < 0).sum()),
                     "minutes_before_first_point": q(lead)}
    out["suspect_close_flagged"] = int(k.suspect_close.sum())
    (K.OUT / "starts_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
