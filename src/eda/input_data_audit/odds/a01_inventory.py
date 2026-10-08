"""Task 2: the odds definition per tour x season in the staged tennis-data rows (current staging, 5 Oct download).

Outputs (out/):
    a01_books_by_season.csv     book prefixes present in the header and their non-missing share, per tour x season
    a01_avg_checks.csv          per tour x season: Avg vs Max, Avg vs the listed books, Avg == Max, overround quantiles
    a01_overround_series.csv    median Avg overround and winner-probability per tour x season x series
    a01_month_2024_on.csv       per tour x month from 2024: books present, Avg overround, PS coverage
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from _common import OUTD, book_cols, load_staged, num

td = load_staged()
print("staged rows 2010-2026:", len(td))

# 1. book columns present per tour x season
rows = []
for (t, y), g in td.groupby(["_tour", "_season"]):
    cols = [c for c in g.columns if not g[c].isna().all()]
    books = book_cols(cols)
    rec = {"tour": t, "season": y, "rows": len(g), "books_with_data": " ".join(books)}
    for b in ["B365", "EX", "LB", "PS", "CB", "GB", "IW", "SB", "SJ", "UB", "B&W", "Max", "Avg"]:
        if f"{b}W" in g.columns:
            rec[f"{b}_share"] = round(float((num(g[f"{b}W"]).notna() & num(g[f"{b}L"]).notna()).mean()), 4)
        else:
            rec[f"{b}_share"] = np.nan
    rows.append(rec)
books = pd.DataFrame(rows)
books.to_csv(OUTD / "a01_books_by_season.csv", index=False)
print(books.to_string())

# 2. Avg checks per tour x season
indiv = ["B365", "EX", "LB", "PS", "CB", "GB", "IW", "SB", "SJ", "UB", "B&W"]
out = []
for (t, y), g in td.groupby(["_tour", "_season"]):
    aw, al = num(g.get("AvgW", pd.Series(index=g.index, dtype=object))), num(g.get("AvgL", pd.Series(index=g.index, dtype=object)))
    mw, ml = num(g.get("MaxW", pd.Series(index=g.index, dtype=object))), num(g.get("MaxL", pd.Series(index=g.index, dtype=object)))
    pw, pl = num(g.get("PSW", pd.Series(index=g.index, dtype=object))), num(g.get("PSL", pd.Series(index=g.index, dtype=object)))
    bw, bl = num(g.get("B365W", pd.Series(index=g.index, dtype=object))), num(g.get("B365L", pd.Series(index=g.index, dtype=object)))
    both = aw.notna() & al.notna()
    ovr = (1 / aw + 1 / al)[both]
    rec = {"tour": t, "season": y, "rows": len(g), "avg_pairs": int(both.sum()),
           "avg_missing": int((~both).sum())}
    hasmax = both & mw.notna() & ml.notna()
    rec["avg_gt_max_w"] = int((aw[hasmax] > mw[hasmax] + 1e-9).sum())
    rec["avg_gt_max_l"] = int((al[hasmax] > ml[hasmax] + 1e-9).sum())
    rec["avg_eq_max_both"] = int(((aw[hasmax] - mw[hasmax]).abs() < 1e-9).mul((al[hasmax] - ml[hasmax]).abs() < 1e-9).sum())
    rec["avg_eq_max_share"] = round(rec["avg_eq_max_both"] / max(1, int(hasmax.sum())), 4)
    # Avg vs the individual books on the row
    present = [b for b in indiv if f"{b}W" in g.columns]
    if present:
        W = pd.concat([num(g[f"{b}W"]) for b in present], axis=1)
        L = pd.concat([num(g[f"{b}L"]) for b in present], axis=1)
        nb = W.notna().sum(axis=1)
        ok = both & (nb >= 2)
        lo_w, hi_w = W.min(axis=1), W.max(axis=1)
        lo_l, hi_l = L.min(axis=1), L.max(axis=1)
        # Avg odds is an average over more books than the listed ones, so it may sit a little outside; count gross misses
        out_w = ok & ((aw < lo_w * 0.85) | (aw > hi_w * 1.15))
        out_l = ok & ((al < lo_l * 0.85) | (al > hi_l * 1.15))
        rec["avg_far_outside_listed_books"] = int((out_w | out_l).sum())
        meanw, meanl = W.mean(axis=1), L.mean(axis=1)
        rec["avg_eq_mean_listed_share"] = round(float((((aw - meanw).abs() < 0.0051) & ((al - meanl).abs() < 0.0051))[ok].mean()), 4) if ok.any() else np.nan
        for b in ["B365", "PS"]:
            if f"{b}W" in g.columns:
                e = ok & ((aw - num(g[f"{b}W"])).abs() < 1e-9) & ((al - num(g[f"{b}L"])).abs() < 1e-9)
                rec[f"avg_eq_{b}_share"] = round(float(e[ok].mean()), 4) if ok.any() else np.nan
    # de-vigged winner probability, Avg and PS
    p_avg_w = (1 / aw) / (1 / aw + 1 / al)
    p_ps_w = (1 / pw) / (1 / pw + 1 / pl)
    p_b_w = (1 / bw) / (1 / bw + 1 / bl)
    rec["mean_p_avg_winner"] = round(float(p_avg_w[both].mean()), 4)
    rec["fav_win_rate_avg"] = round(float((p_avg_w[both] > 0.5).mean()), 4)
    rec["mean_fav_p_avg"] = round(float(np.maximum(p_avg_w[both], 1 - p_avg_w[both]).mean()), 4)
    bp = both & pw.notna() & pl.notna()
    rec["ps_pairs"] = int(bp.sum())
    rec["mean_abs_p_avg_minus_ps"] = round(float((p_avg_w - p_ps_w)[bp].abs().mean()), 4) if bp.any() else np.nan
    rec["n_avg_ps_disagree_gt_0.25"] = int(((p_avg_w - p_ps_w).abs() > 0.25)[bp].sum())
    bb = both & bw.notna() & bl.notna()
    rec["n_avg_b365_disagree_gt_0.25"] = int(((p_avg_w - p_b_w).abs() > 0.25)[bb].sum())
    for q in (0.001, 0.01, 0.5, 0.99, 0.999):
        rec[f"ovr_avg_q{q}"] = round(float(ovr.quantile(q)), 4) if len(ovr) else np.nan
    rec["ovr_avg_lt1"] = int((ovr < 1).sum())
    rec["ovr_avg_gt1.2"] = int((ovr > 1.2).sum())
    if bp.any():
        rec["ovr_ps_med"] = round(float((1 / pw + 1 / pl)[bp].median()), 4)
    hasmax2 = mw.notna() & ml.notna()
    rec["ovr_max_med"] = round(float((1 / mw + 1 / ml)[hasmax2].median()), 4) if hasmax2.any() else np.nan
    if bb.any():
        rec["ovr_b365_med"] = round(float((1 / bw + 1 / bl)[bb].median()), 4)
    out.append(rec)
chk = pd.DataFrame(out)
chk.to_csv(OUTD / "a01_avg_checks.csv", index=False)
pd.set_option("display.width", 250)
print(chk.to_string())

# 3. overround by series
g = td.copy()
g["series"] = g["Series"].fillna(g.get("Tier"))
aw, al = num(g["AvgW"]), num(g["AvgL"])
g["ovr"] = 1 / aw + 1 / al
g["p_w"] = (1 / aw) / g["ovr"]
ser = (g[g["ovr"].notna()].groupby(["_tour", "_season", "series"])
       .agg(rows=("ovr", "size"), ovr_median=("ovr", "median"), ovr_p10=("ovr", lambda x: x.quantile(.1)),
            ovr_p90=("ovr", lambda x: x.quantile(.9)), mean_p_winner=("p_w", "mean")).reset_index())
ser.to_csv(OUTD / "a01_overround_series.csv", index=False)
print(ser.round(4).to_string())

# 4. month by month from 2024
g["date"] = pd.to_datetime(g["Date"], errors="coerce")
g["month"] = g["date"].dt.strftime("%Y-%m")
m = g[g["date"] >= "2024-01-01"]
mon = []
for (t, mo), h in m.groupby(["_tour", "month"]):
    rec = {"tour": t, "month": mo, "rows": len(h)}
    for b in ["B365", "PS", "Max", "Avg"]:
        rec[f"{b}_share"] = round(float((num(h[f"{b}W"]).notna() & num(h[f"{b}L"]).notna()).mean()), 3) if f"{b}W" in h else np.nan
    rec["ovr_avg_med"] = round(float(h["ovr"].median()), 4)
    rec["ovr_avg_p90"] = round(float(h["ovr"].quantile(.9)), 4)
    mw, ml = num(h["MaxW"]), num(h["MaxL"])
    rec["ovr_max_med"] = round(float((1 / mw + 1 / ml).median()), 4)
    rec["mean_p_winner_avg"] = round(float(h["p_w"].mean()), 4)
    mon.append(rec)
mon = pd.DataFrame(mon)
mon.to_csv(OUTD / "a01_month_2024_on.csv", index=False)
print(mon.to_string())
