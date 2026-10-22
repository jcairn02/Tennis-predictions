"""R2 (attack): write votes.json. Row ids are read from Stage 0, not typed. Writes only into this folder."""
import json
import pandas as pd

R2 = "data/studies/p6_data_issues/stage0_review/R2_attack/"
m = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                    columns=["match_id", "tournament_id", "tournament_date", "source", "source_file", "source_row"])

g1 = m[m["tournament_id"].eq("2024-2847")].sort_values("source_row")
assert len(g1) == 31 and g1["source"].eq("tml").all() and g1["tournament_date"].eq("2024-01-21").all()
assert g1["source_row"].tolist() == list(range(280, 311))
assert g1["source_file"].eq("data/raw/public_dump/tennis_my_life/2024_challenger.csv").all()

G2 = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
SK = ["atp|2021-581|Q2|atp:106045|atp:208013", "atp|2021-581|Q2|atp:106408|atp:202103"]
g2 = m[m["match_id"].isin(G2)]
sk = m[m["match_id"].isin(SK)]
assert len(g2) == 2 and g2["tournament_date"].eq("2021-02-08").all() and sorted(g2["source_row"]) == [98, 106]
assert len(sk) == 2 and sk["source"].eq("sackmann").all() and sk["tournament_date"].eq("2021-01-10").all()

