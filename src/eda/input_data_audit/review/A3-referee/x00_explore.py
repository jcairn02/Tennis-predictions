"""A3-referee: first look at the data shapes (read-only)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)

S0 = ROOT / "data/studies/predictability_diagnostic"
m = pd.read_parquet(S0 / "stage0_matches.parquet")
p = pd.read_parquet(S0 / "stage0_match_players.parquet")
print("matches", m.shape, list(m.columns))
print("players", p.shape, list(p.columns))
print(m.head(2).T)

raw = pd.read_parquet(ROOT / "data/dump/matches/sackmann_archive/wta/wta_matches_2015.parquet")
print("sackmann wta 2015", raw.shape, list(raw.columns))
print(raw.head(2).T)

ov = pd.read_csv(ROOT / "data/raw/public_dump/match_charting_project/charting-w-stats-Overview.csv", nrows=5)
print("MCP overview", list(ov.columns))
print(ov.head())
mm = pd.read_csv(ROOT / "data/raw/public_dump/match_charting_project/charting-w-matches.csv", nrows=5)
print("MCP matches", list(mm.columns))
print(mm.head())

t = pq.ParquetFile(ROOT / "data/dump/points/wta/stats/2021.parquet").read().to_pandas()
t = t.loc[:, ~t.columns.duplicated()]
print("WTA API stats 2021", t.shape, list(t.columns))
print(t.head(3).T)
wm = pd.read_parquet(ROOT / "data/dump/points/wta/matches.parquet")
print("WTA matches", wm.shape, list(wm.columns))
print(wm.head(2).T)
ed = pd.read_parquet(ROOT / "data/dump/points/wta/editions.parquet")
print("WTA editions", ed.shape, list(ed.columns))
print(ed.head(3).T)
