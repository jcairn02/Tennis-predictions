# Swapped service games at the Australian Open and Roland Garros: brief for the reviewers (group SVX)

9 October 2026 · Written by the lead session for the three round-2 reviewers (R1-rederive, R2-skeptic, R3-referee) · Point 3 of the owner's [decision of 9 Oct](../../../../../docs/decisions/2026-10-09-roland-garros-box-scores.md).

## 1. What you are deciding

**The owner decided** (9 Oct 2026, "Execute and fix"): "At the Australian Open and Roland Garros, Sackmann's rows often give the two players each other's service games, mostly as the score gives them if the winner had served first. The two counts are exchanged back (`exchange_svgms`, decided on 8 Oct as F2y) wherever the Slam's own point record proves who served first; each match confirmed by three reviewers."

**Your bar is the 8 Oct one.** Confirm a match only if both of these hold:
* its row is corrupt beyond reasonable doubt;
* exchanging the two service-game counts is the clear, unique and correct fix.

Only matches all three of you name are kept. You judge the data only. The fix joins the Roland Garros candidate (report § 8.5), which is adopted on a harm check.

**This round** covers the editions whose MatchBeats files are held in full: Roland Garros 2019–2026 and the Australian Open 2025.
* AO 2018–2024 and 2026, and RG 2013–2018, are being fetched now (`data/studies/rg_first_serve_recount/followup/collection/`).
* They will come to you as an addendum, with the same method.

## 2. The lead's claims (to check)

Code: `src/eda/rg_first_serve_recount/service_games.py` and `sources._mb_counts` (`served_first`, `alternation_ok`, `sv_gms_regular`).

Tables: `data/studies/rg_first_serve_recount/followup/service_games/`:
* `matches.csv`, one row per player row of a Stage 0 match with a MatchBeats file;
* `proposed_swaps.csv`;
* `summary.json`.

* **S1. Who served first is proven by the point record.** The first point of the file is game 1 of set 1. Every game the file holds, in order, is served by the player the alternation of serve names, a tiebreak taking its turn by its first point. Where that fails, the match is "unproven" and not proposed.
* **S2. The true service games** come from the row's score and that first server.
  * Servers alternate game by game through the match, and a tiebreak takes one turn without counting as a service game (Sackmann's convention in his correct rows).
  * A retirement's score holds only finished games, so its unfinished game does not count either (Sackmann never counts it).
  * Where MatchBeats holds the whole match, its own count of completed non-tiebreak games equals this truth on every proposed row.
* **S3. "Swapped":** the row's two counts are the truth's two counts exchanged, and the truth's two differ. 270 of the 324 swapped matches are exactly what the score gives if the winner had served first. Every other difference ("other": equal counts where the score forces unequal ones, totals off by one, ...) is not proposed.
* **S4. Left out because the candidate already changes them another way:**
  * a row the decided corrections of 8 Oct name (none here);
  * a Roland Garros match with a confirmed override, whose box takes MatchBeats' service games (1, in 2023).
* **S5. Proposed:** 323 matches. AO 2025: 81. RG 2019: 71; 2020: 79; 2021: 92.
* **S6. After the exchange,** each row's service games equal the truth. The total is unchanged, so B5 is unchanged. Check B8 yourself (breaks conceded no more than service games).

## 3. Points to settle

1. Is the first server proven in every proposed match (S1)? Could a file's first point not be the match's first point, or could a file hold games out of order?
2. Is the truth right (S2)? Check tiebreaks, the match tiebreak at 6-6 in a final set (RG from 2022, AO), retirements, and defaults.
3. Is the row really swapped, rather than some other error that happens to look like an exchange?
4. Links: is each file the right match, with the right players?
5. Is `exchange_svgms` the right and only change for each row? Does any row already take another correction in the candidate?

## 4. Your lens (as before)

* **R1-rederive:** decrypt and recount the MatchBeats files with your own code: first server, alternation, games. Derive the truth from the score yourself, and link to Sackmann's rows yourself. Compare only then.
* **R2-skeptic:** attack the claims.
  * Snapshot files that start late or stop early.
  * Mislabelled servers.
  * Score orientation (the row's winner against RG's or the AO's).
  * Whether Sackmann's count could be right and the point record wrong.
  * TML rows against Sackmann rows.
* **R3-referee:** check against independent records, and simulate the fix.
  * Records: Court Vision (RG 2019, 2020 and 2022, and AO 2020–2024 where it overlaps) and the hand charts, which name the server point by point.
  * The simulation: apply the swaps with `corrections.apply_row_corrections`, together with the candidate's other tables (`followup/confirmed/candidate/`), and run Stage 0's checks.

## 5. What to write

In your round-2 folder (`data/studies/rg_first_serve_recount/followup/review/<you>/`), with scripts in `src/eda/rg_first_serve_recount/review_followup/<you>/`:

* **`swaps_scope.csv`:** `source_file, source_row, match_id`, one row per swap you confirm. A swap you don't list is not confirmed.
* **An "SVX" entry in `verdict.json`:** `{"vote": "confirm|narrow|reject", "corrupt_beyond_doubt", "fix_clear_and_correct", "scope", "reasons", "checks"}`.

Limits as before:
* write only in your two folders;
* no network, git, GPU or `run_chain.py`;
* don't run the lead's `service_games.py`, `whole_box.py` or consensus scripts;
* don't read the other reviewers' folders.
