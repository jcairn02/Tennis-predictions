#!/usr/bin/env bash
# The current best model's frame built in a sandbox of its own, with (1) or without (0) the level layer
# (docs/decisions/2026-10-10-level-evidence-layer.md). Usage, from anywhere:
#   bash data/studies/level_layer_adoption/build_template.sh <sandbox> <out folder> <layer 0|1> [candidate stage0 folder
#                                                                                                 | accepted]
# "accepted": the template as decided, with every accepted lower-level package merged (current_best_model/additions.py).
# With a candidate Stage 0 folder (stage0_matches, stage0_match_players, timing.parquet), the sandbox is set up with
# --candidate, the candidate's tables are copied over the sandbox's, and lane 0 rebuilds what reads them (Stage 1's odds
# link and the leak-proof features; the candidate brings its own timeline), without the layer; the layer is then
# resolved on the candidate's Stage 0, and lane 1 rebuilds the IOS part with it before leakproof_frame.
set -u
SB="$1"; OUT="$2"; LAYER="$3"; CAND="${4:-}"
REPO=/c/Users/zerom/Documents/Tennis-predictions
cd "$REPO" || exit 1
export MODEL_REBUILD_SANDBOX="$SB" SURFACE_IOS_WORKERS="${SURFACE_IOS_WORKERS:-6}" MATCH_TIMING_WORKERS="${MATCH_TIMING_WORKERS:-3}"
unset LLE_LAYER
mkdir -p "$OUT"
RC="./python.sh src/eda/model_rebuild/run_chain.py"
FLAG=""
[ "$LAYER" = "1" ] && FLAG="--layer"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "$(stamp) setup $SB (layer $LAYER, candidate '${CAND}')"
if [ "$CAND" = "accepted" ]; then
  # the template as decided: the live tables plus every accepted lower-level package (run_chain.py --additions), lane 0
  # on the merged tables (its timeline step skipped: the packages bring their rows), then the layer
  $RC --setup || exit 1
  $RC --additions --out "$OUT" || exit 1
  $RC --lane 0 --out "$OUT" > "$OUT/lane0.out" 2>&1 || { echo "lane 0 failed"; exit 1; }
  if [ "$LAYER" = "1" ]; then $RC --prepare-layer --out "$OUT" || exit 1; fi
elif [ -n "$CAND" ]; then
  $RC --setup --candidate || exit 1
  for f in stage0_matches.parquet stage0_match_players.parquet; do
    cp "$CAND/$f" "$SB/data/studies/predictability_diagnostic/$f" || exit 1
  done
  cp "$CAND/timing.parquet" "$SB/data/studies/match_timing/timing.parquet" || exit 1
  echo "$(stamp) candidate tables in; lane 0 without its timeline step"
  # lane 0: Stage 1's odds link, then the full leak-proof rebuild, without the layer
  ./python.sh - "$SB" "$OUT" <<'EOF' || exit 1
import json, os, subprocess, sys, time
from pathlib import Path
sb, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, ".")
from src.eda.model_rebuild import run_chain as RC
env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
(sb / "logs").mkdir(exist_ok=True)
rec = {"sandbox": str(sb), "lane": "0", "lle_layer": None, "steps": []}
for name, script in [s for s in RC.LANES["0"] if s[0] != "timeline"]:
    t0 = time.time()
    path, *args = script.split()
    with (sb / "logs").joinpath(f"{name}.log").open("w", encoding="utf-8") as fh:
        done = subprocess.run([RC.PY, str(sb / path), *args], cwd=sb, stdout=fh, stderr=subprocess.STDOUT, env=env)
    rec["steps"].append({"step": name, "script": script, "exit": done.returncode, "seconds": round(time.time() - t0, 1)})
    (out / "chain_lane0.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(name, done.returncode, flush=True)
    if done.returncode:
        sys.exit(done.returncode)
EOF
  if [ "$LAYER" = "1" ]; then $RC --prepare-layer --out "$OUT" || exit 1; fi
else
  $RC --setup || exit 1
  if [ "$LAYER" = "1" ]; then $RC --prepare-layer --out "$OUT" || exit 1; fi
fi
echo "$(stamp) lanes 1 and 2"
$RC --lane 2 $FLAG --out "$OUT" > "$OUT/lane2.out" 2>&1 &
P2=$!
$RC --lane 1 $FLAG --out "$OUT" > "$OUT/lane1.out" 2>&1
C1=$?
wait $P2
C2=$?
echo "$(stamp) lane 1 exit $C1, lane 2 exit $C2"
[ $C1 -eq 0 ] && [ $C2 -eq 0 ] || exit 1
$RC --lane 3 $FLAG --out "$OUT" > "$OUT/lane3.out" 2>&1 || { echo "lane 3 failed"; exit 1; }
$RC --collect --out "$OUT" || exit 1
echo "$(stamp) DONE"
