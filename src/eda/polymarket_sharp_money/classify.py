"""Cross-fitted sharpness tiers for the Polymarket sharp-money study.

Sharpness is a gradient: a wallet's expected net return per dollar staked on contested tennis moneyline bets
(fills at 5-95c, after taker fees and estimated maker rebates). Individual win-loss records turned out to be
too noisy to rank most wallets on their own (study README, "Why tiers and not a per-wallet score"), so the
gradient is built from what a wallet's OTHER matches show:

  experience  number of other tennis moneyline matches it traded in the study window
  record      its risk-adjusted net result there, z = net P&L / sqrt(sum of per-market variance estimates)

Tiers, most to least sharp by design (their realised returns are measured in composition.py):
  winning     20+ other matches and z >= +2
  heavy       100+ other matches, record inside +/-2
  regular     10-99 other matches, record inside +/-2 (or fewer than 20 matches)
  occasional  1-9 other matches
  new         no other match
  losing      20+ other matches and z <= -2

Markets are split into five folds by physical match; a wallet's tier for a market in fold f comes only from
folds != f, so no outcome is used to classify the bet it decides.

Inputs:  data/studies/polymarket_sharp_money/{wallet_markets,markets}.parquet
Outputs: data/studies/polymarket_sharp_money/scored_positions.parquet   held-out (wallet, market) rows + tier

Usage:
    ./python.sh src/eda/polymarket_sharp_money/classify.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
STUDY = ROOT / "data" / "studies" / "polymarket_sharp_money"
TIERS = ["winning", "heavy", "regular", "occasional", "new", "losing"]
TIER_LABELS = {
    "winning": "Winning record",
    "heavy": "Heavy, unproven",
    "regular": "Regular",
    "occasional": "Occasional",
    "new": "New",
    "losing": "Losing record",
}
RECORD_MIN_MARKETS = 20
RECORD_Z = 2.0


def tier_of(n_hist: np.ndarray, z_hist: np.ndarray) -> np.ndarray:
    n = np.asarray(n_hist)
    z = np.nan_to_num(np.asarray(z_hist, dtype=float))
    tier = np.select([n == 0, n < 10, n < 100], ["new", "occasional", "regular"], default="heavy").astype(object)
    record = n >= RECORD_MIN_MARKETS
    tier[record & (z >= RECORD_Z)] = "winning"
    tier[record & (z <= -RECORD_Z)] = "losing"
    return tier


def history_stats(hist: pd.DataFrame) -> pd.DataFrame:
    """Per-wallet history from a set of (wallet, market) rows."""
    g = hist.groupby("proxy_wallet", sort=False).agg(
        n_hist=("condition_id", "size"), stake_hist=("stake", "sum"), net_hist=("net", "sum"),
        var_hist=("var_qv", "sum"), taker_hist=("stake_taker", "sum"))
    g["e_hist"] = g.net_hist / g.stake_hist
    g["z_hist"] = g.net_hist / np.sqrt(g.var_hist.where(g.var_hist > 0))
    g["taker_share_hist"] = g.taker_hist / g.stake_hist
    g["stake_per_market_hist"] = g.stake_hist / g.n_hist
    return g.drop(columns=["taker_hist"])


def crossfit(wm: pd.DataFrame, folds: pd.Series) -> pd.DataFrame:
    """Attach to every (wallet, market) row the wallet's history in the other folds and its tier."""
    wm = wm.assign(fold=wm.condition_id.map(folds))
    parts = []
    for f in sorted(wm.fold.unique()):
        stats = history_stats(wm[wm.fold != f])
        parts.append(wm[wm.fold == f].merge(stats, left_on="proxy_wallet", right_index=True, how="left"))
    scored = pd.concat(parts, ignore_index=True)
    scored["n_hist"] = scored["n_hist"].fillna(0).astype(int)
    scored["tier"] = tier_of(scored.n_hist.to_numpy(), scored.z_hist.to_numpy())
    return scored


def main() -> int:
    wm = pd.read_parquet(STUDY / "wallet_markets.parquet")
    markets = pd.read_parquet(STUDY / "markets.parquet", columns=["condition_id", "status", "event_type", "fold"])
    use = markets[(markets.status == "decisive") & markets.event_type.notna()]
    wm = wm[wm.condition_id.isin(use.condition_id) & (wm.stake > 0)]
    scored = crossfit(wm, use.set_index("condition_id").fold)
    scored.to_parquet(STUDY / "scored_positions.parquet", index=False)
    share = scored.groupby("tier").stake.sum() / scored.stake.sum()
    print(json.dumps({"rows": len(scored), "stake_share_by_tier": share.round(4).to_dict()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
