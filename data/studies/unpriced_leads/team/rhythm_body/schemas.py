"""B1 rhythm-and-body scout: outcome-free schema look at the tables the memo's ideas use.

Prints column names, dtypes and row counts only. Reads no result column of any season.
Run: ./python.sh data/studies/unpriced_leads/team/rhythm_body/schemas.py > .../schemas.txt
"""
import pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
TABLES = [
    "data/studies/match_timing/timing.parquet",
    "data/studies/predictability_diagnostic/stage0_matches.parquet",
    "data/studies/predictability_diagnostic/stage0_match_players.parquet",
    "data/dump/points/tennislive/events.parquet",
    "data/dump/points/tennislive/listed.parquet",
    "data/dump/points/tennislive/matches.parquet",
    "data/dump/points/tennislive/index.parquet",
    "data/dump/points/usopen/distance.parquet",
    "data/dump/points/usopen/matches.parquet",
    "data/dump/points/wimbledon/matches.parquet",
    "data/dump/points/wimbledon/tz.parquet",
    "data/dump/points/ausopen/matches.parquet",
    "data/dump/points/rolandgarros/matches.parquet",
    "data/dump/points/wta/events.parquet",
    "data/dump/points/wta/matches.parquet",
    "data/dump/points/wta/editions.parquet",
    "data/dump/points/infosys_atp/matches.parquet",
    "data/dump/points/infosys_atp/rally.parquet",
    "data/dump/points/infosys_slams/matches.parquet",
    "data/dump/points/sofascore/events.parquet",
    "data/dump/points/itf_live/events.parquet",
    "data/dump/matches/open_tennis_data/matches.parquet",
    "data/dump/matches/open_tennis_data/tournaments.parquet",
    "data/studies/current_best_model/template_2026-10-10/model_frame.parquet",
    "data/studies/feature_universe/store.parquet",
]

for rel in TABLES:
    p = ROOT / rel
    print("=" * 100)
    print(rel)
    if not p.exists():
        print("  MISSING")
        continue
    try:
        f = pq.ParquetFile(p)
        sch = f.schema_arrow
        print(f"  rows={f.metadata.num_rows:,}  cols={len(sch)}")
        names = [f"{fld.name}:{fld.type}" for fld in sch]
        if len(names) > 120:
            print("  first 120 columns:")
            names = names[:120]
        for i in range(0, len(names), 6):
            print("   ", " | ".join(names[i:i + 6]))
    except Exception as e:  # noqa: BLE001
        print("  ERROR", e)

for d in ["data/dump/matches/sackmann_archive/atp", "data/dump/matches/sackmann_archive/wta",
          "data/dump/points/wta/events", "data/dump/points/wta/player_matches"]:
    p = ROOT / d
    print("=" * 100)
    print(d)
    if p.exists():
        files = sorted(x.name for x in p.iterdir())
        print(f"  {len(files)} entries; first 30:", files[:30])
        print("  last 10:", files[-10:])
