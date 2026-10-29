"""Shared paths and helpers of the daily prediction script (docs/studies/daily_prediction/; the plan:
docs/studies/prediction_pipeline/PLAN.md).

The script's modules import each other by bare name (dp_*), so the same modules run from the repository and from a work
tree's copy of it. The decided builders are imported from a TREE (the template's build tree, or the run's work tree):
use_tree() puts that tree first on sys.path, so `src.eda...` is the tree's code and its ROOT-relative paths are the
tree's tables. Every output of the script goes to the repository (REPO), never into a tree it only reads.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("DP_REPO", "C:/Users/zerom/Documents/Tennis-predictions"))
OUT = REPO / "data" / "studies" / "daily_prediction"
STATE = Path(os.environ.get("DP_STATE", str(OUT / "state")))
RUNS = OUT / "runs"
PROTOTYPES = HERE.parent / "prediction_pipeline"         # the plan's verified prototypes (imported, never edited)

# Which instance the script predicts with (22 Oct 2026; docs/studies/master_pipeline/process_log.md, Part 9). ONE place
# names the live model: the master notebook's selection (SELECTED, written by its use_instance() and by a retrain's
# switch). DP_INSTANCE with DP_BASE_TREE, its build tree, names another instance explicitly (a retrain's or a
# candidate's checkpoints and replays; the notebook hands both to every step). There is no default: until 22 Oct 2026 the
# 10 Oct instance and its tree were, so a run started without the notebook predicted with a model two retrains old.
# Unresolved, the module still imports (its helpers serve tests and other scripts), but every dp.py command refuses
# (require_instance).
SELECTED = REPO / "data" / "studies" / "master_pipeline" / "selected_instance.json"
UNSELECTED = "NO_INSTANCE_SELECTED"


def _same_path(a, b) -> bool:
    return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))


def resolve_instance(environ=None, selected: Path | None = None) -> tuple[str | None, Path | None, str]:
    """(the instance folder's name, its build tree, where both came from), or (None, None, why there is none)."""
    env = os.environ if environ is None else environ
    path = Path(selected) if selected is not None else SELECTED
    sel = {}
    if path.exists():
        try:
            sel = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return None, None, f"the notebook's selection {path} cannot be read ({type(e).__name__}: {e})"
    s_inst, s_tree = str(sel.get("instance") or "").strip(), str(sel.get("tree") or "").strip()
    e_inst, e_tree = str(env.get("DP_INSTANCE") or "").strip(), str(env.get("DP_BASE_TREE") or "").strip()
    if e_inst:
        if e_tree:
            return e_inst, Path(e_tree), "DP_INSTANCE and DP_BASE_TREE" + (
                "" if e_inst == s_inst else f" (the notebook's selection names {s_inst or 'no instance'})")
        if e_inst == s_inst and s_tree:
            return e_inst, Path(s_tree), "DP_INSTANCE, with the notebook's selection's build tree"
        return None, None, (f"DP_INSTANCE names {e_inst} without DP_BASE_TREE, its build tree (the notebook's "
                            f"selection names {s_inst or 'no instance'})")
    if not s_inst or not s_tree:
        return None, None, (f"no instance is selected: the notebook's selection {path} is missing or names no "
                            "instance and tree, and DP_INSTANCE is not set")
    if e_tree and not _same_path(e_tree, s_tree):
        return None, None, (f"DP_BASE_TREE names {e_tree}, but the notebook's selection pairs {s_inst} with {s_tree}: "
                            "set DP_INSTANCE too")
    return s_inst, Path(s_tree), f"the notebook's selection (selected {sel.get('selected_at', 'at an unrecorded time')})"


_INSTANCE, _TREE, INSTANCE_SOURCE = resolve_instance()
INSTANCE_OK = _INSTANCE is not None
INSTANCE_ID = _INSTANCE or UNSELECTED                     # the instance folder's name (not a path)
INSTANCE = REPO / "data" / "studies" / "current_best_model" / INSTANCE_ID
BASE_TREE = _TREE or (REPO.parent / UNSELECTED)          # the instance's build tree
WORK_TREE = Path(os.environ.get("DP_WORK_TREE", "C:/Users/zerom/tnr_daily"))
# an exact replay's dump view named by hand; without it replay_tables reads the instance's from REPLAY_VIEWS (16 Oct 2026)
FREEZE_DUMP = Path(os.environ["DP_FREEZE_DUMP"]) if os.environ.get("DP_FREEZE_DUMP") else None
REPLAY_VIEWS = OUT / "replay_views.json"
ACCEPTED = REPO / "data" / "studies" / "current_best_model" / "accepted_additions"
PY = Path(os.environ.get("TENNIS_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis/python.exe"))
PY_TABPFN = Path(os.environ.get("TENNIS_TABPFN_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis-tabpfn-local/python.exe"))
# the hosted TabPFN API's environment (tennis-tabpfn), and the paid TabPFN-3.5-Thinking season fits the master pipeline
# makes (src/pipeline/thinking.py): dp_thinking, the --thinking step (20 Oct 2026)
PY_API = Path(os.environ.get("TENNIS_TABPFN_API_PYTHON", "C:/Users/zerom/miniforge3/envs/tennis-tabpfn/python.exe"))
THINKING_FITS = REPO / "data" / "studies" / "master_pipeline" / "thinking"

LAYER_BUILD = Path("data") / "studies" / "current_best_model" / "level_layer" / "this_build" / "build_config.json"
PD = Path("data") / "studies" / "predictability_diagnostic"
MT = Path("data") / "studies" / "match_timing"

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def require_instance() -> str:
    """Refuse (SystemExit) unless an instance was resolved; then hand it to every process this one starts, so a step
    started later in the run reads the same instance even if the selection changes meanwhile (a retrain switching it).
    Returns where the instance came from."""
    if not INSTANCE_OK:
        raise SystemExit(f"Refused: {INSTANCE_SOURCE}. The daily pipeline has no default instance (since 22 Oct 2026): "
                         "choose one in the master notebook (use_instance), or set DP_INSTANCE with DP_BASE_TREE.")
    os.environ["DP_INSTANCE"] = INSTANCE_ID
    os.environ["DP_BASE_TREE"] = str(BASE_TREE)
    return INSTANCE_SOURCE


def stamp() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


# ------------------------------------------------------------------------------------------------
# The code a run used, and the receipt of the last passing replay (production-integrity plan, step 2, 22 Oct 2026;
# docs/decisions/2026-10-22-production-integrity-plan.md): every dp.py process records the project source files it
# imported (code_used/<step>_<pid>.json in the run folder), the predict step merges them into the run's provenance, and a
# replay-compare that passes writes a receipt (RECEIPTS/<instance>.json) holding every source file's fingerprint at that
# moment. "Verified" means: equal to the receipt. The bet sheet compares a live run with it (pipeline/diagnostics).

RECEIPTS = OUT / "receipts"


def code_rel(path) -> str | None:
    """A project source file's path from its tree's root ("src/..."), or None for anything else: only the repository
    and the build and work trees (C:/Users/zerom/tnr_*) count, never an environment's libraries."""
    p = Path(path)
    if p.suffix != ".py" or "src" not in p.parts:
        return None
    i = p.parts.index("src")
    root = Path(*p.parts[:i])
    try:
        mine = root.resolve() == REPO.resolve() or root.name.lower().startswith("tnr_")
    except OSError:
        return None
    return Path(*p.parts[i:]).as_posix() if mine else None


def code_fingerprints() -> dict:
    """{"src/...py": sha256} of every project source module this process has imported."""
    out = {}
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        rel = code_rel(f) if f else None
        if rel and rel not in out:
            try:
                out[rel] = sha256(f)
            except OSError:
                pass
    return dict(sorted(out.items()))


def write_code_used(run_dir: Path, label: str) -> None:
    """This process's code fingerprints into <run>/code_used/<label>_<pid>.json (one file a process, never shared)."""
    d = Path(run_dir) / "code_used"
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / f"{label}_{os.getpid()}.json", {"label": label, "pid": os.getpid(), "at": stamp(),
                                                    "python": sys.executable, "files": code_fingerprints()})


