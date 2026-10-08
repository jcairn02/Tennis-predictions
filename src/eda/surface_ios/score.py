"""Score the surface-IOS study's TabPFN-3.5 fits under the locked plan (plan.py; docs/studies/surface_ios/strategy.md,
sections 5 and 7: the audit's changes).

Forecasts. For every arm, season and seed: the saved probabilities of the local fits (run_local.py: the open-weight
TabPFN-3.5 checkpoint on this machine's GPU, data/studies/surface_ios/local/), or of paid API fits where a slot has only
those (none were made), symmetrised over the two orientations (the mean of P(A | x) and 1 - P(A | x swapped)). An arm's
forecast is the mean of its four seeds' symmetrised probabilities.

Recalibration (the audit's must-fix 1: the local model is over-confident, so a raw comparison mixes information with
calibration). Every forecast column, per tour, gets one slope on its log-odds (no intercept: the forecasts are
antisymmetric), fitted on its own 2019-2021 forecasts:

    test seasons 2022-2026    the slope fitted on all three validation seasons
    validation 2019-2021      cross-fitted: each season scored with the slope fitted on the other two

The reference price is the closing odds recalibrated on each window's own training matches (one slope per tour), as
before. Comparisons are reported on recalibrated forecasts (metric "recal", primary) and raw ones ("raw").

Intervals: paired 95% intervals clustered in four-week blocks of tournament dates (calendar weeks as a sensitivity);
for arm against arm, also with the seeds' variance added (the audit's must-fix 2): SE^2 = SE_block^2 +
(s_arm^2 + s_base^2) / 4, s the SD over the four seeds of a single seed's mean log loss on the same matches. The
verdict of an arm-against-arm row uses the wider interval.

Writes data/studies/surface_ios/results.json, results.csv, residual_check.json and test_predictions.parquet.
Run: ./python.sh src/eda/surface_ios/score.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import guard as G  # noqa: E402
from src.eda.surface_ios import plan as PL  # noqa: E402
from src.eda.surface_ios import run_local as RL  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

UPLOADS = C.OUT / "uploads"
VAL = PL.PHASES["validation"]
EXTRA_PAIRS = [("snet1_perm", "snet1")]       # reporting only (not the locked plan): P1 against its own placebo


def zlogit(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), T.EPS, 1 - T.EPS))


def market(f: pd.DataFrame, year: int) -> np.ndarray:
    """The closing price recalibrated on the window's training matches: one slope per tour, no intercept."""
    out = np.full(len(f), np.nan)
    z = zlogit(f["p_mkt"])
    for tour in ("atp", "wta"):
        tr = ((f["year"] < year) & (f["tour"] == tour) & f["p_mkt"].notna()).to_numpy()
        te = ((f["year"] == year) & (f["tour"] == tour)).to_numpy()
        b, _ = T.fit_logistic(z[tr][:, None], f.loc[tr, "a_won"].to_numpy())
        out[te] = expit(b[0] * z[te])
    return out


def load_predictions() -> pd.DataFrame:
    manifest = json.loads((UPLOADS / "manifest.json").read_text(encoding="utf-8"))
    base = pd.read_parquet(C.OUT / "base_frame.parquet",
                           columns=["match_id", "tour", "year", "tournament_date", "a_won", "group", "surface_code",
                                    "p_mkt", "split"])
    parts = []
    for year in sorted({s["year"] for s in manifest["slots"].values()}):
        g = base[base["year"] == year].copy()
        g["p_market"] = market(base, year)[(base["year"] == year).to_numpy()]
        g["p_market_raw"] = g["p_mkt"]
        for slot, spec in manifest["slots"].items():
            if spec["year"] != year:
                continue
            ids = pd.read_parquet(UPLOADS / slot / "query_ids.parquet")
            local = RL.LOCAL / f"{slot}.npz"
            api = G.canonical_root() / slot / "predictions.npz"
            if local.exists():
                p_a = RL.load_local(slot, spec["input_fingerprint"], len(ids))
            elif api.exists():
                _, p_a, _, _ = G.load_predictions(api, None, len(ids))
            else:
                continue
            n = len(ids) // 2
            if not np.array_equal(ids["match_id"].to_numpy()[:n], g["match_id"].to_numpy()):
                raise RuntimeError(f"{slot}: query rows are not the season's matches in order")
            g[f"p_{spec['arm']}_s{spec['seed']}"] = T.symmetrize(p_a[:n], p_a[n:])
        parts.append(g)
    f = pd.concat(parts, ignore_index=True)
    for arm in PL.ARMS:
        cols = [f"p_{arm}_s{s}" for s in PL.SEEDS]
        if all(c in f for c in cols):
            f[f"p_{arm}"] = f[cols].mean(axis=1)
    return f


