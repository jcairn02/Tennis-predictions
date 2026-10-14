"""The state store (PLAN.md section 3.3): one checkpoint per instance and day.

    <STATE>/<instance_id>/<YYYY-MM-DD>/
        manifest.json         the day; per family and part (tour, pass, run) its slice hash and file; the constants'
                              hashes; the tree and tables it was made on; the code it was made with
        constants/<rel path>  the instance's constants files, copied from the tree the checkpoint was made on; a work
                              tree gets them installed before any family runs (the repository's copies of some of them
                              are older builds' and differ: process log, 20:25)
        elo/<tour>_offset.pkl, <tour>_stage3.pkl + <tour>_stage3_block.parquet, <tour>_weighted_<kind>.pkl
        ios/<tour>_<stat>.npz
        forms/z.parquet
The checkpoint covers everything before its day: the Elo passes' tournament weeks before it, the forms' box rows of those
weeks, the IOS snapshot days before it. A family part whose slice hash differs on today's tables is invalid; the daily
update then recomputes that part in full (tier 2 for that part) and says so.

STATE defaults to data/studies/daily_prediction/state/ (outside git: its own .gitignore). PLAN.md recommends
data/state/<instance_id>/; where states live is the owner's open decision 4 (DP_STATE overrides).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import dp_common as DC

PDR = "data/studies/predictability_diagnostic"
CONSTANT_FILES = [f"{PDR}/stage1_baselines_summary.json", f"{PDR}/stage3_ratings_summary.json",
                  f"{PDR}/stage4_constants.csv", f"{PDR}/stage3_shrinkage.csv", f"{PDR}/stage3_results.json",
                  f"{PDR}/stage4_candidates.csv", f"{PDR}/stage2_pbp_players.parquet",
                  "data/studies/surface_elo_pieces/pieces_meta.json", "data/studies/ios_constants/active.json"]


class InvalidCheckpoint(Exception):
    pass


def root(instance_id: str = DC.INSTANCE_ID) -> Path:
    r = DC.STATE / instance_id
    r.mkdir(parents=True, exist_ok=True)
    gi = DC.STATE / ".gitignore"
    if not gi.exists():
        gi.write_text("# checkpoints of the daily prediction script: large, rebuilt from the tables\n*\n!.gitignore\n",
                      encoding="utf-8")
    return r


def folder(day: str, instance_id: str = DC.INSTANCE_ID) -> Path:
    return root(instance_id) / day


def checkpoints(instance_id: str = DC.INSTANCE_ID) -> list[Path]:
    """Complete checkpoints (with a manifest), newest day first."""
    r = root(instance_id)
    return sorted((p for p in r.iterdir() if (p / "manifest.json").exists()), key=lambda p: p.name, reverse=True)


def latest_on_or_before(day: int, instance_id: str = DC.INSTANCE_ID) -> list[Path]:
    """Checkpoints whose day is on or before `day` (days since 1970), newest first: the fallback ladder."""
    return [p for p in checkpoints(instance_id) if DC.day_of(p.name) <= day]


def ios_constants_files(tree: Path) -> list[str]:
    active = json.loads((Path(tree) / "data/studies/ios_constants/active.json").read_text(encoding="utf-8"))
    vid = active.get("active") or active.get("id") or active.get("version")
    return [f"data/studies/ios_constants/versions/{vid}.json"] if vid else []


def copy_constants(tree: Path, ck: Path) -> dict:
    out = {}
    for rel in CONSTANT_FILES + ios_constants_files(tree):
        src = Path(tree) / rel
        dst = ck / "constants" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        out[rel] = DC.sha256(dst)
    return out


def check_constants(ck: Path, tree: Path, manifest: dict) -> dict:
    """The tree's copies against the checkpoint's: {rel: equal}."""
    return {rel: (Path(tree) / rel).exists() and DC.sha256(Path(tree) / rel) == sha
            for rel, sha in manifest["constants_files"].items()}


def install_constants(ck: Path, tree: Path, manifest: dict) -> dict:
    """The checkpoint's constants files copied into a work tree (never a tree only read). Returns what was replaced."""
    if not (Path(tree) / ".prediction_run_sandbox").exists():
        raise SystemExit(f"{tree} is not a work tree: constants are installed only into a sandbox")
    replaced = {}
    for rel, sha in manifest["constants_files"].items():
        dst = Path(tree) / rel
        before = DC.sha256(dst) if dst.exists() else None
        if before != sha:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ck / "constants" / rel, dst)
            replaced[rel] = {"before": before, "after": sha}
    return replaced


def write_manifest(ck: Path, manifest: dict) -> None:
    DC.write_json(ck / "manifest.json", manifest)


def read_manifest(ck: Path) -> dict:
    return DC.read_json(ck / "manifest.json")


def code_hashes() -> dict:
    """The script's own modules and the prototypes it imports (the builders' code is the tree's: recorded by tree)."""
    files = sorted(DC.HERE.glob("dp*.py")) + [DC.PROTOTYPES / f for f in ("ios_state.py", "forms_state.py",
                                                                           "elo_state.py")]
    return {f.name: DC.sha256(f) for f in files if f.exists()}
