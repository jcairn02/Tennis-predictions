"""Exploratory, added after the confirmation on the owner's question of 6 Oct 2026 ("what if the odds drift? using the
stronger predictor should still be better?"); not pre-registered. Uses only the saved confirmation predictions (three-seed
means, scored population): does the new representation beat base more where the closing market is less settled?

    best-vs-average spread   log(best price / average price) summed over both players (tennis-data's Max and Avg):
                             how far the books' prices are dispersed at the close (stale quotes, disagreement)
    Pinnacle vs average gap  |logit P(A) Pinnacle - logit P(A) average| (Pinnacle ends 13 Jan 2026)
    level                    Grand Slams, 1000s, 500s, 250s

Each split is cut into thirds of the 2022-2026 test matches. Milli-log-loss, positive = the arm is better than base,
paired 95% intervals over four-week blocks. Many cells are examined (3 splits x 3-4 bins x 3 tours x 2 arms), so a few
intervals clearing zero are expected by chance.

Writes data/studies/surface_elo_pieces/unsettled_market.csv. Run: ./python.sh src/eda/surface_elo_pieces/unsettled.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

ODDS = C.PD_OUT / "stage1_odds.parquet"


def main() -> int:
    f = pd.read_parquet(C.OUT / "predictions_confirm.parquet")
    f = f[~f["debut_season"]].copy()
    for arm in ("base", "primary", "literal"):
        f[f"p_{arm}"] = f[[f"p_{arm}_s{s}" for s in (0, 1, 2)]].mean(axis=1)
    o = pd.read_parquet(ODDS, columns=["match_id", "avg_a", "avg_b", "max_a", "max_b", "p_avg_a", "p_ps_a"])
    fr = pd.read_parquet(C.OUT / "frame.parquet", columns=["match_id", "group"])
    f = f.merge(o, on="match_id", how="left", validate="one_to_one").merge(fr, on="match_id", how="left",
                                                                         validate="one_to_one")
    f["spread"] = np.log(f["max_a"] / f["avg_a"]) + np.log(f["max_b"] / f["avg_b"])
    f["ps_vs_avg"] = np.abs(logit(f["p_ps_a"].clip(1e-6, 1 - 1e-6)) - logit(f["p_avg_a"].clip(1e-6, 1 - 1e-6)))
    cells = []
    for name, col in (("best-vs-average spread", "spread"), ("Pinnacle vs average gap", "ps_vs_avg")):
        ok = np.isfinite(f[col]).to_numpy()
        q = f.loc[ok, col].quantile([1 / 3, 2 / 3]).to_numpy()
        v = f[col].to_numpy()
        cells += [(name, "low third", ok & (v <= q[0])), (name, "middle third", ok & (v > q[0]) & (v <= q[1])),
                  (name, "high third (least settled)", ok & (v > q[1]))]
    cells += [("level", lev, (f["group"] == lev).to_numpy()) for lev in ("GS", "T1000", "T500", "T250")]
    rows = []
    for split, label, m in cells:
        for tour in ("atp", "wta", "both"):
            k = m & ((f["tour"] == tour).to_numpy() if tour != "both" else True)
            g = f[k]
            for arm in ("primary", "literal"):
                c = T.compare(T.ll(g["p_base"].to_numpy(), g["a_won"].to_numpy()),
                              T.ll(g[f"p_{arm}"].to_numpy(), g["a_won"].to_numpy()), g["tournament_date"].to_numpy())
                rows.append({"split": split, "bin": label, "tour": tour, "arm": arm, "matches": c["n"],
                             "gain_vs_base": c["gain"], "lo": c["lo"], "hi": c["hi"]})
    out = pd.DataFrame(rows)
    out.to_csv(C.OUT / "unsettled_market.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(out.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
