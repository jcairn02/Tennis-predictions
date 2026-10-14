"""Tests of role A's classifier (src/eda/lower_level_evidence/classify.py): a planted opponent gradient (gamma) is
recovered through the whole gamma() path on a synthetic Stage 0; the within-player-season fixed effects equal an
explicit dummy regression; no outcome of the 2025-2026 holdout is read; the match clock is respected by gamma() and by
the counter-skill's running rates (a cut-and-reverse probe in the spirit of src/eda/match_timing/probe.py).

Run: ./python.sh -m pytest test/lower_level_evidence/test_classify.py -q
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

from src.eda.lower_level_evidence import classify as A  # noqa: E402
from src.eda.lower_level_evidence import common as C  # noqa: E402

EPOCH = pd.Timestamp("1970-01-01")
GAMMA_TRUE = -0.06        # logit of serve points won per 100 Elo of the opponent


# ------------------------------------------------------------------------------------------------
# A synthetic Stage 0 (matches, player rows, clock, strength) written to a temporary folder

def synthetic_stage0(tmp: Path, seed: int = 0, n_players: int = 120, seasons=range(2016, 2026), per_week: int = 30,
                     gamma: float = GAMMA_TRUE) -> dict:
    """Players with a true serve skill; weekly main-tour events; the opponent's Elo tracks his skill; serve points won
    follow logit p = skill_own + season shift + gamma x opp_elo / 100. Better players meet stronger opponents more often
    (they go deeper), so a pooled regression is confounded and only the within-player-season one recovers gamma.
    Season 2025 (events from 30 Dec 2024) is the holdout."""
    rng = np.random.default_rng(seed)
    skill = rng.normal(0.0, 0.35, n_players)
    season_shift = {(p, y): rng.normal(0, 0.1) for p in range(n_players) for y in seasons}
    mrows, prows, trows, srows = [], [], [], []
    k = 0
    for y in seasons:
        start = pd.Timestamp(f"{y - 1}-12-30") if y == 2025 else pd.Timestamp(f"{y}-01-06")
        for wk in range(40):
            date = start + pd.Timedelta(weeks=wk)
            es = int((date - EPOCH).days)
            for _ in range(per_week):
                a = int(rng.integers(n_players))
                # assortative pairing: opponents near one's own skill (deeper runs for the better players)
                b = int(np.argmin(np.abs(skill - (skill[a] + rng.normal(0, 0.25))) + (np.arange(n_players) == a)))
                mid = f"atp|{y}-{wk}|R32|{k}"
                k += 1
                elo = {a: 1500 + 400 * skill[a] + rng.normal(0, 30), b: 1500 + 400 * skill[b] + rng.normal(0, 30)}
                mrows.append({"match_id": mid, "tour": "atp", "year": y, "tournament_date": date, "map_level": "T250",
                              "status": "completed", "format": "standard", "surface": "Hard", "best_of": 3,
                              "round_order": 13, "level": "T250", "tournament_id": f"{y}-{wk}", "has_box": True})
                trows.append({"match_id": mid, "es": float(es), "lf": float(es + 6)})
                srows.append({"match_id": mid, "elo_a_ret": elo[a], "elo_b_ret": elo[b], "n_a_ret": 50.0,
                              "n_b_ret": 50.0})
                for side, me, op in (("A", a, b), ("B", b, a)):
                    lp = 0.4 + skill[me] + season_shift[(me, y)] + gamma * (elo[op] - 1500) / 100.0
                    d = 80.0
                    x = float(rng.binomial(int(d), expit(lp)))
                    row = {"match_id": mid, "player_id": f"p{me}", "opponent_id": f"p{op}", "side": side,
                           "won": side == "A", "has_box": True}
                    for s in A.OWN:
                        row[f"{s}_n"], row[f"{s}_d"] = (x, d) if s != "bp_faced_pg" else (3.0, 10.0)
                    prows.append(row)
    d0 = tmp / "stage0"
    d0.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(mrows).to_parquet(d0 / "stage0_matches.parquet", index=False)
    pd.DataFrame(prows).to_parquet(d0 / "stage0_match_players.parquet", index=False)
    pd.DataFrame(trows).to_parquet(tmp / "timing.parquet", index=False)
    pd.DataFrame(srows).to_parquet(tmp / "strength.parquet", index=False)
    return {"stage0_dir": d0, "timing": tmp / "timing.parquet", "strength_path": tmp / "strength.parquet"}


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    A._CACHE.clear()
    return synthetic_stage0(tmp_path_factory.mktemp("classify"))


# ------------------------------------------------------------------------------------------------
# 1. A planted gamma is recovered

def test_planted_gamma_is_recovered_through_gamma(synth):
    g = A.gamma("2024-12-30", stats=["spw"], tours=["atp"], **synth)
    r = g.iloc[0]
    assert r["n_rows"] > 10_000
    assert r["gamma_lo"] < GAMMA_TRUE < r["gamma_hi"]
    assert abs(r["gamma"] - GAMMA_TRUE) < 0.01
    # the other side of the same rows: X's return points against the first serve are the opponent's first serves not
    # won, driven by the opponent's own skill, which his Elo tracks at 1/4 logit per 100 Elo (400 Elo per unit of
    # skill), attenuated by the Elo noise inside a player-season (reliability about 0.92): about -0.23
    g2 = A.gamma("2024-12-30", stats=["rpw_first"], tours=["atp"], **synth)
    assert -0.26 < g2["gamma"].iloc[0] < -0.19


def test_a_planted_zero_gamma_reads_zero(tmp_path):
    A._CACHE.clear()
    paths = synthetic_stage0(tmp_path, seed=3, seasons=range(2016, 2020), gamma=0.0)
    r = A.gamma("2020-01-01", stats=["spw"], tours=["atp"], **paths).iloc[0]
    assert r["gamma_lo"] < 0.0 < r["gamma_hi"]
    A._CACHE.clear()


# ------------------------------------------------------------------------------------------------
# 2. The within-player-season fixed effects

def test_fixed_effects_equal_an_explicit_dummy_regression():
    rng = np.random.default_rng(7)
    n, groups = 3_000, 150
    g = rng.integers(0, groups, n)
    cl = g // 5                                          # players own several seasons (groups nest in clusters)
    fe = rng.normal(0, 1, groups)
    x = fe[g] * 0.8 + rng.normal(0, 1, n)                # the regressor is correlated with the fixed effect
    z = rng.integers(0, 2, n).astype(float)[:, None]     # one control
    w = rng.uniform(0.5, 3.0, n)
    y = fe[g] + 0.3 * x - 0.2 * z[:, 0] + rng.normal(0, 1, n) / np.sqrt(w)
    res = A.fe_wls(y, w, x, g, cl, z)
    D = np.zeros((n, groups))
    D[np.arange(n), g] = 1.0
    Xf = np.column_stack([x, z, D])
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(Xf * sw[:, None], y * sw, rcond=None)
    assert res["beta"][0] == pytest.approx(beta[0], abs=1e-10)
    # the sandwich: bread and scores of the dummy regression's x block equal the within regression's
    e = y - Xf @ beta
    Ainv = np.linalg.pinv((Xf * w[:, None]).T @ Xf)
    S = (Xf * (w * e)[:, None])
    Sc = np.vstack([S[cl == c].sum(axis=0) for c in np.unique(cl)])
    V = Ainv @ (Sc.T @ Sc) @ Ainv
    G = len(np.unique(cl))
    k_within = 2
    corr = (G / (G - 1.0)) * ((n - 1.0) / (n - k_within))
    assert np.sqrt(res["V"][0, 0]) == pytest.approx(np.sqrt(V[0, 0] * corr), rel=1e-6)
    # pooled OLS without the fixed effects is biased here; the within estimate is not
    b_pool = np.polyfit(x, y, 1)[0]
    assert abs(b_pool - 0.3) > 0.2 and abs(res["beta"][0] - 0.3) < 0.05


def test_fixed_effects_are_player_by_season(synth):
    """A season shift of the player's own level must not leak into gamma: gamma() groups by player x season."""
    A._CACHE.clear()
    rows = A._main_rows(A.day_of("2024-12-30"), A.day_of("2010-01-01"), Path(synth["stage0_dir"]),
                        Path(synth["timing"]), Path(synth["strength_path"]), False)
    f = A.fit_gamma(rows, "spw")
    assert f["n_player_seasons"] == rows.groupby(["player_id", "year"]).ngroups
    assert f["n_players"] == rows["player_id"].nunique()


