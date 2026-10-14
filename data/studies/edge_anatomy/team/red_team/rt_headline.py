"""Red team: re-derive README section 3 (the model's gain over its recalibrated price, by tour) from analysis.parquet's
raw columns (p_mkt, the 16 stored seeds, the speed column, y), without the lead's code or its stored q_close / q_full.

Recipe re-implemented from the docstrings (compare.walk_forward / close_forecast / data.py):
  * price: per test season Y, one slope per tour on logit(p_mkt), fitted on 2019..Y-1, debut seasons out;
  * model: eta4 = logit(mean of seeds 0-3); per Y fit (s_atp, s_wta, b) on 2019..Y-1 with men's spd as the third
    column; b shrunk b * tau^2 / (tau^2 + se^2), tau 0.05, se = inverse-Fisher; final q = expit(s * logit(mean of 16
    seeds) + b * spd_men).
Then the same gains as edge.py, plus extra readings the README omits.

Run: ./python.sh data/studies/edge_anatomy/team/red_team/rt_headline.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_common as R  # noqa: E402

TAU = 0.05
TEST = tuple(range(2020, 2027))


def build():
    a = R.load_analysis().set_index("match_id")
    seeds = pd.read_parquet(R.STUDY / "seeds.parquet").set_index("match_id").reindex(a.index)
    P = seeds.to_numpy(float)
    eta4 = R.lg(P[:, :4].mean(axis=1))
    eta16 = R.lg(P.mean(axis=1))
    atp = (a["tour"] == "atp").to_numpy()
    z = np.where(atp, a["spd"].to_numpy(float), 0.0)
    y = a["y"].to_numpy(float)
    s = a["season"].to_numpy()
    deb = a["debut"].to_numpy(bool)
    L = R.lg(a["p_mkt"].to_numpy(float))
    qc = np.full(len(a), np.nan)
    qf = np.full(len(a), np.nan)
    qf1 = np.full(len(a), np.nan)
    qk = np.full((len(a), P.shape[1]), np.nan)
    pars = {}
    for Y in TEST:
        h = (s < Y) & (s >= 2019) & ~deb
        te = s == Y
        Xc = np.column_stack([np.where(atp, L, 0), np.where(~atp, L, 0)])
        bc, _ = R.logistic(Xc[h], y[h])
        qc[te] = expit(Xc[te] @ bc)
        Xm = np.column_stack([np.where(atp, eta4, 0), np.where(~atp, eta4, 0), z])
        bm, Hi = R.logistic(Xm[h], y[h])
        se_b = np.sqrt(Hi[2, 2])
        b_sh = bm[2] * TAU ** 2 / (TAU ** 2 + se_b ** 2)
        Xm1 = Xm[:, :2]
        bm1, _ = R.logistic(Xm1[h], y[h])
        sl = np.where(atp, bm[0], bm[1])
        qf[te] = expit(sl[te] * eta16[te] + b_sh * z[te])
        qk[te] = expit(sl[te, None] * R.lg(P[te]) + (b_sh * z[te])[:, None])
        sl1 = np.where(atp, bm1[0], bm1[1])
        qf1[te] = expit(sl1[te] * eta16[te])
        pars[Y] = dict(s_atp=bm[0], s_wta=bm[1], b=bm[2], b_shrunk=b_sh, c_atp=bc[0], c_wta=bc[1])
    a["rq_close"], a["rq_full"], a["rq_full_s1"] = qc, qf, qf1
    return a, qk, pars


def seed_var(qk, y):
    g = 1000 * R.ll(qk, y[:, None]).mean(axis=0)       # per-seed LL (price side has no seeds)
    return float(np.var(g, ddof=1) / len(g))


def main():
    a, qk, pars = build()
    test = a["season"].isin(TEST).to_numpy()
    rows = []
    chk = {"max|rq_close - q_close|": float(np.nanmax(np.abs(a.loc[test, "rq_close"] - a.loc[test, "q_close"]))),
           "max|rq_full - q_full|": float(np.nanmax(np.abs(a.loc[test, "rq_full"] - a.loc[test, "q_full"]))),
           "max|rq_full_s1 - q_full_s1|": float(np.nanmax(np.abs(a.loc[test, "rq_full_s1"] - a.loc[test, "q_full_s1"])))}
    print("reproduction of the stored forecasts:", chk)
    print(pd.DataFrame(pars).T.round(4))
    for wname, win in {"2025-26": (2025, 2026), "2020-24": tuple(range(2020, 2025)), "2025": (2025,),
                       "2026": (2026,), "2020-26": TEST}.items():
        for tour in ("both", "atp", "wta"):
            m = a["season"].isin(win).to_numpy() & ~a["debut"].to_numpy()
            if tour != "both":
                m &= (a["tour"] == tour).to_numpy()
            g = a[m]
            y = g["y"].to_numpy()
            for blkname, cl in (("4wk", g["block"].to_numpy()), ("4wk-shift14", R.blocks(g["tournament_date"], 28, 14)),
                                ("8wk", R.blocks(g["tournament_date"], 56))):
                d = R.gain(g["rq_close"], g["rq_full"], y, cl, seed_var(qk[m], y))
                rows.append({"window": wname, "tour": tour, "reading": "model vs recalibrated price", "blocks": blkname,
                             **d, "word": R.word(d)})
            cl = g["block"].to_numpy()
            for name, base in (("model vs raw margin-free price", "p_mkt"),
                               ("model vs recalibrated books' average", "q_avg_close")):
                d = R.gain(g[base], g["rq_full"], y, cl, seed_var(qk[m], y))
                rows.append({"window": wname, "tour": tour, "reading": name, "blocks": "4wk", **d, "word": R.word(d)})
            d = R.gain(g["rq_full_s1"], g["rq_full"], y, cl)
            rows.append({"window": wname, "tour": tour, "reading": "stage 2 adds", "blocks": "4wk", **d, "word": R.word(d)})
    out = pd.DataFrame(rows)
    out.to_csv(R.OUT / "rt_headline.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 300)
    print(out[["window", "tour", "reading", "blocks", "est", "lo", "hi", "P", "G", "n", "word"]].round(3)
          .to_string(index=False))

    # differences between windows (independent samples): women 2025-26 vs 2020-24, men likewise
    print("\nwindow differences (2025-26 minus 2020-24; independent blocks):")
    h = out[(out.reading == "model vs recalibrated price") & (out.blocks == "4wk")].set_index(["window", "tour"])
    for tour in ("atp", "wta", "both"):
        r1, r0 = h.loc[("2025-26", tour)], h.loc[("2020-24", tour)]
        diff = r1["est"] - r0["est"]
        se = np.hypot(r1["se"], r0["se"])
        print(f"  {tour}: {diff:+.2f} (se {se:.2f}, z {diff / se:+.2f}, two-sided p {2 * R.norm.sf(abs(diff / se)):.2f})")

    # where the 2025-26 men's gain sits by the odds input's source
    print("\nmen 2025-26 by the odds input's source (model vs recalibrated price; blocks):")
    m = a["season"].isin((2025, 2026)) & ~a["debut"] & (a["tour"] == "atp")
    for src, g in a[m].groupby("odds_input"):
        d = R.gain(g["rq_close"], g["rq_full"], g["y"].to_numpy(), g["block"].to_numpy())
        print(f"  {src:24s} n {len(g):5d}  G {d['G']:2d}  {R.fmt(d)}")
    for name, cut in (("to 7 Sep 2025 (Pinnacle-fed)", a["tournament_date"] <= "2025-09-07"),
                      ("from 8 Sep 2025 (BetOnline-fed)", a["tournament_date"] > "2025-09-07")):
        for tour in ("atp", "wta"):
            mm = a["season"].isin((2025, 2026)) & ~a["debut"] & (a["tour"] == tour) & cut
            g = a[mm]
            d = R.gain(g["rq_close"], g["rq_full"], g["y"].to_numpy(), g["block"].to_numpy())
            print(f"  {name:32s} {tour}  n {len(g):5d}  {R.fmt(d)}")


if __name__ == "__main__":
    main()
