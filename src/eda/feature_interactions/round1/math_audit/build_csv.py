"""Collect the per-ID audit cards of docs/studies/feature_interactions/round1/math_audit/NN_<family>.md into one CSV.

    ./python.sh src/eda/feature_interactions/round1/math_audit/build_csv.py

A card is a '### I-xxx ...' heading followed by '- <field>: <value>' lines. Writes
data/studies/feature_interactions/round1/math_audit.csv (one row per master ID) and checks that all 91 IDs are there.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
DOCS = ROOT / "docs" / "studies" / "feature_interactions" / "round1" / "math_audit"
OUT = ROOT / "data" / "studies" / "feature_interactions" / "round1" / "math_audit.csv"
FIELDS = ["hid", "family", "type_basis", "swap_ok", "redundancy", "novelty_r2", "effect_bound_mll", "mde_mll",
          "controls", "trait", "sign", "deployment", "verdict", "weight", "kill_reason", "fix", "notes"]


def main() -> int:
    rows = []
    for f in sorted(DOCS.glob("[0-9][0-9]_*.md")):
        family = f.stem
        cur = None
        for line in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^### (I-\d{3})\b", line)
            if m:
                cur = {"hid": m.group(1), "family": family}
                rows.append(cur)
                continue
            if line.startswith("## ") or line.startswith("# "):
                cur = None
                continue
            m = re.match(r"^- ([a-z_0-9]+): (.*)$", line)
            if cur is not None and m and m.group(1) in FIELDS:
                cur[m.group(1)] = m.group(2).strip()
    ids = [r["hid"] for r in rows]
    want = [f"I-{i:03d}" for i in range(1, 92)]
    missing, dup = sorted(set(want) - set(ids)), sorted({i for i in ids if ids.count(i) > 1})
    incomplete = [r["hid"] for r in rows if any(k not in r for k in ("type_basis", "verdict", "weight", "sign"))]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["hid"]):
            w.writerow({k: r.get(k, "") for k in FIELDS})
    print(f"{len(rows)} rows; missing {missing}; duplicated {dup}; incomplete {incomplete}")
    verdicts = {}
    for r in rows:
        verdicts[r.get("verdict", "?")] = verdicts.get(r.get("verdict", "?"), 0) + 1
    print("verdicts:", verdicts)
    return 0 if not (missing or dup or incomplete) else 1


if __name__ == "__main__":
    sys.exit(main())
