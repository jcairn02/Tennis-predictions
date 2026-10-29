"""Section C of the notebook: rebuilding and retraining the current best model.

"The current best model" is a recipe, built on the day's tables (docs/decisions/2026-10-08-current-best-model.md,
§ "Building it"). A built copy of it is an *instance*: a folder under data/studies/current_best_model/ holding the
model frame (57 inputs, Pinnacle-first odds), its input list, the build records and the season fits. These functions
run the decided steps in order, each through its own command line:

    build_instance     run_chain.py in a sandbox copy of the repository: --setup, --additions, lane 0, --prepare-layer,
                       lanes 1 and 2 side by side (about 2.5 h), lane 3, --collect
    finish_instance    the odds input "Pinnacle first" (odds_input.py --apply, which brings OddsTrader's tables up to
                       date itself) and the 57-input list (template_inputs.py --apply); every build path runs it
    fit_seasons        the season fits: local TabPFN-3.5 on the GPU (fits.py, seeds 0-15), or TabPFN-3.5-Thinking on the
                       hosted API (thinking.py: a free quote by default; a paid fit only with spend_tokens=True)
    make_checkpoint    the daily pipeline's saved state before a day (dp.py checkpoint)
    replay_check       the proof: a past day replayed through the daily pipeline reproduces the instance's inputs

Stage 2's coefficients need no step: the daily pipeline fits them for a season the first time it predicts it (from
the instance's own seeds 0-3, about 10 s) and keeps them in data/studies/daily_prediction/stage2/.

The training history is gated (CLAUDE.md, "The frozen reference"): --setup refuses a template build whose lower-level
history differs from the frozen reference's. A build that tests new lower-level data is a candidate (candidate=True,
its own folder), compared with compare_candidate() before anything is accepted; accepting it is the owner's call.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
from pathlib import Path

from . import config as CFG
from .runner import Step, StepResult, run_parallel, run_step, run_steps

CHAIN = "src/eda/model_rebuild/run_chain.py"
BUILD_STEPS = ("setup", "additions", "lane0", "prepare_layer", "lanes12", "lane3", "collect")


# --- which instance the daily pipeline uses ------------------------------------------------------------------------------
# One place names the live model: the notebook's selection (CFG.SELECTED_INSTANCE), written by use_instance() and by a
# retrain's switch. The daily pipeline reads the same file (dp_common.resolve_instance), and every daily-pipeline step is
# also handed it explicitly (dp_env), so the checks and the run can never look at different instances or trees (review
# V1, item 3). Neither has a default (22 Oct 2026; docs/studies/master_pipeline/process_log.md, Part 9): until then both
# fell back to the 10 Oct instance, two retrains old. The kernel's own DP_* variables are never read or passed on
# (runner.SCRUBBED_PREFIXES).
NO_SELECTION = ("No live model is selected: the notebook's selection ({path}) is missing or names no instance and tree. "
                "Choose one with use_instance(<instance>, tree=<its build tree>); list_instances() lists the instances. "
                "There is no default model (since 22 Oct 2026).")


def _dp_common() -> str:
    return (CFG.DAILY / "dp_common.py").read_text(encoding="utf-8")


def dp_reads_instance() -> bool:
    """Whether the daily pipeline takes its instance from DP_INSTANCE (since 11 Oct 2026)."""
    return "DP_INSTANCE" in _dp_common()


def _selection() -> dict:
    return json.loads(CFG.SELECTED_INSTANCE.read_text(encoding="utf-8")) if CFG.SELECTED_INSTANCE.exists() else {}


def selected_instance_name() -> str | None:
    """The live model's name, as the notebook's selection gives it; None with no selection (never a default)."""
    sel = _selection()
    return sel.get("instance") if sel.get("instance") and sel.get("tree") else None


def active_instance() -> Path:
    """The instance the daily pipeline predicts with: the one the notebook's selection names. Refuses with none."""
    name = selected_instance_name()
    if not name:
        raise RuntimeError(NO_SELECTION.format(path=CFG.rel(CFG.SELECTED_INSTANCE)))
    return CFG.INSTANCES / name


def base_tree() -> Path:
    """The selected instance's build tree, which the daily pipeline reads its tables from. Refuses with no selection."""
    if not selected_instance_name():
        raise RuntimeError(NO_SELECTION.format(path=CFG.rel(CFG.SELECTED_INSTANCE)))
    return Path(_selection()["tree"])


def dp_env() -> dict:
    """The variables every daily-pipeline step is given: the selected instance and its build tree."""
    if not dp_reads_instance():
        raise RuntimeError("the daily pipeline does not read DP_INSTANCE (dp_common.py): it cannot be told the instance")
    return {"DP_INSTANCE": active_instance().name, "DP_BASE_TREE": str(base_tree())}


