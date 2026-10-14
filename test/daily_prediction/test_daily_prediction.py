"""The owner's four checks of the daily prediction script, phase 1 (10 Oct 2026), and fast unit checks.

    1. each family's resumed state equals a full recompute: bit for bit; the surface IOS within 1e-6
    2. a replay of a past day through run_day reproduces all 57 inputs of
       data/studies/current_best_model/template_2026-10-10/model_frame.parquet exactly
    3. a changed past row invalidates its checkpoint
    4. the price-grid forecast matches a direct TabPFN prediction within 0.001
Each would fail if the logic it checks were wrong: 1 compares every row after the checkpoint (not a sample) with an
independent full recomputation; 2 compares with the frame the template's own chain built; 3 changes each kind of field
a family reads, before and after the checkpoint day, and requires a change exactly where history changed; 4 compares
the grid read back at each match's own price with that price's own prediction, and with the template's stored fits.

Part 2 (11 Oct 2026, the speed-ups): tests 2 and 4 run through the faster paths; the fit from TabPFN's training caches
must equal the decided path bit for bit (built and loaded), a cache is refused when anything it depends on changed,
and the history check run beside the states step must still be recorded.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from conftest import OUT, PKG, REPLAY, ROOT, TREE, needs_gpu_env, needs_tree, read, run_py

IOS_TOL = 1e-6
GRID_TOL = 1e-3


# ------------------------------------------------------------------------------------------------
# fast: the slice hash itself

def test_slice_hash_sees_every_change():
    import dp_hash as H
    base = {"a": np.array([1.0, 2.0, np.nan]), "b": np.array(["x", "y", None], dtype=object), "c": np.arange(3)}
    h0 = H.hash_arrays(base)
    assert H.hash_arrays({k: np.array(v, copy=True) for k, v in base.items()}) == h0          # deterministic
    assert H.hash_arrays({**base, "a": np.array([1.0, 2.0 + 1e-15, np.nan])}) != h0             # a last bit
    assert H.hash_arrays({**base, "a": np.array([1.0, np.nan, 2.0])}) != h0                     # order
    assert H.hash_arrays({**base, "b": np.array(["x", "y", "z"], dtype=object)}) != h0          # a missing value filled
    assert H.hash_arrays({"b": base["b"], "a": base["a"], "c": base["c"]}) != h0                # array order
    assert H.hash_arrays({**base, "c": np.arange(4)}) != h0                                     # a row added
    nan2 = np.array([1.0, 2.0, np.float64("nan") * -1])
    assert H.hash_arrays({**base, "a": nan2}) == h0                                             # one NaN pattern
    assert H.hash_arrays({**base, "a": base["a"].astype("float32")}) == h0                      # float32 read as float64


# ------------------------------------------------------------------------------------------------
# 1. resume = full recompute, family by family

@pytest.fixture(scope="module")
def families(tmp_path_factory):
    state = tmp_path_factory.mktemp("dp_state")
    out = OUT / "checks" / "pytest_families.json"
    done = run_py([str(PKG / "dp_selftest.py"), "families", "--day", "2026-08-31", "--out", str(out)],
                  timeout=3 * 3600, env={"DP_STATE": str(state)}, log=OUT / "checks" / "pytest_families.log")
    assert done.returncode == 0, done.stdout[-5000:]
    return read(out)


@needs_tree
def test_elo_passes_resume_bit_for_bit(families):
    elo = families["families"]["elo"]
    for key, v in elo.items():
        if isinstance(v, dict):
            assert v["bitwise"], f"{key}: resumed differs from the full pass ({v})"
            assert v["matches_after"] > 0
    assert elo["stage3_atp"]["saved_block_before"] and elo["stage3_wta"]["saved_block_before"]
    assert elo["weighted_full_vs_decided_elo_variants"]


@needs_tree
def test_forms_resume_bit_for_bit(families):
    f = families["families"]["forms"]
    assert f["box_rows_after"] > 0 and f["pool_matches_after"] > 0
    assert f["z_pairs_bitwise_every_box_row"] == f["z_pairs"] == 17, f["not_bitwise"]
    assert f["inputs_bitwise"] == f["inputs"] == 17, f["not_bitwise"]


@needs_tree
def test_ios_resume_within_tolerance(families):
    ios = families["families"]["ios"]
    assert len(ios) == 14
    for key, v in ios.items():
        assert not v.get("invalid"), f"{key}: the checkpoint's slice differs on the table it was made on"
        assert v["rows_after"] > 0
        assert v["nan_pattern_equal"], key
        assert v["max_abs_diff"] <= IOS_TOL, f"{key}: {v['max_abs_diff']}"


@needs_tree
def test_stateless_families_equal_the_build(families):
    s4 = families["families"]["stage4"]
    assert s4["matches_after"] > 0 and all(s4["vs_stored_float32"].values()), s4["vs_stored_float32"]
    pc = families["families"]["pieces"]
    assert pc["matches_after"] > 0 and all(pc["vs_stored"].values()), pc["vs_stored"]


# ------------------------------------------------------------------------------------------------
# 2. a replay of a past day through run_day: the 57 inputs

@needs_tree
def test_replay_reproduces_the_57_inputs(replay_run):
    done = run_py([str(PKG / "dp.py"), "replay-compare", "--run", str(replay_run)], timeout=600)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    res = read(replay_run / "replay_compare.json")
    assert res["matches"] == 23 and not res["missing_from_frame"]
    assert res["inputs"] == 57
    assert res["non_ios_bitwise"] == res["non_ios_inputs"] == 36, \
        {k: v for k, v in res["per_input"].items() if v["bitwise_equal"] < v["rows"]}
    assert res["ios_nan_pattern_equal"] and res["ios_max_abs_diff"] <= IOS_TOL, res["ios_max_abs_diff"]
    states = read(replay_run / "states.json")
    assert all(v == "resumed" for v in states["record"]["parts"].values()), states["record"]["parts"]
    steps = read(replay_run / "run_day.json")["steps"]
    for s in ("worktree", "matchups", "prices", "tables", "states", "fit", "predict"):
        assert s in steps


# ------------------------------------------------------------------------------------------------
# 3. a changed past row invalidates its checkpoint

@needs_tree
def test_changed_past_row_invalidates():
    out = OUT / "checks" / "pytest_invalidation.json"
    done = run_py([str(PKG / "dp_selftest.py"), "invalidation", "--day", "2026-08-31", "--out", str(out)],
                  timeout=3600, log=OUT / "checks" / "pytest_invalidation.log")
    assert done.returncode == 0, done.stdout[-5000:]
    res = read(out)
    assert len(res["cases"]) >= 14
    bad = [c for c in res["cases"] if not c["as_required"]]
    assert not bad, bad
    assert any(c["hash_changed"] for c in res["cases"]) and any(not c["hash_changed"] for c in res["cases"])


@needs_tree
def test_changed_past_row_recomputes_through_the_steps():
    """The same through the real steps: a replay's work tree with one past match's timeline window moved; the states
    step must recompute exactly the parts that read it and still give a from-scratch build's inputs."""
    import datetime as dt
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT / "checks" / "pytest_invalidation_e2e.json"
    done = run_py([str(PKG / "dp_selftest.py"), "invalidation_e2e", "--root",
                   str(OUT / "runs" / f"pytest_invalidation_e2e_{stamp}"), "--checkpoint", REPLAY["checkpoint"],
                   "--out", str(out)], timeout=3 * 3600, log=OUT / "checks" / "pytest_invalidation_e2e.log")
    assert done.returncode == 0, done.stdout[-5000:]
    res = read(out)
    assert res["recomputed"] and all(k.startswith("ios:atp_") for k in res["recomputed"]), res["recomputed"]
    assert all(v == "resumed" for k, v in res["parts"].items() if k not in res["recomputed"])
    assert res["non_ios_bitwise"] == 36 and res["ios_nan_pattern_equal"] and res["ios_max_abs_diff"] <= IOS_TOL
    assert res["as_required"]


