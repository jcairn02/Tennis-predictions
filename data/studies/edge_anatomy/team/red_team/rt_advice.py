"""Red team: re-derive README section 6 (the professional's process, walk-forward) independently, then probe it.

1. Per-input scan by era (2013-16, 2017-19, 2020-22, 2023-24; and 2025-26 for reference only): logistic without
   intercept, per-tour free slopes on L = logit(p_mkt) fitted with one RMS-scaled input (missing = 0), cluster-robust SE
   over four-week blocks. Pooled 2013-24 beta by inverse variance. Selection per tour: |pooled z| >= 2 ("decade"),
   |z_2023-24| >= 2 ("recent").
2. The anchored ridge model (as rt_residual) on the selected inputs only, fitted per tour on 2013..Y-1, Y = 2025, 2026.
3. Probes: thresholds 1.5 / 2.5; "recent" given the same number of inputs as "decade" (top-k by |z_2023-24|); a
   placebo: k inputs drawn at random from the 50 (200 draws) to see what any 9-10 inputs deliver; the paired
   difference "last 4 seasons" against "2013..Y-1" that the README calls worse.
Outcomes: model_frame rows with tournament_date < 29 Jul 2026 only.
Run: ./python.sh data/studies/edge_anatomy/team/red_team/rt_advice.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_common as R  # noqa: E402
import rt_residual as RS  # noqa: E402

ERAS = {"2013-16": (2013, 2016), "2017-19": (2017, 2019), "2020-22": (2020, 2022), "2023-24": (2023, 2024),
        "2025-26": (2025, 2026)}
TEST = (2025, 2026)


def scan(f, xs):
    rows = []
    for era, (lo, hi) in ERAS.items():
        for tour in ("atp", "wta"):
            g = f[f["season"].between(lo, hi) & (f["tour"] == tour)]
            y, cl = g["y"].to_numpy(), R.blocks(g["tournament_date"], 28)
            L = g["L"].to_numpy()
            for c in xs:
                if c == "speed" and tour == "wta":
                    continue
                x = R.rms_scaled(g[f"in_{c}"].to_numpy(float))[0]
                X = np.column_stack([L, x])
                b, Hi = R.logistic(X, y)
                V, G = R.sandwich(X, y, np.zeros(len(y)), b, Hi, cl)
                rows.append({"era": era, "tour": tour, "input": c, "beta": b[1], "se": np.sqrt(V[1, 1]),
                             "z": b[1] / np.sqrt(V[1, 1]), "G": G})
    return pd.DataFrame(rows)


def select(sc):
    old = sc[sc["era"] != "2025-26"]
    w = 1 / old["se"] ** 2
    old = old.assign(w=w, wb=w * old["beta"])
    pooled = old.groupby(["tour", "input"]).agg(W=("w", "sum"), WB=("wb", "sum"))
    pooled["z_2013_24"] = pooled["WB"] / pooled["W"] / np.sqrt(1 / pooled["W"])
    rec = sc[sc["era"] == "2023-24"].set_index(["tour", "input"])["z"].rename("z_2023_24")
    new = sc[sc["era"] == "2025-26"].set_index(["tour", "input"])["z"].rename("z_2025_26")
    return pooled[["z_2013_24"]].join(rec).join(new).reset_index()


def anchored(ft, Y, cols, window="expanding", lam=None):
    te = ft[ft["season"] == Y]
    if window == "expanding":
        tr = ft[ft["season"] <= Y - 1]
    else:
        tr = ft[(ft["season"] >= Y - 4) & (ft["season"] <= Y - 1)]
    if lam is None:
        last = tr["season"] == tr["season"].max()
        best, bl = None, np.inf
        for l in RS.LAMS:
            b, rms = RS.fit(tr[~last], cols, l)
            v = R.ll(expit(RS.design(tr[last], cols, rms) @ b), tr.loc[last, "y"]).mean()
            if v < bl:
                best, bl = l, v
        lam = best
    b, rms = RS.fit(tr, cols, lam)
    return pd.Series(expit(RS.design(te, cols, rms) @ b), index=te["match_id"].to_numpy())


def predict(f, chosen: dict, window="expanding", lam=None):
    parts = []
    for tour in ("atp", "wta"):
        ft = f[f["tour"] == tour]
        for Y in TEST:
            parts.append(anchored(ft, Y, chosen[tour], window, lam))
    return pd.concat(parts)


def score(P, col, base="q_close"):
    out = {}
    for tour in ("both", "atp", "wta"):
        g = P if tour == "both" else P[P["tour"] == tour]
        out[tour] = R.gain(g[base], g[col], g["y"].to_numpy(), g["block"].to_numpy())
    return out


def main():
    f, xs = RS.frame()
    sc = scan(f, xs)
    sc.to_csv(R.OUT / "rt_scan_inputs.csv", index=False)
    sel = select(sc)
    sel.to_csv(R.OUT / "rt_advice_selection.csv", index=False)
    lead = pd.read_csv(R.STUDY / "advice_selection.csv")
    cmp = sel.merge(lead[["tour", "input", "z_2013_24", "z_2023_24"]], on=["tour", "input"], suffixes=("", "_lead"))
    print("max |z diff| vs the lead's selection table:",
          float(np.nanmax(np.abs(cmp["z_2013_24"] - cmp["z_2013_24_lead"]))),
          float(np.nanmax(np.abs(cmp["z_2023_24"] - cmp["z_2023_24_lead"]))))
    a = R.load_analysis().set_index("match_id")
    base = a[a["season"].isin(TEST) & ~a["debut"]][["season", "tour", "y", "block", "q_close", "q_full"]]
    rules = {}
    for thr in (1.5, 2.0, 2.5):
        rules[f"decade |z|>={thr}"] = {t: sel[(sel.tour == t) & (sel.z_2013_24.abs() >= thr)]["input"].tolist()
                                       for t in ("atp", "wta")}
        rules[f"recent |z|>={thr}"] = {t: sel[(sel.tour == t) & (sel.z_2023_24.abs() >= thr)]["input"].tolist()
                                       for t in ("atp", "wta")}
    k = {t: len(rules["decade |z|>=2.0"][t]) for t in ("atp", "wta")}
    rules["recent, top-k (k as decade)"] = {t: sel[sel.tour == t].assign(az=lambda d: d.z_2023_24.abs())
                                            .nlargest(k[t], "az")["input"].tolist() for t in ("atp", "wta")}
    rules["all 50 (49 + speed)"] = {"atp": xs, "wta": [c for c in xs if c != "speed"]}
    for name, ch in rules.items():
        print(name, {t: len(v) for t, v in ch.items()}, ch["atp"][:12], ch["wta"][:12])
    P = base.copy()
    for name, ch in rules.items():
        P[name] = predict(f, ch).reindex(P.index)
    P["decade 2.0, last 4 seasons"] = predict(f, rules["decade |z|>=2.0"], "last4").reindex(P.index)
    P["recent 2.0, last 4 seasons"] = predict(f, rules["recent |z|>=2.0"], "last4").reindex(P.index)
    rows = []
    for col in [c for c in P.columns if c not in base.columns]:
        for against in ("q_close", "q_full"):
            for tour, d in score(P, col, against).items():
                rows.append({"model": col, "against": against, "tour": tour, **d, "word": R.word(d)})
    for a_, b_ in (("decade |z|>=2.0", "decade 2.0, last 4 seasons"), ("recent |z|>=2.0", "recent 2.0, last 4 seasons"),
                   ("recent |z|>=2.0", "decade |z|>=2.0"), ("recent, top-k (k as decade)", "decade |z|>=2.0")):
        for tour, d in score(P, b_, a_).items():
            rows.append({"model": b_, "against": a_, "tour": tour, **d, "word": R.word(d)})
    # placebo: random subsets of the same size per tour as "decade"
    rng = np.random.default_rng(20261012)
    plac = []
    for i in range(60):
        ch = {t: list(rng.choice([c for c in xs if not (c == "speed" and t == "wta")], size=k[t], replace=False))
              for t in ("atp", "wta")}
        q = predict(f, ch, lam=1000.0).reindex(P.index)
        d = R.gain(P["q_close"], q, P["y"].to_numpy(), P["block"].to_numpy())
        plac.append(d["est"])
    out = pd.DataFrame(rows)
    out.to_csv(R.OUT / "rt_advice_scores.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(out[["model", "against", "tour", "est", "lo", "hi", "P", "word"]].round(2).to_string(index=False))
    plac = np.array(plac)
    print(f"\nplacebo: {len(plac)} random {k} -input subsets (lambda 1000), both tours vs the close: "
          f"median {np.median(plac):+.2f}, 10-90% {np.quantile(plac, 0.1):+.2f} .. {np.quantile(plac, 0.9):+.2f}, "
          f"max {plac.max():+.2f}; share >= 1.47: {(plac >= 1.47).mean():.2f}")
    pd.Series(plac).to_csv(R.OUT / "rt_advice_placebo.csv", index=False)


if __name__ == "__main__":
    main()
