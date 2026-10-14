"""Tests of the level layer in the joint solves (src/eda/lower_level_evidence/level_layer_ios.py), role C2.

On synthetic histories built like the solvers' own inputs (rows in A, B pairs; events with rounds on the leak-proof
timeline, so the incremental step has unreleased earlier rounds to add):
    * off without LLE_LAYER: every hook returns its input object, the decided function's result
    * identity (m = 1, delta = 0): both solver variants equal the decided solvers bit for bit
    * m = 0 drops a row exactly: equal bit for bit to the decided solver with that row's box score removed
    * delta: equal bit for bit to the decided solver on y - delta
    * weights enter as weights: the last snapshot equals a dense weighted ridge solve
    * no leak: reversing results after a cut day moves no value of a match finished by it
    * the config: the Phase 1 forms, the tour and family switches, Phase 2 settings refused
    * the patch: applied to a fake sandbox, idempotent, checked, refused on the repository; the guards
Run: ./python.sh -m pytest test/lower_level_evidence/test_level_layer_ios.py -q
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import level_layer_ios as L  # noqa: E402
from src.eda.match_timing import ios_time as IT  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402


# ------------------------------------------------------------------------------------------------
# A synthetic history

def synth(n_players=40, n_events=30, seed=0, stat="spw", typ=70.0, unknown_surface=True, tour="atp"):
    """Events of 8 players and three rounds (QF, SF, F: 4 + 2 + 1 matches), a week apart, on a leak-proof timeline
    where a round is released two days after it starts and the next round starts a day later, so later rounds see
    their own earlier rounds only through the incremental step. Every row carries a level code."""
    rng = np.random.default_rng(seed)
    skill = rng.normal(0, 0.3, n_players)
    pid, day, ev, rnd, surf, es, lf, obs, x, d, lvl, season = ([] for _ in range(12))
    for e in range(n_events):
        d0 = 17000 + 7 * e
        s_code = int(rng.integers(0 if unknown_surface else 1, 5))
        lv = int(rng.choice([0, 1, 2, 3, 4, 5, 6, 7]))
        alive = list(rng.choice(n_players, 8, replace=False))
        for r in range(3):
            nxt = []
            for i in range(0, len(alive), 2):
                a, b = alive[i], alive[i + 1]
                for srv, ret in ((a, b), (b, a)):
                    dd = int(rng.integers(40, 90))
                    p = 1 / (1 + np.exp(-(0.6 + skill[srv] - skill[ret])))
                    pid.append(srv)
                    day.append(d0)
                    ev.append(e)
                    rnd.append(r)
                    surf.append(s_code)
                    es.append(d0 + r)
                    lf.append(d0 + r + 1)
                    obs.append(d0 + r)
                    x.append(rng.binomial(dd, p))
                    d.append(dd)
                    lvl.append(lv)
                    season.append(2010 + e // 10)
                nxt.append(a if rng.random() < 0.5 else b)
            alive = nxt
    x, d = np.array(x, float), np.array(d, float)
    ok = rng.random(len(x)) > 0.05
    mu = 0.62
    y = np.where(ok, np.log((x + 0.5) / (d + 0.5)) - np.log(mu / (1 - mu)), 0.0)
    td = {"tour": tour, "pid": np.array(pid, np.int64), "n_players": n_players, "day": np.array(day, np.int64),
          "ev": np.array(ev, np.int64), "round_order": np.array(rnd, np.int64), "surf": np.array(surf, np.int64),
          "es": np.array(es, float), "lf": np.array(lf, float), "obs": np.array(obs, float),
          "lle_bucket": np.array(lvl, np.int8), "lle_season": np.array(season, np.int64),
          "stats": {stat: {"ok": ok, "x": np.where(ok, x, 0.0), "d": np.where(ok, d, 0.0), "y": y,
                           "mu": np.full(len(x), np.log(mu / (1 - mu))), "typ": typ}}}
    return td


def timed(td, stat="spw", h=26.0, kappa=1.0, tau=1):
    return td, stat, h, kappa, tau, td["es"], td["lf"], td["obs"]


def same(a, b) -> bool:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return a.shape == b.shape and bool(np.all((a == b) | (np.isnan(a) & np.isnan(b))))


TIMED_KEYS = ("O", "D", "O_snap", "D_snap", "gap_matches")
SURF_KEYS = ("O_eff", "D_eff", "O", "D", "E", "F", "O_snap", "D_snap", "E_snap", "F_snap", "P", "Q")


def with_stat(td, stat, **kw):
    return dict(td, stats={**td["stats"], stat: {**td["stats"][stat], **kw}})


@pytest.fixture
def no_layer(monkeypatch):
    monkeypatch.delenv(L.ENV, raising=False)
    L.LL._CFG.clear()


def use_config(monkeypatch, tmp_path, cfg: dict, name="cfg.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv(L.ENV, str(p))
    L.LL._CFG.clear()
    return p


# ------------------------------------------------------------------------------------------------
# Off by default

def test_hooks_are_off_without_the_variable(no_layer, tmp_path):
    td = synth()
    rows = pd.DataFrame({"match_id": ["m"] * len(td["pid"]), "year": 2015})
    assert L.annotate_td(td, rows, idx=np.arange(len(td["pid"]))) is td
    arrays = {"a": np.zeros(3)}
    assert L.annotate_cache(arrays, rows, np.arange(3)) is arrays
    meta = {"x": 1}
    assert L.stamp(meta) is meta
    assert L.runs_dir(tmp_path / "full_runs") == tmp_path / "full_runs"
    assert L.row_plan(td, "spw", "ios") is None
    a = L.run_timed(*timed(td))
    b = IT.run_timed(*timed(td))
    assert all(same(a[k], b[k]) for k in TIMED_KEYS) and "lle_layer" not in a["solver"]
    a = L.run_surface(td, "spw", 26.0, 1.0, 10.0, 1, 70.0)
    b = IS.run(td, "spw", 26.0, 1.0, 10.0, 1, 70.0)
    assert all(same(a[k], b[k]) for k in SURF_KEYS) and "lle_layer" not in a["solver"]
    assert L.fingerprint(None) == "off"


# ------------------------------------------------------------------------------------------------
# Identity: bit for bit

@pytest.mark.parametrize("tau,h", [(1, 26.0), (0, 52.0), (1, np.inf)])
def test_identity_timed_is_the_decided_solver_bit_for_bit(tau, h):
    td = synth(seed=1)
    n = len(td["pid"])
    a = L.solve_timed(*timed(td, h=h, tau=tau), np.ones(n), np.zeros(n))
    b = IT.run_timed(*timed(td, h=h, tau=tau))
    for k in TIMED_KEYS:
        assert same(a[k], b[k]), k
    assert a["solver"] == b["solver"]


@pytest.mark.parametrize("ks", [10.0, np.inf, (np.inf, 3.0), (5.0, np.inf)])
@pytest.mark.parametrize("tau", [0, 1])
def test_identity_surface_is_the_decided_solver_bit_for_bit(ks, tau):
    td = synth(seed=2)
    n = len(td["pid"])
    a = L.solve_surface(td, "spw", 26.0, 1.0, ks, tau, 70.0, np.ones(n), np.zeros(n))
    b = IS.run(td, "spw", 26.0, 1.0, ks, tau, 70.0)
    for k in SURF_KEYS:
        assert same(a[k], b[k]), k
    if "E_all" in b:
        assert same(a["E_all"], b["E_all"]) and same(a["F_all"], b["F_all"])
    assert a["solver"] == b["solver"]


def test_identity_surface_until_day_bit_for_bit():
    td = synth(seed=3)
    n = len(td["pid"])
    cut = int(np.median(td["es"]))
    a = L.solve_surface(td, "spw", 26.0, 1.0, 10.0, 1, 70.0, np.ones(n), np.zeros(n), until_day=cut)
    b = IS.run(td, "spw", 26.0, 1.0, 10.0, 1, 70.0, until_day=cut)
    for k in SURF_KEYS:
        assert same(a[k], b[k]), k


# ------------------------------------------------------------------------------------------------
# m = 0 is a physical exclusion; delta shifts y

def drop_some(td, seed=5, frac=0.3):
    rng = np.random.default_rng(seed)
    n = len(td["pid"])
    m = np.ones(n)
    m[rng.random(n) < frac] = 0.0
    return m


def test_zero_weight_drops_the_row_exactly_timed():
    td = synth(seed=4)
    m = drop_some(td)
    n = len(m)
    a = L.solve_timed(*timed(td), m, np.zeros(n))
    td2 = with_stat(td, "spw", ok=td["stats"]["spw"]["ok"] & (m > 0))
    b = IT.run_timed(*timed(td2))
    for k in TIMED_KEYS:
        assert same(a[k], b[k]), k


@pytest.mark.parametrize("ks", [10.0, np.inf])
def test_zero_weight_drops_the_row_exactly_surface(ks):
    td = synth(seed=6)
    m = drop_some(td, seed=7)
    n = len(m)
    a = L.solve_surface(td, "spw", 26.0, 1.0, ks, 1, 70.0, m, np.zeros(n))
    td2 = with_stat(td, "spw", ok=td["stats"]["spw"]["ok"] & (m > 0))
    b = IS.run(td2, "spw", 26.0, 1.0, ks, 1, 70.0)
    for k in SURF_KEYS:
        assert same(a[k], b[k]), k


def test_a_whole_level_dropped_equals_its_box_scores_removed():
    """SEP_ALL's shape: every lower-level row at m = 0 equals the decided solver on main-tour and team box scores only."""
    td = synth(seed=8)
    lower = np.isin(td["lle_bucket"], L.LOWER_CODES)
    m = np.where(lower, 0.0, 1.0)
    n = len(m)
    a = L.solve_surface(td, "spw", 52.0, 3.0, 30.0, 1, 70.0, m, np.zeros(n))
    td2 = with_stat(td, "spw", ok=td["stats"]["spw"]["ok"] & ~lower)
    b = IS.run(td2, "spw", 52.0, 3.0, 30.0, 1, 70.0)
    for k in SURF_KEYS:
        assert same(a[k], b[k]), k


