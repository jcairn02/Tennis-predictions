"""Tests of role D's scorer and fit queue for the level-evidence system (src/eda/lower_level_evidence/system_pairs.py,
system_fits.py).

The lock: without data/studies/lower_level_evidence/system/holdout_unlock.json holding the hash of every pre-registration
file, no season after 2024 is read (the refusal comes before any frame, fit or result is opened); a wrong hash, a missing
hash, an edited pre-registration, a missing selection hash or a second opening also refuse. Dev needs the checkpoint-1
addition (the hashes of the classes, the parameters and the frozen code as on disk) and refuses after the unlock. Dev
reads results of seasons <= 2024 only. A compared arm with a missing or foreign fit fails loudly. The selection rule,
P(better), Holm's family and the recommendation (addition 2), the 2026 speed rule, the strata, addition 1's reading and
the placebo's permutation on synthetic inputs. No real score is computed here.
Run: ./python.sh -m pytest test/lower_level_evidence/test_system_pairs.py -q
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import system_fits as SF  # noqa: E402
from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402

REAL = ROOT / "data" / "studies" / "lower_level_evidence" / "system"
PREREG_SHA256 = "cc65bcd5eb402326814291156d30c8d7ff4318d7344dd1f636d174bfd6068ae9"
ADDITION1_SHA256 = "c718e6d0696448c7f2a5849cd6e5d2f4443f5e29173b71900f782048a0d48b8a"
ADDITION2_SHA256 = "3f5367969b39003aff28e9e5d29fa35027cf9362d7a4cc321c4eef7249e7a27b"


@pytest.fixture
def system(tmp_path, monkeypatch):
    """A copy of the frozen pre-registration and its hash file in a temporary system folder, made the scorer's (its
    results folder too)."""
    d = tmp_path / "system"
    d.mkdir()
    shutil.copyfile(REAL / "preregistration.md", d / "preregistration.md")
    shutil.copyfile(REAL / "preregistration.sha256", d / "preregistration.sha256")
    monkeypatch.setattr(SP, "SYSTEM", d)
    monkeypatch.setattr(SP, "UNLOCK", d / "holdout_unlock.json")
    monkeypatch.setattr(SP, "RESULTS", d / "results")
    monkeypatch.setattr(SP, "SELECTION", d / "results" / "selection.json")
    return d


@pytest.fixture
def no_reads(monkeypatch):
    """Every way the scorer opens a frame, a fit or a result fails the test if it is reached."""
    def boom(*a, **k):
        raise AssertionError("a frame, fit or result was read before the lock was checked")
    monkeypatch.setattr(SP.CMP, "outcomes", boom)
    monkeypatch.setattr(SP.CMP, "inputs_frame", boom)
    monkeypatch.setattr(SP.CMP, "seed_table", boom)
    monkeypatch.setattr(SP.R, "paths", boom)
    monkeypatch.setattr(SP.R, "speed_column", boom)
    monkeypatch.setattr(SP, "fit_problems", boom)


def write_unlock(d: Path, obj) -> None:
    (d / "holdout_unlock.json").write_text(json.dumps(obj), encoding="utf-8")


def with_addition(d: Path, k: int) -> None:
    for name in (f"preregistration_addition_{k}.md", f"preregistration_addition_{k}.sha256"):
        shutil.copyfile(REAL / name, d / name)


def with_cp1(d: Path) -> Path:
    """Synthetic classes and parameters under d, and a checkpoint-1 addition holding their hashes and the real code
    files' hashes (as the lead's addition will)."""
    (d / "classes").mkdir(exist_ok=True)
    (d / "relationship").mkdir(exist_ok=True)
    (d / "classes" / "classes.csv").write_text("name,class\nspw,OPP\n", encoding="utf-8")
    (d / "relationship" / "params.parquet").write_bytes(b"PAR1 synthetic")
    lines = [f"{k} {SP.hashes_of(p)[0]}" for k, p in SP.cp1_files(d).items()]
    add = d / "preregistration_addition_3.md"
    add.write_text("# Addition 3 (checkpoint 1)\n" + "\n".join(lines) + "\n", encoding="utf-8")
    add.with_suffix(".sha256").write_text(hashlib.sha256(add.read_bytes()).hexdigest() + f" *{add.name}\n")
    return add


# ------------------------------------------------------------------------------------------------
# The pre-registration, the checkpoint-1 freeze and the lock

def test_real_preregistration_hashes_hold():
    got = SP.verify_prereg(REAL)
    assert got["preregistration.md"] == PREREG_SHA256
    assert got["preregistration_addition_1.md"] == ADDITION1_SHA256
    assert got["preregistration_addition_2.md"] == ADDITION2_SHA256


def test_unlock_must_hold_every_preregistration_file(system, no_reads):
    with_addition(system, 1)
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256})            # the addition's hash missing
    with pytest.raises(SP.HoldoutLocked, match="addition_1"):
        SP.verify_unlock()
    with pytest.raises(SP.HoldoutLocked):
        SP.holdout()
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256, "addition_1_sha256": "1" * 64})
    with pytest.raises(SP.HoldoutLocked):
        SP.verify_unlock()
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256,
                          "additions": {"preregistration_addition_1.md": ADDITION1_SHA256}})
    got = SP.verify_unlock()
    assert got["files"] == {"preregistration.md": PREREG_SHA256, "preregistration_addition_1.md": ADDITION1_SHA256}


def test_holdout_refused_without_unlock(system, no_reads):
    assert not (system / "holdout_unlock.json").exists()
    with pytest.raises(SP.HoldoutLocked):
        SP.verify_unlock()
    # the loader itself refuses before reading anything after 2024: fits, results or scores
    with pytest.raises(SP.HoldoutLocked):
        SP.load_models({}, 2026, SP.ALL_FITS, SP.POOLED)
    with pytest.raises(SP.HoldoutLocked):
        SP.load_models({}, 2024, SP.ALL_FITS, SP.DEV_TEST)
    with pytest.raises(SP.HoldoutLocked):
        SP.load_models({}, 2024, SP.DEV_FITS, SP.HOLDOUT)
    with pytest.raises(SP.HoldoutLocked):
        SP.holdout()
    with pytest.raises(SP.HoldoutLocked):
        SP.holdout(without_addition=True)


def test_holdout_refused_with_wrong_hash(system, no_reads):
    write_unlock(system, {"preregistration_sha256": "0" * 64})
    with pytest.raises(SP.HoldoutLocked):
        SP.verify_unlock()
    with pytest.raises(SP.HoldoutLocked):
        SP.holdout()


def test_holdout_refused_without_a_hash_or_unreadable(system, no_reads):
    write_unlock(system, {"unlocked": True, "by": "lead"})
    with pytest.raises(SP.HoldoutLocked):
        SP.verify_unlock()
    (system / "holdout_unlock.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(SP.HoldoutLocked):
        SP.verify_unlock()


def test_holdout_refused_when_the_preregistration_was_edited(system, no_reads):
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256})
    with open(system / "preregistration.md", "a", encoding="utf-8") as fh:
        fh.write("\nan edit after the hash\n")
    with pytest.raises(SP.HoldoutLocked):
        SP.verify_unlock()
    with pytest.raises(SystemExit):
        SP.verify_prereg()


def test_unlock_accepted_with_the_right_hash(system):
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256, "written_by": "lead"})
    got = SP.verify_unlock()
    assert got["preregistration_sha256"] == PREREG_SHA256
    (system / "preregistration.sha256").write_text("f" * 64 + " *preregistration.md\n", encoding="utf-8")
    with pytest.raises(SP.HoldoutLocked):                  # a hash file pointing elsewhere (recorded != held)
        SP.verify_unlock()


def test_holdout_needs_a_final_selection_held_by_the_unlock_and_opens_once(system, monkeypatch):
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256})
    called = []
    monkeypatch.setattr(SP, "load_models", lambda *a, **k: called.append(1))
    monkeypatch.setattr(SP, "gather", lambda *a, **k: called.append(1))
    with pytest.raises(SystemExit, match="selection"):
        SP.holdout(without_addition=True)                  # no selection.json
    (system / "results").mkdir()
    sel = system / "results" / "selection.json"
    sel.write_text(json.dumps({"status": "incomplete", "selected": None}))
    with pytest.raises(SystemExit, match="selection"):
        SP.holdout(without_addition=True)
    sel.write_text(json.dumps({"status": "final", "selected": "SYS", "sides_parquet_sha256": "x"}))
    with pytest.raises(SystemExit, match="decision layer"):
        SP.holdout(without_addition=True)                  # the registered rules' file is not the selection in force
    sel.write_text(json.dumps({"status": "final", "selected": "SYS", "sides_parquet_sha256": "x",
                               "decision_layer": SP.DECISION_LAYER}))
    with pytest.raises(SP.HoldoutLocked, match="selection.json"):
        SP.holdout(without_addition=True)                  # the unlock does not hold selection.json's hash
    (system / "results" / "holdout").mkdir()
    (system / "results" / "holdout" / "readings.json").write_text("{}")
    with pytest.raises(SystemExit, match="opened"):
        SP.holdout(without_addition=True)                  # opened once
    assert not called


def test_holdout_needs_the_checkpoint1_addition(system, monkeypatch):
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256})
    monkeypatch.setattr(SP, "load_models", lambda *a, **k: pytest.fail("read before the checks"))
    with pytest.raises(SystemExit, match="checkpoint-1"):
        SP.holdout()


def test_additions_must_match_their_hashes(system):
    add = system / "preregistration_addition_2026-10-09.md"
    add.write_text("SYS's internals: hashes ...\n", encoding="utf-8")
    with pytest.raises(SystemExit):                    # no hash file
        SP.verify_prereg()
    h = hashlib.sha256(add.read_bytes()).hexdigest()
    add.with_suffix(".sha256").write_text(f"{h} *{add.name}\n", encoding="utf-8")
    got = SP.verify_prereg()
    assert got[add.name] == h and SP.addition_files() == [add]
    add.write_text("changed\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        SP.verify_prereg()


def test_dev_needs_the_checkpoint1_addition_not_any_addition(system):
    with_addition(system, 1)
    with_addition(system, 2)                                                   # neither is checkpoint 1's
    assert SP.cp1_addition()["file"] is None
    with pytest.raises(SystemExit, match="checkpoint-1"):
        SP.dev()
    add = with_cp1(system)
    got = SP.cp1_addition()
    assert got["file"] == add.name and got["missing"] == []
    assert set(got["hashes"]) == {"classes/classes.csv", "relationship/params.parquet", "relationship.py",
                                  "level_layer.py", "level_layer_ios.py", "system_pairs.py", "system_fits.py",
                                  "system_decide.py"}
    (system / "relationship" / "params.parquet").write_bytes(b"PAR1 changed after checkpoint 1")
    moved = SP.cp1_addition()
    assert moved["file"] is None and moved["missing"] == ["relationship/params.parquet"]   # moved on: refused


def test_freeze_accepts_hashes_spread_over_additions(system):
    """Addition 4b may list only the files changed or added since addition 3: each hash may sit in any addition."""
    add3 = with_cp1(system)
    files = SP.cp1_files(system)
    keep = [f"{k} {SP.hashes_of(p)[0]}" for k, p in files.items() if k not in ("system_pairs.py", "system_decide.py")]
    add3.write_text("# Addition 3\n" + "\n".join(keep) + "\n", encoding="utf-8")
    add3.with_suffix(".sha256").write_text(SP.hashes_of(add3)[0] + f" *{add3.name}\n")
    got = SP.cp1_addition()
    assert got["file"] is None and got["missing"] == ["system_decide.py", "system_pairs.py"]
    add4b = system / "preregistration_addition_4b.md"
    add4b.write_text("# Addition 4b\n" + "\n".join(f"{k} {SP.hashes_of(files[k])[0]}"
                                                   for k in ("system_pairs.py", "system_decide.py")) + "\n")
    add4b.with_suffix(".sha256").write_text(SP.hashes_of(add4b)[0] + f" *{add4b.name}\n")
    got = SP.cp1_addition()
    assert got["missing"] == [] and got["file"] == f"{add3.name} + {add4b.name}"
    assert got["held_in"]["system_decide.py"] == add4b.name and got["held_in"]["system_fits.py"] == add3.name
    SP.verify_prereg()                                     # both additions verify against their hash files


def test_dev_refuses_after_the_unlock(system, monkeypatch):
    with_cp1(system)
    write_unlock(system, {"preregistration_sha256": PREREG_SHA256})
    monkeypatch.setattr(SP, "gather", lambda *a, **k: pytest.fail("read after the unlock"))
    with pytest.raises(SystemExit, match="unlock"):
        SP.dev()


def test_dev_results_read_is_filtered(tmp_path):
    """compare.outcomes, as dev mode calls it (through 2024), never returns a later season's result."""
    f = pd.DataFrame({"match_id": [f"m{i}" for i in range(8)], "season": [2023, 2023, 2024, 2024, 2025, 2025, 2026, 2026],
                      "a_won": [1, 0, 1, 0, 1, 0, 1, 0]})
    f.to_parquet(tmp_path / "model_frame.parquet", index=False)

    class P:
        model_frame = tmp_path / "model_frame.parquet"
    y = SP.CMP.outcomes(P, SP.DEV_LAST)
    assert sorted(y.index) == ["m0", "m1", "m2", "m3"]


