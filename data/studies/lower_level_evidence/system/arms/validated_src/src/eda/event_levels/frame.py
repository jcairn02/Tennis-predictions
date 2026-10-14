"""The extended frame: the current model's 58 inputs for its own main-tour matches and for every Challenger and
qualifying match of 2013-2024, on the snapshot the model frame was built on.

The model frame (surface_rating_race/model/model_frame.parquet) holds main-tour matches with a closing price only.
Its inputs come from tables that cover the whole evaluation pool (main tour, tour and Slam qualifying, Challenger and
WTA 125 main draws and qualifying), so the same recipes give every pool match the same 58 inputs:

    31 inputs   the best 2026 model's (src/eda/tabpfn_thinking/build_frame.py's recipes on Stage 4 and the UFC-ideas
                Stage D tables, the 30 Sep Stage 0's match context), with ios_points_short from the leak-proof table
                (src/eda/tabpfn_leakproof/: its column ios_short)
    21 inputs   the surface IOS profile (surface_ios/arms.recipe on surface_features.parquet: iosO, iosD, prod)
    6 inputs    the offset Elo (surface_elo_pieces/arms.new_inputs on pieces.parquet)

Rows the model never had get new level codes (CH 5, TQ 6, GSQ 7, CHQ 8) and no price (odds_logit missing). Their
format: best of 3, except the men's Grand Slam qualifying matches Stage 0 records as best of 5 (Wimbledon's); rows
Stage 0 flags as non-standard (match tiebreaks, short sets) are left out, as the model frame leaves out its own.

Check before writing: on the model frame's rows of 2013-2024 every one of the 58 inputs equals the model frame's value
for value (same missing cells), so the recipes and the snapshot are the model's. The sources are pinned by SHA-256
(common.check_sources).

Writes data/studies/event_levels/frame.parquet and frame_manifest.json.
Run: ./python.sh src/eda/event_levels/frame.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.event_levels import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.surface_elo_pieces import arms as EA  # noqa: E402
from src.eda.surface_ios import arms as SI  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

POOL_COLS = ["match_id", "tour", "year", "group", "status", "a_won", "p_mkt"]
MATCH_COLS = ["match_id", "tournament_name", "tournament_date", "surface", "indoor", "round_order", "best_of",
              "nonstandard_format", "map_level", "player_a_id", "player_b_id"]
NEW_LEVELS = ("CH", "TQ", "GSQ", "CHQ")
SPROF = [f"{k}_{s}" for k in ("iosO", "iosD", "prod") for s in T.IOS_STATS]


def thinking_inputs(pool: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """tabpfn_thinking/build_frame.build's recipes for every pool row (not only the main tour): the odds' log-odds, the
    Stage D differences and the six context columns, as float64 under the model's names."""
    out = pd.DataFrame(index=pool.index)
    tables = {}
    for key in ("stageD", "stageD_profile"):
        cols = sorted({c for f in T.FEATURES if f["src"] == key
                       for c in (f["col"].values() if isinstance(f["col"], dict) else [f["col"]])})
        t = pd.read_parquet(C.SOURCES[key][0], columns=["match_id"] + cols)
        if not np.array_equal(t["match_id"].to_numpy(), pool["match_id"].to_numpy()):
            raise RuntimeError(f"{key} is not in Stage 4's order")
        tables[key] = t
    tour = pool["tour"].to_numpy()
    for spec in T.FEATURES:
        name, src, col = spec["name"], spec["src"], spec["col"]
        if src in tables:
            if isinstance(col, dict):
                v = np.full(len(pool), np.nan)
                for t_, c in col.items():
                    v = np.where(tour == t_, tables[src][c].to_numpy(dtype="float64"), v)
                out[name] = v
            else:
                out[name] = tables[src][col].to_numpy(dtype="float64")
    pm = pool["p_mkt"].to_numpy(dtype="float64")
    out["odds_logit"] = np.where(np.isfinite(pm), logit(np.clip(pm, T.EPS, 1 - T.EPS)), np.nan)
    out["tour"] = pool["tour"].map(T.CODES["tour"]).astype("float64").to_numpy()
    out["surface"] = m["surface"].map(T.CODES["surface"]).astype("float64").to_numpy()
    out["level"] = pool["group"].map(C.LEVEL_CODES).astype("float64").to_numpy()
    ind = m["indoor"].map({True: 1.0, False: 0.0}).astype("float64").to_numpy()
    out["indoor"] = np.where(tour == "atp", ind, np.nan)
    group = pool["group"].to_numpy()
    recorded = m["best_of"].astype("float64").to_numpy()
    bo = np.where((tour == "atp") & (group == "GS"), 5.0, 3.0)
    bo = np.where((tour == "atp") & (group == "GSQ") & (recorded == 5), 5.0, bo)
    out["best_of"] = bo
    out["round"] = m["round_order"].astype("float64").to_numpy()
    return out


