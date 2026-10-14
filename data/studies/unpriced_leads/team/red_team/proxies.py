"""R2: proxies, outcome-free (no result column is loaded).

1. correlations of the five registered group scores and the 13 member scores (frozen recipe, registered values, not the
   store stand-ins group_corr.py used), on 2013-24 and on Look A's rows;
2. non-linear proxy: a gradient-boosted regressor predicting each group's score (and each member's) from the 48 inputs,
   the six context inputs and the price L, cross-validated by season (2013-24); linear R^2 on the same set beside it;
3. each raw member's R^2 on the 48 inputs (1 - (scale_orth / scale_raw)^2 from the registry) against principle 1's
   "about 0.5".
Writes proxies.json and member_corr_*.csv.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

import rt_common as R  # noqa: E402


def cv_r2(X: np.ndarray, y: np.ndarray, groups: np.ndarray, model) -> float:
    pred = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=4).split(X, y, groups):
        m = model()
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return float(1 - np.mean((y - pred) ** 2) / np.mean((y - y.mean()) ** 2))


def lin():
    from sklearn.linear_model import LinearRegression
    return LinearRegression()


def gbm():
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=50,
                                         l2_regularization=1.0, random_state=0)


def main() -> int:
    reg = R.registry()
    f = R.outcome_free_frame()
    td = pd.to_datetime(f["tournament_date"])
    disc = f["season"].between(2013, 2024).to_numpy()
    lookA = (f["season"].between(2025, 2026) & (td < pd.Timestamp("2026-07-29"))).to_numpy()
    mem, grp, omni, _ = R.scores(f, reg)
    out = {}
    G = pd.DataFrame(grp)
    M = pd.DataFrame(mem)
    for lab, m in (("disc", disc), ("lookA", lookA)):
        out[f"group_corr_{lab}"] = G[m].corr().round(4).to_dict()
        M[m].corr().to_csv(R.OUT / f"member_corr_{lab}.csv")
        c = M[m].corr().where(lambda d: (d.abs() > 0.15) & (d.abs() < 0.999))
        pairs = c.stack().dropna()
        out[f"member_pairs_abs_gt_0.15_{lab}"] = {f"{a} ~ {b}": round(float(v), 3) for (a, b), v in pairs.items()
                                                  if a < b}
    # 2. non-linear proxies on 2013-24 (a 40% subsample of rows for speed, fixed seed)
    names = R.diff_inputs()
    ctx = ["in_tour_code", "in_surface", "in_level", "in_indoor", "in_best_of", "in_round"]
    f["in_tour_code"] = (f["tour"] == "atp").astype(float)
    Xcols = [f"in_{n}" for n in names] + ctx + ["L"]
    X = np.nan_to_num(f.loc[disc, Xcols].to_numpy(float), nan=-999.0)
    Xin = np.nan_to_num(f.loc[disc, [f"in_{n}" for n in names]].to_numpy(float), nan=0.0)
    seasons = f.loc[disc, "season"].to_numpy()
    rng = np.random.default_rng(13)
    sub = rng.random(len(X)) < 0.4
    res = {}
    targets = {"omnibus": omni, **grp, **mem}
    for k, s in targets.items():
        y = s[disc]
        res[k] = {"gbm_inputs_context_price": cv_r2(X[sub], y[sub], seasons[sub], gbm),
                  "linear_inputs_context_price": cv_r2(X[sub], y[sub], seasons[sub], lin),
                  "linear_inputs_only": cv_r2(Xin[sub], y[sub], seasons[sub], lin)}
        print(k, {a: round(b, 3) for a, b in res[k].items()}, flush=True)
    out["proxy_r2_cv_by_season"] = res
    # 3. raw members' R^2 on the 48 inputs (registry scales)
    r2 = {}
    for g in reg["groups"]:
        for m in g["members"]:
            r2[m["name"]] = {t: round(1 - (m["scale_orth"][t] / m["scale_raw"][t]) ** 2, 3) for t in ("atp", "wta")}
    out["raw_member_r2_on_48_inputs"] = r2
    (R.OUT / "proxies.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "proxy_r2_cv_by_season"}, indent=1, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
