"""Section A: the day's predictions, through the daily pipeline's own command line (src/eda/daily_prediction/dp.py).

Agreed with the daily_prediction session (process log, 10:20), which owns that pipeline: the notebook calls dp.py as a
subprocess (its CLI is the stable contract; its Python functions are internal), always with --refresh (box scores
first: docs/decisions/2026-10-08-prediction-run-box-scores.md), always in a NEW run folder (a reused folder keeps stale
fits), with the decided seeds 0-15, in the notebook's own work tree, with the instance and build tree that the template
check approved handed over explicitly (train.dp_env).

    predict_day(matchups, model=...)   one live run: refresh, matchups, prices, work tree, tables, states, gate, fit,
                                       predict; about 7 minutes when the checkpoint and TabPFN caches are warm (the first
                                       run after a data revision recomputes more: 20-40 minutes)
    reprice(run)                       a newer price read off the run's stored curve (no refit; seconds)
    grade(run)                         each prediction against its result, once Stage 0 holds it
    cleanup_work_tree()                removes a work tree an interrupted run left, links first (never delete it by hand:
                                       it holds junctions to the repository's data/raw and data/dump)

The model switch: "tabpfn35" is the current best model (local TabPFN-3.5, seeds 0-15, stage 2 with its walk-forward
calibration slope). "tabpfn35_thinking" (TabPFN-3.5-Thinking, the same 57 inputs) runs through the daily pipeline's own
`--model thinking` once that session adds it, and only with spend_tokens=True (each day's prediction is a paid call).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from . import config as CFG
from .runner import Step, run_step

DP = CFG.DAILY / "dp.py"
LOCK = CFG.OUT / "predict.lock"
# The notebook's own work tree (DP_WORK_TREE), so its runs never share a folder with the daily_prediction session's
# runs (tnr_daily) or tests (tnr_daily_pytest): a run's cleanup deletes the tree at its path (reviews D1, D2).
WORK_TREE = Path("C:/Users/zerom/tnr_daily_nb")
THINKING_WAITS = (
    "TabPFN-3.5-Thinking predictions run through the daily pipeline's own `--model thinking`, which its session will "
    "add after three owner decisions: (1) paid spend (each day's prediction is a paid API call; ~30k tokens billed, "
    "estimated), (2) seed 0 only, (3) stage 2 for Thinking (the 8 Oct research rule q = eta_thinking + b_local * spd_L, "
    "or a calibrated slope from paid back-season fits). The paid season fit is ready on this side: "
    "fit_seasons(model='tabpfn35_thinking') quotes its cost for free; spend_tokens=True makes it, once.")


def _run_day_help() -> str:
    out = subprocess.run([str(CFG.interpreter("tennis")), str(DP), "run_day", "--help"], cwd=CFG.ROOT,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout


def dp_takes_thinking() -> bool:
    """Whether dp.py's run_day has the exact option `--model` offering `thinking` (not merely a flag starting so)."""
    text = _run_day_help()
    return bool(re.search(r"(?m)^\s+--model\s+\{[^}]*\bthinking\b[^}]*\}", text)) or \
        bool(re.search(r"--model \{[^}]*thinking", text))


def gpu_users() -> list[str]:
    """Other processes of the local TabPFN environment (the daily fit waits for them, up to 6 hours, silently)."""
    import psutil
    local = str(CFG.interpreter("local")).lower()
    out = []
    for proc in psutil.process_iter(["pid", "exe", "cmdline"]):
        try:
            if (proc.info.get("exe") or "").lower() == local:
                out.append(f"pid {proc.info['pid']}: {' '.join((proc.info.get('cmdline') or [])[1:4])}")
        except (psutil.Error, OSError):
            continue
    return out