# ------------------------------------------------------------------------------------------------
# 4. the price grid against a direct prediction

@needs_tree
@needs_gpu_env
def test_price_grid_matches_direct_prediction(replay_run):
    fit = read(replay_run / "fit.json")
    s = fit["summary"]
    assert s["seeds"] == 16 and s["matches"] == 23 and s["inside_grid"] == 23
    assert s["interpolated_vs_own_max_abs"] <= GRID_TOL, s
    assert s["separate_vs_in_batch_max_abs"] <= 1e-4, s           # the own-price rows are direct predictions
    # and against the template's own stored fits of these matches (the decided path, 16 seeds)
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import dp_fit as FT
    import pandas as pd
    from scipy.special import expit, logit
    d = FT.load(replay_run, list(range(16)))
    pg = d["grid"].mean(axis=0)
    back = FT.interp(d["own_logit"], pg)
    inst = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10" / "fits"
    stored = []
    for seed in range(16):
        with np.load(inst / f"model__2026__seed{seed}.npz", allow_pickle=False) as z:
            ids, p = z["ids_td"].astype(str), z["p_td"].astype("float64")
        n = len(ids)
        ps = 0.5 * (p[:n] + 1.0 - p[n:])
        stored.append(pd.Series(ps, index=ids).reindex(d["match_id"]).to_numpy())
    stored = np.mean(stored, axis=0)
    assert np.isfinite(stored).all()
    assert float(np.max(np.abs(back - stored))) <= GRID_TOL
    assert float(np.max(np.abs(d["own"].mean(axis=0) - stored))) <= GRID_TOL


