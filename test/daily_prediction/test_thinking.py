"""TabPFN-3.5-Thinking beside the local model (`run_day --thinking`; the owner, 20 Oct 2026; dp_thinking.py, dp_predict.py).

Offline: no token is spent and no network is reached (a stand-in backend answers instead of the hosted API).
    * the paid call is guarded: refused without --spend-tokens, the slot written before the call, the answers saved and
      only read back after, never sent twice, a slot without answers refused;
    * the answers are symmetrised as the local seeds are;
    * a fit made on other training rows is refused;
    * the 13 Oct paid answers replayed through the step: its query equals 13 Oct's rows bit for bit and its chances the
      13 Oct comparison's (real data; skipped when the run or its fit is gone);
    * the predict step on a copy of a live run: without Thinking it writes a local run's file as before; with Thinking
      the prediction used is the two models' chances averaged 50/50 in log-odds before the patterns, the patterns after,
      and each model's chance stands beside it (real data; skipped when the run is gone).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit, logit

from conftest import OUT, ROOT

import dp_common as DC
import dp_thinking as TK

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.eda.tabpfn_thinking58 import guard as G  # noqa: E402

RUNS = OUT / "runs"
RUN_13OCT = RUNS / "live_2026-10-13_163937"
ANSWERS_13OCT = ROOT / "data/studies/master_pipeline/thinking/template_2026-10-10/season2026/live_2026-10-13"
RUN_19OCT = RUNS / "live_2026-10-19_173201"
INSTANCES = ROOT / "data" / "studies" / "current_best_model"
CONFIG = {"model_path": "v3.5_default", "n_estimators": 8, "softmax_temperature": 0.9, "random_state": 0,
          "ignore_pretraining_limits": True, "thinking_mode": True, "thinking_effort": "high",
          "thinking_metric": "log_loss", "thinking_timeout_s": None, "http_timeout_s": 2700.0}


class StandIn:
    """The hosted API's place: answers each row with a fixed function of its first column; records its calls."""
    calls: list = []

    def __init__(self, config):
        self.config = config

    def preflight(self):
        lim = {"train_set_max_rows": 10**6, "test_set_max_rows": 10**6, "train_set_max_cells": 2 * 10**8,
               "test_set_max_cells": 2 * 10**8, "max_cols": 20000, "max_classes": 160}
        return {"authenticated": True, "settings": {"model_limits": {"v3.5": lim}},
                "usage": {"daily_usage": 10, "daily_limit": 5_000_000, "monthly_usage": 10, "monthly_limit": 20_000_000}}

    def resume(self, path):
        self.resumed = Path(path).name

    def predict(self, X, fit_state, before):
        before()
        StandIn.calls.append({"rows": len(X), "slot_written_first": (self.slot / "predict_slot.json").exists()})
        p = expit(np.asarray(X.iloc[:, 0], dtype=float))
        return {"probabilities": np.column_stack([1 - p, p]), "classes": [0, 1], "metadata": {"package_version": "x"}}

    def usage(self):
        return {"daily_usage": 25}


def _slot_and_query(tmp_path, monkeypatch, n=2):
    """A season fit slot (fit.json, fit_complete.json, fitted_model.json, train.npz) and a run whose query holds n
    matches at 3 grid prices and their own, stored then swapped (the layout dp_fit.season_jobs gives)."""
    monkeypatch.setattr(DC, "THINKING_FITS", tmp_path / "fits")
    slot = TK.fit_slot(Path("inst"), 2026)
    slot.mkdir(parents=True)
    cols = ["odds_logit", "x1"]
    fit = {"fitted_train_set_id": "fit-1", "train_sha256": "rows-1", "columns": cols, "config": CONFIG}
    (slot / "fit.json").write_text(json.dumps(fit), encoding="utf-8")
    (slot / "fit_complete.json").write_text(json.dumps({"fit_state": {"fitted_train_set_id": "fit-1"}}), encoding="utf-8")
    (slot / "fitted_model.json").write_text("{}", encoding="utf-8")
    np.savez(slot / "train.npz", X=np.zeros((5, 2)), y=np.array([0, 1, 0, 1, 1]), columns=np.asarray(cols))
    grid = np.array([-1.0, 0.0, 1.0])
    own = np.array([0.3, -0.4][:n])
    stored = pd.DataFrame({"odds_logit": np.r_[np.tile(grid, n), own], "x1": 1.0})
    swapped = stored.assign(odds_logit=-stored["odds_logit"])
    X = pd.concat([stored, swapped], ignore_index=True)
    run = tmp_path / "run"
    (run / "thinking").mkdir(parents=True)
    np.savez(run / "thinking" / "query.npz", X=X.to_numpy(), columns=np.asarray(cols))
    seg = {"season": 2026, "start": 0, "rows": len(X), "stored_rows": len(stored), "matches": n,
           "match_id": [f"m{i}" for i in range(n)], "own_logit": own.tolist(), "train_sha256": "rows-1",
           "query_sha256": TK.query_sha256(X), "fitted_train_set_id": "fit-1", "fit_slot": str(slot)}
    (run / "thinking" / "query.json").write_text(json.dumps({"query_sha256": TK.query_sha256(X), "rows": len(X),
                                                             "segments": [seg]}), encoding="utf-8")
    StandIn.slot = run / "thinking" / "season2026"
    StandIn.calls = []
    return run, X, grid, own


