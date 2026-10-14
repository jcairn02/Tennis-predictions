"""B2-skeptic review of F12 (Nottingham 2017 final) and the other winner-swapped / name-swapped odds rows. Read-only.

tennis-data's W columns (rank, set scores, odds) belong to one player. A row whose names disagree with its own rank
columns (WRank equals Stage 0's rank of the player named as the loser, and LRank the rank of the player named as the
winner) has its names exchanged, not its numbers. For every linked Stage 1 row: does tennis-data's (WRank, LRank) agree
with Stage 0's ranks of the two named players as stored, or only exchanged?

Writes data/studies/input_data_audit/fixes/B2-skeptic/f12_rank_orientation.csv (rows that agree only exchanged).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
S0 = ROOT / "data/studies/predictability_diagnostic"


def agree(a, b):
    return (a - b).abs() <= np.maximum(3.0, 0.1 * b)


def main() -> None:
    x = pd.read_parquet(OUT / "f11_raw_books.parquet")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "side", "rank", "player_name", "won"])
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "a_won", "score"])
    ra = p[p["side"].eq("A")].set_index("match_id")
    rb = p[p["side"].eq("B")].set_index("match_id")
    x = x.join(ra[["rank", "player_name"]].rename(columns={"rank": "rank_a", "player_name": "name_a"}), on="match_id")
    x = x.join(rb[["rank", "player_name"]].rename(columns={"rank": "rank_b", "player_name": "name_b"}), on="match_id")
    x = x.join(m.set_index("match_id")[["a_won", "score"]], on="match_id")
    a_is_w = np.where(x["link"].eq("winner_swapped"), ~x["a_won"].astype(bool), x["a_won"].astype(bool))
    # Stage 0 ranks of the players tennis-data NAMES as W and L
    rank_named_w = np.where(a_is_w, x["rank_a"], x["rank_b"])
    rank_named_l = np.where(a_is_w, x["rank_b"], x["rank_a"])
    x["rank_named_w"], x["rank_named_l"] = rank_named_w, rank_named_l
    both = x["WRank"].notna() & x["LRank"].notna() & x["rank_named_w"].notna() & x["rank_named_l"].notna()
    stored = agree(x["WRank"], x["rank_named_w"]) & agree(x["LRank"], x["rank_named_l"])
    exch = agree(x["WRank"], x["rank_named_l"]) & agree(x["LRank"], x["rank_named_w"])
    far = (x["rank_named_w"] - x["rank_named_l"]).abs() >= 10      # ranks distinct enough to tell the players apart
    x["ranks_only_exchanged"] = both & exch & ~stored & far
    print("linked rows with both ranks known:", int(both.sum()), "| agree as stored:", int((both & stored).sum()),
          "| agree only exchanged (ranks >= 10 apart):", int(x["ranks_only_exchanged"].sum()))
    cols = ["match_id", "link", "td_file", "td_row", "src_row", "Winner", "Loser", "WRank", "LRank", "name_a", "name_b",
            "rank_a", "rank_b", "a_won", "score", "Comment", "AvgW", "AvgL", "B365W", "B365L", "PSW", "PSL", "p_Avg",
            "p_books_med"]
    y = x[x["ranks_only_exchanged"]]
    y[cols].to_csv(OUT / "f12_rank_orientation.csv", index=False)
    print(y[cols].to_string())
    ws = x[x["link"].eq("winner_swapped")]
    print("\nwinner_swapped rows: ranks agree as stored", int((ws.index.isin(x.index[both & stored])).sum()),
          "| only exchanged", int(ws["ranks_only_exchanged"].sum()), "| of", len(ws))
    print(ws[["match_id", "Winner", "Loser", "WRank", "LRank", "rank_named_w", "rank_named_l", "Comment", "score"]].to_string())


if __name__ == "__main__":
    main()
