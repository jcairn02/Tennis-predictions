"""EXPLORATORY, NOT PRE-REGISTERED (added 22 Oct 2026, 09:30, after the pre-registered scores were read): how much of
the betting reading is the model, and how much is the price itself?

On the same scored qualifying matches (2020-2026, debut seasons out) and with the same bet rule as score.py (1 unit
on the side whose EV at the odds exceeds the threshold), the ROI of forecasts that use no model:
    raw close         the closing price used as the model's odds input (Pinnacle's, else BetOnline's), margin removed:
                      at BetOnline's odds this is pure line-shopping (where BetOnline's price beats Pinnacle's
                      margin-free close); at the price's own book it never bets (the margin)
    calibrated close  that close with one slope per tour fitted walk-forward (compare.close_forecast): recalibration
                      (the closes underrate favourites on qualifying, market.json) plus line-shopping
and, for reference, the arms' stage-2 forecasts (score.py's betting.csv rows, recomputed here on the same rows).
Nothing here enters a verdict; it explains the betting reading.

Writes data/studies/qualifying_targets/exploratory_decomposition.json.
Run: ./python.sh src/eda/qualifying_targets/explore_decomposition.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.qualifying_targets import score as S  # noqa: E402


def main() -> int:
    info, _ = S.qual_info()
    f = pd.read_parquet(C.OUT / "forecasts.parquet").set_index("match_id")
    ids = f.index
    forecasts = {"raw close": f["p_close"].to_numpy(float), "calibrated close": f["q_close_cal"].to_numpy(float),
                 "M0 (stage 2)": f["q_M0_s2"].to_numpy(float), "M1 (stage 2)": f["q_M1_s2"].to_numpy(float),
                 "M2 (stage 2)": f["q_M2_s2"].to_numpy(float)}
    out = []
    for name, q in forecasts.items():
        for venue, (ca, cb) in (("pinnacle", ("pin_a", "pin_b")), ("betonline", ("bol_a", "bol_b"))):
            for min_ev in (0.0, 0.02):
                r = S.bets(info, ids, q, info.loc[ids, ca].to_numpy(float), info.loc[ids, cb].to_numpy(float), min_ev)
                out.append({"forecast": name, "venue": venue, "min_ev": min_ev, **r})
    t = pd.DataFrame(out)
    C.write_json(C.OUT / "exploratory_decomposition.json", {"note": "exploratory, not pre-registered",
                                                            "rows": t.to_dict("records")})
    t["roi_ci"] = t.apply(lambda r: f"{100 * r['roi']:+.1f}% [{100 * r['roi_lo']:+.1f}, {100 * r['roi_hi']:+.1f}]"
                          if pd.notna(r["roi"]) else "no bets", axis=1)
    print(t.pivot_table(index="forecast", columns=["venue", "min_ev"], values="roi_ci", aggfunc="first").to_string())
    print(t.pivot_table(index="forecast", columns=["venue", "min_ev"], values="bets", aggfunc="first").to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
