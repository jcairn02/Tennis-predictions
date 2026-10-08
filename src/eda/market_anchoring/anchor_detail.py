"""Two follow-ups to anchor.py (men's main tour, average closing anchor).

  1. Context-dependent anchor slope: interactions of the market's log-odds with early surface season,
     best of five, clay, grass and level, as nudges (the favourite-longshot correction by context).
  2. Which inputs carry the nudge: one unpenalized fit of market + profile + context on 2013-2025 with
     cluster-robust standard errors, coefficients per training-RMS unit. Descriptive only.
  3. Both tours: the anchored profile + context model on the audit's repaired frame, men and women.
Run after anchor.py: ./python.sh src/eda/market_anchoring/anchor_detail.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.market_anchoring import common as C
from src.eda.market_anchoring.meta_label import early_flags

WINDOWS = {"2019_2025": (2019, 2025), "2026": (2026, 2026), "2019_2026": (2019, 2026)}


def tours_check() -> pd.DataFrame:
    """The anchored profile + context model for both tours on the repaired frame."""
    from src.eda.feature_alpha_audit import repair_score as R
    f = R.load_frame()
    cols = C.PROFILE + [C.E.SR] + C.E.CONTEXT
    out = []
    for tour in ("atp", "wta"):
        g = f[f.tour.eq(tour) & f.year.ge(2013) & f.status.isin(["completed", "retired"])].copy()
        g = g[np.isfinite(g[cols].to_numpy(float)).all(axis=1)].reset_index(drop=True)
        g["a_won"] = g.a_won.astype(float)
        g["block4week"] = ((pd.to_datetime(g.tournament_date) - pd.Timestamp("2010-01-04")).dt.days // 28).astype(int)
        for anchor, col in (("average", "p_avg_a"), ("pinnacle", "p_ps_a")):
            cal = C.calibrated(g, col)
            p = C.walk(g, cols, col, False)
            for window, (lo, hi) in (("2019_2025", (2019, 2025)), ("2026", (2026, 2026))):
                if anchor == "pinnacle" and hi == 2026:
                    continue
                out.append({"tour": tour, "anchor": anchor, "window": window,
                            **C.gain(g, p, cal, g.year.between(lo, hi).to_numpy() & np.isfinite(cal))})
    return pd.DataFrame(out)


def main():
    frame = C.load_atp()
    frame["early"] = early_flags(frame).to_numpy().astype(float)
    m = frame.mkt_avg.to_numpy()
    terms = {"x_early": frame.early, "x_bo5": frame.scheduled_best_of.eq(5), "x_clay": frame.surface.eq("Clay"),
             "x_grass": frame.surface.eq("Grass"), "x_t1000": frame.level.eq("T1000"),
             "x_t500": frame.level.eq("T500")}
    for k, v in terms.items():
        frame[f"mkt{k}"] = m * np.asarray(v, dtype=float)
    slope_cols = [f"mkt{k}" for k in terms]
    cal = C.calibrated(frame, "p_avg_a")
    rows = []
    base = C.PROFILE + [C.E.SR] + C.E.CONTEXT
    nud = C.walk(frame, base, "p_avg_a", False)
    for name, cols, ref_name, ref in (("context slopes", slope_cols, "calibrated average", cal),
                                      ("early-season slope only", ["mktx_early"], "calibrated average", cal),
                                      ("profile+context + context slopes", base + slope_cols,
                                       "profile+context", nud)):
        p = C.walk(frame, cols, "p_avg_a", False)
        for window, (lo, hi) in WINDOWS.items():
            rows.append({"model": name, "versus": ref_name, "window": window,
                         **C.gain(frame, p, ref, frame.year.between(lo, hi).to_numpy() & np.isfinite(ref))})
    slopes = pd.DataFrame(rows)
    slopes.to_csv(C.OUT / "anchor_context_slopes.csv", index=False)
    # Descriptive full-history fit
    g = frame[frame.year.between(2013, 2025) & np.isfinite(frame[["mkt_avg"] + base]).all(axis=1)]
    x = g[base].to_numpy(dtype=float)
    scale = C.P.rms_scale(x)
    z = np.column_stack([g.mkt_avg.to_numpy(), x / scale])
    beta, se = C.cluster_logit(z, g.a_won.to_numpy(dtype=float), g.block4week.to_numpy())
    coef = pd.DataFrame({"input": ["market log-odds"] + base, "coef_per_rms": beta, "se": se, "z": beta / se})
    coef.to_csv(C.OUT / "anchor_nudge_coefficients.csv", index=False)
    tours = tours_check()
    tours.to_csv(C.OUT / "anchor_tours_check.csv", index=False)
    print(tours.round(3).to_string())
    pd.set_option("display.width", 200)
    print(slopes.round(3).to_string())
    print(f"{len(g):,} matches")
    print(coef.round(3).to_string())


if __name__ == "__main__":
    main()
