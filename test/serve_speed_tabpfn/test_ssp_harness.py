"""Tests of the serve-speed study's harness (the integration strategist's build, audit C7 T-H1 to T-H7), on a synthetic
stand-in world in a temporary folder: a fake model frame (with a_won, so that reading it would be caught), Stage 0
players, an early-price frame, a feature file with its probe record and saved base fits in a fake feature-interactions
and a fake rating-race folder. The real study paths are never written; the real feature file is never read.

    T-H1  flip is an involution with NaN; the 58 base columns hash-equal the frame's; the feature join is one-to-one
    T-H2  the job list is the 223 planned jobs
    T-H3  the reproduction comparison and the reuse gate; the real fingerprint / reproduction checks when present
    T-H4  calibration and nudge read seasons < Y only
    T-H5  every comparison's two seed sets are equal; calibration uses seeds 0-3
    T-H6  --synthetic never selects a_won
    T-H7  --check writes the population hash and counts without outcomes
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

from src.eda.serve_speed_tabpfn import arms as A  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.serve_speed_tabpfn import local_fits as L  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

N_PER_TOUR = 400
SEASONS = range(2013, 2027)


# ------------------------------------------------------------------------------------------------
# The stand-in world

def make_world(root: Path, seed: int = 0) -> C.Paths:
    rng = np.random.default_rng(seed)
    P = C.Paths(out=root / "out", local=root / "out" / "local", checks=root / "out" / "checks",
                features=root / "out" / "features", model_frame=root / "model_frame.parquet",
                model_inputs=C.DEFAULT.model_inputs, fi_local=root / "fi_local", race_local=root / "race_local",
                early=root / "early.parquet", stage0_pre=root / "stage0.parquet", prereg=root / "prereg.md",
                panel=root / "speed_panel.parquet", features_py=root / "features.py")
    P.panel.write_bytes(b"stand-in panel")
    P.features_py.write_text("# stand-in builder\n", encoding="utf-8")
    names, kinds, _ = A.base_inputs(P)
    rows = []
    for s in SEASONS:
        for tour in C.TOURS:
            for i in range(N_PER_TOUR):
                rows.append({"match_id": f"{tour}|{s}|{i:04d}", "tour": tour, "season": s,
                             "tournament_date": pd.Timestamp(f"{s}-01-06") + pd.Timedelta(days=7 * (i % 40))})
    f = pd.DataFrame(rows)
    n = len(f)
    eta = rng.normal(0, 1.2, n)
    f["a_won"] = (rng.random(n) < expit(0.9 * eta)).astype(bool)
    f["p_mkt"] = expit(eta)
    f["debut_season"] = rng.random(n) < 0.002
    for nm in names:
        v = rng.normal(size=n) if kinds[nm] != "context" else rng.integers(0, 3, n).astype(float)
        if nm == "indoor":
            v = np.where(f["tour"] == "wta", np.nan, v)
        f[f"in_{nm}"] = v
    f["in_odds_logit"] = eta
    f.to_parquet(P.model_frame, index=False)
    pool = rng.integers(0, 150, (n, 2))
    pd.DataFrame({"match_id": f["match_id"], "player_a_id": [f"p{a}" for a in pool[:, 0]],
                  "player_b_id": [f"p{(a + 1 + b) % 151}" for a, b in pool], "a_won": f["a_won"]}
                 ).to_parquet(P.stage0_pre, index=False)
    priced = f["season"].isin([2025, 2026]).to_numpy() & (rng.random(n) < 0.35)
    pd.DataFrame({"match_id": f["match_id"][priced], "tour": f["tour"][priced], "season": f["season"][priced],
                  "a_won": f["a_won"][priced], "has_early": True, "clean": rng.random(priced.sum()) < 0.5,
                  "all_early": True, "p_early_a": expit(eta[priced] + rng.normal(0, 0.2, priced.sum())),
                  "p_close_a": expit(eta[priced] + rng.normal(0, 0.1, priced.sum()))}).to_parquet(P.early, index=False)
    atp = (f["tour"] == "atp").to_numpy()
    spd = np.clip(rng.normal(0, 1, n), -4, 4)
    feat = pd.DataFrame({"match_id": f["match_id"], "spd_f": np.where(atp, spd, 0.0),
                         "spd_f_all": np.where(atp, spd, np.clip(rng.normal(0, 1, n), -4, 4) * (rng.random(n) < 0.2)),
                         "spd_raw": np.where(atp & (rng.random(n) < 0.5), spd + rng.normal(0, 0.3, n), np.nan),
                         "k28_a": rng.integers(0, 3, n), "k28_b": rng.integers(0, 3, n),
                         "last_age_a": rng.integers(0, 80, n), "last_age_b": rng.integers(0, 80, n),
                         "id_conflict": (~atp) & (rng.random(n) < 0.03)})
    P.features.mkdir(parents=True)
    feat.to_parquet(P.feature_file, index=False)
    C.write_json(P.feature_meta, {"probes": {"A": {"pass": True}, "B": {"pass": True}}, "probes_pass": True,
                                  "features_parquet_sha256": C.sha256_file(P.feature_file), "standin_panel": False,
                                  "reads_results": False, "panel_sha256": C.sha256_file(P.panel),
                                  "features_py_sha256": C.sha256_file(P.features_py)})
    A.write_registry(P)
    # saved base fits: seeds 0-2 in the "race" folder (sf_ names), 3-15 in the "feature interactions" folder
    sf = set(n for n in names if n.startswith(("iosO_", "iosD_", "prod_")))
    P.fi_local.mkdir()
    P.race_local.mkdir()
    priced_ids = set(pd.read_parquet(P.early, columns=["match_id"])["match_id"])
    for s in range(2019, 2027):
        k_rows = (f["season"] == s).to_numpy()
        ids = f["match_id"][k_rows].to_numpy().astype(str)
        n_train = int(f["season"].between(C.TRAIN_FROM, s - 1).sum())
        for k in range(16):
            noise = rng.normal(0, 0.02, k_rows.sum())
            payload = {"p_td": np.r_[expit(eta[k_rows] + noise), expit(-eta[k_rows] + noise)], "ids_td": ids}
            if s in C.PRICE_SEASONS:
                e_ids = np.array([i for i in ids if i in priced_ids])
                pe = expit(eta[pd.Index(f["match_id"]).get_indexer(e_ids)] + rng.normal(0, 0.02, len(e_ids)))
                payload.update({"p_early": np.r_[pe, 1 - pe], "ids_early": e_ids,
                                "p_late": np.r_[pe, 1 - pe], "ids_late": e_ids})
            race = k < 3
            cols = [f"sf_{c}" if (race and c in sf) else c for c in names]
            meta = {"arm": "model", "season": s, "seed": k, "columns": cols, "train_shape": [n_train, len(names)]}
            folder = P.race_local if race else P.fi_local
            np.savez(folder / f"model__{s}__seed{k}.npz", meta=np.asarray(json.dumps(meta)), **payload)
    return P


@pytest.fixture(scope="module")
def world(tmp_path_factory) -> C.Paths:
    return make_world(tmp_path_factory.mktemp("ssp_world"))


def outcomes(P: C.Paths, beta: float = 0.0, seed: int = 1) -> tuple[pd.DataFrame, pd.Series]:
    info = S.population(P)
    bank = S.Bank(P, S.frame_index(P), require_checks=False)
    eta = bank.eta("model", S.SEEDS16, S.HIST, "td").reindex(info.index).to_numpy()
    rng = np.random.default_rng(seed)
    y = pd.Series((rng.random(len(info)) < expit(0.9 * eta + beta * info["spd_f"].to_numpy())).astype(float),
                  index=info.index)
    return info, y


class ReadSpy:
    """Wraps pandas.read_parquet: records every call and fails on a_won or on reading every column of a file."""

    def __init__(self, real):
        self.real, self.calls = real, []

    def __call__(self, path, *args, columns=None, **kw):
        self.calls.append((str(path), columns))
        assert columns is not None, f"{path}: read without an explicit column list"
        assert "a_won" not in columns, f"{path}: a_won selected"
        return self.real(path, *args, columns=columns, **kw)


# ------------------------------------------------------------------------------------------------
# T-H1

def test_ssp_flip_is_an_involution_with_nan(world):
    f = A.load_frame(["spd_f", "spd_raw", "spd_f_all"], world)
    cols = A.arm_inputs("spd", world) + ["spd_raw", "spd_f_all"]
    assert f["in_spd_raw"].isna().any() and f["in_indoor"].isna().any()
    assert A.check_flip(f, cols, world)
    X = A.matrix(f, cols)
    Xf = A.flip(X, world)
    assert np.allclose(Xf["spd_f"], -X["spd_f"]) and np.array_equal(np.isnan(Xf["spd_raw"]), np.isnan(X["spd_raw"]))
    assert np.allclose(Xf["surf_season_a"], X["surf_season_b"]) and np.allclose(Xf["tour"], X["tour"])


def test_ssp_base_columns_hash_equal_after_join(world):
    f = A.load_frame(["spd_f", "spd_raw", "spd_f_all"], world)
    assert A.base_columns_unchanged(f, world)
    ft = pd.read_parquet(world.feature_file, columns=["match_id", "spd_f"]).set_index("match_id")
    assert np.allclose(f["in_spd_f"].to_numpy(), ft.loc[f["match_id"], "spd_f"].to_numpy())


def test_ssp_feature_join_is_one_to_one(world, tmp_path):
    feat = pd.read_parquet(world.feature_file, columns=["match_id", "spd_f", "spd_f_all", "spd_raw"])
    for name, bad in (("duplicate", pd.concat([feat, feat.iloc[:1]])), ("missing", feat.iloc[1:]),
                      ("nan", feat.assign(spd_f=feat["spd_f"].where(feat.index != 5)))):
        P = world.with_(features=tmp_path / name)
        P.features.mkdir()
        bad.to_parquet(P.feature_file, index=False)
        A.write_registry(P)
        with pytest.raises(RuntimeError):
            A.load_frame(["spd_f"], P)


def test_ssp_feature_status_refuses_bad_meta(world, tmp_path):
    assert A.feature_status(world)["ok"]
    good = C.read_json(world.feature_meta)
    no_hash = {k: v for k, v in good.items() if k != "features_parquet_sha256"}
    for name, meta in (("no_probe_b", {**good, "probes": {"A": {"pass": True}}}),
                       ("failed", {**good, "probes": {"A": {"pass": True}, "B": {"pass": False}}}),
                       ("standin", {**good, "standin_panel": True}),
                       ("other_hash", {**good, "features_parquet_sha256": "0" * 64}),
                       ("no_hash", no_hash),                                               # red team F1
                       ("no_panel_hash", {k: v for k, v in good.items() if k != "panel_sha256"}),
                       ("other_panel", {**good, "panel_sha256": "1" * 64}),
                       ("other_builder", {**good, "features_py_sha256": "2" * 64})):
        P = world.with_(features=tmp_path / name)
        P.features.mkdir()
        P.feature_file.write_bytes(world.feature_file.read_bytes())
        C.write_json(P.feature_meta, meta)
        st = A.feature_status(P)
        assert not st["ok"], name
        with pytest.raises(RuntimeError):
            A.require_features(P)
    # a changed panel or builder file on disk (the meta unchanged) is refused too
    for name, field in (("panel_changed", "panel"), ("builder_changed", "features_py")):
        P = world.with_(features=tmp_path / name, **{field: tmp_path / f"{name}.bin"})
        P.features.mkdir()
        P.feature_file.write_bytes(world.feature_file.read_bytes())
        C.write_json(P.feature_meta, good)
        getattr(P, field).write_bytes(b"rebuilt after the meta was written")
        assert not A.feature_status(P)["ok"], name


# ------------------------------------------------------------------------------------------------
# T-H2

def test_ssp_plan_is_the_223_jobs():
    jobs = L.plan_jobs()
    assert len(jobs) == 223 and len(set(jobs)) == 223
    count = pd.Series([(j.arm, j.kind) for j in jobs]).value_counts().to_dict()
    assert count == {("spd", "fit"): 68, ("spd_raw", "fit"): 44, ("spd_all", "fit"): 44, ("spd_noodds", "fit"): 44,
                     ("model_noodds", "fit"): 20, ("model", "repro"): 2, ("model_noodds", "repro"): 1}
    seeds = lambda arm, seasons: {j.seed for j in jobs if j.arm == arm and j.kind == "fit" and j.season in seasons}  # noqa: E731
    assert seeds("spd", C.CAL_SEASONS) == set(range(4)) and seeds("spd", C.TEST_SEASONS) == set(range(16))
    for arm in ("spd_raw", "spd_all", "spd_noodds"):
        assert seeds(arm, C.CAL_SEASONS) == set(range(4)) and seeds(arm, C.TEST_SEASONS) == set(range(8))
    assert seeds("model_noodds", C.CAL_SEASONS) == {3} and seeds("model_noodds", C.TEST_SEASONS) == set(range(3, 8))
    assert {(j.arm, j.season, j.seed) for j in jobs if j.kind == "repro"} == {("model", 2024, 0), ("model", 2026, 2),
                                                                             ("model_noodds", 2025, 1)}
    assert not [j for j in jobs if j.arm == "model" and j.kind == "fit"]


def test_ssp_scorer_reads_exactly_the_planned_fits():
    """Every fit the scorer reads is planned or reused: the new arms' needs equal their planned jobs; model_noodds needs
    the race's seeds 0-2 plus the 20 new ones; model needs the 16 reused seeds of 2019-2026."""
    need = S.needed_fits()
    planned = {}
    for j in L.plan_jobs():
        if j.kind == "fit":
            planned.setdefault(j.arm, set()).add((j.season, j.seed))
    for arm in ("spd", "spd_raw", "spd_all", "spd_noodds"):
        assert need[arm] == planned[arm], arm
    race_noodds = {(s, k) for s in range(2019, 2027) for k in range(3)}
    assert need["model_noodds"] == planned["model_noodds"] | race_noodds
    assert need["model"] == {(s, k) for s in range(2019, 2027) for k in range(16)}


