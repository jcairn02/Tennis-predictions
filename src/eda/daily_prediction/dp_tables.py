"""Step 4, tables: today's tables in the run's work tree, with the live rows.

prediction_run/run.py's preparation (its own step list, run.stage0_steps, run unchanged: Stage 0 with the live rows and
the decided box-score overrides and fills, the accepted lower-level packages, the live rows' check, the level layer
resolved on this Stage 0, Stage 1's odds with the live prices, the links and the timeline with the live days and
windows), without the steps that reach no input (the daily_update_speed scoping, re-checked there for the IOS source):
    stage0_checks     reports only
    timing_check      reports only
    timing_features   match_timing/rebuild.py: its columns are replaced by the surface IOS; only checks read them
A replay holds the timeline at the instance's (its build tree's timing.parquet), as the 10 Oct layer replay did
(sources were restaged after the freeze; the played matches keep their days: "training" dating), so the steps that only
build the timeline (links, remap, timing, the live and the packages' windows) are skipped there.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC
import dp_worktree as WT

SKIP = ("stage0_checks", "timing_check", "timing_features")
SKIP_REPLAY = ("remap", "links", "live_links", "timing", "live_window", "additions_window")


def steps(has_overrides: bool, hold: bool) -> list[tuple[str, str, list[str]]]:
    from src.eda.prediction_run import run as RUN            # the repository's (this process runs from it)
    skip = set(SKIP) | (set(SKIP_REPLAY) if hold else set())
    return [s for s in RUN.stage0_steps(has_overrides, layer=True) if s[0] not in skip]


def layer_env(box: Path) -> dict:
    from src.eda.current_best_model import layer_config as LCF
    p = LCF.build_config(box)
    LCF.require_resolved(p, box)
    return {"LLE_LAYER": str(p)}


def hold_timeline(box: Path, base_tree: Path) -> dict:
    """The work tree's timeline set to the instance's on every match of the work tree's Stage 0."""
    t = pd.read_parquet(Path(base_tree) / DC.MT / "timing.parquet")
    t["match_id"] = t["match_id"].astype(str)
    m = pd.read_parquet(box / DC.PD / "stage0_matches.parquet", columns=["match_id"])
    ids = set(m["match_id"].astype(str))
    missing = sorted(ids - set(t["match_id"]))
    if missing:
        raise SystemExit(f"hold: {len(missing)} of the work tree's matches are not in the instance's timeline "
                         f"(first: {missing[:3]})")
    held = t[t["match_id"].isin(ids)].reset_index(drop=True)
    path = box / DC.MT / "timing.parquet"
    part = path.with_name(path.name + ".part")
    held.to_parquet(part, index=False)
    os.replace(part, path)
    return {"rows": int(len(held)), "of_instance_rows": int(len(t)), "sha256": DC.sha256(path),
            "source": str(Path(base_tree) / DC.MT / "timing.parquet")}


def history_check(box: Path) -> dict:
    """current_best_model/history.py's check of the work tree's Stage 0 and timeline against the frozen reference (a
    report: nothing reads it to build an input)."""
    import time

    from src.eda.current_best_model import history as H
    t0 = time.time()
    res = H.check(box / DC.PD, box / DC.MT / "timing.parquet")
    return {"history": {k: v for k, v in res.items() if k != "feeds"}, "history_line": H.summary_line(res),
            "history_seconds": round(time.time() - t0, 1)}


def prep(run_dir: Path, box: Path, replay: bool, base_tree: Path = DC.BASE_TREE, hold: bool | None = None,
         history: bool = True) -> dict:
    """The preparation in the work tree; the live rows, meta and overrides come from the run's folder. hold (default:
    a replay): the instance's timeline instead of the timeline steps (the exact replay, "training" dating); a replay
    dated as live builds the timeline as a live run does (a smoke test of those steps, not an exactness test).
    history False: the history check is left to the caller (run_day runs it beside the states step)."""
    hold = replay if hold is None else hold
    if not (box / WT.MARKER).exists():
        raise SystemExit(f"no work tree at {box}: dp.py worktree")
    rdir = box / "run"
    if rdir.exists():
        raise SystemExit(f"{rdir} exists: this work tree has built a run already (dp.py cleanup, worktree)")
    (rdir / "stage0_before").mkdir(parents=True)
    for f in ("live_rows.parquet", "live_meta.parquet", "overrides.csv"):
        if (run_dir / f).exists():
            shutil.copy2(run_dir / f, rdir / f)
    for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
        shutil.copy2(box / DC.PD / f, rdir / "stage0_before" / f)
    record: dict = {"work_tree": str(box), "replay": replay, "timeline_held": hold, "steps": []}
    env: dict = {}
    for name, script, args in steps((rdir / "overrides.csv").exists(), hold):
        code = WT.run(box, name, script, args, env=env, record=record["steps"])
        if code != 0:
            record["failed"] = name
            return record
        if name == "lle_layer":
            env = layer_env(box)
            record["lle_layer"] = env["LLE_LAYER"]
    if hold:
        record["timeline_held"] = hold_timeline(box, base_tree)
    if history:
        record.update(history_check(box))
    else:
        record["history_line"] = "run beside the states step (history.json)"
    return record
