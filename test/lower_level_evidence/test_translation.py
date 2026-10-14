"""Tests of the level-translation analysis (src/eda/lower_level_evidence/translation.py): synthetic data with a planted
level offset (delta) and exchange rate (lambda) that the code must recover, the solvers against direct solutions, the
leak-proof timeline, the history window and the holdout guard.

Run: ./python.sh -m pytest test/lower_level_evidence/test_translation.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as C  # noqa: E402
from src.eda.lower_level_evidence import translation as T  # noqa: E402


# ------------------------------------------------------------------------------------------------
# The batch fit with level effects

def _planted_system(seed=0, n=400, rows=60_000, deltas=(0.25, -0.15), noise=0.3):
    """Players with true O, D; matches at MAIN (col -1) and two lower levels (cols 0, 1) with planted effects. Weaker
    players play the lower levels more often (so a raw comparison is confounded), and everyone plays some MAIN."""
    rng = np.random.default_rng(seed)
    O, D = rng.normal(0, 0.3, n), rng.normal(0, 0.3, n)
    strength = O + D
    p_low = expit(-3 * strength)                          # weaker -> more lower-level matches
    srv = rng.integers(0, n, rows)
    ret = (srv + rng.integers(1, n, rows)) % n
    low = rng.random(rows) < (p_low[srv] + p_low[ret]) / 2
    col = np.where(low, rng.integers(0, len(deltas), rows), -1)
    eff = np.where(col >= 0, np.asarray(deltas)[np.maximum(col, 0)], 0.0)
    y = O[srv] - D[ret] + eff + rng.normal(0, noise, rows)
    return srv, ret, y, np.ones(rows), col, n


def test_batch_fe_recovers_planted_level_effects():
    srv, ret, y, w, col, n = _planted_system()
    res = T.batch_fe(srv, ret, y, w, col, n, 2, kappa=0.1, cluster=np.arange(len(y)) // 50)
    assert res["converged"]
    assert res["delta"] == pytest.approx([0.25, -0.15], abs=0.02)
    assert np.all(res["se"] > 0) and np.all(res["se"] < 0.02)


def test_batch_fe_equals_a_direct_dense_solve():
    srv, ret, y, w, col, n = _planted_system(seed=1, n=30, rows=2_000)
    w = np.random.default_rng(2).uniform(0.5, 2.0, len(y))
    kappa = 0.7
    res = T.batch_fe(srv, ret, y, w, col, n, 2, kappa=kappa)
    X = np.zeros((len(y), 2 * n + 2))
    X[np.arange(len(y)), srv] = 1.0
    X[np.arange(len(y)), n + ret] = -1.0
    has = col >= 0
    X[np.flatnonzero(has), 2 * n + col[has]] = 1.0
    pen = np.r_[np.full(2 * n, kappa), np.full(2, 1e-6)]
    beta = np.linalg.solve(X.T @ (X * w[:, None]) + np.diag(pen), X.T @ (w * y))
    assert res["O"] == pytest.approx(beta[:n], abs=1e-6)
    assert res["D"] == pytest.approx(beta[n:2 * n], abs=1e-6)
    assert res["delta"] == pytest.approx(beta[2 * n:], abs=1e-6)


def test_batch_fe_without_effects_is_the_plain_ridge():
    srv, ret, y, w, col, n = _planted_system(seed=3, n=30, rows=1_500)
    res = T.batch_fe(srv, ret, y, w, np.full(len(y), -1), n, 0, kappa=1.0)
    X = np.zeros((len(y), 2 * n))
    X[np.arange(len(y)), srv] = 1.0
    X[np.arange(len(y)), n + ret] = -1.0
    beta = np.linalg.solve(X.T @ X + np.eye(2 * n), X.T @ y)
    assert np.r_[res["O"], res["D"]] == pytest.approx(beta, abs=1e-6)


# ------------------------------------------------------------------------------------------------
# The weekly leak-proof solve

def _timeline(seed=4, n=60, rows=6_000):
    rng = np.random.default_rng(seed)
    O, D = rng.normal(0, 0.3, n), rng.normal(0, 0.3, n)
    srv = rng.integers(0, n, rows)
    ret = (srv + rng.integers(1, n, rows)) % n
    es = T.ANCHOR + rng.integers(0, 700, rows).astype(float)
    lf = es + rng.integers(0, 10, rows)
    lev = np.where(rng.random(rows) < 0.4, T.LEV_CODE["CH"], 0)
    y = O[srv] - D[ret] + np.where(lev > 0, 0.2, 0.0) + rng.normal(0, 0.3, rows)
    return {"srv": srv, "ret": ret, "n": n, "y": y, "w0": np.ones(rows), "obs": (es + lf) / 2, "release": lf + 1,
            "query": es, "lev": lev}


def test_weekly_solve_never_reads_a_result_that_could_not_precede_the_match():
    sd = _timeline()
    zero, one = np.zeros(len(T.LEVELS)), np.ones(len(T.LEVELS))
    base, _ = T.weekly_solve(sd, 26.0, 1.0, zero, one)
    cut = T.ANCHOR + 350
    flipped = dict(sd)
    later = sd["release"] > cut                      # results that exist only after the cut day
    flipped["y"] = np.where(later, -sd["y"] + 3.0, sd["y"])
    got, _ = T.weekly_solve(flipped, 26.0, 1.0, zero, one)
    early = sd["query"] <= cut                        # matches that may start by the cut day
    assert np.allclose(got["O"][early], base["O"][early], equal_nan=True)
    assert np.allclose(got["D"][early], base["D"][early], equal_nan=True)
    assert not np.allclose(got["O"][~early], base["O"][~early], equal_nan=True)
    # a row is never in the solve its own match reads
    assert np.all(sd["release"] > sd["query"])
    assert np.all(base["snap"][np.isfinite(base["snap"])] <= sd["query"][np.isfinite(base["snap"])])


def test_weekly_solve_at_the_end_equals_the_batch_ridge_without_decay():
    sd = _timeline(seed=5)
    last = sd["release"].max() + 7
    sd["query"] = np.r_[sd["query"][:-1], last]       # one match after every release reads the full solve
    zero, one = np.zeros(len(T.LEVELS)), np.ones(len(T.LEVELS))
    got, _ = T.weekly_solve(sd, np.inf, 2.0, zero, one, rtol=1e-12)
    res = T.batch_fe(sd["srv"], sd["ret"], sd["y"], sd["w0"], np.full(len(sd["y"]), -1), sd["n"], 0, kappa=2.0,
                     rtol=1e-12)
    assert got["O"][-1] == pytest.approx(res["O"][sd["srv"][-1]], abs=1e-8)
    assert got["D"][-1] == pytest.approx(res["D"][sd["ret"][-1]], abs=1e-8)


def test_translation_and_discount_arms_change_only_the_lower_rows():
    sd = _timeline(seed=6)
    zero, one = np.zeros(len(T.LEVELS)), np.ones(len(T.LEVELS))
    shift = zero.copy()
    shift[T.LEV_CODE["CH"]] = 0.2
    a, _ = T.weekly_solve(sd, np.inf, 1.0, zero, one)
    b, _ = T.weekly_solve(sd, np.inf, 1.0, shift, one)
    # translating the planted +0.2 removes the level offset from the ratings: main-tour residuals shrink
    main = (sd["lev"] == 0) & np.isfinite(a["O"])
    ra = sd["y"][main] - (a["O"][main] - a["D"][main])
    rb = sd["y"][main] - (b["O"][main] - b["D"][main])
    assert abs(rb.mean()) < abs(ra.mean())
    w = one.copy()
    w[1:] = 0.0
    c, st = T.weekly_solve(sd, np.inf, 1.0, zero, w)
    assert st["rows_in_solve"] == int((sd["lev"] == 0).sum())


def test_tier_prior_gives_a_player_without_evidence_his_tiers_mean():
    sd = _timeline(seed=12)
    sd["tier_srv"] = np.full(len(sd["y"]), T.TIER_CODES["CH"])
    sd["tier_ret"] = np.full(len(sd["y"]), T.TIER_CODES["CH"])
    zero, one = np.zeros(len(T.LEVELS)), np.ones(len(T.LEVELS))
    mO, mD = np.zeros(len(T.TIER_CODES)), np.zeros(len(T.TIER_CODES))
    mO[T.TIER_CODES["CH"]], mD[T.TIER_CODES["CH"]] = -0.4, -0.2
    got, _ = T.weekly_solve(sd, np.inf, 1.0, zero, one, prior=(mO, mD), rtol=1e-12)
    none_o = got["P"] == 0
    none_d = got["Q"] == 0
    assert none_o.any() and none_d.any()
    assert got["O"][none_o] == pytest.approx(-0.4, abs=1e-8)
    assert got["D"][none_d] == pytest.approx(-0.2, abs=1e-8)
    base, _ = T.weekly_solve(sd, np.inf, 1.0, zero, one)
    assert base["O"][none_o] == pytest.approx(0.0, abs=1e-8)


# ------------------------------------------------------------------------------------------------
# The credibility estimator: planted delta and lambda

def _planted_credibility(seed=7, n=150_000, mu=0.62, k=150.0, delta=0.03, lam=2.5):
    rng = np.random.default_rng(seed)
    var = mu * (1 - mu)
    theta = rng.normal(mu, np.sqrt(var / k), n)
    NM = rng.uniform(0, 600, n).round()
    NL = rng.uniform(0, 1200, n).round()
    xm = theta + rng.normal(0, 1, n) * np.sqrt(var / np.maximum(NM, 1))
    xl = theta + delta + rng.normal(0, 1, n) * np.sqrt(lam * var / np.maximum(NL, 1))
    d = np.full(n, 80.0)
    x = rng.binomial(80, np.clip(theta, 0.01, 0.99)).astype(float)
    return {"x": x, "d": d, "mu": np.full(n, mu), "X_MAIN": xm * NM, "N_MAIN": NM, "X_CH": xl * NL, "N_CH": NL,
            "player": np.arange(n), "lowexp": np.zeros(n, bool)}


def test_credibility_recovers_planted_delta_and_lambda():
    D = _planted_credibility()
    par = T.cred_fit(D, ["CH"], "translated_discounted")
    assert par["converged"]
    assert par["delta"]["CH"] == pytest.approx(0.03, abs=0.006)
    assert 1.0 / par["w"]["CH"] == pytest.approx(2.5, rel=0.25)
    assert par["k"] == pytest.approx(150.0, rel=0.35)


def test_credibility_arms_rank_as_planted():
    D = _planted_credibility(seed=8, n=60_000)
    lls = {}
    for arm in T.CRED_ARMS:
        par = T.cred_fit(D, ["CH"], arm)
        lls[arm] = par["ll_per_unit"]
    # translated + discounted is the true model: best; pooling an offset level as equivalent is worst
    assert lls["translated_discounted"] <= min(lls.values()) + 1e-9
    assert lls["pooled"] > lls["translated"] > lls["translated_discounted"]
    assert lls["main_only"] > lls["translated_discounted"]


def test_cred_theta_main_only_ignores_lower_levels_and_pooled_pools():
    D = {"mu": np.array([0.5]), "X_MAIN": np.array([30.0]), "N_MAIN": np.array([50.0]), "X_CH": np.array([80.0]),
         "N_CH": np.array([100.0])}
    mo = T.cred_theta({"k": 0.0, "delta": {}, "w": {}}, D, ["CH"])
    assert mo[0] == pytest.approx(30 / 50)
    pooled = T.cred_theta({"k": 0.0, "delta": {}, "w": {"CH": 1.0}}, D, ["CH"])
    assert pooled[0] == pytest.approx(110 / 150)
    tr = T.cred_theta({"k": 0.0, "delta": {"CH": 0.1}, "w": {"CH": 0.5}}, D, ["CH"])
    assert tr[0] == pytest.approx((30 + 0.5 * (80 - 10)) / (50 + 50))


# ------------------------------------------------------------------------------------------------
# History window, raw gaps, Elo

def _player_rows(seed=9, players=40, events=30):
    """A small synthetic player table in the shape load() returns: two rows per match, Stage 0's order."""
    rng = np.random.default_rng(seed)
    recs = []
    order = 0
    for e in range(events):
        day = T.ANCHOR + 14 * e + 365
        lvl = rng.choice(["MAIN", "CH", "ITF", "TQ"])
        for _ in range(8):
            a, b = rng.choice(players, 2, replace=False)
            for side, pl, op in (("A", a, b), ("B", b, a)):
                recs.append({"match_id": f"m{order}", "side": side, "pcode": pl, "opp": op, "order": order,
                             "day": day, "bucket": lvl, "played": rng.random() > 0.05, "year": 2015 + e // 26})
            order += 1
    return pd.DataFrame(recs)


def test_own_history_counts_the_players_earlier_matches_of_the_window():
    p = _player_rows()
    h = T.own_history(p, window=60)
    rng = np.random.default_rng(10)
    for i in rng.choice(len(p), 200, replace=False):
        r = p.iloc[i]
        g = p[(p["pcode"] == r["pcode"]) & (p["order"] < r["order"]) & (p["day"] >= r["day"] - 60) & p["played"]]
        for t in T.TIERS:
            want = int((g["bucket"].map(T.TIER_OF) == t).sum())
            assert h[f"n_{t}"].iloc[i] == want


def test_raw_gaps_recover_a_planted_shift():
    rng = np.random.default_rng(11)
    recs = []
    mid = 0
    for pl in range(300):
        true = rng.uniform(0.55, 0.7)
        for lvl, shift in (("MAIN", 0.0), ("CH", 0.03)):
            for _ in range(6):
                x = float(rng.binomial(80, true + shift))
                base = {"tour": "atp", "year": 2016, "bucket": lvl, "status": "completed", "format": "standard",
                        "has_box": True, "rank": 100.0}
                recs.append({**base, "pcode": pl, "won": True, **{f"{s}_n": x for s in T.STATS},
                             **{f"{s}_d": 80.0 for s in T.STATS}})
                # the opponent's row (a one-match player, never paired)
                recs.append({**base, "pcode": 100_000 + mid, "won": False, **{f"{s}_n": 80.0 - x for s in T.STATS},
                             **{f"{s}_d": 80.0 for s in T.STATS}})
                mid += 1
    p = pd.DataFrame(recs)
    g = T.raw_gaps(p, years=(2016, 2016))
    row = g[(g["level"] == "CH") & (g["stat"] == "spw")].iloc[0]
    assert row["gap"] == pytest.approx(0.03, abs=0.006)
    assert row["lo"] < 0.03 < row["hi"]


def test_elo_multiplier_zero_freezes_the_ratings():
    a = np.array([0, 0, 0, 1])
    b = np.array([1, 1, 1, 0])
    y = np.array([1.0, 1.0, 1.0, 0.0])
    p1 = T.elo_run(a, b, y, np.array([0.0, 0.0, 0.0, 1.0]))
    assert p1[:4] == pytest.approx([0.5, 0.5, 0.5, 0.5])
    p2 = T.elo_run(a, b, y, np.ones(4))
    assert p2[1] > 0.5 and p2[2] > p2[1]


# ------------------------------------------------------------------------------------------------
# The holdout guard

def _tiny_stage0(tmp_path: Path) -> Path:
    m = pd.DataFrame({
        "match_id": ["a", "b", "c"], "tour": ["atp"] * 3, "year": [2024, 2025, 2025], "map_level": ["T250", "CH", "T250"],
        "surface": ["Hard"] * 3, "status": ["completed"] * 3, "format": ["standard"] * 3, "has_box": [True] * 3,
        "tournament_date": pd.to_datetime(["2024-06-03", "2024-12-23", "2025-01-06"]), "order": [0, 1, 2],
        "tournament_id": ["t1", "t2", "t3"], "a_won": [True, True, False], "player_a_id": ["atp:1", "atp:1", "atp:2"],
        "player_b_id": ["atp:2", "atp:3", "atp:1"]})
    rows = []
    for r in m.itertuples(index=False):
        for side, pl, op, won in (("A", r.player_a_id, r.player_b_id, r.a_won), ("B", r.player_b_id, r.player_a_id,
                                                                                   not r.a_won)):
            rec = {"match_id": r.match_id, "player_id": pl, "opponent_id": op, "side": side, "won": won, "rank": 50.0}
            for s in T.STATS:
                rec[f"{s}_n"], rec[f"{s}_d"] = 40.0, 70.0
            rows.append(rec)
    m.to_parquet(tmp_path / "stage0_matches.parquet")
    pd.DataFrame(rows).to_parquet(tmp_path / "stage0_match_players.parquet")
    return tmp_path


def test_load_never_reads_a_holdout_match(tmp_path):
    d = _tiny_stage0(tmp_path)
    p, info = T.load(d, through=2026, timing=tmp_path / "no_timing.parquet")
    assert set(p["match_id"]) == {"a", "b"}            # c (6 Jan 2025) is the holdout's; b is a 2025-labelled
    assert not C.in_holdout(p["date"]).any()          # event of 23 Dec 2024, before the holdout
    assert info["timing_fallback_rows"] == len(p)
    p, _ = T.load(d, through=2024, timing=tmp_path / "no_timing.parquet")
    assert set(p["match_id"]) == {"a"}


def test_cli_refuses_a_holdout_season(tmp_path):
    with pytest.raises(SystemExit):
        T.main(["--through", "2025", "--out", str(tmp_path), "--steps", "gaps"])


@pytest.mark.parametrize("args", [["--validate", "2019-2026"], ["--tune", "2013-2019"], ["--fit-window", "2010-2020"]])
def test_cli_refuses_windows_that_overlap_or_pass_the_holdout(tmp_path, args):
    defaults = (T.FIT_WINDOW, T.TUNE, T.VALIDATE)
    try:
        with pytest.raises(SystemExit):
            T.main(args + ["--out", str(tmp_path), "--steps", "gaps"])
    finally:
        T.set_windows(*defaults)


# ------------------------------------------------------------------------------------------------
# ITF: its own delta and lambda once box scores exist (a candidate Stage 0)

def test_a_level_with_box_scores_gets_its_own_offset_and_weight():
    n = 2 * T.MIN_ROWS
    p = pd.DataFrame({"bucket": ["MAIN"] * n + ["ITF"] * n + ["ITFQ"] * 10, "box": [True] * (2 * n + 10)})
    present = T.present_levels(p)
    assert "ITF" in present and "ITFQ" not in present          # ITFQ is too thin to get its own delta
    arms = T.arms(present, {"ITF": 0.07})
    shift, weight, _, _ = arms["tr_lam2"]
    assert shift[T.LEV_CODE["ITF"]] == pytest.approx(0.07)
    assert weight[T.LEV_CODE["ITF"]] == pytest.approx(0.5) and weight[T.LEV_CODE["MAIN"]] == 1.0
    assert T.LEV_CODE["ITF"] in T.LOWER_CODES and T.LEV_CODE["ITFQ"] in T.LOWER_CODES
