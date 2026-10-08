"""Line sharpening, step 3: the start of the early market.

Definition (the owner's, 6 Oct 2026: "enough consistent liquidity to make a bet > $300 at market on both sides"):
    bettable(t)   at minute t, a market buy of $X of EITHER player fills at an average price no more than d above
                  that player's mid (book_minutes.parquet; X = $300, d = 1c by default)
    onset         the first minute from which the market is bettable in at least CONSISTENT of the remaining
                  pre-match minutes, and bettable at that minute
Minutes before the market's first book snapshot in the block count as not bettable. A market listed before the
block began is left-censored: its onset can only be bounded.

On the sample block the onset is measured from the books. For every 2026 market it is predicted from what the
trade record shows, and the rules are scored against the book-measured onset on the block's markets:
    vol_<V>       the first taker order at which cumulative pre-match stake reaches $V
    hours_<H>     H hours before the close

Outputs (data/studies/line_sharpening/):
    book_onsets.parquet    block markets: book-measured onset per criterion, share of minutes bettable, censoring
    early_onsets.parquet   onset per market and rule (book rules for block markets, trade rules for all)
    calibration.json       minute-level bettability by tier and hours / volume, rule scores, chosen rule

Usage:
    ./python.sh src/eda/line_sharpening/calibrate.py
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

CONSISTENT = 0.9
CRITERIA = {"book_300_1c": (300, 0.01), "book_300_2c": (300, 0.02), "book_100_1c": (100, 0.01),
            "book_1000_1c": (1000, 0.01), "book_1000_2c": (1000, 0.02)}
MAIN = "book_300_1c"
VOL_GRID = (250, 500, 1_000, 2_000, 3_000, 5_000, 7_500, 10_000, 15_000, 25_000, 50_000, 100_000)
HOUR_GRID = (48, 36, 24, 18, 12, 9, 6, 4, 3, 2, 1)
HOUR_BINS = [0, 1, 2, 3, 6, 12, 24, 48, 1e6]
VOL_BINS = [-1, 250, 1_000, 2_500, 5_000, 10_000, 25_000, 50_000, 100_000, 1e12]


def bettable(bm: pd.DataFrame, x: int, d: float) -> np.ndarray:
    a = bm[f"vwap_a_{x}"].to_numpy() - bm.mid.to_numpy()
    b = bm[f"vwap_b_{x}"].to_numpy() - (1.0 - bm.mid.to_numpy())
    return (a <= d + 1e-9) & (b <= d + 1e-9)


def consistent_onset(t: np.ndarray, ok: np.ndarray, share: float = CONSISTENT) -> float:
    """First t with ok[t] and the share of ok minutes from t to the end >= share. t sorted (one per minute)."""
    if not ok.any():
        return np.nan
    rest = np.cumsum(ok[::-1])[::-1]               # ok minutes from i to the end
    n = np.arange(len(ok), 0, -1)
    good = ok & (rest >= share * n - 1e-9)
    i = np.flatnonzero(good)
    return float(t[i[0]]) if len(i) else np.nan


def full_grid(pm: pd.DataFrame, bm: pd.DataFrame, block0: float, block1: float) -> pd.DataFrame:
    """Every pre-match minute of every block market, with the book's values where known."""
    parts = []
    for m in pm.itertuples():
        lo = max(block0, m.created_ts)
        hi = min(block1, m.close_ts)
        g = np.arange(np.ceil(lo / 60) * 60, hi, 60.0)
        if len(g):
            parts.append(pd.DataFrame({"mkt": m.mkt, "t": g}))
    grid = pd.concat(parts, ignore_index=True)
    return grid.merge(bm, on=["mkt", "t"], how="left")