def test_the_paid_call_is_guarded(tmp_path, monkeypatch):
    run, X, _, _ = _slot_and_query(tmp_path, monkeypatch)
    season = run / "thinking" / "season2026"
    with pytest.raises(SystemExit, match="paid call"):
        TK.send(run, spend_tokens=False, backend_factory=StandIn)
    assert not StandIn.calls and not list(season.iterdir())                    # refused before anything was written
    assert TK.send(run, spend_tokens=True, backend_factory=StandIn) == {2026: "sent"}
    assert StandIn.calls == [{"rows": len(X), "slot_written_first": True}]
    assert {"predict_slot.json", "predictions.npz", "predict_complete.json"} <= {p.name for p in season.iterdir()}
    assert TK.send(run, spend_tokens=True, backend_factory=StandIn) == {2026: "read back"}
    assert len(StandIn.calls) == 1                                             # never sent twice
    (season / "predictions.npz").unlink()                                      # dispatched, outcome unknown
    with pytest.raises(G.OnceOnlyError, match="never repeated"):
        TK.send(run, spend_tokens=True, backend_factory=StandIn)
    assert len(StandIn.calls) == 1


def test_a_query_for_another_fit_is_refused(tmp_path, monkeypatch):
    run, _, _, _ = _slot_and_query(tmp_path, monkeypatch)
    q = json.loads((run / "thinking" / "query.json").read_text(encoding="utf-8"))
    q["segments"][0]["train_sha256"] = "other-rows"
    (run / "thinking" / "query.json").write_text(json.dumps(q), encoding="utf-8")
    with pytest.raises(G.OnceOnlyError, match="another fit"):
        TK.send(run, spend_tokens=True, backend_factory=StandIn)
    assert not StandIn.calls


def test_answers_are_symmetrised_as_the_local_seeds(tmp_path, monkeypatch):
    import dp_fit as FT
    run, X, grid, own = _slot_and_query(tmp_path, monkeypatch)
    monkeypatch.setattr(FT, "GRID", grid)
    TK.send(run, spend_tokens=True, backend_factory=StandIn)
    TK.read(run)
    th = TK.load(run, ["m1", "m0"])                                           # in the order asked
    p = expit(X["odds_logit"].to_numpy())
    k = len(X) // 2
    sym = 0.5 * (p[:k] + 1 - p[k:])
    assert np.allclose(th["grid"], sym[:6].reshape(2, 3)[::-1]) and np.allclose(th["own"], sym[6:][::-1])
    assert np.allclose(th["own"], expit(own[::-1]))                           # this stand-in is symmetric by design
    rec = json.loads((run / "thinking" / "thinking.json").read_text(encoding="utf-8"))
    assert rec["calibrated"] is False and rec["symmetrised"] is True and rec["seeds"] == [0]
    with pytest.raises(RuntimeError, match="no Thinking forecast"):
        TK.load(run, ["m0", "m9"])


def test_a_fit_on_other_training_rows_is_refused(tmp_path, monkeypatch):
    import dp_fit as FT
    import dp_tabcache as TC
    monkeypatch.setattr(DC, "THINKING_FITS", tmp_path / "fits")
    slot = TK.fit_slot(Path("inst"), 2026)
    slot.mkdir(parents=True)
    for name in TK.FIT_FILES:
        (slot / name).write_text("{}", encoding="utf-8")
    (slot / "fit.json").write_text(json.dumps({"train_sha256": "not-these-rows", "columns": ["a"],
                                               "fitted_train_set_id": "f"}), encoding="utf-8")
    X = pd.DataFrame({"a": [1.0, 2.0]})
    part = pd.DataFrame({"match_id": ["m0"], "in_odds_logit": [0.1]})
    monkeypatch.setattr(FT, "season_jobs", lambda run_dir, instance: iter([(2026, part, X, np.array([0, 1]), X, 1, 1)]))
    assert TC.train_sha256(X, np.array([0, 1])) != "not-these-rows"
    with pytest.raises(SystemExit, match="not the ones the Thinking fit was made on"):
        TK.build_query(tmp_path / "run", Path("inst"))


