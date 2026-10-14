"""Score the TabPFN-3.5-Thinking forecast against the free models on the same test matches (main tour 2022-2026).

Written and run on the free models before the paid call, so the scoring rules were fixed before any TabPFN forecast
existed. All gains are milli-log-loss, positive = the second-named model is better, with paired 95% cluster t
intervals over four-week blocks of tournament dates (calendar weeks as a sensitivity). Per tour, as the earlier
studies report, and both tours together.

    beyond_odds     on the test matches with odds: every model that takes the odds as an input (the free linear and
                    boosting models, and TabPFN) against the odds recalibrated on the same training matches (one
                    logistic slope, single fit), and against the raw odds
    nonlinear_odds  on the same matches: TabPFN against the linear model with the same inputs (lr_mkt_all, which
                    lacks only the match context), against the audit's best linear forecast (odds + everything +
                    profile) and against boosting; boosting with interactions against boosting without
    stacks          every model's forecast stacked with the odds (a logistic regression without an intercept on [odds
                    log-odds, model log-odds], per tour, cross-fitted leaving one test season out; and forward-only:
                    each season 2023-2026 fitted on the earlier test seasons), against the odds stacked the same way:
                    a check that does not depend on the model's own calibration
    beyond_elo      the free models without odds against Elo recalibrated, on every test match; non-linear against
                    linear on the same inputs (TabPFN is not in this section: it was given the odds)
    ladder          (coin - log loss) / (coin - the raw odds' log loss) on the test matches with odds
    by_group        the main comparisons by level group and season
    adjustment      what each odds model does to the price: its log-odds minus the recalibrated odds' log-odds,
                    explained per tour by a linear fit, by boosting without interactions and by boosting with them
                    (R^2 on held-out tournaments), and the input groups' permutation importance in that surrogate

Writes data/studies/tabpfn_thinking/results.json, results.csv and test_predictions.parquet.
Run: ./python.sh src/eda/tabpfn_thinking/score.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking import guard as G  # noqa: E402

FREE = ["elo", "lr_everything", "lr_all", "gbm_additive", "gbm"]                          # no odds
FREE_MKT = ["lr_mkt_profile", "lr_mkt_everything", "lr_mkt_everything_profile", "lr_mkt_all", "gbm_mkt_additive",
            "gbm_mkt"]                                                                       # odds as an input
SEASONS = list(range(T.TEST_YEARS[0], T.TEST_YEARS[1] + 1))
SURR_PARAMS = dict(learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0, max_iter=600,
                   random_state=0)


def lg(p: np.ndarray) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), T.EPS, 1 - T.EPS))


def load() -> tuple[pd.DataFrame, dict]:
    f = pd.read_parquet(T.OUT / "frame.parquet")
    f = f[f["split"] == "test"].reset_index(drop=True)
    f["p_elo_raw"] = f["p_elo"]               # before the baselines: their model "elo" writes p_elo (recalibrated)
    f["p_market_raw"] = f["p_mkt"]
    b = pd.read_parquet(T.OUT / "baselines.parquet")
    assert (b["match_id"].to_numpy() == f["match_id"].to_numpy()).all()
    for c in b.columns:
        if c.startswith("p_"):
            f[c] = b[c].to_numpy()
    info = {"tabpfn": False}
    pred = T.THINKING / "predictions.npz"
    if pred.exists():
        ids = pd.read_parquet(T.UPLOAD / "query_ids.parquet")
        _, p_a, metadata, binding = G.load_predictions(pred, None, len(ids))
        n = len(ids) // 2
        assert (ids["orientation"].to_numpy() == np.r_[np.zeros(n), np.ones(n)]).all()
        rows = f.index[f["tabpfn_split"] == "test"]
        assert (ids["match_id"].to_numpy()[:n] == f.loc[rows, "match_id"].to_numpy()).all()
        for col, v in (("p_tabpfn_orig", p_a[:n]), ("p_tabpfn_flip", p_a[n:]),
                       ("p_tabpfn", T.symmetrize(p_a[:n], p_a[n:]))):
            f[col] = np.nan
            f.loc[rows, col] = v
        gap = np.abs(p_a[:n] - (1 - p_a[n:]))
        info = {"tabpfn": True, "metadata": metadata, "binding": binding, "matches": int(n),
                "asymmetry_mean_abs": float(gap.mean()), "asymmetry_p95": float(np.quantile(gap, 0.95)),
                "asymmetry_max": float(gap.max())}
    return f, info


def odds_models(f: pd.DataFrame) -> list[str]:
    return [m for m in FREE_MKT + ["tabpfn"] if f"p_{m}" in f]


def subsets(f: pd.DataFrame, with_odds: bool):
    has = np.isfinite(f["p_mkt"].to_numpy(dtype=float)) if with_odds else np.ones(len(f), dtype=bool)
    yield "atp", has & (f["tour"] == "atp").to_numpy()
    yield "wta", has & (f["tour"] == "wta").to_numpy()
    yield "both", has


def cmp(f: pd.DataFrame, mask: np.ndarray, base: str, model: str) -> dict:
    pb, pm = f[f"p_{base}"].to_numpy(dtype=float), f[f"p_{model}"].to_numpy(dtype=float)
    m = mask & np.isfinite(pb) & np.isfinite(pm)
    y = f["a_won"].to_numpy()[m]
    out = T.compare(T.ll(pb[m], y), T.ll(pm[m], y), f["tournament_date"].to_numpy()[m])
    out.update(base=base, model=model)
    return out


# ------------------------------------------------------------------------------------------------
# Stacking with the odds

def stack(f: pd.DataFrame, mask: np.ndarray, model: str | None, forward: bool) -> np.ndarray:
    """Cross-fitted forecasts from [odds log-odds (, model log-odds)] on the rows in mask (NaN elsewhere)."""
    out = np.full(len(f), np.nan)
    year = f["year"].to_numpy()
    y = f["a_won"].to_numpy().astype(float)
    Z = lg(f["p_mkt"].to_numpy())[:, None]
    if model is not None:
        Z = np.column_stack([Z, lg(f[f"p_{model}"].to_numpy())])
    for Y in SEASONS:
        test = mask & (year == Y)
        train = mask & ((year < Y) if forward else (year != Y))
        if test.sum() == 0 or train.sum() < 300:
            continue
        b, _ = T.fit_logistic(Z[train], y[train])
        out[test] = expit(Z[test] @ b)
    return out


def stacked(f: pd.DataFrame, models: list[str], forward: bool) -> pd.DataFrame:
    has = np.isfinite(f["p_mkt"].to_numpy(dtype=float))
    S = f[["a_won", "tournament_date"]].copy()
    for col, model in [("p_stack_base", None)] + [(f"p_stack_{m}", m) for m in models]:
        v = np.full(len(f), np.nan)
        for t in T.TOURS:
            mt = has & (f["tour"] == t).to_numpy()
            if model is not None:
                mt &= np.isfinite(f[f"p_{model}"].to_numpy(dtype=float))
            v[mt] = stack(f, mt, model, forward)[mt]
        S[col] = v
    return S


def stack_coefs(f: pd.DataFrame, mask: np.ndarray, model: str) -> dict:
    y = f["a_won"].to_numpy().astype(float)
    Z = np.column_stack([lg(f["p_mkt"].to_numpy()), lg(f[f"p_{model}"].to_numpy())])
    ok = mask & np.isfinite(Z).all(axis=1)
    b, se = T.fit_logistic(Z[ok], y[ok])
    return {"odds": [float(b[0]), float(se[0])], "model": [float(b[1]), float(se[1])], "n": int(ok.sum())}


# ------------------------------------------------------------------------------------------------
# What a model does to the price (a surrogate on the test matches; free)

class Surrogate:
    """An additive-then-interactions description of an antisymmetric target (a model's adjustment to the price):
    linear: least squares on the scaled differences (no intercept); additive: a cubic spline per difference (missing =
    0 = no difference) with a light ridge; interactions: boosting on every input (the match context included, which can
    act only through interactions) fitted to the additive model's residuals."""

    def __init__(self, anti: list[str], cat: list[str]):
        self.anti, self.cat = anti, cat

    def _D(self, X: pd.DataFrame) -> np.ndarray:
        return np.nan_to_num(X[self.anti].to_numpy(dtype=float), nan=0.0)

    def fit(self, X: pd.DataFrame, z: np.ndarray) -> "Surrogate":
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import SplineTransformer
        D = self._D(X)
        sd = D.std(axis=0)
        self.sd = np.where(sd > 0, sd, 1.0)
        Ds = D / self.sd
        self.beta, *_ = np.linalg.lstsq(Ds, z, rcond=None)
        self.spline = SplineTransformer(n_knots=6, degree=3, extrapolation="linear").fit(Ds)
        self.ridge = Ridge(alpha=1.0, fit_intercept=False).fit(self.spline.transform(Ds), z)
        resid = z - self.ridge.predict(self.spline.transform(Ds))
        cat = [list(X.columns).index(c) for c in self.cat if c in X.columns]
        self.gbm = HistGradientBoostingRegressor(categorical_features=cat or None, **SURR_PARAMS).fit(X, resid)
        return self

    def predict(self, X: pd.DataFrame) -> dict:
        Ds = self._D(X) / self.sd
        add = self.ridge.predict(self.spline.transform(Ds))
        return {"linear": Ds @ self.beta, "additive": add, "with_interactions": add + self.gbm.predict(X)}


def adjustment(f: pd.DataFrame, model: str) -> dict:
    """The model's log-odds minus the recalibrated odds' log-odds, on the test matches with odds in both orientations
    (an antisymmetric target), per tour: the share of its variance a linear fit, an additive (spline) fit and the
    additive fit plus interactions explain on held-out tournaments (two halves, each predicted from the other), and
    the input groups' permutation importance (share explained lost) in the full surrogate."""
    out = {}
    for t in T.TOURS:
        m = ((f["tour"] == t).to_numpy() & np.isfinite(f[f"p_{model}"].to_numpy(dtype=float))
             & np.isfinite(f["p_market"].to_numpy(dtype=float)))
        g = f[m].reset_index(drop=True)
        X = pd.DataFrame({c: g[f"in_{c}"].to_numpy(dtype=float) for c in T.TABPFN_NAMES})
        # within one tour: no tour column, and none that is constant or always missing (the women's indoor, best_of)
        X = X[[c for c in X.columns if c != "tour" and pd.Series(X[c]).dropna().nunique() >= 2]]
        z = lg(g[f"p_{model}"].to_numpy()) - lg(g["p_market"].to_numpy())
        XX = pd.concat([X, T.flip(X)], ignore_index=True)
        zz = np.r_[z, -z]
        tid = g["tournament_id"].astype(str).to_numpy() + "|" + g["year"].astype(str).to_numpy()
        half = (pd.util.hash_array(tid.astype(object)) % 2).astype(int)
        hh = np.r_[half, half]
        anti = [c for c in XX.columns if c in T.ANTISYMMETRIC]
        cat = [c for c in XX.columns if c in T.CATEGORICAL]

        def r2(pred, true):
            return float(1 - np.mean((true - pred) ** 2) / np.mean(true ** 2))     # antisymmetric: mean is 0

        preds = {k: np.full(len(zz), np.nan) for k in ("linear", "additive", "with_interactions")}
        models = {}
        for h in (0, 1):
            tr, te = hh != h, hh == h
            s = Surrogate(anti, cat).fit(XX[tr].reset_index(drop=True), zz[tr])
            for k, v in s.predict(XX[te].reset_index(drop=True)).items():
                preds[k][te] = v
            models[h] = s
        rec = {k: r2(v, zz) for k, v in preds.items()}
        rec["interaction_share"] = rec["with_interactions"] - rec["additive"]
        rec["adjustment_sd"] = float(zz.std())
        rec["adjustment_mean_abs_prob"] = float(np.mean(np.abs(g[f"p_{model}"].to_numpy() - g["p_market"].to_numpy())))
        rng = np.random.default_rng(0)
        imp = {}
        groups = {"odds": ["odds_logit"], **{k: [c for c in v if c in XX.columns] for k, v in T.GROUPS.items()}}
        for gname, cols in groups.items():
            if not cols:
                continue
            drop = 0.0
            for h in (0, 1):                           # models[h] was fitted on the other half
                Xte = XX[hh == h].reset_index(drop=True)
                base = r2(models[h].predict(Xte)["with_interactions"], zz[hh == h])
                Xp = Xte.copy()
                Xp[cols] = Xp[cols].to_numpy()[rng.permutation(len(Xp))]
                drop += 0.5 * (base - r2(models[h].predict(Xp)["with_interactions"], zz[hh == h]))
            imp[gname] = float(drop)
        rec["group_importance_r2_drop"] = imp
        out[t] = rec
    return out


def agreement(f: pd.DataFrame, model: str, ref: str) -> dict:
    p1, p2 = f[f"p_{model}"].to_numpy(dtype=float), f[f"p_{ref}"].to_numpy(dtype=float)
    ok = np.isfinite(p1) & np.isfinite(p2)
    p1, p2 = p1[ok], p2[ok]
    return {"n": int(ok.sum()), "mean_abs_prob_diff": float(np.mean(np.abs(p1 - p2))),
            "p95_abs_prob_diff": float(np.quantile(np.abs(p1 - p2), 0.95)),
            "max_abs_prob_diff": float(np.max(np.abs(p1 - p2))),
            "logit_corr": float(np.corrcoef(lg(p1), lg(p2))[0, 1]),
            "favourite_flips": int(((p1 > 0.5) != (p2 > 0.5)).sum())}


def calibration(f: pd.DataFrame, model: str) -> list[dict]:
    p = f[f"p_{model}"].to_numpy(dtype=float)
    y = f["a_won"].to_numpy().astype(float)
    ok = np.isfinite(p)
    p, y = p[ok], y[ok]
    bins = np.clip((p * 10).astype(int), 0, 9)
    return [{"bin": f"{b / 10:.1f}-{(b + 1) / 10:.1f}", "n": int((bins == b).sum()),
             "mean_forecast": float(p[bins == b].mean()), "observed": float(y[bins == b].mean())}
            for b in range(10) if (bins == b).sum() >= 30]


# ------------------------------------------------------------------------------------------------

def ladder(f: pd.DataFrame, S: pd.DataFrame) -> dict:
    out = {}
    for name, m in subsets(f, with_odds=True):
        y = f["a_won"].to_numpy()[m]
        mk = float(T.ll(f["p_mkt"].to_numpy()[m], y).mean())
        rec = {"matches": int(m.sum()), "coin_to_market_milli": 1000 * (T.LN2 - mk)}
        for c in ["elo_raw", "elo", "lr_everything", "lr_all", "gbm_additive", "gbm", "market"] + odds_models(f):
            p = f[f"p_{c}"].to_numpy()[m]
            if np.isfinite(p).all():
                rec[c] = T.share_of_gap(float(T.ll(p, y).mean()), mk)
        for c in [c for c in S.columns if c.startswith("p_stack_")]:
            p = S[c].to_numpy()[m]
            if np.isfinite(p).all():
                rec[c[2:]] = T.share_of_gap(float(T.ll(p, y).mean()), mk)
        out[name] = rec
    return out


def by_group(f: pd.DataFrame, S: pd.DataFrame) -> list[dict]:
    rows = []
    odds_pairs = [("market", "tabpfn"), ("lr_mkt_all", "tabpfn"), ("lr_mkt_everything_profile", "tabpfn"),
                  ("market", "lr_mkt_everything_profile"), ("market", "lr_mkt_profile"), ("market", "gbm_mkt")]
    free_pairs = [("elo", "lr_all"), ("lr_all", "gbm"), ("gbm_additive", "gbm")]
    for (name, mo), (_, ma) in zip(list(subsets(f, True))[:2], list(subsets(f, False))[:2]):
        for kind, key in [("level", "group"), ("season", "year")]:
            for val in sorted(f[key].unique()):
                sel = f[key].to_numpy() == val
                for b, mm in odds_pairs:
                    if f"p_{mm}" in f:
                        rows.append({"tour": name, "kind": kind, "value": str(val), "section": "odds",
                                     **cmp(f, mo & sel, b, mm)})
                for b, mm in free_pairs:
                    rows.append({"tour": name, "kind": kind, "value": str(val), "section": "no odds",
                                 **cmp(f, ma & sel, b, mm)})
                if "p_stack_tabpfn" in S:
                    r = cmp(S, mo & sel, "stack_base", "stack_tabpfn")
                    r.update(base="odds (cross-fitted)", model="odds + tabpfn (stack)")
                    rows.append({"tour": name, "kind": kind, "value": str(val), "section": "stack", **r})
    return rows


def main() -> int:
    f, info = load()
    om = odds_models(f)
    T.log(f"test matches {len(f):,} ({int(np.isfinite(f['p_mkt'].to_numpy(dtype=float)).sum()):,} with odds); "
          f"odds models {om}; TabPFN forecast present: {info['tabpfn']}")
    res = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "tabpfn": info,
           "beyond_odds": {}, "beyond_odds_raw": {}, "nonlinear_odds": {}, "beyond_elo": {}, "nonlinear_no_odds": {},
           "stack": {}, "stack_forward": {}, "stack_coefs": {}}
    nl_pairs = [("lr_mkt_all", "gbm_mkt_additive"), ("gbm_mkt_additive", "gbm_mkt"), ("lr_mkt_all", "gbm_mkt"),
                ("lr_mkt_everything_profile", "lr_mkt_all")]
    if "tabpfn" in om:
        nl_pairs = [("lr_mkt_all", "tabpfn"), ("lr_mkt_everything_profile", "tabpfn"), ("gbm_mkt", "tabpfn"),
                    ("gbm_mkt_additive", "tabpfn")] + nl_pairs
    stack_models = FREE + om
    frames = {"stack": stacked(f, stack_models, False), "stack_forward": stacked(f, stack_models, True)}
    for name, m in subsets(f, with_odds=True):
        res["beyond_odds"][name] = [cmp(f, m, "market", mm) for mm in om]
        res["beyond_odds_raw"][name] = [cmp(f, m, "market_raw", mm) for mm in ["market"] + om]
        res["nonlinear_odds"][name] = [cmp(f, m, b, mm) for b, mm in nl_pairs]
        for kind, S in frames.items():
            rows = []
            for mm in stack_models:
                r = cmp(S, m, "stack_base", f"stack_{mm}")
                r.update(model=mm, base="odds (cross-fitted)")
                rows.append(r)
            res[kind][name] = rows
        if name != "both":
            res["stack_coefs"][name] = {mm: stack_coefs(f, m, mm) for mm in stack_models}
    for name, m in subsets(f, with_odds=False):
        res["beyond_elo"][name] = [cmp(f, m, "elo", mm) for mm in FREE[1:]] + [cmp(f, m, "elo_raw", "elo")]
        res["nonlinear_no_odds"][name] = [cmp(f, m, b, mm) for b, mm in
                                          [("lr_all", "gbm_additive"), ("gbm_additive", "gbm"), ("lr_all", "gbm"),
                                           ("lr_everything", "lr_all")]]
    S = frames["stack"]
    res["ladder"] = ladder(f, S)
    res["by_group"] = by_group(f, S)
    res["calibration"] = {mm: calibration(f, mm) for mm in ["market", "lr_mkt_all", "gbm_mkt"] + (["tabpfn"] if "tabpfn" in om else [])}
    res["agreement"] = {f"{a} vs {b}": agreement(f, a, b) for a, b in
                        [("lr_mkt_all", "market"), ("gbm_mkt", "market"), ("gbm_mkt", "lr_mkt_all")] +
                        ([("tabpfn", "market"), ("tabpfn", "lr_mkt_all"), ("tabpfn", "gbm_mkt")] if "tabpfn" in om else [])}
    res["adjustment"] = {}
    for mm in ["lr_mkt_all", "gbm_mkt"] + (["tabpfn"] if "tabpfn" in om else []):
        res["adjustment"][mm] = adjustment(f, mm)
        T.log(f"adjustment {mm}: " + "; ".join(f"{t} " + ", ".join(f"{k} {v:.3f}" for k, v in r.items()
                                                                     if isinstance(v, float)) for t, r in res["adjustment"][mm].items()))
    T.write_json(T.OUT / "results.json", res)
    flat = []
    for section in ("beyond_odds", "beyond_odds_raw", "nonlinear_odds", "stack", "stack_forward", "beyond_elo",
                    "nonlinear_no_odds"):
        for name, rows in res[section].items():
            flat += [{"section": section, "tour": name, **r} for r in rows]
    flat += [{"section": f"by_group/{r.pop('section')}", **r} for r in [dict(x) for x in res["by_group"]]]
    pd.DataFrame(flat).to_csv(T.OUT / "results.csv", index=False)
    for c in S.columns:
        if c.startswith("p_stack_"):
            f[c] = S[c].to_numpy()
    keep = ["match_id", "tour", "year", "group", "tournament_date", "a_won", "p_elo_raw", "p_market_raw"] + \
           [c for c in f.columns if c.startswith("p_") and c not in ("p_elo", "p_mkt", "p_elo_raw", "p_market_raw")]
    f[keep].to_parquet(T.OUT / "test_predictions.parquet", index=False)
    for name in ("atp", "wta", "both"):
        for sec in ("beyond_odds", "nonlinear_odds", "stack", "beyond_elo", "nonlinear_no_odds"):
            for r in res[sec][name]:
                T.log(f"{name:4s} {sec:17s} {r['base']:>26s} -> {r['model']:<26s} {r['gain']:+.2f} "
                      f"[{r['lo']:+.2f}, {r['hi']:+.2f}] n={r['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
