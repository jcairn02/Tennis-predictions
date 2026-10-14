"""F1: the window's edges (Doha, Acapulco, Kuala Lumpur, Monterrey) by round, and TML's 2015 copy as a second record."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
from x10_f1 import raw_player_rows  # noqa: E402

x = raw_player_rows([2015])
x = x[x["full"] & x["file"].str.startswith("wta_matches_2015")].copy()
x["deffail"] = rc.definition_fails(x)
j = pd.read_csv(rc.OUT / "f1_mcp_rows.csv", parse_dates=["tdate", "mdate"])

edge = ["Doha", "Acapulco", "Kuala Lumpur", "Monterrey", "Dubai", "Rio de Janeiro", "New Haven", "Cincinnati"]
e = x[x["tourney_name"].isin(edge) & x["tdate"].between("2015-02-16", "2015-08-31")]
g = e.groupby(["tdate", "tourney_name", "round"]).agg(rows=("svpt", "size"), deffail=("deffail", "sum"),
                                                     svpt=("svpt", "sum"), fi=("first_in", "sum"), sw=("second_won", "sum"),
                                                     df=("df", "sum"))
g["second_won_pct"] = (100 * g["sw"] / (g["svpt"] - g["fi"])).round(1)
g["second_won_pct_plus_df"] = (100 * g["sw"] / (g["svpt"] + g["df"] - g["fi"])).round(1)
print(g.drop(columns=["svpt", "fi", "sw"]).to_string())

print("\nMCP rows at the edges:")
jj = j[j["tourney_name"].isin(edge) & j["tdate"].between("2015-02-16", "2015-08-31")]
print(jj[["tdate", "tourney_name", "round", "mdate", "name", "oname", "svpt", "df", "serve_pts", "dfs", "first_in",
          "first_in_mcp", "second_won", "second_won_mcp", "verdict"]].sort_values(["tdate", "tourney_name", "mdate"]).to_string())

# the two in-scope rows MCP calls inclusive: both players of those matches
print("\nboth rows of the in-scope matches with an 'includes_df' MCP verdict (Rome F, Birmingham F):")
for ev, rd_ in (("Rome", "F"), ("Birmingham", "F")):
    print(j[(j["tourney_name"] == ev) & (j["round"] == rd_) & (j["tdate"].dt.year == 2015)][
        ["tourney_name", "round", "name", "svpt", "df", "serve_pts", "dfs", "first_in", "first_in_mcp", "first_won",
         "first_won_mcp", "second_won", "second_won_mcp", "ace", "aces", "bp_faced", "bk_pts", "return_pts",
         "return_pts_won", "verdict"]].to_string())

# TML's 2015 WTA copy against Sackmann's
t = pd.read_parquet(rc.TML / "wta_main" / "2015_wta.parquet")
print("\nTML 2015 WTA columns:", list(t.columns)[:60])
t["tdate"] = pd.to_datetime(t["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
rows = []
for side, me, op in (("w", "winner", "loser"), ("l", "loser", "winner")):
    c = rc.raw_counts(t, side)
    d = pd.DataFrame({"tdate": t["tdate"], "tourney_name": t["tourney_name"], "round": t["round"],
                      "pk": rc.keys(t[f"{me}_name"]), "ok": rc.keys(t[f"{op}_name"])})
    rows.append(pd.concat([d, c.add_prefix("t_")], axis=1))
tt = pd.concat(rows, ignore_index=True)
tt = tt[tt["t_svpt"].notna()]
m = x.merge(tt, on=["pk", "ok", "round"], suffixes=("", "_t"))
m = m[(m["tdate"] - m["tdate_t"]).dt.days.abs() <= 7]
m["in_window"] = m["tdate"].between("2015-02-23", "2015-08-24") & ~m["tourney_level"].isin(["G", "D"])
for b in rc.BOX:
    m[f"eq_{b}"] = m[b].eq(m[f"t_{b}"])
m["eq_all"] = m[[f"eq_{b}" for b in rc.BOX]].all(axis=1)
print(f"\nTML rows matched to Sackmann WTA 2015 rows with a box: {len(m)}")
print(m.groupby("in_window")[["eq_all", "eq_svpt", "eq_df", "eq_first_in"]].mean().round(3).to_string())
print(m[~m["eq_all"]][["tdate", "tourney_name", "round", "pk", "svpt", "t_svpt", "df", "t_df", "first_in", "t_first_in"]]
      .head(20).to_string())
