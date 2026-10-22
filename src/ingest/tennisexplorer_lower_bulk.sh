#!/usr/bin/env bash
# Work package P11's bulk download (src/ingest/tennisexplorer_lower.py), rerun after each budget stop.
#
# Each run asks at most BUDGET requests (default 20,000, about a day at 2.5 s plus up to 1 s and the site's answer)
# and goes day by day from yesterday back to SINCE, newest first; days already done are skipped without a request. The
# loop goes on after a budget stop (exit 3) and, after a 10-minute pause, after a run the tour-level adapter crowded out
# (exit 4); it stops when the span is done (0), on a block (2) or anything else (1), and after MAX_RUNS runs. Each run is
# staged (--stage-only, no request: only the months whose pages changed are rebuilt).
#
# Started detached so that it outlives the Claude Code session that starts it, from PowerShell:
#   Start-Process -WindowStyle Hidden -FilePath "C:\Program Files\Git\bin\bash.exe" -ArgumentList '-l','-c','"/c/Users/zerom/Documents/Tennis-predictions/src/ingest/tennisexplorer_lower_bulk.sh"'
# Its own log: data/raw/tennisexplorer_lower/_logs/bulk.log; each run's: _logs/run_<UTC stamp>.log.
set -u
cd "$(dirname "$0")/../.." || exit 9
ENV=/c/Users/zerom/miniforge3/envs/tennis
export PATH="$ENV:$ENV/Library/mingw-w64/bin:$ENV/Library/usr/bin:$ENV/Library/bin:$ENV/Scripts:$ENV/bin:$PATH"
LOGS=data/raw/tennisexplorer_lower/_logs
mkdir -p "$LOGS"
BUDGET=${BUDGET:-20000}
MAX_RUNS=${MAX_RUNS:-40}
SINCE=${SINCE:-2018-01-01}
note() { echo "[bulk $(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOGS/bulk.log"; }
note "started (pid $$; since $SINCE; budget $BUDGET a run, at most $MAX_RUNS runs; args: $*)"
code=1
for i in $(seq 1 "$MAX_RUNS"); do
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  log="$LOGS/run_${stamp}.log"
  ./python.sh -m src.ingest.tennisexplorer_lower --since "$SINCE" --max-requests "$BUDGET" --no-stage "$@" > "$log" 2>&1
  code=$?
  echo "exit $code" >> "$log"
  note "run $i ($log) ended with exit $code"
  ./python.sh -m src.ingest.tennisexplorer_lower --stage-only > "$LOGS/stage_${stamp}.log" 2>&1
  note "staging ended with exit $?"
  case "$code" in
    3) continue ;;
    4) sleep 600; continue ;;
    *) break ;;
  esac
done
note "finished (last run's exit $code)"
