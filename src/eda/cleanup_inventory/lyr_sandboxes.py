"""tnr_lyr_off and tnr_lyr_on (the level-layer adoption study's two builds of 10 Oct 2026): keep what reads them
working, then delete them. The owner, 14 Oct 2026: "Do this and be mindful of anything that reads these files to
properly change it" (docs/studies/cleanup_inventory/process_log.md § 7).

Readers (found 14 Oct 2026):
    src/eda/level_layer_adoption/verify.py --gates     5 summary JSONs of ON (G5's leak probes), 2 of OFF (constants)
    src/eda/level_layer_adoption/solver_tolerance.py   ON's lane-2 cache (surface_ios/cache/atp.npz) and ON's build
                                                       config, which names ON's strength table and a record folder
    src/eda/unpriced_leads/rebuild_pool.py             OFF's stageB_adj.parquet, through its own frozen extract

--extract          copies what they read to data/studies/level_layer_adoption/sandbox_extracts/<sandbox>/, in the
                   sandbox's own layout, byte for byte (SHA-256 of source and copy in its manifest.json). ON's build
                   config is written relocated (strength.path into the extract; record_dir null, so a re-run never
                   writes into the deleted folder); the original is kept beside it as build_config.original.json.
--prove --stage S  before: each reader on the sandboxes and on the extracts (patched in memory), outputs compared;
                   edited: the readers as edited (no patch) against before's sandbox outputs; after: the same once the
                   sandboxes are gone, and neither sandbox re-created. verify.py writes to a temporary folder, never over
                   its records.
--delete           removes both sandboxes as delete_now.py does (links removed first, as links; the kept trees listed
                   before and after); --dry-run lists only.
Record: data/studies/cleanup_inventory/lyr_2026-10-14.json.
Run: ./python.sh src/eda/cleanup_inventory/lyr_sandboxes.py --extract | --prove --stage before | --delete --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.cleanup_inventory import delete_now as D  # noqa: E402

HOME = Path("C:/Users/zerom")
SANDBOX = {"OFF": HOME / "tnr_lyr_off", "ON": HOME / "tnr_lyr_on"}
STUDIES = ROOT / "data" / "studies"
EXTRACTS = STUDIES / "level_layer_adoption" / "sandbox_extracts"
EXTRACT = {k: EXTRACTS / v.name for k, v in SANDBOX.items()}
RECORD = STUDIES / "cleanup_inventory" / "lyr_2026-10-14.json"
BUILD = "data/studies/current_best_model/level_layer/this_build"
SUMMARIES = ["data/studies/predictability_diagnostic/stage1_baselines_summary.json",
             "data/studies/predictability_diagnostic/stage3_ratings_summary.json",
             "data/studies/predictability_diagnostic/stage4_features_summary.json",
             "data/studies/ufc_ideas/stageB_adj_summary.json",
             "data/studies/surface_elo_pieces/pieces_meta.json"]
FILES = {"OFF": SUMMARIES,
         "ON": SUMMARIES + ["data/studies/surface_ios/cache/atp.npz",
                            "data/studies/surface_ios/cache/manifest.json",
                            f"{BUILD}/strength_elo.parquet",
                            f"{BUILD}/strength_elo.parquet.sha256",
                            f"{BUILD}/strength_check.json",
                            f"{BUILD}/layer_calls/layer_calls.jsonl"]}
CONFIG_ORIGINALS = {f"{BUILD}/build_config.json": f"{BUILD}/build_config.original.json",
                    f"{BUILD}/build_config.sha256": f"{BUILD}/build_config.original.sha256"}
UNPRICED = STUDIES / "unpriced_leads" / "candidates" / "pool_rebuilt" / "inputs" / "layer_off_stageB_z.parquet"
UNPRICED_CODE = ROOT / "src" / "eda" / "unpriced_leads" / "rebuild_pool.py"
PROTECTED = [ROOT / "data" / "raw", ROOT / "data" / "dump", HOME / "tnr_dump_freeze", HOME / "tnr_dump_freeze_1014",
             HOME / "tnr_lyr_new", STUDIES / "current_best_model", STUDIES / "level_layer_adoption",
             STUDIES / "unpriced_leads"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}


def save_record(rec: dict) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------------------------------------
# --extract

def extract() -> dict:
    files = []
    for name, rels in FILES.items():
        for rel in rels:
            src, dst = SANDBOX[name] / rel, EXTRACT[name] / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            a, b = sha256(src), sha256(dst)
            if a != b:
                raise RuntimeError(f"{dst}: copy differs from {src}")
            files.append({"sandbox": name, "file": rel, "source": str(src), "bytes": dst.stat().st_size, "sha256": a})
    for rel, rel_copy in CONFIG_ORIGINALS.items():
        src, dst = SANDBOX["ON"] / rel, EXTRACT["ON"] / rel_copy
        shutil.copy2(src, dst)
        a, b = sha256(src), sha256(dst)
        if a != b:
            raise RuntimeError(f"{dst}: copy differs from {src}")
        files.append({"sandbox": "ON", "file": rel_copy, "copied_from_file": rel, "source": str(src),
                      "bytes": dst.stat().st_size, "sha256": a})
    # the relocated build config: only the strength table's path and the record folder change
    orig_path = SANDBOX["ON"] / BUILD / "build_config.json"
    cfg = json.loads(orig_path.read_text(encoding="utf-8"))
    old_strength, old_record = cfg["strength"]["path"], cfg.get("record_dir")
    new_strength = EXTRACT["ON"] / BUILD / "strength_elo.parquet"
    if sha256(new_strength) != cfg["strength"]["sha256"]:
        raise RuntimeError("the extract's strength table is not the one the config pins")
    cfg["strength"]["path"] = str(new_strength)
    cfg["record_dir"] = None
    cfg["relocated"] = {
        "on": "2026-10-14", "why": "the sandbox C:/Users/zerom/tnr_lyr_on was deleted (owner, 14 Oct 2026); the files "
        "the readers use were copied here byte for byte (manifest.json)",
        "original": "build_config.original.json", "original_sha256": sha256(orig_path),
        "changed": {"strength.path": [old_strength, str(new_strength)],
                    "record_dir": [old_record, None]},
        "record_dir_why": "the hooks append layer_calls.jsonl to record_dir and create the folder: pointed at the "
                          "deleted sandbox, a re-run would re-create it; null writes no record (no computed value "
                          "depends on it)"}
    out_cfg = EXTRACT["ON"] / BUILD / "build_config.json"
    out_cfg.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    from src.eda.lower_level_evidence import level_layer as L
    L.load_config(out_cfg)                                   # it must still validate
    manifest = {"what": "files the readers of tnr_lyr_off / tnr_lyr_on use, copied before the sandboxes were deleted",
                "written": now(), "script": "src/eda/cleanup_inventory/lyr_sandboxes.py --extract",
                "files": files,
                "relocated_config": {"file": f"tnr_lyr_on/{BUILD}/build_config.json", "sha256": sha256(out_cfg),
                                     **cfg["relocated"]},
                "readers": {"src/eda/level_layer_adoption/verify.py --gates": "the 5 summary JSONs of ON (G5), "
                            "stage3_ratings_summary and stageB_adj_summary of OFF (constants)",
                            "src/eda/level_layer_adoption/solver_tolerance.py": "ON: surface_ios/cache/atp.npz and "
                            "the relocated build_config.json (its strength table here; params, classes and pins are "
                            "repository files)"}}
    (EXTRACTS / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    rec = load_record()
    rec["extract"] = {"at": now(), "files": len(files), "bytes": sum(f["bytes"] for f in files),
                      "relocated_config_sha256": manifest["relocated_config"]["sha256"]}
    save_record(rec)
    print(json.dumps(rec["extract"], indent=1))
    return manifest


# ------------------------------------------------------------------------------------------------
# --prove

TIMING = {"seconds"}        # wall-clock fields inside a result (the solver's lle_layer.seconds): left out of digests


def digest(x):
    """A comparable fingerprint of a nested result: arrays by dtype, shape and SHA-256 of their bytes; wall-clock
    fields left out (the first before-proof, 07:13, differed only in res/solver/lle_layer/seconds: 62.5 vs 53.9)."""
    if isinstance(x, np.ndarray):
        if x.dtype == object:
            return {"dtype": "object", "values": json.dumps(x.tolist(), default=str)}
        return {"dtype": str(x.dtype), "shape": list(x.shape),
                "sha256": hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()}
    if isinstance(x, dict):
        return {str(k): digest(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0])) if str(k) not in TIMING}
    if isinstance(x, (list, tuple)):
        return [digest(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return repr(float(x))
    return str(x)


def gates_run(roots: dict | None) -> dict:
    """verify.py --gates with its outputs in a temporary folder; roots patch its OFF/ON sandbox roots in memory."""
    from src.eda.level_layer_adoption import verify as V
    saved = (V.CHECKS, V.SANDBOX)
    tmp = Path(tempfile.mkdtemp(prefix="lyr_gates_"))
    try:
        V.CHECKS = tmp
        V.SANDBOX = dict(saved[1], **(roots or {}))
        used = {k: str(V.SANDBOX[k]) for k in ("OFF", "ON")}
        t0 = time.time()
        out = V.gates()
        files = {f.name: sha256(f) for f in sorted(tmp.iterdir())}
    finally:
        V.CHECKS, V.SANDBOX = saved
    return {"roots": used, "pass": out["pass"], "files": files, "seconds": round(time.time() - t0, 1),
            "tmp": str(tmp)}


def solver_run(box: Path | None) -> dict:
    """solver_tolerance.py's ON solve (men's holds, pooled, the decided tolerance); box None: the module's own ON."""
    from src.eda.level_layer_adoption import solver_tolerance as ST
    from src.eda.lower_level_evidence import level_layer as L
    box = box or ST.BOXES["ON"]
    before = os.environ.get(L.ENV)
    try:
        r = ST.solve(box, None, "current")
    finally:
        if before is None:
            os.environ.pop(L.ENV, None)
        else:
            os.environ[L.ENV] = before
    return {"box": str(box), "seconds": r["seconds"], "td": digest(r["td"]), "res": digest(r["res"])}


