"""The once-only dispatch guard: one fit and one prediction, never repeated after an unknown outcome, resumable from
the saved fit id or model record without a new fit. Offline: a fake backend stands in for the API.

Run: ./python.sh -m pytest test/tabpfn_thinking/test_guard.py
     ./python_tabpfn.sh -m pytest test/tabpfn_thinking/test_guard.py   (also checks the installed SDK's structure)
"""
from __future__ import annotations

import functools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.tabpfn_thinking import guard as G  # noqa: E402

LIMITS = {"train_set_max_rows": 10**6, "train_set_max_cells": 2 * 10**8, "test_set_max_rows": 10**6,
          "test_set_max_cells": 2 * 10**8, "max_cols": 20000, "max_classes": 160, "predict_row_pairs_budget": 2.5e11}


def frames(n_train=40, n_query=10, seed=0):
    rng = np.random.default_rng(seed)
    cols = ["elo_logit", "ratings_iid", "tour"]
    X = pd.DataFrame(rng.normal(size=(n_train, 3)), columns=cols)
    X["tour"] = rng.integers(0, 2, n_train).astype(float)
    y = (rng.random(n_train) < 0.5).astype(int)
    y[:2] = [0, 1]
    Q = pd.DataFrame(rng.normal(size=(n_query, 3)), columns=cols)
    Q["tour"] = 0.0
    return X, y, Q


class Fake:
    """A fake backend whose instances share call counters; behaviour switches simulate failures."""
    calls: dict = {}
    fail_fit_after_dispatch = False
    crash_after_submit = False
    fail_predict_after_dispatch = False

    def __init__(self, config):
        self.config = config

    @classmethod
    def reset(cls):
        cls.calls = {"fit": 0, "predict": 0, "wait": 0, "resume": 0, "save": 0}
        cls.fail_fit_after_dispatch = cls.crash_after_submit = cls.fail_predict_after_dispatch = False

    def preflight(self):
        return {"authenticated": True, "checked_at": "now",
                "usage": {"daily_usage": 0, "daily_limit": 5_000_000, "monthly_usage": 0, "monthly_limit": 20_000_000},
                "settings": {"model_limits": {"v3.5": LIMITS}}}

    def fit(self, X, y, before, on_submitted, *, description):
        Fake.calls["fit"] += 1
        before()
        if Fake.fail_fit_after_dispatch:
            raise TimeoutError("ambiguous")
        on_submitted("fake-id-1")
        if Fake.crash_after_submit:
            raise ConnectionError("lost while polling")
        return {"fitted_train_set_id": "fake-id-1", "classes": [0, 1]}

    def save_model(self, path):
        Fake.calls["save"] += 1
        Path(path).write_text(json.dumps({"model_id": "fake-id-1"}), encoding="utf-8")

    def resume(self, path):
        Fake.calls["resume"] += 1

    def wait_for_fit(self, fitted_id):
        Fake.calls["wait"] += 1
        return {"status": "completed", "fitted_train_set_id": fitted_id}

    def predict(self, X, fit_state, before):
        Fake.calls["predict"] += 1
        before()
        if Fake.fail_predict_after_dispatch:
            raise TimeoutError("ambiguous")
        p = np.linspace(0.2, 0.8, len(X))
        return {"probabilities": np.column_stack([1 - p, p]), "classes": [0, 1], "metadata": {"m": 1}}


@pytest.fixture(autouse=True)
def _reset():
    Fake.reset()
    yield


def run(tmp, X, y, Q, **kw):
    return G.execute_once(X, y, Q, tmp, expected_input_sha256=T.fingerprint(X, y, Q), fingerprint=T.fingerprint,
                          description="test", backend_factory=Fake, log=lambda *_: None, **kw)


def test_one_fit_one_predict_then_reuse(tmp_path):
    X, y, Q = frames()
    first = run(tmp_path, X, y, Q)
    assert not first["reused_saved_predictions"]
    assert Fake.calls == {"fit": 1, "predict": 1, "wait": 0, "resume": 0, "save": 1}
    for name in ("budget.json", "request.json", "fit_slot.json", "fit_attempt.json", "fit_submitted.json",
                 "fit_complete.json", "fitted_model.json", "predict_slot.json", "predictions.npz", "COMPLETE.json"):
        assert (tmp_path / name).exists(), name
    second = run(tmp_path, X, y, Q)
    assert second["reused_saved_predictions"]
    assert np.allclose(first["p_a"], second["p_a"])
    assert Fake.calls["fit"] == 1 and Fake.calls["predict"] == 1


