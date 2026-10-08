"""Audit scratch: re-derive the strategy's headline evidence (strategy.md sections 3-4) with independent code
(sklearn / own cluster interval; nothing imported from evidence.py), and run the extra cuts the audit needs:

  * Elo-only gains 2019-2021 (main tour and all evaluation levels) for overall, Stage 1 blend, re-anchored blend, offset
  * with-odds forward-chained logistic gains (2016-2021) and the same split into 2016-2018 / 2019-2021 (the offset's K
    and every Stage 1 constant were tuned on 2013-2018, so 2016-2018 is in-sample for the constants)
  * no-odds forward-chained gains, same split
  * the 'priced' table on ONE population (rows with odds) and against the RECALIBRATED market, and residuals against
    the offset Elo by career count (does the offset leave an inexperience penalty, principle 3?)
  * what the offset is: mean D by surface for experienced players (is it surface-specific or a general correction?)

Run: ./python.sh data/studies/surface_elo_pieces/audit_scratch/rederive_evidence.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent
L10 = np.log(10) / 400
ORIGIN = np.datetime64("2010-01-04")


def ll(p, y):
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    y = np.asarray(y, bool)
    return np.where(y, -np.log(p), -np.log(1 - p))


def gain_ci(ll_base, ll_model, dates, width=28):
    d = np.asarray(ll_base) - np.asarray(ll_model)
    ok = np.isfinite(d)
    d, dates = d[ok], np.asarray(dates)[ok]
    blk = ((np.asarray(dates, dtype="datetime64[D]") - ORIGIN).astype(int)) // width
    u, inv = np.unique(blk, return_inverse=True)
    G, n = len(u), len(d)
    s = np.bincount(inv, weights=d - d.mean())
    se = np.sqrt(G / (G - 1) * (s @ s)) / n
    r = student_t.ppf(0.975, G - 1) * se
    return {"n": int(n), "gain": round(1000 * d.mean(), 3), "lo": round(1000 * (d.mean() - r), 3),
            "hi": round(1000 * (d.mean() + r), 3), "blocks": int(G), "se_mll": round(1000 * se, 4)}


def slope(x, y):
    lr = LogisticRegression(penalty=None, fit_intercept=False, max_iter=1000, tol=1e-10)
    lr.fit(np.asarray(x, float).reshape(len(x), -1), np.asarray(y, int))
    return lr.coef_[0]


p = pd.read_parquet(ROOT / "data/studies/surface_elo_pieces/pieces.parquet")
m = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                    columns=["match_id", "level", "evaluation", "status", "surface", "tournament_date", "a_won"])
p = p.merge(m, on="match_id", how="left", validate="one_to_one")
fr = pd.read_parquet(ROOT / "data/studies/tabpfn_thinking/frame.parquet",
                     columns=["match_id", "split", "tabpfn_split", "odds_logit", "elo_logit", "surface_first"])
p = p.merge(fr, on="match_id", how="left", validate="one_to_one")
p["main"] = p["split"].isin(["train", "test"])
p["eval_ok"] = p["evaluation"] & p["status"].isin(["completed", "retired"]) & p["surface"].notna()
y_all = p["a_won"].to_numpy(bool)
res = {}

# ---------------------------------------------------------------- bias (men, main tour, 2013-2021)
d = p[p["main"] & p["year"].between(2013, 2021)]
bins = [-1, 0, 2, 5, 10, 20, 40, 80, 160, 1e9]
for tour in ("atp", "wta"):
    q = d[d["tour"] == tour]
    rows = pd.DataFrame({"n": np.r_[q["NS_a"], q["NS_b"]], "s1": np.r_[q["S_a"] - q["R_a"], q["S_b"] - q["R_b"]],
                         "an": np.r_[q["XA_a"] - q["R_a"], q["XA_b"] - q["R_b"]], "off": np.r_[q["D_a"], q["D_b"]],
                         "surface": np.r_[q["surface"], q["surface"]]})
    rows["bin"] = pd.cut(rows["n"], bins)
    res[f"bias_{tour}"] = rows.groupby("bin", observed=True)[["s1", "an", "off"]].mean().round(1).astype(float).reset_index().astype(str).to_dict("records")
    hi = rows[rows["n"] > 160]
    res[f"offset_mean_by_surface_160plus_{tour}"] = hi.groupby("surface")["off"].agg(["mean", "std", "size"]).round(1).to_dict("index")

# ---------------------------------------------------------------- Elo-only, 2019-2021
fc = {}
for tour in ("atp", "wta"):
    t = (p["tour"] == tour).to_numpy()
    w = 0.30 if tour == "atp" else 0.25
    q = p
    sa = q["S_a"].fillna(q["R_a"]); sb = q["S_b"].fillna(q["R_b"])
    xa = q["XA_a"].fillna(q["R_a"]); xb = q["XA_b"].fillna(q["R_b"])
    variants = {"overall": L10 * (q["R_a"] - q["R_b"]),
                "stage1_blend": L10 * (q["R_a"] + w * (sa - q["R_a"]) - q["R_b"] - w * (sb - q["R_b"])),
                "anchored_blend": L10 * (q["R_a"] + w * (xa - q["R_a"]) - q["R_b"] - w * (xb - q["R_b"])),
                "offset": L10 * (q["R_a"] + q["D_a"].fillna(0) - q["R_b"] - q["D_b"].fillna(0))}
    tune = t & p["eval_ok"].to_numpy() & p["year"].between(2013, 2018).to_numpy()
    chk = t & p["eval_ok"].to_numpy() & p["year"].between(2019, 2021).to_numpy()
    cal = {k: slope(v.to_numpy()[tune], y_all[tune])[0] for k, v in variants.items()}
    base = ll(expit(cal["stage1_blend"] * variants["stage1_blend"].to_numpy()), y_all)
    for sub, sm in (("all evaluation", chk), ("main tour", chk & p["main"].to_numpy())):
        for k, v in variants.items():
            if k == "stage1_blend":
                continue
            lv = ll(expit(cal[k] * v.to_numpy()), y_all)
            res[f"elo_only|{tour}|{sub}|{k}"] = {**gain_ci(base[sm], lv[sm], p.loc[sm, "tournament_date"].to_numpy()),
                                                  "slope": round(cal[k], 4)}

# ---------------------------------------------------------------- with odds, forward-chained
dd = p[p["tabpfn_split"].isin(["train", "test"]) & p["year"].between(2013, 2021)].copy()
o = dd["odds_logit"].to_numpy()
cap = 1095.0
lsa, lsb = np.log1p(dd["season_n_a"].to_numpy()), np.log1p(dd["season_n_b"].to_numpy())
dsa = np.log1p(np.minimum(dd["days_since_a"].fillna(cap).to_numpy(), cap))
dsb = np.log1p(np.minimum(dd["days_since_b"].fillna(cap).to_numpy(), cap))
nsa, nsb = np.log1p(dd["NS_a"].fillna(0).to_numpy()), np.log1p(dd["NS_b"].fillna(0).to_numpy())
d_over = L10 * (dd["R_a"] - dd["R_b"]).to_numpy()
d_surf = L10 * (dd["S_a"].fillna(dd["R_a"]) - dd["S_b"].fillna(dd["R_b"])).to_numpy()
d_off = L10 * (dd["D_a"].fillna(0) - dd["D_b"].fillna(0)).to_numpy()
prev = (dd["prev_res_a"].fillna(0) / (dd["prev_n_a"].fillna(0) + 5) - dd["prev_res_b"].fillna(0) / (dd["prev_n_b"].fillna(0) + 5)).to_numpy()
specs = {"odds": [o], "odds+elo_blend": [o, dd["elo_logit"].to_numpy()],
         "odds+pieces_literal": [o, d_over, d_surf, nsa - nsb, d_surf * np.minimum(nsa, nsb)],
         "odds+pieces_offset": [o, d_over, d_off],
         "odds+switch diffs": [o, lsa - lsb, dsa - dsb, prev],
         "odds+offset_diff_only": [o, d_off],
         "odds+season_counts_diff": [o, lsa - lsb]}
X = {k: np.column_stack(v) for k, v in specs.items()}
yy = dd["a_won"].to_numpy(int)
yrs = dd["year"].to_numpy()
pred = {k: np.full(len(dd), np.nan) for k in specs}
for tour in ("atp", "wta"):
    for season in range(2016, 2022):
        tr = (dd["tour"] == tour).to_numpy() & (yrs < season)
        te = (dd["tour"] == tour).to_numpy() & (yrs == season)
        if not te.any():
            continue
        for k in specs:
            b = slope(X[k][tr], yy[tr])
            pred[k][te] = expit(X[k][te] @ b)
for tour in ("atp", "wta", "both"):
    tm = np.ones(len(dd), bool) if tour == "both" else (dd["tour"] == tour).to_numpy()
    for per, pm in (("2016-2021", yrs >= 2016), ("2016-2018", (yrs >= 2016) & (yrs <= 2018)), ("2019-2021", yrs >= 2019)):
        s = tm & pm & np.isfinite(pred["odds"])
        base = ll(pred["odds"][s], yy[s])
        for k in specs:
            if k == "odds":
                continue
            res[f"with_odds|{tour}|{per}|{k}"] = gain_ci(base, ll(pred[k][s], yy[s]), dd.loc[s, "tournament_date"].to_numpy())

# ---------------------------------------------------------------- no odds, forward-chained, main tour
dn = p[p["main"] & p["year"].between(2013, 2021) & p["surface"].notna()].copy()
f = {"blend": dn["elo_logit"].to_numpy(), "overall": L10 * (dn["R_a"] - dn["R_b"]).to_numpy(),
     "offset": L10 * (dn["R_a"] + dn["D_a"].fillna(0) - dn["R_b"] - dn["D_b"].fillna(0)).to_numpy(),
     "surface1500": L10 * (dn["S_a"].fillna(dn["R_a"]) - dn["S_b"].fillna(dn["R_b"])).to_numpy(),
     "ns_diff": (np.log1p(dn["NS_a"].fillna(0)) - np.log1p(dn["NS_b"].fillna(0))).to_numpy(),
     "season_diff": (np.log1p(dn["season_n_a"]) - np.log1p(dn["season_n_b"])).to_numpy(),
     "layoff_diff": (np.log1p(np.minimum(dn["days_since_a"].fillna(cap), cap)) - np.log1p(np.minimum(dn["days_since_b"].fillna(cap), cap))).to_numpy(),
     "prev_form": (dn["prev_res_a"].fillna(0) / (dn["prev_n_a"].fillna(0) + 5) - dn["prev_res_b"].fillna(0) / (dn["prev_n_b"].fillna(0) + 5)).to_numpy(),
     "surface_first": dn["surface_first"].fillna(0).to_numpy()}
nspecs = {"blend": ["blend"], "offset": ["offset"], "overall+surface1500": ["overall", "surface1500"],
          "overall+surface1500+career": ["overall", "surface1500", "ns_diff"], "offset+career": ["offset", "ns_diff"],
          "offset+season": ["offset", "season_diff"], "offset+layoff": ["offset", "layoff_diff"],
          "offset+form": ["offset", "prev_form"], "offset+season+layoff": ["offset", "season_diff", "layoff_diff"],
          "offset+all4": ["offset", "ns_diff", "season_diff", "layoff_diff", "prev_form"],
          "blend+surface_first": ["blend", "surface_first"]}
yn = dn["a_won"].to_numpy(int)
yrn = dn["year"].to_numpy()
pn = {k: np.full(len(dn), np.nan) for k in nspecs}
for tour in ("atp", "wta"):
    for season in range(2016, 2022):
        tr = (dn["tour"] == tour).to_numpy() & (yrn < season)
        te = (dn["tour"] == tour).to_numpy() & (yrn == season)
        for k, cols in nspecs.items():
            Xk = np.column_stack([f[c] for c in cols])
            b = slope(Xk[tr], yn[tr])
            pn[k][te] = expit(Xk[te] @ b)
for tour in ("atp", "wta"):
    tm = (dn["tour"] == tour).to_numpy()
    for per, pm in (("2016-2021", yrn >= 2016), ("2016-2018", (yrn >= 2016) & (yrn <= 2018)), ("2019-2021", yrn >= 2019)):
        s = tm & pm & np.isfinite(pn["blend"])
        base = ll(pn["blend"][s], yn[s])
        for k in nspecs:
            if k == "blend":
                continue
            res[f"no_odds|{tour}|{per}|{k}"] = gain_ci(base, ll(pn[k][s], yn[s]), dn.loc[s, "tournament_date"].to_numpy())
    # nested comparisons inside the no-odds family: what each switch piece adds BEYOND the offset (paired, own interval)
    s = tm & (yrn >= 2016)
    for k in ("offset+career", "offset+season", "offset+layoff", "offset+form", "offset+all4", "offset+season+layoff"):
        res[f"no_odds_beyond_offset|{tour}|2016-2021|{k}"] = gain_ci(ll(pn["offset"][s], yn[s]), ll(pn[k][s], yn[s]),
                                                                     dn.loc[s, "tournament_date"].to_numpy())
    s = tm & (yrn >= 2019)
    for k in ("offset+career", "offset+season", "offset+layoff", "offset+form", "offset+all4"):
        res[f"no_odds_beyond_offset|{tour}|2019-2021|{k}"] = gain_ci(ll(pn["offset"][s], yn[s]), ll(pn[k][s], yn[s]),
                                                                     dn.loc[s, "tournament_date"].to_numpy())

# ---------------------------------------------------------------- priced: one population, recalibrated market, offset Elo
dp = p[p["main"] & p["year"].between(2013, 2021) & p["surface"].notna()].copy()
# per-tour market slope fitted on the same design rows with odds (in-sample, as a description)
p_mkt_raw = expit(dp["odds_logit"].to_numpy())
p_mkt_cal = np.full(len(dp), np.nan)
for tour in ("atp", "wta"):
    t = (dp["tour"] == tour).to_numpy() & np.isfinite(dp["odds_logit"].to_numpy())
    b = slope(dp.loc[t, "odds_logit"].to_numpy(), dp.loc[t, "a_won"].to_numpy(int))[0]
    p_mkt_cal[t] = expit(b * dp.loc[t, "odds_logit"].to_numpy())
    res[f"market_slope_design_{tour}"] = round(float(b), 4)
p_el = expit(L10 * (dp["R_a"] - dp["R_b"]).to_numpy())
p_off = expit(L10 * (dp["R_a"] + dp["D_a"].fillna(0) - dp["R_b"] - dp["D_b"].fillna(0)).to_numpy())
parts = []
for side in ("a", "b"):
    own = side == "a"
    flip = (lambda v: v) if own else (lambda v: 1 - v)
    parts.append(pd.DataFrame({"tour": dp["tour"].to_numpy(), "career": dp[f"NS_{side}"].to_numpy(),
                               "days": dp[f"days_since_{side}"].fillna(1e6).to_numpy(),
                               "won": flip(dp["a_won"].to_numpy(float)), "p_elo": flip(p_el), "p_off": flip(p_off),
                               "p_raw": flip(p_mkt_raw), "p_cal": flip(p_mkt_cal)}))
r = pd.concat(parts, ignore_index=True)
r["career_bin"] = pd.cut(r["career"], [-1, 5, 10, 20, 40, 80, 1e9]).astype(str)
r["layoff_bin"] = pd.cut(r["days"], [-1, 3, 10, 30, 90, 200, 400, 1e9]).astype(str)
r["has_odds"] = np.isfinite(r["p_raw"])
out = []
for by in ("career_bin", "layoff_bin"):
    for (tour, b), q in r.groupby(["tour", by]):
        k = q[q["has_odds"]]
        out.append({"tour": tour, "by": by, "bin": b, "rows_all": len(q), "elo_resid_all_rows": round(float((q["won"] - q["p_elo"]).mean()), 4),
                    "rows_with_odds": len(k), "elo_resid_odds_rows": round(float((k["won"] - k["p_elo"]).mean()), 4),
                    "offset_resid_odds_rows": round(float((k["won"] - k["p_off"]).mean()), 4),
                    "mkt_raw_resid": round(float((k["won"] - k["p_raw"]).mean()), 4),
                    "mkt_cal_resid": round(float((k["won"] - k["p_cal"]).mean()), 4),
                    "se_won_minus_mkt": round(float((k["won"] - k["p_cal"]).std(ddof=1) / np.sqrt(max(len(k), 2))), 4)})
res["priced"] = out
(OUT / "rederive_evidence.json").write_text(json.dumps(res, indent=1, default=str))
for k, v in res.items():
    if k != "priced":
        print(k, v)
print(pd.DataFrame(out).to_string(index=False))
