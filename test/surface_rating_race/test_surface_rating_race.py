"""Tests of the surface-rating race (src/eda/surface_rating_race/).

Run: ./python.sh -m pytest test/surface_rating_race -q
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.rating_systems import ratings as R  # noqa: E402
from src.eda.surface_rating_race import ttt_offset as TO  # noqa: E402


def synthetic(seed: int = 0, players: int = 60, weeks: int = 70) -> dict:
    """Two 16-player knock-outs a week, results drawn from hidden skills (a clay bonus for some players), every day an
    integer; es = the round's day, lf a day or two later; a few walkovers (no update) and unknown surfaces."""
    rng = np.random.default_rng(seed)
    skill = rng.normal(0.0, 1.0, players)
    clay = rng.normal(0.0, 0.5, players)
    rows = []
    for wk in range(weeks):
        day = 15000 + 7 * wk
        for ev in range(2):
            field = list(rng.choice(players, 16, replace=False))
            surf = int(rng.choice([-1, 0, 1, 2]))
            for rnd in range(4):
                nxt = []
                for k in range(0, len(field), 2):
                    a, b = int(field[k]), int(field[k + 1])
                    d = skill[a] - skill[b] + ((clay[a] - clay[b]) if surf == 1 else 0.0)
                    won = bool(rng.random() < 1.0 / (1.0 + math.exp(-d)))
                    es = day + 2 * rnd
                    rows.append({"es": es, "lf": es + int(rng.integers(0, 3)), "event": 2 * wk + ev, "rnd": rnd,
                                 "a": a, "b": b, "a_won": won, "surf": surf, "upd": bool(rng.random() > 0.05)})
                    nxt.append(a if won else b)
                field = nxt
    t = pd.DataFrame(rows)
    return {c: t[c].tolist() for c in t.columns} | {"n": players}


def run_offset(h: dict, **kw) -> np.ndarray:
    return TO.ttt_offset_pass_timed(h["es"], h["lf"], h["event"], h["rnd"], h["a"], h["b"], h["surf"], h["a_won"],
                                    h["upd"], h["n"], **kw)


def test_without_offsets_it_is_the_decided_ttt_exactly():
    h = synthetic()
    kw = {"sigma0": 1.3, "gamma": 0.45, "window_days": 90.0}
    ref = R.ttt_pass_timed(h["es"], h["lf"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], [True] * len(h["es"]),
                           h["upd"], h["n"], **kw)
    got = run_offset(h, offsets=False, **kw)
    # ratings.OUT_COLS: mu_a, mu_b, u_a, u_b, vol_a, vol_b, n_a, n_b
    assert np.array_equal(ref[:, [0, 1, 2, 3, 6, 7]], got[:, [0, 1, 2, 3, 8, 9]])
    assert np.isnan(got[:, 4:8]).all() and np.isnan(got[:, 10:]).all()


def test_team_update_matches_the_truncated_gaussian_moments():
    """One 2-v-2 game: each node's posterior equals the exact mean and variance of its skill given the result
    (Monte Carlo, 4 million draws)."""
    m = TO.TTTOffset(n_overall=2, n_keys=4, sigma0=1.2, gamma=0.0, sigma_o=0.4, gamma_o=0.0)
    m.add_batch(0.0, [((0, 2), (1, 3))], batch_iters=1)          # A = keys 0 (overall) + 2 (offset) beat B = 1 + 3
    rng = np.random.default_rng(1)
    n = 4_000_000
    x = np.column_stack([rng.normal(0, 1.2, n), rng.normal(0, 1.2, n), rng.normal(0, 0.4, n), rng.normal(0, 0.4, n)])
    win = (x[:, 0] + x[:, 2] + rng.normal(0, 1, n)) > (x[:, 1] + x[:, 3] + rng.normal(0, 1, n))
    for k in range(4):
        mu, s2 = m.posterior(m.last[k])
        assert mu == pytest.approx(x[win, k].mean(), abs=4e-3)
        assert s2 == pytest.approx(x[win, k].var(), abs=4e-3)


def test_offsets_move_only_on_their_surface():
    h = synthetic(seed=3)
    out = TO.frame_of(run_offset(h, sigma0=1.2, gamma=0.4, sigma_o=0.4, gamma_o=0.05, window_days=60.0))
    surf = np.array(h["surf"])
    assert out.loc[surf < 0, ["off_a", "off_b", "so2_a", "so2_b", "ns_a", "ns_b"]].isna().all().all()
    assert out.loc[surf >= 0, ["off_a", "off_b", "so2_a", "so2_b"]].notna().all().all()
    # a player's offset on a surface is the prior until their first match on it
    first = pd.DataFrame({"p": h["a"], "s": surf, "ns": out["ns_a"], "off": out["off_a"], "q": out["so2_a"]})
    new = first[(first["s"] >= 0) & (first["ns"] == 0)]
    assert (new["off"] == 0.0).all() and np.allclose(new["q"], 0.4 ** 2)


