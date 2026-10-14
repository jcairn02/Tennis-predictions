# Service games set from the score: brief for the reviewers (group SVS)

9 October 2026 · Written by the lead session for the three round-2 reviewers · The owner's word, the same evening: "Fix the remaining service-game errors that aren't simple swaps … plus 123 Roland Garros 2017 matches recorded as 0 and 0 … It needs a new correction type and the same three-reviewer check."

## 1. What you are deciding

* **The fix.** Where the Slam's own point record proves who served first (the same proof as group SVX), set both players' service games to the truth. The truth is the score's alternation of serve, as in SVX.
* **Which matches.** Those where the row's counts are:
  * missing, or 0 with serve points played, which Stage 0 already treats as missing ("fill");
  * different from the truth without being an exchange ("other").
* **The operation** is new: `set_svgms` (`src/eda/input_data_audit/corrections.py`, rule E8 in `stage0_build.py`; tests in `test/input_data_audit/test_corrections.py`).
  * It writes the two counts given in `w_SvGms` and `l_SvGms`.
  * It first checks that the source row still reads the table's serve points (`w_svpt`, `l_svpt`) and the counts it replaces (`value`, "<w>/<l>", blank for a missing count).
  * Any mismatch stops the build.

**Your bar is the 8 Oct one:** the row is corrupt (or a count is missing) beyond reasonable doubt, and the new counts are the clear, unique and correct values. The lead's proposal adds one condition, the **consistency test** (R2's identity, used in SVX):
* each player's games won, tiebreaks apart, must equal their service games, minus their breaks conceded, plus the opponent's breaks conceded;
* breaks are the row's own break points faced minus saved.

A row whose break points are wrong too fails it, so setting its service games alone would not settle it. That is the reason Stosur d. Halep was kept out of SVX. Such rows are left out (2 here).

## 2. The proposal

`src/eda/rg_first_serve_recount/service_games.py`; tables in `data/studies/rg_first_serve_recount/followup/service_games/`:
* **`proposed_sets.csv`:** 558 rows (fix SVS). 460 are "fill" and 98 are "other".
  * AO 2019–2026: 55.
  * RG 2013 and 2014: 167 each. These are Sackmann's rows with serve points but no service games.
  * RG 2015: 8 · 2016: 3 · 2017: 132 · 2018: 6 · 2019: 7 · 2020: 4 · 2021: 7 · 2023: 1 · 2024: 1.
  * The two RG 2022–2025 matches take no override.
* **`matches.csv`:** now with the classes no_box, fill, other, swapped, equal, unproven and incomplete; the row's serve points and break points; and `consistent_true` / `consistent_row`.
* **Left out:**
  * 141 matches with an RG override (their box already takes RG's service games);
  * 1 row the decided corrections name;
  * the 2 failing the consistency test.
* **The swap table** (`proposed_swaps.csv`) is byte-identical to the 810 you reviewed. The consistency test also backs those swaps: the truth passes it in 809 of 810 (Stosur–Halep fails), and the row in 1.

## 3. Points to settle

1. Is the first server proven in every proposed match?
2. Is the truth right (tiebreaks, retirements, match tiebreaks)?
3. **Fills.** Are the rows really otherwise complete? Is filling a blank or "0 and 0" with the truth right? For RG 2013–2014, Sackmann's rows carry serve points but no service games.
4. **"Other".** Is each a real error of the row, and not, for example, a tiebreak counted the other way? The truth counts no tiebreak, as Sackmann's correct rows do.
5. Does every set pass Stage 0's checks afterwards (B5, B8)? Does any row take another correction in the candidate?

## 4. What to write

In your round-2 folder:
* **`sets_scope.csv`:** `source_file, source_row, w_SvGms, l_SvGms`, one row per set you confirm, with **the values you derive**. A set is kept only where all three of you give the same values.
* **An "SVS" entry in `verdict.json`:** `{"vote", "corrupt_beyond_doubt", "fix_clear_and_correct", "scope", "reasons", "checks"}`.

Lenses and limits as before:
* write only in your two folders;
* no network, git, GPU or `run_chain.py`;
* don't run the lead's scripts;
* don't read the other reviewers' folders.
