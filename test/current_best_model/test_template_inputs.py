"""The current best model's input list (src/eda/current_best_model/template_inputs.py): the chain's 58 less the inputs
the owner dropped (ios_points_short, 9 Oct 2026)."""
import json
import shutil
from pathlib import Path

import pytest

from src.eda.current_best_model import template_inputs as TI

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "instance"
TESTED_A2 = ROOT / "data" / "studies" / "lean_review" / "arms" / "A2"


def built_names():
    return TI.names_of(REFERENCE)


def test_the_reference_is_the_built_list_and_the_template_drops_only_ios_points_short():
    names = built_names()
    assert TI.kind(names) == "built" and len(names) == 58
    tmpl = TI.template_names(names)
    assert TI.kind(tmpl) == "template" and len(tmpl) == 57
    assert set(names) - set(tmpl) == {"ios_points_short"}
    assert tmpl == [n for n in names if n != "ios_points_short"]          # order kept


def test_other_lists_are_refused():
    names = built_names()
    with pytest.raises(ValueError):
        TI.kind(names[:-1])                                                 # 57 but with ios_points_short
    with pytest.raises(ValueError):
        TI.kind(TI.template_names(names)[:-1])                              # 56
    with pytest.raises(ValueError):
        TI.kind(names + ["something_new"])                                  # 59
    with pytest.raises(ValueError):
        TI.kind(TI.template_names(names) + [names[0]])                      # a repeated name


def test_apply_rewrites_the_list_once_and_keeps_the_rest(tmp_path):
    # content only: the frozen reference's files are read-only, and must stay so (apply() cannot rewrite them)
    shutil.copyfile(REFERENCE / "model_inputs.json", tmp_path / "model_inputs.json")
    before = json.loads((tmp_path / "model_inputs.json").read_text(encoding="utf-8"))
    r = TI.apply(tmp_path)
    assert r == {"folder": str(tmp_path), "was": "built", "inputs": 57, "dropped": ["ios_points_short"]}
    after = json.loads((tmp_path / "model_inputs.json").read_text(encoding="utf-8"))
    assert [d for d in before["inputs"] if d["name"] != "ios_points_short"] == after["inputs"]
    assert {k: v for k, v in after.items() if k not in ("inputs", "template_dropped")} == \
           {k: v for k, v in before.items() if k != "inputs"}
    assert "ios_points_short" in after["template_dropped"]
    again = TI.apply(tmp_path)
    assert again["was"] == "template" and again["inputs"] == 57
    assert json.loads((tmp_path / "model_inputs.json").read_text(encoding="utf-8")) == after


@pytest.mark.skipif(not (TESTED_A2 / "model_inputs.json").exists(), reason="the lean review's arms are not on disk")
def test_the_template_is_the_list_the_lean_review_tested():
    assert TI.names_of(TESTED_A2) == TI.template_names(built_names())
