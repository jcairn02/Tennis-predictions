"""B3-referee: writes data/studies/input_data_audit/fixes/B3-referee/verdict.json (the vote on F7-F17 and the
"already handled" items). Every number below was computed by the scripts in this folder; the files are named in
`checks`. Run after f7_identity.py, f8_f10_ages.py, f11_f13_odds.py, f14_f16_speed.py, f16_chance.py, f14_strict.py,
f14_broad.py, f14_scope_sim.py and write_scopes.py.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
D = "data/studies/input_data_audit/fixes/B3-referee"
OUT = ROOT / D / "verdict.json"

V = {
    "F7": {
        "vote": "confirm_narrowed",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("11 of the 13 pairs: wta:315232->wta:201548 (Tomljanovic), wta:320319->wta:211713 (Cristian), "
                  "wta:324261->wta:215035 (Yastremska), wta:330332->wta:223253 (Eala), wta:322082->wta:214082 (Kasatkina), "
                  "wta:328897->wta:221236 (Polina Kudermetova), wta:328884->wta:222391 (Boisson), wta:332718->wta:260765 "
                  "(Oktiabreva), wta:321837->wta:215386 (Vivian Wolff), atpcode:M0VL->atp:149128 (Goncalo Marques), "
                  "atpcode:C0UQ->atp:214346 (Tran Quoc Cuong): 20 player rows in 19 Stage 0 matches, 60 id fields. "
                  "EXCLUDED: atpcode:O0A6 (Benjamin O'Connell) and atpcode:M0PF (Bernardo Munk Mesa): same person, but "
                  "Sackmann itself holds two ids for each (atp:206736 + atp:213206; atp:210458 + atp:212827), so the "
                  "target id is not unique and repair_tables refuses the case ('multiple canonical players share exact name')."),
        "scope_file": f"{D}/scope_F7.csv",
        "fix": ("Replace the new id by the established id in every Stage 0 field that holds it: player_id on the player's "
                "own row, opponent_id on the opponent's row, player_a_id/player_b_id on stage0_matches (rows listed in "
                "scope_F7.csv). match_id strings are left unchanged (repair_tables' convention: stable handles)."),
        "reasons": ("Each of the 9 new women's ids is the WTA's own player id, and the WTA API (data/dump/points/wta/"
                    "matches/<year>.parquet) puts that id on matches Stage 0 holds under the established Sackmann id, "
                    "same opponent and week: Tomljanovic 229/256, Cristian 217/253, Yastremska 259/284, Eala 140/166, "
                    "Kasatkina 313/329, Kudermetova 128/167, Boisson 45/60, Oktiabreva 10/12, Wolff 3 (Cleveland 2025 Q1 "
                    "v Gibson 6-2 6-1, Guadalajara 2025 Q1 v Inglis, Austin 125 2025 R32 v Mandlik 6-2 6-1, exact scores); "
                    "every new-id Stage 0 match is in the WTA API under the new id. The country 'conflicts' are real "
                    "nationality changes the WTA API itself records (Kasatkina RUS->AUS, Kudermetova RUS->UZB, Oktiabreva "
                    "RUS->CZE, Wolff USA from 2025). For 7 women the garbage TML ages decode exactly to the age from the "
                    "Sackmann dob of the established id (F8). Marques: TML ATP code M0VL dob 2006-01-07 = Sackmann 149128 "
                    "dob; TML ages = (date-dob)/365.25 to the day; POR=PRT; the other Portuguese Goncalo Marques (dob "
                    "2006-11-18, Zenodo) is not in Stage 0. Tran: TML age 19.699 on 2026-09-07 = Sackmann 214346 dob "
                    "2006-12-26 to the day; VIE=VNM; same three name tokens; both events at Phan Thiet. Simulated alias on "
                    "the 7 Oct Stage 0 (all 13 pairs): 0 matches with one id on both sides, 0 new 'twice in one round', "
                    "0 new 'two events in one week'. repair_tables run in memory on the 7 Oct tables resolves none of the "
                    "13 (demographic conflict x10 from garbage ages or country codes, multiple canonical ids x2, word "
                    "order x1), so the split persists without this fix."),
        "checks": [
            f"{D}/f7_evidence.json (src/eda/input_data_audit/review/B3-referee/f7_identity.py): ids per name key, "
            "Sackmann/TML/Zenodo dobs and countries, WTA API cross-match counts, alias simulation, repair_tables in memory",
            "Stage 0 ids holding each sorted name key: exactly the established and the new id for the 11 confirmed pairs; "
            "3 ids for O'Connell (atp:206736, atp:213206, atpcode:O0A6) and Munk Mesa (atp:210458, atp:212827, atpcode:M0PF)",
            "Sackmann dob of atp:206736 1999-03-31 = TML O0A6 dob; atp:213206 has no dob; Zenodo links its 1999-03-31 "
            "O'Connell to 213206 -> person one, target ambiguous",
            "Sackmann dob of atp:210458 and atp:212827 both 2006-02-13 = TML M0PF dob; Zenodo links to 210458 -> target ambiguous",
            "alias simulation: same_id_both_sides 0, new twice_in_round 0 (4,044 pre-existing), new two_events_same_week 0 (2,961 pre-existing)",
            "TML age convention verified: (date - dob).days/365.25 reproduces 19.699, 20.646, 20.641, 27.439, 33.087 exactly",
        ],
    },
    "F8": {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("The 12 Stage 0 rows with age > 90 (exactly 12 exist): TML 2026 WTA, 8 June 2026, Queen's Club and "
                  "'s-Hertogenbosch, raw data/raw/public_dump/tennis_my_life/2026_wta.csv rows 1270-1321; Cristian x2, "
                  "Kasatkina, Kudermetova, Boisson, Tomljanovic x3, Yastremska x2, Eala x2."),
        "scope_file": f"{D}/scope_F8.csv",
        "fix": "age := missing on those 12 rows (only if F8b is not executed; F8b is preferred).",
        "reasons": ("Ages of 2,143-3,387 are impossible and are in TML's raw CSV as printed (e.g. 'Jaqueline Cristian,...,ROU,2808'). "
                    "Blanking is the conservative correct fix, but the true value is known exactly (F8b)."),
        "checks": [f"{D}/f8_rows.csv: Stage 0 age > 90 -> 12 rows, all TML, all 2026-06-08",
                   "raw TML 2026_wta.csv rows read: the garbage is in the source; the same file gives Tomljanovic 33.087 on her SF row"],
    },
    "F8b": {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": "Same 12 rows as F8.",
        "scope_file": f"{D}/scope_F8.csv",
        "fix": ("age := round((2026-06-08 - Sackmann dob of the established id).days / 365.25, 3), TML's own convention: "
                "Cristian 28.008, Kasatkina 29.087, Kudermetova 23.012, Boisson 23.064, Tomljanovic 33.087, "
                "Yastremska 26.064, Eala 21.043 (column F8b_value). Does not need F7 to be executed first."),
        "reasons": ("Doubly determined: each garbage value is the correct age with its decimal point and the fraction's "
                    "leading zero dropped (2808 = 28.008, 2987 = 29.087, 2312 = 23.012, 2364 = 23.064, 3387 = 33.087, "
                    "2664 = 26.064, 2143 = 21.043) and each equals (date - Sackmann dob)/365.25 exactly (12/12). TML's "
                    "own 's-Hertogenbosch SF row gives Tomljanovic 33.087, the same value. Sackmann dobs agree with the "
                    "Zenodo players file (e.g. Cristian 1998-06-05, Eala 2005-05-23)."),
        "checks": [f"{D}/f8_rows.csv: decode_matches_dob_age True on 12/12",
                   f"{D}/f8_f10_summary.json F8: later TML rows of these players match the dob within 0.015 y (match-day vs tournament-day dating)"],
    },
    "F9": {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("All 182 player rows of ATP Prague CH (2020-600) and Todi CH (2020-8392), both dated 2020-08-17, "
                  "Sackmann source; 93 players, every one with a Sackmann dob. No other rows."),
        "scope_file": f"{D}/scope_F9.csv",
        "fix": ("age := floor(10 * (2020-08-17 - Sackmann dob).days / 365.25) / 10 (Sackmann's convention; column "
                "age_new_floor_1dp; e.g. Alcaraz 16.8 -> 17.2). The date stays."),
        "reasons": ("The age is wrong, not the date: stored - exact = -0.473 y on all 182 rows (SD 0.027, range -0.52 to "
                    "-0.42; none within 0.2), while the next weeks (24 Aug, 31 Aug, 7 Sep) and pre-suspension weeks read "
                    "-0.05 (the floor convention's bias); Tennis My Life independently holds both events in that week "
                    "with ages ~0.47 higher (Alcaraz 17.303, Wawrinka 35.403, Karatsev 26.965 vs stored 16.8, 34.9, 26.5); "
                    "no Challenger was played between March and 17 Aug 2020. The stored ages correspond to 2020-03-16 "
                    "(median implied date), the ATP ranking freeze (inferred cause). Not in the model frame."),
        "checks": [f"{D}/f9_rows.csv, {D}/f8_f10_summary.json F9 (stored-exact distribution, implied date, rounding)",
                   "Sackmann rounding on 2,561 other 2020 Sackmann rows of the same players: floor-to-0.1 matches 2,507",
                   "TML 2020 challenger file: Prague 2020-08-22 and Todi 2020-08-23 rows with August ages"],
    },
    "F10": {
        "vote": "confirm_exclusion",
        "corrupt_beyond_doubt": False,
        "fix_clear_and_correct": False,
        "scope": ("Leave all: Gail Falkenberg (dob 1947, 11 ITF Q1 rows, real), Elizabeth Ernest (dob 1946, 2 ITF rows "
                  "2013), Anna Nemeth (dob 1953, 2 ITF Q1 rows 2022), Yue Yuan (2010-11 ITF rows at 11.5-12.9 that fit "
                  "the dob of the WTA's Yuan Yue b. 1998-09-25: an identity question, not an age), Leila Fabbri (dob "
                  "2007-12-20, 12.0) and Geetaarthi Sunaina Gaba (dob 2008-09-01, 11.3) in Jan 2020 ITF Q1, Elizabeth "
                  "Jones (dob 1964, WTA 125 R32 2026), Raul Sanchez (dob 1954, M15 R32 2026)."),
        "scope_file": None,
        "fix": "None.",
        "reasons": ("Every flagged age equals (date - Sackmann dob) within 0.1 y, so the ages are computed correctly from "
                    "the dob; where a value is implausible (11-12 at ITF events, 62-72 in pro main draws) the error is in "
                    "the dob or the identity, whose true value no held source gives. Some are real (Falkenberg). None is "
                    "in the model frame."),
        "checks": [f"{D}/f10_players.csv: dob, every Stage 0 row of the player, ages fit dob within 0.1 on all rows"],
    },
    "F11": {
        "vote": "confirm_narrowed",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("4 Stage 1 rows: Chennai 2013 SF (atp|2013-891|SF|atp:104386|atp:105379; tennis_data_couk/atp/atp250/"
                  "2013.parquet row 51) and Wimbledon 2016 F (atp|2016-540|F|atp:104918|atp:105683; atp/grand_slam/"
                  "2016.parquet row 380): exchange Avg AND Max; Adelaide 2 2022 R32 (wta|2022-2030|R32|wta:201603|"
                  "wta:216146; wta/wta500/2022.parquet row 34) and 's-Hertogenbosch 2025 F (wta|2025-822|F|wta:210722|"
                  "wta:211817; wta/wta250/2025.parquet row 278): exchange Avg only. EXCLUDED: Cluj-Napoca 2024 R32 "
                  "(Avg = Max, the exchange still leaves it 0.18 from the two books; ranks/Elo side with the Avg) and the "
                  "5 single-book 'reversed' rows (Berlin 2023, Budapest 2023, Metz 2024, Miami 2019, Bad Homburg 2021: "
                  "there B365 is the reversed one; Avg agrees with ranks/Elo)."),
        "scope_file": f"{D}/scope_F11.csv",
        "fix": ("Stage 1: avg_a <-> avg_b on the 4 rows (equivalently AvgW <-> AvgL on the raw row as linked), and max_a "
                "<-> max_b on the first two; p_avg_a := 1 - p_avg_a (an exchange leaves the overround unchanged: 1.061, "
                "1.046, 1.059, 1.059). Only p_avg_a reaches the model (in_odds_logit == logit(p_avg_a) on all 63,737 rows)."),
        "reasons": ("On each raw tennis-data row the stored average is the mirror of every individual book: Chennai p(Bedene) "
                    "0.827 vs B365/PS/EX/LB/SJ 0.157-0.196 -> 0.173 after; Wimbledon p(Raonic) 0.759 vs 0.224-0.263 -> "
                    "0.241; Adelaide p(Kostyuk) 0.642 vs 0.346/0.364 -> 0.358; 's-Hertogenbosch p(Ruse) 0.656 vs "
                    "0.331/0.344 -> 0.344. Impossibility evidence: stored Max below every book's price for the underdog "
                    "(Chennai 1.17 for Bedene vs books 4.75-6.16; Wimbledon 1.30 for Raonic vs 3.5-4.36) and, after "
                    "exchange, Max >= every book on both sides; on Adelaide and 's-Hertogenbosch the stored Avg exceeds the "
                    "stored Max (2.64 > 1.53; 2.74 > 1.50) and after the exchange Avg <= Max on both sides with Max "
                    "agreeing with the books. Links are sound (same set scores, rounds and ranks agree). Note: the "
                    "candidate text says 'Bedene d. Tipsarevic' but Tipsarevic won 4-6 6-2 6-2 (Stage 0 and tennis-data agree)."),
        "checks": [f"{D}/f11_f13_rows.csv (every flagged row v its raw row: per-book p, Avg/Max checks before and after exchange)",
                   f"{D}/f11_stage1_scan.csv: whole 7 Oct Stage 1 scanned; in the model frame only these 4 + Cluj 2024 show Avg opposed by >= 2 agreeing books",
                   "Same signature outside the frame and outside the candidate (not voted): SAP Open 2011 F, US Open 2010 SF, RG 2011 F",
                   "model frame in_odds_logit vs logit(30 Sep Stage 1 p_avg_a): max abs diff 2.2e-16; the 4 rows unchanged 30 Sep -> 7 Oct"],
    },
    "F12": {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("1 Stage 1 row: Nottingham 2017 F, wta|2017-1080|F|wta:202427|wta:202499, tennis_data_couk/wta/"
                  "international/2017.parquet row 553 (link winner_swapped)."),
        "scope_file": f"{D}/scope_F12.csv",
        "fix": ("Exchange every price pair on that Stage 1 row (avg, max, ps, b365: A <-> B), so Konta (A) gets 1.17 and Vekic "
                "4.98; p_avg_a 0.190 -> 0.810."),
        "reasons": ("Only the names are swapped in tennis-data: the row's Winner 'Konta J.' carries WRank 75 (Vekic's rank; "
                    "Konta was 8th), the winner's set scores 2-6 7-6 7-5 (Vekic's, who won 2-6 7-6(3) 7-5 per Stage 0) "
                    "and the underdog prices (B365 5.00, PS 5.77, EX 4.75, LB 5.00, Avg 4.98, Max 6.00); Loser 'Vekic D.' "
                    "carries LRank 8. Stage 1's rank_agrees is False on both sides. Every W-column value belongs to Vekic, "
                    "so the prices belong to her."),
        "checks": ["raw row read: WRank 75 / LRank 8, W1-L1 2-6, 7-6, 7-5, Wsets 2", f"{D}/f11_f13_rows.csv"],
    },
    "F13": {
        "vote": "confirm_exclusion",
        "corrupt_beyond_doubt": False,
        "fix_clear_and_correct": False,
        "scope": ("Leave every other flagged odds row. The 2 a04 rows that are also a07 'reversed' (Adelaide 2 2022 R32, "
                  "'s-Hertogenbosch 2025 F) are corrupt with one clear fix and are confirmed under F11 (scope_F11.csv)."),
        "scope_file": None,
        "fix": "None for the remaining rows.",
        "reasons": ("a04 (23 rows): in the other 21 the Avg agrees with PS/B365 and the Max is the odd value (e.g. Rome 2024 "
                    "R128 Max 1.75 < Avg 2.57 and PS 2.75); the Max does not reach the model. Placeholders: the two "
                    "Washington 2026 finals are already proper rows in the 7 Oct Stage 1 (name_pair, Completed, same set "
                    "scores); the other a06 rows are retirement/status mismatches with prices that follow the names. "
                    "Single-book reversals: the book (B365) is the reversed one. Garbled rows: no unique fix; the strongest "
                    "(Canada 2022 R64 Avg 13.75/1.02 vs books ~0.28 for Giron; Doha 2024 R64 Avg = Max opposed by 2 books) "
                    "would need a policy choice (blank vs exchange vs another book)."),
        "checks": [f"{D}/f11_f13_rows.csv (77 flagged match_ids, all present in the 7 Oct Stage 1)",
                   "7 Oct vs 30 Sep Stage 1 for the Washington 2026 finals: winner_swapped placeholders -> name_pair rows"],
    },
    "F14": {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("Settled rule: a key-statistic record (handoff_ks or mantennisdata) whose first-serve average y_raw >= "
                  "its own spd_max - 1 km/h, where spd_max is the SAME record's fastest serve of the SAME player (the "
                  "panel's field; not the match's maximum), applied to every record chosen or not: 136 records = 82 strict "
                  "(y_raw > spd_max, all handoff_ks) + 32 equal + 22 within 1 (column 'tier'); 108 of them are panel use "
                  "rows (79 handoff, 29 ManTennisData = the audit's 108). No extra n threshold (the panel already drops "
                  "n < 10). If the other reviewers confirm only the strict tier, I confirm that subset too."),
        "scope_file": f"{D}/scope_F14.csv",
        "fix": ("Mark each listed record not a candidate (invalid_reason, as the mislink rules), so the player-match takes "
                "its next valid record by the panel's precedence, else no speed. Simulated with panel.choose(): of the "
                "108 use rows, 76 fall back to an independent point mean (infosys), 32 lose their speed; none falls back "
                "to another key statistic (the twin copies are flagged too)."),
        "reasons": ("An average cannot exceed the maximum of the same serves, and with n >= 10 first serves it cannot sit "
                    "within 1 km/h of it. Against an independent point mean of the same player-match, unflagged key "
                    "statistics read ks - pm = +0.52 (p10 -0.51, p90 +1.68; 19,714 records), flagged strict ones +25.0 "
                    "(p10 +15.7; 62 checkable, all > 5) and flagged equal/within-1 ones +17.2 (p10 +10.4; 30 checkable, all "
                    "> 5): the average is the wrong field, and in the equal/within-1 records it equals the point data's "
                    "MAXIMUM within 1-2 km/h (the average field holds the max). The removed values sit a median 26.0 km/h "
                    "from the player's norm; the fallbacks 4.4."),
        "checks": [f"{D}/f14_rows.csv, {D}/f14_strict_summary.json (ks - point mean by tier), {D}/f14_variants.json, "
                   f"{D}/f14_scope_sim.json (fallback simulation), {D}/scope_F14.csv",
                   "panel.py read: handoff spd_max = keystats 'Max Speed' per player; ManTennisData spd_max = ks_max per player row",
                   "the audit's 108 use rows reproduced: y_raw >= spd_max - 1 on speed_panel use rows"],
    },
    "F15": {
        "vote": "confirm",
        "corrupt_beyond_doubt": True,
        "fix_clear_and_correct": True,
        "scope": ("The 14 men's records with y >= 240 km/h (242-270 raw): all handoff_ks panel use rows, all in F14's "
                  "strict tier; no other record of any source reaches 240 (men) or 210 (women)."),
        "scope_file": f"{D}/scope_F15.csv",
        "fix": "As F14 (not a candidate; next valid record).",
        "reasons": ("33-102 km/h above the player's own norm (e.g. 270 v 167.5); physically impossible as a first-serve "
                    "average. Fallback simulated: 9 take an infosys point mean, 8 of them within -9..+11 km/h of the "
                    "player's norm; the 9th (Rennes CH 2023, atp:131911, 168.8 v a 'norm' of 210.5 built from his other bad "
                    "Rennes row) sits on his 2026 level of 162-169 km/h; 5 lose their speed."),
        "checks": [f"{D}/f15_rows.csv", f"{D}/f14_f16_summary.json F15"],
    },
    "F16": {
        "vote": "reject",
        "corrupt_beyond_doubt": False,
        "fix_clear_and_correct": False,
        "scope": "None. (Not the 5 same-player pairs, not the 12 both-sides matches.)",
        "scope_file": None,
        "fix": "None.",
        "reasons": ("The blocks are chance coincidences of integer statistics, not copies. Same player: 202 pairs of use "
                    "rows share (avg, 2nd avg, max); 5 of them also share n, where chance predicts 4.2 (2.1% of a player's "
                    "match pairs share n). Every record's own first_total matches its own match's box score (svpt), and "
                    "independent point data confirm both of Rune's 'copies' (Tokyo 2024 infosys 192.0/165.1/214; Indian "
                    "Wells 2025 F sirgenkii 193.2/165.7/213). Both sides: ManTennisData 8 matches v 11.1 expected by chance; "
                    "infosys point means confirm both sides at Rotterdam 2024 R32 (207.8/207.8) and Canada 2024 R32 "
                    "(190.9/189.9), so dropping both would delete good values. Separate defects seen (not this candidate, "
                    "not voted): Shanghai 2024 R128 key statistics carry the pooled match average (198 both; points "
                    "193.3/202.2; pooled ceiling 198), Miami 2025 R64 Rublev's ManTennisData record carries Bergs's average "
                    "with swapped counts; AO 2026 match centre shows 4 identical-sides matches v 0.7 expected (which side, "
                    "if any, cannot be told)."),
        "checks": [f"{D}/f16_rows.csv (box check n/n2 v Stage 0, other records, fallback)", f"{D}/f16_chance.json"],
    },
    "F17": {
        "vote": "confirm_exclusion",
        "corrupt_beyond_doubt": False,
        "fix_clear_and_correct": False,
        "scope": "Court/edition offsets, the filter's diffuse start, the 120 km/h floor, second-serve mean >= first: leave.",
        "scope_file": None,
        "fix": "None (design or modelling decisions).",
        "reasons": ("Offsets are measurement shifts of whole courts/editions handled (or not) by the model's centring; the "
                    "diffuse start and the floor are code/design choices in features.py and panel.py; for 'second >= "
                    "first' the used field (first-serve average) is not shown wrong as a class (the audit's median "
                    "first-minus-second gap does not shrink) and which field is wrong differs by record."),
        "checks": ["o13_row_checks.txt sections 3 and 5 read", "panel.py header and constants (MEN_MIN 120, WOMEN_MIN 100) read"],
    },
    "already_handled": {
        "vote": "confirm",
        "corrupt_beyond_doubt": False,
        "fix_clear_and_correct": True,
        "scope": ("#6 IOS products' scale: design. #7 workload after the splice: missing matches, not corrupt values. #9 "
                  "men's 2018 odds: restored in the 7 Oct Stage 1. #10 Wimbledon 2026: replaced on 7 Oct. Also the "
                  "Washington 2026 final placeholders: resolved in the 7 Oct Stage 1."),
        "scope_file": None,
        "fix": "None at source; the model frame needs the rebuild to pick these up.",
        "reasons": ("Observed: 7 Oct Stage 1 holds 2,634 ATP 2018 rows with p_avg_a (30 Sep: 0 of 2,927), from "
                    "tennis_data_couk/atp/*/2018.parquet; the model frame still has 0 ATP 2018 rows. Wimbledon 2026 men's "
                    "main draw pooled first serves in: 67.74% (30 Sep) -> 63.76% (7 Oct), 254 rows. Washington 2026 "
                    "finals: 30 Sep winner_swapped placeholders without scores -> 7 Oct name_pair rows with scores."),
        "checks": ["stage1_odds.parquet 7 Oct vs data_continuity/rebuilds/2026-10-07T0005Z/replaced/.../stage1_odds.parquet",
                   "model_frame.parquet seasons by tour", "Stage 0 30 Sep vs 7 Oct Wimbledon 2026 men pooled first_in/svpt"],
    },
}


def main() -> None:
    out = {"reviewer": "B3-referee", "lens": "referee", "candidates": V}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    json.loads(OUT.read_text(encoding="utf-8"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
