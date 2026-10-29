"""Shared fixtures of the daily prediction script's tests (docs/studies/daily_prediction/).

The four checks the owner asked for (10 Oct 2026) run the script's real paths, so they need:
    the instance's build tree   DP_BASE_TREE: its tables and code, read only
    the instance                DP_INSTANCE
    the GPU environment         tennis-tabpfn-local, for the price-grid test
Both default to the instance the daily pipeline predicts with (the notebook's selection,
data/studies/master_pipeline/selected_instance.json; 20 Oct 2026: before, the 10 Oct instance and its tree, which every
repair decided since made unequal to a replay, so the tests guarded an instance nobody predicted with). With no
selection and neither variable set, the tests that need an instance skip: there is no default (22 Oct 2026).
and take minutes (the replay builds a work tree and today's tables; the families test builds a checkpoint and
recomputes every family in full). They skip when the tree or the environment is missing.

DP_TEST_REPLAY_RUN names an existing replay run folder to check instead of building one (for re-reading a finished
run's outputs; a fresh run is the default).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src" / "eda" / "daily_prediction"
OUT = ROOT / "data" / "studies" / "daily_prediction"
SELECTED = ROOT / "data" / "studies" / "master_pipeline" / "selected_instance.json"
_sel = json.loads(SELECTED.read_text(encoding="utf-8")) if SELECTED.exists() else {}
if "DP_BASE_TREE" not in os.environ and _sel.get("tree"):
    os.environ["DP_BASE_TREE"] = _sel["tree"]                  # set before any dp module reads it (dp_common, at import)
if "DP_INSTANCE" not in os.environ and _sel.get("instance"):
    os.environ["DP_INSTANCE"] = _sel["instance"]
TREE = Path(os.environ["DP_BASE_TREE"]) if os.environ.get("DP_BASE_TREE") else None
INSTANCE_ID = os.environ.get("DP_INSTANCE") or None
PY = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
PY_TABPFN = Path(os.environ.get("TENNIS_TABPFN_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis-tabpfn-local/python.exe"))
REPLAY = {"week": "2026-07-13", "round": "R16", "checkpoint": "2026-06-22"}

needs_tree = pytest.mark.skipif(TREE is None or not (TREE / "src" / "eda").is_dir(),
                                reason=f"no build tree at {TREE}" if TREE else "no instance selected (no default)")
needs_gpu_env = pytest.mark.skipif(not PY_TABPFN.exists(), reason="no tennis-tabpfn-local environment")

if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))


WORK_TREE = os.environ.get("DP_TEST_WORK_TREE", "C:/Users/zerom/tnr_daily_pytest")   # its own: never a run's


def run_py(args: list[str], timeout: int, env: dict | None = None, log: Path | None = None) -> subprocess.CompletedProcess:
    full = {**os.environ, "PYTHONIOENCODING": "utf-8", "DP_WORK_TREE": WORK_TREE, **(env or {})}
    if log is None:
        return subprocess.run([str(PY), *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, env=full)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8") as fh:
        done = subprocess.run([str(PY), *args], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout, env=full)
    return subprocess.CompletedProcess(done.args, done.returncode, log.read_text(encoding="utf-8", errors="replace"), "")


@pytest.fixture(scope="session")
def replay_run() -> Path:
    """A replay of 13 Jul 2026's round of 16 through run_day (with the fit), or the run DP_TEST_REPLAY_RUN names."""
    held = os.environ.get("DP_TEST_REPLAY_RUN")
    if held:
        return Path(held)
    import datetime as dt
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = OUT / "runs" / f"pytest_replay_{REPLAY['week']}_{REPLAY['round']}_{stamp}"
    done = run_py([str(PKG / "dp.py"), "run_day", "--run", str(run), "--replay-week", REPLAY["week"],
                   "--replay-round", REPLAY["round"], "--checkpoint", REPLAY["checkpoint"], "--direct-seeds", "0,1"],
                  timeout=4 * 3600, log=run.with_suffix(".log"))
    assert done.returncode == 0, done.stdout[-5000:]
    return run


def read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
