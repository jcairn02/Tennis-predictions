"""Step 4 (development seasons only, 2014-2024): the TabPFN arm "elosum" (the 58 inputs plus the pair's Elo sum,
local_fits.py) against the current best, both with seeds 0-2.

    1. The arm's own pair-strength slope: does giving TabPFN the Elo sum remove the pattern? (b on s * eta, the screen's
       nuisance; negative = flatter for strong pairs)
    2. Calibrated paired gains, milli-log-loss, positive = the arm has the lower log loss (better): with the decided
       calibration (one slope per tour on each arm's own out-of-sample seasons 2019 .. Y-1; 2020-2024) and with the
       same layer fitted from 2014 (2015-2024)
    3. The encompassing test of the arm's deviation beyond the model, disjoint seeds as the critique's 1.7 requires:
       base eta from model seeds 3-5, deviation = eta_elosum(0-2) - eta_model(0-2), 2016-2024 (positive = the arm adds
       information)

    ./python.sh src/eda/pair_strength/score_arm.py
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
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions import tabpfn_tests as TT  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

ARM = "elosum"


def arm_forecast(seeds, seasons, block: str = "td") -> pd.Series:
    """Seed-mean symmetrised P(A wins) of the elosum arm by match id."""
    parts = []
    for season in seasons:
        per = []
        for seed in seeds:
            with np.load(C.LOCAL / f"{ARM}__{season}__seed{seed}.npz", allow_pickle=False) as z:
                p, ids = z[f"p_{block}"], z[f"ids_{block}"]
                k = len(ids)
                per.append(pd.Series(T.symmetrize(p[:k], p[k:]), index=ids.astype(str)))
        parts.append(pd.concat(per, axis=1).mean(axis=1))
    return pd.concat(parts)


def calibrate(F: pd.DataFrame, eta: np.ndarray, first: int, fit_from: int) -> np.ndarray:
    """One slope per tour, for each season Y >= first fitted on seasons fit_from .. Y-1 of the same forecasts."""
    season, y = F["season"].to_numpy(), F["a_won"].to_numpy(float)
    atp = (F["tour"] == "atp").to_numpy()
    p = np.full(len(F), np.nan)
    for Y in range(first, int(season.max()) + 1):
        tr, te = (season >= fit_from) & (season < Y), season == Y
        Z = lambda m: np.column_stack([np.where(atp[m], eta[m], 0.0), np.where(~atp[m], eta[m], 0.0)])  # noqa: E731
        b, _, _ = S.fit(Z(tr), y[tr])
        p[te] = expit(Z(te) @ b)
    return p


def gain(F, pa, pb, rows) -> dict:
    ok = rows & np.isfinite(pa) & np.isfinite(pb)
    yb = F["a_won"].to_numpy(bool)[ok]
    c = C.compare(C.ll(pa[ok], yb), C.ll(pb[ok], yb), F.loc[ok, "tournament_date"].to_numpy())
    return {"n": int(c["n"]), "gain": float(c["gain"]), "lo": float(c["lo"]), "hi": float(c["hi"])}


def main() -> int:
    warnings.simplefilter("ignore")
    F = C.dev_frame()
    seasons = range(2014, 2025)
    F["z_arm"] = C.lg(F["match_id"].map(arm_forecast(range(3), seasons)).to_numpy(float))
    if not np.isfinite(F["z_arm"]).all():
        raise RuntimeError("development matches without an elosum forecast")
    e_model, e_arm = F["z_model"].to_numpy(float), F["z_arm"].to_numpy(float)
    s = F["s_elo_sum"].to_numpy(float)
    season, tour = F["season"].to_numpy(), F["tour"].to_numpy()
    out = {"n": int(len(F))}
    # 1. the pair-strength slope left in each forecast
    for name, e in (("model", e_model), ("elosum", e_arm)):
        r = C.by_window(F, e, {"elo_sum": s})
        out[f"slope_mod_{name}"] = {w: r[w]["terms"]["elo_sum"] for w in ("2014-2021", "2022-2024")} | \
            {"joint_z": r["joint_z"]["elo_sum"]}
        pooled = C.slope_fit(F, np.ones(len(F), bool), e, {"elo_sum": s})["terms"]["elo_sum"]
        out[f"slope_mod_{name}_pooled"] = pooled
        C.log(f"{name}: pair-strength slope b {pooled['b']:+.4f} (z {pooled['z']:+.2f}); joint z "
              f"{r['joint_z']['elo_sum']:+.2f}")
    # 2. calibrated gains, arm against model (positive = the arm better)
    pm19, pa19 = calibrate(F, e_model, 2020, 2019), calibrate(F, e_arm, 2020, 2019)
    pm14, pa14 = calibrate(F, e_model, 2015, 2014), calibrate(F, e_arm, 2015, 2014)
    out["gain_decided_cal_2020_2024"] = {k: gain(F, pm19, pa19, (season >= 2020) & m) for k, m in
                                         (("both", np.ones(len(F), bool)), ("atp", tour == "atp"),
                                          ("wta", tour == "wta"))}
    out["gain_cal14_2015_2024"] = {k: gain(F, pm14, pa14, (season >= 2015) & m) for k, m in
                                   (("both", np.ones(len(F), bool)), ("2015-2021", season <= 2021),
                                    ("2022-2024", season >= 2022))}
    out["raw_gain_2014_2024"] = gain(F, expit(e_model), expit(e_arm), np.ones(len(F), bool))
    g = out["gain_decided_cal_2020_2024"]["both"]
    C.log(f"elosum vs model, decided calibration 2020-2024: {g['gain']:+.3f} [{g['lo']:+.3f}, {g['hi']:+.3f}] mLL")
    # 3. encompassing, disjoint seeds (2016-2024)
    rows = season >= 2016
    G = F[rows].reset_index(drop=True)
    base = C.lg(G["match_id"].map(TT.forecasts("model", (3, 4, 5), range(2016, 2025))).to_numpy(float))
    dev = G["z_arm"].to_numpy(float) - G["z_model"].to_numpy(float)
    out["encompassing_2016_2024"] = TT.encompassing(G, base, dev)
    C.log(f"encompassing b {out['encompassing_2016_2024']['b']:+.3f} [{out['encompassing_2016_2024']['lo']:+.3f}, "
          f"{out['encompassing_2016_2024']['hi']:+.3f}]")
    out["key"] = ("slope b: negative = flatter for strong pairs; gains in mLL, positive = the elosum arm has the lower log "
                  "loss; encompassing b positive = the arm adds information beyond the model; 95% intervals spanning 0 "
                  "= tie")
    C.write_json(C.OUT / "score_arm.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
