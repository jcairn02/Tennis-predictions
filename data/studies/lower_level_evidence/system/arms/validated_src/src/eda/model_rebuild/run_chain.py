"""Build the current best model's inputs on the current tables, in a sandbox copy of the repository.

The current best model is a TEMPLATE (docs/decisions/2026-10-08-current-best-model.md): the recipe below, built on the
tables of the day when a task needs it. This driver builds its 58-input frame. Its first run (8 Oct 2026) built the frame
of the model_rebuild study (docs/studies/model_rebuild/README.md).

Why a sandbox. Every builder of the chain writes into its own study's folder, which holds earlier models' evidence, and
none takes an output folder. So the chain runs unchanged in a copy of the repository (SANDBOX, a short path: Windows'
260-character limit): its own copy of src/, docs/ (Stage 4 hashes its plan there) and data/studies/, the root config
files, and links (junctions) to the read-only data/dump/ and data/raw/. Each builder resolves its paths from its own
location, so everything it reads and writes is the sandbox's.

The chain, the builders of the 58 inputs in their documented order:
    lane 1   Stage 1 (Elo baselines; its constants re-tuned on 2013-2018), Stage 3 (serve and return ratings:
             ratings_iid), Stage 4 (games Elo, points over 52 weeks, workload, age); the ufc_ideas Stages A and C (no input
             reads them, but Stage D's rundown requires every stage on the same matches; Stage A reads its tuning grids
             back, --reuse-grid), Stage B (opponent-adjusted form and points, IOS points; its IOS tuning re-runs on the
             day's tables, but the inputs read the IOS constants registry, so the next step only reports what that
             re-tune would change: src/eda/ios_constants/registry.py --check) and Stage D (the inputs' tables);
             the base frame (tabpfn_thinking), the leak-proof IOS swap (tabpfn_leakproof); the offset Elo
             (surface_elo_pieces: pieces, which reproduces Stage 1 and re-tunes K on 2013-2018, and the frame)
    lane 2   the surface IOS solver runs (surface_ios: cache and full runs); independent of lane 1, run beside it
    lane 3   after both: the surface IOS frames and arms, then the model frame (surface_rating_race/model_frame.py, whose
             checks tie every input to its source)
Not rebuilt (no input reads them): Stage 2, rating_systems.

Before it: Stage 0, Stage 1's odds and the match timeline on the day's data (src/eda/data_continuity/rebuild_stage0.py
builds all three, with the decided overrides and corrections).

The training history (the owner, 8 Oct 2026; the decision's amendment). The template trains on the frozen reference's
history plus the matches played since, from the feeds that fed it; new lower-level data (Challenger, ITF), even of past
dates, never enters it by itself. --setup therefore checks the live Stage 0 against the reference's
(src/eda/current_best_model/history.py) and refuses when its history differs. A build meant to test new data is made
with --setup --candidate (its own --out folder) and compared with the reference (src/eda/current_best_model/compare.py).
    lane 0   a candidate only, after its new data is put into the sandbox's Stage 0: rebuild_stage0.py's steps after
             the build (Stage 1's odds link, the timeline, the leak-proof IOS and features), so that lanes 1-3 read
             tables in line with the candidate's Stage 0. A template build never needs it. Not yet exercised

Commands (the out folder holds the records; default data/studies/model_rebuild):
    --setup              create the sandbox from the repository (fails if it exists)
    --lane {0,1,2,3}     run a lane; --from <step> resumes; each step's log is SANDBOX/logs/<step>.log and its exit code
                         and seconds go to <out>/chain_lane<lane>.json
    --collect            copy the model frame, its input list, the builders' manifests and the logs to <out>
    --cleanup            remove the links first (rmdir: the link only, never its target), check none is left, delete the
                         sandbox
Run: ./python.sh src/eda/model_rebuild/run_chain.py --setup | --lane 1 | --lane 2 | --lane 3 | --collect | --cleanup
     [--out data/studies/current_best_model/<date>]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SANDBOX = Path(os.environ.get("MODEL_REBUILD_SANDBOX", "C:/Users/zerom/tnr_sb"))
PY = "C:/Users/zerom/miniforge3/envs/tennis/python.exe"
OUT = ROOT / "data" / "studies" / "model_rebuild"
LINKED = ("dump", "raw")                       # data/ folders the sandbox links to, read only

LANES = {
    "0": [("stage1_odds", "src/eda/predictability_diagnostic/stage1_odds.py"),           # a candidate's Stage 0 only
          ("timeline", "src/eda/match_timing/refresh.py --skip-ios"),
          ("timing_features", "src/eda/match_timing/rebuild.py")],
    "1": [("stage1_baselines", "src/eda/predictability_diagnostic/stage1_baselines.py"),
          ("stage3_ratings", "src/eda/predictability_diagnostic/stage3_ratings.py"),
          ("stage4_features", "src/eda/predictability_diagnostic/stage4_features.py"),
          ("ufc_stageA_ratings", "src/eda/ufc_ideas/stageA_ratings.py --reuse-grid"),
          ("ufc_stageA_features", "src/eda/ufc_ideas/stageA_features.py"),
          ("ufc_stageC_fatigue", "src/eda/ufc_ideas/stageC_fatigue.py"),
          ("ufc_stageC_sos", "src/eda/ufc_ideas/stageC_sos.py"),
          ("ufc_stageC_rundown", "src/eda/ufc_ideas/stageC_rundown.py"),
          ("ufc_stageB_adjperf", "src/eda/ufc_ideas/stageB_adjperf.py"),
          ("ufc_stageB_ios", "src/eda/ufc_ideas/stageB_ios.py"),
          ("ios_constants_check", "src/eda/ios_constants/registry.py --check"),          # informational: exit 0
          ("ufc_stageB_split", "src/eda/ufc_ideas/stageB_split.py"),
          ("ufc_stageB_rundown", "src/eda/ufc_ideas/stageB_rundown.py"),
          ("ufc_stageD_profile", "src/eda/ufc_ideas/stageD_profile.py"),
          ("ufc_stageD_rundown", "src/eda/ufc_ideas/stageD_rundown.py"),
          ("thinking_frame", "src/eda/tabpfn_thinking/build_frame.py"),
          ("leakproof_frame", "src/eda/tabpfn_leakproof/build_frame.py"),
          ("elo_pieces", "src/eda/surface_elo_pieces/pieces.py"),
          ("elo_frames", "src/eda/surface_elo_pieces/build_frames.py")],
    "2": [("surface_ios_cache", "src/eda/surface_ios/build_cache.py"),
          ("surface_ios_features", "src/eda/surface_ios/build_features.py")],
    "3": [("surface_ios_frames", "src/eda/surface_ios/frames.py"),
          ("surface_ios_arms", "src/eda/surface_ios/arms.py"),
          ("model_frame", "src/eda/surface_rating_race/model_frame.py")],
}
COLLECT = {  # sandbox path -> name in <out>
    "data/studies/surface_rating_race/model/model_frame.parquet": "model_frame.parquet",
    "data/studies/surface_rating_race/model/model_inputs.json": "model_inputs.json",
    "data/studies/tabpfn_thinking/manifest.json": "chain_outputs/tabpfn_thinking_manifest.json",
    "data/studies/tabpfn_leakproof/manifest.json": "chain_outputs/tabpfn_leakproof_manifest.json",
    "data/studies/surface_elo_pieces/pieces_meta.json": "chain_outputs/surface_elo_pieces_pieces_meta.json",
    "data/studies/surface_elo_pieces/frame_manifest.json": "chain_outputs/surface_elo_pieces_frame_manifest.json",
    "data/studies/predictability_diagnostic/stage1_baselines_summary.json": "chain_outputs/stage1_baselines_summary.json",
}


def robocopy(src: Path, dst: Path, exclude_dirs: tuple[str, ...] = ()) -> None:
    cmd = ["robocopy", str(src), str(dst), "/E", "/MT:16", "/NFL", "/NDL", "/NJH", "/NP", "/R:0", "/W:0"]
    if exclude_dirs:
        cmd += ["/XD", *exclude_dirs]
    if subprocess.run(cmd).returncode >= 8:                 # robocopy: 0-7 success, 8+ failures
        raise SystemExit(f"robocopy {src} failed")


def links() -> list[str]:
    ps = (f"Get-ChildItem -Path '{SANDBOX}' -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue | "
          "ForEach-Object { $_.FullName }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return [x for x in out.splitlines() if x.strip()]


def history_gate(candidate: bool) -> None:
    """A template build keeps the frozen reference's history plus later matches (history.py); a candidate may differ."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.eda.current_best_model import history as H
    res = H.check()
    print(H.summary_line(res), flush=True)
    if not res["template_ok"] and not candidate:
        raise SystemExit("the training history differs from the frozen reference (./python.sh src/eda/current_best_model/"
                         "history.py lists how). A template build keeps the reference's history plus later matches; to "
                         "test new data, use --setup --candidate with its own --out and compare it "
                         "(src/eda/current_best_model/compare.py)")


