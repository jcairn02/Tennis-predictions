"""R2-skeptic (round 2, SVS): add the SVS ruling to verdict.json (groups.SVS and top-level SVS, identical), from
sets_checks.json and sets_dry_run.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/verdict_svs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"


def main() -> int:
    v = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
    ck = json.loads((OUT / "sets_checks.json").read_text(encoding="utf-8"))
    dry = json.loads((OUT / "sets_dry_run.json").read_text(encoding="utf-8"))
    op = ck["other_patterns"]
    entry = {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": (f"All {dry['confirmed']} proposed set_svgms rows (sets_scope.csv): {ck['kinds']['fill']} fills and "
                  f"{ck['kinds']['other']} others. My values equal the proposal's in "
                  f"{dry['values_equal_proposal']} of 558. One note: 6 of the fills (RG 2013-2014 women's rows whose "
                  "double faults are blank for both players) are right but leave those boxes partial in Stage 0."),
        "reasons": (
            "Checked with my own links, proofs and truth (sets_check.py). "
            "Links: my link places all 558 on the lead's match, including the 334 RG 2013-2014 women's rows, whatever "
            "their ids. Serve points equal the file's by name in 537. The other 21 are files with a point or a few "
            "missing or duplicated, and the multi-count label test (serve points, aces, double faults, serve points "
            "won) fits by name in every row with a full box. "
            "First server: proven by both proofs in 557. RG 2014 SD078 stores set 1's game 8 twice under the same "
            "server, which only my positional test minds; the parity proof has no dissent over its 30 games, so I "
            "accept it. "
            "Truth: completed non-tiebreak games from the row's score and that first server; my values equal the "
            "proposal's in all 558. The guard value is the row's in all 558. Where the file holds the whole match, "
            f"its own count is the truth in {ck['file_count_is_truth']}. "
            f"The consistency identity holds for the truth in {ck['identity_truth']} and for the row in "
            f"{ck['identity_row']}, so no row has a break count the set would contradict. "
            f"Fills ({ck['fill_rows']}): the count is missing beyond doubt (blank, or 0 with serve points played). "
            f"The rest of the box is there in {ck['fill_rest_of_box_complete']}. The other 6 (RG 2013 R64 x2 and SF; "
            "RG 2014 Q2, R32, R16) lack both players' double faults: the filled values are right (serve points equal "
            "the file's, identity holds) but Stage 0 keeps those boxes partial. "
            f"Others ({op['rows']}): every one is impossible under either order of serve, so the score alone "
            "disproves the row. None is a convention: no row has the tiebreaks-counted total, none counts a "
            "retirement's unfinished game, none is an exchange. "
            f"{op['total_minus_truth'].get('0.0', 0)} have the right total with a split the score forbids, mostly "
            "a tiebreak not given its turn in the alternation (15 and 15 where a 7-6 set forces 16 and 14). The "
            "rules give that turn: the player who served first in the tiebreak receives first in the next set. One "
            "is a game short, and one is 9 short (a partial count). "
            "Stage 0's checks B0-B9 pass after the set in 552; the 6 partial boxes stay as partial as before. No "
            "proposed row takes another correction, a swap or an override (the build allows one box correction per "
            f"row). The dry run with apply_row_corrections set {dry['dry_run']['rows_set']} rows, every guard "
            f"passing, all reading my values, with {dry['dry_run']['other_counts_changed']} other counts changed."),
        "checks": [
            "sets_check.py -> sets_checked.csv, sets_checks.json: my links, both proofs, my truth, the guard values, "
            "fill completeness, the convention patterns of the others, the identity, Stage 0's checks before and "
            "after, the file's own count, overlaps with the candidate's corrections, the swaps and the overrides",
            "file inspections: RG 2014 SD078 (the repeated game 8), the 21 rows whose serve points differ from the file's",
            "sets_scope.py -> sets_scope.csv (558 rows, my values), sets_dry_run.json: set_svgms applied with the "
            "build's code, 558 rows set, every guard passing, nothing else changed"]}
    v.setdefault("groups", {})["SVS"] = entry
    v["SVS"] = entry
    v["scope_totals"]["SVS"] = {"proposed": 558, "confirmed": int(dry["confirmed"]),
                                "values_equal_proposal": int(dry["values_equal_proposal"]),
                                "partial_boxes_filled": dry["partial_boxes_filled"]}
    (OUT / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(entry["vote"], "|", entry["scope"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