def test_delta_is_y_minus_delta_bit_for_bit():
    td = synth(seed=9)
    n = len(td["pid"])
    rng = np.random.default_rng(10)
    delta = np.where(np.isin(td["lle_bucket"], L.LOWER_CODES), rng.normal(0, 0.05, n), 0.0)
    st = td["stats"]["spw"]
    td2 = with_stat(td, "spw", y=st["y"] - delta)
    a = L.solve_timed(*timed(td), np.ones(n), delta)
    b = IT.run_timed(*timed(td2))
    for k in TIMED_KEYS:
        assert same(a[k], b[k]), k
    a = L.solve_surface(td, "spw", 26.0, 1.0, 10.0, 1, 70.0, np.ones(n), delta)
    b = IS.run(td2, "spw", 26.0, 1.0, 10.0, 1, 70.0)
    for k in SURF_KEYS:
        assert same(a[k], b[k]), k


def test_weights_enter_as_weights_in_a_dense_ridge():
    """No decay, tau 0: the snapshot after every release minimises sum m_k (y_k - O_srv + D_ret)^2 + kappa (|O|^2 +
    |D|^2): compare with the dense normal equations."""
    td = synth(seed=11, n_players=30, n_events=20, unknown_surface=False)
    n = len(td["pid"])
    rng = np.random.default_rng(12)
    m = rng.choice([0.0, 0.5, 1.0, 1.5], n)
    # one extra query row after everything: reuse the last match, moved far into the future (both of its rows)
    last = np.arange(n - 2, n)
    es, lf = td["es"].copy(), td["lf"].copy()
    es[last] = es.max() + 100
    lf[last] = es[last] + 1
    td = dict(td, es=es, lf=lf, obs=es.copy())
    kappa = 2.0
    r = L.solve_timed(td, "spw", np.inf, kappa, 0, td["es"], td["lf"], td["obs"], m, np.zeros(n))
    st = td["stats"]["spw"]
    keep = st["ok"] & (m > 0)
    keep[last] = False
    P = td["n_players"]
    A = np.zeros((2 * P, 2 * P))
    b = np.zeros(2 * P)
    for k in np.flatnonzero(keep):
        s, t = td["pid"][k], td["pid"][k ^ 1]
        w = m[k]
        g = np.zeros(2 * P)
        g[s], g[P + t] = 1.0, -1.0
        A += w * np.outer(g, g)
        b += w * st["y"][k] * g
    A += kappa * np.eye(2 * P)
    sol = np.linalg.solve(A, b)
    k0 = last[0]
    assert abs(r["O_snap"][k0] - sol[td["pid"][k0]]) < 1e-6
    assert abs(r["D_snap"][k0] - sol[P + td["pid"][k0]]) < 1e-6


