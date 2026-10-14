"""The augmented panel of the round-1 feasibility audit: base.get_panel() (2014-2024) plus, per player (_a, _b), the
history quantities of history_feats, the event's country and home flags, Stage B z dispersion and 52-week levels, the
shot-level sides used by candidates, Stage 4's big-point return difference, and the current best's walk-forward forecast
(raw, symmetrised over the two orientations and seeds 0-2; a forecast, not a result). Result-free: `a_won` is carried
but never used. Writes data/studies/feature_interactions/round1/_panel_aug.parquet.
Run: ./python.sh src/eda/feature_interactions/round1/feasibility/augment.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402
from src.eda.feature_interactions.round1.feasibility import history_feats as HF  # noqa: E402

S = B.ROOT / "data" / "studies"
HCOLS = ["fat_min_3", "fat_games_3", "fat_min_28", "fat_games_28", "min_7d", "min_14d", "min_28d", "games_7d",
         "games_28d", "n_7d", "onsite_n", "rest_min", "prev_deciding", "prev_won", "prev_indoor",
         "prev_retired_self", "ret_rate_730", "gap_days", "odo_season", "team_load", "titles_before",
         "slam_qf_before", "h2h_n", "h2h_w", "prev_event_wins", "spp_mean", "n_since_layoff", "layoff_days",
         "layoff_injury", "prev_event_title"]
SIDES = ["spd1_change|off|dec2-w52", "break_back|off|w52", "consolidate|off|w52"]


def stageb_dispersion(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Per player, from Stage B's per-match z (own earlier box-score matches, own order): the 52-week mean and variance
    of z_adjperf_tpw, and the 2-week decayed weight sum (evidence behind the two-week form)."""
    z = pd.read_parquet(S / "ufc_ideas" / "stageB_adj.parquet", columns=["match_id", "player_id", "z_adjperf_tpw"])
    k = L[["match_id", "player_id", "es", "lf", "k"]]
    z = k.merge(z, on=["match_id", "player_id"], how="left").sort_values(["player_id", "k"], kind="stable")
    pid = pd.factorize(z["player_id"])[0]
    es, lf, v = z["es"].to_numpy(float), z["lf"].to_numpy(float), z["z_adjperf_tpw"].to_numpy(float)
    ok = np.isfinite(v)
    s1, _, _ = HF._window(pid, es, lf, np.where(ok, v, 0.0), 364)
    s2, _, _ = HF._window(pid, es, lf, np.where(ok, v * v, 0.0), 364)
    n, _, _ = HF._window(pid, es, lf, ok.astype(float), 364)
    w2 = HF._kernel(pid, es, lf, ok.astype(float), 14.0 / np.log(2.0))
    out = pd.DataFrame({"match_id": z["match_id"].to_numpy(), "player_id": z["player_id"].to_numpy(),
                        "ztpw_mean52": np.where(n > 0.5, s1 / np.maximum(n, 1), np.nan),
                        "ztpw_var52": np.where(n > 2.5, s2 / np.maximum(n, 1) - (s1 / np.maximum(n, 1)) ** 2, np.nan),
                        "ztpw_n52": n, "w_2w": w2})
    res = {}
    for side, ids in (("a", P["player_a_id"]), ("b", P["player_b_id"])):
        q = pd.DataFrame({"match_id": P["match_id"].to_numpy(), "player_id": ids.to_numpy()})
        q = q.merge(out.drop_duplicates(["match_id", "player_id"]), on=["match_id", "player_id"], how="left")
        for c in ("ztpw_mean52", "ztpw_var52", "ztpw_n52", "w_2w"):
            res[f"{c}_{side}"] = q[c].to_numpy(float)
    return res


def forecasts(P: pd.DataFrame) -> np.ndarray:
    """The current best's raw walk-forward log-odds that A wins, symmetrised and averaged over seeds 0-2."""
    eta = pd.Series(np.nan, index=P["match_id"].to_numpy())
    for season in range(2014, 2025):
        base = B.C.LOCAL if season <= 2018 else B.C.RACE_LOCAL
        ps = []
        for seed in (0, 1, 2):
            z = np.load(base / f"model__{season}__seed{seed}.npz", allow_pickle=False)
            ids, p = z["ids_td"].astype(str), z["p_td"].astype(float)
            n = len(ids)
            ps.append(pd.Series(0.5 * (p[:n] + 1.0 - p[n:]), index=ids))
        eta.loc[ps[0].index] = B.lg(pd.concat(ps, axis=1).mean(axis=1)).astype(float)
    return eta.reindex(P["match_id"].to_numpy()).to_numpy(float)