def recorded_gates() -> dict:
    d = STUDIES / "level_layer_adoption" / "checks"
    return {n: sha256(d / n) for n in ("gates.json", "gates_G2.csv", "gates_G3.csv") if (d / n).exists()}


def unpriced_check() -> dict:
    meta = json.loads(UNPRICED.with_suffix(".json").read_text(encoding="utf-8"))
    code = UNPRICED_CODE.read_text(encoding="utf-8")
    m = re.search(r'"stageb_off":\s*\{[^}]*?"sha256":\s*"([0-9a-f]{64})"', code, re.S)
    pin = m.group(1) if m else None
    got = sha256(UNPRICED)
    ok = bool(pin and meta["source_sha256"] == pin and meta["extract_sha256"] == got)
    return {"extract": str(UNPRICED), "pin_in_code": pin, "record_source_sha256": meta["source_sha256"],
            "record_extract_sha256": meta["extract_sha256"], "extract_sha256_now": got,
            "reused_without_the_sandbox": ok}


def prove(stage: str) -> int:
    rec = load_record()
    res = {"at": now(), "stage": stage, "unpriced_leads": unpriced_check()}
    if stage == "before":
        res["gates_sandbox"] = gates_run({k: SANDBOX[k] for k in ("OFF", "ON")})
        res["gates_extract"] = gates_run({k: EXTRACT[k] for k in ("OFF", "ON")})
        res["solver_sandbox"] = solver_run(SANDBOX["ON"])
        res["solver_extract"] = solver_run(EXTRACT["ON"])
        res["gates_equal"] = res["gates_sandbox"]["files"] == res["gates_extract"]["files"]
        res["solver_equal"] = (res["solver_sandbox"]["td"] == res["solver_extract"]["td"]
                               and res["solver_sandbox"]["res"] == res["solver_extract"]["res"])
        res["gates_equal_to_10_oct_record"] = res["gates_sandbox"]["files"] == recorded_gates()
    else:
        ref = rec.get("proof_before")
        if not ref:
            raise SystemExit("run --prove --stage before first")
        from src.eda.level_layer_adoption import solver_tolerance as ST
        from src.eda.level_layer_adoption import verify as V
        res["module_roots"] = {"verify.SANDBOX": {k: str(V.SANDBOX[k]) for k in ("OFF", "ON")},
                               "solver_tolerance.BOXES": {k: str(v) for k, v in ST.BOXES.items()}}
        res["modules_point_at_extracts"] = (all(Path(V.SANDBOX[k]) == EXTRACT[k] for k in ("OFF", "ON"))
                                            and Path(ST.BOXES["ON"]) == EXTRACT["ON"])
        res["gates"] = gates_run(None)
        res["solver"] = solver_run(None)
        res["gates_equal"] = res["gates"]["files"] == ref["gates_sandbox"]["files"]
        res["solver_equal"] = (res["solver"]["td"] == ref["solver_sandbox"]["td"]
                               and res["solver"]["res"] == ref["solver_sandbox"]["res"])
        res["sandboxes_present"] = {k: v.exists() for k, v in SANDBOX.items()}
    keys = ["gates_equal", "solver_equal"] + (["modules_point_at_extracts"] if stage != "before" else [])
    res["pass"] = bool(all(res[k] for k in keys) and res["unpriced_leads"]["reused_without_the_sandbox"]
                       and (stage != "after" or not any(res["sandboxes_present"].values())))
    rec[f"proof_{stage}"] = res
    save_record(rec)
    show = {k: v for k, v in res.items() if not isinstance(v, dict) or k in ("unpriced_leads", "sandboxes_present",
                                                                              "module_roots")}
    print(json.dumps(show, indent=1, default=str))
    return 0 if res["pass"] else 1