def book_onsets(pm: pd.DataFrame, grid: pd.DataFrame, block0: float, block1: float) -> pd.DataFrame:
    rows = []
    for name, (x, d) in CRITERIA.items():
        grid[name] = bettable(grid.fillna({"mid": np.nan}), x, d) & grid.mid.notna().to_numpy()
    meta = pm.set_index("mkt")
    for mkt, g in grid.groupby("mkt", sort=False):
        m = meta.loc[mkt]
        rec = {"mkt": mkt, "minutes": len(g), "book_known_share": float(g.mid.notna().mean()),
               "censored": bool(m.created_ts < block0), "complete": bool(m.created_ts >= block0 and m.close_ts <= block1),
               "first_book_ts": float(g.t[g.mid.notna()].min()) if g.mid.notna().any() else np.nan}
        t = g.t.to_numpy()
        for name in CRITERIA:
            ok = g[name].to_numpy()
            rec[f"{name}_onset"] = consistent_onset(t, ok)
            rec[f"{name}_first"] = float(t[ok][0]) if ok.any() else np.nan
            rec[f"{name}_share"] = float(ok.mean())
            rec[f"{name}_last_hour"] = float(ok[t >= m.close_ts - 3600].mean()) if (t >= m.close_ts - 3600).any() else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def cumulative_volume_at(tk: pd.DataFrame, mkts: np.ndarray, times: np.ndarray) -> np.ndarray:
    """Cumulative pre-match taker stake strictly before each (market, time)."""
    tk = tk.sort_values(["mkt", "ts"], kind="stable")
    cum = tk.groupby("mkt").stake.cumsum().to_numpy()
    v, _ = K.lookup(tk.mkt.to_numpy(), tk.ts.to_numpy() + 0.0, cum, mkts, times - 1e-6, max_age=None)
    return np.nan_to_num(v, nan=0.0)


def trade_onsets(pm: pd.DataFrame, tk: pd.DataFrame) -> pd.DataFrame:
    """Onsets from the trade record for every market: vol_<V> and hours_<H>."""
    tk = tk[tk.ts.to_numpy() < tk.mkt.map(pm.set_index("mkt").close_ts).to_numpy()].copy()
    tk["cum"] = tk.groupby("mkt").stake.cumsum()
    out = []
    for v in VOL_GRID:
        hit = tk[tk.cum >= v].groupby("mkt").ts.first()
        out.append(pd.DataFrame({"mkt": hit.index, "rule": f"vol_{v}", "onset_ts": hit.to_numpy() + 60.0}))
    for h in HOUR_GRID:
        t = pm.close_ts - 3600 * h
        ok = t >= pm.first_price_ts
        out.append(pd.DataFrame({"mkt": pm.mkt[ok], "rule": f"hours_{h}", "onset_ts": t[ok]}))
    return pd.concat(out, ignore_index=True)


def score_rules(bo: pd.DataFrame, tr: pd.DataFrame, pm: pd.DataFrame, crit: str) -> pd.DataFrame:
    """Each trade rule against the book onset on uncensored block markets: share where both say 'never',
    median and quartiles of (rule onset - book onset) in hours, and the share of the rule's onsets that fall
    before the book onset (the rule would call a market open too early)."""
    ref = bo[~bo.censored][["mkt", f"{crit}_onset"]].rename(columns={f"{crit}_onset": "book"})
    ref = ref.merge(pm[["mkt", "tier", "close_ts"]], on="mkt")
    rows = []
    for rule, g in tr.groupby("rule"):
        x = ref.merge(g[["mkt", "onset_ts"]], on="mkt", how="left")
        for tier, y in list(x.groupby("tier")) + [("all", x)]:
            both = y.book.notna() & y.onset_ts.notna()
            err = (y.onset_ts - y.book)[both] / 3600
            agree = ((y.book.isna() & y.onset_ts.isna()) | both).mean()
            rows.append({"rule": rule, "tier": tier, "markets": len(y), "book_open": int(y.book.notna().sum()),
                         "rule_open": int(y.onset_ts.notna().sum()), "open_agree": round(float(agree), 3),
                         "err_h_median": round(float(err.median()), 2) if len(err) else np.nan,
                         "err_h_abs_median": round(float(err.abs().median()), 2) if len(err) else np.nan,
                         "early_share": round(float((err < 0).mean()), 3) if len(err) else np.nan})
    return pd.DataFrame(rows)


