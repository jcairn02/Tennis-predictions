"""Tests of the shared builders' inputs: the score parser and the history's ordering (no data), and, on the real tables
(no results read), the panel's reproduction of the model's inputs and its swap helper."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import history as H  # noqa: E402
from src.eda.feature_interactions import panel as PN  # noqa: E402


def test_parse_score():
    assert H.parse_score("6-4 3-6 7-6(5)") == (3.0, 32.0, 1.0, 2.0)
    assert H.parse_score("7-6(3) 6-7(4) 6-3 RET") == (3.0, 35.0, 2.0, 2.0)
    assert np.isnan(H.parse_score("W/O")[0]) and np.isnan(H.parse_score(None)[0])
    assert H.parse_score("6-7(2) 7-6(9) 7-6(5)")[2] == 3.0


def test_swap_sides_helper():
    P = pd.DataFrame({"x_a": [1.0, 2.0], "x_b": [3.0, 5.0], "a_won": [True, False], "ctx": [7.0, 8.0]})
    Q = PN.swap_sides(P)
    assert Q["x_a"].tolist() == [3.0, 5.0] and Q["x_b"].tolist() == [1.0, 2.0] and Q["a_won"].tolist() == [False, True]
    assert PN.check_swap(lambda T: T["x_a"] - T["x_b"], P, kind="diff")
    assert PN.check_swap(lambda T: T["x_a"] + T["x_b"], P, kind="context")
    assert not PN.check_swap(lambda T: T["x_a"], P, kind="diff")


@pytest.mark.skipif(not PN.SOURCES["surface_features"].exists(), reason="data not on disk")
def test_panel_reproduces_model_inputs():
    warnings.simplefilter("ignore")
    P = PN.panel(max_season=2015)
    assert P["season"].max() <= 2015
    d = (P["ios_srfO_hold_a"] - P["ios_srfO_hold_b"]) - P["in_iosO_hold"]
    assert np.nanmax(np.abs(d)) < 1e-12
    prod = P["ios_srfO_df_a"] * (-P["ios_srfD_df_b"]) - P["ios_srfO_df_b"] * (-P["ios_srfD_df_a"]) - P["in_prod_df"]
    assert np.nanmax(np.abs(prod)) < 1e-12
    assert np.nanmax(np.abs((P["sets_14d_a"] - P["sets_14d_b"]) - P["in_sets_14d"])) < 1e-6


@pytest.mark.skipif(not PN.SOURCES["stage0_matches"].exists(), reason="data not on disk")
def test_history_order_and_rest():
    warnings.simplefilter("ignore")
    L = H.long_table()
    g = L.groupby("player_id")
    assert (g["k"].diff().dropna() == 1).all()
    assert (L["rest_days"].dropna() >= 0).all()
    # rounds never reverse within a player's event (verifier B3), and rest is never negative
    ev = L.groupby(["player_id", "tournament_id", "tday"])["round_order"].diff().dropna()
    assert (ev >= 0).all()
    assert (g["obs_mono"].diff().dropna() >= 0).all()


def test_trait_permuter_restores_and_permutes_within_tour():
    from src.eda.feature_interactions import screen_batch as B
    rng = np.random.default_rng(0)
    n = 400
    players = np.array([f"p{i}" for i in range(60)])
    pa = rng.choice(players[:30], n)
    pb = rng.choice(players[30:], n)
    height = {p: (np.nan if i % 7 == 0 else 170.0 + i) for i, p in enumerate(players)}
    tour = np.where(np.isin(pa, players[:15]), "atp", "wta")
    P = pd.DataFrame({"player_a_id": pa, "player_b_id": pb, "tour": tour,
                      "height_a": [height[p] for p in pa], "height_b": [height[p] for p in pb]})
    spec = {"trait_cols": ["height"], "combine": lambda Q: {"x": (Q["height_a"] - Q["height_b"]).to_numpy(float)}}
    before = P.copy()
    perm = B._trait_permuter(P, {}, spec, np.arange(n), np.zeros(n))
    x1, _ = perm(np.random.default_rng(1))
    pd.testing.assert_frame_equal(P, before)                       # restored
    assert not np.allclose(np.nan_to_num(x1), np.nan_to_num((P["height_a"] - P["height_b"]).to_numpy()))
    # missing heights stay missing for the same players (B6)
    assert (np.isnan(x1) == np.isnan((P["height_a"] - P["height_b"]).to_numpy())).all()


def test_table_hash_sees_eta_modulator_values():
    """Verifier B4 / checkpoint 1 F-9: changing an eta-modulator control's values must change the frozen table hash."""
    import types
    from src.eda.feature_interactions import screen_batch as B
    rng = np.random.default_rng(3)
    n = 300
    P = pd.DataFrame({"match_id": np.arange(n).astype(str), "season": np.repeat([2015, 2023], n // 2),
                      "tour": np.where(rng.random(n) < 0.5, "atp", "wta"), "in_odds_logit": rng.normal(size=n),
                      "eta_model": rng.normal(size=n), "u_a": rng.normal(size=n), "u_b": rng.normal(size=n),
                      "a_won": rng.random(n) < 0.5})

    def module(scale):
        def combine(Q):
            s = (Q["u_a"] + Q["u_b"]).to_numpy()
            return {"x": (Q["u_a"] - Q["u_b"]).to_numpy(), "controls": None, "control_names": [],
                    "eta_mod_controls": (s * scale)[:, None]}
        return types.SimpleNamespace(__name__="x.f98_t", HYPOTHESES=[
            {"hid": "T", "master": "T", "kind": "S", "sign": "+", "weight": 1.0, "trait": "none", "deployment": "none",
             "prepare": None, "combine": combine}])
    saved = B.modules
    try:
        B.modules = lambda pattern=B.FAMILY: [module(1.0)]
        h1 = B.table_hash(pd.DataFrame(B.build_all(P, None)[0]))
        B.modules = lambda pattern=B.FAMILY: [module(2.0)]
        h2 = B.table_hash(pd.DataFrame(B.build_all(P, None)[0]))
    finally:
        B.modules = saved
    assert h1 != h2
