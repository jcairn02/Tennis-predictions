"""Running the project's steps from the notebook: one subprocess per step, in the step's own environment.

Every step
    * runs from the repository root, with the interpreter of its environment (config.interpreter);
    * streams its output into the notebook cell and into a log file, logs/<YYYY-MM-DD>/<HHMMSS>_<step>.log;
    * leaves one receipt line in data/studies/master_pipeline/runs.jsonl (command, times, exit code, log);
    * can be a dry run: the command is printed and recorded, nothing is executed;
    * stops its whole process tree when the cell is interrupted (Ctrl-C / the stop button), and says so.

A failed step raises StepFailed with the end of its output, so a cell never carries on past a failure unnoticed.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from . import config as CFG

TAIL_LINES = 40
RUNNING = CFG.OUT / "running"          # one marker per step while its process lives (status() lists them)


@dataclass
class Step:
    """One command: a name, its arguments after the interpreter, and its environment."""
    name: str
    args: Sequence[str | Path]
    env: str = "tennis"
    ok_codes: tuple[int, ...] = (0,)
    extra_env: dict = field(default_factory=dict)
    note: str = ""

    def command(self) -> list[str]:
        return [str(CFG.interpreter(self.env)), *[str(a) for a in self.args]]

    def shown(self) -> str:
        shim = {"tennis": "./python.sh", "local": "./python_tabpfn_local.sh", "api": "./python_tabpfn.sh"}[self.env]
        prefix = " ".join(f"{k}={v}" for k, v in self.extra_env.items())
        return (prefix + " " if prefix else "") + shim + " " + " ".join(shlex.quote(str(a)) for a in self.args)


@dataclass
class StepResult:
    name: str
    command: str
    status: str                 # ok | failed | dry-run | interrupted | timeout
    returncode: int | None
    seconds: float
    log: str | None
    tail: list[str] = field(default_factory=list, repr=False)

    @property
    def ok(self) -> bool:
        return self.status in ("ok", "dry-run")

    def __str__(self) -> str:
        where = f"  log: {self.log}" if self.log else ""
        return f"[{self.status}] {self.name} ({self.seconds:.0f} s, exit {self.returncode}){where}"


class StepFailed(RuntimeError):
    def __init__(self, result: StepResult):
        self.result = result
        tail = "\n".join(result.tail[-TAIL_LINES:])
        super().__init__(f"step {result.name!r} {result.status} (exit {result.returncode}); log: {result.log}\n"
                         f"--- last lines ---\n{tail}")


def _now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def _receipt(result: StepResult, step: Step, started: dt.datetime, dry_run: bool) -> None:
    CFG.OUT.mkdir(parents=True, exist_ok=True)
    rec = {"step": step.name, "command": step.shown(), "env": step.env, "started": started.isoformat(timespec="seconds"),
           "seconds": round(result.seconds, 1), "status": result.status, "returncode": result.returncode,
           "log": result.log, "dry_run": dry_run, "note": step.note, "env_set": dict(step.extra_env),
           "env_not_inherited": scrubbed_now()}
    with open(CFG.RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


# Variables that silently change what the project's steps build or read (the daily pipeline's tree, state and instance;
# the level layer; the rebuild's sandbox). A step gets them only when it sets them itself (Step.extra_env), so a value
# left in the notebook's environment can never switch a run to another model, instance or tree (review D2, item 2).
SCRUBBED_PREFIXES = ("DP_", "LLE_", "MODEL_REBUILD_")


def _child_env(step: Step) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(SCRUBBED_PREFIXES)}
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["MPLBACKEND"] = "Agg"         # the kernel's inline backend does not exist in the other environments
    env.update({k: str(v) for k, v in step.extra_env.items()})
    return env


def scrubbed_now() -> list[str]:
    """The project variables set in this kernel that steps will NOT inherit."""
    return sorted(k for k in os.environ if k.startswith(SCRUBBED_PREFIXES))


def _kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


def _log_path(name: str, started: dt.datetime) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)[:80]
    folder = CFG.LOGS / started.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{started.strftime('%H%M%S')}_{safe}.log"


class _Running:
    """A started step. The child writes straight into its log file (not into a pipe the kernel reads), so it keeps
    running if the kernel or VS Code dies (review V1: a piped child died at its next print); the cell follows the file."""

    def __init__(self, step: Step, prefix: str = ""):
        self.step = step
        self.prefix = prefix
        self.started = _now()
        self.t0 = time.monotonic()
        self.log_path = _log_path(step.name, self.started)
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"# {step.shown()}\n# started {self.started.isoformat(timespec='seconds')}\n")
        self.tail: list[str] = []
        self._partial = ""
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        with open(self.log_path, "ab") as out:
            self.proc = subprocess.Popen(step.command(), cwd=CFG.ROOT, env=_child_env(step), stdout=out,
                                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags)
        self._reader = open(self.log_path, "r", encoding="utf-8", errors="replace")
        self._reader.readline()
        self._reader.readline()                      # past the two header lines
        self.marker = RUNNING / f"{self.proc.pid}.json"
        RUNNING.mkdir(parents=True, exist_ok=True)
        self.marker.write_text(json.dumps({"step": step.name, "pid": self.proc.pid, "command": step.shown(),
                                           "log": CFG.rel(self.log_path),
                                           "started": self.started.isoformat(timespec="seconds")}), encoding="utf-8")

    def drain(self, echo: bool) -> bool:
        """Show the log's new complete lines. True once the process has exited and its output is all read."""
        exited = self.proc.poll() is not None
        chunk = self._reader.read()
        if chunk:
            text = self._partial + chunk
            lines = text.split("\n")
            self._partial = lines.pop()
            for line in lines:
                line = line.rstrip("\r")
                self.tail.append(line)
                if len(self.tail) > 400:
                    del self.tail[:200]
                if echo:
                    print(self.prefix + line, flush=True)
        if exited and not chunk:
            if self._partial:
                self.tail.append(self._partial)
                if echo:
                    print(self.prefix + self._partial, flush=True)
                self._partial = ""
            return True
        return False

    def finish(self, status: str, returncode: int | None) -> StepResult:
        seconds = time.monotonic() - self.t0
        self._reader.close()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"\n# {status}, exit {returncode}, {seconds:.1f} s\n")
        if status != "interrupted" or self.proc.poll() is not None:
            self.marker.unlink(missing_ok=True)
        res = StepResult(self.step.name, self.step.shown(), status, returncode, seconds, CFG.rel(self.log_path),
                         self.tail[-TAIL_LINES:])
        _receipt(res, self.step, self.started, False)
        return res


