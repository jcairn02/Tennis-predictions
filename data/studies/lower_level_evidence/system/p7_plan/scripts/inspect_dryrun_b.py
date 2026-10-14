"""G's dry run, step 2b: read the code check's parameter rows (B's estimator on C0_now, statistic spw, seasons 2021-2022,
2 bootstrap draws) against B's frozen dev rows of the same cells. Dev seasons only (2021-2022); nothing sealed is read.
A CODE CHECK, NOT EVIDENCE: the frozen strength file (no rating for C0_now's new matches), half-life grid 26/52, 2 draws.

Run: ./python.sh data/studies/lower_level_evidence/system/p7_plan/scripts/inspect_dryrun_b.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path("C:/Users/zerom/Documents/Tennis-predictions")
DRY = ROOT / "data/studies/lower_level_evidence/system/p7_plan/dryrun_b_c0now"
FROZEN = ROOT / "data/studies/lower_level_evidence/system/relationship/params_dev.parquet"
COLS = ["season_used", "tour", "stat", "level", "fitted", "w", "w_free", "delta", "gamma", "strength_ref", "h_weeks",
        "fit_through", "translate_mode", "n_players"]


def main() -> int:
    d = pd.read_parquet(DRY / "params_dev.parquet")
    f = pd.read_parquet(FROZEN)
    f = f[f["stat"].eq("spw") & f["season_used"].isin([2021, 2022])]
    keep = [c for c in COLS if c in d.columns]
    m = d[keep].merge(f[[c for c in keep if c in f.columns]], on=["season_used", "tour", "stat", "level"],
                      how="left", suffixes=("", "_frozen"))
    pd.set_option("display.width", 250)
    show = ["season_used", "tour", "level", "fitted", "fitted_frozen", "w", "w_frozen", "delta", "delta_frozen",
            "gamma", "gamma_frozen", "h_weeks", "h_weeks_frozen", "fit_through"]
    print(m[[c for c in show if c in m.columns]].to_string(index=False))
    g = m.drop_duplicates(["season_used", "tour"])
    out = {"what": "code check, not evidence (frozen strength, h grid 26/52, 2 draws, spw only)",
           "itf_rows": m[m["level"].eq("ITF")][[c for c in show if c in m.columns]].to_dict("records"),
           "gamma_equal_to_frozen": {f"{r.season_used}|{r.tour}": [float(r.gamma), float(r.gamma_frozen)]
                                     for r in g.itertuples()},
           "fit_through_by_season": {int(k): str(v) for k, v in d.groupby("season_used")["fit_through"].max().items()}}
    (DRY / "inspect.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
