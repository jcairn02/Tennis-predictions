#!/usr/bin/env bash
# Start this study's local TabPFN runner only when no other process of the `tennis-tabpfn-local` env is alive.
# Other sessions' runners (e.g. src/eda/surface_rating_race/local_fits.py) wait while ANY other local-env process
# exists; if this runner started beside one of them, each would wait for the other. So: poll, then start.
# Usage: bash src/eda/feature_interactions/launch_when_free.sh --arms model --seasons 2014-2018
cd "$(dirname "$0")/../../.." || exit 1
while true; do
  n=$(powershell.exe -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*tennis-tabpfn-local*' } | Measure-Object).Count" | tr -d '\r')
  if [ "$n" = "0" ]; then break; fi
  echo "[$(date +%H:%M:%S)] $n local-env process(es) running; waiting"
  sleep 60
done
echo "[$(date +%H:%M:%S)] card free of other local-env runners; starting"
exec ./python_tabpfn_local.sh src/eda/feature_interactions/local_fits.py "$@"
