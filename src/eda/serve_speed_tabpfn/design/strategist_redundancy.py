"""R1 design look of the integration strategist (serve-speed TabPFN study): how much of the registered speed change
x_raw is already carried by the model's 58 inputs (the closing odds included), and its coverage in the model frame.

Binding rules (docs/studies/serve_speed_tabpfn/brief.md, 2.1): no match result is read anywhere here (the model frame
is read without `a_won`); relations of a speed feature to the inputs and to the closing odds use seasons <= 2023 only
(a logged price look); 2024 rows are used for counts only. Nothing of 2025-2026 is read.

    x_raw    data/studies/point_sequence/speed_features.parquet (point-sequence study, registered statistic:
             14-day minus 364-day mean first-serve speed in, own history in order, A - B), standardised by the
             registered men's SD 5.998 km/h and clipped at +-4 SD
    level    the 364-day mean first-serve speed itself (A - B), rebuilt with speed_build's own functions (raw and
             event-family centred), to judge a speed LEVEL input

Writes data/studies/serve_speed_tabpfn/design/strategist_redundancy.json (and .csv of per-input correlations).
Run: ./python.sh src/eda/serve_speed_tabpfn/design/strategist_redundancy.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"
MODEL_FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
MODEL_INPUTS = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_inputs.json"
SPEED = ROOT / "data" / "studies" / "point_sequence" / "speed_features.parquet"
STAGE1_ODDS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
S0_NOW = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
S0_PRE = (ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" /
          "studies" / "predictability_diagnostic" / "stage0_matches.parquet")
SD_MEN, SD_WOMEN, CLIP = 5.998, 4.942, 4.0          # speed_prereg.md section 2 (fixed before any result was read)
LAST_RELATION_SEASON = 2023                         # relations: <= 2023 only (brief 2.1)
LAST_COUNT_SEASON = 2024                            # counts: speed_features covers <= 2024
CONTEXT_CAT = ["surface", "level", "indoor", "best_of", "round"]
SERVE_INPUTS = ["form_ace", "form_df", "form_first_in", "form_first_won", "form_second_won", "form_hold",
                "formdef_ace", "formdef_first_in", "iosO_ace", "iosO_first_in", "iosO_first_won", "iosO_second_won",
                "iosO_hold", "iosD_ace", "prod_ace", "prod_first_won", "prod_hold", "sets_14d", "adjperf_tpw_2w",
                "ios_points_short", "odds_logit", "elo_overall", "elo_surf_offset", "ratings_iid", "age"]
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def inputs() -> tuple[list[str], dict[str, str]]:
    meta = json.loads(MODEL_INPUTS.read_text(encoding="utf-8"))
    return [d["name"] for d in meta["inputs"]], {d["name"]: d["kind"] for d in meta["inputs"]}


def model_frame() -> pd.DataFrame:
    names, _ = inputs()
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt"] + [f"in_{n}" for n in names]
    f = pd.read_parquet(MODEL_FRAME, columns=cols, filters=[("season", "<=", LAST_COUNT_SEASON)])
    assert "a_won" not in f.columns
    f["match_id"] = f["match_id"].astype(str)
    return f


def design(f: pd.DataFrame, names: list[str], kinds: dict[str, str]) -> np.ndarray:
    """The 58 inputs as a regression design: numeric inputs (NaN -> 0 plus a missing indicator where any is missing),
    the context inputs one-hot (tour dropped: one tour at a time)."""
    parts, labels = [], []
    for n in names:
        v = f[f"in_{n}"].to_numpy(float)
        if n == "tour":
            continue
        if kinds[n] == "context" and n in CONTEXT_CAT:
            cat = pd.Series(np.where(np.isfinite(v), v, -99.0)).astype(int)
            d = pd.get_dummies(cat, prefix=n, drop_first=True).to_numpy(float)
            parts.append(d)
            labels += [f"{n}_{k}" for k in range(d.shape[1])]
            continue
        miss = ~np.isfinite(v)
        parts.append(np.where(miss, 0.0, v)[:, None])
        labels.append(n)
        if miss.any() and not miss.all():
            parts.append(miss.astype(float)[:, None])
            labels.append(f"{n}_missing")
    X = np.column_stack(parts)
    keep = X.std(axis=0) > 0
    return np.column_stack([np.ones(len(f)), X[:, keep]])


def ols_r2(X: np.ndarray, y: np.ndarray) -> float:
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    return float(1 - r.var() / y.var())


def cross_fitted_r2(X: np.ndarray, y: np.ndarray, groups: np.ndarray, model: str = "ols") -> float:
    """Leave-one-season-out R^2: each season predicted from the other seasons (out-of-sample, so no credit for the
    58 regressors' own fit)."""
    pred = np.full(len(y), np.nan)
    for g in np.unique(groups):
        te = groups == g
        if model == "ols":
            b, *_ = np.linalg.lstsq(X[~te], y[~te], rcond=None)
            pred[te] = X[te] @ b
        else:
            from sklearn.ensemble import HistGradientBoostingRegressor
            m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                              min_samples_leaf=40, l2_regularization=1.0, random_state=0)
            m.fit(X[~te], y[~te])
            pred[te] = m.predict(X[te])
    return float(1 - np.mean((y - pred) ** 2) / np.mean((y - y.mean()) ** 2))


