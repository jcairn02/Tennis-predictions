#!/usr/bin/env bash
# Resume the rebuild of 16 Oct 2026 (build_template.sh) after lane 1 stopped in stage4_features' leak probe (22:21Z:
# OverflowError in weighted_elo_pass, a redrawn outcome's weight of several hundred; the exponent now capped, the
# patched file copied into the sandbox: docs/studies/men_lower_level_fill/process_log.md). Lane 2 had finished (exit 0).
# Lane 1 from stage4_features, lane 3, collect (the remaining steps of level_layer_adoption/build_template.sh's
# accepted route), then build_template.sh with SKIP_BUILD=1: post-build, fits, the harm check, the switch, the fits.
# Usage, from the repository root: bash data/studies/men_lower_level_fill/resume_build.sh
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
SB=C:/Users/zerom/tnr_tpl1016
OUT=data/studies/current_best_model/template_2026-10-16
cd "$REPO" || exit 1
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
export MODEL_REBUILD_SANDBOX="$SB" SURFACE_IOS_WORKERS="${SURFACE_IOS_WORKERS:-6}" MATCH_TIMING_WORKERS="${MATCH_TIMING_WORKERS:-3}"
export RUN_CHAIN_SKIP_DIRS=daily_prediction
unset LLE_LAYER
RC="./python.sh src/eda/model_rebuild/run_chain.py"
echo "$(stamp) resume: lane 1 from stage4_features" | tee -a "$OUT/build.out"
$RC --lane 1 --from stage4_features --layer --out "$OUT" >> "$OUT/lane1.out" 2>&1 || { echo "$(stamp) lane 1 failed (resumed)"; exit 1; }
echo "$(stamp) lane 1 exit 0 (resumed)" | tee -a "$OUT/build.out"
$RC --lane 3 --layer --out "$OUT" > "$OUT/lane3.out" 2>&1 || { echo "$(stamp) lane 3 failed"; exit 1; }
$RC --collect --out "$OUT" >> "$OUT/build.out" 2>&1 || { echo "$(stamp) collect failed"; exit 1; }
echo "$(stamp) DONE (build, resumed)" | tee -a "$OUT/build.out"
SKIP_BUILD=1 bash data/studies/men_lower_level_fill/build_template.sh "$SB" "$OUT"
