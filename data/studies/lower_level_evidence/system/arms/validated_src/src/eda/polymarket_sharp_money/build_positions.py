"""Wallet-by-market positions for the Polymarket sharp-money study.

Inputs (all local):
    data/dump/odds/polymarket/trades/<bucket>.parquet   moneyline fills, both parties (polymarket_trades.py)
    data/dump/odds/polymarket/{event,market}_index.parquet
    data/studies/tennis_data_audit/polymarket/markets.jsonl.gz and the catalog extension   fee fields
Outputs (data/studies/polymarket_sharp_money/):
    markets.parquet          one row per market: event type, settlement, fee schedule, scheduled start, fold
    wallet_markets.parquet   one row per (wallet, market): stake, P&L, fees, variance, role, phase, price bands.
                             Unsuffixed columns cover contested fills (trade price 5-95c); *_all columns every fill
    build_summary.json       counts, exclusions and consistency checks

Every fill record is turned into the outcome it backs. BUY of outcome k at price p backs k at q = p; SELL of k
at p backs the other outcome at q = 1 - p (the complement it is short). Stake = shares * q is the most the
party can lose; payout is shares * settlement value of the backed outcome. Splits and merges are not trades,
but in a two-outcome market they are P&L-neutral, so P&L from fills alone is exact.

Role: the Data API lists a transaction's taker record first (see polymarket_trades.py); the others are makers.
Fees: taker fee = shares * rate * p * (1 - p) (Polymarket fee docs, read 25 Sep 2026) when the market has fees
enabled; maker rebates are approximated as rebateRate * that market's taker fees, shared pro rata by maker shares.

Variance of a wallet's P&L in one market under the no-skill null (its own trade prices are a martingale):
P&L = sum_j H_j (pi_{j+1} - pi_j) + H_J (Y - pi_J) with H the running position in outcome-0 shares, so
v = sum_j H_j^2 (pi_{j+1} - pi_j)^2 + H_J^2 pi_J (1 - pi_J) is an unbiased estimate of its variance.

Usage:
    ./python.sh src/eda/polymarket_sharp_money/build_positions.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
INDEX_DIR = ROOT / "data" / "dump" / "odds" / "polymarket"
TRADES_DIR = INDEX_DIR / "trades"
CENSUS_MARKETS = ROOT / "data" / "studies" / "tennis_data_audit" / "polymarket" / "markets.jsonl.gz"
EXTENSION_MARKETS = ROOT / "data" / "raw" / "public_dump" / "polymarket_catalog" / "markets_extension.jsonl.gz"
OUT_DIR = ROOT / "data" / "studies" / "polymarket_sharp_money"
N_FOLDS = 5
PRICE_BANDS = [0.0, 0.05, 0.25, 0.50, 0.75, 0.95, 1.000001]
CONTESTED = (0.05, 0.95)  # trade-price band of the contested fills (symmetric, so both parties agree)
# Taker fees as actually charged (calibrate_fees.py, 303 fills checked against /activity cash on 25 Sep 2026):
# nothing in cash before 28 Apr 2026 ~11:00 UTC, whatever the market's current schedule says; from 29 Mar to that
# moment taker BUYs paid 0.06 * (1 - p) per share in shares, which the trade records show directly; from then on
# rate * p * (1 - p) USDC per share on both sides, rate from the market's schedule (0.03 v2, 0.05 v3).
FEE_CASH_START = 1777374038  # 2026-04-28 11:00:38 UTC, the last fee taken in shares
MARKOUT_HORIZONS = (300, 3600)  # seconds
MARKOUT_COLUMNS = tuple(f"mo{h // 60}m" for h in MARKOUT_HORIZONS) + ("clv",)
BAND_NAMES = ["lt05", "05_25", "25_50", "50_75", "75_95", "ge95"]

# Event types. `parent` is the merge target when a type is too small to estimate on its own.
EVENT_TYPES = {
    "slam_atp": ("Grand Slam main draw, men", "slam"),
    "slam_wta": ("Grand Slam main draw, women", "slam"),
    "slam_qual": ("Grand Slam qualifying", "qualifying"),
    "finals": ("ATP/WTA Finals and Next Gen", "tour_top"),
    "t1000_atp": ("Masters 1000", "tour_top"),
    "t1000_wta": ("WTA 1000", "tour_top"),
    "t500_atp": ("ATP 500", "tour_mid"),
    "t500_wta": ("WTA 500", "tour_mid"),
    "t250_atp": ("ATP 250", "tour_mid"),
    "t250_wta": ("WTA 250", "tour_mid"),
    "tour_qual": ("Tour-level qualifying (1000/500/250)", "qualifying"),
    "challenger": ("ATP Challenger", "lower"),
    "wta125": ("WTA 125", "lower"),
    "itf_m": ("ITF men", "lower"),
    "itf_w": ("ITF women", "lower"),
    "itf_u": ("ITF, gender not identified", "lower"),
    "doubles": ("Doubles, all levels", "other"),
    "juniors": ("Grand Slam juniors", "other"),
    "team_exhib": ("Team events and exhibitions", "other"),
}
# Main-tour events the name classifier (measure_tier_terrain.py) files under the inferred lower tier because
# their sponsor names are missing from its alias lists. Tiers as in that file's alias lists (SP Open = WTA 250,
# Guadalajara Open = WTA 500, Nordic Open = ATP 250).
LEAGUE_OVERRIDES = {
    "BNP Paribas Nordic Open": "t250_atp",
    "Guadalajara Open Akron": "t500_wta",
    "Sao Paulo Open": "t250_wta",
}
ITF_NAME = re.compile(r"^(ITF\b|M15\b|M25\b|W15\b|W35\b|W50\b|W75\b|W100\b)")
# Polymarket names most ITF events "ITF <city>" with no gender or level, so gender comes from the players'
# full names in the dump's player files: Sackmann's ATP and WTA lists (which include ITF-level players) and the
# Live Tennis API list (atp/Challenger -> men, wta/WTA -> women). A name found under both genders is ignored.
SACKMANN_PLAYERS = {"M": ROOT / "data" / "dump" / "players" / "sackmann_archive" / "atp" / "atp_players.parquet",
                    "W": ROOT / "data" / "dump" / "players" / "sackmann_archive" / "wta" / "wta_players.parquet"}
LIVE_TENNIS_PLAYERS = ROOT / "data" / "dump" / "players" / "live_tennis_api_zenodo" / "players.parquet"
LIVE_TENNIS_TOURS = {"atp": "M", "challenger": "M", "wta": "W"}


def name_key(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[-'.’]", " ", text)
    return " ".join(re.sub(r"[^a-z ]", "", text).split())


def gender_lookup() -> dict[str, str | None]:
    seen: dict[str, set] = {}
    for gender, path in SACKMANN_PLAYERS.items():
        people = pd.read_parquet(path, columns=["name_first", "name_last"])
        for first, last in zip(people.name_first, people.name_last):
            seen.setdefault(name_key(f"{first} {last}"), set()).add(gender)
    people = pd.read_parquet(LIVE_TENNIS_PLAYERS, columns=["name", "tour"])
    for name, tour in zip(people.name, people.tour):
        gender = LIVE_TENNIS_TOURS.get(str(tour).lower())
        if gender:
            seen.setdefault(name_key(name), set()).add(gender)
    return {k: (next(iter(v)) if len(v) == 1 else None) for k, v in seen.items() if k}


def match_gender(title: str, lookup: dict[str, str | None]) -> str | None:
    """Gender of a singles match from 'League: Player A vs Player B', if the known players agree."""
    text = title.split(":", 1)[1] if ":" in title else title
    genders = {lookup.get(name_key(p)) for p in re.split(r"\s+vs\.?\s+", text.strip())} - {None}
    return next(iter(genders)) if len(genders) == 1 else None


def event_type(bucket: str | None, tour: str | None, league: str | None, gender: str | None = None) -> str | None:
    """Study event type from the index's inferred bucket, its tour, the provider league name and (for ITF)
    the gender inferred from player names."""
    league = (league or "").strip()
    base = re.sub(r",\s*Qualification.*$", "", league).strip()
    if ITF_NAME.match(league) or bucket == "itf":
        return {"M": "itf_m", "W": "itf_w"}.get(gender, "itf_u")
    if base in LEAGUE_OVERRIDES and bucket == "challenger_125_inferred":
        return "tour_qual" if "Qualification" in league else LEAGUE_OVERRIDES[base]
    wta = tour == "WTA"
    return {
        "slam_main": "slam_wta" if wta else "slam_atp",
        "slam_qualifying": "slam_qual",
        "tour_finals": "finals",
        "tour_1000": "t1000_wta" if wta else "t1000_atp",
        "tour_500": "t500_wta" if wta else "t500_atp",
        "tour_250": "t250_wta" if wta else "t250_atp",
        "tour_qualifying": "tour_qual",
        "challenger_125_inferred": "wta125" if wta else "challenger",
        "doubles": "doubles",
        "slam_juniors": "juniors",
        "team_exhibition": "team_exhib",
    }.get(bucket)


def fold_of(key: str) -> int:
    """Stable fold (0..N_FOLDS-1) for a physical-match key."""
    return int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % N_FOLDS


def settlement(outcome_prices) -> tuple[str, float | None]:
    """(status, settlement value of outcome 0) from Gamma outcomePrices."""
    try:
        values = [float(x) for x in (json.loads(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices)]
    except (TypeError, ValueError):
        return "unresolved", None
    if values == [1.0, 0.0]:
        return "decisive", 1.0
    if values == [0.0, 1.0]:
        return "decisive", 0.0
    if values == [0.5, 0.5]:
        return "void", 0.5
    return "unresolved", None


# --------------------------------------------------------------------------------------
# per-record transformation
# --------------------------------------------------------------------------------------
def add_roles(fills: pd.DataFrame) -> pd.DataFrame:
    """Taker = the first record (lowest seq) of each transaction within a market. Also the taker's fee taken in
    shares: on some fee-charging markets (seen in April 2026) a taker BUY record carries the shares received,
    fewer than the maker orders delivered; the shortfall is the fee (`share_fee`), and `size_gross` is the
    matched quantity. Checked against /activity cash amounts on 25 Sep 2026 (see the study README)."""
    keys = [fills["condition_id"], fills["tx_hash"]]
    first = fills.groupby(keys, sort=False)["seq"].transform("min")
    taker = fills["seq"].to_numpy() == first.to_numpy()
    fills["is_taker"] = taker
    maker_shares = pd.Series(np.where(taker, 0.0, fills["size"].to_numpy()), index=fills.index)
    matched = maker_shares.groupby(keys, sort=False).transform("sum").to_numpy()
    size = fills["size"].to_numpy()
    short = taker & (fills["side"].to_numpy() == "BUY") & (matched > size + 1e-4 * np.maximum(1.0, size))
    fills["share_fee"] = np.where(short, matched - size, 0.0)
    fills["size_gross"] = size + fills["share_fee"].to_numpy()
    return fills


def backed_bets(fills: pd.DataFrame) -> pd.DataFrame:
    """Vectorised: outcome backed, price q paid for it, stake, and signed outcome-0 shares d at price pi0,
    all on the matched quantity (size_gross when present)."""
    buy = fills["side"].to_numpy() == "BUY"
    k0 = fills["outcome_index"].to_numpy() == 0
    price = fills["price"].to_numpy()
    size = (fills["size_gross"] if "size_gross" in fills else fills["size"]).to_numpy()
    backs0 = buy == k0
    q = np.where(buy, price, 1.0 - price)
    fills["backs0"] = backs0
    fills["q"] = q
    fills["stake"] = size * q
    fills["d"] = np.where(backs0, size, -size)
    fills["pi0"] = np.where(backs0, q, 1.0 - q)
    return fills


def pnl_and_fees(fills: pd.DataFrame) -> pd.DataFrame:
    """Gross P&L at book prices on the matched quantity, taker fee, approximate maker rebate, net P&L.
    A fee taken in shares costs those shares' settlement value; otherwise, from FEE_CASH_START, a fee-charging
    market takes rate * p * (1 - p) USDC per share from the taker. Needs y0, fee_rate, rebate_rate, timestamp."""
    y_backed = np.where(fills["backs0"].to_numpy(), fills["y0"].to_numpy(), 1.0 - fills["y0"].to_numpy())
    size = (fills["size_gross"] if "size_gross" in fills else fills["size"]).to_numpy()
    share_fee = (fills["share_fee"] if "share_fee" in fills else pd.Series(0.0, index=fills.index)).to_numpy()
    price = fills["price"].to_numpy()
    fills["gross"] = size * (y_backed - fills["q"].to_numpy())
    taker = fills["is_taker"].to_numpy()
    cash = taker & (share_fee == 0) & (fills["timestamp"].to_numpy() >= FEE_CASH_START)
    usdc_fee = np.where(cash, size * fills["fee_rate"].to_numpy() * price * (1.0 - price), 0.0)
    fills["fee"] = usdc_fee + share_fee * y_backed
    pool = fills.groupby("condition_id", sort=False)["fee"].transform("sum") * fills["rebate_rate"]
    maker_size = pd.Series(np.where(taker, 0.0, size), index=fills.index)
    maker_total = maker_size.groupby(fills["condition_id"], sort=False).transform("sum")
    fills["rebate"] = np.where(taker, 0.0, pool.to_numpy() * size / np.where(maker_total > 0, maker_total, 1.0))
    fills["net"] = fills["gross"] - fills["fee"] + fills["rebate"]
    return fills


def markouts(fills: pd.DataFrame, horizons: tuple[int, ...] = MARKOUT_HORIZONS) -> dict[str, np.ndarray]:
    """Per-fill markouts: d * (reference price - fill price) in outcome-0 terms, where the reference is the
    market's last taker price at or before t + h (a taker record carries its order's average execution price).
    `clv` marks fills made before the scheduled start against the last taker price before it (closing line);
    other fills get 0. Positive = the market moved the wallet's way."""
    codes = pd.factorize(fills["condition_id"])[0].astype(np.int64)
    ts = fills["timestamp"].to_numpy().astype(np.int64)
    taker = fills["is_taker"].to_numpy()
    span = np.int64(1) << 34  # > any Unix time here; separates markets on one sorted axis
    path_key = codes[taker] * span + ts[taker]
    order = np.argsort(path_key, kind="stable")
    path_key, path_price, path_code = path_key[order], fills["pi0"].to_numpy()[taker][order], codes[taker][order]
    d, pi = fills["d"].to_numpy(), fills["pi0"].to_numpy()

    def ref_price(query_ts: np.ndarray) -> np.ndarray:
        idx = np.searchsorted(path_key, codes * span + query_ts, side="right") - 1
        ok = (idx >= 0) & (path_code[np.maximum(idx, 0)] == codes)
        return np.where(ok, path_price[np.maximum(idx, 0)], np.nan)

    out = {}
    for h in horizons:
        out[f"mo{h // 60}m"] = np.nan_to_num(d * (ref_price(ts + h) - pi))
    start = fills["start_ts"].to_numpy()
    pre = ts < start
    close = ref_price(np.where(pre, np.nan_to_num(start, nan=0).astype(np.int64) - 1, 0))
    out["clv"] = np.where(pre, np.nan_to_num(d * (close - pi)), 0.0)
    return out


