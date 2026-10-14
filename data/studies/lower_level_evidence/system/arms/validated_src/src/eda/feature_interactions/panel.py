"""The player panel: one row per model-frame match, each player's PRE-MATCH values side by side (`<name>_a`, `<name>_b`;
side A = Stage 0's player_a_id), for the feature builders of this study.

Every source is joined by match id from tables consistent with the frozen model frame (the cartographer's join path,
round0/inventory.md section 5.4): the per-player tables built from the same Stage 0 version, and the PRE-REBUILD copies of
Stage 0, the odds and the match clock (data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/). Post-match
fields (score, minutes, box score of the match itself) are never included. Each source's SHA-256 is recorded by
`manifest()`.

    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)      # the screen's seasons; the final test's builds use max_season=2026

Sources and columns (A and B):
    ios_<k>_<s>     surface_ios/surface_features: k in srfO, srfD (effective on the match's surface), curO, curD (pooled),
                    srfE, srfF (surface deviations); s in spw, ace, df, first_in, first_won, second_won, hold, bp_saved
    elo_R, elo_D, elo_N, elo_NS, surf_season_n, surf_days_since, surf_prev_n, surf_prev_res
                    surface_elo_pieces/pieces (overall Elo, surface offset, rated matches, surface matches, ...)
    s3_serve, s3_return, s3_sd_serve, s3_sd_return, s3_serve_pts, s3_return_pts, s3_p_serve
                    Stage 3's iid serve/return ratings (predictability_diagnostic/stage3_ratings); mu_logit is context
    ttt_mu, ttt_s2, ttt_off, ttt_so2, ttt_n, ttt_ns   surface_rating_race/ttt_offset
    form_*, formdef_*, adjperf_tpw_2w, sets_14d, age_pl   the two-week profile and load per player, rebuilt and
                    verified by the cartographer (2013-2024 only; NaN later)
    rank, rank_points, seed, entry, age, height, hand, country   Stage 0 players (pre-rebuild), pre-match fields
Context: tour, season, tournament_date, a_won, p_mkt, in_* (the 58 inputs), tournament_id, tournament_name, round, level,
best_of, indoor, surface, draw_size, mu_logit, odds fields (avg, ps, max, b365 per side; overround_avg; p_ps_a), the
clock's es / lf (earliest start, latest finish day) of the match, and eta_model: the current best's out-of-sample
log-odds (2014-2024; antisymmetric like a difference).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C

OLD = C.ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
SOURCES = {
    "surface_features": C.ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet",
    "pieces": C.ROOT / "data" / "studies" / "surface_elo_pieces" / "pieces.parquet",
    "stage3": C.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage3_ratings.parquet",
    "ttt_offset": C.ROOT / "data" / "studies" / "surface_rating_race" / "ttt_offset.parquet",
    "form": C.OUT / "inventory" / "perplayer_form_2013_2024.parquet",
    "load": C.OUT / "inventory" / "perplayer_load_2013_2024.parquet",
    "stage0_matches": OLD / "predictability_diagnostic" / "stage0_matches.parquet",
    "stage0_players": OLD / "predictability_diagnostic" / "stage0_match_players.parquet",
    "stage1_odds": OLD / "predictability_diagnostic" / "stage1_odds.parquet",
    "timing": OLD / "match_timing" / "timing.parquet",
}
STATS8 = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
IOS_KINDS = {"srfO": "srf_O_eff_{s}", "srfD": "srf_D_eff_{s}", "curO": "cur_O_{s}", "curD": "cur_D_{s}",
             "srfE": "srf_E_{s}", "srfF": "srf_F_{s}"}
PIECES = {"elo_R": "R", "elo_D": "D", "elo_N": "N", "elo_NS": "NS", "surf_season_n": "season_n",
          "surf_days_since": "days_since", "surf_prev_n": "prev_n", "surf_prev_res": "prev_res"}
STAGE3 = {"s3_serve": "serve", "s3_return": "return", "s3_sd_serve": "sd_serve", "s3_sd_return": "sd_return",
          "s3_serve_pts": "serve_pts", "s3_return_pts": "return_pts", "s3_p_serve": "p_serve"}
TTT = {"ttt_mu": "mu", "ttt_s2": "s2", "ttt_off": "off", "ttt_so2": "so2", "ttt_n": "n", "ttt_ns": "ns"}
PLAYER_FIELDS = ("rank", "rank_points", "seed", "entry", "age", "height", "hand", "country")


def _join(base: pd.DataFrame, path, cols: list[str]) -> pd.DataFrame:
    t = pd.read_parquet(path, columns=["match_id"] + cols)
    t["match_id"] = t["match_id"].astype(str)
    return base[["match_id"]].merge(t, on="match_id", how="left", validate="one_to_one")


def panel(max_season: int = 2024, min_season: int = C.TRAIN_FROM) -> pd.DataFrame:
    if max_season > C.REPLICATION[-1]:
        C.log(f"panel up to {max_season}: for the final test's builds only (no results may be read)")
    f = pd.read_parquet(C.MODEL_FRAME)
    f = f[f["season"].between(min_season, max_season)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    out = {}
    # surface IOS, per player
    names = {f"ios_{k}_{s}": pat.format(s=s) for k, pat in IOS_KINDS.items() for s in STATS8}
    t = _join(f, SOURCES["surface_features"], [f"{c}_{side}" for c in names.values() for side in "ab"])
    for new, src in names.items():
        for side in "ab":
            out[f"{new}_{side}"] = t[f"{src}_{side}"].to_numpy(dtype=float)
    for src_key, mapping in (("pieces", PIECES), ("stage3", STAGE3), ("ttt_offset", TTT)):
        t = _join(f, SOURCES[src_key], [f"{c}_{side}" for c in mapping.values() for side in "ab"])
        for new, src in mapping.items():
            for side in "ab":
                out[f"{new}_{side}"] = t[f"{src}_{side}"].to_numpy(dtype=float)
    out["mu_logit"] = _join(f, SOURCES["stage3"], ["mu_logit"])["mu_logit"].to_numpy(dtype=float)
    # the two-week profile and load per player (2013-2024)
    for key in ("form", "load"):
        t = pd.read_parquet(SOURCES[key])
        t["match_id"] = t["match_id"].astype(str)
        t = f[["match_id"]].merge(t, on="match_id", how="left", validate="one_to_one")
        for c in t.columns:
            if c != "match_id":
                out[c if not c.startswith("age_") else c.replace("age_", "age_pl_")] = t[c].to_numpy(dtype=float)
    # Stage 0 players: pre-match fields only
    p = pd.read_parquet(SOURCES["stage0_players"], columns=["match_id", "side"] + list(PLAYER_FIELDS))
    p["match_id"] = p["match_id"].astype(str)
    for side, tag in (("A", "a"), ("B", "b")):
        q = p[p["side"] == side].drop(columns="side")
        q = f[["match_id"]].merge(q, on="match_id", how="left", validate="one_to_one")
        for c in PLAYER_FIELDS:
            out[f"{c}_{tag}"] = q[c].to_numpy()
    # match facts known before the match
    m = _join(f, SOURCES["stage0_matches"], ["tournament_id", "tournament_name", "round", "level", "best_of", "indoor",
                                             "surface", "draw_size", "player_a_id", "player_b_id"])
    for c in m.columns:
        if c != "match_id":
            out[c] = m[c].to_numpy()
    o = _join(f, SOURCES["stage1_odds"], ["avg_a", "avg_b", "ps_a", "ps_b", "max_a", "max_b", "b365_a", "b365_b",
                                          "overround_avg", "p_ps_a"])
    for c in o.columns:
        if c != "match_id":
            out[c] = o[c].to_numpy()
    tm = _join(f, SOURCES["timing"], ["es", "lf", "exact"])
    out["es"], out["lf"], out["clock_exact"] = tm["es"].to_numpy(), tm["lf"].to_numpy(), tm["exact"].to_numpy()
    # the current best's out-of-sample log-odds (walk-forward, seeds 0-2, symmetrised; no result of the match itself),
    # 2014-2024 only (NaN otherwise): for hypotheses on the model's own adjustment, eta_model - in_odds_logit
    from src.eda.feature_interactions.screen import oos_model_forecast
    s_eta = oos_model_forecast()
    out["eta_model"] = C.lg(f["match_id"].map(s_eta).to_numpy(dtype=float))
    out["eta_model"][~np.isfinite(f["match_id"].map(s_eta).to_numpy(dtype=float))] = np.nan
    return pd.concat([f, pd.DataFrame(out, index=f.index)], axis=1)


def manifest() -> dict:
    return {k: {"path": str(v.relative_to(C.ROOT)), "sha256": C.sha256_file(v)} for k, v in SOURCES.items()}


def swap_sides(P: pd.DataFrame) -> pd.DataFrame:
    """The panel with A and B exchanged (every `_a` column with its `_b` partner, and a_won flipped): a builder's
    feature computed on this must be the negative of the original (diff) or equal to it (context)."""
    from src.eda.feature_interactions.arms import base_inputs
    out = P.copy()
    for c in P.columns:
        if c.endswith("_a") and c[:-2] + "_b" in P.columns:
            out[c], out[c[:-2] + "_b"] = P[c[:-2] + "_b"].to_numpy(), P[c].to_numpy()
    _, kinds, _ = base_inputs()                       # the model's own A - B inputs change sign
    for n, k in kinds.items():
        if k == "diff" and f"in_{n}" in P.columns:
            out[f"in_{n}"] = -P[f"in_{n}"].to_numpy(dtype=float)
    if "eta_model" in P.columns:                      # the model's log-odds that A wins
        out["eta_model"] = -P["eta_model"].to_numpy(dtype=float)
    for c in ("p_mkt", "p_ps_a"):                     # probabilities that A wins
        if c in P.columns:
            out[c] = 1.0 - P[c].to_numpy(dtype=float)
    if {"player_a_id", "player_b_id"} <= set(P.columns):
        out["player_a_id"], out["player_b_id"] = P["player_b_id"].to_numpy(), P["player_a_id"].to_numpy()
    if "a_won" in P.columns:
        out["a_won"] = ~P["a_won"].astype(bool)
    return out


def check_swap(builder, P: pd.DataFrame, kind: str = "diff", tol: float = 1e-9) -> bool:
    """A builder P -> array: diff columns must change sign when A and B swap, context columns must not change."""
    x = np.asarray(builder(P), float)
    y = np.asarray(builder(swap_sides(P)), float)
    ok = np.isfinite(x) & np.isfinite(y)
    if kind == "diff":
        return bool(np.allclose(x[ok], -y[ok], atol=tol) and (np.isfinite(x) == np.isfinite(y)).all())
    return bool(np.allclose(x[ok], y[ok], atol=tol) and (np.isfinite(x) == np.isfinite(y)).all())
