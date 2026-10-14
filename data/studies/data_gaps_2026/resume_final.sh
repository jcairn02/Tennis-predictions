#!/usr/bin/env bash
# Resume the final build (build_final.sh) after its lane 1 was stopped at elo_pieces when the session that ran it ended
# (14 Oct 2026, 00:30 PDT, exit 0x4000013A: the console closed). Lane 1 from elo_pieces, lane 3, collect, then
# build_final.sh's remaining steps (post_build.sh, the fits in the switch's order). Launched in a window of its own so a
# session's end does not stop it.
# Usage, from the repository root: bash data/studies/data_gaps_2026/resume_final.sh [<sandbox> [<out folder>]]
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
SB="${1:-C:/Users/zerom/tnr_tpl1014}"
OUT="${2:-data/studies/current_best_model/template_2026-10-14}"
cd "$REPO" || exit 1
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
export MODEL_REBUILD_SANDBOX="$SB" SURFACE_IOS_WORKERS="${SURFACE_IOS_WORKERS:-8}" MATCH_TIMING_WORKERS="${MATCH_TIMING_WORKERS:-3}"
export RUN_CHAIN_SKIP_DIRS=daily_prediction
unset LLE_LAYER
RC="./python.sh src/eda/model_rebuild/run_chain.py"
FITS="./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out $OUT"
L="$OUT/build_final.log"
echo "$(stamp) resume: lane 1 from elo_pieces" >> "$L"
$RC --lane 1 --from elo_pieces --layer --out "$OUT" >> "$OUT/lane1.out" 2>&1 || { echo "$(stamp) lane 1 failed" >> "$L"; exit 1; }
echo "$(stamp) lane 1 exit 0 (resumed)" >> "$OUT/build.out"
$RC --lane 3 --layer --out "$OUT" > "$OUT/lane3.out" 2>&1 || { echo "$(stamp) lane 3 failed" >> "$L"; exit 1; }
$RC --collect --out "$OUT" >> "$OUT/build.out" 2>&1 || { echo "$(stamp) collect failed" >> "$L"; exit 1; }
echo "$(stamp) DONE (build)" >> "$OUT/build.out"
echo "$(stamp) post-build" >> "$L"
bash data/studies/level_layer_adoption/post_build.sh "$OUT" > "$OUT/post_build.out" 2>&1 || { echo "$(stamp) post-build failed" >> "$L"; exit 1; }
echo "$(stamp) fits: seeds 0-3, 2019-2026" >> "$L"
$FITS --seeds 0-3 --seasons 2019-2026 > "$OUT/fits.log" 2>&1 || { echo "$(stamp) fits failed" >> "$L"; exit 1; }
echo "$(stamp) fits: seeds 4-15, 2026" >> "$L"
$FITS --seeds 4-15 --seasons 2026 > "$OUT/fits_seeds4-15_2026.log" 2>&1 || { echo "$(stamp) fits failed" >> "$L"; exit 1; }
echo "$(stamp) READY FOR THE SWITCH" >> "$L"
$FITS --seeds 4-15 --seasons 2019-2025 > "$OUT/fits_seeds4-15_2019-2025.log" 2>&1 || { echo "$(stamp) fits (other seasons) failed" >> "$L"; exit 1; }
echo "$(stamp) DONE" >> "$L"