def surface_profile(ids: pd.Series) -> pd.DataFrame:
    sf = pd.read_parquet(C.SOURCES["surface_features"][0])
    sf = pd.DataFrame({"match_id": ids.to_numpy()}).merge(sf, on="match_id", how="left", validate="one_to_one")
    return pd.DataFrame({n: SI.recipe(n, sf) for n in SPROF})


def elo_inputs(ids: pd.Series) -> pd.DataFrame:
    pieces = pd.read_parquet(C.SOURCES["pieces"][0])
    pieces = pd.DataFrame({"match_id": ids.to_numpy()}).merge(pieces, on="match_id", how="left", validate="one_to_one")
    return EA.new_inputs(pieces).reset_index(drop=True)


def debut_season(rows: pd.DataFrame, m_all: pd.DataFrame) -> np.ndarray:
    """surface_elo_pieces/build_frames.debut_season's rule on the snapshot: a player's first Stage 0 match (any level,
    since 2010) falls in this match's season."""
    first = pd.concat([m_all[["tour", "player_a_id", "year"]].rename(columns={"player_a_id": "pid"}),
                       m_all[["tour", "player_b_id", "year"]].rename(columns={"player_b_id": "pid"})]) \
        .groupby(["tour", "pid"])["year"].min()
    fa = first.reindex(pd.MultiIndex.from_arrays([rows["tour"], rows["player_a_id"]])).to_numpy()
    fb = first.reindex(pd.MultiIndex.from_arrays([rows["tour"], rows["player_b_id"]])).to_numpy()
    s = rows["season"].to_numpy()
    return (fa == s) | (fb == s)


