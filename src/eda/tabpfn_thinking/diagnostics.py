"""Free diagnostics of the TabPFN result (no API call): where does its gain over the odds come from?

    calibration   is the gain a curved or format-specific calibration of the odds themselves (the favourite-longshot
                  shape, best of five), which needs no feature at all? Odds-only logistic regressions fitted per tour
                  on the training matches (2013-2021) and scored on the test matches:
                      odds_cubic     odds log-odds z, z|z| and z^3 (odd terms: antisymmetric)
                      odds_format    z, z x Grand Slam, z x best of five
                      odds_both      both sets of terms
                  each against the one-slope recalibration, and TabPFN against each (does TabPFN still gain once the
                  odds are calibrated flexibly?)
    by_level      the same comparisons by level
    surrogate     where the value of TabPFN's adjustment to the price lives: its adjustment rebuilt from the
                  surrogate's linear, additive and additive-plus-interactions parts (each fitted on the other half of
                  the tournaments, so every match is described out of sample), added to the recalibrated odds and scored
                  like a forecast. A description of the paid model's function on the test matches, not a model that
                  could have been fitted before them

Writes data/studies/tabpfn_thinking/diagnostics.json.
Run: ./python.sh src/eda/tabpfn_thinking/diagnostics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking import score as S  # noqa: E402


def terms(f: pd.DataFrame, kind: str) -> np.ndarray:
    z = f["in_odds_logit"].to_numpy(dtype=float)
    gs = (f["group"] == "GS").to_numpy(dtype=float)
    bo5 = (f["in_best_of"].to_numpy(dtype=float) == 5).astype(float)
    cols = {"slope": [z], "cubic": [z, z * np.abs(z), z ** 3], "format": [z, z * gs, z * bo5],
            "both": [z, z * np.abs(z), z ** 3, z * gs, z * bo5]}[kind]
    return np.column_stack(cols)


def calibrated(kind: str) -> pd.Series:
    """Per-tour odds-only fits on the training matches with odds; forecasts for the test matches."""
    fr = pd.read_parquet(T.OUT / "frame.parquet")
    fr = fr[fr["tabpfn_split"].isin(["train", "test"])].reset_index(drop=True)
    out = pd.Series(np.nan, index=fr["match_id"].to_numpy())
    for t in T.TOURS:
        tr = ((fr["tabpfn_split"] == "train") & (fr["tour"] == t)).to_numpy()
        te = ((fr["tabpfn_split"] == "test") & (fr["tour"] == t)).to_numpy()
        Z = terms(fr, kind)
        sd = Z[tr].std(axis=0)
        Zs = Z / np.where(sd > 0, sd, 1.0)
        b, _ = T.fit_logistic(Zs[tr], fr["a_won"].to_numpy()[tr])
        out.iloc[np.flatnonzero(te)] = expit(Zs[te] @ b)
    return out


def surrogate_value(f: pd.DataFrame, model: str = "tabpfn") -> list[dict]:
    """The log-loss gain over the recalibrated odds of the model's adjustment rebuilt from each surrogate part."""
    from scipy.special import logit
    rows = []
    for t in T.TOURS:
        m = ((f["tour"] == t).to_numpy() & np.isfinite(f[f"p_{model}"].to_numpy(dtype=float))
             & np.isfinite(f["p_market"].to_numpy(dtype=float)))
        g = f[m].reset_index(drop=True)
        X = pd.DataFrame({c: g[f"in_{c}"].to_numpy(dtype=float) for c in T.TABPFN_NAMES})
        X = X[[c for c in X.columns if c != "tour" and pd.Series(X[c]).dropna().nunique() >= 2]]
        base = logit(np.clip(g["p_market"].to_numpy(dtype=float), T.EPS, 1 - T.EPS))
        z = logit(np.clip(g[f"p_{model}"].to_numpy(dtype=float), T.EPS, 1 - T.EPS)) - base
        n = len(g)
        XX = pd.concat([X, T.flip(X)], ignore_index=True)
        zz = np.r_[z, -z]
        tid = g["tournament_id"].astype(str).to_numpy() + "|" + g["year"].astype(str).to_numpy()
        half = (pd.util.hash_array(tid.astype(object)) % 2).astype(int)
        hh = np.r_[half, half]
        anti = [c for c in XX.columns if c in T.ANTISYMMETRIC]
        cat = [c for c in XX.columns if c in T.CATEGORICAL]
        preds = {k: np.full(len(zz), np.nan) for k in ("linear", "additive", "with_interactions")}
        for h in (0, 1):
            s = S.Surrogate(anti, cat).fit(XX[hh != h].reset_index(drop=True), zz[hh != h])
            for k, v in s.predict(XX[hh == h].reset_index(drop=True)).items():
                preds[k][hh == h] = v
        y = g["a_won"].to_numpy()
        dates = g["tournament_date"].to_numpy()
        ll_mkt = T.ll(g["p_market"].to_numpy(dtype=float), y)
        for part, v in preds.items():
            adj = 0.5 * (v[:n] - v[n:])                     # symmetrized
            rows.append({"tour": t, "part": part, **T.compare(ll_mkt, T.ll(expit(base + adj), y), dates)})
        rows.append({"tour": t, "part": "the model itself", **T.compare(ll_mkt, T.ll(g[f"p_{model}"].to_numpy(), y), dates)})
    return rows


def main() -> int:
    f, info = S.load()
    assert info["tabpfn"], "run dispatch.py --run first"
    fr = pd.read_parquet(T.OUT / "frame.parquet", columns=["match_id", "in_best_of"])
    f = f.merge(fr, on="match_id", how="left", suffixes=("", "_fr"))
    for kind in ("slope", "cubic", "format", "both"):
        f[f"p_odds_{kind}"] = f["match_id"].map(calibrated(kind)).to_numpy()
    # the one-slope fit here must equal the baselines' "market" model
    has = np.isfinite(f["p_mkt"].to_numpy(dtype=float))
    assert np.allclose(f.loc[has, "p_odds_slope"], f.loc[has, "p_market"], atol=1e-9)
    res = {"overall": {}, "by_level": []}
    pairs = [("market", "odds_cubic"), ("market", "odds_format"), ("market", "odds_both"),
             ("odds_cubic", "tabpfn"), ("odds_format", "tabpfn"), ("odds_both", "tabpfn")]
    for name, m in S.subsets(f, with_odds=True):
        res["overall"][name] = [S.cmp(f, m, b, mm) for b, mm in pairs]
        for lv in sorted(f["group"].unique()):
            sel = m & (f["group"] == lv).to_numpy()
            for b, mm in pairs:
                res["by_level"].append({"tour": name, "level": lv, **S.cmp(f, sel, b, mm)})
    res["surrogate_value"] = surrogate_value(f)
    for r in res["surrogate_value"]:
        T.log(f"surrogate value {r['tour']} {r['part']:>18s}: {r['gain']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]")
    T.write_json(T.OUT / "diagnostics.json", res)
    for name, rows in res["overall"].items():
        for r in rows:
            T.log(f"{name:4s} {r['base']:>12s} -> {r['model']:<12s} {r['gain']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] n={r['n']}")
    d = pd.DataFrame(res["by_level"])
    d = d[d["tour"] != "both"]
    d["ci"] = d.apply(lambda x: f"{x['gain']:+.2f} [{x['lo']:+.2f}, {x['hi']:+.2f}]", axis=1)
    print(d.pivot_table(index=["tour", "level"], columns=["base", "model"], values="ci", aggfunc="first").to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