def test_fingerprint_mismatch_stops_before_any_call(tmp_path):
    X, y, Q = frames()
    with pytest.raises(ValueError, match="fingerprint"):
        G.execute_once(X, y, Q, tmp_path, expected_input_sha256="0" * 64, fingerprint=T.fingerprint,
                       description="test", backend_factory=Fake, log=lambda *_: None)
    assert Fake.calls["fit"] == 0


def test_config_is_fixed(tmp_path):
    X, y, Q = frames()
    with pytest.raises(ValueError, match="fixed"):
        run(tmp_path, X, y, Q, config=dict(G.CONFIG, thinking_effort="medium"))


def test_ambiguous_fit_is_never_repeated(tmp_path):
    X, y, Q = frames()
    Fake.fail_fit_after_dispatch = True
    with pytest.raises(G.OnceOnlyError):
        run(tmp_path, X, y, Q)
    Fake.fail_fit_after_dispatch = False
    with pytest.raises(G.OnceOnlyError, match="no fit id"):
        run(tmp_path, X, y, Q)
    assert Fake.calls["fit"] == 1


def test_submitted_fit_resumes_by_polling_without_a_new_fit(tmp_path):
    X, y, Q = frames()
    Fake.crash_after_submit = True
    with pytest.raises(G.OnceOnlyError):
        run(tmp_path, X, y, Q)
    Fake.crash_after_submit = False
    out = run(tmp_path, X, y, Q)
    assert Fake.calls["fit"] == 1 and Fake.calls["wait"] == 1 and Fake.calls["predict"] == 1
    assert json.loads((tmp_path / "fit_complete.json").read_text(encoding="utf-8"))["resumed"] is True
    assert len(out["p_a"]) == len(Q)


def test_ambiguous_prediction_is_never_repeated(tmp_path):
    X, y, Q = frames()
    Fake.fail_predict_after_dispatch = True
    with pytest.raises(G.OnceOnlyError):
        run(tmp_path, X, y, Q)
    Fake.fail_predict_after_dispatch = False
    with pytest.raises(G.OnceOnlyError, match="unknown outcome"):
        run(tmp_path, X, y, Q)
    assert Fake.calls["predict"] == 1 and Fake.calls["fit"] == 1


def test_changed_inputs_cannot_reuse_the_study_directory(tmp_path):
    X, y, Q = frames()
    run(tmp_path, X, y, Q)
    X2 = X.copy()
    X2.iloc[0, 0] += 1.0
    with pytest.raises(G.OnceOnlyError, match="different request"):
        run(tmp_path, X2, y, Q)


def test_live_dispatch_needs_the_canonical_directory(tmp_path):
    X, y, Q = frames()
    with pytest.raises(ValueError, match="canonical"):
        G.execute_once(X, y, Q, tmp_path, expected_input_sha256=T.fingerprint(X, y, Q), fingerprint=T.fingerprint,
                       description="test", backend_factory=None, log=lambda *_: None)


def test_account_limits_are_enforced():
    X, y, Q = frames()
    acct = Fake(None).preflight()
    assert G.validate_account(acct, X, Q)["training_rows"] == len(X)
    small = json.loads(json.dumps(acct))
    small["settings"]["model_limits"]["v3.5"]["train_set_max_rows"] = 10
    with pytest.raises(ValueError, match="train_set_max_rows"):
        G.validate_account(small, X, Q)
    spent = json.loads(json.dumps(acct))
    spent["usage"]["daily_usage"] = spent["usage"]["daily_limit"]
    with pytest.raises(ValueError, match="limit"):
        G.validate_account(spent, X, Q)


def test_one_dispatch_strips_the_retry_and_runs_hooks_once():
    attempts = []

    def retry_once(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except TimeoutError:
                return fn(*args, **kwargs)
        return wrapper

    class Service:
        @classmethod
        @retry_once
        def _predict(cls, x):
            attempts.append(x)
            raise TimeoutError("server slow")

    hooks = []
    with pytest.raises(TimeoutError):
        with G._one_dispatch(Service, "_predict", lambda: hooks.append("before")):
            Service._predict(1)
    assert attempts == [1] and hooks == ["before"]
    with pytest.raises(TimeoutError):                    # outside the guard the SDK retry is back
        Service._predict(2)
    assert attempts == [1, 2, 2]


def test_installed_sdk_has_the_inspected_structure():
    client = pytest.importorskip("tabpfn_client.client")
    from importlib.metadata import version
    assert version("tabpfn-client") == G.SDK_VERSION
    for method in ("_submit_fit_job", "_predict"):
        d = client.ServiceClient.__dict__[method]
        assert isinstance(d, classmethod) and hasattr(d.__func__, "__wrapped__"), method
    assert isinstance(client.ServiceClient.__dict__["_wait_for_fit"], classmethod)
