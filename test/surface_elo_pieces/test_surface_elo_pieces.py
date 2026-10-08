"""Offline tests for src/eda/surface_elo_pieces/ (no network, no paid call).

Run: ./python.sh -m pytest test/surface_elo_pieces -p no:cacheprovider
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.surface_elo_pieces import arms as A  # noqa: E402
from src.eda.surface_elo_pieces import guard as G  # noqa: E402
from src.eda.surface_elo_pieces import pieces as P  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402


# ------------------------------------------------------------------------------------------------
# Elo variants

def synthetic_history(n_players=12, weeks=40, seed=1):
    rng = np.random.default_rng(seed)
    week, event, rnd, a, b, won, surf = [], [], [], [], [], [], []
    skill = rng.normal(0, 1, n_players)
    for w in range(weeks):
        for e in range(2):                                      # two events a week
            players = rng.permutation(n_players)[: 8]
            s = int(rng.integers(0, 3))
            for r, (i, j) in enumerate([(players[0], players[1]), (players[2], players[3]), (players[4], players[5])]):
                week.append(w * 7); event.append(w * 10 + e); rnd.append(r % 2); a.append(int(i)); b.append(int(j))
                won.append(bool(rng.random() < 1 / (1 + np.exp(-(skill[i] - skill[j])))))
                surf.append(s if rng.random() > 0.05 else -1)
    return dict(week=week, event=event, rnd=rnd, a=a, b=b, a_won=won, surf=surf, n_players=n_players)


def test_stage1_mode_reproduces_stage1_pass():
    h = synthetic_history()
    upd = [True] * len(h["week"])
    ref = B.elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, h["n_players"],
                     600.0, 2.0, 0.6)
    for mode, kd in (("stage1", {}), ("anchored", {}), ("offset", {"kd0": 80.0, "kd_off": 10.0, "kd_shape": 0.6})):
        out = P.elo_pass_ext(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd,
                             h["n_players"], 600.0, 2.0, 0.6, mode=mode, **kd)
        assert np.allclose(out[:, :8], ref, equal_nan=True), mode       # the shared part is Stage 1 exactly


def test_offset_with_zero_k_stays_zero_and_anchored_starts_at_overall():
    h = synthetic_history()
    upd = [True] * len(h["week"])
    out = P.elo_pass_ext(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd,
                         h["n_players"], 600.0, 2.0, 0.6, mode="offset", kd0=0.0, kd_off=1.0, kd_shape=0.5)
    known = np.asarray(h["surf"]) >= 0
    assert np.allclose(out[known, 8:10], 0.0)
    an = P.elo_pass_ext(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd,
                        h["n_players"], 600.0, 2.0, 0.6, mode="anchored")
    first = known & (an[:, 6] == 0)                              # A's first match on that surface
    assert np.allclose(an[first, 8], an[first, 0])


def test_elo_time_rule_round_robin_and_same_week():
    # two matches of the same round never see each other; another event of the same week neither
    h = dict(week=[0, 0, 0, 7], event=[1, 1, 2, 3], rnd=[1, 1, 1, 1], a=[0, 0, 0, 0], b=[1, 2, 3, 1],
             a_won=[True, True, True, True], surf=[0, 0, 0, 0], n_players=4)
    out = P.elo_pass_ext(**{k: v for k, v in h.items() if k != "n_players"}, upd=[True] * 4, n_players=4,
                         k0=100.0, offset=1.0, shape=0.5, mode="offset", kd0=50.0, kd_off=1.0, kd_shape=0.5)
    assert out[0, 0] == out[1, 0] == out[2, 0] == B.START                   # week 0: nothing seen yet
    assert out[0, 8] == out[1, 8] == out[2, 8] == 0.0
    assert out[3, 0] > B.START and out[3, 8] > 0                            # week 7 sees all three wins


# ------------------------------------------------------------------------------------------------
# Surface switches

def tiny_rows():
    m = pd.DataFrame({
        "match_id": [f"m{i}" for i in range(6)],
        "player_a_id": ["x", "x", "x", "x", "x", "y"], "player_b_id": ["y", "z", "y", "z", "y", "z"],
        "tour": ["atp"] * 6, "year": [2015, 2015, 2015, 2016, 2016, 2016],
        "surface": ["Grass", "Grass", "Clay", "Grass", "Grass", "Grass"],
        "tournament_date": pd.to_datetime(["2015-06-01", "2015-06-01", "2015-07-06", "2016-06-06", "2016-06-06",
                                           "2016-06-06"]),
        "tournament_id": ["e1", "e1", "e2", "e3", "e3", "e3"], "round_order": [1, 2, 1, 1, 2, 2],
        "order": np.arange(6), "status": ["completed"] * 6, "a_won": [True, True, False, True, True, False]})
    obs = (pd.to_datetime(["2015-06-01", "2015-06-03", "2015-07-06", "2016-06-06", "2016-06-08", "2016-06-08"])
           .values.astype("datetime64[D]").astype("int64").astype(float))
    p = np.full(6, 0.5)
    return m, obs, p


def test_surface_switch_counts_layoffs_and_last_season():
    m, obs, p = tiny_rows()
    rows = P.player_rows(m, obs, p)
    sw = P.surface_switch(rows)
    x = rows["player_id"].eq("x").to_numpy()
    sx = sw[x].reset_index(drop=True)
    # x's grass matches: m0 (2015), m1 (2015, next round), m3 (2016), m4 (2016 next round); clay m2
    assert sx["season_n"].tolist() == [0, 1, 0, 0, 1]
    assert np.isnan(sx["days_since"].iloc[0]) and sx["days_since"].iloc[1] == 2
    assert np.isnan(sx["days_since"].iloc[2])                       # first clay match
    assert sx["days_since"].iloc[3] == 369                          # 2015-06-03 -> 2016-06-06 (2016 is a leap year)
    # last season on grass for x in 2016: two wins at P = 0.5 -> +1.0 above expectation, 2 matches
    assert sx["prev_n"].iloc[3] == 2 and sx["prev_res"].iloc[3] == pytest.approx(1.0)
    assert sx["prev_n"].iloc[2] == 0                                # clay in 2014: none


def test_surface_switch_ignores_later_results():
    m, obs, p = tiny_rows()
    base = P.surface_switch(P.player_rows(m, obs, p)).to_numpy()
    m2 = m.copy()
    m2.loc[3:, "a_won"] = ~m2.loc[3:, "a_won"]                      # flip 2016
    got = P.surface_switch(P.player_rows(m2, obs, p)).to_numpy()
    assert np.allclose(got[:6], base[:6], equal_nan=True)           # 2015 rows unchanged


# ------------------------------------------------------------------------------------------------
# Arms and the flip

def fake_pieces(n=50, seed=3):
    rng = np.random.default_rng(seed)
    q = pd.DataFrame({c: rng.normal(1600, 200, n) for c in ("R_a", "R_b", "S_a", "S_b")})
    q["D_a"], q["D_b"] = rng.normal(0, 30, n), rng.normal(0, 30, n)
    for s in ("a", "b"):
        q[f"NS_{s}"] = rng.integers(0, 300, n).astype(float)
        q[f"season_n_{s}"] = rng.integers(0, 20, n).astype(float)
        q[f"days_since_{s}"] = np.where(rng.random(n) < 0.1, np.nan, rng.integers(0, 2000, n)).astype(float)
        q[f"prev_n_{s}"] = rng.integers(0, 15, n).astype(float)
        q[f"prev_res_{s}"] = rng.normal(0, 1, n)
    return q


def swap_pieces(q):
    s = q.copy()
    for c in ("R", "S", "D", "NS", "season_n", "days_since", "prev_n", "prev_res"):
        s[f"{c}_a"], s[f"{c}_b"] = q[f"{c}_b"].to_numpy(), q[f"{c}_a"].to_numpy()
    return s


def test_new_inputs_swap_like_the_flip():
    q = fake_pieces()
    new = A.new_inputs(q)
    assert np.allclose(A.flip(new).to_numpy(), A.new_inputs(swap_pieces(q)).to_numpy(), equal_nan=True)
    assert (new[["surf_layoff_a", "surf_layoff_b"]].max().max() <= np.log1p(A.LAYOFF_CAP) + 1e-12)


def test_arms_columns_and_flip_involution():
    assert len(A.ARMS["base"]) == 54 and A.ARMS["base"] == T.TABPFN_NAMES
    for arm, cols in A.ARMS.items():
        assert len(cols) == len(set(cols)), arm
        for c in cols:
            assert (c in A.ANTISYMMETRIC) or (c in A.SWAP) or (c in A.BASE_CONTEXT), (arm, c)
    assert "elo_logit" not in A.ARMS["primary"] and "surface_first" not in A.ARMS["primary"]
    # amended after the audit: primary keeps only the season and layoff pairs; literal keeps all four
    assert set(A.ARMS["literal"]) - set(A.ARMS["primary"]) == {"elo_surface", "surf_career_a", "surf_career_b",
                                                               "surf_form_prev_a", "surf_form_prev_b"}
    assert set(A.ARMS["primary"]) - set(A.ARMS["literal"]) == {"elo_surf_offset"}
    # elo_only and switch_only decompose primary
    base = set(A.ARMS["base"])
    assert (set(A.ARMS["elo_only"]) - base) | (set(A.ARMS["switch_only"]) - base) == set(A.ARMS["primary"]) - base
    assert (base - set(A.ARMS["elo_only"])) | (base - set(A.ARMS["switch_only"])) == base - set(A.ARMS["primary"])
    assert len(A.ARMS["primary"]) == 58 and len(A.ARMS["literal"]) == 62
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(20, len(A.ARMS["literal"]))), columns=A.ARMS["literal"])
    assert np.allclose(A.flip(A.flip(X)).to_numpy(), X.to_numpy())
    Y = A.flip(X)
    assert np.allclose(Y["surf_career_a"], X["surf_career_b"]) and np.allclose(Y["elo_surface"], -X["elo_surface"])
    assert np.allclose(Y["tour"], X["tour"])
    Z = A.flip(pd.DataFrame(rng.normal(size=(5, 1)), columns=["elo_surf_offset"]))
    assert (Z["elo_surf_offset"] != 0).all()


# ------------------------------------------------------------------------------------------------
# The guard

class FakeBackend:
    calls = {"fit": 0, "predict": 0}

    def __init__(self, config):
        self.config = config

    def usage(self):
        return {"monthly_usage": 100 * FakeBackend.calls["predict"], "monthly_limit": 10_000}

    def fit(self, X, y):
        FakeBackend.calls["fit"] += 1
        return {"fitted_train_set_id": "fake", "classes": [0, 1]}

    def predict(self, X, before_dispatch):
        before_dispatch()
        FakeBackend.calls["predict"] += 1
        p = np.full(len(X), 0.6)
        return {"probabilities": np.column_stack([1 - p, p]), "classes": [0, 1], "metadata": {"fake": True}}


def job_for(X_train, y, X_query):
    return {"job": "pilot__base__2019__seed0", "stage": "pilot", "arm": "base", "season": 2019, "seed": 0,
            "columns": list(X_train.columns), "fingerprint": T.fingerprint(X_train, y, X_query)}


def test_guard_predicts_once_and_reuses(tmp_path):
    rng = np.random.default_rng(0)
    X_train = pd.DataFrame(rng.normal(size=(30, 3)), columns=["a", "b", "c"])
    y = rng.integers(0, 2, 30)
    X_query = pd.DataFrame(rng.normal(size=(10, 3)), columns=["a", "b", "c"])
    job = job_for(X_train, y, X_query)
    FakeBackend.calls = {"fit": 0, "predict": 0}
    r1 = G.execute_job(job, X_train, y, X_query, fingerprint=T.fingerprint, root=tmp_path, backend_factory=FakeBackend)
    r2 = G.execute_job(job, X_train, y, X_query, fingerprint=T.fingerprint, root=tmp_path, backend_factory=FakeBackend)
    assert not r1["reused"] and r2["reused"] and FakeBackend.calls["predict"] == 1
    assert np.allclose(r2["p_a"], 0.6)
    done = json.loads((tmp_path / job["job"] / "COMPLETE.json").read_text())
    assert done["status"] == "COMPLETE"


def test_guard_refuses_unknown_outcome_and_wrong_inputs(tmp_path):
    rng = np.random.default_rng(1)
    X_train = pd.DataFrame(rng.normal(size=(30, 3)), columns=["a", "b", "c"])
    y = rng.integers(0, 2, 30)
    X_query = pd.DataFrame(rng.normal(size=(10, 3)), columns=["a", "b", "c"])
    job = job_for(X_train, y, X_query)
    d = tmp_path / job["job"]
    d.mkdir(parents=True)
    (d / "predict_slot.json").write_text("{}")
    with pytest.raises(G.OnceOnlyError):
        G.execute_job(job, X_train, y, X_query, fingerprint=T.fingerprint, root=tmp_path, backend_factory=FakeBackend)
    with pytest.raises(ValueError):
        G.execute_job(job, X_train, y, X_query * 2, fingerprint=T.fingerprint, root=tmp_path / "other",
                      backend_factory=FakeBackend)


def tiny_frame(seasons=(2020, 2021, 2022), n=40, seed=5):
    rng = np.random.default_rng(seed)
    parts = []
    for s in (2018, 2019) + tuple(seasons):
        k = n
        parts.append(pd.DataFrame({
            "match_id": [f"{s}-{i}" for i in range(k)], "tour": np.where(np.arange(k) % 2, "atp", "wta"),
            "season": s, "a_won": rng.integers(0, 2, k).astype(bool), "p_mkt": rng.uniform(0.2, 0.8, k),
            "tournament_date": pd.Timestamp(f"{s}-03-01") + pd.to_timedelta(rng.integers(0, 200, k), "D"),
            "x_odds_logit": rng.normal(0, 1, k), "x_surface": rng.integers(0, 3, k).astype(float),
            "season_n_a": rng.integers(0, 6, k).astype(float), "season_n_b": rng.integers(0, 6, k).astype(float),
            "debut_season": False, "x_f": rng.normal(0, 1, k)}))
    return pd.concat(parts, ignore_index=True)


def fake_jobs_and_predictions(frame, root, stage, arms_seeds, seasons):
    """Register jobs on a toy frame and fill their receipts through the guard with a fake backend."""
    jobs = []
    for arm, seed in arms_seeds:
        for s in seasons:
            tr = frame["season"].between(2018, s - 1).to_numpy()
            te = (frame["season"] == s).to_numpy()
            X_train = frame.loc[tr, ["x_f"]].reset_index(drop=True)
            X_test = frame.loc[te, ["x_f"]].reset_index(drop=True)
            X_query = pd.concat([X_test, -X_test], ignore_index=True)
            y = frame.loc[tr, "a_won"].astype("int64").to_numpy()
            j = {"job": f"{stage}__{arm}__{s}__seed{seed}", "stage": stage, "arm": arm, "season": s, "seed": seed,
                 "columns": ["x_f"], "fingerprint": T.fingerprint(X_train, y, X_query),
                 "train_rows": int(len(X_train)), "query_rows": int(len(X_query))}
            jobs.append(j)
            G.execute_job(j, X_train, y, X_query, fingerprint=T.fingerprint, root=root, backend_factory=FakeBackend)
    return jobs


def test_scorer_uses_seeds_common_to_both_arms_and_keeps_every_season(tmp_path, monkeypatch):
    from src.eda.surface_elo_pieces import score as S
    monkeypatch.setattr(S.C, "TRAIN_FROM", 2018)
    frame = tiny_frame()
    seasons = [2020, 2021, 2022]
    jobs = fake_jobs_and_predictions(frame, tmp_path, "confirm", [("base", 0), ("base", 1), ("primary", 0),
                                                                   ("primary", 1)], seasons)
    # lose one primary seed-1 job: the endpoint must fall back to seed 0 for BOTH arms, with every season kept
    import shutil
    shutil.rmtree(tmp_path / "confirm__primary__2021__seed1")
    jobs = [j for j in jobs if j["job"] != "confirm__primary__2021__seed1"]
    f, avail, ss = S.load("confirm", root=tmp_path, frame=frame, jobs=jobs)
    assert S.common_seeds(avail, ["base", "primary"], ss) == [0]
    R, meta = S.score("confirm", f, avail, ss)
    r = R[(R["population"] == "excl_debut") & (R["tour"] == "both") & (R["window"] == "2020-2022")
          & (R["subset"] == "all") & (R["base"] == "base") & (R["model"] == "primary")]
    assert len(r) == 1 and r["matches"].iloc[0] == 3 * 40 and r["seeds"].iloc[0] == "0"
    # with every primary job of a season lost, the primary endpoint refuses to run
    jobs2 = [j for j in jobs if not (j["arm"] == "primary" and j["season"] == 2022)]
    for j in [j for j in jobs if j["arm"] == "primary" and j["season"] == 2022]:
        shutil.rmtree(tmp_path / j["job"])
    f2, avail2, ss2 = S.load("confirm", root=tmp_path, frame=frame, jobs=jobs2 + [j for j in jobs if j["arm"] == "primary" and j["season"] == 2022])
    with pytest.raises(SystemExit):
        S.score("confirm", f2, avail2, ss2)


def test_live_dispatch_needs_the_canonical_root(tmp_path):
    rng = np.random.default_rng(2)
    X_train = pd.DataFrame(rng.normal(size=(5, 2)), columns=["a", "b"])
    y = np.array([0, 1, 0, 1, 1])
    job = job_for(X_train, y, X_train)
    with pytest.raises(ValueError):
        G.execute_job(job, X_train, y, X_train, fingerprint=T.fingerprint, root=tmp_path)
