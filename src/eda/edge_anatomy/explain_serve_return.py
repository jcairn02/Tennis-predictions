"""A plain-language view of the men's serve/return and serve-speed leads (edge-anatomy study, follow-up of 13 Oct 2026:
the owner asked for an explanation of "men's serving and break-point-saving records are over-rated while strong
returners are under-rated, and men's serve-speed changes are missed").

For each statistic (an A - B difference in the model's frame; the speed column of stage 2), every men's match is turned
round so that "the focal player" is the one higher on the statistic. Matches where the two players are level on it
(a difference of 0, e.g. no speed data) or where it is missing are left out. Then, by the size of the gap (in units of
the statistic's root mean square in the window: under 0.5, 0.5 to 1, over 1):
    the market's average probability for the focal player (the recalibrated close, the study's benchmark),
    the model's average probability for him (both stages),
    how often he actually won,
    the surprise (won minus the market's probability), in percentage points, with a 95% interval over four-week blocks.
Windows: January 2025 - 28 July 2026 (no sealed result is read: analysis.parquet ends on 28 Jul 2026) and 2020-2024.
Debut seasons out. Descriptive: no fit.

Writes data/studies/edge_anatomy/explain_serve_return.csv.
Run: ./python.sh src/eda/edge_anatomy/explain_serve_return.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.edge_anatomy import stats as S  # noqa: E402

STATS = {
    "iosO_hold": "long-memory serving: service games held",
    "iosO_bp_saved": "long-memory serving: break points saved",
    "form_bp_saved": "two-week form: break points saved",
    "iosD_first_won": "long-memory returning: holding the server's first-serve points down",
    "iosD_hold": "long-memory returning: holding the server's holds down",
    "spd": "recent change in first-serve speed",
}
WINDOWS = {"2025-26": (2025, 2026), "2020-24": (2020, 2021, 2022, 2023, 2024)}
GAPS = ((0.0, 0.5, "small gap"), (0.5, 1.0, "medium gap"), (1.0, np.inf, "large gap"))


def run() -> pd.DataFrame:
    a = pd.read_parquet(E.OUT / "analysis.parquet")
    a = a[(a["tour"] == "atp") & ~a["debut"] & (a["season"] >= 2020)]
    rows = []
    for wname, window in WINDOWS.items():
        g0 = a[a["season"].isin(window)]
        for col, what in STATS.items():
            x = g0[col if col == "spd" else f"in_{col}"].to_numpy(float)
            ok = np.isfinite(x) & (x != 0)
            g = g0[ok]
            x = x[ok]
            rms = float(np.sqrt(np.mean(x ** 2)))
            flip = x < 0
            p_mkt = np.where(flip, 1 - g["q_close"], g["q_close"])
            p_mod = np.where(flip, 1 - g["q_full"], g["q_full"])
            won = np.where(flip, 1 - g["y"], g["y"])
            size = np.abs(x) / rms
            for lo, hi, gname in GAPS + ((0.0, np.inf, "all"),):
                k = (size >= lo) & (size < hi)
                if k.sum() < 100:
                    continue
                d = S.mean_ci(won[k] - p_mkt[k], g["block"].to_numpy()[k], scale=100.0)
                rows.append({"window": wname, "statistic": col, "what": what, "gap": gname, "matches": int(k.sum()),
                             "share_of_matches": float(k.mean()), "market_pct": 100 * float(p_mkt[k].mean()),
                             "model_pct": 100 * float(p_mod[k].mean()), "won_pct": 100 * float(won[k].mean()),
                             "surprise_pp": d["est"], "surprise_lo": d["lo"], "surprise_hi": d["hi"],
                             "p_positive": d["p_better"], "matches_with_a_value": int(ok.sum())})
    return pd.DataFrame(rows)


def main() -> int:
    out = run()
    out.to_csv(E.OUT / "explain_serve_return.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(out.drop(columns=["what"]).round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
