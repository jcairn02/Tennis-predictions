"""Offline tests for removing the margin and scoring (no network, no staged data)."""
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.sharp_benchmark import devig as D  # noqa: E402

ODDS = np.array([[1.52, 2.62], [1.19, 5.10], [1.01, 21.0], [2.05, 1.85], [3.40, 1.33], [1.53, 2.88]])


def shin_numeric(q: np.ndarray) -> np.ndarray:
    """Shin's probabilities for any number of outcomes, z found by bisection so they sum to one."""
    s = q.sum()

    def probs(z):
        return (np.sqrt(z * z + 4 * (1 - z) * q * q / s) - z) / (2 * (1 - z))

    lo, hi = 0.0, 0.5
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if probs(mid).sum() > 1 else (lo, mid)
    return probs((lo + hi) / 2)


def test_every_method_gives_two_chances_that_sum_to_one():
    for method in D.METHODS:
        p_w = D.devig(ODDS[:, 0], ODDS[:, 1], method)
        p_l = D.devig(ODDS[:, 1], ODDS[:, 0], method)
        assert np.allclose(p_w + p_l, 1.0, atol=1e-9), method
        assert np.all((p_w > 0) & (p_w < 1)), method


def test_proportional_is_normalised_implied_probability():
    p = D.devig([1.52], [2.62], "proportional")[0]
    assert np.isclose(p, (1 / 1.52) / (1 / 1.52 + 1 / 2.62))


def test_power_solves_its_equation():
    q_w, q_l = D.implied(ODDS[:, 0], ODDS[:, 1])
    p_w = D.power(q_w, q_l)
    k = np.log(p_w) / np.log(q_w)
    assert np.allclose(q_w ** k + q_l ** k, 1.0, atol=1e-9)
    assert np.all(k > 1)                     # a positive margin needs k above one


def test_shin_closed_form_matches_the_numerical_solution_for_two_outcomes():
    for w, l in ODDS:
        q = np.array([1 / w, 1 / l])
        assert np.isclose(D.devig([w], [l], "shin")[0], shin_numeric(q)[0], atol=1e-9)


def test_without_a_margin_every_method_returns_the_implied_chance():
    for method in D.METHODS:
        assert np.isclose(D.devig([1.25], [5.0], method)[0], 0.8), method


def test_log_loss_and_brier():
    assert np.isclose(D.log_loss([0.5])[0], np.log(2))
    assert np.isclose(D.log_loss([1.0])[0], 0.0)
    assert np.isfinite(D.log_loss([0.0])[0])
    assert np.isclose(D.brier([0.8])[0], 0.04)


def test_bootstrap_means_and_interval():
    x = np.tile([1.0, 2.0, 3.0, 4.0], 10)
    assert np.allclose(D.boot_means(np.ones((3, 40), dtype=np.float32), x), 2.5)
    rng = np.random.default_rng(0)
    boot = D.boot_means(D.weights(40, 500, rng), x)
    r = D.interval(x.mean(), boot, scale=1000.0)
    assert r["est"] == 2500.0 and r["lo"] < 2500.0 < r["hi"]