def run_step(step: Step, *, dry_run: bool = False, check: bool = True, timeout: float | None = None,
             echo: bool = True) -> StepResult:
    """Run one step to its end. echo=False keeps the cell quiet (a line a minute, then the last lines)."""
    if dry_run:
        print(f"DRY RUN  {step.name}:  {step.shown()}")
        res = StepResult(step.name, step.shown(), "dry-run", None, 0.0, None)
        _receipt(res, step, _now(), True)
        return res
    print(f">>> {step.name}:  {step.shown()}", flush=True)
    run = _Running(step)
    last_beat = time.monotonic()
    try:
        while True:
            ended = run.drain(echo)
            if ended and run.proc.poll() is not None:
                break
            if timeout is not None and time.monotonic() - run.t0 > timeout:
                _kill_tree(run.proc)
                run.drain(echo)
                res = run.finish("timeout", run.proc.poll())
                if check:
                    raise StepFailed(res)
                return res
            if not echo and time.monotonic() - last_beat > 60:
                print(f"    ... {step.name} running, {time.monotonic() - run.t0:.0f} s", flush=True)
                last_beat = time.monotonic()
            time.sleep(0.1)
    except KeyboardInterrupt:
        _kill_tree(run.proc)
        run.drain(echo)
        res = run.finish("interrupted", run.proc.poll())
        print(f"!!! {step.name} interrupted: its processes were stopped. Log: {res.log}", flush=True)
        raise
    code = run.proc.wait()
    status = "ok" if code in step.ok_codes else "failed"
    res = run.finish(status, code)
    if not echo:
        print("\n".join(res.tail[-15:]))
    print(str(res), flush=True)
    if status != "ok" and check:
        raise StepFailed(res)
    return res


def run_parallel(steps: Iterable[Step], *, dry_run: bool = False, check: bool = True,
                 echo: bool = True) -> list[StepResult]:
    """Run steps side by side (e.g. the chain's lanes 1 and 2); each line is prefixed with its step's name."""
    steps = list(steps)
    if dry_run:
        return [run_step(s, dry_run=True) for s in steps]
    for s in steps:
        print(f">>> {s.name} (in parallel):  {s.shown()}", flush=True)
    runs = [_Running(s, prefix=f"[{s.name}] ") for s in steps]
    done: dict[int, StepResult] = {}
    try:
        while len(done) < len(runs):
            for i, r in enumerate(runs):
                if i in done:
                    continue
                ended = r.drain(echo)
                if ended and r.proc.poll() is not None:
                    code = r.proc.wait()
                    done[i] = r.finish("ok" if code in r.step.ok_codes else "failed", code)
                    print(str(done[i]), flush=True)
                    if not done[i].ok and check:            # one failed: the others' work is wasted, stop them
                        for j, other in enumerate(runs):
                            if j not in done:
                                _kill_tree(other.proc)
                                other.drain(echo)
                                done[j] = other.finish("interrupted", other.proc.poll())
                                print(f"!!! {other.step.name} stopped: {r.step.name} failed", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        for i, r in enumerate(runs):
            if i not in done:
                _kill_tree(r.proc)
                r.drain(echo)
                done[i] = r.finish("interrupted", r.proc.poll())
        print("!!! interrupted: every parallel step was stopped.", flush=True)
        raise
    results = [done[i] for i in range(len(runs))]
    bad = [r for r in results if not r.ok]
    if bad and check:
        raise StepFailed(bad[0])
    return results


def run_steps(steps: Iterable[Step], *, dry_run: bool = False, check: bool = True, echo: bool = True) -> list[StepResult]:
    """Run steps one after another; stops at the first failure (check=True)."""
    return [run_step(s, dry_run=dry_run, check=check, echo=echo) for s in steps]


def running() -> list[dict]:
    """Steps started from a notebook whose process is still alive. A step outlives its kernel (its output goes to its
    log file, which keeps growing), e.g. a build left running when VS Code closed. Markers of processes that are gone
    are removed."""
    import psutil
    out = []
    for m in sorted(RUNNING.glob("*.json")) if RUNNING.exists() else []:
        try:
            rec = json.loads(m.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if psutil.pid_exists(int(rec["pid"])):
            out.append(rec)
        else:
            m.unlink(missing_ok=True)
    return out


def receipts(last: int = 20) -> list[dict]:
    """The latest receipts (most recent last)."""
    if not CFG.RECEIPTS.exists():
        return []
    lines = CFG.RECEIPTS.read_text(encoding="utf-8").splitlines()
    return [json.loads(x) for x in lines[-last:] if x.strip()]


def as_dict(result: StepResult) -> dict:
    return asdict(result)
