"""Round 0, body-and-schedule brainstormer: print the schemas of the tables the ideas would draw on.

No outcome is read or related to anything: column names, dtypes, row counts and non-missing shares only.
Run: ./python.sh src/eda/feature_interactions/round0/body/schemas.py
"""
from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
TABLES = [
    "data/studies/predictability_diagnostic/stage0_matches.parquet",
    "data/studies/predictability_diagnostic/stage0_match_players.parquet",
    "data/studies/match_timing/timing.parquet",
    "data/studies/match_timing/perplayer_features.parquet",
    "data/studies/surface_rating_race/model/model_frame.parquet",
]


def main() -> None:
    for rel in TABLES:
        path = ROOT / rel
        if not path.exists():
            print(f"\n## {rel}: MISSING")
            continue
        pf = pq.ParquetFile(path)
        print(f"\n## {rel}: {pf.metadata.num_rows:,} rows, {pf.metadata.num_columns} columns")
        for field in pf.schema_arrow:
            print(f"  {field.name}: {field.type}")


if __name__ == "__main__":
    main()
