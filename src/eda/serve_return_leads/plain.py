"""Plain-language tables for the owner (serve/return-leads study): the edge-anatomy explanation's large-gap view, for
the locked traits and the cleaner versions, on seen matches only.

For each oriented statistic (+ = expected to beat the close), every men's match is turned round so that "the focal
player" is the one higher on it (matches where it is 0 or missing are left out). In the matches where the gap is larger
than one RMS of the statistic in the window ("clear gap"), and in all matches:
    the close's margin-free probability for the focal player (the frame's odds input), raw and recalibrated (the
    test's base, s.L + k.L|L|, fitted on the window's men's matches without the statistic: it removes the price
    curve's favourite-longshot tilt, which the raw close carries),
    how often he won,
    the surprise (won minus the recalibrated close), in percentage points, with a 95% interval over four-week blocks.
Windows: 2013-24 and 1 Jan 2025 - 28 Jul 2026 (by season, as everywhere in the study).

Writes data/studies/serve_return_leads/plain.csv.
Run: ./python.sh src/eda/serve_return_leads/plain.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import stats as S  # noqa: E402
from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.serve_return_leads import decompose as D  # noqa: E402
from src.eda.serve_return_leads import readings as R  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

WHAT = {"T1": "Serving strength (long memory)", "T2": "Break points saved, last two weeks",
        "T3": "Returning strength (long memory)", "R0": "The four traits' combined serve/return score",
        "ST": "Serve-heavy rather than return-heavy, at the point level", "PS03_save": "Break points saved beyond what "
        "his serve points imply (last 3 months)", "PS03_hold": "Holds beyond what his serve points imply (last 3 months)",
        "TOT": "Point-level strength, serve plus return (a control)"}


def main() -> int:
    f = R.seen_frame("atp")
    sc = C.scales(f)
    s = C.scores(f, sc)
    c, sign = D.candidates(f)
    vals = {k: s[k] for k in ("R0", "T1", "T2", "T3")}
    for k in ("ST", "PS03_save", "PS03_hold", "TOT"):
        vals[k] = np.nan_to_num(c[k]) * sign[k]
    p_close = f["p_mkt"].to_numpy(float)
    y = f["y"].to_numpy(float)
    blk = f["block"].to_numpy()
    L = f["L"].to_numpy(float)
    rows = []
    for w, (a, b) in {"2013-24": (2013, 2024), "2025-26": (2025, 2026)}.items():
        m = f["season"].between(a, b).to_numpy() & np.isfinite(L)
        Bm = np.column_stack([L[m], L[m] * np.abs(L[m])])
        coef, _ = H.fit_offset(Bm, y[m], np.zeros(int(m.sum())), ridge=1e-6)
        p_cal = np.full(len(f), np.nan)
        p_cal[m] = expit(Bm @ coef)
        for k, x in vals.items():
            x = np.asarray(x, float)
            ok = m & np.isfinite(x) & (x != 0)
            xs = x[ok]
            rms = float(np.sqrt(np.mean(xs ** 2)))
            flip = xs < 0
            pm = np.where(flip, 1 - p_close[ok], p_close[ok])
            pc = np.where(flip, 1 - p_cal[ok], p_cal[ok])
            won = np.where(flip, 1 - y[ok], y[ok])
            for gname, k_ in (("clear gap", np.abs(xs) / rms > 1.0), ("all", np.ones(len(xs), bool))):
                d = S.mean_ci(won[k_] - pc[k_], blk[ok][k_], scale=100.0)
                rows.append({"window": w, "statistic": k, "what": WHAT[k], "gap": gname, "matches": int(k_.sum()),
                             "share": float(k_.mean()), "close_pct": 100 * float(pm[k_].mean()),
                             "recal_pct": 100 * float(pc[k_].mean()), "won_pct": 100 * float(won[k_].mean()),
                             "surprise_pp": d["est"], "lo": d["lo"], "hi": d["hi"], "p_positive": d["p_better"]})
    out = pd.DataFrame(rows)
    out.to_csv(C.OUT / "plain.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.drop(columns=["what"]).round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
