"""Stage 3, part 3: would a flexible learner find what the linear A - B features miss?

Stage 2 scored each shot-level feature as an A - B difference in a logistic regression: a straight line in a contrast.
A learner that sees both players' values separately can find matchups (a big server against a weak returner) and
curves. This diagnostic gives gradient boosting (scikit-learn's HistGradientBoostingClassifier, the TabPFN study's
settings) and ridge logistic regression the closing odds plus:

    shot      the shot-level features of both players separately (A's and B's values, two-week and 52-week memories,
              own / conceded / opponent-adjusted), and their A - B differences for the linear models
    box       the reference: the 16-input box-score profile of the UFC study's Stage D (A - B) and each player's box-score
              serve and return points won in the same two memories
    box+shot  both

on the TabPFN study's design: main-tour matches with closing odds, fitted on 2013-2021, scored on 2022-2026; each test
match predicted in both orientations and averaged; the gain over the odds recalibrated on the same training matches;
95% intervals from four-week blocks of tournament dates (the corrected harness's method). The boosting iterations and
the ridge penalty are chosen on the 2021 season (fitted on 2013-2020), then refitted on 2013-2021. Training rows are
added in both orientations, so the fits are symmetric in A and B.

Run:  ./python.sh src/eda/shot_level/stage3_flexible.py   (several minutes)
Writes data/studies/shot_level/stage3_flexible.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402

MAIN = ("GS", "FIN", "T1000", "T500", "T250")
TRAIN, TEST = (2013, 2021), (2022, 2026)
GBM = dict(learning_rate=0.03, max_leaf_nodes=15, min_samples_leaf=100, l2_regularization=1.0)
ORIGIN = np.datetime64("2010-01-04")
RIDGE_C = (1e-5, 3e-5, 1e-4, 3e-4, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 10.0)


def columns(sides: pd.DataFrame) -> dict:
    a_cols = [c for c in sides.columns if c.startswith("A|") and not c.endswith("|has") and "|box|" not in c
              and c.split("|")[-1] in ("w52", "dec2")]
    shot_names = [c[2:] for c in a_cols]
    box_names = [c[2:] for c in sides.columns if c.startswith("A|") and "|box|" in c and not c.endswith("|has")
                 and c.split("|")[-1] in ("w52", "dec2")]
    profile = [f"adjperf_{s}|decayed" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved",
                                                "bp_faced_pg", "brk", "bp_conv", "rpw_first", "rpw_second")] + \
              [f"adjdef_{s}|decayed" for s in ("ace", "df", "first_in", "bp_faced_pg")]
    return {"shot": shot_names, "box_sides": box_names, "profile": profile}


def frame(sides: pd.DataFrame, cols: dict) -> pd.DataFrame:
    prof = pd.read_parquet(ROOT / "data/studies/ufc_ideas/stageD_profile_features.parquet", columns=["match_id"] + cols["profile"])
    f = sides[sides["evaluation"].astype(bool) & sides["p_mkt"].notna() & sides["group"].isin(MAIN)]
    f = f[f["year"].between(TRAIN[0], TEST[1])].merge(prof, on="match_id", how="left")
    return f.reset_index(drop=True)


def matrices(f: pd.DataFrame, cols: dict, kind: str, flip: bool = False) -> np.ndarray:
    """The inputs of one feature set, in one orientation: the odds' log-odds, then the set's columns. Side columns are
    swapped and differences negated when flipped."""
    sgn = -1.0 if flip else 1.0
    lm = sgn * logit(np.clip(f["p_mkt"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9))
    parts = [lm[:, None]]
    if kind in ("shot", "box+shot", "shot_diff", "box+shot_diff"):
        for n in cols["shot"]:
            a, b = f[f"A|{n}"].to_numpy(dtype="float64"), f[f"B|{n}"].to_numpy(dtype="float64")
            if kind.endswith("_diff"):
                parts.append((sgn * (a - b))[:, None])
            else:
                parts.append(np.column_stack([b, a]) if flip else np.column_stack([a, b]))
    if kind in ("box", "box+shot", "box_diff", "box+shot_diff"):
        for n in cols["profile"]:
            parts.append((sgn * f[n].to_numpy(dtype="float64"))[:, None])
        for n in cols["box_sides"]:
            a, b = f[f"A|{n}"].to_numpy(dtype="float64"), f[f"B|{n}"].to_numpy(dtype="float64")
            if kind.endswith("_diff"):
                parts.append((sgn * (a - b))[:, None])
            else:
                parts.append(np.column_stack([b, a]) if flip else np.column_stack([a, b]))
    return np.column_stack(parts)


def ll(p, y):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -np.where(y, np.log(p), np.log(1 - p))


def interval(d: np.ndarray, dates: np.ndarray) -> dict:
    blocks = ((np.asarray(dates, dtype="datetime64[D]") - ORIGIN).astype(int)) // 28
    labels, ix = np.unique(blocks, return_inverse=True)
    mean = d.mean()
    infl = np.bincount(ix, weights=d - mean)
    G = len(labels)
    se = np.sqrt(G / (G - 1) * (infl @ infl)) / len(d)
    rad = student_t.ppf(0.975, G - 1) * se
    return {"gain": 1000 * mean, "lo": 1000 * (mean - rad), "hi": 1000 * (mean + rad), "n": int(len(d)), "blocks": int(G)}


ODDS_SCALE = 100.0      # the odds' column, standardised then multiplied: its coefficient is barely penalised


def scaled(Xfit: np.ndarray, *others: np.ndarray) -> list[np.ndarray]:
    """Standardise on the fitting rows (ridge needs inputs on one scale); the first column (the odds) is then scaled up
    so that the penalty falls on the other inputs, not on the market."""
    mu, sd = Xfit.mean(axis=0), Xfit.std(axis=0)
    sd[sd == 0] = 1.0
    out = []
    for X in (Xfit,) + others:
        Z = (X - mu) / sd
        Z[:, 0] *= ODDS_SCALE
        out.append(Z)
    return out


def fit_predict(model: str, Xtr, ytr, Xva, yva, Xfull, yfull, Xte, Xte_flip):
    """Choose the capacity on the validation season, refit on all training seasons (both orientations), predict the
    test matches in both orientations and average. 'gbm_mono' constrains the forecast to rise with the odds."""
    if model.startswith("gbm"):
        mono = np.zeros(Xtr.shape[1], dtype=int)
        if model == "gbm_mono":
            mono[0] = 1
        params = dict(GBM, monotonic_cst=mono)
        est = HistGradientBoostingClassifier(max_iter=1500, early_stopping=False, **params).fit(Xtr, ytr)
        losses = [ll(p[:, 1], yva).mean() for p in est.staged_predict_proba(Xva)]
        best = int(np.argmin(losses)) + 1
        final = HistGradientBoostingClassifier(max_iter=best, early_stopping=False, **params).fit(Xfull, yfull)
        cap = best
        p = 0.5 * (final.predict_proba(Xte)[:, 1] + 1 - final.predict_proba(Xte_flip)[:, 1])
        return p, cap
    scores = []
    Ztr, Zva = scaled(Xtr, Xva)
    for c in RIDGE_C:
        lr = LogisticRegression(C=c, fit_intercept=False, max_iter=2000).fit(Ztr, ytr)
        scores.append(ll(lr.predict_proba(Zva)[:, 1], yva).mean())
    cap = RIDGE_C[int(np.argmin(scores))]
    Zfull, Zte, Zte_flip = scaled(Xfull, Xte, Xte_flip)
    final = LogisticRegression(C=cap, fit_intercept=False, max_iter=2000).fit(Zfull, yfull)
    p = 0.5 * (final.predict_proba(Zte)[:, 1] + 1 - final.predict_proba(Zte_flip)[:, 1])
    return p, cap


def main() -> int:
    sides = pd.read_parquet(S.OUT / "stage3_sides.parquet")
    cols = columns(sides)
    f = frame(sides, cols)
    S.log(f"{len(f)} matches with odds; {len(cols['shot'])} shot inputs a side, {len(cols['profile'])} profile, "
          f"{len(cols['box_sides'])} box form a side")
    res = {"design": {"train": TRAIN, "test": TEST, "gbm": GBM, "ridge_C": RIDGE_C,
                      "shot_inputs_per_side": len(cols["shot"]), "profile_inputs": len(cols["profile"]),
                      "box_form_per_side": len(cols["box_sides"])}, "results": {}}
    for t in C.TOURS:
        g = f[f["tour"].eq(t)].reset_index(drop=True)
        g = g[g[cols["profile"]].notna().all(axis=1)].reset_index(drop=True)      # the reference needs its inputs
        yr, y = g["year"].to_numpy(), g["a_won"].to_numpy().astype(bool)
        tr, va, full, te = yr < 2021, yr == 2021, yr <= TRAIN[1], yr >= TEST[0]
        dates = g["tournament_date"].to_numpy()[te]
        yte = y[te]
        # the base: the odds recalibrated on the training matches (one slope, no intercept)
        lm = logit(np.clip(g["p_mkt"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9))
        b = LogisticRegression(C=1e6, fit_intercept=False, max_iter=200).fit(lm[full][:, None], y[full]).coef_[0, 0]
        p_base = expit(b * lm[te])
        llb = ll(p_base, yte)
        out = {"matches_train": int(full.sum()), "matches_test": int(te.sum()), "odds_slope": float(b),
               "raw_odds_vs_recalibrated": interval(ll(g["p_mkt"].to_numpy()[te], yte) - llb, dates)}
        specs = [("ridge", "shot_diff"), ("ridge", "box_diff"), ("ridge", "box+shot_diff"),
                 ("gbm", "odds"), ("gbm", "shot"), ("gbm", "box"), ("gbm", "box+shot"),
                 ("gbm_mono", "odds"), ("gbm_mono", "shot"), ("gbm_mono", "box"), ("gbm_mono", "box+shot")]
        preds = {}
        for model, kind in specs:
            def X(mask, flip=False):
                if kind == "odds":
                    lmx = (-1 if flip else 1) * lm[mask]
                    return lmx[:, None]
                return matrices(g[mask], cols, kind, flip)
            Xtr = np.vstack([X(tr), X(tr, True)])
            ytr = np.concatenate([y[tr], ~y[tr]])
            Xfull = np.vstack([X(full), X(full, True)])
            yfull = np.concatenate([y[full], ~y[full]])
            p, cap = fit_predict(model, Xtr, ytr, X(va), y[va], Xfull, yfull, X(te), X(te, True))
            r = interval(llb - ll(p, yte), dates)
            r["capacity"] = cap
            out[f"{model}|{kind}"] = r
            preds[(model, kind)] = p
            if model.startswith("gbm") and kind != "odds":
                rel = interval(ll(preds[(model, "odds")], yte) - ll(p, yte), dates)
                out[f"{model}|{kind}|over_same_learner_on_odds"] = rel
            if kind == "box+shot" or kind == "box+shot_diff":
                ref = (model, "box") if model.startswith("gbm") else (model, "box_diff")
                out[f"{model}|{kind}|over_box_alone"] = interval(ll(preds[ref], yte) - ll(p, yte), dates)
            S.log(f"  {t} {model} {kind}: {r['gain']:+.2f} ({r['lo']:+.2f} to {r['hi']:+.2f}), capacity {cap}")
        res["results"][t] = out
    (S.OUT / "stage3_flexible.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
