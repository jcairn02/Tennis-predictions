"""B1-rederive reviewer: F14 physical bound and the 7 doubtful fallbacks (read-only).

1. (max - mean) of point-level records (computed from the serves themselves) with n >= 10: the physical range.
2. The 7 player-matches whose fallback is > 10 km/h from the player's norm: every record of both sides.
3. The 2 R_above records with n < 10 and the R_above records the panel does not choose.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
SP = ROOT / "data/studies/serve_speed_tabpfn"
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)

r = pd.read_parquet(SP / "speed_records.parquet")
pan = pd.read_parquet(SP / "speed_panel.parquet")
r["gap"] = r.spd_max - r.y_raw
pm = r[r.kind.eq("point_mean") & r.n.ge(10) & r.spd_max.notna() & r.valid]
print("point-level records n>=10:", len(pm))
print(" (max - mean) quantiles:", pm.gap.quantile([0, 1e-4, 1e-3, .01, .05, .5]).round(2).to_dict())
print(" smallest 10 gaps:", pm.nsmallest(10, "gap")[["source", "match_id", "side", "y_raw", "n", "spd_max", "gap"]].to_string())
for lo in (20, 40, 60):
    x = pm[pm.n >= lo]
    print(f" n>={lo}: min gap {x.gap.min():.2f}, 0.1% quantile {x.gap.quantile(.001):.2f}")
# by tour
print(pm.groupby(r.tour_s0).gap.describe(percentiles=[.001, .01]).round(2).to_string())
# key statistics, gap by n
ks = r[r.kind.eq("keystat") & r.spd_max.notna() & r.n.ge(10)]
print("\nkeystats n>=10:", len(ks), "gap<=1:", int((ks.gap <= 1).sum()), "gap<=0:", int((ks.gap <= 0).sum()),
      "gap<0:", int((ks.gap < 0).sum()), " gap 2..4:", int(ks.gap.between(2, 4).sum()))

eff = pd.read_csv(OUT / "speed_rule_effects.csv")
bad = eff[eff.rule.eq("R_above") & eff.cur_use & (eff.fb_minus_norm.abs() > 10)]
for x in bad.itertuples():
    allr = r[r.match_id.eq(x.match_id)][["match_id", "side", "source", "source_key", "y_raw", "n", "spd2_raw",
                                          "spd_max", "valid", "invalid_reason"]]
    pl = pan[pan.match_id.eq(x.match_id)][["side", "player_id", "use", "source", "y"]]
    print("\n###", x.match_id, "flagged side", x.side, "player", x.player_id, "norm", round(x.norm, 1))
    print(allr.sort_values(["side", "source"]).to_string(index=False))
    print(pl.to_string(index=False))
    # the player's other recent use rows
    o = pan[pan.player_id.eq(x.player_id) & pan.use].sort_values("tdate")
    o = o[(o.tdate - pan.loc[pan.match_id.eq(x.match_id), "tdate"].iloc[0]).abs().le(365)]
    print("   player's use rows within 365 d:", o[["tournament_name", "year", "round", "source", "y"]].values.tolist()[:30])

ab = r[r.kind.eq("keystat") & (r.y_raw > r.spd_max)]
print("\nR_above with n < 10:")
print(ab[ab.n < 10][["match_id", "side", "source", "y_raw", "n", "spd_max", "valid", "invalid_reason"]].to_string())