# ------------------------------------------------------------------------------------------------
# Loud failures: missing or foreign fits

def fake_arm(d: Path, frame_bytes: bytes, seasons, meta_sha: str | None = None, skip=()) -> Path:
    (d / "fits").mkdir(parents=True, exist_ok=True)
    (d / "model_frame.parquet").write_bytes(frame_bytes)
    sha = hashlib.sha256(frame_bytes).hexdigest() if meta_sha is None else meta_sha
    for s in seasons:
        for k in (0, 1, 2, 3):
            if (s, k) in skip:
                continue
            np.savez(d / "fits" / f"model__{s}__seed{k}.npz", meta=np.asarray(json.dumps({"model_frame_sha256": sha})))
    return d


def test_fit_problems_missing_and_foreign_fits(tmp_path):
    good = fake_arm(tmp_path / "good", b"frame A", (2019, 2020))
    assert SP.fit_problems(good, (2019, 2020), registry={}) == []
    gap = fake_arm(tmp_path / "gap", b"frame B", (2019, 2020), skip={(2020, 3)})
    assert SP.fit_problems(gap, (2019, 2020), registry={}) == ["model__2020__seed3.npz: missing"]
    foreign = fake_arm(tmp_path / "foreign", b"frame C", (2019,), meta_sha="9" * 64)
    assert len(SP.fit_problems(foreign, (2019,), registry={})) == 4                  # a stale fit is never scored
    copied = {str((foreign / "fits" / f"model__2019__seed{k}.npz").resolve()):
              SF.sha256(foreign / "fits" / f"model__2019__seed{k}.npz") for k in range(4)}
    assert SP.fit_problems(foreign, (2019,), registry=copied) == []                  # a registered copy passes
    copied[next(iter(copied))] = "0" * 64
    assert len(SP.fit_problems(foreign, (2019,), registry=copied)) == 1             # a copy whose bytes changed