class _Lock:
    """One prediction run at a time from this layer (its work tree is reused)."""

    def __init__(self, what: str):
        self.what = what

    def __enter__(self):
        CFG.OUT.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            held = LOCK.read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(f"another prediction run holds {CFG.rel(LOCK)}: {held}. If no run is going "
                               "(a crashed kernel), delete that file.") from None
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"{self.what} pid {os.getpid()} since {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
        return self

    def __exit__(self, *exc):
        LOCK.unlink(missing_ok=True)
        return False


def cleanup_work_tree(*, dry_run: bool = False):
    """Remove the notebook's work tree after an interrupted or failed run, with the daily pipeline's own cleanup (it
    removes the junctions to data/raw and data/dump first, never their targets). If it refuses (a tree whose setup was
    cut short before its marker was written), remove the tree's junctions with `rmdir` (the link only) before the rest;
    a tool that follows junctions would empty the repository's data."""
    if not WORK_TREE.exists():
        print(f"no work tree at {WORK_TREE}")
        return None
    return run_step(Step("dp_cleanup", [str(DP), "cleanup", "--work-tree", str(WORK_TREE)]), dry_run=dry_run,
                    check=False)


def _new_run(name: str | None, kind: str = "live") -> Path:
    run = CFG.DAILY_RUNS / (name or f"{kind}_{dt.datetime.now():%Y-%m-%d_%H%M%S}")
    if run.exists():
        raise RuntimeError(f"{CFG.rel(run)} exists: every prediction gets a new run folder (a reused one keeps stale fits)")
    return run


def predict_day(matchups: str | Path, *, model: str = CFG.LOCAL, spend_tokens: bool = False, run_name: str | None = None,
                checkpoint: str = "auto", leave_checkpoint: str = "auto", skip_checks: bool = False,
                dry_run: bool = False) -> Path | None:
    """One live prediction run for the matches of a matchups CSV (live.build_matchups or live.manual_matchups).

    Before the run: the template check (the active instance is the decided recipe, fitted for the season, its build
    tree holding its layer), the matchups check (nothing that would stop the run), no other run going. Then dp.py
    run_day --refresh, seeds 0-15, with that instance and tree. After it: the instance the run used must be the one
    checked. leave_checkpoint: "auto" (the daily pipeline's default: after recomputed state parts it saves a
    checkpoint on today's tables before the fit, about 11 minutes, so the next day resumes) or "no" (bet first; the next
    run recomputes those parts again). model="tabpfn35_thinking" needs spend_tokens=True. Returns the run folder (None
    in a dry run); bet_diagnostics(run) gives the bet-time file."""
    CFG.check_model(model)
    extra: list[str] = []
    if model == CFG.THINKING_MODEL:
        if not dp_takes_thinking():
            raise NotImplementedError(THINKING_WAITS)
        if not spend_tokens:
            raise RuntimeError("TabPFN-3.5-Thinking's daily prediction is a paid API call: pass spend_tokens=True "
                               "(owner approval required)")
        extra = ["--model", "thinking"]
    matchups = Path(matchups)
    from .live import check_matchups
    from .train import active_instance, base_tree, dp_env, template_check
    instance = active_instance()
    env = {**dp_env(), "DP_WORK_TREE": str(WORK_TREE)}
    season = int(pd.read_csv(matchups)["day"].map(lambda d: pd.Timestamp(d).year).max())
    if not skip_checks:
        tc = template_check(instance, season=season, tree=base_tree())
        if not tc["ok"]:
            raise RuntimeError("the template check failed (above): the daily pipeline would not predict with the current "
                               "best model's recipe. Fix it, or pass skip_checks=True knowingly.")
        check_matchups(matchups)
    run = _new_run(run_name)
    if WORK_TREE.exists() and not dry_run:
        raise RuntimeError(f"{WORK_TREE} exists: a notebook run is going, or one stopped and left its tree. If none is "
                           "going, run cleanup_work_tree() (never delete it by hand: it holds junctions to data/).")
    busy = gpu_users()
    if busy and not dry_run:
        print("NOTE: the fit will wait for the GPU until these local-TabPFN processes end:", *busy, sep="\n  ")
    args = [str(DP), "run_day", "--run", str(run), "--matchups", str(matchups), "--refresh", "--seeds", "0-15",
            "--checkpoint", checkpoint, "--leave-checkpoint", leave_checkpoint, *extra]
    step = Step("predict_day", args, note=f"model {model}; instance {instance.name}", extra_env=env)
    if dry_run:
        run_step(step, dry_run=True)
        return None
    with _Lock(f"predict_day {run.name}"):
        try:
            run_step(step)
        except BaseException:
            if WORK_TREE.exists():
                print("the run stopped: removing its work tree with the daily pipeline's own cleanup")
                cleanup_work_tree()
            raise
        finally:
            if run.exists():
                shutil.copy2(matchups, run / "matchups_input.csv")
                linking = matchups.with_name(matchups.stem + "_linking.csv")
                if linking.exists():
                    shutil.copy2(linking, run / "matchups_linking.csv")
                (run / "pipeline_model.json").write_text(json.dumps(
                    {"model": model, "instance": instance.name, "tree": env["DP_BASE_TREE"],
                     "matchups": CFG.rel(matchups), "made_at": dt.datetime.now().isoformat()}), encoding="utf-8")
    p = run / "predictions.csv"
    if p.exists():
        d = pd.read_csv(p)
        used = set(d["instance"].astype(str))
        if used != {instance.name}:
            raise RuntimeError(f"the run predicted with {used}, not the checked instance {instance.name}: do not bet on it")
        ok = int((d["gate"].astype(str) == "may be bet").sum())
        print(f"{len(d)} matches predicted with {instance.name}; the gate allows {ok} (see bet_diagnostics). "
              f"Run: {CFG.rel(run)}")
    return run


