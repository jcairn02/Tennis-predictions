"""Stage 0 built twice on the same inputs with two versions of its builders: every output compared byte for byte
(docs/studies/daily_prediction/process_log.md, part 3: the owner's go-ahead of 11 Oct 2026 to speed up
stage0_build.py and feature_alpha_audit/repair_data.py, "with proof that the new Stage 0 is byte-identical").

In a sandbox work tree (dp_worktree; replay mode holds Tennis My Life at the freeze), stage0_build.py runs as the
pipeline runs it (the tree's own script and code, in the tree), in two variants:
    default   no arguments: the repository's and the template's build (the decided overrides and corrections)
    live      --live-rows run/live_rows.parquet: the daily pipeline's (a replay's live rows)
Each build's six outputs are copied to data/studies/daily_prediction/stage0_speed/<tag>_<variant>/ with their
SHA-256 and the builders' own SHA-256. compare: every file byte for byte; stage0_summary.json also without its
"generated_at" line (the build's clock), and field by field, so any other difference is named. The summary holds
every input file's SHA-256 (stage0_build.input_record), so equal summaries also show the two builds read the same
inputs.
Run (the repository's Python):
    dp_stage0_equiv.py build --tree C:/Users/zerom/tnr_s0eq --tag old --variant default
    dp_stage0_equiv.py compare --a old --b new --variant default
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dp_common as DC  # noqa: E402

OUTPUTS = ("stage0_matches.parquet", "stage0_match_players.parquet", "stage0_cleaning_log.csv",
           "stage0_level_applied.csv", "stage0_cells.csv", "stage0_summary.json")
CODE = ("src/eda/predictability_diagnostic/stage0_build.py", "src/eda/feature_alpha_audit/repair_data.py")
VARIANTS = {"default": [], "live": ["--live-rows", "run/live_rows.parquet"]}
EQ = DC.OUT / "stage0_speed"


def build(tree: Path, tag: str, variant: str) -> dict:
    tree = Path(tree)
    dst = EQ / f"{tag}_{variant}"
    if dst.exists():
        raise SystemExit(f"{dst} exists: another --tag")
    t0 = time.time()
    done = subprocess.run([str(DC.PY), str(tree / CODE[0]), *VARIANTS[variant]], cwd=tree, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
    secs = time.time() - t0
    if done.returncode:
        raise SystemExit(f"stage0_build failed:\n{done.stdout[-3000:]}\n{done.stderr[-3000:]}")
    dst.mkdir(parents=True)
    rec = {"tree": str(tree), "tag": tag, "variant": variant, "args": VARIANTS[variant], "seconds": round(secs, 1),
           "built_at": DC.stamp(), "code": {rel: DC.sha256(tree / rel) for rel in CODE}, "files": {}}
    for f in OUTPUTS:
        shutil.copy2(tree / DC.PD / f, dst / f)
        rec["files"][f] = DC.sha256(dst / f)
    (dst / "build.log").write_text(done.stdout + done.stderr, encoding="utf-8")
    DC.write_json(dst / "record.json", rec)
    return rec


def _without_clock(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith('"generated_at":'))


def _diff_paths(a, b, path: str = "") -> list[str]:
    """Where two JSON values differ (first 20 paths)."""
    if type(a) is not type(b):
        return [path or "/"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            out += [f"{path}/{k}"] if (k not in a or k not in b) else _diff_paths(a[k], b[k], f"{path}/{k}")
        return out[:20]
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path} (lengths {len(a)}, {len(b)})"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += _diff_paths(x, y, f"{path}[{i}]")
        return out[:20]
    return [] if a == b else [path or "/"]


def compare(a: str, b: str, variant: str) -> dict:
    da, db = EQ / f"{a}_{variant}", EQ / f"{b}_{variant}"
    ra, rb = DC.read_json(da / "record.json"), DC.read_json(db / "record.json")
    out: dict = {"variant": variant, "a": a, "b": b, "seconds": {a: ra["seconds"], b: rb["seconds"]},
                 "code_differs": {rel: ra["code"][rel] != rb["code"][rel] for rel in CODE}, "files": {}}
    for f in OUTPUTS:
        out["files"][f] = "byte-identical" if ra["files"][f] == rb["files"][f] else "different"
    ta = (da / "stage0_summary.json").read_text(encoding="utf-8")
    tb = (db / "stage0_summary.json").read_text(encoding="utf-8")
    out["summary_byte_identical_but_generated_at"] = _without_clock(ta) == _without_clock(tb)
    ja, jb = json.loads(ta), json.loads(tb)
    out["generated_at"] = {a: ja.pop("generated_at", None), b: jb.pop("generated_at", None)}
    out["summary_fields_differing_but_generated_at"] = _diff_paths(ja, jb)
    out["inputs_identical"] = ja.get("inputs") == jb.get("inputs")
    out["identical"] = (all(v == "byte-identical" for f, v in out["files"].items() if f != "stage0_summary.json")
                        and out["summary_byte_identical_but_generated_at"])
    DC.write_json(EQ / f"compare_{a}_{b}_{variant}.json", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("build", "compare"))
    ap.add_argument("--tree", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--variant", required=True, choices=sorted(VARIANTS))
    ap.add_argument("--a", default=None)
    ap.add_argument("--b", default=None)
    x = ap.parse_args()
    res = build(Path(x.tree), x.tag, x.variant) if x.cmd == "build" else compare(x.a, x.b, x.variant)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