def test_ssp_runner_guard(world, tmp_path):
    with pytest.raises(RuntimeError):
        L.guard(L.Job("model", 2024, 3), world)                  # the base with odds is never refitted
    with pytest.raises(RuntimeError):
        L.guard(L.Job("spd", 2024, 16), world)                   # not planned
    L.guard(L.Job("model", 2024, 0, "repro"), world)
    L.guard(L.Job("spd", 2019, 3), world)
    L.guard(L.Job("model_noodds", 2024, 3), world)
    P = world.with_(race_local=tmp_path)
    np.savez(tmp_path / "model_noodds__2024__seed3.npz", meta=np.asarray("{}"))
    with pytest.raises(RuntimeError):
        L.guard(L.Job("model_noodds", 2024, 3), P)               # a seed the race already holds


# ------------------------------------------------------------------------------------------------
# T-H3

def test_ssp_reproduction_comparison(tmp_path):
    ids = np.array(["a", "b", "c"])
    p = np.array([0.2, 0.5, 0.7, 0.8, 0.5, 0.3])
    stored = tmp_path / "stored.npz"
    np.savez(stored, meta=np.asarray("{}"), p_td=p, ids_td=ids, p_early=p[:2], ids_early=ids[:1])
    cases = {"same": (p, ids, True), "within": (p + 5e-7, ids, True), "beyond": (p + 2e-6, ids, False),
             "ids": (p, np.array(["a", "c", "b"]), False)}
    for name, (pn, idn, expect) in cases.items():
        new = tmp_path / f"{name}.npz"
        np.savez(new, meta=np.asarray("{}"), p_td=pn, ids_td=idn, p_early=p[:2], ids_early=ids[:1])
        assert L.compare_fit_files(new, stored)["passed"] is expect, name
    new = tmp_path / "no_early.npz"
    np.savez(new, meta=np.asarray("{}"), p_td=p, ids_td=ids)
    assert not L.compare_fit_files(new, stored)["passed"]
    assert not L.compare_fit_files(tmp_path / "absent.npz", stored)["passed"]


