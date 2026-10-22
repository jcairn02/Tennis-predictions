"""R2 (attack) scratch: match the 31 Stage 0 rows of 2024-2847 one by one to TennisLive's 'ATP Tenerife 3 Challenger'
main draw and to SofaScore's events; read the clock's windows for them. Read-only; prints only. No network."""
import unicodedata
import pandas as pd

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 40)
R2 = "data/studies/p6_data_issues/stage0_review/R2_attack/"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace("-", " ").split())


def toks(s):
    return set(norm(s).split())


m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet")
mp = pd.read_parquet("data/studies/predictability_diagnostic/stage0_match_players.parquet",
                     columns=["match_id", "player_id", "player_name"])
names = mp.drop_duplicates("player_id").set_index("player_id")["player_name"]
g1 = m[m["tournament_id"].eq("2024-2847")].copy()
g1["w"] = [names[a] if aw else names[b] for a, b, aw in zip(g1.player_a_id, g1.player_b_id, g1.a_won)]
g1["l"] = [names[b] if aw else names[a] for a, b, aw in zip(g1.player_a_id, g1.player_b_id, g1.a_won)]

tl = pd.read_csv(R2 + "tennislive_tenerife3_2024.csv")
tl = tl[tl["discipline"].eq("singles") & tl["round"].isin(["R32", "R16", "QF", "SF", "F"])].copy()
tl["w"] = tl.apply(lambda r: r.player1_name if str(r.winner_side) == "1" else r.player2_name, axis=1)
tl["l"] = tl.apply(lambda r: r.player2_name if str(r.winner_side) == "1" else r.player1_name, axis=1)
tl["day"] = pd.to_datetime(tl["start_utc"]).dt.date
print("TennisLive main-draw singles rows:", len(tl))


def same(a, b):
    ta, tb = toks(a), toks(b)
    return len(ta & tb) >= 1 and (norm(a).split()[-1] in tb or norm(b).split()[-1] in ta or len(ta & tb) >= 2)


def sc(s):
    return norm(s).replace(" ret", "").replace("ret", "").strip()


rows = []
for _, r in g1.sort_values("source_row").iterrows():
    hit = tl[tl["round"].eq(r["round"]) & tl["w"].apply(lambda x: same(x, r.w)) & tl["l"].apply(lambda x: same(x, r.l))]
    rev = tl[tl["round"].eq(r["round"]) & tl["w"].apply(lambda x: same(x, r.l)) & tl["l"].apply(lambda x: same(x, r.w))]
    rows.append({"source_row": r.source_row, "round": r["round"], "s0_winner": r.w, "s0_loser": r.l, "s0_score": r.score,
                 "tl_hits": len(hit), "tl_reversed": len(rev),
                 "tl_day": hit["day"].iloc[0] if len(hit) else None,
                 "tl_score": hit["score"].iloc[0] if len(hit) else None,
                 "score_equal": (sc(hit["score"].iloc[0]) == sc(r.score)) if len(hit) else None})
out = pd.DataFrame(rows)
print(out.to_string())
print("matched:", (out.tl_hits == 1).sum(), " reversed:", (out.tl_reversed > 0).sum(),
      " score equal:", out.score_equal.sum())
print("play days by round:", out.groupby("round")["tl_day"].agg(["min", "max"]).to_string())
out.to_csv(R2 + "g1_vs_tennislive.csv", index=False)

# --- SofaScore events (both copies)
for f in ("data/dump/points/sofascore_editions/events.parquet", "data/dump/points/sofascore/events.parquet"):
    e = pd.read_parquet(f)
    tcols = [c for c in e.columns if "tournament" in c.lower() or "season" in c.lower() or "name" in c.lower()]
    txt = e[tcols].astype(str).agg(" ".join, axis=1)
    t = e[txt.str.contains("Tenerife", case=False)]
    print("\n==", f, "rows", len(e), "Tenerife rows", len(t))
    if len(t):
        tc = [c for c in e.columns if any(k in c.lower() for k in ("start", "date", "time"))]
        print("cols:", list(e.columns)[:60])
        print(t[tcols[:4] + tc[:3]].drop_duplicates().head(40).to_string())
