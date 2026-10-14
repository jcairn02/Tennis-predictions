"""Round 2: F2y (AO 2022 R128 Paire-Monteiro: service games only) and F4x (AO 2012 R128 Li d. Pervak) against the
independent records: AO 2022 ball tracking (2022_MS146), Sofascore; Sackmann's Slam point-by-point (AO and Wimbledon
2012), MCP; and the two Sackmann rows that share the F4x box."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
import refs  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)

# ---------------- F2y: ball tracking
pt = rc.rd(rc.PTS / "slam_ball_tracking" / "points" / "AO_2022.parquet")
x = pt[pt["match_id"].astype(str).eq("2022_MS146")].copy()
for c in ["set_num", "game_num", "point_num", "serve_num"]:
    x[c] = pd.to_numeric(x[c], errors="coerce")
for c in ["is_ace", "is_doublefault", "is_fault", "is_tiebreak", "is_break_point", "is_break_point_converted"]:
    x[c] = x[c].astype(str).str.lower().isin(["true", "1", "1.0"])
print("ball tracking rows:", len(x), "players:", x["player1"].iloc[0], x["player2"].iloc[0])
pts = x.sort_values(["set_num", "game_num", "point_num", "serve_num"]).groupby(["set_num", "game_num", "point_num"]).agg(
    server=("server_id", "first"), winner=("point_winner_id", "last"), n_serves=("serve_num", "max"),
    ace=("is_ace", "any"), dbl=("is_doublefault", "any"), tb=("is_tiebreak", "any"),
    bp=("is_break_point", "any"), bpc=("is_break_point_converted", "any")).reset_index()
for sid, g in pts.groupby("server"):
    games = g[["set_num", "game_num"]].drop_duplicates()
    first_in = g[(g["n_serves"] == 1) & ~g["dbl"]]
    print(f"  server {sid}: serve points {len(g)}, aces {int(g['ace'].sum())}, double faults {int(g['dbl'].sum())}, "
          f"first serves in {len(first_in)}, first won {int((first_in['winner'] == sid).sum())}, second won "
          f"{int(((g['n_serves'] == 2) & (g['winner'] == sid)).sum())}, service games {len(games)} "
          f"(tiebreak games {int(g.groupby(['set_num','game_num'])['tb'].any().sum())}), break points faced {int(g['bp'].sum())}, "
          f"broken {int(g['bpc'].sum())}")
first_game = pts.sort_values(["set_num", "game_num", "point_num"]).iloc[0]
print("  first server of the match:", first_game["server"])
sf = refs.ref_sofascore()
s = sf[sf["pk"].isin([rc.name_key("Benoit Paire"), rc.name_key("Thiago Monteiro")])
       & sf["ok"].isin([rc.name_key("Benoit Paire"), rc.name_key("Thiago Monteiro")]) & sf["year"].eq(2022)]
print(s[["event", "round", "name", "ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]].to_string())

# ---------------- F4x
for y in (2012,):
    r = pd.concat([pd.read_parquet(rc.SACK / "wta" / f"wta_matches_{y}.parquet"),
                   pd.read_parquet(rc.SACK / "wta" / f"wta_matches_qual_itf_{y}.parquet")], ignore_index=True)
    z = r[r["winner_name"].astype(str).str.contains("Li$|Na Li", regex=True) & r["loser_name"].astype(str).str.contains("Pervak")
          | r["loser_name"].astype(str).str.contains("Li$|Na Li", regex=True) & r["winner_name"].astype(str).str.contains("Pervak")]
    print("\nSackmann rows of Li v Pervak, 2012:")
    print(z[["_source_file", "_row", "tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score", "w_ace",
             "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_SvGms", "w_bpSaved", "w_bpFaced", "l_ace", "l_df",
             "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_SvGms", "l_bpSaved", "l_bpFaced"]].to_string())
pbp = refs.ref_slam_pbp()
q = pbp[pbp["year"].eq(2012) & pbp["pk"].isin([rc.name_key("Na Li"), rc.name_key("Li Na")])
        & pbp["ok"].eq(rc.name_key("Ksenia Pervak"))
        | pbp["year"].eq(2012) & pbp["ok"].isin([rc.name_key("Na Li"), rc.name_key("Li Na")]) & pbp["pk"].eq(rc.name_key("Ksenia Pervak"))]
print("\nSackmann Slam point-by-point 2012, Li v Pervak:")
print(q[["event", "round", "name", "oname", "ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]].to_string())
mc = refs.ref_mcp()
q2 = mc[mc["year"].eq(2012) & mc["sn"].isin(["pervak"]) if "sn" in mc else mc["year"].eq(2012) & mc["name"].astype(str).str.contains("Pervak")]
q2 = mc[(mc["year"] == 2012) & (mc["name"].astype(str).str.contains("Pervak") | mc["oname"].astype(str).str.contains("Pervak"))]
print("\nMCP 2012 Pervak:")
print(q2[["date", "event", "round", "name", "oname", "ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_saved", "bp_faced"]].to_string())
