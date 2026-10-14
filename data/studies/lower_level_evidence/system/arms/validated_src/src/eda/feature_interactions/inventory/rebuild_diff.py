"""How far does the live Stage 0 (rebuilt 6 Oct 2026, 17:07 local) differ from the pre-rebuild copy that the frozen
model frame was built from, on the model population of 2013-2024? (feature-interactions data map, round 0)

Compares, per model match: the player ids and sides, and every per-player and per-match field an interaction feature
might read. Counts only; no outcome is related to anything. Read-only on shared data.
Writes data/studies/feature_interactions/inventory/rebuild_diff.json.
Run: ./python.sh src/eda/feature_interactions/inventory/rebuild_diff.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
S = ROOT / "data" / "studies"
OUT = S / "feature_interactions" / "inventory"
OLD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
MODEL = S / "surface_rating_race" / "model" / "model_frame.parquet"
MATCH_COLS = ["match_id", "player_a_id", "player_b_id", "a_won", "tournament_date", "round", "surface", "indoor",
              "best_of", "draw_size", "status", "score", "minutes", "has_box", "level"]
PLAYER_COLS = ["match_id", "side", "player_id", "rank", "rank_points", "seed", "entry", "age", "height", "hand",
               "country", "ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced",
               "tb_won_n", "tb_won_d", "sets_won_d", "games_won_d"]


def differ(a: pd.Series, b: pd.Series) -> np.ndarray:
    a_na, b_na = a.isna().to_numpy(), b.isna().to_numpy()
    av, bv = a.astype(str).to_numpy(), b.astype(str).to_numpy()
    return (a_na != b_na) | (~a_na & ~b_na & (av != bv))


def main() -> int:
    mf = pd.read_parquet(MODEL, columns=["match_id", "season", "tour"])
    mf = mf[mf["season"] <= 2024].reset_index(drop=True)
    res = {"population_2013_2024": int(len(mf))}
    old_m = mf.merge(pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet", columns=MATCH_COLS),
                     on="match_id", how="left")
    new_m = mf.merge(pd.read_parquet(S / "predictability_diagnostic" / "stage0_matches.parquet", columns=MATCH_COLS),
                     on="match_id", how="left")
    res["model_ids_missing_from_live"] = int(new_m["player_a_id"].isna().sum())
    res["matches_fields_differing"] = {c: int(differ(old_m[c], new_m[c]).sum()) for c in MATCH_COLS[1:]}
    op = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_match_players.parquet", columns=PLAYER_COLS)
    np_ = pd.read_parquet(S / "predictability_diagnostic" / "stage0_match_players.parquet", columns=PLAYER_COLS)
    op = mf[["match_id", "tour", "season"]].merge(op, on="match_id", how="left")
    np_ = mf[["match_id"]].merge(np_, on="match_id", how="left")
    key = ["match_id", "side"]
    j = op.merge(np_, on=key, how="left", suffixes=("_old", "_new"))
    res["player_rows"] = int(len(j))
    res["player_fields_differing"] = {c: int(differ(j[f"{c}_old"], j[f"{c}_new"]).sum()) for c in PLAYER_COLS[2:]}
    by = {}
    for c in ("player_id", "ace", "sv_gms", "minutes"):
        if c == "minutes":
            d = differ(old_m["minutes"], new_m["minutes"])
            by[c] = pd.Series(d).groupby([mf["tour"], mf["season"]]).sum().reset_index(name="n") \
                .query("n > 0").to_dict("records")
        else:
            d = differ(j[f"{c}_old"], j[f"{c}_new"])
            by[c] = pd.Series(d).groupby([j["tour"], j["season"]]).sum().reset_index(name="n") \
                .query("n > 0").to_dict("records")
    res["differing_by_tour_season"] = by
    ex = j[differ(j["player_id_old"], j["player_id_new"])][["match_id", "side", "player_id_old", "player_id_new"]].head(10)
    res["player_id_change_examples"] = ex.to_dict("records")
    # the whole history up to 2024 (every level): what a per-player rebuild from the live tables would read
    om = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet", columns=MATCH_COLS + ["year"])
    nm = pd.read_parquet(S / "predictability_diagnostic" / "stage0_matches.parquet", columns=MATCH_COLS + ["year"])
    om, nm = om[om["year"] <= 2024], nm[nm["year"] <= 2024]
    h = {"old_matches": int(len(om)), "live_matches": int(len(nm)),
         "old_ids_not_in_live": int((~om["match_id"].isin(nm["match_id"])).sum()),
         "live_ids_not_in_old": int((~nm["match_id"].isin(om["match_id"])).sum())}
    jj = om.merge(nm, on="match_id", suffixes=("_old", "_new"))
    h["fields_differing"] = {c: int(differ(jj[f"{c}_old"], jj[f"{c}_new"]).sum()) for c in MATCH_COLS[1:]}
    opa = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_match_players.parquet", columns=PLAYER_COLS)
    npa = pd.read_parquet(S / "predictability_diagnostic" / "stage0_match_players.parquet", columns=PLAYER_COLS)
    keep = set(om["match_id"])
    jp = opa[opa["match_id"].isin(keep)].merge(npa, on=["match_id", "side"], suffixes=("_old", "_new"))
    h["player_rows_compared"] = int(len(jp))
    h["player_fields_differing"] = {c: int(differ(jp[f"{c}_old"], jp[f"{c}_new"]).sum()) for c in PLAYER_COLS[2:]}
    res["history_to_2024_all_levels"] = h
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rebuild_diff.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