def _instance(instance) -> Path:
    if instance is None:
        return active_instance()
    p = Path(instance)
    return p if p.is_absolute() else (CFG.INSTANCES / p if not str(p).startswith("data") else CFG.ROOT / p)


def instance_status(instance=None) -> dict:
    """What an instance holds: its inputs, the odds input, the fits per season (local seeds; Thinking fits), the
    stage-2 coefficients computed for it, and the daily pipeline's checkpoints and TabPFN caches for it."""
    inst = _instance(instance)
    out: dict = {"instance": CFG.rel(inst), "exists": inst.exists(), "active": inst.name == selected_instance_name()}
    if not inst.exists():
        return out
    mi = inst / "model_inputs.json"
    if mi.exists():
        j = json.loads(mi.read_text(encoding="utf-8"))
        out["inputs"] = len(j.get("inputs", []))
        out["template_dropped"] = j.get("template_dropped")
    out["odds_input"] = (inst / "odds_input.json").exists()
    seasons: dict[int, list[int]] = {}
    for f in (inst / "fits").glob("model__*__seed*.npz") if (inst / "fits").exists() else []:
        m = re.match(r"model__(\d{4})__seed(\d+)\.npz", f.name)
        if m:
            seasons.setdefault(int(m.group(1)), []).append(int(m.group(2)))
    out["local_fits"] = {y: _span(sorted(s)) for y, s in sorted(seasons.items())}
    th = CFG.THINKING / inst.name
    out["thinking_fits"] = sorted(p.parent.name for p in th.glob("season*/fit.json")) if th.exists() else []
    out["stage2"] = sorted(_stage2_label(p, inst) for p in CFG.STAGE2.glob(f"{inst.name}_*.json"))
    st = CFG.DAILY_STATE / inst.name
    out["checkpoints"] = sorted(p.name for p in st.iterdir() if p.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}$", p.name)) \
        if st.exists() else []
    caches = st / "tabpfn"
    out["tabpfn_caches"] = {p.name: len([q for q in p.iterdir() if q.is_dir()]) for p in sorted(caches.iterdir())
                            if p.is_dir()} if caches.exists() else {}
    return out


def _span(seeds: list[int]) -> str:
    if not seeds:
        return ""
    if seeds == list(range(seeds[0], seeds[-1] + 1)):
        return f"{seeds[0]}-{seeds[-1]}" if len(seeds) > 1 else str(seeds[0])
    return ",".join(map(str, seeds))


def list_instances() -> list[str]:
    """Instance folders (each holding a model frame)."""
    return sorted(p.parent.name for p in CFG.INSTANCES.glob("*/model_frame.parquet"))


# --- building ------------------------------------------------------------------------------------------------------------
def default_out(day: dt.date | None = None) -> Path:
    return CFG.INSTANCES / f"template_{(day or dt.date.today()).isoformat()}"


