"""B1-rederive reviewer: F14, F15, F16 serve-speed records, re-derived from speed_records / speed_panel (read-only).

* F14: records whose first-serve mean (y_raw, as published) is above / at / within 1 km/h of the record's own
  maximum (spd_max: the player's own fastest serve of the match in every source).
* F15: men's records with y_raw >= 240.
* F16: copied blocks: (a) one player, two different matches, identical (y_raw, n, spd2_raw, spd_max);
  (b) one match, both sides identical (y_raw, n, spd2_raw, spd_max).
For each flagged record: is it the value the panel uses (speed_panel use row with the same source and source_key)?
What would the panel take instead (the next valid record by the panel's own ordering, re-implemented), and how
does that compare with the player's other matches (median of his use rows within 365 days, other matches)?
Writes speed_flags.csv and speed_fallbacks.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
SP = ROOT / "data/studies/serve_speed_tabpfn"
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 500)

rec = pd.read_parquet(SP / "speed_records.parquet")
pan = pd.read_parquet(SP / "speed_panel.parquet")
print("records:", len(rec), "by kind/source:")
print(rec.groupby(["kind", "source"]).agg(n=("y_raw", "size"), valid=("valid", "sum"),
                                          with_max=("spd_max", lambda s: int(s.notna().sum()))).to_string())
r = rec.copy()
r["rid"] = np.arange(len(r))
r["gap"] = r.spd_max - r.y_raw
k = r[r.kind.eq("keystat") & r.spd_max.notna()]
print("\nkey statistics with a max: gap (max - mean) quantiles:", k.gap.quantile([0, .001, .005, .01, .05, .5, .95]).round(2).to_dict())
print("gap histogram for keystats (integer bins):")
print(k.gap.clip(-30, 30).round().value_counts().sort_index().loc[-30:12].to_string())
pm = r[r.kind.eq("point_mean") & r.spd_max.notna()]
print("point means: min gap", round(pm.gap.min(), 3), " share gap<=1:", round(float((pm.gap <= 1).mean()), 5))
mc = r[r.kind.eq("mc_floor") & r.spd_max.notna()]
print("AO match centre: min gap", round(mc.gap.min(), 3) if len(mc) else None, " n<=1:", int((mc.gap <= 1).sum()))

# the panel's chosen record for each player-match (source + source_key identify it)
pk = pan[["match_id", "side", "source", "source_key", "use", "drop_reason", "y", "tour", "player_id", "tdate",
          "level", "qualifying", "year"]].rename(columns={"y": "panel_y"})
r = r.merge(pk[["match_id", "side", "source", "source_key", "use", "drop_reason"]].assign(chosen=True),
            on=["match_id", "side", "source", "source_key"], how="left")
r["chosen"] = r.chosen.fillna(False).astype(bool)
r["use"] = r["use"].fillna(False).astype(bool)

r["f14_above"] = r.y_raw > r.spd_max
r["f14_at"] = r.y_raw.eq(r.spd_max)
r["f14_within1"] = (r.y_raw >= r.spd_max - 1) & ~r.f14_above & ~r.f14_at
r["f15_men240"] = r.tour_s0.eq("atp") & (r.y_raw >= 240)
r["men"] = r.tour_s0.eq("atp")

# F16 (a): same player, two different matches, identical block; player from the panel's player id per (match, side)
pid = pan.set_index(["match_id", "side"]).player_id
r["player_id"] = [pid.get((a, b), np.nan) if isinstance(a, str) else np.nan for a, b in zip(r.match_id, r.side)]
blk = ["y_raw", "n", "spd2_raw", "spd_max"]
full = r[r[blk].notna().all(axis=1) & r.player_id.notna() & r.linked]
g = full.groupby(["player_id"] + blk)
dup_a = full[g.match_id.transform("nunique") > 1].sort_values(["player_id", "y_raw", "match_id"])
# (b): both sides of one match identical, same source
two = full.groupby(["match_id", "source"] + blk).side.transform("nunique") > 1
dup_b = full[two].sort_values(["match_id", "source", "side"])
r["f16_player_copy"] = r.rid.isin(dup_a.rid)
r["f16_sides_equal"] = r.rid.isin(dup_b.rid)
# also: identical block on two different matches regardless of player (any id), same source
g2 = full.groupby(["source"] + blk).match_id.transform("nunique")
r["same_block_other_match_any_player"] = r.rid.isin(full[g2 > 1].rid)

flag = r[r.f14_above | r.f14_at | r.f14_within1 | r.f15_men240 | r.f16_player_copy | r.f16_sides_equal]
print("\nF14 above:", int(r.f14_above.sum()), " at:", int(r.f14_at.sum()), " within 1 (not at/above):", int(r.f14_within1.sum()),
      " -> at/above:", int((r.f14_above | r.f14_at).sum()), " total <=1:", int((r.f14_above | r.f14_at | r.f14_within1).sum()))
for name in ("f14_above", "f14_at", "f14_within1", "f15_men240", "f16_player_copy", "f16_sides_equal"):
    x = r[r[name]]
    print(f"  {name}: {len(x)} records; by source {x.source.value_counts().to_dict()}; valid {int(x.valid.sum())}; "
          f"chosen by panel {int(x.chosen.sum())}; chosen & use {int((x.chosen & x.use).sum())}; men {int(x.men.sum())}; "
          f"n<10 {int((x.n < 10).sum())}")
print("F15 men >= 240 also F14 at/above:", int((r.f15_men240 & (r.f14_above | r.f14_at)).sum()),
      " also within 1:", int((r.f15_men240 & r.f14_within1).sum()))
print("F15 men >= 240 rows: ")
print(r[r.f15_men240][["match_id", "side", "source", "source_key", "y_raw", "n", "spd2_raw", "spd_max", "gap", "valid",
                       "invalid_reason", "chosen", "use", "level_s0", "year_s0"]].sort_values("y_raw").to_string())

# player norm: median of the player's other use rows within 365 days (panel y), to judge each flagged record
pu = pan[pan.use][["match_id", "side", "player_id", "tdate", "y"]]
md = pan.set_index(["match_id", "side"]).tdate
r["tdate"] = [md.get((a, b), np.nan) if isinstance(a, str) else np.nan for a, b in zip(r.match_id, r.side)]


def norm(row):
    if pd.isna(row.player_id) or pd.isna(row.tdate):
        return np.nan, 0
    o = pu[pu.player_id.eq(row.player_id) & pu.match_id.ne(row.match_id) & (pu.tdate - row.tdate).abs().le(365)]
    return (float(o.y.median()) if len(o) else np.nan), len(o)


fl = r[r.f14_above | r.f14_at | r.f14_within1 | r.f15_men240 | r.f16_player_copy | r.f16_sides_equal].copy()
nm = [norm(x) for x in fl.itertuples()]
fl["player_norm_y"] = [a for a, b in nm]
fl["player_norm_rows"] = [b for a, b in nm]
fl["y_minus_norm"] = fl.y - fl.player_norm_y


# the next valid record by the panel's ordering, if this record is not a candidate
def order_key(df, level):
    slam = level.eq("GS").to_numpy()
    kind_rank = np.select([df.kind.eq("point_mean"), df.kind.eq("keystat"), df.kind.eq("mc_floor")],
                          [np.where(slam, 0, 1), np.where(slam, 1, 0), 2], 9)
    src_rank = df.source.map({**{s: i for i, s in enumerate(["infosys_slams", "sirgenkii", "infosys", "slam_tracking",
                                                              "slamtracker", "slam_pbp"])},
                              "mantennisdata": 0, "handoff_ks": 1, "ausopen_mc": 0}).fillna(9).to_numpy()
    n_rank = np.where(df.kind.eq("point_mean"), -df.n.fillna(0).to_numpy(), 0)
    return kind_rank, n_rank, src_rank


lev = pan.drop_duplicates("match_id").set_index("match_id").level
fb = []
for x in fl.itertuples():
    same = r[r.match_id.eq(x.match_id) & r.side.eq(x.side) & r.linked]
    cand = same[same.valid & same.rid.ne(x.rid)].copy()
    if len(cand):
        kr, nr, sr = order_key(cand, cand.match_id.map(lev))
        cand = cand.assign(_k=kr, _n=nr, _s=sr).sort_values(["_k", "_n", "_s"])
        nxt = cand.iloc[0]
        fb.append({"rid": x.rid, "next_source": nxt.source, "next_kind": nxt.kind, "next_y": nxt.y, "next_y_raw": nxt.y_raw,
                   "next_n": nxt.n, "next_max": nxt.spd_max, "next_flagged": bool(fl.rid.eq(nxt.rid).any())})
    else:
        fb.append({"rid": x.rid, "next_source": None, "next_kind": None, "next_y": np.nan, "next_y_raw": np.nan,
                   "next_n": np.nan, "next_max": np.nan, "next_flagged": False})
fl = fl.merge(pd.DataFrame(fb), on="rid", how="left")
fl["next_minus_norm"] = fl.next_y - fl.player_norm_y
cols = ["rid", "match_id", "side", "player_id", "source", "kind", "source_key", "tour_s0", "year_s0", "level_s0",
        "round_s0", "y_raw", "y", "n", "spd2_raw", "spd_max", "gap", "valid", "invalid_reason", "chosen", "use",
        "drop_reason", "f14_above", "f14_at", "f14_within1", "f15_men240", "f16_player_copy", "f16_sides_equal",
        "player_norm_y", "player_norm_rows", "y_minus_norm", "next_source", "next_kind", "next_y", "next_n", "next_max",
        "next_flagged", "next_minus_norm"]
fl[cols].to_csv(OUT / "speed_flags.csv", index=False)

f14 = fl[fl.f14_above | fl.f14_at | fl.f14_within1]
print("\nF14 records vs the player's norm (|y - norm|):")
for name in ("f14_above", "f14_at", "f14_within1"):
    x = fl[fl[name]]
    d = x.y_minus_norm.abs()
    print(f"  {name}: {len(x)}; with norm {int(d.notna().sum())}; |y-norm| median {d.median():.1f}; share > 10: "
          f"{(d > 10).mean():.2f}; share <= 5: {(d <= 5).mean():.2f}; chosen&use {int((x.chosen & x.use).sum())}; "
          f"with a fallback {int(x.next_source.notna().sum())}")
print("\nF14 at/above that the panel uses:")
u = fl[(fl.f14_above | fl.f14_at) & fl.chosen & fl.use]
print(u[["match_id", "side", "source", "y_raw", "n", "spd_max", "gap", "player_norm_y", "y_minus_norm", "next_source",
         "next_y", "next_minus_norm"]].to_string())
print("\nF14 within-1 that the panel uses:")
u1 = fl[fl.f14_within1 & fl.chosen & fl.use]
print(u1[["match_id", "side", "source", "y_raw", "n", "spd_max", "gap", "player_norm_y", "y_minus_norm", "next_source",
          "next_y", "next_minus_norm"]].to_string())

print("\nF16 (a) same player, identical block on two matches:")
print(fl[fl.f16_player_copy][["match_id", "side", "player_id", "source", "source_key", "y_raw", "n", "spd2_raw", "spd_max",
                              "chosen", "use", "player_norm_y", "y_minus_norm", "next_source", "next_y"]]
      .sort_values(["player_id", "y_raw"]).to_string())
print("\nF16 (b) both sides of a match identical:")
print(fl[fl.f16_sides_equal][["match_id", "side", "player_id", "source", "source_key", "y_raw", "n", "spd2_raw", "spd_max",
                              "chosen", "use", "player_norm_y", "y_minus_norm", "next_source", "next_y"]]
      .sort_values(["match_id", "side"]).to_string())
