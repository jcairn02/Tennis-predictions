"""Does the closing line's sharpness drift over the seasons, and does the model's use of it drift too? (close_drift)

The owner's question (8 Oct 2026): the model takes the closing line as an input, so it learns from its training seasons
how far to trust the close against the sporting features. If the close was softer in some seasons and sharper in others,
is that trade-off stale, and are features orthogonal to the close weaker, or stronger, against a softer close?

Seasons <= 2024 only: 2025-2026 is the holdout of the proposed clean rebuild (docs/studies/clean_holdout_rebuild/), so
no result of those seasons is read. The frame is loaded with a season filter and asserted (via the feature-provenance
loader); the other tables are joined to its rows only.

Per season (debut seasons out), both tours and each tour:
    gap_pin      log loss of the books' average close minus Pinnacle's (both margin-free, raw), x1000:
                 + = Pinnacle sharper, i.e. the average close is the softer price
    slope_close  the close's own calibration slope that season (logistic through the origin on its log-odds, in-season):
                 above 1 = the close was too timid, below 1 = too bold
    overround    the books' average margin
    room_elo     log loss of surface Elo minus the close's, x1000: + = the close knows more than Elo
    room_noodds  the same for the no-odds TabPFN (meta-stack study's 54-input walk-forward forecast without the price)
    a, b         in-season logistic of the result on the close's log-odds (a) and the no-odds model's log-odds (b),
                 no intercept: the trust that season's data would have given each. A sharper close pushes a up and b
                 towards 0
    combo_gain   that in-season combination's log loss gain over the in-season-recalibrated close, x1000 (in-sample:
                 an upper bound on what a sporting forecast could add to the close that season)
    edge         the current model's stage 1 against the close, both recalibrated walk-forward on 2014..Y-1
                 (feature_provenance/edge_by_season.py's main variant, seeds 0-2): + = model better
    c            realisation of the model's disagreement with the close: logistic of the result with the recalibrated
                 close's log-odds as an offset and c x (model log-odds - close log-odds). 1 = every claimed point came
                 true; below 1 = the model over-reacts; above 1 = it under-reacts
    sd_delta     spread of that disagreement (log-odds)
    edge_pin, c_pin  the same two against Pinnacle's price (recalibrated walk-forward on 2014..Y-1), on the matches it
                 prices: a sharper benchmark than the average close the model takes as its input

Writes data/studies/close_drift/drift_by_season.csv and drift_by_era.csv.
Run: ./python.sh src/eda/close_drift/drift.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_provenance import edge_by_season as E  # noqa: E402

OUT = ROOT / "data" / "studies" / "close_drift"
BASELINES = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_baselines.parquet"
ODDS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_odds.parquet"
WALKFORWARD = ROOT / "data" / "studies" / "meta_stack" / "walkforward.parquet"
SEASONS = list(range(2015, 2025))
ERAS = {"2015-2019": range(2015, 2020), "2020-2024": range(2020, 2025)}


def logistic(X, y, offset=None, iters=100):
    """Logistic regression without intercept by Newton's method; returns coefficients and their standard errors."""
    X = np.atleast_2d(np.asarray(X, float))
    if X.shape[0] != len(y):
        X = X.T
    off = np.zeros(len(y)) if offset is None else np.asarray(offset, float)
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = expit(off + X @ beta)
        grad = X.T @ (y - p)
        hess = (X * (p * (1 - p))[:, None]).T @ X + 1e-9 * np.eye(X.shape[1])
        step = np.linalg.solve(hess, grad)
        beta += np.clip(step, -4, 4)
        if np.max(np.abs(step)) < 1e-10:
            break
    p = expit(off + X @ beta)
    cov = np.linalg.inv((X * (p * (1 - p))[:, None]).T @ X + 1e-9 * np.eye(X.shape[1]))
    return beta, np.sqrt(np.diag(cov))


def frame() -> pd.DataFrame:
    f = E.load_frame()                       # seasons <= 2024 only, asserted
    per_season, _ = E.forecasts(f)
    f["p02"] = pd.concat([per_season[s][[0, 1, 2]].mean(axis=1) for s in E.SEASONS]).reindex(f.index)
    b = pd.read_parquet(BASELINES, columns=["match_id", "p_market", "p_pinnacle", "p_elo_surf_ret"])
    o = pd.read_parquet(ODDS, columns=["match_id", "overround_avg"])
    w = pd.read_parquet(WALKFORWARD, columns=["match_id", "p_noodds"])
    f = f.join(b.set_index("match_id")).join(o.set_index("match_id")).join(w.set_index("match_id"))
    assert np.nanmax(np.abs(f["p_mkt"] - f["p_market"])) == 0, "the close must be the frame's own price"
    return f


