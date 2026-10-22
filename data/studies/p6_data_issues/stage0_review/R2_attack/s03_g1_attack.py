"""R2 (attack) scratch: G1 attacks. Read-only; prints only.

1. TML's raw 2024 Challenger file: every Tenerife row (all three ids are named 'Tenerife 1', dated 20240121).
2. Duplicate test: the 31 pairs against Sackmann's 2024-9623 and 2024-2839 rows (unordered pair, score).
3. Bracket test: the 31 rows form one draw (every R16..F player won the round before).
4. TML's dating convention for 2024 Challengers vs Sackmann's dates (same tourney_id), and weekdays.
5. Clashes: every other Stage 0 match of the 31's players, Jan-Mar 2024.
"""
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 600)
pd.set_option("display.max_colwidth", 45)

m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet")
mp = pd.read_parquet("data/studies/predictability_diagnostic/stage0_match_players.parquet",
                     columns=["match_id", "player_id", "player_name"])
names = mp.drop_duplicates("player_id").set_index("player_id")["player_name"]

def nm(pid):
    return names.get(pid, pid)

g1 = m[m["tournament_id"].eq("2024-2847")].copy()
g1["pair"] = g1.apply(lambda r: frozenset([r.player_a_id, r.player_b_id]), axis=1)

# ---- 2. duplicates against Sackmann's other Tenerife 2024 editions (and anything else in Stage 0)
m["pair"] = [frozenset([a, b]) for a, b in zip(m["player_a_id"], m["player_b_id"])]
others = m[~m["tournament_id"].eq("2024-2847") & m["pair"].isin(set(g1["pair"]))]
print("== 2. other Stage 0 meetings of the 31 pairs (any event, any year) ==")
print(others[["match_id", "tournament_name", "tournament_date", "round", "score", "source"]].sort_values("tournament_date").to_string())
o24 = others[pd.to_datetime(others["tournament_date"]).dt.year.eq(2024)]
print("same pair in 2024 elsewhere:", len(o24))

# ---- 3. bracket consistency
print("\n== 3. bracket ==")
rnd = ["R32", "R16", "QF", "SF", "F"]
winners = {}
for r in rnd:
    rows = g1[g1["round"].eq(r)]
    w = set(rows.apply(lambda x: x.player_a_id if x.a_won else x.player_b_id, axis=1))
    players = set(rows["player_a_id"]) | set(rows["player_b_id"])
    print(r, "matches", len(rows), "players", len(players), "winners", len(w))
    if r != "R32":
        prev = winners[rnd[rnd.index(r) - 1]]
        print("   players who did not win the previous round:", [nm(p) for p in players - prev])
    winners[r] = w
allp = set(g1["player_a_id"]) | set(g1["player_b_id"])
print("distinct players:", len(allp))

# ---- 4. TML dating convention for 2024 Challengers
print("\n== 4. TML 2024 Challenger dates vs Sackmann ==")
raw = pd.read_csv("data/raw/public_dump/tennis_my_life/2024_challenger.csv", dtype=str, keep_default_na=False)
raw["td"] = pd.to_datetime(raw["tourney_date"], format="%Y%m%d", errors="coerce")
ed = raw.groupby(["tourney_id", "tourney_name"]).agg(td=("td", "min"), n=("td", "size"), tdmax=("td", "max")).reset_index()
print("TML editions:", len(ed), " weekday of TML date:", ed["td"].dt.day_name().value_counts().to_dict())
sk = m[m["source"].eq("sackmann") & m["level"].eq("CH")].groupby("tournament_id").agg(
    sname=("tournament_name", "first"), sdate=("tournament_date", "min")).reset_index()
j = ed.merge(sk, left_on="tourney_id", right_on="tournament_id", how="left")
j["diff"] = (j["td"] - j["sdate"]).dt.days
print("TML date minus Sackmann date (days), editions with a Sackmann id:")
print(j["diff"].value_counts(dropna=False).sort_index().to_string())
print(j[j["diff"].ne(0) & j["diff"].notna()].to_string())
# TML-only Challenger editions in Stage 0, 2024: weekday of the date Stage 0 holds
t0 = m[m["source"].eq("tml") & m["level"].eq("CH") & m["year"].eq(2024)]
t0e = t0.groupby(["tournament_id", "tournament_name"])["tournament_date"].min().reset_index()
print("\nStage 0 TML-only CH 2024 editions:", len(t0e), t0e["tournament_date"].dt.day_name().value_counts().to_dict())
print(t0e.to_string())

# ---- 5. clashes: other Stage 0 matches of the 31's players, Jan-Mar 2024
print("\n== 5. other Stage 0 matches of the 31's players, 2024-01-01..2024-03-31 ==")
win = m[(m["tournament_date"] >= "2023-12-25") & (m["tournament_date"] <= "2024-03-31")
        & ~m["tournament_id"].eq("2024-2847")]
rows = []
for p in sorted(allp, key=nm):
    q = win[(win["player_a_id"].eq(p)) | (win["player_b_id"].eq(p))].sort_values(["tournament_date", "round_order"])
    for _, r in q.iterrows():
        opp = r.player_b_id if r.player_a_id == p else r.player_a_id
        won = r.a_won if r.player_a_id == p else (not r.a_won)
        rows.append([nm(p), str(r.tournament_date.date()), r.tournament_id, r.tournament_name, r["round"],
                     "W" if won else "L", nm(opp), r.score, r.source])
out = pd.DataFrame(rows, columns=["player", "s0_date", "tid", "event", "round", "res", "opp", "score", "src"])
print(out.to_string())
out.to_csv("data/studies/p6_data_issues/stage0_review/R2_attack/g1_players_jan_mar_2024.csv", index=False)

# the 31 players' 2847 path for reference
print("\n== the 31 rows with names ==")
g1["a"] = g1["player_a_id"].map(nm)
g1["b"] = g1["player_b_id"].map(nm)
print(g1.sort_values("source_row")[["source_row", "round", "a", "b", "a_won", "score"]].to_string())
