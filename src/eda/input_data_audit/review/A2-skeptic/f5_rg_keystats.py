"""F5 review (A2-skeptic): Roland Garros 2025 box scores against RG's own key statistics.

The key statistics give, per player and match (set0 = whole match):
    ace "Aces", df "Double Faults", first_in / svpt "First Serve" a/b, first_won "Win On 1st Serve" a/_,
    second_won "Win On 2nd Serve" a/_, and from the opponent's columns: bp_faced = opponent's "Break Points Won"
    denominator, bp_saved = that minus its numerator, sv_gms = opponent's "Break Points Converted Games" denominator
    (return games).
Measured here:
  1. per count, exact agreement of the derived counts with Stage 0 by tour, year, draw and source (RG 2025: Sackmann;
     RG 2026: Tennis My Life), and pooled first serves in;
  2. whether the derived counts pass Stage 0's checks (B0-B9) and the games identity under Stage 0's score;
  3. where no fault is suspected (2025 main draw aces/dfs; 2026 TML), how often a count differs by 1-2 (convention
     or noise) against by more.
Writes data/studies/input_data_audit/fixes/A2-skeptic/f5_*.csv
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f5_rg_keystats.py
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

import _common as K


def frac(s: pd.Series, i: int) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.extract(r"(\d+)\s*/\s*(\d+)")[i], errors="coerce")


def main() -> None:
    pd.set_option("display.width", 300)
    k = pd.read_parquet(K.INFOSYS / "keystats.parquet", columns=["slam", "year", "match_id", "set_key", "name", "player1", "player2"])
    k = k[k["slam"].eq("RG") & k["set_key"].eq("set0")].drop_duplicates(["year", "match_id", "name"])
    m = pd.read_parquet(K.INFOSYS / "matches.parquet", columns=["slam", "year", "match_id", "draw", "tour", "p1_first_name",
                                                                "p1_last_name", "p2_first_name", "p2_last_name", "match_winner"])
    m = m[m["slam"].eq("RG")]
    names = {no: m[f"p{no}_first_name"].fillna("") + " " + m[f"p{no}_last_name"].fillna("") for no in ("1", "2")}
    rows = []
    for no, other in (("1", "2"), ("2", "1")):
        me = k.pivot_table(index=["year", "match_id"], columns="name", values=f"player{no}", aggfunc="first")
        op = k.pivot_table(index=["year", "match_id"], columns="name", values=f"player{other}", aggfunc="first")
        r = pd.DataFrame({
            "ace": pd.to_numeric(me["Aces"], errors="coerce"), "df": pd.to_numeric(me["Double Faults"], errors="coerce"),
            "first_in": frac(me["First Serve"], 0), "svpt": frac(me["First Serve"], 1),
            "first_won": frac(me["Win On 1st Serve"], 0), "second_won": frac(me["Win On 2nd Serve"], 0),
            "second_den": frac(me["Win On 2nd Serve"], 1),
            "bp_faced": frac(op["Break Points Won"], 1), "bp_saved": frac(op["Break Points Won"], 1) - frac(op["Break Points Won"], 0),
            "sv_gms": frac(op["Break Points Converted Games"], 1)}).reset_index()
        mm = m.assign(pk=names[no].map(K.name_key), ok=names[other].map(K.name_key), side_no=no)
        r = r.merge(mm[["year", "match_id", "draw", "tour", "pk", "ok", "side_no", "match_winner"]], on=["year", "match_id"])
        rows.append(r)
    ks = pd.concat(rows, ignore_index=True)
    ks["year"] = ks["year"].astype(int)
    ks["second_den_check"] = (ks["second_den"] == ks["svpt"] - ks["first_in"])
    print("key statistics: second-serve denominator = svpt - first_in in", round(float(ks["second_den_check"].mean()), 4))

    d = K.stage0()
    s = d[d["tournament_name"].eq("Roland Garros") & d["year"].isin([2025, 2026]) & d["has_box"]].copy()
    s["pk"], s["ok"] = s["player_name"].map(K.name_key), s["o_player_name"].map(K.name_key)
    j = s.merge(ks, on=["year", "pk", "ok"], suffixes=("", "_rg"))
    j["draw"] = np.where(j["qualifying"], "qualifying", "main")
    for c in K.BOX:
        j[f"{c}_eq"] = j[c].eq(j[f"{c}_rg"])
        j[f"{c}_d"] = j[c] - j[f"{c}_rg"]
    j["all9_eq"] = j[[f"{c}_eq" for c in K.BOX]].all(axis=1)
    g = j.groupby(["tour", "year", "draw", "source"]).agg(rows=("all9_eq", "size"), all9_equal=("all9_eq", "mean"),
                                                         **{f"{c}_equal": (f"{c}_eq", "mean") for c in K.BOX})
    sums = j.groupby(["tour", "year", "draw", "source"])[["first_in", "svpt", "first_in_rg", "svpt_rg"]].sum()
    g["stage0_first_in_pct"] = 100 * sums["first_in"] / sums["svpt"]
    g["rg_first_in_pct"] = 100 * sums["first_in_rg"] / sums["svpt_rg"]
    g.to_csv(K.OUT / "f5_agreement.csv")
    print(g.round(3).to_string())
    # size of disagreements where no fault is suspected: aces/dfs/svpt in 2025 main, all in 2026 TML
    for (tour, year, draw, src), x in j.groupby(["tour", "year", "draw", "source"]):
        dist = {c: x[f"{c}_d"].abs().clip(upper=3).value_counts(normalize=True).sort_index().round(3).to_dict()
                for c in ("svpt", "first_in", "ace", "df", "sv_gms", "bp_faced")}
        print(tour, year, draw, src, "|abs diff| shares (3 = 3+):", dist)
    # checks of the derived counts under Stage 0's score
    j.to_csv(K.OUT / "f5_rows.csv", index=False)


if __name__ == "__main__":
    main()