def test_ssp_race_fits_need_the_reuse_checks(world, tmp_path):
    fx = S.frame_index(world)
    P = world.with_(checks=tmp_path / "checks")
    with pytest.raises(RuntimeError):
        F.load_fit("model", 2024, 0, fx, P, require_checks=True)
    blocks, prov = F.load_fit("model", 2024, 5, fx, P, require_checks=True)         # fingerprinted folder: allowed
    assert prov["folder"] == "feature_interactions" and len(blocks["td"]) == 2 * N_PER_TOUR
    C.write_json(P.checks / "repro_check.json", {"passed": False})
    C.write_json(P.checks / "fingerprint_check.json", {"all_ok": True})
    with pytest.raises(RuntimeError):
        F.load_fit("model", 2024, 0, fx, P, require_checks=True)                   # a failed reproduction blocks
    C.write_json(P.checks / "repro_check.json", {"passed": True})
    blocks, prov = F.load_fit("model", 2024, 0, fx, P, require_checks=True)
    assert prov["folder"] == "race"                                                  # sf_ names normalised


def test_ssp_real_reuse_checks_pass_when_run():
    fp = C.DEFAULT.checks / "fingerprint_check.json"
    rp = C.DEFAULT.checks / "repro_check.json"
    if not fp.exists() and not rp.exists():
        pytest.skip("no reuse check has been run yet")
    if fp.exists():
        r = C.read_json(fp)
        assert r["all_ok"] and r["fi_model_fingerprints_equal"] == r["fi_model_fingerprints_checked"] == 107
    if rp.exists():
        assert C.read_json(rp)["passed"]


