"""Is posting prices (market making) where the edge is? Maker and taker economics on Polymarket tennis.

Every fill has a role: the taker is the first record of its transaction, the others are makers (their resting
orders were filled). For each fill, the midpoint of the book when it happened is the last minute-level price-history
point before it, if no more than MAX_MID_AGE old. A fill's result against the closing price then splits into
    spread   shares x (midpoint at the fill - price paid)       how far from the middle of the book it traded
    drift    shares x (closing midpoint - midpoint at the fill)  how the market then moved, for or against it
(spread + drift = the edge against the closing price used in prematch.py), then fees (takers pay) and rebates
(makers receive an estimated share). For fills during the match there is no closing price, so drift is measured
over 5 and 30 minutes, and the actual result at settlement is reported.

Pre-match fills also carry their account's closing-price group for that match (prematch.py, sorted on other matches).

Output: data/studies/polymarket_sharp_money/maker_economics.json

Usage:
    ./python.sh src/eda/polymarket_sharp_money/maker_economics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_positions as B  # noqa: E402
import prematch as P  # noqa: E402

STUDY = P.STUDY
MAX_MID_AGE = 120
SPAN = np.int64(1) << 34
SUMS = ["stake", "spread", "drift", "edge", "edge_net", "fee", "rebate", "net", "move5", "move30", "stake_mid"]


def price_paths(codes_of: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """All minute-level midpoints of outcome 0, as one axis sorted by (market code, time)."""
    keys, prices = [], []
    for path in sorted(P.PRICE_HISTORY.glob("*/*.parquet")):
        ph = pd.read_parquet(path, columns=["condition_id", "t", "p"])
        code = ph.condition_id.map(codes_of)
        ok = code.notna().to_numpy()
        keys.append(code.to_numpy()[ok].astype(np.int64) * SPAN + ph.t.to_numpy()[ok].astype(np.int64))
        prices.append(ph.p.to_numpy()[ok])
    key, price = np.concatenate(keys), np.concatenate(prices)
    order = np.argsort(key, kind="stable")
    key, price = key[order], price[order]
    return key, price, key // SPAN


def lookup(path_key, path_price, path_code, code, ts, max_age=None) -> np.ndarray:
    """Midpoint at or before `ts` in the same market (NaN if none, or older than max_age seconds)."""
    idx = np.searchsorted(path_key, code * SPAN + ts, side="right") - 1
    j = np.maximum(idx, 0)
    ok = (idx >= 0) & (path_code[j] == code)
    if max_age is not None:
        ok &= (ts - (path_key[j] - path_code[j] * SPAN)) <= max_age
    return np.where(ok, path_price[j], np.nan)


def decompose(d, pi0, mid0, close0) -> tuple[np.ndarray, np.ndarray]:
    """(spread, drift) in dollars for signed outcome-0 shares d traded at pi0 when the midpoint was mid0."""
    return d * (mid0 - pi0), d * (close0 - mid0)


def level_of(event_type: pd.Series) -> pd.Series:
    mapping = {t: key for key, _label, types in P.LEVELS for t in types}
    return event_type.map(mapping)


def process_bucket(path, use, codes_of, paths, groups) -> tuple[pd.DataFrame, pd.DataFrame]:
    f = pd.read_parquet(path, columns=["condition_id", "asset", "outcome_index", "side", "size", "price", "timestamp",
                                       "proxy_wallet", "tx_hash", "seq"])
    f = f[f.condition_id.isin(use.index)]
    if f.empty:
        return pd.DataFrame(), pd.DataFrame()
    t0 = f.condition_id.map(use.token0).to_numpy()
    t1 = f.condition_id.map(use.token1).to_numpy()
    k = np.where(f.asset.to_numpy() == t0, 0, np.where(f.asset.to_numpy() == t1, 1, -1))
    f = f.assign(outcome_index=k)[k >= 0]
    f = B.backed_bets(B.add_roles(f))
    info = use[["y0", "fee_rate", "rebate_rate", "start_ts", "close", "level"]]
    f = f.merge(info, left_on="condition_id", right_index=True)
    f = B.pnl_and_fees(f)
    f = f[f.price.between(*B.CONTESTED)].copy()
    code = f.condition_id.map(codes_of).to_numpy().astype(np.int64)
    ts = f.timestamp.to_numpy().astype(np.int64)
    key, price, pcode = paths
    mid0 = lookup(key, price, pcode, code, ts, MAX_MID_AGE)
    mid5 = lookup(key, price, pcode, code, ts + 300)
    mid30 = lookup(key, price, pcode, code, ts + 1800)
    d, pi0 = f.d.to_numpy(), f.pi0.to_numpy()
    spread, drift = decompose(d, pi0, mid0, f.close.to_numpy())
    has_mid = ~np.isnan(mid0)
    pre = ts < f.start_ts.to_numpy()
    f["phase"] = np.where(pre, "pre", "live")
    f["era"] = np.where(ts >= B.FEE_CASH_START, "cash_fee", "before")
    f["role"] = np.where(f.is_taker.to_numpy(), "taker", "maker")
    f["stake_mid"] = np.where(has_mid, f.stake, 0.0)
    f["spread"] = np.nan_to_num(spread)
    f["drift"] = np.where(pre, np.nan_to_num(drift), 0.0)
    f["edge"] = np.where(pre & has_mid, f.spread + f.drift, 0.0)
    f["edge_net"] = np.where(pre & has_mid, f.spread + f.drift - f.fee + f.rebate, 0.0)
    f["move5"] = np.where(has_mid, np.nan_to_num(d * (mid5 - mid0)), 0.0)
    f["move30"] = np.where(has_mid, np.nan_to_num(d * (mid30 - mid0)), 0.0)
    f = f.merge(groups, on=["proxy_wallet", "condition_id"], how="left")
    f["group"] = np.where(f.phase == "pre", f.group.fillna("none"), "none")
    cell = ["condition_id", "level", "phase", "era", "role", "group"]
    per_market = f.groupby(cell, sort=False)[SUMS].sum().reset_index()
    per_wallet = f[f.role == "maker"].groupby(["proxy_wallet", "level", "phase", "era"], sort=False).stake.sum().reset_index()
    return per_market, per_wallet


def ratios(cells: pd.DataFrame, rng: np.random.Generator, draws: int = 1000) -> dict:
    """Per-$1 components with market-resampled 95% ranges. Spread/drift/edge use money with a midpoint."""
    m = cells.groupby("condition_id")[SUMS].sum()
    w = rng.poisson(1.0, size=(draws, len(m))).astype(float)
    out = {"markets": int(len(m)), "money": float(m.stake.sum()), "money_with_mid": float(m.stake_mid.sum())}
    for num, den in [("spread", "stake_mid"), ("drift", "stake_mid"), ("edge", "stake_mid"),
                     ("edge_net", "stake_mid"), ("fee", "stake"), ("rebate", "stake"), ("net", "stake"),
                     ("move5", "stake_mid"), ("move30", "stake_mid")]:
        dsum = m[den].sum()
        if dsum <= 0:
            out[num] = None
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            boot = (w @ m[num].to_numpy()) / (w @ m[den].to_numpy())
        lo, hi = np.nanpercentile(boot, [2.5, 97.5])
        out[num] = {"est": float(m[num].sum() / dsum), "lo": float(lo), "hi": float(hi)}
    return out


def main() -> int:
    markets = pd.read_parquet(STUDY / "markets.parquet")
    use = markets[(markets.status == "decisive") & markets.event_type.notna()].set_index("condition_id")
    start = use.start_ts.dropna()
    close = P.closing_prices(start)
    use = use.join(close, how="left")
    use["level"] = level_of(use.event_type)
    index = pd.read_parquet(B.INDEX_DIR / "market_index.parquet", columns=["conditionId", "clobTokenIds"])
    index = index[index.conditionId.isin(use.index)].drop_duplicates("conditionId").set_index("conditionId")
    tokens = index.clobTokenIds.map(json.loads)
    use["token0"], use["token1"] = tokens.str[0], tokens.str[1]
    codes_of = {c: i for i, c in enumerate(use.index)}
    paths = price_paths(codes_of)
    groups = pd.read_parquet(STUDY / "prematch_positions.parquet", columns=["proxy_wallet", "condition_id", "group"])
    cells, wallets = [], []
    for path in sorted(B.TRADES_DIR.glob("*.parquet")):
        if path.name == "wallets.parquet":
            continue
        c, w = process_bucket(path, use, codes_of, paths, groups)
        cells.append(c)
        wallets.append(w)
        print(f"{path.name}: {len(c):,} cells", flush=True)
    cells, wallets = pd.concat(cells, ignore_index=True), pd.concat(wallets, ignore_index=True)
    cells.to_parquet(STUDY / "maker_cells.parquet", index=False)

    rng = np.random.default_rng(P.SEED)
    out = {"generated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "max_mid_age_s": MAX_MID_AGE,
           "fee_cash_start": int(B.FEE_CASH_START), "rows": []}

    def add(label, sel, **tags):
        sub = cells[sel]
        if sub.empty:
            return
        out["rows"].append({"label": label, **tags, **ratios(sub, rng)})

    for phase in ("pre", "live"):
        for era in ("cash_fee", "before"):
            for role in ("maker", "taker"):
                base = (cells.phase == phase) & (cells.era == era) & (cells.role == role)
                add("all", base, phase=phase, era=era, role=role, level="all", group="all")
                for key, _label, _types in P.LEVELS:
                    add(key, base & (cells.level == key), phase=phase, era=era, role=role, level=key, group="all")
                if phase == "pre":
                    for g in P.GROUPS:
                        add(g, base & (cells.group == g), phase=phase, era=era, role=role, level="all", group=g)
                        add(g, base & (cells.group == g) & cells.level.isin(["challenger", "itf", "qual"]), phase=phase,
                            era=era, role=role, level="lower", group=g)
    # how concentrated posting is: the ten largest maker accounts' share of maker money, by level (cash-fee era)
    conc = []
    for phase in ("pre", "live"):
        sub = wallets[(wallets.phase == phase) & (wallets.era == "cash_fee")]
        for key, label, _types in [("all", "All tennis", None)] + P.LEVELS:
            s = sub if key == "all" else sub[sub.level == key]
            by = s.groupby("proxy_wallet").stake.sum().sort_values(ascending=False)
            if len(by):
                conc.append({"phase": phase, "level": key, "makers": int(len(by)), "maker_money": float(by.sum()),
                             "top10_share": float(by.head(10).sum() / by.sum()),
                             "top1_share": float(by.head(1).sum() / by.sum())})
    out["concentration"] = conc
    (STUDY / "maker_economics.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    fmt = lambda r: "   n/a" if r is None else f"{r['est']*100:+.2f}"
    for r in out["rows"]:
        if r["level"] in ("all", "lower") or r["group"] == "all":
            print(f"{r['phase']:>4} {r['era']:>8} {r['role']:>5} {r['level']:>10} {r['group']:>6} ${r['money']/1e6:>7.1f}M "
                  f"spread {fmt(r['spread'])} drift {fmt(r['drift'])} edge {fmt(r['edge'])} fee {fmt(r['fee'])} "
                  f"reb {fmt(r['rebate'])} afterfees {fmt(r.get('edge_net'))} m5 {fmt(r['move5'])} m30 {fmt(r['move30'])} "
                  f"net {fmt(r['net'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
