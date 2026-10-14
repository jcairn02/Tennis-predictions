"""Bet timing, step 3b: the model trained on BetOnline's opening line against the plug-in (fits_lines.py), on the same
matches. Does it matter that the decided model was trained on closing prices and is fed an earlier one at bet time?

Forecasts: each arm's queries symmetrised and averaged over seeds 0-3. Calibrated: one slope per tour on the forecast's
log-odds, fitted on its own out-of-sample forecasts of the earlier test seasons (2021 .. Y - 1, debut seasons out), so
the calibrated comparisons start in 2022; raw comparisons cover 2021-2026.

    plug-in        line_close fed the opening line
    open-trained   line_open fed the opening line
    close-fed      line_close fed the last line (the edge at the close, the same training)
    current best   the main study's q_bol_open (2013 .. Y - 1 on the market-average close, the decided calibration or
                   both stages): a reference with a larger, different training set

Milli-log-loss, + = the second named better; paired cluster-t intervals over four-week blocks. Also each forecast's
realisation of its disagreement with the opening line (score.logit_cluster: 1 right-sized, above 1 under-reacting).
Writes data/studies/bet_timing/results_lines.json. Reads the results (a_won) here only.
Run: ./python.sh src/eda/bet_timing/score_lines.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402
from src.eda.bet_timing import fits_lines as FL  # noqa: E402
from src.eda.bet_timing import score as SS  # noqa: E402
from src.eda.tabpfn_thinking.common import fit_logistic, ll  # noqa: E402

FORECASTS = {"plugin": ("line_close", "open"), "open_trained": ("line_open", "open"), "close_fed": ("line_close", "close")}


def raw_forecasts(seasons=FL.TEST_SEASONS, seeds=C.SEEDS) -> pd.DataFrame:
    cols = {}
    for name, (arm, q) in FORECASTS.items():
        parts = []
        for season in seasons:
            per, ids = [], None
            for k in seeds:
                with np.load(FL.fit_path(arm, season, k), allow_pickle=False) as z:
                    p, i = z[f"p_{q}"], z[f"ids_{q}"].astype(str)
                if ids is not None and not np.array_equal(i, ids):
                    raise RuntimeError(f"{arm} {season}: seeds hold different matches")
                ids, n = i, len(i)
                per.append(0.5 * (p[:n] + 1.0 - p[n:]))
            parts.append(pd.Series(np.mean(per, axis=0), index=ids))
        cols[f"raw_{name}"] = pd.concat(parts)
    out = pd.DataFrame(cols)
    out.index.name = "match_id"
    return out


def walk_forward_calibrated(x: pd.DataFrame, col: str) -> np.ndarray:
    """One slope per tour on logit(col), fitted on the seasons before Y (from the first test season), debut out."""
    out = np.full(len(x), np.nan)
    z = C.lg(x[col].to_numpy(float))
    season, tour = x["season"].to_numpy(), x["tour"].to_numpy()
    fit_rows = ~x["debut_season"].astype(bool).to_numpy()
    for y_ in sorted(set(season))[1:]:
        for t in ("atp", "wta"):
            tr = fit_rows & (season < y_) & (tour == t)
            te = (season == y_) & (tour == t)
            beta, _ = fit_logistic(z[tr][:, None], x["y"].to_numpy(float)[tr])
            out[te] = C.ex(beta[0] * z[te])
    return out


def compare(g: pd.DataFrame, base: str, arm: str) -> dict:
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    return SS.mean_ci(ll(g[base].to_numpy(float), y) - ll(g[arm].to_numpy(float), y), blk)


def main() -> int:
    x = SS.load()                     # the main study's frame with q_bol_open, y, blocks
    x = x[x["season"].isin(FL.TEST_SEASONS)].reset_index(drop=True)
    f = raw_forecasts()
    x = x.join(f, on="match_id", how="inner")
    x = x[~x["debut_season"].astype(bool) & x["y"].notna()].reset_index(drop=True)
    for name in FORECASTS:
        x[f"cal_{name}"] = walk_forward_calibrated(x, f"raw_{name}")
    res = {"matches": int(len(x)), "by_season": x.groupby("season").size().to_dict(), "comparisons": []}
    periods = {"2021-2026": x["season"] >= 2021, "2022-2026": x["season"] >= 2022, "2021-2024": x["season"] <= 2024,
               "2022-2024": x["season"].between(2022, 2024), "2025-2026": x["season"] >= 2025}
    tours = {"both": np.ones(len(x), bool), "men": (x["tour"] == "atp").to_numpy(),
             "women": (x["tour"] == "wta").to_numpy()}
    pairs = [("raw_plugin", "raw_open_trained", "raw"), ("cal_plugin", "cal_open_trained", "calibrated"),
             ("p_bol_open", "cal_plugin", "calibrated"), ("p_bol_open", "cal_open_trained", "calibrated"),
             ("p_bol_close", "cal_close_fed", "calibrated"), ("cal_open_trained", "q_bol_open", "calibrated"),
             ("p_bol_open", "q_bol_open", "calibrated"), ("cal_close_fed", "q_bol_close", "calibrated")]
    for pname, pm in periods.items():
        for tname, tm in tours.items():
            g = x[pm.to_numpy() & tm]
            for base, arm, kind in pairs:
                ok = np.isfinite(g[base].to_numpy(float)) & np.isfinite(g[arm].to_numpy(float))
                if ok.sum() < 300:
                    continue
                res["comparisons"].append({"period": pname, "tour": tname, "base": base, "arm": arm, "kind": kind,
                                           **compare(g[ok], base, arm)})
    sizing = {}
    g = x[(x["season"] >= 2022).to_numpy()]
    lp = C.lg(np.clip(g["p_bol_open"], *SS.P_CLIP))
    for col in ("cal_plugin", "cal_open_trained", "q_bol_open"):
        ok = np.isfinite(g[col].to_numpy(float))
        D = C.lg(g[col].to_numpy(float)[ok]) - lp[ok]
        r = SS.logit_cluster(np.column_stack([lp[ok], D]), g["y"].to_numpy(float)[ok], g["block"].to_numpy()[ok])
        sizing[col] = {"price_slope": r["beta"][0], "realisation": r["beta"][1], "lo": r["lo"][1], "hi": r["hi"][1],
                       "n": r["n"], "disagreement_sd_logit": float(np.std(D))}
    res["sizing_2022_2026"] = sizing
    C.write_json(C.OUT / "results_lines.json", res)
    t = pd.DataFrame(res["comparisons"])
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(t[["period", "tour", "base", "arm", "n", "est", "lo", "hi"]].round(3).to_string(index=False))
    print(sizing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
