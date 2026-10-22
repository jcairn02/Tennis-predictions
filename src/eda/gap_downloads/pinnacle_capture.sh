#!/usr/bin/env bash
# Work package P11's forward-capture test, route (A): Pinnacle's tennis listing every EVERY seconds for HOURS hours
# (src/eda/gap_downloads/pinnacle_capture.py). Launched detached (Git Bash -l); logs to data/raw/pinnacle_capture/_logs/.
# A refusal ends the loop (exit 2): back off and report (docs/decisions/2026-10-08-scraping-approved.md).
set -u
cd "$(dirname "$0")/../../.."
EVERY=${EVERY:-600}
HOURS=${HOURS:-36}
mkdir -p data/raw/pinnacle_capture/_logs
LOG=data/raw/pinnacle_capture/_logs/capture_$(date -u +%Y%m%dT%H%M%SZ).log
echo "$(date -u +%FT%TZ) START every=$EVERY hours=$HOURS" >> "$LOG"
./python.sh src/eda/gap_downloads/pinnacle_capture.py --every "$EVERY" --hours "$HOURS" >> "$LOG" 2>&1
echo "$(date -u +%FT%TZ) END rc=$?" >> "$LOG"
