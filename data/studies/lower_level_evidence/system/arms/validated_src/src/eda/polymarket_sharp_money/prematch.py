"""How beatable is Polymarket tennis before the match? Accounts sorted by how they do against the closing price.

Only bets placed before a match's scheduled start count. Each bet is valued at the closing price: the book's
midpoint in the last minute-level point before the scheduled start (Polymarket's price history, staged by
src/ingest/public_dump/polymarket_prices.py). A bet's edge against the close is
    shares x (closing price of the side backed - price paid)
which, if the closing price is the true chance of winning, is the bet's expected profit before fees.
Edges sum to zero across the two sides of every trade: one account's gain against the close is another's loss.

Accounts are sorted using only their OTHER matches (five groups of markets by match, as in classify.py):
    clearly beats the close   10+ other matches with pre-match bets, edge at least 2 standard errors above 0
    clearly loses to it       10+ other matches, edge at least 2 standard errors below 0
    unsure                    everyone else (fewer than 10 other matches, or an edge within 2 standard errors)
The standard error treats each market as one observation (the edge a wallet took in that match), so it
needs no model of prices. What each group then did in the held-out matches is the honest measure of how much
the close can be beaten, by level of play.

Inputs:  data/dump/odds/polymarket/trades/*.parquet, data/dump/odds/polymarket/price_history/,
         data/studies/polymarket_sharp_money/markets.parquet (build_positions.py)
Output:  data/studies/polymarket_sharp_money/prematch.json, prematch_positions.parquet

Usage:
    ./python.sh src/eda/polymarket_sharp_money/prematch.py
    ./python.sh src/eda/polymarket_sharp_money/prematch.py --buffer-minutes 30 --tag buffer30   (robustness)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_positions as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "polymarket_sharp_money"
PRICE_HISTORY = ROOT / "data" / "dump" / "odds" / "polymarket" / "price_history"
GROUPS = ["win", "unsure", "lose"]
GROUP_LABELS = {"win": "Clearly beat the close", "unsure": "Unsure", "lose": "Clearly lose to the close"}
N_MIN = 10
Z = 2.0
MAX_CLOSE_AGE = 3600  # the closing midpoint must be from the last hour before the cut-off
B_DRAWS = 1000
SEED = 20260925
MIN_MARKETS = 150
MAX_HALF_WIDTH = 0.05

# Levels of play for the report: men and women together; the split is kept alongside.
LEVELS = [
    ("slams", "Grand Slams", ["slam_atp", "slam_wta"]),
    ("k1000", "Masters 1000, WTA 1000 and Finals", ["t1000_atp", "t1000_wta", "finals"]),
    ("k500", "500 events", ["t500_atp", "t500_wta"]),
    ("k250", "250 events", ["t250_atp", "t250_wta"]),
    ("qual", "Qualifying (Slams and tour)", ["slam_qual", "tour_qual"]),
    ("challenger", "Challenger and WTA 125", ["challenger", "wta125"]),
    ("itf", "ITF", ["itf_m", "itf_w", "itf_u"]),
    ("other", "Doubles, juniors, team events", ["doubles", "juniors", "team_exhib"]),
]
SPLIT = [
    ("slams_m", "Grand Slams, men", ["slam_atp"]), ("slams_w", "Grand Slams, women", ["slam_wta"]),
    ("k1000_m", "Masters 1000 and Finals", ["t1000_atp", "finals"]), ("k1000_w", "WTA 1000", ["t1000_wta"]),
    ("k500_m", "ATP 500", ["t500_atp"]), ("k500_w", "WTA 500", ["t500_wta"]),
    ("k250_m", "ATP 250", ["t250_atp"]), ("k250_w", "WTA 250", ["t250_wta"]),
    ("challenger_m", "ATP Challenger", ["challenger"]), ("challenger_w", "WTA 125", ["wta125"]),
    ("itf_m", "ITF men", ["itf_m"]), ("itf_w", "ITF women", ["itf_w"]),
]


# --------------------------------------------------------------------------------------
# closing prices
# --------------------------------------------------------------------------------------
def closing_prices(start: pd.Series, buffer_s: int = 0) -> pd.DataFrame:
    """Closing midpoint of outcome 0 per market: the last price-history point before start - buffer, if it is
    no older than MAX_CLOSE_AGE. `start` maps condition_id -> scheduled start (epoch seconds)."""
    parts = []
    for path in sorted(PRICE_HISTORY.glob("*/*.parquet")):
        ph = pd.read_parquet(path, columns=["condition_id", "t", "p"])
        ph = ph[ph.condition_id.isin(start.index)]
        if ph.empty:
            continue
        cut = ph.condition_id.map(start) - buffer_s
        ph = ph[(ph.t < cut) & (ph.t >= cut - MAX_CLOSE_AGE)]
        parts.append(ph.sort_values(["condition_id", "t"]).groupby("condition_id").agg(close=("p", "last"),
                                                                                         close_t=("t", "last")))
    close = pd.concat(parts)
    return close[~close.index.duplicated(keep="last")]


# --------------------------------------------------------------------------------------
# bets before the match
# --------------------------------------------------------------------------------------
def edge_vs_close(d: np.ndarray, pi0: np.ndarray, close0: np.ndarray) -> np.ndarray:
    """Expected profit at the closing price: signed outcome-0 shares x (closing price - price paid), both in
    outcome-0 terms. Equals shares x (close of the side backed - price paid for it)."""
    return d * (close0 - pi0)


def prematch_positions(markets: pd.DataFrame, close: pd.DataFrame, buffer_s: int = 0) -> tuple[pd.DataFrame, dict]:
    files = [f for f in sorted(B.TRADES_DIR.glob("*.parquet")) if f.name != "wallets.parquet"]
    fills = pd.concat([pd.read_parquet(f, columns=["condition_id", "asset", "outcome_index", "side", "size", "price",
                                                   "timestamp", "proxy_wallet", "tx_hash", "seq"]) for f in files],
                      ignore_index=True)
    use = markets[(markets.status == "decisive") & markets.event_type.notna()]
    use = use.merge(close, left_on="condition_id", right_index=True, how="inner")
    fills = fills[fills.condition_id.isin(use.condition_id)]
    index = pd.read_parquet(B.INDEX_DIR / "market_index.parquet", columns=["conditionId", "clobTokenIds"])
    index = index[index.conditionId.isin(use.condition_id)].drop_duplicates("conditionId")
    tokens = {c: json.loads(t) for c, t in zip(index.conditionId, index.clobTokenIds)}
    token0 = fills.condition_id.map({c: t[0] for c, t in tokens.items()}).to_numpy()
    token1 = fills.condition_id.map({c: t[1] for c, t in tokens.items()}).to_numpy()
    k = np.where(fills.asset.to_numpy() == token0, 0, np.where(fills.asset.to_numpy() == token1, 1, -1))
    fills = fills.assign(outcome_index=k)[k >= 0]
    fills = B.backed_bets(B.add_roles(fills))
    fills = fills.merge(use[["condition_id", "y0", "fee_rate", "rebate_rate", "start_ts", "close"]], on="condition_id")
    fills = B.pnl_and_fees(fills)            # fees and rebates need every fill of a market, so filter after
    pre = (fills.timestamp < fills.start_ts - buffer_s) & fills.price.between(*B.CONTESTED)
    fills = fills[pre].copy()
    fills["edge"] = edge_vs_close(fills.d.to_numpy(), fills.pi0.to_numpy(), fills.close.to_numpy())
    agg = fills.groupby(["proxy_wallet", "condition_id"], sort=False).agg(
        n=("size", "size"), stake=("stake", "sum"), edge=("edge", "sum"), fee=("fee", "sum"),
        rebate=("rebate", "sum"), gross=("gross", "sum"), net=("net", "sum")).reset_index()
    info = {"markets_with_close": int(len(use)), "prematch_fills": int(len(fills)),
            "prematch_stake": float(fills.stake.sum()), "edge_sum": float(fills.edge.sum())}
    return agg, info


# --------------------------------------------------------------------------------------
# sorting accounts (cross-fitted)
# --------------------------------------------------------------------------------------
def record(hist: pd.DataFrame) -> pd.DataFrame:
    """Per wallet: markets, money, edge per $1 and its standard error, one observation per market."""
    g = hist.groupby("proxy_wallet", sort=False)
    out = g.agg(n_hist=("condition_id", "size"), stake_hist=("stake", "sum"), edge_hist=("edge", "sum"))
    out["rate"] = out.edge_hist / out.stake_hist
    resid = hist.edge - hist.proxy_wallet.map(out.rate) * hist.stake
    ss = (resid ** 2).groupby(hist.proxy_wallet, sort=False).sum()
    n = out.n_hist
    out["se"] = np.sqrt(ss * n / (n - 1).where(n > 1)) / out.stake_hist
    out["z"] = out.rate / out.se.where(out.se > 0)
    return out


def group_of(n_hist: np.ndarray, z: np.ndarray) -> np.ndarray:
    n = np.asarray(n_hist)
    z = np.nan_to_num(np.asarray(z, dtype=float))
    out = np.full(len(n), "unsure", dtype=object)
    out[(n >= N_MIN) & (z >= Z)] = "win"
    out[(n >= N_MIN) & (z <= -Z)] = "lose"
    return out


def crossfit(pos: pd.DataFrame, folds: pd.Series) -> pd.DataFrame:
    pos = pos.assign(fold=pos.condition_id.map(folds))
    parts = []
    for f in sorted(pos.fold.unique()):
        rec = record(pos[pos.fold != f])
        parts.append(pos[pos.fold == f].merge(rec[["n_hist", "rate", "se", "z"]], left_on="proxy_wallet",
                                              right_index=True, how="left"))
    out = pd.concat(parts, ignore_index=True)
    out["n_hist"] = out.n_hist.fillna(0).astype(int)
    out["group"] = group_of(out.n_hist.to_numpy(), out.z.to_numpy())
    out["few_bets"] = out.n_hist < N_MIN
    return out


# --------------------------------------------------------------------------------------
# summaries with market-resampled intervals
# --------------------------------------------------------------------------------------
class Box:
    """Market x group sums with shared Poisson bootstrap weights over markets."""

    def __init__(self, rows: pd.DataFrame, rng: np.random.Generator, cols=("stake", "edge", "fee", "rebate", "net")):
        codes, self.markets = pd.factorize(rows.condition_id)
        g = pd.Categorical(rows.group, categories=GROUPS).codes
        m = len(self.markets)
        self.sum = {c: np.bincount(codes * 3 + g, weights=rows[c].to_numpy(), minlength=m * 3).reshape(m, 3)
                    for c in cols}
        self.w = rng.poisson(1.0, size=(B_DRAWS, m)).astype(float)
        self.accounts = rows.groupby("group").proxy_wallet.nunique().reindex(GROUPS).fillna(0).astype(int)
        self.accounts_all = int(rows.proxy_wallet.nunique())

    def tot(self, col, groups=None, boot=False):
        arr = self.sum[col] if groups is None else self.sum[col][:, [GROUPS.index(x) for x in groups]]
        per = arr.sum(axis=1)
        return self.w @ per if boot else per.sum()

    def ratio(self, num, den, groups=None, den_groups="same", scale=1.0):
        dg = groups if den_groups == "same" else den_groups
        d = self.tot(den, dg)
        est = scale * self.tot(num, groups) / d if d else float("nan")
        with np.errstate(divide="ignore", invalid="ignore"):
            boot = scale * self.tot(num, groups, True) / self.tot(den, dg, True)
        lo, hi = np.nanpercentile(boot, [2.5, 97.5])
        return {"est": float(est), "lo": float(lo), "hi": float(hi)}


def summary(rows: pd.DataFrame, seed: int = SEED) -> dict:
    b = Box(rows, np.random.default_rng(seed))
    b.sum["edge_net"] = b.sum["edge"] - b.sum["fee"] + b.sum["rebate"]
    has = {g: b.tot("stake", [g]) > 0 for g in GROUPS}
    out = {"markets": int(len(b.markets)), "accounts": b.accounts_all, "money": float(b.tot("stake"))}
    out["share"] = {g: b.ratio("stake", "stake", [g], None) for g in GROUPS}
    out["edge"] = {g: (b.ratio("edge", "stake", [g]) if has[g] else None) for g in GROUPS}
    out["edge_after_fees"] = {g: (b.ratio("edge_net", "stake", [g]) if has[g] else None) for g in GROUPS}
    out["result_after_fees"] = {g: (b.ratio("net", "stake", [g]) if has[g] else None) for g in GROUPS}
    # accounts counted once, by their verdict over the whole year (every match, not just other ones)
    verdict = rows.groupby("proxy_wallet").verdict.first()
    out["accounts_by_verdict"] = {g: int((verdict == g).sum()) for g in GROUPS}
    out["accounts_with_verdict_possible"] = int(rows.groupby("proxy_wallet").n_year.first().ge(N_MIN).sum())
    few = rows.few_bets.to_numpy()
    out["unsure_few_bets_share"] = float(rows.stake.to_numpy()[few].sum() / rows.stake.sum())
    # value clear winners take from everyone else, per $100 of all pre-match money
    out["winner_take_per_100"] = b.ratio("edge", "stake", ["win"], None, scale=100.0)
    out["loser_give_per_100"] = b.ratio("edge", "stake", ["lose"], None, scale=100.0)
    out["unsure_give_per_100"] = b.ratio("edge", "stake", ["unsure"], None, scale=100.0)
    return out


def passes(s: dict) -> bool:
    return s["markets"] >= MIN_MARKETS and all((v["hi"] - v["lo"]) / 2 <= MAX_HALF_WIDTH for v in s["share"].values())


def calibration(markets: pd.DataFrame, close: pd.DataFrame) -> dict:
    """Is the closing price right? Win rate of the side the close favoured, against the price it was given."""
    m = markets[(markets.status == "decisive")].merge(close, left_on="condition_id", right_index=True)
    fav = np.maximum(m.close, 1 - m.close)
    won = np.where(m.close >= 0.5, m.y0, 1 - m.y0)
    m = m.assign(fav=fav, won=won)
    bins = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]
    m["bin"] = pd.cut(m.fav, bins, right=False)
    out = {"bins": [], "by_level": []}
    for b_, g in m.groupby("bin", observed=True):
        out["bins"].append({"lo": b_.left, "hi": min(b_.right, 1.0), "markets": int(len(g)),
                            "price": float(g.fav.mean()), "won": float(g.won.mean()),
                            "won_se": float(np.sqrt(g.won.mean() * (1 - g.won.mean()) / len(g)))})
    for key, label, types in LEVELS:
        g = m[m.event_type.isin(types)]
        if len(g) < 100:
            continue
        # average price of the favourite vs how often it won, and the Brier score of the close
        brier = float(np.mean((g.close - g.y0) ** 2))
        out["by_level"].append({"key": key, "label": label, "markets": int(len(g)), "price": float(g.fav.mean()),
                                "won": float(g.won.mean()), "won_se": float(np.sqrt(g.won.var() / len(g))),
                                "brier": brier})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--buffer-minutes", type=int, default=0, help="close this many minutes before the start")
    ap.add_argument("--tag", default="", help="suffix for the output files (robustness runs)")
    args = ap.parse_args()
    buffer_s = args.buffer_minutes * 60
    markets = pd.read_parquet(STUDY / "markets.parquet")
    start = markets[(markets.status == "decisive") & markets.start_ts.notna()].set_index("condition_id").start_ts
    close = closing_prices(start, buffer_s)
    pos, info = prematch_positions(markets, close, buffer_s)
    folds = markets.set_index("condition_id").fold
    scored = crossfit(pos, folds)
    scored = scored.merge(markets[["condition_id", "event_type", "sport_date"]], on="condition_id")
    full = record(pos)
    full["verdict"] = group_of(full.n_hist.to_numpy(), full.z.to_numpy())
    scored["verdict"] = scored.proxy_wallet.map(full.verdict)
    scored["n_year"] = scored.proxy_wallet.map(full.n_hist)
    suffix = f"_{args.tag}" if args.tag else ""
    scored.to_parquet(STUDY / f"prematch_positions{suffix}.parquet", index=False)

    overall = summary(scored)
    levels, split = [], []
    for key, label, types in LEVELS:
        rows = scored[scored.event_type.isin(types)]
        if rows.condition_id.nunique():
            s = summary(rows)
            levels.append({"key": key, "label": label, "types": types, "passes_rule": passes(s), **s})
    for key, label, types in SPLIT:
        rows = scored[scored.event_type.isin(types)]
        if rows.condition_id.nunique():
            s = summary(rows)
            split.append({"key": key, "label": label, "types": types, "passes_rule": passes(s), **s})
    accounts = scored.groupby("proxy_wallet").agg(n=("condition_id", "size"), money=("stake", "sum"))
    full["group"] = full.verdict
    out = {
        "generated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "rules": {"min_other_matches": N_MIN, "z": Z, "buffer_minutes": args.buffer_minutes, "draws": B_DRAWS,
                  "min_markets": MIN_MARKETS, "max_half_width": MAX_HALF_WIDTH, "max_close_age_s": MAX_CLOSE_AGE},
        "info": {**info, "accounts": int(len(accounts)),
                 "accounts_10plus": int((accounts.n >= N_MIN).sum()),
                 "money_share_10plus": float(accounts.money[accounts.n >= N_MIN].sum() / accounts.money.sum()),
                 "verdicts_whole_year": {g: int((full.group == g).sum()) for g in GROUPS},
                 "verdicts_whole_year_10plus": int((full.n_hist >= N_MIN).sum())},
        "overall": overall, "levels": levels, "split": split,
        "calibration": calibration(markets, close),
    }
    (STUDY / f"prematch{suffix}.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    fmt = lambda r: "n/a" if r is None else f"{r['est']*100:+.2f} [{r['lo']*100:+.2f},{r['hi']*100:+.2f}]"
    print(json.dumps(out["info"], indent=1))
    for s in [dict(label="ALL", **overall)] + levels:
        print(f"{s['label'][:34]:<34} mk {s['markets']:>6} ${s['money']/1e6:>7.1f}M | share win {s['share']['win']['est']:.3f} "
              f"uns {s['share']['unsure']['est']:.3f} lose {s['share']['lose']['est']:.3f} | edge win {fmt(s['edge']['win'])} "
              f"lose {fmt(s['edge']['lose'])} uns {fmt(s['edge']['unsure'])} | pass {s.get('passes_rule', True)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
