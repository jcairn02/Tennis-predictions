# Counting script of the feature-provenance study (8 Oct 2026), written by the session's data-availability
# audit and copied here with its output folder moved to data/studies/feature_provenance/counts/.
# Counts only: no result column is read for any match after 28 Jul 2026.
"""Q1: Stage 0 main-tour singles matches after the model frame (read-only; no label column is read).

Run from the repo root:  ./python.sh <this file>
"""
import pandas as pd

S0 = "data/studies/predictability_diagnostic/stage0_matches.parquet"
ODDS = "data/studies/predictability_diagnostic/stage1_odds.parquet"
FRAME = "data/studies/surface_rating_race/model/model_frame.parquet"
MAIN = ["GS", "FIN", "T1000", "T500", "T250"]

cols = ["match_id", "tour", "year", "level", "qualifying", "evaluation", "status", "tournament_date",
        "tournament_name", "has_box", "source"]          # a_won deliberately NOT read
m = pd.read_parquet(S0, columns=cols)
frame_ids = set(pd.read_parquet(FRAME, columns=["match_id"])["match_id"])

print("Stage 0 rows:", len(m), " tournament_date max by tour:")
print(m.groupby("tour")["tournament_date"].max())

main = m[m["level"].isin(MAIN) & ~m["qualifying"]].copy()
main["in_frame"] = main["match_id"].isin(frame_ids)
post = main[main["tournament_date"] > "2026-07-28"].copy()
wk27 = main[(main["tournament_date"] >= "2026-07-27") & (main["tournament_date"] <= "2026-07-28")]
print("\nweek of 27 Jul (dates 27-28 Jul), main tour, by tour x in_frame x status:")
print(pd.crosstab([wk27["tour"], wk27["in_frame"]], wk27["status"]))

print("\nPOST-FRAME (tournament_date > 2026-07-28), main-tour main draws:", len(post),
      "| in frame:", int(post["in_frame"].sum()))
print("status:\n", pd.crosstab(post["tour"], post["status"], margins=True))
post["month"] = post["tournament_date"].dt.strftime("%Y-%m")
ev = post[post["status"].isin(["completed", "retired"])]
print("\ncompleted+retired by tour x level x month:")
print(pd.crosstab([ev["tour"], ev["level"]], ev["month"], margins=True))
print("\nlast tournament_date by tour:", ev.groupby("tour")["tournament_date"].max().to_dict())
print("events (tournament_name, date) after 28 Jul, by tour:")
print(ev.groupby(["tour", "tournament_date", "tournament_name", "level"]).size().to_string())

# box scores
print("\nhas_box among completed+retired post-frame:")
print(pd.crosstab([ev["tour"], ev["level"]], ev["has_box"], margins=True))

# tennis-data odds (Stage 1 link of 7 Oct)
o = pd.read_parquet(ODDS, columns=["match_id", "link", "td_date", "p_avg_a", "p_ps_a", "b365_a", "b365_b"])
ev = ev.merge(o, on="match_id", how="left")
ev["td_avg"] = ev["p_avg_a"].notna()
ev["td_ps"] = ev["p_ps_a"].notna()
ev["td_b365"] = ev["b365_a"].notna() & ev["b365_b"].notna()
print("\ntennis-data coherent average odds / Pinnacle / Bet365 among completed+retired post-frame:")
print(ev.groupby(["tour", "month"])[["td_avg", "td_ps", "td_b365"]].agg(["sum", "size"]).to_string())
print("totals:", ev.groupby("tour")[["td_avg", "td_ps", "td_b365"]].sum().to_dict(), "of", ev.groupby("tour").size().to_dict())
print("last td_date with avg odds:", ev.loc[ev["td_avg"]].groupby("tour")["td_date"].max().to_dict())

ev[["match_id", "tour", "level", "month", "tournament_date", "tournament_name", "status", "has_box",
    "td_avg", "td_ps", "td_b365"]].to_parquet(
    "data/studies/feature_provenance/counts/postframe_main.parquet", index=False)