# ------------------------------------------------------------------------------------------------
# T-H4

def perturbed_scorer(P: C.Paths, info: pd.DataFrame, y: pd.Series, season: int) -> S.Scorer:
    """The same world with every forecast and outcome of seasons >= season replaced."""
    rng = np.random.default_rng(9)
    bank = S.Bank(P, S.frame_index(P), require_checks=False)
    for s in range(season, 2027):
        for k in S.SEEDS16:
            b = bank.blocks("model", s, k)
            bank.injected[("model", s, k)] = {"td": pd.Series(rng.random(len(b["td"])), index=b["td"].index)}
    late = (info["season"] >= season).to_numpy()
    y2 = y.copy()
    y2[late] = 1 - y2[late]
    return S.Scorer(bank, info, y2)


def test_ssp_calibration_reads_earlier_seasons_only(world):
    info, y = outcomes(world)
    sc = S.Scorer(S.Bank(world, S.frame_index(world), require_checks=False), info, y)
    for season in (2024, 2025, 2026):
        assert sc.slopes("model", season) == perturbed_scorer(world, info, y, season).slopes("model", season)


def test_ssp_nudge_reads_earlier_seasons_only(world):
    info, y = outcomes(world, beta=0.2)
    sc = S.Scorer(S.Bank(world, S.frame_index(world), require_checks=False), info, y)
    for season in (2024, 2026):
        assert S.nudge_parameters(sc, season) == S.nudge_parameters(perturbed_scorer(world, info, y, season), season)


# ------------------------------------------------------------------------------------------------
# T-H5

