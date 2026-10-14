"""Tests of the training-window study (src/eda/training_window/).

Run: ./python.sh -m pytest test/training_window -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.training_window import common as C  # noqa: E402
from src.eda.training_window import score as S  # noqa: E402

# a synthetic season column: 2010-2024, 3,000 matches each, shuffled like no frame is (order must not matter)
SEASONS = np.random.default_rng(0).permutation(np.repeat(np.arange(2010, 2025), 3000))


@pytest.mark.parametrize("arm", C.ARMS)
@pytest.mark.parametrize("season", C.SEASONS)
def test_no_arm_trains_on_the_season_or_later_or_before_the_floor(arm, season):
    for seed in C.SEEDS:
        m = C.train_mask(SEASONS, arm, season, seed)
        assert m.any()
        assert SEASONS[m].max() <= season - 1 and SEASONS[m].min() >= C.TRAIN_FROM


@pytest.mark.parametrize("n", (7, 5, 3))
@pytest.mark.parametrize("season", C.SEASONS)
def test_last_n_is_exactly_the_last_n_seasons_above_the_floor(n, season):
    m = C.train_mask(SEASONS, f"last{n}", season, 0)
    assert set(SEASONS[m]) == set(range(max(C.TRAIN_FROM, season - n), season))
    assert m.sum() == np.isin(SEASONS, list(range(max(C.TRAIN_FROM, season - n), season))).sum()


@pytest.mark.parametrize("n", (7, 5, 3))
def test_rand_n_matches_last_n_in_size_and_draws_anew_per_seed(n):
    season = 2024
    size = C.train_mask(SEASONS, f"last{n}", season, 0).sum()
    pool = C.train_mask(SEASONS, "exp", season, 0)
    draws = [C.train_mask(SEASONS, f"rand{n}", season, k) for k in C.SEEDS]
    for m in draws:
        assert m.sum() == size and not (m & ~pool).any()
    assert not np.array_equal(draws[0], draws[1])
    assert np.array_equal(draws[0], C.train_mask(SEASONS, f"rand{n}", season, 0))     # reproducible
    share_old = SEASONS[draws[0]] < season - n                                        # it does reach old seasons
    assert 0.2 < share_old.mean() < 0.9 or n == 7


def test_rand7_and_last7_equal_exp_where_the_floor_binds():
    for season in (2019, 2020):
        exp = C.train_mask(SEASONS, "exp", season, 0)
        assert np.array_equal(C.train_mask(SEASONS, "last7", season, 0), exp)
        assert np.array_equal(C.train_mask(SEASONS, "rand7", season, 3), exp)


def test_decay_keeps_the_latest_season_and_halves_every_four_seasons():
    season = 2024
    keep = np.mean([C.train_mask(SEASONS, "decay4", season, k) for k in range(8)], axis=0)
    for age in (0, 4, 8):
        s = season - 1 - age
        got = keep[SEASONS == s].mean()
        assert abs(got - 0.5 ** (age / 4)) < 0.02, (age, got)
    assert keep[SEASONS == season].sum() == 0 and keep[SEASONS < C.TRAIN_FROM].sum() == 0


def test_stage2_fit_recovers_known_coefficients_and_shrinks_b():
    rng = np.random.default_rng(3)
    n = 200_000
    eta, z = rng.normal(0, 1.2, n), rng.normal(0, 1.0, n)
    atp = rng.random(n) < 0.5
    y = (rng.random(n) < expit(np.where(atp, 0.9, 0.95) * eta + np.where(atp, 0.1, 0.0) * z)).astype(float)
    par = C.stage2_fit(eta, atp, np.where(atp, z, 0.0), y)
    assert abs(par["s_atp"] - 0.9) < 0.02 and abs(par["s_wta"] - 0.95) < 0.02 and abs(par["b_mle"] - 0.1) < 0.02
    assert par["b_shrunk"] == pytest.approx(par["b_mle"] * C.TAU ** 2 / (C.TAU ** 2 + par["se_b"] ** 2))
    q = C.stage2_apply(eta[:5], atp[:5], z[:5], par)
    want = expit(np.where(atp[:5], par["s_atp"], par["s_wta"]) * eta[:5] + par["b_shrunk"] * np.where(atp[:5], z[:5], 0))
    assert np.allclose(q, want)
    qk = C.stage2_apply(np.column_stack([eta[:5], eta[:5]]), atp[:5], z[:5], par)
    assert np.allclose(qk[:, 0], want) and np.allclose(qk[:, 1], want)


def test_realisation_reads_one_when_right_sized_and_half_when_twice_too_far():
    rng = np.random.default_rng(4)
    n = 300_000
    close, delta = rng.normal(0, 1, n), rng.normal(0, 0.3, n)
    y = (rng.random(n) < expit(close + delta)).astype(float)
    clusters = np.arange(n) // 500
    right = S.realisation(expit(close + delta), expit(close), y, clusters)
    twice = S.realisation(expit(close + 2 * delta), expit(close), y, clusters)
    assert abs(right["c"] - 1) < 3 * right["c_se"] + 0.02
    assert abs(twice["c"] - 0.5) < 3 * twice["c_se"] + 0.02


def test_two_part_recalibration_recovers_the_close_slope_and_the_move_scale():
    rng = np.random.default_rng(5)
    n = 300_000
    lc, d = rng.normal(0, 1, n), rng.normal(0, 0.2, n)
    atp = rng.random(n) < 0.5
    y = (rng.random(n) < expit(np.where(atp, 1.1, 1.05) * lc + np.where(atp, 1.3, 0.8) * d)).astype(float)
    par = S.two_part_fit(lc, lc + d, atp, np.zeros(n), y)
    assert abs(par["a_atp"] - 1.1) < 0.03 and abs(par["a_wta"] - 1.05) < 0.03
    assert abs(par["c_atp"] - 1.3) < 0.1 and abs(par["c_wta"] - 0.8) < 0.1


def test_the_frame_reader_stops_at_2024():
    f = C.load_frame(labels=False)
    assert f["season"].max() == 2024 and "a_won" not in f.columns
    assert f["tournament_date"].max() <= np.datetime64("2024-12-31")