# ------------------------------------------------------------------------------------------------
# Part 2 (owner, 11 Oct 2026): speed-ups "with no cost to prediction quality or potential bugs". Each must leave
# the numbers as they were: tests 2 and 4 above run through the faster paths (the states step's three processes, the
# fit from TabPFN's training caches); these check what they do not.

def test_fit_cache_key_sees_every_change(tmp_path):
    """A cache is used only when its stored key equals today's: a changed training value (a last bit), label, column
    name or NaN position changes the training hash (one NaN pattern does not); a key differing in any field, or a
    folder missing a part, is stale."""
    import pandas as pd

    import dp_tabcache as TC
    X = pd.DataFrame({"a": [1.0, 2.0, np.nan], "b": [0.5, -1.0, 3.0]})
    y = np.array([1, 0, 1])
    h0 = TC.train_sha256(X, y)
    assert TC.train_sha256(X.copy(), y.copy()) == h0
    x1 = X.copy()
    x1.loc[1, "a"] = 2.0 + 4.5e-16
    assert x1.loc[1, "a"] != 2.0 and TC.train_sha256(x1, y) != h0
    assert TC.train_sha256(X, np.array([1, 1, 1])) != h0
    assert TC.train_sha256(X.rename(columns={"b": "c"}), y) != h0
    x2 = X.copy()
    x2.loc[2, "a"], x2.loc[0, "a"] = 1.0, np.nan
    assert TC.train_sha256(x2, y) != h0
    x3 = X.copy()
    x3["a"] = np.array([1.0, 2.0, -np.float64("nan")])
    assert TC.train_sha256(x3, y) == h0
    key = {"format": 1, "train_sha256": h0, "seed": 0, "versions": {"tabpfn": "9.1.0", "torch": "2.11.0"}}
    f = tmp_path / "seed0"
    assert TC.status(f, key) == "missing"
    f.mkdir()
    (f / "key.json").write_text(json.dumps(key), encoding="utf-8")
    assert TC.status(f, key) == "stale: incomplete"
    for name in ("init_params.json", "fitted_attrs.joblib", "executor_state.joblib"):
        (f / name).write_text("x", encoding="utf-8")
    assert TC.status(f, key) == "usable"
    assert TC.status(f, {**key, "seed": 1}) == "stale: seed"
    assert TC.status(f, {**key, "versions": {"tabpfn": "9.2.0", "torch": "2.11.0"}}) == "stale: versions"
    assert TC.status(f, {**key, "train_sha256": "0" * 64}) == "stale: train_sha256"
    assert TC.status(f, {**key, "gpu": "another card"}) == "stale: gpu"


