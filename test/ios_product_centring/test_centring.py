"""Tests for the IOS product-centring study (src/eda/ios_product_centring/).

Run: ./python.sh -m pytest test/ios_product_centring -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.ios_product_centring import common as C  # noqa: E402
from src.eda.ios_product_centring import reference as R  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402

STAT = "spw"
TYP = 70.0


def synthetic(n_players=40, n_matches=1500, seed=0, start=0):
    """A small history on three surfaces over 600 days (surface_ios's test history), with a main-tour flag per match
    and each match's earliest start = latest finish = its day."""
    rng = np.random.default_rng(seed)
    O, D = rng.normal(0, 0.3, n_players), rng.normal(0, 0.3, n_players)
    E, F = rng.normal(0, 0.1, (n_players, 4)), rng.normal(0, 0.1, (n_players, 4))
    a = rng.integers(0, n_players, n_matches)
    b = (a + rng.integers(1, n_players, n_matches)) % n_players
    day = np.sort(rng.integers(0, 600, n_matches)) + start
    surf = rng.choice([1, 2, 3], n_matches, p=[0.5, 0.35, 0.15])
    pid = np.column_stack([a, b]).reshape(-1)
    opp = pid.reshape(-1, 2)[:, ::-1].reshape(-1)
    s2 = np.repeat(surf, 2)
    eta = O[pid] + E[pid, s2 - 1] - D[opp] - F[opp, s2 - 1]
    d = rng.integers(40, 90, 2 * n_matches).astype(float)
    x = rng.binomial(d.astype(int), 1 / (1 + np.exp(-(0.4 + eta)))).astype(float)
    y = np.log((x + 0.5) / (d - x + 0.5)) - 0.4
    days2 = np.repeat(day, 2).astype(np.int64)
    td = {"pid": pid.astype(np.int64), "n_players": n_players, "day": days2,
          "ev": np.repeat(np.arange(n_matches), 2).astype(np.int64),
          "round_order": np.zeros(2 * n_matches, dtype=np.int64), "surf": s2.astype(np.int64),
          "es": days2.astype(float), "lf": days2.astype(float), "obs": days2.astype(float),
          "level_main": np.repeat(rng.random(n_matches) < 0.6, 2),
          "stats": {STAT: {"ok": np.ones(2 * n_matches, dtype=bool), "x": x, "d": d, "y": y,
                           "mu": np.full(2 * n_matches, 0.4)}}}
    return td


def test_hook_passes_every_snapshot_through_unchanged():
    td = synthetic()
    plain = IS.run(td, STAT, 26.0, 1.0, 10.0, 1, TYP)
    hooked, rec = R.solve_with_reference(td, STAT, 26.0, 1.0, 10.0, 1, TYP)
    for k in ("O_eff", "D_eff", "O", "D", "E", "F", "O_snap", "D_snap"):
        assert np.array_equal(plain[k], hooked[k], equal_nan=True), k
    assert IS.snapshots is R.ORIG_SNAPSHOTS                     # the patch is undone
    assert len(rec["days"]) == len(np.unique(td["es"]))


def test_reference_level_equals_a_brute_force_reading():
    td = synthetic(seed=3)
    _, rec = R.solve_with_reference(td, STAT, 26.0, 1.0, 10.0, 1, TYP)
    release = td["lf"] + 1
    k = R.observation_order(td, STAT)
    sysm = IS.SurfaceSystem(td, STAT, np.where(np.isfinite(td["lf"]), release, np.nan), td["obs"], TYP)
    days = np.unique(td["es"])
    checked = 0
    for i, O, D, E, F, *_ in IS.snapshots(sysm, days, 26.0, 1.0, 10.0, 1):
        t = days[i]
        if i % 97:
            continue
        rows = k[(release[k] <= t) & (td["obs"][k] >= t - C.WINDOW_DAYS) & td["level_main"][k]]
        players = np.unique(np.r_[td["pid"][rows], td["pid"][rows ^ 1]])
        cp = sysm.cmap[players]
        assert rec["count"][i] == len(players)
        if len(players) == 0:
            assert np.isnan(rec["m_o"][i]).all()
            continue
        assert np.isclose(rec["m_o"][i, 0], O[cp].mean(), rtol=0, atol=1e-13)
        assert np.isclose(rec["m_d"][i, 0], D[cp].mean(), rtol=0, atol=1e-13)
        for s in (1, 2, 3, 4):
            assert np.isclose(rec["m_o"][i, s], (O[cp] + E[cp, s - 1]).mean(), rtol=0, atol=1e-13)
            assert np.isclose(rec["m_d"][i, s], (D[cp] + F[cp, s - 1]).mean(), rtol=0, atol=1e-13)
        checked += 1
    assert checked >= 5


def test_reference_ignores_results_released_later():
    """Reversing every result after a cut day leaves every reference level read on or before the cut unchanged."""
    td = synthetic(seed=5)
    _, base = R.solve_with_reference(td, STAT, 26.0, 1.0, 10.0, 1, TYP)
    cut = 400
    later = td["es"] > cut
    flipped = {**td, "stats": {STAT: dict(td["stats"][STAT])}}
    st = flipped["stats"][STAT]
    swap = np.arange(len(td["pid"])) ^ 1
    for key in ("x", "d", "y"):
        v = td["stats"][STAT][key].copy()
        v[later] = td["stats"][STAT][key][swap][later]
        st[key] = v
    _, got = R.solve_with_reference(flipped, STAT, 26.0, 1.0, 10.0, 1, TYP)
    early = base["days"] <= cut
    assert np.array_equal(base["m_o"][early], got["m_o"][early], equal_nan=True)
    assert np.array_equal(base["m_d"][early], got["m_d"][early], equal_nan=True)
    assert not np.allclose(base["m_o"][~early], got["m_o"][~early], equal_nan=True)


def test_reference_window_is_52_weeks():
    """A player whose only main-tour observation is 365 days old has left the reference set; at 364 days they count."""
    td = synthetic(n_matches=200, seed=7)
    td["level_main"][:] = False
    td["level_main"][:2] = True                      # only the first match is main tour
    first = td["day"][0]
    _, rec = R.solve_with_reference(td, STAT, 26.0, 1.0, 10.0, 1, TYP)
    for t, want in ((first + 1, 2), (first + C.WINDOW_DAYS, 2), (first + C.WINDOW_DAYS + 1, 0)):
        i = np.searchsorted(rec["days"], t)
        if i < len(rec["days"]) and rec["days"][i] == t:
            assert rec["count"][i] == want


def test_no_reference_players_leaves_the_product_as_built():
    m = np.array([0.3, np.nan, -0.2])
    count = np.array([5, 0, 0])
    assert np.array_equal(C.level(m, count), np.array([0.3, 0.0, 0.0]))
    oa, ob, da, db = 0.4, -0.1, 0.2, 0.5
    assert C.centred_product(oa, ob, da, db, *C.level(np.array([np.nan, np.nan]), np.array([0, 0]))) == \
        C.built_product(oa, ob, da, db)


def test_product_algebra():
    rng = np.random.default_rng(11)
    oa, ob, da, db = rng.normal(size=(4, 1000))
    m_o, m_d = rng.normal(size=2)
    built = C.built_product(oa, ob, da, db)
    cen = C.centred_product(oa, ob, da, db, m_o, m_d)
    assert np.allclose(cen, built + m_d * (oa - ob) - m_o * (da - db))
    assert np.allclose(C.centred_product(oa, ob, da, db, 0.0, 0.0), built)
    assert np.allclose(C.centred_product(ob, oa, db, da, m_o, m_d), -cen)          # antisymmetric
    # a common shift of every rating, carried by the reference level, leaves the centred product unchanged
    o0, d0 = rng.normal(size=2)
    assert np.allclose(C.centred_product(oa + o0, ob + o0, da + d0, db + d0, m_o + o0, m_d + d0), cen)
    assert not np.allclose(C.built_product(oa + o0, ob + o0, da + d0, db + d0), built)