def test_gather_fails_loudly_never_drops(tmp_path, monkeypatch):
    arms = {"SYS": fake_arm(tmp_path / "SYS", b"sys", SP.DEV_FITS),
            "SYS_w0": fake_arm(tmp_path / "SYS_w0", b"w0", SP.DEV_FITS, skip={(2024, 0)}),
            "SYS_w25": fake_arm(tmp_path / "SYS_w25", b"w25", SP.DEV_FITS, skip={(2024, 0)})}
    monkeypatch.setattr(SP.SF, "arm_dir", lambda a: arms.get(a, tmp_path / "absent" / a))
    monkeypatch.setattr(SP.SF, "copied_registry", lambda: {})
    usable, rec = SP.gather(("SYS", "SYS_w25"), SP.DEV_FITS, required=("SYS",))
    assert list(usable) == ["SYS"] and "SYS_w25" in rec["skipped"]                  # optional: skipped, recorded
    with pytest.raises(SystemExit, match="SYS_w0"):
        SP.gather(("SYS", "SYS_w0"), SP.DEV_FITS, required=("SYS", "SYS_w0"))     # a compared arm: loud
    with pytest.raises(SystemExit, match="SEP_ALL"):
        SP.gather(("SYS", "SEP_ALL"), SP.DEV_FITS, required=("SYS", "SEP_ALL"))   # required, no frame: loud
    usable, rec = SP.gather(("SYS", "SEP_ALL"), SP.DEV_FITS, required=("SYS", "SEP_ALL"), allow_missing=("SEP_ALL",))
    assert rec["absent"] == ["SEP_ALL"] and rec["waived"] == ["SEP_ALL"]           # the lead's waiver, recorded