def test_uniform_weights_equal_a_scaled_ridge():
    """m = c on every row is the decided solve with kappa / c (to solver tolerance)."""
    td = synth(seed=13)
    n = len(td["pid"])
    a = L.solve_timed(*timed(td, kappa=2.0), np.full(n, 2.0), np.zeros(n))
    b = IT.run_timed(*timed(td, kappa=1.0))
    assert np.nanmax(np.abs(a["O_snap"] - b["O_snap"])) < 1e-6
    assert np.nanmax(np.abs(a["D_snap"] - b["D_snap"])) < 1e-6


# ------------------------------------------------------------------------------------------------
# No leak

@pytest.mark.parametrize("solver", ["timed", "surface"])
def test_reversing_later_results_moves_no_earlier_value(solver):
    td = synth(seed=14, n_events=24)
    n = len(td["pid"])
    rng = np.random.default_rng(15)
    m = rng.choice([0.0, 0.5, 1.0, 1.3], n)
    delta = np.where(np.isin(td["lle_bucket"], L.LOWER_CODES), 0.04, 0.0)
    cut = float(np.quantile(td["es"], 0.6))
    later = td["es"] > cut
    st = td["stats"]["spw"]
    # reverse every later match: the two rows exchange their statistics
    y2, x2, d2, ok2 = st["y"].copy(), st["x"].copy(), st["d"].copy(), st["ok"].copy()
    k = np.flatnonzero(later)
    y2[k], x2[k], d2[k], ok2[k] = st["y"][k ^ 1], st["x"][k ^ 1], st["d"][k ^ 1], st["ok"][k ^ 1]
    td2 = with_stat(td, "spw", y=y2, x=x2, d=d2, ok=ok2)
    if solver == "timed":
        a = L.solve_timed(*timed(td), m, delta)
        b = L.solve_timed(*timed(td2), m, delta)
        keys = ("O", "D")
    else:
        a = L.solve_surface(td, "spw", 26.0, 1.0, 10.0, 1, 70.0, m, delta)
        b = L.solve_surface(td2, "spw", 26.0, 1.0, 10.0, 1, 70.0, m, delta)
        keys = ("O_eff", "D_eff", "E", "F")
    earlier = td["lf"] <= cut
    assert earlier.any() and later.any()
    for key in keys:
        assert np.allclose(a[key][earlier], b[key][earlier], rtol=0, atol=1e-12, equal_nan=True), key
    assert not all(np.allclose(a[key][later], b[key][later], equal_nan=True) for key in keys)


# ------------------------------------------------------------------------------------------------
# Form (b): the level effect estimated inside the solve

def fe_codes(td, levels=("TQ", "GSQ", "CH", "CHQ")):
    """Each row's level-effect index: the position of its level in ``levels`` (-1 elsewhere)."""
    code = np.full(len(td["pid"]), -1, np.int64)
    for j, b in enumerate(levels):
        code[td["lle_bucket"] == L.CODE[b]] = j
    return code


@pytest.mark.parametrize("ks", [10.0, np.inf])
def test_fixed_effect_without_levels_is_the_plain_solver_bit_for_bit(ks):
    td = synth(seed=20)
    n = len(td["pid"])
    a = L.solve_fe(td, "spw", 26.0, 1.0, ks, 1, 70.0, np.ones(n), np.full(n, -1))
    b = IS.run(td, "spw", 26.0, 1.0, ks, 1, 70.0)
    for k in SURF_KEYS:
        assert same(a[k], b[k]), k
    assert a["beta_rows"].shape == (n, 0)


def planted(seed=21, n_events=160, betas=(0.20, -0.10, 0.05, -0.15), noise=0.05):
    """Observations y = O_srv - D_ret + beta_level + noise on synth's schedule (every level mixes the same players)."""
    td = synth(seed=seed, n_events=n_events, n_players=40, unknown_surface=False)
    rng = np.random.default_rng(seed + 1)
    P = td["n_players"]
    O, D = rng.normal(0, 0.2, P), rng.normal(0, 0.2, P)
    srv, ret = td["pid"], td["pid"][np.arange(len(td["pid"])) ^ 1]
    code = fe_codes(td)
    beta = np.r_[np.asarray(betas), 0.0]
    y = O[srv] - D[ret] + beta[code] + rng.normal(0, noise, len(srv))
    ok = np.ones(len(srv), bool)
    td = with_stat(td, "spw", y=y, ok=ok, d=np.full(len(srv), 70.0), x=np.full(len(srv), 40.0))
    return td, code, np.asarray(betas)


