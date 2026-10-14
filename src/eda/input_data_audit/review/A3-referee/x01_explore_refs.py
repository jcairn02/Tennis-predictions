"""A3-referee: what each possible referee source holds (read-only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 60)


def rd(p: Path) -> pd.DataFrame:
    t = pq.ParquetFile(p).read().to_pandas()
    return t.loc[:, ~t.columns.duplicated()]


P = ROOT / "data/dump/points"
for rel in ["sofascore/statistics.parquet", "sofascore/events.parquet", "sofascore_editions/statistics.parquet",
            "sofascore_editions/events.parquet", "sofascore_tournaments/statistics.parquet",
            "sofascore_tournaments/events.parquet", "tennislive/statistics.parquet", "tennislive/matches.parquet",
            "tdi/statistics.parquet", "tdi/matches.parquet", "sirgenkii_infotennis/atp_key_stats.parquet",
            "sirgenkii_infotennis/atp_results.parquet", "infosys_slams/keystats.parquet", "infosys_slams/matches.parquet",
            "infosys_slams/points.parquet", "ausopen/set_statistics.parquet", "ausopen/matches.parquet",
            "usopen/statistics.parquet", "wimbledon/statistics.parquet", "slam_ball_tracking/matches.parquet"]:
    f = P / rel
    try:
        t = rd(f)
    except Exception as e:  # noqa: BLE001
        print("==", rel, "ERR", e)
        continue
    print("==", rel, t.shape)
    print(list(t.columns))
    yc = [c for c in t.columns if c.lower() in ("year", "season", "eventyear", "date", "start_date", "starttimestamp")]
    for c in yc[:2]:
        try:
            print(c, t[c].astype(str).str[:4].value_counts().sort_index().to_dict())
        except Exception:  # noqa: BLE001
            pass
    print(t.head(2).T.head(40))
for d in ["sackmann_archive/slam_pointbypoint", "match_charting_project/stats", "match_charting_project/points"]:
    print("==", d, sorted(x.name for x in (P / d).iterdir())[:40])
