"""Does the model that beat the close beat the sharp closes? (men, read-only, no refit)

The one TabPFN-3.5-Thinking fit on closing odds + 53 inputs (original, pre-repair features; 2022-2026 test)
scored against:
  the bookmakers' average close: proportional and power margin removal, and the study's recalibration
  Pinnacle's close (to 13 Jan 2026), Betfair Exchange's close (tennis-data BFEW/BFEL, late 2025-2026),
  Polymarket's price 30 minutes and 0 minutes before the listed start (the sharp-benchmark study's table).
Each comparison is on the matches both forecasts cover. Log loss uses the probability each forecast gave
the actual winner, so no side orientation is needed. Joined to the sharp-benchmark rows by tour, date,
winner and loser in tennis-data's naming.
Run: ./python.sh src/eda/market_anchoring/sharp_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.market_anchoring import common as C

THINKING = C.ROOT / "data/studies/tabpfn_thinking/test_predictions.parquet"
SHARP = C.ROOT / "data/studies/sharp_benchmark/matches.parquet"


def power_devig(odds_w: np.ndarray, odds_l: np.ndarray) -> np.ndarray:
    """Winner probability with the power method: (1/oW)^k + (1/oL)^k = 1."""
    a, b = 1 / np.asarray(odds_w, float), 1 / np.asarray(odds_l, float)
    lo, hi = np.full(len(a), 0.2), np.full(len(a), 5.0)
    for _ in range(80):
        k = (lo + hi) / 2
        over = a**k + b**k > 1
        lo, hi = np.where(over, k, lo), np.where(over, hi, k)
    return a ** ((lo + hi) / 2)


def proportional(odds_w, odds_l):
    a, b = 1 / np.asarray(odds_w, float), 1 / np.asarray(odds_l, float)
    return a / (a + b)


def main():
    t = pd.read_parquet(THINKING)
    t = t[t.tour.eq("atp")].copy()
    won = t.a_won.astype(bool).to_numpy()
    t["w_tabpfn"] = np.where(won, t.p_tabpfn, 1 - t.p_tabpfn)
    t["w_avg_recal"] = np.where(won, t.p_market, 1 - t.p_market)
    t["w_avg_study_raw"] = np.where(won, t.p_market_raw, 1 - t.p_market_raw)
    odds = pd.read_parquet(C.ODDS, columns=["match_id", "td_date", "td_winner", "td_loser", "avg_a", "avg_b",
                                            "ps_a", "ps_b"])
    t = t.merge(odds, on="match_id", how="left", validate="one_to_one")
    ow = np.where(won, t.avg_a, t.avg_b)
    ol = np.where(won, t.avg_b, t.avg_a)
    t["w_avg_prop"], t["w_avg_power"] = proportional(ow, ol), power_devig(ow, ol)
    pw = np.where(won, t.ps_a, t.ps_b)
    pl = np.where(won, t.ps_b, t.ps_a)
    t["w_ps_prop"], t["w_ps_power"] = proportional(pw, pl), power_devig(pw, pl)
    s = pd.read_parquet(SHARP)
    s = s[s.tour.eq("atp")]
    key = ["td_date", "td_winner", "td_loser"]
    s = s.rename(columns={"date": "td_date", "winner": "td_winner", "loser": "td_loser"})
    s = s.drop_duplicates(key, keep=False)
    t = t.merge(s[key + ["BFEW", "BFEL", "pw_pm_m30", "pw_pm_m0"]], on=key, how="left", validate="many_to_one")
    t["w_bf_power"] = power_devig(t.BFEW, t.BFEL)
    t["w_pm_m30"], t["w_pm_m0"] = t.pw_pm_m30, t.pw_pm_m0
    t["a_won"] = 1.0                       # every column is the probability given to the actual winner
    t["block4week"] = ((pd.to_datetime(t.tournament_date) - pd.Timestamp("2010-01-04")).dt.days // 28).astype(int)
    rows = []
    for name in ("w_avg_study_raw", "w_avg_prop", "w_avg_power", "w_avg_recal", "w_ps_prop", "w_ps_power",
                 "w_bf_power", "w_pm_m30", "w_pm_m0"):
        ref = t[name].to_numpy(dtype=float)
        ok = np.isfinite(ref) & (ref > 0) & (ref < 1)
        for window, mask in (("2022_2026", np.ones(len(t), bool)), ("2022_2025", t.year.le(2025).to_numpy()),
                             ("2026", t.year.eq(2026).to_numpy())):
            g = C.gain(t, t.w_tabpfn.to_numpy(), np.where(ok, ref, np.nan), mask & ok)
            if g["gain_mll"] is not None:
                rows.append({"versus": name, "window": window, **g})
    out = pd.DataFrame(rows)
    out.to_csv(C.OUT / "sharp_check.csv", index=False)
    cover = {"men_test_matches": len(t), "with_pinnacle": int(np.isfinite(t.w_ps_power).sum()),
             "with_betfair": int(np.isfinite(t.w_bf_power).sum()), "with_polymarket_m30": int(t.w_pm_m30.notna().sum()),
             "test_2026": int(t.year.eq(2026).sum()), "last_test_day": str(pd.to_datetime(t.tournament_date).max().date())}
    C.write_json(C.OUT / "sharp_check_summary.json", cover)
    print(cover)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string())


if __name__ == "__main__":
    main()
