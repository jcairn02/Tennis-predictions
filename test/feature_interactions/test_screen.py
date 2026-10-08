"""Tests of the shared EDA screen (src/eda/feature_interactions/screen.py) on synthetic data: the fit, the clustered
variances against brute force, the weighted multiplicity procedures, invariance to the random choice of side A, and
that a planted coefficient is found while noise is not."""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import screen as S  # noqa: E402


def synthetic(n_per_season: int = 1200, beta: float = 0.0, seed: int = 0) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    seasons = np.repeat(np.arange(2014, 2025), n_per_season)
    n = len(seasons)
    eta = rng.normal(0, 1.0, n)
    x = rng.normal(0, 1.0, n)
    y = rng.random(n) < expit(0.95 * eta + beta * x)
    dates = pd.to_datetime([f"{s}-01-06" for s in seasons]) + pd.to_timedelta(rng.integers(0, 330, n), unit="D")
    pa = rng.integers(0, 400, n)
    pb = (pa + 1 + rng.integers(0, 398, n)) % 400
    f = pd.DataFrame({"match_id": np.arange(n).astype(str), "tour": np.where(rng.random(n) < 0.5, "atp", "wta"),
                      "season": seasons, "tournament_date": dates, "a_won": y, "in_surface": rng.integers(0, 3, n),
                      "z_model": eta, "z_market": eta, "player_a_id": pa.astype(str), "player_b_id": pb.astype(str)})
    f["window"] = np.where(f["season"] <= 2021, "discovery", "replication")
    f["block"] = S.T.blocks(f["tournament_date"].to_numpy(), 28)
    return f, x


def test_fit_first_order_condition():
    rng = np.random.default_rng(1)
    Z = rng.normal(size=(4000, 3))
    y = (rng.random(4000) < expit(Z @ np.array([0.8, -0.5, 0.2]))).astype(float)
    b, p, _ = S.fit(Z, y)
    assert np.abs(Z.T @ (y - p)).max() < 1e-5


def test_clustered_variances_match_brute_force():
    rng = np.random.default_rng(2)
    n = 60
    u = rng.normal(size=n)
    block = rng.integers(0, 5, n)
    pa = rng.integers(0, 8, n).astype(str)
    pb = np.array([str((int(a) + 1 + rng.integers(0, 6)) % 8) for a in pa])
    v = S.clustered_variances(u, block, pa, pb)
    shares = lambda i, j: len({pa[i], pb[i]} & {pa[j], pb[j]}) > 0   # noqa: E731
    vb = vp = vu = 0.0
    for i, j in product(range(n), range(n)):
        sb, sp = block[i] == block[j], shares(i, j)
        vb += u[i] * u[j] * sb
        vp += u[i] * u[j] * sp
        vu += u[i] * u[j] * (sb or sp)
    G = len(np.unique(block))
    k = G / (G - 1)
    assert np.isclose(v["block"], k * vb) and np.isclose(v["player"], k * vp) and np.isclose(v["union"], k * vu)


def test_weighted_multiplicity_reduce_to_unweighted():
    p = np.array([0.01, 0.04, 0.03, 0.5])
    w = np.ones(4)
    assert np.allclose(S.weighted_holm(p, w), [0.04, 0.09, 0.09, 0.5])
    assert np.allclose(S.weighted_bh(p, w), [0.04, 0.04 * 4 / 3, 0.04 * 4 / 3, 0.5])
    # a doubled weight halves that hypothesis's effective p-value
    w2 = np.array([2.0, 1.0, 1.0, 1.0])
    assert S.weighted_holm(p, w2)[0] < S.weighted_holm(p, w)[0]


def test_planted_coefficient_found_noise_not():
    # beta 0.12 on 13,200 matches: expected z about 6 (SE about 0.02); the estimator's spread is about +-1 in z
    f, x = synthetic(beta=0.12, seed=3)
    r = S.run(f, S.Hypothesis("planted", x), n_p1=0, sizes=False)
    assert r["z_joint"] > 3.0 and r["filter_pass"], r
    f0, x0 = synthetic(beta=0.0, seed=4)
    r0 = S.run(f0, S.Hypothesis("noise", x0), n_p1=0, sizes=False)
    assert abs(r0["z_joint"]) < 3.0


