"""F1 step 4: share of 'inclusive' matches per 2015 WTA event (mixture fit of the per-match likelihoods of
f1_scope.py), with a 95% profile-likelihood interval. Writes f1_event_mixture.csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import binom

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 250)
P2 = 0.5205   # pooled second-serve-in won share, WTA 2014 + 2016 (f1_scope.py)
s15 = R.sack("wta", "wta_matches_2015.parquet")


def rowll(svpt, df, fi, sw):
    xi, xe = svpt - fi - df, svpt - fi
    li = np.where(sw <= xi, binom.logpmf(sw, np.maximum(xi, 0), P2), -np.inf)
    return li, binom.logpmf(sw, xe, P2)


s = s15[R.has_box(s15)].copy()
s = s[s[[f"{a}_{b}" for a in "wl" for b in ["svpt", "df", "first_in", "second_won"]]].notna().all(axis=1)]
liw, lew = rowll(s.w_svpt, s.w_df, s.w_first_in, s.w_second_won)
lil, lel = rowll(s.l_svpt, s.l_df, s.l_first_in, s.l_second_won)
s["li"], s["lx"] = liw + lil, lew + lel


def fit(d):
    li, lx = d["li"].to_numpy(), d["lx"].to_numpy()

    def nll(f):
        return -np.logaddexp(np.log(f) + li, np.log1p(-f) + lx).sum()
    r = minimize_scalar(nll, bounds=(1e-6, 1 - 1e-6), method="bounded")
    grid = np.linspace(1e-6, 1 - 1e-6, 2001)
    vals = np.array([nll(g) for g in grid])
    inside = grid[vals - r.fun <= 1.92]
    return pd.Series({"n": len(d), "f_incl_hat": round(r.x, 3), "f_incl_lo": round(inside.min(), 3),
                      "f_incl_hi": round(inside.max(), 3)})


s["ev"] = s["tdate"].dt.strftime("%m-%d") + " " + s["tourney_name"]
res = s.groupby("ev").apply(fit)
print(res.to_string())
win = s["tdate"].between("2015-02-23", "2015-08-24") & ~s["tourney_level"].isin(["G"]) & s["tourney_name"].ne("Doha")
extra = {"ALL 30 window events": s[win],
         "Acapulco R32": s[s["tourney_name"].eq("Acapulco") & s["round"].eq("R32")],
         "Doha R32+R16": s[s["tourney_name"].eq("Doha") & s["round"].isin(["R32", "R16"])],
         "Doha QF": s[s["tourney_name"].eq("Doha") & s["round"].eq("QF")],
         "Doha SF+F": s[s["tourney_name"].eq("Doha") & s["round"].isin(["SF", "F"])],
         "2015 non-window non-Slam": s[~win & s["tourney_level"].ne("G") & s["tourney_name"].ne("Doha")]}
for k, d in extra.items():
    print(k, fit(d).to_dict())
res.to_csv(R.OUT / "f1_event_mixture.csv")
