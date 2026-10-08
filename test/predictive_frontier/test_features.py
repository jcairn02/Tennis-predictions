"""Chronology and numerical invariants for the new rolling-state hypotheses."""
import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

from src.eda.predictive_frontier.features import (
    FEATURE_COLUMNS, FEATURE_GROUPS, POINT_PRIOR, SURFACE_PRIOR, build_features,
)


def match(mid, day, a="P", b="Q", surface="Hard", event="E", wins=(70., 60.),
          points=(100., 100.), skill=((0., 0.), (0., 0.)), p_elo=.6, status="completed"):
    rows = []
    for j, pid in enumerate((a, b)):
        rows.append({"match_id": mid, "side": ("A", "B")[j], "tour": "atp", "player_id": pid,
                     "day": day, "surface": surface, "tournament_id": event, "status": status,
                     "won": j == 0, "spw_n": wins[j], "spw_d": points[j], "history_format_supported": True,
                     "serve_own": skill[j][0], "return_own": skill[j][1], "mu_logit": 0., "p_elo_a": p_elo,
                     "ace": 5.})
    return rows


def toy():
    return pd.DataFrame(match("m1", 0) + match("m2", 0, event="elsewhere")
                        + match("m3", 28) + match("m4", 182, surface="Clay")
                        + match("m5", 364, surface="Hard"))


def features(rows):
    return build_features(rows)[0].set_index("match_id")


def test_same_day_current_and_future_outcomes_are_invisible_and_later_respond():
    rows = toy()
    base = features(rows)
    changed = rows.copy()
    changed.loc[changed.match_id.eq("m1"), "spw_n"] = [90., 30.]
    changed.loc[changed.match_id.eq("m1"), "won"] = [False, True]
    rebuilt = features(changed)
    # Both another event and current match on the same day remain untouched.
    pd.testing.assert_frame_equal(base.iloc[:2], rebuilt.iloc[:2])
    assert rebuilt.loc["m3", "pf_serve_28"] > base.loc["m3", "pf_serve_28"]
    changed = rows.copy()
    changed.loc[changed.match_id.eq("m5"), ["spw_n", "spw_d"]] = np.nan
    changed.loc[changed.match_id.eq("m5"), "status"] = "retired"
    pd.testing.assert_frame_equal(base, features(changed))


def test_same_event_earlier_round_is_also_excluded_on_same_day():
    rows = pd.DataFrame(match("m1", 1) + match("m2", 1) + match("m3", 2))
    rows["round_order"] = np.repeat([1, 2, 3], 2)
    base = features(rows)
    changed = rows.copy()
    changed.loc[:1, "spw_n"] = [99., 1.]
    rebuilt = features(changed)
    pd.testing.assert_frame_equal(base.iloc[:2], rebuilt.iloc[:2])
    assert rebuilt.loc["m3", "pf_serve_28"] > base.loc["m3", "pf_serve_28"]


def test_toy_residual_expectation_and_forecast_gap_decay():
    rows = pd.DataFrame(match("m1", 0) + match("m2", 28))
    out = features(rows)
    # Day-zero residuals 20 and 10; after 28 days each has 50 points.
    assert out.loc["m2", "pf_serve_28"] == pytest.approx((10. - 5.) / (50. + POINT_PRIOR))
    # Return residuals are -10 and -20, so the return advantage is identical.
    assert out.loc["m2", "pf_return_28"] == pytest.approx(.02)
    later = rows.copy()
    later.loc[later.match_id.eq("m2"), "day"] = 182
    assert abs(features(later).loc["m2", "pf_serve_28"]) < abs(out.loc["m2", "pf_serve_28"])


def test_expected_points_use_own_and_opponent_strength():
    skill = ((.7, .3), (-.1, .2))
    wins = (100 * expit(.7 - .2), 100 * expit(-.1 - .3))
    rows = pd.DataFrame(match("m1", 0, wins=wins, skill=skill) + match("m2", 1, skill=skill))
    out = features(rows)
    residual_cols = [c for c in FEATURE_GROUPS["innovations"] if "seen" not in c and "unknown" not in c]
    np.testing.assert_allclose(out.loc["m2", residual_cols], 0., atol=1e-14)


