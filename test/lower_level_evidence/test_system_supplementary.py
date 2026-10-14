"""Tests of the supplementary scoring (src/eda/lower_level_evidence/system_supplementary.py; addition 5): it refuses the
selection arms and anything outside its scope, never touches selection.json, works after the unlock (with the real
lock check), writes only under results/supplementary/, and turns its readings into addition 4's rule-test verdict with
system_decide.rule_test. Synthetic readings only; no real score is read.
Run: ./python.sh -m pytest test/lower_level_evidence/test_system_supplementary.py -q
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402
from src.eda.lower_level_evidence import system_supplementary as SUP  # noqa: E402

REAL = ROOT / "data" / "studies" / "lower_level_evidence" / "system"


def test_refuses_the_selection_arms_and_anything_else():
    for a in SUP.SELECTION_SET:
        with pytest.raises(SystemExit, match="selection arms"):
            SUP.plan([a], "dev")
        with pytest.raises(SystemExit, match="selection arms"):
            SUP.plan(["RES_ONLY", a], "holdout")
    for a in ("REF_noITF", "R_S2", "SYS_S2", "SYS_PLACEBO", "REF"):
        with pytest.raises(SystemExit, match="not a supplementary arm"):
            SUP.plan([a], "dev")
    with pytest.raises(SystemExit):
        SUP.plan(["RES_ONLY"], "both")


def test_plan_names_only_the_registered_pairs(monkeypatch):
    e = {x["arm"]: x for x in SUP.plan(["RES_ONLY", "SYS_BOTH", "NEW_SYS_BOTH"], "holdout")}
    assert e["RES_ONLY"]["vs_ref_full"] and e["RES_ONLY"]["sys_vs"] == ["RES_ONLY"] and SUP.comparators(e["RES_ONLY"]) == ["SYS"]
    assert e["SYS_BOTH"]["vs_ref_full"] and e["SYS_BOTH"]["pairs"] == []
    assert e["NEW_SYS_BOTH"]["pairs"] == [("NEW_SYS_BOTH", "SYS_BOTH"), ("NEW_SYS_BOTH", "NEW_ASIS")]
    assert [p for p, _ in e["NEW_SYS_BOTH"]["periods"]] == [SP.H, SP.PD]
    assert [p for p, _ in e["RES_ONLY"]["periods"]] == [SP.H]
    monkeypatch.setattr(SP, "dev_differs_before_2025", lambda arm: False)
    it = SUP.plan(["SYS_ITFASIS"], "dev")[0]
    assert it["periods"] == [] and "holdout only" in it["note"]                  # identical before 2025: not on dev
    monkeypatch.setattr(SP, "dev_differs_before_2025", lambda arm: True)
    assert SUP.plan(["SYS_BOTH_ITFASIS"], "dev")[0]["pairs"] == [("SYS_BOTH", "SYS_BOTH_ITFASIS")]


def test_source_never_names_the_selection():
    src = (ROOT / "src" / "eda" / "lower_level_evidence" / "system_supplementary.py").read_text(encoding="utf-8")
    assert "SP.SELECTION" not in src and "SELECTION_REGISTERED" not in src and "select_amended" not in src
    assert "SP.dev(" not in src and "SP.holdout(" not in src and "holdout_readings" not in src


# ------------------------------------------------------------------------------------------------
# End to end on a temporary system folder, with the real guards and lock

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def system(tmp_path, monkeypatch):
    d = tmp_path / "system"
    (d / "classes").mkdir(parents=True)
    (d / "relationship").mkdir()
    shutil.copyfile(REAL / "preregistration.md", d / "preregistration.md")
    shutil.copyfile(REAL / "preregistration.sha256", d / "preregistration.sha256")
    (d / "classes" / "classes.csv").write_text("name,class\n", encoding="utf-8")
    (d / "relationship" / "params.parquet").write_bytes(b"PAR1")
    files = {**SP.cp1_files(d), "system_supplementary.py": SUP.THIS}
    add = d / "preregistration_addition_5.md"
    add.write_text("# Addition 5\n" + "\n".join(f"{k} {sha(Path(p))}" for k, p in files.items()) + "\n",
                   encoding="utf-8")
    add.with_suffix(".sha256").write_text(f"{sha(add)} *{add.name}\n", encoding="utf-8")
    res = d / "results"
    res.mkdir()
    monkeypatch.setattr(SP, "SYSTEM", d)
    monkeypatch.setattr(SP, "UNLOCK", d / "holdout_unlock.json")
    monkeypatch.setattr(SP, "RESULTS", res)
    monkeypatch.setattr(SP, "SELECTION", res / "selection.json")
    (res / "selection.json").write_text('{"selected": "SYS", "decision_layer": "sentinel"}', encoding="utf-8")
    return d


def unlock(d: Path) -> None:
    held = {"preregistration_sha256": sha(d / "preregistration.md"),
            "additions": [sha(p) for p in sorted(d.glob("preregistration_addition*.md"))]}
    (d / "holdout_unlock.json").write_text(json.dumps(held), encoding="utf-8")


def fake_rows(entries, period, rule, allow_missing=()):
    """Synthetic readings for every pair the plan names (NEW_SYS_BOTH against SYS_BOTH, men: a harm on the holdout)."""
    rows = []
    for e in entries:
        pairs = list(e["pairs"]) + [("SYS", b) for b in e["sys_vs"]] + ([(e["arm"], "REF")] if e["vs_ref_full"] else [])
        for name, _ in e["periods"]:
            for first, second in pairs:
                for tour in SP.TOURS:
                    est, lo, hi = (-0.20, -0.33, -0.07) if (first, second, tour, name) == (
                        "NEW_SYS_BOTH", "SYS_BOTH", "men", SP.H) else (0.01, -0.10, 0.12)
                    rows.append({"period": name, "group": "supplementary", "comparison": f"{first} vs {second}",
                                 "first": first, "second": second, "stage": "both stages", "tour": tour,
                                 "population": "all", "matches": 100, "estimate": est, "lo": lo, "hi": hi, "se": 0.05,
                                 "p_better": 0.5, "p_better_t": 0.5, "p_two_sided": 0.5, "blocks": 20,
                                 "reading": "worse" if hi < 0 else "unresolved"})
    return pd.DataFrame(rows)


def test_works_after_the_unlock_and_never_touches_selection(system):
    before = (system / "results" / "selection.json").read_bytes()
    unlock(system)                                             # after the unlock: dev and holdout alike
    with pytest.raises(SystemExit, match="unlock"):
        SP.dev()                                               # the main dev run refuses now; the supplementary does not
    SUP.run("dev", ["RES_ONLY", "NEW_SYS_BOTH"], compute_fn=fake_rows)
    s = SUP.run("holdout", ["NEW_SYS_BOTH"], compute_fn=fake_rows)
    assert s["lock"]["preregistration_sha256"] == sha(system / "preregistration.md")
    assert (system / "results" / "selection.json").read_bytes() == before         # untouched, byte for byte
    sup = system / "results" / "supplementary"
    assert (sup / "dev" / "RES_ONLY_pairs.csv").exists() and (sup / "holdout" / "NEW_SYS_BOTH_pairs_drop909.csv").exists()
    written = {p.relative_to(system / "results").parts[0] for p in (system / "results").rglob("*") if p.is_file()}
    assert written == {"selection.json", "supplementary"}                         # nothing written elsewhere
    rt = json.loads((sup / "holdout" / "rule_test.json").read_text())["rule_test"]
    assert rt[SP.H]["tours"]["men"]["verdict"].startswith("not recommended")       # harm on the holdout
    assert rt[SP.H]["decides"] == "C0_now's additions of 2025-2026"
    dev_rt = json.loads((sup / "dev" / "rule_test.json").read_text())["rule_test"]
    assert dev_rt[SUP.DEV]["tours"]["men"]["verdict"].startswith("recommended for entry")
    assert dev_rt[SUP.DEV]["decides"] == "C0_now's additions of 2018-2024"


def test_holdout_needs_the_unlock(system):
    with pytest.raises(SP.HoldoutLocked):
        SUP.run("holdout", ["RES_ONLY"], compute_fn=fake_rows)
    assert not (system / "results" / "supplementary" / "holdout").exists()


def test_freeze_covers_this_module(system):
    add = system / "preregistration_addition_5.md"
    add.write_text("# Addition 5 without this module's hash\n", encoding="utf-8")
    add.with_suffix(".sha256").write_text(f"{sha(add)} *{add.name}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="system_supplementary.py"):
        SUP.run("dev", ["RES_ONLY"], compute_fn=fake_rows)


def test_res_only_flag_reads_the_main_decision_not_the_selection(system):
    (system / "results" / "holdout").mkdir()
    (system / "results" / "holdout" / "decision.json").write_text(
        json.dumps({"primary_speed_rule": {"recommendation": {"recommend": "REF"}}}), encoding="utf-8")
    unlock(system)
    SUP.run("holdout", ["NEW_ASIS", "NEW_SYS_BOTH"], compute_fn=fake_rows)
    rt = json.loads((system / "results" / "supplementary" / "holdout" / "rule_test.json").read_text())["rule_test"]
    assert rt["men_recommendation_read"] == "REF" and rt[SP.H]["register_RES_ONLY_on_C0_now_next"]
