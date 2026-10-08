"""Tests for the rating passes of the study "rating systems against Elo" (src/eda/rating_systems/ratings.py).

    * Glicko-2 reproduces Glickman's worked example (glicko.net/glicko/glicko2.pdf) at every published step, and with
      the volatility held and no drift it is Glicko-1 (Glickman's Glicko example, glicko.net/glicko/glicko.pdf);
    * TrueSkill's two-player update equals the moments of the exact posterior, integrated numerically;
    * the time rule on a hand-made history: a round robin's matches never see each other, two events of one week never
      see each other, a later round sees an earlier one, walkovers never move ratings, retirements do;
    * every pre-match value of random histories (round robins, overlapping events, retirements, walkovers, surfaces)
      equals a fresh pass over only the matches the rule lets that match see, for every system and both components;
    * with one match per player per week the passes are plain Glicko-2 (one game per rating period) and plain
      sequential TrueSkill; several events of one week combine as the formulas say;
    * the probe cut by date, event and round (stage1_baselines.probe_by_round) passes the passes and catches a pass
      that lets every match see the earlier rows of its week.

Run: ./python.sh -m pytest test/rating_systems/test_ratings.py
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

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.rating_systems import ratings as R  # noqa: E402

CFG = {"glicko2": {"rd0": 350.0, "sigma0": 0.06, "tau": 0.5},
       "glicko1": {"rd0": 300.0, "sigma0": 0.05},
       "glicko2m": {"rd0": 400.0, "sigma0": 0.07, "tau": 0.6},
       "trueskill": {"sigma0": 2.0, "tau": 0.05, "gamma": 0.3},
       "trueskill_cs": {"sigma0": 2.0, "gamma": 0.4, "rho": 0.7},
       "glicko_cs": {"rd0": 450.0, "sigma0": 0.07, "rho": 0.8},
       "ttt": {"sigma0": 2.0, "gamma": 0.4, "window": 4, "sweeps": 1}}


# ------------------------------------------------------------------------------------------------
# Helpers

def history(rows, surfaces=None) -> pd.DataFrame:
    """Matches from (match_id, event, date, round, winner, loser[, status]), sorted as the table sorts them, with side
    A = the winner in even rows so both sides occur (test_stage1's helper)."""
    recs = []
    for i, r in enumerate(rows):
        mid, ev, date, rnd, w, l = r[:6]
        status = r[6] if len(r) > 6 else "completed"
        a, b = (w, l) if i % 2 == 0 else (l, w)
        recs.append({"match_id": mid, "tournament_id": ev, "tournament_date": pd.Timestamp(date), "round": rnd,
                     "match_num": str(i), "player_a_id": a, "player_b_id": b, "a_won": a == w, "status": status,
                     "surface": (surfaces or {}).get(ev, "Hard"), "evaluation": True})
    m = pd.DataFrame(recs)
    m["round_order"] = m["round"].map(C.ROUND_ORDER)
    m = C.chrono_sort(m).reset_index(drop=True)
    m["year"] = m["tournament_date"].dt.year
    return m


def run(m: pd.DataFrame, system: str, cfg: dict | None = None) -> dict:
    return R.run(RC.history(m), system, cfg or CFG[system])


def random_history(seed=3, weeks=14, players=30, overlap=True, gaps=True) -> pd.DataFrame:
    """Weekly events: a 16-player knockout with a qualifying round, a round robin of four with a final, and
    (``overlap``) a second small knockout the same week that shares players with the first; some retirements and
    walkovers; mixed surfaces, some unknown; (``gaps``) some weeks skipped so the time dynamics act."""
    rng = np.random.default_rng(seed)
    rows, k = [], 0
    date = pd.Timestamp("2024-01-01")
    for wk in range(weeks):
        date = date + pd.Timedelta(weeks=int(rng.integers(1, 4)) if gaps else 1)
        pool = [f"p{x}" for x in rng.permutation(players)]
        q, ko, rr = pool[:4], pool[4:19], pool[19:23]
        winners_q = []
        for i in (0, 2):
            w, l = (q[i], q[i + 1]) if rng.random() < 0.5 else (q[i + 1], q[i])
            rows.append((f"m{k}", f"K{wk}", date, "Q1", w, l))
            winners_q.append(w)
            k += 1
        alive = ko[:14] + winners_q
        for rnd in ("R16", "QF", "SF", "F"):
            nxt = []
            for i in range(0, len(alive), 2):
                w, l = (alive[i], alive[i + 1]) if rng.random() < 0.5 else (alive[i + 1], alive[i])
                u = rng.random()
                st = "retired" if u < 0.06 else "walkover" if u < 0.09 else "completed"
                rows.append((f"m{k}", f"K{wk}", date, rnd, w, l, st))
                nxt.append(w)
                k += 1
            alive = nxt
        wins = {p: 0 for p in rr}
        for i in range(4):
            for j in range(i + 1, 4):
                w, l = (rr[i], rr[j]) if rng.random() < 0.5 else (rr[j], rr[i])
                wins[w] += 1
                rows.append((f"m{k}", f"R{wk}", date, "RR", w, l))
                k += 1
        top = sorted(rr, key=lambda p: -wins[p])[:2]
        rows.append((f"m{k}", f"R{wk}", date, "F", top[0], top[1]))
        k += 1
        if overlap:
            field = list(rng.choice(ko[:14], size=4, replace=False))
            for i in (0, 2):
                w, l = (field[i], field[i + 1]) if rng.random() < 0.5 else (field[i + 1], field[i])
                rows.append((f"m{k}", f"X{wk}", date, "R32", w, l))
                k += 1
    surfaces = {}
    for wk in range(weeks):
        surfaces[f"K{wk}"] = ["Hard", "Clay", "Grass"][wk % 3]
        surfaces[f"R{wk}"] = "Clay"
        surfaces[f"X{wk}"] = None if wk % 4 == 0 else "Hard"
    return history(rows, surfaces=surfaces)


# ------------------------------------------------------------------------------------------------
# The formulas against the published examples

def test_glicko2_reproduces_glickmans_example():
    """glicko2.pdf: a 1500 / 200 / 0.06 player beats a 1400 / 30 and loses to 1550 / 100 and 1700 / 300, tau 0.5."""
    mu, phi = 0.0, 200 / R.SCALE
    games = [((1400 - 1500) / R.SCALE, 30 / R.SCALE, 1.0), ((1550 - 1500) / R.SCALE, 100 / R.SCALE, 0.0),
             ((1700 - 1500) / R.SCALE, 300 / R.SCALE, 0.0)]
    assert [round(R.g(p), 4) for _, p, _ in games] == [0.9955, 0.9531, 0.7242]
    assert [round(R.expected(mu, m, p), 3) for m, p, _ in games] == [0.639, 0.432, 0.303]
    sv = sum(R.g(p) ** 2 * R.expected(mu, m, p) * (1 - R.expected(mu, m, p)) for m, p, _ in games)
    sd = sum(R.g(p) * (s - R.expected(mu, m, p)) for m, p, s in games)
    # the PDF's v = 1.7785 and Delta = -0.4834 are computed from its rounded g and E (4 and 3 decimals); at full
    # precision v = 1.77898. The final rating, deviation and volatility agree at the published rounding.
    assert 1 / sv == pytest.approx(1.7785, abs=6e-4)
    assert sd / sv == pytest.approx(-0.4834, abs=6e-4)
    mu2, phi2, sig2 = R.glicko2_rate(mu, phi, 0.06, games, tau=0.5)
    assert sig2 == pytest.approx(0.05999, abs=1e-5)
    assert mu2 == pytest.approx(-0.2069, abs=1e-4)
    assert phi2 == pytest.approx(0.8722, abs=1e-4)
    assert 1500 + R.SCALE * mu2 == pytest.approx(1464.06, abs=0.01)
    assert R.SCALE * phi2 == pytest.approx(151.52, abs=0.01)


def test_fixed_volatility_without_drift_is_glicko1():
    """glicko.pdf's example (the same games, RD 200 at the period's start): r' = 1464, RD' = 151.4; the Glicko-2 scale
    is Glicko-1's with q = ln 10 / 400, so 1 / q = 173.7178."""
    assert 400 / math.log(10) == pytest.approx(R.SCALE, abs=1e-4)
    games = [((1400 - 1500) / R.SCALE, 30 / R.SCALE, 1.0), ((1550 - 1500) / R.SCALE, 100 / R.SCALE, 0.0),
             ((1700 - 1500) / R.SCALE, 300 / R.SCALE, 0.0)]
    mu2, phi2, sig2 = R.glicko2_rate(0.0, 200 / R.SCALE, 0.0, games, tau=0.5, vol=False)
    assert sig2 == 0.0
    assert round(1500 + R.SCALE * mu2) == 1464
    assert round(R.SCALE * phi2, 1) == 151.4
    q = math.log(10) / 400                              # Glicko-1's own formulas, on its own scale
    gg = [1 / math.sqrt(1 + 3 * q * q * rd * rd / math.pi ** 2) for rd in (30, 100, 300)]
    ee = [1 / (1 + 10 ** (-gj * (1500 - rj) / 400)) for gj, rj in zip(gg, (1400, 1550, 1700))]
    d2 = 1 / (q * q * sum(gj * gj * e * (1 - e) for gj, e in zip(gg, ee)))
    r1 = 1500 + q / (1 / 200 ** 2 + 1 / d2) * sum(gj * (s - e) for gj, e, s in zip(gg, ee, (1, 0, 0)))
    rd1 = math.sqrt(1 / (1 / 200 ** 2 + 1 / d2))
    # equal up to Glickman's rounded scale constant (173.7178 against 400 / ln 10 = 173.71779...)
    assert 1500 + R.SCALE * mu2 == pytest.approx(r1, abs=1e-4)
    assert R.SCALE * phi2 == pytest.approx(rd1, abs=1e-4)


def test_volatility_iteration_finds_the_root_of_its_equation():
    """ln(sigma'^2) is the root of Glickman's f(x) to the iteration's tolerance (1e-6 on x), against a root found by
    Brent's method to 1e-14, for a range of inputs."""
    from scipy.optimize import brentq
    rng = np.random.default_rng(1)
    for _ in range(300):
        phi, sigma, v = rng.uniform(0.05, 2.0), rng.uniform(0.01, 0.2), rng.uniform(0.2, 20.0)
        delta, tau = rng.normal(0.0, 2.0), rng.uniform(0.1, 1.5)
        a = math.log(sigma * sigma)

        def f(x):
            ex = math.exp(x)
            return ex * (delta ** 2 - phi ** 2 - v - ex) / (2 * (phi ** 2 + v + ex) ** 2) - (x - a) / tau ** 2
        root = brentq(f, a - 60.0, a + 60.0, xtol=1e-14)
        assert math.log(R.volatility(phi, sigma, delta, v, tau) ** 2) == pytest.approx(root, abs=2e-6)
        assert R.volatility_k(phi, sigma, delta, v, tau, 1.0) == R.volatility(phi, sigma, delta, v, tau)
        k = rng.uniform(0.2, 30.0)                      # the time-scaled drift: the root of the generalised f

        def fk(x):
            ex = k * math.exp(x)
            return ex * (delta ** 2 - phi ** 2 - v - ex) / (2 * (phi ** 2 + v + ex) ** 2) - (x - a) / tau ** 2
        root_k = brentq(fk, a - 60.0, a + 60.0, xtol=1e-14)
        assert math.log(R.volatility_k(phi, sigma, delta, v, tau, k) ** 2) == pytest.approx(root_k, abs=2e-6)
    assert R.volatility_k(0.5, 0.06, 1.0, 2.0, 0.5, 0.0) == 0.06


@pytest.mark.parametrize("mu_w,s2_w,mu_l,s2_l", [(0.0, 4.0, 0.0, 4.0), (1.5, 0.3, -0.4, 2.5), (-2.0, 1.0, 2.5, 0.2),
                                                 (0.3, 0.05, 0.1, 0.07), (-6.0, 1.5, 3.0, 1.5)])
def test_trueskill_update_is_the_exact_posteriors_moments(mu_w, s2_w, mu_l, s2_l):
    """Given perf_w > perf_l, the winner's skill has density N(x; mu_w, s2_w) cdf((x - mu_l) / sqrt(s2_l + 2 beta^2)):
    its mean and variance, by quadrature, are TrueSkill's update (moment matching is exact for one comparison)."""
    (mw, sw), (ml, sl) = R.trueskill_rate_1v1(mu_w, s2_w, mu_l, s2_l, beta=1.0)
    from scipy.stats import norm
    for m0, s0, other_m, other_s, sign, (m1, s1) in ((mu_w, s2_w, mu_l, s2_l, 1, (mw, sw)),
                                                     (mu_l, s2_l, mu_w, s2_w, -1, (ml, sl))):
        x = np.linspace(m0 - 12 * math.sqrt(s0), m0 + 12 * math.sqrt(s0), 400_001)
        dens = norm.pdf(x, m0, math.sqrt(s0)) * norm.cdf(sign * (x - other_m) / math.sqrt(other_s + 2.0))
        z = np.trapezoid(dens, x)
        mean = np.trapezoid(x * dens, x) / z
        var = np.trapezoid((x - mean) ** 2 * dens, x) / z
        assert mean == pytest.approx(m1, abs=1e-7)
        assert var == pytest.approx(s1, rel=1e-6)


def test_trueskill_known_numbers_and_probability():
    """Default TrueSkill (mu 25, sigma 25/3, beta 25/6, tau 25/300), no draw margin: equal players, the winner goes to
    29.205 / 7.195 (by hand: c^2 = 173.625, v(0) = 0.79788, w(0) = 0.63662); and the forecast is symmetric."""
    s2 = (25 / 3) ** 2 + (25 / 300) ** 2
    scale = 25 / 6
    (mw, sw), (ml, sl) = R.trueskill_rate_1v1(25 / scale, s2 / scale ** 2, 25 / scale, s2 / scale ** 2, beta=1.0)
    assert mw * scale == pytest.approx(29.205, abs=1e-3)
    assert math.sqrt(sw) * scale == pytest.approx(7.195, abs=1e-3)
    assert ml * scale == pytest.approx(20.795, abs=1e-3)
    p = R.p_trueskill([1.0, -0.5], [0.2, 0.4], [0.5, 2.0], [1.0, 0.1])
    q = R.p_trueskill([0.2, 0.4], [1.0, -0.5], [1.0, 0.1], [0.5, 2.0])
    assert np.allclose(p + q, 1.0)
    pg = R.p_glicko([0.3, -1.0], [0.0, 0.5], [0.2, 1.5], [0.6, 0.4])
    qg = R.p_glicko([0.0, 0.5], [0.3, -1.0], [0.6, 0.4], [0.2, 1.5])
    assert np.allclose(pg + qg, 1.0)


# ------------------------------------------------------------------------------------------------
# The time rule

def hand_made() -> pd.DataFrame:
    return history([
        ("a1", "E1", "2024-01-08", "R32", "P", "X"),     # week 1: P wins R32, loses R16
        ("a2", "E1", "2024-01-08", "R16", "X", "P"),
        ("b1", "E2", "2024-01-15", "Q1", "P", "Y"),      # week 2: P qualifies and plays the main draw
        ("b2", "E2", "2024-01-15", "Q2", "P", "Z"),
        ("b3", "E2", "2024-01-15", "R32", "Q", "P"),
        ("c1", "E3", "2024-01-15", "R32", "P", "Q"),     # week 2, another event: never visible to E2
        ("d1", "F", "2024-01-22", "RR", "P", "Q"),       # week 3: a round robin and a semi-final
        ("d2", "F", "2024-01-22", "RR", "Q", "P"),
        ("d3", "F", "2024-01-22", "RR", "P", "X"),
        ("d4", "F", "2024-01-22", "SF", "P", "Y"),
        ("e1", "G", "2024-01-29", "R32", "P", "Z", "walkover"),   # week 4: a walkover, then a retirement win
        ("e2", "G", "2024-01-29", "R16", "P", "X", "retired"),
        ("f1", "H", "2024-02-05", "R32", "P", "Y"),
    ])


def p_side(m: pd.DataFrame, out: np.ndarray, col: int) -> dict:
    """P's value of an output column (0: mean, 2: uncertainty, 6: count) at each of P's matches, by match id."""
    side_a = m["player_a_id"].eq("P").to_numpy()
    vals = np.where(side_a, out[:, col], out[:, col + 1])
    return {k: v for k, v, pa, pb in zip(m["match_id"], vals, m["player_a_id"], m["player_b_id"]) if "P" in (pa, pb)}


@pytest.mark.parametrize("system", list(CFG))
def test_hand_made_history_follows_the_rule(system):
    m = hand_made()
    out = run(m, system)["overall"]
    mu, u, n = p_side(m, out, 0), p_side(m, out, 2), p_side(m, out, 6)
    assert mu["a1"] == 0.0 and n["a1"] == 0
    assert mu["c1"] == mu["b1"] and u["c1"] == u["b1"]          # another event of week 2 sees only week 1
    assert mu["b2"] > mu["b1"] and mu["b3"] > mu["b2"]          # qualifying wins count before the main draw
    assert mu["d1"] == mu["d2"] == mu["d3"]                     # the round robin's matches never see each other
    assert u["d1"] == u["d2"] == u["d3"]
    assert mu["d4"] != mu["d1"]                                 # the semi-final sees the round robin
    assert mu["e2"] == mu["e1"] and n["e2"] == n["e1"]          # the walkover moved nothing
    assert mu["f1"] > mu["e2"] and n["f1"] == n["e2"] + 1       # the retirement win counted
    assert n == {"a1": 0, "a2": 1, "b1": 2, "b2": 3, "b3": 4, "c1": 2, "d1": 6, "d2": 6, "d3": 6, "d4": 9,
                 "e1": 10, "e2": 10, "f1": 11}


def visible_then(m: pd.DataFrame, i: int) -> pd.DataFrame:
    """The matches the rule lets match i see (earlier weeks; earlier rounds of its event), then match i itself."""
    r = m.iloc[i]
    seen = (m["tournament_date"] < r["tournament_date"]) | (
        m["tournament_date"].eq(r["tournament_date"]) & m["tournament_id"].eq(r["tournament_id"])
        & (m["round_order"] < r["round_order"]))
    return pd.concat([m[seen], m.iloc[[i]]], ignore_index=True)


@pytest.mark.parametrize("system", list(CFG))
@pytest.mark.parametrize("seed", [11, 12])
def test_every_value_equals_a_fresh_pass_over_what_the_rule_lets_it_see(system, seed):
    m = random_history(seed=seed)
    full = run(m, system)
    rng = np.random.default_rng(seed)
    for i in rng.choice(len(m), size=45, replace=False):
        sub = run(visible_then(m, i), system)
        for comp in full:
            got, want = full[comp][i], sub[comp][-1]
            assert np.allclose(got, want, rtol=0, atol=1e-12, equal_nan=True), (system, comp, m.iloc[i]["match_id"])


@pytest.mark.parametrize("system", [s for s in CFG if not s.endswith("_cs")])
def test_surface_component_moves_only_on_its_surface(system):
    m = history([("a", "E1", "2024-01-01", "F", "P", "Q"), ("b", "E2", "2024-01-08", "F", "P", "Q"),
                 ("c", "E3", "2024-01-15", "F", "P", "Q")], surfaces={"E1": "Clay", "E2": "Grass", "E3": None})
    res = run(m, system)
    s = res["surface"]
    assert s[1, 0] == 0.0 and s[1, 1] == 0.0 and s[1, 6] == 0       # grass untouched by clay
    assert np.isnan(s[2]).all()                                      # unknown surface: no surface value
    assert res["overall"][2, 6] == 2
    p = R.blend(system, res, 0.4)
    assert p[2] == pytest.approx(R.blend(system, res, 0.0)[2])       # overall alone where the surface is unknown


# ------------------------------------------------------------------------------------------------
# The passes are the plain algorithms where nothing is simultaneous

def one_match_a_week(seed=5, weeks=40, players=10):
    rng = np.random.default_rng(seed)
    rows, date = [], pd.Timestamp("2023-01-02")
    for wk in range(weeks):
        date = date + pd.Timedelta(days=7 * int(rng.integers(1, 3)))
        a, b = rng.choice(players, size=2, replace=False)
        w, l = (f"p{a}", f"p{b}") if rng.random() < 0.6 else (f"p{b}", f"p{a}")
        rows.append((f"m{wk}", f"E{wk}", date, "F", w, l))
    return history(rows)


def test_glicko_is_plain_glicko2_with_one_game_per_period():
    m = one_match_a_week()
    cfg = CFG["glicko2"]
    out = run(m, "glicko2", cfg)["overall"]
    phi0 = cfg["rd0"] / R.SCALE
    st, last = {}, {}
    for i, r in m.iterrows():
        D = r["tournament_date"]
        pre = {}
        for p in (r["player_a_id"], r["player_b_id"]):
            mu, phi, sig = st.get(p, (0.0, phi0, cfg["sigma0"]))
            if p in last:                                    # empty weekly periods: phi^2 + sigma^2 each
                k = (D - last[p]).days / 7 - 1
                phi = min(math.sqrt(phi * phi + max(k, 0) * sig * sig), phi0)
            pre[p] = (mu, phi, sig)
        a, b = r["player_a_id"], r["player_b_id"]
        for col, p in ((0, a), (1, b)):
            assert out[i, col] == pytest.approx(pre[p][0], abs=1e-12)
            assert out[i, 2 + col] == pytest.approx(math.sqrt(pre[p][1] ** 2 + pre[p][2] ** 2), abs=1e-12)
        s = 1.0 if r["a_won"] else 0.0
        st[a] = R.glicko2_rate(*pre[a], [(pre[b][0], pre[b][1], s)], tau=cfg["tau"])
        st[b] = R.glicko2_rate(*pre[b], [(pre[a][0], pre[a][1], 1 - s)], tau=cfg["tau"])
        last[a] = last[b] = D


def test_match_by_match_glicko_is_plain_sequential_glicko2_with_time_drift():
    m = one_match_a_week(seed=6)
    cfg = CFG["glicko2m"]
    out = run(m, "glicko2m", cfg)["overall"]
    phi0 = cfg["rd0"] / R.SCALE
    st, last = {}, {}
    for i, r in m.iterrows():
        D = r["tournament_date"]
        pre = {}
        for p in (r["player_a_id"], r["player_b_id"]):
            mu, phi, sig = st.get(p, (0.0, phi0, cfg["sigma0"]))
            k = (D - last[p]).days / 7 if p in last else 0.0
            pre[p] = (mu, phi, sig, k, min(math.sqrt(phi * phi + k * sig * sig), phi0))
        a, b = r["player_a_id"], r["player_b_id"]
        for col, p in ((0, a), (1, b)):
            assert out[i, col] == pytest.approx(pre[p][0], abs=1e-12)
            assert out[i, 2 + col] == pytest.approx(pre[p][4], abs=1e-12)
        s = 1.0 if r["a_won"] else 0.0
        for p, q, sp in ((a, b, s), (b, a, 1 - s)):
            gq = R.g(pre[q][4])
            e = R.expected(pre[p][0], pre[q][0], pre[q][4])
            st[p] = R.glicko2_update_k(pre[p][0], pre[p][1], pre[p][2], gq * gq * e * (1 - e), gq * (sp - e),
                                       cfg["tau"], True, pre[p][3], phi0)
        last[a] = last[b] = D


def test_trueskill_is_plain_sequential_trueskill_with_one_match_per_week():
    m = one_match_a_week(seed=8)
    cfg = CFG["trueskill"]
    out = run(m, "trueskill", cfg)["overall"]
    st, last = {}, {}
    for i, r in m.iterrows():
        D = r["tournament_date"]
        pre = {}
        for p in (r["player_a_id"], r["player_b_id"]):
            mu, s2 = st.get(p, (0.0, cfg["sigma0"] ** 2))
            if p in last:
                s2 = min(s2 + cfg["gamma"] ** 2 * (D - last[p]).days / 365.25, cfg["sigma0"] ** 2)
            pre[p] = (mu, s2 + cfg["tau"] ** 2)
        a, b = r["player_a_id"], r["player_b_id"]
        assert out[i, 0] == pytest.approx(pre[a][0], abs=1e-12) and out[i, 2] == pytest.approx(pre[a][1], abs=1e-12)
        assert out[i, 1] == pytest.approx(pre[b][0], abs=1e-12) and out[i, 3] == pytest.approx(pre[b][1], abs=1e-12)
        w, l = (a, b) if r["a_won"] else (b, a)
        st[w], st[l] = R.trueskill_rate_1v1(*pre[w], *pre[l])
        last[a] = last[b] = D


def test_two_events_of_one_week_combine_as_the_formulas_say():
    """P plays two events in week 2 (one match each); week 3 sees: Glicko, one period over both games; TrueSkill, the
    start of week 2 plus both events' changes in natural parameters."""
    m = history([("a", "E1", "2024-01-01", "F", "P", "Q"), ("b", "E2", "2024-01-08", "F", "P", "X"),
                 ("c", "E3", "2024-01-08", "F", "Y", "P"), ("d", "E4", "2024-01-15", "F", "P", "Q")])
    cfg = CFG["glicko2"]
    out = run(m, "glicko2", cfg)["overall"]
    pv = {k: v for k, v in zip(m["match_id"], m["player_a_id"].eq("P"))}
    row = {k: i for i, k in enumerate(m["match_id"])}

    def val(mid, col):
        i = row[mid]
        return out[i, col] if pv[mid] else out[i, col + 1]

    def opp(mid, col):
        i = row[mid]
        return out[i, col + 1] if pv[mid] else out[i, col]
    phi0 = cfg["rd0"] / R.SCALE
    p1 = R.glicko2_rate(0.0, phi0, cfg["sigma0"], [(0.0, phi0, 1.0)], tau=cfg["tau"])            # week 1
    q1 = R.glicko2_rate(0.0, phi0, cfg["sigma0"], [(0.0, phi0, 0.0)], tau=cfg["tau"])
    assert val("b", 0) == pytest.approx(p1[0]) and val("c", 0) == pytest.approx(p1[0])
    p2 = R.glicko2_rate(*p1, [(0.0, phi0, 1.0), (0.0, phi0, 0.0)], tau=cfg["tau"])                 # one period, two games
    assert val("d", 0) == pytest.approx(p2[0], abs=1e-12)
    assert val("d", 2) == pytest.approx(math.sqrt(p2[1] ** 2 + p2[2] ** 2), abs=1e-12)
    assert opp("d", 0) == pytest.approx(q1[0], abs=1e-12)
    cfg = CFG["trueskill"]
    out = run(m, "trueskill", cfg)["overall"]
    s0, t2 = cfg["sigma0"] ** 2, cfg["tau"] ** 2
    pw, _ = R.trueskill_rate_1v1(0.0, s0 + t2, 0.0, s0 + t2)                                     # week 1: P beats Q
    s2w = min(pw[1] + cfg["gamma"] ** 2 * 7 / 365.25, s0)                                       # P at week 2's start
    start = (pw[0], s2w)
    (e2, _) = R.trueskill_rate_1v1(start[0], start[1] + t2, 0.0, s0 + t2)                         # beats X
    (_, e3) = R.trueskill_rate_1v1(0.0, s0 + t2, start[0], start[1] + t2)                         # loses to Y
    prec = 1 / start[1] + (1 / e2[1] - 1 / start[1]) + (1 / e3[1] - 1 / start[1])
    pm = start[0] / start[1] + (e2[0] / e2[1] - start[0] / start[1]) + (e3[0] / e3[1] - start[0] / start[1])
    mu3, s23 = pm / prec, min(1 / prec + cfg["gamma"] ** 2 * 7 / 365.25, s0)
    assert val("d", 0) == pytest.approx(mu3, abs=1e-12)
    assert val("d", 2) == pytest.approx(s23 + t2, abs=1e-12)


# ------------------------------------------------------------------------------------------------
# TrueSkill Through Time

def test_ttt_reproduces_landfried_and_mocskos_published_example():
    """J. Stat. Software 112(6), the one-on-one example (mu 0, sigma 6, beta 1, gamma 0): a beats b, b beats a new player
    c, c beats a. Filtering gives a N(3.339, 4.985), then b N(0.059, 4.218), then a N(-2.688, 3.779); after TTT has
    converged every skill is N(0, 2.395)."""
    model = R.TTT(3, sigma0=6.0, gamma=0.0, beta=1.0)
    a, b, c = 0, 1, 2
    model.add_batch(0.0, [(a, b)], batch_iters=1)
    mu, s2 = model.posterior(model.last[a])
    assert (mu, math.sqrt(s2)) == (pytest.approx(3.339, abs=1e-3), pytest.approx(4.985, abs=1e-3))
    model.add_batch(1.0, [(b, c)], batch_iters=1)
    mu, s2 = model.posterior(model.last[b])
    assert (mu, math.sqrt(s2)) == (pytest.approx(0.059, abs=1e-3), pytest.approx(4.218, abs=1e-3))
    model.add_batch(2.0, [(c, a)], batch_iters=1)
    mu, s2 = model.posterior(model.last[a])
    assert (mu, math.sqrt(s2)) == (pytest.approx(-2.688, abs=1e-3), pytest.approx(3.779, abs=1e-3))
    for _ in range(200):
        model.smooth(window=3)
    for nd in range(len(model.key)):
        mu, s2 = model.posterior(nd)
        assert mu == pytest.approx(0.0, abs=1e-3) and math.sqrt(s2) == pytest.approx(2.395, abs=1e-3)


def test_ttt_hold_keeps_a_fortnight_event_out_until_two_weeks_after_its_start():
    """A Grand Slam (it has a round of 128) dated week 1; an event in week 2 and one in week 3. Plain TTT sees the
    Slam in week 2; with the hold a Slam player's week-2 rating is still their pre-Slam one, and week 3 sees the Slam.
    Events without a round of 128 are never held."""
    m = history([("s1", "GS", "2024-01-15", "R128", "P", "Q"), ("s2", "GS", "2024-01-15", "R64", "P", "X"),
                 ("c1", "CH", "2024-01-22", "R32", "Q", "Y"), ("d1", "CH2", "2024-01-29", "R32", "P", "Z"),
                 ("e1", "E", "2024-02-05", "R32", "Y", "Z")])
    h = RC.history(m)
    assert h["fortnight"] == [True, True, False, False, False]
    cfg = {"sigma0": 2.0, "gamma": 0.4, "window": 4}
    plain, held = R.run(h, "ttt", cfg)["overall"], R.run(h, "ttt_hold", cfg)["overall"]
    q_c1 = {r: (o[2, 0] if m.iloc[2]["player_a_id"] == "Q" else o[2, 1]) for r, o in (("plain", plain), ("held", held))}
    assert q_c1["plain"] < 0.0                      # Q lost to P at the Slam: plain TTT knows it in week 2
    assert q_c1["held"] == 0.0                      # with the hold, Q is still a newcomer in week 2
    p_d1 = held[3, 0] if m.iloc[3]["player_a_id"] == "P" else held[3, 1]
    assert p_d1 > 0.0                               # week 3 sees the Slam


def test_ttt_credits_an_old_win_at_what_the_opponent_turned_out_to_be_worth():
    """P beats Q; later Q beats many strong players. With smoothing P's estimate rises after Q's later wins; without the
    window covering the old batch it does not."""
    def run_model(window):
        model = R.TTT(10, sigma0=2.0, gamma=0.3)
        model.add_batch(0.0, [(0, 1)])
        p0 = model.latest(0, 7.0)[0]
        for wk in range(1, 6):
            model.add_batch(7.0 * wk, [(1, 1 + wk), (1, 6 + min(wk, 3))])
            model.smooth(window=window)
        return p0, model.latest(0, 42.0)[0]
    p0, smoothed = run_model(window=10)
    _, frozen = run_model(window=1)
    assert smoothed > p0 + 0.05
    assert frozen == pytest.approx(p0, abs=1e-12)


# ------------------------------------------------------------------------------------------------
# Correlated surface skills

def run_cs(m: pd.DataFrame, link: str, sigma0: float, gamma: float, rho: float) -> np.ndarray:
    h = RC.history(m)
    return R.correlated_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["surf"], h["a_won"], h["upd"],
                             h["n_players"], sigma0=sigma0, gamma=gamma, rho=rho, link=link)