# ------------------------------------------------------------------------------------------------
# The 2026 speed rule (addition 2 section 1)

def test_speed_rule_zero_and_drop909():
    info = pd.DataFrame({"tour": ["atp", "atp", "wta", "atp", "atp"], "season": [2026, 2026, 2026, 2024, 2026],
                         "debut": [False, False, False, False, True]}, index=["a", "b", "c", "d", "e"])
    z = pd.Series({"a": 0.3, "c": np.nan, "d": 0.1})            # b, e absent; c a woman's; all 2026 gaps count
    gap = SP.speed_gap_ids(info, z, (2025, 2026))
    assert sorted(gap) == ["b", "c", "e"]                      # both tours, debut or not (the 909 of addition 2)
    zz = SP.apply_speed_rule(info, z, gap, "zero")
    assert zz.loc[["b", "c", "e"]].tolist() == [0.0, 0.0, 0.0] and zz.loc["a"] == 0.3
    kept = info.drop(index=gap)
    assert list(SP.apply_speed_rule(kept, z, gap, "drop909").index) == ["a", "d"]


# ------------------------------------------------------------------------------------------------
# P(better), the selection rule, Holm, the recommendation

def reading(est: float, se: float) -> dict:
    lo, hi = est - 1.96 * se, est + 1.96 * se
    return {"estimate": est, "se": se, "lo": lo, "hi": hi, "p_better": SP.p_better(est, se),
            "p_better_t": SP.p_better(est, se), "p_two_sided": SP.p_two_sided(est, se),
            "reading": "better" if lo > 0 else "worse" if hi < 0 else "unresolved"}


