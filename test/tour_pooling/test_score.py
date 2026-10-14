"""Tests of the tour-pooling scorer (src/eda/tour_pooling/score.py).

Synthetic (tmp_path) unless named:
    * the fit loader reads a correct file and symmetrises it; it refuses wrong ids, a wrong training shape, wrong
      columns, another frame, a block that is not stored-then-swapped, a file whose meta is another job's;
    * borrowsim: refused without its similarity cache (none is built) and when the fit carries another cache's hash;
    * completeness: an arm with one file missing is not complete;
    * the arm list: the runner's reproduction file is not an arm; sizectl is a control, never a select candidate;
      select and the winner's luck wait for all six candidates;
    * the sealed filter never returns a match on or after 29 Jul 2026 (also on the instance's frame, which has some);
    * the composites: blend recovers planted coefficients and its own-tour share w; blend_control pairs pooled seed
      4 + k with seed k; select reads earlier seasons only;
    * the post-hoc controls (pooled8, avg_split_pooled): eight fits averaged in log-odds, pseudo-seed k the pair k; their
      two stages are compare.py's recipe (staged_mean equals staged on a model's own seed mean); never candidates;
    * the reporting path (comparisons, contrasts, post-hoc rows, realisation, forecast table, printout, JSON) and the
      winner's luck;
    * question 2 is labelled the explicit tour flag's value (red team B2), never the tour input's value;
    * real data: a per-tour arm assembled from the instance's own fits equals the instance's seed table; the runner's
      reproduction check passes on a copy of the instance's 2022 fit and fails on a perturbed one.

Run: ./python.sh -m pytest test/tour_pooling/test_score.py -q
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

from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.tour_pooling import common as C  # noqa: E402
from src.eda.tour_pooling import score as S  # noqa: E402

SHA = "f" * 64


def toy_frame() -> pd.DataFrame:
    """Seasons 2013-2020, two men's and three women's matches a season, the tours interleaved."""
    rows = [{"match_id": f"{t}{s}_{i}", "season": s, "tour": t}
            for s in range(2013, 2021) for t, n in (("atp", 2), ("wta", 3)) for i in range(n)]
    return pd.DataFrame(rows).sample(frac=1, random_state=0).reset_index(drop=True)


def write_fit(path: Path, frame: pd.DataFrame, arm: str, tour: str, season: int, seed: int, p=None, ids=None,
              cols=None, shape=None, sha: str = SHA, meta_seed: int | None = None, sim_sha: str | None = None) -> Path:
    """A fit file as fits.py writes it, every field right unless overridden (borrowsim: common.sim_inclusion must
    answer, as the tests' stand-in does)."""
    if ids is None:
        ids = frame.loc[C.query_mask(frame, tour, season), "match_id"].to_numpy()
    if p is None:
        p = np.random.default_rng(seed).uniform(0.05, 0.95, 2 * len(ids))
    cols = C.inputs(arm) if cols is None else cols
    tr = C.train_mask(frame, arm, tour, season, seed)
    by = {f"{t} {int(s)}": int(v) for (t, s), v in frame.loc[tr].groupby(["tour", "season"]).size().items()}
    shape = [int(tr.sum()), len(cols)] if shape is None else shape
    k = seed if meta_seed is None else meta_seed
    meta = {"arm": arm, "tour": tour, "season": season, "seed": k, "config": {**C.SC.CONFIG, "random_state": k},
            "columns": list(cols), "train_shape": shape, "train_rows_by_tour_season": by,
            "draw": {"sim_cache_sha256": sim_sha}, "model_frame_sha256": sha}
    np.savez(path, meta=np.asarray(json.dumps(meta)), p_td=np.asarray(p, float), ids_td=np.asarray(ids).astype(str))
    return path


# ------------------------------------------------------------------------------------------------
# The loader

def test_a_correct_file_is_read_and_symmetrised(tmp_path):
    frame = toy_frame()
    p = np.array([0.6, 0.3, 0.45, 0.8])                     # two men's matches of 2020: as stored, then swapped
    path = write_fit(tmp_path / "f.npz", frame, "split", "atp", 2020, 0, p=p)
    s = S.read_fit(path, frame, "split", "atp", 2020, 0, SHA)
    assert s.index.tolist() == frame.loc[C.query_mask(frame, "atp", 2020), "match_id"].tolist()
    np.testing.assert_allclose(s.to_numpy(), [0.575, 0.25], rtol=0, atol=1e-15)   # (p + 1 - p_swapped) / 2


@pytest.mark.parametrize("arm,tour", [("split", "wta"), ("borrow25", "atp"), ("borrow50", "wta"), ("notour", "both"),
                                      ("aligned", "both"), ("sizectl", "atp"), ("sizectl", "wta")])
def test_every_arm_layout_passes_its_own_checks(tmp_path, arm, tour):
    frame = toy_frame()
    path = write_fit(tmp_path / "f.npz", frame, arm, tour, 2019, 2)
    s = S.read_fit(path, frame, arm, tour, 2019, 2, SHA)
    assert len(s) == int(C.query_mask(frame, tour, 2019).sum())


def test_wrong_ids_are_refused(tmp_path):
    frame = toy_frame()
    ids = frame.loc[C.query_mask(frame, "wta", 2020), "match_id"].to_numpy()
    for bad in (ids[::-1],                                               # out of frame order
                frame.loc[C.query_mask(frame, "atp", 2020), "match_id"].to_numpy(),   # the other tour's
                ids[:-1]):                                               # one missing
        path = write_fit(tmp_path / "f.npz", frame, "split", "wta", 2020, 0, ids=bad)
        with pytest.raises(RuntimeError, match="td ids"):
            S.read_fit(path, frame, "split", "wta", 2020, 0, SHA)


def test_a_wrong_training_shape_is_refused(tmp_path):
    frame = toy_frame()
    n = int(C.train_mask(frame, "borrow25", "atp", 2020, 1).sum())
    for shape in ([n + 1, 58], [n, 57], [int(C.pool_mask(frame, 2020).sum()), 58]):   # the last: pooled's rows
        path = write_fit(tmp_path / "f.npz", frame, "borrow25", "atp", 2020, 1, shape=shape)
        with pytest.raises(RuntimeError, match="training shape"):
            S.read_fit(path, frame, "borrow25", "atp", 2020, 1, SHA)


def test_wrong_columns_are_refused(tmp_path):
    frame = toy_frame()
    cols = C.inputs("split")
    for bad in (C.inputs("notour"), cols[::-1], cols + ["spd_f"]):
        path = write_fit(tmp_path / "f.npz", frame, "split", "atp", 2020, 0, cols=bad, shape=[14, 58])
        with pytest.raises(RuntimeError, match="columns"):
            S.read_fit(path, frame, "split", "atp", 2020, 0, SHA)
    path = write_fit(tmp_path / "f.npz", frame, "notour", "both", 2020, 0, cols=cols,
                     shape=[int(C.pool_mask(frame, 2020).sum()), 57])         # notour must not carry `tour`
    with pytest.raises(RuntimeError, match="columns"):
        S.read_fit(path, frame, "notour", "both", 2020, 0, SHA)


def test_another_frame_a_bad_block_and_another_jobs_file_are_refused(tmp_path):
    frame = toy_frame()
    path = write_fit(tmp_path / "f.npz", frame, "split", "atp", 2020, 0, sha="0" * 64)
    with pytest.raises(RuntimeError, match="another frame"):
        S.read_fit(path, frame, "split", "atp", 2020, 0, SHA)
    path = write_fit(tmp_path / "f.npz", frame, "split", "atp", 2020, 0, p=[0.5, 0.5, 0.5, 0.5, 0.5])
    with pytest.raises(RuntimeError, match="stored, then swapped"):
        S.read_fit(path, frame, "split", "atp", 2020, 0, SHA)
    path = write_fit(tmp_path / "f.npz", frame, "split", "atp", 2020, 0, meta_seed=1)
    with pytest.raises(RuntimeError, match="differ from the file's"):
        S.read_fit(path, frame, "split", "atp", 2020, 0, SHA)
    with pytest.raises(RuntimeError, match="differ from the file's"):      # a split file read as borrow50's
        S.read_fit(write_fit(tmp_path / "f.npz", frame, "split", "atp", 2020, 0), frame, "borrow50", "atp", 2020,
                   0, SHA)


def test_borrowsim_is_refused_without_its_cache_or_with_another_caches_hash(tmp_path, monkeypatch):
    sim = tmp_path / "borrow_sim_v3"
    monkeypatch.setattr(C, "SIM", sim)
    frame = toy_frame()
    other = C.pool_mask(frame, 2020) & (frame["tour"] != "atp").to_numpy()
    pi = pd.DataFrame({"match_id": frame.loc[other, "match_id"].to_numpy(), "pi": 0.5})
    monkeypatch.setattr(C, "sim_inclusion", lambda f, tour, season: pi)    # stands in for the record-checked reader
    path = write_fit(tmp_path / "f.npz", frame, "borrowsim", "atp", 2020, 0, sim_sha="0" * 64)
    with pytest.raises(RuntimeError, match="similarity cache .* is missing"):
        S.read_fit(path, frame, "borrowsim", "atp", 2020, 0, SHA)
    assert not sim.exists()                                  # the scorer never builds a cache
    sim.mkdir()
    pi.to_parquet(C.sim_path("atp", 2020), index=False)
    with pytest.raises(RuntimeError, match="another similarity cache"):
        S.read_fit(path, frame, "borrowsim", "atp", 2020, 0, SHA)
    path = write_fit(tmp_path / "f.npz", frame, "borrowsim", "atp", 2020, 0,
                     sim_sha=C.sha256_file(C.sim_path("atp", 2020)))
    assert len(S.read_fit(path, frame, "borrowsim", "atp", 2020, 0, SHA)) == 2


def test_an_arm_with_a_missing_file_is_not_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "FITS", tmp_path)
    need = S.needed("split")
    assert len(need) == 2 * 8 * 4 and len(S.needed("notour")) == 8 * 4 and len(S.needed("sizectl")) == 2 * 8 * 4
    for t, Y, k in need[:-1]:
        C.fit_path("split", t, Y, k).write_bytes(b"")
    st = S.status("split")
    assert not st["complete"] and st["files_present"] == len(need) - 1 and st["first_missing"] == [list(need[-1])]
    C.fit_path("split", *need[-1]).write_bytes(b"")
    assert S.status("split")["complete"]


