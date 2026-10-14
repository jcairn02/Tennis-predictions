"""R3-referee, group SVX: add the "SVX" entry to verdict.json, and its findings to other_findings. Run once.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_verdict.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402


def main() -> int:
    p = F.OUT / "verdict.json"
    v = json.loads(p.read_text(encoding="utf-8"))
    if "SVX" in v:
        raise SystemExit("verdict.json already has an SVX entry")
    v["SVX"] = {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("All 323 proposed swaps (swaps_scope.csv): AO 2025 81 (36 men's, 45 women's), RG 2019 71, RG 2020 79, "
                  "RG 2021 92; exchange_svgms on Sackmann's row. Bar: the 8 Oct bar. Test per match, all from my own "
                  "code: (1) the first server is proven by the Slam's MatchBeats file under a test stricter than the "
                  "brief's (first point in set 1 game 1, no gap in set or game numbers, one server for every point of a "
                  "non-tiebreak game, and every game in file order on the alternation's turn, a tiebreak by its first "
                  "point); (2) the row's two counts are the truth's two exchanged, and the truth's two differ (the truth: "
                  "the row's score read from that first server, servers alternating game by game, a tiebreak taking one "
                  "turn uncounted, a retirement's unfinished game not in the score); (3) MatchBeats' own count of "
                  "completed non-tiebreak games equals the truth; (4) no independent record holding the match reads the "
                  "row or names another first server; (5) with the candidate's tables, the swap changes only the row's two "
                  "service-game counts, exchanged, which then equal the truth, and the row passes Stage 0's checks."),
        "reasons": ("The first server is proven, and the record that proves it names servers correctly: on every match "
                    "Court Vision holds (762, RG 2019-2024) and every match a hand chart holds (456, RG 2019-2026 and AO "
                    "2025) the record's first server equals MatchBeats'. The truth is right: on the matches whose row "
                    "already equals it, the records read that same count (Court Vision 689, the charts 399; the other "
                    "readings are retirements, where they count the unfinished game for its server); MatchBeats' own "
                    "count of completed non-tiebreak games equals the truth on all 323 proposed swaps (302 files holding "
                    "every point, and 21 AO files missing some points but holding every game; on all 455 AO 2025 matches "
                    "classed equal or swapped). The rows are swapped, not otherwise wrong: where an independent record "
                    "holds the match (69 of the 323: Court Vision 52, in RG 2019 13, 2020 13, 2021 26; the charts 25, in "
                    "AO 2025 11, RG 2019 2, 2020 6, 2021 6; 8 by both), it reads the truth 69 times and the row never. "
                    "In 270 the row is the score as if the winner had served first when the loser did, in 53 the "
                    "exchange runs the other way. The box itself is the right way round: on the 302 whole files "
                    "MatchBeats' serve points equal the row's for each named player, and RG's 2019-2021 rows equal RG's "
                    "statistics on all eight counts, so only the two service-game counts are exchanged, not the names. "
                    "Two RG 2019 rows (Halep d. Tsurenko, Halep d. Swiatek) fail Stage 0's B8 as recorded, the loser "
                    "conceding more breaks than the service games the row gives her, and pass with the exchange. "
                    "Tiebreak sets (97 swaps), long advantage final sets (6) and retirements (6) are handled the same "
                    "way and agree with MatchBeats' completed games. The fix is clear, unique and correct: exchanging the "
                    "two counts gives exactly the truth for both players in all 323, leaves the total (so B5) unchanged, "
                    "and touches nothing else; no swap row is named by another box correction of the candidate (the "
                    "combined table applies without a row named twice), and the one swapped RG 2023 match is left to its "
                    "override, which already carries the truth. Links: AO 2025 files placed by tour, draw, round and both "
                    "names (79 exact, 2 transliterations: Khumoun/Khumoyun Sultanov, Georgia/Giorgia Pedone); RG files "
                    "by my round-2 link."),
        "checks": [
            "svx.py: my decryption of the 469 AO 2025 files and the RG 2019-2026 files, my proof, truth and classes: "
            "324 swapped, the lead's 324; the 323 proposed are all swapped and proven; 270 as if the winner served "
            "first; MatchBeats' completed games equal the truth on 302/302 whole files (svx_rows.csv, svx_summary.json)",
            "svx_referees.py: Court Vision and the hand charts point by point: first server equal to MatchBeats' on "
            "762/762 and 456/456 held matches; on the proposed swaps they read the truth 52/52 and 25/25, the row 0 "
            "(svx_ref_rows.csv, svx_ref_summary.json)",
            "svx_simulate.py: the candidate's tables (followup/confirmed/candidate/: the override table with "
            "apply_box_overrides, then the corrections with apply_row_corrections) with and without the swaps; on the "
            "whole raw frame 3,620 rows change and every one is named by a table; between the two versions only the "
            "323 swap rows differ, only in w_SvGms and l_SvGms, exchanged, and all 323 equal the truth after; Stage 0's "
            "box checks on 7,386 Stage 0 rows of AO 2019-2026, RG 2019-2026 and the Olympics: B5 failures 10 -> 10, "
            "B8 failures 6 -> 4 (the two Halep rows regain their boxes), no row loses a box, all 323 swap rows full "
            "after (svx_sim_summary.json; my scope gives the same, svx_sim_summary_scope.json)",
            "svx_scope.py: the five tests per swap, 323/323 pass (svx_scope.json, swaps_scope.csv)",
        ],
    }
    v["other_findings"] += (
        " 10. SVX: the Court Vision copy flags the games after 6-6 of an advantage final set (RG until 2021) as "
        "tiebreak games, so counting service games by its is_tiebreak flag undercounts long final sets (Wawrinka d. "
        "Tsitsipas 8-6, Rodionov d. Chardy 10-8 and 7 matches whose row is right); count a game as a tiebreak only where "
        "both players serve in it. 11. SVX: the 'other' class, left out as not exact swaps, is wrong too where a record "
        "can tell: Court Vision (15 matches) and the charts (7) read the truth on every one they hold, never the row. "
        "That is evidence for the undecided 'service-game mismatches that are not exact swaps'; they would take the "
        "truth, not an exchange. 12. SVX: the swapped RG 2023 match left out (Diaz Acosta d. Agamenone, Q1) is already "
        "corrected by its confirmed override (11 and 10, the truth). 13. SVX: my proof test is stricter than the lead's "
        "on two matches the lead classes equal (no gap in game numbers) and looser on one the lead classes unproven; none "
        "is a swap, so the proposal does not move.")
    p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"SVX": {k: v["SVX"][k] for k in ("vote", "corrupt_beyond_doubt", "fix_clear_and_correct")}},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
