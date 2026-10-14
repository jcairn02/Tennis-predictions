"""Tests of the relationship estimator (role B, src/eda/lower_level_evidence/relationship.py).

* planted gamma, delta, w and prior are recovered by the predictor's fit;
* the decayed window sums equal a brute-force loop;
* the walk-forward fit for a season never reads a result that was not in by the season's cutoff;
* the hierarchical shrinkage behaves (no spread -> full pooling);
* the Elo pass with every multiplier at 1 is the reference's elo_pass; a multiplier of 0 freezes a match;
* the 2025-2026 rows come only from frozen code: the mechanical mode refuses a changed file, and the stored rows carry
  the frozen hash.

Run: ./python.sh -m pytest test/lower_level_evidence/test_relationship.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import relationship as R  # noqa: E402


# ------------------------------------------------------------------------------------------------
# A synthetic Stage 0 in the shape TourStat reads

def synth(n_players: int = 300, years=(2014, 2019), seed: int = 0, gamma_true: float = -0.0006,
          delta_true: dict | None = None, ch_share: float = 0.5) -> pd.DataFrame:
    """Two rows per match (A then B), weekly events at MAIN or CH; spw_n ~ Bin(d, expit(skill + gamma (E_opp - 1900) +
    delta_level)). Players are main-tour based or Challenger based; Elo is fixed per player."""
    rng = np.random.default_rng(seed)
    delta_true = delta_true or {"MAIN": 0.0, "CH": 0.15}
    skill = rng.normal(0.35, 0.25, n_players)
    elo = 1900 + 150 * rng.standard_normal(n_players)
    ch_based = rng.random(n_players) < ch_share
    rows = []
    order = 0
    day0 = int(np.datetime64(f"{years[0]}-01-06", "D").astype("int64"))
    n_weeks = (years[1] - years[0] + 1) * 52
    for wk in range(n_weeks):
        day = day0 + 7 * wk
        year = int(str(np.datetime64(day, "D"))[:4])
        perm = rng.permutation(n_players)[: (n_players // 3) * 2]
        for i in range(0, len(perm), 2):
            pa, pb = int(perm[i]), int(perm[i + 1])
            lev = "CH" if (ch_based[pa] and ch_based[pb]) else "MAIN"
            mid = f"m{order}"
            for side, me, op in (("A", pa, pb), ("B", pb, pa)):
                d = 80.0
                eta = skill[me] + gamma_true * (elo[op] - 1900) + delta_true[lev]
                n = float(rng.binomial(int(d), expit(eta)))
                rows.append({"match_id": mid, "tour": "atp", "player_id": f"p{me}", "side": side, "year": year,
                             "day": day, "obs": float(day + 2), "es": float(day), "lf": float(day + 6),
                             "bucket": lev, "level": lev, "tier_row": "MT" if lev == "MAIN" else "CH",
                             "box": True, "played": True, "surf": "Hard", "elo_opp": float(elo[op]),
                             "elo_own": float(elo[me]), "order": order, "spw_n": n, "spw_d": d})
            order += 1
    p = pd.DataFrame(rows)
    for base in R.BASE_COLS:
        if base != "spw":
            p[f"{base}_n"] = np.nan
            p[f"{base}_d"] = np.nan
    p["pcode"] = pd.factorize(p["tour"] + "|" + p["player_id"])[0]
    p.attrs["skill"], p.attrs["elo"], p.attrs["ch_based"] = skill, elo, ch_based
    return p


@pytest.fixture(scope="module")
def world():
    p = synth()
    hist = R.own_history(p)
    ts = R.TourStat(p, hist, "atp", "spw")
    return p, hist, ts


# ------------------------------------------------------------------------------------------------

def test_window_sums_equal_brute_force(world):
    p, hist, ts = world
    h = 26.0
    S = ts.sums(h)
    rng = np.random.default_rng(1)
    for j in rng.choice(len(ts.pos), size=40, replace=False):
        pos = ts.pos[j]
        code, day, obs = ts.code[pos], p["day"].to_numpy()[ts.rows[pos]], ts.obs[pos]
        V = np.zeros(len(R.LEVELS))
        Y = np.zeros(len(R.LEVELS))
        E = np.zeros(len(R.LEVELS))
        for i in range(pos):                     # strictly earlier positions of the same player within the window
            if ts.code[i] != code:
                continue
            if p["day"].to_numpy()[ts.rows[i]] < day - R.WINDOW_DAYS:
                continue
            v = ts.d[i] * 2.0 ** (-(obs - ts.obs[i]) / (7 * h))
            V[ts.lev[i]] += v
            Y[ts.lev[i]] += v * ts.y[i]
            E[ts.lev[i]] += v * ts.eopp[i]
        assert np.allclose(S["V"][j], V, rtol=1e-9, atol=1e-9)
        assert np.allclose(S["Y"][j], Y, rtol=1e-9, atol=1e-7)
        assert np.allclose(S["E"][j], E, rtol=1e-9, atol=1e-5)


def planted_targets(ts: R.TourStat, S: dict, ix: np.ndarray, par: dict, eref: float, rng) -> None:
    """Redraw the outcomes of targets `ix` from the predictor's own formula with planted parameters (lower level CH,
    'gap' translation): the fit must give them back."""
    D = R.design(ts, S, ix, eref, np.zeros(len(R.SURFACES)), ["CH"], "gap")
    spec = {"prior": "pool", "delta": True, "w": "free", "gamma": par["gamma"]}
    theta = np.r_[np.log(par["k"]), par["mu"], par["delta"], par["w"]]
    eta, _ = R.eta_grad_matrix(theta, D, spec)
    ts.t["x"][ix] = rng.binomial(ts.t["d"][ix].astype(int), expit(eta)).astype(float)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_planted_delta_w_prior_recovered(seed):
    """Five synthetic worlds (seed 0 once stalled in a poor optimum from a single start: the two-start fit fixes it)."""
    p = synth(seed=seed)
    hist = R.own_history(p)
    ts = R.TourStat(p, hist, "atp", "spw")
    S = ts.sums(52.0)
    rng = np.random.default_rng(100 + seed)
    ix = np.flatnonzero((ts.t["year"] >= 2016) & (S["V"][:, 0] + S["V"][:, 3] > 0))
    ts.t["d"][ix] = 2000.0                                 # long targets: a sharp test of the mechanics
    par = {"k": 300.0, "mu": 0.30, "delta": 0.20, "w": 0.55, "gamma": -0.0006}
    planted_targets(ts, S, ix, par, 1900.0, rng)
    D = R.design(ts, S, ix, 1900.0, np.zeros(len(R.SURFACES)), ["CH"], "gap")
    spec = {"prior": "pool", "delta": True, "w": "free", "gamma": par["gamma"]}
    f = R.fit(D, spec)
    assert f["converged"]
    assert abs(f["delta"][0] - par["delta"]) < 0.03
    assert abs(f["w"][0] - par["w"]) < 0.08
    assert abs(f["mu"][0] - par["mu"]) < 0.03
    assert abs(np.log(f["k"]) - np.log(par["k"])) < 0.25
    # gamma free (main rows, target and the lower rows' gap all move with it)
    spec_g = {"prior": "pool", "delta": True, "w": "free", "gamma_free": True}
    fg = R.fit(D, spec_g)
    assert abs(fg["gamma"] - par["gamma"]) < 0.00015


def test_planted_gamma_recovered_main_only(world):
    p, hist, ts = world
    S = ts.sums(52.0)
    rng = np.random.default_rng(11)
    ix = np.flatnonzero((ts.t["year"] >= 2016) & (S["V"][:, 0] > 0))
    ts.t["d"][ix] = 2000.0
    D = R.design(ts, S, ix, 1900.0, np.zeros(len(R.SURFACES)), [], "gap")
    spec = {"prior": "pool", "delta": False, "w": "fixed", "wfix": [], "gamma": -0.0009}
    theta = np.r_[np.log(200.0), 0.4]
    eta, _ = R.eta_grad_matrix(theta, D, spec)
    ts.t["x"][ix] = rng.binomial(2000, expit(eta)).astype(float)
    D = R.design(ts, S, ix, 1900.0, np.zeros(len(R.SURFACES)), [], "gap")
    f = R.fit(D, {"prior": "pool", "delta": False, "w": "fixed", "wfix": [], "gamma_free": True})
    assert abs(f["gamma"] - (-0.0009)) < 0.00015


def test_planted_newcomer_mean_recovered():
    p = synth(seed=3)
    hist = R.own_history(p)
    ts = R.TourStat(p, hist, "atp", "spw")
    S = dict(ts.sums(52.0))
    S["NR"] = np.zeros_like(S["NR"])                       # every target a newcomer: the means are the tiers' own
    rng = np.random.default_rng(5)
    fm = np.ones(len(ts.pos), bool)
    nc = S["NR"][:, 0] < R.NEWCOMER_MAX_MAIN
    mu_tier = {"MT": 0.50, "CH": 0.10}
    for tier, mu in mu_tier.items():
        m = nc & (ts.t["tier"] == R.TIERS.index(tier))
        ts.t["x"][m] = rng.binomial(4000, expit(mu + -0.0006 * (ts.t["eopp"][m] - 1900.0))).astype(float)
        ts.t["d"][m] = 4000.0
    mus, info = R.newcomer_means(ts, S, fm, np.zeros(len(R.SURFACES)), 1900.0, -0.0006)
    assert info["counts"]["CH"] >= R.NEWCOMER_MIN_TARGETS and info["counts"]["MT"] >= R.NEWCOMER_MIN_TARGETS
    assert abs(mus[R.TIERS.index("CH")] - 0.10) < 0.02
    assert abs(mus[R.TIERS.index("MT")] - 0.50) < 0.02


def test_walk_forward_never_reads_the_future():
    """Every result that was not in by the season's cutoff (lf + 1 > cutoff) is replaced at random: the season's fit
    (and its constants) must not move."""
    p = synth(seed=4, years=(2014, 2019))
    first_es = {y: float(p.loc[p["year"] == y, "es"].min()) for y in sorted(p["year"].unique())}
    Y = 2018

    def season_fit(pp):
        hist = R.own_history(pp)
        ts = R.TourStat(pp, hist, "atp", "spw")
        S = ts.sums(52.0)
        ss = R.Season(ts, S, Y, first_es, 1900.0, -0.0006, {"class": "OPP", "delta_levels": ["CH"]}, score=False)
        Df, _, spec = ss.setup("F4free")
        f = R.fit(Df, spec)
        return np.r_[f["theta"], ss.soff, ss.mus], ss.lower, len(ss.fi)

    base, lower, nfit = season_fit(p)
    q = p.copy()
    late = (q["lf"] + 1.0 > first_es[Y]).to_numpy()
    assert late.sum() > 1000 and nfit > 200 and lower == ["CH"]
    rng = np.random.default_rng(9)
    q.loc[late, "spw_n"] = rng.binomial(80, rng.random(int(late.sum()))).astype(float)
    moved, _, _ = season_fit(q)
    assert np.allclose(base, moved, rtol=0, atol=1e-10)


def test_fit_targets_obey_the_clock(world):
    p, hist, ts = world
    first_es = {y: float(p.loc[p["year"] == y, "es"].min()) for y in sorted(p["year"].unique())}
    for Y in (2016, 2018):
        fm = R.fit_mask(ts, Y, first_es)
        assert (ts.t["lf"][fm] + 1.0 <= first_es[Y]).all()
        assert fm.sum() > 0


def test_level_needs_two_seasons_of_box_scores():
    """ITF's rule (any level): fitted only with MIN_LEVEL_SEASONS seasons of box scores in the fit window."""
    p = synth(seed=6, years=(2014, 2019))
    # make CH box scores exist only in 2017 (one season)
    keep = ~((p["bucket"] == "CH") & (p["year"] != 2017))
    p.loc[~keep, "box"] = False
    p.loc[~keep, ["spw_n", "spw_d"]] = np.nan
    first_es = {y: float(p.loc[p["year"] == y, "es"].min()) for y in sorted(p["year"].unique())}
    hist = R.own_history(p)
    ts = R.TourStat(p, hist, "atp", "spw")
    S = ts.sums(52.0)
    fm = R.fit_mask(ts, 2019, first_es)
    assert "CH" not in R.fitted_levels(ts, S, fm, 2019, first_es)
    p2 = synth(seed=6, years=(2014, 2019))
    hist2 = R.own_history(p2)
    ts2 = R.TourStat(p2, hist2, "atp", "spw")
    S2 = ts2.sums(52.0)
    assert "CH" in R.fitted_levels(ts2, S2, R.fit_mask(ts2, 2019, first_es), 2019, first_es)


