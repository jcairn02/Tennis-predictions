"""Read-only checks of how per-player values join to the frozen model frame (feature-interactions data map, round 0).

Questions:
  1. Is the model frame's side A Stage 0's player_a_id? (checked through values that only agree if the sides agree:
     a_won, the market's A probability, age, overall Elo, the surface-IOS per-player columns, the Elo-pieces pairs)
  2. Do the per-player tables with _a/_b columns use the same A (surface_features, pieces, stage1_baselines,
     stage3_ratings, ttt_offset, rating_systems stageA_ratings, ufc_ideas stageA_bt / stageB_ios)?
  3. After the Stage 0 rebuild of 6 Oct 2026 (17:07 local; folder rebuilds/2026-10-07T0005Z), which model match ids are
     missing from the live tables, and does the side A of a re-keyed match stay the same player?

Only seasons 2013-2024 are used for any value comparison (2025-2026 stay closed); the id checks count ids only.
Reads the pre-rebuild Stage 0 copies under data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/ and the live
tables; writes data/studies/feature_interactions/inventory/orientation.json.
Run: ./python.sh src/eda/feature_interactions/inventory/orientation.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[4]
S = ROOT / "data" / "studies"
OUT = S / "feature_interactions" / "inventory"
REBUILD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z"
OLD = REBUILD / "replaced" / "data" / "studies"
MODEL = S / "surface_rating_race" / "model" / "model_frame.parquet"
L10 = float(np.log(10) / 400.0)
LAST_OPEN_SEASON = 2024


def side_is_low(match_id: str) -> bool:
    """Stage 0's side rule (src/eda/predictability_diagnostic/common.py: side_is_low), copied to avoid importing a
    module under edit: the lower-sorted player id is side A when one bit of a hash of match_id is 0."""
    return int(hashlib.sha256(match_id.encode("utf-8")).hexdigest()[:8], 16) % 2 == 0


def gap(x, y) -> dict:
    x, y = np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64")
    both = np.isfinite(x) & np.isfinite(y)
    return {"compared": int(both.sum()), "max_abs_gap": float(np.max(np.abs(x[both] - y[both]))) if both.any() else None,
            "share_equal_1e-9": float(np.mean(np.abs(x[both] - y[both]) < 1e-9)) if both.any() else None,
            "corr": float(np.corrcoef(x[both], y[both])[0, 1]) if both.sum() > 2 else None,
            "missing_pattern_equal": bool(np.array_equal(np.isfinite(x), np.isfinite(y)))}


def main() -> int:
    res: dict = {}
    mf_all = pd.read_parquet(MODEL)
    res["model_rows_by_season_tour"] = mf_all.groupby(["season", "tour"]).size().rename("n").reset_index().to_dict("records")
    ids_all = mf_all["match_id"]
    mf = mf_all[mf_all["season"] <= LAST_OPEN_SEASON].reset_index(drop=True)      # values: 2013-2024 only
    res["value_rows_2013_2024"] = int(len(mf))

    # 1. Stage 0 before the rebuild (the frozen model frame's source)
    m0 = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                         columns=["match_id", "player_a_id", "player_b_id", "a_won", "year", "tour"])
    p0 = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_match_players.parquet",
                         columns=["match_id", "player_id", "side", "player_name", "age"])
    res["model_ids_in_old_stage0"] = float(ids_all.isin(m0["match_id"]).mean())
    j = mf[["match_id", "a_won", "p_mkt", "in_age", "in_odds_logit"]].merge(m0, on="match_id", how="left",
                                                                             validate="one_to_one", suffixes=("", "_s0"))
    res["a_won_equals_old_stage0"] = float((j["a_won"].astype(bool) == j["a_won_s0"].astype(bool)).mean())
    # the side A row of stage0_match_players is player_a_id
    pa = p0[p0["side"] == "A"].set_index("match_id")["player_id"]
    res["players_side_A_is_player_a_id"] = float((m0.set_index("match_id")["player_a_id"].reindex(pa.index) == pa).mean())
    # side rule reproduces player_a_id (lower-sorted id is A when the hash bit is 0)
    smp = m0.sample(20000, random_state=0)
    lo = np.where(smp["player_a_id"] < smp["player_b_id"], smp["player_a_id"], smp["player_b_id"])
    rule = np.array([side_is_low(m) for m in smp["match_id"]])
    res["side_rule_reproduces_player_a_id_sample"] = float(np.mean((smp["player_a_id"].to_numpy() == lo) == rule))
    # age difference from the per-player rows
    age = p0.pivot_table(index="match_id", columns="side", values="age", aggfunc="first")
    ok = lambda a: np.where((a >= 14) & (a <= 50), a - 25.0, np.nan)            # noqa: E731  stage4's AGE_RANGE, centre
    a_ = age.reindex(mf["match_id"])
    res["in_age_vs_stage0_ageA_minus_ageB"] = gap(mf["in_age"], ok(a_["A"].to_numpy()) - ok(a_["B"].to_numpy()))
    res["in_age_sq_vs_stage0"] = gap(mf["in_age_sq"], ok(a_["A"].to_numpy()) ** 2 - ok(a_["B"].to_numpy()) ** 2)
    # the market's A probability (stage 1 odds before the rebuild): p_mkt and odds_logit
    o0 = pd.read_parquet(OLD / "predictability_diagnostic" / "stage1_odds.parquet", columns=["match_id", "p_avg_a", "p_ps_a"])
    oj = mf[["match_id", "p_mkt", "in_odds_logit"]].merge(o0, on="match_id", how="left", validate="one_to_one")
    res["p_mkt_vs_stage1_odds_p_avg_a"] = gap(oj["p_mkt"], oj["p_avg_a"])
    res["in_odds_logit_vs_logit_p_avg_a"] = gap(oj["in_odds_logit"], logit(np.clip(oj["p_avg_a"], 1e-9, 1 - 1e-9)))

    # 2. per-player tables with _a/_b columns
    pc = pd.read_parquet(S / "surface_elo_pieces" / "pieces.parquet",
                         columns=["match_id", "R_a", "R_b", "D_a", "D_b", "season_n_a", "season_n_b"])
    pj = mf[["match_id", "in_elo_overall", "in_elo_surf_offset", "in_surf_season_a", "in_surf_season_b"]] \
        .merge(pc, on="match_id", how="left", validate="one_to_one")
    res["in_elo_overall_vs_pieces_L10(R_a-R_b)"] = gap(pj["in_elo_overall"], L10 * (pj["R_a"] - pj["R_b"]))
    res["in_elo_surf_offset_vs_pieces_L10(D_a-D_b)"] = gap(pj["in_elo_surf_offset"],
                                                          L10 * (pj["D_a"].fillna(0) - pj["D_b"].fillna(0)))
    res["in_surf_season_a_vs_log1p(season_n_a)"] = gap(pj["in_surf_season_a"], np.log1p(pj["season_n_a"]))
    sf = pd.read_parquet(S / "surface_ios" / "surface_features.parquet")
    sj = mf[["match_id"] + [c for c in mf.columns if c.startswith(("in_iosO_", "in_iosD_", "in_prod_"))]] \
        .merge(sf, on="match_id", how="left", validate="one_to_one")
    for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"):
        oa, ob = sj[f"srf_O_eff_{s}_a"], sj[f"srf_O_eff_{s}_b"]
        da, db = sj[f"srf_D_eff_{s}_a"], sj[f"srf_D_eff_{s}_b"]
        res[f"in_iosO_{s}_vs_srf_O_eff_a-b"] = gap(sj[f"in_iosO_{s}"], oa - ob)
        res[f"in_iosD_{s}_vs_srf_D_eff_a-b"] = gap(sj[f"in_iosD_{s}"], da - db)
        res[f"in_prod_{s}_vs_Oa(-Db)-Ob(-Da)"] = gap(sj[f"in_prod_{s}"], oa * (-db) - ob * (-da))
    # Stage 1's Elo (per player) against the model's elo_overall: same orientation if strongly positively correlated
    b1 = pd.read_parquet(S / "predictability_diagnostic" / "stage1_baselines.parquet",
                         columns=["match_id", "elo_a_ret", "elo_b_ret", "p_market"])
    bj = mf[["match_id", "in_elo_overall", "p_mkt"]].merge(b1, on="match_id", how="left", validate="one_to_one")
    res["in_elo_overall_vs_stage1_L10(elo_a_ret-elo_b_ret)"] = gap(bj["in_elo_overall"], L10 * (bj["elo_a_ret"] - bj["elo_b_ret"]))
    res["p_mkt_vs_stage1_p_market"] = gap(bj["p_mkt"], bj["p_market"])
    s3 = pd.read_parquet(S / "predictability_diagnostic" / "stage3_ratings.parquet",
                         columns=["match_id", "serve_a", "serve_b", "return_a", "return_b"])
    tj = mf[["match_id", "in_ratings_iid"]].merge(s3, on="match_id", how="left", validate="one_to_one")
    res["in_ratings_iid_vs_stage3_(serve_a-return_b)-(serve_b-return_a)"] = gap(
        tj["in_ratings_iid"], (tj["serve_a"] - tj["return_b"]) - (tj["serve_b"] - tj["return_a"]))
    to = pd.read_parquet(S / "surface_rating_race" / "ttt_offset.parquet", columns=["match_id", "mu_a", "mu_b"])
    oj2 = mf[["match_id", "in_elo_overall"]].merge(to, on="match_id", how="left", validate="one_to_one")
    res["in_elo_overall_vs_ttt_offset_mu_a-mu_b"] = gap(oj2["in_elo_overall"], oj2["mu_a"] - oj2["mu_b"])
    gl = pd.read_parquet(S / "rating_systems" / "stageA_ratings.parquet",
                         columns=["match_id", "glicko2m_mu_a", "glicko2m_mu_b"])
    gj = mf[["match_id", "in_elo_overall"]].merge(gl, on="match_id", how="left", validate="one_to_one")
    res["in_elo_overall_vs_glicko2m_mu_a-mu_b"] = gap(gj["in_elo_overall"], gj["glicko2m_mu_a"] - gj["glicko2m_mu_b"])
    bt = pd.read_parquet(S / "ufc_ideas" / "stageA_bt.parquet", columns=["match_id", "bt_a", "bt_b"])
    btj = mf[["match_id", "in_elo_overall"]].merge(bt, on="match_id", how="left", validate="one_to_one")
    res["in_elo_overall_vs_bt_a-bt_b"] = gap(btj["in_elo_overall"], btj["bt_a"] - btj["bt_b"])
    ios = pd.read_parquet(S / "ufc_ideas" / "stageB_ios.parquet", columns=["match_id", "O_ace_a", "O_ace_b"])
    ij = mf[["match_id", "in_iosO_ace"]].merge(ios, on="match_id", how="left", validate="one_to_one")
    res["in_iosO_ace_vs_weekly_stageB_ios_O_ace_a-b"] = gap(ij["in_iosO_ace"], ij["O_ace_a"] - ij["O_ace_b"])
    me = pd.read_parquet(S / "ufc_ideas" / "stageA_mesr.parquet", columns=["match_id", "mesr_a", "mesr_b"])
    mj = mf[["match_id", "in_odds_logit"]].merge(me, on="match_id", how="left", validate="one_to_one")
    res["in_odds_logit_vs_mesr_a-mesr_b"] = gap(mj["in_odds_logit"], mj["mesr_a"] - mj["mesr_b"])
    sd = pd.read_parquet(S / "shot_level" / "stage3_sides.parquet", columns=["match_id", "p_serve_a", "p_serve_b"])
    s3b = pd.read_parquet(S / "predictability_diagnostic" / "stage3_ratings.parquet",
                          columns=["match_id", "p_serve_a", "p_serve_b"])
    sdj = mf[["match_id"]].merge(sd, on="match_id", how="left").merge(s3b, on="match_id", how="left",
                                                                      suffixes=("_sides", "_s3"))
    res["shot_sides_p_serve_a_vs_stage3_p_serve_a"] = gap(sdj["p_serve_a_sides"], sdj["p_serve_a_s3"])
    s2 = pd.read_parquet(S / "predictability_diagnostic" / "stage2_matches.parquet", columns=["match_id", "player_id_a"])
    s2j = s2.merge(m0[["match_id", "player_a_id"]], on="match_id", how="inner")
    res["stage2_matches_player_id_a_is_player_a_id"] = float((s2j["player_id_a"] == s2j["player_a_id"]).mean())
    # per-player-match rows (two per match) keyed by player_id and side
    adj = pd.read_parquet(S / "ufc_ideas" / "stageB_adj.parquet", columns=["match_id", "player_id", "side"])
    aj = adj.merge(m0[["match_id", "player_a_id"]], on="match_id", how="inner")
    res["stageB_adj_side_A_is_player_a_id"] = float(((aj["side"] == "A") == (aj["player_id"] == aj["player_a_id"])).mean())
    sl = pd.read_parquet(S / "shot_level" / "stage1_match_stats.parquet", columns=["match_id", "side", "player_id"])
    sj2 = sl.merge(m0[["match_id", "player_a_id"]], on="match_id", how="inner")
    res["shot_level_stage1_side_A_is_player_a_id"] = float(((sj2["side"] == "A") == (sj2["player_id"] == sj2["player_a_id"])).mean())

    # 3. the rebuild: ids and sides
    m1 = pd.read_parquet(S / "predictability_diagnostic" / "stage0_matches.parquet",
                         columns=["match_id", "player_a_id", "player_b_id", "year", "tour"])
    p1 = pd.read_parquet(S / "predictability_diagnostic" / "stage0_match_players.parquet",
                         columns=["match_id", "side", "player_name"])
    idm = pd.read_csv(REBUILD / "id_map.csv")
    res["id_map_rows"] = int(len(idm))
    res["id_map_by_tour_year"] = idm.assign(year=idm["tournament_id"].str.slice(0, 4)).groupby(["tour", "year"]).size() \
        .rename("n").reset_index().to_dict("records")
    missing = ids_all[~ids_all.isin(m1["match_id"])]
    res["model_ids_missing_from_live_stage0"] = int(len(missing))
    res["model_ids_missing_by_season"] = mf_all[mf_all["match_id"].isin(missing)].groupby(["season", "tour"]).size() \
        .rename("n").reset_index().to_dict("records")
    res["missing_model_ids_covered_by_id_map"] = int(missing.isin(idm["old_match_id"]).sum())
    # side A's name before and after for the re-keyed model matches (ids and names only)
    nm0 = p0[p0["side"] == "A"].set_index("match_id")["player_name"]
    nm1 = p1[p1["side"] == "A"].set_index("match_id")["player_name"]
    mm = idm[idm["old_match_id"].isin(ids_all)].copy()
    mm["A_before"] = mm["old_match_id"].map(nm0)
    mm["A_after"] = mm["new_match_id"].map(nm1)
    mm["side_A_same_player"] = mm["A_before"].str.lower().str.strip() == mm["A_after"].str.lower().str.strip()
    res["rekeyed_model_matches"] = int(len(mm))
    res["rekeyed_model_matches_side_A_same_player"] = int(mm["side_A_same_player"].sum())
    res["rekeyed_examples"] = mm[["old_match_id", "new_match_id", "A_before", "A_after", "side_A_same_player"]] \
        .head(12).to_dict("records")
    # other model ids the rebuild changed without an id_map row (should be none)
    res["model_ids_missing_live_without_map"] = missing[~missing.isin(idm["old_match_id"])].head(20).tolist()
    # the frozen leak-proof tables vs the live ones: which model ids are absent from the live versions
    for name in ("leakproof_features", "perplayer_features", "ios_features"):
        live = pd.read_parquet(S / "match_timing" / f"{name}.parquet", columns=["match_id"])
        old = pd.read_parquet(OLD / "match_timing" / f"{name}.parquet", columns=["match_id"])
        res[f"model_ids_missing_from_live_{name}"] = int((~ids_all.isin(live["match_id"])).sum())
        res[f"model_ids_missing_from_old_{name}"] = int((~ids_all.isin(old["match_id"])).sum())
    tl = pd.read_parquet(S / "match_timing" / "timing.parquet", columns=["match_id"])
    to_ = pd.read_parquet(OLD / "match_timing" / "timing.parquet", columns=["match_id"])
    res["model_ids_missing_from_live_timing"] = int((~ids_all.isin(tl["match_id"])).sum())
    res["model_ids_missing_from_old_timing"] = int((~ids_all.isin(to_["match_id"])).sum())

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "orientation.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for k, v in res.items():
        if k in ("model_rows_by_season_tour",):
            continue
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
