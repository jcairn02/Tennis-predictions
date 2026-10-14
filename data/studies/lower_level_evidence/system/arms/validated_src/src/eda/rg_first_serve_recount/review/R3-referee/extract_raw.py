"""R3-referee, step 0: the raw Sackmann rows the review needs, read once with Stage 0's own loader.

Reads stage0_build.normalise(stage0_build.load_raw()) (the raw rows before any correction) and keeps the Sackmann rows
of the Slams, the Paris Olympics and the big clay events of 2018-2025 (main draw and qualifying), every row named in
the proposed table, and every row named in the decided row_corrections.csv that falls in these events.

Writes data/studies/rg_first_serve_recount/review/R3-referee/raw_subset.parquet (read-only elsewhere).
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/extract_raw.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R3-referee"
STUDY = ROOT / "data" / "studies" / "rg_first_serve_recount"
NAMES = ["Roland Garros", "Paris Olympics", "Australian Open", "Wimbledon", "US Open", "Us Open", "Madrid Masters",
         "Rome Masters", "Monte Carlo Masters", "Madrid", "Rome", "Internazionali BNL d'Italia", "Mutua Madrid Open"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = B.normalise(B.load_raw())
    raw = raw[raw["source"].eq("sackmann")]
    prop = pd.read_csv(STUDY / "proposed_corrections.csv", dtype=str, keep_default_na=False)
    keys = set(zip(prop["source_file"], pd.to_numeric(prop["source_row"]).astype(int)))
    rk = list(zip(raw["_source_file"].astype(str), pd.to_numeric(raw["_row"]).astype(int)))
    named = pd.Series([k in keys for k in rk], index=raw.index)
    tn = raw["tourney_name"].astype(str)
    big = tn.isin(NAMES) | tn.str.contains("Olympic", case=False) | tn.str.contains("Roland", case=False)
    yr = pd.to_numeric(raw["season"], errors="coerce")
    keep = named | (big & yr.between(2018, 2025))
    sub = raw[keep].copy()
    print("rows kept:", len(sub), "named in the proposal:", int(named.sum()), "of", len(keys))
    print(sub.groupby(["tour", "tourney_name"]).size().sort_values(ascending=False).head(40).to_string())
    print(sub.dtypes.to_string())
    try:
        sub.to_parquet(OUT / "raw_subset.parquet", index=False)
    except Exception as err:          # mixed object columns: write them as text, blanks kept as None
        print("as text:", err)
        for c in sub.columns:
            if sub[c].dtype == object:
                sub[c] = sub[c].map(lambda x: None if x is None or (isinstance(x, float) and x != x) else str(x))
        sub.to_parquet(OUT / "raw_subset.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
