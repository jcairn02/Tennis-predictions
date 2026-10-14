"""R2-skeptic (round 2, SVX addendum): add the SVX_addendum ruling to verdict.json (groups.SVX_addendum and top-level
SVX_addendum, identical), from svx2_checks.json and svx2_dry_run.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/verdict_svx2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"


def main() -> int:
    v = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
    ck = json.loads((OUT / "svx2_checks.json").read_text(encoding="utf-8"))
    dry = json.loads((OUT / "svx2_dry_run.json").read_text(encoding="utf-8"))
    sc, allp = ck["swapped_checks"], ck["all_proven"]
    entry = {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": (f"All {ck['confirmed']} addendum swaps, appended to swaps_scope.csv, which now has "
                  f"{dry['total']} rows: AO 2019 36, 2020 32, 2021 48, 2022 46, 2023 83, 2024 70, 2026 66, and RG 2015 "
                  "Safarova d. Lisicki. My own derivation of the new editions (AO 2018-2024 and 2026, RG 2013-2015) "
                  "finds the same 382 swapped matches, give or take two. (a) AO 2022 R128 Paire d. Monteiro I also "
                  "find swapped. It is rightly left out: the decided F2y row of 8 Oct already exchanges it, a second "
                  "exchange would undo it, and the build allows one box correction per row. (b) AO 2024 R128 "
                  "Griekspoor d. Safiullin fails my strict proof, so I confirm it on independent evidence (reasons). "
                  "Nothing to add; nothing to drop."),
        "reasons": (
            "The same four lines of evidence as the first round, with my own parse of the 4,254 new files, links "
            "and code. (1) The first server is proven twice (opening point plus in-order alternation; parity over "
            "every game held) in 381 of the 382. Independent records never contradict it: hand charts agree in "
            f"{allp['charts']['agree']} of {allp['charts']['held']} matches of these editions "
            f"({sc['charts']['agree']} of {sc['charts']['held']} swaps), Court Vision (AO 2020-2024) in "
            f"{allp['court_vision']['agree']} of {allp['court_vision']['held']} ({sc['court_vision']['agree']} of "
            f"{sc['court_vision']['held']} swaps). (2) The file's own count is the truth in "
            f"{sc['file_count_is_truth_where_whole']} of {sc['file_whole']} swaps whose file holds the whole match "
            f"(the rest are {sc['status'].get('retired', 0)} retirements). (3) The identity from the row's own score "
            "and break points (games won on serve = service games - service games lost + the opponent's lost) holds "
            f"for the truth and fails for Sackmann's row in {sc['identity_truth_only']} of 382. On the equal class of "
            f"these editions it holds in {allp['identity_equal_class']['holds']} of "
            f"{allp['identity_equal_class']['matches']}. (4) Serve points, aces, double faults and serve points won "
            f"fit the row's box by name in {sc['labels_by_name']} of 382, so no box is exchanged and no server label "
            f"swapped. The winner agrees with the Slam's in all. Nothing else in the candidate touches these rows "
            f"(the one hit is Paire-Monteiro's F2y, left out), and there are {sc['candidate_override']} overrides. "
            f"B8 passes after the exchange in all, and {sc['b8_before_fails']} rows that fail it today are repaired: "
            "AO 2021 R32 Dimitrov d. Carreno Busta, AO 2023 R128 Muchova d. Tsurenko, AO 2024 R16 Noskova d. "
            "Svitolina, AO 2026 Q3 Bartunkova d. Osuigwe. "
            f"{sc['row_as_if_winner_first']} of the 382 rows are the count as if the winner had served first. "
            f"Tennis My Life equals Sackmann's swapped counts in {sc['tml_equals_sackmann']} of {sc['tml_held']} and "
            f"the truth in {sc['tml_equals_truth']}: the same derivation, no independent support. "
            "Griekspoor d. Safiullin (AO 2024 R128, MS136). The file has one glitch: set 4's game 4 is stored "
            "twice, the second time as a single point labelled to the other server, and game 5's first point carries "
            "the wrong server too. Taking each game's majority server, as the lead's test does, all 52 game entries "
            "alternate; my strict test counts the stray point and fails (1 dissent in 51 games). The rest settles "
            "it: the file opens set 1 with Safiullin serving, the hand chart and Court Vision both name Safiullin, "
            "and the score-and-break identity holds for the truth (25 and 26) and fails for the row (26 and 25). "
            "Confirmed. "
            f"The fix is clear, unique and correct: the dry run with apply_row_corrections exchanged "
            f"{dry['dry_run']['rows_exchanged']} rows, all reading the truth after, with "
            f"{dry['dry_run']['other_counts_changed']} other counts changed."),
        "checks": [
            "svx_inputs2.py: Stage 0's raw rows of AO 2018-2026 (the build's own loader, once); 4,254 point files of "
            "AO 2018-2024 and 2026 and RG 2013-2015 decrypted (716,650 points); 1,252 hand charts of 2013-2026 (all "
            "open at 0-0, 0 parity dissents)",
            "svx2.py -> svx2_matches.csv: my links, both proofs, the truth from the row's score, classes per edition "
            "(the lead's counts, but for Griekspoor-Safiullin, unproven by my strict test, and Paire-Monteiro, left "
            "out by the lead), the label test, the identity test, B8",
            "svx2_checks.py -> svx2_checks.json, svx2_checked.csv: hand charts and Court Vision against the file's "
            "first server (0 disagreements in 1,746 matches), TML's rows, the candidate's corrections and overrides",
            "svx2_scope.py -> swaps_scope.csv (705 rows; the first round's 323 kept as swaps_scope_round1.csv), "
            "svx2_dry_run.json: 382 exchanged with the build's code, all reading the truth after, nothing else "
            "changed"]}
    v.setdefault("groups", {})["SVX_addendum"] = entry
    v["SVX_addendum"] = entry
    v.setdefault("scope_totals", {})["SVX"].update({"addendum_proposed": 382, "addendum_confirmed": int(ck["confirmed"]),
                                                    "total_confirmed": int(dry["total"])})
    (OUT / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(entry["vote"], "|", entry["scope"])
    print(json.dumps(v["scope_totals"]["SVX"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
