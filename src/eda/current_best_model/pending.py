"""Revisions decided for the current best model that reach its training rows only at a retrain (the owner, 22 Oct 2026:
"Ensure that when we implement the next re-train either through the master script or via another LLM agent, that it's
aware of these intended revisions to the model, not simply adding the latest data").

The register, data/studies/current_best_model/pending_at_retrain.json, lists each revision: its decision, what it
changes, how a build takes it, and its checks. A check is a command run with the project's Python on a Stage 0 folder
(check_stage0) or on a built instance and the Stage 0 it was built from (check_instance); it exits 0 only when the
revision is there. A revision stays "pending" until a retrain's instance holding it becomes the one in use.

    --show                                      the register's pending revisions
    --check [--stage0 <folder>]                 every pending revision's Stage 0 check (default: the shared tables).
                                                tp.retrain() runs it before a retrain starts and refuses to start when
                                                one fails: a retrain on tables without them would only add the latest
                                                data
    --check --stage0 <folder> --instance <dir>  every pending revision's instance check; with --write, the result into
                                                <dir>/revisions_at_build.json (retrain.sh, before the fits)
    --mark-applied <instance name>              after a retrain's switch: each pending revision its instance holds
                                                (revisions_at_build.json) becomes "applied", with the instance and time
Exit 0 when every check passes (or nothing is pending), 1 otherwise.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTER = ROOT / "data" / "studies" / "current_best_model" / "pending_at_retrain.json"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic"
INSTANCES = ROOT / "data" / "studies" / "current_best_model"
AT_BUILD = "revisions_at_build.json"


def register(path: Path = REGISTER) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {"revisions": []}


def pending(path: Path = REGISTER) -> list[dict]:
    return [r for r in register(path).get("revisions", []) if r.get("status") == "pending"]


def _run(cmd: list[str], stage0: Path, instance: Path | None) -> dict:
    args = [str(stage0) if a == "{stage0}" else str(instance) if a == "{instance}" else a for a in cmd]
    done = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                          env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    return {"command": args, "exit": done.returncode, "ok": done.returncode == 0,
            "tail": (done.stdout + done.stderr).strip().splitlines()[-3:]}


def check(stage0: Path = STAGE0, instance: Path | None = None, path: Path = REGISTER) -> dict:
    """Each pending revision's check on a Stage 0 folder (and an instance): {id: result}, and ok overall."""
    out: dict = {"stage0": str(stage0), "instance": str(instance) if instance else None, "revisions": {},
                 "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    for r in pending(path):
        cmd = r["check_instance"] if instance is not None else r["check_stage0"]
        res = _run(cmd, Path(stage0), instance)
        res.update({"decision": r["decision"], "what": r["what"]})
        out["revisions"][r["id"]] = res
    out["ok"] = all(v["ok"] for v in out["revisions"].values())
    return out


def mark_applied(instance: str, path: Path = REGISTER) -> list[str]:
    """Mark the pending revisions the instance holds (its revisions_at_build.json, every check passed) applied."""
    rec_path = INSTANCES / instance / AT_BUILD
    if not rec_path.exists():
        raise SystemExit(f"{rec_path}: the instance has no record of the revisions at its build")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    held = {k for k, v in rec.get("revisions", {}).items() if v.get("ok")}
    reg = register(path)
    done = []
    for r in reg.get("revisions", []):
        if r.get("status") == "pending" and r["id"] in held:
            r.update(status="applied", applied_in=instance,
                     applied_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
            done.append(r["id"])
    Path(path).write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return done


def lines(res: dict | None = None) -> list[str]:
    """The pending revisions, one line each, for the retrain's plan."""
    out = []
    for r in pending():
        status = "" if res is None else (" [in the tables]" if res["revisions"][r["id"]]["ok"] else
                                         " [NOT in the tables]")
        out.append(f"{r['id']} ({r['decision']}){status}")
        out += [f"    - {w}" for w in r["what"]]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--show", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--mark-applied", metavar="INSTANCE")
    ap.add_argument("--stage0", default=str(STAGE0))
    ap.add_argument("--instance", default=None)
    ap.add_argument("--write", action="store_true", help="--check --instance: write <instance>/revisions_at_build.json")
    a = ap.parse_args()
    if a.show:
        print("\n".join(lines()) or "no revision pending at the next retrain")
        return 0
    if a.mark_applied:
        print({"applied": mark_applied(a.mark_applied)})
        return 0
    stage0 = Path(a.stage0) if Path(a.stage0).is_absolute() else ROOT / a.stage0
    inst = (Path(a.instance) if Path(a.instance).is_absolute() else ROOT / a.instance) if a.instance else None
    res = check(stage0, inst)
    if a.write:
        if inst is None:
            raise SystemExit("--write needs --instance")
        (inst / AT_BUILD).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "revisions"}
                     | {"revisions": {k: {x: v[x] for x in ("ok", "exit", "tail")} for k, v in res["revisions"].items()}},
                     indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
