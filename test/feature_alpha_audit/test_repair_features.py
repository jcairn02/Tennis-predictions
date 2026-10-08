"""Repaired shortlist wiring and day-level workload availability regressions."""
import numpy as np

from src.eda.feature_alpha_audit import repair_features as R
from src.eda.feature_alpha_audit import repair_history as H
from src.eda.feature_alpha_audit.chronology import frozen_profile
from test_repair_history import rows_and_constants


def constants():
    means = {s: {(t, sf): .5 for t in R.C.TOURS for sf in ("all", "Hard", "Clay", "Grass", "Carpet")}
             for s in R.B.STATS}
    typ = {(s, t): 50. for s in R.B.STATS for t in R.C.TOURS}
    mad = {(s, ch, t, 0): .4 for s in R.B.STATS for ch in R.AP.CHANNELS for t in R.C.TOURS}
    chosen = {(t, s): {"h1": 52., "K1": 2., "tau": 0, "h3": 2., "K3": 10.}
              for t in R.C.TOURS for s in R.AP.CORE}
    return means, typ, mad, chosen


def test_shortlist_adjperf_preserves_frozen_method_and_adds_total_points():
    rows, *_ = rows_and_constants()
    means, typ, mad, chosen = constants()
    new = R.adjperf_features(rows, means, chosen, typ, mad)
    old = frozen_profile(R.AP.Ctx(rows, means, typ=typ, madpop=mad, stats=R.D.ADJ_STATS), chosen)
    for col in R.PROFILE:
        np.testing.assert_allclose(new[col], old[col], atol=1e-12, equal_nan=True)
    assert np.isfinite(new["adjperf_tpw|decayed"][-1])


def test_context_and_games_elo_ignore_future_overlap_and_use_earlier_same_day_round():
    rows, elo, *_ = rows_and_constants()
    changed = rows.copy()
    future = changed.match_id.eq("future")
    changed.loc[future, "sets_won_d"] = 5.
    changed.loc[future, "games_won_n"] = changed.loc[future, "games_won_d"] - changed.loc[future, "games_won_n"]
    changed.loc[future, "won"] = ~changed.loc[future, "won"]
    before, after = R.context_features(rows), R.context_features(changed)
    a = rows.iloc[::2]
    protected = a.match_id.ne("after").to_numpy()
    for col in R.CONTEXT:
        np.testing.assert_array_equal(before[col][protected], after[col][protected])
    target = int(np.flatnonzero(a.match_id.eq("target").to_numpy())[0])
    later = int(np.flatnonzero(a.match_id.eq("later_round").to_numpy())[0])
    assert np.isclose(before["sets_14d|single"][target], np.log(3.))
    assert np.isclose(before["sets_14d|single"][later], np.log(5.) - np.log(3.))
    assert before["age|single"][target] == 8.
    games1 = R.games_elo(rows, elo, {"atp": .65})
    games2 = R.games_elo(changed, elo, {"atp": .65})
    np.testing.assert_array_equal(games1[protected], games2[protected])
    assert not np.allclose(games1[~protected], games2[~protected])


def test_new_iid_paths_ignore_current_score_anatomy_and_future_box():
    rows, elo, sr, mu = rows_and_constants()
    rows, _, _ = H.rebuild_ratings(rows, elo, sr, mu)
    changed = rows.copy()
    changed["format"], changed["best_of"], changed["sets_won_n"] = "short_sets", 5, 3.
    np.testing.assert_array_equal(R.rating_matchup(rows), R.rating_matchup(changed))
    means, typ, *_ = constants()
    changed = rows.copy()
    future = changed.match_id.eq("future")
    changed.loc[future, "spw_n"] = changed.loc[future, "spw_d"] - changed.loc[future, "spw_n"]
    kwargs = {"atp": {"h": 4., "kappa": 1., "tau": 1}}
    one, _ = R.ios_features(rows, means, typ, kwargs)
    two, _ = R.ios_features(changed, means, typ, kwargs)
    protected = rows.iloc[::2].match_id.ne("after").to_numpy()
    np.testing.assert_allclose(one[protected], two[protected], atol=1e-10)
    assert not np.allclose(one[~protected], two[~protected])