@needs_tree
@needs_gpu_env
def test_fit_cache_equals_decided_path(replay_run, tmp_path_factory):
    """The replay's fit came from TabPFN's training caches (run_day's default). (a) The decided path itself
    (fit_preprocessors) on the same live rows, seeds 0 and 1 with their separate own-price calls: every array bit for
    bit. (b) Seed 2's cache built from scratch in a state folder of its own: bit for bit with the replay's seed 2, so
    both a built and a loaded cache are checked whichever the replay used (its own cache, 3.6 GB, is removed after)."""
    import datetime as dt
    import shutil
    fit = read(replay_run / "fit.json")
    assert fit.get("path", "").startswith("training cache"), fit.get("path")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT / "checks" / "pytest_fit_cache_off.json"
    done = run_py([str(PKG / "dp_selftest.py"), "fit_cache", "--src", str(replay_run), "--seeds", "0,1", "--mode",
                   "off", "--tag", f"off_{stamp}", "--direct-seeds", "0,1", "--out", str(out)], timeout=3600,
                  log=OUT / "checks" / "pytest_fit_cache_off.log")
    assert done.returncode == 0, done.stdout[-5000:]
    res = read(out)
    assert res["compared"] == 2 and res["all_bitwise"], res["seeds"]
    assert all("own_separate_bitwise" in r for r in res["seeds"].values())
    state = tmp_path_factory.mktemp("dp_tabcache")
    out = OUT / "checks" / "pytest_fit_cache_built.json"
    try:
        done = run_py([str(PKG / "dp_selftest.py"), "fit_cache", "--src", str(replay_run), "--seeds", "2", "--mode",
                       "use", "--tag", f"built_{stamp}", "--out", str(out)], timeout=3600,
                      env={"DP_STATE": str(state)}, log=OUT / "checks" / "pytest_fit_cache_built.log")
        assert done.returncode == 0, done.stdout[-5000:]
        res = read(out)
        assert res["per_seed"]["season2026_seed2"]["how"] == "built", res["per_seed"]
        assert res["compared"] == 1 and res["all_bitwise"], res["seeds"]
    finally:
        shutil.rmtree(state, ignore_errors=True)


@needs_tree
def test_history_check_recorded(replay_run):
    """run_day runs the history check beside the states step: its result must still reach tables.json, and run_day
    must have waited for it."""
    hist = read(replay_run / "history.json")
    tab = read(replay_run / "tables.json")
    assert tab["history_line"] == hist["history_line"] and "->" in hist["history_line"]
    assert "history" in read(replay_run / "run_day.json")["steps"]


def test_side_names_follow_stage0_sides():
    """predictions.csv's names come from Stage 0's player rows by side, never from the matchups CSV (whose player_a is
    side B whenever its id sorts higher: reported 11 Oct 2026). A match whose player rows disagree with its A/B ids, or
    give a side twice, is refused."""
    import pandas as pd

    import dp_steps as S
    matches = pd.DataFrame({"match_id": ["m1", "m2"], "player_a_id": ["atp:1", "atp:4"], "player_b_id": ["atp:2", "atp:3"]})
    players = pd.DataFrame({"match_id": ["m1", "m1", "m2", "m2", "m9"], "player_id": ["atp:2", "atp:1", "atp:4", "atp:3", "x"],
                            "side": ["B", "A", "A", "B", "A"], "player_name": ["Iga", "Elise", "Ann", "Bea", "None"]})
    out = S.side_names(matches, players).set_index("match_id")
    assert out.loc["m1", ["player_a_name", "player_b_name"]].tolist() == ["Elise", "Iga"]
    assert out.loc["m2", ["player_a_name", "player_b_name"]].tolist() == ["Ann", "Bea"]
    assert list(out.index) == ["m1", "m2"]
    wrong = players.assign(side=["A", "B", "A", "B", "A"])            # m1's sides swapped against its ids
    with pytest.raises(RuntimeError, match="disagree"):
        S.side_names(matches, wrong)
    twice = players.assign(side=["A", "A", "A", "B", "A"])
    with pytest.raises(RuntimeError, match="twice"):
        S.side_names(matches, twice)


