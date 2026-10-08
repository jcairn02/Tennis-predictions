"""Audit step 4: independent copies of AO 2024 speeds (AO match centre Wayback captures, Flashscore crawl, handoff)."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path.cwd()
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 120)
A = ROOT / "data/dump/points/ausopen"
m = pd.read_parquet(A / "matches.parquet")
print("ausopen matches cols", list(m.columns))
print(m.groupby(["year", "event"]).size().unstack(fill_value=0))
st = pd.read_parquet(A / "set_statistics.parquet")
print("set_statistics cols", list(st.columns))
print(st.groupby("year").size())
s1 = st[st["stat"].eq("1st Serve Average") & st["set"].eq("All")]
print(s1.groupby(["year", "event"]).size())
print(s1[s1["year"].astype(str).eq("2024")].head(20).to_string())
# panel rows of ausopen_mc by year
p = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_panel.parquet")
print(p[p["source"].eq("ausopen_mc")].groupby(["tour", "year", "mq", "use"]).size())
rec = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_records.parquet")
print("records cols", list(rec.columns))
print(rec.groupby(["source", "year_s0"]).size().unstack(fill_value=0).T.to_string())
