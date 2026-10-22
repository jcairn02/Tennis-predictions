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

INSTANCE_ID = os.environ.get("DP_INSTANCE", "template_2026-10-10")   # the instance folder's name (not a path); with
#     another instance set DP_BASE_TREE to its build tree too, and make a checkpoint on it (11 Oct 2026, for the master
#     notebook: tennis-predictions-fc's request)
INSTANCE = REPO / "data" / "studies" / "current_best_model" / INSTANCE_ID
BASE_TREE = Path(os.environ.get("DP_BASE_TREE", "C:/Users/zerom/tnr_lyr_new"))   # the instance's build tree
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


def stamp() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


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
