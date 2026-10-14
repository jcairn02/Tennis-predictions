"""Box-score coverage of completed singles matches in Stage 0, by tour, kind of match and season: what the model's
training rows hold (docs/studies/box_score_gate_review/). A gap of a kind that training rows lack at similar rates is
not a live-versus-training difference; a gap of a kind training nearly always has is.

Run: ./python.sh src/eda/box_score_gate_review/coverage.py [--stage0 <folder>]
Writes data/studies/box_score_gate_review/coverage.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.box_score_gate_review.simulate_gate import level_group  # noqa: E402

OUT = ROOT / "data" / "studies" / "box_score_gate_review"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0", default=str(ROOT / "data" / "studies" / "predictability_diagnostic"))
    a = ap.parse_args()
    m = pd.read_parquet(Path(a.stage0) / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "status", "has_box"])
    m = m[m["status"].eq("completed") & m["year"].between(2013, 2026)].copy()
    m["kind"] = level_group(m["level"], m["qualifying"])
    c = (m.groupby(["tour", "kind", "year"])["has_box"].agg(matches="size", with_box="sum").reset_index())
    c["pct"] = (100 * c["with_box"] / c["matches"]).round(1)
    c.to_csv(OUT / "coverage.csv", index=False)
    w = c.pivot_table(index=["tour", "kind"], columns="year", values="pct")
    pd.set_option("display.width", 250)
    print(w.to_string(float_format=lambda x: f"{x:.0f}"))
    tr = m[m["year"].between(2013, 2025)].groupby(["tour", "kind"])["has_box"].mean().mul(100).round(1)
    print("\n2013-2025 pooled:\n" + tr.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
