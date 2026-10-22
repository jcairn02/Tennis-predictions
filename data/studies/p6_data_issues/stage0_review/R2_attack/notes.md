# R2 (attack): review of the Stage 0 date corrections G1 and G2

14 Oct 2026 · Reviewer R2, the attack lens, under the [three-reviewer rule of 8 Oct](../../../../../docs/decisions/2026-10-08-corrupt-data-fixes.md) · Votes: [votes.json](votes.json)

## Verdicts

| Group | Rows | Corrupt beyond doubt | The proposed fix | My vote |
|---|---:|---|---|---|
| G1, Tenerife 2024 | 31 | Yes | Set `tournament_date` to 2024-02-26 | **Confirm** |
| G2, AO 2021 qualifying walkovers | 2 | Yes, but as duplicates, not as misdated rows | Set `tournament_date` to 2021-01-10 | **Reject**: drop the rows instead, put to a vote of its own |

## G1: confirmed

* **What the rows are.** All three of Tennis My Life's 2024 Tenerife draws (ids 9623, 2839 and 2847) carry the name "Tenerife 1" and the date 20240121, which is the Sunday that ends Tenerife 1's week.
  * Sackmann has rows for 9623 (15 Jan) and 2839 (19 Feb), and Stage 0 keeps those.
  * Sackmann has no rows for 2847. So Stage 0 keeps Tennis My Life's 2847 rows, with Tennis My Life's date.
* **Which draw they are.** The 31 rows form a single draw of 32 players. Each one matches a match of TennisLive's "ATP Tenerife 3 Challenger": the same winner and the same set scores, 31 out of 31. SofaScore lists the same draw.
  * The main draw ran 26 Feb to 3 Mar 2024. Four first-round matches were played on Monday 26 Feb.
  * The final was Kukushkin d. Gigante, 6-2 2-0, retired.
* **Ruled out:**
  * *Duplicates.* None of the 31 pairs met at Tenerife 1 or Tenerife 2.
  * *Two draws mixed together.* The bracket is consistent.
  * *Stage 0's date being right after all.* The players' other matches make it impossible. In the week of 15 Jan, Kukushkin lost a quarter-final at Tenerife 1 and Gigante won Nonthaburi 3. In the week of 22 Jan, Demin and Landaluce were at Manacor and Krueger was at Indian Wells 2.
  * *A clash in the proposed week.* None of the 32 players has another Stage 0 match in that week.
* **The value.** 2024-02-26 is both the first day of the main draw and the Monday of the event week. It matches:
  * C05's rule: "the main draw's first date, as in Sackmann";
  * Sackmann's dates for the other two Tenerife draws, both Mondays;
  * Stage 0's other Challenger editions that only Tennis My Life holds, which are dated on Mondays.

  The alternatives fail:
  * 3 Mar is Tennis My Life's usual end-of-week Sunday. The clock would anchor it to 4 Mar, and its windows would miss the matches played before then.
  * 25 Feb is the first day of qualifying, and Stage 0 holds no qualifying rows of this draw.
* **Side effects.** Changing the date links no row to another source's row, and drops none.
* **The consequence is confirmed.**
  * The clock's windows for these rows now close on 28-31 Jan 2024.
  * 136 other Stage 0 matches of the 32 players read these results before they were played.
* **Noted, not voted.** The same rows also carry a wrong name ("Tenerife 1") and a blank surface. Neither affects the date fix.

## G2: rejected

* **They are duplicates.** Stage 0 already holds both walkovers from Sackmann: Sweeny d. Kudla and Vilella Martinez d. Cerundolo.
  * Sackmann files them as `atp|2021-581|Q2|...`, under "Doha Aus Open Qualies", dated 2021-01-10.
  * They have the same players, the same round, the same walkover and the same winner as the two Tennis My Life rows.
  * The study's note "no Sackmann row" missed them, because Sackmann files this qualifying under its own id (2021-581), not the main draw's (2021-580).
* **Why they stayed unlinked.** Stage 0's linker accepts a match more than 10 days apart only when the set scores are identical, and a walkover has no set scores. The two sources date the draw 29 days apart. The draw's other 110 Tennis My Life rows linked through their scores.
* **The date is Stage 0's convention, not the fault.**
  * Every Sackmann Slam qualifying draw of 2015-2025 carries its main draw's date (41 of 42). The one exception is this AO 2021 draw, which Sackmann files as an event of its own.
  * C05 does the same for Tennis My Life's qualifying rows.
  * The clock has a rule for exactly this case, the "Australian Open" 2021 qualifying, with offsets of -29 to -26 days. It turns 2021-02-08 into a window of 8-15 Jan 2021, which contains the real days. Today there is no leak.
* **The proposed fix would create a leak.** With the name left as "Australian Open", the clock would apply the same offsets from the new date, giving a window of 11-18 Dec 2020. I reproduced this from the clock's own arithmetic (it gives today's window exactly); timing.py was not rerun. The rows would also stay exact duplicates.
* **Counter-proposal, for its own vote.** Drop `atp|2021-580|Q2|atp:106045|atp:208013` and `atp|2021-580|Q2|atp:106408|atp:202103` as duplicates of the two 2021-581 rows. Linking them to those rows has the same effect.

## Process (short log)

* **Brief:** the parent agent's brief, as received. Interpretation: vote only on the claim as stated, attack it, and record any other fix as an objection rather than a vote. Session `b2538231-694b-4911-acc2-603ecdaff3ea`. I read no other reviewer's folder, sent no network request, and read no model result.
* **Order of work, and what I had seen before each decision:**
  1. Read the decision of 8 Oct, the study's README, C05 in `stage0_build.py`, and the clock's `anchor_day` and rule code.
  2. Read Stage 0's rows (`s01`, `s02`), then the attacks: duplicates, bracket, Tennis My Life's dating convention, clashes (`s03`, `s04`). I saw the three-way "Tenerife 1" labelling here.
  3. Checked the sources: Sackmann's staged files, TennisLive and SofaScore (`s05`, `s06`). The G1 verdict was settled here.
  4. G2 (`s07`). The duplicate showed up at the first look at Stage 0's AO 2021 rows. I then read `link_tml` and `pick` for the mechanism, and the clock's rules and windows (`s08`).
* **Threats to validity:**
  * The G2 window after the fix is computed, not rerun.
  * The G1 match to TennisLive uses surname tokens. The scores agree on all 31, so a wrong match is unlikely.
  * Whether walkovers feed any input was not checked. It does not change either vote.
* **Reproduction:**
  * Run `./python.sh` on `s01`-`s08` in this folder, which only read files; then `s09_write_votes.py` writes `votes.json`.
  * Outputs on disk: `s03_out.txt`, `s04_out.txt`, `s07_out.txt`, `g1_players_jan_mar_2024.csv`, `tennislive_tenerife3_2024.csv`, `g1_vs_tennislive.csv`.
