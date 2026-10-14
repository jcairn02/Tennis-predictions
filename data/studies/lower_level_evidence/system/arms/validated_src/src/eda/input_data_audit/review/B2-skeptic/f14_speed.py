"""B2-skeptic review of F14-F16 (serve-speed records). Read-only.

Inputs: data/studies/serve_speed_tabpfn/speed_records.parquet (every record), speed_panel.parquet (the chosen record per
player-match; use = True rows feed spd_L), Stage 0 (box scores, to tell an original block from its copy).

F14  y_raw (first-serve mean as published; key statistics are the integer ceiling of the point mean) against spd_max
     (the same record's fastest serve; shown here to be the player's own: A and B differ in 97% of matches).
     Calibration: the gap max - mean in point-mean records, which are self-consistent by construction.
     For each flagged record: the player's norm (median y of the player's other valid records within +-365 days),
     the other valid records of the same player-match, and the record the panel would fall back to.
F15  men's records with y_raw >= 240.
F16  (a) the same player with identical (y_raw, n, spd2_raw, spd_max) on two matches; (b) matches whose two sides carry
     identical y_raw and n. For each record, its source box (ks_first_in / ks_first_total) against Stage 0's first_in /
     svpt of the player it is linked to, and against the opponent's.

Writes data/studies/input_data_audit/fixes/B2-skeptic/f14_flagged.csv, f15_flagged.csv, f16_pairs.csv, f16_same_sides.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
SP = ROOT / "data/studies/serve_speed_tabpfn"
S0 = ROOT / "data/studies/predictability_diagnostic"
KIND_RANK_SLAM = {"point_mean": 0, "keystat": 1, "mc_floor": 2}
KIND_RANK_TOUR = {"keystat": 0, "point_mean": 1, "mc_floor": 2}
SRC_RANK = {"infosys_slams": 0, "sirgenkii": 1, "infosys": 2, "slam_tracking": 3, "slamtracker": 4, "slam_pbp": 5,
            "mantennisdata": 0, "handoff_ks": 1, "ausopen_mc": 0}


def fallback(rec: pd.DataFrame, excluded: pd.Series) -> pd.DataFrame:
    """The record the panel's choose() would pick per player-match once `excluded` records are not candidates."""
    r = rec[rec["linked"] & rec["valid"] & ~excluded].copy()
    slam = r["level_s0"].eq("GS")
    r["_kind"] = np.where(slam, r["kind"].map(KIND_RANK_SLAM), r["kind"].map(KIND_RANK_TOUR))
    r["_n"] = np.where(r["kind"].eq("point_mean"), -r["n"].fillna(0), 0)
    r["_src"] = r["source"].map(SRC_RANK).fillna(9)
    r = r.sort_values(["match_id", "side", "_kind", "_n", "_src"])
    return r.drop_duplicates(["match_id", "side"]).set_index(["match_id", "side"])


