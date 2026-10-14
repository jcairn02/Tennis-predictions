"""R2-skeptic (round 2, SVX): add the SVX ruling to verdict.json (groups.SVX and top-level SVX, identical), from my
files (svx_checks.json, svx_identity.json, svx_labels.csv, svx_dry_run.json).
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/verdict_svx.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"


def main() -> int:
    v = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
    ck = json.loads((OUT / "svx_checks.json").read_text(encoding="utf-8"))
    idn = json.loads((OUT / "svx_identity.json").read_text(encoding="utf-8"))
    dry = json.loads((OUT / "svx_dry_run.json").read_text(encoding="utf-8"))
    lab = pd.read_csv(OUT / "svx_labels.csv")
    sw, allp = ck["swapped"], ck["all_proven_matches"]
    lsw = lab[lab["cls"].eq("swapped")]
    entry = {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": (f"All {dry['confirmed']} proposed swaps (swaps_scope.csv): AO 2025 81, RG 2019 71, RG 2020 79, "
                  "RG 2021 92. My own derivation finds the same 324 swapped matches. The 324th, RG 2023 Q1 "
                  "Diaz Acosta d. Agamenone, is rightly left out: its confirmed override already carries RG's box "
                  "with the true 11 and 10, and an exchange on top would undo it. Nothing to add; nothing to drop."),
        "reasons": (
            "Corrupt beyond doubt, by four lines of evidence, one of them independent of MatchBeats. "
            "(1) The first server is proven twice in every proposed match, with my own parse, links and code. The "
            "file's first point opens set 1 and its games alternate in order (the lead's test). Separately, every "
            "non-tiebreak game the file holds, placed by the score, implies the same first server. Independent "
            f"records never contradict it: hand charts agree in {allp['chart_agrees_with_file']} of "
            f"{allp['chart_held']} matches they hold ({sw['chart_agrees_with_file']} of {sw['chart_held']} swaps; "
            "every chart opens at 0-0 and passes the parity test). Court Vision agrees in "
            f"{allp['cv_agrees_with_file']} of {allp['cv_held']} ({sw['cv_agrees_with_file']} of {sw['cv_held']} "
            "swaps). "
            "(2) Where the file holds the whole match, its own game-by-game count of who served is the truth in "
            f"{sw['file_count_is_truth_where_whole']} of {sw['file_whole']} swaps (the rest are retirements). "
            "(3) A test from the row's own score and break points alone: each player's non-tiebreak games won "
            "equal his service games, minus his service games lost, plus the opponent's. Exchanging the two counts "
            "flips the difference, so the test can pass for only one of them. It holds for the truth and fails for "
            f"Sackmann's row in {idn['swapped']['truth_only']} of {idn['swapped']['matches']} swapped matches, "
            "including all 323 proposed. On the equal class it holds in "
            f"{idn['equal']['identity_holds_for_truth']} of {idn['equal']['matches']}. In 2 swaps, RG 2019 R32 and "
            "R16 (Halep d. Tsurenko 6-2 6-1, Halep d. Swiatek 6-1 6-0), Sackmann's counts even fail B8 today: the loser "
            "was broken more times than her recorded service games. The exchange repairs them. "
            "(4) Not another error dressed as an exchange: serve points, aces, double faults and serve points won fit "
            f"the row's box by name strictly better than exchanged in {int(lsw['labels_by_name'].sum())} of "
            f"{len(lsw)} swaps, so the box itself is not exchanged and the server labels are right. The same test "
            "flags exactly the four RGX boxes as exchanged, which validates it. "
            "Other attacks: the row's winner equals the Slam's in every swap. The row's score equals the Slam's in "
            f"{sw['row_score_equals_slam_score']} of {sw['matches']} (the 3 others are AO retirements where the file "
            "also holds the unfinished game). Files that start late are unproven and not proposed. Files that stop "
            "early are 6 retirements, and the truth counts completed games, as Sackmann does. Sackmann's count "
            "cannot be the right one: the point record, the hand charts and Court Vision name the first server the "
            "file names, not the one Sackmann's counts imply, and the score-and-break identity rejects Sackmann's "
            "counts. "
            f"Tennis My Life's rows equal Sackmann's swapped counts in {sw['tml_equals_sackmann']} of "
            f"{sw['tml_held']} and the truth in {sw['tml_equals_truth']}. TML shares the derivation, so it is no "
            "independent support for Sackmann. "
            f"{sw['row_as_if_winner_first']} of 324 rows are exactly the count as if the winner had served first. "
            "The fix is clear, unique and correct. exchange_svgms exchanges only the two counts. After it, every row "
            "reads the truth, totals and B5 are unchanged, and B8 passes in all (2 rows newly). No proposed row takes "
            "another correction in the candidate (corrections allow one box correction per row) or an override. The "
            f"dry run with the build's own apply_row_corrections exchanged {dry['dry_run']['rows_exchanged']} rows, "
            f"all reading the truth after, with {dry['dry_run']['other_counts_changed']} other counts changed."
        ),
        "checks": [
            "svx_inputs.py: Stage 0's raw rows of AO 2025 (the build's own loader, once); the 469 AO 2025 MatchBeats "
            "files decrypted (78,845 points); the first point of 974 hand charts of RG and AO 2019-2026",
            "svx.py -> svx_matches.csv: my links, both first-server proofs, the truth from the row's score, classes: "
            "the same counts as the lead's in every edition with a swap, and the same 324 swapped matches",
            "svx_checks.py -> svx_checks.json, svx_checked.csv: hand charts and Court Vision against the file's "
            "first server (0 disagreements in 1,192 matches), the file's own count, the Slam's score, TML's rows, "
            "the candidate's other corrections, B8, statuses",
            "svx_labels.csv (multi-count label test): the box by name fits better in 324 of 324 swaps; the only "
            "exchanged fits are the 4 RGX boxes",
            "svx_identity.py -> svx_identity.json: the identity from the row's score and break points picks the "
            "truth in 323 of 323 proposed swaps",
            "svx_scope.py -> swaps_scope.csv, svx_dry_run.json: 323 confirmed; apply_row_corrections exchanges 323 "
            "rows, all reading the truth after, nothing else changed"]}
    v.setdefault("groups", {})["SVX"] = entry
    v["SVX"] = entry
    v.setdefault("scope_totals", {})["SVX"] = {"proposed": 323, "confirmed": int(dry["confirmed"]),
                                               "by_edition": {"AO2025": 81, "RG2019": 71, "RG2020": 79, "RG2021": 92}}
    (OUT / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(entry["vote"], "|", entry["scope"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
