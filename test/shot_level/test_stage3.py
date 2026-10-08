"""Stage 3 of the shot-level study: the point-level binomial fit, the server rows' orientation, the flexible learners'
symmetry, and the planted-signal test's arithmetic.

Run: ./python.sh -m pytest test/shot_level/test_stage3.py
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

from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.shot_level import stage3_flexible as X  # noqa: E402
from src.eda.shot_level import stage3_planted as P  # noqa: E402
from src.eda.shot_level import stage3_points as Q  # noqa: E402
from src.eda.shot_level import stage3_profiles as W  # noqa: E402


def test_fit_binomial_equals_bernoulli_fit():
    """A binomial regression on counts is the logistic regression on the expanded 0/1 points."""
    rng = np.random.default_rng(11)
    n = 300
    Z = np.column_stack([np.ones(n), rng.normal(size=n), rng.normal(size=n)])
    d = rng.integers(20, 120, n).astype(float)
    x = rng.binomial(d.astype(int), expit(Z @ np.array([0.5, 0.3, -0.2]))).astype(float)
    b = Q.fit_binomial(Z, x, d)
    rep = d.astype(int)
    Ze = np.repeat(Z, rep, axis=0)
    ye = np.concatenate([np.r_[np.ones(int(k)), np.zeros(int(m - k))] for k, m in zip(x, d)]).astype(bool)
    be = R.newton(Ze[None], ye, np.zeros((1, 3)))[0]
    assert b == pytest.approx(be, abs=1e-6)


def test_clustered_ratio_estimate():
    """Per-point gain is the ratio of sums; a gain proportional to the points has no spread across clusters."""
    units = np.array([10.0, 30.0, 60.0, 100.0])
    mean, lo, hi = Q.clustered(0.002 * units, units, np.array([0, 0, 1, 2]))
    assert (mean, lo, hi) == pytest.approx((2.0, 2.0, 2.0))
    mean, lo, hi = Q.clustered(np.array([1.0, 0.0, 0.0, 1.0]), units, np.array([0, 1, 2, 3]))
    assert mean == pytest.approx(1000 * 2 / 200) and lo < mean < hi


def server_frame() -> pd.DataFrame:
    cols = {"match_id": ["m1"], "tour": ["atp"], "year": [2020], "evaluation": [True],
            "tournament_date": [pd.Timestamp("2020-01-06")], "A_spw_n": [50], "A_spw_d": [80], "B_spw_n": [40],
            "B_spw_d": [70], "p_serve_a": [0.66], "p_serve_b": [0.61]}
    names = {n for _, n in Q.BOX + Q.SHOT}
    for n in names:
        cols[f"A|{n}"] = [1.0]
        cols[f"B|{n}"] = [-1.0]
    return pd.DataFrame(cols)


def test_server_rows_orientation():
    """Server A: A's counts and serve forecast, A's serve-side and B's return-side values; server B the reverse."""
    rows = Q.server_rows(server_frame()).set_index("server")
    assert (rows.loc["A", "x"], rows.loc["A", "d"], rows.loc["A", "base"]) == (50, 80, 0.66)
    assert (rows.loc["B", "x"], rows.loc["B", "d"], rows.loc["B", "base"]) == (40, 70, 0.61)
    assert rows.loc["A", "srv|spw|box|w52"] == 1.0 and rows.loc["A", "ret|rpw|box|w52"] == -1.0
    assert rows.loc["B", "srv|spw|box|w52"] == -1.0 and rows.loc["B", "ret|rpw|box|w52"] == 1.0
    assert rows.loc["A", "srv|srv_quick|off|w52"] == 1.0 and rows.loc["A", "ret|ret_quick|off|w52"] == -1.0


