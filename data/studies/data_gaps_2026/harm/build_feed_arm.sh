#!/usr/bin/env bash
# The lower-level feed's harm check, arm FEED (docs/studies/data_gaps_2026/process_log.md, § 3 addendum of 13 Oct 2026):
# the template recipe on the frozen reference's tables plus the feed's first snapshot's additions (its derived candidate),
# built as the 10 Oct candidate was (data/studies/level_layer_adoption/build_template.sh <sandbox> <out> 1 <candidate>),
# then post_build.sh (Pinnacle-first odds, the 57-input list), the fits (seeds 0-3, 2019-2026), the gate and the scorer.
# Usage, from the repository root: bash data/studies/data_gaps_2026/harm/build_feed_arm.sh <derived candidate folder>
set -u
CAND="$1"
REPO=/c/Users/zerom/Documents/Tennis-predictions
SB=C:/Users/zerom/tnr_gaps
OUT=data/studies/data_gaps_2026/harm/feed_instance
cd "$REPO" || exit 1
mkdir -p "$OUT"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
export RUN_CHAIN_SKIP_DIRS=daily_prediction     # the daily engine's 55 GB of TabPFN caches: no chain step reads them
export SURFACE_IOS_WORKERS="${SURFACE_IOS_WORKERS:-8}"   # 6 by default; 16 threads here, the machine nearly idle
echo "$(stamp) build: $CAND"
bash data/studies/level_layer_adoption/build_template.sh "$SB" "$OUT" 1 "$CAND" > "$OUT/build.out" 2>&1 || { echo "$(stamp) build failed"; exit 1; }
echo "$(stamp) post-build"
bash data/studies/level_layer_adoption/post_build.sh "$OUT" > "$OUT/post_build.out" 2>&1 || { echo "$(stamp) post-build failed"; exit 1; }
echo "$(stamp) fits (seeds 0-3, 2019-2026)"
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out "$OUT" --seeds 0-3 --seasons 2019-2026 > "$OUT/fits.log" 2>&1 || { echo "$(stamp) fits failed"; exit 1; }
echo "$(stamp) gate"
./python.sh src/eda/data_gaps_2026/harm.py --feed "$OUT" --gate "$CAND" > "$OUT/gate.out" 2>&1
G=$?
echo "$(stamp) gate exit $G (0 = pass)"
echo "$(stamp) DONE (the scorer is run separately, after the gate is read)"
