"""Line sharpening, step 4: how far the line is from its close at each point of the market's life, by time, by
volume traded and from the early market on, for each tier.

Every comparison is a market's price at a checkpoint against the SAME market's closing price (build.py's main
close, or the extended close with --close ext), scored three ways:
    dLL     log loss at the checkpoint minus log loss at the close, milli-nats per market (positive = the
            checkpoint is less accurate than the close: the market has toughened by that much)
    move    |price at checkpoint - closing price|, cents of outcome probability
    clv     what a bettor who knew the close would make per $1 by backing, at the checkpoint price, the side the
            close moved toward: max(q_close / q - 1) over the two sides, cents per $1, before spread and fees
Ranges are 95% Poisson-bootstrap intervals over markets (2,000 draws).

Checkpoints:
    time        hours before the close (HOURS)
    volume      the line once $V of pre-match taker stake has traded (VOLUMES), read one minute after the order
    share       the line once a share of the market's own pre-match volume has traded (SHARES)
    open        the market's first quoted price, and its first price away from the 0.50 placeholder
    early       the start of the early market (onsets from calibrate.py, if present)

Inputs:  data/studies/line_sharpening/{markets,prices,takers}.parquet, early_onsets.parquet (optional)
Outputs: data/studies/line_sharpening/results.json, checkpoints.parquet

Usage:
    ./python.sh src/eda/line_sharpening/evaluate.py
    ./python.sh src/eda/line_sharpening/evaluate.py --close ext --tag ext
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.line_sharpening import common as K  # noqa: E402

HOURS = (72, 48, 36, 24, 18, 12, 9, 6, 4, 3, 2, 1, 0.5, 0.25)
VOLUMES = (100, 250, 500, 1_000, 2_500, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 500_000)
SHARES = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90)
DRAWS = 2000
EPS = 0.005                         # prices clipped to [0.5c, 99.5c] for log loss


def seed_of(*parts) -> int:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def boot_means(x: np.ndarray, seed: int, draws: int = DRAWS) -> np.ndarray:
    """Column means of x (markets x measures) and their 95% Poisson-bootstrap intervals, one set of market
    weights shared by every column. Returns an array (3, columns): mean, low, high. Rows with any non-finite
    value are dropped."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x).all(axis=1)]
    if len(x) < 2:
        m = x.mean(axis=0) if len(x) else np.full(x.shape[1], np.nan)
        return np.vstack([m, np.full_like(m, np.nan), np.full_like(m, np.nan)])
    rng = np.random.default_rng(seed)
    means = np.empty((draws, x.shape[1]))
    step = max(1, int(2e7 // len(x)))
    for i in range(0, draws, step):
        w = rng.poisson(1.0, size=(min(step, draws - i), len(x))).astype(np.float32)
        means[i:i + len(w)] = (w @ x.astype(np.float32)) / np.maximum(w.sum(axis=1), 1)[:, None]
    lo, hi = np.percentile(means, [2.5, 97.5], axis=0)
    return np.vstack([x.mean(axis=0), lo, hi])


def boot_mean(x: np.ndarray, seed: int, draws: int = DRAWS) -> tuple[float, float, float]:
    """Mean and 95% Poisson-bootstrap interval of one measure."""
    m, lo, hi = boot_means(np.asarray(x, float)[:, None], seed, draws)[:, 0]
    return float(m), float(lo), float(hi)


def scores(p: np.ndarray, p_close: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
    pc = np.clip(p, EPS, 1 - EPS)
    pz = np.clip(p_close, EPS, 1 - EPS)
    dll = 1000 * (K.log_loss(pc, y) - K.log_loss(pz, y))
    move = 100 * np.abs(p - p_close)
    clv = 100 * np.maximum(pz / pc - 1, (1 - pz) / (1 - pc) - 1)
    return {"dll": dll, "move": move, "clv": clv}


# --------------------------------------------------------------------------------------
# checkpoints
# --------------------------------------------------------------------------------------
def time_checkpoints(pm: pd.DataFrame, pr: pd.DataFrame, close: str) -> pd.DataFrame:
    rows = []
    for h in HOURS:
        qt = pm[close].to_numpy() - 3600 * h
        v, t = K.lookup(pr.mkt.to_numpy(), pr.t.to_numpy(), pr.p.to_numpy(), pm.mkt.to_numpy(), qt)
        ok = qt >= pm.first_price_ts.to_numpy()
        rows.append(pd.DataFrame({"mkt": pm.mkt, "kind": "time", "point": str(h), "t": qt, "p": np.where(ok, v, np.nan)}))
    return pd.concat(rows, ignore_index=True)


def volume_paths(pm: pd.DataFrame, tk: pd.DataFrame, close: str) -> pd.DataFrame:
    tk = tk[tk.ts.to_numpy() < tk.mkt.map(pm.set_index("mkt")[close]).to_numpy()].copy()
    tk["cum"] = tk.groupby("mkt").stake.cumsum()
    return tk


def first_crossing(tk: pd.DataFrame, level: pd.Series) -> pd.Series:
    """Per market, the time of the first taker order at which cumulative stake reaches `level` (mkt -> $)."""
    lv = tk.mkt.map(level)
    hit = tk[tk.cum >= lv]
    return hit.groupby("mkt").ts.first()


def volume_checkpoints(pm: pd.DataFrame, pr: pd.DataFrame, tk: pd.DataFrame, close: str) -> pd.DataFrame:
    rows = []
    total = tk.groupby("mkt").stake.sum()
    specs = [("volume", str(v), pd.Series(float(v), index=pm.mkt)) for v in VOLUMES]
    specs += [("share", str(s), total * s) for s in SHARES]
    close_t = pm.set_index("mkt")[close]
    for kind, point, level in specs:
        when = first_crossing(tk, level)
        qt = np.minimum(when.to_numpy() + 60, close_t.reindex(when.index).to_numpy())
        v, _ = K.lookup(pr.mkt.to_numpy(), pr.t.to_numpy(), pr.p.to_numpy(), when.index.to_numpy(), qt)
        rows.append(pd.DataFrame({"mkt": when.index, "kind": kind, "point": point, "t": qt, "p": v}))
    return pd.concat(rows, ignore_index=True)


def open_checkpoints(pm: pd.DataFrame, pr: pd.DataFrame) -> pd.DataFrame:
    g = pr.groupby("mkt", sort=False)
    first = g.head(1).set_index("mkt")
    moved = pr[np.abs(pr.p - 0.5) > 1e-9].groupby("mkt", sort=False).head(1).set_index("mkt")
    return pd.concat([pd.DataFrame({"mkt": first.index, "kind": "open", "point": "first", "t": first.t, "p": first.p}),
                      pd.DataFrame({"mkt": moved.index, "kind": "open", "point": "first_off_50", "t": moved.t,
                                    "p": moved.p})], ignore_index=True)


def early_checkpoints(pm: pd.DataFrame, pr: pd.DataFrame, close: str) -> pd.DataFrame:
    path = K.OUT / "early_onsets.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["mkt", "kind", "point", "t", "p"])
    on = pd.read_parquet(path)                      # mkt, rule, onset_ts
    on = on[on.mkt.isin(pm.mkt)]
    close_t = pm.set_index("mkt")[close]
    on = on[on.onset_ts < on.mkt.map(close_t)]
    v, _ = K.lookup(pr.mkt.to_numpy(), pr.t.to_numpy(), pr.p.to_numpy(), on.mkt.to_numpy(), on.onset_ts.to_numpy())
    return pd.DataFrame({"mkt": on.mkt, "kind": "early", "point": on.rule, "t": on.onset_ts, "p": v})


# --------------------------------------------------------------------------------------
# summaries
# --------------------------------------------------------------------------------------
def scored(cp: pd.DataFrame, pm: pd.DataFrame, tk: pd.DataFrame, close: str) -> pd.DataFrame:
    """Checkpoint rows with their scores, the hours left to the close and the pre-match stake traded before
    the checkpoint and after it."""
    pclose = "p_close" if close == "close_ts" else "p_close_ext"
    x = cp.merge(pm[["mkt", "tier", "level", pclose, "y0", close]], on="mkt").dropna(subset=["p", pclose])
    for k, v in scores(x.p.to_numpy(), x[pclose].to_numpy(), x.y0.to_numpy()).items():
        x[k] = v
    x["hours_before_close"] = (x[close] - x.t) / 3600
    x["ll_close"] = 1000 * K.log_loss(np.clip(x[pclose].to_numpy(), EPS, 1 - EPS), x.y0.to_numpy())
    v, _ = K.lookup(tk.mkt.to_numpy(), tk.ts.to_numpy() + 0.0, tk.cum.to_numpy(), x.mkt.to_numpy(),
                    x.t.to_numpy() - 1e-6, max_age=None)
    x["vol_before"] = np.nan_to_num(v, nan=0.0)
    total = tk.groupby("mkt").stake.sum()
    x["vol_total"] = x.mkt.map(total).fillna(0.0)
    x["vol_after_share"] = np.where(x.vol_total > 0, 1 - x.vol_before / x.vol_total.where(x.vol_total > 0), np.nan)
    return x


def aggregate(x: pd.DataFrame, keys: list[str], label: str = "") -> list[dict]:
    out = []
    for vals, g in x.groupby(keys, sort=False, observed=True):
        vals = vals if isinstance(vals, tuple) else (vals,)
        rec = dict(zip(keys, [v if isinstance(v, (str, int, float)) else str(v) for v in vals]))
        rec.update({"markets": int(len(g)), "hours_before_close_median": round(float(g.hours_before_close.median()), 2),
                    "ll_close": round(float(g.ll_close.mean()), 2),
                    "vol_before_median": round(float(g.vol_before.median()), 0),
                    "vol_after_share_median": round(float(g.vol_after_share.median()), 3)
                    if g.vol_after_share.notna().any() else None})
        b = boot_means(g[["dll", "move", "clv"]].to_numpy(), seed_of(label, *vals))
        for j, k in enumerate(("dll", "move", "clv")):
            rec[k] = [round(float(b[0, j]), 2), round(float(b[1, j]), 2), round(float(b[2, j]), 2)]
        rec["move_median"] = round(float(g.move.median()), 2)
        rec["clv_median"] = round(float(g.clv.median()), 2)
        rec["move_3c_share"] = round(float((g.move >= 3).mean()), 3)
        rec["info_share"] = round(1 - rec["dll"][0] / (1000 * np.log(2) - rec["ll_close"]), 3)
        out.append(rec)
    return out


def panels(x: pd.DataFrame, starts=(24, 12, 6)) -> list[dict]:
    """The time curve on a fixed set of markets: those priced at every horizon from `start` hours on."""
    t = x[x.kind == "time"].copy()
    t["h"] = t.point.astype(float)
    out = []
    for h0 in starts:
        need = [h for h in HOURS if h <= h0]
        have = t[t.h.isin(need)].groupby("mkt").h.nunique()
        keep = have[have == len(need)].index
        p = t[t.mkt.isin(keep) & t.h.isin(need)]
        for rec in aggregate(p, ["tier", "point"], label=f"panel{h0}") + aggregate(p, ["level", "point"],
                                                                                      label=f"panel{h0}"):
            rec["panel_from_h"] = h0
            out.append(rec)
    return out


def block_early(x: pd.DataFrame) -> list[dict]:
    """Early-market rows of the markets whose onset was measured from the books, every rule on the same markets:
    the book-measured onset against the trade-record rules."""
    path = K.OUT / "book_onsets.parquet"
    if not path.exists():
        return []
    bo = pd.read_parquet(path, columns=["mkt", "censored", "book_300_1c_onset"])
    keep = bo[~bo.censored & bo.book_300_1c_onset.notna()].mkt
    e = x[(x.kind == "early") & x.mkt.isin(keep)]
    rules = ["book_300_1c", "book_300_2c", "typical_300_1c", "typical_300_2c", "vol_1000", "vol_2000", "vol_5000"]
    return aggregate(e[e.point.isin(rules)], ["tier", "point"], label="block_early")


def by_month(x: pd.DataFrame, pm: pd.DataFrame, rules=("typical_300_1c",), hours=("24", "6")) -> list[dict]:
    """Month by month (listed start), the early market's distance from the close."""
    month = pm.set_index("mkt").start_ts.map(lambda s: pd.Timestamp(s, unit="s").strftime("%Y-%m"))
    e = x[((x.kind == "early") & x.point.isin(rules)) | ((x.kind == "time") & x.point.isin(hours))].copy()
    e["month"] = e.mkt.map(month)
    return aggregate(e, ["tier", "kind", "point", "month"], label="month")


def volume_by_time(x: pd.DataFrame, points=("24", "12", "6", "3", "1")) -> list[dict]:
    """At the same hours before the close, markets split into thirds by the stake traded so far."""
    t = x[(x.kind == "time") & x.point.isin(points)].copy()
    t["vol_third"] = t.groupby(["tier", "point"]).vol_before.transform(
        lambda s: pd.qcut(s.rank(method="first"), 3, labels=["low", "mid", "high"]))
    return aggregate(t, ["tier", "point", "vol_third"], label="volxtime")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--close", choices=["main", "ext"], default="main")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    close = "close_ts" if args.close == "main" else "close_ext_ts"
    pclose = "p_close" if close == "close_ts" else "p_close_ext"

    pm = pd.read_parquet(K.OUT / "markets.parquet")
    pm = pm[pm[pclose].notna() & ~pm.suspect_close.fillna(True).astype(bool)].copy()
    pm["y0"] = pm.y0.astype(float)
    pr = pd.read_parquet(K.OUT / "prices.parquet")
    pr = pr[pr.t.to_numpy() <= pr.mkt.map(pm.set_index("mkt")[close]).to_numpy()]
    tk = volume_paths(pm, pd.read_parquet(K.OUT / "takers.parquet"), close)

    cp = pd.concat([time_checkpoints(pm, pr, close), volume_checkpoints(pm, pr, tk, close), open_checkpoints(pm, pr),
                    early_checkpoints(pm, pr, close)], ignore_index=True)
    cp = cp.astype({"mkt": int, "t": float, "p": float})
    tag = f"_{args.tag}" if args.tag else ""
    cp.to_parquet(K.OUT / f"checkpoints{tag}.parquet", index=False)
    x = scored(cp, pm, tk, close)
    res = {"close": args.close, "markets": int(len(pm)),
           "markets_by_tier": pm.tier.value_counts().to_dict(), "markets_by_level": pm.level.value_counts().to_dict(),
           "by_tier": aggregate(x, ["tier", "kind", "point"], "tier"),
           "by_level": aggregate(x, ["level", "kind", "point"], "level"),
           "panels": panels(x), "volume_by_time": volume_by_time(x), "block_early": block_early(x),
           "by_month": by_month(x, pm)}
    (K.OUT / f"results{tag}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"wrote results{tag}.json: {len(res['by_tier'])} tier rows, {len(res['by_level'])} level rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
