"""R2 (attack) scratch: G2, the two AO 2021 qualifying walkovers. Read-only; prints only. No network."""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 45)

IDS = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet")
mp = pd.read_parquet("data/studies/predictability_diagnostic/stage0_match_players.parquet",
                     columns=["match_id", "player_id", "player_name", "entry", "seed", "rank"])
names = mp.drop_duplicates("player_id").set_index("player_id")["player_name"]
nm = lambda p: names.get(p, p)

g2 = m[m["match_id"].isin(IDS)]
print("== the two rows ==")
print(g2.T.to_string())

# AO 2021 in Stage 0: every edition/name/date of the qualifying and main draw
ao = m[(m["year"].eq(2021)) & m["tour"].eq("atp") & m["level"].eq("GS")
       & (m["tournament_name"].str.contains("austral|aus open|doha|qualies", case=False, regex=True))]
print("\n== ATP GS 2021 rows named like the AO ==")
print(ao.groupby(["tournament_id", "tournament_name", "tournament_date", "qualifying", "round", "source", "status"]).size().to_string())

# the draw around the two pairs: every Stage 0 match of the 4 players, Dec 2020 - Mar 2021
pl = set(g2["player_a_id"]) | set(g2["player_b_id"])
w = m[(m["tournament_date"] >= "2020-12-01") & (m["tournament_date"] <= "2021-03-31")
      & (m["player_a_id"].isin(pl) | m["player_b_id"].isin(pl))].copy()
w["a"] = w["player_a_id"].map(nm)
w["b"] = w["player_b_id"].map(nm)
print("\n== the 4 players' Stage 0 matches, Dec 2020 - Mar 2021 ==")
print(w.sort_values(["tournament_date", "round_order"])[["match_id", "tournament_name", "tournament_date", "round", "a", "b",
                                                       "a_won", "score", "status", "source", "source_row"]].to_string())

# Sackmann's staged 2021 qualifying file: the AO 2021 qualifying draw
q = pd.read_parquet("data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2021.parquet")
aoq = q[q["tourney_name"].astype(str).str.contains("aus|australian|qualies", case=False, regex=True)]
print("\n== Sackmann qual_chall 2021, AO-like names ==")
print(aoq.groupby(["tourney_id", "tourney_name", "tourney_date", "round"]).size().to_string())
pn = {nm(p) for p in pl}
sub = aoq[aoq["winner_name"].isin(pn) | aoq["loser_name"].isin(pn)]
print(sub[["tourney_id", "tourney_name", "tourney_date", "round", "match_num", "winner_name", "loser_name", "score"]].to_string())
wo = aoq[aoq["score"].astype(str).str.contains("W/O|w/o|walkover", case=False, regex=True)]
print("Sackmann AO21 qualifying W/O rows:", len(wo))
print(wo[["round", "winner_name", "loser_name", "score"]].to_string())

# TML's raw quali file, rows 98 and 106 and every row of the same tourney
t = pd.read_csv("data/raw/public_dump/tennis_my_life/atp_quali/2021_atp_quali.csv", dtype=str, keep_default_na=False)
print("\n== TML 2021_atp_quali.csv: shape", t.shape)
t["_row1"] = range(1, len(t) + 1)
print(t.iloc[[96, 97, 98, 104, 105, 106]][["_row1", "tourney_id", "tourney_name", "tourney_date", "round", "match_num",
                                            "winner_name", "loser_name", "score"]].to_string())
tao = t[t["tourney_id"].eq("2021-580")]
print("TML 2021-580 rows by round/date:")
print(tao.groupby(["tourney_name", "tourney_date", "round"]).size().to_string())
print(tao[tao["score"].str.contains("W/O", case=False)][["_row1", "round", "winner_name", "loser_name", "score"]].to_string())
