#!/usr/bin/env bash
# Start a local-TabPFN runner of this study only when no process of the `tennis-tabpfn-local` env is running.
# Other sessions' runners (training_window.fits.wait_for_card) wait while ANY process of that env exists, so a runner of
# ours that waited inside the env would block them and they it (seen 8 Oct 2026). The waiting happens here instead, in a
# plain shell, polling every 60 s; the runner itself then waits for free card memory only.
# Usage: bash src/eda/bet_timing/run_when_free.sh <script.py> [args...]
cd "$(dirname "$0")/../../.." || exit 1
count() {
  powershell.exe -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*tennis-tabpfn-local*' }).Count" | tr -d '\r'
}
while true; do
  n=$(count)
  if [ "$n" = "0" ]; then
    break
  fi
  echo "[$(date -u +%FT%TZ)] waiting: $n local-env process(es) running"
  sleep 60
done
echo "[$(date -u +%FT%TZ)] no local-env process running; starting $*"
exec ./python_tabpfn_local.sh "$@"