def test_ssp_equal_seed_sets_and_calibration_seeds(world):
    assert C.CAL_SEEDS == (0, 1, 2, 3)
    assert S.PRIMARY.seeds == tuple(range(16)) and S.PRIMARY.base == "model" and S.PRIMARY.arm == "spd"
    for cmp in S.COMPARISONS + [S.S14]:
        assert isinstance(cmp.seeds, tuple) and cmp.seeds in (S.SEEDS16, S.SEEDS8), cmp.cid
    assert S.S14.seeds == S.PRIMARY.seeds and S.S14.population == S.PRIMARY.population and S.S14.loss == "brier"
    assert {c.cid: c.seeds for c in S.COMPARISONS if c.cid in ("S5", "S8_A2", "S8_A3")} == \
        {"S5": S.SEEDS8, "S8_A2": S.SEEDS8, "S8_A3": S.SEEDS8}
    info, y = outcomes(world)
    bank = S.Bank(world, S.frame_index(world), require_checks=False)
    calls = []
    real = bank.per_seed

    def spy(arm, seeds, seasons, block="td"):
        calls.append((arm, tuple(seeds), tuple(seasons)))
        return real(arm, seeds, seasons, block)
    bank.per_seed = spy
    # a twin arm "spd" built from the base, so the primary comparison can run in the stand-in world
    for s in S.HIST:
        for k in S.SEEDS16:
            bank.injected[("spd", s, k)] = {"td": bank.blocks("model", s, k)["td"]}
    S.Scorer(bank, info, y).paired(S.PRIMARY)
    scored = [c for c in calls if c[2] == S.TEST]
    cal = [c for c in calls if c[2] != S.TEST]
    assert {c[1] for c in scored} == {S.SEEDS16} and {c[0] for c in scored} == {"model", "spd"}
    assert {c[1] for c in cal} == {C.CAL_SEEDS} and {c[0] for c in cal} == {"model", "spd"}
    assert {c[2] for c in cal} == {tuple(range(2019, y)) for y in S.TEST}           # windows 2019 .. Y - 1


# ------------------------------------------------------------------------------------------------
# T-H6, T-H7

def test_ssp_synthetic_never_selects_a_won(world, monkeypatch):
    spy = ReadSpy(pd.read_parquet)
    monkeypatch.setattr(pd, "read_parquet", spy)
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))
    out = S.synthetic(world, beta=0.0, capture_share=0.5, reps=3, seed=1)
    assert out["summary"]["reps"] == 3 and spy.calls
    assert any(Path(p) == world.model_frame for p, _ in spy.calls)
    assert (world.out / "synthetic").exists()


def test_ssp_check_writes_hash_and_counts_without_outcomes(world, monkeypatch):
    spy = ReadSpy(pd.read_parquet)
    monkeypatch.setattr(pd, "read_parquet", spy)
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))
    out = S.check(world)
    saved = C.read_json(world.out / "check.json")
    men = saved["populations"]["men 2024-2026"]
    assert men["matches"] > 1000 and len(men["sha256"]) == 64 and set(men["by_season"]) == {"2024", "2025", "2026"}
    assert set(saved["hashes"]) == set(S.PREREG_KEYS)
    assert saved["hashes"]["POPULATION_SHA256"] == men["sha256"]
    assert out["feature_status"]["ok"] and saved["recency_available"]


# ------------------------------------------------------------------------------------------------
# The scorer's arithmetic

def test_ssp_block_interval_is_the_project_convention():
    rng = np.random.default_rng(4)
    n = 3000
    y = rng.random(n) < 0.5
    pa, pb = rng.uniform(0.1, 0.9, n), rng.uniform(0.1, 0.9, n)
    dates = pd.Timestamp("2024-01-01").to_datetime64() + rng.integers(0, 700, n).astype("timedelta64[D]")
    ref = T.compare(T.ll(pa, y), T.ll(pb, y), dates)
    r = S.paired_stats(T.ll(pa, y), T.ll(pb, y), np.zeros(1), np.zeros(1), T.blocks(dates, 28), T.blocks(dates, 7))
    assert np.isclose(r["estimate"], ref["gain"]) and np.isclose(r["lo_block_only"], ref["lo"])
    assert np.isclose(r["hi_block_only"], ref["hi"]) and np.isclose(r["lo"], ref["lo"])   # no seed variance: equal
    r2 = S.paired_stats(T.ll(pa, y), T.ll(pb, y), np.array([1.0, 1.2, 0.9]), np.array([1.1, 0.8, 1.0]),
                        T.blocks(dates, 28), T.blocks(dates, 7))
    assert r2["lo"] < r2["lo_block_only"] and np.isclose(r2["v_seed_base"], np.var([1.0, 1.2, 0.9], ddof=1) / 3)


def test_ssp_decision_table():
    p2 = lambda g, lo, hi: {"estimate": g, "lo": lo, "hi": hi}   # noqa: E731
    s0 = lambda b, lo, hi: {"estimate": b, "lo": lo, "hi": hi, "unit": "log-odds per unit of spd_f"}   # noqa: E731
    assert "P2 has less power than S0" in S.decision(p2(0.1, -0.2, 0.4), s0(0.1, 0.02, 0.2))["reading"]   # V4
    assert S.decision(p2(0.5, 0.1, 0.9), s0(0.0, -1, 1))["row"] == 1
    assert S.decision(p2(-0.5, -0.9, -0.1), s0(0.1, 0.05, 0.2))["row"] == 2
    assert S.decision(p2(0.1, -0.2, 0.4), s0(0.1, 0.02, 0.2))["row"] == 3
    assert S.decision(p2(0.1, -0.2, 0.4), s0(0.0, -0.1, 0.1))["row"] == 4
    assert S.decision(p2(0.1, -0.2, 0.4), s0(-0.1, -0.2, -0.01))["row"] == 5


