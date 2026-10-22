"""The Jupyter interrupt daemon must not hold up a fit; real jobs and low VRAM still do."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.training_window import fits as F  # noqa: E402
from src.pipeline import predict as P  # noqa: E402

LOCAL = str(P.CFG.interpreter("local"))
HELPER = (r"C:\Users\Example User\.vscode\extensions\ms-toolsai.jupyter-2025.9.1-win32-x64"
          r"\pythonFiles\vscode_datascience_helpers\kernel_interrupt_daemon.py")


@pytest.fixture
def processes(monkeypatch):
    """Feed the same processes to the guard's CIM scan and the notebook's psutil scan."""
    rows = []

    def scan(args, **kwargs):
        # Support the original PID-only query as well, to reproduce the bug before the fix.
        stdout = (json.dumps([{"ProcessId": pid, "CommandLine": subprocess.list2cmdline(cmd)}
                              for pid, cmd in rows]) if "ConvertTo-Json" in args[-1]
                  else "\n".join(str(pid) for pid, _ in rows))
        return SimpleNamespace(stdout=stdout, returncode=0)

    monkeypatch.setattr(F.subprocess, "run", scan)
    monkeypatch.setattr(F.os, "getpid", lambda: 999)
    monkeypatch.setattr(psutil, "process_iter", lambda attrs: [
        SimpleNamespace(info={"pid": pid, "exe": LOCAL, "cmdline": cmd}) for pid, cmd in rows])
    return rows


@pytest.mark.parametrize("script", [HELPER, HELPER.replace("\\", "/").upper(),
                                  HELPER.replace("Example User", "zerom")])
def test_interrupt_helper_is_not_a_competing_job(processes, script):
    processes.append((53492, [LOCAL, script, "--ppid", "27060"]))
    assert F.other_local_processes() == []
    assert P.gpu_users() == []


@pytest.mark.parametrize("args", [
    ["src/eda/daily_prediction/dp.py", "fit"],
    ["-m", "ipykernel_launcher", "-f", "kernel.json"],
    ["train.py", "--input", HELPER, "--ppid", "27060"],
    ["-c", "print('kernel_interrupt_daemon.py')"],
    ["kernel_interrupt_daemon.py", "--ppid", "27060"],
    [HELPER],  # An unrecognised invocation stays conservative.
])
def test_other_jobs_still_block_even_with_the_helper_present(processes, args):
    processes.extend([(53492, [LOCAL, HELPER, "--ppid", "27060"]), (123, [LOCAL, *args])])
    assert F.other_local_processes() == [123]
    assert [s.split(":", 1)[0] for s in P.gpu_users()] == ["pid 123"]


def test_fit_still_excludes_itself(processes):
    processes.append((999, [LOCAL, "src/eda/daily_prediction/dp.py", "fit"]))
    assert F.other_local_processes() == []


@pytest.mark.parametrize("stdout, expected", [
    ("", []),
    (json.dumps({"ProcessId": 53492, "CommandLine": subprocess.list2cmdline(
        [LOCAL, HELPER, "--ppid", "27060"])}), []),
    (json.dumps({"ProcessId": 123, "CommandLine": subprocess.list2cmdline([LOCAL, "fit.py"])}), [123]),
    (json.dumps({"ProcessId": 123, "CommandLine": None}), [123]),
])
def test_cim_empty_and_single_object_output(monkeypatch, stdout, expected):
    monkeypatch.setattr(F.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=stdout))
    monkeypatch.setattr(F.os, "getpid", lambda: 999)
    assert F.other_local_processes() == expected


@pytest.fixture
def card(monkeypatch):
    """No CUDA import or real waiting: drive the existing guard's memory and timeout branches."""
    state = {"free": 30.3, "time": 0, "sleeps": 0}
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(
        mem_get_info=lambda: (state["free"] * 2**30, 32 * 2**30))))
    monkeypatch.setattr(F.time, "monotonic", lambda: state["time"])

    def sleep(seconds):
        state["time"] += seconds
        state["sleeps"] += 1

    monkeypatch.setattr(F.time, "sleep", sleep)
    monkeypatch.setattr(F.C, "log", lambda message: None)
    return state


def test_helper_allows_fit_with_enough_memory(processes, card):
    processes.append((53492, [LOCAL, HELPER, "--ppid", "27060"]))
    assert F.wait_for_card(patience_s=1) == pytest.approx(30.3)
    assert card["sleeps"] == 0


def test_real_fit_blocks_despite_enough_memory(processes, card):
    processes.append((123, [LOCAL, "src/eda/model_rebuild/fits.py"]))
    with pytest.raises(RuntimeError, match=r"other processes \[123\]"):
        F.wait_for_card(patience_s=1)
    assert card["sleeps"] == 1


def test_low_memory_still_blocks_with_only_the_helper(processes, card):
    processes.append((53492, [LOCAL, HELPER, "--ppid", "27060"]))
    card["free"] = 11.9
    with pytest.raises(RuntimeError, match=r"other processes \[\], 11.9 GB free"):
        F.wait_for_card(patience_s=1)
    assert card["sleeps"] == 1


def test_fit_starts_when_competing_job_exits(processes, card, monkeypatch):
    processes.extend([(53492, [LOCAL, HELPER, "--ppid", "27060"]), (123, [LOCAL, "fit.py"])])

    def release_job(seconds):
        card["time"] += seconds
        if processes[-1][0] == 123:
            processes.pop()

    monkeypatch.setattr(F.time, "sleep", release_job)
    assert F.wait_for_card(patience_s=31) == pytest.approx(30.3)
    assert [pid for pid, _ in processes] == [53492]  # The helper stays alive.


def test_fit_starts_when_memory_becomes_available(processes, card, monkeypatch):
    processes.append((53492, [LOCAL, HELPER, "--ppid", "27060"]))
    card["free"] = 11.9

    def release_memory(seconds):
        card["time"] += seconds
        card["free"] = 12.0

    monkeypatch.setattr(F.time, "sleep", release_memory)
    assert F.wait_for_card(patience_s=31) == 12.0


def test_memory_is_checked_even_when_process_scan_is_disabled(processes, card):
    card["free"] = 11.9
    with pytest.raises(RuntimeError, match="11.9 GB free"):
        F.wait_for_card(patience_s=1, processes=False)
