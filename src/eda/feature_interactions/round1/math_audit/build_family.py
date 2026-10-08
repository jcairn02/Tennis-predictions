"""Parse docs/studies/feature_interactions/round2/hypothesis_family.md's table into
data/studies/feature_interactions/round2/hypothesis_family.csv, check it, and print the weighted-Holm MDE.

    ./python.sh src/eda/feature_interactions/round1/math_audit/build_family.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[5]
DOC = ROOT / "docs" / "studies" / "feature_interactions" / "round2" / "hypothesis_family.md"
OUT = ROOT / "data" / "studies" / "feature_interactions" / "round2" / "hypothesis_family.csv"
COLS = ["hid", "members", "primary_columns", "test", "sign", "multipliers", "weight", "trait", "controls", "deployment",
        "module", "notes"]
N_JOINT = 50087            # model matches, 2014-2024 (critique section 1.1)


def main() -> int:
    rows, inside = [], False
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if line.startswith("| hid |"):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("| "):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip()[1:-1].split(" | ")]
        if len(cells) != len(COLS):
            print("bad row:", cells[0], len(cells))
            return 1
        rows.append(dict(zip(COLS, cells)))
    ids = [r["hid"] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    wts = [float(r["weight"]) for r in rows]
    m, f = len(wts), len(wts) / sum(wts)
    print(f"{m} hypotheses; duplicates {dup}; raw weight sum {sum(wts)}; normalising factor {f:.3f}")
    print("by test:", {t: sum(r["test"] == t for r in rows) for t in sorted({r["test"] for r in rows})})
    for w_ in (2.0, 1.0, 0.5):
        a = 0.05 * w_ * f / m
        one = 1000 * (norm.isf(a) + norm.isf(0.2)) ** 2 / (2 * N_JOINT)
        two = 1000 * (norm.isf(a / 2) + norm.isf(0.2)) ** 2 / (2 * N_JOINT)
        print(f"weight {w_}: normalised {w_ * f:.2f}; alpha {a:.5f}; MDE one-sided {one:.3f} mLL, two-sided {two:.3f}")
    return 0 if not dup else 1


if __name__ == "__main__":
    sys.exit(main())
