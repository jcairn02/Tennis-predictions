"""R1 recompute, step 8:
(a) G2: how Stage 0 and the clock hold the rest of the AO 2021 men's qualifying draw; Sackmann's and TML's rows.
(b) G1: the later Stage 0 matches of the same players that read the 31 results early (my own definition).
Read-only."""
import pandas as pd
import numpy as np

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 500)
OUT = "data/studies/p6_data_issues/stage0_review/R1_recompute/"
EPOCH = pd.Timestamp("1970-01-01")
d2s = lambda x: (EPOCH + pd.to_timedelta(x, unit="D")).strftime("%Y-%m-%d")

s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet")
tm = pd.read_parquet("data/studies/match_timing/timing.parquet",
                     columns=["match_id", "anchor", "es", "lf", "exact", "window_basis", "sources", "n_sources"])

# ---------------- (a) G2 context
q = s0[(s0["tour"] == "atp") & (s0["year"] == 2021) & s0["qualifying"] & (s0["level"] == "GS")]
q = q[q["tournament_date"] <= "2021-02-28"]
print("ATP 2021 Slam-qualifying rows in Stage 0 up to Feb 2021, by event:")
print(q.groupby(["tournament_id", "tournament_name", "tournament_date", "source", "tml_link"], dropna=False).size().to_string())
qq = q.merge(tm, on="match_id", how="left")
print("\nTheir clock windows by event / round / basis:")
qq["es_d"] = qq["es"].map(d2s)
qq["lf_d"] = qq["lf"].map(d2s)
print(qq.groupby(["tournament_name", "tournament_date", "round", "window_basis", "exact"], dropna=False).agg(
    n=("match_id", "size"), es_min=("es_d", "min"), es_max=("es_d", "max"), lf_min=("lf_d", "min"),
    lf_max=("lf_d", "max")).to_string())

# Stage 0 rows of the same event key as the two G2 rows (tour|tournament_id|tournament_date)
ev = s0[(s0["tour"] == "atp") & (s0["tournament_id"] == "2021-580")]
print("\nStage 0 rows with tournament_id 2021-580 by date / qualifying / source:")
print(ev.groupby(["tournament_name", "tournament_date", "qualifying", "source"]).size().to_string())

# Sackmann's staged 2021 qual_chall file: the AO qualifying draw
sk = pd.read_parquet("data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2021.parquet")
ao = sk[sk["tourney_name"].astype(str).str.contains("Aus|Australian", case=False)]
print("\nSackmann qual_chall 2021, AO-qualifying-like events:")
print(ao.groupby(["tourney_id", "tourney_name", "tourney_date", "tourney_level"]).size().to_string())
print(ao["round"].value_counts().to_string())
for nm in ["Kudla", "Sweeny", "Cerundolo", "Vilella"]:
    h = ao[ao["winner_name"].astype(str).str.contains(nm) | ao["loser_name"].astype(str).str.contains(nm)]
    print(f"\nSackmann AO-quali rows with {nm}:")
    print(h[["tourney_id", "tourney_name", "tourney_date", "round", "match_num", "winner_name", "loser_name", "score"]].to_string())

# TML's quali file: the two players' other rounds
tml = pd.read_csv("data/raw/public_dump/tennis_my_life/atp_quali/2021_atp_quali.csv", low_memory=False)
tml["source_row"] = tml.index + 1
for nm in ["Kudla", "Sweeny", "Cerundolo", "Vilella"]:
    h = tml[(tml["tourney_id"] == "2021-580") & (tml["winner_name"].astype(str).str.contains(nm) | tml["loser_name"].astype(str).str.contains(nm))]
    print(f"\nTML AO-quali rows with {nm}:")
    print(h[["source_row", "tourney_id", "tourney_name", "tourney_date", "round", "match_num", "winner_name", "loser_name", "score"]].to_string())

