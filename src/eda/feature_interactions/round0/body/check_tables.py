"""Round 0, body brainstormer: check that every markdown table row in ideas_body.md has a consistent cell count
(unescaped pipes per row), so that no formula breaks a table. Text check only.

Run: ./python.sh src/eda/feature_interactions/round0/body/check_tables.py
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DOC = ROOT / "docs/studies/feature_interactions/round0/ideas_body.md"
PIPE = re.compile(r"(?<!\\)\|")


def main() -> None:
    import sys
    doc = ROOT / sys.argv[1] if len(sys.argv) > 1 else DOC
    rows = []
    block = []
    for i, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("|"):
            block.append((i, len(PIPE.findall(line))))
        elif block:
            rows.append(block)
            block = []
    if block:
        rows.append(block)
    problems = []
    for b in rows:
        expected = b[0][1]
        problems += [(i, n, expected) for i, n in b if n != expected]
    print("tables:", len(rows), "row pipe counts:", Counter(n for b in rows for _, n in b))
    print("rows differing from their table header:", problems or "none")


if __name__ == "__main__":
    main()
