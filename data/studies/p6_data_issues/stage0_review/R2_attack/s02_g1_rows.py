"""R2 (attack) scratch: G1's 31 rows against Sackmann's Tenerife 2024 editions. Read-only."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 50)

m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet")
mp = pd.read_parquet("data/studies/predictability_diagnostic/stage0_match_players.parquet")
print("match_players columns:", list(mp.columns))

g1 = m[m["tournament_id"].eq("2024-2847")].copy()
print(len(g1))
cols = ["match_id", "round", "match_num", "player_a_id", "player_b_id", "a_won", "score", "status", "level",
        "qualifying", "evaluation", "surface", "indoor", "draw_size", "source_row", "source_file", "tml_link"]
print(g1.sort_values("source_row")[cols].to_string())

# names
idcols = [c for c in mp.columns if "name" in c.lower()]
print(idcols)