def latest_run(kind: str = "live") -> Path | None:
    """The newest run folder of a kind (live, replay), by the time in its name (a later reprice or grade written into an
    older run does not make it the newest)."""
    runs = sorted(p for p in CFG.DAILY_RUNS.glob(f"{kind}_*") if p.is_dir())
    return runs[-1] if runs else None


def reprice(run: str | Path | None = None, prices: str | Path | None = None, *, dry_run: bool = False) -> Path | None:
    """New prices for a run's matches, read off its stored curve (no refit). Without `prices`, Pinnacle is pulled now
    and each match's new margin-free price is oriented to side A (live.live_prices). Returns the reprice file
    (match_id, p_market_a, q_a, note), or None in a dry run; bet_diagnostics(run, reprice_file=...) uses it."""
    run = Path(run) if run else latest_run()
    if run is None:
        raise RuntimeError("no run to reprice")
    from .train import dp_env
    if dry_run:
        print(f"DRY RUN  reprice {CFG.rel(run)}: a Pinnacle pull, then dp.py reprice --run <run> --prices <file>")
        return None
    if prices is None:
        from .live import live_prices
        prices = live_prices(run)
    before = set(run.glob("reprice_*.csv"))
    run_step(Step("reprice", [str(DP), "reprice", "--run", str(run), "--prices", str(prices)], extra_env=dp_env()))
    new = sorted(set(run.glob("reprice_*.csv")) - before)
    new = [p for p in new if not p.stem.endswith("_prices")]
    if not new:
        raise RuntimeError("the daily pipeline's reprice wrote no file")
    shutil.copy2(prices, new[-1].with_name(new[-1].stem + "_prices.csv"))
    return new[-1]


def grade(run: str | Path | None = None, *, dry_run: bool = False):
    """Each prediction of a run against its result (log loss of the model and of the price), once Stage 0 holds the
    results (after a Stage 0 rebuild: data.rebuild_shared_tables). Its numbers decide nothing."""
    run = Path(run) if run else latest_run()
    from .train import dp_env
    return run_step(Step("grade", [str(DP), "grade", "--run", str(run)], extra_env=dp_env()), dry_run=dry_run)
