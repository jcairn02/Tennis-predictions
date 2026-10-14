"""The free models of this study re-run on the feature-alpha audit's repaired features (free; no API call).

The paid fit uses the original studies' features. The audit's repair (docs/studies/feature_alpha_audit/repairs.md,
2 Oct 2026) rebuilt the shortlisted features from raw rows in provider match-day order, after finding that
overlapping tournaments could expose future results under the original event-start clock; its cohort is the 78,706
main-tour matches with an accepted match date. This script asks how much of this study's free comparisons survive
that repair, on identical test matches:

    repaired     the same design (train 2013-2021, test 2022-2026, main tour, supported format) on the repaired
                 features: Elo (rebuilt), serve/return ratings, games-weighted Elo, two-week adjusted points, short IOS,
                 load, surface familiarity, age, the 16-input profile (25 differences) + the match context
    original     this study's models on the original features, restricted to the same columns (the 25 that have a
                 repaired counterpart) and the same test matches, refitted on the same training matches

The repaired history omits undated matches (lower levels and the men's 2018 season), so repaired ratings and load
differ for reasons beyond the leak; differences between the two columns are not a pure measure of leakage.

Writes data/studies/tabpfn_thinking/repaired_check.json and repaired_check.csv.
Run: ./python.sh src/eda/tabpfn_thinking/repaired_check.py    (about two minutes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import baselines as B  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking import score as S  # noqa: E402

REPAIRED = ROOT / "data" / "studies" / "feature_alpha_audit" / "repairs" / "repair_features.parquet"
MAP = {"ratings_iid": "rating_matchup|single", "elo_games": "elo_games|single", "adjperf_tpw_2w": "adjperf_tpw|decayed",
       "ios_points_short": "ios_short", "sets_14d": "sets_14d|single", "surface_first": "surface_first|single",
       "age": "age|single", "age_sq": "age|single|2"}
MAP.update({f"form_{s}": f"adjperf_{s}|decayed" for s in T.PROFILE_STATS})
MAP.update({f"formdef_{s}": f"adjdef_{s}|decayed" for s in T.ADJDEF_STATS})
DIFF25 = ["elo_logit"] + list(MAP)                    # Elo + 8 + the 16-input profile = 25 differences
CONTEXT = T.CONTEXT


def frames() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    orig = pd.read_parquet(T.OUT / "frame.parquet")
    orig = orig[orig["split"].isin(["train", "test"])].reset_index(drop=True)
    rep = pd.read_parquet(REPAIRED)
    rep = rep[rep["group"].isin(T.MAIN_GROUPS) & rep["scheduled_format_supported"].astype(bool)
              & rep["status"].isin(["completed", "retired"])]
    common_ids = np.intersect1d(orig["match_id"].to_numpy(), rep["match_id"].to_numpy())
    o = orig.set_index("match_id").loc[common_ids].reset_index()
    r = rep.set_index("match_id").loc[common_ids].reset_index()
    assert (o["a_won"].astype(bool).to_numpy() == r["a_won"].astype(bool).to_numpy()).all(), "orientation differs"
    # the repaired frame in this study's layout: repaired inputs, this study's context, ids, result and odds
    R = o[["match_id", "tour", "year", "group", "split", "a_won", "p_mkt", "tournament_date", "tournament_id"]].copy()
    R["in_elo_logit"] = logit(np.clip(r["p_elo"].to_numpy(dtype=float), T.EPS, 1 - T.EPS))
    for k, v in MAP.items():
        R[f"in_{k}"] = r[v].to_numpy(dtype=float)
    for c in CONTEXT:
        R[f"in_{c}"] = o[f"in_{c}"].to_numpy()
    R["p_elo"] = r["p_elo"].to_numpy(dtype=float)
    O = o[R.columns.drop(["in_elo_logit"] + [f"in_{k}" for k in MAP] + [f"in_{c}" for c in CONTEXT] + ["p_elo"])].copy()
    O["in_elo_logit"] = o["in_elo_logit"].to_numpy()
    for k in MAP:
        O[f"in_{k}"] = o[f"in_{k}"].to_numpy()
    for c in CONTEXT:
        O[f"in_{c}"] = o[f"in_{c}"].to_numpy()
    O["p_elo"] = o["p_elo"].to_numpy()
    for F in (R, O):
        F["mkt_logit"] = np.where(np.isfinite(F["p_mkt"].to_numpy(dtype=float)),
                                  logit(np.clip(F["p_mkt"].to_numpy(dtype=float), T.EPS, 1 - T.EPS)), np.nan)
    info = {"original_rows": int(len(orig)), "repaired_rows_in_scope": int(len(rep)), "common": int(len(common_ids)),
            "common_by_split": o.groupby(["split", "tour"]).size().rename("n").reset_index().to_dict("records")}
    return O, R, info


def run(F: pd.DataFrame) -> pd.DataFrame:
    diffs = DIFF25
    everything = [c for c in T.EVERYTHING if c in diffs]
    te = (F["split"] == "test").to_numpy()
    out = F.loc[te, ["match_id", "tour", "year", "group", "a_won", "p_mkt", "tournament_date"]].reset_index(drop=True)
    specs = [("elo", ["elo_logit"], False), ("lr_all", diffs, False), ("market", [], True),
             ("lr_mkt_profile", T.PROFILE16, True), ("lr_mkt_everything", everything, True),
             ("lr_mkt_everything_profile", everything + T.PROFILE16, True), ("lr_mkt_all", diffs, True)]
    for name, cols, mk in specs:
        p, _ = B.linear(F, cols, with_market=mk)
        out[f"p_{name}"] = p[te]
    for name, cols, additive, mk in (("gbm", diffs + CONTEXT, False, False), ("gbm_mkt_additive", diffs, True, True),
                                     ("gbm_mkt", diffs + CONTEXT, False, True)):
        p, meta = B.gbm_fit_predict(F, cols, additive, mk)
        out[f"p_{name}"] = p[te]
        T.log(f"  {name}: {meta['n_iter']} trees")
    return out


def score(P: pd.DataFrame) -> list[dict]:
    rows = []
    has = np.isfinite(P["p_mkt"].to_numpy(dtype=float))
    for t, sub in (("atp", (P["tour"] == "atp").to_numpy()), ("wta", (P["tour"] == "wta").to_numpy()),
                   ("both", np.ones(len(P), dtype=bool))):
        for b, m in [("market", x) for x in ("lr_mkt_profile", "lr_mkt_everything", "lr_mkt_everything_profile",
                                             "lr_mkt_all", "gbm_mkt_additive", "gbm_mkt")] + \
                    [("lr_mkt_all", "gbm_mkt"), ("gbm_mkt_additive", "gbm_mkt")]:
            rows.append({"tour": t, "section": "odds", **S.cmp(P, sub & has, b, m)})
        for b, m in (("elo", "lr_all"), ("lr_all", "gbm")):
            rows.append({"tour": t, "section": "no odds", **S.cmp(P, sub, b, m)})
    return rows


def main() -> int:
    O, R, info = frames()
    T.log(f"common matches: {info['common']:,} of {info['original_rows']:,} in this study's train/test")
    res = {"info": info, "inputs": DIFF25 + CONTEXT}
    table = []
    for label, F in (("original", O), ("repaired", R)):
        T.log(f"{label} features")
        P = run(F)
        for r in score(P):
            table.append({"features": label, **r})
    df = pd.DataFrame(table)
    df.to_csv(T.OUT / "repaired_check.csv", index=False)
    res["rows"] = table
    T.write_json(T.OUT / "repaired_check.json", res)
    for _, r in df.iterrows():
        T.log(f"{r['features']:9s} {r['tour']:4s} {r['base']:>18s} -> {r['model']:<26s} {r['gain']:+.2f} "
              f"[{r['lo']:+.2f}, {r['hi']:+.2f}] n={r['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