def test_p_better_is_phi_and_p_two_sided_normal():
    assert SP.p_better(0.1, 0.1) == pytest.approx(norm.cdf(1.0))
    assert SP.p_better(-0.1, 0.1) == pytest.approx(1 - norm.cdf(1.0))
    assert SP.p_better(0.0, 0.05) == pytest.approx(0.5)
    assert np.isnan(SP.p_better(0.0, 0.0))
    assert SP.p_better(0.2, 0.0) == 1.0
    assert SP.p_two_sided(-0.275, 0.1) == pytest.approx(2 * (1 - norm.cdf(2.75)))   # E's example: 0.0060
    assert SP.p_two_sided(0.275, 0.1) == SP.p_two_sided(-0.275, 0.1)
    assert np.isnan(SP.p_two_sided(0.0, 0.0))


def test_holm_adjust():
    adj = SP.holm_adjust([0.01, 0.04, 0.03, 0.005])
    assert adj == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert SP.holm_adjust([float("nan"), 0.001]) == pytest.approx([1.0, 0.002])


def holm_table(values: dict) -> pd.DataFrame:
    """Rows of SELECTED (SYS) vs REF, men, holdout, for the eight family readings: values[(pop, stage)] = (est, se)."""
    rows = []
    for (pop, stage), (est, se) in values.items():
        r = reading(est, se)
        rows.append({"period": SP.H, "first": "SYS", "second": "REF", "tour": "men", "population": pop,
                     "stage": stage, "matches": 500, **r})
    return pd.DataFrame(rows)


