"""B1-rederive reviewer: write verdict.json (the numbers below were computed by r01-r09 in this folder)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B1-rederive"
D = "data/studies/input_data_audit/fixes/B1-rederive/"

v = {"reviewer": "B1-rederive", "lens": "rederive", "candidates": {}}
C = v["candidates"]

C["F7"] = {
    "vote": "confirm_narrowed", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("12 of the 13 pairs, 21 Stage 0 player rows: wta:315232->wta:201548 Tomljanovic (4 rows), "
              "wta:320319->wta:211713 Cristian (2), wta:324261->wta:215035 Yastremska (2), wta:330332->wta:223253 Eala (2), "
              "wta:322082->wta:214082 Kasatkina (1), wta:328897->wta:221236 Kudermetova (1), wta:328884->wta:222391 Boisson (1), "
              "wta:332718->wta:260765 Oktiabreva (1), wta:321837->wta:215386 Wolff (1), atpcode:M0VL->atp:149128 Marques (4), "
              "atpcode:M0PF->atp:212827 Munk Mesa (1), atpcode:C0UQ->atp:214346 Tran (1). EXCLUDED: atpcode:O0A6 "
              "(Benjamin O'Connell)."),
    "scope_file": D + "scope_F7.csv",
    "fix": ("Replace the new id by the established id wherever it occurs: stage0_match_players.player_id on the 21 listed "
            "rows, opponent_id on the 21 opponent rows that point at them, stage0_matches.player_a_id/player_b_id "
            "(21 references). match_id strings, names, countries and ages are not touched by this fix."),
    "reasons": ("Women: TML's new numbers are the WTA's own player ids (WTA API PlayerID with the same name). The WTA API's "
                "matches under those ids sit in Stage 0 under the established Sackmann ids: Tomljanovic 23, Cristian 8, "
                "Yastremska 22, Eala 8, Kasatkina 33, Kudermetova 3, Boisson 2, Oktiabreva 3 (Rome 125 2025 v Bandecchi, "
                "Radivojevic, Selekhmeteva, same scores, all under wta:260765). Wolff: the WTA's player page for id 321837 "
                "(https://www.wtatennis.com/players/321837/vivian-wolff, read 8 Oct 2026) gives born 8 Oct 1998 = Sackmann's "
                "dob of wta:215386, nationality now USA, rank 245 (Sackmann 249 on 1 Jun 2026, TML 240 on 21 Sep). Each name "
                "is held by exactly one id in Sackmann's WTA player file (70,571 rows). Country conflicts are nationality "
                "changes already on the established rows (Kasatkina RUS->AUS, Kudermetova RUS->UZB), on the WTA's record "
                "(Wolff GER->USA) or TML's (Oktiabreva CZE), or code conventions (PRT/POR, VNM/VIE). Men: M0VL dob "
                "2006-01-07 in TML's ATP database = Sackmann atp:149128; M0PF dob 2006-02-13 = Sackmann atp:212827 (and "
                "atp:210458, a second Sackmann id of the same man, 2 rows Jan 2022, left as is; 212827 holds his 2024-26 "
                "history); C0UQ 'Quoc Cuong Tran' age 19.699 on 2026-09-07 implies dob 2006-12-26 to the day = Sackmann "
                "atp:214346 'Tran Quoc Cuong' (only id with those tokens). O'Connell excluded: two Sackmann ids carry the "
                "name (atp:206736 dob 1999-03-31; atp:213206 no dob, 38 rows), and O0A6's dob 1999-03-31 matches 206736, "
                "not the proposed target 213206, so the target is not unique. Note: the audit's name_key column is "
                "token-sorted ('cristian jaqueline'); with repair_data.name_key (word order kept) every pair but Tran "
                "matches its Sackmann id exactly; repair_tables refused the 9 women for the garbage ages / countries, "
                "Marques for PRT vs POR, O'Connell and Munk Mesa for two Sackmann ids, Tran for the word order."),
    "checks": [
        "r01: same-week rows at different events for the 13 pairs: none; direct meetings between the two ids: none",
        "r02: Sackmann player-file ids per exact and token-sorted name: 1 for 11 pairs, 2 for O'Connell and Munk Mesa",
        "r03: WTA API PlayerID = the 9 new numbers, same names; their matches found under the established ids (counts above)",
        "Oktiabreva: WTA API 332718 Rome 125 2025 matches = Stage 0 wta|2025-1130 R32/R16/QF under wta:260765",
        "Wolff: WTA player page 321837, dob 1998-10-08 = Sackmann wta_players dob of 215386 (external, read 8 Oct 2026)",
        "TML ATP_Database: M0VL 20060107, M0PF 20060213, O0A6 19990331; C0UQ absent (dob from TML age, exact to the day)",
        "r09: after aliasing, matches whose two sides would share one id: 0",
        "independent scan: 28 non-Sackmann ids share an exact name with a Sackmann id; 12 are F7 pairs (Tran differs by "
        "word order); 16 others (e.g. atp:200473 carrying both 'Mats Rosenkranz' and 'Taym Al Azmeh' on TML rows) are "
        "not part of F7 and were not reviewed"]}

C["F8"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("12 TML player rows (2026_wta.csv rows 1270-1324), 7 players, 's-Hertogenbosch and Queen's, 8 Jun 2026, "
              "ages 2,143-3,387. They are the only Stage 0 rows with an age above 100."),
    "scope_file": D + "scope_F8.csv",
    "fix": "Set age to missing on the 12 rows (Stage 0's treatment of an unknown age).",
    "reasons": ("An age in the thousands is impossible. The first two digits are the true age in years "
                "(e.g. Tomljanovic 3387, true 33.09), so the field is garbled, not a different person."),
    "checks": ["r04: Stage 0 rows with age > 100: exactly these 12; all source tml; all new ids of F7"]}

C["F8b"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": "The same 12 rows.", "scope_file": D + "scope_F8.csv",
    "fix": ("age := round((tournament_date - dob).days / 365.25, 3), dob from Sackmann's player file of the established "
            "id: Tomljanovic 33.087 (x3), Eala 21.043 (x2), Kasatkina 29.087, Yastremska 26.064 (x2), Cristian 28.008 "
            "(x2), Boisson 23.064, Kudermetova 23.012. Supersedes F8 if both pass."),
    "reasons": ("The identity is proven by the WTA's own ids (F7). The formula is TML's own convention: on 11,666 TML rows "
                "with a dob it equals TML's age to 3 dp in 69% and within 0.01 in 91%; Tomljanovic's uncorrupted SF row at "
                "the same event reads 33.087, exactly this formula. Valid whether or not F7 is executed (dob keyed by person)."),
    "checks": ["r04/r09: dob found for all 12 rows via the established id; computed values listed in scope_F8.csv"]}

C["F9"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("182 Sackmann ATP rows dated 2020-08-17: Prague CH 98, Todi CH 84; 93 players, all with a dob in "
              "Sackmann's player file."),
    "scope_file": D + "scope_F9.csv",
    "fix": ("age := floor((2020-08-17 - dob).days / 365.25 * 10) / 10 (Sackmann's own one-decimal convention). Raises "
            "every age by 0.4-0.5 years (e.g. Alcaraz 16.8 -> 17.2)."),
    "reasons": ("The age is wrong, not the date. The stored ages imply an age date of 8 Feb-15 Mar 2020 (median 27 Feb), "
                "i.e. computed around the ATP ranking freeze, for events played in August 2020. TML lists the same events "
                "as Prague 2020-08-22 and Todi 2020-08-23 with ages equal to (date - dob) in 95% of rows (Alcaraz 17.303 at "
                "Todi). The weeks before (2 and 9 Mar 2020) and after (24 Aug-7 Sep 2020) are 0% off; these 93 players' "
                "other Sackmann rows agree with their dob (max deviation 0.126 years), so the dobs are right. Floor to 0.1 "
                "is Sackmann's convention: it matches 98.6% of 1.69M Sackmann ages (97.7% of these players' other rows)."),
    "checks": ["r04: |age - age_dob| > 0.15 on 2020-08-17: 182 of 182 ATP CH rows; median -0.47 years",
               "r04: TML 2020_challenger Prague/Todi: TML age = (TML date - dob) within 0.01 in 94.7%/95.2% of rows",
               "r09: other rows of the 93 players: max |age - age_dob| = 0.126"]}

C["F10"] = {
    "vote": "confirm_exclusion", "corrupt_beyond_doubt": False, "fix_clear_and_correct": False,
    "scope": "26 Sackmann rows aged under 13 or 60-100, 8 players.", "scope_file": D + "f10_extreme_ages.csv",
    "fix": "None (left as is).",
    "reasons": ("Every one of the 26 ages equals the age from the player's recorded dob (|diff| <= 0.1). Per player: "
                "Falkenberg (b. 1947, 11 ITF rows 2021-23): real. Ernest (b. 1946, 2 rows 2013), Nemeth (b. 1953, 2 rows "
                "2022), Jones (b. 1964, 1 WTA 125 row 2026), Raul Sanchez (b. 1954, 1 ITF row 2026), Yue Yuan (b. "
                "1998-09-25, 7 ITF rows 2010-11 at 11.5-12.9 inside a 494-row career consistent with that dob), Fabbri "
                "(b. 2007-12-20, 12.0 in Jan 2020), Gaba (b. 2008-09-01, 11.3 in Jan 2020): nothing internally corrupt. If "
                "any is wrong (common names under a veteran's id, a wrong dob) it is an identity question with no single "
                "clear fix. Outside this candidate: TML 2026 Challenger rows 30.9 and 38.0 years above the dob (the "
                "1970-default pattern) are corrupt too but not proposed here."),
    "checks": ["r04: per-player age vs dob table (f10_extreme_ages.csv)"]}

C["F11"] = {
    "vote": "confirm_narrowed", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("4 of the 10 a07 'reversed' rows: Chennai 2013 SF (atp|2013-891|SF|atp:104386|atp:105379), Wimbledon 2016 F "
              "(atp|2016-540|F|atp:104918|atp:105683), 's-Hertogenbosch 2025 F (wta|2025-822|F|wta:210722|wta:211817), "
              "Adelaide 2 2022 R32 (wta|2022-2030|R32|wta:201603|wta:216146). Also, equally certain but outside every "
              "audit list and outside the model frame (evaluation False): US Open 2010 SF, San Jose 2011 F, RG 2011 F "
              "(flag in_audit_a07_list False)."),
    "scope_file": D + "scope_F11.csv",
    "fix": ("In stage1_odds.parquet exchange avg_a<->avg_b, and max_a<->max_b where the max is reversed too (Chennai, "
            "Wimbledon and the three extra rows; not 's-Hertogenbosch or Adelaide, whose max is right); then "
            "p_avg_a := 1 - p_avg_a (overround and coherence unchanged). ps and b365 unchanged."),
    "reasons": ("Stage 1 carries avg, ps, max and b365 per side; only p_avg_a (de-vigged AvgW/AvgL) reaches the model "
                "(odds_logit = logit(p_mkt), p_mkt = p_avg_a); the max is carried but not a model input. Raw rows: "
                "Chennai (atp/2013.xlsx row 52): Tipsarevic (9) d. Bedene (86) 4-6 6-2 6-2 (Tipsarevic won; the "
                "candidate text has it backwards), B365 1.12/6.0, EX 1.16/4.75, LB 1.14/5.0, PS 1.17/6.16, SJ 1.13/6.0 "
                "against Max 6.7/1.17 and Avg 5.44/1.14; p_avg_a 0.827 -> 0.173. Wimbledon 2016 (atp/2016.xlsx row "
                "1645): Murray (2) d. Raonic (7), B365 1.25/4.33, EX 1.25/3.5, LB 1.25/4.0, PS 1.27/4.36 against Max "
                "4.36/1.30, Avg 3.97/1.26; p_avg_a (Raonic) 0.759 -> 0.241. After exchanging avg and max, each average "
                "lies within its side's books and each max >= every book, as for an ordinary row. 's-Hertogenbosch 2025 "
                "(wta/2025.xlsx row 1281): Mertens (25) d. Ruse (80), B365 1.44/2.75, PS 1.46/2.95, Max 1.50/3.00, Avg "
                "2.74/1.44: AvgW 2.74 > MaxW 1.50 is impossible; exchanged, 1.44 <= 1.50 and 2.74 <= 3.00; p_avg_a "
                "0.656 -> 0.344. Adelaide 2 (wta/2022.xlsx row 97): Kostyuk (50) d. Rogers (36), B365 2.62/1.50, PS "
                "2.81/1.49, Max 2.90/1.53, Avg 1.47/2.64: AvgL 2.64 > MaxL 1.53; exchanged, consistent; p_avg_a 0.642 "
                "-> 0.358. Ranks agree with the books in all four. Excluded 'reversed' rows: Berlin 2023, Budapest 2023, "
                "Metz 2024, Miami 2019, Bad Homburg 2021 (only B365 disagrees; the average agrees with the max and the "
                "ranks, and B365 itself looks in-play or reversed); Cluj 2024 Cristian-Bassols (B365 and PS 3.4/1.33, "
                "3.59/1.32 against Avg = Max 1.70/2.02, ranks and Elo; which side is wrong cannot be told). The 7 "
                "'garbled' rows are not reversals (see F13)."),
    "checks": ["r05: Stage 1 avg_a re-derived from the raw row and the link orientation: equal on 83,183 of 83,183 linked rows",
               "r05: strict reversal (>= 2 books, all books give their favourite >= 0.60, the average <= 0.40): 8 rows in "
               "Stage 1; 7 are the scope; the 8th (Rome 2020 SF, Avg 17.0/5.05) is already incoherent and missing",
               "r05: consistency after the exchange (avg within books, avg <= max, max >= books): passes for all 7, fails before"]}

C["F12"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("1 Stage 1 row: wta|2017-1080|F|wta:202427|wta:202499 (td_file wta/international/2017.parquet td_row 553; "
              "workbook wta/2017.xlsx row 1338)."),
    "scope_file": D + "scope_F12.csv",
    "fix": ("Exchange all four price pairs on the row: avg_a<->avg_b, ps_a<->ps_b, max_a<->max_b, b365_a<->b365_b; "
            "p_avg_a 0.190 -> 0.810, p_ps_a 0.170 -> 0.830."),
    "reasons": ("In the raw row only the two names are exchanged: WRank 75 / LRank 8 (Vekic 70, Konta 8), sets 2-6 7-6 "
                "7-5 (Vekic's score), every book's W price ~5 (B365 5.0/1.16, EX 4.75/1.15, LB 5.0/1.17, PS 5.77/1.18, Max "
                "6.0/1.23, Avg 4.98/1.17) - all oriented to the true winner Vekic. Stage 1's winner_swapped pass attaches "
                "the W prices to the named winner Konta, so Konta (8th, at home) carries 4.98. The other 14 winner_swapped "
                "links have ranks agreeing with the names (prices follow the names) and are right as they are."),
    "checks": ["r05: rank_agrees False/False and same_set_scores False only on this winner_swapped link; True on the other 14"]}

C["F13"] = {
    "vote": "contest_exclusion", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("Exclusion confirmed for every F13 row EXCEPT 3 averages captured off the pre-match close (a07 'garbled'): "
              "atp|2022-421|R64|atp:105138|atp:106218 (Canada 2022, Bautista Agut d. Giron), "
              "atp|2022-520|R128|atp:105967|atp:124079 (RG 2022, Laaksonen d. Martinez), "
              "atp|2013-560|R128|atp:104297|atp:105577 (US Open 2013, Dutra Silva d. Pospisil)."),
    "scope_file": D + "scope_F13.csv",
    "fix": ("Blank avg_a, avg_b, max_a, max_b on those 3 rows (p_avg_a missing, avg_coherent False), as Stage 1 already "
            "does for incoherent quotes; nothing substituted."),
    "reasons": ("On each, the maximum on one side is below every individual book on that side, which is impossible for "
                "contemporaneous quotes: Canada 2022 Max 1.03 for Bautista Agut against B365 1.30 and PS 1.37 (Avg "
                "1.02/13.75, p_avg 0.069 for Giron against ~0.28); RG 2022 Max 2.31 for Laaksonen against B365 4.0 and PS "
                "4.37 (p 0.439 against ~0.23); US Open 2013 Max 2.80 for Dutra Silva against B365 6.5, EX 5.25, LB 6.0, PS "
                "5.98 (p 0.358 against ~0.16). The books agree with each other and with the ranks; the average drifted "
                "toward the eventual winner, the in-play signature. Two test rows and one training row. Rest of F13: a04 "
                "(21 rows besides the two F11 reversals): the average's probability agrees with the books; the Max column "
                "(not a model input) is the inconsistent one; no clear fix. a06_placeholders: the Washington 2026 finals "
                "are already real rows in the 7 Oct Stage 1 (name_pair, scores 4-6 6-4 6-0 and 7-6 6-4, prices consistent); "
                "the other 23 are status mismatches (walkover/retired), not price corruption. Single-book reversals and "
                "the other garbled rows (Rome 2020 F: only Pinnacle 52.0 garbled; Stuttgart 2026, Eastbourne 2023: one "
                "book; Doha 2024 Potapova-Trevisan, Cluj 2024: Max = Avg, which side is wrong cannot be told): exclude."),
    "checks": ["r05: raw price blocks of every a04, a06 and a07 row printed and checked",
               "r05: Washington 2026 finals in the 7 Oct Stage 1: link name_pair, td_winner Eala / Fritz, sets present"]}

C["F14"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("136 key-statistic records (handoff_ks 107, mantennisdata 29): first-serve mean above the record's own "
              "maximum, any n (82), or at it (32) or within 1 km/h below it (22) with n >= 10. 108 of them are the value "
              "the panel uses (exactly the audit's 108); 1 is already invalid."),
    "scope_file": D + "scope_F14.csv",
    "fix": ("New validity reason in build_records: a key statistic (handoff_ks or mantennisdata) is not a candidate when "
            "y_raw > spd_max, or y_raw >= spd_max - 1 and n >= 10; spd_max = the same record's own maximum (the player's "
            "own fastest serve of the match), not the match's. Applied to every key-statistic record of both sources, "
            "so the other source's copy of the same statistic falls too; the player-match then takes its next valid "
            "record by the panel's ordering: the Infosys point mean for 76 of the 108, none for 32 (use False)."),
    "reasons": ("Physical bound: among 36,493 point-level records with n >= 10 the smallest max - mean is 3.7 km/h (men "
                "6.35; 0.1% quantile 6.2). A published (ceiling) mean within 1 km/h of the max means a true gap below 2 "
                "km/h; above the max is impossible. The used values sit a median 26-29 km/h from the player's own "
                "365-day median (92-97% > 10 km/h); the fallbacks a median 4.8 (6-9% > 10). No fallback is another copy of "
                "the same statistic; no flagged record has a same-source sibling, so the rule's order relative to "
                "ks_duplicate does not matter. Point means at their max all have n <= 2 and are not in scope. The 7 "
                "fallbacks > 10 km/h from the median are Infosys point means (n 14-40): 4 have the statistic's own max "
                "(e.g. Basel 2024 R16 227.0, max 240), 2 are within 3 km/h of it, and the seventh (Rennes CH 2023 R32, "
                "atp:131911: 168.8, max 179, against the statistic's impossible 262 with max 218) matches the "
                "statistic's second-serve mean (132.2 vs 133); those medians rest on few or corrupt rows. The fallback "
                "is the panel's existing next-valid-record mechanism, as for its mislink rules."),
    "checks": ["r06/r07: gap histogram of key statistics: continuous below 0; rule variants R_above 82 / R_at 112 / R_w1 134 (+2 n<10 above)",
               "r07: fallback recomputed with all flagged records excluded at once; same-statistic copy as fallback: 0",
               "r08: physical bound from point data; 7 doubtful fallbacks inspected record by record"]}

C["F15"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("14 men's records with mean >= 240 (242-270), all handoff_ks, all used by the panel, all also F14 'above' "
              "(own max 198-240)."),
    "scope_file": D + "scope_F15.csv",
    "fix": "As F14 (not a candidate; next valid record). Redundant once F14 passes.",
    "reasons": ("The highest men's first-serve mean in 36,493 point-level records is 227.0; no key statistic consistent "
                "with its own max reaches 230. All 14 are caught by F14."),
    "checks": ["r08: max men's point mean 227.0, 99.99% quantile 222.7; men's records >= 240 by source: handoff_ks 14"]}

C["F16"] = {
    "vote": "confirm_narrowed", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("4 records: the copied block on the later match of the 3 pairs whose original is verified by point-level "
              "data: atp|2026-422|R64|atp:105807|atp:126094 side A mantennisdata 2026-422-re44-cd85-R64; "
              "atp|2025-404|F|atp:207733|atp:208029 side B mantennisdata 2025-404-d0co-r0dg-F; "
              "atp|2023-352|R64|atp:104755|atp:126205 side A mantennisdata 2023-352-pl56-g628-R64 and handoff_ks "
              "2023_352_MS044."),
    "scope_file": D + "scope_F16.csv",
    "fix": ("Not a candidate (as F14); the player-match takes its next valid record: sirgenkii point mean 193.24 (n 33) "
            "for the 2025 final; none for the other two (use False). Every source's copy of the block on that match goes."),
    "reasons": ("Identical (mean, n, second-serve mean, max) on two matches of one player cannot be chance. The original "
                "is the earlier match in these 3: its Infosys point data reproduce the block (126094 at 2022-337 R16: "
                "195.2 -> 196, n 33, 146.1 -> 147, max 215 vs 216; 126205 at 2022-429 R32: 192.4 -> 193, 47, 153.4 -> "
                "154, 221 exact; 208029 at 2024-329 R16: 192.0 -> 193, 165.1 -> 166, 214), while the 2025 final's own "
                "point data read 193.2 -> 194 and max 213. Only one side was copied each time. Both sources copied "
                "2023-352, so both records must go or the other becomes the fallback. Not confirmed: 106043 (handoff "
                "2021-404 R64 vs MTD + handoff 2023-5014 R64) and 208169 (MTD 2026-8394 R16 vs 2026-9120 R16): no point "
                "data on either match, original unknown; 'drop the later' could drop the genuine one and 'drop both' "
                "drops a genuine one. Not confirmed: the 12 matches whose two sides share (mean, n): the second-serve "
                "means and maxima differ; MTD 8 against ~5.5 expected by chance, handoff 3 against ~2.8; the AO match "
                "centre's 4 (2026) exceed chance (0.3) but which side is the copy cannot be told."),
    "checks": ["r07: same-source identical 4-tuples on two matches of one player: exactly 5 pairs",
               "r07/r09: every record of both matches of each pair, including Infosys/sirgenkii point means",
               "chance check: within-source permutation of n across matches"]}

C["F17"] = {
    "vote": "confirm_exclusion", "corrupt_beyond_doubt": False, "fix_clear_and_correct": False,
    "scope": "Court and edition offsets, the filter's diffuse start, the 120 km/h floor, second-serve mean >= first.",
    "scope_file": None, "fix": "None.",
    "reasons": ("Offsets and the floor/start are measurement or design questions, not single corrupt records. Second-serve "
                "mean >= first (437 records with n2 >= 5, all sources): spd_L reads only y (first-serve mean) and n; on the "
                "205 used records y sits a median 5.0 km/h from the player's median (14% > 10), so the used value is "
                "mostly normal and no single clear fix exists."),
    "checks": ["r08: second >= first counts and deviation of the used value; features.py reads p['y'] only"]}

C["already_handled"] = {
    "vote": "confirm", "corrupt_beyond_doubt": False, "fix_clear_and_correct": True,
    "scope": "#6 IOS product scale, #7 workload after the splice, #9 men's 2018 odds, #10 Wimbledon 2026.",
    "scope_file": None, "fix": "None needed in the tables.",
    "reasons": ("#6 is a design issue and #7 a coverage gap (matches missing, not values corrupt). #9: the live Stage 1 "
                "has 2,927 ATP 2018 rows, 2,637 linked, 2,634 with p_avg_a (the model frame still needs the rebuild). "
                "#10: Stage 0's Wimbledon 2026 men read 66.0% first serves in (main) and 64.4% (qualifying), in line with "
                "2024-25 (64.9-66.8%); the override table data/studies/data_continuity/slam_box_overrides.csv (731 rows) "
                "is applied by default per docs/decisions/2026-10-06-slam-box-scores.md."),
    "checks": ["stage1_odds ATP 2018 counts", "Stage 0 Wimbledon first-in by tour/year/draw"]}

(OUT / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", OUT / "verdict.json", len(json.dumps(v)))
