"""B1-rederive reviewer: inspect the columns of the live tables (read-only)."""
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
FILES = [
    "data/studies/predictability_diagnostic/stage0_matches.parquet",
    "data/studies/predictability_diagnostic/stage0_match_players.parquet",
    "data/studies/predictability_diagnostic/stage1_odds.parquet",
    "data/studies/serve_speed_tabpfn/speed_records.parquet",
    "data/studies/serve_speed_tabpfn/speed_panel.parquet",
]
for f in FILES:
    pf = pq.ParquetFile(ROOT / f)
    print("==", f, pf.metadata.num_rows, "rows")
    print(pf.schema_arrow.names)
