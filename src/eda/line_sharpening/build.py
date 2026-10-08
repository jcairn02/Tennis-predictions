"""Line sharpening, step 1: every 2026 singles match-winner market on Polymarket with its pre-match price path,
its taker orders, the detected start of play and the closing price.

Markets: the singles moneylines of src/eda/sharp_benchmark/build.py (load_markets), settled decisively, listed to
start from 1 Jan to 4 Oct 2026, at a level in common.TIER (juniors and team events are left out).

Start of play: Polymarket's listed start (gameStartTime) is within 5 minutes of the first point in only 49% of
2,370 main-tour markets checked against official first-point times, and 11% start 3+ hours after it. So the start
is detected from the price path (common.detect_start). The close is the last price-history point at least
CLOSE_BUFFER before the detected start; without a detected start, FALLBACK_BUFFER before the listed start.
Everything before the close is pre-match.

Taker orders: the first record of each transaction is the taker (build_positions.add_roles). Its price is the
order's average execution price; the maker records of the same transaction give the levels it took, so the best
and worst level and the number of levels walked are known. Stake = shares x price of the outcome backed.

Inputs (all local): data/dump/odds/polymarket/{event,market}_index.parquet, price_history/, trades/
Outputs (data/studies/line_sharpening/):
    markets.parquet       one row per market
    prices.parquet        pre-match price path of outcome 0 (every price-history point before the close)
    takers.parquet        pre-match taker orders
    build_summary.json    counts, exclusions, detector rates, price-check agreement

Usage:
    ./python.sh src/eda/line_sharpening/build.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.line_sharpening import common as K  # noqa: E402
from src.eda.polymarket_sharp_money import build_positions as B  # noqa: E402
from src.eda.sharp_benchmark import build as SB  # noqa: E402

FIRST, LAST = "2026-01-01", "2026-10-05"     # listed start window (the last day held complete is 4 Oct)
PRICE_MONTHS_FROM = "2025-12"


def load_markets() -> pd.DataFrame:
    pm = SB.load_markets()
    idx = pd.read_parquet(K.PM_DIR / "market_index.parquet",
                          columns=["conditionId", "sportsMarketType", "createdAt", "clobTokenIds"])
    idx = idx[idx.sportsMarketType == "moneyline"].drop_duplicates("conditionId")
    pm = pm.merge(idx.rename(columns={"conditionId": "condition_id"}).drop(columns="sportsMarketType"),
                  on="condition_id", how="left")
    start = pd.to_datetime(pm.start_ts, unit="s", utc=True)
    keep = (pm.status == "decisive") & pm.event_type.isin(K.TIER) & (start >= FIRST) & (start < LAST)
    pm = pm[keep].copy()
    pm["tier"] = pm.event_type.map(K.TIER)
    pm["level"] = pm.event_type.map(K.LEVEL)
    pm["created_ts"] = K.epoch(pd.to_datetime(pm.createdAt, utc=True, errors="coerce"))
    tokens = pm.clobTokenIds.map(lambda s: json.loads(s) if isinstance(s, str) and s.startswith("[") else [None, None])
    pm["token0"], pm["token1"] = tokens.str[0], tokens.str[1]
    pm = pm.drop(columns=["clobTokenIds", "createdAt", "outcome_list"]).reset_index(drop=True)
    pm["mkt"] = np.arange(len(pm), dtype=np.int32)          # integer key for vectorised lookups
    return pm


def load_prices(ids: set[str]) -> pd.DataFrame:
    parts = []
    for path in sorted((K.PM_DIR / "price_history").glob("*/*.parquet")):
        if path.stem < PRICE_MONTHS_FROM:
            continue
        ph = pd.read_parquet(path, columns=["condition_id", "t", "p"])
        parts.append(ph[ph.condition_id.isin(ids)])
    ph = pd.concat(parts, ignore_index=True)
    return ph.drop_duplicates(["condition_id", "t"], keep="last").sort_values(["condition_id", "t"], kind="stable")


def price_at(t: np.ndarray, p: np.ndarray, when: float) -> tuple[float, float]:
    i = np.searchsorted(t, when, side="right") - 1
    if i < 0 or when - t[i] > K.MAX_PRICE_AGE:
        return np.nan, np.nan
    return p[i], t[i]


def starts_and_closes(pm: pd.DataFrame, ph: pd.DataFrame) -> pd.DataFrame:
    """Validated start of play, decision time and both closes per market:
        close_ts       main close: the earlier of the listed start - FALLBACK_BUFFER and the validated start -
                       CLOSE_BUFFER. It cannot contain play that the price path shows.
        close_ext_ts   the validated start - CLOSE_BUFFER (listed start - FALLBACK_BUFFER without one): the true
                       close when a match starts after its listed time (a sensitivity check).
    suspect_close flags markets decided less than MIN_PLAY_H after the main close (play began before it)."""
    meta = pm.set_index("condition_id")
    rows = []
    for cid, g in ph.groupby("condition_id", sort=False):
        t, p = g.t.to_numpy(float), g.p.to_numpy(float)
        s = meta.start_ts[cid]
        slam = meta.event_type[cid] in ("slam_atp", "slam_wta")
        d, dec, tries = K.validated_start(t, p, s, K.MAX_PLAY_H_SLAM if slam else K.MAX_PLAY_H)
        close_ext = d - K.CLOSE_BUFFER if np.isfinite(d) else s - K.FALLBACK_BUFFER
        close = min(s - K.FALLBACK_BUFFER, close_ext)
        pc, pct = price_at(t, p, close)
        pe, pet = price_at(t, p, close_ext)
        suspect = bool(np.isfinite(dec) and dec < close + K.MIN_PLAY_H * 3600)
        rows.append((cid, d, dec, tries, close, pc, pct, close_ext, pe, pet, suspect, t[0], len(t)))
    out = pd.DataFrame(rows, columns=["condition_id", "play_ts", "decided_ts", "det_tries", "close_ts", "p_close",
                                      "p_close_t", "close_ext_ts", "p_close_ext", "p_close_ext_t", "suspect_close",
                                      "first_price_ts", "n_price_points"])
    out["close_basis"] = np.where(out.play_ts.notna() & (out.close_ts == out.close_ext_ts), "validated start",
                                  "listed start")
    return out


def taker_orders(pm: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Pre-match taker orders of every market, one row per transaction."""
    use = pm.set_index("condition_id")
    t_min = int(pd.Timestamp(PRICE_MONTHS_FROM + "-01", tz="UTC").timestamp())
    parts, check = [], {"taker_rows": 0, "price_matches_makers": 0, "tx_without_makers": 0}
    for path in sorted((K.PM_DIR / "trades").glob("*.parquet")):
        if path.name == "wallets.parquet":
            continue
        f = pd.read_parquet(path, columns=["condition_id", "asset", "side", "size", "price", "timestamp", "tx_hash",
                                           "seq"], filters=[("timestamp", ">=", t_min)])
        f = f[f.condition_id.isin(use.index)]
        if f.empty:
            continue
        tok0 = f.condition_id.map(use.token0).to_numpy()
        tok1 = f.condition_id.map(use.token1).to_numpy()
        k = np.where(f.asset.to_numpy() == tok0, 0, np.where(f.asset.to_numpy() == tok1, 1, -1))
        f = f.assign(outcome_index=k)[k >= 0]
        f = B.backed_bets(B.add_roles(f))
        f = f[f.timestamp.to_numpy() < f.condition_id.map(use.close_ext_ts).to_numpy()]
        mk = f[~f.is_taker]
        lv = (mk.assign(qt=1.0 - mk.q, w=mk["size"] * (1.0 - mk.q))
              .groupby(["condition_id", "tx_hash"], sort=False)
              .agg(best=("qt", "min"), worst=("qt", "max"), levels=("qt", "nunique"), maker_shares=("size", "sum"),
                   maker_cost=("w", "sum")))
        tk = f[f.is_taker][["condition_id", "tx_hash", "timestamp", "backs0", "q", "stake", "size_gross"]]
        tk = tk.rename(columns={"timestamp": "ts", "size_gross": "shares"}).merge(
            lv, left_on=["condition_id", "tx_hash"], right_index=True, how="left")
        vw = tk.maker_cost / tk.maker_shares
        check["taker_rows"] += len(tk)
        check["price_matches_makers"] += int((np.abs(vw - tk.q) <= 0.0015).sum())
        check["tx_without_makers"] += int(tk.best.isna().sum())
        parts.append(tk.drop(columns=["maker_cost"]))
    return pd.concat(parts, ignore_index=True), check


