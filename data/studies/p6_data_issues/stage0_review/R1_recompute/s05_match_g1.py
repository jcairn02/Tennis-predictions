"""R1 recompute, step 5: match each Tenerife row (TML 2024-2847, and Sackmann's 2024-9623 / 2024-2839 as controls)
to TennisLive's and SofaScore's 2024 Tenerife editions by player pair, winner and score. Local files only."""
import re
import unicodedata
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 500)
OUT = "data/studies/p6_data_issues/stage0_review/R1_recompute/"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", " ", s.lower().replace("-", " "))
    return set(t for t in s.split() if len(t) >= 2)


def same(a, b):
    """Two names are the same player when they share a surname-like token (>=3 letters) and
    the token sets overlap by at least half of the shorter name."""
    A, B = norm(a), norm(b)
    inter = A & B
    if not any(len(t) >= 3 for t in inter):
        return False
    return len(inter) >= max(1, min(len(A), len(B)) // 2)


def canon_score(s):
    s = str(s).upper().replace("RET.", "RET").strip()
    s = re.sub(r"\s+", " ", s)
    return s


# ---- Stage 0 rows (G1 and controls) with player names from the raw TML / Sackmann files are not in Stage 0;
# take names from the raw TML file directly (rows 280-310) for G1.
tml = pd.read_csv("data/raw/public_dump/tennis_my_life/2024_challenger.csv", low_memory=False)
tml["source_row"] = tml.index + 1
g1 = tml[tml["tourney_id"] == "2024-2847"][["source_row", "round", "match_num", "winner_name", "loser_name", "score"]].copy()
assert len(g1) == 31 and g1["source_row"].min() == 280 and g1["source_row"].max() == 310

s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tournament_id", "tournament_date", "source_row", "source_file", "round",
                              "score", "player_a_id", "player_b_id", "a_won"])
s0g = s0[s0["tournament_id"] == "2024-2847"].set_index("source_row")
g1 = g1.merge(s0g[["match_id", "score"]].rename(columns={"score": "s0_score"}), left_on="source_row", right_index=True, how="left")
assert g1["match_id"].notna().all()

# ---- TennisLive singles of the three Tenerife 2024 editions (main and qualifying)
tl = pd.read_parquet("data/dump/points/tennislive/listed.parquet")
tl = tl[tl["event_name"].astype(str).str.contains("Tenerife", case=False)
        & tl["start_utc"].astype(str).str.startswith(("2024",)) & (tl["discipline"] == "singles")].copy()
tl["w_name"] = tl.apply(lambda r: r["player1_name"] if str(r["winner_side"]) == "1" else r["player2_name"], axis=1)
tl["l_name"] = tl.apply(lambda r: r["player2_name"] if str(r["winner_side"]) == "1" else r["player1_name"], axis=1)

# ---- SofaScore singles of the three editions
ss = pd.read_parquet("data/dump/points/sofascore_editions/events.parquet")
ss = ss[ss["unique_tournament_name"].astype(str).str.contains("Tenerife", case=False)
        & ss["start_utc"].astype(str).str.startswith("2024") & (ss["doubles"].astype(str) == "FALSE")].copy()


def ss_sets(r):
    out = []
    w = "home" if str(r["winner_code"]) == "1" else "away"
    l = "away" if w == "home" else "home"
    for i in range(1, 6):
        a, b = r.get(f"{w}_set{i}"), r.get(f"{l}_set{i}")
        if pd.isna(a) or pd.isna(b) or str(a) == "" or str(b) == "":
            break
        out.append(f"{a}-{b}")
    return " ".join(out)


ss["w_name"] = ss.apply(lambda r: r["home_name"] if str(r["winner_code"]) == "1" else r["away_name"], axis=1)
ss["l_name"] = ss.apply(lambda r: r["away_name"] if str(r["winner_code"]) == "1" else r["home_name"], axis=1)
ss["w_sets"] = ss.apply(ss_sets, axis=1)


def find(rows, src, wcol, lcol, cols):
    out = []
    for _, r in rows.iterrows():
        hits = src[src.apply(lambda x: (same(x[wcol], r["winner_name"]) and same(x[lcol], r["loser_name"]))
                             or (same(x[wcol], r["loser_name"]) and same(x[lcol], r["winner_name"])), axis=1)]
        out.append((r, hits[cols]))
    return out


rec = []
for r, hits in find(g1, tl, "w_name", "l_name", ["event_name", "draw", "round", "start_utc", "w_name", "l_name", "score", "end_reason"]):
    for _, h in hits.iterrows():
        rec.append({"source_row": r["source_row"], "match_id": r["match_id"], "tml_round": r["round"],
                    "tml_winner": r["winner_name"], "tml_loser": r["loser_name"], "tml_score": r["score"],
                    "src": "tennislive", "edition": h["event_name"], "draw": h["draw"], "src_round": h["round"],
                    "start_utc": h["start_utc"], "src_winner": h["w_name"], "src_loser": h["l_name"],
                    "src_score": h["score"], "end_reason": h["end_reason"],
                    "winner_agrees": same(h["w_name"], r["winner_name"])})
    if len(hits) == 0:
        rec.append({"source_row": r["source_row"], "match_id": r["match_id"], "tml_round": r["round"],
                    "tml_winner": r["winner_name"], "tml_loser": r["loser_name"], "tml_score": r["score"],
                    "src": "tennislive", "edition": None})
for r, hits in find(g1, ss, "w_name", "l_name", ["unique_tournament_name", "tournament_name", "round_name", "start_utc",
                                                  "w_name", "l_name", "w_sets", "status_description", "status_type"]):
    for _, h in hits.iterrows():
        rec.append({"source_row": r["source_row"], "match_id": r["match_id"], "tml_round": r["round"],
                    "tml_winner": r["winner_name"], "tml_loser": r["loser_name"], "tml_score": r["score"],
                    "src": "sofascore", "edition": h["tournament_name"], "draw": None, "src_round": h["round_name"],
                    "start_utc": h["start_utc"], "src_winner": h["w_name"], "src_loser": h["l_name"],
                    "src_score": h["w_sets"], "end_reason": h["status_description"],
                    "winner_agrees": same(h["w_name"], r["winner_name"])})
    if len(hits) == 0:
        rec.append({"source_row": r["source_row"], "match_id": r["match_id"], "tml_round": r["round"],
                    "tml_winner": r["winner_name"], "tml_loser": r["loser_name"], "tml_score": r["score"],
                    "src": "sofascore", "edition": None})
rec = pd.DataFrame(rec)
rec.to_csv(OUT + "g1_play_days.csv", index=False)
print(rec.to_string())

print("\nHits per source and edition:")
print(rec.groupby(["src", rec["edition"].fillna("NO MATCH")]).agg(rows=("source_row", "nunique"), hits=("source_row", "size"),
                                                                   first=("start_utc", "min"), last=("start_utc", "max")).to_string())
print("\nRows with more than one hit per source:")
print(rec.groupby(["src", "source_row"]).size().loc[lambda x: x > 1].to_string())
print("\nWinner disagreements:", int((rec["winner_agrees"] == False).sum()))
