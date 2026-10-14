"""Meta-labeling (López de Prado, AFML ch. 3) against anchor-and-nudge, men's main tour, 2020-2026.

A primary model picks a side; a secondary logistic model, trained on earlier seasons' picks, predicts
whether that side wins (the meta-label: at fixed odds, a winning pick is a profitable pick) and decides
whether to bet. Primaries:
  sport    the market-free 36-input forecast's value side (sign of its log-odds minus the market's)
  anchor   the anchored profile+context model's value side
  fav      the market favourite (the market itself as the primary model)
Meta inputs, oriented to the side: the market's log-odds, the primary's edge, surface, level, best of
five, early-surface-season, edge x surface/early, and (fav only) the profile+context nudges.
Bets are hypothetical: flat one-unit stakes at the archived closing odds (average; Pinnacle to 2025;
best available as an optimistic bound). These are not executable prices.
Run after anchor.py and market_surface.py: ./python.sh src/eda/market_anchoring/meta_label.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.market_anchoring import common as C

TEST_YEARS = range(2020, 2027)
NUDGE = C.PROFILE + [C.E.SR] + C.E.CONTEXT
THRESHOLDS = (0.0, 0.2, 0.4)


def early_flags(frame: pd.DataFrame) -> pd.Series:
    rows = pd.read_parquet(C.REPAIRS / "repair_rows.parquet", columns=["match_id", "player_id", "year", "surface", "day"])
    seen = rows.groupby(["player_id", "year", "surface"]).cumcount()
    prior = seen - rows.groupby(["player_id", "year", "surface", "day"]).cumcount()
    return frame.match_id.map(rows.assign(early=prior.lt(3)).groupby("match_id").early.any()).fillna(False)


def fit_with_intercept(x: np.ndarray, y: np.ndarray, ridge: float = 0.01, free: int = 1):
    """Logistic fit with an intercept; the first `free` columns (the market's log-odds) are never shrunk.

    Shrinking the market term was checked and is harmful: with the anchor penalized at ridge 0.01 the
    favourite-oriented model lost 1.3 milli-log-loss; unpenalized it reproduces the anchored fit."""
    scale = C.P.rms_scale(x)
    z = np.column_stack([np.ones(len(x)), x / scale])
    pen = np.r_[0.0, np.zeros(free), np.full(x.shape[1] - free, ridge)]
    beta = C.P.fit_logistic(z, y, np.zeros(len(y)), pen)
    return lambda q: expit(np.column_stack([np.ones(len(q)), q / scale]) @ beta)


def oriented(frame: pd.DataFrame, sign: np.ndarray, primary_logit: np.ndarray, with_nudges: bool,
             context: bool = True) -> np.ndarray:
    m = sign * frame.mkt_avg.to_numpy()
    edge = sign * (primary_logit - frame.mkt_avg.to_numpy())
    clay, grass = frame.surface.eq("Clay").to_numpy(float), frame.surface.eq("Grass").to_numpy(float)
    early = frame.early.to_numpy(float)
    cols = [m]
    if context:
        cols += [edge, clay, grass, frame.scheduled_best_of.eq(5).to_numpy(float),
                 frame.level.eq("T1000").to_numpy(float), frame.level.eq("T500").to_numpy(float), early,
                 edge * clay, edge * grass, edge * early]
    if with_nudges:
        cols += [sign * frame[c].to_numpy(dtype=float) for c in NUDGE]
    return np.column_stack(cols)


def odds_for(frame: pd.DataFrame, side_a: np.ndarray, book: str) -> np.ndarray:
    return np.where(side_a, frame[f"{book}_a"], frame[f"{book}_b"]).astype(float)


def bet_stats(profit: np.ndarray, stake: np.ndarray, clusters: np.ndarray) -> dict:
    keep = stake > 0
    if keep.sum() < 20:
        return {"bets": int(keep.sum()), "roi": None, "roi_lo": None, "roi_hi": None}
    r = C.P.clustered_interval(profit[keep], clusters[keep])
    return {"bets": int(keep.sum()), "roi": r["gain_mll"] / 1000, "roi_lo": r["lo_mll"] / 1000,
            "roi_hi": r["hi_mll"] / 1000}


def run(frame: pd.DataFrame, anchored: np.ndarray, calibrated: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    y = frame.a_won.to_numpy(dtype=float)
    years = frame.year.to_numpy()
    blocks = frame.block4week.to_numpy()
    primaries = {
        "sport": C.clip_logit(frame.p_sport36),
        "anchor": C.clip_logit(anchored),
        "fav": None,
        "fav_plain": None,   # market log-odds and the nudges only: the anchored model, favourite-oriented
    }
    prob_rows, bet_rows = [], []
    for name, plogit in primaries.items():
        favourite = name.startswith("fav")
        for tau in (THRESHOLDS if not favourite else (0.0,)):
            if favourite:
                side_a = frame.mkt_avg.to_numpy() >= 0
                fires = np.isfinite(frame.mkt_avg.to_numpy())
                plogit_use = frame.mkt_avg.to_numpy()
            else:
                diff = plogit - frame.mkt_avg.to_numpy()
                side_a = diff >= 0
                fires = np.isfinite(diff) & (np.abs(diff) > tau)
                plogit_use = plogit
            sign = np.where(side_a, 1.0, -1.0)
            ys = np.where(side_a, y, 1 - y)
            x = oriented(frame, sign, plogit_use, with_nudges=favourite, context=(name != "fav_plain"))
            ok = fires & np.isfinite(x).all(axis=1)
            start = 2019 if name == "sport" else 2014
            p_meta = np.full(len(frame), np.nan)
            for year in TEST_YEARS:
                tr = ok & (years >= start) & (years < year)
                te = ok & (years == year)
                if tr.sum() < 300 or not te.any():
                    continue
                p_meta[te] = fit_with_intercept(x[tr], ys[tr])(x[te])
            test = ok & np.isfinite(p_meta)
            p_market = expit(sign * frame.mkt_avg.to_numpy())
            p_cal = np.where(side_a, calibrated, 1 - calibrated)
            p_anchor = np.where(side_a, anchored, 1 - anchored)
            p_primary = expit(sign * plogit_use)
            label = name if favourite else f"{name} |edge|>{tau}"
            for model, p in (("market (de-vigged average)", p_market), ("calibrated average", p_cal),
                             ("primary model", p_primary), ("meta-label model", p_meta),
                             ("anchored profile+context", p_anchor)):
                m = test & np.isfinite(p)
                for window, wm in (("2020_2025", years <= 2025), ("2026", years == 2026), ("2020_2026", years > 0)):
                    k = m & wm
                    if not k.any():
                        continue
                    prob_rows.append({"primary": label, "probability": model, "window": window, "picks": int(k.sum()),
                                      "log_loss": float(C.ll(ys[k], p[k]).mean()),
                                      "win_rate": float(ys[k].mean()), "mean_p": float(p[k].mean())})
            for book in ("avg", "ps", "max"):
                o = odds_for(frame, side_a, book)
                for rule, p in (("every primary pick", None), ("meta: P x odds > 1", p_meta),
                                ("anchored: P x odds > 1", p_anchor)):
                    stake = test & np.isfinite(o) & (o > 1)
                    if p is not None:
                        stake &= np.isfinite(p) & (p * o > 1)
                    profit = np.where(stake, np.where(ys == 1, o - 1, -1.0), 0.0)
                    for window, wm in (("2020_2025", years <= 2025), ("2026", years == 2026), ("2020_2026", years > 0)):
                        if book == "ps" and window != "2020_2025":
                            continue
                        bet_rows.append({"primary": label, "odds": book, "rule": rule, "window": window,
                                         **bet_stats(profit, (stake & wm).astype(float), blocks)})
            print(f"{label}: {int(test.sum()):,} scored picks", flush=True)
    return pd.DataFrame(prob_rows), pd.DataFrame(bet_rows)


def anchored_both_sides(frame: pd.DataFrame, anchored: np.ndarray, calibrated: np.ndarray) -> pd.DataFrame:
    """Reference: the anchored probability model free to back either side, and the plain market."""
    y = frame.a_won.to_numpy(dtype=float)
    years = frame.year.to_numpy()
    out = []
    for book in ("avg", "ps", "max"):
        oa, ob = frame[f"{book}_a"].to_numpy(float), frame[f"{book}_b"].to_numpy(float)
        for label, p in (("anchored profile+context", anchored), ("calibrated average", calibrated)):
            ev_a, ev_b = p * oa - 1, (1 - p) * ob - 1
            back_a = (ev_a > 0) & (ev_a >= ev_b)
            back_b = (ev_b > 0) & (ev_b > ev_a)
            profit = np.where(back_a, np.where(y == 1, oa - 1, -1.0), 0.0) + np.where(back_b, np.where(y == 0, ob - 1, -1.0), 0.0)
            stake = (back_a | back_b) & np.isfinite(p) & np.isfinite(oa) & np.isfinite(ob)
            for window, wm in (("2020_2025", (years >= 2020) & (years <= 2025)), ("2026", years == 2026),
                               ("2020_2026", years >= 2020)):
                if book == "ps" and window != "2020_2025":
                    continue
                out.append({"model": label, "odds": book, "window": window,
                            **bet_stats(profit, (stake & wm).astype(float), frame.block4week.to_numpy())})
    return pd.DataFrame(out)


def main():
    frame = C.load_atp()
    frame["early"] = early_flags(frame).to_numpy()
    preds = pd.read_parquet(C.OUT / "anchor_predictions.parquet")
    if not (preds.match_id.to_numpy() == frame.match_id.to_numpy()).all():
        raise ValueError("anchor predictions are not in frame order")
    anchored = preds["average|profile16_context|free"].to_numpy()
    calibrated = preds["average|calibrated"].to_numpy()
    probs, bets = run(frame, anchored, calibrated)
    both = anchored_both_sides(frame, anchored, calibrated)
    probs.to_csv(C.OUT / "meta_probabilities.csv", index=False)
    bets.to_csv(C.OUT / "meta_bets.csv", index=False)
    both.to_csv(C.OUT / "meta_reference_bets.csv", index=False)
    pd.set_option("display.width", 250)
    print(probs[probs.window.eq("2020_2026")].pivot_table(index="primary", columns="probability",
                                                           values="log_loss").round(5).to_string())
    print(probs[probs.window.eq("2020_2026")].groupby("primary").picks.first().to_string())
    b = bets[bets.window.isin(["2020_2025", "2026"])].copy()
    b["cell"] = b.apply(lambda r: "n/a" if r.roi is None or pd.isna(r.roi) else
                        f"{r.roi:+.3f} [{r.roi_lo:+.3f},{r.roi_hi:+.3f}] n={r.bets}", axis=1)
    print(b.pivot_table(index=["primary", "rule"], columns=["odds", "window"], values="cell", aggfunc="first").to_string())
    print(both.to_string())


if __name__ == "__main__":
    main()