# ------------------------------------------------------------------------------------------------
# --delete

def delete(dry: bool) -> int:
    rec = load_record()
    for k in ("proof_before", "proof_edited"):
        if not rec.get(k, {}).get("pass"):
            raise SystemExit(f"{k} has not passed: nothing deleted")
    plan = []
    for name, sb in SANDBOX.items():
        files, links, bad = D.walk(sb)
        plan.append({"sandbox": name, "path": str(sb), "exists": sb.exists(), "files": len(files),
                     "bytes": sum(s for _, s in files), "unreadable": bad[:3],
                     "links": [(str(x), D.target(x)) for x in links]})
    targets = sorted({t for p in plan for _, t in p["links"]})
    roots = list(PROTECTED) + [Path(t) for t in targets
                               if not any(t.lower().startswith(str(p).lower()) for p in PROTECTED)]
    for p in plan:
        print(f"{p['path']}: {p['files']:,} files, {p['bytes'] / 1e9:.2f} GB, links:")
        for x, t in p["links"]:
            print(f"    {Path(x).relative_to(p['path'])} -> {t}")
    print("kept trees listed:", *[str(r) for r in roots], sep="\n    ")
    if dry:
        return 0
    before = D.fingerprint(roots)
    out = []
    for p in plan:
        entry = dict(p)
        try:
            entry["result"] = D.remove_tree(Path(p["path"]))
            entry["deleted"] = True
        except Exception as e:
            entry["deleted"] = False
            entry["error"] = f"{type(e).__name__}: {e}"[:500]
        entry["kept_trees_lost_after"] = D.lost_files(before, D.fingerprint(roots))
        out.append(entry)
        print(f"{now()} {p['path']}: deleted {entry['deleted']}, kept trees lost "
              f"{sum(len(v) for v in entry['kept_trees_lost_after'].values())} files", flush=True)
        if entry["kept_trees_lost_after"]:
            break
    rec["delete"] = {"at": now(), "items": out, "kept_trees": {str(k): len(v) for k, v in before.items()},
                     "deleted_bytes": sum(e["bytes"] for e in out if e.get("deleted"))}
    save_record(rec)
    ok = all(e.get("deleted") and not e["kept_trees_lost_after"] for e in out) and len(out) == len(plan)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--extract", action="store_true")
    g.add_argument("--prove", action="store_true")
    g.add_argument("--delete", action="store_true")
    ap.add_argument("--stage", choices=("before", "edited", "after"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.extract:
        extract()
        return 0
    if a.prove:
        if not a.stage:
            ap.error("--prove needs --stage")
        return prove(a.stage)
    return delete(a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
