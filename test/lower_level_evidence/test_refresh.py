"""Tests of the review's refresh (src/eda/lower_level_evidence/refresh.py): the flags, the snapshot, the commands.

Run: ./python.sh -m pytest test/lower_level_evidence/test_refresh.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import refresh as R  # noqa: E402


def _snap(box=None, family=None, exposure=None, levels=None, cred=None, label="x"):
    return {"label": label, "generated_at": "t",
            "composition": {"box_share_by_season": box or {}, "family_dose": family or {},
                            "exposure_under10": exposure or {}},
            "translation": {"levels_with_box_scores": levels or [], "credibility": cred or {}}}


def _seasons(values: dict[int, float], key="wta|h52w") -> dict:
    return {f"{key}|{s}": v for s, v in values.items()}


def test_uneven_dose_flags_a_jump_in_some_seasons_only():
    base = _seasons({s: 0.20 for s in range(2013, 2027)})
    cand = dict(base)
    for s in range(2019, 2025):                        # the shape of the ITF 2018-2024 box scores (P7)
        cand[f"wta|h52w|{s}"] = 0.33
    flags = R.uneven_dose({"box_share_by_season": base}, {"box_share_by_season": cand})
    assert len(flags) == 1 and flags[0]["flag"] == "UNEVEN DOSE" and flags[0]["where"] == "wta|h52w"
    assert flags[0]["moved_seasons"] == list(range(2019, 2025))
    assert 2013 in flags[0]["unmoved_seasons"] and flags[0]["largest_change_points"] == 13.0


def test_a_uniform_shift_is_not_uneven():
    base = _seasons({s: 0.20 for s in range(2013, 2027)})
    cand = {k: v + 0.05 for k, v in base.items()}
    assert R.uneven_dose({"box_share_by_season": base}, {"box_share_by_season": cand}) == []


def test_small_moves_raise_nothing():
    base = _seasons({s: 0.20 for s in range(2013, 2027)})
    cand = dict(base, **{"wta|h52w|2020": 0.22})
    assert R.uneven_dose({"box_share_by_season": base}, {"box_share_by_season": cand}) == []


def test_groups_are_kept_apart():
    base = {**_seasons({s: 0.2 for s in range(2013, 2025)}, "atp|h2w"),
            **_seasons({s: 0.2 for s in range(2013, 2025)}, "wta|h2w")}
    cand = dict(base, **{"wta|h2w|2020": 0.30})
    flags = R.uneven_dose({"box_share_by_season": base}, {"box_share_by_season": cand})
    assert [f["where"] for f in flags] == ["wta|h2w"]


def test_family_dose_and_exposure_thresholds():
    fam = R.threshold_flags("FAMILY DOSE", {"a|wta|2019-24": 0.23, "b|atp|2019-24": 0.34},
                            {"a|wta|2019-24": 0.27, "b|atp|2019-24": 0.35}, R.FAMILY_POINTS)
    assert [f["where"] for f in fam] == ["a|wta|2019-24"] and fam[0]["change_points"] == 4.0
    exp = R.threshold_flags("EXPOSURE", {"wta 2019-24": 0.278}, {"wta 2019-24": 0.290}, R.EXPOSURE_POINTS)
    assert exp == []


def test_new_level_is_flagged():
    flags = R.new_levels({"levels_with_box_scores": ["TQ", "CH"]}, {"levels_with_box_scores": ["TQ", "CH", "ITF"]})
    assert [f["where"] for f in flags] == ["ITF"]


def test_drift_needs_the_base_range_and_fires_outside_it():
    base = {"credibility": {"atp|spw|CH": {"delta": 0.035, "w": 0.58, "delta_lo": 0.029, "delta_hi": 0.040,
                                           "w_lo": 0.49, "w_hi": 0.80},
                            "wta|spw|CH": {"delta": 0.02, "w": 1.0}}}            # no bootstrap: never flagged
    cand = {"credibility": {"atp|spw|CH": {"delta": 0.050, "w": 0.60},
                            "wta|spw|CH": {"delta": 0.09, "w": 0.1}}}
    flags = R.drift(base, cand)
    assert [f["where"] for f in flags] == ["atp|spw|CH delta"]


def test_diff_combines_the_flags_and_the_markdown_lists_them():
    base = _snap(box=_seasons({s: 0.2 for s in range(2013, 2025)}), levels=["CH"], label="base")
    cand = _snap(box=dict(_seasons({s: 0.2 for s in range(2013, 2025)}), **{"wta|h52w|2021": 0.35}),
                 levels=["CH", "ITF"], label="cand")
    flags = R.diff(base, cand)
    assert {f["flag"] for f in flags} == {"UNEVEN DOSE", "NEW LEVEL"}
    md = R.markdown(base, cand, flags)
    assert "## UNEVEN DOSE (1)" in md and "## NEW LEVEL (1)" in md
    assert "No flag" in R.markdown(base, cand, [])


def test_step_commands_carry_the_stage0_label_and_passthrough(tmp_path):
    cmds = R.step_commands(["incoming", "composition", "translation"], tmp_path / "s0", tmp_path / "t.parquet",
                           tmp_path / "f.parquet", "cand1", scores=False, model="reference", boot=30,
                           translation_args="--fit-window 2018-2021 --tune 2019-2021 --validate 2022-2024")
    names = [n for n, _ in cmds]
    assert names == ["incoming", "composition", "translation"]
    inc, comp, tr = (c for _, c in cmds)
    assert str(tmp_path / "s0") in inc and inc[inc.index("--out") + 1].endswith(str(Path("incoming") / "cand1"))
    assert "--no-scores" in comp and comp[comp.index("--label") + 1] == "cand1"
    assert tr[-6:] == ["--fit-window", "2018-2021", "--tune", "2019-2021", "--validate", "2022-2024"]
    assert R.step_commands(["snapshot", "diff"], tmp_path, None, tmp_path, "x", False, "reference", 0) == []


def test_missing_sections_are_flagged_never_read_as_no_change():
    base = _snap(box=_seasons({2020: 0.2}), family={"f|wta|2019-24": 0.2}, exposure={"wta 2019-24": 0.28},
                 levels=["CH"], cred={"atp|spw|CH": {"delta": 0.03, "w": 0.6}}, label="base")
    empty = {"label": "c", "generated_at": "t", "composition": {}, "translation": {}, "incoming": {}}
    flags = R.diff(base, empty)
    assert {f["flag"] for f in flags} == {"MISSING"}
    assert {f["where"] for f in flags} == {"composition.family_dose", "composition.box_share_by_season",
                                           "composition.exposure_under10", "translation.levels_with_box_scores",
                                           "translation.credibility"}
    assert "No flag" not in R.markdown(base, empty, flags)


def test_a_moved_fitting_window_suppresses_drift():
    cred_b = {"atp|spw|CH": {"delta": 0.035, "w": 0.58, "delta_lo": 0.029, "delta_hi": 0.040, "w_lo": 0.49,
                             "w_hi": 0.80}}
    cred_c = {"atp|spw|CH": {"delta": 0.090, "w": 0.20}}
    base = {"translation": {"credibility": cred_b, "windows": {"fit_window": [2010, 2018]}}}
    same = {"translation": {"credibility": cred_c, "windows": {"fit_window": [2010, 2018]}}}
    moved = {"translation": {"credibility": cred_c, "windows": {"fit_window": [2018, 2021]}}}
    assert {f["flag"] for f in R.diff(base, same)} == {"DRIFT"}
    assert {f["flag"] for f in R.diff(base, moved)} == {"WINDOWS CHANGED"}


def test_a_candidate_cannot_take_the_first_runs_label(tmp_path):
    with pytest.raises(SystemExit, match="first run's"):
        R.validate(R.BASE_LABEL, ["composition"], tmp_path / "candidate_stage0", tmp_path / "t.parquet", force=True)


def test_a_candidate_stage0_needs_its_own_timeline(tmp_path):
    with pytest.raises(SystemExit, match="--timing"):
        R.validate("cand_x_never_used", ["composition"], tmp_path / "candidate_stage0", None, force=False)
    assert R.validate("cand_x_never_used", ["composition"], tmp_path / "s0", tmp_path / "t.parquet",
                      force=False) == tmp_path / "t.parquet"
    assert R.validate("anything", ["snapshot", "diff"], tmp_path / "s0", None, force=False) == R.C.TIMING


@pytest.mark.skipif(not R.composition_dir(R.BASE_LABEL).exists(), reason="the first run's outputs are not on disk")
def test_existing_outputs_are_not_overwritten_without_force():
    with pytest.raises(SystemExit, match="would be overwritten"):
        R.validate(R.BASE_LABEL, ["composition"], R.C.STAGE0_DIR, None, force=False)
    assert R.validate(R.BASE_LABEL, ["composition"], R.C.STAGE0_DIR, None, force=True) == R.C.TIMING


def test_unknown_steps_are_refused(tmp_path):
    with pytest.raises(SystemExit, match="unknown steps"):
        R.validate("x", ["compositon"], tmp_path, None, force=False)


@pytest.mark.skipif(not (R.composition_dir(R.BASE_LABEL) / "itf_p7_scenario.csv").exists(),
                    reason="the first run's outputs are not on disk")
def test_the_p7_scenario_flags_womens_uneven_dose_only():
    base = R.snapshot(R.BASE_LABEL)
    flags = R.diff(base, R.scenario_p7(base))
    assert flags and {f["flag"] for f in flags} == {"UNEVEN DOSE"}
    assert {f["where"].split("|")[0] for f in flags} == {"wta"}
    for f in flags:
        assert 2018 in f["moved_seasons"] and 2013 in f["unmoved_seasons"]


@pytest.mark.skipif(not (R.composition_dir(R.BASE_LABEL) / "inputs_dose.csv").exists(),
                    reason="the first run's outputs are not on disk")
def test_the_first_runs_snapshot_reads_every_part():
    s = R.snapshot(R.BASE_LABEL)
    comp, tr, inc = s["composition"], s["translation"], s["incoming"]
    assert comp["family_dose"] and comp["box_share_by_season"] and comp["exposure_under10"]
    assert set(tr["levels_with_box_scores"]) >= {"TQ", "GSQ", "CH", "CHQ"}
    assert any("delta_lo" in v for v in tr["credibility"].values())
    assert inc["p7_share_by_season"]
    assert R.diff(s, s) == []                                             # a run against itself raises nothing