# ------------------------------------------------------------------------------------------------
# 3. No outcome of the 2025-2026 holdout is read

def test_gamma_refuses_holdout_outcomes(synth):
    A._CACHE.clear()
    with pytest.raises(PermissionError):
        A.gamma("2025-06-01", stats=["spw"], **synth)
    ok = A.gamma("2025-06-01", stats=["spw"], tours=["atp"], allow_holdout=True, **synth)   # the mechanical fit
    assert ok["n_rows"].iloc[0] > 0
    A._CACHE.clear()


def test_filtered_read_never_requests_a_holdout_match(synth, monkeypatch):
    A._CACHE.clear()
    seen = []
    real = C.load_players

    def spy(stage0_dir=C.STAGE0_DIR, columns=None, match_ids=None):
        assert match_ids is not None, "an unfiltered read of the player rows"
        seen.extend(pd.Index(match_ids).astype(str))
        return real(stage0_dir, columns=columns, match_ids=match_ids)
    monkeypatch.setattr(C, "load_players", spy)
    A.gamma("2024-12-30", stats=["spw"], tours=["atp"], **synth)
    m = pd.read_parquet(Path(synth["stage0_dir"]) / "stage0_matches.parquet", columns=["match_id", "tournament_date"])
    dates = m.set_index("match_id").loc[seen, "tournament_date"]
    assert len(seen) > 0 and not C.in_holdout(dates).any()
    A._CACHE.clear()