@pytest.mark.parametrize("ks", [np.inf, 5.0])
def test_fixed_effect_recovers_planted_level_effects(ks):
    td, code, betas = planted()
    n = len(code)
    r = L.solve_fe(td, "spw", np.inf, 0.1, ks, 0, 70.0, np.ones(n), code)
    assert r["solver"]["not_converged"] == 0
    assert np.max(np.abs(r["beta_last"] - betas)) < 0.02
    # ignoring the level effects biases the players instead
    r0 = L.solve_surface(td, "spw", np.inf, 0.1, ks, 0, 70.0, np.ones(n), np.zeros(n))
    last = td["es"] == td["es"].max()
    resid_fe = np.abs(r["O_snap"][last] - r0["O_snap"][last]).max()
    assert resid_fe > 0.0


def test_fixed_effect_solves_the_augmented_normal_equations():
    """Pooled, no decay, tau 0, weights m: the last snapshot equals the dense solve of the ridge with level effects."""
    td, code, _ = planted(seed=22, n_events=40)
    n = len(code)
    rng = np.random.default_rng(23)
    m = rng.choice([0.0, 0.5, 1.0, 1.5], n)
    last = np.arange(n - 2, n)
    es, lf = td["es"].copy(), td["lf"].copy()
    es[last] = es.max() + 100
    lf[last] = es[last] + 1
    td = dict(td, es=es, lf=lf, obs=es.copy())
    kappa, kb = 0.7, 0.3
    r = L.solve_fe(td, "spw", np.inf, kappa, np.inf, 0, 70.0, m, code, kappa_beta=kb)
    st = td["stats"]["spw"]
    keep = st["ok"] & (m > 0)
    keep[last] = False
    P, nL = td["n_players"], int(code.max()) + 1
    A = np.zeros((2 * P + nL, 2 * P + nL))
    b = np.zeros(2 * P + nL)
    for k in np.flatnonzero(keep):
        s, t = td["pid"][k], td["pid"][k ^ 1]
        g = np.zeros(2 * P + nL)
        g[s], g[P + t] = 1.0, -1.0
        if code[k] >= 0:
            g[2 * P + code[k]] = 1.0
        A += m[k] * np.outer(g, g)
        b += m[k] * st["y"][k] * g
    A[:2 * P, :2 * P] += kappa * np.eye(2 * P)
    A[2 * P:, 2 * P:] += kb * np.eye(nL)
    sol = np.linalg.solve(A, b)
    # the solver's system holds only players with an observation; the others are 0 in both
    k0 = last[0]
    assert abs(r["O_snap"][k0] - sol[td["pid"][k0]]) < 1e-6
    assert abs(r["D_snap"][k0] - sol[P + td["pid"][k0]]) < 1e-6
    assert np.max(np.abs(r["beta_rows"][k0] - sol[2 * P:])) < 1e-6


@pytest.mark.parametrize("ks", [np.inf, 10.0])
def test_fixed_effect_reversing_later_results_moves_no_earlier_value(ks):
    td = synth(seed=24, n_events=24)
    n = len(td["pid"])
    code = fe_codes(td)
    m = np.random.default_rng(25).choice([0.0, 0.5, 1.0], n)
    cut = float(np.quantile(td["es"], 0.6))
    later = td["es"] > cut
    st = td["stats"]["spw"]
    y2, x2, d2, ok2 = st["y"].copy(), st["x"].copy(), st["d"].copy(), st["ok"].copy()
    k = np.flatnonzero(later)
    y2[k], x2[k], d2[k], ok2[k] = st["y"][k ^ 1], st["x"][k ^ 1], st["d"][k ^ 1], st["ok"][k ^ 1]
    td2 = with_stat(td, "spw", y=y2, x=x2, d=d2, ok=ok2)
    a = L.solve_fe(td, "spw", 26.0, 1.0, ks, 1, 70.0, m, code)
    b = L.solve_fe(td2, "spw", 26.0, 1.0, ks, 1, 70.0, m, code)
    earlier = td["lf"] <= cut
    for key in ("O_eff", "D_eff", "E", "F"):
        assert np.allclose(a[key][earlier], b[key][earlier], rtol=0, atol=1e-12, equal_nan=True), key
    assert np.allclose(a["beta_rows"][earlier], b["beta_rows"][earlier], rtol=0, atol=1e-12, equal_nan=True)
    assert not np.allclose(a["O_eff"][later], b["O_eff"][later], equal_nan=True)


# ------------------------------------------------------------------------------------------------
# The config

FAMS ={"points_52w": False, "forms": False, "ios": True, "ios_points_short": True, "ratings_iid": False,
        "elo": False}
BASE = {"name": "X", "tours": ["atp"], "params": None, "params_sha256": None, "classes": None, "translate": False,
        "weight": 1, "weight_results": 1, "prior": "pool", "itf_box": "as_is", "families": FAMS}


