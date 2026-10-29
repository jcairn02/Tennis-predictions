"""The master pipeline: the functions scripts/master_pipeline.ipynb calls (docs/studies/master_pipeline/README.md).

    import src.pipeline as tp        # with the repository root on sys.path
    tp.status()

Names load lazily (PEP 562), so a worker in another environment (the hosted TabPFN's tennis-tabpfn) can import one
module of the package without the others' dependencies.

A notebook's kernel outlives code changes. On 23 Oct 2026 A4 stopped with "dp_common.py: cannot read its default
INSTANCE_ID / DP_BASE_TREE": the kernel, started 21 Oct, still ran the train.py it had imported then, which read the
daily engine's file as changed on 22 Oct. So in a kernel every call through this package first checks the files of
src/ the kernel has imported, and refuses when one has changed on disk since (StaleKernel: restart the kernel, run
SETUP). An agent's choice of 23 Oct 2026, not the owner's words (docs/studies/master_pipeline/process_log.md, Part 11).
"""
from __future__ import annotations

import datetime as dt
import functools
import hashlib
import importlib
import importlib.machinery
import os
import sys
import threading
import time

_NAMES = {
    "status": ("overview", "status"),
    # section B: data
    "morning_refresh": ("data", "morning_refresh"),
    "scheduled_downloads": ("data", "scheduled_downloads"),
    "scheduled_runs": ("data", "scheduled_runs"),
    "refresh_results": ("data", "refresh_results"),
    "held_tml_files": ("data", "held_tml_files"),
    "accept_held_tml": ("data", "accept_held_tml"),
    "refresh_speeds": ("data", "refresh_speeds"),
    "refresh_timeline_sources": ("data", "refresh_timeline_sources"),
    "refresh_odds_history": ("data", "refresh_odds_history"),
    "rebuild_shared_tables": ("data", "rebuild_shared_tables"),
    "weekly_update": ("data", "weekly_update"),
    "lower_level_feed": ("data", "lower_level_feed"),
    "feed_status": ("data", "feed_status"),
    # section C: rebuild and retrain
    "active_instance": ("train", "active_instance"),
    "list_instances": ("train", "list_instances"),
    "instance_status": ("train", "instance_status"),
    "template_check": ("train", "template_check"),
    "model_age": ("train", "model_age"),
    "retrain": ("train", "retrain"),
    "show_model_age": ("train", "show_model_age"),
    "new_instance_path": ("train", "default_out"),
    "use_instance": ("train", "use_instance"),
    "build_instance": ("train", "build_instance"),
    "finish_instance": ("train", "finish_instance"),
    "fit_seasons": ("train", "fit_seasons"),
    "compare_candidate": ("train", "compare_candidate"),
    "check_history": ("train", "check_history"),
    "make_checkpoint": ("train", "make_checkpoint"),
    "replay_check": ("train", "replay_check"),
    "stage2_status": ("train", "stage2_status"),
    "cleanup_build_sandbox": ("train", "cleanup_build_sandbox"),
    "sandboxes": ("train", "sandboxes"),
    "running": ("runner", "running"),
    "paused_jobs": ("data", "paused_jobs"),
    "thinking_status": ("thinking", "status"),
    # section A: the bet day
    "record_pinnacle": ("live", "record_pinnacle"),
    "todays_matches": ("live", "todays_matches"),
    "show_matches": ("live", "show"),
    "build_matchups": ("live", "build_matchups"),
    "check_matchups": ("live", "check_matchups"),
    "data_check": ("readiness", "data_check"),
    "manual_matchups": ("live", "manual_matchups"),
    "live_prices": ("live", "live_prices"),
    "predict_day": ("predict", "predict_day"),
    "reprice": ("predict", "reprice"),
    "grade": ("predict", "grade"),
    "grade_due": ("predict", "grade_due"),
    "latest_run": ("predict", "latest_run"),
    "cleanup_work_tree": ("predict", "cleanup_work_tree"),
    "bet_diagnostics": ("diagnostics", "bet_diagnostics"),
    "clv_ledger": ("closing_line", "clv_ledger"),
    "receipts": ("runner", "receipts"),
}

__all__ = sorted(_NAMES)


_MODULES = {"config", "runner", "overview", "data", "train", "live", "predict", "diagnostics", "bet_sheet", "readiness",
            "thinking", "closing_line"}   # no module may share a name with a function above (it would shadow it)


