"""R2 data checks, outcome-free (no frame result is loaded; the doubles table holds facts of earlier doubles matches).

1. Fame (titles and Slam QFs since 2010): the raw A - B spread and the players' mean fame by season: does a count that
   starts in 2010 drift through discovery into Look A?
2. Doubles window (rb01_d7_else): the builder counts doubles on days obs-7..obs-1 (obs = the clock's best estimate);
   the leak-proof rule reads the state as of es. Count frame player-rows (2018 on) with obs > es where an
   other-event doubles day falls in [es, obs-1] (possibly after the singles match).
3. Short rest (rb03_lt20): rule (i) (Flashscore's end first) against rule (ii) (start + minutes first), from the values'
   rb03_short / rb03_short2 per player: agreement by tour and season (the end source shifts for men's 2025-26).
Writes data_checks.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import rt_common as R  # noqa: E402

sys.path.insert(0, str(R.ROOT))


def main() -> int:
    out = {}
    f = R.outcome_free_frame()
    td = pd.to_datetime(f["tournament_date"])
    keep = (td < pd.Timestamp("2026-07-29")).to_numpy()        # the sealed set is not counted
    f = f[keep].reset_index(drop=True)
    # 1. fame
    pool = pd.read_parquet(R.ROOT / "data/studies/unpriced_leads/candidates/pool_rebuilt/values.parquet",
                           columns=["match_id", "rb__fp__f14_anchor__fame_a", "rb__fp__f14_anchor__fame_b",
                                    "rb__fp__f14_anchor__fame_a-b", "rb__fp__f28_state__bdst_pastfat_a",
                                    "rb__fp__f28_state__bdst_pastfat_b"])
    pool = pool.astype({"match_id": str}).set_index("match_id").reindex(f["match_id"])
    fa, fb = pool["rb__fp__f14_anchor__fame_a"].to_numpy(float), pool["rb__fp__f14_anchor__fame_b"].to_numpy(float)
    d = pool["rb__fp__f14_anchor__fame_a-b"].to_numpy(float)
    pa, pb = pool["rb__fp__f28_state__bdst_pastfat_a"].to_numpy(float), pool["rb__fp__f28_state__bdst_pastfat_b"].to_numpy(float)
    fam = {}
    for s in range(2013, 2027):
        m = (f["season"] == s).to_numpy()
        fam[s] = {"rms_diff": float(np.sqrt(np.nanmean(d[m] ** 2))), "mean_player_fame": float(np.nanmean(np.r_[fa[m], fb[m]])),
                  "p90_player_fame": float(np.nanpercentile(np.r_[fa[m], fb[m]], 90)),
                  "pastfat_mean": float(np.nanmean(np.r_[pa[m], pb[m]])),
                  "pastfat_present": float(np.mean(np.isfinite(np.r_[pa[m], pb[m]])))}
    out["fame_and_pastfat_by_season"] = fam
    # 3. short rest: rule (i) vs rule (ii)
    rv = pd.read_parquet(R.ROOT / "data/studies/unpriced_leads/candidates/rhythm/values.parquet",
                         columns=["match_id", "rb03_lt20_a", "rb03_lt20_b", "rb03_short_a", "rb03_short_b",
                                  "rb03_short2_a", "rb03_short2_b", "rb03_lt20"])
    rv = rv.astype({"match_id": str}).set_index("match_id").reindex(f["match_id"])
    rows = []
    for side in ("a", "b"):
        l1 = rv[f"rb03_lt20_{side}"].to_numpy(float)
        s2 = rv[f"rb03_short2_{side}"].to_numpy(float)
        l2 = np.where(np.isfinite(s2), (s2 > 4 / 24).astype(float), np.nan)
        rows.append(pd.DataFrame({"tour": f["tour"], "season": f["season"], "l1": l1, "l2": l2}))
    T = pd.concat(rows, ignore_index=True)
    ok = np.isfinite(T["l1"]) & np.isfinite(T["l2"])
    T = T[ok]
    T["agree"] = T["l1"] == T["l2"]
    g = T.groupby(["tour", "season"]).agg(n=("agree", "size"), agree=("agree", "mean"), lt20_i=("l1", "mean"),
                                          lt20_ii=("l2", "mean"))
    out["rest_rule_i_vs_ii"] = {f"{t}|{s}": r.round(5).to_dict() for (t, s), r in g.iterrows()}
    # 2. doubles window vs the leak-proof clock (reuse the rhythm builder's own doubles functions)
    from src.eda.unpriced_leads import build_rhythm as BR
    id2s0, name2s0 = BR.tl_name_map()
    s0m = pd.read_parquet(R.ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                          columns=["match_id", "player_a_id", "player_b_id", "tournament_id", "tournament_date"])
    s0m = s0m.astype({"match_id": str})
    tim = pd.read_parquet(R.ROOT / "data/studies/match_timing/timing.parquet", columns=["match_id", "obs", "es", "lf"])
    tim = tim.astype({"match_id": str})
    s0m = s0m.merge(tim[["match_id", "obs"]], on="match_id")
    ev2tid, _ = BR.tl_event_map(id2s0, s0m)
    D, _ = BR.tl_doubles(name2s0, ev2tid)
    fr = f[f["season"] >= 2018][["match_id", "tour", "season"]].merge(
        s0m[["match_id", "player_a_id", "player_b_id", "tournament_id"]], on="match_id").merge(tim, on="match_id")
    q = pd.concat([fr.assign(pid=fr["player_a_id"].astype(str)), fr.assign(pid=fr["player_b_id"].astype(str))],
                  ignore_index=True)
    q["tid"] = q["tournament_id"].astype(str)
    q["obs_i"] = q["obs"].astype(float)
    q["es_i"] = np.floor(q["es"].astype(float))
    unc = q[np.isfinite(q["obs_i"]) & np.isfinite(q["es_i"]) & (q["obs_i"] > q["es_i"])]
    dd = D[["pid", "day", "tid"]]
    j = unc[["match_id", "pid", "tid", "obs_i", "es_i", "season", "tour"]].merge(dd, on="pid", suffixes=("", "_d"))
    j = j[(j["day"] >= j["obs_i"] - 7) & (j["day"] <= j["obs_i"] - 1)]
    j["else"] = j["tid_d"] != j["tid"]
    risky = j[j["else"] & (j["day"] >= j["es_i"])]
    out["doubles_window"] = {"frame_player_rows_2018_on": int(len(q)),
                             "rows_obs_after_es": int(len(unc)),
                             "rows_with_else_doubles_in_window": int(j[j["else"]][["match_id", "pid"]].drop_duplicates().shape[0]),
                             "rows_with_else_doubles_on_or_after_es": int(risky[["match_id", "pid"]].drop_duplicates().shape[0]),
                             "risky_rows_by_season": risky.drop_duplicates(["match_id", "pid"]).groupby("season").size().to_dict(),
                             "obs_minus_es_days_among_uncertain": unc.assign(g=unc["obs_i"] - unc["es_i"])["g"].describe().to_dict()}
    # the all-rows count of nonzero rb01_d7_else per side, for scale
    rr = pd.read_parquet(R.ROOT / "data/studies/unpriced_leads/candidates/rhythm/values.parquet",
                         columns=["match_id", "rb01_d7_else_a", "rb01_d7_else_b"]).astype({"match_id": str})
    rr = rr.set_index("match_id").reindex(fr["match_id"])
    out["doubles_window"]["frame_player_rows_with_else_gt0"] = int((rr["rb01_d7_else_a"] > 0).sum() + (rr["rb01_d7_else_b"] > 0).sum())
    (R.OUT / "data_checks.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out["doubles_window"], indent=1, default=float))
    print(pd.DataFrame(out["fame_and_pastfat_by_season"]).T.round(3).to_string())
    print(g.round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
