"""B1 finishing-form carry-over: the iid replayer against the reference scoring rules (replay.py), the binomial GLM with
offset and its clustered covariance, the difference-in-differences contrast and the label swap, on synthetic data.

Run: ./python.sh -m pytest test/point_sequence/test_carry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import carry_fit as F  # noqa: E402
from src.eda.point_sequence import carry_sim as S  # noqa: E402
from src.eda.point_sequence import replay as R  # noqa: E402

RULES = [(3, "tb"), (3, "tb10"), (3, "adv"), (3, "tb12"), (3, "mtb10"), (5, "tb"), (5, "tb10"), (5, "adv"),
         (5, "tb12")]


# ------------------------------------------------------------------------------------------------
# Simulator against replay.py

@pytest.mark.parametrize("bo,final", RULES)
@pytest.mark.parametrize("level", ["even", "strong_servers"])
def test_simulator_matches_reference_rules(bo, final, level):
    rng = np.random.default_rng(bo * 100 + len(final) + (7 if level == "even" else 11))
    K = 120
    if level == "even":
        pa, pb = rng.uniform(0.45, 0.75, K), rng.uniform(0.45, 0.75, K)
    else:   # many tie-breaks and long advantage sets
        pa, pb = rng.uniform(0.85, 0.95, K), rng.uniform(0.85, 0.95, K)
    s0 = rng.integers(1, 3, K)
    sim = S.simulate(pa, pb, np.full(K, bo), np.full(K, S.FINAL_CODE[final]), s0, rng, record=True)
    for i in range(K):
        w = sim["point_winners"][i]
        srv = np.asarray(sim["point_servers"][i])
        rp = R.replay(w, R.Rules(bo, final))
        assert rp.status == "complete", (i, rp.status)
        assert rp.winner == sim["winner"][i]
        assert len(rp.sets) == sim["sets"][i]
        expect = R.rule_servers(rp.game_idx, rp.pt_no, rp.is_tb, int(s0[i]))
        assert np.array_equal(expect, srv)
        for s in range(1, len(rp.sets) + 1):
            m = rp.set_no == s
            for side in (1, 2):
                n = int(((srv == side) & m).sum())
                won = int(((srv == side) & m & (np.asarray(w) == side)).sum())
                assert sim["served"][i, s - 1, side - 1] == n
                assert sim["won"][i, s - 1, side - 1] == won


def test_simulator_point_rates_are_the_day_rates():
    rng = np.random.default_rng(5)
    K = 4000
    sim = S.simulate(np.full(K, 0.66), np.full(K, 0.58), np.full(K, 3), np.zeros(K, int), rng.integers(1, 3, K), rng)
    a = sim["won"][:, :, 0].sum() / sim["served"][:, :, 0].sum()
    b = sim["won"][:, :, 1].sum() / sim["served"][:, :, 1].sum()
    assert abs(a - 0.66) < 0.005 and abs(b - 0.58) < 0.005


def test_replay_triples_conditions_on_the_winner_and_takes_the_late_set():
    rng = np.random.default_rng(3)
    K = 300
    bo = rng.choice([3, 5], K)
    tri = pd.DataFrame({
        "side_t": rng.integers(1, 3, K), "n_tot": 80, "w_tot": rng.integers(44, 60, K), "on_tot": 80,
        "ow_tot": rng.integers(44, 60, K), "tour": "atp", "surface": "Hard", "bo": bo,
        "final": np.where(bo == 5, "adv", "tb"), "s0": rng.integers(1, 3, K), "winner_t": rng.integers(1, 3, K)})
    prior = pd.DataFrame([{"tour": "atp", "surface": "Hard", "mu": 0.63, "true_var": 0.003},
                          {"tour": "atp", "surface": "_tour", "mu": 0.62, "true_var": 0.003}])
    rep, info = S.replay_triples(tri, prior, seed=1)
    assert info["never_matched"] == 0
    assert (rep["n1"] > 0).all() and (rep["nL"] > 0).all() and (rep["on1"] > 0).all() and (rep["onL"] > 0).all()
    # the player-centred variant needs the pre-match expectations
    tri["ps_t"], tri["pso_t"] = 0.64, 0.62
    dev = pd.DataFrame([{"tour": "atp", "true_var": 0.0009}])
    rep2, info2 = S.replay_triples(tri, prior, seed=2, mode="player", dev_prior=dev)
    assert info2["never_matched"] == 0 and (rep2["nL"] > 0).all()


def test_replay_late_set_is_set_three_in_best_of_five():
    # strong servers: best-of-five matches reach set 3 always; its counts must be what the simulator put in set 3
    rng = np.random.default_rng(8)
    K = 50
    sim = S.simulate(np.full(K, 0.7), np.full(K, 0.7), np.full(K, 5), np.zeros(K, int), np.ones(K, int), rng)
    assert (sim["served"][:, 2, :].sum(axis=1) > 0).all()
    assert (sim["sets"] >= 3).all()


# ------------------------------------------------------------------------------------------------
# Binomial GLM and clustered covariance

def test_glm_recovers_coefficients_and_sandwich_matches_model_variance():
    rng = np.random.default_rng(11)
    N = 40000
    X = np.column_stack([np.ones(N), rng.normal(size=N), rng.normal(size=N)])
    off = logit(rng.uniform(0.5, 0.7, N))
    beta = np.array([0.05, 0.10, -0.04])
    n = rng.integers(40, 120, N).astype(float)
    y = rng.binomial(n.astype(int), expit(off + X @ beta)).astype(float)
    b, H, mu = F.fit_binomial(y, n, off, X)
    assert np.allclose(b, beta, atol=0.01)
    assert np.allclose(X.T @ (y - n * mu), 0, atol=1e-6)
    V = F.cluster_cov(y, n, X, mu, H, np.arange(N))
    ratio = np.diag(V) / np.diag(np.linalg.inv(H))
    assert np.all(np.abs(ratio - 1) < 0.08)


def synthetic_triples(T: int, carry: float, seed: int) -> pd.DataFrame:
    """Triples where each player's form theta drives every match; the forward endpoint also gets carry * (L - E)."""
    rng = np.random.default_rng(seed)
    players = rng.integers(0, T // 8, T)
    theta = rng.normal(0, 0.15, T)
    rE = theta * 0.2 + rng.normal(0, 0.09, T)
    rL = theta * 0.2 + rng.normal(0, 0.09, T)
    n_m, n_p = rng.integers(50, 100, T), rng.integers(50, 100, T)
    ps_m, ps_p = rng.uniform(0.55, 0.7, T), rng.uniform(0.55, 0.7, T)
    eta_m = logit(ps_m) + theta
    eta_p = logit(ps_p) + theta + carry * F.SCALE * (rL - rE)
    return pd.DataFrame({
        "player_id": players.astype(str), "tour": np.where(rng.random(T) < 0.6, "atp", "wta"), "rE": rE, "rL": rL,
        "sv_n_m": n_m, "sv_w_m": rng.binomial(n_m, expit(eta_m)), "sv_n_p": n_p,
        "sv_w_p": rng.binomial(n_p, expit(eta_p)), "ps_m": ps_m, "ps_p": ps_p,
        "form_m": rng.normal(0, 0.02, T), "form_p_lit": rng.normal(0, 0.02, T),
        "gap_fwd": rng.choice([1.0, 2.0, 3.0], T), "gap_rev": rng.choice([1.0, 2.0, 3.0], T)})


def test_delta_detects_planted_forward_carry_and_is_null_without_it():
    # planting carry * (L - E) on the forward endpoint gives b_L = +carry and b_E = -carry forward: Delta = 2 carry
    planted = F.estimate(F.design(synthetic_triples(30000, 0.05, 1)), F.standard_contrasts())["contrasts"]
    assert planted["delta"]["lo"] > 0
    assert abs(planted["delta"]["est"] - 0.10) < 3 * planted["delta"]["se"]
    null = F.estimate(F.design(synthetic_triples(30000, 0.0, 2)), F.standard_contrasts())["contrasts"]
    assert abs(null["delta"]["est"]) < 3.5 * null["delta"]["se"]


def test_swapping_every_label_flips_delta_exactly():
    tri = synthetic_triples(5000, 0.03, 3)
    d0 = F.estimate(F.design(tri))["contrasts"]["delta"]["est"]
    sw = tri.copy()
    sw["rE"], sw["rL"] = tri["rL"], tri["rE"]
    d1 = F.estimate(F.design(sw))["contrasts"]["delta"]["est"]
    assert abs(d0 + d1) < 1e-8


def test_bootstrap_interval_is_close_to_the_sandwich():
    tri = synthetic_triples(8000, 0.0, 4)
    D = F.design(tri)
    res = F.estimate(D)
    bs = F.bootstrap_delta(D, res["beta"], 200, seed=9)
    assert 0.75 < bs.std(ddof=1) / res["contrasts"]["delta"]["se"] < 1.3