def test_phase1_forms_of_the_config():
    b = np.array([L.CODE[x] for x in L.BUCKETS], np.int8)
    s = np.full(len(b), 2015)
    m, d = L.level_arrays(L.validate_config(dict(BASE)), "atp", "spw", b, s)
    assert np.all(m == 1) and np.all(d == 0)
    m, _ = L.level_arrays(L.validate_config({**BASE, "weight": 0, "itf_box": "exclude"}), "atp", "spw", b, s)
    assert dict(zip(L.BUCKETS, m)) == {"MAIN": 1, "TQ": 0, "GSQ": 0, "CH": 0, "CHQ": 0, "ITF": 0, "ITFQ": 0, "TEAM": 1}
    m, _ = L.level_arrays(L.validate_config({**BASE, "itf_box": "exclude"}), "atp", "spw", b, s)
    assert dict(zip(L.BUCKETS, m)) == {"MAIN": 1, "TQ": 1, "GSQ": 1, "CH": 1, "CHQ": 1, "ITF": 0, "ITFQ": 0, "TEAM": 1}
    m, _ = L.level_arrays(L.validate_config({**BASE, "weight": 0.5, "itf_box": "exclude"}), "atp", "spw", b, s)
    assert dict(zip(L.BUCKETS, m)) == {"MAIN": 1, "TQ": .5, "GSQ": .5, "CH": .5, "CHQ": .5, "ITF": 0, "ITFQ": 0,
                                       "TEAM": 1}
    # C1's rule: under "as_is" ITF and ITFQ rows stay as the reference has them, whatever the arm's weight
    m, _ = L.level_arrays(L.validate_config({**BASE, "weight": 0.5}), "atp", "spw", b, s)
    assert dict(zip(L.BUCKETS, m)) == {"MAIN": 1, "TQ": .5, "GSQ": .5, "CH": .5, "CHQ": .5, "ITF": 1, "ITFQ": 1,
                                       "TEAM": 1}


@pytest.mark.parametrize("change", [{"translate": True, "ios_level_term": "supplied"}, {"prior": "newcomer"}])
def test_switched_off_settings_are_refused(change):
    """Form (a) in the config path and the newcomer prior stay refused (the lead's rulings of 9 Oct 2026), bypassing
    C1's own checks of params and strength."""
    b = np.zeros(3, np.int8)
    cfg = {**L.validate_config(dict(BASE)), **change}
    with pytest.raises(NotImplementedError):
        L.level_arrays(cfg, "atp", "spw", b, np.full(3, 2015))


@pytest.mark.parametrize("bad", [{"weight": 2.0}, {"tours": ["itf"]}, {"prior": "x"}, {"itf_box": "x"},
                                 {"translate": "yes"}])
def test_malformed_configs_are_refused(bad):
    with pytest.raises((ValueError, KeyError)):
        L.validate_config({**BASE, **bad})


def test_tour_and_family_switches(monkeypatch, tmp_path):
    use_config(monkeypatch, tmp_path, {**BASE, "tours": ["atp"], "weight": 0, "itf_box": "exclude",
                                       "families": {**FAMS, "ios": True, "ios_points_short": False}})
    td = synth()
    assert L.row_plan(dict(td, tour="wta"), "spw", "ios") is None          # a tour the config does not name
    assert L.row_plan(td, "spw", "ios_points_short") is None               # a family switched off
    plan = L.row_plan(td, "spw", "ios")
    lower = np.isin(td["lle_bucket"], L.LOWER_CODES)
    ok = td["stats"]["spw"]["ok"]                                  # rows without a box score read no w (they never enter)
    assert np.all(plan.mult[lower & ok] == 0) and np.all(plan.mult[~lower] == 1)
    assert plan.summary["dropped_rows"] == int((td["stats"]["spw"]["ok"] & lower).sum())
    # the hook routes to the variant, and the decided function for WTA
    a = L.run_timed(*timed(td))
    b = IT.run_timed(*timed(with_stat(td, "spw", ok=td["stats"]["spw"]["ok"] & ~lower)))
    assert all(same(a[k], b[k]) for k in ("O", "D")) and a["solver"]["lle_layer"]["dropped_rows"] > 0
    w = L.run_timed(*timed(dict(td, tour="wta")))
    assert "lle_layer" not in w["solver"]
    with pytest.raises(RuntimeError):
        L.row_plan({k: v for k, v in td.items() if k != "lle_bucket"}, "spw", "ios")


def fe_config(tmp_path, **kw) -> dict:
    """A config with the level effect estimated in the solve (form b). C1's loader asks for params and the strength
    whenever translate is on; the fixed-effect solve reads neither, so stand-in files serve."""
    stand = tmp_path / "standin.bin"
    stand.write_bytes(b"not read")
    sha = L.sha256_file(stand)
    return {**BASE, "translate": True, "ios_level_term": "fixed_effect", "params": str(stand), "params_sha256": sha,
            "strength": {"path": str(stand), "sha256": sha}, **kw}


