"""Tests for the meta-stack study (src/eda/meta_stack/): the meta-models, the walk-forward windows, the frames sent to
the local model, and the estimation-cost formula the design argument rests on.

Run: ./python.sh -m pytest test/meta_stack
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.meta_stack import meta as M  # noqa: E402
from src.eda.meta_stack import run_local as R  # noqa: E402


def synthetic(n: int, rng: np.random.Generator, b=(1.05, 0.2)) -> tuple[M.Z, np.ndarray]:
    """A market and a correlated no-odds forecast; the truth is logistic in both (S2 is the correct model)."""
    zc = rng.normal(0, 1.0, n)
    zm = 0.8 * zc + rng.normal(0, 0.6, n)
    y = (rng.random(n) < expit(b[0] * zc + b[1] * zm)).astype(float)
    return {"mkt": zc, "noodds": zm, "base": zc + 0.1 * zm}, y


def test_log_odds_difference_drops_out():
    """The owner's three inputs with the log-odds difference make exactly the two-input model's forecasts."""
    z, y = synthetic(20_000, np.random.default_rng(1))
    b2, _ = M.fit("S2", z, y)
    b3, _ = M.fit("S3lit", z, y)
    np.testing.assert_allclose(M.predict("S3lit", z, b3), M.predict("S2", z, b2), atol=1e-6)
    np.testing.assert_allclose([b3[0] - b3[2], b3[1] + b3[2]], b2, atol=1e-4)       # only the combinations are fixed
    assert np.linalg.matrix_rank(M.design("S3lit", z)) == 2


@pytest.mark.parametrize("spec", ["S2", "S3p", "S3q", "E1", "E2", "best", "mkt"])
def test_antisymmetric(spec):
    """Swapping A and B negates every input; every meta-model then forecasts 1 - p."""
    z, y = synthetic(5_000, np.random.default_rng(2))
    b, _ = M.fit(spec, z, y)
    swapped = {k: -v for k, v in z.items()}
    np.testing.assert_allclose(M.predict(spec, swapped, b), 1 - M.predict(spec, z, b), atol=1e-12)


def test_windows():
    assert M.window("from2019", 2022) == [2019, 2020, 2021]
    assert M.window("from2014", 2019) == [2014, 2015, 2016, 2017, 2018]
    assert M.window("last3", 2022) == [2019, 2020, 2021]
    assert M.window("last5", 2016) == [2014, 2015]                     # nothing before the first forecast season
    assert M.window("from2019", 2019) == []


def test_walk_forward_reads_only_earlier_seasons():
    """Changing every result of the target season and later leaves the target's forecasts unchanged."""
    rng = np.random.default_rng(3)
    n = 12_000
    z, y = synthetic(n, rng)
    year = np.repeat(np.arange(2016, 2022), n // 6)
    tour = np.tile(np.array(["atp", "wta"]), n // 2)
    p1, c1 = M.walk_forward("S2", z, y, year, tour, [2019, 2020], lambda t: M.window("from2016", t))
    y2 = y.copy()
    y2[year >= 2020] = 1 - y2[year >= 2020]
    p2, _ = M.walk_forward("S2", z, y2, year, tour, [2019, 2020], lambda t: M.window("from2016", t))
    np.testing.assert_array_equal(p1[year == 2020], p2[year == 2020])
    assert np.isnan(p1[year < 2019]).all() and np.isfinite(p1[np.isin(year, [2019, 2020])]).all()
    assert c1[(2020, "atp")]["seasons"] == [2016, 2017, 2018, 2019]
    with pytest.raises(ValueError):
        M.walk_forward("S2", z, y, year, tour, [2019], lambda t: [2018, 2019])


def test_sandwich_trace_is_k_for_a_correct_model():
    z, y = synthetic(200_000, np.random.default_rng(4))
    b, _ = M.fit("S2", z, y)
    assert abs(M.sandwich("S2", z, y, b)["tr"] - 2.0) < 0.05


def test_excess_log_loss_is_k_over_2n():
    """The design argument's estimation term: a k-weight logistic meta-learner fitted on n matches loses, on new
    matches, k / (2 n) nats per match on average against the true weights (here k = 2, n = 1,000)."""
    rng = np.random.default_rng(5)
    b_true = np.array([1.05, 0.2])
    zt, _ = synthetic(400_000, rng, b_true)
    pt = expit(M.design("S2", zt) @ b_true)

    def expected_ll(b):                                   # exact expected log loss under the true probabilities
        q = np.clip(expit(M.design("S2", zt) @ b), 1e-12, 1 - 1e-12)
        return float(np.mean(-(pt * np.log(q) + (1 - pt) * np.log(1 - q))))

    base = expected_ll(b_true)
    n, reps = 1_000, 300
    excess = [expected_ll(M.fit("S2", *synthetic(n, rng, b_true))[0]) - base for _ in range(reps)]
    assert np.mean(excess) == pytest.approx(2 / (2 * n), rel=0.2)


@pytest.mark.parametrize("a,c", [(0.4, 0.01), (0.4, 0.1), (0.05, 0.02)])
def test_random_walk_window_optimum(a, c):
    """The README's optimum for a random-walk drift: a / W + c (W + 1)(2W + 1) / (6W) is smallest at
    W* = sqrt(3a / c + 1/2)."""
    W = np.linspace(0.2, 60, 200_000)
    cost = a / W + c * (W + 1) * (2 * W + 1) / (6 * W)
    assert W[np.argmin(cost)] == pytest.approx(np.sqrt(3 * a / c + 0.5), rel=1e-3)


def test_holdout_split_optimum():
    """The hold-out split's a / W + d W is smallest at W* = sqrt(a / d), where it equals 2 sqrt(a d)."""
    a, d = 0.4, 0.07
    W = np.linspace(0.1, 30, 300_000)
    cost = a / W + d * W
    assert W[np.argmin(cost)] == pytest.approx(np.sqrt(a / d), rel=1e-3)
    assert cost.min() == pytest.approx(2 * np.sqrt(a * d), rel=1e-6)


def test_frames_swap_only_the_differences():
    f = pd.DataFrame({"match_id": ["a", "b", "c", "d"], "year": [2013, 2014, 2015, 2015], "a_won": [1, 0, 1, 0],
                      "in_odds_logit": [0.5, -0.2, 0.3, 1.0], "in_elo_logit": [0.1, 0.2, -0.3, 0.4],
                      "in_tour": [0, 1, 0, 1], "in_surface": [1, 0, 2, 0], "in_round": [3, 4, 5, 6]})
    X_train, y, X_query, ids = R.frames(f, 2014, (2015,))
    assert list(X_train.columns) == ["odds_logit", "elo_logit", "tour", "surface", "round"]
    assert len(X_train) == 2 and list(y) == [1, 0] and list(ids) == ["c", "d"]
    np.testing.assert_array_equal(X_query["odds_logit"].to_numpy(), [0.3, 1.0, -0.3, -1.0])
    np.testing.assert_array_equal(X_query["elo_logit"].to_numpy(), [-0.3, 0.4, 0.3, -0.4])
    np.testing.assert_array_equal(X_query["surface"].to_numpy(), [2, 0, 2, 0])
    np.testing.assert_array_equal(X_query["round"].to_numpy(), [5, 6, 5, 6])


def test_holdout_fits_never_query_a_test_season():
    for spec in R.slots().values():
        assert max(spec["query"]) <= 2021 and min(spec["query"]) == spec["train_to"] + 1
