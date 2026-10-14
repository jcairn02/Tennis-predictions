"""Tests of the IOS constants registry (src/eda/ios_constants/registry.py): a version is hashed and never edited, the
pointer decides what the builders read and keeps every activation, a revert is an activation, a build can pin one
version for all its workers, and the first version holds exactly the constants the frozen reference of 8 Oct 2026 was
built with.

Run: ./python.sh -m pytest test/ios_constants -q
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.ios_constants import registry as IC  # noqa: E402

FIRST = "2026-10-08_reference"
FROZEN = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.setenv(IC.ENV, "unset at teardown")    # so a pin() inside a test is undone afterwards
    monkeypatch.delenv(IC.ENV)
    monkeypatch.setattr(IC, "surface_means_fingerprint", lambda: "surface-means")


def stage_b(folder: Path, kappa: float = 1.0, tau: int = 1, name: str = "stageB_ios_summary.json") -> Path:
    """A Stage B summary in stageB_ios.py's format; bp_saved without decay, as the men's is."""
    chosen = [{"tour": t, "stat": s, "h": "inf" if s == "bp_saved" else 52.0, "kappa": kappa, "tau": tau,
               "tuning_better_milli_per_unit": 1.0} for t in IC.TOURS for s in IC.STATS]
    units = [{"stat": s, "tour": t, "units": 70.0 + i} for i, (s, t) in
             enumerate((s, t) for s in IC.STATS for t in IC.TOURS)]
    p = folder / name
    p.write_text(json.dumps({"generated_at": "2026-10-02T21:43:49+00:00", "chosen": chosen, "typical_units": units}),
                 encoding="utf-8")
    return p


def surface(folder: Path, mult: float = 10.0, name: str = "tuning_choice.json") -> Path:
    """A surface tuning choice in summarise_tuning.py's format: shared penalties, the women's holds pooled (None)."""
    c = {f"{t}|{s}": {"h_mult": 1.0, "variant": "shared", "ks_mult": mult, "kE_mult": mult, "kF_mult": mult,
                      "h": 52.0, "kappa": 1.0, "gain_vs_current_all": 0.1, "current_h": 52.0}
         for t in IC.TOURS for s in IC.STATS}
    c["wta|hold"].update(variant="pooled", ks_mult=None, kE_mult=None, kF_mult=None)
    p = folder / name
    p.write_text(json.dumps(c), encoding="utf-8")
    return p


@pytest.fixture
def reg(tmp_path):
    r = tmp_path / "registry"
    IC.add("v1", "the first", stage_b(tmp_path), surface(tmp_path), {"atp": 4, "wta": 13}, reg=r)
    IC.activate("v1", "start", reg=r)
    return r


def test_the_builders_get_the_active_version_in_their_own_shapes(reg):
    v = IC.current(reg)
    assert v["id"] == "v1" and v["selected_by"] == "active.json"
    chosen, typ = IC.ios_constants(v)
    assert chosen[("atp", "spw")] == {"h": 52.0, "kappa": 1.0, "tau": 1} and type(chosen[("atp", "spw")]["tau"]) is int
    assert chosen[("wta", "bp_saved")]["h"] == math.inf
    assert typ[("spw", "atp")] == 70.0 and typ[("spw", "wta")] == 71.0          # keyed (stat, tour), as before
    assert IC.short_h(v) == {"atp": 4.0, "wta": 13.0}
    sc = IC.surface_choice(v)
    assert sc["atp|ace"] == {"variant": "shared", "h_mult": 1.0, "ks_mult": 10.0, "kE_mult": 10.0, "kF_mult": 10.0}
    assert sc["wta|hold"] == {"variant": "pooled", "h_mult": 1.0, "ks_mult": None, "kE_mult": None, "kF_mult": None}


def test_an_edited_version_is_refused_even_with_its_hash_redone(reg):
    path = reg / "versions" / "v1.json"
    v = json.loads(path.read_text(encoding="utf-8"))
    v["constants"]["base"]["atp|spw"]["kappa"] = 3.0
    path.write_text(json.dumps(v), encoding="utf-8")
    with pytest.raises(ValueError, match="was edited"):
        IC.current(reg)
    assert not IC.verify(reg)["ok"]
    v["sha256"] = IC.digest(v["constants"])                       # a consistent edit: the version alone now checks out
    path.write_text(json.dumps(v), encoding="utf-8")
    assert IC.load("v1", reg)["sha256"] == v["sha256"]
    with pytest.raises(ValueError, match="after its activation"):
        IC.current(reg)


def test_a_new_version_replaces_only_what_is_given_and_a_revert_is_an_activation(reg):
    v1 = IC.load("v1", reg)
    v2 = IC.add("v2", "a longer men's short memory", short={"atp": 13, "wta": 13}, reg=reg)
    assert v2["based_on"] == "v1" and v2["sha256"] != v1["sha256"]
    for block in ("base", "typical_units", "surface"):
        assert v2["constants"][block] == v1["constants"][block] and v2["sources"][block] == v1["sources"][block]
    assert IC.current(reg)["id"] == "v1"                          # added, not active
    IC.activate("v2", "try it", reg=reg)
    assert IC.short_h(IC.current(reg)) == {"atp": 13.0, "wta": 13.0}
    IC.activate("v1", "revert", reg=reg)
    assert IC.short_h(IC.current(reg)) == {"atp": 4.0, "wta": 13.0}
    hist = IC.pointer(reg)["history"]
    assert [h["version"] for h in hist] == ["v1", "v2", "v1"] and [h["reason"] for h in hist] == ["start", "try it",
                                                                                                    "revert"]
    with pytest.raises(ValueError, match="already the active"):
        IC.activate("v1", "again", reg=reg)


def test_a_version_is_never_overwritten_or_duplicated(reg, tmp_path):
    with pytest.raises(FileExistsError):
        IC.add("v1", "again", short={"atp": 5, "wta": 13}, reg=reg)
    with pytest.raises(ValueError, match="exactly"):
        IC.add("v9", "the same constants", stage_b(tmp_path, name="copy.json"), reg=reg)
    with pytest.raises(ValueError, match="note"):
        IC.add("v9", " ", short={"atp": 5, "wta": 13}, reg=reg)
    with pytest.raises(ValueError, match="version id"):
        IC.add("../v9", "a path", short={"atp": 5, "wta": 13}, reg=reg)


def test_the_first_version_needs_every_block(tmp_path):
    with pytest.raises(ValueError, match="first version"):
        IC.add("v1", "no surface", stage_b(tmp_path), None, {"atp": 4, "wta": 13}, reg=tmp_path / "r")


def test_unusable_values_are_refused(tmp_path):
    r = tmp_path / "r"
    with pytest.raises(ValueError, match="tau"):
        IC.add("v1", "tau 2", stage_b(tmp_path, tau=2), surface(tmp_path), {"atp": 4, "wta": 13}, reg=r)
    with pytest.raises(ValueError, match="kappa"):
        IC.add("v1", "kappa 0", stage_b(tmp_path, kappa=0.0), surface(tmp_path), {"atp": 4, "wta": 13}, reg=r)
    bad = json.loads(surface(tmp_path).read_text(encoding="utf-8"))
    bad["atp|ace"]["kF_mult"] = 3.0                               # "shared" with two different penalties
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="does not fit"):
        IC.add("v1", "mixed", stage_b(tmp_path), tmp_path / "bad.json", {"atp": 4, "wta": 13}, reg=r)
    del bad["atp|ace"]
    (tmp_path / "short.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="cells missing"):
        IC.add("v1", "a cell short", stage_b(tmp_path), tmp_path / "short.json", {"atp": 4, "wta": 13}, reg=r)
    with pytest.raises(ValueError, match="tours"):
        IC.add("v1", "one tour", stage_b(tmp_path), surface(tmp_path), {"atp": 4}, reg=r)
    assert not (r / "versions").exists() or not list((r / "versions").glob("*.json"))


def test_a_pin_holds_for_the_build_and_its_workers_whatever_the_pointer_does(reg, monkeypatch):
    IC.add("v2", "another", short={"atp": 26, "wta": 26}, reg=reg)
    monkeypatch.setenv(IC.ENV, "v2")                              # a candidate build trying v2
    assert IC.current(reg)["id"] == "v2" and IC.current(reg)["selected_by"] == IC.ENV
    monkeypatch.delenv(IC.ENV)
    v = IC.pin(reg)
    assert v["id"] == "v1" and IC.record(v) == {"version": "v1", "sha256": v["sha256"], "selected_by": "active.json"}
    IC.activate("v2", "moved during the build", reg=reg)
    assert IC.current(reg)["id"] == "v1"
    with ProcessPoolExecutor(max_workers=1) as ex:               # spawned workers inherit the pin
        assert ex.submit(os.getenv, IC.ENV).result() == "v1"


def test_check_reports_what_adding_the_tuning_outputs_would_change(reg, tmp_path):
    v = IC.current(reg)
    same = IC.check(v, stage_b(tmp_path, name="same.json"), surface(tmp_path, name="same_choice.json"))
    assert not same["drift"] and same["surface_means_unchanged"]
    moved = IC.check(v, stage_b(tmp_path, kappa=3.0, name="retuned.json"), surface(tmp_path, mult=30.0, name="c.json"))
    assert moved["drift"] and len(moved["stage_b_summary"]["base_differs"]) == 16
    assert len(moved["surface_choice"]["surface_differs"]) == 15                 # the pooled cell has no multiple
    assert "differ in 16 cells" in IC.check_line(moved)
    assert IC.check(v, tmp_path / "absent.json", surface(tmp_path, name="c2.json"))["drift"]


@pytest.mark.skipif(not (IC.REG / "versions" / f"{FIRST}.json").exists(), reason="the registry is not seeded")
def test_the_first_version_is_the_frozen_reference_constants():
    v = IC.load(FIRST)
    assert IC.short_h(v) == {"atp": 4.0, "wta": 13.0}
    inv = FROZEN / "inventory.csv.gz"
    if inv.exists():                                              # the source files are the ones the reference saw
        with gzip.open(inv, "rt", encoding="utf-8", newline="") as f:
            hashes = {r["path"]: r["sha256"] for r in csv.DictReader(f)}
        assert v["sources"]["base"]["sha256"] == hashes["data/studies/ufc_ideas/stageB_ios_summary.json"]
        assert v["sources"]["surface"]["sha256"] == hashes["data/studies/surface_ios/tuning_choice.json"]
    code = FROZEN / "code" / "src" / "eda" / "match_timing" / "rebuild.py"
    if code.exists():                                             # the short memory the reference's code hard-coded
        m = re.search(r'SHORT_H = \{"atp": ([\d.]+), "wta": ([\d.]+)\}', code.read_text(encoding="utf-8"))
        assert m and IC.short_h(v) == {"atp": float(m.group(1)), "wta": float(m.group(2))}
    for name, src in (("base", IC.STAGEB_SUMMARY), ("surface", IC.SURFACE_CHOICE)):
        if src.exists() and IC.file_sha256(src) == v["sources"][name]["sha256"]:
            got = IC.base_from(src)[0] if name == "base" else IC.surface_from(src)
            assert got == v["constants"][name]