def test_player_rows_asserts_on_holdout_matches(synth):
    m = A.match_table(synth["stage0_dir"], synth["timing"])
    with pytest.raises(AssertionError):
        A.player_rows(m, synth["stage0_dir"], pd.read_parquet(synth["strength_path"]))


@pytest.mark.skipif(not A.STRENGTH.exists(), reason="the frozen reference's strength copy is not on this machine")
def test_real_data_cutoff_2025_reads_no_holdout_match(monkeypatch):
    """On the frozen Stage 0: the fit for season 2025 (results in by its first main-tour match) reads no 2025-26 row."""
    A._CACHE.clear()
    seen = []
    real = C.load_players

    def spy(stage0_dir=C.STAGE0_DIR, columns=None, match_ids=None):
        seen.extend(pd.Index(match_ids).astype(str))
        return real(stage0_dir, columns=columns, match_ids=match_ids)
    monkeypatch.setattr(C, "load_players", spy)
    cut = A.season_cutoff(2025)
    assert cut <= C.HOLDOUT_START
    g = A.gamma(cut, stats=["spw"])
    m = C.load_matches(columns=["match_id", "tournament_date"]).set_index("match_id")
    assert not C.in_holdout(m.loc[seen, "tournament_date"]).any()
    assert (pd.to_datetime(g["last_result_day"]) <= cut).all()
    with pytest.raises(PermissionError):
        A.gamma(A.season_cutoff(2026), stats=["spw"])
    A._CACHE.clear()


# ------------------------------------------------------------------------------------------------
# The class rule (thresholds.json applied as written)

def test_class_rule_follows_the_fixed_thresholds():
    """OPP needs gamma's interval to exclude 0 AND |gamma| x reference gap >= 0.10 SD_signal; delta is 'real' at a
    level when the shift left after the class's translation clears 0 and reaches 0.10 SD_signal, with >= 100
    player-seasons."""
    gam = pd.DataFrame([
        # material: 0.05 x 2.0 = 0.10 >= 0.10 x 0.5
        {"tour": "atp", "stat": "spw", "side": "serve", "gamma": -0.05, "gamma_lo": -0.06, "gamma_hi": -0.04,
         "unit": "logit per 100 Elo", "sd_signal": 0.5, "sd_match": 1.0},
        # significant but immaterial: 0.02 x 2.0 = 0.04 < 0.05
        {"tour": "atp", "stat": "first_in", "side": "serve", "gamma": 0.02, "gamma_lo": 0.01, "gamma_hi": 0.03,
         "unit": "logit per 100 Elo", "sd_signal": 0.5, "sd_match": 1.0},
        # material size but interval spans 0
        {"tour": "atp", "stat": "df", "side": "serve", "gamma": -0.2, "gamma_lo": -0.45, "gamma_hi": 0.05,
         "unit": "logit per 100 Elo", "sd_signal": 0.5, "sd_match": 1.0}])
    gaps = pd.DataFrame([{"tour": "atp", "level": L, "n_ps": 500, "delta_elo_100": -2.0, "box_rows": 100}
                         for L in A.LEVELS])
    lev = []
    for s, raw, res in (("spw", 0.10, 0.08), ("first_in", 0.20, 0.16), ("df", 0.01, 0.0)):
        for L in A.LEVELS:
            n = 50 if L == "CHQ" else 400
            lev.append({"tour": "atp", "stat": s, "level": L, "n_ps": n, "raw_shift": raw, "raw_lo": raw - 0.02,
                        "raw_hi": raw + 0.02, "explained": raw - res, "explained_share": (raw - res) / raw,
                        "residual": res, "residual_lo": res - 0.02, "residual_hi": res + 0.02})
    out = A.classify_stats(gam, pd.DataFrame(lev), gaps, {}).set_index("stat")
    assert out.loc["spw", "class"] == "OPP"
    assert out.loc["first_in", "class"] == "ENV"
    assert out.loc["df", "class"] == "ENV"
    # spw (OPP): residual 0.08 >= 0.05 and clears 0 -> real at TQ, GSQ, CH; CHQ has under 100 player-seasons
    assert out.loc["spw", "delta_levels"] == "TQ,GSQ,CH"
    assert out.loc["spw", "delta_CHQ"] == "not identified"
    # first_in (ENV): judged on the raw shift 0.20 -> real; df: 0.01 < 0.05 -> not real anywhere
    assert out.loc["first_in", "delta_levels"] == "TQ,GSQ,CH"
    assert out.loc["df", "delta_levels"] == ""
    assert A.rule_for("OPP", "one_step_forms", "CH").startswith("translate: gamma")
    assert A.rule_for("ENV", "raw_rates", "") == "weight only"
    assert A.rule_for("OPP", "joint_solves", "").startswith("solve handles the opponent; weight w only")
    assert A.rule_for("RES", "results_ratings", "") == "w_results only"
    assert A.rule_for("INTR", "intrinsic", "") == "untouched"


