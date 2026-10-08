#!/usr/bin/env bash
# Wrapper for the isolated `tennis-tabpfn-local` conda env (environment-tabpfn-local.yml): local TabPFN-3.5 on the GPU,
# no API tokens. Paid API calls stay in ./python_tabpfn.sh; everything else runs through ./python.sh.
# Usage:
#   ./python_tabpfn_local.sh src/eda/tabpfn_local/verify.py
# Fails loudly if the env does not exist — no silent fallback to another interpreter.
PY="C:/Users/zerom/miniforge3/envs/tennis-tabpfn-local/python.exe"
if [ ! -f "$PY" ]; then
  echo "ERROR: conda env 'tennis-tabpfn-local' not found at $PY" >&2
  echo "Create it from the project root first:" >&2
  echo "    conda env create -f environment-tabpfn-local.yml" >&2
  exit 1
fi
exec "$PY" "$@"
