#!/usr/bin/env bash
# Work package P9's bulk download (src/ingest/point_sources/infosys_atp_recent.py), rerun after each budget stop.
#
# Each run asks at most BUDGET requests (default 30,000, about a day at 2 s plus up to 1 s) and resumes where the
# receipts end. The loop goes on after a budget stop (exit 3), and once after a finished plan with some error answers
# (exit 5), which that run asks again; it stops on a finished plan (0), a second exit 5 in a row (answers the host keeps
# failing, such as the API's HTTP 500 for a match without a file), a block or a streak without documents (2), another
# collector on the host (4) or anything else (1), and after MAX_RUNS runs. Waiting for the daily speed job and
# prediction runs is the collector's own (HostShare). When the plan is done (exit 0, or 5 twice), the files are staged
# (--stage-only, no request) and checked.
#
# Started detached (WMI Win32_Process.Create of Git Bash) so that it outlives the Claude Code session that starts it:
#   & "C:\Program Files\Git\bin\bash.exe" -lc "/c/Users/zerom/Documents/Tennis-predictions/src/ingest/point_sources/infosys_atp_recent_bulk.sh"
# Its own log: data/raw/point_sources/infosys_atp_recent/_logs/bulk.log; each run's: _logs/bulk_<UTC stamp>.log.
set -u
cd "$(dirname "$0")/../../.." || exit 9
ENV=/c/Users/zerom/miniforge3/envs/tennis
export PATH="$ENV:$ENV/Library/mingw-w64/bin:$ENV/Library/usr/bin:$ENV/Library/bin:$ENV/Scripts:$ENV/bin:$PATH"
LOGS=data/raw/point_sources/infosys_atp_recent/_logs
mkdir -p "$LOGS"
BUDGET=${BUDGET:-30000}
MAX_RUNS=${MAX_RUNS:-6}
note() { echo "[bulk $(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOGS/bulk.log"; }
note "started (pid $$; budget $BUDGET a run, at most $MAX_RUNS runs; args: $*)"
code=1
errors_runs=0
for i in $(seq 1 "$MAX_RUNS"); do
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  log="$LOGS/bulk_${stamp}.log"
  ./python.sh -m src.ingest.point_sources.infosys_atp_recent --max-requests "$BUDGET" --no-stage "$@" > "$log" 2>&1
  code=$?
  echo "exit $code" >> "$log"
  note "run $i ($log) ended with exit $code"
  case "$code" in
    3) errors_runs=0; continue ;;
    5) errors_runs=$((errors_runs + 1)); [ "$errors_runs" -ge 2 ] && break; continue ;;
    *) break ;;
  esac
done
if [ "$code" = "0" ] || [ "$code" = "5" ]; then
  note "the plan is done: staging"
  ./python.sh -m src.ingest.point_sources.infosys_atp_recent --stage-only > "$LOGS/stage_$(date -u +%Y%m%dT%H%M%SZ).log" 2>&1
  note "staging ended with exit $?: checks"
  ./python.sh src/eda/serve_speed_acquisition/infosys_atp_recent_checks.py > "$LOGS/checks_$(date -u +%Y%m%dT%H%M%SZ).log" 2>&1
  note "checks ended with exit $?"
fi
note "finished (last run's exit $code)"
