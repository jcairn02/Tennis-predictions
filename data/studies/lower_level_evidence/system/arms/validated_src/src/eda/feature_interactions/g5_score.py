"""M2, step 2: the G5 deployment and harm check of an eligible member (plan.md, "Fixed at M1", rules 4-6).

    harm     the arm's paired log-loss gain over the base (seeds 0-2 each), both tours pooled, 2020-2024, each forecast
             calibrated by the decided walk-forward slope per tour (every earlier out-of-sample season from 2019);
             harm if the point estimate is below -0.10 mLL -> the member is deployed as a nudge instead of columns
    capture  OLS slope without intercept of (eta_arm - eta_base) (raw log-odds, seed 0-2 means, 2016-2024) on the
             screen's fitted term b_hat x, b_hat from one pooled fit on 2014-2024 with the screen's specification
             (slopes per tour x season, the cubic, the row's controls) on the model base; >= 0.5 -> columns, else nudge

Reads 2014-2024 results (a G5 look, ledger). Writes data/studies/feature_interactions/g5/<family>_g5.json.
Run: ./python.sh src/eda/feature_interactions/g5_score.py --hid B-INJ --arm binj
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions import screen_batch as B  # noqa: E402
from src.eda.feature_interactions import tabpfn_tests as TT  # noqa: E402
from src.eda.feature_interactions.g5_build import spec_of  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402

HARM_LINE = -0.10
CAPTURE_LINE = 0.5


def screen_term(hid: str) -> pd.Series:
    """b_hat x of the frozen hypothesis on the screen's rows (2014-2024), b_hat from one pooled 2014-2024 fit on the
    model base with the screen's specification and the row's assembled controls."""
    spec = spec_of(hid)
    P = panel(max_season=2024).drop(columns=["a_won"])
    L = long_table()
    new = spec["prepare"](P, L) if spec.get("prepare") else {}
    r = B.evaluate(spec, P.assign(**new))
    F = S.load(with_model=True)
    pos = pd.Series(np.arange(len(P)), index=P["match_id"].astype(str)).reindex(F["match_id"]).to_numpy().astype(int)
    e = F["z_model"].to_numpy(float)
    x = np.asarray(r["x"], float)[pos]
    parts = [np.asarray(r["controls"], float).reshape(len(P), -1)[pos]] if r.get("controls") is not None else []
    if r.get("eta_mod_controls") is not None or r.get("m_set") or r.get("x_times_eta") or r.get("x_of_eta"):
        raise NotImplementedError("price-form members need the batch's per-base assembly")
    miss = ~np.isfinite(x)
    if miss.any() and not miss.all():
        parts.append(miss.astype(float)[:, None] * e[:, None])
    Cb = np.column_stack(parts) if parts else None
    h = S.Hypothesis(hid, x, Cb, [], spec["sign"])
    xs, Cs, prep = S.prepare(F, h, "model")
    rows = np.ones(len(F), bool)
    fit = S.coef_test(F, rows, xs, Cs, "model", prep)
    return pd.Series(fit["b"] * xs, index=F["match_id"].to_numpy()), fit


def main() -> int:
    warnings.simplefilter("ignore")
    hid = sys.argv[sys.argv.index("--hid") + 1]
    arm = sys.argv[sys.argv.index("--arm") + 1]
    seasons = range(2016, 2025)
    f = TT.frame(seasons)
    pb = f["match_id"].map(TT.forecasts("model", (0, 1, 2), seasons)).to_numpy(float)
    pa = f["match_id"].map(TT.forecasts(arm, (0, 1, 2), seasons)).to_numpy(float)
    # harm: calibrated paired gain, 2020-2024
    rows = f["season"].between(2020, 2024).to_numpy()
    harm = TT.paired_gain(f, TT.calibrated(f, pb), TT.calibrated(f, pa), rows)
    raw = TT.paired_gain(f, pb, pa)
    # capture
    term, fit = screen_term(hid)
    t = f["match_id"].map(term).to_numpy(float)
    dev = C.lg(pa) - C.lg(pb)
    slope = TT.capture(dev, t)
    deploy = "columns" if (harm["gain"] >= HARM_LINE and slope >= CAPTURE_LINE) else "nudge"
    out = {"hid": hid, "arm": arm, "seasons": [2016, 2024],
           "harm": {"gain_mll": harm["gain"], "lo": harm["lo"], "hi": harm["hi"], "matches": harm["n"],
                    "window": "2020-2024, calibrated walk-forward from 2019", "harm_line": HARM_LINE,
                    "harmful": bool(harm["gain"] < HARM_LINE)},
           "raw_gain_2016_2024": {"gain_mll": raw["gain"], "lo": raw["lo"], "hi": raw["hi"], "matches": raw["n"]},
           "capture": {"slope": slope, "line": CAPTURE_LINE, "b_hat": fit["b"], "z_pooled": fit["z"],
                       "sd_term": float(np.nanstd(t)), "sd_dev": float(np.nanstd(dev)),
                       "corr_dev_term": float(np.corrcoef(np.nan_to_num(dev), np.nan_to_num(t))[0, 1])},
           "deployment": deploy,
           "key": "gains in mLL, positive = the arm has the lower log loss (better); 95% four-week-block intervals"}
    C.write_json(C.OUT / "g5" / f"{arm}_g5.json", out)
    C.log(f"{hid}: harm {harm['gain']:+.3f} [{harm['lo']:+.3f}, {harm['hi']:+.3f}] (2020-2024, calibrated); raw "
          f"2016-2024 {raw['gain']:+.3f}; capture slope {slope:.3f} (b_hat {fit['b']:.4f}, pooled z {fit['z']:.2f}); "
          f"deployment: {deploy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
