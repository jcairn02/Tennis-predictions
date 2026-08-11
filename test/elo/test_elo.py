"""Unit tests for the surface-blended Elo baseline."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ratings.elo import (DEFAULT_RATING, SurfaceBlendElo, expected_score,
                             k_factor)


def test_expected_score_symmetry():
    assert expected_score(1500, 1500) == pytest.approx(0.5)
    for r_a, r_b in [(1600, 1400), (1500, 1700), (1234, 1876)]:
        assert expected_score(r_a, r_b) + expected_score(r_b, r_a) == pytest.approx(1.0)
    assert expected_score(1700, 1500) > 0.5


def test_k_factor_decay():
    assert k_factor(0) == pytest.approx(250.0 / 5.0 ** 0.4)
    ks = [k_factor(n) for n in range(0, 200, 10)]
    assert all(a > b for a, b in zip(ks, ks[1:])), "K must decrease with experience"


def test_update_conservation_for_equal_experience():
    elo = SurfaceBlendElo()
    elo.update("A", "B", "Hard")
    gain = elo.overall["A"] - DEFAULT_RATING
    loss = DEFAULT_RATING - elo.overall["B"]
    assert gain == pytest.approx(loss)  # same K (both debut) => zero-sum
    assert gain > 0
    # surface table updated too, with its own count
    assert elo.by_surface["Hard"]["A"] > DEFAULT_RATING
    assert elo.surface_counts["Hard"]["A"] == 1


def test_surface_blend_separates_surfaces():
    elo = SurfaceBlendElo(surface_weight=0.5)
    for _ in range(5):
        elo.update("A", "B", "Clay")
    p_clay = elo.predict_proba("A", "B", "Clay")
    p_hard = elo.predict_proba("A", "B", "Hard")
    assert p_clay > p_hard > 0.5  # overall component still carries signal to Hard

    elo_pure = SurfaceBlendElo(surface_weight=1.0)
    for _ in range(5):
        elo_pure.update("A", "B", "Clay")
    assert elo_pure.predict_proba("A", "B", "Hard") == pytest.approx(0.5)


def test_k_scale_multiplies_rating_change():
    base, scaled = SurfaceBlendElo(), SurfaceBlendElo()
    base.update("A", "B", "Hard", k_scale=1.0)
    scaled.update("A", "B", "Hard", k_scale=1.1)   # the verified Grand Slam multiplier
    base_gain = base.overall["A"] - DEFAULT_RATING
    scaled_gain = scaled.overall["A"] - DEFAULT_RATING
    assert scaled_gain == pytest.approx(1.1 * base_gain)


def test_unknown_surface_raises_by_default():
    elo = SurfaceBlendElo()
    with pytest.raises(ValueError, match="Unknown surface"):
        elo.predict_proba("A", "B", None)
    with pytest.raises(ValueError, match="Unknown surface"):
        elo.update("A", "B", "Moon")


def test_missing_surface_overall_policy():
    elo = SurfaceBlendElo(missing_surface="overall")
    elo.update("A", "B", None)            # updates overall only
    assert elo.overall["A"] > DEFAULT_RATING
    assert all(not table for table in elo.by_surface.values())
    assert elo.predict_proba("A", "B", None) > 0.5


def test_fit_raises_on_unsorted_dates():
    df = pd.DataFrame({
        "tourney_date": [20240101, 20231231],
        "winner_name": ["A", "A"],
        "loser_name": ["B", "B"],
        "surface": ["Hard", "Hard"],
    })
    elo = SurfaceBlendElo()
    with pytest.raises(ValueError, match="must be chronological"):
        elo.fit(df)


def test_fit_walk_forward_is_leak_free_and_scores():
    rng = np.random.default_rng(7)
    n = 300
    # A is truly stronger than B-pool: A wins 75% of its matches
    rows = []
    date = 20200101
    for i in range(n):
        date += 1
        opp = f"P{rng.integers(0, 20)}"
        if rng.random() < 0.75:
            rows.append((date, "A", opp, "Hard"))
        else:
            rows.append((date, opp, "A", "Hard"))
    df = pd.DataFrame(rows, columns=["tourney_date", "winner_name", "loser_name", "surface"])

    elo = SurfaceBlendElo()
    preds = elo.fit(df)
    assert preds["p_winner"].iloc[0] == pytest.approx(0.5)  # nobody rated yet
    log_loss = -np.log(preds["p_winner"]).mean()
    assert np.isfinite(log_loss)
    assert log_loss < np.log(2)  # beats coin flip on a 75/25 process
    assert elo.overall["A"] > DEFAULT_RATING + 50
