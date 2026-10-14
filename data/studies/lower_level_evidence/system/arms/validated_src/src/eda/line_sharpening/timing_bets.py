"""Line sharpening, step 5c: betting the current best model at the early market against betting it at the close.

Forecasts (timing_local.py): each seed symmetrised over the two orientations, the three seeds averaged, then the current
best's own calibration for 2026, one slope per tour on the log-odds (data/studies/meta_stack/coefficients.csv, fitted
on the out-of-sample seasons 2019-2025).

Execution at time T (early1c, early2c or close), a taker buying either player at market:
    ask       the mid + HALF_SPREAD (the block's books: half a 1c spread, no walk, for $300 inside the early market)
    fee       rate(T) x (1 - ask) per $1 staked (timing_frame.py)
    EV        model probability / ask - 1 - fee, per $1
    rule      back the player with the higher EV if it is at least TAU; $1 flat stakes

Measures, per rule and group, with 95% Poisson-bootstrap intervals over matches (2,000 draws):
    roi           realized profit per $1 staked
    clv_ev        expected profit per $1 if the closing mid is the true chance (bets at the close score -costs)
    per100        realized profit per 100 matches available (bets and passes)
    early - close the same per match, paired: what moving the whole strategy from the close to the early market changes
    same_bet      on matches where both moments back the same player: the early bet's return minus the close bet's
Also the log loss of the model and of the price at each moment (positive gain = the model better).

Output: data/studies/line_sharpening/timing_results.json
Usage:  ./python.sh src/eda/line_sharpening/timing_bets.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.line_sharpening import common as K  # noqa: E402

LOCAL = K.OUT / "local"
COEF = ROOT / "data" / "studies" / "meta_stack" / "coefficients.csv"
SEEDS = (0, 1, 2)
MOMENTS = ("early1c", "early2c", "close")
TAUS = (0.0, 0.02, 0.04, 0.06)
HALF_SPREAD = 0.005
MAX_ASK = 0.99
DRAWS = 2000
EPS = 1e-6


def seed_of(*parts) -> int:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def forecasts() -> pd.DataFrame:
    """match_id -> raw P(A) per query (seed mean of the symmetrised forecasts)."""
    out = None
    for q in ("td",) + MOMENTS:
        cols = {}
        for s in SEEDS:
            with np.load(LOCAL / f"base__2026__seed{s}.npz", allow_pickle=False) as z:
                p, ids = z[f"p_{q}"], z[f"ids_{q}"].astype(str)
            n = len(ids)
            cols["match_id"] = ids
            cols[f"s{s}"] = 0.5 * (p[:n] + 1.0 - p[n:])
        d = pd.DataFrame(cols)
        d[f"raw_{q}"] = d[[f"s{s}" for s in SEEDS]].mean(axis=1)
        d = d[["match_id", f"raw_{q}"]]
        out = d if out is None else out.merge(d, on="match_id", how="outer")
    return out


def slopes() -> dict[str, float]:
    c = pd.read_csv(COEF)
    c = c[(c.forecast == "best") & (c.spec == "best") & (c.window == "from2019") & (c.season == 2026)]
    return dict(zip(c.tour, c.b0))


def boot(values: np.ndarray, weights_den: np.ndarray | None, seed: int) -> tuple[float, float, float]:
    """Mean of values (or ratio sum(values) / sum(weights_den)) with a 95% Poisson-bootstrap interval over rows."""
    v = np.asarray(values, float)
    d = np.ones_like(v) if weights_den is None else np.asarray(weights_den, float)
    if d.sum() <= 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    w = rng.poisson(1.0, size=(DRAWS, len(v))).astype(np.float32)
    est = (w @ v.astype(np.float32)) / np.maximum(w @ d.astype(np.float32), 1e-9)
    lo, hi = np.percentile(est, [2.5, 97.5])
    return float(v.sum() / d.sum()), float(lo), float(hi)


def decide(m: np.ndarray, p: np.ndarray, fee: np.ndarray, tau: float, slip: float = HALF_SPREAD):
    """Side backed (1 = A, 0 = B, -1 = no bet), ask paid, fee per $1, model EV per $1. `slip` is what the bet pays
    over the mid (half a 1c spread by default)."""
    ask_a = np.minimum(p + slip, MAX_ASK)
    ask_b = np.minimum(1.0 - p + slip, MAX_ASK)
    fa, fb = fee * (1.0 - ask_a), fee * (1.0 - ask_b)
    ev_a = m / ask_a - 1.0 - fa
    ev_b = (1.0 - m) / ask_b - 1.0 - fb
    side = np.where(ev_a >= ev_b, 1, 0)
    ev = np.where(side == 1, ev_a, ev_b)
    ok = np.isfinite(ev) & (ev >= tau)
    side = np.where(ok, side, -1)
    ask = np.where(side == 1, ask_a, ask_b)
    f = np.where(side == 1, fa, fb)
    return side, ask, f, ev


def simulate(x: pd.DataFrame, moment: str, tau: float, slip: float = HALF_SPREAD) -> pd.DataFrame:
    m = x[f"m_{moment}"].to_numpy()
    p = x[f"p_{moment}"].to_numpy()
    side, ask, f, ev = decide(m, p, x[f"fee_{moment}"].to_numpy(), tau, slip)
    won = np.where(side == 1, x.a_won.to_numpy(), 1 - x.a_won.to_numpy())
    close_side = np.where(side == 1, x.p_close.to_numpy(), 1.0 - x.p_close.to_numpy())
    bet = side >= 0
    return pd.DataFrame({"bet": bet, "side": side, "ev": np.where(bet, ev, 0.0),
                         "ret": np.where(bet, won / ask - 1.0 - f, 0.0),
                         "clv": np.where(bet, close_side / ask - 1.0 - f, 0.0)}, index=x.index)


def summarise(x: pd.DataFrame, label: str, early_slip: float = HALF_SPREAD) -> list[dict]:
    """Every rule at every moment; the close always pays HALF_SPREAD, the early moments `early_slip`."""
    rows = []
    for tau in TAUS:
        sims = {mo: simulate(x, mo, tau, HALF_SPREAD if mo == "close" else early_slip) for mo in MOMENTS}
        for mo, s in sims.items():
            n = int(s.bet.sum())
            rec = {"group": label, "tau": tau, "moment": mo, "matches": int(len(x)), "bets": n,
                   "bet_rate": round(n / len(x), 3) if len(x) else None,
                   "model_ev": round(float(s.ev[s.bet].mean()), 4) if n else None}
            for k, (val, den) in {"roi": (s.ret, s.bet.astype(float)), "clv_ev": (s.clv, s.bet.astype(float)),
                                  "per100": (100 * s.ret, None)}.items():
                rec[k] = [round(v, 4) for v in boot(val.to_numpy(), None if den is None else den.to_numpy(),
                                                    seed_of(label, tau, mo, k))]
            rows.append(rec)
        for mo in ("early1c", "early2c"):
            e, c = sims[mo], sims["close"]
            ok = x[f"p_{mo}"].notna().to_numpy()
            diff = (e.ret - c.ret).to_numpy()[ok]
            same = (e.side == c.side).to_numpy() & e.bet.to_numpy() & ok
            dclv = (e.clv - c.clv).to_numpy()[ok]
            rec = {"group": label, "tau": tau, "moment": f"{mo}_minus_close", "matches": int(ok.sum()),
                   "per_match": [round(v, 4) for v in boot(diff, None, seed_of(label, tau, mo, "diff"))],
                   "per_match_clv": [round(v, 4) for v in boot(dclv, None, seed_of(label, tau, mo, "dclv"))],
                   "same_bets": int(same.sum()),
                   "same_bet_return_diff": [round(v, 4) for v in boot((e.ret - c.ret).to_numpy()[same], None,
                                                                      seed_of(label, tau, mo, "same"))]
                   if same.any() else None}
            rows.append(rec)
    return rows


def drift(x: pd.DataFrame, label: str) -> list[dict]:
    """How much of the model's disagreement with the early price the market closes by the close: the slope of
    M = logit(close) - logit(early) on D = logit(model at early) - logit(early), through the origin. 1 = the price
    moves all the way to the model, 0 = not at all. For betting, D's own noise counts too: an early price that has
    over-reacted and reverts is money for whoever bet against it."""
    out = []
    for mo in ("early1c", "early2c"):
        ok = x[f"p_{mo}"].notna().to_numpy()
        pe = logit(np.clip(x[f"p_{mo}"].to_numpy()[ok], 0.005, 0.995))
        pc = logit(np.clip(x.p_close.to_numpy()[ok], 0.005, 0.995))
        me = logit(np.clip(x[f"m_{mo}"].to_numpy()[ok], EPS, 1 - EPS))
        M, D = pc - pe, me - pe
        rng = np.random.default_rng(seed_of(label, mo, "drift"))
        w = rng.poisson(1.0, size=(DRAWS, len(D))).astype(float)
        slopes = (w @ (M * D)) / np.maximum(w @ (D * D), 1e-12)
        lo, hi = np.percentile(slopes, [2.5, 97.5])
        out.append({"group": label, "moment": mo, "matches": int(ok.sum()),
                    "slope": [round(float((M * D).sum() / (D * D).sum()), 3), round(float(lo), 3), round(float(hi), 3)],
                    "disagreement_sd_logit": round(float(D.std()), 3), "move_sd_logit": round(float(M.std()), 3)})
    return out


def favourites(x: pd.DataFrame, label: str) -> dict:
    """Market only: how the early favourite's price moves by the close (cents; + = the favourite firms up), and the
    model's bets split by whether they back the favourite or the underdog at the moment of the bet. Also the mixed
    policy the drift suggests (favourites at the early market, underdogs at the close), against all at the close."""
    out = {"group": label}
    for mo in ("early1c", "early2c"):
        g = x[x[f"p_{mo}"].notna()]
        pe = g[f"p_{mo}"].to_numpy()
        fav_a = pe >= 0.5
        d = 100 * (np.where(fav_a, g.p_close, 1 - g.p_close) - np.where(fav_a, pe, 1 - pe))
        out[f"favourite_drift_c_{mo}"] = [round(v, 3) for v in boot(d, None, seed_of(label, mo, "fav"))]
    sims = {mo: simulate(x, mo, 0.0) for mo in ("early1c", "close")}
    for mo, s in sims.items():
        fav_side = np.where(x[f"p_{mo}"].to_numpy() >= 0.5, 1, 0)
        for lab, mask in (("favourite", s.bet & (s.side == fav_side)), ("underdog", s.bet & (s.side != fav_side))):
            out[f"{mo}_{lab}_bets"] = int(mask.sum())
            out[f"{mo}_{lab}_clv_ev"] = [round(v, 4) for v in boot(s.clv[mask].to_numpy(), None,
                                                                   seed_of(label, mo, lab, "clv"))]
            out[f"{mo}_{lab}_roi"] = [round(v, 4) for v in boot(s.ret[mask].to_numpy(), None,
                                                                seed_of(label, mo, lab, "roi"))]
    e, c = sims["early1c"], sims["close"]
    e_fav = e.bet & (e.side == np.where(x.p_early1c.to_numpy() >= 0.5, 1, 0))
    c_dog = c.bet & (c.side != np.where(x.p_close.to_numpy() >= 0.5, 1, 0))
    mix_ret = np.where(e_fav, e.ret, 0.0) + np.where(c_dog, c.ret, 0.0)
    mix_clv = np.where(e_fav, e.clv, 0.0) + np.where(c_dog, c.clv, 0.0)
    out["mixed_minus_close_per_match_clv"] = [round(v, 4) for v in boot(mix_clv - c.clv.to_numpy(), None,
                                                                        seed_of(label, "mix", "clv"))]
    out["mixed_minus_close_per_match"] = [round(v, 4) for v in boot(mix_ret - c.ret.to_numpy(), None,
                                                                    seed_of(label, "mix", "ret"))]
    return out


def log_loss_gains(x: pd.DataFrame, label: str) -> list[dict]:
    """Model against the price it was fed, per moment: mean log-loss gain (milli; positive = model better)."""
    out = []
    y = x.a_won.to_numpy()
    for mo in MOMENTS:
        ok = x[f"p_{mo}"].notna().to_numpy()
        m = np.clip(x[f"m_{mo}"].to_numpy()[ok], EPS, 1 - EPS)
        p = np.clip(x[f"p_{mo}"].to_numpy()[ok], 0.005, 0.995)
        gain = 1000 * (K.log_loss(p, y[ok]) - K.log_loss(m, y[ok]))
        out.append({"group": label, "moment": mo, "matches": int(ok.sum()),
                    "gain_vs_price": [round(v, 2) for v in boot(gain, None, seed_of(label, mo, "ll"))]})
    return out


def main() -> int:
    tf = pd.read_parquet(K.OUT / "timing_frame.parquet")
    fc = forecasts()
    x = tf.merge(fc, on="match_id", how="inner")
    x = x[x.p_early1c.notna() & x.p_close.notna() & x.raw_close.notna() & x.raw_early1c.notna()].reset_index(drop=True)
    b = slopes()
    slope = x.tour.map(b).to_numpy()
    for q in ("td",) + MOMENTS:
        x[f"m_{q}"] = expit(slope * logit(np.clip(x[f"raw_{q}"].to_numpy(), EPS, 1 - EPS)))
    x["a_won"] = x.a_won.astype(float)
    groups = {"all": x, "highest": x[x.tier == "highest"], "higher": x[x.tier == "higher"],
              "Grand Slam": x[x.level == "Grand Slam"], "1000 and Finals": x[x.level == "1000 and Finals"],
              "500": x[x.level == "500"], "250": x[x.level == "250"], "men": x[x.tour == "atp"],
              "women": x[x.tour == "wta"], "clean": x[x.clean.astype(bool)]}
    ms = pd.read_parquet(ROOT / "data" / "studies" / "meta_stack" / "test_predictions.parquet",
                         columns=["match_id", "year", "p_best"])
    chk = x[["match_id", "m_td"]].merge(ms[ms.year == 2026], on="match_id")
    lm, lb = logit(np.clip(chk.m_td, EPS, 1 - EPS)), logit(np.clip(chk.p_best, EPS, 1 - EPS))
    check = {"matches": int(len(chk)), "logit_corr": round(float(np.corrcoef(lm, lb)[0, 1]), 5),
             "mean_abs_prob_gap": round(float(np.mean(np.abs(chk.m_td - chk.p_best))), 4)}
    res = {"matches": int(len(x)), "half_spread": HALF_SPREAD, "slopes_2026": b, "taus": list(TAUS),
           "hours_early_to_close_median": {mo: round(float(((x.t_close - x[f"t_{mo}"]) / 3600).median()), 2)
                                           for mo in ("early1c", "early2c")},
           "check_td_vs_meta_stack": check, "bets": [], "log_loss": []}
    res["drift"], res["favourites"] = [], []
    for name, g in groups.items():
        g = g.reset_index(drop=True)
        res["bets"] += summarise(g, name)
        res["log_loss"] += log_loss_gains(g, name)
        res["drift"] += drift(g, name)
        res["favourites"].append(favourites(g, name))
    # what a $300 bet really pays at the early market: up to 1c over the mid at early1c, up to 2c at early2c
    res["slippage_sensitivity"] = []
    for name in ("all", "highest", "higher"):
        g = groups[name].reset_index(drop=True)
        for slip in (0.01, 0.015):
            res["slippage_sensitivity"] += summarise(g, f"{name}|early_slip_{slip}", early_slip=slip)
    (K.OUT / "timing_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"wrote timing_results.json for {len(x)} matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
