"""Paths and helpers shared by the prediction run (docs/decisions/2026-10-08-prediction-run-box-scores.md).

Every builder of the model's chain writes into its own study's folder and resolves its paths from its own location, so
the run builds in a sandbox: a copy of src/, docs/ and data/studies/ with links to the read-only data/dump/ and data/raw/,
the way src/eda/model_rebuild/run_chain.py builds the template. Its own sandbox (SANDBOX), so that a template build and
a prediction run never share one. A file at its root (MARKER) is the only licence Stage 0 accepts for live rows.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SANDBOX = Path(os.environ.get("PREDICTION_RUN_SANDBOX", "C:/Users/zerom/tnr_live"))
MARKER = ".prediction_run_sandbox"                 # stage0_build.SANDBOX_MARKER's name
PY = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
OUT = ROOT / "data" / "studies" / "prediction_run"
STUDIES = Path("data") / "studies"
PD = STUDIES / "predictability_diagnostic"         # relative: resolved against ROOT or SANDBOX
MT = STUDIES / "match_timing"
FRAME = STUDIES / "surface_rating_race" / "model" / "model_frame.parquet"
INPUTS = STUDIES / "surface_rating_race" / "model" / "model_inputs.json"
THINKING_FRAME = STUDIES / "tabpfn_thinking" / "frame.parquet"   # holds each row's indoor source (indoor_fill/status.py)
WINDOW_DAYS = 14                                   # the two-week profile's span: the gate's and the fills' horizon
LOOKBACK_DAYS = 28                                 # how far back a fill looks: events that began up to 4 weeks ago
FILL_START = dt.date(2026, 10, 8)                  # fills only for matches the frozen reference does not hold
EPOCH = dt.date(1970, 1, 1)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    os.replace(part, path)


def day_of(value) -> int:
    """A date (anything pandas reads) as days since 1970-01-01, the timeline's unit."""
    import pandas as pd

    return int((pd.Timestamp(value).normalize() - pd.Timestamp(EPOCH)).days)


def stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%MZ")


def reason_of(exc: BaseException) -> str:
    """Why one row failed, in one line: a refusal's own text (SystemExit), else the error's type and message (a match
    left out for it: docs/decisions/2026-10-28-one-bad-match-left-out.md)."""
    if isinstance(exc, SystemExit):
        return str(exc) or "stopped without a reason"
    return f"{type(exc).__name__}: {exc}"
