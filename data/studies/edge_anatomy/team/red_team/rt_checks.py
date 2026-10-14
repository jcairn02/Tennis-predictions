"""Red team: further checks of the edge-anatomy README (12 Oct 2026). Outcomes: analysis.parquet (to 28 Jul 2026) and
model_frame rows with tournament_date < 29 Jul 2026 only.

 1. The men's 2025-26 serve/return leads (iosO_hold, iosO_bp_saved, iosD_first_won, prod_hold, form_bp_saved) and the
    women's serve-form leads: per-input z beyond the frame's close, split by the odds input's feed (Pinnacle-fed to
    7 Sep 2025 / BetOnline-fed after), by Slams / non-Slams, and the inputs' scale (SD) by season (an "uneven" input).
 2. Multiplicity: the 2025-26 scan's p-values on t(G - 1) instead of the normal, BH within tour; G = blocks.
 3. The underdog lean: the difference between the gains when the model leans to the underdog and to the favourite.
 4. The return at BetOnline's close, men, split by the odds input's feed.
 5. TabPFN on the price alone (arm L1, fits complete): its gain over the recalibrated price, re-derived from the fit
    files with the walk-forward recipe; and what a per-tour-and-level linear recalibration of the price gets.
 6. Women's 2025-26 gain by odds input (recalibrated price).
Run: ./python.sh data/studies/edge_anatomy/team/red_team/rt_checks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm, t as student_t

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_common as R  # noqa: E402
import rt_residual as RS  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)


def z_input(g, c):
    y, cl = g["y"].to_numpy(), R.blocks(g["tournament_date"], 28)
    x = R.rms_scaled(g[f"in_{c}"].to_numpy(float))[0]
    X = np.column_stack([g["L"].to_numpy(), x])
    b, Hi = R.logistic(X, y)
    V, G = R.sandwich(X, y, np.zeros(len(y)), b, Hi, cl)
    return b[1] / np.sqrt(V[1, 1]), G


def check1(f):
    print("\n=== 1. leads by feed, level; scale by season ===")
    lev = R.load_frame(["in_level"]).set_index("match_id")["in_level"]
    f = f.assign(slam=(lev.reindex(f["match_id"]).to_numpy() == 0.0))
    men = ["iosO_hold", "iosO_bp_saved", "iosD_first_won", "iosD_hold", "prod_hold", "prod_bp_saved", "form_bp_saved",
           "speed", "sets_14d", "surf_layoff", "age"]
    wom = ["form_ace", "form_first_won", "form_bp_saved", "form_hold", "surf_layoff", "sets_14d"]
    rec = f[f["season"].isin((2025, 2026))]
    subsets = {"all 2025-26": rec, "Pinnacle-fed (to 7 Sep 2025)": rec[rec["tournament_date"] <= "2025-09-07"],
               "BetOnline-fed (from 8 Sep 2025)": rec[rec["tournament_date"] > "2025-09-07"],
               "Slams": rec[rec["slam"]], "non-Slams": rec[~rec["slam"]],
               "2024 (development)": f[f["season"] == 2024]}
    rows = []
    for tour, ins in (("atp", men), ("wta", wom)):
        for name, g in subsets.items():
            gg = g[g["tour"] == tour]
            for c in ins:
                z, G = z_input(gg, c)
                rows.append({"tour": tour, "subset": name, "input": c, "z": z, "n": len(gg)})
    t = pd.DataFrame(rows).pivot_table(index=["tour", "input"], columns="subset", values="z")
    print(t.round(2).to_string())
    t.to_csv(R.OUT / "rt_leads_split.csv")
    sd = []
    for tour, ins in (("atp", ["iosO_hold", "iosO_bp_saved", "iosD_first_won", "prod_hold", "form_bp_saved"]),
                      ("wta", ["form_ace", "form_first_won", "form_hold", "form_bp_saved"])):
        for c in ins:
            for s, g in f[f["tour"] == tour].groupby("season"):
                x = g[f"in_{c}"].to_numpy(float)
                sd.append({"tour": tour, "input": c, "season": s, "sd": np.nanstd(x), "missing": np.mean(~np.isfinite(x))})
    sd = pd.DataFrame(sd)
    base = sd[sd.season.between(2013, 2021)].groupby(["tour", "input"])["sd"].mean().rename("sd13_21")
    sd = sd.join(base, on=["tour", "input"])
    sd["ratio"] = sd["sd"] / sd["sd13_21"]
    print(sd.pivot_table(index=["tour", "input"], columns="season", values="ratio").round(2).to_string())
    print(sd.pivot_table(index=["tour", "input"], columns="season", values="missing").round(2).to_string())


def check2():
    print("\n=== 2. multiplicity on t(G-1) ===")
    sc = pd.read_csv(R.OUT / "rt_scan_inputs.csv")
    rec = sc[sc["era"] == "2025-26"].copy()
    rec["p_norm"] = 2 * norm.sf(rec["z"].abs())
    rec["p_t"] = 2 * student_t.sf(rec["z"].abs(), rec["G"] - 1)
    for tour, g in rec.groupby("tour"):
        rec.loc[g.index, "q_norm"] = R.bh(g["p_norm"].to_numpy())
        rec.loc[g.index, "q_t"] = R.bh(g["p_t"].to_numpy())
    sel = rec[(rec["q_norm"] <= 0.10) | (rec["q_t"] <= 0.10) | (rec["z"].abs() >= 2)]
    print(sel[["tour", "input", "z", "G", "p_norm", "q_norm", "p_t", "q_t"]].sort_values(["tour", "q_t"]).round(3)
          .to_string(index=False))
    rec.to_csv(R.OUT / "rt_multiplicity.csv", index=False)


def check3(a):
    print("\n=== 3. the underdog lean ===")
    g = a[a["season"].isin((2025, 2026)) & ~a["debut"]].copy()
    d = R.lg(g["q_full"]) - R.lg(g["q_close"])
    dog = np.sign(d) != np.sign(R.lg(g["q_close"]))
    v = R.ll(g["q_close"], g["y"]) - R.ll(g["q_full"], g["y"])
    # difference of the per-match mean gains between the two groups, cluster-robust: regress v on [dog, fav] dummies
    cl = g["block"].to_numpy()
    lab, ix = np.unique(cl, return_inverse=True)
    m1, m0 = v[dog].mean(), v[~dog].mean()
    # influence of the difference
    infl = np.where(dog, (v - m1) / dog.sum(), -(v - m0) / (~dog).sum())
    s = np.bincount(ix, weights=infl)
    G = len(lab)
    se = np.sqrt(G / (G - 1) * s @ s) * 1000
    diff = 1000 * (m1 - m0)
    r = student_t.ppf(0.975, G - 1) * se
    print(f"  leans to the underdog: n {dog.sum()}, {1000 * m1:+.2f}; to the favourite: n {(~dog).sum()}, "
          f"{1000 * m0:+.2f}; difference {diff:+.2f} [{diff - r:+.2f}, {diff + r:+.2f}]")
    print(f"  share of matches leaning to the underdog {dog.mean():.2f}; share of the gain {v[dog].sum() / v.sum():.2f}")
    g2 = a[a["season"].between(2020, 2024) & ~a["debut"]]
    d2 = R.lg(g2["q_full"]) - R.lg(g2["q_close"])
    print(f"  2020-24: share leaning to the underdog {(np.sign(d2) != np.sign(R.lg(g2['q_close']))).mean():.2f}")


def stake(d):
    d = np.asarray(d, float)
    return np.where(d <= 2.0, 1.0 / (d - 1.0), d / (2.0 * (d - 1.0)))


def check4(a):
    print("\n=== 4. return at BetOnline's close, by feed (owner's staking, edge > 0, completed matches) ===")
    ref = R.ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "tables" / "data" / \
        "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
    st = pd.read_parquet(ref, columns=["match_id", "status"]).astype({"match_id": str}).set_index("match_id")["status"]
    g = a[a["season"].isin((2025, 2026))].copy()
    g["status"] = st.reindex(g["match_id"]).to_numpy()
    g = g[(g["status"] == "completed") & g["bol_a"].notna() & g["bol_b"].notna()]
    p = g["q_full"].to_numpy()
    da, db = g["bol_a"].to_numpy(float), g["bol_b"].to_numpy(float)
    eva, evb = p * da - 1, (1 - p) * db - 1
    on_a = (eva > 0) & (eva >= evb)
    on_b = (evb > 0) & ~on_a
    bet = on_a | on_b
    odds = np.where(on_a, da, db)
    sk = np.where(bet, stake(np.where(bet, odds, 2.0)), 0.0)
    won = np.where(on_a, g["y"].to_numpy() == 1, g["y"].to_numpy() == 0)
    prof = np.where(bet, np.where(won, sk * (odds - 1), -sk), 0.0)
    g = g.assign(bet=bet, sk=sk, prof=prof)
    rng = np.random.default_rng(7)
    for name, m in {"all": np.ones(len(g), bool),
                    "men": (g["tour"] == "atp").to_numpy(),
                    "men, Pinnacle-fed (to 7 Sep 2025)": ((g["tour"] == "atp") & (g["tournament_date"] <= "2025-09-07")).to_numpy(),
                    "men, BetOnline-fed (from 8 Sep 2025)": ((g["tour"] == "atp") & (g["tournament_date"] > "2025-09-07")).to_numpy(),
                    "women, Pinnacle-fed": ((g["tour"] == "wta") & (g["tournament_date"] <= "2025-09-07")).to_numpy(),
                    "women, BetOnline-fed": ((g["tour"] == "wta") & (g["tournament_date"] > "2025-09-07")).to_numpy()}.items():
        h = g[m & g["bet"].to_numpy()]
        lab, ix = np.unique(h["block"], return_inverse=True)
        P_ = np.bincount(ix, weights=h["prof"])
        S_ = np.bincount(ix, weights=h["sk"])
        W = rng.multinomial(len(lab), np.full(len(lab), 1 / len(lab)), size=2000)
        dist = (W @ P_) / (W @ S_)
        print(f"  {name:38s} bets {len(h):5d}  ROI {h['prof'].sum() / h['sk'].sum():+.3%}  "
              f"[{np.quantile(dist, 0.025):+.3%}, {np.quantile(dist, 0.975):+.3%}]")


def check5(a):
    print("\n=== 5. TabPFN on the price alone (L1) and simple recalibrations ===")
    frame = pd.read_parquet(R.INSTANCE / "model_frame.parquet", columns=["match_id", "season"])
    frame["match_id"] = frame["match_id"].astype(str)
    tab = []
    for s in range(2019, 2027):
        per = {}
        for k in range(4):
            path = R.STUDY / "fits" / f"L1__{s}__seed{k}.npz"
            with np.load(path, allow_pickle=False) as z:
                p, ids = z["p_td"], z["ids_td"].astype(str)
                meta = json.loads(str(z["meta"]))
            assert meta["columns"] == ["odds_logit"], meta["columns"]
            n = len(ids)
            per[k] = pd.Series(0.5 * (p[:n] + 1 - p[n:]), index=ids)
        tab.append(pd.DataFrame(per))
    L1 = pd.concat(tab).reindex(a["match_id"].to_numpy())
    assert not L1.isna().any().any()
    eta = R.lg(L1.mean(axis=1).to_numpy())
    atp = (a["tour"] == "atp").to_numpy()
    y, s, deb = a["y"].to_numpy(), a["season"].to_numpy(), a["debut"].to_numpy(bool)
    q = np.full(len(a), np.nan)
    Lp = R.lg(a["p_mkt"].to_numpy())
    lev = a["level"].astype(str).to_numpy()
    q_lv = np.full(len(a), np.nan)
    for Y in range(2020, 2027):
        h = (s < Y) & (s >= 2019) & ~deb
        te = s == Y
        X = np.column_stack([np.where(atp, eta, 0), np.where(~atp, eta, 0)])
        b, _ = R.logistic(X[h], y[h])
        q[te] = expit(X[te] @ b)
        # per tour x level slope recalibration of the raw price (walk-forward)
        keys = sorted(set(zip(a["tour"], lev)))
        Xl = np.column_stack([np.where((a["tour"].to_numpy() == t) & (lev == l), Lp, 0.0) for t, l in keys])
        bl, _ = R.logistic(Xl[h], y[h], ridge=1e-6)
        q_lv[te] = expit(Xl[te] @ bl)
    a = a.assign(q_L1=q, q_lv=q_lv)
    for wname, win in {"2025-26": (2025, 2026), "2020-24": tuple(range(2020, 2025))}.items():
        for tour in ("both", "atp", "wta"):
            m = a["season"].isin(win).to_numpy() & ~a["debut"].to_numpy()
            if tour != "both":
                m &= (a["tour"] == tour).to_numpy()
            g = a[m]
            d1 = R.gain(g["q_close"], g["q_L1"], g["y"].to_numpy(), g["block"].to_numpy())
            d2 = R.gain(g["q_close"], g["q_lv"], g["y"].to_numpy(), g["block"].to_numpy())
            d3 = R.gain(g["q_close"], g["q_full"], g["y"].to_numpy(), g["block"].to_numpy())
            print(f"  {wname} {tour:4s}  L1 vs price {R.fmt(d1)}   tour x level slopes {R.fmt(d2)}   "
                  f"full {d3['est']:+.2f}   L1 share {d1['est'] / d3['est']:.2f}")


def check6(a):
    print("\n=== 6. 2025-26 gain by odds input, recalibrated price ===")
    g = a[a["season"].isin((2025, 2026)) & ~a["debut"]]
    for (tour, src), h in g.groupby(["tour", "odds_input"]):
        d = R.gain(h["q_close"], h["q_full"], h["y"].to_numpy(), h["block"].to_numpy())
        print(f"  {tour} {src:24s} n {len(h):5d}  {R.fmt(d)}")


def main():
    f, xs = RS.frame()
    a = R.load_analysis()
    check1(f)
    check2()
    check3(a)
    check4(a)
    check5(a)
    check6(a)


if __name__ == "__main__":
    main()