def orientation_checks(f: pd.DataFrame, sp: pd.DataFrame) -> dict:
    """Is the model frame's side A Stage 0's player_a (the side speed_build used)? Checked on the market price (Stage 1's
    A-oriented odds) and on the players before/after the 7 Oct Stage 0 rebuild. No result is read."""
    o = pd.read_parquet(STAGE1_ODDS, columns=["match_id", "p_avg_a", "p_ps_a"])
    o["match_id"] = o["match_id"].astype(str)
    g = f[f["season"] <= LAST_RELATION_SEASON][["match_id", "p_mkt"]].merge(o, on="match_id", how="inner")
    out = {"odds_rows_compared": int(len(g))}
    for c in ("p_avg_a", "p_ps_a"):
        ok = g[c].notna() & g["p_mkt"].notna()
        out[f"share_equal_{c}"] = float(np.isclose(g.loc[ok, c], g.loc[ok, "p_mkt"], atol=1e-6).mean())
        out[f"share_equal_flipped_{c}"] = float(np.isclose(1 - g.loc[ok, c], g.loc[ok, "p_mkt"], atol=1e-6).mean())
    ids = set(sp["match_id"])
    pre = pd.read_parquet(S0_PRE, columns=["match_id", "player_a_id", "player_b_id"])
    now = pd.read_parquet(S0_NOW, columns=["match_id", "player_a_id", "player_b_id"])
    pre, now = pre[pre["match_id"].astype(str).isin(ids)], now[now["match_id"].astype(str).isin(ids)]
    j = pre.merge(now, on="match_id", suffixes=("_pre", "_now"))
    out["speed_ids_in_stage0_pre"] = int(len(pre))
    out["speed_ids_in_stage0_now"] = int(len(now))
    out["player_a_same_pre_now"] = float((j["player_a_id_pre"] == j["player_a_id_now"]).mean())
    return out


def coverage(f: pd.DataFrame, sp: pd.DataFrame) -> list[dict]:
    """Counts only (no relation): model-frame matches per tour, season and Slam/non-Slam with the registered feature
    (both sides have a timed match in the 14 days) and with at least one side's value."""
    g = f[["match_id", "tour", "season", "in_level"]].merge(
        sp[["match_id", "x_raw", "x_raw_side_a", "x_raw_side_b", "n2_a", "n2_b", "n52_a", "n52_b"]],
        on="match_id", how="left")
    g["slam"] = g["in_level"] == 0
    g["both"] = g["x_raw"].notna()
    g["one_or_more"] = g["x_raw_side_a"].notna() | g["x_raw_side_b"].notna()
    g["any_364"] = (g["n52_a"].fillna(0) > 0) | (g["n52_b"].fillna(0) > 0)
    g["both_364"] = (g["n52_a"].fillna(0) > 0) & (g["n52_b"].fillna(0) > 0)
    rows = []
    for (tour, season, slam), h in g.groupby(["tour", "season", "slam"]):
        if season < 2015:
            continue
        rows.append({"tour": tour, "season": int(season), "slam": bool(slam), "frame": int(len(h)),
                     "both_14d": int(h["both"].sum()), "at_least_one_14d": int(h["one_or_more"].sum()),
                     "both_364d": int(h["both_364"].sum()), "any_364d": int(h["any_364"].sum())})
    return rows


