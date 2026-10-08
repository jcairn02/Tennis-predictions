"""Checks of the mathematics brainstormer's exact calculations (src/eda/feature_interactions/round0/mathematics/).

Run: ./python.sh -m pytest test/feature_interactions/test_round0_mathematics.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_PATH = ROOT / "src" / "eda" / "feature_interactions" / "round0" / "mathematics" / "markov_composition.py"
_spec = importlib.util.spec_from_file_location("markov_composition", _PATH)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def test_textbook_hold():
    assert abs(float(M.game(0.6)) - 0.7357) < 5e-5


def test_matches_stage2_iid_and_symmetries():
    out = M.verify()
    assert out["ok"]


def test_even_match_is_a_coin_and_bo5_amplifies():
    for m in (0.5, 0.6, 0.7):
        assert abs(float(M.match_win(m, m, 3)) - 0.5) < 1e-12
        assert abs(float(M.match_win(m, m, 5)) - 0.5) < 1e-12
    assert float(M.match_win(0.64, 0.62, 5)) > float(M.match_win(0.64, 0.62, 3)) > 0.5


def test_leverage_falls_with_serve_dominance():
    b = [float(M.lev_logit(mu, 3)) for mu in (0.2, 0.5, 0.8)]
    assert b[0] > b[1] > b[2]
    # dP/ds at fixed d is odd in d: zero at d = 0, negative for the favourite
    assert abs(float(M.dP_ds(0.62, 0.0, 3))) < 1e-9
    assert float(M.dP_ds(0.62, 0.04, 3)) < 0


def test_serve_return_exchange_invariance():
    """P(pA, pB) = P(1 - pB, 1 - pA) under every set rule: the leverage is even in the serve dominance around 1/2."""
    rng = np.random.default_rng(7)
    pa, pb = rng.uniform(0.3, 0.9, 500), rng.uniform(0.3, 0.9, 500)
    for rule in M.SET_RULES:
        for bo in (3, 5):
            assert np.abs(M.match_win(pa, pb, bo, rule) - M.match_win(1 - pb, 1 - pa, bo, rule)).max() < 1e-12


def test_quadratic_identity_prod_and_squares():
    rng = np.random.default_rng(3)
    Oa, Ob, Da, Db = rng.normal(0, 0.3, (4, 1000))
    xa, xb = Oa - Db, Ob - Da
    prod = Oa * (-Db) - Ob * (-Da)                 # the model's prod_<s>
    sq = (Oa ** 2 - Ob ** 2) - (Da ** 2 - Db ** 2)
    assert np.allclose(xa ** 2 - xb ** 2, sq + 2 * prod, atol=1e-12)
    # antisymmetry: swapping A and B negates all three
    prod_sw = Ob * (-Da) - Oa * (-Db)
    sq_sw = (Ob ** 2 - Oa ** 2) - (Db ** 2 - Da ** 2)
    assert np.allclose(prod_sw, -prod) and np.allclose(sq_sw, -sq)


@pytest.mark.parametrize("rule", ["power", "shin", "equal"])
def test_devig_quotes_sum_to_overround(rule):
    for p in (0.3, 0.6, 0.85):
        for marg in (0.03, 0.058, 0.1):
            qa, qb = M.quotes(p, marg, rule)
            assert abs(qa + qb - (1 + marg)) < 1e-9
            # a margin loaded this way makes the proportional de-vig under-confident for the favourite
            pp = qa / (qa + qb)
            if p > 0.5:
                assert pp < p


def test_shin_inverse():
    """Shin's de-vig formula recovers the true probability from quotes built by quotes(..., 'shin')."""
    p, marg = 0.73, 0.06
    qa, qb = M.quotes(p, marg, "shin")
    pi_ = qa + qb

    def shin_p(zz, q):
        return (np.sqrt(zz * zz + 4 * (1 - zz) * q * q / pi_) - zz) / (2 * (1 - zz))
    from scipy.optimize import brentq
    zz = brentq(lambda z: shin_p(z, qa) + shin_p(z, qb) - 1, 1e-9, 0.5)
    assert abs(shin_p(zz, qa) - p) < 1e-9


def test_day_noise_attenuation_matches_probit():
    mu, sd, dlt = 0.5, 0.27, 0.05
    b = float(M.lev_logit(mu, 3))
    z = float(M.lg(M.gh_expect_P(mu, dlt, sd, 3)))
    c_probit = 1 / np.sqrt(1 + np.pi * (b * sd) ** 2 / 8)
    assert abs(z / (b * dlt) - c_probit) < 0.01
    assert abs(float(expit(0.0)) - 0.5) < 1e-15
