"""Paired repaired-feature evaluation must preserve rows, dates and comparator meaning."""
import numpy as np
import pandas as pd
import pytest

from src.eda.feature_alpha_audit import repair_score as R


def frame():
    return pd.DataFrame({"match_id": ["a", "b", "c", "d"], "tour": ["atp"] * 4,
                         "year": [2019, 2019, 2022, 2022], "evaluation": [True] * 4,
                         "a_won": [1, 0, 0, 1], "group": "T250",
                         "tournament_date": pd.to_datetime(["2019-02-01", "2019-04-01", "2022-02-01", "2022-04-01"]),
                         "x": [1, 2, np.nan, 4], "z": [3, 4, 5, 6]})


def test_comparisons_use_identical_scored_rows_for_both_loglosses():
    f = frame()
    p = {"model": np.array([.8, np.nan, .3, .7]), "raw_market": np.array([.6, .8, np.nan, .6])}
    got = R.comparison_rows(f, p, [("model", "raw_market")])[0]
    wanted = np.array([0, 3])
    yl = f.a_won.to_numpy()[wanted]
    assert got["n"] == 2
    assert got["model_ll"] == pytest.approx(R.E.loss(yl, p["model"][wanted]).mean())
    assert got["comparator_ll"] == pytest.approx(R.E.loss(yl, p["raw_market"][wanted]).mean())
    assert got["gain_mll"] == pytest.approx(1000 * (got["comparator_ll"] - got["model_ll"]))


def test_common_cohort_drops_missing_feature_for_all_models():
    got, coverage = R.common_cohort(frame(), ["x", "z"], "atp")
    assert got.match_id.tolist() == ["a", "b", "d"]
    assert coverage[0]["eligible"] == 4 and coverage[0]["common_rows"] == 3
    assert coverage[1]["eligible"] == 2 and coverage[1]["common_rows"] == 1


def test_ladder_preserves_frozen_order_and_records_unrebuilt_optional_features():
    cols = [R.E.SR, R.E.ADJ, *R.E.CONTEXT, R.E.IOS, R.E.GAMES]
    specs, refs, omitted = R.ladder_specs(cols)
    final = "elo_sr_adjperf_ios_short_games_context"
    assert specs[final] == ["elo_logit", R.E.SR, R.E.ADJ, R.E.IOS, R.E.GAMES, *R.E.CONTEXT]
    assert refs[final] == "elo_sr_adjperf_ios_short_games" and omitted == []
    specs, refs, omitted = R.ladder_specs([c for c in cols if c not in (R.E.IOS, R.E.GAMES)])
    assert omitted == [R.E.IOS, R.E.GAMES]
    assert "elo_sr_adjperf_context" in specs
    with pytest.raises(ValueError, match="required ladder block"):
        R.ladder_specs([R.E.SR])


def test_cached_comparison_joins_by_id_and_rejects_changed_outcome_orientation():
    f = frame().assign(model=[.8, .3, .4, .7])
    cache = f.iloc[[3, 0, 2]].copy().assign(old=[.6, .7, .3])
    got = R.compare_cached(f, cache, [("model", "old")], "example", "cache.parquet")
    assert got[0]["n"] == 3
    assert got[0]["interpretation"] == "combined_repair_and_history_universe_change_not_timing_only"
    cache.loc[cache.index[0], "a_won"] = 0
    with pytest.raises(ValueError, match="outcomes/orientations"):
        R.compare_cached(f, cache, [("model", "old")], "example", "cache.parquet")


def test_one_temporal_cluster_cannot_receive_positive_interval_label():
    f = frame().iloc[:1]
    got = R.comparison_rows(f, {"model": np.array([.8]), "base": np.array([.6])}, [("model", "base")])[0]
    assert got["gain_mll"] > 0 and np.isnan(got["lo_mll"])
    assert not got["positive_clustered_interval"]


@pytest.mark.parametrize("defect", ["duplicate", "missing_day", "wrong_fold_year"])
def test_loader_rejects_misidentified_or_mistimed_repaired_rows(monkeypatch, defect):
    f = frame().assign(p_elo=.6, p_mkt=.6)
    for col in R.P.PROFILE + R.PROFILE_CONTEXT + [R.E.ADJ]:
        f[col] = .1
    if defect == "duplicate":
        f.loc[1, "match_id"] = "a"
    elif defect == "missing_day":
        f.loc[1, "tournament_date"] = pd.NaT
    else:
        f.loc[1, "year"] = 2020
    monkeypatch.setattr(R.pd, "read_parquet", lambda path, **kwargs: f)
    with pytest.raises(ValueError):
        R.load_frame()
