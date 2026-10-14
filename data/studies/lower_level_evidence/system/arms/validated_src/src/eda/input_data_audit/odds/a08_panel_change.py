"""Task 2: the OddsPortal panel behind Avg/Max, month by month, against a fixed single book (Bet365).

If the set of books behind the average changes, the Max overround (the best price on each side) and the distance
between the average and a fixed book move. Also the market's calibration on the frame's rows before and after.

Outputs (out/): a08_panel_by_month.csv, a08_panel_periods.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import OUTD, load_staged, logit, num

td = load_staged(range(2013, 2027))
td["date"] = pd.to_datetime(td["Date"], errors="coerce")
aw, al, mw, ml, bw, bl = (num(td[c]) for c in ("AvgW", "AvgL", "MaxW", "MaxL", "B365W", "B365L"))
td["p_avg"] = (1 / aw) / (1 / aw + 1 / al)
td["p_max"] = (1 / mw) / (1 / mw + 1 / ml)
td["p_b365"] = (1 / bw) / (1 / bw + 1 / bl)
td["ovr_avg"] = 1 / aw + 1 / al
td["ovr_max"] = 1 / mw + 1 / ml
td["ovr_b365"] = 1 / bw + 1 / bl
td["d_avg_b365"] = (td["p_avg"] - td["p_b365"]).abs()
td["d_max_b365"] = (td["p_max"] - td["p_b365"]).abs()
td["month"] = td["date"].dt.strftime("%Y-%m")
ok = td["p_avg"].notna() & td["p_b365"].notna()
mon = (td[ok].groupby(["_tour", "month"]).agg(rows=("p_avg", "size"), ovr_avg_med=("ovr_avg", "median"),
                                              ovr_max_med=("ovr_max", "median"), ovr_b365_med=("ovr_b365", "median"),
                                              mean_abs_avg_minus_b365=("d_avg_b365", "mean"),
                                              mean_abs_max_minus_b365=("d_max_b365", "mean")).reset_index())
mon.to_csv(OUTD / "a08_panel_by_month.csv", index=False)
pd.set_option("display.width", 200)
print(mon[mon["month"] >= "2024-06"].round(4).to_string())

# periods
per = {"2013-2018": ("2013-01-01", "2019-01-01"), "2019-2024": ("2019-01-01", "2025-01-01"),
       "2025-01..07": ("2025-01-01", "2025-08-01"), "2025-08..2026-09": ("2025-08-01", "2026-10-01")}
out = {}
for k, (a, b) in per.items():
    g = td[ok & (td["date"] >= a) & (td["date"] < b)]
    out[k] = {"rows": int(len(g)), "ovr_avg_median": round(float(g["ovr_avg"].median()), 4),
              "ovr_max_median": round(float(g["ovr_max"].median()), 4),
              "ovr_b365_median": round(float(g["ovr_b365"].median()), 4),
              "mean_abs_avg_minus_b365": round(float(g["d_avg_b365"].mean()), 4),
              "share_avg_within_0.01_of_b365": round(float((g["d_avg_b365"] < .01).mean()), 4)}
# calibration of the frame's p_mkt in the two recent periods (frame rows only)
D = pd.read_parquet(OUTD / "a03_joined.parquet")
D["date"] = pd.to_datetime(D["td_date"])


def fit(z, y):
    X = np.column_stack([np.ones_like(z), z])
    w = np.zeros(2)
    for _ in range(50):
        mu = 1 / (1 + np.exp(-(X @ w)))
        w += np.linalg.solve((X * (mu * (1 - mu))[:, None]).T @ X, X.T @ (y - mu))
    return w


for k, (a, b) in (("frame 2024-08..2025-07", ("2024-08-01", "2025-08-01")), ("frame 2025-08..2026-08", ("2025-08-01", "2026-09-01")),
                  ("frame train 2013-2021", ("2013-01-01", "2022-01-01")), ("frame test 2022-2025-07", ("2022-01-01", "2025-08-01"))):
    g = D[(D["date"] >= a) & (D["date"] < b)]
    p, y = g["p_mkt"].to_numpy(), g["a_won"].astype(float).to_numpy()
    w = fit(logit(p), y)
    out[k] = {"n": int(len(g)), "logloss": round(float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()), 4),
              "cal_intercept": round(float(w[0]), 4), "cal_slope": round(float(w[1]), 4),
              "mean_overround": round(float((1 / g["avg_a"] + 1 / g["avg_b"]).mean()), 4)}
(OUTD / "a08_panel_periods.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