def test_fixed_effect_through_the_hooks(monkeypatch, tmp_path):
    use_config(monkeypatch, tmp_path, fe_config(tmp_path, tours=["atp"]))
    td = synth(seed=30)
    plan = L.row_plan(td, "spw", "ios")
    assert plan.fe_levels == tuple(L_ for L_ in L.LOWER if (td["lle_bucket"] == L.CODE[L_]).any()
                                   and L_ not in ("ITF", "ITFQ"))
    none = np.isin(td["lle_bucket"], [L.CODE[b] for b in ("MAIN", "TEAM", "ITF", "ITFQ")])
    ok = td["stats"]["spw"]["ok"]                                  # a level code only on kept observations
    assert np.all(plan.fe_code[none | ~ok] == -1) and np.all(plan.fe_code[~none & ok] >= 0)
    itf = np.isin(td["lle_bucket"], [L.CODE["ITF"], L.CODE["ITFQ"]])
    assert np.all(plan.mult[itf] == 1.0)                          # as_is: ITF rows left as the reference has them
    n = len(td["pid"])
    a = L.run_surface(td, "spw", 26.0, 1.0, 10.0, 1, 70.0)
    b = L.solve_fe(td, "spw", 26.0, 1.0, 10.0, 1, 70.0, np.ones(n), plan.fe_code)
    assert all(same(a[k], b[k]) for k in SURF_KEYS)
    assert set(a["solver"]["lle_layer_beta_2024"]) == set(plan.fe_levels)      # synth's days precede the holdout
    # the timed hook runs the pooled model in the same solver, and equals lane 2's pooled ("current") run bit for bit
    # (lane 3's mapping check): the pooled surface hook zeroes the rows' surfaces as the timed hook does (synth's rows
    # carry several surfaces, so this fails if the pooled run splits them)
    assert len(np.unique(td["surf"])) > 2
    t = L.run_timed(*timed(td, h=26.0, kappa=1.0, tau=1))
    s = L.run_surface(td, "spw", 26.0, 1.0, np.inf, 1, 70.0)
    assert same(t["O"], s["O"]) and same(t["D"], s["D"]) and same(t["O"], s["O_eff"]) and same(t["D"], s["D_eff"])
    split = L.solve_fe(td, "spw", 26.0, 1.0, np.inf, 1, 70.0, np.ones(n), plan.fe_code)    # surfaces kept: the old run
    assert not same(t["O"], split["O"])                     # so the check above can tell the two arrangements apart
    # with ITF excluded, ITF rows get no level effect (they are dropped)
    use_config(monkeypatch, tmp_path, fe_config(tmp_path, itf_box="exclude"), "itf.json")
    plan = L.row_plan(td, "spw", "ios")
    assert "ITF" not in plan.fe_levels and "ITFQ" not in plan.fe_levels


# ------------------------------------------------------------------------------------------------
# Phase 2: role B's fitted w_joint, role A's levels, the plain path when no level effect is left

def write_params(tmp_path, seasons=range(2013, 2016), stats=("spw", "hold"), drop=()) -> tuple[str, str]:
    """A small table in role B's shape: w and w_joint differ (the hook must read w_joint); w_joint encodes the key."""
    rows = []
    for y in seasons:
        for t in ("atp", "wta"):
            for si, s in enumerate(stats):
                for li, lv in enumerate(("MAIN", "TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")):
                    if (y, t, s, lv) in drop:
                        continue
                    wj = 1.0 if lv == "MAIN" else round(0.1 + 0.01 * (y - 2013) + 0.1 * li + 0.001 * si, 6)
                    rows.append({"season_used": y, "tour": t, "stat": s, "level": lv, "gamma": 0.0, "delta": 0.0,
                                 "w": 0.5, "strength_ref": 1500.0, "w_joint": wj})
    p = tmp_path / "params.parquet"
    pd.DataFrame(rows).to_parquet(p, index=False)
    return str(p), L.sha256_file(p)


def write_classes(tmp_path) -> tuple[str, str]:
    rows = [{"name": "spw", "kind": "stat", "base_stat": "spw", "class": "OPP", "tour": "atp", "delta_levels": "CH,CHQ"},
            {"name": "hold", "kind": "stat", "base_stat": "hold", "class": "OPP", "tour": "atp", "delta_levels": "none"},
            {"name": "spw", "kind": "stat", "base_stat": "spw", "class": "ENV", "tour": "wta", "delta_levels": "GSQ"},
            {"name": "hold", "kind": "stat", "base_stat": "hold", "class": "INTR", "tour": "wta",
             "delta_levels": "CH"},
            {"name": "ios_points_short", "kind": "input", "base_stat": "spw+rpw", "class": "OPP", "tour": "atp",
             "delta_levels": "TQ,GSQ,CH,CHQ"}]
    p = tmp_path / "classes.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return str(p), L.sha256_file(p)


def sys_config(tmp_path, **kw) -> dict:
    params, psha = write_params(tmp_path, **kw.pop("params_kw", {}))
    classes, csha = write_classes(tmp_path)
    stand = tmp_path / "strength.bin"
    stand.write_bytes(b"x")
    return {**BASE, "tours": ["atp", "wta"], "translate": True, "weight": "fitted", "weight_results": 1,
            "params": params, "params_sha256": psha, "classes": classes, "classes_sha256": csha,
            "strength": {"path": str(stand), "sha256": L.sha256_file(stand)}, "params_season_floor": 2013,
            "missing_params": "error", "solve_w": "w_joint", "itf_box": "exclude",
            "families": {**FAMS, "ios": True, "ios_points_short": True}, **kw}


def test_fitted_w_is_w_joint_by_key_level_and_own_season_with_the_floor(tmp_path):
    cfg = L.validate_config(sys_config(tmp_path))
    bucket = np.array([L.CODE[b] for b in ("MAIN", "TQ", "CH", "CHQ", "ITF", "TEAM", "CH", "CH")], np.int8)
    season = np.array([2014, 2014, 2014, 2014, 2014, 2014, 2011, 2015])
    m, d = L.level_arrays(cfg, "atp", "spw", bucket, season)
    t = pd.read_parquet(cfg["params"]).set_index(["season_used", "tour", "stat", "level"])["w_joint"]
    want = [1.0, t[(2014, "atp", "spw", "TQ")], t[(2014, "atp", "spw", "CH")], t[(2014, "atp", "spw", "CHQ")], 0.0,
            1.0, t[(2013, "atp", "spw", "CH")], t[(2015, "atp", "spw", "CH")]]   # ITF excluded; 2011 -> the 2013 floor
    assert np.allclose(m, want, rtol=0, atol=0) and np.all(d == 0)
    mh, _ = L.level_arrays(cfg, "atp", "hold", bucket, season)                    # the key's own row, not spw's
    assert mh[2] == t[(2014, "atp", "hold", "CH")] != m[2]
    # rows that do not enter the solve read no parameter: a missing cell there is no error
    cfg2 = L.validate_config(sys_config(tmp_path, params_kw={"drop": [(2014, "atp", "spw", "CH")]}))
    with pytest.raises(KeyError):
        L.level_arrays(cfg2, "atp", "spw", bucket, season)
    valid = np.array([True, True, False, True, True, True, True, True])
    m2, _ = L.level_arrays(cfg2, "atp", "spw", bucket, season, valid=valid)
    assert m2[2] == 1.0 and m2[3] == t[(2014, "atp", "spw", "CHQ")]
    # missing_params "untouched": a cell with no parameter stays as the reference has it (w 1)
    cfg3 = L.validate_config(sys_config(tmp_path, params_kw={"drop": [(2014, "atp", "spw", "CH")]},
                                        missing_params="untouched"))
    m3, _ = L.level_arrays(cfg3, "atp", "spw", bucket, season)
    assert m3[2] == 1.0 and m3[1] == t[(2014, "atp", "spw", "TQ")]


