"""Stage A of "ideas borrowed from UFC-predictions", part 2: the feature frame the shared harness scores.

stageA_features.parquet is common.load_pool() (the Stage 4 pool: 255,123 evaluation-level matches of 2010-2026, the
table's order, side A random) with the Stage 4 leaders' columns, plus Stage A's (every feature is A's value minus B's
on the log-odds scale, missing where it does not exist for both players):

    p_bt                    the primary BT's probability that A wins (a base column)
    p_mesr                  MESR's probability that A wins (a base column; missing where either player has no MESR)
    bt|single               bt_a - bt_b
    bt_games|single         the games-margin-weighted BT
    bt_nodecay|single       the BT without decay (the best grid row without decay)
    bt_surface|single       the surface BT: (s + u_surface) of A minus B's
    elo|single              ln(10) / 400 x (A's surface-blended Elo - B's) = logit(p_elo), Stage 1's surface Elo
    mesr|single             mesr_a - mesr_b
    mesr_minus_bt|single    A's (mesr - bt) minus B's: the market's view of the pair against the results' view
    mesr_minus_elo|single   the same against Elo on the log-odds scale

The Stage 4 leaders (rating_matchup|single, elo_games|single, sets_14d|single, mu_points|52 weeks, age|single,
age|single|2, surface_first|single) come through load_pool(extra=...) unchanged. elo|single is checked against
Stage 1's blended ratings (stage1_baselines.parquet and its frozen surface weights).

Writes data/studies/ufc_ideas/stageA_features.parquet and stageA_features_summary.json (coverage and the checks).
Run after stageA_ratings.py: ./python.sh src/eda/ufc_ideas/stageA_features.py   (ran in 1.4 seconds on 2 Oct 2026; the
summary's "seconds")
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

FEATURES = U.OUT / "stageA_features.parquet"
SUMMARY = U.OUT / "stageA_features_summary.json"
BT = U.OUT / "stageA_bt.parquet"
MESR = U.OUT / "stageA_mesr.parquet"
BASELINES = C.OUT / "stage1_baselines.parquet"
BASE_SUMMARY = C.OUT / "stage1_baselines_summary.json"
LEADERS = ["rating_matchup|single", "elo_games|single", "sets_14d|single", "mu_points|52 weeks", "age|single",
           "age|single|2", "surface_first|single"]
NEW = ["bt|single", "bt_games|single", "bt_nodecay|single", "bt_surface|single", "elo|single", "mesr|single",
       "mesr_minus_bt|single", "mesr_minus_elo|single"]
T0 = time.time()


def elo_check(pool: pd.DataFrame, elo_logit: np.ndarray) -> dict:
    """elo|single from Stage 1's ratings, by the definition: ln(10)/400 x the blended ratings' difference (overall
    alone where the surface is unknown), against logit(p_elo)."""
    bl = pd.read_parquet(BASELINES, columns=["match_id", "elo_a_ret", "elo_b_ret", "elo_surf_a_ret", "elo_surf_b_ret"])
    bl = bl.set_index("match_id").reindex(pool["match_id"])
    w = {c["tour"]: c["w"] for c in json.loads(BASE_SUMMARY.read_text(encoding="utf-8"))["chosen"] if c["rule"] == "ret"}
    wv = pool["tour"].map(w).to_numpy(dtype="float64")
    oa, ob = bl["elo_a_ret"].to_numpy(dtype="float64"), bl["elo_b_ret"].to_numpy(dtype="float64")
    sa, sb = bl["elo_surf_a_ret"].to_numpy(dtype="float64"), bl["elo_surf_b_ret"].to_numpy(dtype="float64")
    sa, sb = np.where(np.isnan(sa), oa, sa), np.where(np.isnan(sb), ob, sb)
    by_def = np.log(10) / 400 * (((1 - wv) * oa + wv * sa) - ((1 - wv) * ob + wv * sb))
    diff = np.abs(by_def - elo_logit)
    return {"max_abs_difference": float(np.nanmax(diff)), "mean_abs_difference": float(np.nanmean(diff)),
            "note": "stage1_baselines.parquet stores ratings as float32 (to about 0.001 point), so the definition "
                    "recomputed from them differs from logit(p_elo) by rounding only; elo|single is logit(p_elo)"}


def main() -> int:
    pool = U.load_pool(extra=LEADERS)
    bt = pd.read_parquet(BT).set_index("match_id").reindex(pool["match_id"])
    me = pd.read_parquet(MESR).set_index("match_id").reindex(pool["match_id"])
    assert bt["bt_a"].notna().all(), "every pool match has a BT rating"
    f = pool.copy()
    f["p_bt"] = bt["p_bt_a"].to_numpy(dtype="float64")
    f["p_mesr"] = me["p_mesr_a"].to_numpy(dtype="float64")
    f["bt|single"] = (bt["bt_a"] - bt["bt_b"]).to_numpy(dtype="float64")
    for k in ("bt_games", "bt_nodecay", "bt_surface"):
        f[f"{k}|single"] = (bt[f"{k}_a"].astype("float64") - bt[f"{k}_b"].astype("float64")).to_numpy()
    f["elo|single"] = logit(np.clip(f["p_elo"].to_numpy(dtype="float64"), 1e-12, 1 - 1e-12))
    ma, mb = me["mesr_a"].to_numpy(dtype="float64"), me["mesr_b"].to_numpy(dtype="float64")
    f["mesr|single"] = ma - mb
    f["mesr_minus_bt|single"] = (ma - bt["bt_a"].to_numpy()) - (mb - bt["bt_b"].to_numpy())
    f["mesr_minus_elo|single"] = f["mesr|single"] - f["elo|single"]
    assert np.allclose(np.isfinite(f["p_mesr"]), np.isfinite(f["mesr|single"]))
    f.to_parquet(FEATURES, index=False, compression="zstd")

    ev = f["evaluation"].to_numpy(dtype=bool)
    cov = {}
    for tour in C.TOURS:
        t = f["tour"].eq(tour).to_numpy()
        mk = np.isfinite(f["p_mkt"].to_numpy(dtype="float64"))
        cov[tour] = {"pool_matches": int(t.sum()), "evaluation_matches_2013_2026": int((t & ev).sum()),
                     "evaluation_with_odds": int((t & ev & mk).sum()), "features": {}}
        for c in NEW + ["p_mesr"] + LEADERS:
            has = np.isfinite(f[c].to_numpy(dtype="float64"))
            cov[tour]["features"][c] = {"evaluation": int((t & ev & has).sum()),
                                        "evaluation_share": float((t & ev & has).sum() / (t & ev).sum()),
                                        "with_odds": int((t & ev & mk & has).sum()),
                                        "with_odds_share": float((t & ev & mk & has).sum() / (t & ev & mk).sum())}
    corr = {}
    for tour in C.TOURS:
        t = f["tour"].eq(tour).to_numpy() & ev
        sub = f.loc[t, ["bt|single", "elo|single", "bt_games|single", "bt_nodecay|single", "bt_surface|single",
                        "mesr|single", "rating_matchup|single", "elo_games|single"]]
        corr[tour] = {k: {k2: round(float(v2), 4) for k2, v2 in v.items()} for k, v in sub.corr().to_dict().items()}
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "rows": int(len(f)),
               "columns_added": ["p_bt", "p_mesr"] + NEW, "leaders": LEADERS, "coverage": cov,
               "correlations_evaluation_matches": corr, "elo_check": elo_check(pool, f["elo|single"].to_numpy()),
               "seconds": round(time.time() - T0, 1)}
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {FEATURES.name} ({FEATURES.stat().st_size / 1e6:.1f} MB) and {SUMMARY.name} in {summary['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