# The two G2 player ids: their Stage 0 matches Dec 2020 - Mar 2021, with windows
g2 = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
pl = set(s0.loc[s0["match_id"].isin(g2), ["player_a_id", "player_b_id"]].values.ravel())
near = s0[(s0["player_a_id"].isin(pl) | s0["player_b_id"].isin(pl)) & s0["tournament_date"].between("2020-12-01", "2021-03-15")]
near = near.merge(tm, on="match_id", how="left")
near["es_d"] = near["es"].map(d2s)
near["lf_d"] = near["lf"].map(d2s)
print("\nStage 0 matches of the four G2 players, Dec 2020 - mid Mar 2021:")
print(near[["match_id", "tournament_name", "tournament_date", "round", "score", "source", "es_d", "lf_d", "window_basis",
            "exact"]].sort_values("es_d").to_string())

# ---------------- (b) G1 readers
g1 = pd.read_csv(OUT + "g1_play_days_strict.csv")
g1 = g1[g1["src"] == "sofascore"][["key", "play_day"]].rename(columns={"key": "source_row"})
ids = s0[s0["tournament_id"] == "2024-2847"][["match_id", "source_row", "player_a_id", "player_b_id"]]
g1 = g1.merge(ids, on="source_row").merge(tm[["match_id", "es", "lf"]], on="match_id")
g1["play"] = (pd.to_datetime(g1["play_day"]) - EPOCH).dt.days
s0t = s0[["match_id", "tournament_id", "tournament_name", "tournament_date", "round", "player_a_id", "player_b_id",
          "evaluation", "level", "source"]].merge(tm[["match_id", "es", "lf"]], on="match_id")
s0t = s0t[s0t["tournament_id"] != "2024-2847"]
rows = []
for _, m in g1.iterrows():
    for pid in (m["player_a_id"], m["player_b_id"]):
        r = s0t[(s0t["player_a_id"] == pid) | (s0t["player_b_id"] == pid)]
        reads_now = r["es"] >= m["lf"] + 1                      # the current clock lets M count for R
        before_played = r["es"] <= m["play"]                   # M had not finished when R could start (its real day)
        hit = r[reads_now & before_played].copy()
        hit["g1_match"] = m["match_id"]
        hit["g1_play_day"] = m["play_day"]
        hit["g1_lf"] = d2s(m["lf"])
        hit["player"] = pid
        rows.append(hit)
rd = pd.concat(rows)
rd["es_d"] = rd["es"].map(d2s)
rd["lf_d"] = rd["lf"].map(d2s)
print("\nG1 leak readers (definition: shares a player; es_R >= lf_M + 1; es_R <= play day of M):")
print("  distinct reader matches:", rd["match_id"].nunique(), "| (reader, G1 match) pairs:", len(rd.drop_duplicates(["match_id", "g1_match"])),
      "| (reader, G1 match, player) rows:", len(rd))
print("  reader es range:", rd["es_d"].min(), rd["es_d"].max())
print("  readers by level:", rd.drop_duplicates("match_id")["level"].value_counts().to_dict(),
      "| evaluation:", rd.drop_duplicates("match_id")["evaluation"].value_counts().to_dict())
print("  G1 matches read early:", rd["g1_match"].nunique(), "| players with readers:", rd["player"].nunique())

# Alternative definition: R reads M now but would not under the fixed date (lf_M shifted by the same offset)
shift = (pd.Timestamp("2024-02-26") - pd.Timestamp("2024-01-22")).days   # anchor 22 Jan -> anchor 26 Feb
rows2 = []
for _, m in g1.iterrows():
    for pid in (m["player_a_id"], m["player_b_id"]):
        r = s0t[(s0t["player_a_id"] == pid) | (s0t["player_b_id"] == pid)]
        sel = (r["es"] >= m["lf"] + 1) & (r["es"] < m["lf"] + shift + 1)
        h = r[sel].copy()
        h["g1_match"] = m["match_id"]
        rows2.append(h)
rd2 = pd.concat(rows2)
print("\nAlternative (reads now, would not after a +35-day shift of the window):",
      "distinct readers", rd2["match_id"].nunique(), "| pairs", len(rd2.drop_duplicates(["match_id", "g1_match"])))
rd.to_csv(OUT + "g1_leak_readers_R1.csv", index=False)

# Compare with the study's table (verify, not trust)
st = pd.read_csv("data/studies/p6_data_issues/tml_misdates/clock_leak_readers.csv")
print("\nStudy's clock_leak_readers.csv:", st.shape, st.columns.tolist())
print(st.head(5).to_string())
