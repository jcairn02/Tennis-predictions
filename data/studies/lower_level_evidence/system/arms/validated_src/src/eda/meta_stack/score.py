"""Score the meta-model against the current best on 2022-2026 (the plan: docs/studies/meta_stack/README.md, "The plan,
fixed before the test"). Every meta-learner is refitted for each test season, per tour, on out-of-sample forecasts of
earlier seasons only (meta.walk_forward):

    best           the current best: one slope on the with-odds TabPFN's log-odds, fitted on every out-of-sample
                   season from 2019 to the season before (docs/studies/surface_ios/README.md: +1.30 over the close)
    S2             the owner's meta-model (closing line + no-odds TabPFN; their log-odds difference drops out), on the
                   window design.py chose (S2_WINDOW)
    S3lit          S2 with the difference kept as a literal third column (rank 2: the same forecasts)
    S3p, S3q       S2 plus the difference entering non-linearly (probability scale; signed square)
    E1, E2         the current best plus the no-odds forecast; the closing line and the current best with separate
                   weights (the current best's window)
    best_w, S2_19  sensitivities: the current best on S2's window; S2 on the current best's window
    market         the reference price: the closing line recalibrated on each window's training matches (2013 to the
                   season before), one slope per tour (the surface-IOS study's reference)
    ceiling        a diagnostic, not a forecast: S2 with weights fitted on the test matches themselves

Each meta-model is also fitted and scored on each seed's forecasts alone, which gives the seeds' variance (score.py of
the surface-IOS study): for model against model, SE^2 = SE_block^2 + (s_a^2 + s_b^2) / 4, s the SD over the four seeds
of a single seed's mean log loss (conservative where two forecasts share a model's seeds); the verdict uses that wider
interval. Intervals are paired, clustered in four-week blocks of tournament dates.

Writes data/studies/meta_stack/results.csv, results.json, coefficients.csv and test_predictions.parquet.
Run: ./python.sh src/eda/meta_stack/score.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.meta_stack import common as C  # noqa: E402
from src.eda.meta_stack import meta as M  # noqa: E402
from src.eda.surface_ios import common as SC  # noqa: E402  (jdump)
from src.eda.tabpfn_thinking import common as T  # noqa: E402

S2_WINDOW = "from2014"            # chosen by design.py (docs/studies/meta_stack/README.md), before this script ran
BEST_WINDOW = f"from{C.CURRENT_BEST_FROM}"

# (name, spec, window, which forecasts: "mean" = four-seed means, k = seed k only)
FORECASTS = [("best", "best", BEST_WINDOW), ("S2", "S2", S2_WINDOW), ("S3lit", "S3lit", S2_WINDOW),
             ("S3p", "S3p", S2_WINDOW), ("S3q", "S3q", S2_WINDOW), ("E1", "E1", BEST_WINDOW),
             ("E2", "E2", BEST_WINDOW), ("best_w", "best", S2_WINDOW), ("S2_19", "S2", BEST_WINDOW)]
SEEDED = tuple(name for name, _, _ in FORECASTS)      # every meta-model also from each seed's forecasts alone
PRIMARY = ("best", "S2")
PAIRS = [PRIMARY, ("market", "S2"), ("market", "best"), ("S2", "S3lit"), ("S2", "S3p"), ("S2", "S3q"),
         ("best", "S3p"), ("best", "S3q"), ("best", "E1"), ("best", "E2"), ("best", "best_w"), ("best_w", "S2"),
         ("S2", "S2_19"), ("market", "E1"), ("market", "E2")]
WINDOWS = [("2022-2026", 2022, 2026)] + [(str(y), y, y) for y in C.TEST] + [("2022-2024", 2022, 2024),
                                                                            ("2025-2026", 2025, 2026)]


def zs(d: pd.DataFrame, seed: str = "") -> M.Z:
    sfx = f"_s{seed}" if seed != "" else ""
    return {"mkt": C.zlogit(d["p_mkt"]), "noodds": C.zlogit(d[f"p_noodds{sfx}"]), "base": C.zlogit(d[f"p_base{sfx}"])}


def market(frame: pd.DataFrame, f: pd.DataFrame) -> np.ndarray:
    """The reference price for f's rows: per test season and tour, the closing line with one slope fitted on every
    frame match of 2013 to the season before (surface_ios/score.py: market)."""
    out = np.full(len(f), np.nan)
    zf, zt = C.zlogit(frame["p_mkt"]), C.zlogit(f["p_mkt"])
    for year in C.TEST:
        for tour in C.TOURS:
            tr = ((frame["year"] < year) & (frame["tour"] == tour)).to_numpy()
            te = ((f["year"] == year) & (f["tour"] == tour)).to_numpy()
            b, _ = T.fit_logistic(zf[tr][:, None], frame.loc[tr, "a_won"].to_numpy(float))
            out[te] = expit(b[0] * zt[te])
    return out


def forecasts(wf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    y, year, tour = wf["a_won"].to_numpy(float), wf["year"].to_numpy(), wf["tour"].to_numpy()
    test = wf["year"].isin(C.TEST).to_numpy()
    out = wf.loc[test, ["match_id", "tour", "year", "tournament_date", "a_won", "p_mkt"]].reset_index(drop=True)
    coefs = []
    for name, spec, win in FORECASTS:
        for seed in [""] + ([str(k) for k in C.SEEDS] if name in SEEDED else []):
            p, cf = M.walk_forward(spec, zs(wf, seed), y, year, tour, C.TEST, lambda t, w=win: M.window(w, t))
            out[f"p_{name}" + (f"_s{seed}" if seed else "")] = p[test]
            if not seed:
                coefs += [{"forecast": name, "spec": spec, "window": win, "season": s, "tour": tr,
                           "n": v["n"], **{f"b{i}": b for i, b in enumerate(v["beta"])},
                           **{f"se{i}": e for i, e in enumerate(v["se"])}} for (s, tr), v in cf.items()]
    return out, pd.DataFrame(coefs)


def seed_var(g: pd.DataFrame, name: str) -> float:
    """Variance (milli^2) of a four-seed forecast's mean log loss from the seeds alone."""
    cols = [f"p_{name}_s{k}" for k in C.SEEDS]
    if not all(c in g for c in cols):
        return 0.0
    y = g["a_won"].to_numpy()
    vals = [1000 * T.ll(g[c].to_numpy(), y).mean() for c in cols]
    return float(np.var(vals, ddof=1) / len(vals))