def test_invariant_to_side_a():
    """Swapping A and B in every match (negate eta and x, flip the result, swap players) leaves z unchanged."""
    f, x = synthetic(beta=0.05, seed=5)
    g = f.copy()
    g["z_model"] = -f["z_model"]
    g["a_won"] = ~f["a_won"].to_numpy(bool)
    g["player_a_id"], g["player_b_id"] = f["player_b_id"], f["player_a_id"]
    a = S.run(f, S.Hypothesis("x", x), n_p1=0, sizes=False)
    b = S.run(g, S.Hypothesis("x", -x), n_p1=0, sizes=False)
    assert abs(a["z_joint"] - b["z_joint"]) < 1e-8 and abs(a["b1"] - b["b1"]) < 1e-8


def test_wald_matches_single_coefficient_and_finds_planted_block():
    f, x = synthetic(beta=0.05, seed=6)
    h = S.Hypothesis("x", x)
    xs, Cs, prep = S.prepare(f, h, "model")
    disc = (f["window"] == "discovery").to_numpy()
    one = S.coef_test(f, disc, xs, Cs, "model", prep)
    multi = S.coef_test_multi(f, disc, xs[:, None], Cs, "model", prep)
    assert abs(multi["W"] - one["z"] ** 2) < 1e-6 * max(1.0, one["z"] ** 2)
    rng = np.random.default_rng(8)
    x2 = rng.normal(size=len(f))
    f2 = f.copy()
    f2["a_won"] = rng.random(len(f)) < S.expit(0.95 * f["z_model"] + 0.10 * x - 0.10 * x2)
    r = S.run_wald(f2, "blk", np.column_stack([x, x2]), None, n_p1=0)
    assert r["p_joint"] < 1e-4 and r["filter_pass"] and r["replicates"], r
    f3 = f.copy()
    f3["a_won"] = rng.random(len(f)) < S.expit(0.95 * f["z_model"])
    r0 = S.run_wald(f3, "null", np.column_stack([x, x2]), None, n_p1=0)
    assert r0["p_joint"] > 0.001, r0


def test_encompassing_recovers_informative_deviation():
    from src.eda.feature_interactions import tabpfn_tests as TT
    rng = np.random.default_rng(11)
    n = 30000
    seasons = rng.integers(2016, 2025, n)
    f = pd.DataFrame({"tour": np.where(rng.random(n) < 0.5, "atp", "wta"), "season": seasons,
                      "tournament_date": pd.to_datetime([f"{s}-01-06" for s in seasons]) +
                      pd.to_timedelta(rng.integers(0, 330, n), unit="D"),
                      "player_a_id": rng.integers(0, 500, n).astype(str)})
    f["player_b_id"] = ((f["player_a_id"].astype(int) + 1 + rng.integers(0, 498, n)) % 500).astype(str)
    f["block"] = S.T.blocks(f["tournament_date"].to_numpy(), 28)
    eta = rng.normal(0, 1, n)
    dev = rng.normal(0, 0.08, n)
    f["a_won"] = rng.random(n) < S.expit(eta + dev)
    r = TT.encompassing(f, eta, dev)
    assert 0.5 < r["b"] < 1.5 and r["p_one_sided"] < 0.01, r
    r0 = TT.encompassing(f, eta, rng.normal(0, 0.08, n))
    assert abs(r0["t"]) < 3.5, r0


def test_effect_sizes_with_a_season_missing_one_tour():
    """Verifier B1: the men's 2018 season has no odds, so a held-out season can lack a tour."""
    f, x = synthetic(beta=0.05, seed=12)
    drop = (f["season"] == 2018) & (f["tour"] == "atp")
    f = f[~drop].reset_index(drop=True)
    x = x[~drop.to_numpy()]
    r = S.run(f, S.Hypothesis("x", x), n_p1=0, sizes=True)
    assert np.isfinite(r["gain_disc_both"]) and np.isfinite(r["gain_repl_both"])
