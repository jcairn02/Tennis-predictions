#!/usr/bin/env bash
# The fits of the three arms (qualifying_targets step 7), detached. Log: fits.log beside it.
# M0 2019 seed 0 is fitted and checked against the instance's stored fit first (fits.py --check-m0); the batch runs
# only if that check passes. A fit on disk is never redone, so the script resumes where it stopped.
cd /c/Users/zerom/Documents/Tennis-predictions || exit 1
L=data/studies/qualifying_targets/fits.log
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) start" >> "$L"
./python_tabpfn_local.sh src/eda/qualifying_targets/fits.py --check-m0 >> "$L" 2>&1
rc=$?
if [ $rc -ne 0 ]; then echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) M0 check failed (exit $rc): batch not started" >> "$L"; exit $rc; fi
./python_tabpfn_local.sh src/eda/qualifying_targets/fits.py --arms M0,M1,M2 --seasons 2019-2026 --seeds 0-3 >> "$L" 2>&1
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) exit $?" >> "$L"