def main() -> int:
    hours = sorted(p.stem for p in (K.PM_DIR / "books_pmxt").glob("*.parquet"))
    block0 = pd.Timestamp(hours[0], tz="UTC").timestamp()
    block1 = pd.Timestamp(hours[-1], tz="UTC").timestamp() + 3600
    pm_all = pd.read_parquet(K.OUT / "markets.parquet")
    pm_all = pm_all[pm_all.p_close.notna() & ~pm_all.suspect_close.fillna(True).astype(bool)]
    tk = pd.read_parquet(K.OUT / "takers.parquet")
    bm = pd.read_parquet(K.OUT / "book_minutes.parquet")
    pm = pm_all[pm_all.mkt.isin(bm.mkt.unique()) | ((pm_all.close_ts > block0) & (pm_all.created_ts < block1))]
    pm = pm[(pm.close_ts > block0) & (pm.created_ts < block1)]

    grid = full_grid(pm, bm, block0, block1)
    bo = book_onsets(pm, grid, block0, block1)
    bo = bo.merge(pm[["mkt", "tier", "level", "close_ts", "created_ts", "pre_volume"]], on="mkt")
    bo.to_parquet(K.OUT / "book_onsets.parquet", index=False)

    # minute-level bettability by tier and hours before the close, and by cumulative volume so far
    grid = grid.merge(pm[["mkt", "tier", "close_ts"]], on="mkt")
    grid["hours"] = (grid.close_ts - grid.t) / 3600
    grid["vol"] = cumulative_volume_at(tk, grid.mkt.to_numpy(), grid.t.to_numpy())
    grid["hbin"] = pd.cut(grid.hours, HOUR_BINS)
    grid["vbin"] = pd.cut(grid.vol, VOL_BINS)
    by_h = grid.groupby(["tier", "hbin"], observed=True)[list(CRITERIA)].mean().round(3)
    by_v = grid.groupby(["tier", "vbin"], observed=True)[list(CRITERIA)].mean().round(3)
    n_h = grid.groupby(["tier", "hbin"], observed=True).size()
    n_v = grid.groupby(["tier", "vbin"], observed=True).size()

    tr = trade_onsets(pm_all, tk)
    # Typical onset per level: the close minus the median book-measured lead of the level's block markets that
    # opened. Grand Slams take the 1000s' value (no Slam was played in the block).
    typical = {}
    for crit in ("book_300_1c", "book_300_2c"):
        u = bo[~bo.censored & bo[f"{crit}_onset"].notna()]
        lead = ((u.close_ts - u[f"{crit}_onset"]) / 3600).groupby(u.level).median()
        lead["Grand Slam"] = lead.get("Grand Slam", lead.get("1000 and Finals"))
        typical[crit] = {k: round(float(v), 2) for k, v in lead.items()}
        h = pm_all.level.map(typical[crit])
        t = pm_all.close_ts - 3600 * h
        ok = h.notna() & (t >= pm_all.first_price_ts)
        tr = pd.concat([tr, pd.DataFrame({"mkt": pm_all.mkt[ok], "rule": f"typical_{crit[5:]}", "onset_ts": t[ok]})],
                       ignore_index=True)
    scores = score_rules(bo, tr, pm, MAIN)
    book_rules = []
    for name in CRITERIA:
        b = bo[bo[f"{name}_onset"].notna()]
        book_rules.append(pd.DataFrame({"mkt": b.mkt, "rule": name, "onset_ts": b[f"{name}_onset"]}))
    onsets = pd.concat(book_rules + [tr], ignore_index=True)
    onsets.to_parquet(K.OUT / "early_onsets.parquet", index=False)

    summary = {
        "block": [hours[0], hours[-1]], "consistent_share": CONSISTENT, "criteria": CRITERIA, "main": MAIN,
        "block_markets": int(len(bo)), "uncensored": int((~bo.censored).sum()), "complete": int(bo.complete.sum()),
        "typical_lead_h_by_level": typical,
        "by_tier": {},
        "bettable_by_hours": {f"{t}|{h}": {**by_h.loc[(t, h)].to_dict(), "minutes": int(n_h.loc[(t, h)])}
                              for t, h in by_h.index},
        "bettable_by_volume": {f"{t}|{v}": {**by_v.loc[(t, v)].to_dict(), "minutes": int(n_v.loc[(t, v)])}
                               for t, v in by_v.index},
        "rule_scores": scores.to_dict(orient="records"),
    }
    for tier, g in bo.groupby("tier"):
        u = g[~g.censored]
        rec = {"markets": int(len(g)), "uncensored": int(len(u))}
        for name in CRITERIA:
            on = u[f"{name}_onset"]
            lead = (u.close_ts - on) / 3600
            rec[name] = {"ever_open_share": round(float(on.notna().mean()), 3),
                         "lead_h_quartiles": [round(float(x), 2) for x in lead.quantile([0.25, 0.5, 0.75])] if on.notna().any() else None,
                         "minutes_bettable_share": round(float(g[f"{name}_share"].mean()), 3),
                         "last_hour_bettable_share": round(float(g[f"{name}_last_hour"].mean()), 3)}
        summary["by_tier"][tier] = rec
    (K.OUT / "calibration.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary["by_tier"], indent=1, default=str))
    print(scores[scores.tier == "all"].sort_values("err_h_abs_median").head(12).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
