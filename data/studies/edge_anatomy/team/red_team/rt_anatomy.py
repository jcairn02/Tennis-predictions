"""Red team: re-derive README section 5.2 (the men's schedule and IOS 'worth' in 2025-26) with an independent surrogate,
then test how much of the attribution is the surrogate's arbitrary split between correlated families.

The surrogate (outcome-free): d1 = logit(stage 1, calibrated) - logit(recalibrated price), least squares without
intercept on the groups price shape (L, L|L|, L^3), context (L x indicators), ratings, schedule, form, IOS (RMS-scaled
A - B inputs, pairs as A - B, missing = 0). Worth of part f = mean(LL(expit(logit q - d_f)) - LL(q)), + = the part helps.

Checks added:
  * the sum of the worths against the total gain, and the correlation matrix of the parts (offsetting parts);
  * leave-family-out surrogates: refit the surrogate WITHOUT family f (the others absorb what they can), the worth of
    what is then lost = the family's unique part; and family-ALONE surrogates (d1 on that family + price shape only);
  * the same split by date: Pinnacle-fed (to 7 Sep 2025) and BetOnline-fed (from 8 Sep 2025), both tours.

Run: ./python.sh data/studies/edge_anatomy/team/red_team/rt_anatomy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_common as R  # noqa: E402

GROUPS = ("price shape", "context", "ratings", "schedule", "form", "ios")


def design(g: pd.DataFrame) -> dict[str, np.ndarray]:
    L = R.lg(g["q_close"].to_numpy())
    out = {"price shape": np.column_stack([L, L * np.abs(L), L ** 3])}
    ctx = []
    for c, ref in (("in_level", 4.0), ("in_surface", 0.0), ("in_best_of", 3.0), ("in_indoor", 0.0)):
        v = g[c].to_numpy()
        for lev in sorted(set(v[np.isfinite(v)])):
            if lev != ref and (v == lev).sum() >= 50:
                ctx.append(L * (v == lev))
    ctx.append(L * np.isin(g["in_round"].to_numpy(), (15.0, 16.0, 17.0, 10.0)))
    out["context"] = np.column_stack(ctx)
    for fam, members in R.FAM.items():
        out[fam] = np.column_stack([R.rms_scaled(g[f"in_{c}"].to_numpy(float))[0] for c in members])
    return out


def ols(X, d):
    b, *_ = np.linalg.lstsq(X, d, rcond=None)
    return b


def parts_of(des, d1, groups):
    X = np.column_stack([des[k] for k in groups])
    b = ols(X, d1)
    out, i = {}, 0
    for k in groups:
        w = des[k].shape[1]
        out[k] = des[k] @ b[i:i + w]
        i += w
    out["rest"] = d1 - X @ b
    return out


def worth(q, part, y, cl):
    lq = R.lg(q)
    return R.cmean(R.ll(expit(lq - part), y) - R.ll(q, y), cl)


def analyse(g: pd.DataFrame, label: str, rows: list):
    g = R.add_pairs(g.copy())
    y, cl = g["y"].to_numpy(float), g["block"].to_numpy()
    q = g["q_full"].to_numpy()
    d1 = R.lg(g["q_full_s1"].to_numpy()) - R.lg(g["q_close"].to_numpy())
    d2 = R.lg(q) - R.lg(g["q_full_s1"].to_numpy())
    des = design(g)
    full = parts_of(des, d1, GROUPS)
    tot = R.gain(g["q_close"], q, y, cl)
    r2 = 1 - np.sum(full["rest"] ** 2) / np.sum(d1 ** 2)
    ws = {}
    for k in list(GROUPS) + ["rest"]:
        w = worth(q, full[k], y, cl)
        ws[k] = w["est"]
        rows.append({"window": label, "method": "joint surrogate (lead's)", "part": k, **w, "word": R.word(w),
                     "total": tot["est"], "r2": r2, "n": len(g)})
    if np.any(d2 != 0):
        w = worth(q, d2, y, cl)
        ws["speed"] = w["est"]
        rows.append({"window": label, "method": "joint surrogate (lead's)", "part": "speed (stage 2)", **w,
                     "word": R.word(w), "total": tot["est"], "r2": r2, "n": len(g)})
    P = pd.DataFrame({k: full[k] for k in GROUPS})
    corr = P.corr().round(2)
    # unique part: surrogate without family f; what is lost from the TOTAL disagreement is d1_fit_full - d1_fit_without
    for f in ("ratings", "schedule", "form", "ios", "price shape"):
        others = [k for k in GROUPS if k != f]
        Xa = np.column_stack([des[k] for k in GROUPS])
        Xo = np.column_stack([des[k] for k in others])
        lost = Xa @ ols(Xa, d1) - Xo @ ols(Xo, d1)
        w = worth(q, lost, y, cl)
        rows.append({"window": label, "method": "unique (surrogate refitted without it)", "part": f, **w,
                     "word": R.word(w), "total": tot["est"], "r2": r2, "n": len(g)})
        # family alone with the price shape (what an analyst attributing 'first' would credit)
        Xf = np.column_stack([des["price shape"], des[f]]) if f != "price shape" else des["price shape"]
        bf = ols(Xf, d1)
        alone = Xf @ bf - (des["price shape"] @ bf[:3] if f != "price shape" else 0)
        w = worth(q, alone, y, cl)
        rows.append({"window": label, "method": "alone (surrogate on price shape + it)", "part": f, **w,
                     "word": R.word(w), "total": tot["est"], "r2": r2, "n": len(g)})
    return ws, tot, corr


def main():
    a = R.load_analysis()
    a = a[(a["season"] >= 2020) & ~a["debut"]]
    rows = []
    out = {}
    for label, m in {
        "men 2025-26": a["season"].isin((2025, 2026)) & (a["tour"] == "atp"),
        "women 2025-26": a["season"].isin((2025, 2026)) & (a["tour"] == "wta"),
        "men 2020-24": a["season"].between(2020, 2024) & (a["tour"] == "atp"),
        "women 2020-24": a["season"].between(2020, 2024) & (a["tour"] == "wta"),
        "women H-exposed, Pinnacle-fed (to 7 Sep 2025)": a["season"].isin((2025, 2026)) & (a["tour"] == "wta")
                                                         & (a["tournament_date"] <= "2025-09-07"),
        "women H-exposed, BetOnline-fed (from 8 Sep 2025)": a["season"].isin((2025, 2026)) & (a["tour"] == "wta")
                                                            & (a["tournament_date"] > "2025-09-07"),
        "men H-exposed, Pinnacle-fed (to 7 Sep 2025)": a["season"].isin((2025, 2026)) & (a["tour"] == "atp")
                                                       & (a["tournament_date"] <= "2025-09-07"),
        "men H-exposed, BetOnline-fed (from 8 Sep 2025)": a["season"].isin((2025, 2026)) & (a["tour"] == "atp")
                                                          & (a["tournament_date"] > "2025-09-07"),
    }.items():
        ws, tot, corr = analyse(a[m.to_numpy()].reset_index(drop=True), label, rows)
        out[label] = (ws, tot, corr)
    df = pd.DataFrame(rows)
    df.to_csv(R.OUT / "rt_anatomy.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    print(df[["window", "method", "part", "est", "lo", "hi", "P", "word", "total"]].round(3).to_string(index=False))
    for label, (ws, tot, corr) in out.items():
        s = sum(v for k, v in ws.items())
        print(f"\n{label}: total gain {tot['est']:+.2f}; sum of the parts' worths {s:+.2f}")
        print(corr.to_string())


if __name__ == "__main__":
    main()