def main() -> None:
    rec = pd.read_parquet(SP / "speed_records.parquet")
    pan = pd.read_parquet(SP / "speed_panel.parquet")
    pid = pan.set_index(["match_id", "side"])["player_id"]
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "player_a_id", "player_b_id", "tournament_date"])
    rec = rec.merge(m, on="match_id", how="left")
    rec["player_id"] = np.where(rec["side"].eq("A"), rec["player_a_id"], rec["player_b_id"])
    rec["tdate"] = pd.to_datetime(rec["tournament_date"])
    rec["gap"] = rec["spd_max"] - rec["y_raw"]
    use = pan[pan["use"]].set_index(["match_id", "side"])
    rec["is_chosen"] = [(mm, s) in use.index and use.loc[(mm, s), "source_key"] == k and use.loc[(mm, s), "source"] == src
                        for mm, s, k, src in zip(rec["match_id"], rec["side"], rec["source_key"], rec["source"])]

    # calibration on point-mean records (self-consistent by construction)
    pm = rec[rec["kind"].eq("point_mean") & rec["valid"] & rec["n"].ge(10) & rec["spd_max"].notna()]
    print("point-mean records n>=10:", len(pm), "| gap (max - mean) quantiles:",
          pm["gap"].quantile([0, .0001, .001, .01, .5]).round(2).to_dict(),
          "| share gap < 2:", round(float((pm["gap"] < 2).mean()), 6), "| share gap < 5:", round(float((pm["gap"] < 5).mean()), 6))
    print("  point-mean sd_within quantiles:", pm["sd_within"].quantile([.001, .01, .5]).round(2).to_dict())
    ks = rec[rec["kind"].eq("keystat") & rec["spd_max"].notna()]
    print("key-statistic records with a max:", len(ks), "| KS >= max - 1:", int((ks["gap"] <= 1).sum()),
          "| KS >= max:", int((ks["gap"] <= 0).sum()), "| KS > max:", int((ks["gap"] < 0).sum()))
    print("   of them chosen (use) rows:", int(((ks["gap"] <= 1) & ks["is_chosen"]).sum()))

    # the player's norm: median y of his other valid records within +-365 days (any source), excluding this match
    v = rec[rec["valid"] & rec["linked"] & rec["player_id"].notna()][["player_id", "match_id", "tdate", "y", "source"]]
    by_player = {k: g for k, g in v.groupby("player_id")}

    def norm(row) -> tuple[float, int]:
        g = by_player.get(row.player_id)
        if g is None:
            return np.nan, 0
        g = g[(g["match_id"] != row.match_id) & ((g["tdate"] - row.tdate).abs() <= pd.Timedelta(days=365))]
        return (float(g["y"].median()) if len(g) else np.nan), int(len(g))

    flag14 = rec["kind"].eq("keystat") & rec["gap"].le(1) & rec["linked"]
    flag15 = rec["tour_s0"].eq("atp") & rec["y_raw"].ge(240) & rec["linked"]
    fb = fallback(rec, flag14 | flag15)
    rows = []
    for r in rec[flag14 | flag15].itertuples():
        nm, nn = norm(r)
        others = rec[(rec["match_id"] == r.match_id) & (rec["side"] == r.side) & rec["valid"]
                     & ~((rec["source"] == r.source) & (rec["source_key"] == r.source_key))]
        key = (r.match_id, r.side)
        f = fb.loc[key] if key in fb.index else None
        rows.append({"match_id": r.match_id, "side": r.side, "source": r.source, "source_key": r.source_key,
                     "player_id": r.player_id, "year": r.year_s0, "level": r.level_s0, "valid_now": r.valid,
                     "chosen_now": r.is_chosen, "y_raw": r.y_raw, "spd_max": r.spd_max, "gap": r.gap, "n": r.n,
                     "spd2_raw": r.spd2_raw, "player_norm": nm, "norm_n": nn, "resid_vs_norm": r.y - nm if nn else np.nan,
                     "other_records": ";".join(f"{o.source}:{o.y:.1f}" for o in others.itertuples()),
                     "fallback_source": None if f is None else f["source"],
                     "fallback_y": None if f is None else f["y"],
                     "fallback_gap": None if f is None else f["spd_max"] - f["y_raw"],
                     "fallback_resid": (None if f is None or not nn else float(f["y"] - nm)),
                     "f14": bool(flag14.loc[r.Index]), "f15": bool(flag15.loc[r.Index])})
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "f14_flagged.csv", index=False)
    f14 = t[t["f14"]]
    print("\nF14 flagged records:", len(f14), "| chosen now:", int(f14["chosen_now"].sum()),
          "| by source:", f14["source"].value_counts().to_dict())
    print("  strictly above max:", int((f14["gap"] < 0).sum()), "| equal:", int((f14["gap"] == 0).sum()),
          "| max - 1:", int((f14["gap"] == 1).sum()))
    print("  resid vs player norm (km/h) quantiles:", f14["resid_vs_norm"].quantile([0, .1, .25, .5, .75, .9, 1]).round(1).to_dict())
    print("  |resid| <= 5 (mean plausible -> the max may be the wrong field):", int((f14["resid_vs_norm"].abs() <= 5).sum()),
          "| resid > +8:", int((f14["resid_vs_norm"] > 8).sum()), "| no norm:", int(f14["resid_vs_norm"].isna().sum()))
    print("  y_raw == spd_max exactly:", int((f14["gap"] == 0).sum()), "of which spd2 missing:",
          int(((f14["gap"] == 0) & f14["spd2_raw"].isna()).sum()))
    print("  fallback exists:", int(f14["fallback_source"].notna().sum()), "| fallback resid quantiles:",
          pd.to_numeric(f14["fallback_resid"]).quantile([0, .5, 1]).round(1).to_dict(),
          "| fallback itself |resid| > 10:", int((pd.to_numeric(f14["fallback_resid"]).abs() > 10).sum()))
    f15 = t[t["f15"]]
    print("\nF15 men's records >= 240:", len(f15), "| chosen now:", int(f15["chosen_now"].sum()), "| also F14:",
          int(f15["f14"].sum()), "| by source:", f15["source"].value_counts().to_dict())
    print(f15[["match_id", "side", "source", "y_raw", "spd_max", "n", "player_norm", "chosen_now", "other_records",
               "fallback_source", "fallback_y", "fallback_resid"]].round(1).to_string())
    # the 240 threshold: the highest men's means among point-mean records
    pmm = rec[rec["kind"].eq("point_mean") & rec["tour_s0"].eq("atp") & rec["valid"] & rec["n"].ge(10)]
    print("men's point-mean records n>=10, top y:", pmm["y_raw"].nlargest(8).round(1).tolist())
    ksm = rec[rec["kind"].eq("keystat") & rec["tour_s0"].eq("atp") & rec["valid"]]
    print("men's key statistics, count by y bands:", pd.cut(ksm["y_raw"], [200, 220, 225, 230, 235, 240, 300]).value_counts().sort_index().to_dict())

    # F16
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "side", "player_id", "first_in", "svpt", "df"])
    box = p.set_index(["match_id", "side"])
    kcols = ["player_id", "y_raw", "n", "spd2_raw", "spd_max"]
    k = rec[rec["linked"] & rec["kind"].eq("keystat")]
    d = k[k.duplicated(kcols, keep=False)].sort_values(kcols + ["tdate"])
    d = d[d.groupby(kcols)["match_id"].transform("nunique") > 1]
    out = []
    for r in d.itertuples():
        own = box.loc[(r.match_id, r.side)] if (r.match_id, r.side) in box.index else None
        opp_side = "B" if r.side == "A" else "A"
        opp = box.loc[(r.match_id, opp_side)] if (r.match_id, opp_side) in box.index else None
        out.append({"player_id": r.player_id, "match_id": r.match_id, "side": r.side, "source": r.source,
                    "source_key": r.source_key, "tdate": r.tdate.date(), "y_raw": r.y_raw, "n": r.n, "spd2_raw": r.spd2_raw,
                    "spd_max": r.spd_max, "ks_first_in": r.ks_first_in, "ks_first_total": r.ks_first_total,
                    "s0_first_in": None if own is None else own["first_in"],
                    "s0_svpt_minus_df": None if own is None else own["svpt"] - own["df"],
                    "s0_opp_first_in": None if opp is None else opp["first_in"],
                    "valid": r.valid, "chosen_now": r.is_chosen})
    dd = pd.DataFrame(out)
    dd["box_matches_own"] = dd["ks_first_in"].eq(dd["s0_first_in"])
    dd.to_csv(OUT / "f16_pairs.csv", index=False)
    print("\nF16(a) key-statistic records sharing (player, y, n, spd2, max) across matches:", len(dd))
    print(dd.to_string())
    # (b) matches whose two sides carry identical y_raw and n (chosen rows)
    u = pan[pan["use"]]
    ab = u.pivot_table(index="match_id", columns="side", values="y_raw", aggfunc="first").dropna()
    abn = u.pivot_table(index="match_id", columns="side", values="n", aggfunc="first").reindex(ab.index)
    same = ab[(ab["A"] == ab["B"]) & (abn["A"] == abn["B"])].index
    sr = u[u["match_id"].isin(same)][["match_id", "side", "source", "source_key", "y_raw", "n", "spd2_raw", "spd_max"]]
    sr = sr.join(box[["first_in", "svpt", "df"]], on=["match_id", "side"])
    rk = rec.set_index(["match_id", "side", "source", "source_key"])[["ks_first_in", "ks_first_total"]]
    sr = sr.join(rk, on=["match_id", "side", "source", "source_key"])
    sr.to_csv(OUT / "f16_same_sides.csv", index=False)
    print("\nF16(b) matches whose two chosen sides carry identical y_raw and n:", len(same))
    print(sr.to_string())


if __name__ == "__main__":
    main()