def test_level_effects_at_role_a_levels_of_the_statistic(tmp_path):
    cfg = L.validate_config(sys_config(tmp_path))
    assert cfg["ios_level_term"] == "fixed_effect"                               # form (b) is the default
    assert L.fe_levels(cfg, "atp", "spw") == ("CH", "CHQ")                      # the stat row, not the input row
    assert L.fe_levels(cfg, "atp", "hold") == ()                                 # "none"
    assert L.fe_levels(cfg, "wta", "spw") == ("GSQ",)                            # ENV: delta where measured
    assert L.fe_levels(cfg, "wta", "hold") == ()                                 # a class that takes no term
    noclass = L.validate_config({**sys_config(tmp_path), "classes": None, "classes_sha256": None})
    assert L.fe_levels(noclass, "atp", "hold") == ("TQ", "GSQ", "CH", "CHQ")     # ITF and ITFQ never
    assert L.stat_key("spw", "ios_points_short") == "spw" and L.stat_key("hold", "ios") == "hold"
    with pytest.raises(NotImplementedError):                                     # form (a): off in the config path
        L.level_arrays({**cfg, "ios_level_term": "supplied"}, "atp", "spw", np.zeros(2, np.int8), np.full(2, 2014))


def test_sys_hooks_run_form_b_with_w_joint_and_w0_is_sep_all(monkeypatch, tmp_path):
    td = synth(seed=40, n_events=40)
    td = dict(td, lle_season=np.clip(td["lle_season"], 2010, 2015))
    use_config(monkeypatch, tmp_path, sys_config(tmp_path, tours=["atp"]), "sys.json")
    plan = L.row_plan(td, "spw", "ios_points_short")
    assert plan.fe_levels == tuple(b for b in ("CH", "CHQ") if (td["lle_bucket"] == L.CODE[b]).any())
    lower = np.isin(td["lle_bucket"], [L.CODE[b] for b in ("TQ", "GSQ", "CH", "CHQ")])
    ok = td["stats"]["spw"]["ok"]
    itf = np.isin(td["lle_bucket"], [L.CODE["ITF"], L.CODE["ITFQ"]])
    assert np.all(plan.mult[lower & ok] < 1) and np.all(plan.mult[itf & ok] == 0) and np.all(plan.mult[~lower & ~itf] == 1)
    a = L.run_timed(*timed(td))
    b = L.solve_fe(dict(td, surf=np.zeros(len(td["pid"]), np.int64)), "spw", 26.0, 1.0, np.inf, 1, 70.0,
                   plan.mult, plan.fe_code, kappa_beta=1.0)
    assert all(same(a[k], b[k]) for k in ("O", "D")) and a["solver"]["lle_layer"]["level_effects"]
    # SYS_w0 (w = 0 at every lower level, translate on): no level effect is left, the plain variant runs, and it is
    # the SEP_ALL config's result bit for bit
    use_config(monkeypatch, tmp_path, sys_config(tmp_path, tours=["atp"], weight=0), "w0.json")
    w0 = L.run_timed(*timed(td))
    s0 = L.run_surface(td, "spw", 26.0, 1.0, 10.0, 1, 70.0)
    assert w0["solver"]["lle_layer"]["level_effects"] == []
    use_config(monkeypatch, tmp_path, {**BASE, "tours": ["atp"], "weight": 0, "itf_box": "exclude"}, "sep.json")
    sep = L.run_timed(*timed(td))
    ss = L.run_surface(td, "spw", 26.0, 1.0, 10.0, 1, 70.0)
    assert all(same(w0[k], sep[k]) for k in TIMED_KEYS) and all(same(s0[k], ss[k]) for k in SURF_KEYS)


def test_fe_shares_and_the_pre_holdout_record():
    td, code, betas = planted(seed=41, n_events=40)
    n = len(code)
    r = L.solve_fe(td, "spw", np.inf, 0.1, np.inf, 0, 70.0, np.ones(n), code)
    sh = r["share_srv_rows"]
    assert sh.shape == (n, len(betas)) and np.nanmin(sh) >= 0 and np.nanmax(sh.sum(axis=1)) <= 1 + 1e-12
    plan = L.RowPlan(np.ones(n), np.zeros(n), {}, code, ("TQ", "GSQ", "CH", "CHQ"))
    res = L._fe_result({"solver": {}, "beta_rows": r["beta_rows"]}, plan, td["es"])
    assert "lle_layer_beta_2024" in res["solver"]                       # synth's days are of 2016-2017
    late = np.full(n, 30000.0)                                           # every query after the holdout's start
    res2 = L._fe_result({"solver": {}, "beta_rows": r["beta_rows"]}, plan, late)
    assert "lle_layer_beta_2024" not in res2["solver"]


