# Proposed first-serve corrections, Roland Garros 2022–2025 and the Paris Olympics 2024: brief for the reviewers

9 October 2026 · Written by the lead session for three independent reviewers (R1-rederive, R2-skeptic, R3-referee) · Item 6, step 2 of [the adoption checklist](../../../../docs/studies/adoption_framework/checklist.md).

## 1. What you are deciding

The owner's instruction (checklist item 6): "If a recount validates, write the proposed per-match corrections. Have three independent reviewers (subagents) check them, as on 8 Oct, and keep only what all three confirm."

**The rule, as on 8 Oct 2026** ([decision](../../../../docs/decisions/2026-10-08-corrupt-data-fixes.md)). A correction is applied only where all three reviewers confirm both points:
* the row is corrupt beyond reasonable doubt;
* the fix is clear, unique and correct.

All three must name the same rows, the same operation and the same values. **You may narrow the scope:** confirm a class only for some rows, or only for rows that pass a test you state. Anything short of unanimity is left as it is. **Treat every claim below as a claim to check, not a fact.**

You judge **the data only**. Whether the corrected data enters the model is decided later (step 3, a candidate build under the frozen-reference rule, then the owner's acceptance). Don't weigh model performance; no model result is read in this step.

## 2. The fault, and why it was not corrected on 8 Oct

* **The fault** ([input-data audit § 3.2](../../../../docs/studies/input_data_audit/README.md)). In Sackmann's Roland Garros rows of 2022–2025 (qualifying and main draw, both tours) and the Paris Olympics 2024 (played at Roland Garros), second serves are booked as first serves. First serves in read +5 points in qualifying, +0.6 to +2.4 in the main draw, +6 to +8 at the Olympics. Example: Li Tu, RG 2025 Q1, 82 first serves in where RG's statistics say 57.
* **Rejected on 8 Oct, unanimously:**
  * **F5 (RG 2025 from RG's key statistics).** The proposed fix replaced the whole box. RG's statistics "count differently from Sackmann even where nothing is wrong": all nine counts agreed in about half of main-draw rows, serve points in 92–94%, service games in 68–84%. No clean RG overlap existed to show the feed measures what Sackmann measures. A narrower fix (the split only) was suggested by two reviewers as "a different operation".
  * **F6 (RG 2022–24, the Olympics).** "The fault shows only edition by edition, and no per-match record is held."
  * The reviewers' verdicts are in `data/studies/input_data_audit/fixes/A1-rederive/verdict.json`, `A2-skeptic/`, `A3-referee/` (candidates F5 and F6).
* **The Slam box-score decision of 6 Oct** ([decision](../../../../docs/decisions/2026-10-06-slam-box-scores.md)) left "Sackmann's Roland Garros men's qualifying of 2022–2025" flagged "until a study measures its effect". This step is that study's data part.

## 3. What is new since 8 Oct

The owner approved collecting and decrypting every RG edition's own files on 8 Oct ([decision](../../../../docs/decisions/2026-10-08-scraping-approved.md)). Collected today, with receipts and raw copies:

| Record | Editions | Where (raw) | Staged / read by |
|---|---|---|---|
| **RG's own statistics** (rolandgarros.com's plain match API: per match and set, aces, double faults, "first serve" in/served, "win on 1st serve" won/in, "win on 2nd serve" won/(served − in), break points won, receiving points, total points won) | 2019–2025, main draw and qualifying | `data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz` | `data/dump/points/rolandgarros/statistics.parquet`, `matches.parquet` (adapter `src/ingest/point_sources/rolandgarros.py`) |
| **RG's own point-by-point** (Infosys MatchBeats: every point with its server, `serve` 1 or 2, scorer, result A/DF/...) | 2019–2024 (new, raw only), 2025 (match-centre file), 2026 (API) | `data/raw/point_sources/infosys_slams/RG/<year>/<route>/<code>.json.gz` (encrypted envelopes; decrypt with `src.ingest.point_sources.infosys_slams.decrypt` and `blocks_of`) | not staged for 2019–2024 (the serve-speed panel reads the shared table); `src/eda/rg_first_serve_recount/sources.py` reads the raw files |
| **The Paris 2024 Olympic results files** (olympics.com, via the Wayback Machine: per player 1ST_SERVE in/attempts with points won, 2ND_SERVE, ACES, DBL_FAULT, BREAK_PTS, PTS_WON_SERVE; and a play-by-play whose results are PS1/PS2/PR1/PR2/A1/A2/DF) | 125 of the 128 singles matches | `data/raw/point_sources/olympics/OG2024/RES_ByRSC_H2H/<unit>.json.gz` | `data/dump/points/olympics/stats.parquet`, `pbp.parquet`, `units.parquet` (adapter `src/ingest/point_sources/olympics.py`) |

Already held: RG's Infosys key statistics 2025–26 (`data/dump/points/infosys_slams/keystats.parquet`), the AO's Infosys MatchBeats 2025, the Hawk-Eye Court Vision copy (RG 2019–24, AO 2020–24; `data/dump/points/slam_ball_tracking/`), SofaScore (`data/dump/points/sofascore_tournaments/`), the Match Charting Project (`data/dump/points/match_charting_project/`).

## 4. The lead's claims (to check)

The lead's code is `src/eda/rg_first_serve_recount/` (`sources.py`, `link.py`, `recount.py`, `propose.py`); its tables are in `data/studies/rg_first_serve_recount/`. Counts are Sackmann's: serve points include double faults; second-serve points = serve points − first serves in.

* **C1. The recount from a Slam's own point-by-point is exact wherever the point file is complete.** At the AO 2025 (where Stage 0's rows match the hand charts), the MatchBeats recount equals Stage 0's first serves in on every row whose serve points agree (`ao_check.csv`, `ao_rows.csv`); the rows that differ are point files missing points. The Olympic play-by-play equals the Olympic statistics on every complete row (`agree_olp_vs_ol.csv`).
* **C2. RG's two own records agree.** RG's statistics equal RG's MatchBeats recount on first serves in and first-serve points won, 2019–2025 (`agree_mb_vs_api.csv`).
* **C3. In the editions before the fault (2019–2021), RG's statistics equal Sackmann's rows on all eight counts** (`agree_api_vs_raw.csv`, `control_2019_2021.csv`): 2,732 of 2,740 linked player rows. The other 8 are four 2021 women's matches whose two boxes Sackmann has exchanged between winner and loser (Muchova–Petkovic, Peterson–Rogers, Siniakova–Zidansek, Bogdan–Badosa); exchanged back, they are equal too. If this holds, RG's statistics measure what the training data measured, the point F5's reviewers could not show.
* **C4. In 2022–2025 and at the Olympics, Sackmann's rows differ from the official record**, mostly by first serves in alone, with the extra first serves won at second-serve rates (`proposal_summary.json`, `proposed_rows.csv`). Court Vision (2022) and the Match Charting Project side with the official record (`disputed_referees.csv`, `agree_cv_vs_api.csv`, `agree_mcp_vs_*.csv`).
* **C5. Other sources cannot referee the split.** SofaScore's point records carry no serve number, and its box scores equal Sackmann's at RG (8 Oct: 95.5–100%), so it shares the fault. The Court Vision copy recounts AO rows exactly in only 80–99% of complete rows, and its 2023–24 RG copy lacks many faulted first serves (the share of points played on a second serve falls from 37% in 2021–22 to 27% and 16%).
* **C6. Every corrected side now reads the official split, nothing else changes, and Stage 0's split checks (B1–B3, B6, B7) pass** (the dry run in `proposal_summary.json`).