def test_holm_family_worse_only_after_correction():
    base = {k: (0.01, 0.1) for k in SP.HOLM_FAMILY}
    base[("season 2025", "both stages")] = (-0.23, 0.1)        # raw worse (z -2.3) but Holm p 0.17: not worse
    h = SP.holm_family(holm_table(base), "SYS")
    assert h["complete"] and h["worse_after_holm"] == [] and h["raw_worse"] == ["season 2025 / both stages"]
    base[("season 2025", "both stages")] = (-0.40, 0.1)        # z -4: Holm p 0.0005: worse
    base[("share gap >= 0.5", "both stages")] = (0.40, 0.1)    # significant but better: never "worse"
    h = SP.holm_family(holm_table(base), "SYS")
    assert h["worse_after_holm"] == ["season 2025 / both stages"]
    del base[("all", "stage 1")]
    assert not SP.holm_family(holm_table(base), "SYS")["complete"]


def test_recommendation_branches_with_holm():
    better, worse, unres = reading(0.2, 0.05), reading(-0.2, 0.05), reading(0.06, 0.05)   # unres: P 0.885
    clean = {"complete": True, "worse_after_holm": []}
    harmed = {"complete": True, "worse_after_holm": ["season 2026 / both stages"]}
    assert SP.recommend(better, None, clean, "SYS")["recommend"] == "SYS"
    assert SP.recommend(worse, None, clean, "SYS")["recommend"] == "REF"
    assert SP.recommend(unres, better, clean, "SYS")["recommend"] == "SYS"
    assert SP.recommend(unres, better, harmed, "SYS")["recommend"] == "unresolved"
    assert SP.recommend(unres, better, {"complete": False, "worse_after_holm": []}, "SYS")["recommend"] == "unresolved"
    assert SP.recommend(unres, unres, clean, "SYS")["recommend"] == "unresolved"
    assert SP.recommend(reading(0.02, 0.05), better, clean, "SYS")["recommend"] == "unresolved"   # P 0.66 < 0.80
    assert SP.recommend(None, None, None, "REF")["recommend"].startswith("REF")
    with pytest.raises(SystemExit, match="never a fall back"):
        SP.recommend(None, None, clean, "SYS")                 # a missing primary is loud, never REF
    r = SP.recommend(unres, better, clean, "SYS")
    assert r["t_cdf_check"]["agrees"]


def base_readings(sys_vs_ref=(0.08, 0.04)):
    sys_vs = {c: reading(0.05, 0.05) for c in SP.CHALLENGERS}        # SYS ahead of every challenger
    vs_ref = {a: reading(0.02, 0.05) for a in SP.CHALLENGERS}
    vs_ref["SYS"] = reading(*sys_vs_ref)
    return sys_vs, vs_ref


def test_sys_stays_selected():
    sys_vs, vs_ref = base_readings()
    s = SP.select(sys_vs, vs_ref)
    assert s["status"] == "final" and s["selected"] == "SYS" and s["qualifying"] == []


def test_ref_when_sys_does_not_lean_better_than_ref():
    sys_vs, vs_ref = base_readings(sys_vs_ref=(-0.01, 0.05))
    s = SP.select(sys_vs, vs_ref)
    assert s["step1_arm"] == "SYS" and s["selected"] == "REF"


def test_challenger_qualifies_at_090_only():
    sys_vs, vs_ref = base_readings()
    se = 0.05
    sys_vs["SEP_ALL"] = reading(-norm.ppf(0.89) * se, se)            # P(SEP_ALL better than SYS) = 0.89
    assert SP.select(sys_vs, vs_ref)["selected"] == "SYS"
    sys_vs["SEP_ALL"] = reading(-norm.ppf(0.91) * se, se)            # 0.91
    s = SP.select(sys_vs, vs_ref)
    assert s["qualifying"] == ["SEP_ALL"] and s["selected"] == "SEP_ALL"


