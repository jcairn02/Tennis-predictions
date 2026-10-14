"""Lint the round-0 inventory markdown: unescaped pipes inside table cells and tables whose rows have different
column counts (feature-interactions data map). Reads docs/studies/feature_interactions/round0/inventory.md only.
Run: ./python.sh src/eda/feature_interactions/inventory/md_check.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MD = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "studies" / "feature_interactions" / "round0" / "inventory.md"
SPLIT = re.compile(r"(?<!\\)\|")


def main() -> int:
    lines = MD.read_text(encoding="utf-8").splitlines()
    problems = 0
    table_start, ncols = None, None
    in_code = False
    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.startswith("|"):
            n = len(SPLIT.split(line)) - 2
            if table_start is None:
                table_start, ncols = i, n
            elif n != ncols:
                problems += 1
                print(f"line {i}: {n} cells, table at line {table_start} has {ncols}")
        else:
            table_start, ncols = None, None
    print(f"{problems} problem rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
