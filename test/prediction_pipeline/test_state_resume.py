"""The saved-state logic of the prediction-pipeline plan (docs/studies/prediction_pipeline/PLAN.md, section 4).

Each check runs src/eda/prediction_pipeline/pp_selftest.py in its own process (it imports the build tree's code, not
the repository's). The build tree defaults to the current instance's sandbox (PP_TREE overrides it); the tests skip
when it is absent.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SELFTEST = ROOT / "src" / "eda" / "prediction_pipeline" / "pp_selftest.py"
TREE = Path(os.environ.get("PP_TREE", "C:/Users/zerom/tnr_lyr_new"))


def run(check: str) -> dict:
    done = subprocess.run([sys.executable, str(SELFTEST), check, "--tree", str(TREE)], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=900)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-4000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_pandas_grouped_cumsum_is_compensated():
    res = run("kahan")
    assert res["groupby_cumsum_last"] == 7.0 and res["naive_last"] == 3.0


needs_tree = pytest.mark.skipif(not (TREE / "src" / "eda").is_dir(), reason=f"no build tree at {TREE}")


@needs_tree
def test_ios_checkpoint_resume_is_exact_and_older_table_within_tolerance():
    res = run("ios")
    assert res["bitwise"] and res["resumed_rows"] > 0
    assert res["older_table_max_abs_diff"] <= 1e-6
    assert res["players_old_new"][0] < res["players_old_new"][1]       # the older system really is smaller


@needs_tree
def test_elo_state_resume_and_remap_are_exact():
    res = run("elo")
    assert res["bitwise"] and res["matches_resumed"] > 0
    assert res["players_old_new"][0] < res["players_old_new"][1]