def test_largest_gain_wins_among_qualifiers():
    sys_vs, vs_ref = base_readings()
    sys_vs["SYS_w0"] = reading(-0.20, 0.05)                           # gain 0.20, P ~ 1
    sys_vs["R_S2"] = reading(-0.30, 0.12)                             # gain 0.30, P ~ 0.994
    sys_vs["SYS_w100"] = reading(-0.40, 0.40)                         # gain 0.40 but P 0.84: not qualifying
    s = SP.select(sys_vs, vs_ref)
    assert set(s["qualifying"]) == {"SYS_w0", "R_S2"} and s["selected"] == "R_S2"


def test_qualifier_falls_back_to_ref():
    sys_vs, vs_ref = base_readings()
    sys_vs["SYS_NOCLASS"] = reading(-0.20, 0.05)
    vs_ref["SYS_NOCLASS"] = reading(-0.02, 0.05)                      # P(better than REF) < 0.5
    s = SP.select(sys_vs, vs_ref)
    assert s["step1_arm"] == "SYS_NOCLASS" and s["selected"] == "REF"


def test_selection_incomplete_when_a_challenger_is_missing():
    sys_vs, vs_ref = base_readings()
    sys_vs["SYS_S2"] = None
    s = SP.select(sys_vs, vs_ref)
    assert s["status"] == "incomplete" and s["selected"] is None and s["missing_challengers"] == ["SYS_S2"]


def test_res_only_and_new_arms_stay_out_of_the_selection():
    assert "RES_ONLY" not in SP.CHALLENGERS and "RES_ONLY" in SP.SYS_VS and "RES_ONLY" in SP.REQUIRED_DEV
    assert not set(SP.ITFASIS + SP.NEW) & set(SP.CHALLENGERS + SP.ARMS)
    assert ("NEW_ASIS_PRE", "REF") in SP.ADD1_NEW and ("NEW_ASIS", "NEW_ASIS_PRE") in SP.ADD1_NEW


# ------------------------------------------------------------------------------------------------
# Addition 1

def named(first, second, est, se):
    r = reading(est, se)
    r.update({"first": first, "second": second, "comparison": f"{first} vs {second}", "matches": 100})
    return r


def test_flip_names_the_other_way_round():
    r = named("REF_noITF", "REF", 0.10, 0.04)                 # better
    f = SP.flip(r)
    assert f["comparison"] == "REF vs REF_noITF" and f["estimate"] == -0.10
    assert (f["lo"], f["hi"]) == (-r["hi"], -r["lo"]) and f["reading"] == "worse"
    assert f["p_better"] == pytest.approx(1 - r["p_better"])
    assert SP.flip(None) is None


def test_rule_of_8_october_reading():
    worse_asis = named("NEW_ASIS", "REF", -0.2, 0.05)
    leaning_worse = named("NEW_ASIS", "REF", -0.05, 0.05)       # unresolved, P(better) 0.16 <= 0.20
    unres = named("NEW_ASIS", "REF", 0.0, 0.05)
    better_sys = named("NEW_SYS_BOTH", "SYS_BOTH", 0.2, 0.05)
    assert SP.rule_reading({"a": worse_asis}, {})["reading"] == "the rule is protective"
    assert SP.rule_reading({"a": leaning_worse}, {})["reading"] == "the rule is protective"
    assert SP.rule_reading({"a": unres}, {})["reading"].startswith("unresolved")
    assert SP.rule_reading({"a": unres}, {"s": better_sys})["reading"] == "the rule holds the model back"
    assert SP.rule_reading({"a": worse_asis}, {"s": better_sys})["reading"].startswith("mixed")
    assert SP.rule_reading({"a": None}, {"s": None})["reading"] == "not scored"


