"""A notebook kernel that outlives a code change refuses to run it (src/pipeline/__init__.py; 23 Oct 2026: A4 stopped
with "dp_common.py: cannot read its default INSTANCE_ID / DP_BASE_TREE", the kernel of 21 Oct still running the
train.py it had imported then, against the daily engine's file as changed on 22 Oct).

Most cases run the real src/pipeline/__init__.py, copied into a temporary repository beside small stand-in modules, in a
fresh interpreter: the guard notes what each import reads, so a case needs imports no earlier case has made, and files
it may change."""
from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.pipeline as tp  # noqa: E402

HELPERS = """
import os, sys
from pathlib import Path
sys.path.insert(0, os.getcwd())
import src.pipeline as tp

def edit(rel, text):
    # a new text, and a file time that surely differs from the one the import read
    p = Path(rel)
    st = p.stat()
    p.write_text(text, encoding="utf-8")
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))

def attempt(f):
    try:
        print("RAN", f())
    except getattr(tp, "StaleKernel", ()) as e:
        print("REFUSED", str(e).replace(chr(10), " | "))
"""


@pytest.fixture
def repo(tmp_path):
    """A repository holding the real package's __init__.py, stand-ins for two of its modules, and an engine module."""
    pkg = tmp_path / "src" / "pipeline"
    pkg.mkdir(parents=True)
    shutil.copyfile(ROOT / "src" / "pipeline" / "__init__.py", pkg / "__init__.py")
    (pkg / "overview.py").write_text('def status():\n    return "v1"\n', encoding="utf-8")
    (pkg / "data.py").write_text('def morning_refresh():\n    return "m1"\n', encoding="utf-8")
    engine = tmp_path / "src" / "eda" / "engine"
    engine.mkdir(parents=True)
    (engine / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    return tmp_path


def run(repo: Path, body: str, guard: str | None = "1") -> list[str]:
    """`body` in a fresh interpreter started in the repository, after HELPERS; its printed lines. guard: TP_CODE_GUARD
    (None: unset, as in a script)."""
    env = {k: v for k, v in os.environ.items() if k != "TP_CODE_GUARD"}
    if guard is not None:
        env["TP_CODE_GUARD"] = guard
    out = subprocess.run([sys.executable, "-c", HELPERS + textwrap.dedent(body)], cwd=repo, env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    return out.stdout.splitlines()


def test_a_changed_module_is_refused_before_it_runs(repo):
    lines = run(repo, """
        attempt(tp.status)
        edit("src/pipeline/overview.py", 'def status():\\n    return "v2"\\n')
        attempt(tp.status)
    """)
    assert lines[0] == "RAN v1"
    assert lines[1].startswith("REFUSED STOP: tp.status() was not run. This notebook's kernel is running older code")
    assert "src/pipeline/overview.py: loaded " in lines[1] and ", changed " in lines[1]
    assert "Restart the kernel" in lines[1]


def test_the_same_text_rewritten_still_runs(repo):
    lines = run(repo, """
        attempt(tp.status)
        edit("src/pipeline/overview.py", 'def status():\\n    return "v1"\\n')
        attempt(tp.status)
    """)
    assert lines == ["RAN v1", "RAN v1"]


def test_a_module_first_imported_after_its_change_is_current(repo):
    lines = run(repo, """
        attempt(tp.status)
        edit("src/pipeline/data.py", 'def morning_refresh():\\n    return "m2"\\n')
        attempt(tp.morning_refresh)
        edit("src/pipeline/data.py", 'def morning_refresh():\\n    return "m3"\\n')
        attempt(tp.morning_refresh)
        attempt(tp.status)
    """)
    assert lines[:2] == ["RAN v1", "RAN m2"]
    assert all(x.startswith("REFUSED") and "src/pipeline/data.py" in x for x in lines[2:])
    assert "overview.py" not in lines[3]                  # every call refuses; only the changed file is named


def test_an_engine_module_imported_by_its_bare_name_is_watched(repo):
    lines = run(repo, """
        sys.path.insert(0, str(Path("src/eda/engine").resolve()))
        import helper
        attempt(tp.status)
        edit("src/eda/engine/helper.py", "VALUE = 2\\n")
        attempt(tp.status)
    """)
    assert lines[0] == "RAN v1"
    assert lines[1].startswith("REFUSED") and "src/eda/engine/helper.py: loaded " in lines[1]


def test_a_removed_file_is_refused(repo):
    lines = run(repo, """
        attempt(tp.status)
        os.remove("src/pipeline/overview.py")
        attempt(tp.status)
    """)
    assert lines[0] == "RAN v1"
    assert lines[1].startswith("REFUSED") and "src/pipeline/overview.py: loaded " in lines[1]
    assert "since removed" in lines[1]


def test_an_unknown_name_on_a_stale_kernel_says_to_restart(repo):
    lines = run(repo, """
        attempt(tp.status)
        edit("src/pipeline/overview.py", 'def status():\\n    return "v2"\\n')
        try:
            tp.a_function_added_later
        except AttributeError as e:
            print("ATTRIBUTE", e)
    """)
    assert lines[1].startswith("ATTRIBUTE") and "restart the kernel and run SETUP" in lines[1]


def test_a_script_runs_as_before(repo):
    """Outside an IPython session (a script, retrain.sh's calls) the guard is off: the old code runs, as before it."""
    lines = run(repo, """
        attempt(tp.status)
        edit("src/pipeline/overview.py", 'def status():\\n    return "v2"\\n')
        attempt(tp.status)
    """, guard=None)
    assert lines == ["RAN v1", "RAN v1"]


def test_the_guard_is_on_in_an_ipython_session(monkeypatch):
    monkeypatch.delenv("TP_CODE_GUARD", raising=False)
    monkeypatch.setitem(sys.modules, "IPython", SimpleNamespace(get_ipython=lambda: object()))
    assert tp._guarding()
    monkeypatch.setitem(sys.modules, "IPython", SimpleNamespace(get_ipython=lambda: None))
    assert not tp._guarding()                             # IPython imported by a script: no session
    monkeypatch.delitem(sys.modules, "IPython")
    assert not tp._guarding()
    monkeypatch.setitem(sys.modules, "IPython", SimpleNamespace(get_ipython=lambda: object()))
    monkeypatch.setenv("TP_CODE_GUARD", "0")
    assert not tp._guarding()


def test_the_real_package_refuses_its_own_changed_module(monkeypatch):
    """The installed guard on the real package: train.py's record made to differ from its file (no file is touched)."""
    from src.pipeline import train as T
    record = tp._LOADED["src.pipeline.train"]
    assert Path(record[0]).resolve() == Path(T.__file__).resolve()
    monkeypatch.setenv("TP_CODE_GUARD", "1")
    monkeypatch.setitem(tp._LOADED, "src.pipeline.train", (record[0], record[1] - 1, record[2], "0" * 40, record[4]))
    # refused at the name's first look-up (before its module's import), or at the call once it has been looked up
    with pytest.raises(tp.StaleKernel, match=r"tp\.new_instance_path(\(\))? was not run(.|\n)*src/pipeline/train\.py: "
                                             r"loaded .*, changed "):
        tp.new_instance_path()
    monkeypatch.setitem(tp._LOADED, "src.pipeline.train", record)
    assert not any("src/pipeline/train.py" in line for line in tp._changed())


def test_the_calls_keep_their_signatures_and_help():
    from src.pipeline import predict as P
    assert inspect.signature(tp.predict_day) == inspect.signature(P.predict_day)
    assert tp.predict_day.__doc__ == P.predict_day.__doc__ and tp.predict_day.__name__ == "predict_day"
