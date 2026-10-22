"""Paths, interpreters and defaults of the master pipeline (scripts/master_pipeline.ipynb).

The pipeline is an operator layer: it runs the project's own command-line steps in the right order and the right
environment, and reads their outputs. It holds no model logic. Three conda environments are involved:

    tennis        the notebook's kernel and every builder, scraper and reader (./python.sh)
    local         tennis-tabpfn-local: the local TabPFN-3.5 fits on the GPU (./python_tabpfn_local.sh)
    api           tennis-tabpfn: the hosted TabPFN API, TabPFN-3.5-Thinking (./python_tabpfn.sh)

Each interpreter's path is read from its shim, so the shims stay the one place it is written. An environment
variable overrides it (the daily pipeline's names where it has one). A missing interpreter fails loudly when a step
needs it; there is no fallback to another environment.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- environments -----------------------------------------------------------------------------------------------
_SHIMS = {"tennis": ("python.sh", "TENNIS_PYTHON"),
          "local": ("python_tabpfn_local.sh", "TENNIS_TABPFN_PYTHON"),
          "api": ("python_tabpfn.sh", "TENNIS_TABPFN_API_PYTHON")}


def interpreter(env: str) -> Path:
    """The python.exe of an environment: the override variable if set, else the path its shim names."""
    if env not in _SHIMS:
        raise ValueError(f"unknown environment {env!r}; one of {sorted(_SHIMS)}")
    shim, var = _SHIMS[env]
    if os.environ.get(var):
        return Path(os.environ[var])
    text = (ROOT / shim).read_text(encoding="utf-8")
    hit = re.search(r'^PY="([^"]+)"', text, flags=re.M)
    if not hit:
        raise RuntimeError(f"{shim} names no interpreter (a line PY=\"...\")")
    return Path(hit.group(1))


# --- where this layer writes --------------------------------------------------------------------------------------
OUT = ROOT / "data" / "studies" / "master_pipeline"
LOGS = OUT / "logs"                     # one log per step: logs/<YYYY-MM-DD>/<HHMMSS>_<step>.log
RECEIPTS = OUT / "runs.jsonl"           # one line per step run (or dry run)
MATCHUPS = OUT / "matchups"             # the matchups CSVs written for prediction runs
THINKING = OUT / "thinking"             # TabPFN-3.5-Thinking fits' records, one folder per instance and season
PREDICTIONS = ROOT / "predictions"      # <day>/bet_sheet_*.xlsx on top; <day>/records/: the sheets' records and the
                                        # daily pipeline's archive of each live run

# --- what other studies own (read, or run through their own command lines) -----------------------------------------
DAILY = ROOT / "src" / "eda" / "daily_prediction"
DAILY_OUT = ROOT / "data" / "studies" / "daily_prediction"
DAILY_RUNS = DAILY_OUT / "runs"
DAILY_STATE = DAILY_OUT / "state"        # the daily pipeline's default (DP_* variables are never passed on: runner.py)
STAGE2 = DAILY_OUT / "stage2"
INSTANCES = ROOT / "data" / "studies" / "current_best_model"
RETRAIN_DUE_DAYS = 30                # the timer's "retrain due" (train.model_age): Claude's default of 20 Oct 2026, a
                                     # setting; the owner calls each retrain and has not chosen a threshold
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
SCHEDULED = ROOT / "data" / "raw" / "_scheduled"
TML_RAW = ROOT / "data" / "raw" / "public_dump" / "tennis_my_life"
SPEED_LIVE = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "live"
ODDS_DUMP = ROOT / "data" / "dump" / "odds"
PINNACLE_RAW = ROOT / "data" / "raw" / "pinnacle"
PINNACLE_DUMP = ODDS_DUMP / "pinnacle"
ALIASES = ROOT / "config" / "player_aliases.csv"

SELECTED_INSTANCE = OUT / "selected_instance.json"   # the instance chosen with use_instance() (else the daily pipeline's default)

# --- the two settings of the switch (the owner's requests of 11 and 20 Oct 2026) --------------------------------------
LOCAL = "tabpfn35"                  # the current best model alone: local TabPFN-3.5, seeds 0-15, stage 2 calibrated
THINKING_MODEL = "tabpfn35_thinking"   # that model AND TabPFN-3.5-Thinking beside it (hosted, paid, the same 57 inputs
                                       # and training rows, uncalibrated); their 50/50 log-odds average decides. Season fits
                                       # (fit_seasons) with this setting are Thinking's alone
MODELS = (LOCAL, THINKING_MODEL)


def check_model(model: str) -> str:
    if model not in MODELS:
        raise ValueError(f"model must be one of {MODELS}, not {model!r}")
    return model


def rel(path: Path | str) -> str:
    """A path relative to the repository when it is inside it (for printing and receipts)."""
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)