def level_features(f: pd.DataFrame) -> pd.DataFrame:
    """The 364-day level (mean first-serve speed in) per side, rebuilt with speed_build's own functions for the model
    frame's matches <= 2023 (raw and event-family centred), plus the rebuilt x_raw as a reproduction check."""
    from src.eda.point_sequence import speed_build as SB
    rows = SB.player_rows()
    ids = set(f.loc[f["season"] <= LAST_RELATION_SEASON, "match_id"])
    tgt = rows.index[rows["match_id"].astype(str).isin(ids) & (rows["year"] <= LAST_RELATION_SEASON)].to_numpy()
    raw = SB.window_feature(rows, tgt, "spd1_n")
    evt = SB.window_feature(rows, tgt, "spd1_e")
    side = rows.loc[tgt, ["match_id", "side"]].copy()
    side["match_id"] = side["match_id"].astype(str)
    side["lvl_raw"] = (raw["s52"] / raw["n52"].where(raw["n52"] > 0)).to_numpy()
    side["lvl_evt"] = (evt["s52"] / evt["n52"].where(evt["n52"] > 0)).to_numpy()
    side["x_raw_rebuilt"] = SB.side_values(raw).to_numpy()
    a = side[side["side"] == "A"].set_index("match_id")
    b = side[side["side"] == "B"].set_index("match_id")
    out = pd.DataFrame({"lvl_raw": a["lvl_raw"] - b["lvl_raw"], "lvl_evt": a["lvl_evt"] - b["lvl_evt"],
                        "lvl_raw_a": a["lvl_raw"], "lvl_raw_b": b["lvl_raw"],
                        "x_raw_rebuilt": a["x_raw_rebuilt"] - b["x_raw_rebuilt"]})
    return out.reset_index()


def relations(f: pd.DataFrame, sp: pd.DataFrame, lv: pd.DataFrame, names, kinds) -> tuple[dict, pd.DataFrame]:
    g = f[f["season"] <= LAST_RELATION_SEASON].merge(sp[["match_id", "x_raw", "x_evt", "x_shot", "n2_a", "n2_b"]],
                                                    on="match_id", how="left")
    g = g.merge(lv, on="match_id", how="left")
    out, corr_rows = {}, []
    for tour, sd in (("atp", SD_MEN), ("wta", SD_WOMEN)):
        h = g[(g["tour"] == tour) & g["x_raw"].notna()].reset_index(drop=True)
        x = np.clip(h["x_raw"].to_numpy(float) / sd, -CLIP, CLIP)
        X = design(h, names, kinds)
        seasons = h["season"].to_numpy()
        res = {"rows": int(len(h)), "by_season": h["season"].value_counts().sort_index().to_dict(),
               "sd_x_std": float(x.std()), "var_x_std": float(x.var()),
               "share_clipped": float((np.abs(h["x_raw"].to_numpy(float) / sd) > CLIP).mean()),
               "r2_58_inputs_in_sample": ols_r2(X, x),
               "r2_58_inputs_leave_one_season_out": cross_fitted_r2(X, x, seasons),
               "corr_odds_logit": float(np.corrcoef(x, h["in_odds_logit"])[0, 1]),
               "r2_odds_logit_alone": float(np.corrcoef(x, h["in_odds_logit"])[0, 1] ** 2)}
        Xo = np.column_stack([np.ones(len(h)), h[["in_odds_logit", "in_elo_overall", "in_ratings_iid"]].fillna(0)])
        res["r2_odds_elo_ratings"] = ols_r2(Xo, x)
        if tour == "atp":
            res["r2_58_inputs_gbm_leave_one_season_out"] = cross_fitted_r2(X[:, 1:], x, seasons, model="gbm")
            sub = {"slams_2015_2020": (h["in_level"] == 0) & (h["season"] <= 2020),
                   "all_2021_2023": h["season"] >= 2021, "nonslam_2021_2023": (h["season"] >= 2021) & (h["in_level"] != 0)}
            for k, m in sub.items():
                m = m.to_numpy()
                if m.sum() > 200:
                    res[f"r2_58_in_sample_{k}"] = ols_r2(X[m], x[m])
                    res[f"rows_{k}"] = int(m.sum())
            # alternative representations, <= 2023 (feature-feature correlations only)
            for alt in ("x_evt", "x_shot", "x_raw_rebuilt"):
                ok = h[alt].notna().to_numpy()
                res[f"corr_x_raw_{alt}"] = float(np.corrcoef(h.loc[ok, "x_raw"], h.loc[ok, alt])[0, 1])
                res[f"rows_{alt}"] = int(ok.sum())
            ok = h["x_raw_rebuilt"].notna().to_numpy()
            res["rebuilt_x_raw_max_abs_diff_kmh"] = float(np.abs(h.loc[ok, "x_raw"] - h.loc[ok, "x_raw_rebuilt"]).max())
            n2 = pd.concat([h["n2_a"], h["n2_b"]])
            res["n2_timed_first_serves_in_14d_quantiles"] = n2.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(0).to_dict()
        for n in SERVE_INPUTS:
            v = h[f"in_{n}"].to_numpy(float)
            ok = np.isfinite(v)
            corr_rows.append({"tour": tour, "input": n, "rows": int(ok.sum()), "corr_with_x_std": float(np.corrcoef(x[ok], v[ok])[0, 1])})
        out[tour] = res
    # the speed LEVEL (trait), men, every model-frame match <= 2023 where both sides have a 364-day level
    h = g[(g["tour"] == "atp") & g["lvl_evt"].notna()].reset_index(drop=True)
    X = design(h, names, kinds)
    lev = {"rows": int(len(h)), "by_season": h["season"].value_counts().sort_index().to_dict()}
    for c in ("lvl_raw", "lvl_evt"):
        y = h[c].to_numpy(float)
        y = (y - y.mean()) / y.std()
        lev[f"{c}_r2_58_in_sample"] = ols_r2(X, y)
        lev[f"{c}_r2_58_leave_one_season_out"] = cross_fitted_r2(X, y, h["season"].to_numpy())
        lev[f"{c}_corr_iosO_ace"] = float(np.corrcoef(y, h["in_iosO_ace"].fillna(0))[0, 1])
        lev[f"{c}_corr_iosO_first_won"] = float(np.corrcoef(y, h["in_iosO_first_won"].fillna(0))[0, 1])
        lev[f"{c}_corr_odds_logit"] = float(np.corrcoef(y, h["in_odds_logit"])[0, 1])
    hb = h[h["x_raw"].notna()]
    lev["corr_level_evt_with_x_raw"] = float(np.corrcoef(hb["lvl_evt"], hb["x_raw"])[0, 1])
    out["atp_level"] = lev
    return out, pd.DataFrame(corr_rows)