# --- a kernel running older code than the files on disk ----------------------------------------------------------------
_SRC = os.path.normcase(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + os.sep    # this repository's src/
_REPO = os.path.dirname(_SRC.rstrip(os.sep))
# module -> (file, mtime_ns, size, sha1, when) as its import read it; kept through a reload of this package, which would
# otherwise take the stale files of the modules it does not reload for fresh ones
_LOADED: dict[str, tuple[str, int, int, str, float]] = globals().get("_LOADED", {})
_SEARCHING = threading.local()


class StaleKernel(RuntimeError):
    """A file of src/ that this kernel imported has changed on disk since: restart the kernel."""


def _in_src(path) -> bool:
    return isinstance(path, str) and os.path.normcase(os.path.abspath(path)).startswith(_SRC)


def _record(name: str, path: str) -> None:
    try:
        st = os.stat(path)
        with open(path, "rb") as f:
            digest = hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return
    _LOADED[name] = (path, st.st_mtime_ns, st.st_size, digest, time.time())


class _Recorder:
    """First on sys.meta_path and finding nothing: for a module about to be read from src/ (by its package name or, with
    a folder of src/ on sys.path, by its bare name) it notes the file, then the usual finders import it. A reload is
    noted again."""
    tp_recorder = True

    @staticmethod
    def find_spec(name, path=None, target=None):
        if getattr(_SEARCHING, "on", False) or (path is not None and not any(_in_src(p) for p in path)):
            return None
        _SEARCHING.on = True
        try:
            spec = importlib.machinery.PathFinder.find_spec(name, path)
        except Exception:                                # the note must never break an import
            return None
        finally:
            _SEARCHING.on = False
        if spec is not None and spec.has_location and _in_src(spec.origin):
            _record(name, spec.origin)
        return None


def _note_imported() -> None:
    """This package, and the modules of src/ imported before it, as their files are now (then the import hook)."""
    _record(__name__, __file__)
    for name, module in list(sys.modules.items()):
        try:
            path = getattr(module, "__file__", None)
        except Exception:                                # a lazy module object can raise on any attribute
            continue
        if name not in _LOADED and _in_src(path):
            _record(name, path)
    if not any(getattr(f, "tp_recorder", False) for f in sys.meta_path):
        sys.meta_path.insert(0, _Recorder)


_note_imported()


def _at(seconds: float) -> str:
    return dt.datetime.fromtimestamp(seconds).strftime("%d %b %H:%M")


def _changed() -> list[str]:
    """The files of src/ this process imported that differ on disk now, one line each; none: an empty list."""
    out = []
    for name, (path, mtime_ns, size, digest, when) in list(_LOADED.items()):
        if name not in sys.modules:
            continue
        shown = os.path.relpath(path, _REPO).replace(os.sep, "/")
        try:
            st = os.stat(path)
        except OSError:
            out.append(f"  {shown}: loaded {_at(when)}, since removed")
            continue
        if (st.st_mtime_ns, st.st_size) == (mtime_ns, size):
            continue
        try:
            with open(path, "rb") as f:
                same = hashlib.sha1(f.read()).hexdigest() == digest
        except OSError:
            same = False
        if same:                                         # rewritten with the same text (a checkout, a save): current
            _LOADED[name] = (path, st.st_mtime_ns, st.st_size, digest, when)
        else:
            out.append(f"  {shown}: loaded {_at(when)}, changed {_at(st.st_mtime)}")
    return sorted(out)


def _guarding() -> bool:
    """On in an IPython kernel or shell (the notebook's), which outlives code changes; a script imports, calls and exits.
    TP_CODE_GUARD=1 turns it on anywhere (the tests), 0 off."""
    flag = os.environ.get("TP_CODE_GUARD", "")
    if flag in ("0", "1"):
        return flag == "1"
    ipython = sys.modules.get("IPython")
    return bool(ipython is not None and getattr(ipython, "get_ipython", lambda: None)())


def _refuse_if_changed(call: str) -> None:
    lines = _changed() if _guarding() else []
    if lines:
        raise StaleKernel(
            f"STOP: {call} was not run. This notebook's kernel is running older code than the files on disk. Changed "
            "since the kernel loaded them:\n" + "\n".join(lines) + "\n"
            "Old code reading new files can fail (23 Oct 2026: A4 stopped with \"cannot read its default INSTANCE_ID\") "
            "or apply a replaced rule without saying so. Restart the kernel (Restart, in the notebook's toolbar), run "
            "SETUP, then the cells you need again. A matchups file or bet sheet this kernel made after the first change "
            "above came from the old code: make it again.")


def _guarded(name: str, fn):
    @functools.wraps(fn)
    def call(*args, **kwargs):
        _refuse_if_changed(f"tp.{name}()")
        return fn(*args, **kwargs)
    return call


def __getattr__(name: str):
    if name in _MODULES:
        return importlib.import_module(f"{__name__}.{name}")
    if name in _NAMES:
        _refuse_if_changed(f"tp.{name}")                 # before the import: a new module importing an old one can fail
        module, attr = _NAMES[name]
        value = getattr(importlib.import_module(f"{__name__}.{module}"), attr)
        value = _guarded(name, value) if callable(value) else value
        globals()[name] = value
        return value
    hint = ""
    if not name.startswith("__") and _guarding() and _changed():
        hint = " (this kernel's code is older than the files on disk: restart the kernel and run SETUP)"
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}{hint}")


def __dir__():
    return sorted(set(globals()) | set(_NAMES))
