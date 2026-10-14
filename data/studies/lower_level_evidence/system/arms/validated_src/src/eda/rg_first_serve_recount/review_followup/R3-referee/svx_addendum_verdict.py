"""R3-referee, group SVX addendum: add "SVX_addendum" to verdict.json and its findings to other_findings. Run once.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_addendum_verdict.py
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
    if "SVX_addendum" in v:
        raise SystemExit("verdict.json already has an SVX_addendum entry")
    v["SVX_addendum"] = {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("All 382 swaps of addendum_swaps.csv, appended to swaps_scope.csv after my 323 (705 rows, equal to the "
                  "proposal's 705): AO 2019 36, 2020 32, 2021 48, 2022 46, 2023 83, 2024 70, 2026 66, and RG 2015 1 "
                  "(Safarova d. Lisicki, R32); exchange_svgms on Sackmann's row. Bar: the 8 Oct bar. The same tests as "
                  "SVX, from my own code (svx_addendum.py): the first server proven by the Slam's MatchBeats file under my "
                  "stricter test (381), or, where the file is irregular, named by the independent records holding the "
                  "match (1: Griekspoor d. Safiullin, AO 2024 R128); the row's two counts the truth's two exchanged, the "
                  "truth's two differing; MatchBeats' own completed games equal to the truth; no independent record "
                  "reading the row or naming another first server; with the candidate as confirmed (its 323 round-1 "
                  "swaps included), only the row's two counts change, exchanged, to the truth, and Stage 0's checks pass. "
                  "Nothing added: the only other swap my derivation finds, Paire d. Monteiro (AO 2022), is already "
                  "exchanged by the decided F2y row; AO 2018 and RG 2013-2014 hold no swap."),
        "reasons": ("My decryption of the new files (AO 2018-2024 and 2026 on the static route, 2,915 files; RG 2013-2015 "
                    "on the API route, 1,340 files; none failing) and my link to Sackmann's rows by tour, draw, round and "
                    "both names (4,018 rows placed, no tie; the 382 swaps 373 exact and 9 name variants with the other "
                    "player exact) find exactly the lead's swaps. The records naming the server point by point confirm "
                    "the method on these editions: Court Vision's AO 2020-2024 main draws (its server ids are the files' "
                    "player ids) name MatchBeats' first server on all 1,262 matches they hold, and the hand charts on all "
                    "567 they hold that have a file; on the matches whose row already equals the truth both read that "
                    "count (1,021 and 468). On the addendum swaps a record holds 226 of the 382 (Court Vision 203, the "
                    "charts 71, both 48; every AO 2020-2022 swap among them) and reads the truth in 273 of its 274 "
                    "readings and the row never; the one inexact reading is Court Vision's own on Griekspoor d. Safiullin "
                    "(24 and 26 against the truth's 25 and 26, a game with points of both servers in the copy), whose chart "
                    "reads the truth exactly. That match's MatchBeats file is garbled in set 4 (game 4 recorded twice, game "
                    "5 with both servers, set scores out of order), which my test flags and the brief's passes only because "
                    "it keys games by number; sets 1-3 and 5 alternate cleanly from Safiullin's first serve, which Court "
                    "Vision and the chart both name, so the row is corrupt beyond doubt on independent records. "
                    "MatchBeats' own completed games equal the truth on all 382 (374 files holding every point). 323 rows "
                    "are the score as if the winner had served first when the loser did; 59 run the other way; 18 are "
                    "retirements, handled by the score's finished games. The fix: on the candidate as confirmed, only the "
                    "382 rows change, only in their two service-game counts, exchanged, all 382 then equal the truth, and "
                    "every changed row of the whole frame is named by a table; B5 failures stay 12; the 4 B8 failures "
                    "left among AO and RG rows (AO 2021 R32, AO 2023 R128, AO 2024 R16, AO 2026 Q3, which I noted after "
                    "round 1) are all addendum swaps and pass with the exchange, so B8 failures fall to 0; no row loses a "
                    "box. The RG 2015 swap (6-3 7-6(2), Lisicki serving first: truth 10 and 11, row 11 and 10) has no "
                    "independent record, but its file holds every point and its completed games equal the truth."),
        "checks": [
            "svx_addendum.py: raw rows read once with Stage 0's loader; the new files decrypted and parsed with my "
            "stricter proof; links, truth and classes; the lead's 382 found, 381 swapped and proven, 1 unproven by my "
            "test (the garbled file); my swaps outside the list: only Paire d. Monteiro (decided F2y); Court Vision and "
            "chart readings (svx_add_rows.csv, svx_add_summary.json)",
            "svx_simulate.py --table addendum_swaps.csv --tag _add: the candidate as confirmed (2,272 overrides, 1,907 "
            "corrections with the 323 round-1 swaps) with and without the 382: on the whole raw frame 4,002 rows change, "
            "all named by a table, exchange_svgms on 706 rows; only the 382 rows differ, only in w_SvGms and l_SvGms, "
            "exchanged; all 382 equal the truth after; Stage 0's checks on 12,762 rows of AO and RG 2013-2026 and the "
            "Olympics: B5 12 -> 12, B8 4 -> 0, 4 rows failed_check -> full, no row loses a box (svx_sim_summary_add.json)",
            "svx_addendum_scope.py: the tests per swap, 382/382 pass; swaps_scope.csv 705 rows, equal to the proposal's "
            "705 (svx_add_scope.json; the round-1 scope kept as swaps_scope_round1.csv)",
        ],
    }
    v["other_findings"] += (
        " 14. SVX addendum: the proof test should not key a file's games by their numbers alone. The AO 2024 file of "
        "Griekspoor d. Safiullin repeats game 4 and mixes servers in game 5 of set 4, and keying by (set, game) merges "
        "the repeat so the alternation passes; checking that game numbers run without repeat or gap catches it. Here "
        "the independent records settle the match, so nothing changes. 15. SVX addendum: Court Vision's AO copy uses "
        "the MatchBeats files' own player ids as server ids, so its first server maps onto the files without names. 16. "
        "SVX addendum: the hand charts' 17 first-server mismatches are all on AO qualifying matches with no MatchBeats "
        "file (2018-2020, 2022), so there is nothing to compare; on every match with a file they agree.")
    p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v["SVX_addendum"][k] for k in ("vote", "corrupt_beyond_doubt", "fix_clear_and_correct")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
