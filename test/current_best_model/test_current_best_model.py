"""Tests of the frozen reference (src/eda/current_best_model/reference.py) and its comparison (compare.py).

Offline and synthetic: the input-drift measures and their flags, the copy check, the freeze's refusal to run twice.
On the frozen reference itself (skipped if it is not on disk): its key files are intact and read-only; the reference
against itself differs by exactly 0, with a zero-width interval (the seed term paired by seed); the previous model against
it reproduces model_rebuild's published per-season rows of 2022-2024 exactly (their unpaired interval, kept as
lo_unpaired / hi_unpaired); no result after --through is read. The seed term itself: test_seed_term.py.

Run: ./python.sh -m pytest test/current_best_model -q
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as G  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402

FROZEN_OK = R.MANIFEST.exists() and (R.FROZEN / R.FILES_CSV).exists()
needs_reference = pytest.mark.skipif(not FROZEN_OK, reason="the frozen reference is not on disk")


def synthetic(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = [{"match_id": f"m{i}", "tour": "atp" if i % 2 else "wta", "season": 2013 + i % 12,
             "in_a": rng.normal(), "in_b": rng.normal(2, 3)} for i in range(2400)]
    return pd.DataFrame(rows).set_index("match_id")


def test_drift_of_identical_frames_is_zero():
    f = synthetic()
    by_season, per_input = G.input_drift(f, f.copy())
    assert (by_season["changed_share"] == 0).all()
    assert np.allclose(by_season["scale_ratio"], 1) and np.allclose(by_season["level_shift_sd"], 0)
    assert set(per_input["flag"]) == {"none"}


def test_drift_flags_one_widened_tour_season_as_uneven():
    ref = synthetic()
    cand = ref.copy()
    m = (cand["tour"] == "wta") & (cand["season"] == 2015)
    cand.loc[m, "in_a"] = cand.loc[m, "in_a"] * 1.3            # the shape of finding #6: one era rescaled
    _, per_input = G.input_drift(ref, cand)
    row = per_input.set_index("input").loc["a"]
    assert row["flag"] == "uneven" and row["flagged"] == "wta 2015"
    assert per_input.set_index("input").loc["b", "flag"] == "none"


def test_drift_flags_a_level_shift_everywhere():
    ref = synthetic()
    cand = ref.copy()
    cand["in_b"] = cand["in_b"] + 0.5 * ref["in_b"].std()
    _, per_input = G.input_drift(ref, cand)
    assert per_input.set_index("input").loc["b", "flag"] == "every season"


def test_drift_lists_inputs_only_in_one_frame():
    ref = synthetic()
    cand = ref.drop(columns=["in_b"]).assign(in_new=1.0)
    _, per_input = G.input_drift(ref, cand)
    flags = dict(zip(per_input["input"], per_input["flag"]))
    assert flags["b"] == "only in the reference" and flags["new"] == "only in the candidate"


def test_copy_and_check_catch_a_changed_copy(tmp_path):
    src = tmp_path / "src.bin"
    src.write_bytes(b"reference")
    size, digest = R.copy_file(src, tmp_path / "frozen" / "x.bin")
    rows = [{"role": "t", "source": str(src), "frozen": "x.bin", "bytes": size, "sha256": digest}]
    ok = R.check(rows, tmp_path / "frozen", sources=False)
    assert not ok["missing"] and not ok["differ"]
    (tmp_path / "frozen" / "x.bin").write_bytes(b"changed!!")
    bad = R.check(rows, tmp_path / "frozen", sources=False)
    assert bad["differ"] == ["x.bin"]


def test_reading_labels():
    assert G.reading(0.1, 0.5) == "better" and G.reading(-0.5, -0.1) == "worse"
    assert G.reading(-0.1, 0.1) == "unresolved" and G.reading(0.0, 0.0) == "unresolved"


@needs_reference
def test_freeze_refuses_to_run_twice():
    with pytest.raises(SystemExit):
        R.freeze()


@needs_reference
def test_key_files_are_intact_and_read_only():
    rows = R.read_rows(R.FROZEN / R.FILES_CSV)
    m = R.C.read_json(R.MANIFEST)
    assert R.sha(R.FROZEN / R.FILES_CSV) == m["files_csv"]["sha256"]
    keys = set(m["key_files"])
    picked = [r for r in rows if r["frozen"] in keys or r["frozen"].startswith("instance/fits/")]
    assert len(picked) == len(keys) + 32
    res = R.check(picked, R.FROZEN, sources=False)
    assert not res["missing"] and not res["differ"]
    assert not any(os.access(R.FROZEN / r["frozen"], os.W_OK) for r in picked)


@needs_reference
def test_no_result_after_through_is_read():
    y = G.outcomes(R.paths("reference"), 2024)
    seasons = G.inputs_frame(R.paths("reference"))["season"]
    assert seasons.reindex(y.index).max() <= 2024
    assert len(y) == int((seasons <= 2024).sum())


def _scores(base: str, cand: str, test, info_from: str = "reference"):
    Pr, Pc = R.paths("reference"), R.paths(cand)
    ref, cnd = G.inputs_frame(Pr), G.inputs_frame(Pc)
    info = G.scoring_info(ref, cnd, G.outcomes(Pr, max(test)), G.outcomes(Pc, max(test)), max(test), base=info_from)
    seasons = tuple(range(G.FIT_FROM, max(test) + 1))
    p_ref = G.seed_table(Pr, ref, seasons).reindex(info.index)
    p_cnd = G.seed_table(Pc, cnd, seasons).reindex(info.index)
    z_cnd = R.speed_column("reference" if cand == "reference" else "previous")
    return G.score(info, p_ref, p_cnd, R.speed_column("reference"), z_cnd, test)[0]


@needs_reference
def test_the_reference_against_itself_is_exactly_zero():
    sc = _scores("reference", "reference", (2022, 2023, 2024))
    vs = sc[sc["comparison"].str.contains("candidate vs reference")]
    assert len(vs) and (vs["estimate"] == 0).all()
    assert (vs["lo"] == 0).all() and (vs["hi"] == 0).all() and (vs["seed_term"] == "paired").all()
    assert (vs["lo_unpaired"] < 0).all()                  # the unpaired term counted the shared seed noise twice


@needs_reference
def test_previous_against_reference_reproduces_the_published_rows():
    """model_rebuild/compare.py compared the rebuilt model (arm) with the previous one (base), match facts from the
    previous frame; here the previous model is the candidate, so every estimate and bound comes out negated. Its
    published bounds are the unpaired ones (lo_unpaired / hi_unpaired here)."""
    sc = _scores("reference", "previous", (2022, 2023, 2024), info_from="candidate")
    pub = pd.read_csv(R.FROZEN / "instance" / "comparison.csv")
    pairs = (("both stages: candidate vs reference", "both stages, rebuilt model with the corrected speed history"),
             ("stage 1: candidate vs reference", "stage 1 (calibrated base)"))
    for Y in (2022, 2023, 2024):
        for mine, theirs in pairs:
            m = sc[(sc["group"] == "season") & (sc["population"] == str(Y)) & (sc["comparison"] == mine)].iloc[0]
            t = pub[(pub["population"] == f"both_{Y}") & (pub["comparison"] == theirs)].iloc[0]
            assert m["matches"] == t["matches"]
            assert abs(m["estimate"] + t["estimate"]) < 1e-9
            assert abs(m["lo_unpaired"] + t["hi"]) < 1e-9 and abs(m["hi_unpaired"] + t["lo"]) < 1e-9
