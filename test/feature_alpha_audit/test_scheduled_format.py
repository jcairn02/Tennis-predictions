"""Regression checks for outcome-independent match-probability conversion."""
import numpy as np
import pandas as pd
import pytest

from src.eda.predictability_diagnostic import stage2_iid as M
from src.eda.predictability_diagnostic import stage4_features as F
from src.eda.ufc_ideas import stageB_ios as IO


def metadata(**overrides):
    return {"tour": "atp", "year": 2025, "level": "T250", "qualifying": False,
            "round": "QF", "round_order": 15, "tournament_name": "Brisbane",
            "best_of": 3, "format": "standard", **overrides}


@pytest.mark.parametrize("year", [2010, 2018, 2019, 2025, 2026])
def test_wimbledon_final_qualifying_is_scheduled_bo5_even_if_source_says_three(year):
    rows = pd.DataFrame([metadata(year=year, level="GS", tournament_name="Wimbledon", qualifying=True,
                                  round=r, round_order=i) for i, r in enumerate(["Q1", "Q2", "Q3"], 1)])
    np.testing.assert_array_equal(F.best_of_five(rows), [0, 0, 1])
    expected = M.match_win(0.65, 0.60, 5, F.deciding_rules(rows.iloc[[2, 2]])[0])
    assert F.scheduled_iid_prob([0.65], [0.60], rows.iloc[[2]])[0] == pytest.approx(expected)


def test_gs_main_women_and_other_qualifying_rules_ignore_recorded_best_of():
    rows = pd.DataFrame([
        metadata(level="GS", tournament_name="Roland Garros", best_of=3),
        metadata(level="GS", tournament_name="US Open", qualifying=True, round="Q3", best_of=5),
        metadata(tour="wta", level="GS", tournament_name="Wimbledon", best_of=5),
        metadata(tour="wta", level="GS", tournament_name="Wimbledon", qualifying=True, round="Q3", best_of=5),
    ])
    np.testing.assert_array_equal(F.best_of_five(rows), [1, 0, 0, 0])


def test_schedule_forecast_unchanged_when_own_result_and_score_labels_are_replaced():
    rows = pd.DataFrame([metadata(), metadata(level="GS", tournament_name="Wimbledon", qualifying=True,
                                             round="Q3", round_order=3)])
    rows["sets_won_n"], rows["score"], rows["won"] = [2, 0], ["6-4 6-4", "0-6 0-6 RET"], [True, False]
    expected = F.scheduled_iid_prob([0.65, 0.65], [0.6, 0.6], rows)
    mutated = rows.assign(sets_won_n=[3, 3], score="4-0 4-0 4-0", won=True,
                          best_of=5, format="short_sets", status="retired")
    np.testing.assert_array_equal(F.scheduled_iid_prob([0.65, 0.65], [0.6, 0.6], mutated), expected)
    np.testing.assert_array_equal(F.best_of_five(mutated), F.best_of_five(rows))


def test_ios_points_and_games_predictions_do_not_read_own_score_or_derived_format(monkeypatch):
    rows = pd.DataFrame([metadata(), metadata()])
    rows["sets_won_n"] = [2, 0]
    monkeypatch.setattr(IO.B, "pool_rows", lambda frame: (np.array([0]), np.array([1])))
    sa = {s: {"mu_scale": np.array([0.5, 0.5])} for s in ("spw", "hold")}
    ios = {s: {"O": np.array([0.15, -0.05]), "D": np.array([0.03, -0.02])} for s in IO.IOS_STATS}
    expected = IO.features(rows, sa, ios, {})
    changed = IO.features(rows.assign(sets_won_n=[3, 2], best_of=5, format="match_tiebreak"), sa, ios, {})
    for col in ["ios_matchup_points|single", "ios_matchup_games|single"]:
        np.testing.assert_array_equal(expected[col], changed[col])
        assert np.isfinite(expected[col]).all()


def test_unsupported_rules_yield_nan_instead_of_standard_set_approximation():
    rows = pd.DataFrame([
        metadata(level="FIN", tournament_name="NextGen Finals"),
        metadata(level="FIN", tournament_name="Next Gen Finals"),
        metadata(tour="wta", year=2021, tournament_name="Yarra Valley Classic"),
        metadata(tour="wta", year=2021, tournament_name="Gippsland Trophy"),
        metadata(tour="wta", year=2021, tournament_name="Grampians Trophy"),
        metadata(level="GS", tournament_name="Wimbledon", qualifying=True, round=None, round_order=None),
        metadata(level="GS", tournament_name="Unmapped major"),
        metadata(level="TEAM", tournament_name="Unknown team event"),
        metadata(level="ITF"), metadata(year=2000), metadata(year=2027), metadata(tournament_name=None),
    ])
    assert not F.scheduled_format(rows)["supported"].any()
    assert F.scheduled_format(rows).iloc[0]["best_of"] == 5  # known rules, unsupported iid scoring
    assert np.isnan(F.best_of_five(rows)).all()
    assert np.isnan(F.scheduled_iid_prob(np.full(len(rows), .65), np.full(len(rows), .6), rows)).all()
    assert np.isnan(F.iid_prob([.65, .65, .65], [.6, .6, .6], [1, np.nan, 0],
                              ["TB7@6"] * 3, ["short_sets", "standard", "unknown"])).all()


def test_score_anatomy_requires_explicit_retrospective_entry_point():
    rows = pd.DataFrame([metadata(), metadata()])
    rows["sets_won_n"] = [3, 2]
    np.testing.assert_array_equal(F.best_of_five(rows), [0, 0])
    np.testing.assert_array_equal(F.retrospective_best_of_five(rows), [True, True])
    with pytest.raises(ValueError, match="Forecast format must be scheduled"):
        F.best_of_five(rows, "score")


def test_qualifying_round_order_fallback_and_unknown_missing_metadata():
    rows = pd.DataFrame([metadata(level="GS", tournament_name="Wimbledon", qualifying=True,
                                  round_order=3)]).drop(columns="round")
    assert F.best_of_five(rows)[0] == 1
    assert np.isnan(F.best_of_five(rows.drop(columns="qualifying"))[0])