def position_groups(wallet, cid, timestamp, seq) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Order rows by wallet, market and time, oldest first (within one second, reverse API order, which is
    newest first). Returns (order, group index per ordered row, first-row flags, last-row flags)."""
    w_codes = pd.factorize(pd.Series(wallet))[0].astype(np.int64)
    c_codes, c_uniques = pd.factorize(pd.Series(cid))
    order = np.lexsort((-np.asarray(seq), np.asarray(timestamp), c_codes, w_codes))
    gid = w_codes[order] * (len(c_uniques) + 1) + c_codes[order]
    first = np.r_[True, gid[1:] != gid[:-1]]
    last = np.r_[gid[1:] != gid[:-1], True]
    return order, np.cumsum(first) - 1, first, last


def qv_terms(d: np.ndarray, pi0: np.ndarray, group: np.ndarray, last: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-row variance terms (sum them by group) and running positions, rows in time order within groups:
    H_j^2 (pi_{j+1} - pi_j)^2 inside a group, H_J^2 pi_J (1 - pi_J) on its last row."""
    h = pd.Series(d).groupby(group).cumsum().to_numpy()
    nxt = np.r_[pi0[1:], np.nan]
    return np.where(last, h ** 2 * pi0 * (1.0 - pi0), h ** 2 * (nxt - pi0) ** 2), h