def recalibrate(f: pd.DataFrame) -> pd.DataFrame:
    """q_<name> for every p_<arm>[_s<k>] column: per tour, one slope fitted on the column's own validation forecasts
    (all three seasons for the test seasons; the other two for each validation season). NaN where the column lacks a
    validation season."""
    y = f["a_won"].to_numpy()
    year, tour = f["year"].to_numpy(), f["tour"].to_numpy()
    cols = [c for c in f.columns if c.startswith("p_") and c not in ("p_mkt", "p_market", "p_market_raw")]
    for c in cols:
        z = zlogit(f[c])
        q = np.full(len(f), np.nan)
        for t in ("atp", "wta"):
            val = (tour == t) & np.isin(year, VAL) & np.isfinite(z)
            if not all(((year == v) & val).any() for v in VAL):
                continue
            b, _ = T.fit_logistic(z[val][:, None], y[val])
            test = (tour == t) & ~np.isin(year, VAL)
            q[test] = expit(b[0] * z[test])
            for v in VAL:
                fit = val & (year != v)
                bb, _ = T.fit_logistic(z[fit][:, None], y[fit])
                tgt = (tour == t) & (year == v)
                q[tgt] = expit(bb[0] * z[tgt])
        f["q_" + c[2:]] = q
    return f


def block_compare(g: pd.DataFrame, b: str, m: str) -> dict:
    y = g["a_won"].to_numpy()
    return T.compare(T.ll(g[b].to_numpy(), y), T.ll(g[m].to_numpy(), y), g["tournament_date"].to_numpy())


def seed_var(g: pd.DataFrame, prefix: str, arm: str) -> float:
    """Variance of a four-seed mean's log loss from the seeds alone (milli^2): var over seeds of a single seed's mean
    log loss on these matches, divided by the number of seeds."""
    y = g["a_won"].to_numpy()
    vals = [1000 * T.ll(g[f"{prefix}_{arm}_s{k}"].to_numpy(), y).mean() for k in PL.SEEDS
            if f"{prefix}_{arm}_s{k}" in g]
    return float(np.var(vals, ddof=1) / len(vals)) if len(vals) > 1 else 0.0


def row(tour, window, metric, b, m, c, extra=None) -> dict:
    r = {"tour": tour, "window": window, "metric": metric, "base": b, "model": m, "matches": c["n"],
         "gain": c["gain"], "lo": c["lo"], "hi": c["hi"], "week_lo": c["week_lo"], "week_hi": c["week_hi"]}
    if extra:
        r.update(extra)
    lo, hi = r.get("lo_seed", r["lo"]), r.get("hi_seed", r["hi"])
    r["verdict"] = "tie" if lo <= 0 <= hi else (m if lo > 0 else b)
    return r


def compare_rows(g: pd.DataFrame, tour: str, window: str) -> list[dict]:
    out = []
    arms = [a for a in PL.ARMS if f"p_{a}" in g and g[f"p_{a}"].notna().all()]
    for metric, prefix in (("recal", "q"), ("raw", "p")):
        mk = "p_market"
        for a in arms:                                           # each arm against the price
            col = f"{prefix}_{a}"
            if col in g and g[col].notna().all():
                out.append(row(tour, window, metric, "market", a, block_compare(g, mk, col)))
        for b, m in PL.COMPARISONS + EXTRA_PAIRS:               # arm against arm, seeds' variance added
            cb, cm = f"{prefix}_{b}", f"{prefix}_{m}"
            if not (cb in g and cm in g and g[[cb, cm]].notna().all().all()):
                continue
            c = block_compare(g, cb, cm)
            tq = student_t.ppf(0.975, c["blocks"] - 1)
            se_block = (c["hi"] - c["lo"]) / (2 * tq)
            vs = seed_var(g, prefix, b) + seed_var(g, prefix, m)
            se = np.sqrt(se_block ** 2 + vs)
            out.append(row(tour, window, metric, b, m, c, {"se_block": se_block, "se_seed": float(np.sqrt(vs)),
                                                           "lo_seed": c["gain"] - tq * se,
                                                           "hi_seed": c["gain"] + tq * se}))
        for a in arms:                                           # seed against seed (single seeds): the noise
            for k in PL.SEEDS[1:]:
                cb, cm = f"{prefix}_{a}_s{PL.SEEDS[0]}", f"{prefix}_{a}_s{k}"
                if cb in g and cm in g and g[[cb, cm]].notna().all().all():
                    out.append(row(tour, window, metric, cb[2:], cm[2:], block_compare(g, cb, cm)))
    return out


