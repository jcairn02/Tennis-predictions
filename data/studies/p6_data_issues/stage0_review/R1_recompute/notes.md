# R1 (recompute): Stage 0 date fixes G1 (Tenerife 2024) and G2 (AO 2021 qualifying)

Reviewer R1, one of three under the [8 Oct 2026 rule](../../../../../docs/decisions/2026-10-08-corrupt-data-fixes.md). Session `b2538231-694b-4911-acc2-603ecdaff3ea`, 14 Oct 2026. Votes: [votes.json](votes.json).

* **Brief:** "Your lens: R1, recompute. Recompute every claim from the raw files ... Confirm or refute each number in the claim (31 rows, the dates, the windows closing 28-31 Jan, the 136 later matches that read them). Same for G2's two rows."
* **Rules kept:**
  * read-only, with writes to this folder only;
  * no request to any web host;
  * the other reviewers' folders not read;
  * no model result read.
* **Process:** the study's tables were opened only at the end, to compare against my own reader count (`clock_leak_readers.csv`).

## Verdicts

| Group | Corrupt beyond doubt | Fix clear, unique, correct | Rows | Value |
|---|---|---|---:|---|
| G1 Tenerife 2024 | yes | yes | 31 | 2024-02-26 |
| G2 AO 2021 qualifying | no (as claimed) | no | 0 | (2021-01-10 rejected) |

## G1: every number in the claim confirmed

* **The 31 rows.** Stage 0 holds 31 rows with tournament_id 2024-2847, dated 2024-01-21, from Tennis My Life. Their `source_row` 280-310 are the raw file's data lines 280-310.
  * Tennis My Life's file names all three 2024 Tenerife editions "Tenerife 1" and dates all three 20240121.
  * Only 2847 reaches Stage 0 from that file, and no other Stage 0 row carries 2024-01-21.
* **Which tournament they belong to.** All 31 rows match the third Tenerife Challenger, and only it, in both TennisLive and SofaScore. Each one matches on the player pair, the winner, the games and the tiebreak points.
* **When they were played.** 26 Feb - 3 Mar 2024; the final, Kukushkin d. Gigante 6-2 2-0 ret., was on 3 Mar.
* **Controls.**
  * Sackmann's 2024-9623 is the January edition: final Nakashima d. P. Martinez, 31 of 31 main-draw matches equal to the sources.
  * Sackmann's 2024-2839 is the 19 Feb edition, also 31 of 31.
  * Sackmann has no copy of the third edition, and Stage 0 holds none of the 31 matches twice.
* **The clock.**
  * The windows close on 28-31 Jan.
  * Play day minus window end is 29 to 32 days, so each result counts 28 to 31 days early.
  * None of the 31 windows holds its play day.
* **Early readers: 136**, with 335 (reader, match, player) rows. My definition: the reader shares a player; its earliest start is at or after the window end + 1; and that start is on or before the match's real play day.
  * Readers' earliest starts run from 29 Jan to 24 Feb.
  * 93 of the 136 are evaluation matches.
  * My set equals the study's table row for row.
* **The fix, simulated** with timing.py's own `anchor_day`, `rule_label` and `rule_windows`.
  * The anchor moves from 22 Jan to 26 Feb; the rule and its offsets are unchanged.
  * All 31 windows then hold their play day.
  * 26 Feb is the Monday convention: 787 of the 804 ATP Challenger editions of 2022-25 in Stage 0 are dated on a Monday.
* **Remarks that do not block the fix:**
  * The name "Tenerife 1" is also wrong; it is Tenerife 3. The clock ignores Challenger names.
  * 2024-02-25 would give the clock the same anchor, but 26 Feb is the convention value.
  * Tennis My Life may repair or reorder its file; the correction's guards must then stop the build.
  * Per-player features ordered by date probably also see these matches out of order today. I did not check this.

## G2: the numbers confirmed, the corruption and the fix not

* **Confirmed as stated:**
  * data lines 98 and 106 of Tennis My Life's file are the two walkovers;
  * the Stage 0 ids and the 2021-02-08 date are as the claim gives them;
  * the qualifying ran 10-13 Jan 2021 (TennisLive, SofaScore), and both walkovers were in Q2 on 12 Jan;
  * Sackmann dates the draw 2021-01-10.
* **What the claim misses:**
  1. **The two rows are duplicates.** Sackmann's copies are already in Stage 0, under tournament_id 2021-581: same players, same round, same walkover, same winner. The linker left both pairs unlinked.
  2. **The date is the convention, not corruption.**
     * Stage 0 dates AO qualifying with the main draw's date in 2019, 2020, 2022 and 2023.
     * The clock has a named rule for these 2021 rows, giving a window of 8-15 Jan, which holds 12 Jan.
     * Nothing reads them early today.
  3. **The proposed fix would create a leak.** With the name kept, the same rule would apply from 11 Jan, giving a window of 11-18 Dec 2020.
     * The walkovers would count from 19 Dec 2020, 24 days before they happened.
     * 8 matches of the same draw would read them early.
* **The fix the evidence supports instead** is to drop the two Tennis My Life rows as duplicates. That needs its own proposal and review.

## Where a flaw would hide

* **Name matching (s06):** it requires a shared token beyond a shared first name. A looser first version produced 2 false hits, through the first names "Daniel" and "Martin", and they were discarded. In the strict run, every match had exactly one hit per source.
* **SofaScore times** are UTC, and Tenerife's local time equals UTC in winter. TennisLive gives days only, at a placeholder 09:00.
* **Simulating the fix by shifting each window by 35 days** assumes the windows don't depend on the date beyond the anchor. That holds here: these rows have no source links, siblings or event shift, the year is unchanged, and `rule_windows` was rerun.
* **The G2 simulation** used the clock's functions, not a full rebuild. A rebuild could add links for the moved rows, but nothing currently links them.

## Reproduction

`./python.sh <script>` from the repository root, in order: `s01_stage0_rows.py` to `s11_g2_readers_after_fix.py`, then `s12_write_votes.py`. Run `s09` with `-B` so that importing timing.py writes no bytecode.

Outputs:
* `g1_play_days.csv` (loose match, superseded);
* `g1_play_days_strict.csv`;
* `g1_clock_windows.csv`;
* `g1_leak_readers_R1.csv`;
* `votes.json`.
