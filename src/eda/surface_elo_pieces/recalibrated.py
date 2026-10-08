"""Post-hoc sensitivity, prompted on 6 Oct 2026 by a finding of the surface-IOS study (docs/studies/surface_ios/README.md,
side finding) relayed by another session: non-thinking TabPFN-3.5 is over-confident, and one calibration slope per tour,
fitted on the model's own earlier-season forecasts, brings it level with the paid thinking fit.

The same check on this study's paid TabPFN-3.5-Plus forecasts, with no new fit:

    slope       per arm and tour, a logistic fit without intercept of the result on the arm's log-odds over its 2019-2021
                pilot forecasts (walk-forward: each season trained on 2013 to the season before; base the mean of seeds 0
                and 1, primary and literal seed 0), scored population only
    applied     to the arm's 2022-2026 confirmation forecasts (the mean of seeds 0-2): expit(slope x logit p).
                elo_only and switch_only have no pilot forecasts and take base's slope (an approximation, labelled so)
    compared    the recalibrated arms against recalibrated base, against the paid TabPFN-3.5-Thinking fit (raw, as the
                surface-IOS study compared them), and against the closing price recalibrated on each fold's training
                matches; per tour and both tours, 2022-2026 and each season

Milli-log-loss, positive = the second-named forecast is better; paired 95% intervals over four-week blocks (they cover the
sampling of matches, not the seeds' variance). Writes data/studies/surface_elo_pieces/recalibrated.csv and
recalibrated.json. Run: ./python.sh src/eda/surface_elo_pieces/recalibrated.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

THINKING = ROOT / "data" / "studies" / "tabpfn_leakproof" / "test_predictions.parquet"
PILOT_SEEDS = {"base": (0, 1), "primary": (0,), "literal": (0,)}
ARMS = ("base", "primary", "literal", "elo_only", "switch_only")
EPS = 1e-9


def lg(p):
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def main() -> int:
    pil = pd.read_parquet(C.OUT / "predictions_pilot.parquet")
    pil = pil[~pil["debut_season"]]
    con = pd.read_parquet(C.OUT / "predictions_confirm.parquet")
    con = con[~con["debut_season"]].copy()
    th = pd.read_parquet(THINKING, columns=["match_id", "p_leakproof"])
    con = con.merge(th, on="match_id", how="left", validate="one_to_one")
    slopes = {}
    for arm, seeds in PILOT_SEEDS.items():
        x = lg(pil[[f"p_{arm}_s{s}" for s in seeds]].mean(axis=1))
        for tour in C.TOURS:
            k = (pil["tour"] == tour).to_numpy()
            beta, se = T.fit_logistic(x[k][:, None], pil.loc[k, "a_won"].to_numpy(float))
            slopes[(arm, tour)] = (float(beta[0]), float(se[0]))
    for arm in ("elo_only", "switch_only"):
        for tour in C.TOURS:
            slopes[(arm, tour)] = slopes[("base", tour)]
    for arm in ARMS:
        raw = con[[f"p_{arm}_s{s}" for s in (0, 1, 2)]].mean(axis=1).to_numpy()
        con[f"p_{arm}"] = raw
        s = np.where(con["tour"] == "atp", slopes[(arm, "atp")][0], slopes[(arm, "wta")][0])
        con[f"p_{arm}_recal"] = expit(s * lg(raw))
    con["p_thinking"] = con["p_leakproof"]
    pairs = ([("base_recal", f"{a}_recal") for a in ARMS if a != "base"]
             + [("thinking", "base_recal"), ("thinking", "primary_recal"), ("thinking", "base")]
             + [("market", f"{a}_recal") for a in ARMS] + [("market", "thinking"), ("base", "base_recal"),
                                                               ("primary", "primary_recal")])
    rows = []
    for tour in ("atp", "wta", "both"):
        tm = (con["tour"] == tour).to_numpy() if tour != "both" else np.ones(len(con), bool)
        for label, ss in [("2022-2026", range(2022, 2027))] + [(str(s), [s]) for s in range(2022, 2027)]:
            k = tm & con["season"].isin(list(ss)).to_numpy() & np.isfinite(con["p_thinking"].to_numpy())
            g = con[k]
            y = g["a_won"].to_numpy()
            for a, b in pairs:
                c = T.compare(T.ll(g[f"p_{a}"].to_numpy(), y), T.ll(g[f"p_{b}"].to_numpy(), y),
                              g["tournament_date"].to_numpy())
                rows.append({"tour": tour, "window": label, "base": a, "model": b, "matches": c["n"], "gain": c["gain"],
                             "lo": c["lo"], "hi": c["hi"], "week_lo": c["week_lo"], "week_hi": c["week_hi"]})
    R = pd.DataFrame(rows)
    R.to_csv(C.OUT / "recalibrated.csv", index=False)
    C.write_json(C.OUT / "recalibrated.json", {
        "key": "milli-log-loss; positive = the second-named forecast is better; 95% intervals over four-week blocks",
        "slopes_2019_2021": {f"{a}|{t}": {"slope": v[0], "se": v[1]} for (a, t), v in slopes.items()},
        "note": "elo_only and switch_only take base's slope (no pilot forecasts of their own)"})
    with pd.option_context("display.width", 220, "display.max_rows", 300):
        print({f"{a}|{t}": round(v[0], 3) for (a, t), v in slopes.items() if a in PILOT_SEEDS})
        print(R[R["window"] == "2022-2026"].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
