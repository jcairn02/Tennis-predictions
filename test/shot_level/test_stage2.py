"""Stage 2 of the shot-level study: the shrinkage constants, the memories' time rule, and the walk-forward base.

Run: ./python.sh -m pytest test/shot_level/test_stage2.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import stage2_features as F  # noqa: E402


def test_eb_constant_recovers_k():
    """Beta-binomial player-seasons with K = 100 (true rates Beta(mu K, (1 - mu) K)): the method of moments returns it
    within a third."""
    rng = np.random.default_rng(3)
    mu, K, n = 0.3, 100.0, 4000
    p = rng.beta(mu * K, (1 - mu) * K, n)
    d = rng.integers(100, 400, n).astype(float)
    x = rng.binomial(d.astype(int), p).astype(float)
    k = F.eb_constant(x, d, "share")
    assert 66 < k < 150


def test_eb_constant_no_spread_is_infinite():
    rng = np.random.default_rng(4)
    d = rng.integers(50, 200, 3000).astype(float)
    x = rng.binomial(d.astype(int), 0.4).astype(float)
    k = F.eb_constant(x, d, "share")
    assert not np.isfinite(k) or k > 1000          # no spread: infinite, or (sampling noise) very heavy shrinkage


def history_rows() -> pd.DataFrame:
    """Player P on days 0, 100 and 400 (three events), and once more on day 400 in a later round of the same event."""
    offs = [0, 100, 400, 400]
    dates = pd.to_datetime("2017-01-02") + pd.to_timedelta(offs, unit="D")
    rows = pd.DataFrame({"player_id": "P", "pcode": 0, "tournament_date": dates,
                         "day": dates.to_numpy().astype("datetime64[D]").astype("int64"),
                         "tournament_id": ["e0", "e1", "e2", "e2"], "round_order": [11, 11, 11, 12]})
    return rows


def test_forms_time_rule():
    rows = history_rows()
    V = np.array([[1.0], [2.0], [4.0], [8.0]])
    f = F.forms(rows, V)
    assert list(f["career"][:, 0]) == [0, 1, 3, 7]
    # last 52 weeks (364 days): day 400 sees day 100 (and the same event's earlier round), not day 0
    assert list(f["w52"][:, 0]) == [0, 1, 2, 6]
    # two-week half-life: day 400 weights day 100 by 2^(-300 / 14)
    assert f["dec2"][2, 0] == pytest.approx(2 ** (-400 / 14) + 2 * 2 ** (-300 / 14), rel=1e-6, abs=1e-12)
    assert f["dec2"][3, 0] == pytest.approx(2 ** (-400 / 14) + 2 * 2 ** (-300 / 14) + 4, rel=1e-6)


def test_walk_base_uses_only_earlier_seasons():
    """The walk-forward base for a season does not move when later seasons' results are redrawn."""
    from src.eda.shot_level import stage2_rundown as RD
    rng = np.random.default_rng(5)
    n = 6000
    frame = pd.DataFrame({"tour": "atp", "year": np.repeat(np.arange(2011, 2017), n // 6),
                          "p_mkt": rng.uniform(0.2, 0.8, n), "x": rng.normal(size=n)})
    frame["a_won"] = rng.random(n) < frame["p_mkt"]
    base = RD.walk_base(frame, "p_mkt", ["x"])
    pert = frame.copy()
    late = pert["year"] >= 2015
    pert.loc[late, "a_won"] = ~pert.loc[late, "a_won"]
    got = RD.walk_base(pert, "p_mkt", ["x"])
    early = frame["year"] <= 2015
    assert np.allclose(np.nan_to_num(base[early.to_numpy()]), np.nan_to_num(got[early.to_numpy()]))
    assert np.isnan(base[frame["year"].eq(2011).to_numpy()]).all()     # no earlier season to fit on
