#!/usr/bin/env bash
# Start this study's local TabPFN runner only when no other process of the `tennis-tabpfn-local` env is alive (the
# card's sharing rule: other sessions' runners wait while ANY other local-env process exists, so two runners started
# side by side would wait for each other). Poll, then start.
# Usage: bash src/eda/pair_strength/launch_when_free.sh --seasons 2014-2024 --seeds 0-2
cd "$(dirname "$0")/../../.." || exit 1
while true; do
  n=$(powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*tennis-tabpfn-local*' } | Measure-Object).Count" | tr -d '\r')
  if [ "$n" = "0" ]; then break; fi
  echo "[$(date +%H:%M:%S)] $n local-env process(es) running; waiting"
  sleep 60
done
echo "[$(date +%H:%M:%S)] card free of other local-env runners; starting"
exec ./python_tabpfn_local.sh src/eda/pair_strength/local_fits.py "$@"
