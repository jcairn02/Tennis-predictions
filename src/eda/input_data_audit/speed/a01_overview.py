"""Audit step 1: overview of the panel (read-only)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 60)

p = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_panel.parquet")
print(p.shape)
print(p.dtypes.to_string())
print(p.head(3).T)
u = p[p["use"]]
print("use rows", len(u))
g = u.groupby(["tour", "source", "basis"]).size()
print(g)
# Slam editions by source
s = u[u["level"].eq("GS")]
t = s.groupby(["tour", "slam", "year", "mq", "source"]).agg(n=("y", "size"), y=("y", "mean"), med=("y", "median")).round(2)
print(t.to_string())