@pytest.mark.parametrize("seed", [4, 9])
def test_correlated_with_rho_one_is_the_overall_trueskill(seed):
    """rho = 1: one skill for every surface, i.e. TrueSkill (tau 0) on the overall rating, unknown surfaces included."""
    m = random_history(seed=seed)
    cs = run_cs(m, "probit", sigma0=2.0, gamma=0.5, rho=1.0)
    ts = run(m, "trueskill", {"sigma0": 2.0, "tau": 0.0, "gamma": 0.5})["overall"]
    assert np.allclose(cs[:, [0, 1, 2, 3, 6, 7]], ts[:, [0, 1, 2, 3, 6, 7]], rtol=0, atol=1e-10)


@pytest.mark.parametrize("seed", [4, 9])
def test_correlated_logit_with_rho_one_is_match_by_match_glicko1(seed):
    """rho = 1 with the logit link is Glicko-1 match by match, with sigma^2 per week = gamma^2 x 7 / 365.25."""
    m = random_history(seed=seed)
    rd0, sig = 450.0, 0.07
    cs = run_cs(m, "logit", sigma0=rd0 / R.SCALE, gamma=sig * math.sqrt(365.25 / 7), rho=1.0)
    gl = run(m, "glicko1m", {"rd0": rd0, "sigma0": sig})["overall"]
    assert np.allclose(cs[:, [0, 1, 2, 3, 6, 7]], gl[:, [0, 1, 2, 3, 6, 7]], rtol=0, atol=1e-10)


