"""R1 recompute, step 4: the Tenerife 2024 editions in TennisLive and SofaScore (local files only)."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 500)

tl = pd.read_parquet("data/dump/points/tennislive/listed.parquet")
m = tl["event_name"].astype(str).str.contains("Tenerife", case=False) & tl["start_utc"].astype(str).str.startswith(("2023-12", "2024"))
t = tl[m].copy()
print("TennisLive rows, Tenerife, 2024:", len(t))
print(t.groupby(["event_key", "event_name", "event_url", "draw", "discipline"]).agg(
    n=("match_id", "size"), first=("start_utc", "min"), last=("start_utc", "max")).to_string())

ss1 = pd.read_parquet("data/dump/points/sofascore_editions/events.parquet")
ss2 = pd.read_parquet("data/dump/points/sofascore/events.parquet")
for name, ss in [("sofascore_editions", ss1), ("sofascore", ss2)]:
    mm = (ss["tournament_name"].astype(str).str.contains("Tenerife", case=False)
          | ss["season_name"].astype(str).str.contains("Tenerife", case=False)
          | ss["unique_tournament_name"].astype(str).str.contains("Tenerife", case=False))
    s = ss[mm & ss["start_utc"].astype(str).str.startswith(("2023-12", "2024"))]
    print("\n", name, "rows, Tenerife, 2024:", len(s))
    if len(s):
        print(s.groupby(["unique_tournament_id", "unique_tournament_name", "tournament_id", "tournament_name", "season_id",
                         "season_name", "doubles"], dropna=False).agg(
            n=("event_id", "size"), first=("start_utc", "min"), last=("start_utc", "max")).to_string())
