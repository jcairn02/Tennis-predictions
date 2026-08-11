"""Unit tests for the betting math layer."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.betting.staking import (clv_pct, ev_per_unit, implied_prob,
                                 kelly_fraction, log_growth,
                                 remove_vig_proportional, stake)


def test_implied_prob():
    assert implied_prob(2.0) == pytest.approx(0.5)
    assert implied_prob(1.25) == pytest.approx(0.8)
    with pytest.raises(ValueError):
        implied_prob(1.0)


def test_devig_proportional():
    # 1.95/1.95 two-way: 51.28% each side raw -> 50/50 devigged
    p = implied_prob(1.95)
    fair_a, fair_b = remove_vig_proportional(p, p)
    assert fair_a == pytest.approx(0.5)
    assert fair_a + fair_b == pytest.approx(1.0)


def test_ev_per_unit_signs():
    assert ev_per_unit(0.5, 2.0) == pytest.approx(0.0)      # fair coin at evens
    assert ev_per_unit(0.55, 2.0) == pytest.approx(0.10)    # +10% edge
    assert ev_per_unit(0.45, 2.0) < 0


def test_kelly_fraction():
    # p=0.55 at evens: f* = (0.55*2-1)/(2-1) = 0.10
    assert kelly_fraction(0.55, 2.0) == pytest.approx(0.10)
    assert kelly_fraction(0.40, 2.0) == 0.0                  # negative edge -> 0


def test_stake_cap_and_multiplier():
    # full Kelly 10% * 0.33 = 3.3% of 1000 = 33
    assert stake(0.55, 2.0, 1000.0, kelly_multiplier=0.33, cap_fraction=0.05) == pytest.approx(33.0)
    # big edge hits the 5% cap: full Kelly would be 30%
    assert stake(0.65, 2.0, 1000.0, kelly_multiplier=1.0, cap_fraction=0.05) == pytest.approx(50.0)
    assert stake(0.40, 2.0, 1000.0) == 0.0


def test_clv_pct():
    assert clv_pct(2.10, 2.00) == pytest.approx(5.0)   # beat the close by 5%
    assert clv_pct(1.90, 2.00) == pytest.approx(-5.0)


def test_log_growth_peaks_at_kelly():
    p, odds = 0.55, 2.0
    f_star = kelly_fraction(p, odds)
    g_star = log_growth(p, odds, f_star)
    assert g_star > log_growth(p, odds, f_star / 2)
    assert g_star > log_growth(p, odds, min(0.99, f_star * 2))
