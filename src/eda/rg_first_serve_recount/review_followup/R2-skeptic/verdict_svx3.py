"""R2-skeptic (round 2, SVX addendum 2): add the SVX_addendum2 ruling to verdict.json (groups.SVX_addendum2 and top-level
SVX_addendum2, identical), from svx3_checks.json and svx3_dry_run.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/verdict_svx3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"


def main() -> int:
    v = json.loads((OUT / "verdict.json").read_text(encoding="utf-8"))
    ck = json.loads((OUT / "svx3_checks.json").read_text(encoding="utf-8"))
    dry = json.loads((OUT / "svx3_dry_run.json").read_text(encoding="utf-8"))
    sc, allp = ck["swapped_checks"], ck["all_proven"]
    entry = {
        "vote": "narrow",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": (f"{dry['confirmed']} of the 105 RG 2016-2018 swaps, appended to swaps_scope.csv (now "
                  f"{dry['scope_total']} rows; the earlier 705 kept as they are, also saved as "
                  "swaps_scope_round2a.csv). My own derivation (my parse of the 1,331 files, links and code) finds "
                  "exactly the lead's 105. 103 pass every test. One more is confirmed on the evidence: 2016 R128 "
                  "Nara d. Allertova (wta|2016-520|R128|wta:201597|wta:202653). Left out: 2016 R16 Stosur d. Halep "
                  "(wta|2016-520|R16|wta:201325|wta:201594)."),
        "reasons": (
            f"The same tests as before. The first server is proven twice; hand charts agree in "
            f"{allp['charts_agree']} of {allp['charts_held']} matches of these editions ({sc['charts_agree']} of "
            f"{sc['charts_held']} swaps; no Court Vision before 2019). The file's own count is the truth in "
            f"{sc['file_count_is_truth_where_whole']} of {sc['file_whole']} swaps whose file holds the whole match. "
            f"The box fits by name in {sc['labels_by_name']} of 105. B8 passes after the exchange in all. No other "
            "correction or override touches these rows. The score-and-break identity holds for the truth and fails "
            f"for the row in {sc['identity_truth_only']} of 105; on the equal class it holds in "
            f"{allp['identity_equal_class']['holds']} of {allp['identity_equal_class']['matches']}. "
            f"{sc['row_as_if_winner_first']} of the 105 rows are the count as if the winner had served first. "
            f"Tennis My Life equals Sackmann's swapped counts in {sc['tml_equals_sackmann']} of {sc['tml_held']} and "
            "the truth in none: the same derivation. "
            "Nara d. Allertova (5-7 6-3 2-0 RET): its only failed check is the file's winner flag, which names "
            "Allertova. The flag is wrong. Nara plays the next round in Stage 0, and the file's own games give her "
            "13 to 10, 2-0 up in the third set at the retirement. It is the flag's only disagreement among the 1,316 "
            "RG 2016-2018 matches where it is set, and it is a retirement. Every other test passes. Confirmed. "
            "Stosur d. Halep (7-6(0) 6-3): the file proves the truth. Every game is present, matches the set scores "
            "and alternates from Stosur's first serve, and a global flip of the server labels would give Stosur 8 "
            "breaks and Halep 9, absurd beside any record. So Stosur served 10 games and Halep 11, and the row's 11 "
            "and 10 are swapped. But the row carries a second error the exchange does not touch. The file has Halep "
            "facing 12 break points and losing 3; Sackmann has 7 and 2 (Stosur's 7 and 6 agree in both). With 11 "
            "service games, Halep must have been broken exactly 3 times to give the 9 games she won, so Sackmann's "
            "break count is wrong. His swapped service games and his break points are consistent only with each "
            "other: this is why the identity picks the row here. After the exchange alone the row would no longer "
            "add up, and Halep's hold rate would move further from the truth (80.0% to 81.8%, truth 72.7%). "
            "exchange_svgms alone is not the clear and complete fix for this row. A separate operation could set "
            "both counts from the file. "
            "Not swaps, and rightly not proposed: RG 2017's 132 'other' rows, whose service games fall 14 to 40 short "
            "of the score's (median 20 short; Stage 0's B5 already drops them). "
            "My earlier confirmations stand against the new alternation_strict flag. AO 2019 MS140's split set "
            "records still carry set 3, games 9 and 10, so the order of play and every game's place are unchanged. "
            "Griekspoor d. Safiullin was already confirmed on the independent evidence. "
            f"The dry run with apply_row_corrections exchanged {dry['dry_run']['rows_exchanged']} rows, all reading "
            f"the truth after, with {dry['dry_run']['other_counts_changed']} other counts changed."),
        "checks": [
            "svx3.py -> rg1618_matches.csv, svx3_checks.json: my parse of RG 2016-2018 (the API route; the 16 RG 2016 "
            "codes without a file have no match here), links, both proofs, the truth, classes (the lead's 105 swaps "
            "exactly), the label test, the identity test, the file's own count, B8, hand charts, TML, the candidate's "
            "corrections and overrides",
            "file recount of Stosur-Halep: games, servers, game winners, break points faced and saved per player",
            "svx3_scope.py -> swaps_scope.csv (809 rows), swaps_addendum2_rows.csv, svx3_dry_run.json: 104 exchanged "
            "with the build's code, all reading the truth after, nothing else changed"]}
    v.setdefault("groups", {})["SVX_addendum2"] = entry
    v["SVX_addendum2"] = entry
    v["scope_totals"]["SVX"].update({"addendum2_proposed": 105, "addendum2_confirmed": int(dry["confirmed"]),
                                     "addendum2_left_out": dry["left_out"], "total_confirmed": int(dry["scope_total"])})
    (OUT / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(entry["vote"], "|", entry["scope"])
    print(json.dumps(v["scope_totals"]["SVX"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
