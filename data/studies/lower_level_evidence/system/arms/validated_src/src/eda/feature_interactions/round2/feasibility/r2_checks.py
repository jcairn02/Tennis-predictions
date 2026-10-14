"""Round-2 feasibility checks (result-free): INFO-1's clock blind spot and what each player's own last match offers,
the I-020 and I-086 corrections, and coverage of the new ideas built from the augmented panel. 2014-2024 only;
`a_won` is never read. Writes data/studies/feature_interactions/round2/feasibility/r2_checks.json.
Run: ./python.sh src/eda/feature_interactions/round2/feasibility/r2_checks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402

OUT = B.C.OUT / "round2" / "feasibility"
S = B.ROOT / "data" / "studies"


def by_cell(P, ok):
    ok = np.asarray(ok, float)
    r = {}
    for tag, (lo, hi) in (("2014_21", B.DISC), ("2022_24", B.REP)):
        for t in ("atp", "wta"):
            m = (P["tour"].to_numpy() == t) & P["season"].between(lo, hi).to_numpy() & np.isfinite(ok)
            r[f"{t}_{tag}"] = round(float(np.nanmean(ok[m])), 4) if m.any() else None
    return r


def main() -> int:
    P = pd.read_parquet(B.OUT / "_panel_aug.parquet").drop(columns=["a_won"])
    res = {}
    # INFO-1: rest = es - lf of the previous own match; <= 0 means that result is not yet in the IOS solve
    ra, rb = P["rest_min_a"].to_numpy(float), P["rest_min_b"].to_numpy(float)
    res["info1_either_rest_le0"] = by_cell(P, (ra <= 0) | (rb <= 0))
    pm = pd.DataFrame({"tour": np.r_[P["tour"], P["tour"]], "season": np.r_[P["season"], P["season"]],
                       "r": np.r_[ra, rb], "same": np.r_[P["prev_same_event_a"], P["prev_same_event_b"]]})
    res["info1_player_rest_le0"] = by_cell(pm, pm["r"].to_numpy() <= 0)
    res["info1_player_rest_le0_same_event"] = by_cell(pm[pm["same"] == 1], pm.loc[pm["same"] == 1, "r"].to_numpy() <= 0)
    res["info1_player_rest_le0_other_event"] = by_cell(pm[pm["same"] == 0], pm.loc[pm["same"] == 0, "r"].to_numpy() <= 0)
    w = (P["lf"] - P["es"]).value_counts(normalize=True).sort_index()
    res["lf_minus_es_share"] = {str(int(k)): round(float(v), 4) for k, v in w.items() if v > 0.001}
    # do the sequential inputs include the previous same-event match? consecutive model matches of one player
    long = pd.concat([pd.DataFrame({"pid": P[f"player_{s}_id"], "tid": P["tournament_id"], "es": P["es"],
                                    "form": P[f"adjperf_tpw_2w_{s}"], "elo": P[f"elo_R_{s}"],
                                    "ios": P[f"ios_srfO_spw_{s}"], "rest": P[f"rest_min_{s}"]}) for s in "ab"])
    long = long.sort_values(["pid", "es"]).reset_index(drop=True)
    same = (long["pid"] == long["pid"].shift(1)) & (long["tid"] == long["tid"].shift(1))
    for c in ("form", "elo", "ios"):
        d = (long[c] - long[c].shift(1)).abs()[same]
        res[f"same_event_next_round_{c}_changed"] = round(float((d > 1e-9).mean()), 4)
    res["same_event_next_round_pairs"] = int(same.sum())
    # what u (INFO-1) needs: the previous match is a pool match (surface IOS state stored) with a box score
    L = B.get_history()
    pool = set(pq.read_table(S / "surface_ios" / "surface_features.parquet", columns=["match_id"]).column(0).to_pylist())
    prev_mid = L.groupby("player_id")["match_id"].shift(1)
    prev_box = L.assign(hb=L["svpt"].notna() & (L["svpt"] > 0)).groupby("player_id")["hb"].shift(1)
    ok_u = prev_mid.isin(pool).to_numpy() & (prev_box.fillna(False).to_numpy(dtype=bool))
    ua, ub = B.at_model(L, ok_u.astype(float), P)
    m = (ra <= 0) | (rb <= 0)
    ok = ((ra > 0) | (ua > 0.5)) & ((rb > 0) | (ub > 0.5))
    res["info1_u_buildable_when_rest_le0"] = by_cell(P[m], ok[m])
    # I-020 correction: a serve speed recorded in the player's own previous three matches (both players)
    sp = pd.read_parquet(S / "shot_level" / "stage1_match_stats.parquet", columns=["match_id", "player_id", "spd1_d"])
    sp = sp[sp["spd1_d"] > 0][["match_id", "player_id"]].assign(has=1.0)
    Lh = L[["match_id", "player_id"]].merge(sp, on=["match_id", "player_id"], how="left")["has"].fillna(0).to_numpy()
    rec3 = pd.Series(Lh).groupby(L["player_id"].to_numpy()).transform(lambda s: s.shift(1).rolling(3, min_periods=1).max())
    a3, b3 = B.at_model(L, rec3.fillna(0).to_numpy(), P)
    res["i020_speed_in_last3_both"] = by_cell(P, (a3 > 0.5) & (b3 > 0.5))
    # I-086: share of late-round rows (QF on) with both previous prices; the rest become 0 under S11
    late = P["in_round"].to_numpy(float) >= 15
    both_p = np.isfinite(P["prev_p_own_a"]) & np.isfinite(P["prev_p_own_b"])
    res["i086_late_rows_share"] = by_cell(P, late)
    res["i086_both_prev_prices_when_late"] = by_cell(P[late], both_p[late].to_numpy())
    # new ideas from panel columns
    res["c1_pinnacle_both"] = by_cell(P, np.isfinite(P["p_ps_a"]))
    res["c2_rank_both"] = by_cell(P, np.isfinite(P["rank_a"].astype(float)) & np.isfinite(P["rank_b"].astype(float)))
    res["bodl2_age_both"] = by_cell(P, np.isfinite(P["age_a"].astype(float)) & np.isfinite(P["age_b"].astype(float)))
    res["bodc2_rest_both"] = by_cell(P, np.isfinite(P["gap_days_a"]) & np.isfinite(P["gap_days_b"]))
    res["bodl1_prev_same_event_le3d_either"] = by_cell(P, ((P["prev_same_event_a"] == 1) & (P["rest_min_a"] <= 3))
                                                       | ((P["prev_same_event_b"] == 1) & (P["rest_min_b"] <= 3)))
    res["bodc1_both_played_14d"] = by_cell(P, (P["gap_days_a"] <= 14) & (P["gap_days_b"] <= 14))
    res["mec_k2_earlier_meeting"] = by_cell(P, P["h2h_n_a"].to_numpy(float) > 0)
    q = ((P["entry_a"].isin(["Q", "LL"]) & (P["onsite_n_a"] >= 1)) ^ (P["entry_b"].isin(["Q", "LL"]) & (P["onsite_n_b"] >= 1)))
    first = P["in_round"] == P.groupby("tournament_id")["in_round"].transform("min")
    res["info2_subgroup_share"] = by_cell(P, (q & first).to_numpy())
    # MEC-L1 novelty: tau = O_A D_B - O_B D_A on spw
    tau = P["ios_srfO_spw_a"] * P["ios_srfD_spw_b"] - P["ios_srfO_spw_b"] * P["ios_srfD_spw_a"]
    res["mec_l1_r2"] = {t: B.r2_on_inputs(P[P["tour"] == t], tau[P["tour"] == t].to_numpy(), "diff")["novelty_r2"]
                        for t in ("atp", "wta")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "r2_checks.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
