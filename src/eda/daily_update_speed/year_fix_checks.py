"""The 2027 fix's equality checks (docs/studies/daily_update_speed/): on the data held today, every changed rule gives
what the rule before 10 Oct 2026 gave. Reads the repository's tables and the frozen reference's Stage 0; writes
data/studies/daily_update_speed/year_fix_checks.json.

    stage0_evaluation   C.in_evaluation on each Stage 0 against its stored evaluation flag (repository; frozen reference)
    years               the latest season in each table the rules read (no row after 2026, so every cap was inactive)
    stage1_seasons      Stage 1's per-season loop: the same seasons in the same order
    pool                Stage 4's pool mask, old rule (2010-2026) against new (2010 on), on the repository's Stage 4 rows
    split               the frame split, old rule against new, on the repository's thinking frame
    eras                both era helpers, old against new, on Stage 0's seasons
    slam_feeds          the Grand Slam feed rows (srcc_slams.ausopen, slamtracker) with the per-row bound against the
                        bound of before (EPOCH_OK's end for every row): equal tables
    stage2_next         serve-speed adjustment: whether 2027 is fittable today (it was the only extra season before)
Run: ./python.sh src/eda/daily_update_speed/year_fix_checks.py
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

from src.eda.match_timing import srcc_slams as SL  # noqa: E402
from src.eda.match_timing import timing as TM  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

OUT = ROOT / "data" / "studies" / "daily_update_speed" / "year_fix_checks.json"
REF_STAGE0 = (ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "tables"
              / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet")


def old_era_timing(year: pd.Series) -> pd.Series:
    out = pd.Series("", index=year.index, dtype=object)
    for a, b in TM.ERAS:
        out[year.between(a, b)] = f"{a}-{b}"
    return out


def old_era_common(year: pd.Series) -> pd.Series:
    out = pd.Series(pd.NA, index=year.index, dtype="object")
    for name, years in C.ERAS.items():
        out[year.isin(list(years))] = name
    return out


def same_frames(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    return a.shape == b.shape and bool(a.equals(b))


def main() -> int:
    out: dict = {}
    cols = ["match_id", "year", "level", "status", "evaluation"]
    for name, path in (("repository", C.OUT / "stage0_matches.parquet"), ("frozen_reference", REF_STAGE0)):
        if not path.exists():
            out[f"stage0_evaluation_{name}"] = {"path": str(path), "present": False}
            continue
        m = pd.read_parquet(path, columns=cols)
        new = C.in_evaluation(m)
        out[f"stage0_evaluation_{name}"] = {"matches": int(len(m)), "max_year": int(m["year"].max()),
                                            "equal": bool((new == m["evaluation"].astype(bool)).all())}
    m = pd.read_parquet(C.OUT / "stage0_matches.parquet", columns=cols)
    ev_years = set(m.loc[m["evaluation"], "year"].astype(int))
    out["stage1_seasons_equal"] = sorted(set(C.EVAL_YEARS) | ev_years) == list(C.EVAL_YEARS)
    y = m["year"]
    out["eras_timing_equal"] = bool(old_era_timing(y).equals(TM.era_of(y)))
    oc, nc = old_era_common(y), C.era_of(y)
    out["eras_common_equal"] = bool(((oc == nc) | (oc.isna() & nc.isna())).all())
    s4 = C.OUT / "stage4_features.parquet"
    if s4.exists():
        f = pd.read_parquet(s4, columns=["year"])
        out["stage4_rows_max_year"] = int(f["year"].max())
        out["pool_old_equals_new"] = bool((f["year"].between(C.FIRST_YEAR, 2026) == f["year"].ge(C.FIRST_YEAR)).all())
    th = ROOT / "data" / "studies" / "tabpfn_thinking" / "frame.parquet"
    if th.exists():
        f = pd.read_parquet(th, columns=["year"])
        yr = f["year"].to_numpy()
        out["frame_max_year"] = int(yr.max())
        out["split_old_equals_new"] = bool(((yr >= 2022) & (yr <= 2026)).sum() == (yr >= 2022).sum())
    # the Grand Slam feeds: the per-row bound against the old constant bound
    real = SL.epoch_hi
    new_rows = {"ausopen": SL.ausopen(), **{s: SL.slamtracker(s) for s in ("wimbledon", "usopen")}}
    SL.epoch_hi = lambda year: np.full(len(np.asarray(year)), SL.EPOCH_OK[1])
    try:
        old_rows = {"ausopen": SL.ausopen(), **{s: SL.slamtracker(s) for s in ("wimbledon", "usopen")}}
    finally:
        SL.epoch_hi = real
    out["slam_feeds"] = {k: {"rows": int(len(new_rows[k])), "max_year": int(new_rows[k]["year"].max()),
                             "equal": same_frames(new_rows[k], old_rows[k])} for k in new_rows}
    try:
        from src.eda.serve_speed_tabpfn import common as SC
        from src.eda.serve_speed_tabpfn.adaptive import adjust as AD
        ok, why = AD.fittable(SC.DEFAULT, 2027)
        out["stage2_2027_fittable_today"] = {"fittable": bool(ok), "why": why}
    except Exception as e:                        # noqa: BLE001  (recorded)
        out["stage2_2027_fittable_today"] = {"error": f"{type(e).__name__}: {e}"[:300]}
    flat = [v for k, v in out.items() if k.endswith("_equal")]
    flat += [v["equal"] for k, v in out.items() if k.startswith("stage0_evaluation") and "equal" in v]
    flat += [v["equal"] for v in out["slam_feeds"].values()]
    out["all_equal"] = bool(all(flat))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0 if out["all_equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
