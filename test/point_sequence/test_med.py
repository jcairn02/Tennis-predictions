"""Tests for the E1 medical-event gate (src/eda/point_sequence/med_*.py): exposure coding and the numpy regressions."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import med_build as B  # noqa: E402
from src.eda.point_sequence import med_stats as S  # noqa: E402


# ---------------------------------------------------------------------------------------------
# exposure coding

def test_record_kind():
    assert B.record_kind("PhysioCalled", "PhysioCalled") == "call"
    assert B.record_kind("MedicalTreatment", "PhysioCalled") == "call"          # 2019 vocabulary
    assert B.record_kind("PhysioCallCancelled", "PhysioCancelled") == "cancel"
    assert B.record_kind("MedicalTreatment", "PhysioCancelled") == "cancel"
    assert B.record_kind("MedicalTreatment", "NoTreatment") == "cancel"
    assert B.record_kind("MedicalTreatment", "TreatmentInProgress") == "treat"
    assert B.record_kind("MedicalTreatment", "TreatmentComplete") == "treat"
    assert B.record_kind("MedicalTreatment", "PhysioEvaluationStarted") == "eval"
    assert B.record_kind("ToiletBreak", "NoClothingChanged") == "toilet"
    assert B.record_kind("Suspension", "Injury") is None
    assert B.record_kind("Let", None) is None


def test_treated_flag():
    assert B.treated_flag(1, 0, 0, 0)            # a call not cancelled
    assert not B.treated_flag(1, 1, 0, 1)        # call, evaluation, cancelled (2022+ pattern)
    assert B.treated_flag(1, 1, 1, 1)            # cancelled once, treated later
    assert B.treated_flag(0, 0, 1, 0)            # a treatment without a logged call (2020/2021)
    assert B.treated_flag(0, 0, 0, 1)            # an evaluation with nothing else
    assert not B.treated_flag(0, 1, 0, 1)        # an evaluation ending in "no treatment"
    assert B.treated_flag(2, 1, 0, 0)            # two calls, one cancelled
    assert not B.treated_flag(0, 0, 0, 0)


def test_attribute_suspension():
    assert B.attribute_suspension(50, [], {}) == 0
    assert B.attribute_suspension(50, [2], {2: [10]}) == 2
    # both treated: the nearest medical record before the suspension wins
    assert B.attribute_suspension(50, [1, 2], {1: [10, 20], 2: [45]}) == 2
    assert B.attribute_suspension(50, [1, 2], {1: [48], 2: [45]}) == 1
    # nobody before: the nearest after
    assert B.attribute_suspension(5, [1, 2], {1: [30], 2: [9]}) == 2


def test_exposures_frame():
    ev = pd.DataFrame([
        # match k1: side 1 called and cancelled, side 2 treated; an injury suspension follows side 2's treatment
        ("k1", 10, "PhysioCalled", "PhysioCalled", 1),
        ("k1", 11, "PhysioCallCancelled", "PhysioCancelled", 1),
        ("k1", 20, "PhysioCalled", "PhysioCalled", 2),
        ("k1", 21, "MedicalTreatment", "TreatmentComplete", 2),
        ("k1", 30, "Suspension", "Injury", 0),
        ("k1", 40, "ToiletBreak", "NoClothingChanged", 1),
        # match k2: a heat suspension with nobody treated -> unattributed; a 2019-style treatment
        ("k2", 5, "MedicalTreatment", "PhysioCalled", 1),
        ("k2", 6, "MedicalTreatment", "TreatmentInProgress", 1),
        ("k3", 7, "Suspension", "Heat", 0),
        ("k3", 8, "Suspension", "HeatBreak10Minutes", 0),
    ], columns=["key", "index", "name", "reason", "player_side_ab"])
    ex, audit = B.exposures(ev)
    ex = ex.set_index(["key", "side_n"])
    assert not ex.loc[("k1", 1), "treated"] and ex.loc[("k1", 1), "toilet"]
    assert ex.loc[("k1", 2), "treated"] and ex.loc[("k1", 2), "injury"]
    assert ex.loc[("k2", 1), "treated"] and not ex.loc[("k2", 1), "injury"]
    assert audit["suspensions_injury_illness_heat"] == 2      # HeatBreak10Minutes is not counted
    assert audit["attributed"] == 1 and audit["unattributed_no_treated_player"] == 1


# ---------------------------------------------------------------------------------------------
# regressions

def test_poisson_single_binary_rr():
    rng = np.random.default_rng(1)
    n = 20000
    x = rng.integers(0, 2, n)
    y = rng.random(n) < np.where(x == 1, 0.06, 0.03)
    X = np.column_stack([np.ones(n), x])
    fit = S.poisson_fit(y, X, cluster=np.arange(n), ridge=0.0)
    rr = math.exp(fit["coef"][1])
    assert abs(rr - y[x == 1].mean() / y[x == 0].mean()) < 1e-6
    # robust SE of log RR equals the delta-method SE for two independent proportions
    p1, p0 = y[x == 1].mean(), y[x == 0].mean()
    n1, n0 = (x == 1).sum(), (x == 0).sum()
    se = math.sqrt((1 - p1) / (n1 * p1) + (1 - p0) / (n0 * p0))
    assert abs(math.sqrt(fit["cov"][1, 1]) - se) / se < 0.01


def test_wls_matches_lstsq():
    rng = np.random.default_rng(2)
    n = 500
    X = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n)])
    w = rng.uniform(0.5, 2, n)
    y = X @ np.array([1.0, -0.5, 2.0]) + rng.normal(size=n)
    fit = S.wls_fit(y, X, w, cluster=np.arange(n))
    sw = np.sqrt(w)
    ref, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    assert np.allclose(fit["coef"], ref)


def test_logit_recovers():
    rng = np.random.default_rng(3)
    n = 50000
    x = rng.normal(size=n)
    p = 1 / (1 + np.exp(-(-2 + 0.7 * x)))
    y = rng.random(n) < p
    b = S.logit_fit(y, np.column_stack([np.ones(n), x]), ridge=0.0)
    assert abs(b[0] + 2) < 0.06 and abs(b[1] - 0.7) < 0.05


def test_holm():
    adj = S.holm([0.01, 0.04, 0.03, 0.2])
    assert np.allclose(adj, [0.04, 0.09, 0.09, 0.2])


def test_mh_rr_one_stratum_equals_crude():
    y = np.array([1, 0, 0, 0, 1, 1, 0, 0, 0, 0])
    x = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    r = S.mh_rr(y, x, np.zeros(10))
    assert abs(r["est"] - (1 / 4) / (2 / 6)) < 1e-12
