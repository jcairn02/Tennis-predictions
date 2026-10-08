"""Score the leak-proof refit against the original fit and the recalibrated closing odds, on the same test matches.

Written before the paid call. The forecasts, all on the original study's test matches with odds (main tour 2022-2026):

    market      the closing odds recalibrated on the training matches (the original study's p_market)
    original    the original TabPFN-3.5-Thinking fit (src/eda/tabpfn_thinking/), symmetrised
    leakproof   this study's single fit: the same rows, configuration and inputs, the IOS inputs rebuilt on the
                leak-proof timeline, symmetrised the same way (the mean of P(A | x) and 1 - P(A | x swapped))

Gains are milli-log-loss, positive = the second-named forecast is better, with paired 95% cluster intervals over
four-week blocks of tournament dates (the original study's method; calendar weeks as a sensitivity), per tour and both
tours, for 2022-2026 and each season. Agreement: how far the two fits' forecasts differ match by match.

Writes data/studies/tabpfn_leakproof/results.json, results.csv and test_predictions.parquet.
Run: ./python.sh src/eda/tabpfn_leakproof/score.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_leakproof import common as C  # noqa: E402
from src.eda.tabpfn_leakproof import guard as G  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

PAIRS = [("market", "original"), ("market", "leakproof"), ("original", "leakproof")]
WINDOWS = [("2022-2026", 2022, 2026)] + [(str(y), y, y) for y in range(2022, 2027)]


def load() -> pd.DataFrame:
    _, _, X_query, ids, _ = C.load_upload()
    _, p_a, metadata, _ = G.load_predictions(C.THINKING / "predictions.npz", None, len(ids))
    n = len(ids) // 2
    new = pd.DataFrame({"match_id": ids["match_id"].to_numpy()[:n], "p_leakproof_orig": p_a[:n],
                        "p_leakproof_flip": p_a[n:], "p_leakproof": T.symmetrize(p_a[:n], p_a[n:])})
    old = pd.read_parquet(T.OUT / "test_predictions.parquet",
                          columns=["match_id", "tour", "year", "group", "tournament_date", "a_won", "p_market",
                                   "p_market_raw", "p_tabpfn"])
    f = old.merge(new, on="match_id", how="inner", validate="one_to_one")
    if len(f) != n or f["p_tabpfn"].isna().any():
        raise RuntimeError("the refit's query rows are not the original fit's test matches")
    return f.rename(columns={"p_tabpfn": "p_original"})


def compare(f: pd.DataFrame, base: str, model: str) -> dict:
    y = f["a_won"].to_numpy()
    return T.compare(T.ll(f[f"p_{base}"].to_numpy(), y), T.ll(f[f"p_{model}"].to_numpy(), y),
                     f["tournament_date"].to_numpy())


def agreement(f: pd.DataFrame) -> dict:
    a, b = f["p_original"].to_numpy(), f["p_leakproof"].to_numpy()
    la, lb = logit(np.clip(a, T.EPS, 1 - T.EPS)), logit(np.clip(b, T.EPS, 1 - T.EPS))
    d = np.abs(a - b)
    gap = np.abs(f["p_leakproof_orig"].to_numpy() - (1 - f["p_leakproof_flip"].to_numpy()))
    return {"matches": int(len(f)), "log_odds_correlation": float(np.corrcoef(la, lb)[0, 1]),
            "mean_abs_prob_change": float(d.mean()), "p90_abs_prob_change": float(np.quantile(d, 0.9)),
            "max_abs_prob_change": float(d.max()),
            "favourite_changes": int(((a > 0.5) != (b > 0.5)).sum()),
            "leakproof_orientation_gap_mean": float(gap.mean())}


def main() -> int:
    f = load()
    rows = []
    for tour in ("atp", "wta", "both"):
        g0 = f if tour == "both" else f[f["tour"] == tour]
        for label, lo, hi in WINDOWS:
            g = g0[g0["year"].between(lo, hi)]
            if g.empty:
                continue
            for base, model in PAIRS:
                c = compare(g, base, model)
                rows.append({"tour": tour, "window": label, "base": base, "model": model, "matches": c["n"],
                             "gain": c["gain"], "lo": c["lo"], "hi": c["hi"], "week_lo": c["week_lo"],
                             "week_hi": c["week_hi"]})
    R = pd.DataFrame(rows)
    ll = {tour: {name: float(T.ll(g[f"p_{name}"].to_numpy(), g["a_won"].to_numpy()).mean())
                 for name in ("market_raw", "market", "original", "leakproof")}
          for tour, g in list(f.groupby("tour")) + [("both", f)]}
    res = {"key": "milli-log-loss; positive = the second-named forecast has the lower log loss (better); a 95% "
                  "interval spanning 0 is a tie", "log_loss": ll, "comparisons": R.to_dict("records"),
           "agreement": {tour: agreement(g) for tour, g in list(f.groupby("tour")) + [("both", f)]}}
    C.write_json(C.OUT / "results.json", res)
    R.to_csv(C.OUT / "results.csv", index=False)
    f.to_parquet(C.OUT / "test_predictions.parquet", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(R[R["window"].isin(["2022-2026", "2026"])].round(2).to_string(index=False))
        print(pd.DataFrame(res["agreement"]).round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
