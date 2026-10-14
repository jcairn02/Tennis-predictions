"""Section C of the notebook: rebuilding and retraining the current best model.

"The current best model" is a recipe, built on the day's tables (docs/decisions/2026-10-08-current-best-model.md,
§ "Building it"). A built copy of it is an *instance*: a folder under data/studies/current_best_model/ holding the
model frame (57 inputs, Pinnacle-first odds), its input list, the build records and the season fits. These functions
run the decided steps in order, each through its own command line:

    build_instance     run_chain.py in a sandbox copy of the repository: --setup, --additions, lane 0, --prepare-layer,
                       lanes 1 and 2 side by side (about 2.5 h), lane 3, --collect
    finish_instance    the odds input "Pinnacle first" (odds_sources/table.py --link, OddsTrader's every-book lines,
                       odds_input.py --apply) and the 57-input list (template_inputs.py --apply)
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
from pathlib import Path

from . import config as CFG
from .runner import Step, StepResult, run_parallel, run_step, run_steps

CHAIN = "src/eda/model_rebuild/run_chain.py"
BUILD_STEPS = ("setup", "additions", "lane0", "prepare_layer", "lanes12", "lane3", "collect")


# --- which instance the daily pipeline uses ------------------------------------------------------------------------------
# One place decides it, and every daily-pipeline step is handed it explicitly (dp_env), so the checks and the run can
# never look at different instances or trees (review V1, item 3). The kernel's own DP_* variables are never read or
# passed on (runner.SCRUBBED_PREFIXES).
def _dp_common() -> str:
    return (CFG.DAILY / "dp_common.py").read_text(encoding="utf-8")


def dp_defaults() -> tuple[str, Path]:
    """The daily pipeline's own default instance and build tree (read from dp_common.py, not imported: its Python
    functions are internal)."""
    text = _dp_common()
    inst = re.search(r'INSTANCE_ID\s*=\s*(?:os\.environ\.get\("DP_INSTANCE",\s*)?"([^"]+)"', text)
    tree = re.search(r'DP_BASE_TREE",\s*"([^"]+)"', text)
    if not inst or not tree:
        raise RuntimeError("dp_common.py: cannot read its default INSTANCE_ID / DP_BASE_TREE")
    return inst.group(1), Path(tree.group(1))


def dp_reads_instance() -> bool:
    """Whether the daily pipeline takes its instance from DP_INSTANCE (its session is adding it, 11 Oct)."""
    return "DP_INSTANCE" in _dp_common()


def _selection() -> dict:
    return json.loads(CFG.SELECTED_INSTANCE.read_text(encoding="utf-8")) if CFG.SELECTED_INSTANCE.exists() else {}


def active_instance() -> Path:
    """The instance the daily pipeline predicts with: the one chosen with use_instance(), else its own default."""
    return CFG.INSTANCES / (_selection().get("instance") or dp_defaults()[0])


def base_tree() -> Path:
    """The active instance's build tree, which the daily pipeline reads its tables from."""
    sel = _selection()
    return Path(sel["tree"]) if sel.get("tree") else dp_defaults()[1]


def dp_env() -> dict:
    """The variables every daily-pipeline step is given: the build tree always; the instance once the daily pipeline
    reads DP_INSTANCE. Refuses a chosen instance the daily pipeline cannot be pointed at."""
    inst, default = active_instance().name, dp_defaults()[0]
    env = {"DP_BASE_TREE": str(base_tree())}
    if dp_reads_instance():
        env["DP_INSTANCE"] = inst
    elif inst != default:
        raise RuntimeError(f"the chosen instance {inst} differs from the daily pipeline's {default}, and the daily "
                           "pipeline does not read DP_INSTANCE yet: use_instance(None) to go back to its default")
    return env


def _instance(instance) -> Path:
    if instance is None:
        return active_instance()
    p = Path(instance)
    return p if p.is_absolute() else (CFG.INSTANCES / p if not str(p).startswith("data") else CFG.ROOT / p)


