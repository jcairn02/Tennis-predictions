"""Behavioral checks for the bounded profile retest, independent of data files."""
import numpy as np
import pandas as pd
from scipy.special import expit

from src.eda.feature_alpha_audit.profile_retest import (
    GRID, clustered_interval, fit_logistic, pick_lambda, rms_scale, walk_model,
)


def test_lambda_selection_never_uses_target_or_future_outcomes():
    years = np.repeat([2018, 2019, 2020, 2021], 200)
    losses = np.ones((800, len(GRID)))
    losses[:400, 1] = 0.5
    losses[400:, 4] = -1000
    j, n, validation_years = pick_lambda(years, 2020, losses, np.ones(800, dtype=bool))
    assert (j, n, validation_years) == (1, 400, [2018, 2019])


def test_side_swap_complements_predictions_and_preserves_ridge_fit():
    rng = np.random.default_rng(19)
    x = rng.normal(size=(800, 3))
    off = rng.normal(size=800)
    y = rng.binomial(1, expit(off + x[:, 0] / 3))
    b = fit_logistic(x, y, off, np.ones(3) * 0.01)
    swapped = fit_logistic(-x, 1-y, -off, np.ones(3) * 0.01)
    assert np.allclose(b, swapped, atol=1e-10)
    assert np.allclose(expit(off+x@b) + expit(-off-x@swapped), 1)
    assert np.allclose(rms_scale(x), rms_scale(-x))


def test_future_feature_changes_do_not_change_past_forecasts_or_scales():
    rng = np.random.default_rng(14)
    n = 1600
    x = rng.normal(size=n)
    market_eta = rng.normal(size=n)
    f = pd.DataFrame({"year": np.repeat([2017, 2018, 2019, 2020], 400),
                      "x": x, "p": expit(market_eta), "evaluation": True,
                      "a_won": rng.binomial(1, expit(market_eta + x / 4))})
    p, records = walk_model(f, ["x"], "p", True, False)
    f.loc[f.year == 2020, "x"] *= 1e8
    other, changed_records = walk_model(f, ["x"], "p", True, False)
    assert np.allclose(p[f.year < 2020], other[f.year < 2020], equal_nan=True)
    assert records == changed_records  # 2020 features cannot affect 2020 training or penalty choice


def test_cluster_interval_counts_repeated_matches_as_one_cluster():
    vals = np.array([0.001, 0.002, -0.001, 0.004])
    original = clustered_interval(vals, np.arange(4))
    repeated = clustered_interval(np.repeat(vals, 20), np.repeat(np.arange(4), 20))
    assert original["clusters"] == repeated["clusters"] == 4
    for key in ("gain_mll", "lo_mll", "hi_mll"):
        assert np.isclose(original[key], repeated[key])