def test_ssp_synthetic_recovers_a_planted_beta(world):
    out = S.synthetic(world, beta=0.4, capture_share=1.0, reps=12, seed=3, tag="test_planted")
    sm = out["summary"]
    assert abs(sm["S0_b_mean"] - 0.4) < 0.08                     # S0 recovers beta (log-odds per SD)
    assert sm["P2_mean"] > 0 and abs(sm["P2_mean"] - sm["expected_gain_mean"]) < 5.0   # about 3.4 SE of the mean
    assert sm["S10_a_mean"] > 0


def scorer_with(world, info, y, a1_logit=None) -> S.Scorer:
    """A scorer on the stand-in world; A1 ("spd") injected for 2019-2026, seeds 0-15, from a log-odds Series."""
    bank = S.Bank(world, S.frame_index(world), require_checks=False)
    if a1_logit is not None:
        rng = np.random.default_rng(2)
        for s in S.HIST:
            idx = info.index[(info["season"] == s).to_numpy()]
            for k in S.SEEDS16:
                p = expit(a1_logit.reindex(idx).to_numpy() + rng.normal(0, 0.02, len(idx)))
                bank.injected[("spd", s, k)] = {"td": pd.Series(p, index=idx)}
    return S.Scorer(bank, info, y)


def test_ssp_s13_s14_sign_conventions(world):
    info, _ = outcomes(world)
    bank = S.Bank(world, S.frame_index(world), require_checks=False)
    eta = bank.eta("model", S.SEEDS16, S.HIST, "td").reindex(info.index)
    z = info["spd_f"]
    truth = 0.9 * eta + 1.0 * z                                   # a strong planted speed effect
    y = pd.Series((np.random.default_rng(5).random(len(info)) < expit(truth)).astype(float), index=info.index)
    # S14 (Brier) and P2 (log loss): positive = A1 better
    good = scorer_with(world, info, y, a1_logit=eta + z / 0.9)    # A1 knows the speed term
    bad = scorer_with(world, info, y, a1_logit=eta + pd.Series(np.random.default_rng(6).normal(0, 1.0, len(info)),
                                                              index=info.index))
    for sc, sign in ((good, 1), (bad, -1)):
        p2, s14 = sc.paired(S.PRIMARY), sc.paired(S.S14)
        assert sign * p2["estimate"] > 0 and sign * s14["estimate"] > 0
        assert s14["unit"] == "1000 x Brier" and "Brier score" in s14["direction"] and s14["v_seed_arm"] > 0
    # S13: positive = the calibrated base better than the calibrated close
    useless = info.assign(p_mkt=0.5)
    perfect = info.assign(p_mkt=expit(truth))
    p2 = good.paired(S.PRIMARY)
    s13_base_better = S.close_edge(S.Scorer(bank, useless, y), p2)
    s13_close_better = S.close_edge(S.Scorer(bank, perfect, y), p2)
    assert s13_base_better["estimate"] > 0 and s13_base_better["lo"] > 0
    assert s13_close_better["estimate"] < 0 and s13_close_better["hi"] < 0
    assert s13_base_better["ratio_P2_to_S13"] == p2["estimate"] / s13_base_better["estimate"]
    assert "positive = the calibrated base" in s13_base_better["direction"]


def test_ssp_s13_close_calibration_reads_earlier_seasons_only(world):
    info, y = outcomes(world)
    sc = S.Scorer(S.Bank(world, S.frame_index(world), require_checks=False), info, y)
    rng = np.random.default_rng(8)
    for season in (2024, 2025, 2026):
        late = (info["season"] >= season).to_numpy()
        info2 = info.copy()
        info2.loc[late, "p_mkt"] = rng.uniform(0.05, 0.95, late.sum())
        y2 = y.copy()
        y2[late] = 1 - y2[late]
        sc2 = S.Scorer(S.Bank(world, S.frame_index(world), require_checks=False), info2, y2)
        assert sc.price_slopes(season) == sc2.price_slopes(season)
    assert sc.price_slopes(2024) != sc.price_slopes(2026)          # the window does grow


def test_ssp_multiplicity_counts_s14_not_the_s13_context(world):
    info, y = outcomes(world, beta=0.3)
    bank = S.Bank(world, S.frame_index(world), require_checks=False)
    eta = bank.eta("model", S.SEEDS16, S.HIST, "td").reindex(info.index)
    res = S.evaluate(scorer_with(world, info, y, a1_logit=eta + 0.3 / 0.9 * info["spd_f"]), core_only=True)
    shown = {r["cid"] for r in S.secondary_rows(res)}
    counted = {r["cid"] for r in S.secondary_rows(res, counted=True)}
    assert {"S0", "S11_block_only", "S11_week", "S13", "S14"} <= shown
    assert "S13" not in counted and "S14" in counted and shown - counted == {"S13"}
    assert res["multiplicity"]["secondary_intervals"] == len(counted)
    assert "S13" not in res["multiplicity"]["which"]
    roles = dict(zip(S.table(res)["cid"], S.table(res)["role"]))
    assert roles["S13"] == "context (not counted)" and roles["S14"] == "secondary" and roles["P2"] == "primary"


