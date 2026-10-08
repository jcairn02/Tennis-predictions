"""Tests for the surface-IOS solver (src/eda/surface_ios/ios_surface.py).

Run: ./python.sh -m pytest test/surface_ios -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import ios_surface as IS  # noqa: E402
from src.eda.match_timing import ios_time as IT  # noqa: E402

STAT = "spw"
TYP = 70.0


def synthetic(n_players=40, n_matches=1500, seed=0, surface_effect=0.0):
    """A small history: random pairings over 600 days, three surfaces, a serve statistic drawn from
    expit(O + E_s - D - F_s), each match on its own day (so earliest start = latest finish = the day)."""
    rng = np.random.default_rng(seed)
    O = rng.normal(0, 0.3, n_players)
    D = rng.normal(0, 0.3, n_players)
    E = rng.normal(0, surface_effect, (n_players, 4))
    F = rng.normal(0, surface_effect, (n_players, 4))
    a = rng.integers(0, n_players, n_matches)
    b = (a + rng.integers(1, n_players, n_matches)) % n_players
    day = np.sort(rng.integers(0, 600, n_matches))
    surf = rng.choice([1, 2, 3], n_matches, p=[0.5, 0.35, 0.15])
    pid = np.column_stack([a, b]).reshape(-1)
    opp = pid.reshape(-1, 2)[:, ::-1].reshape(-1)
    s2 = np.repeat(surf, 2)
    eta = O[pid] + E[pid, s2 - 1] - D[opp] - F[opp, s2 - 1]
    d = rng.integers(40, 90, 2 * n_matches).astype(float)
    x = rng.binomial(d.astype(int), 1 / (1 + np.exp(-(0.4 + eta)))).astype(float)
    y = np.log((x + 0.5) / (d - x + 0.5)) - 0.4
    ok = np.ones(2 * n_matches, dtype=bool)
    days2 = np.repeat(day, 2).astype(np.int64)
    td = {"pid": pid.astype(np.int64), "n_players": n_players, "day": days2,
          "ev": np.repeat(np.arange(n_matches), 2).astype(np.int64),
          "round_order": np.zeros(2 * n_matches, dtype=np.int64), "surf": s2.astype(np.int64),
          "es": days2.astype(float), "lf": days2.astype(float), "obs": days2.astype(float),
          "stats": {STAT: {"ok": ok, "x": x, "d": d, "y": y, "mu": np.full(2 * n_matches, 0.4), "typ": TYP}}}
    return td, {"O": O, "D": D, "E": E, "F": F}


def test_arrow_solve_matches_dense():
    rng = np.random.default_rng(1)
    m, S = 5, 4
    alpha = rng.uniform(5, 10, m)
    c = rng.uniform(0, 2, (m, S))
    d = c + rng.uniform(0.5, 3, (m, S))
    r0, r = rng.normal(size=m), rng.normal(size=(m, S))
    x0, x = IS.arrow_solve(alpha, c, d, r0, r)
    A = IS.Arrow(alpha, c.T, d.T)
    y0, y = A.solve(r0, r.T)
    for i in range(m):
        M = np.zeros((S + 1, S + 1))
        M[0, 0], M[0, 1:], M[1:, 0] = alpha[i], c[i], c[i]
        M[1:, 1:] = np.diag(d[i])
        sol = np.linalg.solve(M, np.r_[r0[i], r[i]])
        assert np.allclose(sol, np.r_[x0[i], x[i]])
        assert np.allclose(sol, np.r_[y0[i], y[:, i]])


def test_pooled_path_equals_ios_time():
    td, _ = synthetic()
    old = {k: td[k] for k in ("pid", "n_players", "day", "ev", "round_order")}
    old["stats"] = {STAT: {k: td["stats"][STAT][k] for k in ("ok", "y", "d")} | {"typ": TYP}}
    ref = IT.run_timed(old, STAT, 26.0, 3.0, 1, td["es"], td["lf"], td["obs"])
    new = IS.run(td, STAT, 26.0, 3.0, np.inf, 1, TYP)
    huge = IS.run(td, STAT, 26.0, 3.0, 1e10, 1, TYP)
    for a, b in ((new["O_eff"], ref["O"]), (new["D_eff"], ref["D"])):
        assert np.allclose(a, b, atol=1e-12, equal_nan=True)
    for a, b in ((huge["O_eff"], ref["O"]), (huge["D_eff"], ref["D"])):
        assert np.allclose(a, b, atol=1e-7, equal_nan=True)


def test_players_without_data_are_left_out_exactly():
    """Players who never appear in an observation have ratings of exactly 0, and leaving them out of the system
    changes nothing for the others (compared with ios_time, which keeps every player)."""
    td, _ = synthetic(seed=11)
    td["n_players"] = td["n_players"] + 25            # 25 player codes with no match
    old = {k: td[k] for k in ("pid", "n_players", "day", "ev", "round_order")}
    old["stats"] = {STAT: {k: td["stats"][STAT][k] for k in ("ok", "y", "d")} | {"typ": TYP}}
    ref = IT.run_timed(old, STAT, 52.0, 2.0, 1, td["es"], td["lf"], td["obs"])
    new = IS.run(td, STAT, 52.0, 2.0, np.inf, 1, TYP)
    assert new["solver"]["players"] == 40 and new["solver"]["players_in_history"] == 65
    assert np.allclose(new["O_eff"], ref["O"], atol=1e-12) and np.allclose(new["D_eff"], ref["D"], atol=1e-12)
    # a row-mask hole: half the observations missing leaves some players with no data at all
    td2 = {**td, "stats": {STAT: dict(td["stats"][STAT])}}
    ok = td2["stats"][STAT]["ok"].copy()
    ok[np.isin(td["pid"], np.arange(10))] = False
    ok[np.isin(td["pid"][np.arange(len(ok)) ^ 1], np.arange(10))] = False
    td2["stats"][STAT]["ok"] = ok
    s = IS.run(td2, STAT, 52.0, 2.0, 3.0, 1, TYP)
    gone = np.isin(td["pid"], np.arange(10))
    assert np.allclose(s["O_eff"][gone], 0) and np.allclose(s["E"][gone], 0)


def test_recovers_planted_surface_effects():
    td, truth = synthetic(n_matches=6000, surface_effect=0.25, seed=3)
    res = IS.run(td, STAT, np.inf, 1.0, 1.0, 1, TYP)
    last = {}
    for r in np.flatnonzero(td["surf"] == 2):          # each player's clay deviation at their last clay match
        last[td["pid"][r]] = res["E"][r]
    p = np.array(sorted(last))
    est = np.array([last[k] for k in p])
    assert np.corrcoef(est, truth["E"][p, 1])[0, 1] > 0.5
    # and the surface model forecasts the statistic better than the pooled one late in the history
    pooled = IS.run(td, STAT, np.inf, 1.0, np.inf, 1, TYP)
    late = td["day"] >= 300
    ll_s, _ = IS.row_logloss(td, STAT, res)
    ll_p, _ = IS.row_logloss(td, STAT, pooled)
    assert np.nansum(ll_s[late]) < np.nansum(ll_p[late])


def test_no_leak_from_results_released_later():
    """Changing every result released after a match's earliest start leaves that match's ratings unchanged."""
    td, _ = synthetic(n_matches=800, surface_effect=0.2, seed=5)
    td["lf"] = td["lf"] + 2                       # windows: results surely exist only two days after the day
    base = IS.run(td, STAT, 52.0, 2.0, 4.0, 1, TYP)
    cut = 300
    later = td["lf"] + 1 > cut                    # not yet released on the cut day
    pert = {**td, "stats": {STAT: dict(td["stats"][STAT])}}
    rng = np.random.default_rng(9)
    y = pert["stats"][STAT]["y"].copy()
    y[later] = rng.normal(0, 1, later.sum())
    pert["stats"][STAT]["y"] = y
    got = IS.run(pert, STAT, 52.0, 2.0, 4.0, 1, TYP)
    protected = td["es"] <= cut                   # matches that read a solve no later than the cut
    # the own-sequence step may add a player's own earlier matches that are unreleased at their query day; protect only
    # rows whose own earlier matches were all released by then (no incremental gap)
    protected &= base["gap_matches"] == 0
    assert protected.sum() > 100
    for k in ("O_eff", "D_eff"):
        assert np.allclose(got[k][protected], base[k][protected], atol=1e-10)
    assert not np.allclose(got["O_eff"][~protected], base["O_eff"][~protected], atol=1e-6)


def test_separate_serve_and_return_penalties():
    """A pair (kappa_E, kappa_F): equal values match the shared penalty; an infinite side switches that side off;
    both infinite is the pooled IOS."""
    td, _ = synthetic(n_matches=1200, surface_effect=0.2, seed=13)
    shared = IS.run(td, STAT, 52.0, 2.0, 3.0, 1, TYP)
    pair = IS.run(td, STAT, 52.0, 2.0, (3.0, 3.0), 1, TYP)
    assert np.allclose(shared["O_eff"], pair["O_eff"], atol=1e-12, equal_nan=True)
    ret_only = IS.run(td, STAT, 52.0, 2.0, (np.inf, 3.0), 1, TYP)
    assert np.nanmax(np.abs(ret_only["E"])) < 1e-8 and np.nanmax(np.abs(ret_only["F"])) > 1e-3
    pooled = IS.run(td, STAT, 52.0, 2.0, np.inf, 1, TYP)
    both_off = IS.run(td, STAT, 52.0, 2.0, (np.inf, np.inf), 1, TYP)
    assert np.allclose(both_off["O_eff"], pooled["O_eff"], atol=1e-12, equal_nan=True)


def test_surface_effects_zero_without_surface_data():
    td, _ = synthetic(seed=7)
    td["surf"] = np.zeros_like(td["surf"])        # every surface unknown: no deviation term can be fitted
    res = IS.run(td, STAT, 26.0, 3.0, 2.0, 1, TYP)
    pooled = IS.run(td, STAT, 26.0, 3.0, np.inf, 1, TYP)
    assert np.allclose(res["E"], 0) and np.allclose(res["F"], 0)
    assert np.allclose(res["O_eff"], pooled["O_eff"], atol=1e-7)


@pytest.mark.parametrize("bad", [True])
def test_inverted_window_refused(bad):
    td, _ = synthetic(n_matches=100)
    td["lf"] = td["es"] - 2
    with pytest.raises(ValueError):
        IS.run(td, STAT, 26.0, 3.0, 2.0, 1, TYP)
