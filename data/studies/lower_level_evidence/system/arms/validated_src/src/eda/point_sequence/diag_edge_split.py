"""Diagnostic I1, fixed contrasts: does the model's edge over the close differ by the state players bring from their
previous match? Discovery 2015-2021, replication 2022-2024; 2025-2026 stays closed.

Forecasts: the meta-stack study's walk-forward forecasts of the 54-input model (data/studies/meta_stack/
walkforward.parquet, `p_base`: local TabPFN-3.5, seeds averaged, trained on every earlier season) and the de-vigged
average closing probability `p_mkt`. Both are recalibrated prequentially, one logistic slope per tour on the log-odds
(no intercept), fitted on every earlier season from 2014 (the model) and the same for the market, so each season is
scored with constants that never saw it. The men's 2018 season has no odds and is skipped.

Six contrasts, fixed before this script ran on 2015-2021 (definitions as in diag_edge_location.py, which looked at
2022-2024 first; that window is therefore not a clean replication for those two splits):
    C1 both players' first match at the event  minus  both players in a later round
    C2 smaller rest of the two > 7 days          minus  <= 1 day
    C3 neither previous match went the distance  minus  at least one went to a deciding set
    C4 early rounds (R128-R32, round robin)      minus  R16 and later
    C5 Grand Slams                               minus  other levels
    C6 men                                       minus  women
Gain per match = log loss of the recalibrated close minus that of the recalibrated model (positive = model better);
a contrast is the difference of the two groups' mean gains (milli-log-loss), with a 95% interval from a bootstrap over
four-week blocks of tournament dates, and a two-sided bootstrap p-value; Holm across the six in each window.

    ./python.sh src/eda/point_sequence/diag_edge_split.py
Writes data/studies/point_sequence/diag_edge_split.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import diag_edge_location as D  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

WF = ROOT / "data" / "studies" / "meta_stack" / "walkforward.parquet"
WINDOWS = {"discovery 2015-2021": (2015, 2021), "replication 2022-2024": (2022, 2024)}
B = 4000


def slope(x: np.ndarray, y: np.ndarray) -> float:
    beta, _ = T.fit_logistic(x[:, None], y)
    return float(beta[0])


def prequential(f: pd.DataFrame, col: str) -> np.ndarray:
    """Recalibrate `col` season by season: one slope per tour on logit, fitted on every earlier season."""
    out = np.full(len(f), np.nan)
    z = logit(np.clip(f[col].to_numpy(), T.EPS, 1 - T.EPS))
    y = f["a_won"].astype(int).to_numpy()
    for tour in f["tour"].unique():
        for yr in sorted(f["year"].unique()):
            now = ((f["tour"] == tour) & (f["year"] == yr)).to_numpy()
            past = ((f["tour"] == tour) & (f["year"] < yr)).to_numpy()
            if now.any() and past.sum() > 1000:
                out[now] = expit(slope(z[past], y[past]) * z[now])
    return out


def contrasts(f: pd.DataFrame) -> list[tuple[str, np.ndarray, np.ndarray]]:
    k = lambda c: f[c].astype(object).fillna("unknown").to_numpy()  # noqa: E731
    return [
        ("C1 first at event minus later round", k("later_rounds") == "both first at event",
         k("later_rounds") == "both later round"),
        ("C2 rest >7 days minus <=1 day", k("min_rest") == ">7 days", k("min_rest") == "<=1 day"),
        ("C3 no deciding set minus a deciding set", k("prev_decider_any") == "no deciding set",
         k("prev_decider_any") == "a deciding set"),
        ("C4 early rounds minus R16 and later", k("round_group") == "early rounds (R128-R32, RR)",
         k("round_group") == "R16 and later"),
        ("C5 Grand Slams minus other levels", k("level") == "GS", k("level") != "GS"),
        ("C6 men minus women", k("tour") == "atp", k("tour") == "wta"),
    ]


def holm(p: np.ndarray) -> np.ndarray:
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def main() -> int:
    wf = pd.read_parquet(WF, columns=["match_id", "tour", "year", "tournament_date", "a_won", "p_mkt", "p_base"])
    wf = wf[wf["p_mkt"].notna() & wf["p_base"].notna()].reset_index(drop=True)
    wf["p_model"] = prequential(wf, "p_base")
    wf["p_market"] = prequential(wf, "p_mkt")
    rows = []
    rng = np.random.default_rng(20261006)
    for wname, (lo_y, hi_y) in WINDOWS.items():
        f = wf[wf["year"].between(lo_y, hi_y) & wf["p_model"].notna() & wf["p_market"].notna()].reset_index(drop=True)
        f = D.match_states(f.rename(columns={"year": "season"}).assign(debut_season=False)).rename(
            columns={"season": "year"})
        y = f["a_won"].astype(int).to_numpy()
        d = 1000 * (T.ll(f["p_market"].to_numpy(), y) - T.ll(f["p_model"].to_numpy(), y))
        blk = T.blocks(f["tournament_date"].to_numpy(), 28)
        ub = np.unique(blk)
        idx = {b: np.flatnonzero(blk == b) for b in ub}
        overall = T.compare(T.ll(f["p_market"].to_numpy(), y), T.ll(f["p_model"].to_numpy(), y),
                            f["tournament_date"].to_numpy())
        rows.append({"window": wname, "contrast": "overall gain (not a contrast)", "n1": overall["n"], "n2": 0,
                     "g1": overall["gain"], "g2": np.nan, "diff": overall["gain"], "lo": overall["lo"],
                     "hi": overall["hi"], "p": np.nan})
        draws = [np.concatenate([idx[b] for b in rng.choice(ub, len(ub), replace=True)]) for _ in range(B)]
        for name, m1, m2 in contrasts(f):
            obs = d[m1].mean() - d[m2].mean()
            bs = np.array([d[ii[m1[ii]]].mean() - d[ii[m2[ii]]].mean() for ii in draws])
            p = min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))
            rows.append({"window": wname, "contrast": name, "n1": int(m1.sum()), "n2": int(m2.sum()),
                         "g1": d[m1].mean(), "g2": d[m2].mean(), "diff": obs, "lo": np.percentile(bs, 2.5),
                         "hi": np.percentile(bs, 97.5), "p": p})
    R = pd.DataFrame(rows)
    R["p_holm"] = np.nan
    for w in WINDOWS:
        m = (R["window"] == w) & R["p"].notna()
        R.loc[m, "p_holm"] = holm(R.loc[m, "p"].to_numpy())
    R["verdict"] = np.where(R["lo"] > 0, "first group better", np.where(R["hi"] < 0, "second group better", "tie"))
    R.loc[R["contrast"].str.startswith("overall"), "verdict"] = np.where(
        R.loc[R["contrast"].str.startswith("overall"), "lo"] > 0, "model better", "tie")
    D.OUT.mkdir(parents=True, exist_ok=True)
    R.to_csv(D.OUT / "diag_edge_split.csv", index=False)
    with pd.option_context("display.width", 220):
        print("milli-log-loss; gains positive = model better than the recalibrated close; diff = first group's gain "
              "minus second's")
        print(R.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