@pytest.mark.parametrize("link", ["probit", "logit"])
def test_a_result_on_one_surface_moves_the_others_through_the_correlation(link):
    """Two newcomers on clay: the winner's hard, grass and carpet skills move by rho times the clay move (the prior
    covariance is sigma0^2 C); with rho = 0 they do not move; the surfaces' variances shrink by rho^2 times as much."""
    m = history([("a", "E1", "2024-01-01", "F", "P", "Q"), ("b", "E2", "2024-01-08", "F", "P", "X"),
                 ("c", "E3", "2024-01-15", "F", "P", "Y")], surfaces={"E1": "Clay", "E2": "Hard", "E3": "Grass"})
    h = RC.history(m)
    clay, hard = 1, 0
    assert h["surf"][0] == clay and h["surf"][1] == hard
    s2 = 1.5 ** 2
    if link == "probit":                                  # the clay win's move, by hand, from the prior
        (move, post), _ = R.trueskill_rate_1v1(0.0, s2, 0.0, s2)
    else:
        gq = R.g(math.sqrt(s2))
        post = 1 / (1 / s2 + gq * gq * 0.25)
        move = gq * 0.5 * post
    for rho in (0.0, 0.6, 0.9):
        out = run_cs(m, link, sigma0=1.5, gamma=0.0, rho=rho)
        side = 0 if m.iloc[1]["player_a_id"] == "P" else 1         # P's pre-match values at match b (hard)
        assert out[1, side] == pytest.approx(rho * move, abs=1e-12)
        var_hard = out[1, 2 + side] if link == "probit" else out[1, 2 + side] ** 2
        assert var_hard == pytest.approx(s2 - rho ** 2 * (s2 - post), abs=1e-12)


# ------------------------------------------------------------------------------------------------
# The probe cut by date, event and round

@pytest.mark.parametrize("system", list(CFG))
def test_probe_passes_the_pass_and_catches_a_leaky_one(system):
    m = random_history(seed=21, weeks=12)
    h = RC.history(m)

    def ratings(hh):
        res = R.run(hh, system, CFG[system])
        return np.concatenate([res[c] for c in ("overall", "surface") if c in res], axis=1)

    def leaky(hh):                    # every row its own round of one event per week: it sees the week's earlier rows
        hh = {**hh, "event": [0] * len(hh["week"]), "rnd": list(range(len(hh["week"])))}
        return ratings(hh)
    ok = B.probe_by_round(h, ratings, n_cuts=8, seed=5, from_quantile=0.3)
    assert ok["protected_matches_changed"] == 0 and ok["later_matches_changed"] > 0
    bad = B.probe_by_round(h, leaky, n_cuts=8, seed=5, from_quantile=0.3)
    assert bad["protected_matches_changed"] > 0