def test_fingerprints_and_runs_folders(monkeypatch, tmp_path):
    a = L.validate_config(dict(BASE))
    assert L.fingerprint({**a, "families": {**FAMS, "ios": False, "ios_points_short": False}}) == "off"
    assert L.fingerprint(a) != "off"
    assert L.fingerprint(a) != L.fingerprint({**a, "weight": 0.0})
    assert L.fingerprint(a) == L.fingerprint({**a, "name": "other", "weight_results": 0.0})   # not the IOS's business
    assert L.fingerprint(a, ("ios",)) != L.fingerprint({**a, "tours": ["atp", "wta"]}, ("ios",))
    use_config(monkeypatch, tmp_path, dict(BASE))
    d = L.runs_dir(tmp_path / "full_runs")
    assert d.parent == tmp_path / "full_runs" and d.name.startswith("lle_X_")


def test_standard_configs_validate():
    for name, cfg in L.CONFIGS.items():
        c = L.validate_config(dict(cfg), name)
        assert c["name"] == name
    assert L.CONFIGS["SEP_ALL"]["tours"] == ["atp"] and L.CONFIGS["SEP_ALL"]["weight"] == 0
    assert L.CONFIGS["REF_noITF"]["itf_box"] == "exclude" and L.CONFIGS["REF_noITF"]["weight"] == 1
    i = L.CONFIGS["IDENTITY"]
    assert (i["translate"], i["weight"], i["prior"], i["itf_box"]) == (False, 1, "pool", "as_is")


# ------------------------------------------------------------------------------------------------
# The patch and the guards

def fake_sandbox(tmp_path) -> Path:
    """A sandbox holding the DECIDED builders: since 10 Oct 2026 the repository's carry the patch's edits, so the
    decided text is the repository's with each edit undone (unpatched_text)."""
    sb = tmp_path / "sb"
    for rel in list(L.PATCHES) + list(L.COPIED):
        (sb / rel).parent.mkdir(parents=True, exist_ok=True)
        if rel in L.PATCHES:
            (sb / rel).write_text(L.unpatched_text((ROOT / rel).read_text(encoding="utf-8"), rel), encoding="utf-8")
        else:
            shutil.copy2(ROOT / rel, sb / rel)
    return sb


def test_the_repository_carries_the_patch_and_undoing_it_gives_the_decided_builders():
    for rel, edits in L.PATCHES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert L.integrated(text, rel)
        dec = L.unpatched_text(text, rel)
        assert not L.integrated(dec, rel)
        assert all(dec.count(old) == 1 for old, _ in edits)
        assert "_LLEIOS" not in dec                            # the decided builder knows nothing of the layer


def test_patch_applies_once_checks_and_refuses_the_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "DIFF", tmp_path / "patch.diff")
    sb = fake_sandbox(tmp_path)
    assert not L.check_patch(sb)["ok"]
    r = L.apply_patch(sb)
    assert all(set(v) == {"patched"} for v in r["files"].values())
    assert L.check_patch(sb)["ok"]
    r2 = L.apply_patch(sb)                                     # idempotent
    assert all(set(v) == {"already patched"} for v in r2["files"].values())
    assert L.check_patch(sb)["ok"]
    p = sb / "src/eda/surface_ios/build_features.py"
    p.write_text(p.read_text(encoding="utf-8") + "\n# another edit\n", encoding="utf-8")
    assert not L.check_patch(sb)["ok"]
    with pytest.raises(SystemExit):
        L.apply_patch(ROOT)
    # the patched sandbox equals the repository's (integrated) builders, so no diff is written: the study's own diff
    # (system/ios_layer/sandbox_patch_ios.diff) is never overwritten by an empty one
    assert r["diff"] is None and r.get("integrated_in_repository")
    assert not (tmp_path / "patch.diff").exists()


def write_records(root: Path, part: str | None, merge: str | None, lane2: str | None):
    mt = root / "data" / "studies" / "match_timing"
    si = root / "data" / "studies" / "surface_ios"
    mt.mkdir(parents=True, exist_ok=True)
    si.mkdir(parents=True, exist_ok=True)
    rec = (lambda fp: {} if fp is None else {"lle_layer": {"fingerprint": fp}})
    (mt / "ios_features_summary.json").write_text(json.dumps({"ios": {}, **rec(part)}), encoding="utf-8")
    (mt / "leakproof_features_summary.json").write_text(json.dumps({"ios": rec(merge)}), encoding="utf-8")
    (si / "build_features.json").write_text(json.dumps(rec(lane2)), encoding="utf-8")


def test_guards(monkeypatch, tmp_path):
    root = tmp_path / "tree"
    write_records(root, None, None, None)
    monkeypatch.delenv(L.ENV, raising=False)
    L.LL._CFG.clear()
    L.require_consistent(root, "both")                         # the decided build on decided records
    use_config(monkeypatch, tmp_path, dict(BASE))
    with pytest.raises(RuntimeError):
        L.require_consistent(root, "ios_part")                 # the layer on, the IOS part not rebuilt
    cfg = L.config()
    fp, fp2 = L.fingerprint(cfg), L.fingerprint(cfg, ("ios",))
    write_records(root, fp, None, fp2)
    with pytest.raises(RuntimeError):
        L.require_consistent(root, "ios_part")                 # the merge not re-run after the IOS part
    write_records(root, fp, fp, None)
    L.require_consistent(root, "ios_part")
    with pytest.raises(RuntimeError):
        L.require_consistent(root, "both")                     # lane 2 not run with the layer
    write_records(root, fp, fp, fp2)
    L.require_consistent(root, "both")
    use_config(monkeypatch, tmp_path, {**BASE, "families": {**FAMS, "ios": False, "ios_points_short": False}},
               "off.json")
    write_records(root, None, None, None)
    L.require_consistent(root, "both")                         # the family off: the stored (decided) outputs serve