def flex_frame(n: int = 400, seed: int = 5) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    cols = {"shot": ["s1|off|w52", "s2|off|w52"], "box_sides": ["spw|box|w52"], "profile": ["prof1"]}
    f = pd.DataFrame({"p_mkt": rng.uniform(0.1, 0.9, n), "prof1": rng.normal(size=n)})
    for c in cols["shot"] + cols["box_sides"]:
        f[f"A|{c}"] = rng.normal(size=n)
        f[f"B|{c}"] = rng.normal(size=n)
    return f, cols


def test_matrices_flip():
    """Flipped: the odds and the differences change sign, the side columns swap."""
    f, cols = flex_frame(5)
    for kind in ("shot", "box+shot", "shot_diff", "box+shot_diff"):
        a, b = X.matrices(f, cols, kind), X.matrices(f, cols, kind, flip=True)
        assert a.shape == b.shape
        assert b[:, 0] == pytest.approx(-a[:, 0])
    a, b = X.matrices(f, cols, "shot"), X.matrices(f, cols, "shot", flip=True)
    assert b[:, 1] == pytest.approx(a[:, 2]) and b[:, 2] == pytest.approx(a[:, 1])
    a, b = X.matrices(f, cols, "shot_diff"), X.matrices(f, cols, "shot_diff", flip=True)
    assert b[:, 1:] == pytest.approx(-a[:, 1:])


def test_fit_predict_is_symmetric():
    """The averaged forecast for a match seen from B's side is one minus the forecast from A's side."""
    f, cols = flex_frame()
    rng = np.random.default_rng(6)
    y = rng.random(len(f)) < f["p_mkt"].to_numpy()
    tr, te = np.arange(len(f)) < 300, np.arange(len(f)) >= 300
    Xtr = np.vstack([X.matrices(f[tr], cols, "shot_diff"), X.matrices(f[tr], cols, "shot_diff", True)])
    ytr = np.concatenate([y[tr], ~y[tr]])
    Xte, Xte_f = X.matrices(f[te], cols, "shot_diff"), X.matrices(f[te], cols, "shot_diff", True)
    p, _ = X.fit_predict("ridge", Xtr, ytr, Xte, y[te], Xtr, ytr, Xte, Xte_f)
    q, _ = X.fit_predict("ridge", Xtr, ytr, Xte, y[te], Xtr, ytr, Xte_f, Xte)
    assert p + q == pytest.approx(np.ones(te.sum()), abs=1e-12)


def test_planted_beta_gives_the_planted_gain():
    """beta = sqrt(2 G / v): the expected log-loss gain of the true model over the odds is G (to second order)."""
    rng = np.random.default_rng(7)
    lb = rng.normal(0, 1.2, 200_000)
    z = rng.normal(size=lb.size)
    z = (z - z.mean()) / z.std()
    p = expit(lb)
    v = (p * (1 - p)).mean()
    for G in (0.25, 1.0, 2.0):
        beta = np.sqrt(2 * G / 1000 / v)
        pt = expit(lb + beta * z)
        kl = pt * np.log(pt / p) + (1 - pt) * np.log((1 - pt) / (1 - p))
        assert 1000 * kl.mean() == pytest.approx(G, rel=0.03)


def test_residual_and_partial_corr():
    rng = np.random.default_rng(8)
    n = 100_000
    lb = rng.normal(size=n)
    e = rng.normal(size=n)
    truth = 0.6 * lb + e
    r = P.residual(truth, lb)
    assert abs(r @ lb) < 1e-6 * n
    x = e + rng.normal(0, 1.0, n) + 2.0 * lb           # what the odds already price does not count
    assert P.partial_corr(x[:, None], truth, lb) == pytest.approx(1 / np.sqrt(2), abs=0.01)


