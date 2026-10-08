"""Independent checks of benchmark equivalence and chronological selection."""
import numpy as np
import pandas as pd
from scipy.special import expit

from src.eda.feature_alpha_audit import elo_retest as E
from src.eda.predictive_frontier import score as S


def fitting_sample():
    rng = np.random.default_rng(908)
    x = rng.normal(size=(2400, 3))
    return pd.DataFrame({"year": np.repeat(np.arange(2013, 2021), 300),
                         "evaluation": True, "x": x[:, 0], "z": x[:, 1],
                         "candidate": x[:, 2],
                         "a_won": rng.binomial(1, expit(x[:, 0] - .3*x[:, 1] + .2*x[:, 2]))})


def test_unpenalized_scorer_matches_repaired_elo_solver():
    frame = fitting_sample()
    expected, _ = E.walk_predictions(frame, ["x", "z"])
    actual, _ = S.walk(frame, ["x", "z"], [])
    scored = frame.year.ge(2019)
    np.testing.assert_allclose(actual[scored], expected[scored], atol=2e-6, rtol=0)


def test_future_feature_scale_cannot_change_past_fits_or_its_own_fit():
    frame = fitting_sample()
    before, records = S.walk(frame, ["x", "z", "candidate"], ["candidate"])
    altered = frame.copy()
    altered.loc[altered.year.eq(2020), "candidate"] *= 1_000
    after, updated = S.walk(altered, ["x", "z", "candidate"], ["candidate"])
    # Current forecast inputs can change current forecasts, but cannot change
    # training scales, model coefficients, ridge selection, or earlier forecasts.
    assert records == updated
    np.testing.assert_allclose(before[frame.year.lt(2020)], after[frame.year.lt(2020)], equal_nan=True)
    assert not np.allclose(before[frame.year.eq(2020)], after[frame.year.eq(2020)])


def test_family_selector_ignores_dominant_but_old_validation_history():
    years = np.concatenate([np.repeat(2016, 5000), np.repeat(np.arange(2017, 2021), 400)])
    frame = pd.DataFrame({"year": years, "evaluation": True, "a_won": 1})
    predictions = {"baseline": np.where(years <= 2017, .99, .55),
                   "candidate": np.where(years <= 2017, .01, .9)}
    actual, records = S.select_past(frame, predictions)
    record = next(r for r in records if r["year"] == 2020)
    assert record["selected"] == "candidate"
    assert record["validation_years"] == [2018, 2019]
    np.testing.assert_array_equal(actual[years == 2020], predictions["candidate"][years == 2020])


def test_family_selector_fallback_uses_eligible_oos_row_count():
    years = np.repeat(np.arange(2017, 2021), 400)
    frame = pd.DataFrame({"year": years, "evaluation": True, "a_won": 1})
    frame.loc[frame.year.eq(2018), "evaluation"] = False
    frame.loc[frame.index[frame.year.eq(2019)][250:], "evaluation"] = False
    predictions = {"baseline": np.repeat(.55, len(frame)), "candidate": np.repeat(.9, len(frame))}
    _, records = S.select_past(frame, predictions)
    record = next(r for r in records if r["year"] == 2020)
    assert record["validation_n"] == 250
    assert record["selected"] == "baseline"


def test_future_overlapping_event_isolated_through_upstream_rating_rebuild():
    from src.eda.feature_alpha_audit import repair_history as H
    from src.eda.predictive_frontier.features import build_features, FEATURE_COLUMNS
    from src.eda.predictability_diagnostic import common as C

    # The long event starts before the target event, but its result happens
    # after the target. Build the actual provider-date join and rating pass.
    matches, players, odds = [], [], []
    origin = pd.Timestamp("2016-01-01")
    for order, (mid, start, day, event) in enumerate([
            ("warm", 0, 1, "WARM"), ("future", 2, 12, "LONG"),
            ("target", 6, 8, "TARGET"), ("after", 19, 20, "AFTER")]):
        matches.append({"match_id": mid, "tour": "atp", "year": 2016, "level": "T250",
                        "qualifying": False, "evaluation": True, "round_order": 1,
                        "tournament_date": origin + pd.Timedelta(days=start),
                        "tournament_id": event, "order": order, "surface": "Hard",
                        "status": "completed", "format": "standard", "has_box": True,
                        "player_a_id": "a", "player_b_id": "b", "a_won": True,
                        "best_of": 3, "tournament_name": event, "round": "R32"})
        odds.append({"match_id": mid, "td_date": origin + pd.Timedelta(days=day),
                     "td_redated": False, "link": "name_pair", "round_agrees": "yes",
                     "same_set_scores": True, "p_avg_a": .6})
        for side, pid, opponent in [("A", "a", "b"), ("B", "b", "a")]:
            player = {"match_id": mid, "side": side, "player_id": pid,
                      "opponent_id": opponent, "won": side == "A", "age": 28.}
            for stat in C.RATES:
                player[f"{stat}_n"] = 32. if side == "A" else 24.
                player[f"{stat}_d"] = 50.
            players.append(player)
    selected, _ = H.select_dated_matches(pd.DataFrame(matches), pd.DataFrame(odds))
    rows = H.build_rows(selected, pd.DataFrame(players), pd.DataFrame(odds))
    elo = {"atp": {"k0": 250., "offset": 5., "shape": .4, "w": .3}}
    sr = {"atp": {"var_serve": .02, "var_return": .005, "drift": .0002}}
    mu = {("atp", "all"): .4, ("atp", "Hard"): .4}
    altered = rows.copy()
    future = altered.match_id.eq("future")
    altered.loc[future, "won"] = ~altered.loc[future, "won"]
    altered.loc[future, "spw_n"] = altered.loc[future, "spw_d"] - altered.loc[future, "spw_n"]
    original_rows, _, _ = H.rebuild_ratings(rows, elo, sr, mu)
    altered_rows, _, _ = H.rebuild_ratings(altered, elo, sr, mu)
    before = build_features(original_rows)[0].set_index("match_id")
    after = build_features(altered_rows)[0].set_index("match_id")
    protected = before.index != "after"
    np.testing.assert_allclose(before.loc[protected, FEATURE_COLUMNS], after.loc[protected, FEATURE_COLUMNS], atol=1e-12)
    # A test that all states were accidentally disabled would fail this control.
    assert not np.allclose(before.loc["after", FEATURE_COLUMNS], after.loc["after", FEATURE_COLUMNS])
