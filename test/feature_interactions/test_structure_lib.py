"""Tests of the STRUCTURE analyst's shared helpers (src/eda/feature_interactions/features/f01_structure_lib.py) and two
closed-form pieces of the builders. Result-free; no data files are read.
Run: ./python.sh -m pytest test/feature_interactions/test_structure_lib.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402


def test_clock_sum_release_rule_and_window():
    # key 1 released on days 10, 20, 30; a target on day 20 reads the day-20 release (lf + 1 <= es)
    out = S.clock_sum([1, 1, 1, 2], [10, 20, 30, 5], [1, 2, 3, 7], [1, 1, 1, 2, 3], [20, 25, 31, 4, 100])
    assert out.ravel().tolist() == [3.0, 3.0, 6.0, 0.0, 0.0]
    win = S.clock_sum([1, 1, 1], [10, 20, 30], [1, 2, 3], [1, 1], [25, 31], window=15)
    assert win.ravel().tolist() == [2.0, 5.0]


def test_clock_sum_decay():
    out = S.clock_sum([1, 1, 1], [10, 20, 30], [1, 2, 3], [1, 1], [20, 30], tau=10.0).ravel()
    assert np.allclose(out, [np.exp(-1) + 2, np.exp(-2) + 2 * np.exp(-1) + 3])


def test_clock_sum_keys_are_isolated():
    # changing another key's values must not move a target's sum, not even in the last bit
    rng = np.random.default_rng(0)
    keys = np.repeat(np.arange(50), 40)
    days = np.tile(np.arange(40) * 7.0, 50)
    vals = rng.normal(size=len(keys))
    base = S.clock_sum(keys, days, vals, np.arange(50), np.full(50, 150.0), tau=30.0)
    vals2 = vals.copy()
    vals2[keys == 7] += 1e6
    new = S.clock_sum(keys, days, vals2, np.arange(50), np.full(50, 150.0), tau=30.0)
    other = np.arange(50) != 7
    assert np.array_equal(base[other], new[other])


def test_signed_block_missing_member_contributes_zero():
    P = pd.DataFrame({"season": [2015] * 4})
    a = np.array([1.0, -1.0, 1.0, np.nan])
    b = np.array([np.nan, 2.0, -2.0, np.nan])
    x = S.signed_block(P, [(a, "+"), (b, "-")])
    assert np.isnan(x[3]) and np.isfinite(x[:3]).all()
    assert np.isclose(x[0], 1.0 / np.nanstd(a[:3]))


def test_break_points_per_game_matches_the_originator():
    from src.eda.feature_interactions.features.f08_clutch import bp_per_game
    assert abs(float(bp_per_game(0.62)) - 0.59) < 0.005
    assert abs(float(bp_per_game(0.70)) - 0.33) < 0.005


def test_iid_set_share_variance_is_symmetric_and_shrinks_with_dominance():
    from src.eda.feature_interactions.features.f06_volatility import var_iid_share
    v = var_iid_share(np.array([0.62, 0.55, 0.70]), np.array([0.55, 0.62, 0.70]))
    assert np.isclose(v[0], v[1])
    assert v[2] < var_iid_share(np.array([0.62]), np.array([0.62]))[0]


def test_leverage_matches_the_mechanics_numbers():
    lev = S.leverage(np.array([0.49, 0.49]), np.array([3, 5]), np.array(["TB7@6", "TB7@6"], dtype=object))
    assert np.allclose(lev, [4.78, 5.98], atol=0.01)