# ------------------------------------------------------------------------------------------------
# 4. The match clock

def test_gamma_reads_only_results_in_by_the_cut(synth, tmp_path):
    """Reverse every outcome whose result is not in by the cut (lf + 1 > cut): gamma at the cut must not move. Reverse
    one that is in: it must move (the leaky control)."""
    A._CACHE.clear()
    cut = A.day_of("2021-06-01")
    base = A.gamma(cut, stats=["spw"], tours=["atp"], **synth)["gamma"].iloc[0]
    t = pd.read_parquet(synth["timing"])
    pl = pd.read_parquet(Path(synth["stage0_dir"]) / "stage0_match_players.parquet")
    for name, mask_fn in (("later", lambda lf: lf + 1 > cut), ("earlier", lambda lf: lf + 1 <= cut)):
        ids = set(t.loc[mask_fn(t["lf"].to_numpy()), "match_id"])
        p2 = pl.copy()
        sel = p2["match_id"].isin(ids)
        p2.loc[sel, "spw_n"] = p2.loc[sel, "spw_d"] - p2.loc[sel, "spw_n"]      # reverse the serve points won
        d = tmp_path / name / "stage0"
        d.mkdir(parents=True)
        pd.read_parquet(Path(synth["stage0_dir"]) / "stage0_matches.parquet").to_parquet(d / "stage0_matches.parquet")
        p2.to_parquet(d / "stage0_match_players.parquet")
        A._CACHE.clear()
        g = A.gamma(cut, stats=["spw"], tours=["atp"], stage0_dir=d, timing=synth["timing"],
                    strength_path=synth["strength_path"])["gamma"].iloc[0]
        if name == "later":
            assert g == pytest.approx(base, abs=1e-12)
        else:
            assert abs(g - base) > 1e-3
    A._CACHE.clear()


def test_season_cutoff_is_the_first_earliest_start(synth):
    A._CACHE.clear()
    t = pd.read_parquet(synth["timing"])
    m = pd.read_parquet(Path(synth["stage0_dir"]) / "stage0_matches.parquet", columns=["match_id", "year"])
    first = int(t.merge(m, on="match_id").query("year == 2020")["es"].min())
    assert A.season_cutoff(2020, synth["stage0_dir"], synth["timing"]) == A.date_of(first)
    A._CACHE.clear()


def test_counter_skill_running_rate_respects_the_clock():
    """The counter-skill reads a player's rows with lf + 1 <= es only: changing every row that finishes on or after a
    cut day leaves every target that starts by the cut unchanged; changing an earlier row moves some (leaky control)."""
    rng = np.random.default_rng(11)
    n = 4_000
    hist = pd.DataFrame({"player_id": rng.choice([f"p{i}" for i in range(40)], n),
                         "lf": rng.integers(18_000, 18_700, n).astype(np.int64),
                         "x": rng.integers(0, 50, n).astype(float), "d": np.full(n, 80.0)})
    who = rng.choice([f"p{i}" for i in range(40)], 2_000)
    es = rng.integers(18_100, 18_700, 2_000).astype(np.int64)
    base = A.counter_values(hist, 0.6, 400.0, "spw", who, es)
    cut = 18_400
    later = hist.copy()
    later.loc[later["lf"] + 1 > cut, "x"] = 80.0 - later.loc[later["lf"] + 1 > cut, "x"]
    v = A.counter_values(later, 0.6, 400.0, "spw", who, es)
    early = es <= cut
    assert np.array_equal(v[early], base[early])
    assert not np.array_equal(v[~early], base[~early])
    # brute force on a sample
    for i in rng.choice(len(who), 50, replace=False):
        h = hist[(hist["player_id"] == who[i]) & (hist["lf"] + 1 <= es[i]) & (hist["lf"] >= es[i] - 365)]
        p = (h["x"].sum() + 400.0 * 0.6) / (h["d"].sum() + 400.0)
        assert base[i] == pytest.approx(np.log(p / (1 - p)), abs=1e-12)
