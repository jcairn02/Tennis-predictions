"""F1 step 2: Sackmann's WTA 2014-2016 box scores against the Match Charting Project, per player-match.

Matching (my own): same calendar year, MCP date within [tourney_date - 3, tourney_date + 21] days, same round label,
and the two players' normalised names (full-name key, else surname) on the same sides. A charted match that
matches more than one Sackmann row is dropped.
Writes f1_mcp_pairs.csv (one row per player-match) and prints the split by window / df.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

WINDOW = ("2015-02-23", "2015-08-24")

s = pd.concat([R.sack("wta", f"wta_matches_{y}.parquet") for y in (2013, 2014, 2015, 2016, 2017)], ignore_index=True)
s = s[R.has_box(s)].copy()
s["year"] = s["tdate"].dt.year
s["wk"], s["lk"] = s["winner_name"].map(R.nkey), s["loser_name"].map(R.nkey)
s["wl"], s["ll"] = s["winner_name"].map(R.last), s["loser_name"].map(R.last)
s["round"] = s["round"].str.upper()

o = R.mcp_overview("w")
o = o[o["mdate"].dt.year.between(2013, 2017)].copy()
ROUNDS = {"R128": "R128", "R64": "R64", "R32": "R32", "R16": "R16", "QF": "QF", "SF": "SF", "F": "F", "RR": "RR"}
o["round"] = o["round"].astype(str).str.upper()
mt = o.groupby("match_id").agg(p1=("p1", "first"), p2=("p2", "first"), mdate=("mdate", "first"),
                               tournament=("tournament", "first"), round=("round", "first")).reset_index()
mt["k1"], mt["k2"] = mt["p1"].map(R.nkey), mt["p2"].map(R.nkey)
mt["l1"], mt["l2"] = mt["p1"].map(R.last), mt["p2"].map(R.last)

links = []
s_idx = s.reset_index(drop=True)
by_pair_full = {}
for i, r in s_idx.iterrows():
    by_pair_full.setdefault(frozenset((r["wk"], r["lk"])), []).append(i)
by_pair_last = {}
for i, r in s_idx.iterrows():
    by_pair_last.setdefault(frozenset((r["wl"], r["ll"])), []).append(i)
for _, r in mt.iterrows():
    cand = by_pair_full.get(frozenset((r["k1"], r["k2"])), [])
    how = "full"
    if not cand:
        cand = by_pair_last.get(frozenset((r["l1"], r["l2"])), [])
        how = "last"
    ok = [i for i in cand
          if s_idx.at[i, "round"] == r["round"]
          and -3 <= (r["mdate"] - s_idx.at[i, "tdate"]).days <= 21]
    if len(ok) == 1:
        links.append((r["match_id"], ok[0], how))
lk = pd.DataFrame(links, columns=["match_id", "si", "how"])
print("charted matches 2013-17:", len(mt), " linked:", len(lk), lk["how"].value_counts().to_dict())

rows = []
for mid, si, how in lk.itertuples(index=False):
    r = s_idx.loc[si]
    ov = o[o["match_id"].eq(mid)]
    for side, name in (("w", r["winner_name"]), ("l", r["loser_name"])):
        k, ln = R.nkey(name), R.last(name)
        hit = ov[ov["pkey"].eq(k)]
        if len(hit) != 1:
            hit = ov[ov["player"].map(R.last).eq(ln)]
        if len(hit) != 1:
            continue
        h = hit.iloc[0]
        rows.append({"mcp_match_id": mid, "_source_file": r["_source_file"], "_row": r["_row"], "side": side,
                     "player": name, "tourney_name": r["tourney_name"], "tdate": r["tdate"], "round": r["round"],
                     "tourney_level": r["tourney_level"],
                     **{f"s_{b}": r[f"{side}_{b}"] for b in R.BOX},
                     "m_svpt": h["serve_pts"], "m_df": h["dfs"], "m_ace": h["aces"], "m_first_in": h["first_in"],
                     "m_first_won": h["first_won"], "m_second_won": h["second_won"], "m_bp_faced": h["bk_pts"],
                     "m_bp_saved": h["bp_saved"]})
pm = pd.DataFrame(rows)
pm["in_window"] = pm["tdate"].between(*WINDOW) & ~pm["tourney_name"].eq("Doha") & ~pm["tourney_level"].eq("G")
pm["eq_svpt"] = pm["s_svpt"].eq(pm["m_svpt"])
pm["eq_plus"] = (pm["s_svpt"] + pm["s_df"]).eq(pm["m_svpt"])
pm["df0"] = pm["s_df"].eq(0)
for b in ("df", "ace", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"):
    pm[f"eq_{b}"] = pm[f"s_{b}"].eq(pm[f"m_{b}"])
pm["d_svpt"] = pm["m_svpt"] - pm["s_svpt"]
pm.to_csv(R.OUT / "f1_mcp_pairs.csv", index=False)


def summ(d):
    return pd.Series({"n": len(d), "eq_svpt": d["eq_svpt"].mean(), "eq_plus": d["eq_plus"].mean(),
                      "eq_svpt_only": (d["eq_svpt"] & ~d["eq_plus"]).sum(), "eq_plus_only": (d["eq_plus"] & ~d["eq_svpt"]).sum(),
                      "neither": (~d["eq_svpt"] & ~d["eq_plus"]).sum(),
                      "eq_df": d["eq_df"].mean(), "eq_first_in": d["eq_first_in"].mean(),
                      "eq_first_won": d["eq_first_won"].mean(), "eq_second_won": d["eq_second_won"].mean(),
                      "eq_ace": d["eq_ace"].mean()})


pd.set_option("display.width", 250)
print(pm.groupby(["in_window", "df0"]).apply(summ).to_string(float_format=lambda x: f"{x:.3f}"))
print(pm.groupby(["in_window"]).apply(summ).to_string(float_format=lambda x: f"{x:.3f}"))
pm["year"] = pm["tdate"].dt.year
pm["grp"] = np.where(pm["in_window"], "window", np.where(pm["tdate"].dt.year.eq(2015), "2015_other", "other"))
print(pm.groupby(["grp", pm["tourney_level"].eq("G")]).apply(summ).to_string(float_format=lambda x: f"{x:.3f}"))
w = pm[pm["in_window"]]
print(w.groupby("tourney_name").apply(summ)[["n", "eq_svpt_only", "eq_plus_only", "neither"]].to_string())
print("window rows, df>0, svpt equals MCP (inclusive-looking):")
print(w[(~w["df0"]) & w["eq_svpt"]][["mcp_match_id", "player", "s_svpt", "s_df", "m_svpt", "m_df", "s_first_in", "m_first_in",
                                      "s_second_won", "m_second_won"]].to_string())
print("window rows, neither:")
print(w[~w["eq_svpt"] & ~w["eq_plus"]][["mcp_match_id", "player", "s_svpt", "s_df", "m_svpt", "m_df", "s_first_in",
                                         "m_first_in", "s_first_won", "m_first_won", "s_second_won", "m_second_won"]].to_string())
# 2015 rows outside the window (Doha, Slams, Jan-Feb) for the boundary
b = pm[pm["year"].eq(2015) & ~pm["in_window"]]
print(b.groupby("tourney_name").apply(summ)[["n", "eq_svpt_only", "eq_plus_only", "neither"]].to_string())