def test_queue_order_is_the_leads():
    assert SF.FIT_ORDER[:17] == ("SEP_ALL", "REF_noITF", "SYS", "SYS_w0", "SYS_w100", "RES_ONLY", "SYS_S2", "SYS_PLACEBO",
                                 "SYS_w50", "SYS_NOCLASS", "SYS_BOTH", "SYS_ITFASIS", "SYS_BOTH_ITFASIS", "NEW_ASIS",
                                 "NEW_SYS_BOTH", "NEW_ASIS_PRE", "SYS_w25")
    ready = ["SYS_w50", "SYS", "NEW_ASIS", "SEP_ALL", "RES_ONLY"]
    assert SF.pick_next(ready, set(), set(), set()) == "SEP_ALL"
    assert SF.pick_next(ready, {"SEP_ALL"}, set(), set()) == "SYS"
    assert SF.pick_next(ready, {"SEP_ALL", "SYS"}, set(), set()) == "RES_ONLY"
    assert SF.pick_next(["SYS_ITFASIS", "SYS_w25"], set(), set(), {"SYS_ITFASIS"}) == "SYS_w25"
    assert SF.pick_next([], set(), set(), set()) is None
    assert "NEW_ASIS_PRE" in SF.EXTRA_MATCHES_OK and SF.EXPECT["RES_ONLY"]["families"] == ["elo"]


# ------------------------------------------------------------------------------------------------
# Strata and the placebo

def test_strata_masks():
    sc = pd.DataFrame({"res_a": [5, 30, 25, 12, 40], "res_b": [40, 22, 9, 30, 35],
                       "share_a": [0.9, 0.05, 0.2, np.nan, 0.0], "share_b": [0.1, 0.02, 0.8, 0.3, 0.09]})
    m = SP.strata_masks(sc)
    assert m["exposure < 10"].tolist() == [True, False, True, False, False]
    assert m["share gap >= 0.5"].tolist() == [True, False, True, False, False]
    assert m["share gap < 0.5"].tolist() == [False, True, False, False, True]
    assert m["share gap unknown (left out)"].tolist() == [False, False, False, True, False]
    assert m["falsification: both 20+ main-tour, share < 0.10"].tolist() == [False, True, False, False, True]


def test_placebo_permutes_within_tour_season():
    rng = np.random.default_rng(1)
    n = 400
    ref = pd.DataFrame({"tour": np.repeat(["atp", "wta"], n // 2), "season": np.tile(np.repeat([2019, 2020], n // 4), 2),
                        "in_x": rng.normal(size=n), "in_y": rng.normal(size=n)})
    ref.loc[[3, 250], "in_x"] = np.nan
    sys_ = ref.copy()
    men = (ref["tour"] == "atp").to_numpy()
    sys_.loc[men, "in_x"] = ref.loc[men, "in_x"] - rng.uniform(0, 1, men.sum())           # men only, as SYS
    out, perm, info = SF.placebo_change(ref, sys_, ["x"])
    keys = list(zip(ref["tour"], ref["season"]))
    assert all(keys[i] == keys[perm[i]] for i in range(n))                                 # within tour x season
    assert sorted(perm.tolist()) == list(range(n))                                         # a permutation
    d_sys = np.nan_to_num(sys_["in_x"].to_numpy() - ref["in_x"].to_numpy())
    d_pl = out["x"] - ref["in_x"].to_numpy()
    ok = np.isfinite(ref["in_x"].to_numpy())
    assert np.allclose(d_pl[ok], d_sys[perm][ok], rtol=0, atol=1e-12)                      # each match: a cell-mate's change
    assert np.isnan(out["x"][3]) and np.isnan(out["x"][250])                               # missing stays missing
    assert np.array_equal(out["x"][~men], ref["in_x"].to_numpy()[~men], equal_nan=True)    # women unchanged
    out2, perm2, _ = SF.placebo_change(ref, sys_, ["x"])
    assert np.array_equal(perm, perm2)                                                     # seed 20261009 fixed


def test_every_reference_input_has_a_family():
    names = [n for n, _ in SF.input_names(SF.REF_DIR)]
    fams = {n: SF.family(n) for n in names}
    assert len(names) == 58
    assert sum(f in SF.BOX_FAMILIES for f in fams.values()) == 41       # the 41 box-score inputs (CLAUDE.md)
    counts = pd.Series(fams).value_counts().to_dict()
    assert counts == {"joint_solves": 15, "forms": 17, "products": 7, "workload_intrinsic": 7, "market_context": 7,
                      "elo": 3, "raw_rates": 1, "ratings_iid": 1}
