"""Audit scratch (design seasons only; nothing from 2022-2026 is scored for the new inputs).

A. Career-count encodings beside the offset Elo, forward-chained logistic 2016-2021 (the evidence's harness, own code):
   the evidence's log1p(NS_a) - log1p(NS_b) against capped forms log1p(min(NS, cap)) and an indicator NS < 20.
B. Power proxy for the TabPFN test: a free flexible model (sklearn HistGradientBoosting, with the odds) trained like the
   pilot (season Y in 2019-2021 on 2013..Y-1, both orientations averaged) on the `base` and `primary` columns of
   frame.parquet. The paired SE of primary vs base on 2019-2021 is scaled to the confirmation's 23,819 matches to give
   an approximate minimum detectable effect. Also the paired SE of existing forecast pairs on 2022-2026 (no new inputs).

Run: ./python.sh data/studies/surface_elo_pieces/audit_scratch/career_caps_and_power.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm, t as student_t
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.surface_elo_pieces import arms as A  # noqa: E402

OUT = Path(__file__).resolve().parent
L10 = np.log(10) / 400
ORIGIN = np.datetime64("2010-01-04")


def ll(p, y):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return np.where(np.asarray(y, bool), -np.log(p), -np.log(1 - p))


def gain_ci(lb, lm, dates):
    d = np.asarray(lb) - np.asarray(lm)
    blk = ((np.asarray(dates, dtype="datetime64[D]") - ORIGIN).astype(int)) // 28
    u, inv = np.unique(blk, return_inverse=True)
    G, n = len(u), len(d)
    s = np.bincount(inv, weights=d - d.mean())
    se = np.sqrt(G / (G - 1) * (s @ s)) / n
    r = student_t.ppf(0.975, G - 1) * se
    return {"n": int(n), "gain": round(1000 * d.mean(), 3), "lo": round(1000 * (d.mean() - r), 3),
            "hi": round(1000 * (d.mean() + r), 3), "se_mll": round(1000 * se, 4), "blocks": int(G)}


def fit(X, y):
    lr = LogisticRegression(C=np.inf, fit_intercept=False, max_iter=2000, tol=1e-10)
    lr.fit(X, y)
    return lr.coef_[0]


res = {}
# ------------------------------------------------------------------ A. career encodings (no odds and with odds)
p = pd.read_parquet(ROOT / "data/studies/surface_elo_pieces/pieces.parquet")
m = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                    columns=["match_id", "surface", "tournament_date", "a_won"])
fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet",
                     columns=["match_id", "split", "tabpfn_split", "odds_logit", "elo_logit"])
p = p.merge(m, on="match_id").merge(fr, on="match_id", how="left")
for label, pop in (("no odds, main tour", p["split"].isin(["train", "test"])),
                   ("with odds", p["tabpfn_split"].isin(["train", "test"]))):
    d = p[pop & p["year"].between(2013, 2021) & p["surface"].notna()].copy()
    off = L10 * (d["R_a"] + d["D_a"].fillna(0) - d["R_b"] - d["D_b"].fillna(0)).to_numpy()
    base_cols = [d["odds_logit"].to_numpy()] if label == "with odds" else []
    na, nb = d["NS_a"].fillna(0).to_numpy(), d["NS_b"].fillna(0).to_numpy()
    enc = {"none": [], "log diff (evidence)": [np.log1p(na) - np.log1p(nb)]}
    for cap in (10, 20, 40):
        enc[f"log diff capped at {cap}"] = [np.log1p(np.minimum(na, cap)) - np.log1p(np.minimum(nb, cap))]
    enc["indicator <20 diff"] = [(na < 20).astype(float) - (nb < 20).astype(float)]
    y = d["a_won"].to_numpy(int)
    yr = d["year"].to_numpy()
    preds = {}
    for k, extra in enc.items():
        X = np.column_stack(base_cols + [off] + extra)
        pr = np.full(len(d), np.nan)
        for tour in ("atp", "wta"):
            for season in range(2016, 2022):
                tr = (d["tour"] == tour).to_numpy() & (yr < season)
                te = (d["tour"] == tour).to_numpy() & (yr == season)
                if te.any():
                    pr[te] = expit(X[te] @ fit(X[tr], y[tr]))
        preds[k] = pr
    for tour in ("atp", "wta"):
        s = (d["tour"] == tour).to_numpy() & (yr >= 2016) & np.isfinite(preds["none"])
        for k in enc:
            if k == "none":
                continue
            res[f"career|{label}|{tour}|{k} vs offset alone"] = gain_ci(ll(preds["none"][s], y[s]), ll(preds[k][s], y[s]),
                                                                         d.loc[s, "tournament_date"].to_numpy())

# ------------------------------------------------------------------ B. power proxy on the pilot's folds (design years)
f = pd.read_parquet(ROOT / "data/studies/surface_elo_pieces/frame.parquet")
yv = f["a_won"].to_numpy(int)
pp = {}
for arm in ("base", "primary"):
    cols = [f"x_{c}" for c in A.ARMS[arm]]
    out = np.full(len(f), np.nan)
    for season in (2019, 2020, 2021):
        tr = f["season"].between(2013, season - 1).to_numpy()
        te = (f["season"] == season).to_numpy()
        Xtr = f.loc[tr, cols].set_axis(A.ARMS[arm], axis=1)
        Xte = f.loc[te, cols].set_axis(A.ARMS[arm], axis=1)
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.04, max_leaf_nodes=15, min_samples_leaf=200,
                                             l2_regularization=1.0, early_stopping=False, random_state=0)
        clf.fit(Xtr.to_numpy(), yv[tr])
        p1 = clf.predict_proba(Xte.to_numpy())[:, 1]
        p2 = clf.predict_proba(A.flip(Xte).to_numpy())[:, 1]
        out[te] = 0.5 * (p1 + 1 - p2)
    pp[arm] = out
s = np.isfinite(pp["base"]) & np.isfinite(pp["primary"])
g = gain_ci(ll(pp["base"][s], yv[s]), ll(pp["primary"][s], yv[s]), f.loc[s, "tournament_date"].to_numpy())
lb, lp = logit(np.clip(pp["base"][s], 1e-9, 1 - 1e-9)), logit(np.clip(pp["primary"][s], 1e-9, 1 - 1e-9))
res["power_proxy_hgb_primary_vs_base_2019_2021"] = {**g, "rms_logit_diff": round(float(np.sqrt(np.mean((lp - lb) ** 2))), 4)}
n_conf = 23819
se_conf = g["se_mll"] * np.sqrt(g["n"] / n_conf)
res["power_proxy_projected_confirm"] = {"se_mll": round(se_conf, 4),
                                        "half_width_95": round(1.96 * se_conf, 3),
                                        "mde_80pct_power": round((1.96 + 0.8416) * se_conf, 3),
                                        "power_at_+0.3": round(float(1 - norm.cdf(1.96 - 0.3 / se_conf)), 3),
                                        "power_at_+0.5": round(float(1 - norm.cdf(1.96 - 0.5 / se_conf)), 3)}

# existing forecast pairs on 2022-2026 (none uses the new inputs): SE vs how far the forecasts disagree
tp = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/test_predictions.parquet")
lp_ = pd.read_parquet(ROOT / "data/studies/tabpfn_leakproof/test_predictions.parquet")[["match_id", "p_leakproof"]]
tp = tp.merge(lp_, on="match_id", how="inner")
tp = tp[np.isfinite(tp["p_market"]) & np.isfinite(tp["p_tabpfn"])]
pairs = [("p_market", "p_tabpfn"), ("p_tabpfn", "p_leakproof"), ("p_lr_mkt_everything", "p_lr_mkt_everything_profile"),
         ("p_gbm_mkt_additive", "p_gbm_mkt"), ("p_market", "p_lr_mkt_everything"), ("p_lr_mkt_all", "p_gbm_mkt")]
for a, b in pairs:
    q = tp[np.isfinite(tp[a]) & np.isfinite(tp[b])]
    yy = q["a_won"].to_numpy(int)
    g2 = gain_ci(ll(q[a], yy), ll(q[b], yy), q["tournament_date"].to_numpy())
    la, lb2 = logit(np.clip(q[a], 1e-9, 1 - 1e-9)), logit(np.clip(q[b], 1e-9, 1 - 1e-9))
    res[f"pair_2022_2026|{a} vs {b}"] = {"se_mll": g2["se_mll"], "n": g2["n"], "blocks": g2["blocks"],
                                         "rms_logit_diff": round(float(np.sqrt(np.mean((la - lb2) ** 2))), 4)}
(OUT / "career_caps_and_power.json").write_text(json.dumps(res, indent=1))
for k, v in res.items():
    print(k, v)