def compare(g: pd.DataFrame, a: str, b: str) -> dict:
    y = g["a_won"].to_numpy()
    c = T.compare(T.ll(g[f"p_{a}"].to_numpy(), y), T.ll(g[f"p_{b}"].to_numpy(), y), g["tournament_date"].to_numpy())
    tq = student_t.ppf(0.975, c["blocks"] - 1)
    se_block = (c["hi"] - c["lo"]) / (2 * tq)
    vs = seed_var(g, a) + seed_var(g, b)
    se = float(np.sqrt(se_block ** 2 + vs))
    lo, hi = c["gain"] - tq * se, c["gain"] + tq * se
    verdict = "tie" if lo <= 0 <= hi else (b if lo > 0 else a)
    return {"base": a, "model": b, "matches": c["n"], "gain": c["gain"], "lo_block": c["lo"], "hi_block": c["hi"],
            "se_block": se_block, "se_seed": float(np.sqrt(vs)), "lo": lo, "hi": hi, "week_lo": c["week_lo"],
            "week_hi": c["week_hi"], "verdict": verdict}


def ceiling(f: pd.DataFrame, wf: pd.DataFrame) -> list[dict]:
    """A diagnostic, not a forecast: S2 with its weights fitted on the test matches themselves (per tour over
    2022-2026, and per tour and season), against the honest current best. No choice of the meta-learner's data can do
    better than these weights, so a gap left here is not a data-split problem."""
    g = f.merge(wf[["match_id", "p_noodds", "p_base"]], on="match_id", validate="one_to_one")
    y = g["a_won"].to_numpy(float)
    z = zs(g)
    out = []
    for label, by in (("per tour, 2022-2026", ["tour"]), ("per tour and season", ["tour", "year"])):
        p = np.full(len(g), np.nan)
        for _, rows in g.groupby(by).indices.items():
            k = np.zeros(len(g), bool)
            k[rows] = True
            b, _ = M.fit("S2", M.take(z, k), y[k])
            p[k] = M.predict("S2", M.take(z, k), b)
        g["p_ceiling"] = p
        for tour in ("atp", "wta", "both"):
            h = g if tour == "both" else g[g["tour"] == tour]
            yy = h["a_won"].to_numpy()
            c = T.compare(T.ll(h["p_best"].to_numpy(), yy), T.ll(h["p_ceiling"].to_numpy(), yy),
                          h["tournament_date"].to_numpy())
            out.append({"weights_fitted": label, "tour": tour, "base": "best", "model": "S2 in-sample", **c})
    return out


def main() -> int:
    if not S2_WINDOW:
        raise SystemExit("set S2_WINDOW from design.py's result, and record it in the plan, before scoring the test")
    wf = pd.read_parquet(C.OUT / "walkforward.parquet")
    frame = pd.read_parquet(C.SIOS / "base_frame.parquet", columns=["match_id", "tour", "year", "a_won", "p_mkt"])
    f, coefs = forecasts(wf)
    f["p_market"] = market(frame, f)
    rows = []
    for tour in ("atp", "wta", "both"):
        g0 = f if tour == "both" else f[f["tour"] == tour]
        for label, lo, hi in WINDOWS:
            g = g0[g0["year"].between(lo, hi)]
            rows += [{"tour": tour, "window": label, **compare(g, a, b)} for a, b in PAIRS]
    R = pd.DataFrame(rows)
    ll = {tour: {label: {c[2:]: float(T.ll(h[c].to_numpy(), h["a_won"].to_numpy()).mean())
                         for c in f.columns if c.startswith("p_") and c != "p_mkt"}
                 for label, lo, hi in WINDOWS for h in [g[g["year"].between(lo, hi)]]}
          for tour, g in list(f.groupby("tour")) + [("both", f)]}
    R.to_csv(C.OUT / "results.csv", index=False)
    coefs.to_csv(C.OUT / "coefficients.csv", index=False)
    f.to_parquet(C.OUT / "test_predictions.parquet", index=False)
    SC.jdump({"key": "milli-log-loss per match; gain = log loss of 'base' minus log loss of 'model': positive = the "
                     "model (second named) is better; lo/hi: 95% interval with the seeds' variance, used for the "
                     "verdict; lo_block/hi_block: four-week blocks only; an interval spanning 0 is a tie",
              "s2_window": S2_WINDOW, "best_window": BEST_WINDOW, "primary": list(PRIMARY), "log_loss": ll,
              "comparisons": R.to_dict("records"), "coefficients": coefs.to_dict("records"),
              "ceiling_in_sample_weights": ceiling(f, wf)},
             C.OUT / "results.json")
    show = R[R["window"] == "2022-2026"]
    with pd.option_context("display.width", 220, "display.max_rows", 200):
        print(show[["tour", "base", "model", "matches", "gain", "lo", "hi", "verdict"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
