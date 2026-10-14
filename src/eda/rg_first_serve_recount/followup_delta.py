"""The changes between the proposal the round-2 reviewers checked (proposed_overrides_v1.csv) and the amended one
(proposed_overrides.csv), after the three reviewers' findings on service games: retirements count completed games
only; a match whose service games RG's record disproves is proposed though its eight counts are equal; the score
and the first server give service games where MatchBeats misses points.

Writes data/studies/rg_first_serve_recount/followup/review/addendum_matches.csv: one row per match that changed,
was added or was removed, with what changed and the v1 and v2 values (only the counts that differ).
Usage: ./python.sh src/eda/rg_first_serve_recount/followup_delta.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.rg_first_serve_recount import whole_box as WB  # noqa: E402

KEY = ["feed_key", "stage0_match_id"]


def main() -> int:
    v1 = pd.read_csv(WB.OUT / "proposed_overrides_v1.csv", dtype=str, keep_default_na=False)
    v2 = pd.read_csv(WB.OUT / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    m = v1.merge(v2, on=KEY, how="outer", suffixes=("_v1", "_v2"), indicator=True)
    rows = []
    for r in m.to_dict("records"):
        if r["_merge"] == "both":
            diff = [c for c in B.OVERRIDE_COUNTS if r[f"{c}_v1"] != r[f"{c}_v2"]]
            if not diff:
                continue
            what = "changed"
        else:
            diff = list(B.OVERRIDE_COUNTS)
            what = "added" if r["_merge"] == "right_only" else "removed"
        names = "v2" if what != "removed" else "v1"
        rows.append({"what": what, **{k: r[k] for k in KEY}, "winner_name": r[f"winner_name_{names}"],
                     "loser_name": r[f"loser_name_{names}"], "counts": " ".join(diff),
                     **{f"{c}_v1": r.get(f"{c}_v1", "") for c in diff if what == "changed"},
                     **{f"{c}_v2": r.get(f"{c}_v2", "") for c in diff if what != "removed"}})
    out = pd.DataFrame(rows)
    out.to_csv(WB.OUT / "review" / "addendum_matches.csv", index=False)
    print(out["what"].value_counts().to_dict() if len(out) else "no changes")
    print(out.groupby(["what", "counts"]).size().to_string() if len(out) else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
