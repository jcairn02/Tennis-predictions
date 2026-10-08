"""Offline tests for the cross-fitted sharpness tiers."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "polymarket_sharp_money"))

import classify as K  # noqa: E402


def test_tier_rules():
    n = np.array([0, 3, 15, 15, 50, 50, 50, 150, 150])
    z = np.array([np.nan, 5.0, 3.0, -3.0, 2.5, -2.5, 1.0, 0.0, 2.0])
    assert K.tier_of(n, z).tolist() == ["new", "occasional", "regular", "regular", "winning", "losing", "regular",
                                        "heavy", "winning"]


def test_crossfit_never_uses_the_scored_market():
    # one wallet, two folds: a win in fold 0 and a loss in fold 1; each fold's history must be the other fold's
    wm = pd.DataFrame({"proxy_wallet": ["w"] * 4, "condition_id": ["a", "b", "c", "d"], "stake": [100.0] * 4,
                       "net": [30.0, 30.0, -30.0, -30.0], "var_qv": [25.0] * 4, "stake_taker": [100.0] * 4})
    scored = K.crossfit(wm, pd.Series({"a": 0, "b": 0, "c": 1, "d": 1})).set_index("condition_id")
    assert np.allclose(scored.loc[["a", "b"], "e_hist"], -0.30)
    assert np.allclose(scored.loc[["c", "d"], "e_hist"], 0.30)
    assert (scored.n_hist == 2).all() and (scored.tier == "occasional").all()


def test_wallet_seen_only_in_one_fold_is_new():
    wm = pd.DataFrame({"proxy_wallet": ["w", "v"], "condition_id": ["a", "b"], "stake": [10.0, 10.0],
                       "net": [1.0, -1.0], "var_qv": [1.0, 1.0], "stake_taker": [10.0, 10.0]})
    scored = K.crossfit(wm, pd.Series({"a": 0, "b": 1}))
    assert (scored.n_hist == 0).all() and (scored.tier == "new").all()
