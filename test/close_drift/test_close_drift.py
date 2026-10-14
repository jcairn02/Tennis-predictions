"""Tests of the close-drift study (src/eda/close_drift/).

Run: ./python.sh -m pytest test/close_drift -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.close_drift import drift as D  # noqa: E402


def test_logistic_recovers_two_coefficients():
    rng = np.random.default_rng(1)
    x = rng.normal(0.0, 1.0, (100_000, 2))
    y = (rng.random(len(x)) < 1 / (1 + np.exp(-(0.9 * x[:, 0] + 0.2 * x[:, 1])))).astype(float)
    beta, se = D.logistic(x, y)
    assert abs(beta[0] - 0.9) < 3 * se[0] + 0.01 and abs(beta[1] - 0.2) < 3 * se[1] + 0.01


def test_realisation_is_one_when_the_disagreement_is_the_truth():
    rng = np.random.default_rng(2)
    close = rng.normal(0.0, 1.0, 100_000)
    delta = rng.normal(0.0, 0.3, len(close))
    y = (rng.random(len(close)) < 1 / (1 + np.exp(-(close + delta)))).astype(float)
    (c,), (se,) = D.logistic(delta[:, None], y, offset=close)
    assert abs(c - 1.0) < 3 * se + 0.01
