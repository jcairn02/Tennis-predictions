"""R1 recompute, step 12: write votes.json (row ids taken from Stage 0, not typed by hand)."""
import json
import pandas as pd

OUT = "data/studies/p6_data_issues/stage0_review/R1_recompute/"
s0 = pd.read_parquet("data/studies/predictability_diagnostic/stage0_matches.parquet",
                     columns=["match_id", "tournament_id", "tournament_name", "tournament_date", "source", "source_file",
                              "source_row"])
g1 = s0[s0["tournament_id"] == "2024-2847"].sort_values("source_row")
assert len(g1) == 31 and g1["source_row"].tolist() == list(range(280, 311))
assert (g1["tournament_date"] == "2024-01-21").all() and (g1["source"] == "tml").all()
assert (g1["source_file"] == "data/raw/public_dump/tennis_my_life/2024_challenger.csv").all()

votes = [
    {
        "group": "G1",
        "corrupt_beyond_doubt": True,
        "fix_clear_unique_correct": True,
        "rows": g1["match_id"].tolist(),
        "operation": "set tournament_date",
        "value": "2024-02-26",
        "objections": [],
        "evidence": [
            "Stage 0 holds exactly 31 rows with tournament_id 2024-2847 ('Tenerife 1', 2024-01-21, source tml, "
            "source_file data/raw/public_dump/tennis_my_life/2024_challenger.csv, source_row 280-310 = the raw file's "
            "data lines 280-310, all tourney_id 2024-2847, tourney_date 20240121). [s01, s02]",
            "Tennis My Life's 2024 Challenger file names all three 2024 Tenerife editions (2839, 2847, 9623) 'Tenerife 1' "
            "and dates all three 20240121; only 2847 reaches Stage 0 from that file (the other two come from Sackmann). "
            "No other Stage 0 row is dated 2024-01-21. [s02, s10]",
            "All 31 rows match one to one, by player pair, winner, games and tiebreak points, TennisLive's 'ATP Tenerife 3 "
            "Challenger' main draw (/atp-men/tenerife-3-challenger-2024/) and SofaScore's 'Tenerife 3, Spain' (unique "
            "tournament 19937, season 57110): 31/31 winners, 31/31 games, tiebreaks 31/31 (TennisLive) and 13/13 where "
            "SofaScore gives them. No row has a second hit. [s06 -> g1_play_days_strict.csv]",
            "Play days (both sources agree on every match): R32 26-27 Feb, R16 28-29 Feb, QF 1 Mar, SF 2 Mar, F 3 Mar 2024 "
            "(Kukushkin d. Gigante 6-2 2-0 ret., SofaScore 11:30 UTC on 3 Mar). [s06, s07]",
            "Controls: Sackmann's 2024-9623 'Tenerife CH' (2024-01-15; final Nakashima d. P. Martinez 6-3 6-4) matches 31/31 "
            "main-draw rows of the January edition (Tenerife 1, 15-21 Jan) in both sources; Sackmann's 2024-2839 'Tenerife 2 "
            "CH' (2024-02-19; final Gigante d. Travaglia) matches 31/31 of Tenerife 2 (19-25 Feb). Sackmann has no 2024-2847. "
            "None of the 31 matches is elsewhere in Sackmann 2024 or Stage 0 (the three pairs that recur are different "
            "meetings: Como Aug, Nottingham Feb QF 6-3 6-3, Wimbledon Q2 Jul). [s06]",
            "Clock now (timing.parquet): windows close 28 Jan (R32), 29 Jan (R16), 30 Jan (QF), 31 Jan (SF, F) 2024; "
            "basis empirical+rule, no source links. Play day - lf = 29..32 days; results count from 29 Jan - 1 Feb, "
            "28-31 days before they were played. 0 of 31 windows hold the play day. [s07 -> g1_clock_windows.csv]",
            "Early readers (shares a player; reader es >= lf + 1; reader es <= the match's play day): 136 distinct Stage 0 "
            "matches, 335 (reader, match, player) rows, reader es 29 Jan - 24 Feb 2024; 93 of the 136 are evaluation "
            "matches; all 31 matches are read early. The set equals the study's clock_leak_readers.csv row for row. "
            "[s08 -> g1_leak_readers_R1.csv, s09]",
            "Fix simulated with timing.py's own anchor_day / rule_label / rule_windows: anchor 22 Jan -> 26 Feb (+35 days), "
            "rule label ('ATP Challenger (all categories)') and offsets unchanged; new windows R32 23 Feb-3 Mar, R16 25 Feb-"
            "4 Mar, QF 27 Feb-5 Mar, SF 27 Feb-6 Mar, F 28 Feb-6 Mar: 31 of 31 hold the play day. [s09]",
            "Value: 2024-02-26 is the Monday of the event week, the convention of Stage 0's ATP Challenger dates (787 of "
            "804 editions 2022-25 dated on a Monday; the siblings 2024-01-15 and 2024-02-19 are Mondays). [s10]",
        ],
    },
    {
        "group": "G2",
        "corrupt_beyond_doubt": False,
        "fix_clear_unique_correct": False,
        "rows": [],
        "operation": "set tournament_date",
        "value": "2021-01-10",
        "objections": [
            "The two rows are duplicates: Stage 0 already holds atp|2021-581|Q2|atp:106045|atp:208013 and "
            "atp|2021-581|Q2|atp:106408|atp:202103 (Sackmann, 'Doha Aus Open Qualies', 2021-01-10): same players, round "
            "Q2, walkover and winner (atp:208013 Sweeny; atp:106408 Vilella Martinez). Re-dating keeps both copies "
            "(tournament ids 2021-580 vs 2021-581 stay separate events). The defect beyond doubt is the duplication, "
            "not the date, and it needs a different fix (drop the two Tennis My Life rows), proposed and reviewed on its own.",
            "The date 2021-02-08 is the convention, not corruption: Stage 0 dates AO qualifying with the main draw's id and "
            "date in 2019, 2020, 2022 and 2023 (112 rows each), and Tennis My Life files all 112 of its 2021 AO qualifying "
            "rows under 2021-580 / 20210208. The clock has a named rule for exactly this case ('Australian Open' 2021 Q2, "
            "offsets -31..-24 days from the main-draw anchor): window 8-15 Jan 2021, which holds the walkovers' day "
            "(12 Jan 2021). Nothing reads them early now.",
            "The proposed fix breaks the clock: with the name 'Australian Open' kept, the same named rule applies from the "
            "new anchor (11 Jan 2021), so the window becomes 11-18 Dec 2020. The walkovers would count from 19 Dec 2020, "
            "24 days before they happened, and 8 Stage 0 matches would read them early: the four players' Q1 matches, the "
            "two Sackmann twins and two Q3 matches of the same draw. Checked with timing.py's own functions.",
            "Not unique: dropping the duplicates, or re-keying them onto 2021-581 with that event's name and date, are "
            "other fixes. Changing only the date is the one option that turns a correct window into a leaking one.",
        ],
        "evidence": [
            "Tennis My Life's 2021_atp_quali.csv data lines 98 and 106: Sweeny d. Kudla W/O and Vilella Martinez d. "
            "Cerundolo W/O, Q2, tourney 2021-580 'Australian Open', 20210208. Stage 0 rows "
            "atp|2021-580|Q2|atp:106045|atp:208013 and atp|2021-580|Q2|atp:106408|atp:202103, source_row 98/106, "
            "tml_link 'tml_only', date 2021-02-08: as claimed. [s01, s02]",
            "The qualifying was played 10-13 Jan 2021: TennisLive 'ATP Australian Open Qualifying - Doha', 112 matches "
            "10-13 Jan; SofaScore's 2021 qualifying, 112 events 10-13 Jan. Both list the two walkovers in Q2 on "
            "12 Jan 2021. [s09]",
            "Sackmann's date for the same draw is 2021-01-10, under a different id: 2021-581 'Doha Aus Open Qualies', "
            "112 rows, including both walkovers (match_num 170 and 183). [s08]",
            "Clock now: the Tennis My Life rows' window is 8-15 Jan 2021 (named_rule); the Sackmann twins' is 11-13 Jan "
            "(event_round). Early readers now: 0. Under the proposed date: 8. [s07, s08, s09, s11]",
        ],
    },
]
with open(OUT + "votes.json", "w", encoding="utf-8") as fh:
    json.dump(votes, fh, indent=2, ensure_ascii=False)
print("wrote votes.json:", [(v["group"], v["corrupt_beyond_doubt"], v["fix_clear_unique_correct"], len(v["rows"]), v["value"]) for v in votes])