def test_surface_partial_pooling_and_unseen_surface_neutrality():
    hard = pd.DataFrame(match("m1", 0) + match("m2", 182))
    out = features(hard)
    global_a, global_b = 10 / 250, 5 / 250
    a = (10 + SURFACE_PRIOR * global_a) / (50 + SURFACE_PRIOR) - global_a
    b = (5 + SURFACE_PRIOR * global_b) / (50 + SURFACE_PRIOR) - global_b
    assert out.loc["m2", "pf_surface_serve"] == pytest.approx(a - b)
    hard.loc[hard.match_id.eq("m2"), "surface"] = "Clay"
    unseen = features(hard)
    assert unseen.loc["m2", "pf_surface_serve"] == pytest.approx(0.)
    assert unseen.loc["m2", "pf_surface_unknown_elo"] > 0.


@pytest.mark.parametrize("bad_column,bad_value", [("spw_n", -1.), ("spw_n", 101.),
                                                   ("spw_d", np.nan), ("ace", -1.),
                                                   ("history_format_supported", False)])
def test_invalid_paired_box_cannot_update_any_point_state(bad_column, bad_value):
    rows = pd.DataFrame(match("m1", 0) + match("m2", 28))
    if bad_column == "history_format_supported":
        rows.loc[:1, bad_column] = bad_value
    else:
        rows.loc[0, bad_column] = bad_value
    out = features(rows)
    assert out.loc["m2", "pf_serve_182"] == 0.
    assert out.loc["m2", "pf_return_182"] == 0.
    assert out.loc["m2", "pf_surface_serve"] == 0.
    assert out.loc["m2", "pf_event_speed_elo"] == 0.
    # Played-match history survives a missing box, so rest isn't invented as unknown.
    assert out.loc["m2", "pf_history_unknown_elo"] == 0.
    assert out.loc["m2", "pf_box_unknown_elo"] > 0.


def test_all_features_are_side_antisymmetric():
    rows = toy()
    # Give the players different history, skill, and rest to make symmetry nontrivial.
    rows.loc[rows.side.eq("A"), "serve_own"] = .3
    rows.loc[rows.side.eq("B"), "return_own"] = -.2
    rows.loc[rows.match_id.eq("m4") & rows.side.eq("B"), "player_id"] = "NEW"
    rows.loc[rows.match_id.eq("m3"), "status"] = "retired"
    base = features(rows)
    swapped = rows.iloc[np.arange(len(rows)) ^ 1].reset_index(drop=True)
    swapped["side"] = np.tile(["A", "B"], len(rows) // 2)
    swapped["p_elo_a"] = 1 - swapped.p_elo_a
    np.testing.assert_allclose(features(swapped).to_numpy(), -base.to_numpy(), atol=1e-12)


def test_event_conditions_use_only_prior_days_in_same_edition():
    rows = pd.DataFrame(match("m1", 1, event="E") + match("m2", 2, a="R", b="S", event="E")
                        + match("m3", 2, a="U", b="V", event="OTHER"))
    out = features(rows)
    assert out.loc["m1", "pf_event_speed_elo"] == 0.
    assert out.loc["m2", "pf_event_speed_elo"] > 0.
    assert out.loc["m3", "pf_event_speed_elo"] == 0.
    changed = rows.copy()
    changed.loc[changed.match_id.eq("m2"), "spw_n"] = [1., 1.]
    pd.testing.assert_frame_equal(out, features(changed))


def test_retired_loss_history_is_lagged_and_distinct_from_box_history():
    rows = pd.DataFrame(match("m1", 0, status="retired") + match("m2", 28))
    out = features(rows)
    assert out.loc["m1", "pf_retired_loss_recent"] == 0.
    assert out.loc["m2", "pf_retired_loss_recent"] == pytest.approx(-.5)
    assert out.loc["m2", "pf_retired_loss_rate"] < 0.
    assert out.loc["m2", "pf_serve_28"] == 0.
    assert out.loc["m2", "pf_history_unknown_elo"] == 0.


def test_no_market_dependency_and_complete_finite_schema():
    rows = toy()
    rows["p_mkt_a"] = .9
    first, meta = build_features(rows)
    rows["p_mkt_a"] = np.nan
    pd.testing.assert_frame_equal(first, build_features(rows)[0])
    assert first.columns.tolist() == ["match_id", *FEATURE_COLUMNS]
    assert len(set(FEATURE_COLUMNS)) == len(FEATURE_COLUMNS)
    assert np.isfinite(first[FEATURE_COLUMNS].to_numpy()).all()
    assert meta["feature_groups"] == FEATURE_GROUPS


def test_day_order_validation():
    rows = toy().iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError):
        build_features(rows)
