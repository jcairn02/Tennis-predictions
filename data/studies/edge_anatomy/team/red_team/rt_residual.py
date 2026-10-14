"""Red team: re-derive README section 4 point 2 (the transparent "price plus nudges" model against the current model)
with an independent implementation, and test its fairness and fragility.

The model: logit P = s_atp L 1[men] + s_wta L 1[women] + gamma'x, L = logit(frame's p_mkt), x = the 49 non-price
inputs (A - B; the two pairs as A - B) plus men's speed (0 for women), each scaled by its training RMS, missing = 0;
slopes unpenalised, gamma ridge-penalised. Lambda chosen as residual.py's docstring says: fit on the window without its
last season, validate on that season, from (10, 100, 1000, 10000); refit on the whole window. Expanding window
2013..Y-1, debut seasons out. Scored against analysis.parquet's q_close and q_full on the same matches.

Additions: (a) every fixed lambda; (b) 2020-26 pooled; (c) the lambda chosen per season.
Outcomes: model_frame rows with tournament_date < 29 Jul 2026 only.
Run: ./python.sh data/studies/edge_anatomy/team/red_team/rt_residual.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_common as R  # noqa: E402

LAMS = (10.0, 100.0, 1000.0, 10000.0)
TEST = tuple(range(2020, 2027))


def frame() -> tuple[pd.DataFrame, list[str]]:
    names = R.input_names()
    cols = ["tour", "season", "debut_season", "p_mkt", "a_won"] + [f"in_{n}" for n in names]
    f = R.load_frame(cols)
    f = f[~f["debut_season"].astype(bool)].copy()
    sp = pd.read_parquet(R.SPEED, columns=["match_id", "spd_L_B"]).astype({"match_id": str}).set_index("match_id")
    f["in_speed"] = sp["spd_L_B"].reindex(f["match_id"]).to_numpy(float)
    f.loc[f["tour"] == "wta", "in_speed"] = 0.0
    f = R.add_pairs(f)
    f["y"] = f["a_won"].astype(float)
    f["L"] = R.lg(f["p_mkt"])
    xs = [c for fam in R.FAM.values() for c in fam] + ["speed"]
    return f.reset_index(drop=True), xs


def design(g, xs, rms):
    atp = (g["tour"] == "atp").to_numpy()
    L = g["L"].to_numpy()
    X = [np.where(atp, L, 0.0), np.where(~atp, L, 0.0)]
    for c in xs:
        X.append(R.rms_scaled(g[f"in_{c}"].to_numpy(float), rms[c])[0])
    return np.column_stack(X)


def fit(tr, xs, lam):
    rms = {c: R.rms_scaled(tr[f"in_{c}"].to_numpy(float))[1] for c in xs}
    Z = design(tr, xs, rms)
    pen = np.r_[1e-8, 1e-8, np.full(len(xs), lam)]
    b, _ = R.logistic(Z, tr["y"].to_numpy(), ridge=pen)
    return b, rms


def choose(f, Y, xs):
    tr = f[f["season"] <= Y - 1]
    last = tr["season"] == tr["season"].max()
    best, bl = None, np.inf
    for lam in LAMS:
        b, rms = fit(tr[~last], xs, lam)
        v = R.ll(expit(design(tr[last], xs, rms) @ b), tr.loc[last, "y"]).mean()
        if v < bl:
            best, bl = lam, v
    return best


def main():
    f, xs = frame()
    a = R.load_analysis().set_index("match_id")
    preds = []
    chosen = {}
    for Y in TEST:
        te = f[f["season"] == Y]
        tr = f[f["season"] <= Y - 1]
        lam_c = choose(f, Y, xs)
        chosen[Y] = lam_c
        rec = {"match_id": te["match_id"].to_numpy()}
        for lam in LAMS:
            b, rms = fit(tr, xs, lam)
            rec[f"lam{int(lam)}"] = expit(design(te, xs, rms) @ b)
        rec["chosen"] = rec[f"lam{int(lam_c)}"]
        preds.append(pd.DataFrame(rec))
        print(f"{Y}: lambda chosen {lam_c:g}", flush=True)
    P = pd.concat(preds).set_index("match_id").join(a[["season", "tour", "y", "block", "debut", "q_close", "q_full"]],
                                                    how="inner")
    P = P[~P["debut"]]
    rows = []
    for wname, win in {"2025-26": (2025, 2026), "2020-24": tuple(range(2020, 2025)), "2020-26": TEST}.items():
        for tour in ("both", "atp", "wta"):
            g = P[P["season"].isin(win)]
            if tour != "both":
                g = g[g["tour"] == tour]
            y, cl = g["y"].to_numpy(), g["block"].to_numpy()
            for arm in ["chosen"] + [f"lam{int(l)}" for l in LAMS]:
                v1 = R.gain(g["q_close"], g[arm], y, cl)
                v2 = R.gain(g["q_full"], g[arm], y, cl)
                rows.append({"window": wname, "tour": tour, "arm": arm, "n": len(g),
                             "vs_close": v1["est"], "vs_close_lo": v1["lo"], "vs_close_hi": v1["hi"],
                             "vs_model": v2["est"], "vs_model_lo": v2["lo"], "vs_model_hi": v2["hi"],
                             "vs_model_P": v2["P"], "vs_model_word": R.word(v2)})
    out = pd.DataFrame(rows)
    out.to_csv(R.OUT / "rt_residual.csv", index=False)
    pd.Series(chosen).to_csv(R.OUT / "rt_residual_lambdas.csv")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
