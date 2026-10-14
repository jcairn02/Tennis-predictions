# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""Misc counts (read-only; no label column read). Needs postframe_main.parquet from q1_postframe.py.
Run from the repo root: ./python.sh <this file>
(a) serve speeds for post-frame main-tour matches; (b) which post-frame matches sat in the 30 Sep build's study frames;
(c) tennis-data raw rows with Pinnacle / OddsPortal average / Betfair Exchange by season, and BFE after 28 Jul."""
from pathlib import Path
import pandas as pd

SCR = "data/studies/feature_provenance/counts/"
post = pd.read_parquet(SCR + "postframe_main.parquet")

# (a) serve speeds: both players with a reading in the speed panel (y = speed, not a result)
for f in ["data/studies/serve_speed_tabpfn/speed_panel.parquet", "data/studies/serve_speed_tabpfn/live/speed_panel_live.parquet"]:
    p = pd.read_parquet(f, columns=["match_id", "side", "y"])
    g = p[p["y"].notna()].groupby("match_id")["side"].nunique()
    post["spd_both"] = post["match_id"].isin(set(g[g == 2].index))
    print(f, "\n", post.groupby(["tour", "level"])["spd_both"].agg(["sum", "size"]).to_string())

# (b) 30 Sep build membership (Stage 1 baselines = 30 Sep Stage 0; Stage 4 and tabpfn_thinking frames hold labels)
b1 = set(pd.read_parquet("data/studies/predictability_diagnostic/stage1_baselines.parquet", columns=["match_id"])["match_id"])
s4 = set(pd.read_parquet("data/studies/predictability_diagnostic/stage4_features.parquet", columns=["match_id"])["match_id"])
tt = set(pd.read_parquet("data/studies/tabpfn_thinking/test_predictions.parquet", columns=["match_id"])["match_id"])
post["in_30sep"], post["in_stage4"], post["in_thinking"] = (post["match_id"].isin(b1), post["match_id"].isin(s4),
                                                            post["match_id"].isin(tt))
print(post.groupby(["tour", "in_30sep", "in_stage4", "in_thinking"]).size().to_string())
print(post[~post["in_30sep"]].groupby(["tour", "tournament_name"]).agg(n=("match_id", "size"), td_avg=("td_avg", "sum")).to_string())

# (c) tennis-data raw rows by season with both quotes > 1
rows = []
for f in Path("data/dump/odds/tennis_data_couk").glob("*/*/*.parquet"):
    x = pd.read_parquet(f)
    def both(b):
        return int(((pd.to_numeric(x.get(f"{b}W"), errors="coerce") > 1) & (pd.to_numeric(x.get(f"{b}L"), errors="coerce") > 1)).sum()) \
            if f"{b}W" in x and f"{b}L" in x else 0
    rows.append({"tour": f.parts[-3], "season": int(f.stem), "rows": len(x), "PS": both("PS"), "Avg": both("Avg"), "BFE": both("BFE")})
print(pd.DataFrame(rows).groupby(["season", "tour"]).sum(numeric_only=True).unstack("tour").to_string())
x = pd.concat([pd.read_parquet(f).assign(tour=f.parts[-3]) for f in Path("data/dump/odds/tennis_data_couk").glob("*/*/2026.parquet")])
x["Date"] = pd.to_datetime(x["Date"], errors="coerce")
x = x[x["Date"] > "2026-07-28"]
bfe = (pd.to_numeric(x["BFEW"], errors="coerce") > 1) & (pd.to_numeric(x["BFEL"], errors="coerce") > 1)
print("tennis-data rows after 28 Jul:", x.groupby("tour").size().to_dict(), "with BFE:", bfe.groupby(x["tour"]).sum().to_dict())