def code_used(run_dir: Path, extra: dict | None = None) -> tuple[dict, list]:
    """The run's code: every process's fingerprints merged ({rel: sha}), and the files seen with more than one content
    (the code changed while the run was going)."""
    seen: dict[str, set] = {}
    for f in sorted((Path(run_dir) / "code_used").glob("*.json")):
        for rel, sha in read_json(f).get("files", {}).items():
            seen.setdefault(rel, set()).add(sha)
    for rel, sha in (extra or {}).items():
        seen.setdefault(rel, set()).add(sha)
    merged = {rel: next(iter(s)) for rel, s in seen.items() if len(s) == 1}
    conflicts = [{"file": rel, "sha256": sorted(s)} for rel, s in sorted(seen.items()) if len(s) > 1]
    return dict(sorted(merged.items())), conflicts


def source_snapshot(root: Path = REPO) -> dict:
    """{"src/...py": sha256} of every source file under root/src: what a receipt calls verified."""
    base = Path(root)
    return {p.relative_to(base).as_posix(): sha256(p) for p in sorted((base / "src").rglob("*.py"))
            if "__pycache__" not in p.parts}


def replay_passed(res: dict) -> bool:
    """The replay proof's own standard: every input bit for bit, or every non-IOS input bit for bit and the IOS inputs
    within the owner's 1e-6 with their blanks in the same places; and every replayed match found in the frame."""
    if not res.get("matches") or res.get("missing_from_frame"):
        return False
    if res.get("inputs_bitwise") == res.get("inputs"):
        return True
    return (res.get("non_ios_bitwise") == res.get("non_ios_inputs") and bool(res.get("ios_nan_pattern_equal"))
            and float(res.get("ios_max_abs_diff") or 0.0) <= 1e-6)