def test_shrinkage_pools_when_statistics_agree():
    rows = [{"tour": "atp", "season": 2020, "h": 52.0, "formulation": "F4free", "level": "CH", "w": 0.6,
             "se": 0.1} for _ in range(8)]
    rows += [{"tour": "atp", "season": 2020, "h": 52.0, "formulation": "F4free", "level": "TQ", "w": w, "se": 0.05}
             for w in (0.2, 0.5, 0.8, 1.1, 1.4, 0.3, 1.2, 0.9)]
    sh = R.shrinkage(pd.DataFrame(rows))
    wbar, tau2 = sh[("atp", 2020, 52.0, "F4free", "CH")]
    assert abs(wbar - 0.6) < 1e-12 and tau2 == 0.0
    wbar2, tau22 = sh[("atp", 2020, 52.0, "F4free", "TQ")]
    assert tau22 > 0.05


def test_w_prior_with_tiny_tau_pins_w(world):
    p, hist, ts = world
    S = ts.sums(52.0)
    ix = np.flatnonzero((ts.t["year"] >= 2016) & (S["V"][:, 3] > 0))
    D = R.design(ts, S, ix, 1900.0, np.zeros(len(R.SURFACES)), ["CH"], "gap")
    spec = {"prior": "pool", "delta": True, "w": "free", "gamma": -0.0006,
            "wprior": (np.array([0.42]), np.array([1e-8]))}
    f = R.fit(D, spec)
    assert abs(f["w"][0] - 0.42) < 1e-3


