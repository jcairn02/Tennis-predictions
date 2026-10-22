"""R1 recompute, step 1: find the claimed rows in Stage 0 (read-only)."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 400)

S0 = "data/studies/predictability_diagnostic/stage0_matches.parquet"
s0 = pd.read_parquet(S0)
print("Stage 0 shape", s0.shape)
print(list(s0.columns))
print(s0.dtypes.to_string())

g1 = s0[s0["tournament_id"].astype(str) == "2024-2847"]
print("\nG1 rows with tournament_id 2024-2847:", len(g1))
cols = [c for c in ["match_id", "tour", "tournament_id", "tournament_name", "tournament_date", "tourney_level",
                    "level", "round", "source", "source_file", "source_row", "winner_name", "loser_name", "score",
                    "winner_id", "loser_id"] if c in s0.columns]
print(g1[cols].sort_values(cols[0]).to_string())

# Other Tenerife rows in 2024
ten = s0[s0["tournament_name"].astype(str).str.contains("Tenerife", case=False, na=False)]
print("\nAll Tenerife rows by tournament id/name/date/source:")
print(ten.groupby(["tournament_id", "tournament_name", "tournament_date", "source"], dropna=False).size().to_string())

for mid in ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]:
    r = s0[s0["match_id"] == mid]
    print("\nG2", mid, len(r))
    print(r.T.to_string())