def write_receipt(run_dir: Path, res: dict) -> Path | None:
    """The receipt of a passing replay: the instance, the replay, the code it ran, and every source file's fingerprint
    now. None (and nothing written) when the code changed during the replay or since it ran: such a replay verifies
    nothing."""
    run_dir = Path(run_dir)
    cfg = read_json(run_dir / "run.json")
    prov = read_json(run_dir / "provenance.json") if (run_dir / "provenance.json").exists() else {}
    used, conflicts = code_used(run_dir)
    snap = source_snapshot()
    moved = sorted(rel for rel, sha in used.items() if snap.get(rel) != sha)
    if conflicts or moved:
        print(f"no receipt: the code changed during the replay ({[c['file'] for c in conflicts]}) or since it ran "
              f"({moved[:5]})", file=sys.stderr, flush=True)
        return None
    inst = Path(cfg["instance"]).name
    rec = {"what": "The last passing replay proof of this instance: what 'verified' means for the bet sheet's model "
                   "check (docs/decisions/2026-10-22-production-integrity-plan.md).",
           "written_at": stamp(), "instance": inst, "base_tree": cfg.get("base_tree"), "replay_run": str(run_dir),
           "replay": cfg.get("replay"),
           "result": {k: res.get(k) for k in ("matches", "inputs", "inputs_bitwise", "non_ios_bitwise",
                                              "non_ios_inputs", "ios_max_abs_diff", "max_abs_diff")},
           "model_files": {k: prov.get(k) for k in ("instance_frame_sha256", "instance_inputs_sha256",
                                                    "layer_config_sha256", "tabpfn_weights_sha256", "tabpfn")},
           "code_used": used, "snapshot": snap}
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    path = RECEIPTS / f"{inst}.json"
    write_json(path, rec)
    with (RECEIPTS / "receipts.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({k: rec[k] for k in ("written_at", "instance", "replay_run", "replay", "result")},
                            default=_default) + "\n")
    return path


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    return str(o)


