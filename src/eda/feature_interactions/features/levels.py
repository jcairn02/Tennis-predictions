"""H-S2, the omnibus "levels" arm (plan.md): the two players' sums A + B of the model's own player inputs, as 17 context
columns (unchanged when A and B swap), so TabPFN can see the levels its difference-only inputs hide.

    lv_iosO_<s>, lv_iosD_<s>   surface-IOS offence / defence on the match's surface, s in the model's 7 statistics
    lv_elo                     overall Elo, R_A + R_B
    lv_age                     age_A + age_B (years)
    lv_sets14                  sets in the last 14 days, A + B

Writes data/studies/feature_interactions/features/levels.parquet and its registry entries. Reads no results.
Run: ./python.sh src/eda/feature_interactions/features/levels.py [--max-season 2024]
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.panel import check_swap, panel  # noqa: E402
from src.eda.feature_interactions.registry import register  # noqa: E402

STATS7 = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")


def build(P: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cols, specs = {"match_id": P["match_id"].to_numpy()}, {}
    for k, src in (("iosO", "srfO"), ("iosD", "srfD")):
        for s in STATS7:
            name = f"lv_{k}_{s}"
            cols[name] = P[f"ios_{src}_{s}_a"].to_numpy(float) + P[f"ios_{src}_{s}_b"].to_numpy(float)
            specs[name] = {"kind": "context", "desc": f"surface-IOS {'offence' if k == 'iosO' else 'defence'} of {s}, "
                                                      f"A + B (the model has A - B)"}
    for name, a, b, desc in (("lv_elo", "elo_R_a", "elo_R_b", "overall Elo ratings, A + B"),
                             ("lv_age", "age_pl_a", "age_pl_b", "ages, A + B"),
                             ("lv_sets14", "sets_14d_a", "sets_14d_b", "sets in the last 14 days, A + B")):
        cols[name] = P[a].to_numpy(float) + P[b].to_numpy(float)
        specs[name] = {"kind": "context", "desc": desc}
    return pd.DataFrame(cols), specs


def main() -> int:
    warnings.simplefilter("ignore")
    max_season = int(sys.argv[sys.argv.index("--max-season") + 1]) if "--max-season" in sys.argv else 2024
    P = panel(max_season=max_season)
    F, specs = build(P)
    for name in specs:
        if not check_swap(lambda Q, n=name: build(Q)[0][n].to_numpy(), P, kind="context"):
            raise RuntimeError(f"{name}: not symmetric")
    register("levels", F, specs)
    cov = {n: round(float(np.isfinite(F[n]).mean()), 3) for n in specs}
    C.log(f"levels: {len(F):,} matches to {max_season}; coverage {cov}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
