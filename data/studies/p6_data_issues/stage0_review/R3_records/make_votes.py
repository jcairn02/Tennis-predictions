"""R3 scratch: write votes.json from the checks in simulate_fix.log / sim_*.csv (row ids read from Stage 0, not typed)."""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
m = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet",
                    columns=["match_id", "tournament_id", "tournament_name", "tournament_date", "source", "source_row",
                             "source_file"])
g1 = m[m["tournament_id"].astype(str).eq("2024-2847")].sort_values("source_row")
assert len(g1) == 31 and g1["source"].eq("tml").all()
assert g1["source_row"].tolist() == list(range(280, 311))
assert g1["tournament_date"].astype(str).str[:10].eq("2024-01-21").all()
g2_ids = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
g2 = m[m["match_id"].isin(g2_ids)]
assert len(g2) == 2 and g2["tournament_date"].astype(str).str[:10].eq("2021-02-08").all()

order = pd.read_csv(HERE / "sim_g1_order_after.csv")
win = pd.read_csv(HERE / "sim_g1_windows.csv")
n_t2 = int(order["prev_event"].eq("Tenerife 2 CH").sum())
assert bool(win["in_window"].all()) and not bool(win["in_old_window"].any())
assert bool(order["t3_contiguous"].all() and order["prev_ok"].all() and order["next_ok"].all())

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
            "atptour.com results archive for event 2847/2024 (https://www.atptour.com/en/scores/archive/tenerife/2847/2024/results, "
            "accessed 14 Oct 2026): header 'Tenerife 3', '26 Feb - 3 Mar, 2024'; its 31 main-draw results equal the 31 Stage 0 rows "
            "match for match (players, winner, every set score and tiebreak, both retirements).",
            "Wikipedia '2024 Tenerife Challenger III' and its singles draw: 26 Feb - 3 Mar 2024, hard; the same 31 results; "
            "final Kukushkin d. Gigante 6-2 2-0 ret.",
            "Tenerife 1 (ATP id 9623, 15-21 Jan 2024, Nakashima d. P. Martinez) and Tenerife 2 (ATP id 2839, 19-25 Feb 2024, "
            "Gigante d. Travaglia) are different draws on atptour.com and Wikipedia; none of the 31 results is in Tenerife 1 "
            "(e.g. there Landaluce lost his R32 to Nakashima and Brancaccio lost his to Barranco Cosano). Stage 0 holds both "
            "from Sackmann with their own dates (2024-01-15, 2024-02-19).",
            "atptour.com news of 4 Mar 2024 (kukushkin-gigante-tenerife-challenger-2024-final): the final was played on the "
            "Sunday, i.e. 3 Mar 2024.",
            "Mechanism: Tennis My Life's raw 2024_challenger.csv labels all three Tenerife events (ids 2839, 2847, 9623) "
            "'Tenerife 1' with date 20240121, the first event's label copied onto the other two; Stage 0 took 2839 and 9623 "
            "from Sackmann but 2847 only from TML (rows 280-310).",
            "Stage 0's convention: of 113 TML-sourced ATP Challenger main-draw events since 2023, 110 are dated on a Monday "
            "(their dated matches run from 0 to 6 days after it, medians) and 2 on a Tuesday; 2024-2847 (a Sunday, no dated "
            "match) is the only exception. 2024-02-26 is the ATP's start Monday, so the value is unique under the convention "
            "(and the timeline's anchor rule maps it to itself); match ids carry no date and stay unchanged.",
            "Now: the 31 rows' windows (19-31 Jan) contain 48 exact-dated matches of the same players elsewhere, e.g. Gigante "
            "played the Nonthaburi 3 (Thailand) QF, SF and final on 19-21 Jan, Kukushkin lost the Tenerife 1 QF on 19 Jan and played Ottignies qualifying "
            "22-23 Jan and Koblenz 29-31 Jan, Demin and Landaluce played M15 Manacor 23-26 Jan.",
            "Simulated fix (timing.py's own anchor_day, rule_windows, class windows and draw_narrowing on an in-memory copy; "
            "the code reproduces timing.parquet's current windows for all 31): windows R32 23 Feb-3 Mar, R16 25 Feb-4 Mar, "
            "QF 27 Feb-5 Mar, SF 27 Feb-6 Mar, F 28 Feb-6 Mar; every match's play day lies inside (31/31; days from the local "
            "TennisLive and SofaScore copies, 26 Feb-3 Mar, final 3 Mar as the ATP says); the current windows hold 0/31.",
            "Check (i) after the fix: none of the 32 players has another Stage 0 match dated inside his Tenerife 3 span, nor "
            "any other match whose window touches one of his Tenerife 3 play days.",
            f"Check (iii) after the fix: in Stage 0's chronological order every player's Tenerife 3 matches are contiguous, "
            f"follow his previous event ({n_t2} of 32 come from Tenerife 2, the rest from Manama, Pune, M15 Villena, "
            f"M25 Vila Real or AO qualifying) and precede his next (Lugano, Szekesfehervar, Murcia, Miami, ...), days in order.",
            "Size of the present leak (independent code): 136 distinct Stage 0 matches of these players have an earliest start "
            "after a misdated result counts (old lf + 1) and before that match was played, as the study says; 171 matches of "
            "these players dated 22 Jan - 25 Feb sit after the misdated rows in Stage 0's order although played before them.",
            "No duplicate is created: Stage 0 holds no other copy of Tenerife 3 (its only 2024 Tenerife events are 2839, 2847, 9623).",
        ],
    },
    {
        "group": "G2",
        "corrupt_beyond_doubt": True,
        "fix_clear_unique_correct": False,
        "rows": g2_ids,
        "operation": "set tournament_date",
        "value": "2021-01-10",
        "objections": [
            "The two rows are duplicates, not unique records: Stage 0 already holds the same two walkovers from Sackmann, "
            "atp|2021-581|Q2|atp:106045|atp:208013 and atp|2021-581|Q2|atp:106408|atp:202103 ('Doha Aus Open Qualies', "
            "2021-01-10; same players, round, winner and W/O). Re-dating keeps each walkover twice, now on the same date and "
            "round, so check (i) fails: each of the four players would hold two Q2 rows on the same days.",
            "Check (ii) fails for the fix as proposed (date changed, name 'Australian Open' kept): timing.py then applies the "
            "named rule 'Australian Open' 2021 Q2 (schedule_rules.csv, offsets -29..-26 from the main draw's anchor, +-2), "
            "anchored on Mon 11 Jan 2021, giving the window 11-18 Dec 2020, which does not hold the Q2 day (12 Jan 2021); "
            "each walkover would count from 19 Dec 2020, before it happened. Today's window, 8-15 Jan 2021, holds it, so the "
            "timeline does not leak on these rows now. Only re-dating and renaming to the Sackmann event's name gives a "
            "window (10-14 Jan) that holds it.",
            "The clear, unique correction is a different operation: drop the two TML rows as duplicates of the Sackmann "
            "rows (or merge them into those rows). Setting the date alone is neither unique nor correct.",
            "The date 2021-02-08 follows TML's and the ATP's filing of the 2021 qualifying under the main draw (the ATP's "
            "archive lists it under id 580, 8-21 Feb), the usual convention for Slam qualifying. What is corrupt is that "
            "these two rows were not merged with Sackmann's own 2021 qualifying event, so they sit four weeks late in "
            "Stage 0's order as second copies.",
        ],
        "evidence": [
            "atptour.com news of 17 Dec 2020 (https://www.atptour.com/en/news/atp-announces-updated-start-to-2021-calendar): "
            "'Australian Open men's qualifying will take place from 10-13 January in Doha'.",
            "Wikipedia '2021 Australian Open - Men's singles qualifying': held at the Khalifa International Tennis and Squash "
            "Complex, Doha; second round Sweeny d. Kudla w/o and Vilella Martinez d. Cerundolo w/o.",
            "atptour.com AO 2021 results archive (id 580): the qualifying is listed under the main draw's header (8-21 Feb "
            "2021); Q2 Sweeny/Kudla and Vilella Martinez/Cerundolo with no score; Q3 Stakhovsky d. Sweeny, Vilella Martinez "
            "d. Wu, which Stage 0 holds from Sackmann with exact days 12-13 Jan 2021.",
            "Stage 0's Sackmann twins: source rows 2438 and 2451 of event 2021-581, dated 2021-01-10, windows 11-13 Jan.",
            "Simulation (timing.py's functions; they reproduce today's windows for both rows): proposed fix gives "
            "2020-12-11..2020-12-18; the same date with Sackmann's event name gives 2021-01-10..2021-01-14.",
        ],
    },
]
(HERE / "votes.json").write_text(json.dumps(votes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote votes.json:", [(v["group"], v["corrupt_beyond_doubt"], v["fix_clear_unique_correct"], len(v["rows"]))
                            for v in votes])
