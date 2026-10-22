#!/usr/bin/env bash
# The TennisExplorer pull for the missing Pinnacle closes (docs/research/pinnacle-gap/). Launched detached (Git Bash -l),
# it logs to data/studies/pinnacle_gap/pull.log. Phases, each resumable (pages on disk are not fetched again):
#   1. the calendars of 2025-26 and the tour-level event pages from January 2025
#   2. the gap: every finished main-draw match page from 1 Aug 2025 to today, newest first; staged and linked
#   3. the overlap: January - July 2025 (Pinnacle's own closes are on disk there: the check); staged and linked
# A block (exit 2 from the adapter) stops the job: back off and report (docs/decisions/2026-10-08-scraping-approved.md).
set -u
cd "$(dirname "$0")/../../.."
LOG=data/studies/pinnacle_gap/pull.log
FRAME=${FRAME:-data/studies/current_best_model/template_2026-10-21b/model_frame.parquet}
PAUSE=${PAUSE:-2.5}
mkdir -p data/studies/pinnacle_gap
step() {
  echo "$(date -u +%FT%TZ) START $*" >> "$LOG"
  ./python.sh -m src.ingest.tennisexplorer "$@" --pause "$PAUSE" >> "$LOG" 2>&1
  rc=$?
  echo "$(date -u +%FT%TZ) END rc=$rc $*" >> "$LOG"
  if [ $rc -ne 0 ]; then echo "$(date -u +%FT%TZ) JOB STOPPED (rc=$rc)" >> "$LOG"; exit $rc; fi
}
echo "$(date -u +%FT%TZ) JOB START frame=$FRAME pause=$PAUSE" >> "$LOG"
step --calendar 2025 2026
step --events --since 2025-01-01
step --matches --since 2025-08-01
step --stage --link "$FRAME" --since 2025-08-01
step --matches --since 2025-01-01 --until 2025-07-31
step --stage --link "$FRAME" --since 2025-01-01
echo "$(date -u +%FT%TZ) JOB DONE" >> "$LOG"