def residual_check(f: pd.DataFrame) -> dict:
    """The audit's linear check (SHOULD 2): logit p = a logit(q_base) + b dnet_spw per tour, fitted on 2019-2021 with
    the cross-fitted recalibrated base, scored on 2022-2026 against the recalibrated base (positive = the nudge helps)."""
    if "q_base" not in f:
        return {}
    d = pd.read_parquet(PL.arm_path("snet1"), columns=["match_id", "in_dnet_spw"])
    g = f.merge(d, on="match_id", how="left", validate="one_to_one")
    y = g["a_won"].to_numpy()
    z0, x = zlogit(g["q_base"]), g["in_dnet_spw"].to_numpy(dtype=float)
    p = np.full(len(g), np.nan)
    coef = {}
    for t in ("atp", "wta"):
        val = (g["tour"] == t).to_numpy() & np.isin(g["year"], VAL)
        test = (g["tour"] == t).to_numpy() & ~np.isin(g["year"], VAL)
        b, se = T.fit_logistic(np.column_stack([z0[val], x[val]]), y[val])
        p[test] = expit(b[0] * z0[test] + b[1] * x[test])
        coef[t] = {"a": float(b[0]), "b": float(b[1]), "b_z": float(b[1] / se[1])}
    g["p_resid"] = p
    out = {"coefficients_2019_2021": coef, "comparisons": []}
    for tour in ("atp", "wta", "both"):
        h = g if tour == "both" else g[g["tour"] == tour]
        h = h[~np.isin(h["year"], VAL)]
        c = block_compare(h, "q_base", "p_resid")
        out["comparisons"].append({"tour": tour, "window": "2022-2026", **c})
    return out


def main() -> int:
    f = recalibrate(load_predictions())
    windows = []
    for years in PL.PHASES.values():
        windows += [(f"{years[0]}-{years[-1]}", years[0], years[-1])] + [(str(y), y, y) for y in years]
    windows += [("2022-2024", 2022, 2024), ("2025-2026", 2025, 2026)]   # the audit's split for the 2025 data change
    rows = []
    for tour in ("atp", "wta", "both"):
        g0 = f if tour == "both" else f[f["tour"] == tour]
        for label, lo, hi in windows:
            g = g0[g0["year"].between(lo, hi)]
            if not g.empty:
                rows += compare_rows(g, tour, label)
    # the pre-declared subgroups (subgroups.py): surface and early in the surface season, arm against arm
    sub = pd.read_parquet(C.OUT / "subgroups.parquet", columns=["match_id", "surface", "early_season"])
    fs = f.merge(sub, on="match_id", how="left", validate="many_to_one")
    for tour in ("atp", "wta", "both"):
        g0 = fs if tour == "both" else fs[fs["tour"] == tour]
        for label, lo, hi in (("2019-2021", 2019, 2021), ("2022-2026", 2022, 2026)):
            g1 = g0[g0["year"].between(lo, hi)]
            groups = [(f"surface={s}", (g1["surface"] == s).to_numpy()) for s in ("Hard", "Clay", "Grass")]
            groups += [("early_season", g1["early_season"].to_numpy(dtype=bool)),
                       ("later_season", ~g1["early_season"].to_numpy(dtype=bool))]
            for gname, m in groups:
                g = g1[m]
                for b, mdl in PL.COMPARISONS:
                    cb, cm = f"q_{b}", f"q_{mdl}"
                    if g.empty or cb not in g or cm not in g or g[[cb, cm]].isna().any().any():
                        continue
                    rows.append(row(tour, f"{label} | {gname}", "recal", b, mdl, block_compare(g, cb, cm)))
    R = pd.DataFrame(rows)
    names = [c[2:] for c in f.columns if c[:2] in ("p_", "q_") and c != "p_mkt"]
    ll = {}
    for tour, g in list(f.groupby("tour")) + [("both", f)]:
        ll[tour] = {}
        for w, lo, hi in windows:
            h = g[g["year"].between(lo, hi)]
            ll[tour][w] = {pre + nm: float(T.ll(h[pre + nm].to_numpy(), h["a_won"].to_numpy()).mean())
                           for pre in ("p_", "q_") for nm in {n for n in names}
                           if pre + nm in h and h[pre + nm].notna().all() and len(h)}
    res = {"key": "milli-log-loss; positive = the second-named forecast (model) has the lower log loss (better); a 95% "
                  "interval spanning 0 is a tie; arm-against-arm rows carry a wider interval with the seeds' variance "
                  "(lo_seed, hi_seed), used for the verdict", "plan_sha256": PL.plan_hash(),
           "recalibration": "per forecast column and tour, one slope on its log-odds fitted on its 2019-2021 forecasts "
                            "(cross-fitted by season inside 2019-2021)", "log_loss": ll, "comparisons": R.to_dict("records")}
    C.jdump(res, C.OUT / "results.json")
    R.to_csv(C.OUT / "results.csv", index=False)
    C.jdump(residual_check(f), C.OUT / "residual_check.json")
    f.to_parquet(C.OUT / "test_predictions.parquet", index=False)
    show = R[(R["base"] == "base") & R["window"].isin(["2019-2021", "2022-2026"])]
    with pd.option_context("display.width", 250, "display.max_rows", 400):
        print(show[["tour", "window", "metric", "model", "matches", "gain", "lo_seed", "hi_seed", "verdict"]]
              .round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
