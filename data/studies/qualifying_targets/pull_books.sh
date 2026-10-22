#!/usr/bin/env bash
# The every-book pull of the qualifying events (qualifying_targets step 2), detached. Log: pull_books.log beside it.
cd /c/Users/zerom/Documents/Tennis-predictions || exit 1
L=data/studies/qualifying_targets/pull_books.log
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) start" >> "$L"
./python.sh -m src.ingest.oddstrader --books-eids data/studies/qualifying_targets/oddstrader_eids.csv --max-requests 800 >> "$L" 2>&1
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) exit $?" >> "$L"
