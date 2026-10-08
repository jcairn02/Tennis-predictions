"""Decision-relevant score checks; no hosted API is used."""
import json

import numpy as np
import pandas as pd
import pytest

from src.eda.predictive_frontier_tabpfn import score as S


def frame():
    f = pd.DataFrame({"match_id": ["a", "b", "c", "d"], "tour": "atp", "year": 2026,
                      "tournament_date": pd.to_datetime(["2026-01-05", "2026-01-06", "2026-03-05", "2026-04-05"]),
                      "a_won": [1, 0, 1, 0], "tabpfn": [.8, .2, .7, .3],
                      "logistic_combined_fixed": [.6, .4, .6, .4],
                      "logistic_strong_fixed": [.5, .5, .5, .5],
                      "logistic_combined_annual": [.55, .45, .55, .45],
                      "p_avg_a": [.75, .25, .75, .25], "average_calibrated": [.7, .3, .7, .3],
                      "p_ps_a": [.9, .1, np.nan, np.nan], "pinnacle_calibrated": [.85, .15, np.nan, np.nan]})
    return f


def test_logloss_penalizes_confident_wrong_forecasts_and_handles_boundaries():
    assert S.loss([1, 0], [.5, .5]).mean() == pytest.approx(np.log(2))
    assert S.loss([1], [.9])[0] < S.loss([1], [.7])[0] < S.loss([1], [.1])[0]
    assert np.isfinite(S.loss([1, 0], [0., 1.])).all()
    with pytest.raises(ValueError):
        S.loss([1], [1.01])


def test_symmetry_reverses_consistently():
    a, b = np.array([.8, .7]), np.array([.3, .4])
    assert np.allclose(S.symmetrize(a, b), [.75, .65])
    assert np.allclose(S.symmetrize(b, a), 1 - S.symmetrize(a, b))


def test_pairing_uses_only_shared_market_matches():
    f = frame()
    r = S.compare(f, "p_ps_a", "tabpfn", "pinnacle_closing", np.ones(4, dtype=bool))
    assert r["n"] == 2
    assert r["model_ll"] == pytest.approx(-np.log(.8))
    assert r["base_ll"] == pytest.approx(-np.log(.9))
    assert r["gain_mll"] < 0
    assert r["clusters"] == 1
    assert r["lo_mll"] is None and r["hi_mll"] is None
    json.dumps(r, allow_nan=False)


def test_interval_centers_on_match_weighted_not_cluster_weighted_gain():
    dates = pd.to_datetime(["2026-01-05"] * 3 + ["2026-04-05"])
    result = S.paired_interval([.01, .01, .01, -.01], dates)
    assert result["gain_mll"] == pytest.approx(5.)
    assert result["lo_mll"] < 0 < result["hi_mll"]


def test_no_fake_uncertainty_when_no_data():
    r = S.paired_interval([], [])
    assert r == {"clusters": 0, "gain_mll": None, "lo_mll": None, "hi_mll": None}
    json.dumps(r, allow_nan=False)


def test_summarize_enforces_atp_2026_and_common_rows():
    f = frame()
    out = S.summarize(f)
    assert {r["n"] for r in out["scores"] if r["subset"] == "all_2026"} == {4}
    assert {r["n"] for r in out["scores"] if r["subset"] == "pinnacle_closing"} == {2}
    for key, value in (("tour", "wta"), ("year", 2025)):
        wrong = f.copy()
        wrong.loc[0, key] = value
        with pytest.raises(ValueError):
            S.summarize(wrong)
    f.loc[0, "average_calibrated"] = np.nan
    with pytest.raises(ValueError, match="Missing"):
        S.summarize(f)


def test_report_uses_scored_values_and_explains_small_pinnacle_subset():
    f = frame()
    result = {"generated_at": "2026-10-02", **S.summarize(f)}
    info = {"manifest": {"config": S.G.CONFIG, "input_sha256": "abc", "train_selection": {"strategy": "all"}},
            "metadata": {}, "training_rows": 1000, "test_rows": 4, "query_rows": 8,
            "train_first_date": "2013-01-01", "train_last_date": "2025-12-31",
            "test_first_date": "2026-01-05", "test_last_date": "2026-04-05", "training_year_counts": {"2025": 1000},
            "asymmetry_mean_abs": 0., "asymmetry_p95": 0., "asymmetry_max": 0.}
    report = S.render_report(result, info)
    assert "TabPFN had lower log loss" in report
    assert "Only 2 of 4 test matches" in report
    assert "Unavailable: fewer than two time blocks" in report
    assert f'{S.loss(f.a_won, f.tabpfn).mean():.5f}' in report
    assert "not untouched research data" in report


