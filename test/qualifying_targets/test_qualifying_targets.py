"""Offline tests of the qualifying-targets study's arithmetic (no data files, no GPU).

    ./python.sh -m pytest test/qualifying_targets -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.qualifying_targets import prices as PR  # noqa: E402
from src.eda.qualifying_targets import score as SCO  # noqa: E402


def test_devig_and_coherence():
    p = PR.devig([1.5], [2.75])
    assert np.isclose(p[0], (1 / 1.5) / (1 / 1.5 + 1 / 2.75))
    assert PR.coherent([1.9], [1.9]).all()                  # overround 1.053
    assert not PR.coherent([1.5], [1.5]).any()              # overround 1.33: not a quote
    assert not PR.coherent([2.2], [2.2]).any()              # overround 0.91: below 1
    assert not PR.coherent([np.nan], [1.9]).any()


def test_power_devig_sums_to_one_and_shrinks_the_longshot():
    d_a, d_b = np.array([1.2, 2.63]), np.array([4.74, 1.508])
    p = SCO.power_devig(d_a, d_b)
    k_check = (1 / d_a) ** 1 + (1 / d_b) ** 1
    assert (k_check > 1).all()
    prop = PR.devig(d_a, d_b)
    # the power method gives the favourite more and the longshot less than the proportional method
    assert p[0] > prop[0] and p[1] < prop[1]


def test_side_lines_orient_to_side_a():
    o = pd.DataFrame({"eid": [1, 2], "part_a": [10, 21], "part_b": [11, 20]})
    lines = pd.DataFrame({"kind": ["last"] * 4, "paid": [20] * 4, "eid": [1, 1, 2, 2], "partid": [10, 11, 20, 21],
                          "pri": [1.5, 2.6, 1.8, 2.05], "tim_ms": [1.0, 2.0, 3.0, 4.0]})
    pa, pb, t = PR.side_lines(o, lines, "last", 20)
    assert list(pa) == [1.5, 2.05] and list(pb) == [2.6, 1.8] and list(t) == [2.0, 4.0]


def _info(n_blocks=6):
    ids = pd.Index([f"m{i}" for i in range(4 * n_blocks)])
    return pd.DataFrame({"y": np.tile([1.0, 0.0, 1.0, 0.0], n_blocks),
                         "block": np.repeat(np.arange(n_blocks), 4)}, index=ids)


def test_bets_pick_the_positive_ev_side_and_count_profit():
    info = _info()
    ids = info.index
    q = np.tile([0.6, 0.6, 0.3, 0.5], 6)
    d_a = np.tile([2.0, 2.0, 2.0, 1.9], 6)          # EV_a = 0.2, 0.2, -0.4, -0.05
    d_b = np.tile([1.8, 1.8, 1.8, 1.9], 6)          # EV_b = -0.28, -0.28, 0.26, -0.05
    r = SCO.bets(info, ids, q, d_a, d_b, 0.0)
    # per 4 matches: A on m0 (won, +1), A on m1 (lost, -1), B on m2 (A won: lost, -1), no bet on m3
    assert r["bets"] == 18 and r["won"] == 6
    assert np.isclose(r["profit"], 6 * (1.0 - 1.0 - 1.0))
    assert np.isclose(r["roi"], -6 / 18)
    assert r["roi_lo"] <= r["roi"] <= r["roi_hi"]
    r2 = SCO.bets(info, ids, q, d_a, d_b, 0.21)     # only the B bets (EV 0.26) clear 0.21
    assert r2["bets"] == 6


def test_bets_refuse_incoherent_odds():
    info = _info(2)
    with pytest.raises(SystemExit):
        SCO.bets(info, info.index, np.full(8, 0.5), np.full(8, 2.5), np.full(8, 2.5), 0.0)


def test_training_masks_of_the_arms():
    from src.eda.qualifying_targets import fits as F

    class P:   # flip needs the kinds of the inputs; one diff input and one context input
        pass

    main = pd.DataFrame({"match_id": [f"a{i}" for i in range(6)], "season": [2013, 2017, 2018, 2019, 2020, 2020],
                         "a_won": [1, 0, 1, 0, 1, 0], "in_x": np.arange(6.0), "in_c": np.ones(6)})
    q = pd.DataFrame({"match_id": [f"q{i}" for i in range(5)], "season": [2017, 2018, 2019, 2020, 2020],
                      "a_won": [1, 1, 0, 0, 1], "in_x": np.arange(5.0) + 10, "in_c": np.ones(5)})
    orig = F.A.flip
    F.A.flip = lambda X, P_: X.assign(x=-X["x"])
    try:
        X0, y0, n0, b0 = F.job("M0", 2020, P, ["x", "c"], main, q)
        X1, y1, n1, b1 = F.job("M1", 2020, P, ["x", "c"], main, q)
        X2, y2, n2, b2 = F.job("M2", 2020, P, ["x", "c"], main, q)
    finally:
        F.A.flip = orig
    assert list(X0["x"]) == [0, 1, 2, 3] and n0 == 0                       # main 2013-2019, frame order
    assert list(X1["x"]) == [0, 1, 2, 3, 11, 12] and n1 == 2                # then qualifying 2018-2019 (not 2017)
    assert list(X2["x"]) == [11, 12] and n2 == 2
    assert list(y1) == [1, 0, 1, 0, 1, 0]
    assert "main" in b0 and "main" in b1 and "main" not in b2
    assert list(b1["qual"][1]) == ["q3", "q4"] and len(b1["qual"][0]) == 4  # stored, then swapped
    assert list(b1["qual"][0]["x"]) == [13, 14, -13, -14]
