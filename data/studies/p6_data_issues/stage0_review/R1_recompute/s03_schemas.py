"""R1 recompute, step 3: schemas of the independent listings (read-only)."""
import os
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)

for f in ["data/dump/points/tennislive/listed.parquet",
          "data/dump/points/sofascore_editions/events.parquet",
          "data/dump/points/sofascore/events.parquet"]:
    print("=" * 100)
    print(f, os.path.getsize(f), "bytes")
    d = pd.read_parquet(f)
    print(d.shape)
    print(d.dtypes.to_string())
    print(d.head(3).T.to_string())
