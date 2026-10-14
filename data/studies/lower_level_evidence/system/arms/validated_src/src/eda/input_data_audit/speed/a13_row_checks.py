"""Audit step 13: row-level checks on the panel's use rows: duplicates, unit errors (mph), first/second-serve mix-ups,
max-vs-average mix-ups, implausibly slow values, match-level measurement failures (both sides far below their norm),
own-history outliers. Read-only on the repo; writes scratch tables."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_columns", 40)

P = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_panel.parquet")
u = P[P["use"]].copy()
R = pd.read_parquet(SCR / "panel_resid.parquet", columns=["match_id", "side", "resid", "ident"])
u = u.merge(R, on=["match_id", "side"], how="left")
u["grp"] = u["source"] + "|" + u["year"].astype(str)
TEST = u["year"].between(2024, 2026)

print("=== 1. duplicates")
k = ["player_id", "y_raw", "n", "spd2_raw", "spd_max"]
d = u[u.duplicated(k, keep=False) & u["n"].gt(0)].sort_values(k)
print("same player with identical (y_raw, n, spd2_raw, spd_max) on different matches:", len(d))
print(d[["match_id", "side", "player_id", "source", "source_key", "y_raw", "n", "spd2_raw", "spd_max", "obs"]]
      .head(30).to_string(index=False))
ab = u.pivot_table(index="match_id", columns="side", values="y_raw", aggfunc="first").dropna()
abn = u.pivot_table(index="match_id", columns="side", values="n", aggfunc="first").reindex(ab.index)
same = ab[(ab["A"] == ab["B"]) & (abn["A"] == abn["B"])]
print("matches whose two sides carry the identical value and n:", len(same))
sk = u.groupby("source_key")["match_id"].nunique()
print("source records linked to more than one Stage 0 match:", int((sk > 1).sum()))
print(u[u["source_key"].isin(sk[sk > 1].index)][["source", "source_key", "match_id", "side", "y_raw"]].head(20).to_string())

print("\n=== 2. unit errors / implausibly slow (men y < 150, women y < 125)")
slow = u[np.where(u["tour"].eq("atp"), u["y"] < 150, u["y"] < 125)]
print(slow.groupby(["tour", "source", "year"]).size().unstack("year", fill_value=0).to_string())
print("of which in 2024-26:", int(slow["year"].between(2024, 2026).sum()))
# mph test: y_raw * 1.609 lands in the player's usual range? (relative to the player-season mean via the residual)
slow = slow.assign(mph_conv=slow["y_raw"] * 1.609344)
print(slow[["match_id", "side", "player_id", "tour", "source", "year", "y_raw", "n", "spd2_raw", "spd_max", "resid",
            "mph_conv"]].sort_values("y_raw").head(40).round(1).to_string(index=False))

print("\n=== 3. first/second-serve mix-ups: second-serve mean >= first-serve mean (both present, n2 >= 5)")
m = u[u["spd2"].notna() & (u["n2"].fillna(0) >= 5)]
mix = m[m["spd2"] >= m["y"]]
print(f"{len(mix)} of {len(m)}")
print(mix.groupby(["source", "year"]).size().to_string())
print(mix[["match_id", "side", "source", "year", "y", "n", "spd2", "n2", "spd_max"]].head(20).round(1).to_string(index=False))
gap = m.assign(gap=m["y"] - m["spd2"]).groupby(["tour", "source", "year"])["gap"].median().unstack("year").round(1)
print("median first-minus-second gap by source and year (a mix-up would shrink it):")
print(gap.to_string())

print("\n=== 4. max-vs-average: first-serve mean >= the match's fastest serve - 1 km/h")
mm = u[u["spd_max"].notna()]
bad = mm[mm["y_raw"] >= mm["spd_max"] - 1.0]
print(f"{len(bad)} of {len(mm)}")
print(bad.groupby(["source", "year"]).size().to_string())
print(bad[["match_id", "side", "source", "year", "y_raw", "n", "spd2_raw", "spd_max"]].head(20).to_string(index=False))
gm = mm.assign(g=mm["spd_max"] - mm["y_raw"]).groupby(["tour", "source", "year"])["g"].median().unstack("year").round(1)
print("median (max - first-serve mean) by source and year:")
print(gm.to_string())

print("\n=== 5. match-level measurement failures: both sides' residual (vs the same player-season and edition) <= -8")
w = u[u["ident"].fillna(False)].pivot_table(index="match_id", columns="side", values="resid", aggfunc="first").dropna()
both = w[(w["A"] <= -8) & (w["B"] <= -8)]
up = w[(w["A"] >= 8) & (w["B"] >= 8)]
info = u.drop_duplicates("match_id").set_index("match_id")[["tour", "tournament_name", "year", "mq", "round", "source",
                                                             "obs"]]
both = both.join(info)
up = up.join(info)
print(f"both sides <= -8 km/h: {len(both)} matches; both >= +8: {len(up)}")
print(both.groupby(["source", "year"]).size().to_string())
print(both.sort_values("A").head(40).round(1).to_string())
print(up.sort_values("A", ascending=False).head(15).round(1).to_string())
both.to_csv(SCR / "t_match_failures_slow.csv")
up.to_csv(SCR / "t_match_failures_fast.csv")
print("of the slow failures in 2024-26:", int(both["year"].between(2024, 2026).sum()))

print("\n=== 6. own-history outliers (panel flag: > 20 km/h from the player's previous-10 median)")
fo = u[u["flag_own_outlier"]]
print(fo.groupby(["tour", "source", "year"]).size().unstack("year", fill_value=0).to_string())
print("in 2024-26:", int(fo["year"].between(2024, 2026).sum()), "| below the median:", int((fo["resid"] < 0).sum()),
      "above:", int((fo["resid"] > 0).sum()))

print("\n=== 7. residual tails by source and test years (share of |resid| > 10 km/h)")
t = u[u["ident"].fillna(False)].assign(big=lambda x: x["resid"].abs() > 10)
print(t.groupby(["tour", "source"])["big"].agg(["size", "mean"]).round(4).to_string())
print(t[TEST.loc[t.index]].groupby(["tour", "source", "year"])["big"].agg(["size", "mean"]).round(4).to_string())
