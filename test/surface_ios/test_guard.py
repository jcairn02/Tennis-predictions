"""The surface-IOS study's dispatch guard: one fit and one prediction per registered slot, never repeated after an
unknown outcome, a fixed list of slots and configurations. Offline: the leak-proof study's fake backend.

Run: ./python.sh -m pytest test/surface_ios/test_guard.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test" / "tabpfn_leakproof"))

from src.eda.tabpfn_thinking import common as T  # noqa: E402
from src.eda.surface_ios import guard as G  # noqa: E402
from test_leakproof_guard import Fake, frames  # noqa: E402

REG = {"base_s0_2022": G.slot_config(0), "base_s1_2022": G.slot_config(1), "surf_s0_2022": G.slot_config(0)}


@pytest.fixture(autouse=True)
def _reset():
    Fake.reset()
    yield


def run(tmp, slot, X, y, Q, registered=REG):
    return G.execute_once(slot, registered, X, y, Q, expected_input_sha256=T.fingerprint(X, y, Q),
                          fingerprint=T.fingerprint, description="test", backend_factory=Fake, root=tmp,
                          log=lambda *_: None)


def test_one_fit_one_predict_per_slot_then_reuse(tmp_path):
    X, y, Q = frames()
    a = run(tmp_path, "base_s0_2022", X, y, Q)
    b = run(tmp_path, "base_s1_2022", X, y, Q)
    assert Fake.calls["fit"] == 2 and Fake.calls["predict"] == 2
    again = run(tmp_path, "base_s0_2022", X, y, Q)
    assert again["reused_saved_predictions"] and np.allclose(a["p_a"], again["p_a"])
    assert Fake.calls["fit"] == 2 and Fake.calls["predict"] == 2
    req = json.loads((tmp_path / "base_s1_2022" / "request.json").read_text(encoding="utf-8"))
    assert req["config"]["random_state"] == 1 and req["config"]["thinking_mode"] is False
    assert req["config"]["model_path"] == "v3.5_default"
    assert not b["reused_saved_predictions"]


def test_unregistered_slot_refused(tmp_path):
    X, y, Q = frames()
    with pytest.raises(ValueError, match="registered"):
        run(tmp_path, "other_s0_2022", X, y, Q)
    assert Fake.calls["fit"] == 0


def test_registered_slots_cannot_change(tmp_path):
    X, y, Q = frames()
    run(tmp_path, "base_s0_2022", X, y, Q)
    changed = dict(REG, base_s1_2022=G.slot_config(7))
    with pytest.raises(G.OnceOnlyError, match="changed"):
        run(tmp_path, "base_s1_2022", X, y, Q, registered=changed)


def test_ambiguous_prediction_never_repeated(tmp_path):
    X, y, Q = frames()
    Fake.fail_predict_after_dispatch = True
    with pytest.raises(G.OnceOnlyError):
        run(tmp_path, "surf_s0_2022", X, y, Q)
    Fake.fail_predict_after_dispatch = False
    with pytest.raises(G.OnceOnlyError, match="unknown outcome"):
        run(tmp_path, "surf_s0_2022", X, y, Q)
    assert Fake.calls["predict"] == 1


def test_changed_inputs_cannot_reuse_a_slot(tmp_path):
    X, y, Q = frames()
    run(tmp_path, "base_s0_2022", X, y, Q)
    X2 = X.copy()
    X2.iloc[0, 0] += 1.0
    with pytest.raises(G.OnceOnlyError, match="different request"):
        run(tmp_path, "base_s0_2022", X2, y, Q)


def test_live_dispatch_needs_the_canonical_directory(tmp_path):
    X, y, Q = frames()
    with pytest.raises(ValueError, match="canonical"):
        G.execute_once("base_s0_2022", REG, X, y, Q, expected_input_sha256=T.fingerprint(X, y, Q),
                       fingerprint=T.fingerprint, description="test", backend_factory=None, root=tmp_path,
                       log=lambda *_: None)
