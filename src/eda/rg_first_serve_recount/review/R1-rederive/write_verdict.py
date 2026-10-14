"""R1-rederive: write verdict.json (the brief's format, section 8). The numbers quoted come from my scripts in this
folder (printed by them; tables in data/studies/rg_first_serve_recount/review/R1-rederive/).
Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/write_verdict.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"
SRC = "src/eda/rg_first_serve_recount/review/R1-rederive/"

COMMON_CHECKS = [
    f"{SRC}parse_sources.py: parsed all 3,290 rolandgarros.com documents of 2019-2025 myself (3,274 with statistics); "
    "every team of every document passes the record's own checks (1st/2nd-serve denominators, receiving points = the "
    "opponent's serve points, total points = serve + return points won). Decrypted every RG MatchBeats file "
    "(2019-2024 match-beats, 2025 match-centre; 3 empty, 8 absent) and the AO 2025 files with the adapter's decrypt/"
    "blocks_of and recounted every point myself; parsed all 125 Olympic results files and recounted their "
    "play-by-play.",
    f"{SRC}link_compare.py: read Sackmann's raw CSVs with the csv module (row numbers from 1 after the header; equal "
    "to the staged copies' _row and to every count of the staged copies); linked all 3,290 RG documents and all 125 "
    "Olympic units to Sackmann rows by names within year/tour/round (optimal assignment), each link checked by the "
    "games of every set and the winner; every name pair below an exact match reviewed by hand.",
]

verdict = {
    "reviewer": "R1-rederive",
    "lens": "rederive",
    "recount_validated": {
        "vote": "yes",
        "reasons": (
            "Recomputed from the raw files with my own code; no code or table of the study was read before my values "
            "existed. C1: at the AO 2025 my MatchBeats recount equals Sackmann's (Stage 0's) first serves in, "
            "first- and second-serve points won on all 718 sides of the 359 matches whose file holds every point of "
            "both players; the other 110 files miss points (106) or hold 1-3 extra (4). With completeness judged per "
            "side instead of per match I reproduce the lead's ao_check.csv exactly (one exception, MQ159 Blanchet, in "
            "a file with 3 extra points on the other serve). The Olympic play-by-play equals the Olympic statistics on "
            "239 of 240 player rows of complete units; the exception is Carle (R32-0016: 2nd-serve points won 8 vs 7), "
            "so C1's Olympic sentence holds for first serves in, not for every count. C2: RG's statistics equal my "
            "MatchBeats recount on 1stIn, 1stWon and 2ndWon on all 6,468 team rows (2019-2025) whose file holds every "
            "point of both players (aces too; DFs differ by 1 on 3 rows of 2019-21); RG 2025's key statistics equal "
            "the statistics' split on all 930 team rows where they hold every point. C3: 2019-2021, 2,732 of 2,740 "
            "linked player rows equal on all eight counts; the other "
            "8 are the four 2021 WTA matches named by the lead, equal once the two boxes are exchanged (16 rows have no "
            "Sackmann box). Beyond the claims: RG's own pooled first-serve-in rate is stable 2019-2025 (61.2-65.2%) "
            "while Sackmann's breaks in 2022 (qualifying +3.4 to +6.0 points, main draw +0.5 to +2.8, Olympics "
            "+5.6/+6.3); the radar check below never contradicts the official split."
        ),
    },
    "classes": {
        "RGFSA": {
            "vote": "narrow",
            "corrupt_beyond_doubt": True,
            "fix_clear_and_correct": True,
            "scope": (
                "Every class-A side of the proposal (all three signs, no minimum size: 1,337 of the lead's 1,340 "
                "sides, 854 match rows) with my values (equal to the lead's on every one), except the '-' and '0' "
                "sides for which the venue's own point record does not itself show Sackmann's split impossible "
                "(test T5: one of its four cells - first serve won/lost, second serve won/lost - holds more points "
                "than Sackmann's). Left out: RG 2025 QM079 Coria (w, '0', no MatchBeats file), QM034 Erhard (l, '0', "
                "no file), QM122 Dellien Velasco (l, '0', partial file inside both readings). Tests on every side: "
                "T1 link verified, T2 official checks pass for both players, T3 class A by my own comparison, T4 the "
                "point record contradicts the official split for neither player (full: equal; partial: no cell above "
                "the official's)."
            ),
            "reasons": (
                "The rows are corrupt: (1) the official record measures what Sackmann measures (C3, 2019-21 exact on "
                "all eight counts); (2) from 2022 Sackmann departs from it, mostly by the split alone (1,433 class-A "
                "and 191 class-B RG sides of 3,824), with the moved points on '+' sides won at 0.494 (the official "
                "second-serve rate on those "
                "sides is 0.479, first-serve about 0.65): second-serve points booked as first serves; (3) RG's point "
                "log equals RG's statistics in full on 1,595 of the 1,624 RG A/B sides and never contradicts them "
                "(15 partial files lie inside the official cells, 2 hold one extra point, 12 sides have no file); "
                "(4) radar: in "
                "2023-25 MatchBeats records the speed of a faulted first serve; on 568 of 903 '+' sides the points "
                "with a measured fault outnumber Sackmann's second-serve points (Sackmann impossible), covering 3,189 "
                "of the 4,608 moved points, including 114 of 290 '+1' sides; the same bound never exceeds the official "
                "count (0 of 1,079 disputed sides) nor the agreed count on 1,469 equal sides; (5) hand-charted MCP "
                "(light check, sides with MCP serve points within 1): MCP equals the official 1stIn on 124 of 153 "
                "disputed sides and Sackmann's on 18 (control: 82% exact on equal sides); '+1' sides 41:7. The '-' "
                "(176) and '0' (55) sides are the same family, not another error: they occur only in the fault "
                "editions (none in 2019-21 or at the AO 2025), sit in the same matches as '+' sides, '0' sides prove "
                "two-way misassignment, and MCP sides with the official on RG '-' sides 16:2 and on '0' sides' "
                "first-serve points won 5:0 (MCP noise explains the 2). It does not matter for the fix (same "
                "operation, same values), but because they run against the named fault I require the point record "
                "itself to refute Sackmann for them (T5). No minimum size: +1 and -1 sides are supported as above."
            ),
            "checks": COMMON_CHECKS + [
                f"{SRC}link_compare.py -> sides.csv: my classes equal the lead's on every side except 73 sides the "
                "lead labels 'other' and I label 'points' (serve points differ while the split agrees; neither "
                "proposes them) and 2024 QM126, which the lead left unplaced.",
                f"{SRC}evidence.py: radar bound (radar_sides.csv), pooled rates (pooled_rates.csv), moved-point win "
                "rates, class-B make-up, and Stage 0's B1-B3, B6, B7 plus 2ndWon + df <= svpt - 1stIn on every "
                "corrected side (0 failures).",
                f"{SRC}mcp_check.py: MCP referee on linked sides (mcp_sides.csv).",
                f"{SRC}speeds.py: on RG 2023-25 '-' sides, serve-1 points at second-serve speeds are slightly more "
                "common (2.98 vs 2.06 per side on equal sides); this fits either reading (Sackmann's source booking "
                "slow first serves as second serves, or RG mislabelling) and is not used for or against the fix.",
                f"{SRC}scope.py: tests T1-T5 per side (scope_all.csv); {SRC}apply_check.py: my scope applied in "
                "memory with the project's replace_split to the staged rows: 1,069 rows found by their guards, the "
                "three counts equal mine, serve points/aces/DFs/serve points won and every other column unchanged, "
                "B1-B3, B6, B7 pass.",
                f"{SRC}compare_proposal.py -> compare_sides.csv: on the 1,713 sides in both sets my values equal the "
                "lead's (0 differences) and the fix ids agree; the lead's guards (svpt, ace, df, tourney_id, round, "
                "names) equal the raw rows on all 1,718 proposed sides.",
            ],
        },
        "RGFSB": {
            "vote": "confirm",
            "corrupt_beyond_doubt": True,
            "fix_clear_and_correct": True,
            "scope": (
                "All 282 sides (157 match rows) of the proposal, with my values (equal to the lead's), under the same "
                "tests T1-T5 (all pass). My scope.csv also lists 2024 QM126 (Kolar d. Faurel; Sackmann names the "
                "loser 'T. Farquhar'), 2 sides the proposal does not hold - see other_findings."
            ),
            "reasons": (
                "The split part is the same fault as class A (191 RG B sides: 184 '+', 5 '-', 2 '0'; every '-'/'0' "
                "side refuted by the point record). The other differing counts are aces (79 B sides overall), DFs "
                "(179, Sackmann mostly lower; 4 WTA 2022 sides have Sackmann's DFs blank) and break points (6). "
                "Correcting only the split is a clear, unique fix: the values are the official split, the operation "
                "keeps serve points, aces, DFs and serve points won, Stage 0's rates that use aces and DFs (per serve "
                "point) are untouched, and every corrected side passes B1-B3, B6, B7 and the stricter 2ndWon + df <= "
                "svpt - 1stIn. It leaves known errors: on all 231 B sides with a full point record the record takes "
                "the official ace and DF counts, so Sackmann's differing ace/DF counts are wrong too and stay wrong "
                "(a separate operation would be needed; DF per second serve moves slightly closer to the official on "
                "average, 0.066 -> 0.057 mean absolute error)."
            ),
            "checks": COMMON_CHECKS + [
                f"{SRC}evidence.py: class-B make-up and the corrected-side checks (0 failures).",
                f"{SRC}apply_check.py and {SRC}compare_proposal.py as for RGFSA.",
            ],
        },
        "OGFSA": {
            "vote": "narrow",
            "corrupt_beyond_doubt": True,
            "fix_clear_and_correct": True,
            "scope": (
                "37 of the lead's 39 sides (25 of its 26 match rows), my values equal to the lead's. Left out: "
                "Fernandez (R64-0012, w, '-1': the Olympic play-by-play is partial for her serve, 81 of 87 points, "
                "and does not refute Sackmann's 59 first serves in; MCP also reads 59) and Gauff (R32-0016, w, '-1': "
                "the play-by-play contradicts the official statistics on Carle's serve in the same match, which the "
                "lead also drops; I do not take a match whose two official records disagree as beyond doubt for a "
                "side running against the named fault)."
            ),
            "reasons": (
                "The Olympic results file is the right reference: status OFFICIAL, and its own checks hold on all 124 "
                "played units (PTS_WON_SERVE = 1st + 2nd won over the serve points, 2ND_SERVE attempts = serve points "
                "- first serves in, DBL_FAULT = 2nd attempts - 2nd in, RECEIVE attempts = the opponent's serve "
                "points, POINTS = serve + return won, ACES = 1st + 2nd-serve aces); its play-by-play equals it on 239 "
                "of 240 complete player rows; it measures what Sackmann measures (97 sides equal on all eight "
                "counts). No clean edition exists, but Sackmann's Olympic rows carry the RG 2022-25 signature: pooled "
                "first serves in +5.6/+6.3 points against the file, moved points won at 0.491 against the official "
                "second-serve rate of 0.492. The '-' (13) and '0' (7) sides occur at about the share seen at RG "
                "('-': 5.2% of Olympic sides vs 4.7% of RG 2022-25 sides); MCP cannot referee the Olympics (59% exact "
                "on equal sides), so I rely on the "
                "official play-by-play refuting Sackmann for every '-'/'0' side I keep (T5)."
            ),
            "checks": COMMON_CHECKS + [
                f"{SRC}parse_sources.py / link_compare.py: Olympic statistics and play-by-play recount; links "
                "(links_ol.csv): all 125 units, names, games and winners agree; the 3 Sackmann rows without a unit "
                "(Shnaider-Cocciaretto, Swiatek-Wang, Zheng-Kerber) are not proposed.",
                f"{SRC}scope.py, apply_check.py, compare_proposal.py as for RGFSA.",
            ],
        },
        "OGFSB": {
            "vote": "confirm",
            "corrupt_beyond_doubt": True,
            "fix_clear_and_correct": True,
            "scope": "All 57 sides (32 match rows) of the proposal, my values equal to the lead's; tests T1-T5 pass.",
            "reasons": (
                "Same reference and evidence as OGFSA; the B sides (41 '+', one '-' and one '0', both refuted by the "
                "play-by-play) differ also in aces or DFs, which the operation leaves as Sackmann has them (see "
                "RGFSB); every corrected side passes Stage 0's split checks."
            ),
            "checks": COMMON_CHECKS + [f"{SRC}scope.py, apply_check.py, compare_proposal.py as for RGFSA."],
        },
    },
    "other_findings": (
        "1. Link the lead left unplaced: 2024 QM126 (links.json 'unplaced_matches'), Sackmann "
        "atp_matches_qual_chall_2024.csv row 683, Zdenek Kolar d. 'T. Farquhar' (USA, id 212408, no age) 6-7(3) 6-4 "
        "6-3 Q1, is RG's Kolar d. Thomas Faurel (FRA, WC) 6-7 6-4 6-3: the same fault (Kolar A+ 59 vs 54, Faurel B+ 64 "
        "vs 63, DF 1 vs 2; MatchBeats complete and agreeing; radar refutes Sackmann on both). It is in my scope.csv "
        "(fix RGFSB) but not in the proposal. 2. Sackmann identity slips outside this fix: 'T. Farquhar' (id 212408) "
        "is Thomas Faurel; RG 2023 'Eduardo Nava' (id 124013; QM082, QM041, QM020, SM078) is Emilio Nava per RG (the "
        "matches link by opponent, games and winner). 3. Sackmann's Paris Olympics R32 walkover (atp_matches_2024.csv "
        "row 2011) reads 'Struff d. Moutet W/O'; the Olympic file has Moutet the winner, and Sackmann's own R16 row "
        "has Moutet playing Paul: winner and loser reversed (no box, outside this fix). 4. RG's statistics are not "
        "infallible: on 8 'points' sides of 2024 qualifying (QM107, QM114, QM118, QM119, QD071, QD080, QD108, QD109) "
        "RG's statistics lack one serve point (apparently the last of the match) that MatchBeats and Sackmann both "
        "hold, on 2025 SM078 (Monfils) they hold one more than both, and on 2025 QM083 Kotov and QM088 Fognini (proposed "
        "'+' sides) MatchBeats holds one point more than both the statistics and Sackmann; neither touches a proposed "
        "value (the corrected split keeps the serve points the statistics and Sackmann share, and the official cells "
        "lie inside MatchBeats'). 5. 2024 SM123 (Heide, an equal side): one MatchBeats point has scorer '0' and "
        "result 'N'; I skip it, the lead counts it, hence its 'contradicts' flag there (no effect on the proposal). "
        "6. Class B leaves ace/DF counts that the point record shows are Sackmann errors (179 DF, 79 ace "
        "differences); a later replace of those counts would be a different operation. 7. Labels only: the lead "
        "calls 73 sides 'other' (split equal, serve points differ) that I call 'points'; neither proposes them. "
        "8. The RG 2019 QD087 document (Zavatska-Haddad Maia) has the two players' games reversed against "
        "Sackmann's score although both boxes agree (control year, outside the fix)."
    ),
}

(HERE / "verdict.json").write_text(json.dumps(verdict, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("written", HERE / "verdict.json")
