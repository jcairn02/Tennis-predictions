"""B1-rederive reviewer: F11, F12, F13 closing odds, re-derived from the raw tennis-data rows (read-only).

For every linked Stage 1 row, the raw tennis-data row (td_file, positional td_row as stage1_odds.load_td
numbers it) is re-read with every book column. Checks, in tennis-data's own W/L orientation:
  * books: B365, EX, LB, PS, SJ, CB, GB, IW, SB, UB, B&W, BFE (a quote is a number > 1.0, as Stage 1 treats it);
  * avg_vs_books: the favourite of the average (AvgW vs AvgL) against the favourite of every individual book;
  * avg_gt_max: AvgW > MaxW or AvgL > MaxL (an average cannot exceed the maximum);
  * avg_outside: an average outside [min of the books, Max] on a side;
  * after exchanging AvgW<->AvgL (and MaxW<->MaxL when the max is reversed too), do all relations hold?
Stage 1's orientation (a = Stage 0 side A) is re-derived: a_is_td_winner = a_won, except for winner_swapped links.
Writes odds_rows_checked.csv (flagged rows) and prints the detail of every candidate row.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
S0 = ROOT / "data/studies/predictability_diagnostic"
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 60)
pd.set_option("display.max_rows", 500)

BOOKS = ["B365", "EX", "LB", "PS", "SJ", "CB", "GB", "IW", "SB", "UB", "B&W", "BFE"]

o = pd.read_parquet(S0 / "stage1_odds.parquet")
m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "a_won", "score", "tournament_name",
                                                             "player_a_id", "player_b_id"])
p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "side", "player_name", "rank"])
pa = p[p.side.eq("A")].set_index("match_id")
pb = p[p.side.eq("B")].set_index("match_id")
o = o.merge(m, on="match_id", how="left")
o["name_a"], o["name_b"] = o.match_id.map(pa.player_name), o.match_id.map(pb.player_name)
o["rank_a"], o["rank_b"] = o.match_id.map(pa["rank"]), o.match_id.map(pb["rank"])
lk = o[o.link.ne("none")].copy()

# raw rows
raw = []
for f, g in lk.groupby("td_file"):
    df = pd.read_parquet(ROOT / f)
    take = df.iloc[g.td_row.astype(int).to_numpy()].copy()
    take["match_id"] = g.match_id.to_numpy()
    raw.append(take)
raw = pd.concat(raw, ignore_index=True)
num = lambda s: pd.to_numeric(s, errors="coerce").where(lambda v: v > 1.0)
for b in BOOKS + ["Max", "Avg"]:
    for s in "WL":
        c = f"{b}{s}"
        raw[c] = num(raw[c]) if c in raw else np.nan
r = lk.merge(raw[["match_id", "Winner", "Loser", "WRank", "LRank", "W1", "L1", "W2", "L2", "W3", "L3", "Comment",
                  "_source_file", "_sheet", "_row"] + [f"{b}{s}" for b in BOOKS + ["Max", "Avg"] for s in "WL"]],
             on="match_id", how="left")
assert (r.Winner.astype(str) == r.td_winner.astype(str)).all(), "raw row does not match Stage 1's td_winner"

# consistency of the Stage 1 a/b prices with the raw row
a_is_w = np.where(r.link.eq("winner_swapped"), ~r.a_won.astype(bool), r.a_won.astype(bool))
r["a_is_td_winner"] = a_is_w
chk = np.where(a_is_w, r.AvgW, r.AvgL)
ok = np.isclose(chk, r.avg_a) | (np.isnan(chk) & r.avg_a.isna())
print("Stage 1 avg_a equals the raw row's oriented Avg on", int(ok.sum()), "of", len(r))

bw = r[[f"{b}W" for b in BOOKS]].to_numpy()
bl = r[[f"{b}L" for b in BOOKS]].to_numpy()
both = ~np.isnan(bw) & ~np.isnan(bl)
r["n_books"] = both.sum(1)
fav_w = np.where(both, bw < bl, False).sum(1)      # books making td-winner the favourite
fav_l = np.where(both, bl < bw, False).sum(1)
r["books_fav_w"], r["books_fav_l"] = fav_w, fav_l
r["avg_fav"] = np.where(r.AvgW < r.AvgL, "W", np.where(r.AvgL < r.AvgW, "L", "even"))
r["max_fav"] = np.where(r.MaxW < r.MaxL, "W", np.where(r.MaxL < r.MaxW, "L", "even"))
r["books_fav"] = np.where((fav_w > 0) & (fav_l == 0), "W", np.where((fav_l > 0) & (fav_w == 0), "L", "split"))
bmin_w, bmax_w = np.nanmin(np.where(both, bw, np.nan), 1), np.nanmax(np.where(both, bw, np.nan), 1)
bmin_l, bmax_l = np.nanmin(np.where(both, bl, np.nan), 1), np.nanmax(np.where(both, bl, np.nan), 1)
r["bmin_w"], r["bmax_w"], r["bmin_l"], r["bmax_l"] = bmin_w, bmax_w, bmin_l, bmax_l
r["avg_gt_max"] = (r.AvgW > r.MaxW + 1e-9) | (r.AvgL > r.MaxL + 1e-9)
r["avg_reversed_vs_books"] = (r.n_books >= 1) & (r.books_fav != "split") & (r.avg_fav != "even") & (r.avg_fav != r.books_fav)


def consistent(avgw, avgl, maxw, maxl, row):
    """avg <= max on each side; max >= every book; avg within [min book - 3%, max]."""
    ok = True
    for avg, mx, lo, hi in ((avgw, maxw, row.bmin_w, row.bmax_w), (avgl, maxl, row.bmin_l, row.bmax_l)):
        if np.isfinite(mx) and np.isfinite(avg) and avg > mx + 1e-9:
            ok = False
        if np.isfinite(mx) and np.isfinite(hi) and hi > mx + 1e-9:
            ok = False
        if np.isfinite(lo) and np.isfinite(avg) and avg < lo * 0.97:
            ok = False
    return ok


r["consistent_as_is"] = [consistent(x.AvgW, x.AvgL, x.MaxW, x.MaxL, x) for x in r.itertuples()]
r["consistent_avg_swapped"] = [consistent(x.AvgL, x.AvgW, x.MaxW, x.MaxL, x) for x in r.itertuples()]
r["consistent_avg_max_swapped"] = [consistent(x.AvgL, x.AvgW, x.MaxL, x.MaxW, x) for x in r.itertuples()]
wr, lr = pd.to_numeric(r.WRank, errors="coerce"), pd.to_numeric(r.LRank, errors="coerce")
r["td_rank_fav"] = np.where(wr < lr, "W", np.where(lr < wr, "L", "?"))

flag = r[r.avg_reversed_vs_books | r.avg_gt_max | r.link.eq("winner_swapped")
         | (~r.consistent_as_is & r.n_books.ge(1))].copy()
cols = ["match_id", "evaluation", "link", "tournament_name", "round", "td_date", "Winner", "Loser", "WRank", "LRank",
        "a_won", "name_a", "name_b", "rank_a", "rank_b", "score", "status", "Comment", "W1", "L1", "W2", "L2", "W3", "L3"] \
    + [f"{b}{s}" for b in BOOKS + ["Max", "Avg"] for s in "WL"] \
    + ["n_books", "books_fav", "avg_fav", "max_fav", "td_rank_fav", "avg_reversed_vs_books", "avg_gt_max",
       "consistent_as_is", "consistent_avg_swapped", "consistent_avg_max_swapped", "avg_a", "avg_b", "p_avg_a",
       "avg_coherent", "td_file", "td_row", "_source_file", "_sheet", "_row"]
flag[cols].to_csv(OUT / "odds_rows_checked.csv", index=False)
print("flagged rows:", len(flag))
print(pd.crosstab([flag.avg_reversed_vs_books, flag.avg_gt_max, flag.link.eq("winner_swapped")],
                  [flag.consistent_as_is, flag.consistent_avg_swapped]))

show = ["match_id", "link", "td_date", "Winner", "Loser", "WRank", "LRank", "a_won", "name_a", "rank_a", "rank_b",
        "score", "Comment", "n_books", "books_fav", "avg_fav", "max_fav", "td_rank_fav", "avg_gt_max",
        "consistent_as_is", "consistent_avg_swapped", "consistent_avg_max_swapped", "p_avg_a", "evaluation"]
print("\n=== avg reversed against every individual book (n_books>=1)")
print(flag[flag.avg_reversed_vs_books][show].to_string())
print("\n=== avg > max")
print(flag[flag.avg_gt_max][show].to_string())
print("\n=== other inconsistent rows (not reversed, avg<=max)")
print(flag[~flag.avg_reversed_vs_books & ~flag.avg_gt_max & ~flag.link.eq("winner_swapped")][show].to_string())

# strict reversal: >= 2 books, all books agree, each book gives its favourite >= 0.60 (normalised),
# and the average gives that player <= 0.40
pw = (1 / bw) / (1 / bw + 1 / bl)                      # each book's normalised p(td winner)
pavg_w = (1 / r.AvgW) / (1 / r.AvgW + 1 / r.AvgL)
pmax_w = (1 / r.MaxW) / (1 / r.MaxW + 1 / r.MaxL)
r["p_avg_w"], r["p_max_w"] = pavg_w, pmax_w
r["books_p_w_min"] = np.nanmin(np.where(both, pw, np.nan), 1)
r["books_p_w_max"] = np.nanmax(np.where(both, pw, np.nan), 1)
strict_w = (r.n_books >= 2) & (r.books_p_w_min >= 0.60) & (r.p_avg_w <= 0.40)     # books: W favourite; avg: L
strict_l = (r.n_books >= 2) & (r.books_p_w_max <= 0.40) & (r.p_avg_w >= 0.60)     # books: L favourite; avg: W
r["strict_reversal"] = strict_w | strict_l
r["max_reversed_too"] = np.where(strict_w, r.p_max_w <= 0.5, np.where(strict_l, r.p_max_w >= 0.5, False))
sr = r[r.strict_reversal].copy()
sr.to_csv(OUT / "odds_strict_reversals.csv", index=False)
print(f"\n=== strict reversals of the average against >= 2 agreeing books: {len(sr)} "
      f"(evaluation {int(sr.evaluation.sum())})")


def block(row):
    blk = " ".join(f"{b}:{row[b + 'W']}/{row[b + 'L']}" for b in BOOKS + ["Max", "Avg"]
                   if pd.notna(row[b + "W"]) or pd.notna(row[b + "L"]))
    return (f"{row['match_id']} [{row['link']}, eval={row['evaluation']}] | {row['Winner']} d. {row['Loser']} | td ranks "
            f"{row['WRank']}/{row['LRank']} | td sets {row['W1']}-{row['L1']} {row['W2']}-{row['L2']} {row['W3']}-{row['L3']} "
            f"| S0: A={row['name_a']} ({row['rank_a']}) B={row['name_b']} ({row['rank_b']}) a_won={row['a_won']} "
            f"score {row['score']} ({row['status']}) | {blk} | p_avg_a={row['p_avg_a']} "
            f"| {row['_source_file']} sheet {row['_sheet']} row {row['_row']} (td_row {row['td_row']})")


for _, row in sr.iterrows():
    print(block(row), "| max reversed too:", row["max_reversed_too"],
          "| consistent avg-swapped:", row["consistent_avg_swapped"], "avg+max swapped:", row["consistent_avg_max_swapped"])

print("\n=== winner_swapped links")
for _, row in r[r.link.eq("winner_swapped")].iterrows():
    print(block(row), "| rank_agrees", row["rank_agrees_a"], row["rank_agrees_b"], "| same_set_scores", row["same_set_scores"])

# the audit's flagged rows
aud = set()
for f in ["a07_avg_vs_books", "a04_avg_gt_max", "a06_winner_swapped", "a06_placeholders"]:
    d = pd.read_csv(ROOT / f"data/studies/input_data_audit/odds/{f}.csv")
    ids = set(d.match_id) if "match_id" in d else set()
    print(f"\n=== audit table {f}: {len(d)} rows, {len(ids)} match ids; in my strict reversals: "
          f"{len(ids & set(sr.match_id))}")
    for mid in sorted(ids):
        x = r[r.match_id.eq(mid)]
        if len(x):
            row = x.iloc[0]
            print(block(row), "| strict:", row["strict_reversal"], "| avg>max:", row["avg_gt_max"],
                  "| max reversed too:", row["max_reversed_too"])
        else:
            y = o[o.match_id.eq(mid)]
            print(mid, "NOT LINKED in Stage 1" if len(y) else "NOT IN Stage 1",
                  y[["link", "avg_a", "avg_b", "p_avg_a"]].to_dict("records"))
    aud |= ids
r[r.match_id.isin(aud) | r.strict_reversal | r.link.eq("winner_swapped")][cols + ["strict_reversal", "max_reversed_too", "p_avg_w", "p_max_w", "books_p_w_min", "books_p_w_max"]].to_csv(OUT / "odds_candidate_rows.csv", index=False)