def test_quote_times_follow_csv_rows():
    """The matchups CSV's optional quoted_at reaches each live match by row (live_from_matchups keeps the CSV's order),
    as UTC; rows whose tour or round disagree are refused rather than misplaced; no column, no times."""
    import pandas as pd

    import dp_matchups as MU
    meta = pd.DataFrame({"match_id": ["m1", "m2"], "tour": ["atp", "wta"], "round": ["R32", "QF"]})
    csv = pd.DataFrame({"tour": ["atp", "wta"], "round": ["r32", "QF"],
                        "quoted_at": ["2026-10-11T17:15:02+00:00", "2026-10-11T10:16:00-07:00"]})
    assert MU.quote_times(meta, csv).tolist() == ["2026-10-11T17:15:02Z", "2026-10-11T17:16:00Z"]
    assert MU.quote_times(meta, csv.drop(columns="quoted_at")).tolist() == [None, None]
    assert MU.quote_times(meta, None).tolist() == [None, None]
    with pytest.raises(SystemExit, match="line up"):
        MU.quote_times(meta, csv.iloc[::-1].reset_index(drop=True))


def test_run_day_never_deletes_another_runs_work_tree(tmp_path):
    """A run refused because another run's work tree exists must leave that tree in place (run_day deletes only a tree
    whose marker names it: found by the tennis-predictions-fc session's review, 11 Oct 2026)."""
    tree = tmp_path / "other_runs_tree"
    (tree / "data").mkdir(parents=True)
    (tree / ".prediction_run_sandbox").write_text(json.dumps({"owner": "another run"}), encoding="utf-8")
    run = tmp_path / "run"
    done = run_py([str(PKG / "dp.py"), "run_day", "--run", str(run), "--replay-week", REPLAY["week"],
                   "--replay-round", REPLAY["round"], "--checkpoint", REPLAY["checkpoint"]], timeout=600,
                  env={"DP_WORK_TREE": str(tree)})
    assert done.returncode != 0
    assert "exists" in done.stdout + done.stderr
    assert (tree / ".prediction_run_sandbox").exists() and (tree / "data").is_dir()


@needs_tree
def test_prediction_names_are_stage0_sides(replay_run):
    """Each predicted match's player_a / player_b is the name the template build's own Stage 0 gives player_a_id /
    player_b_id in that match (the replay keeps the matches' ids and sides): a name beside the other side's figures
    fails here."""
    import pandas as pd
    pred = pd.read_csv(replay_run / "predictions.csv").astype({"match_id": str})
    players = pd.read_parquet(TREE / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet",
                              columns=["match_id", "player_id", "player_name"]).astype({"match_id": str})
    name = players.set_index(["match_id", "player_id"])["player_name"]
    for side in ("a", "b"):
        want = name.reindex(pd.MultiIndex.from_arrays([pred["match_id"], pred[f"player_{side}_id"]])).to_numpy()
        assert pred[f"player_{side}"].notna().all()
        assert (pred[f"player_{side}"].to_numpy() == want).all(), pred[["match_id", f"player_{side}_id", f"player_{side}"]]


@needs_tree
def test_states_ran_in_three_processes(replay_run):
    """Test 2's inputs came through the states step's three processes (the IOS and Stage B's forms in their own)."""
    sec = read(replay_run / "states.json")["record"]["seconds"]
    assert {"ios_family", "forms_family", "waited_for_forms_and_ios"} <= set(sec), sorted(sec)
