"""R2 (attack) scratch: first look at Stage 0's Tenerife 2024 and AO 2021 qualifying rows. Read-only."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 60)

S0 = "data/studies/predictability_diagnostic/stage0_matches.parquet"
m = pd.read_parquet(S0)
print(m.shape)
print(list(m.columns))
print(m.dtypes.to_string())

ten = m[m["tournament_name"].astype(str).str.contains("Tenerife", case=False, na=False)]
ten = ten[pd.to_datetime(ten["tournament_date"]).dt.year.isin([2023, 2024, 2025])]
print(ten.groupby(["tournament_id", "tournament_name", "tournament_date", "source"], dropna=False).size())
