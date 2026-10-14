"""The current best model's forecasts for every match of the instance's frame, seasons 2019-2026, for the single check
(docs/studies/unpriced_leads/check_now_rules.md): both stages (the TabPFN 16-seed mean, recalibrated per tour, plus the
men's serve-speed term) and stage 1 alone.

The recipe is edge_anatomy/data.py's, which built the forecasts the registered looks read (analysis.parquet's q_full),
without its cut at 29 Jul 2026:
    * the forecast is the 16-seed mean of the instance's stored fits;
    * the per-tour calibration slopes and the men's speed coefficient b are fitted walk-forward on 2019 .. Y - 1 from
      seeds 0-3 (compare.walk_forward), debut seasons out, b shrunk with tau 0.05;
    * one departure: a 2026 match without a value in the speed column (the column was built on 8 Oct 2026 and ends on
      28 Jul 2026; also 40 women's matches of June 2026 whose ids changed) gets a speed term of 0, as women's matches
      always do, where edge_anatomy left such matches out. Only the 416 men's matches of 29 Jul - 23 Sep 2026 are
      affected. The term is small (2026: b = 0.037 per unit, the column's SD about 0.76 among men's non-zero values),
      and the flag `spd_filled` marks those matches. No fitted season lacks a value, so every coefficient is
      unchanged (run of 13 Oct 2026: 30,839 matches identical to analysis.parquet, max |diff| 0).

Results read: only what the walk-forward fits need. Season Y's coefficients read the results of 2019 .. Y - 1, so the
newest season, 2026, reads 2019-2025. No result of the 2026 season is read; the read is filtered and asserted. The
output holds no result column. The rebuilt forecasts are checked against analysis.parquet on every match both hold.

Writes data/studies/unpriced_leads/check_now/forecasts.parquet and forecasts_facts.json.
Run: ./python.sh src/eda/unpriced_leads/build_forecasts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402

C = CMP.C
FIRST, LAST = 2019, 2026
TEST = tuple(range(2020, LAST + 1))
OUT = ROOT / "data" / "studies" / "unpriced_leads" / "check_now"
STORED = ROOT / "data" / "studies" / "edge_anatomy" / "analysis.parquet"


def results_through(P: C.Paths, last_season: int) -> pd.Series:
    """The results of seasons <= last_season only (filtered in the read, then asserted)."""
    f = pd.read_parquet(P.model_frame, columns=["match_id", "season", "a_won"],
                        filters=[("season", "<=", last_season)])
    if len(f) and f["season"].max() > last_season:
        raise RuntimeError("a result after the last fitted season was read")
    return pd.Series(f["a_won"].astype(float).to_numpy(), index=f["match_id"].astype(str).to_numpy())


def build() -> tuple[pd.DataFrame, dict]:
    _, P, _ = CMP.candidate(str(E.INSTANCE))
    frame = CMP.inputs_frame(P)
    y = results_through(P, LAST - 1)
    s = pd.read_parquet(E.SPEED, columns=["match_id", "spd_L_B"]).astype({"match_id": str})
    z = s.drop_duplicates("match_id").set_index("match_id")["spd_L_B"]
    keep = frame["season"].between(FIRST, LAST).to_numpy()
    ids = frame.index[keep]
    no_speed = ids[~np.isfinite(z.reindex(ids).to_numpy(float))]
    if (frame.loc[no_speed, "season"].to_numpy() != LAST).any():
        raise RuntimeError("a match of a fitted season lacks its speed value")
    z = z.reindex(ids)
    z.loc[no_speed] = 0.0
    info = frame.loc[ids, ["tour", "season", "tournament_date", "debut_season"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y.reindex(ids).to_numpy(float)
    fit_rows = (info["season"] < LAST).to_numpy()
    if np.isnan(info.loc[fit_rows, "y"].to_numpy()).any():
        raise RuntimeError("a match of a fitted season lacks its result")
    if np.isfinite(info.loc[~fit_rows, "y"].to_numpy()).any():
        raise RuntimeError("a result of the newest season was loaded")
    seasons = tuple(range(FIRST, LAST + 1))
    p16, _ = F.seed_table("model", seasons, tuple(range(16)), F.FrameIndex(frame.reset_index()[["match_id", "season"]]),
                          P, "td", require_checks=True)
    p16 = p16.reindex(info.index)
    if p16.isna().any().any():
        raise RuntimeError("forecasts are missing for some matches")
    eta4 = pd.Series(C.lg(p16[[0, 1, 2, 3]].mean(axis=1).to_numpy()), index=p16.index)
    par_both = CMP.walk_forward(eta4, info, z, TEST)
    par_s1 = CMP.walk_forward(eta4, info, None, TEST)
    test = info.index[info["season"].isin(TEST).to_numpy()]
    q_both, _ = CMP.forecasts(p16, info, par_both, z, test)
    q_s1, _ = CMP.forecasts(p16, info, par_s1, None, test)
    out = info.loc[test, ["tour", "season", "tournament_date", "debut_season"]].copy()
    out["eta16"] = C.lg(p16.loc[test].mean(axis=1).to_numpy())
    out["spd"] = z.reindex(test).to_numpy(float)
    out["spd_filled"] = out.index.isin(no_speed)
    out["q_full"] = q_both
    out["q_full_s1"] = q_s1
    # the check against the stored forecasts (forecast columns only; the stored file's result column is not read)
    st = pd.read_parquet(STORED, columns=["match_id", "q_full", "q_full_s1"]).astype({"match_id": str})
    st = st.drop_duplicates("match_id").set_index("match_id")
    both = out.index.intersection(st.index[np.isfinite(st["q_full"].to_numpy(float))])
    d_full = float(np.max(np.abs(out.loc[both, "q_full"].to_numpy() - st.loc[both, "q_full"].to_numpy())))
    d_s1 = float(np.max(np.abs(out.loc[both, "q_full_s1"].to_numpy() - st.loc[both, "q_full_s1"].to_numpy())))
    if max(d_full, d_s1) > 1e-9:
        raise RuntimeError(f"the rebuilt forecasts differ from analysis.parquet (max {d_full:.2e}, {d_s1:.2e})")
    facts = {"seasons": [FIRST, LAST], "scored": [TEST[0], TEST[-1]], "matches_scored": int(len(test)),
             "speed_term_0_without_speed_value": int(len(no_speed)),
             "speed_term_0_by_tour": {str(k): int(v) for k, v in frame.loc[no_speed, "tour"].value_counts().items()},
             "results_read_through_season": LAST - 1,
             "checked_against_stored": {"matches": int(len(both)), "max_abs_diff_q_full": d_full,
                                        "max_abs_diff_q_full_s1": d_s1},
             "coefficients_both_stages": {str(k): v for k, v in par_both.items()},
             "coefficients_stage1": {str(k): v for k, v in par_s1.items()},
             "last_date": str(out["tournament_date"].max().date())}
    return out, facts


def main() -> int:
    out, facts = build()
    OUT.mkdir(parents=True, exist_ok=True)
    out.reset_index().rename(columns={"index": "match_id"}).to_parquet(OUT / "forecasts.parquet", index=False)
    (OUT / "forecasts_facts.json").write_text(json.dumps(facts, indent=1), encoding="utf-8")
    print(f"forecasts: {facts['matches_scored']:,} matches scored {facts['scored']}, last {facts['last_date']}; "
          f"speed term 0 (no speed value): {facts['speed_term_0_by_tour']}; checked against the stored forecasts on "
          f"{facts['checked_against_stored']['matches']:,} matches, max |diff| "
          f"{facts['checked_against_stored']['max_abs_diff_q_full']:.1e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