def test_no_leak_from_results_after_a_cut():
    """Reversing every result that surely started after day D moves nothing of a match that surely finished by D."""
    h = synthetic(seed=5)
    kw = {"sigma0": 1.2, "gamma": 0.4, "sigma_o": 0.4, "gamma_o": 0.05, "window_days": 200.0}
    base = run_offset(h, **kw)
    es, lf = np.array(h["es"]), np.array(h["lf"])
    for D in (15000 + 7 * 20 + 3, 15000 + 7 * 41 + 5):
        g = dict(h)
        g["a_won"] = [(not w) if e > D else w for w, e in zip(h["a_won"], h["es"])]
        got = run_offset(g, **kw)
        early = lf <= D
        assert early.sum() > 100 and (es > D).sum() > 100
        assert np.array_equal(base[early], got[early], equal_nan=True)
        assert not np.array_equal(base[~early], got[~early], equal_nan=True)


def test_arms_change_only_the_rating():
    from src.eda.surface_rating_race import arms as A
    base = set(A.BASE)
    assert set(A.ARMS["ttt_blend"]) == base - {"elo_logit"} | {"ttt_logit"}
    assert set(A.ARMS["ttt_off"]) - set(A.ARMS["elo_off"]) == {"ttt_overall", "ttt_surf_offset"}
    assert set(A.ARMS["elo_off"]) - set(A.ARMS["ttt_off"]) == {"elo_overall", "elo_surf_offset"}
    assert set(A.ARMS["both_off"]) == set(A.ARMS["elo_off"]) | set(A.ARMS["ttt_off"])
    for arm in ("base", "elo_off", "ttt_blend", "ttt_off", "both_off"):
        assert "odds_logit" in A.ARMS[arm] and set(A.ARMS[f"{arm}_noodds"]) == set(A.ARMS[arm]) - {"odds_logit"}
    assert A.NEEDS_OFFSET_TTT == {"ttt_off", "ttt_off_noodds", "both_off", "both_off_noodds"}


def test_flip_negates_ttt_inputs_and_is_an_involution():
    from src.eda.surface_rating_race import arms as A
    rng = np.random.default_rng(0)
    cols = A.ARMS["both_off"] + ["ttt_logit"]
    X = pd.DataFrame(rng.normal(size=(20, len(cols))), columns=cols)
    Y = A.flip(X)
    for c in ("ttt_logit", "ttt_overall", "ttt_surf_offset", "elo_overall", "odds_logit"):
        assert np.allclose(Y[c], -X[c])
    assert np.allclose(Y["surf_season_a"], X["surf_season_b"]) and np.allclose(Y["surf_layoff_b"], X["surf_layoff_a"])
    assert np.allclose(Y["surface"], X["surface"])
    assert np.allclose(A.flip(Y).to_numpy(), X.to_numpy())


def test_model_arm_is_the_surface_profile_with_the_elo_swap():
    from src.eda.surface_rating_race import arms as A
    assert len(A.SPROF) == 21 and all(n in A.BASE for n in A.SPROF)
    assert len(A.ARMS["sprof"]) == 54 and len(A.ARMS["model"]) == 58
    assert [c for c in A.ARMS["sprof"] if c.startswith("sf_")] == [f"sf_{n}" for n in A.BASE if n in A.SPROF]
    assert set(A.ARMS["model"]) - set(A.ARMS["sprof"]) == {"elo_overall", "elo_surf_offset", "surf_season_a",
                                                           "surf_season_b", "surf_layoff_a", "surf_layoff_b"}
    assert set(A.ARMS["sprof"]) - set(A.ARMS["model"]) == {"elo_logit", "surface_first"}
    assert all(f"sf_{n}" in A.ANTISYMMETRIC for n in A.SPROF)
    assert A.NEEDS_SPROF == {"sprof", "model", "sprof_noodds", "model_noodds"}


def test_z_parts_add_up():
    h = synthetic(seed=7)
    o = TO.frame_of(run_offset(h, sigma0=1.2, gamma=0.4, sigma_o=0.4, gamma_o=0.0, window_days=60.0))
    z, z_over, z_off = TO.z_parts(o)
    assert np.allclose(z, z_over + z_off)
    known = np.array(h["surf"]) >= 0
    assert (z_off[~known] == 0).all()
    assert np.all((TO.p_offset(o) > 0) & (TO.p_offset(o) < 1))
