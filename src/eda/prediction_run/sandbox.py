"""The prediction run's sandbox: a copy of the repository the model's chain builds in, never the repository itself.

Like src/eda/model_rebuild/run_chain.py's sandbox (whose lanes it runs), but its own (common.SANDBOX), so a template
build and a prediction run never share one, and marked (common.MARKER) as the one place Stage 0 accepts live rows.
It copies src/, docs/, data/studies/ (without full runs, test folders, the frozen reference, which is read-only and read
by nothing in the chain, and the prediction runs' own records) and the root files, and links (junctions) the read-only
data/dump/ and data/raw/. Every builder resolves its paths from its own location, so everything it reads and writes is
the sandbox's.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from src.eda.prediction_run import common as P

LINKED = ("dump", "raw")
EXCLUDE = ("full_runs", "pytest_*", "__pycache__", "current_best_model", "prediction_run")


def robocopy(src: Path, dst: Path, exclude_dirs: tuple[str, ...] = ()) -> None:
    cmd = ["robocopy", str(src), str(dst), "/E", "/MT:16", "/NFL", "/NDL", "/NJH", "/NP", "/R:0", "/W:0"]
    if exclude_dirs:
        cmd += ["/XD", *exclude_dirs]
    if subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode >= 8:      # robocopy: 0-7 success, 8+ failures
        raise SystemExit(f"robocopy {src} failed")


def setup() -> None:
    """Create the sandbox (refused if it exists: clean it up first)."""
    box = P.SANDBOX
    if box.exists():
        raise SystemExit(f"{box} exists; clean it up first (run.py --cleanup)")
    if box.resolve() == P.ROOT.resolve():
        raise SystemExit("the sandbox must not be the repository")
    t0 = time.time()
    (box / "data").mkdir(parents=True)
    robocopy(P.ROOT / "src", box / "src", ("__pycache__",))
    robocopy(P.ROOT / "docs", box / "docs")
    robocopy(P.ROOT / "data" / "studies", box / "data" / "studies", EXCLUDE)
    for f in list(P.ROOT.glob("*.json")) + list(P.ROOT.glob("*.yml")):
        shutil.copy2(f, box / f.name)
    for name in LINKED:
        subprocess.run(["cmd", "/c", "mklink", "/J", str(box / "data" / name), str(P.ROOT / "data" / name)],
                       check=True, stdout=subprocess.DEVNULL)
    (box / P.MARKER).write_text(json.dumps({"created_at": P.stamp(), "repository": str(P.ROOT)}), encoding="utf-8")
    P.log(f"sandbox ready at {box} in {time.time() - t0:.0f} s")


def refresh_code() -> None:
    """Copy src/ again (code changed since setup)."""
    robocopy(P.ROOT / "src", P.SANDBOX / "src", ("__pycache__",))


def links() -> list[str]:
    ps = (f"Get-ChildItem -Path '{P.SANDBOX}' -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue "
          "| ForEach-Object { $_.FullName }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return [x for x in out.splitlines() if x.strip()]


def cleanup() -> None:
    """Remove the links first (rmdir: the link only, never its target), check none is left, then delete the sandbox."""
    box = P.SANDBOX
    if not box.exists():
        P.log("no sandbox")
        return
    if not (box / P.MARKER).exists():
        raise SystemExit(f"{box} is not a prediction run's sandbox (no {P.MARKER}); nothing deleted")
    for name in LINKED:
        link = box / "data" / name
        if link.exists():
            subprocess.run(["cmd", "/c", "rmdir", str(link)], check=True)
    left = links()
    if left:
        raise SystemExit(f"links left in the sandbox, nothing deleted: {left[:5]}")
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(box)], check=True)
    P.log(f"deleted {box}: {not box.exists()}")


def run(name: str, script: str, *args: str, record: list | None = None) -> int:
    """Run one of the sandbox's scripts with the tennis environment's Python, its output in SANDBOX/logs/<name>.log."""
    box = P.SANDBOX
    if not (box / P.MARKER).exists():
        raise SystemExit(f"no sandbox at {box}: run.py --setup")
    (box / "logs").mkdir(exist_ok=True)
    log = box / "logs" / f"{name}.log"
    t0 = time.time()
    P.log(f"--> {name}: {script} {' '.join(args)}")
    with log.open("w", encoding="utf-8") as fh:
        done = subprocess.run([str(P.PY), str(box / script), *args], cwd=box, stdout=fh, stderr=subprocess.STDOUT,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    row = {"step": name, "script": script, "args": list(args), "exit": done.returncode,
           "seconds": round(time.time() - t0, 1), "finished_at": P.stamp(), "log": str(log)}
    if record is not None:
        record.append(row)
    P.log(f"    exit {done.returncode} in {row['seconds']} s")
    if done.returncode != 0:
        print(log.read_text(encoding="utf-8", errors="replace")[-3000:])
    return done.returncode
