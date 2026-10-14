"""Tests of the level layer in the current best model (docs/decisions/2026-10-10-level-evidence-layer.md): the hooks in
the repository's builders do nothing while LLE_LAYER is unset, the ceiling rule for seasons after the last fitted one,
the strength each build computes on its own Stage 0 (and its check, and the study's option-(c) re-centring), the
per-build config and its guard, and the lane plans of run_chain.py and of the prediction run.
Run: ./python.sh -m pytest test/current_best_model/test_level_layer_template.py -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import layer_config as LCF  # noqa: E402
from src.eda.lower_level_evidence import level_layer as L  # noqa: E402
from src.eda.lower_level_evidence import level_layer_ios as LI  # noqa: E402
from src.eda.lower_level_evidence import system_sandbox as SB  # noqa: E402

FAMS = {f: True for f in L.FAMILIES}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.delenv(L.ENV, raising=False)
    for c in (L._CFG, L._TABLES, L._BUCKETS, L._BOX, L._SHA):
        c.clear()
    yield
    for c in (L._CFG, L._TABLES, L._BUCKETS, L._BOX, L._SHA):
        c.clear()


# ------------------------------------------------------------------------------------------------
# The hooks are in the builders, and do nothing while LLE_LAYER is unset

def test_the_builders_carry_the_hooks_and_undo_to_the_decided_code():
    for rel in SB.PATCH_SPECS:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert SB.integrated(text, rel), rel
        assert "_LLE" not in SB.unpatched_text(text, rel)
    for rel in LI.PATCHES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert LI.integrated(text, rel), rel
        assert "_LLEIOS" not in LI.unpatched_text(text, rel)
        assert "sandbox only" not in text                     # the integrated tag, not the study's sandbox tag


def test_joint_solve_hooks_off_call_the_decided_solvers_with_their_arguments(monkeypatch, tmp_path):
    calls = []
    IT, IS = LI._it(), LI._is()
    monkeypatch.setattr(IT, "run_timed", lambda *a: calls.append(("timed", a)) or "decided timed")
    monkeypatch.setattr(IS, "run", lambda *a: calls.append(("surface", a)) or "decided surface")
    td = {"tour": "atp"}
    assert LI.run_timed(td, "spw", 4.0, 1.0, 1, "es", "lf", "obs") == "decided timed"
    assert calls[-1] == ("timed", (td, "spw", 4.0, 1.0, 1, "es", "lf", "obs", IT.LOOKBACK))
    assert LI.run_surface(td, "hold", 4.0, 1.0, 2.0, 1, 0.5) == "decided surface"
    assert calls[-1] == ("surface", (td, "hold", 4.0, 1.0, 2.0, 1, 0.5, None, IS.LOOKBACK))
    arrays, meta = {"x": 1}, {"m": 1}
    assert LI.annotate_td(td, None) is td and LI.annotate_cache(arrays, None, None) is arrays
    assert LI.stamp(meta) is meta and LI.runs_dir(tmp_path) == tmp_path


# ------------------------------------------------------------------------------------------------
# The ceiling rule

def params_file(tmp: Path, seasons_by_tour: dict) -> tuple[str, str]:
    recs = []
    for t, seasons in seasons_by_tour.items():
        for y in seasons:
            for lv in L.LOWER:
                for s in ("spw", "results"):
                    recs.append({"season_used": y, "tour": t, "stat": s, "level": lv, "gamma": -0.01 * y,
                                 "delta": 0.001 * y, "w": 0.5 + (y - 2020) * 0.01, "w_joint": 0.6,
                                 "strength_ref": 1700.0})
    p = tmp / "params.parquet"
    pd.DataFrame(recs).to_parquet(p, index=False)
    return str(p), sha(p)


def cfg_with(tmp: Path, **kw) -> dict:
    p, h = params_file(tmp, {"atp": (2020, 2021, 2022), "wta": (2020, 2021)})
    cfg = {"name": "T", "tours": ["atp", "wta"], "params": p, "params_sha256": h, "translate": False,
           "weight": "fitted", "weight_results": 1.0, "prior": "pool", "itf_box": "exclude", "families": dict(FAMS),
           "record_dir": str(tmp / "rec")}
    cfg.update(kw)
    return L.validate(cfg)


def test_ceiling_reads_the_last_fitted_season_per_tour_and_is_recorded(tmp_path):
    cfg = cfg_with(tmp_path, params_season_ceiling="last_fitted")
    assert L.last_fitted(cfg) == {"atp": 2022, "wta": 2021}
    s = L._season_used(cfg, np.array([2020, 2023, 2027, 2022]), np.array(["atp", "atp", "wta", "wta"]))
    assert s.tolist() == [2020, 2022, 2021, 2021]
    w = L.weights(cfg, "spw", np.array(["atp", "atp"]), np.array(["CH", "CH"]), np.array([2022, 2027]))
    assert w[0] == w[1] == pytest.approx(0.52)                  # 2027 reads 2022's fitted w
    rec = [json.loads(x) for x in (tmp_path / "rec" / "layer_calls.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(r["hook"] == "season_ceiling" and r["read_as"] == [2022] for r in rec)


def test_without_the_ceiling_a_later_season_is_an_error_and_the_floor_still_applies(tmp_path):
    cfg = cfg_with(tmp_path, params_season_floor=2020)
    with pytest.raises(KeyError):
        L.weights(cfg, "spw", np.array(["atp"]), np.array(["CH"]), np.array([2023]))
    assert L._season_used(cfg, np.array([2015]), np.array(["atp"])).tolist() == [2020]
    cfg2 = cfg_with(tmp_path, params_season_floor=2020, params_season_ceiling="last_fitted")
    assert L._season_used(cfg2, np.array([2015, 2030]), np.array(["atp", "atp"])).tolist() == [2020, 2022]
    with pytest.raises(ValueError):
        cfg_with(tmp_path, params_season_ceiling=2025)


def test_the_ceiling_leaves_the_study_fingerprints_and_changes_its_own(tmp_path):
    sys_cfg = L.load_config(ROOT / "data/studies/lower_level_evidence/system/arms/configs/SYS.json")
    rec = json.loads((ROOT / "data/studies/lower_level_evidence/system/arms/SYS/build.json").read_text(encoding="utf-8"))
    want = next(r["lane2_runs_dir"]["fingerprint"] for r in rec["runs"] if r.get("lane2_runs_dir"))
    assert LI.fingerprint(sys_cfg, ("ios",)) == want         # the study's recorded fingerprint, recomputed
    off = L.load_config(ROOT / "data/studies/current_best_model/level_layer/official.json")
    assert off["params_season_ceiling"] == "last_fitted"
    assert LI.fingerprint(off) != LI.fingerprint({**off, "params_season_ceiling": None})


# ------------------------------------------------------------------------------------------------
# The official config

def test_the_official_config_is_sys_but_for_the_listed_changes():
    o = json.loads((ROOT / "data/studies/current_best_model/level_layer/official.json").read_text(encoding="utf-8"))
    s = json.loads((ROOT / "data/studies/lower_level_evidence/system/arms/configs/SYS.json").read_text(encoding="utf-8"))
    assert (ROOT / "data/studies/current_best_model/level_layer/official.sha256").read_text().split()[0] == sha(
        ROOT / "data/studies/current_best_model/level_layer/official.json")
    changed = {"name", "record_dir", "families", "what", "written_at"}
    for k, v in s.items():
        if k not in changed:
            assert o[k] == v, k
    assert o["families"] == {**s["families"], "ios_points_short": False}
    assert o["params_sha256"].startswith("4c559abd") and o["classes_sha256"].startswith("58e78622")
    assert o["strength"]["sha256"].startswith("4fa9a573")
    assert (o["tours"], o["itf_box"], o["weight"], o["weight_results"]) == (["atp"], "exclude", "fitted", "fitted")
    LCF.official(ROOT / "data/studies/current_best_model/level_layer/official.json")


# ------------------------------------------------------------------------------------------------
# The strength

def synthetic_stage0(tmp: Path, n_weeks=40, players=30, seed=3) -> Path:
    rng = np.random.default_rng(seed)
    recs, order = [], 0
    for tour in ("atp", "wta"):
        for w in range(n_weeks):
            day = pd.Timestamp("2024-01-01") + pd.Timedelta(days=7 * w)
            for r in (1, 2):
                for k in range(4):
                    a, b = rng.choice(players, 2, replace=False)
                    level = "CH" if k == 3 else "T250"
                    recs.append({"match_id": f"{tour}|{w}|{r}|{k}", "tour": tour, "year": day.year,
                                 "status": "completed" if rng.random() > 0.05 else "retired",
                                 "surface": rng.choice(["Hard", "Clay", "Grass", None]),
                                 "tournament_id": f"{tour}-{w}-{k % 2}", "tournament_date": day, "round_order": r,
                                 "player_a_id": f"{tour}:{a}", "player_b_id": f"{tour}:{b}",
                                 "a_won": bool(rng.random() < 0.5), "map_level": level, "order": order})
                    order += 1
    p = tmp / "stage0_matches.parquet"
    pd.DataFrame(recs).to_parquet(p, index=False)
    return p


K = {"atp": {"k0": 600.0, "offset": 2.0, "shape": 0.6}, "wta": {"k0": 600.0, "offset": 1.0, "shape": 0.6}}


def test_plain_strength_is_stage1s_own_pass(tmp_path, monkeypatch):
    from src.eda.predictability_diagnostic import common as C
    from src.eda.predictability_diagnostic import stage1_baselines as B1
    monkeypatch.setattr(C, "MATCHES", synthetic_stage0(tmp_path))
    s = LCF.plain_strength(K)
    m = C.load_matches()
    for tour in C.TOURS:                                      # Stage 1's tune(): the frozen pass, surface on
        idx = np.flatnonzero(m["tour"].eq(tour).to_numpy())
        t = m.iloc[idx].reset_index(drop=True)
        out = B1.run_elo(B1.history_arrays(t), t["status"], "ret", K[tour], surface=True)
        for j, c in enumerate(LCF.STRENGTH_COLS[1:]):
            assert np.array_equal(s[c].to_numpy()[idx], out[:, j].astype("float32"))
    assert list(s.columns) == LCF.STRENGTH_COLS and s["match_id"].tolist() == m["match_id"].tolist()


def test_check_finds_equality_differences_and_a_scale_shift(tmp_path, monkeypatch):
    from src.eda.predictability_diagnostic import common as C
    monkeypatch.setattr(C, "MATCHES", synthetic_stage0(tmp_path))
    s = LCF.plain_strength(K)
    ref = tmp_path / "ref.parquet"
    s.to_parquet(ref, index=False)
    chk, _ = LCF.check(s, ref)
    assert chk["equal_bit_for_bit"] and chk["differing_matches"] == 0 and not chk["scale_shift"]
    s2 = s.copy()
    s2.loc[5, "elo_a_ret"] += np.float32(0.5)
    chk, _ = LCF.check(s2, ref)
    assert not chk["equal_bit_for_bit"] and chk["differing_matches"] == 1 and not chk["scale_shift"]
    s3 = s.copy()
    atp = s3["match_id"].str.startswith("atp")
    s3.loc[atp, ["elo_a_ret", "elo_b_ret"]] += np.float32(12.0)
    new = s3.iloc[[0]].assign(match_id="atp|new")             # a match the frozen table lacks
    chk, shift = LCF.check(pd.concat([s3, new], ignore_index=True), ref)
    assert chk["scale_shift"] and chk["new_in_build"] == 1
    assert shift.loc["atp"].round(4).eq(12.0).all() and not shift.loc["wta"].any()


def test_centre_reproduces_the_studys_option_c():
    """system_new_arms.strength_centred (addition 7, option c) made NEW_C0_now_elo_optC.parquet from C0_now's plain Elo;
    layer_config.centre on the same inputs gives the same file, bit for bit."""
    arms = ROOT / "data/studies/lower_level_evidence/system/arms/strength"
    src, want = arms / "NEW_C0_now_elo.parquet", arms / "NEW_C0_now_elo_optC.parquet"
    stage0 = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now/stage0_matches.parquet"
    ref = ROOT / "data/studies/lower_level_evidence/system/classes/strength_elo.parquet"
    if not (src.exists() and want.exists() and stage0.exists()):
        pytest.skip("the study's option-(c) files are not in this tree")
    new = pd.read_parquet(src)
    new["match_id"] = new["match_id"].astype(str)
    m = pd.read_parquet(stage0, columns=["match_id", "tour", "year", "tournament_date", "map_level"])
    m["match_id"] = m["match_id"].astype(str)
    chk, shift = LCF.check(new[LCF.STRENGTH_COLS], ref, m)
    assert chk["scale_shift"]
    got = LCF.centre(new[LCF.STRENGTH_COLS], ref, shift, m)
    exp = pd.read_parquet(want)
    exp["match_id"] = exp["match_id"].astype(str)
    assert got["match_id"].tolist() == exp["match_id"].tolist()
    for c in LCF.STRENGTH_COLS[1:]:
        assert np.array_equal(got[c].to_numpy(), exp[c].to_numpy(), equal_nan=True), c


# ------------------------------------------------------------------------------------------------
# The build's config and its guard

def test_resolve_writes_a_valid_build_config_and_the_guard_refuses_another_stage0(tmp_path, monkeypatch):
    from src.eda.predictability_diagnostic import common as C
    tree = tmp_path / "tree"
    st0 = tree / LCF.STAGE0
    st0.parent.mkdir(parents=True)
    src = synthetic_stage0(tmp_path)
    st0.write_bytes(src.read_bytes())
    monkeypatch.setattr(C, "MATCHES", st0)
    frozen = tmp_path / "frozen.parquet"
    LCF.plain_strength(K).to_parquet(frozen, index=False)
    off = json.loads((ROOT / "data/studies/current_best_model/level_layer/official.json").read_text(encoding="utf-8"))
    off.update({"strength": {"path": str(frozen), "sha256": sha(frozen)}, "strength_k": K})
    op = tmp_path / "official.json"
    op.write_text(json.dumps(off), encoding="utf-8")
    op.with_suffix(".sha256").write_text(f"{sha(op)} *official.json\n", encoding="utf-8")
    p = LCF.resolve(op, root=tree)
    cfg = LCF.require_resolved(p, tree)
    assert Path(cfg["strength"]["path"]).parent == tree / LCF.REL_BUILD
    assert cfg["record_dir"] == str(tree / LCF.REL_BUILD / "layer_calls")
    assert cfg["resolved"]["strength_rule"] == "plain"
    chk = json.loads((tree / LCF.REL_BUILD / "strength_check.json").read_text(encoding="utf-8"))
    assert chk["equal_bit_for_bit"]
    LI.validate_config(dict(cfg), "build")
    m = pd.read_parquet(st0)
    m.iloc[:-1].to_parquet(st0, index=False)                  # another Stage 0
    with pytest.raises(SystemExit):
        LCF.require_resolved(p, tree)


# ------------------------------------------------------------------------------------------------
# Maintenance: a refit freezes into its own folder, never over the study's record

def test_relationship_freeze_writes_into_out_and_never_overwrites(tmp_path):
    import argparse
    from src.eda.lower_level_evidence import relationship as R
    study = R.FREEZE
    before = sha(study) if study.exists() else None
    (tmp_path / "params_dev.parquet").write_bytes(b"dev rows")
    a = argparse.Namespace(out=str(tmp_path), method="F4", h_grid="", boot=100, strength=str(R.STAGE1))
    assert R.step_freeze(a) == 0
    rec = json.loads((tmp_path / "method_freeze.json").read_text(encoding="utf-8"))
    assert rec["strength_sha256"] == sha(R.STAGE1) and rec["params_dev_sha256"] == sha(tmp_path / "params_dev.parquet")
    with pytest.raises(SystemExit):
        R.step_freeze(a)                                      # once per folder
    assert R.freeze_path(R.OUT) == study                      # the study's own record, the default --out's
    with pytest.raises(SystemExit):
        R.step_freeze(argparse.Namespace(out=str(R.OUT), method="F4", h_grid="", boot=100, strength=str(R.STAGE1)))
    assert (sha(study) if study.exists() else None) == before
    assert R.verify_frozen(R.freeze_path(tmp_path), R.STAGE1)["params_dev_sha256"] == rec["params_dev_sha256"]


# ------------------------------------------------------------------------------------------------
# The lane plans

def test_run_chain_inserts_the_ios_part_only_with_a_joint_solve_family():
    from src.eda.model_rebuild import run_chain as RC
    off = str(ROOT / "data/studies/current_best_model/level_layer/official.json")
    names = [n for n, _ in RC.lane_steps("1", {"LLE_LAYER": off})]
    i = names.index("leakproof_frame")
    assert names[i - 2:i] == ["lle_ios_part", "lle_ios_merge"]
    assert [n for n, _ in RC.lane_steps("1", {})] == [n for n, _ in RC.LANES["1"]]
    assert RC.lane_steps("2", {"LLE_LAYER": off}) == RC.LANES["2"]


def test_lane_0_keeps_the_packages_timeline_when_they_were_merged(tmp_path, monkeypatch):
    from src.eda.model_rebuild import run_chain as RC
    monkeypatch.setattr(RC, "SANDBOX", tmp_path)
    assert [n for n, _ in RC.lane_steps("0", {})] == [n for n, _ in RC.LANES["0"]]
    rec = tmp_path / RC.ADDITIONS_RECORD
    rec.parent.mkdir(parents=True)
    rec.write_text(json.dumps({"packages": []}), encoding="utf-8")
    assert "timeline" in [n for n, _ in RC.lane_steps("0", {})]          # nothing merged
    rec.write_text(json.dumps({"packages": [{"package": "p", "added": 3}]}), encoding="utf-8")
    assert [n for n, _ in RC.lane_steps("0", {})] == ["stage1_odds", "timing_features"]


def test_run_chain_layer_env_refuses_an_unresolved_sandbox(tmp_path, monkeypatch):
    from src.eda.model_rebuild import run_chain as RC
    monkeypatch.setattr(RC, "SANDBOX", tmp_path)
    assert RC.layer_env(False) == {}
    with pytest.raises(SystemExit):
        RC.layer_env(True)


def test_the_prediction_run_resolves_the_layer_after_stage0_checks():
    from src.eda.prediction_run import run as R
    names = [s[0] for s in R.stage0_steps(False)]
    assert names[names.index("stage0_checks") + 1] == R.LAYER_STEP
    assert names.index(R.LAYER_STEP) < names.index("timing_features")
    assert R.LAYER_STEP not in [s[0] for s in R.stage0_steps(False, layer=False)]