def setup(candidate: bool = False) -> None:
    if SANDBOX.exists():
        raise SystemExit(f"{SANDBOX} exists; --cleanup it first")
    history_gate(candidate)
    (SANDBOX / "data").mkdir(parents=True)
    robocopy(ROOT / "src", SANDBOX / "src", ("__pycache__",))
    robocopy(ROOT / "docs", SANDBOX / "docs")
    robocopy(ROOT / "data" / "studies", SANDBOX / "data" / "studies", ("full_runs", "pytest_*", "__pycache__"))
    for f in list(ROOT.glob("*.json")) + list(ROOT.glob("*.yml")):
        shutil.copy2(f, SANDBOX / f.name)
    for name in LINKED:
        subprocess.run(["cmd", "/c", "mklink", "/J", str(SANDBOX / "data" / name), str(ROOT / "data" / name)], check=True)
    print(f"sandbox ready at {SANDBOX}")


def cleanup() -> None:
    if not SANDBOX.exists():
        print("no sandbox")
        return
    for name in LINKED:
        p = SANDBOX / "data" / name
        if p.exists():
            subprocess.run(["cmd", "/c", "rmdir", str(p)], check=True)    # a junction: removes the link only
    left = links()
    if left:
        raise SystemExit(f"links left in the sandbox, nothing deleted: {left[:5]}")
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(SANDBOX)], check=True)
    print(f"deleted {SANDBOX}: {not SANDBOX.exists()}")