def sandboxes(*, sizes: bool = False) -> list[dict]:
    """The build and work trees under C:/Users/zerom (tnr_*): which one the daily pipeline reads (its base tree, the
    replays' frozen dump, its work tree), and optionally their sizes (slow: minutes for ~20 GB trees)."""
    import os
    special = {"c:/users/zerom/tnr_dump_freeze": "replays' frozen dump", "c:/users/zerom/tnr_daily": "daily work tree",
               "c:/users/zerom/tnr_daily_nb": "notebook's daily work tree"}
    if selected_instance_name():
        special[base_tree().as_posix().lower()] = "the active instance's build tree (the daily pipeline reads it)"
    out = []
    for p in sorted(Path("C:/Users/zerom").glob("tnr_*")):
        if not p.is_dir():
            continue
        rec = {"tree": str(p), "role": special.get(p.as_posix().lower(), ""),
               "modified": dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
        if sizes:
            total = 0
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
                total += sum(os.path.getsize(os.path.join(root, f)) for f in files
                             if not os.path.islink(os.path.join(root, f)))
            rec["gb"] = round(total / 1e9, 1)
        out.append(rec)
    return out


BUILD_DISK_GB = 90    # a sandbox copies data/studies (run_chain.setup) without the daily pipeline's TabPFN caches (55 GB
                      # an instance, 220 GB for four on 20 Oct 2026: RUN_CHAIN_SKIP_DIRS below), ~16 GB; the new
                      # instance's own caches add ~55 GB when it first predicts
SKIP_DIRS = "daily_prediction"   # left out of the sandbox's copy: no chain step reads the daily engine's caches (the
                                 # 16 Oct build's script did the same; before 20 Oct this cell copied them, which with four
                                 # instances' caches would have filled the disk)


def build_instance(out=None, *, sandbox=None, candidate: bool = False, start_at: str = "setup",
                   allow_low_disk: bool = False, dry_run: bool = False) -> list[StepResult]:
    """Build a new instance's model frame with the documented chain, in a sandbox copy of the repository.

    out       the instance folder (default data/studies/current_best_model/template_<today>)
    sandbox   the build tree (default C:/Users/zerom/tnr_build_<YYYYMMDD>); keep it after the build: the daily
              pipeline reads the instance's tables from its build tree (DP_BASE_TREE)
    candidate a build whose lower-level history may differ from the frozen reference (new Challenger/ITF/qualifying
              data); then compare_candidate(out) before anything is accepted
    start_at  resume after a failure: one of setup, additions, lane0, prepare_layer, lanes12, lane3, collect
              (run_chain's own --from resumes inside a lane)
    About 3 hours in all (lane 1 about 2.5 h, lane 2 beside it). No GPU."""
    out = Path(out) if out else default_out()
    sandbox = Path(sandbox) if sandbox else Path(f"C:/Users/zerom/tnr_build_{dt.date.today():%Y%m%d}")
    if start_at not in BUILD_STEPS:
        raise ValueError(f"start_at: one of {BUILD_STEPS}")
    import shutil
    free = shutil.disk_usage(sandbox.anchor or "C:/").free / 1e9
    if start_at == "setup" and free < BUILD_DISK_GB and not allow_low_disk and not dry_run:
        raise RuntimeError(
            f"{free:.0f} GB free; a build needs about {BUILD_DISK_GB} GB (its sandbox, ~16 GB without the daily "
            "pipeline's caches, and the new instance's own TabPFN caches, ~55 GB, at its first prediction). Free space "
            "(sandboxes() lists the tnr_* trees, ~16-20 GB each; older instances' caches are 55 GB each, the owner's "
            "call), then allow_low_disk=True if you must.")
    env = {"MODEL_REBUILD_SANDBOX": str(sandbox), "RUN_CHAIN_SKIP_DIRS": SKIP_DIRS}
    o = ["--out", str(out)]
    plan = {
        "setup": [Step("chain_setup", [CHAIN, "--setup"] + (["--candidate"] if candidate else []), extra_env=env)],
        "additions": [Step("chain_additions", [CHAIN, "--additions", *o], extra_env=env)],
        "lane0": [Step("chain_lane0", [CHAIN, "--lane", "0", *o], extra_env=env, note="about 25 minutes")],
        "prepare_layer": [Step("chain_prepare_layer", [CHAIN, "--prepare-layer", *o], extra_env=env)],
        "lanes12": [Step("chain_lane1", [CHAIN, "--lane", "1", "--layer", *o], extra_env=env, note="about 2.5 h"),
                    Step("chain_lane2", [CHAIN, "--lane", "2", "--layer", *o], extra_env=env)],
        "lane3": [Step("chain_lane3", [CHAIN, "--lane", "3", "--layer", *o], extra_env=env)],
        "collect": [Step("chain_collect", [CHAIN, "--collect", *o], extra_env=env)],
    }
    print(f"instance: {CFG.rel(out)}   sandbox: {sandbox}   candidate: {candidate}")
    results: list[StepResult] = []
    for name in BUILD_STEPS[BUILD_STEPS.index(start_at):]:
        steps = plan[name]
        if len(steps) > 1:
            results += run_parallel(steps, dry_run=dry_run)
        else:
            results += run_steps(steps, dry_run=dry_run)
    if not dry_run:
        print(f"Built. Next: finish_instance({str(out)!r}). Keep the sandbox {sandbox}: it is this instance's build tree.")
    return results


def finish_instance(out, *, stage1=None, dry_run: bool = False) -> list[StepResult]:
    """The decided odds input and input list on a built instance, the one list of these steps (21 Oct 2026: the
    scripted builds' post_build.sh runs this function; their own copy of the steps had lost the OddsTrader refresh):
        the chain's own frame and list kept (model_frame_chain.parquet, model_inputs_chain.json: the books'-average
        odds input, all 58 columns), then
        odds_input.py --apply (it brings OddsTrader's tables up to date for the frame itself, network, and refuses a
        frame they do not cover; then Pinnacle first: Pinnacle's close, BetOnline's, the average) and
        template_inputs.py --apply (57 inputs: ios_points_short dropped).
    `stage1`: a Stage 1 odds table other than the live one (a candidate's)."""
    out = Path(out)
    if not dry_run:
        for name, kept in (("model_frame.parquet", "model_frame_chain.parquet"),
                           ("model_inputs.json", "model_inputs_chain.json")):
            if not (out / kept).exists():
                shutil.copyfile(out / name, out / kept)
    odds = ["src/eda/current_best_model/odds_input.py", "--apply", str(out)] + (["--stage1", str(stage1)] if stage1 else [])
    steps = [Step("odds_input_apply", odds),
             Step("template_inputs_apply", ["src/eda/current_best_model/template_inputs.py", "--apply", str(out)])]
    return run_steps(steps, dry_run=dry_run)


def _sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def template_check(instance=None, *, season: int | None = None, tree=None, show: bool = True) -> dict:
    """Is this instance the current best model's recipe, ready to predict `season` (default: this year)? Checked
    before any prediction (review D2, item 2): 57 inputs with ios_points_short dropped; the Pinnacle-first odds input
    applied to THIS frame; the level layer built; seeds 0-15 fitted for the season; and the daily pipeline's build tree
    holding the same level-layer configuration. Returns {check: (ok, detail)}; `ok` is all of them."""
    inst = _instance(instance)
    season = season or dt.date.today().year
    checks: dict[str, tuple[bool, str]] = {}
    mi = inst / "model_inputs.json"
    if mi.exists():
        j = json.loads(mi.read_text(encoding="utf-8"))
        n, dropped = len(j.get("inputs", [])), j.get("template_dropped") or {}
        checks["57 inputs, ios_points_short dropped"] = (n == 57 and "ios_points_short" in dropped,
                                                         f"{n} inputs; dropped {sorted(dropped)}")
    else:
        checks["57 inputs, ios_points_short dropped"] = (False, "no model_inputs.json")
    oi = inst / "odds_input.json"
    if oi.exists():
        o = json.loads(oi.read_text(encoding="utf-8"))
        order = (o.get("rule") or {}).get("order")
        same = o.get("frame_sha256") == _sha256(inst / "model_frame.parquet")
        checks["odds input Pinnacle first, on this frame"] = (order == ["pinnacle", "betonline", "average"] and same,
                                                              f"order {order}; frame hash matches: {same}")
    else:
        checks["odds input Pinnacle first, on this frame"] = (False, "no odds_input.json (finish_instance not run)")
    layer = inst / "level_layer" / "build_config.json"
    lsha = (inst / "level_layer" / "build_config.sha256")
    want = lsha.read_text(encoding="utf-8").split()[0] if lsha.exists() else None
    checks["level layer built"] = (layer.exists() and want is not None, f"build_config sha256 {str(want)[:12]}")
    fits = inst / "fits"
    have = sorted(int(m.group(1)) for f in fits.glob(f"model__{season}__seed*.npz")
                  if (m := re.match(rf"model__{season}__seed(\d+)\.npz", f.name))) if fits.exists() else []
    checks[f"seeds 0-15 fitted for {season}"] = (have == list(range(16)), f"seeds {_span(have) or 'none'}")
    if inst.name == selected_instance_name():
        t = Path(tree) if tree else base_tree()
        tl = t / "data" / "studies" / "current_best_model" / "level_layer" / "this_build" / "build_config.json"
        ok = tl.exists() and want is not None and _sha256(tl) == want
        checks["daily build tree holds the instance's layer config"] = (ok, f"{t}: {'same' if ok else 'missing or different'}")
    out = {"instance": CFG.rel(inst), "season": season, "checks": checks, "ok": all(v[0] for v in checks.values())}
    if show:
        print(f"template check: {CFG.rel(inst)}, season {season}: {'OK' if out['ok'] else 'NOT OK'}")
        for k, (ok, detail) in checks.items():
            print(f"  [{'ok' if ok else 'FAIL'}] {k}: {detail}")
    return out


def fit_seasons(instance=None, *, model: str = CFG.LOCAL, seasons: str | None = None, seeds: str = "0-15",
                wait_memory_only: bool = False, spend_tokens: bool = False, dry_run: bool = False):
    """The season fits of an instance (season Y trained on 2013 .. Y-1).

    model="tabpfn35"           local TabPFN-3.5 on the GPU, seeds 0-15 (fits.py; about an hour for 2019-2026;
                               the card is shared: it waits its turn)
    model="tabpfn35_thinking"  TabPFN-3.5-Thinking on the hosted API, one fit per season (seed 0), see
                               thinking.fit_season: a free quote unless spend_tokens=True
    seasons                    "2019-2026" (default: fits.py's, 2019 to the frame's last season)"""
    CFG.check_model(model)
    inst = _instance(instance)
    if model == CFG.THINKING_MODEL:
        from . import thinking
        years = _years(seasons) if seasons else [dt.date.today().year]
        return [thinking.fit_season(inst, y, spend_tokens=spend_tokens, dry_run=dry_run) for y in years]
    args = ["src/eda/model_rebuild/fits.py", "--out", str(inst), "--seeds", seeds]
    if seasons:
        args += ["--seasons", seasons]
    if wait_memory_only:
        args.append("--wait-memory-only")
    return run_step(Step("fits_local", args, env="local", note="GPU"), dry_run=dry_run)


def _years(spec: str) -> list[int]:
    a, _, b = str(spec).partition("-")
    return list(range(int(a), int(b or a) + 1))


def compare_candidate(candidate, *, through: int | None = None, dry_run: bool = False) -> StepResult:
    """A candidate instance against the frozen reference (compare.py): first the input check (read it first: an
    input flagged "uneven" is the warning sign), then both stages. Then read it with the adoption framework
    (adoption_read.py --scores <its scores.csv> --kind <kind>); accepting it is the owner's call."""
    args = ["src/eda/current_best_model/compare.py", "--candidate", str(candidate)]
    if through:
        args += ["--through", str(through)]
    return run_step(Step("compare_candidate", args), dry_run=dry_run)


def check_history(stage0=None, *, dry_run: bool = False) -> StepResult:
    """A Stage 0 against the frozen reference's (history.py): every new, dropped or revised past match, split into
    the gated lower-level part and the allowed main-tour part."""
    args = ["src/eda/current_best_model/history.py"]
    if stage0:
        args += ["--stage0", str(stage0)]
    return run_step(Step("check_history", args), dry_run=dry_run)


def cleanup_build_sandbox(sandbox, *, confirm: bool = False, dry_run: bool = False) -> StepResult | None:
    """Remove a build sandbox (run_chain --cleanup: the links first, never their targets). Only once no instance
    the daily pipeline may use is built from it."""
    if not confirm and not dry_run:
        print("Refused without confirm=True: the daily pipeline reads an instance's tables from its build sandbox.")
        return None
    return run_step(Step("chain_cleanup", [CHAIN, "--cleanup"], extra_env={"MODEL_REBUILD_SANDBOX": str(sandbox)}),
                    dry_run=dry_run)


# --- the daily pipeline's state for an instance ----------------------------------------------------------------------------
def make_checkpoint(day: str | dt.date, *, tree=None, dry_run: bool = False) -> StepResult:
    """Every input family's state before `day` (dp.py checkpoint; about 11 minutes). A live run leaves a new one by
    itself when parts were recomputed; make one by hand after pointing the daily pipeline at a new instance."""
    args = [str(CFG.DAILY / "dp.py"), "checkpoint", "--day", str(day), "--tree", str(tree or base_tree())]
    return run_step(Step("dp_checkpoint", args, note="about 11 minutes", extra_env=dp_env()), dry_run=dry_run)


def replay_check(week: str = "2026-07-13", round_: str = "R16", checkpoint: str = "2026-06-22", *,
                 run_name: str | None = None, dry_run: bool = False) -> list[StepResult]:
    """The end-to-end proof (the daily pipeline's test 2): a past day's matches replayed as live rows through run_day,
    then replay-compare: every one of the 57 inputs must equal the active instance's model frame. About 7 minutes
    with the GPU (the fit runs too). The replay rebuilds the instance's own tables (since 16 Oct 2026: its dump view
    from data/studies/daily_prediction/replay_views.json and the additions its build merged); a new instance is
    refused until its frozen dump view is listed there."""
    run = CFG.DAILY_RUNS / (run_name or f"replay_{week}_{round_}_{dt.datetime.now():%Y%m%dT%H%M%S}")
    dp = str(CFG.DAILY / "dp.py")
    env = {**dp_env(), "DP_WORK_TREE": "C:/Users/zerom/tnr_daily_nb"}
    return run_steps([Step("dp_replay", [dp, "run_day", "--run", str(run), "--replay-week", week,
                                         "--replay-round", round_, "--checkpoint", checkpoint], extra_env=env),
                      Step("dp_replay_compare", [dp, "replay-compare", "--run", str(run)], extra_env=env)],
                     dry_run=dry_run)


def use_instance(instance, *, tree=None, season: int | None = None) -> dict:
    """Point the daily pipeline at another instance and its build tree (the sandbox it was built in, kept). The choice is
    saved in the notebook's selection (data/studies/master_pipeline/selected_instance.json), the one place that names
    the live model: the daily pipeline reads it, and every daily-pipeline step is handed it. The instance must pass the
    template check with that tree. Afterwards: make_checkpoint(..., tree) and replay_check() before the first live run.
    There is no default to go back to (22 Oct 2026): use_instance(None) refuses; a rollback names the previous instance
    (data/studies/current_best_model/README.md lists each with its tree)."""
    if instance is None:
        raise RuntimeError("There is no default model to go back to (since 22 Oct 2026): name the instance and its build "
                           "tree, e.g. use_instance('template_2026-10-16', tree='C:/Users/zerom/tnr_tpl1016'). "
                           "list_instances() lists the instances; data/studies/current_best_model/README.md gives each "
                           "one's tree.")
    inst = _instance(instance)
    if not dp_reads_instance():
        raise RuntimeError("the daily pipeline does not read DP_INSTANCE yet (dp_common.INSTANCE_ID is hard-coded); "
                           "its session is adding it. Until then the instance cannot be switched from here.")
    if tree is None:
        raise ValueError("give tree=<the instance's build sandbox> (build_instance printed it; sandboxes() lists them)")
    previous = _selection()
    CFG.OUT.mkdir(parents=True, exist_ok=True)
    CFG.SELECTED_INSTANCE.write_text(json.dumps({"instance": inst.name, "tree": str(tree),
                                                 "selected_at": dt.datetime.now().isoformat(timespec="seconds")}),
                                     encoding="utf-8")
    tc = template_check(inst, season=season, tree=tree)
    if not tc["ok"]:
        if previous:
            CFG.SELECTED_INSTANCE.write_text(json.dumps(previous), encoding="utf-8")
        else:
            CFG.SELECTED_INSTANCE.unlink(missing_ok=True)
        raise RuntimeError("the template check failed (above): the choice was not saved")
    print(f"the daily pipeline now uses {inst.name} on {tree}. Next: make_checkpoint(<a day ~3 weeks back>, "
          f"tree={str(tree)!r}), then replay_check(), then the first live run.")
    return {"instance": inst.name, "tree": str(tree), "template_check_ok": True}


# --- the retrain the owner calls (20 Oct 2026) ---------------------------------------------------------------------------
RETRAIN_SCRIPT = "src/eda/in_season_retrain/retrain.sh"
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")


def retrain(name: str | None = None, *, sandbox: str | None = None, cutoff: str | None = None,
            confirm: bool = False) -> dict:
    """A retrain, when the owner says it is time (docs/decisions/2026-10-09-adoption-by-change-class.md, its amendment):
    src/eda/in_season_retrain/retrain.sh builds the template on the shared tables as last rebuilt (B6), records the
    cut-off (default the rebuild's day) and the extended speed table, fits, runs the harm check against the instance in
    use and, with no harm, switches (replay proof, rollback on failure). About 5-6 hours, no input needed.
    confirm=False shows the plan and its checks; confirm=True starts it detached (it survives the kernel and VS Code)
    and returns its log. Run B5, B2, B4 and B6 (confirm=True) first, after the week's lower-level feed snapshot.
    Since 22 Oct 2026 the plan lists the revisions the owner decided for the next retrain
    (data/studies/current_best_model/pending_at_retrain.json; src/eda/current_best_model/pending.py) and refuses to
    start while one is missing from the shared tables; retrain.sh checks the built instance again before its fits."""
    import shutil
    import subprocess
    today = dt.date.today()
    name = name or f"template_{today.isoformat()}"
    sandbox = sandbox or f"C:/Users/zerom/tnr_tpl{today:%m%d}"
    rebuilds = sorted(p for p in (CFG.ROOT / "data" / "studies" / "data_continuity" / "rebuilds").iterdir()
                      if (p / "rebuild.json").exists())
    tables = json.loads((rebuilds[-1] / "rebuild.json").read_text(encoding="utf-8"))["started_at"] if rebuilds else None
    active = active_instance()
    built = dt.datetime.fromtimestamp((active / "model_frame.parquet").stat().st_mtime, dt.timezone.utc) \
        if (active / "model_frame.parquet").exists() else None
    free = shutil.disk_usage("C:/").free / 1e9
    plan = {"instance": name, "sandbox": sandbox, "tables_rebuilt": tables,
            "cutoff": cutoff or (tables[:10] if tables else None), "in_use": active.name,
            "in_use_built": built.isoformat(timespec="minutes") if built else None,
            "disk_free_gb": round(free, 0), "age_now": model_age(active).get("line")}
    checks = {"a new name": not (CFG.INSTANCES / name).exists(),
              f"disk: at least {BUILD_DISK_GB} GB free": free >= BUILD_DISK_GB,
              "tables rebuilt (B6) after the instance in use was built": bool(
                  tables and built and dt.datetime.fromisoformat(tables) > built),
              "Git Bash found": GIT_BASH.exists()}
    # the revisions the owner decided that reach the model only at a retrain (the owner, 22 Oct 2026: "aware of these
    # intended revisions to the model, not simply adding the latest data"): each pending one must already be in the
    # shared tables the build copies (data/studies/current_best_model/pending_at_retrain.json)
    from src.eda.current_best_model import pending as PEND
    pend = PEND.pending()
    if pend:
        res = PEND.check(CFG.STAGE0)
        key = f"the {len(pend)} decided revision(s) pending at this retrain are in the shared tables"
        checks[key] = res["ok"]
        plan["pending_revisions"] = PEND.lines(res)
    plan["checks"] = checks
    print("RETRAIN PLAN")
    for k, v in plan.items():
        if k in ("checks", "pending_revisions"):
            continue
        print(f"  {k}: {v}")
    if pend:
        print("  revisions decided for this retrain (pending_at_retrain.json; the build must carry them):")
        for line in plan["pending_revisions"]:
            print(f"    {line}")
    for k, ok in checks.items():
        print(f"  [{'ok' if ok else 'NO'}] {k}")
    if not checks["tables rebuilt (B6) after the instance in use was built"]:
        print("  The shared tables have not been rebuilt since the instance in use was built. A retrain on them still "
              "trains on this season's matches and grows stage 2, but brings no match, result or repair newer than "
              "those tables: run B5, B2 and B4, then B6 with confirm=True, first.")
    if pend and not checks[key]:
        print("  A decided revision is not in the shared tables yet: rebuild them (B6, rebuild_shared_tables(confirm="
              "True)) first. A retrain without it would add only the latest data; it refuses to start.")
    if not confirm:
        print("Nothing started (confirm=False).")
        return plan
    hard = ["a new name", f"disk: at least {BUILD_DISK_GB} GB free", "Git Bash found"] + ([key] if pend else [])
    if not all(checks[k] for k in hard):
        raise RuntimeError("the retrain's checks failed (above): nothing started")
    log = CFG.ROOT / "data" / "studies" / "in_season_retrain" / "retrains" / f"{name}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    # PowerShell's Start-Process, Git Bash in a hidden window of its own: neither a session's end nor VS Code's closing
    # stops it (a build started from a session's shell died with its console on 14 Oct: data_gaps_2026 process log,
    # 00:24; this launch is the one that build was resumed with, 07:01)
    inner = (f"cd {CFG.ROOT.as_posix().replace('C:', '/c', 1)} && bash {RETRAIN_SCRIPT} {name} {sandbox}"
             + (f" {cutoff}" if cutoff else "") + f" >> {CFG.rel(log).replace(chr(92), '/')} 2>&1")
    # -l: a login shell, whose profile puts conda's folders on PATH. Without it the build's worker processes die in
    # numpy's MKL at their first linear-algebra call (21 Oct 2026: lane 0's IOS pool, BrokenProcessPool; a probe of
    # the same launch: -c fails, -l -c solves)
    ps = (f"$p = Start-Process -FilePath '{GIT_BASH}' -ArgumentList '-l -c \"{inner}\"' -WorkingDirectory '{CFG.ROOT}' "
          "-WindowStyle Hidden -PassThru; $p.Id")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        raise RuntimeError("PowerShell not found: start src/eda/in_season_retrain/retrain.sh by hand, detached")
    done = subprocess.run([shell, "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=120)
    pid = done.stdout.strip().splitlines()[-1] if done.stdout.strip() else None
    if done.returncode or not (pid or "").isdigit():
        raise RuntimeError(f"the retrain did not start: {done.stderr.strip()[-500:]}")
    plan.update({"started": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "pid": int(pid),
                 "log": CFG.rel(log)})
    print(f"STARTED (pid {pid}, a hidden window of its own): follow {CFG.rel(log)}. It switches by itself only if the "
          "harm check and the replay proof pass.")
    return plan


# --- the timer: how far the live training rows are behind (the owner, 20 Oct 2026) ------------------------------------------
MAIN_LEVELS = ("GS", "T1000", "T500", "T250", "FIN")      # the training rows' levels (main-tour main draws)


def model_age(instance=None, *, today: dt.date | None = None) -> dict:
    """The owner's timer ("a timer can exist that watches time since last retrain so im informed off it on the masters
    script", 20 Oct 2026): the instance's live training rows end at its retrain's cut-off (training_cutoff.json) or,
    with none for the season, at 31 Dec of the season before (the season rule). Returns the date they run through, the
    days since, and the main-tour main-draw matches whose results count after it (Stage 0's evaluation rows, the shared
    results table, by the match clock): matches the model has not trained on. Due at CFG.RETRAIN_DUE_DAYS."""
    import pandas as pd

    from src.eda.current_best_model import training_rows as TR
    inst = _instance(instance)
    today = today or dt.date.today()
    rec = TR.read_cutoff(inst) if inst.exists() else None
    if rec and int(rec["season"]) == today.year:
        cutoff = dt.date.fromisoformat(rec["cutoff"])
        rule = f"retrain cut-off, recorded {rec['written_at'][:10]}"
    else:
        cutoff = dt.date(today.year, 1, 1)
        rule = "the season rule: no retrain recorded for this season"
    through = cutoff - dt.timedelta(days=1)          # a result counts by the cut-off when it surely finished before it
    out = {"instance": inst.name, "rule": rule, "trained_through": through.isoformat(),
           "days": (today - through).days, "due_days": CFG.RETRAIN_DUE_DAYS}
    try:
        s0p = CFG.STAGE0 / "stage0_matches.parquet"
        s0 = pd.read_parquet(s0p, columns=["match_id", "level", "qualifying", "evaluation"])
        tm = pd.read_parquet(TR.TIMING, columns=["match_id", "lf"])
        s = s0[s0["evaluation"].astype(bool) & s0["level"].isin(MAIN_LEVELS) & ~s0["qualifying"].astype(bool)]
        lf = s[["match_id"]].merge(tm, on="match_id", how="left").set_index("match_id")["lf"]
        if rec and int(rec["season"]) == today.year:
            # a retrain's rows end where its frame ends: the newest admitted match (closing odds arrive about a week
            # late, so the cut-off's last days are not in the frame); not training rows = the season's main-tour
            # results it does not admit, whether after the cut-off or waiting for their closing price
            admitted = set(rec["ids"])
            newest = tm.set_index("match_id")["lf"].reindex(rec["ids"]).max()
            if pd.notna(newest):
                through = TR.EPOCH + dt.timedelta(days=int(newest))
                out["trained_through"], out["days"] = through.isoformat(), (today - through).days
            season_rows = lf[lf.fillna(-1).to_numpy() + 1 > TR.day_number(dt.date(today.year, 1, 1))]
            out["matches_since"] = int((~season_rows.index.isin(admitted)).sum())
        else:
            out["matches_since"] = int((lf.fillna(-1).to_numpy() + 1 > TR.day_number(cutoff)).sum())
        out["results_table"] = dt.datetime.fromtimestamp(s0p.stat().st_mtime).date().isoformat()
    except Exception as e:                           # the timer never stops a cell
        out["matches_since"], out["results_table"] = None, f"unread ({type(e).__name__})"
    out["due"] = out["days"] >= CFG.RETRAIN_DUE_DAYS
    out["line"] = (f"trained through {dt.date.fromisoformat(out['trained_through']):%d %b %Y} ({rule}): "
                   f"{out['days']} days ago"
                   + (f"; {out['matches_since']:,} main-tour matches of the season are not training rows (results "
                      f"table of {out['results_table']})" if out["matches_since"] is not None else "")
                   + (f". RETRAIN DUE (setting: {CFG.RETRAIN_DUE_DAYS} days)" if out["due"] else "."))
    return out


def show_model_age(instance=None) -> dict:
    """Print the timer's line (A1, A4, Status); never raises."""
    try:
        age = model_age(instance)
        print(f"MODEL AGE: {age['line']}")
        return age
    except Exception as e:
        print(f"MODEL AGE: unknown ({type(e).__name__}: {e})")
        return {}


def _stage2_label(path: Path, inst: Path) -> str:
    """A stage-2 record's season and speed feed from its file name: "2026" (the weekly set) or "2026 daily"."""
    return path.stem[len(inst.name) + 1:].replace("_", " ")


def stage2_status(instance=None) -> dict:
    """The stage-2 coefficients the daily pipeline computed for an instance, by season and speed feed (s_atp, s_wta,
    b shrunk): "2026" is the weekly feed's set, "2026 daily" the daily collector's (live runs from 8 Oct 2026)."""
    inst = _instance(instance)
    out = {}
    for p in sorted(CFG.STAGE2.glob(f"{inst.name}_*.json")):
        j = json.loads(p.read_text(encoding="utf-8"))
        out[_stage2_label(p, inst)] = {k: j.get(k) for k in ("s_atp", "s_wta", "b_shrunk", "matches", "computed_at")}
    return out