def write_speed_fit(P: C.Paths, season: int, seed: int, feature_sha: str) -> None:
    f = pd.read_parquet(P.model_frame, columns=["match_id", "season"])
    ids = f.loc[f["season"] == season, "match_id"].to_numpy().astype(str)        # fixed-width, as the runner saves
    n_train = int(f["season"].between(C.TRAIN_FROM, season - 1).sum())
    cols = A.arm_inputs("spd", P)
    meta = {"arm": "spd", "season": season, "seed": seed, "columns": cols, "train_shape": [n_train, len(cols)],
            "feature_sha256": feature_sha}
    P.local.mkdir(parents=True, exist_ok=True)
    np.savez(P.local / f"spd__{season}__seed{seed}.npz", meta=np.asarray(json.dumps(meta)),
             p_td=np.full(2 * len(ids), 0.5), ids_td=ids)


def test_ssp_stale_speed_fits_are_refused(world, tmp_path, monkeypatch):
    P = world.with_(local=tmp_path / "local", out=tmp_path / "out", checks=tmp_path / "checks",
                    prereg=tmp_path / "prereg.md")
    current = F.feature_sha(P)
    write_speed_fit(P, 2024, 0, current)
    write_speed_fit(P, 2024, 1, "0" * 64)                         # made before a feature rebuild
    fx = S.frame_index(P)
    F.load_fit("spd", 2024, 0, fx, P)
    with pytest.raises(RuntimeError, match="another feature file"):
        F.load_fit("spd", 2024, 1, fx, P)
    st = F.stale_speed_fits(P)
    assert st["speed_fits_checked"] == 2 and [m["file"] for m in st["mismatches"]] == ["spd__2024__seed1.npz"]
    assert [m["file"] for m in S.check(P)["stale_speed_fits"]["mismatches"]] == ["spd__2024__seed1.npz"]
    # --run: a valid hashed pre-registration and passed reuse checks, then the stale fit stops it before any result
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))
    hashed_prereg(P)
    with pytest.raises(RuntimeError, match="another feature file"):
        S.run(P)
    assert not (P.out / "results.json").exists()


def hashed_prereg(P: C.Paths, extra: str = "") -> None:
    """A valid hashed pre-registration for the stand-in world, with passed reuse checks."""
    h = S.hashes(P)
    P.prereg.write_text("\n".join(f"{k}: {v}" for k, v in h.items()) + "\n" + extra, encoding="utf-8")
    S.hash_prereg(P)
    C.write_json(P.checks / "repro_check.json", {"passed": True})
    C.write_json(P.checks / "fingerprint_check.json", {"all_ok": True})


def no_labels(monkeypatch) -> None:
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))


def test_ssp_run_refuses_missing_fits_before_labels(world, tmp_path, monkeypatch):
    """V2: with the base fits present and every speed-arm fit missing, --run refuses before reading a result."""
    P = world.with_(local=tmp_path / "local", out=tmp_path / "out", checks=tmp_path / "checks",
                    prereg=tmp_path / "prereg.md")
    no_labels(monkeypatch)
    hashed_prereg(P)
    assert S.missing_fits(P) and {a for a, _, _ in S.missing_fits(P)} == {"spd", "spd_raw", "spd_all", "spd_noodds",
                                                                           "model_noodds"}
    with pytest.raises(RuntimeError, match="needed fits are missing"):
        S.run(P)
    assert not (P.out / "results.json").exists()


def test_ssp_run_checks_a_recorded_forecasts_hash(world, tmp_path, monkeypatch):
    """V7: a FORECASTS_SHA256 that differs from the fits refuses; the right one passes that guard."""
    P = world.with_(local=tmp_path / "local", out=tmp_path / "out", checks=tmp_path / "checks",
                    prereg=tmp_path / "prereg.md")
    no_labels(monkeypatch)
    monkeypatch.setattr(S, "missing_fits", lambda *a, **k: [])            # past V2, to reach the V7 guard
    hashed_prereg(P, extra="FORECASTS_SHA256: " + "f" * 64 + "\n")
    with pytest.raises(RuntimeError, match="FORECASTS_SHA256"):
        S.run(P)
    hashed_prereg(P, extra=f"FORECASTS_SHA256: {S.forecasts_hash(P)['FORECASTS_SHA256']}\n")
    with pytest.raises(AssertionError, match="labels"):                    # every guard passed: it reached labels()
        S.run(P)


def test_ssp_prereg_hash_ignores_crlf(world, tmp_path):
    """V8: the hash is of the text with CRLF normalised to LF, so a CRLF checkout still verifies."""
    P = world.with_(out=tmp_path / "out", checks=tmp_path / "checks", prereg=tmp_path / "prereg.md")
    hashed_prereg(P)
    current = S.hashes(P)
    S.verify_prereg(P, current)
    lf = P.prereg.read_bytes().replace(b"\r\n", b"\n")
    P.prereg.write_bytes(lf.replace(b"\n", b"\r\n"))
    S.verify_prereg(P, current)
    P.prereg.write_bytes(lf)
    S.verify_prereg(P, current)
    P.prereg.write_bytes(lf + b"one more line\n")
    with pytest.raises(RuntimeError, match="does not match"):
        S.verify_prereg(P, current)


