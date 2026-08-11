#!/usr/bin/env bash
# Wrapper to invoke this project's conda Python environment.
# Usage:
#   ./python.sh script.py [args...]
#   ./python.sh -c "print('hello')"
#   ./python.sh -m pytest
#
# The dedicated env is `tennis` (see environment.yml). This wrapper fails loudly
# if the env does not exist yet — no silent fallback to another interpreter.
PY="C:/Users/zerom/miniforge3/envs/tennis/python.exe"
if [ ! -f "$PY" ]; then
  echo "ERROR: conda env 'tennis' not found at $PY" >&2
  echo "Create it from the project root first:" >&2
  echo "    conda env create -f environment.yml" >&2
  echo "If you deliberately want another env, call its python.exe explicitly" >&2
  echo "(e.g. C:/Users/zerom/miniforge3/envs/ufc-ag/python.exe) — do not edit this wrapper to fall back silently." >&2
  exit 1
fi
exec "$PY" "$@"
