"""Step 4a (development seasons only, 2016-2024): the feature-interactions study's levels arm (H-S2: the 58 inputs plus
17 sums A + B, among them the Elo sum lv_elo; seeds 0-5) against the model (seeds 0-5).

    1. The pair-strength slope left in each forecast (b on s * eta, the screen's nuisance; negative = flatter for strong
       pairs): does TabPFN, given the levels, absorb the pattern?
    2. The calibrated paired gain, levels against model: one slope per tour fitted walk-forward on each arm's own
       out-of-sample seasons 2016 .. Y-1, scored 2017-2024; mLL per match, positive = levels better.

    ./python.sh src/eda/pair_strength/levels_check.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.pair_strength import common as C  # noqa: E402
from src.eda.pair_strength.score_arm import calibrate, gain  # noqa: E402
from src.eda.feature_interactions import tabpfn_tests as TT  # noqa: E402


def main() -> int:
    warnings.simplefilter("ignore")
    F = C.dev_frame()
    F = F[F["season"] >= 2016].reset_index(drop=True)
    seasons = range(2016, 2025)
    F["z_levels"] = C.lg(F["match_id"].map(TT.forecasts("levels", range(6), seasons)).to_numpy(float))
    F["z_model6"] = C.lg(F["match_id"].map(TT.forecasts("model", range(6), seasons)).to_numpy(float))
    if not (np.isfinite(F["z_levels"]).all() and np.isfinite(F["z_model6"]).all()):
        raise RuntimeError("matches without a forecast")
    s = F["s_elo_sum"].to_numpy(float)
    out = {"n": int(len(F))}
    for name in ("z_model6", "z_levels", "z_market"):
        out[f"slope_mod_{name}"] = C.slope_fit(F, np.ones(len(F), bool), F[name].to_numpy(float),
                                               {"elo_sum": s})["terms"]["elo_sum"]
        C.log(f"{name}: b {out[f'slope_mod_{name}']['b']:+.4f} z {out[f'slope_mod_{name}']['z']:+.2f}")
    pm = calibrate(F, F["z_model6"].to_numpy(float), 2017, 2016)
    pl = calibrate(F, F["z_levels"].to_numpy(float), 2017, 2016)
    out["levels_vs_model_2017_2024"] = gain(F, pm, pl, F["season"].to_numpy() >= 2017)
    C.log(f"levels vs model: {out['levels_vs_model_2017_2024']}")
    out["key"] = ("slope b: negative = flatter for strong pairs; gain in mLL per match, positive = the levels arm has the "
                  "lower log loss (better); 95% interval over four-week blocks; spanning 0 = tie")
    C.write_json(C.OUT / "levels_check.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