def test_the_reproduction_file_is_no_arm_and_sizectl_is_a_control():
    assert "pooled" in C.ARMS and "pooled" not in S.ARMS          # it would overwrite the yardstick (red team S8)
    assert "sizectl" in S.ARMS and "sizectl" in S.CONTROLS
    assert "sizectl" not in S.SELECT_POOL and "sizectl" not in S.LUCK and "sizectl" not in S.BORROWING
    assert set(S.POSTHOC_CONTROLS).isdisjoint(S.SELECT_POOL + S.LUCK + S.ARMS + S.BORROWING)
    assert S.select_missing({"pooled": 1, "split": 1, "notour": 1, "sizectl": 1, "pooled8": 1}) == \
        ["borrow25", "borrow50", "borrowsim", "aligned"]
    assert S.select_missing({m: 1 for m in S.SELECT_POOL}) == []


# ------------------------------------------------------------------------------------------------
# The sealed holdout

def test_the_sealed_filter_never_returns_a_match_on_or_after_29_july_2026(tmp_path):
    days = ["2019-01-01", "2026-07-20", "2026-07-28", "2026-07-29", "2026-08-03", "2026-12-28", "2027-01-04"]
    f = pd.DataFrame({"match_id": [f"m{i}" for i in range(len(days))], "a_won": [1, 0, 1, 0, 1, 0, 1],
                      "tournament_date": pd.to_datetime(days)})
    f.to_parquet(tmp_path / "f.parquet", index=False)
    y = S.outcomes(tmp_path / "f.parquet")
    assert y.index.tolist() == ["m0", "m1", "m2"] and y.tolist() == [1.0, 0.0, 1.0]


