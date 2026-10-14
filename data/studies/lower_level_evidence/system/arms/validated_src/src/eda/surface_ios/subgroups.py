"""Pre-declared subgroups for the surface-IOS comparisons (written before any TabPFN result of a surface arm).

    surface         hard, clay, grass (carpet is too rare to report)
    early_season    either player has fewer than three earlier matches on the match's surface in the same calendar
                    year (any level of the history, the player's own earlier rounds included): the market-anchoring
                    study's "early" (docs/studies/market_anchoring/README.md, section 6.4), where the market-free model
                    trails the price most and where a pooled profile still mostly reflects the previous surface

Earlier = an earlier tournament week, or an earlier round of the same event (the player's own sequence).
Writes data/studies/surface_ios/subgroups.parquet (one row per pool match).
Run: ./python.sh src/eda/surface_ios/subgroups.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402

EARLY_BELOW = 3


def earlier_same_surface_year(td: dict) -> np.ndarray:
    """Per row: the player's earlier matches (own sequence) on the same surface in the same calendar year."""
    order = np.lexsort((td["round_order"], td["ev"], td["day"], td["surf"], td["year"], td["pid"]))
    key = np.stack([td["pid"], td["year"], td["surf"]], axis=1)[order]
    new_group = np.r_[True, (key[1:] != key[:-1]).any(axis=1)]
    pos = np.arange(len(order))
    start = np.maximum.accumulate(np.where(new_group, pos, 0))
    # rows of the same day and event share a round order only in round robins; count strictly earlier positions
    day, ev, rn = td["day"][order], td["ev"][order], td["round_order"][order]
    same_slot = np.r_[False, (day[1:] == day[:-1]) & (ev[1:] == ev[:-1]) & (rn[1:] == rn[:-1]) & ~new_group[1:]]
    slot_start = np.maximum.accumulate(np.where(~same_slot, pos, 0))
    count_sorted = slot_start - start
    out = np.empty(len(order), dtype=np.int64)
    out[order] = count_sorted
    return out


def main() -> int:
    pool = pd.read_parquet(C.CACHE / "pool.parquet")
    early_a = np.zeros(len(pool), dtype=np.int64)
    early_b = np.zeros(len(pool), dtype=np.int64)
    for t in ("atp", "wta"):
        td = C.load_tour(t)
        n_prior = earlier_same_surface_year(td)
        m = (pool["tour"] == t).to_numpy()
        early_a[m] = n_prior[pool.loc[m, "pos_a"].to_numpy()]
        early_b[m] = n_prior[pool.loc[m, "pos_b"].to_numpy()]
    out = pd.DataFrame({"match_id": pool["match_id"].to_numpy(), "surface": pool["surf"].map(C.SURF_NAMES).fillna("unknown"),
                        "prior_on_surface_a": early_a, "prior_on_surface_b": early_b,
                        "early_season": (np.minimum(early_a, early_b) < EARLY_BELOW)})
    out.to_parquet(C.OUT / "subgroups.parquet", index=False)
    C.log(f"wrote subgroups.parquet: {len(out):,} matches, early share {out['early_season'].mean():.3f}")
    print(out.groupby("surface")["early_season"].mean().round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