## 5. The proposal

`proposed_corrections.csv` (one row per raw Sackmann row, in the columns of `data/studies/input_data_audit/fixes/row_corrections.csv`) and `proposed_rows.csv` (one row per player row, with every source's counts).

* **Scope:** Sackmann's player rows of RG 2022–2025 (both tours, main draw and qualifying) and the Paris Olympics 2024.
* **The official record:** RG's statistics for RG rows; the Olympic results file for Olympic rows. Required: the record's own consistency checks pass for both players (RG: the denominators of "win on 1st serve" and "win on 2nd serve" equal first serves in and serve points − first serves in; receiving points' denominator equals the opponent's serve points; total points won = points won on serve + on return. Olympics: status OFFICIAL; PTS_WON_SERVE = first + second-serve points won; 2ND_SERVE attempts = serve points − first serves in).
* **The venue's second record may veto:** where RG's MatchBeats (or RG's key statistics, 2025) or the Olympic play-by-play holds every point of the row (the same serve points), it must give the same split; otherwise the row is not proposed (one row was dropped this way).
* **Classes of a player row** (Sackmann against the official record):
  * **A, "split":** only first serves in, first-serve points won and second-serve points won differ. Serve points, aces, double faults, serve points won and break points faced and saved are equal. Sub-classes by Sackmann's first serves in: "+" (more), "−" (fewer), "0" (equal, with points won moved between the serves).
  * **B, "split_other":** the split differs, serve points and serve points won agree, and an ace, double-fault or break-point count also differs. The proposal corrects only the split; the other count stays as it is.
  * Not proposed: "points" (serve points or serve points won differ; partial boxes among them), "other" (the split agrees, something else differs), "equal", "no_record".
* **The operation, `replace_split`** (`src/eda/input_data_audit/corrections.py`, added today with tests; no decided table uses it). For each side whose three split counts are given:
  * the source row must still read the table's serve points (and its aces and double faults, where given);
  * its serve points won (1stWon + 2ndWon) may not change;
  * then 1stIn, 1stWon and 2ndWon take the given values;
  * any mismatch stops the build.
* **Fix ids:** `RGFSA`, `RGFSB` (Roland Garros, classes A and B) and `OGFSA`, `OGFSB` (the Olympics). A match row with a B side is labelled B.

## 6. Points to settle

1. **Does the recount validate?** Is the method exact where the truth is known (C1), and do RG's own records agree with each other (C2)?
2. **Is the official record the right reference, row by row?** Does RG's record measure what Sackmann measures where nothing is wrong (C3)? Could RG's statistics be the wrong ones on the disputed rows? Is the Olympic results file the right reference for the Olympics, where no clean edition can be compared?
3. **Class A:** are these rows corrupt beyond reasonable doubt? All three signs, or only "+"? Any minimum size? Are the "−" and "0" rows the same fault or another error, and does it matter for the fix?
4. **Class B:** is it a clear fix to correct the split and leave a differing ace, double-fault or break-point count as it is?
5. **Links:** is every proposed row the right match and the right player (RG codes to Stage 0 by names; the Olympic units by names and round)?
6. **The values:** do your own counts equal the proposed ones?

## 7. Your lens

* **R1-rederive: recompute every claim from the raw files, with your own code.**
  * Parse the RG API documents and the Olympic files yourself.
  * Decrypt the Infosys files with the adapter's `decrypt` (that is the site's own step, not the analysis) and recount yourself.
  * Read Sackmann's rows from `data/dump/matches/sackmann_archive/{atp,wta}/` (or `stage0_build.normalise(stage0_build.load_raw())`).
  * Link them yourself.
  * Don't import `src/eda/rg_first_serve_recount/` or read its tables until you have your own numbers; then compare and explain every difference.
* **R2-skeptic: attack every claim. Look for another explanation and for rows that should not be there.**
  * Convention differences: retirements, penalty points, lets, overrules.
  * Linking errors: sisters, married names, the same pair twice.
  * Whether the official record could be the faulty one.
  * Whether the control years really are clean.
  * Whether the class rules let in rows they should not.
  * Use any of the lead's code and tables, and check them.
* **R3-referee: check against independent records and simulate the fix.**
  * The Match Charting Project (hand-charted; noisy: it matches Sackmann's first serves in on only about half to four-fifths of rows even in 2019–21).
  * Court Vision where you judge it reliable.
  * Pooled rates by edition against the other years.
  * Apply the proposed table to the raw rows with `src.eda.input_data_audit.corrections.apply_row_corrections`, and run Stage 0's box checks (`stage0_build.box_scores` needs parsed scores; reproduce the per-side checks B1–B3, B6 and B7 at least).
  * Check the rows Stage 0 now drops for a failed check that the fix would bring back.

## 8. What to write

In `data/studies/rg_first_serve_recount/review/<your name>/`. Your scripts go in `src/eda/rg_first_serve_recount/review/<your name>/`.

* **`verdict.json`:**
  ```json
  {"reviewer": "R1-rederive", "lens": "rederive",
   "recount_validated": {"vote": "yes|no", "reasons": "..."},
   "classes": {"RGFSA": {"vote": "confirm|narrow|reject", "corrupt_beyond_doubt": true, "fix_clear_and_correct": true,
                         "scope": "which rows, by what test", "reasons": "...", "checks": ["script: what it showed"]},
               "RGFSB": {...}, "OGFSA": {...}, "OGFSB": {...}},
   "other_findings": "..."}
  ```
* **`scope.csv`:** one row per side you confirm, with **the values you derived**:
  * `source_file, source_row, side, first_in, first_won, second_won`;
  * `side` is `w` or `l` (the raw row's winner or loser);
  * optionally `fix`, `notes`.

  A side you do not list is not confirmed.
* Any evidence files you want.

## 9. Limits

* **Read-only** everywhere except your two folders.
* Don't run the lead's `recount.py`, `propose.py` or `consensus.py`: they rewrite the study's tables.
* Don't read the other reviewers' folders.
* Use `./python.sh` (the project's `tennis` environment), from the repository root in Git Bash.
* No network access is needed; don't fetch anything.
* No GPU, no `run_chain.py`, no git commands.
* Other sessions run in parallel; keep memory use moderate (Stage 0's raw loader takes about a minute and a few GB).
