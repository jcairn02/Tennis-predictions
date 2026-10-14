"""Side check of the training-window study: where the speed adjustment's 2023 loss sits.

Walk-forward on 2020-2024 the current model's speed adjustment (score.py's speed_adjustment rows) lost clearly in 2023
for men. This breaks the loss down, per men's frame match of 2022-2024 (+ = the adjustment helped, mLL):
    * by the size of the speed term, |spd_L| (the weekly feed's 28-day column);
    * by month;
    * by whether either player had, in the 60 days before, one of the 130 serve-speed records that three reviewers
      confirmed impossible on 8 Oct 2026 (data/studies/input_data_audit/fixes/speed_exclusions.csv; written, not
      applied: docs/decisions/2026-10-08-corrupt-data-fixes.md), and whether the speed panel used it.

Seasons <= 2024 only, as the rest of the study. Writes data/studies/training_window/speed_check.json.
Run: ./python.sh src/eda/training_window/speed_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.training_window import common as C  # noqa: E402
from src.eda.training_window import score as S  # noqa: E402

EXCLUSIONS = ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "speed_exclusions.csv"
WINDOW_DAYS = 60
SEASONS = (2022, 2023, 2024)


def bad_records() -> pd.DataFrame:
    """The panel records the exclusions name, once each: a record confirmed impossible from both sources (handoff and
    ManTennisData) is listed twice in the exclusions but is one panel row (the panel is unique on match and side)."""
    ex = pd.read_csv(EXCLUSIONS)
    pan = pd.read_parquet(C.P.panel, columns=["match_id", "side", "player_id", "tournament_date", "y_raw", "use",
                                              "drop_reason"])
    keys = ex.drop_duplicates(["match_id", "side"])[["match_id", "side", "y_raw"]]
    j = keys.merge(pan, on=["match_id", "side"], how="left", validate="one_to_one", indicator=True,
                   suffixes=("_listed", ""))
    if (j["_merge"] != "both").any():
        raise RuntimeError("an excluded record is not in the speed panel")
    if ((j["y_raw_listed"] - j["y_raw"]).abs() > 0.6).any():
        raise RuntimeError("the panel holds another value than the one listed as impossible")
    j["tournament_date"] = pd.to_datetime(j["tournament_date"])
    j.attrs["listed_rows"] = int(len(ex))
    return j


def near_bad(rows: pd.DataFrame, bad: pd.DataFrame) -> np.ndarray:
    """True where player A or B has a used bad record dated 1..WINDOW_DAYS days before the match's event."""
    by_player = {p: g["tournament_date"].to_numpy() for p, g in bad[bad["use"] == True].groupby("player_id")}  # noqa: E712
    out = np.zeros(len(rows), bool)
    for i, (a, b, day) in enumerate(zip(rows["player_a_id"], rows["player_b_id"], rows["tournament_date"].to_numpy())):
        for p in (a, b):
            if p in by_player:
                dd = (day - by_player[p]).astype("timedelta64[D]").astype(int)
                if ((dd > 0) & (dd <= WINDOW_DAYS)).any():
                    out[i] = True
    return out


def part(g: pd.DataFrame) -> dict:
    return {"matches": int(len(g)), "mean": float(g["gain"].mean()), "sum": float(g["gain"].sum())}


def main() -> int:
    saved = C.ARMS, C.NEW_ARMS
    C.ARMS, C.NEW_ARMS = ("exp",), ()                  # only the current model is needed
    try:
        info, fc, extra, params = S.build(C.load_frame(labels=True))
    finally:
        C.ARMS, C.NEW_ARMS = saved
    bad = bad_records()
    s0 = pd.read_parquet(C.P.stage0_pre, columns=["match_id", "player_a_id", "player_b_id"])
    s0["match_id"] = s0["match_id"].astype(str)
    out = {"what": "the speed adjustment's walk-forward value per men's match (exp two-stage minus its calibrated stage "
                   "1, mLL; + = the adjustment helped)",
           "bad_records": {"listed_rows": bad.attrs["listed_rows"], "panel_records": int(len(bad)),
                           "used_by_the_panel": int((bad["use"] == True).sum()),  # noqa: E712
                           "used_by_year": {str(k): int(v) for k, v in bad.loc[bad["use"] == True, "tournament_date"]  # noqa: E712
                                            .dt.year.value_counts().sort_index().items()}},
           "window_days": WINDOW_DAYS, "seasons": {}}
    season = info["season"].to_numpy()
    for yr in SEASONS:
        m = extra["test_mask"] & (season == yr) & info["atp"].to_numpy()
        rows = info[m].join(s0.set_index("match_id"))
        y = rows["y"].to_numpy()
        rows["gain"] = 1000 * (C.ll(fc["exp_stage1"][0][m], y) - C.ll(fc["exp"][0][m], y))
        rows["size"] = pd.cut(np.abs(rows["z"]), [-0.01, 0.5, 1, 2, 4.01], labels=["<=0.5", "0.5-1", "1-2", ">2"])
        rows["near_bad"] = near_bad(rows, bad)
        out["seasons"][str(yr)] = {
            "all": part(rows),
            "by_speed_term_size": {str(k): part(g) for k, g in rows.groupby("size", observed=True)},
            "by_month": {str(int(k)): part(g) for k, g in rows.groupby(rows["tournament_date"].dt.month)},
            "near_a_used_bad_record": part(rows[rows["near_bad"]]), "not_near": part(rows[~rows["near_bad"]])}
    C.write_json(C.OUT / "speed_check.json", out)
    for yr, r in out["seasons"].items():
        print(yr, {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in r.items() if k in ("all", "near_a_used_bad_record", "not_near")})
        print("   by size", {k: round(v["mean"], 2) for k, v in r["by_speed_term_size"].items()},
              {k: v["matches"] for k, v in r["by_speed_term_size"].items()})
    print(out["bad_records"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