# --------------------------------------------------------------------------------------
# market table
# --------------------------------------------------------------------------------------
def fee_fields() -> dict[str, tuple]:
    """conditionId -> (fees_enabled, fee_type, rate, rebate_rate) from the census and the catalog extension."""
    out = {}
    for path in (CENSUS_MARKETS, EXTENSION_MARKETS):
        if not path.exists():
            continue
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if '"moneyline"' not in line:
                    continue
                m = json.loads(line)
                if m.get("sportsMarketType") != "moneyline" or not m.get("conditionId"):
                    continue
                sched = m.get("feeSchedule") or {}
                if isinstance(sched, str):
                    try:
                        sched = json.loads(sched)
                    except json.JSONDecodeError:
                        sched = {}
                out[m["conditionId"]] = (bool(m.get("feesEnabled")), m.get("feeType"),
                                         float(sched.get("rate") or 0.0), float(sched.get("rebateRate") or 0.0))
    return out


def build_markets(condition_ids: set[str]) -> pd.DataFrame:
    events = pd.read_parquet(INDEX_DIR / "event_index.parquet",
                             columns=["id", "slug", "title", "league", "sport_date", "bucket_slug", "bucket_tour", "gameId"])
    markets = pd.read_parquet(INDEX_DIR / "market_index.parquet",
                              columns=["id", "question", "conditionId", "sportsMarketType", "event_id", "closed",
                                       "outcomes", "outcomePrices", "clobTokenIds", "gameStartTime", "volumeNum"])
    markets = markets[(markets.sportsMarketType == "moneyline") & markets.conditionId.isin(condition_ids)]
    markets = markets.drop_duplicates("conditionId")
    df = markets.merge(events.rename(columns={"id": "event_id", "gameId": "game_id"}), on="event_id", how="left")
    df["league"] = df.league.fillna(df.title.map(lambda t: t.split(":")[0].strip() if isinstance(t, str) else None))
    lookup = gender_lookup()
    itf = (df.bucket_slug == "itf") | df.league.fillna("").str.match(ITF_NAME)
    df["itf_gender"] = [match_gender(t, lookup) if i and isinstance(t, str) else None for t, i in zip(df.title, itf)]
    df["event_type"] = [event_type(b, t, lg, g) for b, t, lg, g in
                        zip(df.bucket_slug, df.bucket_tour, df.league, df.itf_gender)]
    status = [settlement(x) if c == "True" else ("unresolved", None) for x, c in zip(df.outcomePrices, df.closed)]
    df["status"] = [s for s, _ in status]
    df["y0"] = [y for _, y in status]
    # unit-agnostic epoch seconds (pandas 3 parses these strings at microsecond resolution); NaN if unparseable
    start = pd.to_datetime(df.gameStartTime, utc=True, errors="coerce")
    df["start_ts"] = (start - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    fees = fee_fields()
    fee = [fees.get(c, (False, None, 0.0, 0.0)) for c in df.conditionId]
    df["fees_enabled"] = [f[0] for f in fee]
    df["fee_type"] = [f[1] for f in fee]
    df["fee_rate"] = [f[2] if f[0] else 0.0 for f in fee]
    df["rebate_rate"] = [f[3] if f[0] else 0.0 for f in fee]
    df["match_key"] = [str(g) if isinstance(g, str) and g and g != "None" else f"event:{e}"
                       for g, e in zip(df.game_id, df.event_id)]
    df["fold"] = [fold_of(k) for k in df.match_key]
    df["gamma_volume"] = pd.to_numeric(df.volumeNum, errors="coerce")
    df = df.rename(columns={"conditionId": "condition_id", "id": "market_id"})
    keep = ["condition_id", "market_id", "event_id", "slug", "title", "question", "league", "bucket_slug", "bucket_tour",
            "itf_gender", "event_type", "sport_date", "start_ts", "status", "y0", "fees_enabled", "fee_type", "fee_rate",
            "rebate_rate", "match_key", "fold", "gamma_volume", "outcomes", "clobTokenIds"]
    return df[keep].reset_index(drop=True)


# --------------------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------------------
def wallet_market_rows(fills: pd.DataFrame) -> pd.DataFrame:
    """Aggregate prepared fills (roles, bets, P&L, market columns) to one row per (wallet, market)."""
    order, group, first, last = position_groups(fills["proxy_wallet"].to_numpy(), fills["condition_id"].to_numpy(),
                                                fills["timestamp"].to_numpy(), fills["seq"].to_numpy())
    col = {name: fills[name].to_numpy()[order] for name in
           ("is_taker", "timestamp", "start_ts", "q", "stake", "gross", "fee", "rebate", "net", "d", "pi0")
           + MARKOUT_COLUMNS}
    col["size"] = fills["size_gross"].to_numpy()[order]
    var_terms, _ = qv_terms(col["d"], col["pi0"], group, last)
    taker = col["is_taker"]
    pre = col["timestamp"] < col["start_ts"]
    band = np.digitize(col["q"], PRICE_BANDS[1:-1])
    n_groups = int(group[-1]) + 1 if len(group) else 0

    def total(weights):
        return np.bincount(group, weights=weights, minlength=n_groups)

    out = {
        "proxy_wallet": fills["proxy_wallet"].to_numpy()[order][first],
        "condition_id": fills["condition_id"].to_numpy()[order][first],
        "n_rec": total(np.ones(len(group))), "n_taker": total(taker.astype(float)),
        "shares": total(col["size"]), "stake": total(col["stake"]),
        "stake_taker": total(np.where(taker, col["stake"], 0.0)), "stake_pre": total(np.where(pre, col["stake"], 0.0)),
        "gross": total(col["gross"]), "fee": total(col["fee"]), "rebate": total(col["rebate"]), "net": total(col["net"]),
        "net_taker": total(np.where(taker, col["net"], 0.0)), "net_pre": total(np.where(pre, col["net"], 0.0)),
        "h_final": total(col["d"]), "var_qv": total(var_terms),
        "first_ts": col["timestamp"][first], "last_ts": col["timestamp"][last],
        "stake_taker_pre": total(np.where(taker & pre, col["stake"], 0.0)),
        "net_taker_pre": total(np.where(taker & pre, col["net"], 0.0)),
        "fee_taker": total(np.where(taker, col["fee"], 0.0)),
    }
    for name in MARKOUT_COLUMNS:
        out[name] = total(col[name])
        out[f"{name}_taker"] = total(np.where(taker, col[name], 0.0))
    stake_q = total(col["stake"] * col["q"])
    out["mean_q"] = np.divide(stake_q, out["stake"], out=np.full(n_groups, np.nan), where=out["stake"] > 0)
    for i, name in enumerate(BAND_NAMES):
        out[f"stake_{name}"] = total(np.where(band == i, col["stake"], 0.0))
        out[f"net_{name}"] = total(np.where(band == i, col["net"], 0.0))
    return pd.DataFrame(out)


def check_zero_sum(fills: pd.DataFrame) -> dict:
    """Book-price P&L on matched quantities sums to zero across both parties of every market when taker records
    carry average execution prices; counts transactions whose taker and maker quantities still disagree."""
    by_market = fills.groupby("condition_id", sort=False).agg(gross=("gross", "sum"), stake=("stake", "sum"))
    rel = (by_market.gross.abs() / by_market.stake.where(by_market.stake > 0)).fillna(0)
    taker = fills[fills.is_taker].groupby(["condition_id", "tx_hash"], sort=False)["size_gross"].sum()
    maker = fills[~fills.is_taker].groupby(["condition_id", "tx_hash"], sort=False)["size"].sum()
    joined = pd.concat([taker.rename("taker"), maker.rename("maker")], axis=1).fillna(0.0)
    mismatch = (joined.taker - joined.maker).abs() > 1e-4 * np.maximum(1.0, joined.taker)
    return {"markets": int(len(by_market)), "max_abs_gross_sum_over_stake": float(rel.max()),
            "markets_gross_sum_gt_0.1pct_of_stake": int((rel > 0.001).sum()),
            "total_gross_sum": float(by_market.gross.sum()), "total_stake": float(by_market.stake.sum()),
            "transactions": int(len(joined)), "tx_taker_vs_maker_quantity_mismatch": int(mismatch.sum()),
            "tx_without_maker_record": int((joined.maker == 0).sum()),
            "taker_buys_with_fee_in_shares": int((fills.share_fee > 0).sum())}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(TRADES_DIR.glob("*.parquet"))
    files = [f for f in files if f.name != "wallets.parquet"]
    if not files:
        sys.exit(f"no staged trades in {TRADES_DIR}; run src/ingest/public_dump/polymarket_trades.py first")
    fills = pd.concat([pd.read_parquet(f, columns=["condition_id", "asset", "outcome_index", "side", "size", "price",
                                                   "timestamp", "proxy_wallet", "tx_hash", "seq"]) for f in files],
                      ignore_index=True)
    summary = {"fill_records": int(len(fills)), "trade_files": [f.name for f in files]}
    markets = build_markets(set(fills.condition_id.unique()))
    summary["markets_with_fills"] = int(fills.condition_id.nunique())
    summary["markets_by_status"] = markets.status.value_counts().to_dict()
    summary["markets_without_event_type"] = int(markets.event_type.isna().sum())

    # The outcome index comes from the token id and Gamma's token order, which settlement prices follow. In three
    # markets checked on 25 Sep 2026 the Data API's outcomeIndex was swapped relative to that order.
    tokens = {c: json.loads(t) for c, t in zip(markets.condition_id, markets.clobTokenIds)}
    token0 = fills.condition_id.map({c: t[0] for c, t in tokens.items()}).to_numpy()
    token1 = fills.condition_id.map({c: t[1] for c, t in tokens.items()}).to_numpy()
    asset = fills.asset.to_numpy()
    k = np.where(asset == token0, 0, np.where(asset == token1, 1, -1))
    summary["fills_outcome_index_swapped_vs_gamma"] = int(((k >= 0) & (k != fills.outcome_index.to_numpy())).sum())
    summary["fills_asset_not_a_market_token"] = int((k < 0).sum())
    fills = fills.assign(outcome_index=k)[k >= 0]

    fills = add_roles(fills)
    fills = backed_bets(fills)
    fills = fills.merge(markets[["condition_id", "y0", "fee_rate", "rebate_rate", "start_ts", "status"]],
                        on="condition_id", how="inner")
    summary["fill_records_by_market_status"] = fills.status.value_counts().to_dict()
    scored = fills[fills.status != "unresolved"].copy()
    scored["y0"] = scored["y0"].astype(float)
    scored = pnl_and_fees(scored)
    for name, values in markouts(scored).items():
        scored[name] = values
    summary["zero_sum_check"] = check_zero_sum(scored)
    # Contested fills (5-95c) are the bets on an open contest; beyond them are mostly settlement sweeps. A fill's
    # P&L is its own bet's P&L, so restricting to a price band needs no position netting.
    contested = (scored["price"] >= CONTESTED[0]) & (scored["price"] <= CONTESTED[1])
    summary["contested_band"] = CONTESTED
    summary["stake_share_contested"] = float(scored.loc[contested, "stake"].sum() / scored["stake"].sum())
    wm_all = wallet_market_rows(scored)
    wm_c = wallet_market_rows(scored[contested])
    keep_all = ["proxy_wallet", "condition_id", "n_rec", "stake", "gross", "fee", "rebate", "net", "var_qv", "h_final",
                "first_ts", "last_ts"] + [f"stake_{b}" for b in BAND_NAMES] + [f"net_{b}" for b in BAND_NAMES]
    wm = wm_all[keep_all].rename(columns={c: f"{c}_all" for c in keep_all[2:]}).merge(
        wm_c.drop(columns=[f"stake_{b}" for b in BAND_NAMES] + [f"net_{b}" for b in BAND_NAMES]),
        on=["proxy_wallet", "condition_id"], how="left")
    wm.to_parquet(OUT_DIR / "wallet_markets.parquet", index=False)
    stake = scored.groupby("condition_id").agg(stake_total=("stake", "sum"), n_rec=("size", "size"),
                                               n_wallets=("proxy_wallet", "nunique"),
                                               fees_total=("fee", "sum"))
    markets = markets.merge(stake, left_on="condition_id", right_index=True, how="left")
    markets.drop(columns=["clobTokenIds"]).to_parquet(OUT_DIR / "markets.parquet", index=False)
    summary.update(wallet_market_rows=int(len(wm)), wallets=int(wm.proxy_wallet.nunique()),
                   stake_total=float(scored.stake.sum()), fees_total=float(scored.fee.sum()),
                   rebates_total=float(scored.rebate.sum()), net_total=float(scored.net.sum()))
    (OUT_DIR / "build_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
