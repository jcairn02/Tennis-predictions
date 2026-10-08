"""The swap in the model as it stands. After the race, the owner decided on 6 Oct 2026 to swap the old Elo blend for
the offset Elo in the model (docs/decisions/2026-10-06-offset-elo.md). The race tested the swap on the best 2026
model's inputs; the model that day also carried the surface IOS profile, kept by a decision of the same day
(docs/decisions/2026-10-06-surface-ios-profile.md). This checks the swap on top of it, with the race's fits,
calibration and scoring (local_fits.py, score.py):

    sprof   the model before the swap (the surface-IOS study's arm sprof: its 21 IOS profile inputs built per surface)
    model   the model after it (sprof with the race's elo_off swap; model_frame.py writes its inputs)

Comparisons: sprof -> model (the swap in the model), base -> sprof (the surface profile alone: a cross-check of the
surface-IOS study inside this pipeline), elo_off -> model (the surface profile on top of the swap), base -> model (both
decisions together). Settings as the race: at the close and without the odds, 2022-2026; fed the Polymarket price
24 hours and 30 minutes before the start, 2025-2026; the move from 24 hours to 30 minutes toward model's no-odds view
beyond sprof's and beyond base's. A check run after the decision, not pre-registered; reported whatever it shows.

Writes data/studies/surface_rating_race/composed_results.csv and composed_moves.csv.
Run: ./python.sh src/eda/surface_rating_race/composed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_rating_race import common as C  # noqa: E402
from src.eda.surface_rating_race import score as S  # noqa: E402

PAIRS = [("sprof", "model"), ("base", "sprof"), ("elo_off", "model"), ("base", "model")]
WITH_ODDS = ("sprof", "model")
MOVE_PAIRS = [("sprof", "model"), ("base", "model")]


def main() -> int:
    F, _, slopes = S.build(partial=False)
    R, M = S.comparisons(F, PAIRS, WITH_ODDS, MOVE_PAIRS)
    R.to_csv(C.OUT / "composed_results.csv", index=False)
    M.to_csv(C.OUT / "composed_moves.csv", index=False)
    show = R[R["population"].isin(["excl_debut", "early_all"]) & R["calibrated"]]
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print({f"{a}|{t}": round(v[0], 3) for (a, t), v in slopes.items() if a.split("_noodds")[0] in ("sprof", "model")})
        print(show[["setting", "tour", "base", "model", "matches", "gain", "lo", "hi", "s_mean", "s_positive",
                    "s_gains"]].round(2).to_string(index=False))
        print(M[(M["clusters_by"] == "block") & M["calibrated"]].drop(columns=["clusters_by", "calibrated"])
              .round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
