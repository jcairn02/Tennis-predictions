"""R1 recompute, step 7: the leak-proof clock's windows for the 31 rows and the 2 G2 rows (read-only)."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 500)
OUT = "data/studies/p6_data_issues/stage0_review/R1_recompute/"

tm = pd.read_parquet("data/studies/match_timing/timing.parquet")
print(tm.shape)
print(tm.dtypes.to_string())

g1 = pd.read_csv(OUT + "g1_play_days_strict.csv")
g1 = g1[g1["src"] == "sofascore"][["key", "round", "winner", "loser", "play_day", "start_utc"]].rename(columns={"key": "source_row"})
tl = pd.read_csv(OUT + "g1_play_days_strict.csv")
tl = tl[tl["src"] == "tennislive"][["key", "play_day"]].rename(columns={"key": "source_row", "play_day": "tl_day"})
g1 = g1.merge(tl, on="source_row")
assert (g1["play_day"] == g1["tl_day"]).all(), "TennisLive and SofaScore disagree on a play day"

s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tournament_id", "tournament_date", "source_row", "round"])
ids = s0[s0["tournament_id"] == "2024-2847"][["match_id", "source_row"]]
g1 = g1.merge(ids, on="source_row")
t = tm[tm["match_id"].isin(g1["match_id"])].copy()
print("\ntiming rows for G1:", len(t))
EPOCH = pd.Timestamp("1970-01-01")
day = lambda x: (EPOCH + pd.to_timedelta(x, unit="D")).dt.strftime("%Y-%m-%d") if hasattr(x, "dt") or True else None
for c in [c for c in t.columns if c in ("es", "lf", "best", "exact_lo", "exact_hi", "anchor", "day_best", "best_day")]:
    pass
g1 = g1.merge(t.drop(columns=["round"]), on="match_id", how="left")
g1["play_day_n"] = (pd.to_datetime(g1["play_day"]) - EPOCH).dt.days
g1["es_date"] = (EPOCH + pd.to_timedelta(g1["es"], unit="D")).dt.strftime("%Y-%m-%d")
g1["lf_date"] = (EPOCH + pd.to_timedelta(g1["lf"], unit="D")).dt.strftime("%Y-%m-%d")
g1["counts_from"] = (EPOCH + pd.to_timedelta(g1["lf"] + 1, unit="D")).dt.strftime("%Y-%m-%d")
g1["days_early"] = g1["play_day_n"] - (g1["lf"] + 1)
g1["window_holds_play_day"] = (g1["es"] <= g1["play_day_n"]) & (g1["play_day_n"] <= g1["lf"])
show = ["source_row", "match_id", "round", "play_day", "es_date", "lf_date", "counts_from", "days_early", "window_holds_play_day"]
extra = ["start", "anchor", "obs", "width_days", "exact", "window_basis", "best_source", "sources", "rejected_links"]
print(g1[show + extra].sort_values("source_row").to_string())
print("\nlf range:", g1["lf_date"].min(), g1["lf_date"].max(), "| es range:", g1["es_date"].min(), g1["es_date"].max())
print("days between window end (lf) and play day: min", int((g1["play_day_n"] - g1["lf"]).min()),
      "max", int((g1["play_day_n"] - g1["lf"]).max()))
print("windows holding the play day:", int(g1["window_holds_play_day"].sum()), "of", len(g1))
g1[show].to_csv(OUT + "g1_clock_windows.csv", index=False)

# G2
g2ids = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
t2 = tm[tm["match_id"].isin(g2ids)].copy()
t2["es_date"] = (EPOCH + pd.to_timedelta(t2["es"], unit="D")).dt.strftime("%Y-%m-%d")
t2["lf_date"] = (EPOCH + pd.to_timedelta(t2["lf"], unit="D")).dt.strftime("%Y-%m-%d")
print("\nG2 timing rows:")
print(t2.T.to_string())
