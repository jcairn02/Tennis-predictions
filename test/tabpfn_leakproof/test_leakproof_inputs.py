"""The leak-proof refit changes only the solved-together (IOS) inputs, and keeps the original model's input order.

Run: ./python.sh -m pytest test/tabpfn_leakproof/test_leakproof_inputs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_leakproof import common as C  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402


def test_the_inputs_are_the_original_models_in_the_original_order():
    assert C.NAMES == T.TABPFN_NAMES and C.NAMES[0] == "odds_logit" and len(C.NAMES) == 54


def test_only_the_solved_together_inputs_are_replaced():
    ios = {f["name"] for f in T.FEATURES if f["group"] == "profile_traits"} | {"ios_points_short"}
    assert set(C.REPLACED) == ios and len(ios) == 22
    assert "odds_logit" not in C.REPLACED and not set(C.REPLACED) & set(T.CONTEXT)
    assert all(name in T.DIFF for name in C.REPLACED)        # every replaced input is an A - B difference


def test_each_replaced_input_reads_its_own_leakproof_column():
    for s in T.IOS_STATS:
        assert C.REPLACED[f"iosO_{s}"] == f"ios_O_{s}|single" and C.REPLACED[f"iosD_{s}"] == f"ios_D_{s}|single"
        assert C.REPLACED[f"prod_{s}"] == f"prod_{s}|single"
    assert C.REPLACED["ios_points_short"] == "ios_short"
    assert len(set(C.REPLACED.values())) == len(C.REPLACED)
