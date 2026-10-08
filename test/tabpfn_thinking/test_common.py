"""The study's shared definitions: the A/B swap, symmetrization, the paired cluster interval (parity with the corrected
harness), the value fingerprint, the logistic fit, and the scorer's stacking and surrogate decomposition on toy data.

Run: ./python.sh -m pytest test/tabpfn_thinking/test_common.py
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

from src.eda.tabpfn_thinking import common as T  # noqa: E402


def toy_inputs(n=50, seed=1):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(rng.normal(size=(n, len(T.TABPFN_NAMES))), columns=T.TABPFN_NAMES)
    for c in T.CONTEXT:
        X[c] = rng.integers(0, 3, n).astype(float)
    X.iloc[0, 3] = np.nan
    return X


def test_feature_lists_are_consistent():
    assert len(T.NAMES) == len(set(T.NAMES)) == 53
    assert T.TABPFN_NAMES[0] == "odds_logit" and T.TABPFN_NAMES[1:] == T.NAMES
    assert set(T.DIFF) | set(T.CONTEXT) == set(T.NAMES) and not set(T.DIFF) & set(T.CONTEXT)
    assert set(T.CATEGORICAL) <= set(T.CONTEXT)
    assert sum(len(v) for v in T.GROUPS.values()) == len(T.NAMES)
    assert set(T.EVERYTHING) <= set(T.DIFF) and set(T.PROFILE16) <= set(T.DIFF) and len(T.PROFILE16) == 16
    # the audit's deprioritised families are not inputs
    assert not any(n.startswith(("bt", "mesr", "revalue", "sos_", "grinder")) for n in T.NAMES)


def test_flip_negates_differences_and_odds_and_keeps_context():
    X = toy_inputs()
    F = T.flip(X)
    for c in X.columns:
        a, b = X[c].to_numpy(), F[c].to_numpy()
        if c in T.ANTISYMMETRIC:
            assert np.allclose(b, -a, equal_nan=True), c
        else:
            assert np.allclose(b, a, equal_nan=True), c
    assert np.allclose(T.flip(F).to_numpy(), X.to_numpy(), equal_nan=True)


def test_symmetrize_is_exact_for_an_antisymmetric_forecast_and_averages_otherwise():
    p = np.array([0.2, 0.7, 0.55])
    assert np.allclose(T.symmetrize(p, 1 - p), p)
    assert np.allclose(T.symmetrize([0.6], [0.5]), [0.55])


def test_paired_interval_matches_the_corrected_harness():
    R = pytest.importorskip("src.eda.predictability_diagnostic.stage4_rundown")
    if not hasattr(R, "paired_interval"):
        pytest.skip("the harness under edit has no paired_interval")
    rng = np.random.default_rng(3)
    v = rng.normal(0.001, 0.01, 500)
    cl = rng.integers(0, 37, 500)
    assert T.paired_interval(v, cl) == pytest.approx(R.paired_interval(v, cl))


def test_compare_uses_four_week_blocks_from_a_monday():
    # blocks run 28 days from Monday 2010-01-04: 2022-01-17 opens block 157, 2022-02-14 block 158
    dates = pd.to_datetime(["2022-01-16", "2022-01-17", "2022-02-13", "2022-02-14"]).to_numpy()
    assert list(T.blocks(dates, 28)) == [156, 157, 157, 158]
    assert list(T.blocks(dates, 7)) == [627, 628, 631, 632]
    r = T.compare(np.array([0.7, 0.6, 0.65, 0.7]), np.array([0.6, 0.6, 0.6, 0.6]), dates)
    assert r["n"] == 4 and r["gain"] == pytest.approx(1000 * np.mean([0.1, 0.0, 0.05, 0.1]))
    assert r["blocks"] == 3 and r["weeks"] == 4


def test_fingerprint_is_value_exact_and_order_sensitive():
    X = toy_inputs()
    y = (np.arange(len(X)) % 2).astype(int)
    Q = toy_inputs(seed=2)
    a = T.fingerprint(X, y, Q)
    assert a == T.fingerprint(X.copy(), y.copy(), Q.copy())
    X2 = X.copy()
    X2.iloc[5, 5] = np.nextafter(X2.iloc[5, 5], np.inf)
    assert T.fingerprint(X2, y, Q) != a
    assert T.fingerprint(X[X.columns[::-1]], y, Q[Q.columns[::-1]]) != a
    with pytest.raises(ValueError):
        T.fingerprint(X, y + 2, Q)


def test_fit_logistic_recovers_coefficients():
    rng = np.random.default_rng(5)
    Z = rng.normal(size=(20000, 2))
    y = rng.random(20000) < expit(Z @ np.array([1.2, -0.5]))
    b, se = T.fit_logistic(Z, y)
    assert b == pytest.approx([1.2, -0.5], abs=4 * se.max())


def test_surrogate_separates_additive_from_interaction_structure():
    S = pytest.importorskip("src.eda.tabpfn_thinking.score")
    rng = np.random.default_rng(7)
    n = 6000
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n), "surface": rng.integers(0, 3, n).astype(float)})
    lin = 0.3 * X["a"] - 0.2 * X["b"]
    inter = 0.3 * X["a"] * (X["surface"] == 2)            # an antisymmetric effect that depends on the context
    for target, expect_inter in ((lin, False), (lin + inter, True)):
        XX = pd.concat([X, X.assign(a=-X["a"], b=-X["b"])], ignore_index=True)
        zz = np.r_[target, -target]
        tr = np.arange(len(zz)) % 2 == 0
        s = S.Surrogate(["a", "b"], ["surface"]).fit(XX[tr].reset_index(drop=True), zz[tr])
        p = s.predict(XX[~tr].reset_index(drop=True))
        r2 = {k: 1 - np.mean((zz[~tr] - v) ** 2) / np.mean(zz[~tr] ** 2) for k, v in p.items()}
        if expect_inter:
            # the part no additive fit can reach: 0.09 * E[a^2] * Var(1[surface=2]) = 0.02 of E[z^2] = 0.22
            assert r2["with_interactions"] - r2["additive"] == pytest.approx(0.02 / 0.22, abs=0.02)
            assert r2["with_interactions"] > 0.98
        else:
            assert r2["additive"] > 0.98 and r2["with_interactions"] - r2["additive"] < 0.01
