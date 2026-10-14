"""R3-referee (follow-up, addendum): add the addendum entry to verdict.json; point the round-2 entries' evidence at the
*_v1 copies of the files the addendum reran; note what the addendum supersedes. Run once.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/addendum_verdict.py
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
    if "addendum" in v:
        raise SystemExit("verdict.json already has an addendum entry")
    g = v["groups"]
    rep = {"(extract_summary.json)": "(extract_summary_v1.json)",
           "(sim_summary.json, sim_scope_summary.json, brought_back.csv)":
               "(sim_summary_v1.json, sim_scope_summary_v1.json, brought_back_v1.csv)",
           "(rates_by_edition.csv)": "(rates_by_edition_v1.csv)"}
    for grp in ("RGX", "W22", "W26"):
        new = []
        for c in g[grp]["checks"]:
            for k, r in rep.items():
                c = c.replace(k, r)
            new.append(c)
        g[grp]["checks"] = new
    g["W22"]["scope"] += (" [Round-2 scope, superseded in part by the addendum below: the 8 W22 retirements take the "
                          "completed-games count and 13 W22 matches are added; my overrides_scope.csv now holds 1,190 W22 "
                          "matches; the round-2 scope is kept as overrides_scope_v1.csv.]")
    g["W26"]["scope"] += (" [Superseded in part by the addendum below: Maestrelli-Noguchi now reads 14 and 15, the 3 W26 "
                          "retirements take the completed-games count, and 19 W26 qualifying matches are added; my "
                          "overrides_scope.csv now holds 351 W26 matches.]")
    v["addendum"] = {
        "vote": "confirm",
        "bar": ("source rule (the 6 Oct rule applies, as for W22 and W26); for the 10 counts the score's alternation "
                "disproves, the 8 Oct bar is met as well"),
        "scope": ("All 44 matches of addendum_matches.csv, with my own values, which equal the amended override rows on "
                  "all eighteen counts. Changed (12): the 11 retirements (W22: rolandgarros:2022/QM041, 2022/SD073, "
                  "2022/SM038, 2023/QM117, 2023/SD081, 2024/QM044, 2024/SM038, 2025/SM115; W26: 2026/SD062, 2026/SM077, "
                  "2026/SM084), one player's service games one lower; and Maestrelli d. Noguchi (2026/QM080), 14 and 15 "
                  "where round 2 had them blank. Added (32): 13 W22 matches (Sackmann's blanks in 2023 qualifying: "
                  "QD027, QD030, QM024; counts the score's alternation disproves: 2023 SD003, SD048; 2024 SD035, SD044, "
                  "SM022, SM053, SM058, SM107, SM110, SM121) and 19 W26 matches (TML's zeros in 2026 qualifying). "
                  "overrides_scope.csv: the 12 changed rows replaced, the 32 appended, every other row as before: 1,541 "
                  "matches (1,190 W22, 351 W26), equal to the amended proposed_overrides.csv cell for cell. Tests per "
                  "match: my values equal the amended row's; for an added match my eight counts from RG's statistics "
                  "equal the row's (only the service games change); where MatchBeats holds every point its count equals "
                  "the score's alternation; no independent record reads another count once the unfinished game of a "
                  "retirement is set apart; the box passes Stage 0's checks."),
        "reasons": ("My own derivation, independent of the lead's code: MatchBeats decrypted and counted as completed, "
                    "non-tiebreak games per server (isGameComplete is present on every game of every route, 2019-2026, "
                    "and is false only on the last game of 33 documents: 25 retirements, 3 captures still in progress, and 5 placeholder documents of 2026 walkovers or a match outside Stage 0); and "
                    "the score's alternation, from the row's score and the player MatchBeats has serving the first point, "
                    "servers alternating game by game with a tiebreak taking one turn uncounted. The two agree on all 42 "
                    "matches where MatchBeats holds every point. The other 2 rest on the alternation because their "
                    "MatchBeats documents are captures that stop before the last game: Maestrelli d. Noguchi 3-6 7-6 6-2 "
                    "(Noguchi serves first, every game the document holds follows the alternation, and the missing final "
                    "game is Maestrelli's, hence 14 and 15, summing to the 29 non-tiebreak games) and Molcan d. Crawford "
                    "1-6 6-4 6-1 (24 games without a tiebreak: 12 each whoever served first). Retirements: a score holds "
                    "only finished games, so the alternation gives the completed-games count; MatchBeats flags exactly one "
                    "unfinished game, the last, served by the player whose count drops; in the 8 W22 retirements the new "
                    "value equals Sackmann's own count, which in every RG retirement of 2019-2025 leaves the unfinished "
                    "game out, so those overrides no longer change service games and the convention is the training "
                    "data's, as for tiebreaks (my round-2 finding 3, now addressed). The added matches: in the 10 of "
                    "2023-2024 the row's count is impossible under the score (Muchova d. Podoroska 13 and 11 in 24 games "
                    "without a tiebreak; Muchova d. Sabalenka 15 and 16 for 36 non-tiebreak games, failing B5; the other 8 "
                    "one game short of the score), so the row is corrupt and the fix is forced by the score and the first "
                    "server; the 19 TML zeros and 3 Sackmann blanks are missing values Stage 0 drops today, filled with "
                    "RG's completed games (my round-2 finding 2, now addressed). Independent records hold 7 of the 44 "
                    "matches and agree: Court Vision and the charts count games with a point served, so in the 4 "
                    "retirements they hold (Kalinina, Van de Zandschulp, Noskova, Rinderknech) they read the new value "
                    "plus the unfinished game for its server, and elsewhere exactly the new values (Day-Avanesyan 17-17, "
                    "Muchova-Sabalenka 18-18, De Jong-Draper 26-26). Only service games change in the added matches, so "
                    "first-serve rates are unchanged; hold rates move by hundredths; 2026 men's qualifying player rows "
                    "with service games rise from 178 to 218."),
        "checks": [
            "addendum.py: my values for the 44 matches (addendum_rows.csv): MatchBeats' completed non-tiebreak games, "
            "the score's alternation, the row's count, Court Vision and the charts; all eighteen values equal the "
            "amended rows (44/44); MatchBeats equals the alternation on 42/42 complete matches; my eight counts equal "
            "the row's on 32/32 added matches (addendum_summary.json)",
            "addendum_scope.py: the tests per match, 44/44 pass (addendum_tests.csv, addendum_scope.json); "
            "overrides_scope.csv rebuilt from overrides_scope_v1.csv (12 rows replaced, 32 appended), 1,541 rows, equal "
            "to the amended proposed_overrides.csv on every cell",
            "extract.py (amended candidate): whole_box.candidate_tables equals my own construction; on the whole raw "
            "frame 2,272 override rows (1,541 RG, 731 decided) read their tables, 3,297 rows change, 0 outside the "
            "tables, no override row also corrected, 4/4 exchanges read exchanged (extract_summary.json; round 2's in "
            "extract_summary_v1.json)",
            "simulate.py --scope: the amended candidate and my scope give the same box status on 3,784/3,784 RG "
            "2019-2026 and Olympic rows; full boxes 3,721 -> 3,745, service-games-missing rows 33 -> 9, B5 failures "
            "11 -> 10; no row loses a usable box; none of the 44 fails a check (B8 included); of the 44, 24 go from no "
            "service games to a full box, 17 stay full, 3 (2026 main-draw retirements) go from blank to full as in "
            "round 2 (sim_scope_summary.json; brought_back.csv: 20 W22 rows and 347 W26 rows brought back)",
            "rates.py: pooled rates with the amended candidate (rates_by_edition.csv; round 2's in rates_by_edition_v1.csv)",
        ],
    }
    of = v["other_findings"]
    of = of.replace("2. Scope gap (not an error):",
                    "2. Scope gap (not an error; addressed by the amended proposal, see the addendum):")
    of = of.replace("3. Retirement convention:", "3. Retirement convention (addressed by the amended proposal, see the addendum):")
    of = of.replace("8. Evidence files in this folder:",
                    "8. Evidence files in this folder (round-2 versions of the files the addendum reran are kept as *_v1):")
    of = of.replace("scope_notes.csv, scope_summary.json;",
                    "scope_notes.csv, scope_summary.json, addendum_rows.csv, addendum_summary.json, addendum_tests.csv, "
                    "addendum_scope.json;")
    of = of.replace("make_scope, simulate --scope, verdict).",
                    "make_scope, simulate --scope, verdict; for the addendum: addendum, addendum_scope, extract, simulate, "
                    "simulate --scope, rates, verdict, addendum_verdict).")
    of += (" 9. The one equal-class match the amended proposal leaves out (Baez d. Heide, RG 2024 R128, mb_contradicts): "
           "RG's statistics and MatchBeats differ by one point on Heide's first-serve points won (40 against 39), a count "
           "the override would leave as it is; only Baez's service games would change (22 to 23: the row's 22 and 22 make "
           "44 in a 45-game match without a tiebreak, and MatchBeats and the alternation give 23 and 22). It could be in "
           "on the service games alone; not proposed, so not voted.")
    v["other_findings"] = of
    p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: (x.get("vote"), x.get("bar")) for k, x in {**v["groups"], "addendum": v["addendum"]}.items()},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