@pytest.mark.skipif(not ((RUN_13OCT / "live_frame.parquet").exists() and (ANSWERS_13OCT / "predictions.npz").exists()
                         and (DC.THINKING_FITS / "template_2026-10-10" / "season2026" / "fit.json").exists()),
                    reason="no 13 Oct run, answers or fit")
def test_the_13_oct_paid_answers_replay_through_the_step(tmp_path):
    """The run's query equals the 13 Oct query's rows of that run bit for bit; its paid answers, sent back through the
    guard by a stand-in, read back as the 13 Oct comparison's Thinking chances, exactly."""
    run = tmp_path / RUN_13OCT.name
    run.mkdir()
    for f in ("run.json", "live_frame.parquet", "live_meta.parquet"):
        shutil.copy2(RUN_13OCT / f, run / f)
    TK.build_query(run, INSTANCES / "template_2026-10-10")
    old = json.loads((ANSWERS_13OCT / "query.json").read_text(encoding="utf-8"))
    seg = next(s for s in old["segments"] if s["run"] == RUN_13OCT.name)
    with np.load(ANSWERS_13OCT / "query.npz") as z:
        part = z["X"][seg["start"]:seg["start"] + seg["rows"]]
    with np.load(run / "thinking" / "query.npz") as z:
        new = z["X"]
    assert new.shape == part.shape and np.array_equal(new, part, equal_nan=True)
    with np.load(ANSWERS_13OCT / "predictions.npz") as z:
        proba = z["probabilities"][seg["start"]:seg["start"] + seg["rows"]]

    class Saved(StandIn):
        def predict(self, X, fit_state, before):
            before()
            return {"probabilities": proba, "classes": [0, 1], "metadata": {}}
    TK.send(run, spend_tokens=True, backend_factory=Saved)
    TK.read(run)
    ids = seg["match_id"]
    want = pd.read_csv(ANSWERS_13OCT / "comparison.csv").set_index("match_id").loc[ids, "thinking_own_price_a"]
    assert np.array_equal(TK.load(run, ids)["own"], want.to_numpy())


