"""The study's fixed design: the swap of A and B on the 58 inputs, the owner's staking rule, the symmetrised query, and
the prepared upload (when it has been built).

Run: ./python.sh -m pytest test/tabpfn_thinking58/test_thinking58_design.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.tabpfn_thinking58 import common as C  # noqa: E402

KINDS = {"odds_logit": "diff", "elo_overall": "diff", "surf_season_a": "pair", "surf_season_b": "pair",
         "surface": "context"}


def frame(n=6, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(size=(n, len(KINDS))), columns=list(KINDS))


def test_flip_negates_differences_exchanges_pairs_keeps_context():
    X = frame()
    F = C.flip(X, KINDS)
    assert np.allclose(F["odds_logit"], -X["odds_logit"]) and np.allclose(F["elo_overall"], -X["elo_overall"])
    assert np.allclose(F["surf_season_a"], X["surf_season_b"]) and np.allclose(F["surf_season_b"], X["surf_season_a"])
    assert np.allclose(F["surface"], X["surface"])
    assert np.allclose(C.flip(F, KINDS), X)


def test_flip_refuses_a_column_without_a_kind():
    X = frame().assign(mystery=1.0)
    with pytest.raises(ValueError, match="no kind"):
        C.flip(X, KINDS)


def test_partner_of_pair_columns():
    assert C.partner("surf_layoff_a") == "surf_layoff_b" and C.partner("surf_layoff_b") == "surf_layoff_a"
    with pytest.raises(ValueError):
        C.partner("elo_overall")


def test_stake_follows_the_owners_rule():
    d = np.array([1.25, 1.5, 2.0, 2.5, 3.0, 5.0, 11.0])
    s = C.stake(d)
    wins = s * (d - 1)
    assert np.allclose(s[:3], [4.0, 2.0, 1.0])                 # favourites: to win 1; even money: 1 unit
    assert np.allclose(wins[:3], 1.0)
    assert np.allclose(s[3:], d[3:] / (2 * (d[3:] - 1)))       # underdogs: Kelly's shape, 1 unit at even money
    assert np.all((s[3:] < 1) & (np.diff(s[2:]) < 0))          # slightly under 1 unit, falling with the price
    assert np.all(wins[3:] > 1) and np.allclose(wins[3:], d[3:] / 2)
    assert np.isclose(C.stake(2.0 - 1e-9), C.stake(2.0 + 1e-9), atol=1e-6)   # the branches meet at even money


def test_stake_kelly_shape_for_a_constant_probability_edge():
    d = np.array([2.2, 3.0, 4.5, 8.0])
    delta = 0.01
    p = 1 / d + delta
    kelly = (p * d - 1) / (d - 1)
    kelly_even = (0.5 + delta) * 2 - 1                        # Kelly at even money for the same edge
    assert np.allclose(C.stake(d), kelly / kelly_even)


def test_stake_refuses_non_prices():
    for bad in (1.0, 0.5, np.nan):
        with pytest.raises(ValueError):
            C.stake([bad])


def test_symmetrised_pairs_each_match_with_its_swap():
    ids = pd.DataFrame({"match_id": ["m1", "m2", "m1", "m2", "m2", "m2"],
                        "block": ["td"] * 4 + ["early"] * 2, "orientation": [0, 0, 1, 1, 0, 1]})
    p = np.array([0.7, 0.4, 0.2, 0.5, 0.6, 0.3])
    out = C.symmetrised(p, ids)
    assert np.allclose(out["td"].to_numpy(), [0.5 * (0.7 + 0.8), 0.5 * (0.4 + 0.5)])
    assert np.allclose(out["early"].to_numpy(), [0.5 * (0.6 + 0.7)]) and list(out["early"].index) == ["m2"]


@pytest.mark.skipif(not (C.OUT / "manifest.json").exists(), reason="the upload has not been built")
def test_the_prepared_upload_is_the_58_input_model():
    X_train, y_train, X_query, ids, manifest = C.load_upload()
    names = [i["name"] for i in C.model_inputs()]
    assert manifest["names"] == names and len(names) == 58 and names[0] == "odds_logit"
    assert X_train.shape == (39918, 58) and len(y_train) == 39918
    assert all(v is True for v in manifest["checks"].values())
    n = manifest["query_blocks"]["td_matches"]
    assert n == 23819 and len(X_query) == 2 * n + 2 * manifest["query_blocks"]["early_matches"]
    kinds = manifest["kinds"]
    assert np.allclose(C.flip(X_query.iloc[n:2 * n].reset_index(drop=True), kinds).to_numpy(),
                       X_query.iloc[:n].to_numpy(), equal_nan=True)
    early = (ids["block"] == "early").to_numpy()
    assert ids.loc[early, "match_id"].isin(ids.loc[~early, "match_id"]).all()
    assert json.loads((C.OUT / "manifest.json").read_text(encoding="utf-8"))["input_fingerprint"] == \
        C.fingerprint(X_train, y_train, X_query)
