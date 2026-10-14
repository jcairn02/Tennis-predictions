"""The run's work tree: a sandbox copy of the repository in which today's tables are built, never the repository.

As prediction_run/sandbox.py makes its sandbox (the same copies and exclusions, and its marker, the only licence
Stage 0 accepts for live rows), at its own path (DP_WORK_TREE, default C:/Users/zerom/tnr_daily), so a prediction run,
a template build and this script never share one. Copied: src/, docs/, data/studies/ (without full solver runs, test
folders, the frozen reference, the prediction runs' and this script's own records) and the root config files; linked
(junctions, read only): data/dump/ and data/raw/. Every builder resolves its paths from its own location, so all it
reads and writes is the work tree's.

A replay (--replay) holds Tennis My Life's staged dump at the freeze of 8 Oct 2026 18:53 UTC (the instance's tables):
data/dump/ is a folder of junctions with matches/tennis_my_life pointing at the frozen view
(level_layer_adoption/freeze_dump.py wrote it; Stage 0 built on it equals the frozen Stage 0 byte for byte), as the
10 Oct layer replay's sandbox did by hand.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import dp_common as DC

MARKER = ".prediction_run_sandbox"                  # prediction_run/common.MARKER: stage0_build's licence for live rows
EXCLUDE = ("full_runs", "pytest_*", "__pycache__", "current_best_model", "prediction_run", "daily_prediction")
LINKED = ("dump", "raw")


def robocopy(src: Path, dst: Path, exclude_dirs: tuple[str, ...] = ()) -> None:
    cmd = ["robocopy", str(src), str(dst), "/E", "/MT:16", "/NFL", "/NDL", "/NJH", "/NP", "/R:0", "/W:0"]
    if exclude_dirs:
        cmd += ["/XD", *exclude_dirs]
    if subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode >= 8:      # robocopy: 0-7 success, 8+ failures
        raise SystemExit(f"robocopy {src} failed")


def junction(link: Path, target: Path) -> None:
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, stdout=subprocess.DEVNULL)


def links(box: Path) -> list[str]:
    ps = (f"Get-ChildItem -Path '{box}' -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue "
          "| ForEach-Object { $_.FullName }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return [x for x in out.splitlines() if x.strip()]


def setup(box: Path = DC.WORK_TREE, replay: bool = False, freeze: Path = DC.FREEZE_DUMP, owner: str = "") -> dict:
    """A fresh work tree (refused if one exists: clean it up first). owner (a run's folder) is written into the marker:
    run_day deletes a tree only when it names that run (owner_of)."""
    box = Path(box)
    if box.exists():
        raise SystemExit(f"{box} exists; clean it up first (dp.py cleanup)")
    if box.resolve() == DC.REPO.resolve():
        raise SystemExit("the work tree must not be the repository")
    t0 = time.time()
    (box / "data").mkdir(parents=True)
    robocopy(DC.REPO / "src", box / "src", ("__pycache__",))
    robocopy(DC.REPO / "docs", box / "docs")
    robocopy(DC.REPO / "data" / "studies", box / "data" / "studies", EXCLUDE)
    for f in list(DC.REPO.glob("*.json")) + list(DC.REPO.glob("*.yml")):
        shutil.copy2(f, box / f.name)
    junction(box / "data" / "raw", DC.REPO / "data" / "raw")
    if not replay:
        junction(box / "data" / "dump", DC.REPO / "data" / "dump")
    else:
        tml = Path(freeze) / "matches" / "tennis_my_life"
        if not tml.is_dir():
            raise SystemExit(f"{tml}: no frozen Tennis My Life view (level_layer_adoption/freeze_dump.py writes it)")
        dump = box / "data" / "dump"
        (dump / "matches").mkdir(parents=True)
        for child in (DC.REPO / "data" / "dump").iterdir():
            if child.is_dir() and child.name != "matches":
                junction(dump / child.name, child)
        for child in (DC.REPO / "data" / "dump" / "matches").iterdir():
            if child.is_dir():
                junction(dump / "matches" / child.name, tml if child.name == "tennis_my_life" else child)
    (box / MARKER).write_text(json.dumps({"created_at": DC.stamp(), "repository": str(DC.REPO), "replay": replay,
                                          "by": "daily_prediction/dp_worktree.py", "owner": owner}), encoding="utf-8")
    return {"work_tree": str(box), "replay": replay, "seconds": round(time.time() - t0, 1)}


def owner_of(box: Path) -> str | None:
    """The run named in a work tree's marker (setup's owner); None without a readable marker."""
    try:
        return json.loads((Path(box) / MARKER).read_text(encoding="utf-8")).get("owner") or None
    except (OSError, ValueError):
        return None


def cleanup(box: Path = DC.WORK_TREE) -> dict:
    """Remove the junctions first (rmdir: the link only, never its target), check none is left, delete the tree."""
    box = Path(box)
    if not box.exists():
        return {"deleted": False, "why": "no work tree"}
    if not (box / MARKER).exists():
        raise SystemExit(f"{box} is not a work tree (no {MARKER}); nothing deleted")
    t0 = time.time()
    for link in sorted(links(box), key=len, reverse=True):
        subprocess.run(["cmd", "/c", "rmdir", link], check=True)
    left = links(box)
    if left:
        raise SystemExit(f"links left in the work tree, nothing deleted: {left[:5]}")
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(box)], check=True)
    return {"deleted": not box.exists(), "seconds": round(time.time() - t0, 1)}


def run(box: Path, name: str, script: str, args: list[str], env: dict | None = None, record: list | None = None,
        python: Path = DC.PY) -> int:
    """One of the work tree's scripts, with the tennis environment's Python, its output in <box>/logs/<name>.log."""
    import os
    (box / "logs").mkdir(exist_ok=True)
    log = box / "logs" / f"{name}.log"
    t0 = time.time()
    DC.log(f"--> {name}: {script} {' '.join(args)}")
    with log.open("w", encoding="utf-8") as fh:
        done = subprocess.run([str(python), str(box / script), *args], cwd=box, stdout=fh, stderr=subprocess.STDOUT,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8", **(env or {})})
    row = {"step": name, "script": script, "args": list(args), "exit": done.returncode,
           "seconds": round(time.time() - t0, 1), "log": str(log)}
    if record is not None:
        record.append(row)
    DC.log(f"    exit {done.returncode} in {row['seconds']} s")
    if done.returncode != 0:
        print(log.read_text(encoding="utf-8", errors="replace")[-3000:])
    return done.returncode
