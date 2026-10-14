"""Stage 3, part 5: the profiles again, with a fit that does not pay for its inputs.

The planted-signal test (stage3_planted.py) found that the harness's walk-forward fit of a 10-input profile costs about
half a milli-log-loss or more before any signal: the early seasons are fitted, without a penalty, on a few thousand
matches. Stage 2's shuffled copies show the same cost (their average for the 10-input profiles is about -0.5). A real
gain of that size reads as "no better than the odds".

Here every Stage 2 profile is scored again with a ridge-penalised walk-forward fit (ridge_walk): the base's log-odds
unpenalised, the inputs standardised on the training seasons and penalised. The penalty for season Y is the one whose
forecasts had the smallest log loss over the seasons before Y, each of those forecast by fits on the seasons before it
(the largest penalty when no season has been scored yet). Nothing about season Y is used to fit or choose. The
box-score profile of the UFC study's Stage D is scored the same way, as the control: the method should find the men's
known box-score lead. "Over the odds + box score" uses the ridge fit of the odds and the box-score profile as its base.

The same rows and seasons as the harness; the harness's unpenalised walk (stage4_rundown.walk) is recomputed beside it;
95% intervals clustered by calendar week (stage2_summary.clustered_interval).

Run:  ./python.sh src/eda/shot_level/stage3_profiles.py   (a few minutes)
Writes data/studies/shot_level/stage3_profiles.csv and stage3_profiles.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level.stage2_rundown import BOX_PROFILE  # noqa: E402
from src.eda.shot_level.stage2_summary import clustered_interval  # noqa: E402

LAMBDAS = (0.0, 10.0, 30.0, 100.0, 300.0, 1000.0, 3000.0, 10000.0, 30000.0, 100000.0)
WINDOWS = {"all": (C.EVAL_YEARS[0], C.EVAL_YEARS[-1]), "2022_26": (2022, 2026)}


def ridge_newton(Z: np.ndarray, y: np.ndarray, pen: np.ndarray, beta: np.ndarray, iters: int = 100) -> np.ndarray:
    """Logistic regression without an intercept, penalty pen_j beta_j^2 / 2 on each coefficient: Newton steps (a step
    longer than 4 is cut back), with the harness's tiny numerical ridge."""
    beta = beta.copy()
    eye = np.diag(pen + R.RIDGE)
    for _ in range(iters):
        p = expit(Z @ beta)
        g = Z.T @ (y - p) - (pen + R.RIDGE) * beta
        H = (Z.T * (p * (1 - p))) @ Z + eye
        step = np.linalg.solve(H, g)
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return beta


def ridge_walk(X: np.ndarray, base: np.ndarray, y: np.ndarray, year: np.ndarray, seasons: list[int],
               lambdas: tuple = LAMBDAS) -> dict:
    """Walk-forward by season over matches sorted by season: X (n, k) the inputs, base (n,) the base's log-odds. For
    season Y, every penalty is fitted on the seasons before Y; the forecast used is that of the penalty with the smallest
    log loss over the seasons already forecast. Returns per-match log losses of the forecast (llm) and of the base
    recalibrated as in stage4_rundown.walk (llb), the forecasts (p) and the penalties chosen."""
    n, k = X.shape
    L = len(lambdas)
    llm, llb, pm = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    betas = np.zeros((L, k + 1))
    bb = np.zeros((1, 1))
    cum, seen, chosen = np.zeros(L), False, {}
    for Y in seasons:
        lo, hi = np.searchsorted(year, Y, "left"), np.searchsorted(year, Y, "right")
        if hi == lo or lo < R.MIN_TRAIN:
            continue
        mu, sd = X[:lo].mean(axis=0), X[:lo].std(axis=0)
        use = sd > 1e-6                                   # an input with no spread in training is left out that season
        sdu = np.where(use, sd, 1.0)
        Ztr = np.column_stack([base[:lo], np.where(use, (X[:lo] - mu) / sdu, 0.0)])
        Zte = np.column_stack([base[lo:hi], np.where(use, (X[lo:hi] - mu) / sdu, 0.0)])
        ll_l = np.empty((L, hi - lo))
        p_l = np.empty((L, hi - lo))
        for j, lam in enumerate(lambdas):
            betas[j] = ridge_newton(Ztr, y[:lo], np.r_[0.0, np.full(k, lam)], betas[j])
            p_l[j] = expit(Zte @ betas[j])
            ll_l[j] = R.ll(p_l[j], y[lo:hi])
        j_star = int(np.argmin(cum)) if seen else L - 1
        llm[lo:hi], pm[lo:hi] = ll_l[j_star], p_l[j_star]
        chosen[int(Y)] = float(lambdas[j_star])
        cum += ll_l.sum(axis=1)
        seen = True
        bb = R.newton(base[None, :lo, None], y[:lo], bb)
        llb[lo:hi] = R.ll(expit(base[lo:hi] * bb[0, 0]), y[lo:hi])
    return {"llm": llm, "llb": llb, "p": pm, "chosen": chosen}