def build() -> tuple[pd.DataFrame, dict]:
    sources = C.check_sources()
    names, kinds, _ = SA.base_inputs()
    pool = pd.read_parquet(C.SOURCES["stage4"][0], columns=POOL_COLS)
    m_all = pd.read_parquet(C.SOURCES["stage0_matches"][0], columns=MATCH_COLS + ["tour", "year"])
    m = m_all.drop(columns=["tour", "year"]).set_index("match_id").reindex(pool["match_id"]).reset_index()
    X = thinking_inputs(pool, m)
    lp = pd.read_parquet(C.SOURCES["leakproof"][0], columns=["match_id", "ios_short"])
    lp = pool[["match_id"]].merge(lp, on="match_id", how="left", validate="one_to_one")
    X["ios_points_short"] = lp["ios_short"].to_numpy(dtype="float64")

    mf = pd.read_parquet(C.MODEL_FRAME)
    mf = mf[mf["season"] <= C.LAST_SEASON].reset_index(drop=True)
    mf["match_id"] = mf["match_id"].astype(str)
    in_model = pool["match_id"].isin(set(mf["match_id"])).to_numpy()
    season = pool["year"].to_numpy()
    lower = (pool["group"].isin(NEW_LEVELS).to_numpy() & pool["status"].isin(["completed", "retired"]).to_numpy()
             & ~m["nonstandard_format"].fillna(False).astype(bool).to_numpy()
             & (season >= C.TRAIN_FROM) & (season <= C.LAST_SEASON))
    keep = in_model | lower
    if int(in_model.sum()) != len(mf):
        raise RuntimeError(f"{len(mf) - int(in_model.sum())} model-frame matches are not in Stage 4's pool")
    rows = pool[keep].reset_index(drop=True)
    Xk = X[keep].reset_index(drop=True)
    mk = m[keep].reset_index(drop=True)
    sp = surface_profile(rows["match_id"])
    el = elo_inputs(rows["match_id"])
    frame = pd.DataFrame({"match_id": rows["match_id"].astype(str), "tour": rows["tour"],
                          "season": rows["year"].astype(int), "tournament_date": pd.to_datetime(mk["tournament_date"]),
                          "level": rows["group"], "pop": np.where(rows["group"].isin(C.MAIN), "MT",
                                                                  np.where(rows["group"] == "CH", "CH", "Q")),
                          "a_won": rows["a_won"].astype(bool), "p_mkt": rows["p_mkt"].astype("float64"),
                          "player_a_id": mk["player_a_id"], "player_b_id": mk["player_b_id"]})
    frame["debut_season"] = debut_season(frame, m_all)
    for n in names:
        if n in SPROF:
            v = sp[n]
        elif n in el.columns:
            v = el[n]
        else:
            v = Xk[n]
        frame[f"in_{n}"] = np.asarray(v, dtype="float64")
    C.frame_seasons_ok(frame)

    # the check: on the model frame's rows, every input equals the model frame's
    j = mf[["match_id"]].merge(frame, on="match_id", how="left", validate="one_to_one")
    checks = {"model_rows": int(len(mf)), "model_rows_found": int(j["season"].notna().sum())}
    bad = {}
    for n in names:
        a = j[f"in_{n}"].to_numpy(dtype="float64")
        b = mf[f"in_{n}"].to_numpy(dtype="float64")
        if not np.array_equal(a, b, equal_nan=True):
            both = np.isfinite(a) & np.isfinite(b)
            bad[n] = {"differ": int((both & (a != b)).sum()), "missing_differs": int((np.isnan(a) != np.isnan(b)).sum()),
                      "max_abs": float(np.nanmax(np.abs(a - b))) if both.any() else None}
    checks["inputs_equal_model_frame"] = not bad
    checks["differences"] = bad
    checks["labels_equal"] = bool(np.array_equal(j["a_won"].to_numpy(bool), mf["a_won"].to_numpy(bool)))
    checks["debut_equal"] = bool(np.array_equal(j["debut_season"].to_numpy(bool), mf["debut_season"].to_numpy(bool)))
    checks["levels_of_model_rows"] = j["level"].value_counts().to_dict()
    # the flip maps the extended frame's inputs as it maps the model's
    Xf = SA.matrix(frame, names)
    checks["flip_is_an_involution"] = bool(np.allclose(SA.flip(SA.flip(Xf)).to_numpy(), Xf.to_numpy(), equal_nan=True))
    if bad or not checks["labels_equal"] or not checks["flip_is_an_involution"] or checks["model_rows_found"] != len(mf):
        raise RuntimeError(f"the extended frame does not reproduce the model frame: {checks}")
    meta = {"sources": sources, "checks": checks,
            "rows": frame.groupby(["pop", "level", "tour"]).size().rename("matches").reset_index().to_dict("records"),
            "rows_by_season": frame.groupby(["season", "pop"]).size().unstack(fill_value=0).reset_index()
                                   .to_dict("records"),
            "coverage_by_level": {lv: {n: float(np.isfinite(g[f"in_{n}"].to_numpy(dtype="float64")).mean())
                                       for n in names}
                                  for lv, g in frame.groupby("level")},
            "best_of_by_level": frame.groupby(["level", "tour"])["in_best_of"].value_counts().rename("matches")
                                     .reset_index().to_dict("records")}
    return frame, meta


def main() -> int:
    frame, meta = build()
    C.OUT.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(C.FRAME, index=False)
    meta["generated_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    meta["frame_sha256"] = C.sha256_file(C.FRAME)
    C.write_json(C.OUT / "frame_manifest.json", meta)
    C.log(f"frame: {len(frame):,} matches; {meta['checks']['model_rows']:,} model rows reproduced exactly")
    C.log(frame.groupby(["pop", "level"]).size().to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
