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
    grade(run)                         each prediction of one run against its result, once a Stage 0 holds it
    grade_due()                        A7: every live run whose results came in since its last grade, graded again
    cleanup_work_tree()                removes a work tree an interrupted run left, links first (never delete it by hand:
                                       it holds junctions to the repository's data/raw and data/dump)

The model switch: "tabpfn35" is the current best model (local TabPFN-3.5, seeds 0-15, stage 2 with its walk-forward
calibration slope). "tabpfn35_thinking" is that same run plus TabPFN-3.5-Thinking beside it (the owner, 20 Oct 2026:
docs/decisions/2026-10-20-thinking-beside-local.md): the daily pipeline's `run_day --thinking --spend-tokens` sends the
same live rows to the instance's paid season fit and uses the API's probabilities uncalibrated; the prediction used is
the two models' chances averaged 50/50 in log-odds. Only with spend_tokens=True: each run makes one paid call, and the first Thinking
run of an instance and season also makes that season's paid fit (thinking.fit_season) before the run starts.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from src.eda.tabpfn_local.processes import is_jupyter_interrupt_helper

from . import config as CFG
from .runner import Step, run_step

DP = CFG.DAILY / "dp.py"
LOCK = CFG.OUT / "predict.lock"
# The notebook's own work tree (DP_WORK_TREE), so its runs never share a folder with the daily_prediction session's
# runs (tnr_daily) or tests (tnr_daily_pytest): a run's cleanup deletes the tree at its path (reviews D1, D2).
WORK_TREE = Path("C:/Users/zerom/tnr_daily_nb")
THINKING_WAITS = ("this daily pipeline's run_day has no --thinking option (added 20 Oct 2026 in "
                  "src/eda/daily_prediction/dp.py): TabPFN-3.5-Thinking cannot run beside the local model")


def _run_day_help() -> str:
    out = subprocess.run([str(CFG.interpreter("tennis")), str(DP), "run_day", "--help"], cwd=CFG.ROOT,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout


def dp_takes_thinking() -> bool:
    """Whether dp.py's run_day has the exact options `--thinking` and `--spend-tokens` (not merely flags starting so)."""
    text = _run_day_help()
    return all(re.search(rf"(?m)^\s+{flag}(\s|$)", text) for flag in ("--thinking", "--spend-tokens"))


def gpu_users() -> list[str]:
    """Local TabPFN processes the fit waits for (up to 6 hours), excluding VS Code's interrupt helper."""
    import psutil
    local = str(CFG.interpreter("local")).lower()
    out = []
    for proc in psutil.process_iter(["pid", "exe", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if ((proc.info.get("exe") or "").lower() == local
                    and not is_jupyter_interrupt_helper(subprocess.list2cmdline(cmdline))):
                out.append(f"pid {proc.info['pid']}: {' '.join(cmdline[1:4])}")
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


def predict_day(matchups: str | Path | None, *, model: str = CFG.LOCAL, spend_tokens: bool = False,
                run_name: str | None = None, checkpoint: str = "auto", leave_checkpoint: str = "auto",
                skip_checks: bool = False, dry_run: bool = False) -> Path | None:
    """One live prediction run for the matches of a matchups CSV (live.build_matchups or live.manual_matchups).

    Before the run: the template check (the active instance is the decided recipe, fitted for the season, its build
    tree holding its layer), the matchups check (a match it flags is left out, below), no other run going. Then dp.py
    run_day --refresh, seeds 0-15, with that instance and tree. After it: the instance the run used must be the one
    checked. leave_checkpoint: "auto" (the daily pipeline's default: after recomputed state parts it saves a
    checkpoint on today's tables before the fit, about 11 minutes, so the next day resumes) or "no" (bet first; the next
    run recomputes those parts again).
    model="tabpfn35_thinking": the same run plus TabPFN-3.5-Thinking beside the local model (run_day --thinking), the
    prediction used being their 50/50 average in log-odds. It needs spend_tokens=True: one paid call per run (about 6k tokens a
    match on 13 Oct), and, the first time for an instance and season, its paid season fit (about 180k tokens and 8
    minutes on 13 Oct), made here after the free checks and before the run. If the Thinking call fails, the run still
    gives the local model's predictions, and this says so. Returns the run folder (None in a dry run, and with no
    matchups: A3 found nothing to predict); bet_diagnostics(run) gives the bet sheet.
    One match never holds up the others (since 28 Oct 2026, the owner: "a single row shouldnt hold up the whole
    pipeline"; docs/decisions/2026-10-28-one-bad-match-left-out.md): a match the matchups check flags is left out of the
    run (the run predicts a checked copy of the CSV, in its folder), and so is one the daily engine cannot place; each is
    said with "!!!" at the end of this cell's output (left_out.lines), and the bet sheet lists them."""
    if matchups is None:
        print("Nothing to predict (A3 wrote no matchups): no run.")
        return None
    CFG.check_model(model)
    extra: list[str] = []
    thinking = model == CFG.THINKING_MODEL
    if thinking:
        if not dp_takes_thinking():
            raise NotImplementedError(THINKING_WAITS)
        if not spend_tokens:
            raise RuntimeError("TabPFN-3.5-Thinking's prediction is a paid API call: pass spend_tokens=True "
                               "(owner approval required)")
        extra = ["--thinking", "--spend-tokens"]
    matchups = Path(matchups)
    from . import left_out as LO
    from .live import check_matchups
    from .train import active_instance, base_tree, dp_env, show_model_age, template_check
    instance = active_instance()
    show_model_age(instance)                       # the owner's timer (20 Oct 2026): how old the training rows are
    env = {**dp_env(), "DP_WORK_TREE": str(WORK_TREE)}
    days = pd.to_datetime(pd.read_csv(matchups)["day"], errors="coerce").dropna()   # an unreadable day: its row's
    years = sorted({int(d.year) for d in days}) or [dt.date.today().year]          # problem (check_matchups)
    season = years[-1]
    flagged = None
    if not skip_checks:
        tc = template_check(instance, season=season, tree=base_tree())
        if not tc["ok"]:
            raise RuntimeError("the template check failed (above): the daily pipeline would not predict with the current "
                               "best model's recipe. Fix it, or pass skip_checks=True knowingly.")
        checked = check_matchups(matchups)
        flagged = checked[~checked["ok"]]
        if len(flagged) == len(checked):
            print(f"!!! Every match of {CFG.rel(matchups)} has a problem in its row (above): nothing to predict, no run.")
            return None
    run = _new_run(run_name)
    if WORK_TREE.exists() and not dry_run:
        raise RuntimeError(f"{WORK_TREE} exists: a notebook run is going, or one stopped and left its tree. If none is "
                           "going, run cleanup_work_tree() (never delete it by hand: it holds junctions to data/).")
    if thinking:
        _thinking_fits(instance, years, dry_run=dry_run)
    busy = gpu_users()
    if busy and not dry_run:
        print("NOTE: the fit will wait for the GPU until these local-TabPFN processes end:", *busy, sep="\n  ")

    def step_for(csv: Path) -> Step:
        args = [str(DP), "run_day", "--run", str(run), "--matchups", str(csv), "--refresh", "--seeds", "0-15",
                "--checkpoint", checkpoint, "--leave-checkpoint", leave_checkpoint, *extra]
        return Step("predict_day", args, note=f"model {model}; instance {instance.name}", extra_env=env)
    if dry_run:
        run_step(step_for(matchups), dry_run=True)
        return None
    with _Lock(f"predict_day {run.name}"):
        try:
            # the rows the check flagged left out: the run predicts a checked copy, in its own folder (made here)
            csv = _checked_copy(matchups, run, flagged) if flagged is not None and len(flagged) else matchups
            run_step(step_for(csv))
        except BaseException:
            if WORK_TREE.exists():
                print("the run stopped: removing its work tree with the daily pipeline's own cleanup")
                cleanup_work_tree()
            raise
        finally:
            if run.exists():
                shutil.copy2(matchups, run / "matchups_input.csv")       # the CSV as given (the bet sheet reads it)
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
        gate = d["gate"].astype(str)
        may = gate.str.startswith("may be bet")
        ok, bar = int(may.sum()), int((may & gate.ne("may be bet")).sum())
        print(f"{len(d)} matches predicted with {instance.name}; the gate allows {ok}"
              + (f", {bar} of them only with an edge above 1 point (a missing box score)" if bar else "")
              + f" (see bet_diagnostics). Run: {CFG.rel(run)}")
        if thinking:
            print(thinking_outcome(run))
        for line in continuity_lines(run):
            print(line)
        for line in LO.lines(run, predicted=len(d)):    # last, where the eye lands: each match left out, and why
            print(line)
    return run


def _checked_copy(csv: Path, run: Path, flagged: pd.DataFrame) -> Path:
    """The matchups CSV without the rows the check flagged (live.check_matchups), in the run's folder (made here), its
    other rows as written (the csv module: every value's text kept), with the CSV's sidecar of earlier qualifying rounds
    whole (history), and the rows recorded as left out by A4's check (left_out.json, the step "check"). Returns it."""
    import csv as csvmod

    from src.eda.prediction_run import earlier_rounds as ER

    from . import left_out as LO
    gone = {int(x) for x in flagged["row"]}
    with open(csv, newline="", encoding="utf-8") as fh:
        lines = [r for r in csvmod.reader(fh) if r]            # pandas skips blank lines too: its rows' numbering
    head, body = lines[0], lines[1:]
    run.mkdir(parents=True)
    out = run / "matchups_checked.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        csvmod.writer(fh).writerows([head] + [r for i, r in enumerate(body) if i not in gone])
    side = ER.sidecar(csv)
    if side.exists():
        shutil.copy2(side, ER.sidecar(out))
    df = pd.read_csv(csv)
    recs = []
    for _, b in flagged.iterrows():
        r = df.loc[int(b["row"])]
        name = r.get("tourney_name")
        recs.append({"csv_row": None, "row_given": int(b["row"]), "tour": r["tour"], "tourney_id": str(r["tourney_id"]),
                     "tourney_name": name if isinstance(name, str) and name else None, "round": str(r["round"]),
                     "player_a": r["player_a"], "player_b": r["player_b"], "day": str(r["day"]),
                     "reason": b["problem"], **({"switched_off": True} if b.get("switched_off") else {})})
    LO.write_check(run, recs)
    return out


def continuity_lines(run: Path) -> list[str]:
    """The run's continuity check (28 Oct 2026; daily_prediction/dp_continuity.py): finished matches earlier runs had
    and this run's data lacks, and Tennis My Life's lagging held files and carried events as of the run. Never a
    block."""
    p = Path(run) / "continuity.json"
    if not p.exists():
        return []
    c = json.loads(p.read_text(encoding="utf-8"))
    return [c.get("line") or "", *[x for x in (c.get("tml") or {}).get("lines") or []
                                   if x.startswith(("LAGGING", "CARRIED", "Tennis My Life status unknown"))]]


def thinking_outcome(run: Path) -> str:
    """One line on a Thinking run: both models and their ensemble, or Thinking's failure and why."""
    d = pd.read_csv(run / "predictions.csv")
    th = json.loads((run / "provenance.json").read_text(encoding="utf-8")).get("thinking") or {}
    if "ensemble" in d.columns and (d["ensemble"].astype(str) == "on").all():
        tokens = sum(int(s.get("tokens_used_daily_counter") or 0) for s in (th.get("seasons") or {}).values())
        return (f"TabPFN-3.5-Thinking predicted the same {len(d)} matches ({tokens:,} tokens on the account's daily "
                "counter); the prediction used is the two models' chances averaged 50/50 in log-odds (bet sheet: A5).")
    return (f"WARNING: TabPFN-3.5-Thinking FAILED ({th.get('failed') or 'no Thinking forecast in the run'}). This run's "
            "predictions are the local model's ALONE: the bet sheet decides on it and says so. A new run tries again; "
            f"receipts: {CFG.rel(run / 'thinking')}")


def _thinking_fits(instance: Path, seasons: list[int], *, dry_run: bool) -> None:
    """The instance's paid Thinking fit of each season, made here when it has none (thinking.fit_season with
    spend_tokens=True: the training rows prepared, then the one fit). A fit prepared on another frame than the
    instance's present one is refused: its training rows may differ, and a slot once used is never reset."""
    from . import thinking as TH
    for y in seasons:
        state = TH.fit_state(instance, y)
        if state == "ok":
            continue
        if state == "other frame":
            raise RuntimeError(f"{CFG.rel(TH.folder(instance, y))}: the Thinking fit was made on another frame than "
                               f"{instance.name}'s present one. A rebuilt frame needs its own instance folder.")
        if state == "other rows":
            raise RuntimeError(f"{CFG.rel(TH.folder(instance, y))}: the Thinking fit was made on other training rows "
                               f"than {instance.name}'s present retrain cut-off (training_cutoff.json written or changed "
                               "after the fit). A retrain is a new instance, with its own fit.")
        print(f"PAID: {instance.name} has no TabPFN-3.5-Thinking fit for {y}. Making it now, once for this instance and "
              "season (about 180k tokens and 8 minutes on 13 Oct), before the run.")
        TH.fit_season(instance, y, spend_tokens=True, dry_run=dry_run)
        if not dry_run and TH.fit_state(instance, y) != "ok":
            raise RuntimeError(f"the Thinking fit of {instance.name} for {y} did not complete: see "
                               f"{CFG.rel(TH.folder(instance, y))}. Nothing was predicted.")


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


def grade(run: str | Path | None = None, *, stage0: str | Path | None = None, dry_run: bool = False):
    """Each prediction of a run against its result (log loss of the model and of the price), once a Stage 0 holds the
    results: the repository's (after a Stage 0 rebuild: data.rebuild_shared_tables), or the file `stage0` (grade_due
    passes the freshest on disk). Its numbers decide nothing."""
    run = Path(run) if run else latest_run()
    from .train import dp_env
    args = [str(DP), "grade", "--run", str(run)] + (["--stage0", str(stage0)] if stage0 else [])
    return run_step(Step("grade", args, extra_env=dp_env()), dry_run=dry_run)


def _grade_json(run: Path) -> dict:
    try:
        return json.loads((run / "grade.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _bet_tours_grade(run: Path) -> dict:
    """A run's last grade read on the bet day's tours only (its graded.csv, config.BET_TOURS): the matches graded and
    their mean log losses, the keys grade.json gives for every tour; {} before its first grade."""
    try:
        g = pd.read_csv(run / "graded.csv")
    except (OSError, ValueError):
        return {}
    g = g[~CFG.off_mask(g)]
    done = g["ll_model"].notna() if "ll_model" in g.columns else pd.Series(False, index=g.index)
    out = {"graded": int(done.sum())}
    if done.any():
        out.update(mean_ll_model=float(g.loc[done, "ll_model"].mean()),
                   mean_ll_market=float(g.loc[done, "ll_market"].mean()))
    return out


def _run_time(name: str) -> str:
    """A run folder's time (live_2026-10-25_092143 -> Sun 25 Oct 09:21), else its name."""
    try:
        return f"{dt.datetime.strptime(name.split('_', 1)[1], '%Y-%m-%d_%H%M%S'):%a %d %b %H:%M}"
    except (IndexError, ValueError):
        return name


def _grade_run(run: Path, done: set, path: Path, dry_run: bool) -> dict | None:
    """One run's row of grade_due (None: a switched-off tour's run alone, not listed), graded when it is due."""
    pred = pd.read_csv(run / "predictions.csv", usecols=lambda c: c in ("match_id", "tour"))
    off = CFG.off_mask(pred)
    if len(pred) and off.all():                   # a switched-off tour's run alone: not listed
        return None
    ids = pred.loc[~off, "match_id"].astype(str)
    last = _bet_tours_grade if off.any() else _grade_json
    before = int(last(run).get("graded") or 0)
    n = sum(i in done for i in ids)               # a set lookup each (Series.isin on 870k ids: ~4 s a run)
    state = "graded now" if n > before else "up to date" if before else "waiting for results"
    if state == "graded now":
        if dry_run:
            grade(run, stage0=path, dry_run=True)
        else:
            with contextlib.redirect_stdout(io.StringIO()):     # the engine's output stays in the step's log
                grade(run, stage0=path)
    g = last(run) if state != "waiting for results" else {}
    return {"run": run.name, "predicted": len(ids), "results": n, "graded_before": before, "state": state,
            "mean_ll_model": g.get("mean_ll_model"), "mean_ll_market": g.get("mean_ll_market"),
            "switched_off": int(off.sum())}


def _results_source(path: Path, runs: Path) -> str:
    """Which Stage 0 the results came from, in plain words."""
    when = f"{dt.datetime.fromtimestamp(path.stat().st_mtime):%a %d %b %H:%M}"
    if runs in path.parents:                       # <runs>/<run>/stage0/stage0_matches.parquet
        return f"results as the prediction run of {_run_time(path.parents[1].name)} downloaded them"
    if CFG.OUT in path.parents:
        return f"results as the data check (A3b) read them at {when}"
    if path.parent == CFG.STAGE0:
        return f"results from the shared tables, rebuilt {when} (B6)"
    return f"results from {CFG.rel(path)} ({when})"


def grade_due(*, stage0: str | Path | None = None, runs: str | Path | None = None,
              dry_run: bool = False) -> pd.DataFrame:
    """A7: every live run graded again (grade) once the freshest Stage 0 on disk holds results for more of its
    predictions than its last grade counted. So a run is graded when its matches are played, again as more results
    arrive, and never before: the run A4 just made waits. With nothing new it reads one file and returns.

    The owner asked to run the bet-day cells in order "with the aproximate same net effect of I did A7 more
    selectively" (27 Oct 2026). This rule, and the freshest Stage 0 (A8's closing_line.stage0_path: the repository's,
    the data check's or the newest live run's own, so grading never waits for B6), are an agent's choice. A result
    counts as the engine's grade counts it: by match id, completed or retired. The engine's output goes to each step's
    log; this prints one line per run graded. Returns one row per live run with predictions, its state "graded now",
    "up to date" or "waiting for results", and its grade's mean log losses. Its numbers decide nothing.

    A tour switched off for the bet day (config.BET_TOURS; the owner, 28 Oct 2026: the women's): a run made before the
    switch is graded in full as before (its files are the record), but its state and figures here are its other
    matches' (switched_off: how many it leaves out), and a run of that tour alone is not listed.
    An error with one run is said with "!!!" and its state is "ERROR"; the other runs are graded (28 Oct 2026: one row
    never holds up the rest, docs/decisions/2026-10-28-one-bad-match-left-out.md)."""
    from .closing_line import DONE, stage0_path
    runs = Path(runs) if runs else CFG.DAILY_RUNS
    path = Path(stage0) if stage0 else stage0_path(runs)
    cols = ["run", "predicted", "results", "graded_before", "state", "mean_ll_model", "mean_ll_market", "switched_off"]
    if path is None:
        print("Nothing to grade yet: no Stage 0 on disk holds results.")
        return pd.DataFrame(columns=cols)
    s0 = pd.read_parquet(path, columns=["match_id", "status"])
    done = set(s0.loc[s0["status"].isin(DONE), "match_id"].astype(str))
    rows, errors = [], []
    for run in sorted(p for p in runs.glob("live_*") if (p / "predictions.csv").exists()):
        try:
            row = _grade_run(run, done, path, dry_run)
        except Exception as exc:  # noqa: BLE001 - one run's error is said; the other runs are graded (28 Oct 2026)
            errors.append(f"{run.name}: {type(exc).__name__}: {str(exc).splitlines()[0] if str(exc) else ''}")
            row = {"run": run.name, "state": "ERROR"}
        if row is not None:
            rows.append(row)
    out = pd.DataFrame(rows, columns=cols)
    if errors:
        print(f"!!! ERROR grading {len(errors)} run{'s' * (len(errors) != 1)} (the others below are graded as usual; "
              "each error's run keeps its earlier grade):")
        for e in errors:
            print(f"!!!   {e}")
    now = out[out["state"].eq("graded now")]
    n_runs = out["state"].value_counts()
    rest = (f"{n_runs.get('up to date', 0)} up to date, {n_runs.get('waiting for results', 0)} waiting for their "
            "matches' results")
    source = _results_source(path, runs)
    if now.empty:
        print(f"Nothing new to grade ({source}): {rest}.")
        return out
    print(f"{len(now)} run(s) graded now, {int((now['results'] - now['graded_before']).sum())} new result(s) "
          f"({source}); {rest}.")
    if not dry_run:
        show = pd.DataFrame({
            "Run": now["run"].map(_run_time),
            "Matches": now["predicted"], "With results": now["results"],
            "Log loss: model": now["mean_ll_model"].map(lambda x: f"{x:.3f}" if pd.notna(x) else ""),
            "Pinnacle": now["mean_ll_market"].map(lambda x: f"{x:.3f}" if pd.notna(x) else "")})
        print(show.to_string(index=False))
        print("Log loss: lower is better; Pinnacle's price with its margin removed. Each run's grade is in its folder "
              "(graded.csv, grade.json). A few matches decide nothing: A8 reads every sheet together.")
        if now["switched_off"].sum():
            print(f"Left out of these figures: {int(now['switched_off'].sum())} {CFG.off_names()} predictions of these "
                  f"runs ({CFG.off_names()} matches are switched off; config.BET_TOURS). Their runs' files grade them.")
    return out
