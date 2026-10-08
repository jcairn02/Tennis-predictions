"""The 2026 men-only comparison must not select its history on test outcomes."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.eda.predictive_frontier_tabpfn import common as C, prepare as S


def synthetic_frame():
    rng = np.random.default_rng(73)
    years = np.repeat(np.arange(2013, 2027), 110)
    x = rng.normal(size=(len(years), len(C.SPORTS)))
    frame = pd.DataFrame(x, columns=C.SPORTS)
    frame["year"] = years
    frame["tour"] = "atp"
    frame["tournament_date"] = pd.to_datetime(pd.Series(years).astype(str) + "-06-01")
    frame["a_won"] = rng.random(len(years)) < expit(.6*x[:, 0] - .3*x[:, 1])
    frame["match_id"] = [f"m{i}" for i in range(len(frame))]
    frame["evaluation"] = True
    frame["status"] = "completed"
    frame["scheduled_format_supported"] = True
    return frame


def test_exact_sports_inputs_and_flip_cover_all_36_columns():
    assert len(C.STRONG) == 9
    assert len(C.FEATURE_COLUMNS) == 27
    assert len(C.SPORTS) == len(C.NAMES) == len(set(C.NAMES)) == 36
    assert "tour_code" not in C.NAMES
    assert not {"a_won", "match_id", "tournament_date", "p_avg_a", "p_ps_a"}.intersection(C.NAMES)
    values = np.arange(1., 1. + 2*len(C.NAMES)).reshape(2, -1)
    frame = pd.DataFrame(values, columns=C.NAMES)
    flipped = C.flip(frame)
    np.testing.assert_array_equal(flipped.to_numpy(), -values)
    pd.testing.assert_frame_equal(C.flip(flipped), frame)
    np.testing.assert_array_equal(frame.to_numpy(), values)


@pytest.mark.parametrize("validation_year", [2023, 2024, 2025, 2026])
@pytest.mark.parametrize("strategy,span", [("all", None), ("latest6", 6), ("latest4", 4)])
def test_history_windows_are_past_only_and_use_calendar_years(validation_year, strategy, span):
    frame = pd.DataFrame({"year": np.arange(2010, 2028), "tour": "atp"})
    chosen = frame.loc[S.history_mask(frame, validation_year, strategy), "year"]
    first = 2013 if span is None else max(2013, validation_year-span)
    assert chosen.tolist() == list(range(first, validation_year))
    assert chosen.max() < validation_year


def test_training_selection_ignores_2026_features_and_outcomes():
    frame = synthetic_frame()
    selected = S.select_training_history(frame)
    changed = frame.copy()
    future = changed.year.eq(2026)
    changed.loc[future, "a_won"] = ~changed.loc[future, "a_won"]
    changed.loc[future, C.SPORTS] *= 10_000_000.
    changed.loc[future, "evaluation"] = False
    assert S.select_training_history(changed) == selected
    assert selected["validation_years"] == [2023, 2024, 2025]
    assert selected["validation_rows"] == int(frame.year.between(2023, 2025).sum())
    assert selected["strategy"] in {"all", "latest6", "latest4"}
    assert selected["chosen_penalty"] in S.F.GRID
    assert selected["selected_training_min_year"] >= 2013
    assert len(selected["candidates"]) == 3*len(S.F.GRID)


def test_frame_builder_excludes_women_and_preserves_2026_test_rows(monkeypatch):
    full = synthetic_frame()
    women = full[full.year.ge(2025)].copy()
    women["tour"] = "wta"
    women["match_id"] = "wta_" + women.match_id
    mixed = pd.concat([full, women], ignore_index=True)
    base = mixed.drop(columns=C.FEATURE_COLUMNS)
    extra = mixed[["match_id", *C.FEATURE_COLUMNS]]
    monkeypatch.setattr(S.R, "load_frame", lambda: base.copy())
    monkeypatch.setattr(S.pd, "read_parquet", lambda *_args, **_kwargs: extra.copy())
    frame, _ = S.build_frame()
    assert set(frame.tour) == {"atp"}
    assert set(frame[frame.year.eq(2026)].match_id) == set(full[full.year.eq(2026)].match_id)
    assert len(frame) == len(full)
    assert frame.match_id.is_unique
    assert frame.tournament_date.is_monotonic_increasing


def test_fixed_fit_uses_selected_history_only_and_never_test_labels():
    frame = synthetic_frame()
    frame["split"] = np.where(frame.year.eq(2026), "test", "unused_history")
    frame.loc[S.history_mask(frame, 2026, "latest4"), "split"] = "train"
    args = (C.SPORTS, C.FEATURE_COLUMNS, .01)
    prediction, metadata = S.fixed_logistic(frame, *args)
    expected_scale = S.P.rms_scale(frame.loc[frame.split.eq("train"), C.SPORTS].to_numpy())
    np.testing.assert_allclose(metadata["training_rms"], expected_scale)
    assert metadata["train_years"] == [2022, 2023, 2024, 2025]
    assert metadata["n_train"] == 440
    assert metadata["n_test"] == 110
    changed = frame.copy()
    not_training = changed.split.ne("train")
    changed.loc[not_training, "a_won"] = ~changed.loc[not_training, "a_won"]
    changed.loc[changed.split.eq("unused_history"), C.SPORTS] *= 10_000_000.
    second_prediction, second_metadata = S.fixed_logistic(changed, *args)
    # Identical selected values may have different array memory layouts after
    # assignment/copy. BLAS can then accumulate floating-point sums in a
    # different order; require numerical identity, not bitwise identity.
    np.testing.assert_allclose(prediction, second_prediction, rtol=0., atol=1e-12)
    for key in ("training_rms", "beta"):
        np.testing.assert_allclose(metadata[key], second_metadata[key], rtol=0., atol=1e-12)
    assert {key: value for key, value in metadata.items() if key not in ("training_rms", "beta")} == {
        key: value for key, value in second_metadata.items() if key not in ("training_rms", "beta")}
    contaminated = frame.copy()
    contaminated.loc[contaminated.year.eq(2026), "split"] = "train"
    with pytest.raises(ValueError, match="chronological"):
        S.fixed_logistic(contaminated, *args)
