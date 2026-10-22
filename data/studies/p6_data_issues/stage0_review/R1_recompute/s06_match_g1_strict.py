"""R1 recompute, step 6: strict re-match of the 31 rows (surname-level names, exact games and tiebreaks),
plus controls: Sackmann's 2024 Tenerife editions matched the same way, and whether the 31 matches exist
anywhere else in Sackmann or Stage 0. Local files only."""
import re
import unicodedata
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 500)
OUT = "data/studies/p6_data_issues/stage0_review/R1_recompute/"


def toks(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", " ", s.lower().replace("-", " "))
    return [t for t in s.split() if len(t) >= 2 and t not in ("jr", "sr")]


def same(a, b):
    """Same player: equal token sets, or they share a token that is not the first token of both
    (so a shared first name alone never matches)."""
    A, B = toks(a), toks(b)
    if set(A) == set(B):
        return True
    shared = set(A) & set(B)
    return any(not (t == A[0] and t == B[0]) and len(t) >= 3 for t in shared)


def games(score):
    """'7-6(6) 1-0 RET' -> ('7-6 1-0', '6')  (games, tiebreak loser points)"""
    s = str(score).upper().replace("RET.", "").replace("RET", "").replace("W/O", "").strip()
    tb = re.findall(r"\((\d+)\)", s)
    g = re.sub(r"\(\d+\)", "", s)
    return " ".join(g.split()), ",".join(tb)


tml = pd.read_csv("data/raw/public_dump/tennis_my_life/2024_challenger.csv", low_memory=False)
tml["source_row"] = tml.index + 1

tl = pd.read_parquet("data/dump/points/tennislive/listed.parquet")
tl = tl[tl["event_name"].astype(str).str.contains("Tenerife", case=False)
        & tl["start_utc"].astype(str).str.startswith("2024") & (tl["discipline"] == "singles")].copy()
tl["w_name"] = tl.apply(lambda r: r["player1_name"] if str(r["winner_side"]) == "1" else r["player2_name"], axis=1)
tl["l_name"] = tl.apply(lambda r: r["player2_name"] if str(r["winner_side"]) == "1" else r["player1_name"], axis=1)
tl["edition"] = tl["event_name"] + " [" + tl["draw"] + "]"

ss = pd.read_parquet("data/dump/points/sofascore_editions/events.parquet")
ss = ss[ss["unique_tournament_name"].astype(str).str.contains("Tenerife", case=False)
        & ss["start_utc"].astype(str).str.startswith("2024") & (ss["doubles"].astype(str) == "FALSE")].copy()


def ss_games(r):
    w = "home" if str(r["winner_code"]) == "1" else "away"
    l = "away" if w == "home" else "home"
    out, tbs = [], []
    for i in range(1, 6):
        a, b = r.get(f"{w}_set{i}"), r.get(f"{l}_set{i}")
        if pd.isna(a) or pd.isna(b) or str(a) == "" or str(b) == "":
            break
        out.append(f"{a}-{b}")
        ta, tb_ = r.get(f"{w}_tb{i}"), r.get(f"{l}_tb{i}")
        if not (pd.isna(ta) or str(ta) == ""):
            tbs.append(str(min(int(ta), int(tb_))))
    return " ".join(out), ",".join(tbs)


ss["w_name"] = ss.apply(lambda r: r["home_name"] if str(r["winner_code"]) == "1" else r["away_name"], axis=1)
ss["l_name"] = ss.apply(lambda r: r["away_name"] if str(r["winner_code"]) == "1" else r["home_name"], axis=1)
ss[["g", "tb"]] = ss.apply(lambda r: pd.Series(ss_games(r)), axis=1)
ss["edition"] = ss["tournament_name"]


def match_rows(rows, wn, ln, sc, label):
    recs = []
    for _, r in rows.iterrows():
        g, tb = games(r[sc])
        for src_name, src in [("tennislive", tl), ("sofascore", ss)]:
            hits = src[src.apply(lambda x: (same(x["w_name"], r[wn]) and same(x["l_name"], r[ln]))
                                 or (same(x["w_name"], r[ln]) and same(x["l_name"], r[wn])), axis=1)]
            if len(hits) == 0:
                recs.append({"set": label, "key": r["key"], "src": src_name, "n_hits": 0})
            for _, h in hits.iterrows():
                if src_name == "tennislive":
                    hg, htb = games(h["score"])
                else:
                    hg, htb = h["g"], h["tb"]
                recs.append({"set": label, "key": r["key"], "round": r["round"], "winner": r[wn], "loser": r[ln],
                             "score": r[sc], "src": src_name, "n_hits": len(hits), "edition": h["edition"],
                             "start_utc": h["start_utc"], "play_day": str(h["start_utc"])[:10],
                             "winner_same": same(h["w_name"], r[wn]), "games_same": hg == g,
                             "tb_same": (htb == tb) if src_name == "tennislive" or htb else None,
                             "src_winner": h["w_name"], "src_loser": h["l_name"], "src_games": hg, "src_tb": htb})
    return pd.DataFrame(recs)


g1 = tml[tml["tourney_id"] == "2024-2847"].copy()
g1["key"] = g1["source_row"]
r1 = match_rows(g1, "winner_name", "loser_name", "score", "G1 TML 2024-2847")
r1.to_csv(OUT + "g1_play_days_strict.csv", index=False)
print(r1.to_string())
print("\nG1 summary by source/edition:")
print(r1.groupby(["src", r1["edition"].fillna("NO MATCH")]).agg(rows=("key", "nunique"), hits=("key", "size"),
      winner_same=("winner_same", "sum"), games_same=("games_same", "sum"), first=("play_day", "min"),
      last=("play_day", "max")).to_string())
print("tiebreaks agree (tennislive):", r1[(r1.src == "tennislive")]["tb_same"].value_counts(dropna=False).to_dict())
print("tiebreaks agree (sofascore, where given):", r1[(r1.src == "sofascore")]["tb_same"].value_counts(dropna=False).to_dict())
print("multi-hit rows:", r1[r1["n_hits"] > 1][["src", "key"]].drop_duplicates().values.tolist())
pd_by_round = r1.groupby(["src", "round"])["play_day"].agg(["min", "max", "nunique"])
print(pd_by_round.to_string())

# ---- Controls: Sackmann's 2024 Tenerife editions
sk = pd.read_parquet("data/dump/matches/sackmann_archive/atp/atp_matches_qual_chall_2024.parquet")
print("\nSackmann qual_chall 2024 columns:", sk.columns.tolist()[:12])
skt = sk[sk["tourney_name"].astype(str).str.contains("Tenerife", case=False)]
print(skt.groupby(["tourney_id", "tourney_name", "tourney_date"]).size().to_string())
for tid in sorted(skt["tourney_id"].unique()):
    e = skt[skt["tourney_id"] == tid].copy()
    e["key"] = e["tourney_id"] + "#" + e["match_num"].astype(str)
    rr = match_rows(e, "winner_name", "loser_name", "score", f"Sackmann {tid}")
    print(f"\nControl Sackmann {tid} ({len(e)} rows): finals:",
          e[e["round"] == "F"][["winner_name", "loser_name", "score"]].values.tolist())
    print(rr.groupby(["src", rr["edition"].fillna("NO MATCH")]).agg(rows=("key", "nunique"), hits=("key", "size"),
          winner_same=("winner_same", "sum"), games_same=("games_same", "sum"), first=("play_day", "min"),
          last=("play_day", "max")).to_string())

# ---- Are the 31 matches anywhere in Sackmann 2024 (any tournament)?
def pairkey(a, b):
    return tuple(sorted([" ".join(sorted(toks(a))), " ".join(sorted(toks(b)))]))


skp = set(sk.apply(lambda r: pairkey(r["winner_name"], r["loser_name"]), axis=1))
g1p = g1.apply(lambda r: pairkey(r["winner_name"], r["loser_name"]), axis=1)
print("\nG1 pairs found anywhere in Sackmann qual_chall 2024 (exact names):", int(g1p.isin(skp).sum()), "of", len(g1p))
print(g1[g1p.isin(skp)][["winner_name", "loser_name", "round", "score"]].to_string())
# who/where
for _, r in g1[g1p.isin(skp)].iterrows():
    k = pairkey(r["winner_name"], r["loser_name"])
    hit = sk[sk.apply(lambda x: pairkey(x["winner_name"], x["loser_name"]) == k, axis=1)]
    print(hit[["tourney_id", "tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"]].to_string())

# ---- Stage 0: same player-id pairs, Jan-Mar 2024, outside 2024-2847
s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tournament_id", "tournament_name", "tournament_date", "round", "score",
                              "player_a_id", "player_b_id", "source"])
s0 = s0[(s0["tournament_date"] >= "2023-12-01") & (s0["tournament_date"] <= "2024-04-30")]
s0["pair"] = s0.apply(lambda r: tuple(sorted([r["player_a_id"], r["player_b_id"]])), axis=1)
gp = set(s0[s0["tournament_id"] == "2024-2847"]["pair"])
dup = s0[(s0["tournament_id"] != "2024-2847") & s0["pair"].isin(gp)]
print("\nStage 0 rows Dec 2023-Apr 2024 with a G1 player pair, outside 2024-2847:", len(dup))
print(dup[["match_id", "tournament_name", "tournament_date", "round", "score", "source"]].to_string())
