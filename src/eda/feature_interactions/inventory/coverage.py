"""Read-only coverage of every feature and raw field on the frozen model population (feature-interactions data map).

Population: the 58-input model frame (data/studies/surface_rating_race/model/model_frame.parquet), seasons 2013-2024
only. 2025-2026 rows are dropped right after loading (they are the closed test; only their row counts are reported, by
orientation.py). Coverage = share of the population's matches where the value exists, by tour and period:
    d = 2013-2021 (discovery), r = 2022-2024 (replication)
For per-player fields "exists" means both players have it (a difference or interaction needs both); for seed and entry
it means at least one player has a value (missing = unseeded / direct acceptance).

Stage 0 and the tables rebuilt on 6 Oct 2026 are read from the pre-rebuild copies (data/studies/data_continuity/
rebuilds/2026-10-07T0005Z/replaced/), which are the frozen model frame's sources; no 2013-2024 model match is re-keyed.

Writes data/studies/feature_interactions/inventory/:
    coverage_all.csv         table, column, n and share for (atp|wta) x (d|r)
    coverage_by_season.csv   a few key fields by tour and season (2013-2024)
    raw_values.json          value counts of categorical raw fields on the population
Run: ./python.sh src/eda/feature_interactions/inventory/coverage.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
S = ROOT / "data" / "studies"
OUT = S / "feature_interactions" / "inventory"
OLD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
MODEL = S / "surface_rating_race" / "model" / "model_frame.parquet"
LAST_OPEN_SEASON = 2024
CELLS = [(t, p) for t in ("atp", "wta") for p in ("d", "r")]

# match-keyed tables of built features (path, label); every numeric column is covered
FEATURE_TABLES = [
    (S / "predictability_diagnostic" / "stage4_features.parquet", "stage4_features"),
    (S / "predictability_diagnostic" / "stage1_baselines.parquet", "stage1_baselines"),
    (S / "predictability_diagnostic" / "stage3_ratings.parquet", "stage3_ratings"),
    (S / "predictability_diagnostic" / "audit4" / "lag_features.parquet", "audit4_lag_features"),
    (S / "ufc_ideas" / "stageA_bt.parquet", "ufc_stageA_bt"),
    (S / "ufc_ideas" / "stageA_mesr.parquet", "ufc_stageA_mesr"),
    (S / "ufc_ideas" / "stageA_features.parquet", "ufc_stageA_features"),
    (S / "ufc_ideas" / "stageB_adj_features.parquet", "ufc_stageB_adj_features"),
    (S / "ufc_ideas" / "stageB_ios.parquet", "ufc_stageB_ios"),
    (S / "ufc_ideas" / "stageB_ios_features.parquet", "ufc_stageB_ios_features"),
    (S / "ufc_ideas" / "stageB_split_features.parquet", "ufc_stageB_split_features"),
    (S / "ufc_ideas" / "stageB_features.parquet", "ufc_stageB_features"),
    (S / "ufc_ideas" / "stageC_features.parquet", "ufc_stageC_features"),
    (S / "ufc_ideas" / "stageC_fatigue_part.parquet", "ufc_stageC_fatigue_part"),
    (S / "ufc_ideas" / "stageC_sos_part.parquet", "ufc_stageC_sos_part"),
    (S / "ufc_ideas" / "stageD_features.parquet", "ufc_stageD_features"),
    (S / "ufc_ideas" / "stageD_profile_features.parquet", "ufc_stageD_profile_features"),
    (S / "rating_systems" / "stageA_ratings.parquet", "rating_systems_stageA_ratings"),
    (S / "rating_systems" / "stageA_ttt_hold.parquet", "rating_systems_stageA_ttt_hold"),
    (S / "rating_systems" / "stageB_features.parquet", "rating_systems_stageB_features"),
    (OLD / "match_timing" / "ttt_timed.parquet", "match_timing_ttt_timed(pre-rebuild)"),
    (OLD / "match_timing" / "leakproof_features.parquet", "match_timing_leakproof_features(pre-rebuild)"),
    (S / "surface_rating_race" / "ttt_offset.parquet", "surface_rating_race_ttt_offset"),
    (S / "surface_elo_pieces" / "pieces.parquet", "surface_elo_pieces_pieces"),
    (S / "surface_ios" / "surface_features.parquet", "surface_ios_surface_features"),
    (S / "surface_ios" / "subgroups.parquet", "surface_ios_subgroups"),
    (S / "market_anchoring" / "surface_stat_features.parquet", "market_anchoring_surface_stat_features"),
    (S / "predictive_frontier" / "frontier_features.parquet", "predictive_frontier_frontier_features"),
    (S / "shot_level" / "stage2_features.parquet", "shot_level_stage2_features"),
    (S / "shot_level" / "stage3_sides.parquet", "shot_level_stage3_sides"),
    (S / "predictability_diagnostic" / "stage2_matches.parquet", "stage2_matches(post-match)"),
]
SKIP_COLS = {"match_id", "tour", "year", "group", "evaluation", "status", "a_won", "order", "order_x", "order_y", "era",
             "tournament_id", "tournament_date", "level", "qualifying", "round", "round_order", "surface",
             "tournament_name", "season", "week"}


def model_population() -> pd.DataFrame:
    mf = pd.read_parquet(MODEL)
    mf = mf[mf["season"] <= LAST_OPEN_SEASON].reset_index(drop=True)
    mf["period"] = np.where(mf["season"] <= 2021, "d", "r")
    return mf


def shares(mf: pd.DataFrame, exists: dict[str, np.ndarray], table: str) -> list[dict]:
    rows = []
    for col, ok in exists.items():
        r = {"table": table, "column": col}
        for t, p in CELLS:
            m = (mf["tour"].to_numpy() == t) & (mf["period"].to_numpy() == p)
            r[f"n_{t}_{p}"] = int(m.sum())
            r[f"cov_{t}_{p}"] = round(float(ok[m].mean()), 4) if m.any() else np.nan
        rows.append(r)
    return rows


def finite(x) -> np.ndarray:
    v = pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(dtype="float64")
    return np.isfinite(v)


def read_on_model(path: Path, ids: pd.Series, cols: list[str] | None = None) -> pd.DataFrame:
    t = pq.read_table(path, columns=cols, filters=[("match_id", "in", list(ids))])
    d = t.to_pandas()
    if d["match_id"].duplicated().any():
        raise ValueError(f"{path.name}: duplicated match_id")
    return ids.to_frame().merge(d, on="match_id", how="left")


def rest_days(ids: pd.Series) -> tuple[tuple[np.ndarray, np.ndarray], np.ndarray]:
    """For A and B of each model match: this match's earliest possible start minus the player's previous match's
    latest possible finish, in days (the least rest the clock allows), and whether both previous matches have an exact
    day. Previous = the player's latest earlier match in Stage 0's chronological order (any level). Pre-rebuild tables."""
    m = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                        columns=["match_id", "order", "player_a_id", "player_b_id"])
    tm = pd.read_parquet(OLD / "match_timing" / "timing.parquet", columns=["match_id", "es", "lf", "exact"])
    m = m.merge(tm, on="match_id", how="left")
    long = pd.concat([m.assign(pid=m["player_a_id"], side="A"), m.assign(pid=m["player_b_id"], side="B")])
    long = long.sort_values(["pid", "order"], kind="mergesort")
    g = long.groupby("pid", sort=False)
    long["prev_lf"] = g["lf"].shift(1)
    long["prev_exact"] = g["exact"].shift(1)
    long["rest_min"] = long["es"] - long["prev_lf"]
    out, ex = [], []
    for side in ("A", "B"):
        s = long[long["side"] == side].set_index("match_id")
        out.append(ids.map(s["rest_min"]).to_numpy(dtype="float64"))
        ex.append(ids.map(s["prev_exact"]).fillna(False).to_numpy(dtype=bool))
    return (out[0], out[1]), ex[0] & ex[1]


def feature_tables(mf: pd.DataFrame) -> list[dict]:
    out = []
    for path, label in FEATURE_TABLES:
        names = [n for n in pq.read_schema(path).names if n not in SKIP_COLS and n != "__index_level_0__"]
        for i in range(0, len(names), 80):
            chunk = names[i:i + 80]
            d = read_on_model(path, mf["match_id"], ["match_id"] + chunk)
            ex = {}
            for c in chunk:
                if not pd.api.types.is_numeric_dtype(d[c]) and not pd.api.types.is_bool_dtype(d[c]):
                    ex[c] = d[c].notna().to_numpy()
                else:
                    ex[c] = finite(d[c])
            out += shares(mf, ex, label)
        print(f"  {label}: {len(names)} columns", flush=True)
    return out


def raw_fields(mf: pd.DataFrame) -> tuple[list[dict], dict]:
    out, values = [], {}
    ids = mf["match_id"]
    # Stage 0 matches (pre-rebuild)
    m = read_on_model(OLD / "predictability_diagnostic" / "stage0_matches.parquet", ids)
    ex = {"minutes": finite(m["minutes"]), "score": m["score"].notna().to_numpy(),
          "indoor": m["indoor"].notna().to_numpy(), "draw_size": finite(m["draw_size"]),
          "best_of": finite(m["best_of"]), "has_box(match)": m["has_box"].fillna(False).to_numpy(dtype=bool),
          "status_retired(share, not coverage)": m["status"].eq("retired").to_numpy(),
          "score_has_tiebreak(share, not coverage)": m["score"].fillna("").str.contains(r"7-6|6-7").to_numpy(),
          "box_status_full(share)": m["box_status"].eq("full").to_numpy()}
    out += shares(mf, ex, "stage0_matches(pre-rebuild)")
    values["box_status"] = m["box_status"].value_counts(dropna=False).to_dict()
    # Stage 0 per-player rows (pre-rebuild): both sides
    pcols = ["match_id", "side", "rank", "rank_points", "seed", "entry", "age", "height", "hand", "country", "has_box",
             "ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced",
             "tb_won_n", "tb_won_d", "sets_won_d", "games_won_d"]
    p = pq.read_table(OLD / "predictability_diagnostic" / "stage0_match_players.parquet", columns=pcols,
                      filters=[("match_id", "in", list(ids))]).to_pandas()
    A = ids.to_frame().merge(p[p["side"] == "A"], on="match_id", how="left")
    B = ids.to_frame().merge(p[p["side"] == "B"], on="match_id", how="left")
    ex = {}
    for c in ["rank", "rank_points", "age", "height", "ace", "df", "svpt", "first_in", "first_won", "second_won",
              "sv_gms", "bp_saved", "bp_faced", "tb_won_d", "sets_won_d", "games_won_d"]:
        ex[f"{c}(both)"] = finite(A[c]) & finite(B[c])
    ex["hand_known(both, L or R)"] = A["hand"].isin(["L", "R"]).to_numpy() & B["hand"].isin(["L", "R"]).to_numpy()
    ex["country(both)"] = A["country"].notna().to_numpy() & B["country"].notna().to_numpy()
    ex["has_box(both)"] = A["has_box"].fillna(False).to_numpy(dtype=bool) & B["has_box"].fillna(False).to_numpy(dtype=bool)
    ex["seed(either; missing=unseeded)"] = finite(A["seed"]) | finite(B["seed"])
    ex["entry(either; missing=direct)"] = A["entry"].notna().to_numpy() | B["entry"].notna().to_numpy()
    ex["lefty_in_match(share)"] = A["hand"].eq("L").to_numpy() | B["hand"].eq("L").to_numpy()
    ex["tiebreak_played(share)"] = (pd.to_numeric(A["tb_won_d"], errors="coerce").fillna(0) > 0).to_numpy()
    ex["same_country(share)"] = (A["country"] == B["country"]).fillna(False).to_numpy(dtype=bool)
    out += shares(mf, ex, "stage0_match_players(pre-rebuild)")
    values["entry"] = pd.concat([A["entry"], B["entry"]]).value_counts(dropna=False).to_dict()
    values["hand"] = pd.concat([A["hand"], B["hand"]]).value_counts(dropna=False).to_dict()
    # the match clock (pre-rebuild)
    tm = read_on_model(OLD / "match_timing" / "timing.parquet", ids,
                       ["match_id", "es", "lf", "start", "obs", "width_days", "exact", "n_sources", "conflict",
                        "window_basis"])
    ex = {"es_lf(both finite)": finite(tm["es"]) & finite(tm["lf"]), "exact_day(share)": tm["exact"].fillna(False).to_numpy(dtype=bool),
          "width_1_day(share; an exact local day)": (tm["width_days"].to_numpy() == 1),
          "n_sources>=2(share)": (pd.to_numeric(tm["n_sources"], errors="coerce").fillna(0) >= 2).to_numpy(),
          "conflict(share)": tm["conflict"].fillna(False).to_numpy(dtype=bool)}
    values["timing_window_basis"] = tm["window_basis"].value_counts(dropna=False).to_dict()
    values["timing_width_days_quantiles"] = {str(q): float(tm["width_days"].quantile(q)) for q in (0.5, 0.9, 0.99)}
    values["timing_width_days_counts"] = tm["width_days"].value_counts().sort_index().to_dict()
    # rest before the match from the clock: each player's previous match (any level, Stage 0's order)
    rest, prev_exact = rest_days(ids)
    ex["rest_min_days(both players have a previous match)"] = np.isfinite(rest[0]) & np.isfinite(rest[1])
    ex["rest_both_prev_exact_and_this_exact(share)"] = prev_exact & tm["exact"].fillna(False).to_numpy(dtype=bool)
    r_all = np.concatenate(rest)
    r_all = r_all[np.isfinite(r_all)]
    values["rest_min_days_quantiles(per player-match, model population)"] = {
        str(q): float(np.quantile(r_all, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}
    # start time of day: any link file with a start_utc (pre-rebuild copies)
    starts = set()
    for f in sorted((OLD / "match_timing" / "links").glob("*.parquet")):
        names = pq.read_schema(f).names
        if "start_utc" in names and "match_id" in names:
            d = pd.read_parquet(f, columns=["match_id", "start_utc"])
            starts |= set(d.loc[d["start_utc"].notna(), "match_id"])
    ex["start_utc_any_link_source(time of day)"] = ids.isin(starts).to_numpy()
    out += shares(mf, ex, "match_timing_timing(pre-rebuild)")
    # odds (pre-rebuild Stage 1) and the raw tennis-data.co.uk rows behind them
    o = read_on_model(OLD / "predictability_diagnostic" / "stage1_odds.parquet", ids,
                      ["match_id", "td_file", "td_row", "td_tournament", "avg_a", "ps_a", "max_a", "b365_a", "p_avg_a",
                       "p_ps_a", "overround_avg", "overround_ps", "td_date", "td_redated"])
    ex = {c: finite(o[c]) for c in ["avg_a", "ps_a", "max_a", "b365_a", "p_ps_a", "overround_avg", "overround_ps"]}
    ex["td_date(finite)"] = o["td_date"].notna().to_numpy()
    out += shares(mf, ex, "stage1_odds(pre-rebuild)")
    raw_cols = ["Court", "Location", "Tournament", "B365W", "PSW", "MaxW", "AvgW", "EXW", "LBW", "SJW", "BFEW",
                "W1", "L1", "Wsets", "Comment", "WRank", "WPts"]
    raw = []
    for f, g in o.dropna(subset=["td_file"]).groupby("td_file"):
        fp = ROOT / f
        have = [c for c in raw_cols if c in pq.read_schema(fp).names]
        r = pd.read_parquet(fp, columns=have).reset_index(drop=True)
        r["_pos"] = np.arange(len(r))          # stage1_odds.load_td: td_row is the row's position in the file
        r = g[["match_id", "td_row"]].astype({"td_row": "int64"}).merge(r, left_on="td_row", right_on="_pos", how="left")
        raw.append(r)
    raw = ids.to_frame().merge(pd.concat(raw, ignore_index=True), on="match_id", how="left")
    linked = o["td_tournament"].notna()
    values["td_row_join_check"] = {"linked": int(linked.sum()), "tournament_name_agrees": float(
        (raw.loc[linked, "Tournament"].astype(str).str.strip() == o.loc[linked, "td_tournament"].astype(str).str.strip()).mean())}
    ex = {}
    text_cols = {"Court", "Location", "Tournament", "Comment"}
    for c in raw_cols:
        if c not in raw:
            ex[f"td_{c}"] = np.zeros(len(raw), dtype=bool)
        elif c in text_cols:
            ex[f"td_{c}"] = raw[c].notna().to_numpy() & raw[c].astype(str).str.strip().ne("").to_numpy()
        else:                       # odds, set scores, ranks: present = parses as a number (some files store text)
            ex[f"td_{c}"] = finite(raw[c])
    ex["td_Court_indoor(share)"] = raw["Court"].astype(str).str.lower().eq("indoor").to_numpy()
    out += shares(mf, ex, "tennis_data_couk_raw(via stage1_odds td_file/td_row)")
    values["td_Court"] = raw["Court"].value_counts(dropna=False).to_dict()
    # indoor: Stage 0 against tennis-data.co.uk where both exist (agreement)
    both = m["indoor"].notna() & raw["Court"].notna()
    agree = (m.loc[both, "indoor"].astype(bool) == raw.loc[both, "Court"].astype(str).str.lower().eq("indoor"))
    values["indoor_stage0_vs_td_court_agreement"] = {"compared": int(both.sum()), "agree_share": float(agree.mean())}
    # point-level and shot-level sources
    sm = pd.read_parquet(S / "shot_level" / "stage0_source_matches.parquet",
                         columns=["match_id", "source", "n_points", "has_rally", "has_ending", "has_speed",
                                  "has_placement", "has_net", "has_return", "has_stroke", "has_tracking"])
    sm = sm[sm["match_id"].isin(set(ids))]
    ex = {}
    anyp = sm.groupby("match_id")["n_points"].max()
    ex["point_by_point(any source, n_points>0)"] = ids.map(anyp).fillna(0).to_numpy() > 0
    for h in ["has_rally", "has_ending", "has_speed", "has_placement", "has_net", "has_return", "has_stroke", "has_tracking"]:
        g = sm.groupby("match_id")[h].max()
        ex[f"pbp_{h}"] = ids.map(g).fillna(False).to_numpy(dtype=bool)
    for src, g in sm.groupby("source"):
        ex[f"pbp_source={src}"] = ids.isin(set(g.loc[g["n_points"].fillna(0) > 0, "match_id"])).to_numpy()
    out += shares(mf, ex, "shot_level_stage0_source_matches")
    st = pd.read_parquet(S / "shot_level" / "stage1_match_stats.parquet")
    st = st[st["match_id"].isin(set(ids))]
    sA = ids.to_frame().merge(st[st["side"] == "A"], on="match_id", how="left")
    sB = ids.to_frame().merge(st[st["side"] == "B"], on="match_id", how="left")
    ex = {}
    for f in [c[:-2] for c in st.columns if c.endswith("_d")]:
        ex[f"{f}(both, d>0)"] = (pd.to_numeric(sA[f"{f}_d"], errors="coerce").fillna(0) > 0).to_numpy() & \
                               (pd.to_numeric(sB[f"{f}_d"], errors="coerce").fillna(0) > 0).to_numpy()
    out += shares(mf, ex, "shot_level_stage1_match_stats(per player-match)")
    # TML's ATP player database (backhand, weight, birth date) on the men's population, joined by Stage 0's player ids
    # is not attempted here: Stage 0 uses Sackmann ids and TML's are ATP codes (see stage0_build.py); coverage is
    # reported from the raw table only.
    db = pd.read_parquet(ROOT / "data" / "dump" / "players" / "tennis_my_life" / "ATP_Database.parquet")
    values["tml_atp_database"] = {"rows": int(len(db)), "backhand": db["backhand"].value_counts(dropna=False).head(6).to_dict(),
                                  "birthdate_non_null": float(db["birthdate"].notna().mean()),
                                  "height_non_null": float(db["height"].notna().mean()),
                                  "weight_non_null": float(db["weight"].notna().mean())}
    return out, values


def by_season(mf: pd.DataFrame) -> pd.DataFrame:
    ids = mf["match_id"]
    p = pq.read_table(OLD / "predictability_diagnostic" / "stage0_match_players.parquet",
                      columns=["match_id", "side", "has_box", "sv_gms", "bp_faced", "ace"],
                      filters=[("match_id", "in", list(ids))]).to_pandas()
    A = ids.to_frame().merge(p[p["side"] == "A"], on="match_id", how="left")
    B = ids.to_frame().merge(p[p["side"] == "B"], on="match_id", how="left")
    m = read_on_model(OLD / "predictability_diagnostic" / "stage0_matches.parquet", ids, ["match_id", "minutes", "indoor"])
    tm = read_on_model(OLD / "match_timing" / "timing.parquet", ids, ["match_id", "exact", "width_days"])
    sm = pd.read_parquet(S / "shot_level" / "stage0_source_matches.parquet", columns=["match_id", "n_points", "has_speed"])
    sm = sm[sm["match_id"].isin(set(ids))]
    pbp = ids.map(sm.groupby("match_id")["n_points"].max()).fillna(0).to_numpy() > 0
    spd = ids.map(sm.groupby("match_id")["has_speed"].max()).fillna(False).to_numpy(dtype=bool)
    d = pd.DataFrame({
        "tour": mf["tour"], "season": mf["season"],
        "box_both": A["has_box"].fillna(False).to_numpy(dtype=bool) & B["has_box"].fillna(False).to_numpy(dtype=bool),
        "sv_gms_both": finite(A["sv_gms"]) & finite(B["sv_gms"]),
        "minutes": finite(m["minutes"]), "indoor": m["indoor"].notna().to_numpy(),
        "exact_day": tm["exact"].fillna(False).to_numpy(dtype=bool), "width_1_day": (tm["width_days"].to_numpy() == 1),
        "pbp_any": pbp, "speed_any": spd,
        "in_form_hold": finite(mf["in_form_hold"]), "in_form_ace": finite(mf["in_form_ace"]),
        "in_iosO_hold": finite(mf["in_iosO_hold"]), "in_ratings_iid": finite(mf["in_ratings_iid"]),
        "in_sets_14d": finite(mf["in_sets_14d"]), "in_indoor": finite(mf["in_indoor"]),
    })
    g = d.groupby(["tour", "season"])
    res = g.mean().round(4)
    res.insert(0, "matches", g.size())
    return res.reset_index()


def main() -> int:
    """--raw-only recomputes the model inputs and raw fields and keeps the feature tables' rows of a previous run."""
    mf = model_population()
    print(f"population 2013-2024: {len(mf):,} matches", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    # the 58 model inputs
    ex = {c[3:]: finite(mf[c]) for c in mf.columns if c.startswith("in_")}
    ex["surf_season_pair(both)"] = finite(mf["in_surf_season_a"]) & finite(mf["in_surf_season_b"])
    ex["surf_layoff_pair(both)"] = finite(mf["in_surf_layoff_a"]) & finite(mf["in_surf_layoff_b"])
    rows = shares(mf, ex, "model_frame")
    print("  model inputs done", flush=True)
    raw, values = raw_fields(mf)
    rows += raw
    pd.DataFrame(rows).to_csv(OUT / "coverage_model_and_raw.csv", index=False)
    (OUT / "raw_values.json").write_text(json.dumps(values, indent=1, default=str), encoding="utf-8")
    print("  raw fields done", flush=True)
    feat_csv = OUT / "coverage_feature_tables.csv"
    if "--raw-only" not in sys.argv or not feat_csv.exists():
        pd.DataFrame(feature_tables(mf)).to_csv(feat_csv, index=False)
    cov = pd.concat([pd.DataFrame(rows), pd.read_csv(feat_csv)], ignore_index=True)
    cov.to_csv(OUT / "coverage_all.csv", index=False)
    by_season(mf).to_csv(OUT / "coverage_by_season.csv", index=False)
    print(f"wrote coverage_all.csv ({len(cov):,} rows), coverage_by_season.csv, raw_values.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
