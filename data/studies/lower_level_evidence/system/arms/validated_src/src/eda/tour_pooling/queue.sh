#!/usr/bin/env bash
# The tour-pooling study's fits, one arm per runner, each started only when no tennis-tabpfn-local process runs
# (src/eda/bet_timing/run_when_free.sh), so other studies' runners can take the card between arms.
# Usage: bash src/eda/tour_pooling/queue.sh split notour borrow50 ...   (log: data/studies/tour_pooling/fits.log)
cd "$(dirname "$0")/../../.." || exit 1
mkdir -p data/studies/tour_pooling
for arm in "$@"; do
  echo "[$(date -u +%FT%TZ)] queue: $arm" >> data/studies/tour_pooling/fits.log
  bash src/eda/bet_timing/run_when_free.sh src/eda/tour_pooling/fits.py --arm "$arm" --seeds 0-3 --seasons 2019-2026 \
    >> data/studies/tour_pooling/fits.log 2>&1 || echo "[$(date -u +%FT%TZ)] queue: $arm FAILED" >> data/studies/tour_pooling/fits.log
done
echo "[$(date -u +%FT%TZ)] queue: done ($*)" >> data/studies/tour_pooling/fits.log
