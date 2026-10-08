"""Line sharpening, step 5a: the early-versus-close betting sample.

The owner's question of 6 Oct 2026: if we bet at the early market, against betting at the close (crossing the
spread), how different is our performance? "Our" model is the current best (local TabPFN-3.5 on the closing odds
plus 53 inputs; docs/studies/meta_stack/README.md). This builds its sample: the 2026 main-tour matches of the
surface-Elo study's frame (data/studies/surface_elo_pieces/frame.parquet, which holds every input) that link to a
Polymarket market of this study, with P(player A wins) at

    early1c   the early market, typical onset at $300 within 1c (calibrate.py's `typical_300_1c`)
    early2c   the earlier, looser early market ($300 within 2c, `typical_300_2c`)
    close     the main close (build.py)

and the taker fee rate in force at each moment (src/eda/polymarket_sharp_money/build_positions.py's measurement):
none before 29 Mar 2026; about 6% x (1 - price) in shares on taker buys to 28 Apr 2026 11:00 UTC; then the market's
own schedule (3% or 5% x (1 - price) of the stake), 5% where the market is newer than the fee table.

Timing. A market exists only once both players are known, so at the early time each player's previous match is over.
`clean` marks the stricter sample of the surface-Elo study (both players in their first match of the event, previous
match at least 3 days earlier): there every input surely existed 24 hours before the start.

Output: data/studies/line_sharpening/timing_frame.parquet, timing_frame_counts.json
Usage:  ./python.sh src/eda/line_sharpening/timing_frame.py
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

SEP = ROOT / "data" / "studies" / "surface_elo_pieces"
SHARP = ROOT / "data" / "studies" / "sharp_benchmark" / "matches.parquet"
SHARP_MARKETS = ROOT / "data" / "studies" / "polymarket_sharp_money" / "markets.parquet"
SHARE_FEE_FROM = pd.Timestamp("2026-03-29", tz="UTC").timestamp()
CASH_FEE_FROM = 1777374038          # 2026-04-28 11:00:38 UTC (build_positions.FEE_CASH_START)
SHARE_FEE_RATE = 0.06
LATE_RATE = 0.05                    # markets missing from the fee table (listed after 21 Sep 2026)
RULES = {"early1c": "typical_300_1c", "early2c": "typical_300_2c"}


def fee_rate(t: np.ndarray, market_rate: np.ndarray) -> np.ndarray:
    """Taker fee per $1 staked is rate x (1 - price); the rate in force at time t."""
    return np.where(t < SHARE_FEE_FROM, 0.0, np.where(t < CASH_FEE_FROM, SHARE_FEE_RATE, market_rate))


def main() -> int:
    ep = pd.read_parquet(SEP / "early_price_frame.parquet",
                         columns=["match_id", "tour", "season", "a_won", "condition_id", "opener", "buffer_ok", "clean",
                                  "debut_season", "x_odds_logit", "p_early_a", "p_close_a"])
    ep = ep[(ep.season == 2026) & ep.condition_id.notna()].rename(columns={"p_early_a": "p_24h_a",
                                                                         "p_close_a": "p_30m_a"})
    sb = pd.read_parquet(SHARP, columns=["condition_id", "winner_outcome"]).dropna().drop_duplicates("condition_id")
    pm = pd.read_parquet(K.OUT / "markets.parquet",
                         columns=["condition_id", "mkt", "level", "tier", "start_ts", "close_ts", "p_close",
                                  "suspect_close", "first_price_ts"]).rename(columns={"p_close": "p0_close"})
    x = ep.merge(sb, on="condition_id", how="left").merge(pm, on="condition_id", how="inner")
    x = x[x.p0_close.notna() & x.winner_outcome.notna() & ~x.suspect_close.fillna(True).astype(bool)].copy()
    # outcome index of player A, and P(A) from outcome-0 prices
    idx_a = np.where(x.a_won.astype(bool), x.winner_outcome, 1 - x.winner_outcome).astype(int)
    x["idx_a"] = idx_a
    to_a = lambda p0: np.where(idx_a == 0, p0, 1.0 - p0)  # noqa: E731
    x["p_close"] = to_a(x.p0_close.to_numpy())
    x["t_close"] = x.close_ts
    pr = pd.read_parquet(K.OUT / "prices.parquet")
    pr = pr[pr.mkt.isin(x.mkt)]
    on = pd.read_parquet(K.OUT / "early_onsets.parquet")
    for name, rule in RULES.items():
        o = on[on.rule == rule].set_index("mkt").onset_ts
        t = x.mkt.map(o).to_numpy(dtype=float)
        v, _ = K.lookup(pr.mkt.to_numpy(), pr.t.to_numpy(), pr.p.to_numpy(), x.mkt.to_numpy(),
                        np.nan_to_num(t, nan=0.0))
        x[f"t_{name}"] = t
        x[f"p_{name}"] = np.where(np.isfinite(t), to_a(v), np.nan)
    fees = pd.read_parquet(SHARP_MARKETS, columns=["condition_id", "fees_enabled", "fee_rate"])
    x = x.merge(fees, on="condition_id", how="left")
    rate = np.where(x.fee_rate.notna(), x.fee_rate.fillna(0.0) * x.fees_enabled.fillna(False).astype(float), LATE_RATE)
    for name in ("early1c", "early2c", "close"):
        x[f"fee_{name}"] = fee_rate(x[f"t_{name}"].to_numpy(dtype=float), rate)
    x = x.rename(columns={"p_24h_a": "p_24h", "p_30m_a": "p_30m"})
    x["agree_close_30m"] = (x.p_close - x.p_30m).abs()
    keep = ["match_id", "tour", "season", "a_won", "condition_id", "mkt", "level", "tier", "opener", "buffer_ok", "clean",
            "debut_season", "x_odds_logit", "idx_a", "start_ts", "p_24h", "p_30m"] + \
           [f"{c}_{n}" for n in ("early1c", "early2c", "close") for c in ("t", "p", "fee")] + ["agree_close_30m"]
    x = x[keep].reset_index(drop=True)
    x.to_parquet(K.OUT / "timing_frame.parquet", index=False)
    both = x.p_early1c.notna() & x.p_close.notna()
    counts = {"frame_2026_linked": int(len(ep)), "with_study_market": int(len(x)),
              "with_early1c_and_close": int(both.sum()),
              "with_early2c_and_close": int((x.p_early2c.notna() & x.p_close.notna()).sum()),
              "clean_with_early1c": int((both & x.clean).sum()),
              "by_level": x[both].level.value_counts().to_dict(),
              "orientation_check_close_vs_30m_median_abs": round(float(x.agree_close_30m.median()), 4),
              "orientation_check_share_within_2c": round(float((x.agree_close_30m <= 0.02).mean()), 4),
              "fee_rate_at_close": x.fee_close.round(3).value_counts().to_dict()}
    (K.OUT / "timing_frame_counts.json").write_text(json.dumps(counts, indent=1), encoding="utf-8")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
