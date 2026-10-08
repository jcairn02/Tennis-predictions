"""Step 5 (development seasons only, 2015-2024): where the elosum arm's gain over the current best comes from, and
whether it survives a change of the model's seeds and a placebo.

Both arms are calibrated walk-forward from 2014 (one slope per tour on each arm's own out-of-sample seasons 2014 .. Y-1)
and compared by paired log loss, mLL per match, positive = the elosum arm has the lower log loss (better); 95%
intervals over four-week blocks. Subsets: tour, level, pair-strength fifth (per tour, edges on 2014-2021), the price's
favourite probability band, best of five, surface. Seed check: elosum (seeds 0-2) against the model's seeds 3-5
(2016-2024). Placebo: elosum_perm (the column permuted within tour x season) against the model, when its fits exist.

    ./python.sh src/eda/pair_strength/where_gain.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.pair_strength import common as C  # noqa: E402
from src.eda.pair_strength.score_arm import calibrate, gain  # noqa: E402
from src.eda.feature_interactions import tabpfn_tests as TT  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402


def arm_eta(arm: str, seeds, seasons) -> pd.Series:
    parts = []
    for season in seasons:
        per = []
        for seed in seeds:
            with np.load(C.LOCAL / f"{arm}__{season}__seed{seed}.npz", allow_pickle=False) as z:
                p, ids = z["p_td"], z["ids_td"]
                k = len(ids)
                per.append(pd.Series(T.symmetrize(p[:k], p[k:]), index=ids.astype(str)))
        parts.append(pd.concat(per, axis=1).mean(axis=1))
    s = pd.concat(parts)
    return pd.Series(C.lg(s.to_numpy()), index=s.index)


def main() -> int:
    warnings.simplefilter("ignore")
    F = C.dev_frame()
    season, tour = F["season"].to_numpy(), F["tour"].to_numpy()
    e_model = F["z_model"].to_numpy(float)
    e_arm = F["match_id"].map(arm_eta("elosum", range(3), range(2014, 2025))).to_numpy(float)
    pm, pa = calibrate(F, e_model, 2015, 2014), calibrate(F, e_arm, 2015, 2014)
    rows = season >= 2015
    out = {}
    lv = F["level"].astype(str).to_numpy()
    q = np.full(len(F), -1)
    for t in C.TOURS:
        m = tour == t
        ed = np.quantile(F["pr_elo_sum"].to_numpy(float)[m & C.disc_mask(F)], [0.2, 0.4, 0.6, 0.8])
        q[m] = np.digitize(F["pr_elo_sum"].to_numpy(float)[m], ed)
    fav = expit(np.abs(F["z_market"].to_numpy(float)))
    bands = np.digitize(fav, [0.6, 0.7, 0.8, 0.9])
    bo5 = pd.to_numeric(F["best_of"], errors="coerce").to_numpy(float) == 5
    surf = F["surface"].astype(str).to_numpy()
    subsets = {"all": rows, "atp": rows & (tour == "atp"), "wta": rows & (tour == "wta"),
               **{f"level {k}": rows & np.isin(lv, v) for k, v in
                  {"GS+FIN": ("GS", "FIN"), "T1000": ("T1000",), "T500": ("T500",), "T250": ("T250",)}.items()},
               **{f"pair-strength fifth {b + 1}": rows & (q == b) for b in range(5)},
               **{f"favourite {lab}": rows & (bands == b) for b, lab in
                  enumerate(("50-60%", "60-70%", "70-80%", "80-90%", "90%+"))},
               "best of 5": rows & bo5, "best of 3": rows & ~bo5,
               **{f"surface {s}": rows & (surf == s) for s in ("Hard", "Clay", "Grass")}}
    out["by_subset"] = {k: gain(F, pm, pa, m) for k, m in subsets.items()}
    for k, v in out["by_subset"].items():
        C.log(f"{k:24s} n {v['n']:6d}  {v['gain']:+.3f} [{v['lo']:+.3f}, {v['hi']:+.3f}]")
    # seed check: the model's seeds 3-5 (2016-2024), the arm's 0-2
    s16 = range(2016, 2025)
    m35 = F["match_id"].map(TT.forecasts("model", (3, 4, 5), s16)).to_numpy(float)
    keep = np.isfinite(m35)
    G = F[keep].reset_index(drop=True)
    e35 = C.lg(m35[keep])
    p35, pa16 = calibrate(G, e35, 2017, 2016), calibrate(G, e_arm[keep], 2017, 2016)
    p02 = calibrate(G, e_model[keep], 2017, 2016)
    r = G["season"].to_numpy() >= 2017
    out["seed_check_2017_2024"] = {"arm_vs_model_seeds_3_5": gain(G, p35, pa16, r),
                                   "arm_vs_model_seeds_0_2": gain(G, p02, pa16, r),
                                   "model_seeds_3_5_vs_0_2": gain(G, p02, p35, r)}
    C.log(f"seed check: {out['seed_check_2017_2024']}")
    # placebo
    if all((C.LOCAL / f"elosum_perm__{y}__seed{k}.npz").exists() for y in range(2014, 2025) for k in range(3)):
        e_perm = F["match_id"].map(arm_eta("elosum_perm", range(3), range(2014, 2025))).to_numpy(float)
        pp = calibrate(F, e_perm, 2015, 2014)
        pp19, pm19 = calibrate(F, e_perm, 2020, 2019), calibrate(F, e_model, 2020, 2019)
        out["placebo"] = {"perm_vs_model_2015_2024": gain(F, pm, pp, rows),
                          "perm_vs_model_decided_cal_2020_2024": gain(F, pm19, pp19, season >= 2020),
                          "arm_vs_perm_2015_2024": gain(F, pp, pa, rows),
                          "perm_slope_mod": C.slope_fit(F, np.ones(len(F), bool), e_perm,
                                                        {"elo_sum": F["s_elo_sum"].to_numpy(float)})["terms"]["elo_sum"]}
        C.log(f"placebo: {out['placebo']}")
    out["key"] = ("gains in mLL per match, positive = the second-named (the elosum arm, or as named) has the lower log "
                  "loss (better); 95% intervals over four-week blocks; spanning 0 = tie")
    C.write_json(C.OUT / "where_gain.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