def wf_probs(f, rows):
    """The model's, the close's and Pinnacle's probabilities, each recalibrated with slopes on 2014..Y-1 (per tour).
    Pinnacle's slope is fitted on the earlier matches it prices; rows without a Pinnacle price get NaN."""
    s = int(rows["season"].iloc[0])
    sm, sc = E.slopes(f, "p02", 2014, s), E.slopes(f, "p_mkt", 2014, s)
    fp = f[f["p_pinnacle"].notna()]
    sp = E.slopes(fp, "p_pinnacle", 2014, s)
    q_pin = np.full(len(rows), np.nan)
    has = rows["p_pinnacle"].notna().to_numpy()
    q_pin[has] = E.recalibrated(rows[has], "p_pinnacle", sp)
    return E.recalibrated(rows, "p02", sm), E.recalibrated(rows, "p_mkt", sc), q_pin


def diff_mll(rows, p_worse_if_positive, p_ref):
    """Mean of (log loss of the first minus the second) x1000 with a four-week-block interval."""
    d = E.log_loss(p_worse_if_positive, rows["y"]) - E.log_loss(p_ref, rows["y"])
    est, lo, hi, _ = E.paired(d, rows["block"].to_numpy())
    return est, lo, hi


def measures(f, rows) -> dict:
    out = {"matches": len(rows)}
    y = rows["y"].to_numpy()
    m = E.lg(rows["p_mkt"])
    pin = rows["p_pinnacle"].notna().to_numpy()
    out["gap_pin"], out["gap_pin_lo"], out["gap_pin_hi"] = diff_mll(rows[pin], rows.loc[pin, "p_mkt"], rows.loc[pin, "p_pinnacle"])
    out["overround"] = float(rows["overround_avg"].mean())
    out["room_elo"], out["room_elo_lo"], out["room_elo_hi"] = diff_mll(rows, rows["p_elo_surf_ret"], rows["p_mkt"])
    nd = rows["p_noodds"].notna().to_numpy()
    out["room_noodds"], out["room_noodds_lo"], out["room_noodds_hi"] = diff_mll(rows[nd], rows.loc[nd, "p_noodds"], rows.loc[nd, "p_mkt"])
    (sl,), (sl_se,) = logistic(m[:, None], y)
    out["slope_close"], out["slope_close_se"] = sl, sl_se
    r = rows[nd]
    (a, b), (a_se, b_se) = logistic(np.column_stack([E.lg(r["p_mkt"]), E.lg(r["p_noodds"])]), r["y"].to_numpy())
    out.update({"a": a, "a_se": a_se, "b": b, "b_se": b_se})
    q_close_in = expit(sl * E.lg(r["p_mkt"]))                    # the close recalibrated in-season (one slope)
    q_combo = expit(a * E.lg(r["p_mkt"]) + b * E.lg(r["p_noodds"]))
    out["combo_gain"] = 1000 * float((E.log_loss(q_close_in, r["y"]) - E.log_loss(q_combo, r["y"])).mean())
    return out


def model_measures(rows, q_model, q_close, q_pin) -> dict:
    out = {}
    for tag, q_ref, keep in (("", q_close, np.ones(len(rows), bool)), ("_pin", q_pin, ~np.isnan(q_pin))):
        r, qm, qr = rows[keep], q_model[keep], q_ref[keep]
        d = E.log_loss(qr, r["y"]) - E.log_loss(qm, r["y"])
        est, lo, hi, _ = E.paired(d, r["block"].to_numpy())
        delta = E.lg(qm) - E.lg(qr)
        (c,), (c_se,) = logistic(delta[:, None], r["y"].to_numpy(), offset=E.lg(qr))
        out.update({f"edge{tag}": est, f"edge{tag}_lo": lo, f"edge{tag}_hi": hi, f"c{tag}": c, f"c{tag}_se": c_se})
        if not tag:
            out["sd_delta"] = float(np.std(delta))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    f = frame()
    scored = f[~f["debut"]]
    probs = {}
    for s in SEASONS:
        rows = scored[scored["season"] == s]
        probs[s] = (rows.index, *wf_probs(f, rows))
    index = np.concatenate([probs[s][0] for s in SEASONS])
    qm, qc, qp = (pd.Series(np.concatenate([probs[s][k] for s in SEASONS]), index=index) for k in (1, 2, 3))

    def block(label, rows):
        res = []
        for tour in ("both", "atp", "wta"):
            r = rows if tour == "both" else rows[rows["tour"] == tour]
            if len(r) < 500:
                continue
            res.append({"window": label, "tour": tour, **measures(f, r),
                        **model_measures(r, *(q.reindex(r.index).to_numpy() for q in (qm, qc, qp)))})
        return res

    by_season = pd.DataFrame([x for s in SEASONS for x in block(str(s), scored[scored["season"] == s])])
    by_era = pd.DataFrame([x for lab, ss in ERAS.items() for x in block(lab, scored[scored["season"].isin(ss)])])
    by_season.to_csv(OUT / "drift_by_season.csv", index=False)
    by_era.to_csv(OUT / "drift_by_era.csv", index=False)
    cols = ["window", "tour", "matches", "gap_pin", "slope_close", "overround", "room_elo", "room_noodds", "a", "b",
            "combo_gain", "edge", "c", "c_se", "sd_delta", "edge_pin", "c_pin", "c_pin_se"]
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(by_season[by_season["tour"] == "both"][cols].round(3).to_string(index=False))
        print(by_era[cols].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