def main() -> int:
    K.OUT.mkdir(parents=True, exist_ok=True)
    pm = load_markets()
    summary = {"markets": int(len(pm)), "by_level": pm.level.value_counts().to_dict(),
               "listed_window": [FIRST, LAST]}
    ph = load_prices(set(pm.condition_id))
    sc = starts_and_closes(pm, ph)
    pm = pm.merge(sc, on="condition_id", how="left")
    summary["without_price_history"] = int(pm.n_price_points.isna().sum())
    summary["close_basis"] = pm.close_basis.value_counts(dropna=False).to_dict()
    gap = (pm.play_ts - pm.start_ts) / 60
    summary["detected_minus_listed_min"] = {
        lv: {q: round(float(gap[pm.level == lv].quantile(q)), 1) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}
        for lv in K.LEVELS}
    summary["validated_share_by_level"] = pm.groupby("level").play_ts.apply(lambda s: round(float(s.notna().mean()), 3)).to_dict()
    summary["suspect_close_by_level"] = pm.groupby("level").suspect_close.sum().astype(int).to_dict()
    summary["candidates_tried"] = pm.det_tries.value_counts().sort_index().to_dict()

    ph = ph.merge(pm[["condition_id", "mkt", "close_ext_ts"]], on="condition_id")
    pre = ph[ph.t <= ph.close_ext_ts][["mkt", "t", "p"]].sort_values(["mkt", "t"], kind="stable")
    pre.to_parquet(K.OUT / "prices.parquet", index=False)
    summary["prematch_price_points"] = int(len(pre))

    tk, check = taker_orders(pm)
    tk = tk.merge(pm[["condition_id", "mkt"]], on="condition_id").drop(columns=["condition_id"])
    tk = tk.sort_values(["mkt", "ts"], kind="stable")
    tk.to_parquet(K.OUT / "takers.parquet", index=False)
    summary["taker_check"] = check
    main = tk.ts.to_numpy() < tk.mkt.map(pm.set_index("mkt").close_ts).to_numpy()
    vol = pd.DataFrame({"pre_volume": tk[main].groupby("mkt").stake.sum(),
                        "pre_takers": tk[main].groupby("mkt").size(),
                        "pre_volume_ext": tk.groupby("mkt").stake.sum()})
    pm = pm.merge(vol, left_on="mkt", right_index=True, how="left").fillna(
        {"pre_volume": 0.0, "pre_takers": 0, "pre_volume_ext": 0.0})
    pm.to_parquet(K.OUT / "markets.parquet", index=False)
    summary["prematch_taker_orders"] = int(len(tk))
    summary["prematch_volume_by_level"] = pm.groupby("level").pre_volume.sum().round(0).to_dict()
    (K.OUT / "build_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