votes = [
    {
        "group": "G1",
        "corrupt_beyond_doubt": True,
        "fix_clear_unique_correct": True,
        "rows": g1["match_id"].tolist(),
        "operation": "set tournament_date",
        "value": "2024-02-26",
        "objections": [
            "None blocking.",
            "Not covered by this fix, noted only: the same 31 rows also carry TML's wrong name ('Tenerife 1'; the "
            "draw is Tenerife 3) and a blank surface. Leaving them does not affect the date fix: the clock labels every "
            "ATP Challenger alike whatever its name, and keys events on tour, tournament id and date.",
            "Implementation: the correction must be guarded on names, round and tournament (as corrections.py does), "
            "since it keys on TML's row positions 280-310 (unchanged in the held revision ca3a597f1a97).",
        ],
        "evidence": [
            "TML's 2024_challenger.csv files all three Tenerife 2024 draws as 'Tenerife 1', 20240121: id 2024-9623 "
            "(lines 374-404, final won by Nakashima), 2024-2839 (lines 250-280, Gigante) and 2024-2847 (lines 281-311, "
            "Kukushkin; surface blank). The held revision of 10 Oct and the superseded file of 22 Sep are the same. "
            "TML's own date for 2024-9623 is the Sunday that ends Tenerife 1's week.",
            "Sackmann holds 2024-9623 'Tenerife CH' 2024-01-15 and 2024-2839 'Tenerife 2 CH' 2024-02-19 and no 2024-2847. "
            "ATP id 2847 is Sackmann's 'Tenerife 3 CH' in 2023 (2023-02-06).",
            "The 31 rows form one consistent 32-player draw: every R16, QF, SF and F player won the round before.",
            "TennisLive 'ATP Tenerife 3 Challenger' (event 19451): all 31 matched one to one, with the same winner and "
            "the same set scores (31 of 31). Days: R32 on 26-27 Feb 2024 (4 matches on Mon 26 Feb), R16 on 28-29 Feb, "
            "QF on 1 Mar, SF on 2 Mar, F on 3 Mar (Kukushkin d. Gigante 6-2 2-0 ret.). Qualifying on 25-26 Feb.",
            "SofaScore (sofascore_editions events) 'ATP Challenger Tenerife 3, Spain Men Singles 2024': the same draw. "
            "Main draw 26 Feb 10:00 to 3 Mar 11:30 UTC (31 played, plus Roca Batalla v De Jong cancelled). "
            "Qualifying 25-26 Feb.",
            "Not a duplicate: none of the 31 pairs met at Tenerife CH or Tenerife 2 CH 2024. The pairs' only other 2024 "
            "meetings are in other rounds, with other scores, at other events: Nottingham CH QF, Wimbledon Q2, Como CH R16.",
            "Stage 0's current date is impossible. In the week of 15 Jan, Kukushkin lost the Tenerife CH QF to Barranco "
            "Cosano, Gigante won Nonthaburi 3 CH and Krueger won Indian Wells 1 CH. In the week of 22 Jan, Demin and "
            "Landaluce played M15 Manacor, Krueger played Indian Wells 2 CH and Rodriguez Taverna played Punta del Este CH.",
            "The proposed week is clean: none of the 32 players has another Stage 0 match in an event dated 2024-02-26. "
            "The neighbouring weeks fit: Gigante won Tenerife 2 on 25 Feb; Kukushkin, Bu, Molleker and Travaglia played "
            "Lugano CH from 4 Mar; Bonadio played Lugano qualifying after losing in the R32.",
            "The value is unique. 2024-02-26 is the main draw's first play day and the Monday of the event week. It "
            "matches C05's rule ('the main draw's first date, as in Sackmann'), Sackmann's Mondays for the other two "
            "Tenerife draws, and Stage 0's TML-only ATP Challenger editions (all Mondays in 2017-2026 apart from two "
            "Tuesdays in 2026; this draw is the only Sunday since 2014). The alternatives fail. 2024-03-03 is TML's end-of-week Sunday, its date for 120 of its "
            "192 2024 Challenger editions; the clock would anchor it to Mon 4 Mar, and the windows would miss the R32-QF "
            "days. 2024-02-25 is the first day of qualifying, and Stage 0 holds no qualifying rows of this draw.",
            "No linking side effect: after the redate, no Sackmann row shares a pair and round with any of the 31 inside "
            "link_tml's windows, so no row would be linked or dropped.",
            "The consequence is confirmed in timing.parquet. The windows close 28-31 Jan 2024 (lf 2024-01-28 to "
            "2024-01-31). 136 other Stage 0 matches of the 32 players have es between a result's lf + 1 and its real "
            "play day (335 player-result pairs).",
        ],
    },
    {
        "group": "G2",
        "corrupt_beyond_doubt": True,
        "fix_clear_unique_correct": False,
        "rows": G2,
        "operation": "set tournament_date",
        "value": "2021-01-10",
        "objections": [
            "Duplicates, not misdates. Stage 0 already holds both walkovers from Sackmann: "
            "atp|2021-581|Q2|atp:106045|atp:208013 (Sweeny d. Kudla, W/O) and atp|2021-581|Q2|atp:106408|atp:202103 "
            "(Vilella Martinez d. Cerundolo, W/O). They are filed under 'Doha Aus Open Qualies', 2021-01-10, from "
            "Sackmann's atp_matches_qual_chall_2021 rows 2438 and 2451. The players, round, result and winner are the "
            "same. The study's 'no Sackmann row' is wrong: Sackmann files this qualifying under its own id (2021-581), "
            "TML under the main draw's id (2021-580).",
            "Why they stayed unlinked: stage0_build.pick accepts a candidate more than 10 days away only when the set "
            "scores are identical and not empty. A W/O has no set scores, and the two sources' dates are 29 days apart. "
            "The other 110 TML rows of this draw linked through their scores (Stage 0's 2021-580 holds no other "
            "TML qualifying row).",
            "The date is not the fault: it follows Stage 0's convention. Every Sackmann ATP Slam qualifying draw of "
            "2015-2025 in Stage 0 carries its main draw's date (41 of 42; the only exception is AO 2021, which Sackmann "
            "files as its own event). C05 also gives TML qualifying rows the main draw's first date. The clock decodes it: the rule for "
            "'Australian Open' 2021 Q2 in schedule_rules.csv (-29 to -26 days from the anchor) turns 2021-02-08 into es "
            "2021-01-08 and lf 2021-01-15, a window that contains the real Q2 days. Today there is no leak; the study's "
            "own clock_leak is empty for both rows.",
            "The proposed redate would create a leak. With the name left as 'Australian Open', the same rule applied "
            "from the new anchor (Mon 2021-01-11) gives es 2020-12-11 and lf 2020-12-18. This reproduces the clock's "
            "anchor and rule arithmetic, which gives today's window exactly; timing.py was not rerun. Each walkover "
            "would then count from 19 Dec 2020, about three weeks before the Doha qualifying. The two rows would also "
            "stay exact duplicates of Sackmann's, now on the same date.",
            "Counter-proposal, for its own vote: drop the two TML-only rows as duplicates of the two 2021-581 rows. "
            "Linking them to those rows has the same effect in Stage 0, where a linked TML row is represented by its "
            "Sackmann row.",
        ],
        "evidence": [
            "Stage 0: the two TML-only rows (2021-580, 'Australian Open', 2021-02-08, Q2, W/O, source rows 98 and 106 of "
            "atp_quali/2021_atp_quali.csv) sit beside Sackmann's rows 532083 and 532109 (2021-581, 'Doha Aus Open "
            "Qualies', 2021-01-10, Q2, W/O, the same pairs and the same winners).",
            "Sackmann's staged atp_matches_qual_chall_2021: 2021-581 'Doha Aus Open Qualies' 20210110, with 64 Q1, "
            "32 Q2 and 16 Q3 rows. Its only two W/O rows are exactly these two Q2 walkovers.",
            "TML's 2021_atp_quali.csv: 2021-580 'Australian Open' 20210208, with 64 Q1, 32 Q2 and 16 Q3 rows, all dated "
            "with the main draw. The two W/O are lines 98 and 106.",
            "Clashes from the current date: Sweeny, Vilella Martinez and Kudla played other events in the weeks of "
            "1 and 7 Feb (Great Ocean Road Open, Cherbourg CH). This only shows that the date needs its decoding rule, "
            "which the clock has.",
            "timing.parquet: the TML rows' es 18635 and lf 18642 (8-15 Jan 2021); Sackmann's rows' es 10-11 Jan and "
            "lf 12-14 Jan 2021.",
        ],
    },
]
with open(R2 + "votes.json", "w", encoding="utf-8") as f:
    json.dump(votes, f, indent=2, ensure_ascii=False)
print("wrote", R2 + "votes.json", [(v["group"], len(v["rows"]), v["corrupt_beyond_doubt"], v["fix_clear_unique_correct"]) for v in votes])