def write_json(path: Path, value) -> None:
    """Atomic JSON write (a partial file never replaces a good one)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(value, indent=1, default=_default), encoding="utf-8")
    os.replace(part, path)


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def day_of(value) -> int:
    """A date (anything numpy reads as a day, or a pandas timestamp) as days since 1970-01-01."""
    import pandas as pd
    return int((pd.Timestamp(value).normalize() - pd.Timestamp("1970-01-01")).days)


def date_of(day: int) -> str:
    return str(np.datetime64(int(day), "D"))


def replay_tables(instance: Path = INSTANCE, freeze: Path | None = FREEZE_DUMP,
                  registry: Path = REPLAY_VIEWS, accepted: Path = ACCEPTED) -> dict:
    """What an exact replay of `instance` builds its tables from, so that they are the instance's own (16 Oct 2026):
        dump view   Tennis My Life's staged dump as the instance's build read it (level_layer_adoption/freeze_dump.py):
                    `freeze` (DP_FREEZE_DUMP) if given, else the registry's entry for the instance
        additions   the lower-level additions its build merged, in accepted.json's form and order: the instance's own
                    record (accepted_at_build.json, else chain_additions.json's applied packages), else the registry's
    Refuses an instance missing either: on another dump, or with today's accepted.json (which since 14 Oct differs
    from every instance's), the replay's Stage 0 is not the instance's, and the merge or the held timeline fails."""
    instance = Path(instance)
    reg = read_json(registry).get(instance.name, {}) if Path(registry).exists() else {}
    view = Path(freeze) if freeze else (Path(reg["dump_view"]) if reg.get("dump_view") else None)
    if view is None:
        raise SystemExit(f"{instance.name}: no dump view for an exact replay. Freeze one at the start of the Stage 0 "
                         f"rebuild its build copied (level_layer_adoption/freeze_dump.py), then add it to {registry} "
                         "or set DP_FREEZE_DUMP")
    if not (view / "freeze_dump.json").exists():
        raise SystemExit(f"{view}: not a dump view (no freeze_dump.json)")
    at_build, chain = instance / "accepted_at_build.json", instance / "chain_additions.json"
    if at_build.exists():
        cur = read_json(at_build)
        add, source = {"packages": list(cur.get("packages", [])), "feeds": dict(cur.get("feeds", {}))}, str(at_build)
    elif chain.exists():
        names = []
        for p in read_json(chain)["applied"]["packages"]:
            parts = Path(p["package"]).parts
            low = [x.lower() for x in parts]
            if "accepted_additions" not in low:
                raise SystemExit(f"{chain}: {p['package']} is not under accepted_additions")
            names.append("/".join(parts[low.index("accepted_additions") + 1:]))
        add, source = {"packages": names, "feeds": {}}, str(chain)
    elif "additions" in reg:
        add, source = {"packages": list(reg["additions"].get("packages", [])),
                       "feeds": dict(reg["additions"].get("feeds", {}))}, f"{registry} ({instance.name})"
    else:
        raise SystemExit(f"{instance.name}: no record of the additions its build merged (accepted_at_build.json, "
                         f"chain_additions.json, or an 'additions' entry in {registry})")
    for name in add["packages"] + [f"{f}/{s}" for f, s in add["feeds"].items()]:
        if not (Path(accepted) / name / "manifest.json").exists():
            raise SystemExit(f"{instance.name}: its build merged {name}, which {accepted} no longer holds")
    return {"instance": instance.name, "dump_view": str(view), "view_from": "DP_FREEZE_DUMP" if freeze else str(registry),
            "freeze": read_json(view / "freeze_dump.json").get("freeze"), "additions": add, "additions_from": source}


# ------------------------------------------------------------------------------------------------
# Trees

def use_tree(tree: Path) -> Path:
    """Put the tree first on sys.path (its `src` package and tables win); refuse if `src` came from elsewhere already.
    Importing a tree's modules must not write bytecode into it."""
    tree = Path(tree).resolve()
    if not (tree / "src" / "eda").is_dir():
        raise SystemExit(f"{tree} is not a tree (no src/eda)")
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"          # worker processes too
    mod = sys.modules.get("src")
    if mod is not None and Path(list(mod.__path__)[0]).resolve() != (tree / "src"):
        raise RuntimeError(f"`src` already imported from {list(mod.__path__)[0]}, not {tree}")
    if str(tree) not in sys.path:
        sys.path.insert(0, str(tree))
    if str(PROTOTYPES) not in sys.path:
        sys.path.insert(1, str(PROTOTYPES))
    return tree


def layer_config_for(tree: Path, copy_to: Path | None = None) -> Path:
    """The tree's resolved level-layer config. For a tree only read (copy_to given): a copy with record_dir null, so the
    layer's hooks write nothing into the tree, and stage0_matches pinned to the tree's Stage 0."""
    src = Path(tree) / LAYER_BUILD
    if not src.exists():
        raise SystemExit(f"{src}: the tree has no resolved level-layer config")
    if copy_to is None:
        return src
    cfg = json.loads(src.read_text(encoding="utf-8"))
    cfg["record_dir"] = None
    cfg["stage0_matches"] = str(Path(tree) / PD / "stage0_matches.parquet")
    cfg["read_only_copy_of"] = {"path": str(src), "sha256": sha256(src)}
    copy_to.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cfg, indent=1)
    if not copy_to.exists() or copy_to.read_text(encoding="utf-8") != text:
        copy_to.write_text(text, encoding="utf-8")
    return copy_to


def enter_tree(tree: Path, read_only: bool) -> Path:
    """use_tree + LLE_LAYER: a read-only tree's config copy (in OUT/layer_copies/<tree name>.json), or a work tree's own
    config (its hooks record into the work tree). Returns the config path."""
    use_tree(tree)
    cfg = layer_config_for(tree, OUT / "layer_copies" / f"{Path(tree).name}.json" if read_only else None)
    held = os.environ.get("LLE_LAYER", "").strip()
    if held and Path(held).resolve() != cfg.resolve():
        raise SystemExit(f"LLE_LAYER is set to {held}, not this tree's {cfg}")
    os.environ["LLE_LAYER"] = str(cfg)
    return cfg


def threads(n: int) -> None:
    """BLAS threads (the IOS runs were built single-threaded: build_features.py sets 1); call before numpy work."""
    for v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ.setdefault(v, str(n))


# ------------------------------------------------------------------------------------------------
# Comparisons

def compare(a, b) -> dict:
    """a against b: equal NaN pattern, bitwise-equal count, largest absolute difference."""
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    na, nb = np.isnan(a), np.isnan(b)
    both = ~na & ~nb
    d = np.abs(a[both] - b[both])
    return {"rows": int(a.size), "nan_pattern_equal": bool(np.array_equal(na, nb)),
            "bitwise_equal": int(np.sum(a[both] == b[both]) + np.sum(na & nb)),
            "max_abs_diff": float(d.max()) if d.size else 0.0}


def bitwise(c: dict) -> bool:
    return c["nan_pattern_equal"] and c["bitwise_equal"] == c["rows"]
