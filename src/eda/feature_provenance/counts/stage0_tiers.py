# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""Q2/Q3/Q4/Q5 Stage 0 tables: counts by tour x level x season, box scores, tennis-data odds, Pinnacle.
No label column is read. Run from the repo root: ./python.sh <this file>
"""
import pandas as pd

S0 = "data/studies/predictability_diagnostic/stage0_matches.parquet"
ODDS = "data/studies/predictability_diagnostic/stage1_odds.parquet"
FRAME = "data/studies/surface_rating_race/model/model_frame.parquet"
m = pd.read_parquet(S0, columns=["match_id", "tour", "year", "level", "qualifying", "status", "tournament_date", "has_box"])
o = pd.read_parquet(ODDS, columns=["match_id", "p_avg_a", "p_ps_a"])
m = m.merge(o, on="match_id", how="left")
m["odds"], m["pin"] = m["p_avg_a"].notna(), m["p_ps_a"].notna()
m["in_frame"] = m["match_id"].isin(set(pd.read_parquet(FRAME, columns=["match_id"])["match_id"]))
m = m[m["status"].isin(["completed", "retired"])]
m["tier"] = m["level"].where(~m["qualifying"], m["level"].map(
    {"GS": "GS-Q", "T1000": "tour-Q", "T500": "tour-Q", "T250": "tour-Q", "FIN": "tour-Q", "CH": "CH-Q", "ITF": "ITF-Q"}))
m["tier"] = m["tier"].replace({"GS": "main", "FIN": "main", "T1000": "main", "T500": "main", "T250": "main"})


def table(d, by):
    g = d.groupby(by).agg(matches=("match_id", "size"), box=("has_box", "sum"), odds=("odds", "sum"),
                          pinnacle=("pin", "sum"), in_frame=("in_frame", "sum"))
    return g


pd.set_option("display.width", 250)
print("== 2010-2012 warm-up, completed+retired, by tour x tier x season")
print(table(m[m["year"] <= 2012], ["tour", "tier", "year"]).to_string())
print("\n== lower tiers 2013-2026 by tour x tier x season (matches, full box scores)")
low = m[m["tier"].isin(["CH", "CH-Q", "ITF", "ITF-Q", "tour-Q", "GS-Q", "TEAM"]) & (m["year"] >= 2013)]
t = low.groupby(["tour", "tier", "year"]).agg(matches=("match_id", "size"), box=("has_box", "sum")).unstack("year")
print(t.to_string())
print("\n== main-tour main draws: Pinnacle coverage by tour x season (linked tennis-data rows with coherent PS)")
mm = m[m["tier"].eq("main")]
print(mm.groupby(["year", "tour"]).agg(matches=("match_id", "size"), odds=("odds", "sum"), pinnacle=("pin", "sum"),
                                       in_frame=("in_frame", "sum")).unstack("tour").to_string())
print("\n== main-tour main draws 2013-2026 with odds but NOT in the model frame, by tour x season")
nf = mm[(mm["year"] >= 2013) & mm["odds"] & ~mm["in_frame"]]
print(nf.groupby(["tour", "year"]).size().to_string())
print("\n== WTA main-tour main draws: box-score share by season (2013-2018)")
w = mm[(mm["tour"] == "wta") & mm["year"].between(2010, 2019)]
print(w.groupby("year")["has_box"].agg(["sum", "size", "mean"]).round(3).to_string())
