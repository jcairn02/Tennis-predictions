"""Guards for role G's P7 plan (docs/studies/lower_level_evidence/system/P7_plan.md): every command-line flag the plan
cites still exists in the script it names, and the plan's own dry-run scripts keep their rules. Source text and synthetic
frames only: nothing is built, fitted or scored, and no outcome is read.

The second group lists the code paths the plan's section 10 says are missing before the P7 arms can be built and scored.
They are marked xfail (not strict): today they fail by design; when the owning role adds the path they "xpass", which is
the signal to re-read the plan's commands for that step.

Run: ./python.sh -m pytest test/lower_level_evidence/test_p7_plan_commands.py -q
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
LLE = ROOT / "src" / "eda" / "lower_level_evidence"
P7 = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "p7_plan" / "scripts"

# script -> the flags the plan cites (P7_plan.md sections 1-6 and Appendix B)
CITED = {
    LLE / "candidate_stage0.py": ["--label", "--sources", "--revisions", "--sofascore-skip", "--out", "--checks",
                                  "--ready", "--derive-from", "--until", "--round-union"],
    LLE / "relationship.py": ["--steps", "--stage0-dir", "--timing", "--strength", "--through", "--first-season",
                              "--last-season", "--stats", "--h-grid", "--workers", "--boot", "--out", "--work",
                              "--method", "--freeze", "--mechanical"],
    LLE / "system_sandbox.py": ["--setup", "--patch", "--check", "--sandbox", "--n", "--stage0"],
    LLE / "system_new_arms.py": ["--patch", "--check", "--lane0-check", "--strength", "--sandbox", "--stage0",
                                 "--from", "--name"],
    LLE / "system_arms.py": ["--prepare", "--config", "--build", "--status", "--write-configs", "--freeze-hashes",
                             "--sandbox", "--lanes", "--no-reuse", "--resume-from"],
    LLE / "system_gates.py": ["--arm", "--sandbox", "--ready", "--dose"],
    LLE / "system_fits.py": ["--verify", "--part1", "--fit", "--fit60", "--check-fits", "--write-expectations",
                             "--seasons", "--seeds"],
    LLE / "system_pairs.py": ["--dev", "--holdout", "--allow-missing", "--without-addition"],
    LLE / "refresh.py": ["--label", "--stage0-dir", "--timing", "--steps", "--scenario"],
    LLE / "classify.py": ["--strength", "--demo", "--analysis"],
    ROOT / "src" / "eda" / "model_rebuild" / "run_chain.py": ["--setup", "--lane", "--collect", "--cleanup", "--from",
                                                              "--out", "--candidate"],
    ROOT / "src" / "eda" / "model_rebuild" / "fits.py": ["--seeds", "--seasons", "--out", "--wait-memory-only"],
    ROOT / "src" / "eda" / "current_best_model" / "compare.py": ["--candidate", "--speed", "--through", "--out"],
    ROOT / "src" / "eda" / "current_best_model" / "history.py": ["--stage0", "--timing"],
}


def flags_of(path: Path) -> set[str]:
    """The long options a script's argparse declares (add_argument's first string)."""
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"add_argument\(\s*\"(--[a-z0-9-]+)\"", text))


@pytest.mark.parametrize("path", sorted(CITED, key=str), ids=lambda p: p.name)
def test_every_cited_flag_exists(path):
    missing = sorted(set(CITED[path]) - flags_of(path))
    assert not missing, f"{path.name}: the plan cites {missing}, which the script no longer declares"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, P7 / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_trigger_check_thresholds_are_the_plans():
    t = load("p7_trigger_check")
    assert t.YIELD_MIN == {"default": 0.90, 2018: 0.75}
    assert t.YIELD_2025_26 == 0.80
    assert (t.AGREE_MIN, t.WINNER_DIFF_MAX) == (0.98, 0.001)


def test_trigger_check_counts_a_synthetic_gap(tmp_path, monkeypatch):
    t = load("p7_trigger_check")
    gaps = tmp_path / "gaps"
    gaps.mkdir()
    rows = []
    for i in range(100):           # 2019: 95 box scores; 2018: 80 box scores of 100
        rows.append({"uid": i, "tour": "W", "year": 2019, "event_id": i, "stats_status": 200.0,
                     "stats_full_box": i < 95})
        rows.append({"uid": 1000 + i, "tour": "W", "year": 2018, "event_id": 1000 + i,
                     "stats_status": 200.0 if i < 99 else None, "stats_full_box": i < 80})
    pd.DataFrame(rows).to_csv(gaps / "sofascore_itf_detail_matches.csv.gz", index=False)
    (gaps / "sofascore_itf_detail_link_check.json").write_text(
        json.dumps({"verdicts": {"agrees": 199, "not linked": 0, "winner differs": 1}}), encoding="utf-8")
    (gaps / "sofascore_itf_detail_summary.json").write_text(
        json.dumps({"gap": "itf_detail", "finished_at": "2026-11-01T00:00:00+00:00"}), encoding="utf-8")
    monkeypatch.setattr(t, "GAPS", gaps)
    monkeypatch.setattr(t, "OUT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["x", "--gap", "itf_detail"])
    rc = t.main()
    res = json.loads((tmp_path / "trigger_itf_detail.json").read_text(encoding="utf-8"))
    assert res["pending"] == 1 and not res["complete"]          # one linked target without a statistics outcome
    assert res["yield_ok"]                                        # 95% >= 90% (2019), 80% >= 75% (2018)
    assert not res["links_ok"]                                    # 1 of 200 winners differs: 0.5% > 0.1%
    assert rc == 1


def test_calibration_rule_flags_a_shifted_count():
    c = load("sofascore_calibration")
    assert (c.AGREE_MIN, c.MEAN_MAX) == (0.90, 0.25)
    assert c.COUNTS == ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]


# ------------------------------------------------------------------------------------------------
# The missing paths of the plan's section 10 (xfail until the owning role adds them)

@pytest.mark.xfail(strict=False, raises=ValueError, reason="P7_plan.md 10 #1: level_layer has no itf_box 'fitted' mode")
def test_layer_accepts_itf_box_fitted():
    from src.eda.lower_level_evidence import level_layer as L
    cfg = {"name": "X", "tours": ["wta"], "params": "p.parquet", "params_sha256": "0" * 64, "translate": True,
           "weight": "fitted", "weight_results": "fitted", "prior": "pool", "itf_box": "fitted",
           "strength": {"path": "s.parquet", "sha256": "0" * 64},
           "families": {f: True for f in L.FAMILIES}}
    L.validate(cfg)


@pytest.mark.xfail(strict=False, raises=AssertionError, reason="P7_plan.md 10 #2: C2's form (b) never estimates an ITF level term")
def test_joint_solves_can_carry_an_itf_level_term():
    from src.eda.lower_level_evidence import level_layer_ios as I
    assert "ITF" not in I.NO_LEVEL_TERM


@pytest.mark.xfail(strict=False, raises=AssertionError, reason="P7_plan.md 10 #3: relationship.py has no --classes, and its freeze record "
                                        "is the frozen run's file")
def test_relationship_takes_a_class_table_and_an_own_freeze_record():
    src = (LLE / "relationship.py").read_text(encoding="utf-8")
    assert "--classes" in flags_of(LLE / "relationship.py")
    assert "FREEZE.write_text" not in src


@pytest.mark.xfail(strict=False, raises=AssertionError, reason="P7_plan.md 10 #4: A's decomposition has no ITF level")
def test_classify_decomposes_itf():
    from src.eda.lower_level_evidence import classify as A
    assert "ITF" in A.LEVELS


@pytest.mark.xfail(strict=False, raises=AssertionError, reason="P7_plan.md 10 #5: system_arms knows no P7 arm")
def test_system_arms_knows_the_p7_arms():
    src = (LLE / "system_arms.py").read_text(encoding="utf-8")
    assert all(a in src for a in ("P7_ASIS", "P7CTL_ASIS", "P7_SYS_EXCL", "P7_SYS_ITF"))


@pytest.mark.xfail(strict=False, raises=AssertionError, reason="P7_plan.md 10 #9: no P7 scorer yet")
def test_a_p7_scorer_exists():
    assert (LLE / "p7_pairs.py").exists()