def test_truths_shrinkage_and_seasons():
    """Career: (n + K mu) / (d + K) on the log-odds scale, mu the tour's pooled rate; season: per (player, year)."""
    st = pd.DataFrame({"player_id": ["p", "p", "q", "w"], "tour": ["atp", "atp", "atp", "wta"],
                       "year": [2020, 2021, 2020, 2020], "winner_rate_n": [10.0, 50.0, 20.0, 5.0],
                       "winner_rate_d": [100.0, 100.0, 100.0, 50.0]})
    K = {"winner_rate|atp|off": 50.0, "winner_rate|wta|off": 50.0}
    car, sea = P.truths("winner_rate", K, st)
    mu = 80 / 300
    assert car["p"] == pytest.approx(logit((60 + 50 * mu) / (200 + 50)))
    assert car["q"] == pytest.approx(logit((20 + 50 * mu) / (100 + 50)))
    assert sea[("p", 2021)] == pytest.approx(logit((50 + 50 * mu) / (100 + 50)))
    assert sea[("p", 2020)] == pytest.approx(logit((10 + 50 * mu) / (100 + 50)))
    assert car["w"] == pytest.approx(logit(0.1))        # one player: shrunk to their own rate


def test_ridge_newton_without_penalty_is_the_harness_fit():
    rng = np.random.default_rng(9)
    Z = np.column_stack([rng.normal(size=3000), rng.normal(size=3000), rng.normal(size=3000)])
    y = rng.random(3000) < expit(Z @ np.array([1.0, 0.3, 0.0]))
    b = W.ridge_newton(Z, y, np.zeros(3), np.zeros(3))
    assert b == pytest.approx(R.newton(Z[None], y, np.zeros((1, 3)))[0], abs=1e-8)
    shrunk = W.ridge_newton(Z, y, np.array([0.0, 1e5, 1e5]), np.zeros(3))
    assert abs(shrunk[1]) < 0.05 * abs(b[1]) and shrunk[0] == pytest.approx(b[0], abs=0.1)


def walk_data(n_per: int = 1500, signal: float = 0.0, seed: int = 10):
    rng = np.random.default_rng(seed)
    year = np.repeat(np.arange(2011, 2021), n_per)
    lb = rng.normal(0, 1, year.size)
    Xs = rng.normal(size=(year.size, 8))
    y = rng.random(year.size) < expit(lb + signal * Xs[:, 0])
    return Xs, lb, y, year


def test_ridge_walk_noise_inputs_cost_less():
    """Eight pure-noise inputs, five data sets: the harness's unpenalised fit pays for them; the ridge walk mostly picks
    a strong penalty and pays less."""
    seasons = list(range(2012, 2021))
    ridge, harness, chosen = [], [], []
    for seed in range(10, 15):
        Xs, lb, y, year = walk_data(n_per=3000, seed=seed)
        w = W.ridge_walk(Xs, lb, y, year, seasons)
        ridge.append(np.nanmean(w["llb"] - w["llm"]))
        chosen += list(w["chosen"].values())
        h = R.walk(np.ascontiguousarray(np.column_stack([lb, Xs])[None]), y, year, seasons, lb)
        harness.append(np.nanmean(h["llb"] - h["llm"][0]))
    assert np.mean(harness) < np.mean(ridge) and np.mean(harness) < -0.0002
    assert np.median(chosen) >= 1000


def test_ridge_walk_finds_a_real_signal():
    Xs, lb, y, year = walk_data(signal=0.3)
    w = W.ridge_walk(Xs, lb, y, year, list(range(2012, 2021)))
    assert np.nanmean(w["llb"] - w["llm"]) > 0.004          # the planted gain is about 0.009 nats
    assert np.median(list(w["chosen"].values())) <= 300


def test_ridge_walk_uses_no_result_of_the_season_it_forecasts():
    """Changing the results of the last season leaves its forecasts unchanged."""
    Xs, lb, y, year = walk_data(signal=0.2)
    seasons = list(range(2012, 2021))
    a = W.ridge_walk(Xs, lb, y, year, seasons)
    y2 = y.copy()
    last = year == 2020
    y2[last] = ~y2[last]
    b = W.ridge_walk(Xs, lb, y2, year, seasons)
    assert a["p"][last] == pytest.approx(b["p"][last], abs=1e-12)
    assert a["chosen"] == b["chosen"]