def collect(out: Path) -> None:
    for src, name in COLLECT.items():
        dst = out / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SANDBOX / src, dst)
    logs = out / "chain_logs"
    logs.mkdir(parents=True, exist_ok=True)
    for f in (SANDBOX / "logs").glob("*.log"):
        shutil.copy2(f, logs / f.name)
    print(f"collected into {out}")


def run_lane(lane: str, start: str | None, out: Path) -> int:
    if not (SANDBOX / "src").is_dir() or not (SANDBOX / "data" / "studies").is_dir():
        raise SystemExit(f"no sandbox at {SANDBOX}: run --setup")
    if SANDBOX.resolve() == ROOT.resolve():
        raise SystemExit("the sandbox must not be the repository")
    steps = LANES[lane]
    if start:
        names = [s for s, _ in steps]
        steps = steps[names.index(start):]
    (SANDBOX / "logs").mkdir(exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    record_path = out / f"chain_lane{lane}.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {"steps": []}
    record.update({"sandbox": str(SANDBOX), "lane": lane})
    for name, script in steps:
        t0 = time.time()
        log = SANDBOX / "logs" / f"{name}.log"
        print(f"--> {name}: {script}", flush=True)
        with log.open("w", encoding="utf-8") as fh:
            path, *args = script.split()
            done = subprocess.run([PY, str(SANDBOX / path), *args], cwd=SANDBOX, stdout=fh, stderr=subprocess.STDOUT,
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        row = {"step": name, "script": script, "exit": done.returncode, "seconds": round(time.time() - t0, 1),
               "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "log": str(log)}
        record["steps"].append(row)
        record_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
        print(f"    exit {done.returncode} in {row['seconds']} s", flush=True)
        if done.returncode != 0:
            print(log.read_text(encoding="utf-8", errors="replace")[-3000:])
            return done.returncode
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--setup", action="store_true")
    which.add_argument("--lane", choices=sorted(LANES))
    which.add_argument("--collect", action="store_true")
    which.add_argument("--cleanup", action="store_true")
    ap.add_argument("--from", dest="start", default=None, help="resume a lane at this step")
    ap.add_argument("--out", default=str(OUT), help="the records' folder (default data/studies/model_rebuild)")
    ap.add_argument("--candidate", action="store_true",
                    help="with --setup: a build whose training history may differ from the frozen reference (new data "
                         "under test); compare it with the reference before anything is accepted")
    a = ap.parse_args()
    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    if a.setup:
        setup(a.candidate)
    elif a.cleanup:
        cleanup()
    elif a.collect:
        collect(out)
    else:
        return run_lane(a.lane, a.start, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
