"""Tests of the feature-provenance study (src/eda/feature_provenance/).

Run: ./python.sh -m pytest test/feature_provenance -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.feature_provenance import edge_by_season as E  # noqa: E402
from src.eda.feature_provenance import ledger as L  # noqa: E402


def test_ledger_covers_exactly_the_58_inputs():
    names = [i["name"] for i in json.loads(L.INPUTS.read_text())["inputs"]]
    listed = [n for g in L.GROUP_RECORDS for n in g["inputs"]]
    assert len(names) == 58 and sorted(listed) == sorted(names)


def test_ledger_labels_are_known():
    for g in L.GROUP_RECORDS:
        assert g["constants_label"] in L.CONSTANT_LABELS
        assert g["group"] in L.GROUPS
    assert {r["constants_label"] for r in L.STAGE2} <= L.CONSTANT_LABELS


def test_edge_reads_no_season_after_2024():
    f = E.load_frame()
    assert E.LAST_SEASON == 2024 and f["season"].max() <= 2024
    assert f["tournament_date"].max() <= pd.Timestamp("2024-12-31")


def test_paired_interval_on_a_constant_difference():
    est, lo, hi, g = E.paired(np.full(40, 0.002), np.repeat(np.arange(8), 5))
    assert g == 8 and abs(est - 2.0) < 1e-12 and abs(lo - 2.0) < 1e-9 and abs(hi - 2.0) < 1e-9


def test_slope_recovers_a_known_coefficient():
    rng = np.random.default_rng(0)
    z = rng.normal(0.0, 1.5, 200_000)
    y = (rng.random(z.size) < 1 / (1 + np.exp(-0.9 * z))).astype(float)
    assert abs(E.fit_slope(z, y) - 0.9) < 0.02
