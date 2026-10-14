"""B1 rhythm-and-body scout: outcome-free look at the fields the ideas need.

Reads no winner, no score string, no won/a_won column and no `*_n` box-score numerator (those reveal who won).
Only load denominators (sets played, points played), minutes, statuses, dates, starts, levels and entry codes.
Run: ./python.sh data/studies/unpriced_leads/team/rhythm_body/peek_fields.py > .../peek_fields.txt
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
S = ROOT / "data" / "studies"
D = ROOT / "data" / "dump"
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)

# ---- the clock's start field
tm = pd.read_parquet(S / "match_timing/timing.parquet",
                     columns=["match_id", "tour", "year", "level", "qualifying", "start", "es", "lf", "obs",
                              "exact", "best_source"])
print("timing: start non-null share", tm["start"].notna().mean().round(3))
print(tm["start"].describe())
st = tm["start"].dropna()
frac = st - np.floor(st)
print("start fractional-day share > 0:", float((frac > 1e-6).mean()))
print("sample starts:", st.sample(8, random_state=1).tolist())
print("es sample:", tm["es"].dropna().sample(5, random_state=1).tolist())
print(tm.loc[tm["start"].notna(), "best_source"].value_counts().head(15))

# ---- Stage 0 levels and entries (no outcomes)
s0 = pd.read_parquet(S / "predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
                              "tournament_name", "tournament_date", "status", "minutes", "best_of", "draw_size",
                              "surface", "indoor", "player_a_id", "player_b_id"])
print("\nStage 0 level x tour counts")
print(pd.crosstab(s0["level"], s0["tour"]))
print("\nStage 0 status counts")
print(s0["status"].value_counts())
team = s0[s0["level"].astype(str).str.upper().str.contains("TEAM|D|DC|BJK|F", regex=True)]
print("\nTEAM-like levels sample tournament names:")
print(s0[s0["level"].eq("TEAM")]["tournament_name"].value_counts().head(25) if (s0["level"] == "TEAM").any() else "no TEAM level")

mp = pd.read_parquet(S / "predictability_diagnostic/stage0_match_players.parquet",
                     columns=["match_id", "player_id", "side", "entry", "seed", "country", "height", "hand"])
print("\nentry codes")
print(mp["entry"].value_counts(dropna=False).head(20))

# ---- main-tour frame population: start coverage and minutes coverage by season and tour
fr = pd.read_parquet(S / "current_best_model/template_2026-10-10/model_frame.parquet",
                     columns=["match_id", "tour", "season"])
x = fr.merge(tm[["match_id", "start", "exact"]], on="match_id", how="left").merge(
    s0[["match_id", "minutes", "level", "best_of", "tournament_name"]], on="match_id", how="left")
x["has_start"] = x["start"].notna()
x["has_tod"] = x["start"].notna() & ((x["start"] - np.floor(x["start"])) > 1e-6)
x["has_min"] = x["minutes"].notna()
print("\nframe: share with start / time of day / minutes, by tour x season")
print(x.groupby(["tour", "season"])[["has_start", "has_tod", "has_min"]].mean().round(3).unstack(0))
print("frame level counts:", x["level"].value_counts().to_dict())
