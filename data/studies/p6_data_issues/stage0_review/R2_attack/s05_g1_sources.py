"""R2 (attack) scratch: G1 against Sackmann's staged 2024 files, TennisLive's listings and SofaScore's events.
Read-only; prints only. No network."""
import glob
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 45)

# --- Sackmann's staged files: any Tenerife 2024 edition (main, challenger, qualifying)
print("== Sackmann staged: Tenerife 2024 ==")
for f in sorted(glob.glob("data/dump/matches/sackmann_archive/atp/*2024*.parquet")):
    d = pd.read_parquet(f)
    if "tourney_name" not in d.columns:
        continue
    t = d[d["tourney_name"].astype(str).str.contains("Tenerife", case=False)]
    if len(t):
        print(f, t.groupby(["tourney_id", "tourney_name", "tourney_date"]).size().to_dict())

# --- TennisLive listings
tl = pd.read_parquet("data/dump/points/tennislive/listed.parquet")
print("\n== TennisLive listed columns ==", list(tl.columns))
ten = tl[tl["event_name"].astype(str).str.contains("Tenerife", case=False)]
ten = ten.copy()
ten["start_utc"] = pd.to_datetime(ten["start_utc"], utc=True, errors="coerce")
ten = ten[(ten["start_utc"] >= "2024-01-01") & (ten["start_utc"] < "2024-04-01")]
print(ten.groupby("event_name")["start_utc"].agg(["min", "max", "size"]))
t3 = ten[ten["event_name"].astype(str).str.contains("3")]
cols = ["event_name", "start_utc", "start_timestamp", "stage", "round", "discipline", "player1_name", "player2_name",
        "winner_side", "score", "end_reason", "played", "event_id", "match_id"]
t3[cols].to_csv("data/studies/p6_data_issues/stage0_review/R2_attack/tennislive_tenerife3_2024.csv", index=False)
print(ten.groupby(["event_name", "discipline", "stage"], dropna=False).size())
s = t3[~t3["discipline"].astype(str).str.contains("double", case=False)]
print(s.sort_values(["start_utc", "round"])[cols].to_string())
