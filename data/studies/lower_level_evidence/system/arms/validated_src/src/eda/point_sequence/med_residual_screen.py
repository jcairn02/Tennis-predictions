"""E1 follow-up, registered here before it ran: the residual screen of the WTA medical-event signal.

The mechanism gate (med_estimate.py) passed on one cell: a physio treatment in a player's previous logged match
(TREATED) roughly doubles her chance of retiring or giving a walkover in the next match. This screen asks whether that
reaches the match result BEYOND what the model and the closing price already say, on the women's main-tour matches of
the model frame.

Registration (fixed before the first run):
* Matches: women's model-frame matches (main tour, closing odds) whose date falls in discovery (4 Jun 2019 - 2021) or
  replication (2022-2024). 2025-2026 is a closed holdout and is not read.
* Exposure per side: TREATED in that player's previous match, from med_pairs.parquet's primary pairs (previous match
  logged, next match within 21 days, the previous match not her own retirement). A side without such a pair counts 0
  and is flagged unlogged. x = TREATED_A - TREATED_B (antisymmetric). Sensitivity: both sides logged.
* Benchmarks: the 54-input model's walk-forward forecast (meta-stack) and the closing price, each recalibrated season by
  season with one slope per tour fitted on earlier seasons only (as diag_edge_split.py).
* Statistic: beta in logistic(a_won) = offset(logit benchmark) + beta * x, no intercept; negative beta = a treated
  player wins less often than the benchmark says. Wald 95% interval; the four-week-block bootstrap as a check.
* Pass: beta < 0 with the interval excluding 0 in discovery against the model, and the same sign in replication.
  Power is stated before reading beta: the screen detects only shifts of roughly 0.15-0.2 in log-odds on the treated
  side, so a tie bounds the effect, it does not close it.

Writes data/studies/point_sequence/med_residual_screen.json.
    ./python.sh src/eda/point_sequence/med_residual_screen.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import diag_edge_split as S  # noqa: E402
from src.eda.predictability_diagnostic import common as PD  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = ROOT / "data" / "studies" / "point_sequence"
WINDOWS = {"discovery": ("2019-06-04", "2021-12-31"), "replication": ("2022-01-01", "2024-12-31")}


def exposures() -> pd.DataFrame:
    p = pd.read_parquet(OUT / "med_pairs.parquet",
                        columns=["player_id", "n_match_id", "logged", "next_le21", "own_ret", "treated", "next_holdout"])
    p = p[p["logged"] & p["next_le21"].fillna(False) & ~p["own_ret"] & ~p["next_holdout"].fillna(False)]
    p = p.dropna(subset=["n_match_id"]).drop_duplicates(["n_match_id", "player_id"])
    return p.rename(columns={"n_match_id": "match_id"})[["match_id", "player_id", "treated"]]


def frame() -> pd.DataFrame:
    wf = pd.read_parquet(S.WF, columns=["match_id", "tour", "year", "tournament_date", "a_won", "p_mkt", "p_base"])
    wf = wf[wf["p_mkt"].notna() & wf["p_base"].notna()].reset_index(drop=True)
    wf["p_model"] = S.prequential(wf, "p_base")
    wf["p_market"] = S.prequential(wf, "p_mkt")
    f = wf[(wf["tour"] == "wta") & wf["p_model"].notna() & wf["p_market"].notna()].copy()
    m = PD.load_matches(["match_id", "player_a_id", "player_b_id"])
    tm = pd.read_parquet(S.D.TIMING, columns=["match_id", "obs"])
    f = f.merge(m, on="match_id", how="left").merge(tm, on="match_id", how="left")
    f["day"] = pd.to_datetime(f["obs"], unit="D")
    e = exposures()
    for side in ("a", "b"):
        f = f.merge(e.rename(columns={"player_id": f"player_{side}_id", "treated": f"treated_{side}"}),
                    on=["match_id", f"player_{side}_id"], how="left")
        f[f"logged_{side}"] = f[f"treated_{side}"].notna()
        f[f"treated_{side}"] = f[f"treated_{side}"].fillna(False).astype(bool)
    f["x"] = f["treated_a"].astype(int) - f["treated_b"].astype(int)
    return f


def fit(g: pd.DataFrame, bench: str, rng: np.random.Generator) -> dict:
    y = g["a_won"].astype(int).to_numpy()
    off = logit(np.clip(g[bench].to_numpy(), T.EPS, 1 - T.EPS))
    x = g["x"].to_numpy(dtype=float)
    # Newton on beta with the benchmark as offset
    beta = 0.0
    for _ in range(50):
        p = 1 / (1 + np.exp(-(off + beta * x)))
        g1, h = np.sum(x * (y - p)), np.sum(x * x * p * (1 - p))
        if h <= 0:
            break
        step = g1 / h
        beta += step
        if abs(step) < 1e-10:
            break
    p = 1 / (1 + np.exp(-(off + beta * x)))
    se = 1 / np.sqrt(np.sum(x * x * p * (1 - p))) if np.any(x != 0) else np.nan
    blk = T.blocks(g["tournament_date"].to_numpy(), 28)
    ub = np.unique(blk)
    idx = {b: np.flatnonzero(blk == b) for b in ub}
    boots = []
    for _ in range(1000):
        ii = np.concatenate([idx[b] for b in rng.choice(ub, len(ub), replace=True)])
        b0 = 0.0
        for _ in range(30):
            pp = 1 / (1 + np.exp(-(off[ii] + b0 * x[ii])))
            hh = np.sum(x[ii] ** 2 * pp * (1 - pp))
            if hh <= 0:
                break
            st = np.sum(x[ii] * (y[ii] - pp)) / hh
            b0 += st
            if abs(st) < 1e-8:
                break
        boots.append(b0)
    lo_b, hi_b = np.percentile(boots, [2.5, 97.5])
    return {"matches": int(len(g)), "exposed_matches": int((x != 0).sum()), "beta": float(beta), "se": float(se),
            "lo": float(beta - 1.96 * se), "hi": float(beta + 1.96 * se), "block_lo": float(lo_b),
            "block_hi": float(hi_b),
            "verdict": "treated side wins less than the benchmark says" if beta + 1.96 * se < 0 else
            ("treated side wins more" if beta - 1.96 * se > 0 else "tie")}


def main() -> int:
    f = frame()
    rng = np.random.default_rng(7)
    res = {"key": "beta = log-odds shift per treated side (A minus B), given the benchmark as an offset; negative = a "
                  "player treated in her previous match wins less often than the benchmark says; Wald 95% interval "
                  "(block bootstrap as a check); spanning 0 = tie", "windows": {}}
    for w, (lo, hi) in WINDOWS.items():
        g0 = f[(f["day"] >= lo) & (f["day"] <= hi)]
        for subset, g in (("all", g0), ("both logged", g0[g0["logged_a"] & g0["logged_b"]])):
            for bench in ("p_model", "p_market"):
                res["windows"][f"{w} | {subset} | {bench}"] = fit(g, bench, rng)
    (OUT / "med_residual_screen.json").write_text(json.dumps(res, indent=1))
    print(pd.DataFrame(res["windows"]).T.round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