def harness_walk(X: np.ndarray, base: np.ndarray, y: np.ndarray, year: np.ndarray) -> dict:
    """The harness's unpenalised walk (stage4_rundown.walk) on the same rows, seasons 2013-2026."""
    w = R.walk(np.ascontiguousarray(np.column_stack([base, X])[None]), y, year, list(C.EVAL_YEARS), base)
    return {"llm": w["llm"][0], "llb": w["llb"]}


def summarise(d: np.ndarray, year: np.ndarray, week: np.ndarray) -> dict:
    out = {}
    for name, (a, b) in WINDOWS.items():
        m = np.isfinite(d) & (year >= a) & (year <= b)
        mean, lo, hi, G = clustered_interval(d[m], week[m])
        out.update({f"gain_{name}": mean, f"lo_{name}": lo, f"hi_{name}": hi, f"n_{name}": int(m.sum())})
    return out


def main() -> int:
    cat = [c for c in json.loads((S.OUT / "stage2_catalog.json").read_text(encoding="utf-8")) if c["family"] == "profile"]
    need = sorted({c for p in cat for c in p["inputs"]} | set(BOX_PROFILE))
    frame = pd.read_parquet(S.OUT / "stage2_frame.parquet",
                            columns=["match_id", "tour", "year", "evaluation", "a_won", "p_mkt", "p_elo"] + need)
    week = C.load_matches(["match_id", "tournament_date"]).set_index("match_id")["tournament_date"]
    frame["week"] = week.reindex(frame["match_id"]).dt.to_period("W-SUN").astype(str).to_numpy()
    rows, chosen = [], {}
    for t in C.TOURS:
        ft = frame[frame["tour"].eq(t)].reset_index(drop=True)
        assert (np.diff(ft["year"].to_numpy()) >= 0).all()
        y = ft["a_won"].to_numpy().astype(bool)
        yr = ft["year"].to_numpy()
        ev = ft["evaluation"].to_numpy().astype(bool)
        seasons = list(range(int(yr.min()) + 1, C.EVAL_YEARS[-1] + 1))
        bases = {"market": logit(np.clip(ft["p_mkt"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9)),
                 "elo": logit(np.clip(ft["p_elo"].to_numpy(dtype="float64"), 1e-9, 1 - 1e-9))}
        # the control first: the box-score profile; its ridge forecast is the base "odds + box score"
        Xb = ft[BOX_PROFILE].to_numpy(dtype="float64")
        for bname in ("market", "elo"):
            lb = bases[bname]
            ok = np.isfinite(lb) & np.isfinite(Xb).all(axis=1)
            ix = np.flatnonzero(ok)
            for method in ("harness", "ridge"):
                if method == "ridge":
                    w = ridge_walk(Xb[ix], lb[ix], y[ix], yr[ix], seasons)
                    pb = np.full(len(ft), np.nan)
                    pb[ix] = w["p"]
                    bases[f"{bname}+box"] = logit(np.clip(pb, 1e-9, 1 - 1e-9))
                    chosen[f"{t}|box|{bname}"] = w["chosen"]
                else:
                    w = harness_walk(Xb[ix], lb[ix], y[ix], yr[ix])
                d = w["llb"] - w["llm"]
                sc = ev[ix]
                rows.append({"tour": t, "profile": "box score (Stage D)", "form": "2-week", "inputs": len(BOX_PROFILE),
                             "base": bname, "method": method,
                             **summarise(d[sc], yr[ix][sc], ft["week"].to_numpy()[ix][sc])})
        S.log(f"  {t} box control: " + ", ".join(f"{r['base']} {r['method']} {r['gain_all']:+.2f}" for r in rows
                                                if r["tour"] == t))
        for p in [c for c in cat if c["tour"] == t]:
            X = ft[p["inputs"]].to_numpy(dtype="float64")
            for bname in ("market", "elo", "market+box"):
                lb = bases[bname]
                ok = np.isfinite(lb) & np.isfinite(X).all(axis=1)
                ix = np.flatnonzero(ok)
                for method in ("harness", "ridge"):
                    if method == "ridge":
                        w = ridge_walk(X[ix], lb[ix], y[ix], yr[ix], seasons)
                        chosen[f"{t}|{p['id']}|{p['form']}|{bname}"] = w["chosen"]
                    else:
                        w = harness_walk(X[ix], lb[ix], y[ix], yr[ix])
                    d = w["llb"] - w["llm"]
                    sc = ev[ix]
                    rows.append({"tour": t, "profile": p["id"].removeprefix("profile_"), "form": p["form"],
                                 "inputs": len(p["inputs"]), "base": bname, "method": method,
                                 **summarise(d[sc], yr[ix][sc], ft["week"].to_numpy()[ix][sc])})
            S.log(f"  {t} {p['id']} {p['form']}: " + ", ".join(
                f"{r['base']} {r['method']} {r['gain_all']:+.2f}" for r in rows
                if r["tour"] == t and r["profile"] == p["id"].removeprefix("profile_") and r["form"] == p["form"]))
    out = pd.DataFrame(rows)
    out.to_csv(S.OUT / "stage3_profiles.csv", index=False)
    (S.OUT / "stage3_profiles.json").write_text(json.dumps({"lambdas": LAMBDAS, "rows": rows, "chosen": chosen},
                                                           indent=1, default=float), encoding="utf-8")
    S.log(f"wrote stage3_profiles.csv ({len(out)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
