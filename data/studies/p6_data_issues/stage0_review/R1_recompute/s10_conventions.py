"""R1 recompute, step 10: conventions. (a) How Stage 0 dates Slam qualifying in other years (main-draw date or own date);
(b) which weekday Stage 0's ATP Challenger dates fall on (is the Monday the convention?); (c) other TML-only Stage 0
rows that carry TML's 2024-01-21. Read-only."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tour", "year", "level", "qualifying", "tournament_id", "tournament_name",
                              "tournament_date", "source", "tml_link"])

q = s0[(s0["tour"] == "atp") & (s0["level"] == "GS")]
g = q.groupby(["year", "tournament_id", "tournament_name", "qualifying", "tournament_date"]).size().reset_index(name="n")
print("ATP Slam rows, Australian Open 2019-2023 (main and qualifying):")
print(g[g["tournament_name"].str.contains("Australian|Aus Open", case=False) & g["year"].between(2019, 2023)].to_string())

ch = s0[(s0["tour"] == "atp") & (s0["level"] == "CH") & (s0["year"].between(2022, 2025))]
ev = ch.drop_duplicates(["tournament_id", "tournament_date"])
print("\nATP Challenger editions 2022-2025 by weekday of tournament_date and source:")
print(pd.crosstab(ev["tournament_date"].dt.day_name(), ev["source"]).to_string())

x = s0[(s0["tournament_date"] == "2024-01-21")]
print("\nStage 0 rows dated 2024-01-21, by event and source:")
print(x.groupby(["tour", "level", "tournament_id", "tournament_name", "source"]).size().to_string())
