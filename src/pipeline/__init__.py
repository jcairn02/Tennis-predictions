"""The master pipeline: the functions scripts/master_pipeline.ipynb calls (docs/studies/master_pipeline/README.md).

    import src.pipeline as tp        # with the repository root on sys.path
    tp.status()

Names load lazily (PEP 562), so a worker in another environment (the hosted TabPFN's tennis-tabpfn) can import one
module of the package without the others' dependencies.
"""
from __future__ import annotations

import importlib

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
    "latest_run": ("predict", "latest_run"),
    "cleanup_work_tree": ("predict", "cleanup_work_tree"),
    "bet_diagnostics": ("diagnostics", "bet_diagnostics"),
    "receipts": ("runner", "receipts"),
}

__all__ = sorted(_NAMES)


_MODULES = {"config", "runner", "overview", "data", "train", "live", "predict", "diagnostics", "bet_sheet", "readiness",
            "thinking"}                 # no module may share a name with a function above (it would shadow it)


def __getattr__(name: str):
    if name in _MODULES:
        return importlib.import_module(f"{__name__}.{name}")
    if name in _NAMES:
        module, attr = _NAMES[name]
        value = getattr(importlib.import_module(f"{__name__}.{module}"), attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_NAMES))
