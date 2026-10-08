"""Regression checks for the audit's evaluation defects, independent of archived outputs."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit
from scipy.stats import t as student_t

from src.eda.predictability_diagnostic import stage4_rundown as R
from src.eda.ufc_ideas import common as U


def training_fixture():
    rng = np.random.default_rng(182)
    years = np.repeat(np.arange(2010, 2017), 350)
    x = rng.normal(size=(len(years), 2)) * [4, 30]
    base = rng.normal(size=len(years))
    y = rng.random(len(years)) < expit(0.3 * base + 0.2 * x[:, 0] - 0.01 * x[:, 1])
    z = np.column_stack([base, x])[None]
    return z, y, years, base


def test_future_feature_magnitude_cannot_change_earlier_fit_or_training_scale():
    z, y, years, base = training_fixture()
    before = R.walk(z, y, years, [2013, 2014, 2015], base)
    changed = z.copy()
    changed[:, years >= 2015, 1:] *= 1e9
    after = R.walk(changed, y, years, [2013, 2014, 2015], base)
    for year in (2013, 2014, 2015):
        assert before["coefs"][year] == after["coefs"][year]
        assert before["coefs"][year]["feature_training_sd"] == pytest.approx(z[0, years < year, 1:].std(axis=0))
    early = (years >= 2013) & (years < 2015)
    assert np.array_equal(before["llm"][:, early], after["llm"][:, early])


def test_walk_raw_baseline_is_distinct_from_fitted_calibration():
    z, y, years, base = training_fixture()
    got = R.walk(z, y, years, [2013, 2014], base)
    scored = np.isfinite(got["llb"])
    assert got["llraw"][scored] == pytest.approx(R.ll(expit(base[scored]), y[scored]))
    assert not np.allclose(got["llraw"][scored], got["llb"][scored])


def test_four_week_ci_preserves_dependence_and_uses_paired_differences():
    gains = np.repeat(np.array([-0.004, -0.001, 0.003, 0.005, 0.001, 0.007]), 40)
    dates = np.repeat(pd.date_range("2020-01-06", periods=6, freq="28D").to_numpy(), 40)
    d = np.vstack([gains, np.zeros((R.COPIES, len(gains)))])
    got = R.summarize(d, np.ones(len(gains), dtype=bool), dates, gains + 0.002)
    means = gains.reshape(6, 40).mean(axis=1)
    radius = student_t.ppf(.975, 5) * means.std(ddof=1) / np.sqrt(6) * 1000
    assert got["lo"] == pytest.approx(1000 * gains.mean() - radius)
    assert got["hi"] == pytest.approx(1000 * gains.mean() + radius)
    assert got["hi"] - got["lo"] > got["iid_hi"] - got["iid_lo"]
    assert got["raw_baseline_imp"] == pytest.approx(got["imp"] + 2)
    assert got["raw_baseline_lo"] == pytest.approx(got["lo"] + 2)


def test_missing_or_single_cluster_cannot_produce_positive_evidence():
    d = np.vstack([np.full(50, .002), np.zeros((R.COPIES, 50))])
    mask = np.ones(50, dtype=bool)
    no_dates = R.summarize(d, mask)
    one_date = R.summarize(d, mask, np.repeat(np.datetime64("2020-01-06"), 50))
    for got in (no_dates, one_date):
        assert np.isnan(got["lo"])
        assert not R.clears_heuristic_line({**got, "z": 20}, {"line": 4})


@pytest.mark.parametrize("gain,lower", [(-.05, -.1), (0, -.1), (.2, -.1), (.2, 0)])
def test_negative_or_uncertain_gain_never_clears_line_or_becomes_a_finding(gain, lower):
    g = {"n": 500, "imp": gain, "lo": lower, "z": 50, "above_band": True, "below_band": False,
         "ci_method": "paired_four_week_cluster_t"}
    assert not R.clears_heuristic_line(g, {"line": 4})
    assert R.observed_category("market", g) in ("none", "worse")
    # Also reject stale externally supplied positive flags.
    rec = {"elo_clears_line": True, "elo_above_band": True, "elo_below_band": False, "eras_positive": 4}
    row = {"constant": False, "scores": {"elo": {"groups": {"all": g}}}}
    assert U.reading_of(rec, row) != "finding"


def test_positive_clustered_evidence_can_pass_descriptive_screen():
    g = {"n": 500, "imp": 0.8, "lo": 0.1, "z": 7, "above_band": True, "below_band": False,
         "ci_method": "paired_four_week_cluster_t"}
    assert R.clears_heuristic_line(g, {"line": 5})
    assert R.observed_category("market", g) == "small"


def test_dates_are_resolved_in_input_order_and_missing_dates_are_rejected(monkeypatch):
    source = pd.DataFrame({"match_id": ["a", "b"], "tournament_date": pd.to_datetime(["2020-01-06", "2020-02-03"])})
    monkeypatch.setattr(R.C, "load_matches", lambda columns: source)
    assert np.array_equal(R.cluster_dates(pd.DataFrame({"match_id": ["b", "a"]})),
                          source.tournament_date.to_numpy(dtype="datetime64[ns]")[::-1])
    with pytest.raises(ValueError, match="tournament_date"):
        R.cluster_dates(pd.DataFrame({"match_id": ["unknown"]}))


def test_empty_family_has_no_threshold():
    got = R.family_line([], "atp", "market")
    assert got["rows"] == 0 and np.isnan(got["line"])


def test_both_studies_share_repaired_metrics_and_plain_scoring(monkeypatch):
    z, y, years, base = training_fixture()
    dates = pd.to_datetime(pd.Series(years).astype(str) + "-01-01") + pd.to_timedelta(np.arange(len(years)) % 300, unit="D")
    f = pd.DataFrame({"match_id": np.arange(len(years)), "tour": "atp", "year": years,
                      "tournament_date": dates, "a_won": y, "evaluation": years >= 2013,
                      "era": np.where(years <= 2015, "2013-2015", "2016-2018"), "group": "T250",
                      "p_elo": expit(base), "p_mkt": expit(base * 1.2), "x|single": z[0, :, 1]})
    state = {"f": f, "atp": np.arange(len(f)), "keys": np.random.default_rng(9).random((len(f), R.COPIES))}
    monkeypatch.setattr(R, "_D", state)
    monkeypatch.setattr(U, "_D", state)
    task = U.task("atp", "x", "single", "x", "regression", ["x|single"], scores=("elo", "market"))
    earlier, current = R.score_row(task), U.score_row(task)
    plain = U.score_plain(f, task)
    plain_earlier = R.score_plain(f, task, task["cols"])
    for score in task["scores"]:
        a, b = earlier["scores"][score]["groups"]["all"], current["scores"][score]["groups"]["all"]
        for metric in ("imp", "lo", "hi", "week_lo", "week_hi", "raw_baseline_imp", "raw_baseline_lo"):
            assert a[metric] == pytest.approx(b[metric])
            assert a[metric] == pytest.approx(plain[score][metric])
            assert a[metric] == pytest.approx(plain_earlier[score][metric])
        assert a["ci_method"] == b["ci_method"] == "paired_four_week_cluster_t"