def test_ssp_synthetic_real_arms_need_the_hash(world, tmp_path):
    """V5: synthetic(arms="real") relates the real A1 forecasts to spd_f, so it runs only after the hash."""
    P = world.with_(out=tmp_path / "out", checks=tmp_path / "checks", prereg=tmp_path / "prereg.md")
    with pytest.raises(RuntimeError, match="pre-registration"):
        S.synthetic(P, beta=0.0, reps=1, arms="real")


def test_ssp_units_capture_and_nan(world):
    """V6 units per unit of the column; V9 S10's calibrated share; V13 eta refuses NaN."""
    info, y = outcomes(world, beta=0.3)
    bank = S.Bank(world, S.frame_index(world), require_checks=False)
    eta = bank.eta("model", S.SEEDS16, S.HIST, "td").reindex(info.index)
    sc = scorer_with(world, info, y, a1_logit=eta + 0.3 / 0.9 * info["spd_f"])
    res = S.evaluate(sc, core_only=True)
    assert res["S0"]["unit"].startswith("log-odds per unit of spd_f") and "per SD" not in res["S0"]["unit"]
    assert S.column_unit("spd_raw", world).startswith("log-odds per unit of spd_raw (one unit = 5.998 km/h")
    s10 = res["S10"]
    ids = S.population_ids(info, "men", S.TEST)
    dev = (sc.bank.eta("spd", S.SEEDS16, S.TEST) - sc.bank.eta("model", S.SEEDS16, S.TEST)).reindex(ids).to_numpy()
    z = info.loc[ids, "spd_f"].to_numpy()
    s_row = np.array([sc.slopes("spd", int(s))["atp"] for s in info.loc[ids, "season"]])
    assert np.isclose(s10["applied_slope_calibrated"], np.dot(s_row * dev, z) / np.dot(z, z))
    assert set(s10["s_Y_men_A1"]) == {"2024", "2025", "2026"}
    if res["S0"]["lo"] > 0:
        assert np.isclose(s10["calibrated_ratio_to_S0"], s10["applied_slope_calibrated"] / res["S0"]["estimate"])
    holes = S.Bank(world, S.frame_index(world), require_checks=False)
    b = holes.blocks("model", 2024, 0)["td"]
    holes.injected[("model", 2024, 0)] = {"td": b.iloc[1:]}                # one match missing in one seed
    with pytest.raises(RuntimeError, match="missing"):
        holes.eta("model", S.SEEDS16, (2024,))


def test_ssp_s6_odds_move_uses_disjoint_base_seeds(world):
    """V1: M on [eta_B[0-7] - logit p24, eta_B[0-7], eta_A1[0-15] - eta_B[8-15]], the last slope; a price that moves
    toward A1's view gives a positive slope near the planted one, and the base's seed sets are 0-7 and 8-15."""
    info, y = outcomes(world)
    bank = S.Bank(world, S.frame_index(world), require_checks=False)
    rng = np.random.default_rng(12)
    shift = {}
    for s in (2025, 2026):
        for k in S.SEEDS16:
            e = bank.blocks("model", s, k)["early"]
            sh = shift.setdefault(s, pd.Series(rng.normal(0, 0.3, len(e)), index=e.index))
            bank.injected[("spd", s, k)] = {"early": pd.Series(expit(C.lg(e.to_numpy()) + sh.to_numpy()),
                                                               index=e.index)}
        for k in S.SEEDS8:
            t = bank.blocks("model", s, k)["td"]
            bank.injected[("model_noodds", s, k)] = {"td": t}
            bank.injected[("spd_noodds", s, k)] = {"td": pd.Series(expit(C.lg(t.to_numpy()) + rng.normal(0, 0.1, len(t))),
                                                                   index=t.index)}
    view = pd.concat(shift.values())
    info2 = info.copy()
    priced = info2["p_early_a"].notna()
    move = 0.7 * view.reindex(info2.index[priced]).fillna(0).to_numpy()
    info2.loc[priced, "p_close_a"] = expit(C.lg(info2.loc[priced, "p_early_a"].to_numpy()) + move)
    calls = []
    real = bank.eta

    def spy(arm, seeds, seasons, block="td"):
        calls.append((arm, tuple(seeds), block))
        return real(arm, seeds, seasons, block)
    bank.eta = spy
    rows = S.moves(S.Scorer(bank, info2, y))
    odds = {r["cid"]: r for r in rows if r["cid"].startswith("S6_move_odds")}
    assert odds and all(0.5 < r["estimate"] < 0.9 and r["lo"] > 0 for r in odds.values())
    assert ("model", tuple(range(8)), "early") in calls and ("model", tuple(range(8, 16)), "early") in calls
    assert ("model", S.SEEDS16, "early") not in calls and ("spd", S.SEEDS16, "early") in calls


def test_ssp_run_refuses_without_a_hashed_prereg(world, monkeypatch):
    monkeypatch.setattr(S, "labels", lambda *a, **k: (_ for _ in ()).throw(AssertionError("labels() called")))
    with pytest.raises(RuntimeError):
        S.run(world)
    assert not (world.out / "results.json").exists()
