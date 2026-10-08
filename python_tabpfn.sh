#!/usr/bin/env bash
# Wrapper for the isolated `tennis-tabpfn` conda env (environment-tabpfn.yml): the hosted TabPFN API calls only.
# Everything else in the project runs through ./python.sh (the `tennis` env).
# Usage:
#   ./python_tabpfn.sh src/eda/tabpfn_thinking/dispatch.py --quote
# Fails loudly if the env does not exist — no silent fallback to another interpreter.
PY="C:/Users/zerom/miniforge3/envs/tennis-tabpfn/python.exe"
if [ ! -f "$PY" ]; then
  echo "ERROR: conda env 'tennis-tabpfn' not found at $PY" >&2
  echo "Create it from the project root first:" >&2
  echo "    conda env create -f environment-tabpfn.yml" >&2
  exit 1
fi
exec "$PY" "$@"