def main() -> int:
    names, kinds = inputs()
    f = model_frame()
    sp = pd.read_parquet(SPEED, filters=[("year", "<=", LAST_COUNT_SEASON)])
    sp["match_id"] = sp["match_id"].astype(str)
    log(f"model frame <= {LAST_COUNT_SEASON}: {len(f)} matches; speed features: {len(sp)}")
    res = {"rules": "no match result read; relations <= 2023 (a logged look incl. the closing odds); 2024 counts only",
           "inputs": len(names), "orientation": orientation_checks(f, sp)}
    j = f[["match_id"]].merge(sp[["match_id"]], on="match_id", how="left", indicator=True)
    res["model_frame_ids_in_speed_features"] = float((j["_merge"] == "both").mean())
    res["coverage"] = coverage(f, sp)
    log("rebuilding the 364-day level with speed_build (<= 2023 targets)")
    lv = level_features(f)
    rel, corr = relations(f, sp, lv, names, kinds)
    res["relations_le_2023"] = rel
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "strategist_redundancy.json").write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    corr.to_csv(OUT / "strategist_redundancy_corr.csv", index=False)
    log(json.dumps(res["orientation"]))
    for t in ("atp", "wta"):
        r = rel[t]
        log(f"{t}: rows {r['rows']}, R2 58 in-sample {r['r2_58_inputs_in_sample']:.4f}, LOSO "
            f"{r['r2_58_inputs_leave_one_season_out']:.4f}, corr odds {r['corr_odds_logit']:+.4f}")
    log(json.dumps(rel["atp"], default=float)[:1500])
    log(json.dumps(rel["atp_level"], default=float))
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print(corr[corr["tour"] == "atp"].sort_values("corr_with_x_std", key=np.abs, ascending=False).round(4).to_string(index=False))
        print(pd.DataFrame(res["coverage"]).query("tour == 'atp'").to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
