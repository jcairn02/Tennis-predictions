"""Offline tests for the maker/taker split of the edge against the closing price."""
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "polymarket_sharp_money"))

import maker_economics as M  # noqa: E402
import prematch as P  # noqa: E402


def test_spread_plus_drift_is_the_edge_against_the_close():
    d = np.array([100.0, -100.0])          # a maker buys outcome 0 at 0.49; its taker sells it (backs outcome 1)
    pi0 = np.array([0.49, 0.49])
    mid, close = np.array([0.50, 0.50]), np.array([0.48, 0.48])
    spread, drift = M.decompose(d, pi0, mid, close)
    assert np.allclose(spread, [1.0, -1.0])          # the maker bought 1c under the middle of the book
    assert np.allclose(drift, [-2.0, 2.0])           # then the price fell 2c before the start
    assert np.allclose(spread + drift, P.edge_vs_close(d, pi0, close))


def test_midpoint_lookup_respects_market_and_age():
    span = M.SPAN
    key = np.array([0 * span + 100, 0 * span + 160, 1 * span + 50], dtype=np.int64)
    price = np.array([0.40, 0.42, 0.90])
    code = key // span
    got = M.lookup(key, price, code, np.array([0, 0, 1, 1], dtype=np.int64), np.array([170, 90, 60, 400], dtype=np.int64),
                   max_age=120)
    assert np.isclose(got[0], 0.42)                  # latest point at or before the fill
    assert np.isnan(got[1])                          # nothing before it in that market
    assert np.isclose(got[2], 0.90)                  # never borrows another market's price
    assert np.isnan(got[3])                          # too old (350 s)
