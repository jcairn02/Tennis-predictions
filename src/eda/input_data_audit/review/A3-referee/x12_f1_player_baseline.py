"""F1: per event and round, how the same players read against their own matches outside the window.

For each WTA tour main-draw player row of 2014-2016 with a box, the second-serve points-won share as recorded,
minus the same player's pooled share in her inclusive matches (2014-16 outside the 30-event window and Doha).
Under 'serve points exclude double faults' the recorded share reads about 7 points above her own norm; under the
normal convention about 0. Also the first-serve-in share, inflated the same way.
Writes f1_event_round_baseline.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
from x10_f1 import raw_player_rows  # noqa: E402

x = raw_player_rows([2014, 2015, 2016])
x = x[x["full"] & ~x["qual"] & x["file"].str.match(r"wta_matches_20\d\d\.parquet") & ~x["tourney_level"].isin(["D"])].copy()
win = x["tdate"].between("2015-02-23", "2015-08-24") & ~x["tourney_level"].isin(["G"])
doha = win & x["tourney_name"].eq("Doha")
x["group"] = np.select([doha, win], ["Doha", "window"], "outside")
x["L"] = x["svpt"] - x["first_in"] - x["second_won"]        # second-serve points lost, as recorded
base = x[x["group"].eq("outside")].groupby("pid").agg(b_sw=("second_won", "sum"), b_s2=("svpt", "sum"),
                                                      b_fi=("first_in", "sum"), b_df=("df", "sum"), b_n=("svpt", "size"))
base["b_s2"] = base["b_s2"] - base["b_fi"]
bsv = x[x["group"].eq("outside")].groupby("pid")["svpt"].sum()
base["base_second_share"] = base["b_sw"] / base["b_s2"]
base["base_first_in_share"] = base["b_fi"] / bsv
x = x.join(base[["base_second_share", "base_first_in_share", "b_n"]], on="pid")
y = x[x["b_n"] >= 5].copy()        # players with at least 5 inclusive matches elsewhere
y["s2"] = y["svpt"] - y["first_in"]
y["exp_sw"] = y["base_second_share"] * y["s2"]
y["exp_fi"] = y["base_first_in_share"] * y["svpt"]
y["deffail"] = rc.definition_fails(y)
g = y.groupby(["group", "tdate", "tourney_name", "round"]).agg(
    rows=("svpt", "size"), deffail=("deffail", "sum"), sw=("second_won", "sum"), s2=("s2", "sum"), exp_sw=("exp_sw", "sum"),
    fi=("first_in", "sum"), svpt=("svpt", "sum"), exp_fi=("exp_fi", "sum"), df=("df", "sum"))
g["second_share_vs_own_pp"] = 100 * (g["sw"] - g["exp_sw"]) / g["s2"]
g["first_in_vs_own_pp"] = 100 * (g["fi"] - g["exp_fi"]) / g["svpt"]
# the same under the hypothesis 'exclusive' corrected (svpt + df)
g["second_share_vs_own_if_corrected_pp"] = 100 * (g["sw"] - g["exp_sw"] * (g["s2"] + g["df"]) / g["s2"]) / (g["s2"] + g["df"])
g = g.reset_index()
g.to_csv(rc.OUT / "f1_event_round_baseline.csv", index=False)

# per event (all rounds)
e = y.groupby(["group", "tdate", "tourney_name"]).agg(rows=("svpt", "size"), deffail=("deffail", "sum"),
                                                     sw=("second_won", "sum"), s2=("s2", "sum"), exp_sw=("exp_sw", "sum"),
                                                     fi=("first_in", "sum"), svpt=("svpt", "sum"), exp_fi=("exp_fi", "sum"))
e["second_share_vs_own_pp"] = 100 * (e["sw"] - e["exp_sw"]) / e["s2"]
e["first_in_vs_own_pp"] = 100 * (e["fi"] - e["exp_fi"]) / e["svpt"]
pd.set_option("display.max_rows", 500)
print("per event, 2015 (players with >= 5 inclusive matches elsewhere):")
print(e.reset_index().query("tdate.dt.year == 2015")[["group", "tdate", "tourney_name", "rows", "deffail",
                                                      "second_share_vs_own_pp", "first_in_vs_own_pp"]].round(1).to_string(index=False))
print("\ndistribution of event-level effects, outside vs window:")
print(e.reset_index().groupby("group")[["second_share_vs_own_pp", "first_in_vs_own_pp"]].describe().round(1).T.to_string())
print("\nevent-rounds with >= 12 rows: distribution by group")
gg = g[g["rows"] >= 12]
print(gg.groupby("group")[["second_share_vs_own_pp", "first_in_vs_own_pp"]].describe().round(1).T.to_string())
print("\nwindow and Doha event-rounds (>= 8 rows), lowest second-share effects first:")
print(g[g["group"].isin(["window", "Doha"]) & (g["rows"] >= 8)].sort_values("second_share_vs_own_pp")[
    ["group", "tdate", "tourney_name", "round", "rows", "deffail", "second_share_vs_own_pp", "first_in_vs_own_pp"]]
      .round(1).head(40).to_string(index=False))
print("\noutside event-rounds (>= 8 rows), highest second-share effects first:")
print(g[g["group"].eq("outside") & (g["rows"] >= 8)].sort_values("second_share_vs_own_pp", ascending=False)[
    ["group", "tdate", "tourney_name", "round", "rows", "deffail", "second_share_vs_own_pp", "first_in_vs_own_pp"]]
      .round(1).head(20).to_string(index=False))
print("\nKuala Lumpur, Acapulco, Doha, Monterrey by round:")
print(g[g["tourney_name"].isin(["Kuala Lumpur", "Acapulco", "Doha", "Monterrey"]) & (g["tdate"].dt.year == 2015)][
    ["tourney_name", "round", "rows", "deffail", "second_share_vs_own_pp", "first_in_vs_own_pp"]].round(1).to_string(index=False))
