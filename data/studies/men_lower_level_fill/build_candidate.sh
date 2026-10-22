#!/usr/bin/env bash
# The men's lower-level fill (docs/studies/men_lower_level_fill/, 16 Oct 2026), plan step 1: the candidate MLF20261016
# with the level-evidence builder against the frozen reference, the sources of men's matches (the two WTA sources left
# out), the feed's box sources and exclusions (data_gaps_2026/feed.py), then its checks.
# Usage, from the repository root: bash data/studies/men_lower_level_fill/build_candidate.sh
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
cd "$REPO" || exit 1
B=src/eda/lower_level_evidence/candidate_stage0.py
P=C:/Users/zerom/tnr_mlf/candidates
L=MLF20261016
OUT=data/studies/men_lower_level_fill
S="--status-log $OUT/status.log"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "$(stamp) build $L"
./python.sh $B --label $L --out $P/$L --sources tennislive,itf_live,sofascore,tennislive_pages,tdi \
  --box-sources wta_api,itf_live,tdi,tennislive_pages --box-exclude tennislive_pages:ITF,tennislive_pages:ITFQ $S \
  > $OUT/build_$L.log 2>&1 || { echo "$(stamp) build failed"; exit 1; }
echo "$(stamp) checks $L"
./python.sh $B --label $L --out $P/$L --checks $S > $OUT/checks_$L.log 2>&1 || { echo "$(stamp) checks failed"; exit 1; }
echo "$(stamp) DONE"