def test_the_sealed_filter_on_the_instance_frame():
    path = C.INSTANCE / "model_frame.parquet"
    d = pd.read_parquet(path, columns=["match_id", "tournament_date"])
    sealed = d["tournament_date"] >= S.SEALED_FROM
    assert sealed.sum() > 0                                  # the frame holds sealed matches: the filter is tested
    y = S.outcomes(path)
    assert len(y) == int((~sealed).sum()) and set(y.index) == set(d.loc[~sealed, "match_id"].astype(str))


# ------------------------------------------------------------------------------------------------
# The composites, the reporting path and the winner's luck

def synthetic_info(n_per: int = 4000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for season in range(2019, 2024):
        for tour in ("atp", "wta"):
            days = pd.Timestamp(f"{season}-01-07") + pd.to_timedelta(rng.integers(0, 330, n_per), unit="D")
            rows.append(pd.DataFrame({"tour": tour, "season": season, "tournament_date": days, "debut": False}))
    info = pd.concat(rows, ignore_index=True)
    info.index = pd.Index([f"m{i}" for i in range(len(info))], name="match_id")
    info["block"] = C.SC.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.SC.blocks(info["tournament_date"].to_numpy(), 7)
    return info


def test_blend_recovers_planted_coefficients_and_the_own_tour_share():
    rng = np.random.default_rng(1)
    info = synthetic_info()
    n = len(info)
    base = rng.normal(0, 1.2, n)
    e_split, e_pool = base + rng.normal(0, 0.5, n), base + rng.normal(0, 0.5, n)
    atp = (info["tour"] == "atp").to_numpy()
    z = pd.Series(np.where(atp, rng.normal(0, 1, n), 0.0), index=info.index)
    a, c, b = np.where(atp, 0.6, 0.2), np.where(atp, 0.4, 0.8), 0.3
    info["y"] = (rng.random(n) < expit(a * e_split + c * e_pool + b * z.to_numpy())).astype(float)
    noise = lambda e: pd.DataFrame(expit(e[:, None] + rng.normal(0, 0.02, (n, 4))), index=info.index,  # noqa: E731
                                   columns=list(C.SEEDS))
    p_split, p_pool = noise(e_split), noise(e_pool)
    fc, rows = S.blend(info, z, p_split, p_pool)
    last = {r["tour"]: r for r in rows if r["stage"] == "both stages" and r["season"] == 2023}
    assert last["atp"]["a"] == pytest.approx(0.6, abs=0.08) and last["atp"]["c"] == pytest.approx(0.4, abs=0.08)
    assert last["wta"]["a"] == pytest.approx(0.2, abs=0.08) and last["wta"]["c"] == pytest.approx(0.8, abs=0.08)
    assert last["atp"]["w"] == pytest.approx(0.6, abs=0.06) and last["wta"]["w"] == pytest.approx(0.2, abs=0.06)
    for r in last.values():                                  # w = a / (a + c); its SE finite, below a's and c's
        assert r["w"] == pytest.approx(r["a"] / (r["a"] + r["c"])) and 0 < r["se_w"] < max(r["se_a"], r["se_c"])
        assert r["a_model"] == "split" and r["composite"] == "blend"
    r = last["atp"]
    assert r["b_mle"] == pytest.approx(0.3, abs=0.05) and r["b"] == pytest.approx(S.shrink(r["b_mle"], r["se_b"]))
    i = int(np.flatnonzero((info["season"] == 2023).to_numpy() & atp)[0])        # seed 2 of a 2023 man, by hand
    want = expit(r["a"] * C.SC.lg(p_split.iloc[i, 2]) + r["c"] * C.SC.lg(p_pool.iloc[i, 2]) + r["b"] * z.iloc[i])
    assert fc.qk[i, 2] == pytest.approx(want, rel=1e-12)
    assert np.isnan(fc.q[(info["season"] == 2019).to_numpy()]).all()             # 2019 only feeds the fits
    # b touches men's rows only and no coefficient is shared across tours, so women's two stages coincide (as
    # compare.walk_forward's s_wta does)
    women = (info["season"] == 2023).to_numpy() & ~atp
    assert np.allclose(fc.q[women], fc.q1[women], rtol=0, atol=1e-7)
    men = (info["season"] == 2023).to_numpy() & atp
    assert not np.allclose(fc.q[men], fc.q1[men], rtol=0, atol=1e-3)


def test_blend_control_pairs_pooled_seed_4_plus_k_with_seed_k():
    p47 = pd.DataFrame(np.arange(8).reshape(2, 4) / 10 + 0.1, index=["m0", "m1"], columns=[4, 5, 6, 7])
    t = S.control_table(p47)
    assert list(t.columns) == list(C.SEEDS) and np.array_equal(t.to_numpy(), p47.to_numpy())
    with pytest.raises(RuntimeError):
        S.control_table(p47[[5, 4, 6, 7]])


def test_post_hoc_controls_average_eight_fits_in_log_odds_with_pseudo_seeds_paired_by_k():
    idx = pd.Index(["m0", "m1", "m2"], name="match_id")
    rng = np.random.default_rng(4)
    a = pd.DataFrame(rng.uniform(0.1, 0.9, (3, 4)), index=idx, columns=list(C.SEEDS))
    b = pd.DataFrame(rng.uniform(0.1, 0.9, (3, 4)), index=idx, columns=list(C.SEEDS))
    eta, eta_k = S.logodds_mean(a, b, idx)
    la, lb = C.SC.lg(a.to_numpy()), C.SC.lg(b.to_numpy())
    np.testing.assert_allclose(eta_k.to_numpy(), (la + lb) / 2, rtol=0, atol=1e-15)       # pseudo-seed k: a_k with b_k
    np.testing.assert_allclose(eta.to_numpy(), np.hstack([la, lb]).mean(axis=1), rtol=0, atol=1e-15)   # the eight
    with pytest.raises(RuntimeError):
        S.logodds_mean(a, b.iloc[:2], idx)                   # a match without the second model's forecast
    with pytest.raises(RuntimeError):
        S.logodds_mean(a, b.set_axis([4, 5, 6, 7], axis=1), idx)


def test_staged_mean_is_compares_recipe_on_a_model_given_in_log_odds():
    """Fed a model's own seed-mean logit and seed logits, staged_mean must give staged's (compare.py's) forecasts and
    coefficients: the post-hoc controls differ from any model only in how their eight fits are averaged."""
    rng = np.random.default_rng(5)
    info = synthetic_info(n_per=1500)
    n = len(info)
    eta0 = rng.normal(0, 1, n)
    info["y"] = (rng.random(n) < expit(0.9 * eta0)).astype(float)
    z = pd.Series(np.where((info["tour"] == "atp").to_numpy(), rng.normal(0, 1, n), 0.0), index=info.index)
    p = pd.DataFrame(expit(eta0[:, None] + rng.normal(0, 0.05, (n, 4))), index=info.index, columns=list(C.SEEDS))
    want, par_want = S.staged(p, info, z)
    eta = pd.Series(C.SC.lg(p.mean(axis=1).to_numpy()), index=info.index)
    got, par_got = S.staged_mean(eta, pd.DataFrame(C.SC.lg(p.to_numpy()), index=info.index, columns=list(C.SEEDS)),
                                 info, z)
    assert par_got == par_want
    for g, w in ((got.q, want.q), (got.qk, want.qk), (got.q1, want.q1), (got.q1k, want.q1k)):
        np.testing.assert_allclose(g, w, rtol=0, atol=1e-12, equal_nan=True)


def test_select_reads_earlier_seasons_only():
    info = synthetic_info(n_per=300)
    rng = np.random.default_rng(2)
    y = (rng.random(len(info)) < 0.5).astype(float)
    info["y"] = y
    season = info["season"].to_numpy()

    def model(q):
        qk = np.repeat(q[:, None], 4, axis=1)
        return S.Fc(q.copy(), qk.copy(), q.copy(), qk.copy())

    pooled = model(np.full(len(info), 0.5))
    good = np.where(y == 1, 0.8, 0.2)
    split_q = np.where(season == 2022, np.where(y == 1, 0.05, 0.95), good)       # good until 2022, then awful
    models = {"pooled": pooled, "split": model(split_q)}
    fc, rows, src = S.select(info, models, ["pooled", "split"])
    chosen = {(r["tour"], r["season"]): r["chosen"] for r in rows}
    for t in ("atp", "wta"):
        assert chosen[(t, 2020)] == "pooled"                  # nothing earlier to choose on
        assert chosen[(t, 2021)] == "split" and chosen[(t, 2022)] == "split"   # 2022's own result is not read
        assert chosen[(t, 2023)] == "pooled"                  # 2020-2022 now favour pooled
    m22 = season == 2022
    assert np.array_equal(fc.q[m22], split_q[m22]) and set(src[m22]) == {"split"}


def test_the_reporting_path_runs_on_synthetic_forecasts(capsys):
    """comparisons, contrasts, realisation, the winner's luck, the forecast table, the printout and the JSON cleaning,
    end to end on synthetic forecasts: a candidate equal to its base reads exactly 0."""
    rng = np.random.default_rng(3)
    info = synthetic_info(n_per=400)
    info = pd.concat([info, synthetic_info(n_per=400, seed=9).assign(season=lambda d: d["season"] + 3)])
    info.index = pd.Index([f"m{i}" for i in range(len(info))], name="match_id")
    info["level"] = rng.choice(["Slams", "1000s", "500s", "250s", "Finals"], len(info))
    info["y"] = (rng.random(len(info)) < 0.5).astype(float)
    info["p_cand"] = rng.uniform(0.2, 0.8, len(info))
    n = len(info)
    test = info["season"].isin(S.TEST).to_numpy()

    def model(shift):
        fc = S.Fc.empty(n)
        qk = expit(C.SC.lg(info["p_cand"].to_numpy())[:, None] + shift + rng.normal(0, 0.05, (n, 4)))
        fc.qk[test], fc.q[test] = qk[test], qk[test].mean(axis=1)
        fc.q1k[test], fc.q1[test] = qk[test], qk[test].mean(axis=1)
        return fc

    pooled, split = model(0.0), model(0.1)
    models = {"pooled": pooled, "split": split, "borrow50": model(0.05), "sizectl": pooled, "blend": split,
              "blend_control": model(0.02)}
    close_fc = S.Fc.empty(n, 1)
    close_fc.q[test] = info["p_cand"].to_numpy()[test]
    close_fc.qk[test] = close_fc.q[test][:, None]
    candidates = [m for m in models if m != "pooled"]
    posthoc = {"pooled8": model(0.01), "avg_split_pooled": model(0.05)}
    scores = pd.DataFrame(S.comparisons(info, models, close_fc, model(-0.1), candidates) + S.contrasts(info, models)
                          + S.posthoc_rows(info, models, posthoc))
    ph = scores[scores["role"] == S.POSTHOC]
    assert len(ph) == 3 * 2 * 3 and ph["group"].eq("primary").all() and set(ph["population"]) == {
        "both tours", "men", "women"}
    assert {(r.comparison, r.base, r.arm) for r in ph.itertuples()} == {
        (S.P8, "pooled", "pooled8"), (S.AVG8, "pooled8", "avg_split_pooled"), (S.AVG, "pooled", "avg_split_pooled")}
    assert (scores.loc[scores["arm"].isin(S.POSTHOC_CONTROLS), "role"] == S.POSTHOC).all()   # only in their rows
    assert {"window", "group", "population", "comparison", "base", "arm", "estimate", "lo", "hi", "reading"} <= \
        set(scores.columns)
    same = scores[(scores["arm"] == "sizectl") & (scores["base"] == "pooled")]    # sizectl here is pooled itself
    assert len(same) and (same[["estimate", "lo", "hi"]] == 0).all().all()
    assert set(scores.loc[scores["base"] == "reference", "window"]) == {"W2"}
    pairs = {(r["comparison"], r["base"], r["arm"]) for _, r in scores.iterrows()}
    assert {(S.SIZE, "sizectl", "pooled"), (S.MIX, "sizectl", "split"), (S.VS_SPLIT, "split", "borrow50"),
            (S.VS_CONTROL, "blend_control", "blend")} <= pairs
    contrast = scores[scores["comparison"].isin([S.SIZE, S.MIX, S.VS_SPLIT, S.VS_CONTROL])]
    assert len(contrast) == 4 * 2 * 3 and set(contrast["population"]) == {"both tours", "men", "women"}
    size = contrast[contrast["comparison"] == S.SIZE]
    assert (size[["estimate", "lo", "hi"]] == 0).all().all()                  # pooled against its own copy
    real = pd.DataFrame(S.realisation_rows(info, models, close_fc))
    assert set(real["model"]) == set(models) and real["c"].notna().all()
    luck = S.winners_luck(scores)
    assert luck["best"] in ("borrow50", "blend") and not luck["complete_search"]
    table = S.forecast_table(info, {**models, **posthoc}, close_fc, None)
    assert len(table) == n and {"q_blend_control", "q1_blend_control", "q_blend_control_s3", "q_close", "match_id",
                                "q_pooled8", "q1_pooled8", "q_pooled8_s0", "q_avg_split_pooled",
                                "q1_avg_split_pooled", "q_avg_split_pooled_s3"} <= set(table.columns)
    S.print_primary(scores, candidates)
    out = capsys.readouterr().out
    assert "contrast" in out and "post-hoc control" in out and "avg_split_pooled" in out
    json.dumps(S.clean({"a": np.float64(np.nan), "b": [np.int64(2), (np.bool_(True), 1.5)]}), allow_nan=False)


def test_winners_luck_takes_the_best_of_the_declared_six():
    rows = [{"window": "W1", "population": "both tours", "comparison": S.VS_POOLED, "arm": a, "estimate": e, "se": s}
            for a, e, s in (("borrow25", 0.10, 0.2), ("blend", 0.30, 0.1), ("split", 0.9, 0.1),
                            ("sizectl", 1.5, 0.1), ("blend_control", 2.0, 0.1))]       # the last three: not of the 6
    out = S.winners_luck(pd.DataFrame(rows))
    assert out["best"] == "blend" and out["sel"] == pytest.approx(0.127)
    assert out["estimate_minus_sel"] == pytest.approx(0.30 - 0.127) and not out["complete_search"]


def test_question_2_is_the_explicit_flags_value_never_the_tour_inputs():
    rows = [{"window": "W1", "population": "both tours", "comparison": S.VS_POOLED, "arm": "notour", "matches": 100,
             "estimate": -0.2, "lo": -0.5, "hi": 0.1, "se": 0.15, "p_better": 0.1, "reading": "unresolved"},
            {"window": "W1", "population": "both tours", "comparison": S.VS_POOLED, "arm": "split", "matches": 100,
             "estimate": 0.3, "lo": 0.1, "hi": 0.5, "se": 0.1, "p_better": 0.99, "reading": "better"}]
    d = S.declared_primaries(pd.DataFrame(rows), ["borrow25", "aligned"])
    assert "tour input" not in json.dumps(S.clean(d)).lower()
    assert "indoor is missing on every women's match" in S.FLAG and "box-score scales differ" in S.FLAG
    flag = d[f"question 2: {S.FLAG}"]
    assert (flag["estimate"], flag["lo"], flag["hi"]) == pytest.approx((0.2, -0.1, 0.5))
    assert flag["p_better"] == pytest.approx(0.9) and flag["reading"] == "unresolved"
    assert d["question 1: split"]["reading"] == "better"
    assert d["question 3: select"].startswith("not scored") and "borrow25, aligned" in d["question 3: select"]


# ------------------------------------------------------------------------------------------------
# Real data: the per-tour assembly and the runner's reproduction

def test_a_per_tour_arm_rebuilt_from_the_instances_fits_assembles_to_the_instance(tmp_path, monkeypatch):
    """The instance's own forecasts, cut into per-tour files in the arms' layout, must come back as its seed table."""
    monkeypatch.setattr(C, "FITS", tmp_path)
    frame = C.load_frame()
    sha = C.sha256_file(C.P.model_frame)
    seasons = (2025, 2026)
    fx = F.FrameIndex(frame[["match_id", "season"]])
    want, _ = F.seed_table("model", seasons, C.SEEDS, fx, C.P, "td", require_checks=False)
    for Y in seasons:
        for k in C.SEEDS:
            with np.load(C.P.local / f"model__{Y}__seed{k}.npz", allow_pickle=False) as z:
                p, ids = z["p_td"], z["ids_td"].astype(str)
            n = len(ids)
            tours = frame.set_index("match_id").loc[ids, "tour"].to_numpy()
            for t in C.TOURS:
                m = tours == t
                write_fit(C.fit_path("split", t, Y, k), frame, "split", t, Y, k, p=np.r_[p[:n][m], p[n:][m]],
                          ids=ids[m], sha=sha)
    got = S.arm_table("split", frame, sha, seasons=seasons)
    assert got.shape == want.shape
    pd.testing.assert_frame_equal(got.reindex(want.index), want, check_exact=True, check_names=False)


def test_the_runner_reproduction_compares_raw_p_td_with_the_instances_stored_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "FITS", tmp_path)
    frame = C.load_frame()
    sha = C.sha256_file(C.P.model_frame)
    assert S.runner_reproduction(frame, sha)["passed"] is None             # not written yet: not a failure
    with np.load(C.INSTANCE / "fits" / "model__2022__seed0.npz", allow_pickle=False) as z:
        p, ids = z["p_td"].astype(float), z["ids_td"].astype(str)
    path = C.fit_path(*S.REPRO)
    write_fit(path, frame, "pooled", "both", 2022, 0, p=p, ids=ids, sha=sha)
    r = S.runner_reproduction(frame, sha)
    assert r["passed"] is True and r["ids_equal"] and r["max_abs_diff_p_td"] == 0 and r["values"] == len(p)
    write_fit(path, frame, "pooled", "both", 2022, 0, p=p * (1 - 1e-5), ids=ids, sha=sha)
    r = S.runner_reproduction(frame, sha)
    assert r["passed"] is False and 1e-6 < r["max_abs_diff_p_td"] < 1e-5
    write_fit(path, frame, "pooled", "both", 2022, 0, p=p, ids=ids, sha="0" * 64)   # its own checks come first
    r = S.runner_reproduction(frame, sha)
    assert r["passed"] is False and r["status"].startswith("refused")
