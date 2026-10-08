"""Verification of temporal fitting, side symmetry and clustered uncertainty."""
import numpy as np
import pandas as pd

from src.eda.feature_alpha_audit.elo_retest import clustered_gain, walk_predictions


def fixture():
    rng = np.random.default_rng(947)
    x = rng.normal(size=(1800, 2))
    y = rng.binomial(1, 1 / (1 + np.exp(-(x[:, 0] + .3 * x[:, 1]))))
    return pd.DataFrame({"year": np.repeat([2017, 2018, 2019], 600), "a_won": y, "x": x[:, 0], "z": x[:, 1]})


def test_future_outcomes_and_feature_scale_do_not_change_earlier_forecasts():
    f = fixture()
    before, coeff = walk_predictions(f, ["x", "z"], train_from=2017, score_from=2018)
    changed = f.copy()
    changed.loc[changed.year == 2019, "a_won"] = 1 - changed.loc[changed.year == 2019, "a_won"]
    changed.loc[changed.year == 2019, "x"] *= 1000
    after, coeff2 = walk_predictions(changed, ["x", "z"], train_from=2017, score_from=2018)
    np.testing.assert_array_equal(before[f.year == 2018], after[f.year == 2018])
    assert coeff[0] == coeff2[0]


def test_swapping_sides_complements_forecasts():
    f = fixture()
    p, _ = walk_predictions(f, ["x", "z"], train_from=2017, score_from=2018)
    f[["x", "z"]] *= -1
    f.a_won = 1 - f.a_won
    q, _ = walk_predictions(f, ["x", "z"], train_from=2017, score_from=2018)
    np.testing.assert_allclose(q[np.isfinite(q)], 1 - p[np.isfinite(p)], atol=1e-10)


def test_cluster_interval_does_not_treat_duplicate_within_week_as_independent():
    values = np.array([-.003, .001, .002, .004, .006])
    a = clustered_gain(values, np.arange(5))
    b = clustered_gain(np.repeat(values, 20), np.repeat(np.arange(5), 20))
    for key in ("gain_mll", "lo_mll", "hi_mll"):
        np.testing.assert_allclose(a[key], b[key], atol=1e-12)
