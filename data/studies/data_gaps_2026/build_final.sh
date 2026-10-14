#!/usr/bin/env bash
# The template on the day's tables once the lower-level feed is adopted and the Roland Garros repair applied
# (docs/studies/data_gaps_2026/process_log.md, § 3 addendum 2, steps 5-6, 13 Oct 2026): build_template.sh's accepted
# route (the live tables, then every accepted package and the feed merged into the sandbox's own), post_build.sh, and
# the fits in the order the switch needs them: seeds 0-3 for 2019-2026 (stage 2 reads them), seeds 4-15 for the current
# season (the template check), then the other seasons' seeds 4-15.
# Usage, from the repository root: bash data/studies/data_gaps_2026/build_final.sh [<sandbox> [<out folder>]]
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
SB="${1:-C:/Users/zerom/tnr_tpl1014}"
OUT="${2:-data/studies/current_best_model/template_2026-10-14}"
cd "$REPO" || exit 1
mkdir -p "$OUT"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
export RUN_CHAIN_SKIP_DIRS=daily_prediction     # the daily engine's TabPFN caches: no chain step reads them
export SURFACE_IOS_WORKERS="${SURFACE_IOS_WORKERS:-8}"
FITS="./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out $OUT"
echo "$(stamp) build (accepted route) in $SB"
bash data/studies/level_layer_adoption/build_template.sh "$SB" "$OUT" 1 accepted > "$OUT/build.out" 2>&1 || { echo "$(stamp) build failed"; exit 1; }
echo "$(stamp) post-build"
bash data/studies/level_layer_adoption/post_build.sh "$OUT" > "$OUT/post_build.out" 2>&1 || { echo "$(stamp) post-build failed"; exit 1; }
echo "$(stamp) fits: seeds 0-3, 2019-2026"
$FITS --seeds 0-3 --seasons 2019-2026 > "$OUT/fits.log" 2>&1 || { echo "$(stamp) fits failed"; exit 1; }
echo "$(stamp) fits: seeds 4-15, 2026"
$FITS --seeds 4-15 --seasons 2026 > "$OUT/fits_seeds4-15_2026.log" 2>&1 || { echo "$(stamp) fits failed"; exit 1; }
echo "$(stamp) READY FOR THE SWITCH"
$FITS --seeds 4-15 --seasons 2019-2025 > "$OUT/fits_seeds4-15_2019-2025.log" 2>&1 || { echo "$(stamp) fits (other seasons) failed"; exit 1; }
echo "$(stamp) DONE"