def main() -> int:
    P = B.get_panel().copy()
    L = B.get_history()
    H = HF.build(L)
    prev_tid, prev_surf = H.pop("prev_tid"), H.pop("prev_surface")
    H["prev_same_event"] = np.where(prev_tid.isna(), np.nan, (prev_tid == L["tournament_id"]).astype(float))
    H["prev_same_surface"] = np.where(prev_surf.isna(), np.nan, (prev_surf == L["surface"]).astype(float))
    for c in HCOLS + ["prev_same_event", "prev_same_surface"]:
        a, b = B.at_model(L, H[c].to_numpy(float), P)
        P[f"{c}_a"], P[f"{c}_b"] = a, b
    for k, v in stageb_dispersion(P, L).items():
        P[k] = v
    sides = pq.read_table(S / "shot_level" / "stage3_sides.parquet",
                          columns=["match_id"] + [f"{s}|{x}" for x in SIDES for s in ("A", "B")]
                          + [f"{s}|{x}|has" for x in SIDES for s in ("A", "B")]).to_pandas()
    sides = P[["match_id"]].merge(sides, on="match_id", how="left")
    for x in SIDES:
        nm = x.split("|")[0]
        for s, tag in (("A", "a"), ("B", "b")):
            has = sides[f"{s}|{x}|has"].fillna(0).to_numpy() > 0.5
            P[f"sh_{nm}_{tag}"] = np.where(has, sides[f"{s}|{x}"].to_numpy(float), np.nan)
    s4 = pq.read_table(S / "predictability_diagnostic" / "stage4_features.parquet",
                       columns=["match_id", "bigpoint_return|single", "home|single"]).to_pandas()
    s4 = P[["match_id"]].merge(s4, on="match_id", how="left")
    P["d_bigpoint"], P["d_home_s4"] = s4["bigpoint_return|single"].to_numpy(float), s4["home|single"].to_numpy(float)
    from src.eda.predictability_diagnostic import stage4_country as SC
    ev = SC.event_country(P.assign(year=P["season"]))
    for tag in ("a", "b"):
        pc = SC.player_country(P[f"country_{tag}"])
        P[f"home_{tag}"] = np.where(ev.isna().to_numpy(), np.nan, (pc.to_numpy() == ev.to_numpy()).astype(float))
    P["eta"] = forecasts(P)
    # peak Elo before the match (cumulative maximum of each player's own pre-match overall Elo)
    pc = pd.read_parquet(S / "surface_elo_pieces" / "pieces.parquet", columns=["match_id", "R_a", "R_b"]).set_index("match_id")
    r_row = np.where(L["side"].to_numpy() == "A", L["match_id"].map(pc["R_a"]).to_numpy(float),
                     L["match_id"].map(pc["R_b"]).to_numpy(float))
    peak = pd.Series(r_row).groupby(L["player_id"].to_numpy()).cummax().to_numpy()
    P["elo_peak_a"], P["elo_peak_b"] = B.at_model(L, peak, P)
    # the player's own price in the previous match (average close, de-vigged), where that match had one
    o = pd.read_parquet(B.ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced"
                        / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet",
                        columns=["match_id", "p_avg_a"]).set_index("match_id")["p_avg_a"]
    pa = L["match_id"].map(o).to_numpy(float)
    p_own = np.where(L["side"].to_numpy() == "A", pa, 1.0 - pa)
    prev_p = pd.Series(p_own).groupby(L["player_id"].to_numpy()).shift(1).to_numpy()
    P["prev_p_own_a"], P["prev_p_own_b"] = B.at_model(L, prev_p, P)
    # days from this match's earliest start to the next Grand Slam main draw of the tour
    gs = L.loc[(L["level"] == "GS") & ~L["qualifying"].astype(bool), ["tour", "tday"]].drop_duplicates()
    nxt = np.full(len(P), np.nan)
    for t in ("atp", "wta"):
        days = np.sort(gs.loc[gs["tour"] == t, "tday"].to_numpy())
        m = (P["tour"] == t).to_numpy()
        es = P.loc[m, "es"].to_numpy(float)
        j = np.searchsorted(days, es, side="left")
        nxt[m] = np.where(j < len(days), days[np.minimum(j, len(days) - 1)] - es, np.nan)
    P["next_slam_days"] = nxt
    P.to_parquet(B.OUT / "_panel_aug.parquet", index=False)
    B.C.log(f"augmented panel {P.shape}; eta missing {int(np.isnan(P['eta']).sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