@pytest.mark.skipif(not (RUN_19OCT / "predictions.csv").exists(), reason="no 19 Oct live run")
def test_the_prediction_used_is_the_average_of_the_two_models(tmp_path, monkeypatch):
    """On a copy of a live run: without Thinking the predict step writes a local run's columns, as before; with Thinking
    answers, q_a_local is that run's prediction, Thinking's chance takes stage 2's serve-speed term with the run's own
    b (men only) and never the calibration slope (the owner, 20 Oct 2026 evening), the ensemble before the patterns is
    the local stage-2 chance and that chance averaged 50/50 in log-odds, the patterns are added after it, and the curves
    and a reprice carry them all (the reprice's ensemble equal to the log-odds average of the two curves read at the new
    price: interpolation in log-odds is linear). (On
    20 Oct 2026 the local re-run also equalled the run's own predictions.csv bit for bit: master_pipeline process log,
    Part 6; not asserted here, as later corrections of the shared speed panel may legitimately move spd_L.)"""
    import dp_fit as FT
    import dp_predict as PR
    import dp_steps as S
    run = tmp_path / RUN_19OCT.name
    shutil.copytree(RUN_19OCT, run, ignore=shutil.ignore_patterns("stage0"))
    inst = INSTANCES / Path(json.loads((run / "run.json").read_text(encoding="utf-8"))["instance"]).name
    held = [PR.coef_path(inst, 2026, feed) for feed in ("weekly", "daily")]
    monkeypatch.setattr(PR, "STAGE2", tmp_path / "stage2")                  # the shared coefficients never written
    (tmp_path / "stage2").mkdir()
    for path in held:
        if path.exists():
            shutil.copy2(path, tmp_path / "stage2" / path.name)
    orig = pd.read_csv(RUN_19OCT / "predictions.csv")
    seeds, ck = list(range(16)), orig["checkpoint"].iloc[0]
    PR.run(run, seeds, inst, checkpoint=ck)
    local = pd.read_csv(run / "predictions.csv")
    assert list(local.columns) == list(orig.columns)                       # a local run's file is as it was
    d = FT.load(run, seeds)
    bump = np.linspace(-0.2, 0.2, len(d["match_id"]))
    th_own = expit(logit(d["own"].mean(axis=0)) + bump)
    th_grid = expit(logit(d["grid"].mean(axis=0)) + bump[:, None])
    TK.folder(run).mkdir()
    np.savez(TK.folder(run) / "thinking.npz", match_id=d["match_id"], grid=th_grid, own=th_own,
             own_logit=d["own_logit"])
    (TK.folder(run) / "thinking.json").write_text(json.dumps({"seasons": {}}), encoding="utf-8")
    PR.run(run, seeds, inst, checkpoint=ck, thinking=True)
    ens = pd.read_csv(run / "predictions.csv").set_index("match_id")
    L = local.set_index("match_id").loc[ens.index]
    th_api = pd.Series(th_own, index=d["match_id"]).loc[ens.index].to_numpy()
    assert (ens["ensemble"] == "on").all() and (ens["ensemble_weight_local"] == 0.5).all()
    assert np.array_equal(ens["q_a_local"], L["q_a"]) and np.array_equal(ens["q_a_local_patterns_off"],
                                                                          L["q_a_patterns_off"])
    # Thinking with the serve-speed term b x spd_L (the run's own b by season and feed), slope 1, men only
    coefs = json.loads((run / "provenance.json").read_text(encoding="utf-8"))["stage2"]["coefficients"]
    b = np.array([coefs[str(day)[:4] if feed == "weekly" else f"{str(day)[:4]}_{feed}"]["b_shrunk"]
                  for day, feed in zip(ens["day"], ens["speed_feed"])])
    men = (ens["tour"] == "atp").to_numpy()
    assert (men & (ens["spd_L"].to_numpy() != 0)).any()                                   # the term is exercised
    th = expit(logit(th_api) + np.where(men, b * ens["spd_L"].to_numpy(), 0.0))
    assert np.allclose(ens["q_a_thinking_api"], th_api, rtol=0, atol=1e-15)
    assert np.allclose(ens["q_a_thinking"], th, rtol=0, atol=1e-12)
    assert np.allclose(ens.loc[~men, "q_a_thinking"], ens.loc[~men, "q_a_thinking_api"], rtol=0, atol=1e-12)
    avg = expit(0.5 * logit(L["q_a_patterns_off"].to_numpy()) + 0.5 * logit(th))         # the log-odds average
    assert np.allclose(ens["q_a_patterns_off"], avg, rtol=0, atol=1e-12)
    plain = 0.5 * L["q_a_patterns_off"].to_numpy() + 0.5 * th
    assert not np.allclose(ens["q_a_patterns_off"], plain, rtol=0, atol=1e-9)             # not the plain average
    assert np.allclose(ens["q_a"], expit(logit(avg) + ens["pattern_shift"].to_numpy()), rtol=0, atol=1e-12)
    for c in ("p_base_a", "eta", "spd_L", "p_market_a", "gate"):
        assert ens[c].tolist() == L[c].tolist(), c
    cur = pd.read_parquet(run / "curves.parquet")
    assert {"q_a_local", "q_a_local_patterns_off", "q_a_thinking", "q_a_thinking_api"} <= set(cur.columns)
    prices = tmp_path / "prices.csv"
    pd.DataFrame({"match_id": ens.index, "p_a": np.clip(ens["p_market_a"] + 0.01, 0.06, 0.94)}).to_csv(prices,
                                                                                                    index=False)
    rep = pd.read_csv(S.reprice(run, prices)["file"]).dropna(subset=["q_a"])
    both = expit(0.5 * logit(rep["q_a_local_patterns_off"]) + 0.5 * logit(rep["q_a_thinking"]))
    assert np.allclose(rep["q_a_patterns_off"], both, rtol=0, atol=1e-12)
    assert rep["q_a_thinking_api"].notna().all()
    # a failed Thinking step: the local model alone, said in predictions.csv and provenance.json
    (TK.folder(run) / "failed.json").write_text(json.dumps({"reason": "test: the API refused"}), encoding="utf-8")
    PR.run(run, seeds, inst, checkpoint=ck, thinking=True)
    off = pd.read_csv(run / "predictions.csv")
    assert (off["ensemble"] == "off").all() and off["q_a_thinking"].isna().all()
    assert np.array_equal(off["q_a"], local["q_a"])
    prov = json.loads((run / "provenance.json").read_text(encoding="utf-8"))
    assert prov["thinking"]["ensemble"] == "off" and "API refused" in prov["thinking"]["failed"]
