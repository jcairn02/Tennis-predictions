"""B2-skeptic: write data/studies/input_data_audit/fixes/B2-skeptic/verdict.json (the review's votes).
Evidence: the f*_*.py scripts in this folder and their outputs next to verdict.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
D = "data/studies/input_data_audit/fixes/B2-skeptic/"

C = {}

C["F7"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("All 23 Stage 0 player rows of the 13 new ids in frame_split_ids_oct07.csv, each to the established id named "
              "there: wta:315232->wta:201548 (4 rows), wta:320319->wta:211713 (2), wta:324261->wta:215035 (2), "
              "wta:330332->wta:223253 (2), wta:322082->wta:214082 (1), wta:328897->wta:221236 (1), "
              "wta:328884->wta:222391 (1), wta:332718->wta:260765 (1), wta:321837->wta:215386 (1), "
              "atpcode:O0A6->atp:213206 (2), atpcode:M0VL->atp:149128 (4), atpcode:M0PF->atp:212827 (1), "
              "atpcode:C0UQ->atp:214346 (1)."),
    "scope_file": D + "scope_F7.csv",
    "fix": ("Alias each new id to its established id on every Stage 0 row of the new id: player_id in "
            "stage0_match_players, the opponent row's opponent_id, and player_a_id / player_b_id in stage0_matches. "
            "match_id handles and A/B sides unchanged (as repair_tables does). No other field changed by this fix "
            "(the garbage ages are F8/F8b). Not included: the further Sackmann duplicates of two of these people, "
            "atp:206736 (O'Connell, 2 rows) and atp:210458 (Munk Mesa, 2 rows), which stay as they are."),
    "reasons": (
        "Every pair is one person, by links independent of the name. WTA: TML's 2026 WTA rows carry the WTA's own player "
        "ids; in the WTA API match list each of the 9 ids is that player and its singles matches coincide with the "
        "established Sackmann id's (Tomljanovic 38 of 40 WTA-API matches found in Stage 0 under wta:201548, Cristian 42/54, "
        "Yastremska 48/49, Kasatkina 66/71, Eala 22/32, Boisson 5/5, Kudermetova 6/13, Oktiabreva 3/3 = Rome 125 2025 vs "
        "Bandecchi, Radivojevic, Selekhmeteva; the unshared are 31 doubles and 6 qualifying matches, which Stage 0 lacks, "
        "and Wolff's only WTA-API match, Ljubljana 125 in Sep 2026, after Sackmann's end). "
        "Wolff: WTA id 321837 is the WTA profile of Vivian Wolff born 8 Oct 1998 = Sackmann's dob for wta:215386 (web), "
        "and Wikipedia's 2026 ITF pages carry the USA flag on the W75 Lopota finalist whom Sackmann holds as wta:215386 "
        "(GER); rank 249 (1 Jun) -> 240 (21 Sep). ATP: TML's three-decimal ages give birth dates equal (within the "
        "one-day rounding) to Sackmann's: M0VL 2006-01-07 = atp:149128; M0PF 2006-02-13 = atp:212827 (and its own "
        "duplicate atp:210458, same dob); C0UQ 2006-12-26 = atp:214346 ('Tran Quoc Cuong' / 'Quoc Cuong Tran', both at "
        "Phan Thiet); O0A6 1999-03-31 = atp:206736's dob, while atp:213206 (no dob) is the ATP-ranked Benjamin O'Connell "
        "(Sackmann rank 1,140 with 12 pts on 8 Jun 2026 -> TML rank 984 with 22 pts on 31 Aug 2026 for O0A6; atp:206736 "
        "never ranked), and the web profile shows one Benjamin O'Connell, b. 31 Mar 1999, 178 cm, right-handed, playing "
        "M15/M25 in 2026 (TML: 178, R). Country 'conflicts' are real switches in the WTA's own data (Kasatkina RUS->AUS, "
        "Kudermetova RUS->UZB, Wolff USA) or code conventions (PRT/POR, VNM/VIE); Oktiabreva's CZE is TML's label on WTA "
        "id 332718, RUS in the WTA API. The birth-year 'conflicts' of 7 women are the garbage ages (F8), which decode to "
        "the right ages."),
    "checks": [
        "Two people of one name? Every new id's Stage 0 rows carry one name; WTA ids cross-linked to the established ids "
        "through shared matches (f7_crosslink.csv); ATP dobs equal to the day (f7_dob_check.csv).",
        "Same week at different events: none for any pair (f7_pairs_detail.txt).",
        "Opponent collapse: no alias puts one id on both sides (Tomljanovic v Yastremska R16 becomes wta:201548 v wta:215035).",
        "cuong quoc tran: one established match only, but dob 2006-12-26 matches TML's age 19.699 on 2026-09-07 to the day.",
        "goncalo marques: many Portuguese Marques exist (Diogo, Joao, Rafael...), but only atp:149128 has dob 2006-01-07; "
        "rank 1,180 (8 Jun) -> 762 (31 Aug) plausible after his M25 results.",
        "bernardo mesa munk / benjamin connell o: repair_tables refused them ('multiple canonical players share exact "
        "name'); the two Sackmann ids are one person in each case (same dob for Munk Mesa; dob + ranking chain + web "
        "profile for O'Connell), so the named target is correct; the leftover duplicate ids are outside this fix.",
        "vivian wolff / alisa oktiabreva: country differs (USA, CZE) but WTA ids and dob tie them to the established ids.",
        "Boisson's rank 43 -> 154 in two weeks fits her 2025 Roland Garros semi-final points dropping off on 8 Jun 2026 "
        "(inference; observed: one name, FRA, R, WTA id 328884 sharing 5 of 5 WTA-API matches with wta:222391).",
    ],
}

C["F8"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": "The 12 TML player rows of 's-Hertogenbosch and Queen's Club 2026 (8 Jun) with age 2,143-3,387.",
    "scope_file": D + "scope_F8.csv",
    "fix": "Set age to missing on those 12 rows (age_F8 column). If F8b is unanimous, F8b supersedes it.",
    "reasons": ("An age of 2,143-3,387 is impossible. The values are the true ages with the decimal mangled: "
                "'33.087' -> 3387 (integer part x 100 + thousandths), on all 12 rows. No other TML WTA 2026 row with a "
                "Sackmann dob deviates by more than 0.034 years from its dob-based age (1,897 rows), so the scope is "
                "complete. Live Stage 0 has no other age > 100 or < 5 among TML rows."),
    "checks": ["Scan of every Stage 0 age > 90 or < 10: exactly these 12 TML rows.",
               "In the 30 Sep model frame these matches have in_age missing; a rebuild on the 7 Oct tables would carry the "
               "garbage into in_age, so the fix matters for the next rebuild."],
}

C["F8b"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": "The same 12 rows as F8.",
    "scope_file": D + "scope_F8.csv",
    "fix": ("age := round((tournament_date - dob).days / 365.25, 3), dob from Sackmann's player file of the established "
            "id: Tomljanovic 33.087 (x3, dob 1993-05-07), Cristian 28.008 (x2, 1998-06-05), Yastremska 26.064 (x2, "
            "2000-05-15), Eala 21.043 (x2, 2005-05-23), Kasatkina 29.087 (1997-05-07), Kudermetova 23.012 (2003-06-04), "
            "Boisson 23.064 (2003-05-16). Preferred over F8."),
    "reasons": ("Two independent derivations agree exactly on all 12 rows: the dob-based age and the garbage value "
                "decoded (int(g/100) + (g mod 100)/1000). It is also TML's own convention at that event: Tomljanovic's "
                "SF row at 's-Hertogenbosch carries 33.087. TML's ages for the same players at later events equal the "
                "dob-based ones (Yastremska Nottingham 26.084; Cristian Wimbledon 28.066). Identity is certain (F7), so "
                "the dob lookup does not need F7 to be executed."),
    "checks": ["decode_equals_F8b is True on all 12 rows (scope_F8.csv).",
               "TML's convention: tournament date, 365.25-day years, 3 decimals at these events (at Wimbledon TML uses "
               "the match day, up to 0.034 y later); the fix uses the tournament date, as the garbage itself encodes."],
}

C["F9"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("All 182 player rows of the two ATP Challengers dated 17 Aug 2020 in Sackmann's file: Prague CH (2020-600, "
              "98 rows) and Todi CH (2020-8392, 84 rows); 93 players, every one with a Sackmann dob."),
    "scope_file": D + "scope_F9.csv",
    "fix": ("age := floor(10 x (tournament_date - dob).days / 365.25) / 10 (Sackmann's own truncation to 0.1, as on "
            "every other Sackmann row; column age_F9). Full precision would also be correct (< 0.1 y apart)."),
    "reasons": ("The age is wrong, not the date. TML, an independent record, dates Todi to the week ending 23 Aug 2020 "
                "and gives Alcaraz 17.303 there; Sackmann's 16.8 equals his age on 16 Mar 2020, the frozen ATP ranking "
                "date: on every row the shift is 154.2-190.3 days = 154 days (16 Mar -> 17 Aug) plus up to 36.5 days of "
                "truncation. Sackmann computes age at the latest ranking date: the same players read correctly a week "
                "later (rankings resumed 24 Aug), and the only other misses in 2020 are +0.1 y in weeks where the "
                "ranking date lags 7 days. A scan of every level and week from Feb to Oct 2020, both tours, finds this "
                "week and level alone. The dob is established: 97.9% of the same players' 2,561 other 2020 rows equal "
                "the truncated dob-based age, the rest differ by exactly +0.1 in those lagging weeks."),
    "checks": ["Date wrong instead? No: Prague and Todi 2020 were played 17-23 Aug (TML: 22-23 Aug), consistent with the "
               "players' sequences (Alcaraz: Todi, then Trieste 24 Aug, Cordenons 31 Aug).",
               "Other events of the freeze (WTA Palermo/Prague/Lexington, Cincinnati 2020, ITF Aug 2020): ages normal.",
               "Not in the model frame (Challengers)."],
}

C["F10"] = {
    "vote": "confirm_exclusion", "corrupt_beyond_doubt": False, "fix_clear_and_correct": False,
    "scope": "None executed: the 26 Sackmann 'impossible' age rows (8 players).",
    "scope_file": None,
    "fix": "None.",
    "reasons": (
        "Per player: Gail Falkenberg (dob 1947-01-16, 11 ITF qualifying rows 2021-23, ages 74-76) is real. Yue Yuan's "
        "ages fit her dob (1998-09-25) on all 494 rows; her 2010-11 ITF rows at 11.5-13 are odd for ITF age rules, but "
        "that is an identity question, not an age error. Elizabeth Ernest (dob 1946, 2 rows 2013) and Anna Nemeth (dob "
        "1953, 2 rows 2022) may be genuine senior entrants: unknowable. Leila Fabbri (12.0, 2020) and Geetaarthi Gaba "
        "(11.3, 2020) are below ITF's minimum age, so the dob or the identity is wrong, with no source for the true "
        "value; blanking one row would leave the player's other dob-based ages. Elizabeth Jones (61.8, Midland 125 2026, "
        "wildcard, lost 6-4 2-6 6-2 in 144 min to #313) and Raul Sanchez (72.1, M15 Ceuta 2026) are clearly younger "
        "players merged into old Sackmann ids (wta:200992 GBR b. 1964; atp:203679 MEX b. 1954): the fault is the "
        "identity (and country), whose fix is a new id, not the age. Not in the model frame."),
    "checks": ["Each id's full history and dob checked (one match each for Jones and Sanchez)."],
}

C["F11"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("4 Stage 1 rows: the two named finals plus the two other 'reversed' rows that are equally certain. "
              "atp|2016-540|F|atp:104918|atp:105683 (Wimbledon 2016 F; atp/grand_slam/2016 row 380, xlsx row 1645): "
              "average AND maximum; atp|2013-891|SF|atp:104386|atp:105379 (Chennai 2013 SF; atp/atp250/2013 row 51, "
              "xlsx row 52): average AND maximum; wta|2025-822|F|wta:210722|wta:211817 ('s-Hertogenbosch 2025 F; "
              "wta/wta250/2025 row 278, xlsx 1281): average only; wta|2022-2030|R32|wta:201603|wta:216146 (Adelaide 2 "
              "2022 R32; wta/wta500/2022 row 34, xlsx 97): average only. Rows are positions in the staged parquet "
              "under data/dump/odds/tennis_data_couk/ (Stage 1 td_row); xlsx rows are the raw workbook's (_row). The other six 'reversed' rows (Berlin 2023, Budapest 2023, Metz 2024, Miami 2019, "
              "Bad Homburg 2021, Cluj-Napoca 2024) are rejected."),
    "scope_file": D + "scope_F11.csv",
    "fix": ("Exchange AvgW and AvgL on the raw row (Stage 1: avg_a <-> avg_b, p_avg_a := 1 - p_avg_a, overround and "
            "coherence unchanged); for Wimbledon 2016 F and Chennai 2013 SF also MaxW <-> MaxL (max_a <-> max_b). "
            "B365, PS and the other books unchanged. p_avg_a (= the model's p_mkt): Raonic 0.759 -> 0.241, Bedene 0.827 "
            "-> 0.173, Ruse 0.656 -> 0.344, Kostyuk 0.642 -> 0.358 (books' median for A: 0.232, 0.160, 0.337, 0.355)."),
    "reasons": (
        "Wimbledon 2016 F: B365 1.25/4.33, EX 1.25/3.50, LB 1.25/4.00, PS 1.27/4.36 (Murray/Raonic) against Avg 3.97/1.26 "
        "and Max 4.36/1.30. As stored the max on Raonic (1.30) is below every book's Raonic price (3.50-4.36), "
        "impossible; exchanged, max >= every book on both sides and the average lies inside the books' range on both "
        "sides. Avg and max move together, so the deciding evidence is external: Murray #2 v Raonic #7 (Elo 0.26 for "
        "Raonic); Murray was the clear favourite. Chennai 2013 SF: 5 books (B365, EX, LB, PS, SJ) put Tipsarevic (#9) at "
        "1.12-1.17 v Bedene (#86) 4.75-6.16; Avg 5.44/1.14 and Max 6.70/1.17 are the mirror; max on Bedene 1.17 < 6.16 "
        "as stored; exchanged it is consistent (Elo 0.22 for Bedene). 's-Hertogenbosch 2025 F and Adelaide 2 2022 R32: "
        "here the max agrees with B365 and PS (Mertens 1.50/Ruse 3.00; Kostyuk 2.90/Rogers 1.53) and the stored average "
        "exceeds the maximum of its own feed (Mertens 2.74 > 1.50; Rogers 2.64 > 1.53): internal proof the average is "
        "the wrong field; exchanged, it sits under the max on both sides and within 0.01 of the books (0.344 v 0.337; "
        "0.358 v 0.355), and ranks agree (Mertens #25 v Ruse #80; Rogers #36 v Kostyuk #50). The six rejected rows have "
        "one referee book only and the average agrees with the max and mostly the ranks (the single book is the odd "
        "one), or (Cluj-Napoca 2024) avg = max exactly and both books oppose: one source against one source, ranks "
        "and Elo mildly favour the average's side: not certain."),
    "checks": [
        "Could the books be wrong and the average right? For the two finals the books and the avg/max are each "
        "internally consistent (H1/H2 cannot tell them apart), so ranks, Elo and the known favourite decide; for the "
        "two avg-only rows the average contradicts its own feed's maximum.",
        "Exact exchange, not garbled values: exchanged averages reproduce the books within 0.004-0.014.",
        "Pairing a price with the wrong player in another column: only Avg (and Max for the finals) move; every other "
        "column already follows the result orientation; Stage 1 carries only p_avg_a into the model (p_mkt).",
        "Full scan of the 7 Oct Stage 1 (all years, incl. the restored ATP 2018) with the same tests (f11_reversed_scan.csv): "
        "8 rows qualify; besides these 4, two are certain by history but outside the candidate and the model frame "
        "(2011 RG F Nadal-Federer: books Nadal 1.36-1.40 v Avg 2.99; 2010 US Open SF Djokovic-Federer: books Federer "
        "1.25-1.36 v Avg on Djokovic 1.30) and two are not certain (2010 Toronto SF, 2011 San Jose F).",
    ],
}

C["F12"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("1 Stage 1 row: wta|2017-1080|F|wta:202427|wta:202499 (Nottingham 2017 F; "
              "data/dump/odds/tennis_data_couk/wta/international/2017.parquet row 553; xlsx row 1338)."),
    "scope_file": D + "scope_F12.csv",
    "fix": ("Exchange every price between the two players: avg_a/avg_b 4.98/1.17 -> 1.17/4.98, ps 5.77/1.18 -> 1.18/5.77, "
            "max 6.00/1.23 -> 1.23/6.00, b365 5.00/1.16 -> 1.16/5.00 (A = Konta); p_avg_a 0.190 -> 0.810, p_ps_a 0.170 -> "
            "0.830. Equivalent source fix: exchange the Winner/Loser names of the raw row (Stage 1 then links it by name "
            "pair with identical set scores)."),
    "reasons": ("Only the names are exchanged in tennis-data's row: its W columns are Vekic's. WRank 75 / LRank 8 "
                "(Stage 0: Vekic 70, Konta 8), the set scores 2-6 7-6 7-5 are the true winner Vekic's, and all four price "
                "columns put the W player at about 5.0, the underdog price that fits #70 v #8. Stage 1's winner-swapped "
                "pass therefore gave Konta Vekic's prices. Of 82,894 linked rows with both ranks, this is the only one "
                "whose ranks agree only when exchanged (3 other hits are tolerance artifacts with one rank exactly equal "
                "as stored)."),
    "checks": ["The other 14 winner-swapped rows: names and ranks agree as stored, so prices follow the right players; "
               "only who-won differs (retirements, 2 completed): no price fix."],
}

C["F13"] = {
    "vote": "contest_exclusion", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("1 row only: atp|2022-421|R64|atp:105138|atp:106218 (Canada Masters 2022 R64, Bautista Agut d. Giron; "
              "data/dump/odds/tennis_data_couk/atp/masters_1000/2022.parquet row 372; xlsx row 1902). Exclusion confirmed for every "
              "other F13 row."),
    "scope_file": D + "scope_F13.csv",
    "fix": "Blank AvgW/AvgL and MaxW/MaxL (avg_a, avg_b, max_a, max_b missing; p_avg_a missing). Books untouched.",
    "reasons": (
        "Avg 1.02/13.75 and Max 1.03/16.00 for #18 v #57 in a 7-6(5) 6-3, 118-minute match, against the row's own "
        "closes B365 1.30/3.50 and PS 1.37/3.41 (Elo 0.29 for Giron): an in-play price, not a close. It passes Stage 1's "
        "overround test (1.053), so the model reads 0.069 for Giron (test split). The true average is unknown; marking "
        "it missing invents nothing and is what Stage 1 already does with incoherent quotes (consequence: the match "
        "leaves the frame under 'no odds, no row'; substituting PS would be a design choice, not a correction). "
        "Other F13 rows, exclusion confirmed: a04 'avg above max' rows have averages within 0.03 of the books (the max "
        "is the bad field and the model does not use it), except the two rows handled in F11; the Washington 2026 "
        "finals are complete in the 7 Oct Stage 1 (scores, 'Completed', coherent prices); the other placeholder rows "
        "are retirements or walkovers with coherent prices; single-book reversals (Berlin 2023, Budapest 2023, Metz "
        "2024, Miami 2019, Bad Homburg 2021, Eastbourne 2023, Stuttgart 2026): the lone book is the outlier; garbled "
        "Rome 2020 F: only PS (52.00) is bad and Stage 1 already drops it; Cluj-Napoca 2024 and Doha 2024: avg = max "
        "exactly, one source v two books, exchanged values break the max: not certain; RG 2022 Laaksonen-Martinez and "
        "US Open 2013 Dutra Silva-Pospisil: avg/max contradict the books but which side is right is not knowable."),
    "checks": ["f11_flagged_rows.csv holds every a04/a06/a07 row with all printed books and the H1/H2 tests."],
}

C["F14"] = {
    "vote": "confirm_narrowed", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("130 key-statistic records (103 handoff_ks, 27 ManTennisData; 105 of them chosen today) in "
              "speed_records.parquet, identified by (match_id, side, source, source_key) in scope_F14.csv. Rule: "
              "KS >= spd_max - 1 km/h, spd_max being the same record's (the player's own) fastest serve, AND the "
              "published mean itself shown wrong: >= 8 km/h from the player's own +-365-day median (>= 3 other records) "
              "or >= 5 km/h from a valid point mean of the same player-match; every flagged copy of a player-match goes "
              "together. Left out (5 records, 3 player-matches) where the mean is plausible and the max may be the bad "
              "field: atp|2022-2805|Q2|atp:111190|atp:207925 A (ManTennisData + handoff, 185 v max 186, norm 182.5), "
              "atp|2022-7485|Q1|atp:106187|atp:126646 A (both, 172 = max, norm 173.3), "
              "atp|2023-3503|R16|atp:105430|atp:131911 A (handoff 211 v max 197, norm 215 from 2 records)."),
    "scope_file": D + "scope_F14.csv",
    "fix": ("The record is not a candidate (a new invalid_reason, e.g. 'mean_ge_max', set before choose()), so the "
            "player-match takes its next valid record or none; nothing else changes."),
    "reasons": (
        "The max is the player's own: A and B maxima differ in 97% of key-statistic matches. A key statistic is the "
        "ceiling of the point mean, so KS >= max - 1 means a true mean within 2 km/h of the player's fastest serve; in "
        "36,493 self-consistent point-mean records (n >= 10) the smallest gap is 3.7 km/h (0.01% quantile 5.2), so the "
        "record is impossible. 135 records meet the rule (81 strictly above the max, 32 equal, 22 at max - 1), all n >= "
        "8; 119 sit more than +8 km/h above the player's norm (median +22.7). Where the mean is plausible, dropping a "
        "possibly correct value is not clearly right, hence the narrowing. Fallback: 92 of 135 have another valid "
        "record (median residual +1.3 km/h), the rest go to use = False."),
    "checks": [
        "'Strictly above / at / within 1': within 1 is justified by the ceiling and the 3.7 km/h minimum gap.",
        "'Which maximum': the record's own; rounding cannot produce KS >= max (an integer max >= mean implies "
        "ceil(mean) <= max) let alone exceed it.",
        "Fallbacks more than 10 km/h from the player's norm: 6, mostly infosys point means at editions that read low "
        "(2023-5014, 2024-451), which the edition centring absorbs; one doubtful (Poullain, 2023-3503 R32, infosys 168.8 "
        "with a one-record norm). Not a reason to keep an impossible value.",
        "Outside scope: in many of these matches the opponent's ManTennisData/handoff mean is far too low (e.g. 119, 130, "
        "141, 153 km/h at 2023-5014 and 2024-451): a related fault the max rule does not catch.",
    ],
}

C["F15"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("14 men's handoff_ks records with y_raw >= 240 (242-270), all chosen today, all inside F14's scope "
              "(each also has KS >= its own max - 1, the max being 198-240)."),
    "scope_file": D + "scope_F15.csv",
    "fix": "As F14: the record is not a candidate; the player-match falls back to its next valid record or none.",
    "reasons": ("The highest men's first-serve point mean among 36,493 records is 227.0 km/h; men's key statistics "
                "above 220 are rare (32 in 220-225) and the 14 at >= 240 are 33-102 km/h above the players' norms. "
                "Fallbacks: 9 to infosys point means (residuals -8.6 to +10.5 except Poullain's -41.7 against a "
                "one-record norm), 5 to none (use = False)."),
    "checks": ["Already caught by F14: all 14."],
}

C["F16"] = {
    "vote": "reject", "corrupt_beyond_doubt": False, "fix_clear_and_correct": False,
    "scope": "None.",
    "scope_file": None,
    "fix": "None.",
    "reasons": (
        "Identical integer key statistics recur by chance, and the data show it. (a) Same player, identical (mean, n, "
        "second-serve mean, max) on two matches: 5 pairs among 20,021 key-statistic rows, against 2.96 expected when "
        "the player's own n, second-serve mean and max are permuted across his matches (95th percentile 6). One pair is "
        "proven a coincidence: atp:208029's two 193s are each confirmed by an independent point mean (infosys 192.0 at "
        "2024-329; sirgenkii 193.2 at 2025-404). In two more pairs the earlier record is confirmed by infosys (195.2 v "
        "196; 192.4 v 193) and the later has no independent record. Every record's own box (first serves in / total) "
        "matches Stage 0 for its own match exactly (first serves in = first_in, total = svpt, on every valid record). "
        "So 'drop both' would destroy verified records and 'drop the later' has no "
        "basis. (b) Both sides identical (mean, n): 12 matches, against about 11.8 expected from the within-match rates "
        "of equal means (1.4%) and equal n (3.9%): ManTennisData 8 v 11.1 expected. Where independent point means "
        "exist they point to other faults (2024-5014 R128 Opelka-Rinderknech: KS 198/198 = ceiling of the pooled match "
        "mean while infosys gives 193.3/202.2, apparently with servers swapped), so the fallback would select another "
        "bad record. The AO match centre's 4 (0.7 expected) differ in their other fields and have no independent "
        "record. The original cannot be told."),
    "checks": ["f16_null.json (permutation nulls), f16_pairs.csv (boxes v Stage 0), f16_same_sides.csv."],
}

C["F17"] = {
    "vote": "confirm_exclusion", "corrupt_beyond_doubt": False, "fix_clear_and_correct": False,
    "scope": "None executed.",
    "scope_file": None,
    "fix": "None.",
    "reasons": ("Court and edition offsets are measurement offsets of whole groups (the edition centring absorbs the "
                "edition level; a court-level correction is a model, not a record fix). The filter's diffuse start and "
                "the 120 km/h floor are code design. 'Second-serve mean >= first': of 205 chosen rows, 102 have a "
                "first-serve mean within 5 km/h of the player's norm (the second-serve field, unused by the panel, is "
                "the bad one) and 55 are > 8 km/h below it: no single rule fixes the class without dropping good values."),
    "checks": ["f17_second_serve.csv."],
}

C["already_handled"] = {
    "vote": "confirm_exclusion", "corrupt_beyond_doubt": False, "fix_clear_and_correct": False,
    "scope": "#6 IOS products' scale, #7 workload after the splice, #9 men's 2018 odds, #10 Wimbledon 2026 men.",
    "scope_file": None,
    "fix": "None in today's tables.",
    "reasons": ("#6 is a design property of prod_* (scale moves with the ratings' level), not a corrupt record; #7 is "
                "missing matches (coverage), not wrong values. #9 verified: the 7 Oct Stage 1 holds 2,927 ATP 2018 "
                "rows, 2,637 linked, 2,634 with an average probability. #10 verified: today's Stage 0 Wimbledon 2026 "
                "men's main draw reads 65.96% first serves in (2023-25: 64.9-66.2%) and slam_box_overrides.csv holds "
                "239 Wimbledon 2026 men's rows. Both #9 and #10 still differ in the 30 Sep model frame: a rebuild "
                "matter, not a correction."),
    "checks": ["Stage 1 ATP 2018 counts; Stage 0 Wimbledon first-in rates 2023-26 by tour and draw."],
}

verdict = {"reviewer": "B2-skeptic", "lens": "skeptic", "candidates": C}
(OUT / "verdict.json").write_text(json.dumps(verdict, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", OUT / "verdict.json")