def instance_status(instance=None) -> dict:
    """What an instance holds: its inputs, the odds input, the fits per season (local seeds; Thinking fits), the
    stage-2 coefficients computed for it, and the daily pipeline's checkpoints and TabPFN caches for it."""
    inst = _instance(instance)
    out: dict = {"instance": CFG.rel(inst), "exists": inst.exists(), "active": inst == active_instance()}
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
    out["stage2"] = sorted(p.stem.rsplit("_", 1)[-1] for p in CFG.STAGE2.glob(f"{inst.name}_*.json"))
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
    special = {base_tree().as_posix().lower(): "the active instance's build tree (the daily pipeline reads it)",
               "c:/users/zerom/tnr_dump_freeze": "replays' frozen dump", "c:/users/zerom/tnr_daily": "daily work tree",
               "c:/users/zerom/tnr_daily_nb": "notebook's daily work tree"}
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


BUILD_DISK_GB = 130   # a sandbox copies data/studies whole (run_chain.setup), today ~75 GB with the daily pipeline's
                      # 55 GB of TabPFN caches, and the new instance's own caches add ~56 GB when it first predicts


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
            f"{free:.0f} GB free; a build needs about {BUILD_DISK_GB} GB. run_chain's sandbox copies data/studies whole, "
            "including the daily pipeline's TabPFN caches (55 GB in data/studies/daily_prediction/state), which a model "
            "build does not read. Options: free space (sandboxes() lists the tnr_* trees, ~20 GB each), or have "
            "run_chain exclude daily_prediction/prediction_run/master_pipeline from its copy (another study's code: the "
            "owner's call), then allow_low_disk=True.")
    env = {"MODEL_REBUILD_SANDBOX": str(sandbox)}
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


def finish_instance(out, *, dry_run: bool = False) -> list[StepResult]:
    """The decided odds input and input list on a built instance:
        odds_sources/table.py --link, OddsTrader's every-book lines for the frame's events (network), then
        odds_input.py --apply (Pinnacle first: Pinnacle's close, BetOnline's, the average) and
        template_inputs.py --apply (57 inputs: ios_points_short dropped).
    The monthly OddsTrader pull must cover the frame's months first (data.refresh_odds_history)."""
    out = Path(out)
    steps = [Step("odds_link", ["src/eda/odds_sources/table.py", "--link"]),
             Step("oddstrader_books", ["-m", "src.ingest.oddstrader", "--books-eids",
                                       "data/studies/odds_sources/oddstrader_eids.csv", "--max-requests", "600"]),
             Step("odds_input_apply", ["src/eda/current_best_model/odds_input.py", "--apply", str(out)]),
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
    if inst == active_instance():
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
    with the GPU (the fit runs too)."""
    run = CFG.DAILY_RUNS / (run_name or f"replay_{week}_{round_}_{dt.datetime.now():%Y%m%dT%H%M%S}")
    dp = str(CFG.DAILY / "dp.py")
    env = {**dp_env(), "DP_WORK_TREE": "C:/Users/zerom/tnr_daily_nb"}
    return run_steps([Step("dp_replay", [dp, "run_day", "--run", str(run), "--replay-week", week,
                                         "--replay-round", round_, "--checkpoint", checkpoint], extra_env=env),
                      Step("dp_replay_compare", [dp, "replay-compare", "--run", str(run)], extra_env=env)],
                     dry_run=dry_run)


def use_instance(instance, *, tree=None, season: int | None = None) -> dict:
    """Point the daily pipeline at another instance and its build tree (the sandbox it was built in, kept), or back at
    its own default with use_instance(None). The choice is saved (data/studies/master_pipeline/selected_instance.json)
    and handed to every daily-pipeline step. It needs the daily pipeline to read DP_INSTANCE (its session is adding it)
    and the instance to pass the template check with that tree. Afterwards: make_checkpoint(..., tree) and
    replay_check() before the first live run."""
    if instance is None:
        CFG.SELECTED_INSTANCE.unlink(missing_ok=True)
        print(f"back to the daily pipeline's default: {dp_defaults()[0]} on {dp_defaults()[1]}")
        return {"instance": dp_defaults()[0], "tree": str(dp_defaults()[1])}
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


def stage2_status(instance=None) -> dict:
    """The stage-2 coefficients the daily pipeline computed for an instance, by season (s_atp, s_wta, b shrunk)."""
    inst = _instance(instance)
    out = {}
    for p in sorted(CFG.STAGE2.glob(f"{inst.name}_*.json")):
        j = json.loads(p.read_text(encoding="utf-8"))
        out[p.stem.rsplit("_", 1)[-1]] = {k: j.get(k) for k in ("s_atp", "s_wta", "b_shrunk", "matches", "computed_at")}
    return out
