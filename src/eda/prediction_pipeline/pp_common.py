"""Shared helpers of the prediction-pipeline verification (docs/studies/prediction_pipeline/).

The verification reads a finished template build TREE (default: the sandbox the current best model of 10 Oct 2026 was
built in, C:/Users/zerom/tnr_lyr_new, whose intermediate tables are still on disk) and imports that tree's own code,
so the checks compare against the very code and tables that built the template's frame. Nothing in the tree is
written: the level layer's hooks run with a copy of the tree's resolved config whose record_dir is null (its hooks then
record nothing), written into this study's data folder.

Import pattern of this study's scripts (the tree's `src` package must win over the repository's):
    HERE = Path(__file__).resolve().parent
    sys.path.insert(0, str(HERE))         # this study's modules by bare name
    import pp_common as PC
    PC.use_tree()                          # the tree first on sys.path; then `from src.eda... import ...`
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
REPO = HERE.parents[2]
TREE = Path(os.environ.get("PP_TREE", "C:/Users/zerom/tnr_lyr_new"))
OUT = REPO / "data" / "studies" / "prediction_pipeline"
LAYER_BUILD = Path("data") / "studies" / "current_best_model" / "level_layer" / "this_build" / "build_config.json"

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def use_tree(tree: Path = TREE) -> Path:
    """Put the build tree first on sys.path, so `src.eda...` is the tree's code (and its ROOT-relative paths its
    tables). Refuses when `src` was already imported from elsewhere."""
    tree = Path(tree).resolve()
    if not (tree / "src" / "eda").is_dir():
        raise SystemExit(f"{tree} is not a build tree (no src/eda)")
    sys.dont_write_bytecode = True               # importing the tree's modules must not write __pycache__ into it
    mod = sys.modules.get("src")
    if mod is not None and Path(mod.__path__[0]).resolve() != (tree / "src"):
        raise RuntimeError(f"`src` already imported from {mod.__path__[0]}")
    if str(tree) not in sys.path:
        sys.path.insert(0, str(tree))
    return tree


def layer_config(tree: Path = TREE, out: Path = OUT) -> Path:
    """A copy of the tree's resolved layer config with record_dir null (no hook writes anything), stage0_matches
    pinned to the tree's Stage 0. Returns its path; set LLE_LAYER to it to run the hooks as the build ran them."""
    src = Path(tree) / LAYER_BUILD
    cfg = json.loads(src.read_text(encoding="utf-8"))
    cfg["record_dir"] = None
    cfg["stage0_matches"] = str(Path(tree) / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet")
    cfg["verification_copy_of"] = {"path": str(src), "sha256": sha256(src)}
    out.mkdir(parents=True, exist_ok=True)
    p = out / "layer_config_verify.json"
    text = json.dumps(cfg, indent=1)
    if not p.exists() or p.read_text(encoding="utf-8") != text:
        p.write_text(text, encoding="utf-8")
    return p


def set_layer(tree: Path = TREE) -> Path:
    p = layer_config(tree)
    os.environ["LLE_LAYER"] = str(p)
    return p


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, Path):
            return str(o)
        return str(o)
    path.write_text(json.dumps(value, indent=1, default=default), encoding="utf-8")


def compare(a: np.ndarray, b: np.ndarray) -> dict:
    """Exactness of a against b: equal NaN pattern, bitwise-equal count, largest absolute and relative difference."""
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    na, nb = np.isnan(a), np.isnan(b)
    both = ~na & ~nb
    d = np.abs(a[both] - b[both])
    scale = np.maximum(np.abs(b[both]), 1e-300)
    return {"rows": int(a.size), "nan_pattern_equal": bool(np.array_equal(na, nb)),
            "bitwise_equal": int(np.sum(a[both] == b[both]) + np.sum(na & nb)),
            "max_abs_diff": float(d.max()) if d.size else 0.0,
            "max_rel_diff": float((d / scale).max()) if d.size else 0.0}