def test_class_bars_delta_where_not_real(world):
    p, hist, ts = world
    S = ts.sums(52.0)
    ix = np.flatnonzero(ts.t["year"] >= 2016)
    D = R.design(ts, S, ix, 1900.0, np.zeros(len(R.SURFACES)), ["CH"], "gap")
    f = R.fit(D, {"prior": "pool", "delta": True, "w": "free", "gamma": -0.0006, "delta_allowed": [False]})
    assert f["delta"][0] == 0.0


# ------------------------------------------------------------------------------------------------
# The results channel

def test_elo_pass_w_is_the_reference_pass_at_one_and_frozen_at_zero():
    from src.eda.predictability_diagnostic import stage1_baselines as S1
    rng = np.random.default_rng(2)
    n, P = 3000, 120
    week = np.sort(rng.integers(0, 150, n)) * 7
    event = (week // 7) * 3 + rng.integers(0, 3, n)
    rnd = rng.integers(1, 6, n)
    o = np.lexsort((rnd, event, week))
    week, event, rnd = week[o].tolist(), event[o].tolist(), rnd[o].tolist()
    a = rng.integers(0, P, n)
    b = (a + 1 + rng.integers(0, P - 1, n)) % P
    won = (rng.random(n) < 0.5).tolist()
    upd = (rng.random(n) < 0.95).tolist()
    ref = S1.elo_pass(week, event, rnd, a.tolist(), b.tolist(), won, [0] * n, upd, P, 600.0, 2.0, 0.6, surface=False)
    mine = R.elo_pass_w(week, event, rnd, a.tolist(), b.tolist(), won, upd, [1.0] * n, P, 600.0, 2.0, 0.6)
    assert np.allclose(mine[:, 0], ref[:, 0]) and np.allclose(mine[:, 1], ref[:, 1])
    # a multiplier of 0 on every match: nobody moves
    still = R.elo_pass_w(week, event, rnd, a.tolist(), b.tolist(), won, upd, [0.0] * n, P, 600.0, 2.0, 0.6)
    assert np.all(still == R.ELO_START)


# ------------------------------------------------------------------------------------------------
# The holdout and the frozen code

def test_load_refuses_holdout_seasons_without_the_mechanical_mode():
    with pytest.raises(SystemExit):
        R.load(through=2025)
    with pytest.raises(SystemExit):
        R.elo_history(R.C.STAGE0_DIR, 2025, R.C.TIMING)


def test_mechanical_mode_refuses_code_that_is_not_the_frozen_code(tmp_path):
    freeze = tmp_path / "method_freeze.json"
    freeze.write_text(json.dumps({"relationship_sha256": "0" * 64, "classify_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(SystemExit):
        R.verify_frozen(freeze)


def test_stored_holdout_rows_carry_the_frozen_hash():
    """Once the parameters exist: every 2025-2026 row was written by the frozen file."""
    params = R.OUT / "params.parquet"
    if not params.exists() or not R.FREEZE.exists():
        pytest.skip("parameters not produced yet")
    fr = json.loads(R.FREEZE.read_text(encoding="utf-8"))
    df = pd.read_parquet(params)
    hold = df[df["season_used"] >= 2025]
    if not len(hold):
        pytest.skip("the 2025-2026 rows are not produced yet")
    assert set(hold["code_sha256"].unique()) == {fr["relationship_sha256"]}


def test_itf_box_scores_enter_only_after_two_fit_seasons():
    """The ITF rule on a Stage 0 that holds ITF box scores (a P7 candidate): the same code fits ITF once the fit window
    holds two seasons of them, and gives it w = 0 before."""
    p = synth(seed=8, years=(2014, 2019))
    itf = (p["bucket"] == "CH") & (p["year"] >= 2017)        # the candidate's ITF box scores begin in 2017
    p.loc[itf, ["bucket", "level", "tier_row"]] = ["ITF", "ITF", "ITF"]
    first_es = {y: float(p.loc[p["year"] == y, "es"].min()) for y in sorted(p["year"].unique())}
    hist = R.own_history(p)
    ts = R.TourStat(p, hist, "atp", "spw")
    S = ts.sums(52.0)
    assert "ITF" not in R.fitted_levels(ts, S, R.fit_mask(ts, 2018, first_es), 2018, first_es)   # one season (2017)
    assert "ITF" in R.fitted_levels(ts, S, R.fit_mask(ts, 2019, first_es), 2019, first_es)       # 2017 and 2018