@pytest.fixture
def saved_run(tmp_path, monkeypatch):
    """A local saved run, with no backend, for identity and receipt checks."""
    out, thinking = tmp_path, tmp_path / "thinking"
    thinking.mkdir()
    monkeypatch.setattr(S.C, "OUT", out)
    monkeypatch.setattr(S.C, "THINKING", thinking)
    f = frame()
    f["split"] = "test"
    train = f.iloc[:2].copy()
    train["match_id"] = ["train1", "train2"]
    train["year"] = [2024, 2025]
    train["tournament_date"] = pd.to_datetime(["2024-05-01", "2025-05-01"])
    train["split"] = "train"
    pd.concat([train, f], ignore_index=True).to_parquet(out / "frame.parquet", index=False)
    f[["match_id", *S.SPORTS_MODELS[1:], "average_calibrated", "pinnacle_calibrated"]].to_parquet(out / "baselines.parquet", index=False)
    manifest = {"input_sha256": "frozen-test-hash", "config": S.G.CONFIG}
    ids = pd.DataFrame({"match_id": list(f.match_id) * 2, "orientation": [0] * 4 + [1] * 4})
    x = pd.DataFrame(np.zeros((2, 36)), columns=S.C.NAMES)
    q = pd.DataFrame(np.zeros((8, 36)), columns=S.C.NAMES)
    monkeypatch.setattr(S.C, "load_upload", lambda: (x, np.array([0, 1]), q, ids, manifest))
    binding = S.G.binding_for(manifest["input_sha256"], manifest["config"])
    p = np.r_[f.tabpfn.to_numpy(), 1 - f.tabpfn.to_numpy()]
    metadata = {"n_estimators": 8}
    S.G._save_predictions(thinking / "predictions.npz", np.column_stack([1 - p, p]), [0, 1], metadata, binding)
    for name in ("fit_slot.json", "predict_slot.json"):
        (thinking / name).write_text(json.dumps(binding), encoding="utf-8")
    (thinking / "fit_complete.json").write_text(json.dumps({"binding": binding}), encoding="utf-8")
    complete = {**binding, "status": "COMPLETE", "fit_requests_dispatched": 1,
                "prediction_requests_dispatched": 1, "prediction_sha256": S.C.sha256_file(thinking / "predictions.npz"),
                "query_rows": 8, "metadata": metadata}
    (thinking / "COMPLETE.json").write_text(json.dumps(complete), encoding="utf-8")
    return out, thinking


def test_load_only_scores_a_completed_correctly_bound_run(saved_run):
    f, info = S.load()
    assert len(f) == 4
    assert info["training_rows"] == 2
    assert np.allclose(f.tabpfn, frame().tabpfn)
    path = saved_run[1] / "fit_slot.json"
    bad = json.loads(path.read_text())
    bad["input_sha256"] = "another-study"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="another request"):
        S.load()


def test_load_refuses_baseline_row_reordering(saved_run):
    path = saved_run[0] / "baselines.parquet"
    base = pd.read_parquet(path).iloc[::-1]
    base.to_parquet(path, index=False)
    with pytest.raises(ValueError, match="IDs/order"):
        S.load()


def test_training_history_table_uses_best_pre2026_ridge_per_strategy():
    selection = {"strategy": "latest6", "validation_years": [2023, 2024, 2025], "candidates": [
        {"strategy": "all", "penalty": .001, "log_loss": .615, "validation_rows": 7784},
        {"strategy": "all", "penalty": .01, "log_loss": .613, "validation_rows": 7784},
        {"strategy": "latest6", "penalty": .01, "log_loss": .612, "validation_rows": 7784},
        {"strategy": "latest4", "penalty": .01, "log_loss": .614, "validation_rows": 7784}]}
    table = S.training_choice_html(selection)
    assert "Why train on 2020–2025?" in table
    assert "0.613000" in table and "0.615000" not in table
    assert "1.00 milli-log-loss" in table
    assert "7,784 validation matches" in table
    assert "2026 scores" in table
