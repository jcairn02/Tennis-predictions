"""The runner sets up each step's conda environment itself (14 Oct 2026).

A step started from a shell with no conda environment active (PowerShell, a scheduled task) used to inherit a PATH
without the environment's folders. numpy's MKL then died at its first linear-algebra call (Windows 0xC06D007F, a
lazily loaded library missing a function), silently: three bet-day runs of 14 Oct stopped in their states step. These
tests start steps from such a PATH: they failed before the fix and pass with it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import config as CFG  # noqa: E402
from src.pipeline import runner as R  # noqa: E402

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the conda layout and the failure are Windows'")
ENVS = ("tennis", "local", "api")
LINALG = ("import numpy as np; a = np.random.rand(400, 400); np.linalg.solve(a @ a.T + np.eye(400), a); "
          "print('linalg ok')")


@pytest.fixture()
def sandbox_out(tmp_path, monkeypatch):
    """Logs and receipts of the runner go to a temporary folder."""
    monkeypatch.setattr(CFG, "OUT", tmp_path)
    monkeypatch.setattr(CFG, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(CFG, "RECEIPTS", tmp_path / "runs.jsonl")
    monkeypatch.setattr(R, "RUNNING", tmp_path / "running")
    return tmp_path


@pytest.fixture()
def no_conda_path(monkeypatch):
    """PATH as a shell with no conda environment active has it: every folder of the conda installation removed."""
    conda = str(CFG.interpreter("tennis").parents[2]).lower().rstrip("\\")
    keep = [p for p in os.environ.get("PATH", "").split(os.pathsep)
            if p and not p.lower().rstrip("\\").startswith(conda)]
    monkeypatch.setenv("PATH", os.pathsep.join(keep))
    return keep


@pytest.mark.parametrize("env", ENVS)
def test_each_step_gets_its_environment_folders_first(env, no_conda_path):
    prefix = CFG.interpreter(env).parent
    path = R._child_env(R.Step("x", ["-c", "pass"], env=env))["PATH"].split(os.pathsep)
    want = [prefix, prefix / "Library" / "mingw-w64" / "bin", prefix / "Library" / "usr" / "bin",
            prefix / "Library" / "bin", prefix / "Scripts", prefix / "bin"]
    assert path[:len(want)] == [str(p) for p in want]
    assert path[len(want):] == no_conda_path                      # the inherited PATH follows, unchanged


@pytest.mark.parametrize("env", ENVS)
def test_linear_algebra_runs_from_a_shell_without_conda(env, sandbox_out, no_conda_path):
    res = R.run_step(R.Step(f"linalg_{env}", ["-c", LINALG], env=env), echo=False)
    assert res.ok and "linalg ok" in res.tail


def test_the_fit_environment_loads_under_a_prediction_step(sandbox_out, no_conda_path):
    """The daily engine (a tennis step) starts its fit in the local TabPFN environment, which inherits the step's PATH:
    numpy and pandas, then tabpfn and torch, as the fit imports them, then numpy's linear algebra. Torch's own CPU maths
    is left out: in this environment it and numpy's linear algebra start two OpenMP runtimes that abort the process
    under any PATH, activated or not (OMP Error #15), and the fit computes on the GPU. Skipped while a GPU job runs,
    since the fit's wait for the card counts every local-environment process."""
    from src.pipeline import predict as P
    if P.gpu_users():
        pytest.skip("a local-TabPFN process is running: not adding one")
    child = "import numpy as np, pandas; import tabpfn, torch; " + LINALG.replace("linalg ok", "fit env ok")
    code = (f"import subprocess, sys; r = subprocess.run([{str(CFG.interpreter('local'))!r}, '-c', {child!r}]); "
            "sys.exit(r.returncode)")
    res = R.run_step(R.Step("fit_env", ["-c", code], env="tennis"), echo=False)
    assert res.ok and "fit env ok" in res.tail
