# Roland Garros box scores and the Slams' service games: process log of the candidate build and harm check

9 Oct 2026, 23:55 – 10 Oct 2026, 00:30 (UTC−7) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session: `640ec189-24f6-4fba-ac7c-fc7670902a2c` · For a future reviewer · Report: [README.md](README.md) § 10.3

**Scope.** This log opens at the resumption of the study for steps 3–4 of checklist item 6: the candidate build and its harm check. The process-log default came on 9 Oct, while the study was in progress ([decision](../../decisions/2026-10-09-study-process-logs.md)). Everything before that point is in the README, §§ 1–10.2, and is not retrofitted here. Chronology rows marked **R** are *reconstructed, not contemporaneous*: they come from the session transcript and the build's records, written up after a context summary.

## 1. The request

* **The owner's words, verbatim** (10 Oct 2026, 00:46 UTC; 9 Oct, 17:46 local):
  > "Execute these 3 fixes"
  >
  > *(pasted: Claude's own recommendations of § 9.4)* "Run the candidate build and harm check next in the build queue: yes. It's the only step before adoption. Say "go" and I'll check the build sandbox and GPU are free and start it.
  > Take future Australian Open and Roland Garros box scores from the Slams' own feeds: yes, and this matters most for betting. The match data we get for recent and future matches (Tennis My Life) carries both faults at these two Slams. Its 2026 Roland Garros main draw has the first-serve error, and its service games copy Sackmann's. Wimbledon and the US Open already work this way.
  > Fix the remaining service-game errors that aren't simple swaps: yes, as a small follow-up. That's about 1–3% of matches, plus 123 Roland Garros 2017 matches recorded as 0 and 0. Where an independent record holds them, it reads the true count. It needs a new correction type and the same three-reviewer check."
  >
  > "However, if it requires the GPU wait if other CLAUDE processes are clearly using it"
* **Earlier words that govern this phase:**
  * 9 Oct: "Execute and fix" (the decision that declared the harm rule: [RG box scores](../../decisions/2026-10-09-roland-garros-box-scores.md), point 2).
  * 9 Oct: "SUGGEST to me, don't delegate to me. I am only the final arbiter of YOUR suggestions".
* **How it was read:**
  * The three fixes were carried out in order: the sets (§ 10.1), the future feeds (§ 10.2), then the build and the harm check (§ 10.3), with the sets inside the candidate.
  * "Wait if other CLAUDE processes are clearly using it" was read as: never run a fit beside another session's GPU process. A watcher waits until no local TabPFN-environment process has run for three minutes, and `fits.py` holds each fit until the card is free.
  * No question was put to the owner.
* **The target.** This is a harm check of a data repair, not a betting reading.
  * The comparison: `compare.py`, both stages, both tours, seasons 2020–2024 (seasons ≤ 2024).
  * The models take the close as an input, so the reading answers only "does the repair harm the model beyond the close?".
  * The declared primary: "both tours / both stages: candidate vs reference", mLL per match, + = the candidate better.
  * All of it was fixed in the RG decision of 9 Oct, before any reading of this candidate.

## 2. Starting point

* **Code:** commit `677a63f`, plus uncommitted changes from this study and other sessions.
  * This study's: `stage0_build.py` (the override table's `source` column, rule E8) and `input_data_audit/corrections.py` (`set_svgms`).
  * Other sessions', in the chain: `tabpfn_thinking/build_frame.py` and `common.py` (the indoor fill of 9 Oct).
  * The sandbox copied `src/` at setup on 9 Oct (`setup.log`).
* **Data (observed):**
  * The frozen reference: `data/studies/current_best_model/reference_2026-10-08/` (frame, fits, Stage 0).
  * The candidate tables: `data/studies/rg_first_serve_recount/followup/confirmed/candidate/` (overrides `505336f6…`, corrections `25e48366…`, aliases `846cde8d…`).
  * The decided tables they extend, unchanged since 6 and 8 Oct: overrides `f2870e5c…`, corrections `563c6933…`.
  * The sandbox Stage 0 after the trim: `candidate_trim.json`.
* **Earlier looks:** no outcome of this candidate has been read. The reference's 2020–2024 seasons are the project's standing yardstick and have been read by many studies.
* **Environment:**
  * the `tennis` Conda environment (`./python.sh`) for the build and the reading;
  * `tennis-tabpfn-local` (`./python_tabpfn_local.sh`) for the fits;
  * one 32 GB GPU, shared with other sessions.
* **The idea and how it arose:** a verified fix. The corrections are official records confirmed match by match by three independent reviewers (README §§ 8–10.1). Under the adoption-by-kind decision it is a **repair**: data evidence decides it, and the comparison serves as a bug alarm.

## 3. Plan

As declared before this phase (RG decision, point 2; checklist item 6, steps 3–4). Not edited later.

1. **The candidate:** the decided tables plus 1,541 RG overrides, step 2's split for 58 matches, 4 exchanges, 809 service-game swaps and 558 service-game sets.
2. **The build:** `run_chain.py --setup --candidate --out data/studies/current_best_model/2026-10-09_rg_box_scores`; Stage 0 rebuilt in the sandbox with the candidate tables; lanes 0–3; `--collect`.
3. **The fits:** seeds 0–3, seasons 2019–2024 (2019 for stage 2's walk-forward coefficients), on the reference's 58-input list.
4. **The reading:** `compare.py --candidate` (seasons ≤ 2024), the input check first.
5. **The rule:** adopt unless the candidate is worse than the frozen reference by more than 0.1 mLL per match with the whole 95% interval below 0, or an input is flagged "uneven".
   * The 2025–2026 part is adopted with it on the data evidence and is not read.
   * If the rule stops the adoption, report what drove it.
6. **Added after the adoption-by-kind decision of 9 Oct, before any reading:** `adoption_read.py --kind repair` on compare.py's scores.

## 4. Chronology

Local time (UTC−7). "Results" means any outcome-based score of any candidate. **R** = reconstructed. The input check (compare.py's first part) reads inputs, not outcomes, so it is not a result.

| When | Step (command or action) | Why | Results seen by then | Output |
|---|---|---|---|---|
| 9 Oct 17:46 **R** | Owner: "Execute these 3 fixes" (§ 1) | | none | |
| 9 Oct evening **R** | `set_svgms` and rule E8; `service_games.py` sets; three-reviewer review (558 confirmed); the future-feeds decision and builder; candidate tables rebuilt (2,951 corrections); dry run (4,664 rows change, none outside the tables) | the second and third fixes, then the candidate | none | README §§ 10.1–10.2 |
| 9 Oct evening **R** | `run_chain.py --setup --candidate`; Stage 0 in the sandbox | the first fix | none | `setup.log` |
| 9 Oct evening **R** | **Failure:** the shell's `cp` asked before overwriting and silently declined, so the sandbox kept the 2,393-row corrections. Seen in the build log (2,393, not 2,951). Stopped; re-copied with `cp -f`; SHA-256s checked; rebuilt (2,951 logged) | | none | README § 10.3, step 2 |
| 9 Oct evening **R** | `candidate_trim.py`: 35 new matches dropped and 160 newer rows restored, so the candidate differs from the live Stage 0 only in its 2,964 named matches | the sandbox read newer source files | none | `candidate_trim.json` |
| 9 Oct evening **R** | Stage 1's odds (identical to the live table); timeline not rebuilt; lane 0 (32 min); lanes 1–2 (220 and 28 min); lane 3; `--collect` (23:07) | | none | `chain_lane*.json` |
| 9 Oct 23:08 **R** | GPU watcher started; the card was busy with the lower-level-evidence session's fits (99%, 16 GB) | the owner's GPU condition | none | `fits_wait.log` |
| ~23:13 | **Context summary** of the session; work resumed from it | | none | |
| 23:15 | Input check, part 1 only (`compare.input_drift` on the collected frame): 42 of 58 inputs changed; 8 flagged "uneven" | read the input check first | none | (console) |
| 23:16–23:20 | Read the decisions of 9 Oct made by other sessions: the indoor input, adoption by kind of change and its errata, the 57-input amendment, the narrowed freeze | the `indoor` flag; the rules now in force | none | |
| 23:17 | `indoor`: flagged in exactly the 14 women's seasons; 32,634 rows changed = 32,507 women's + 127 men's 2026 US Open. That is the indoor fill, which `build_frame.py` now applies in every build | | none | |
| 23:18 | Stage 0 dose: WTA service-game counts (hold denominator) known in 20 player rows in 2013 and 0 in 2014 in the reference; 348 and 328 in the candidate. Service games changed only at RG and AO (3,493 player rows) | the WTA 2013–2014 flags | none | `input_dose/coverage.csv`, `dose_rows.csv` |
| 23:19 | Size of every input's change: inputs the repair cannot reach are identical; the ATP's 2013–2015 hold inputs move by ~1e-6 SD (a constant pooled across tours) | | none | (console) |
| 23:20 | **Change of plan** (judgment call 1): watcher stopped before any fit started; first collection kept in `first_collect_indoor_filled/`; frame steps rebuilt with `--indoor-men-only`; lane 3; `--collect` | isolate the repair | none | `chain_lane1i.json`, `chain_lane3.json` |
| 23:22 | Rebuilt frame checked: only `in_indoor` differs from the first; `indoor` identical to the reference's; 7 flags left, all in WTA 2013–2014; no WTA match before RG 2013 moves | | none | |
| 23:22 | Watcher restarted | | none | `fits_wait.log` |
| 23:24–23:31 | `input_dose.py` written and run; README § 10.3 (steps 9–10 and a corrected count); checklist item 6; the RG decision record (two decided items, 6 → 7 inputs); the evidence README | evidence for a reviewer | none | `input_dose/` |
| 23:39–23:53 | Fits: 24 of 24, exit 0; every fit on frame `8549316e…`; 8 estimators, temperature 0.9 | | none | `fits.log`, `fits/` |
| 23:55 | This log opened, before compare.py's second part runs | | none | |
| 23:56 | `compare.py --candidate data/studies/current_best_model/2026-10-09_rg_box_scores` (seasons ≤ 2024) | the declared reading | **The first and only look at this candidate's results.** Primary −0.026 [−0.076, +0.023], unresolved, P(better) 0.145; men −0.023, women −0.030 | `vs_reference_2026-10-08/` |
| 23:58 | `adoption_read.py --kind repair` | the reading by kind of change (plan step 6) | the above | `adoption_read.json`: resolution ±0.049; blind; harm no; "adopt, pending the input check" |
| 23:59 | **Verdict:** no harm, so the candidate is adopted under the declared rule. The input check was already read against the dose. The lean was not searched for a cause (judgment call 6) | | the above | |
| 10 Oct 00:00 | Read the lower-level-evidence study's `status.log` and `D_verification.md`: arms are still being built in their own sandboxes, and gate G2 failed at 06:52 UTC on the indoor fill | how to apply the adoption safely | the above | |
| 00:03 | **Judgment call 7:** the swap is deferred to the next coordinated Stage 0 rebuild | | the above | |
| 00:05–00:15 | Class record row `rg_box_scores`. `adopt.py` with tests (7 pass; the study, corrections and continuity suites 94 pass). `adopt.py --check`: ready (overrides 731 + 1,541; corrections 1,522 + 1,429; aliases identical) | | the above | `class_record.csv`, `adopt.py`, `test_adopt.py` |
| 00:15–00:30 | Documents: the README (header, "In short", § 10.3 steps 11–13, § 10.4); the decision record's harm-check section; the decisions index; checklist item 6 ticked; the studies index | | the above | |
| ~00:45 | **Owner, verbatim:** "p15% better is awfuL?? wtf? Thats highly suggestive we shouldnt do it?" | | the above | |
| ~00:50 | Read the level and season slices already in compare.py's `scores.csv` (the same run, read as description, not as a test). Split the interval's seed term (`reading_split.py`) | the owner's question; judgment call 6 revisited | **Second look, the same run:** Slams −0.065 [−0.162, +0.033] (P 0.09; 4 of 4 seeds negative); 500s −0.057 (P 0.12); 1000s −0.001; 250s −0.003; seasons 2020–2024 −0.001 to −0.045, all unresolved. The seed term is 28% of the primary's variance, and 16 seeds would give an SE of 0.0218 instead of 0.0246 | `vs_reference_2026-10-08/reading_split.csv` |
| ~01:00 | **Owner, verbatim:** "so you recommend it as it fixes a clear bug? the fix being better is so likely an improvement as a prior that you need a strong probability evidence otherwise for the posterior to lead into harmful?" Answered with the reading under normal priors (README § 10.3, step 13). Only a confident prior of a gain (+0.02 ± 0.01) makes the fix probably better on the backtest, and none is held. The recommendation rests on the data's correctness and train-live consistency, not on the backtest | the owner's question | no new result: arithmetic on the same reading | README § 10.3 |
| ~01:10 | **Owner, verbatim:** "I dont fully understand this all and I dont think you can make me fully understand it all. I understand the probabilitic justification on why its not enough to sway a decision. However, 91% chance of causing harm to the exact area the fix is being implemented is VERY alarming to me. So the justification for the change in the first place needs to be rock solid such that we can nearly ignore the test. Yes I see why its likely not a failure in implementation because it doesnt reach the thresholds. But, why did we even decide to fix this in the first place? Maybe a probability in this region of harm is an indication your initial logic or intention to fix or add anything was wrong. Its an indicator not strong evidence" | | | |
| | Answered: the justification split into the solid parts (the numbers were provably wrong; the fix was applied as intended; keeping the error means feeding it live for good) and the part never claimed (that predictions improve). No convincing mechanism was found by which the true numbers predict worse at the Slams. The service-game error usually moves one game per match, and the first-serve error hit every player at the event. Under no effect, one of five levels would look this bad about 4 times in 10 (1 − 0.91^5 = 0.38, treating the levels as independent). Recommended: adopt, with a tripwire, re-checking the Slam slice on new matches | | no new result | |
| ~01:20 | **Owner, verbatim:** "ah ok yes I think the why we fixed logic was rock solid. The next possiblity is that you fixed it incorrectly? how likely is that?" | | | |
| ~01:25–02:10 | `verify_applied.py`, written and run three times. V1 values; V2 orientation (points; service games against the score); V3 timing, with the light cone of the rescued boxes and the clock test for IOS; V4 direction; V5 Stage 0's rule counts | test the application directly rather than argue it | no new result: the fix's data and inputs only | `verify_applied/` |
| | **First run:** 12 service-game rows unexpected; the exchanged boxes' winners won more points in 1 of 4 after the exchange; the women's point inputs move from RG 2019; the men's IOS from the week before RG 2022 | | | |
| | **Explained:** 6 boxes rescued (Stage 0 had dropped them for failing "breaks conceded exceed service games"); 6 partial boxes Stage 0 still drops (§ 10.1); the four exchanged boxes are close three-setters, and the score test passes all four only after the exchange; the women's RG 2019 changes come from two rescued RG 2019 boxes; the men's from RG 2022's qualifying, the week before the main draw | | | |
| | **A further finding, explained:** 131 changed women's IOS rows lie outside the rescued boxes' light cone. IOS is solved jointly, so the right test is the clock: none starts before the boxes' results count (2 June 2019), and every row from that day on moved | | | |
| | **Failures while checking:** the timeline's days are day numbers since 1970, first read as dates, so the clock test said 1970; a path was off by one folder (exit 1). Both were fixed and the script rerun | | | |
| | **Result:** every check passes; Stage 0 has 42 fewer boxes failing its checks. Assessed: an application error that matters is about 1–2% likely (README § 10.3, step 14) | | | |
| | *Correction (same session):* the chat status message and the first draft of step 14 said the losers of all four exchanged-box matches won as many games or more. False for Peterson d. Rogers: the winner won 18 regular games to 14, but 115 points to 117. Step 14 is corrected; the conclusion is unchanged, since the score test decides it | | | |
| 10 Oct ~10:10 | **Owner, verbatim:** "Official decision: adopt, with the tripwire on the Slam number. Note: the final model is in the process of being rebuilt a bit in another LLM process (claude, in this IDE), so be careful not to do anything that conflicts with that process or hurts it" | | | |
| ~10:12–10:25 | Read-only look at the other work: no build or fit running; the busy session follows `IMPLEMENTATION_PROMPT.md` (the level layer into the template). Its template build uses `run_chain.py --setup` on the default sandbox path, and its replay builds Stage 0 from the decided tables | avoid any conflict | none | |
| ~10:25 | **Judgment call 8:** the table swap and the Stage 0 rebuild wait until the level-layer work reports done. My sandbox renamed (not deleted) to `C:/Users/zerom/tnr_sb_rg_candidate`, freeing the default path; checked first that nothing had touched it since 9 Oct 23:21; its junctions still resolve | the owner's caution | none | |
| ~10:30 | The tripwire declared in the decision record before any match it reads (rule, matches, comparison, timing, trigger, power), tracked as checklist item 12 with its prompt; the decisions index; README § 10.4 | the owner's condition | none | decision record, checklist |
| 16 Oct ~13:10 | **New session; a new person taking over from the owner, verbatim:** "im a laymen taking over for my partner, I dont understand this explanation. Where are we at with this? does it still need to be done?" | | | |
| ~13:10–13:30 | Read-only state check. The repair was applied on 13 Oct, 21:12, by the session working on the 2026 data gaps: `adopt.py --apply` kept the old tables (`f2870e5c…`, `563c6933…`); `rebuild_stage0.py` ran (2,272 overrides, 1,541 of them RG's); `history.py` was clean. The template of 14 Oct carries it. V1 and V2 of `verify_applied.py` rerun on today's Stage 0: every value in place, the same 12 explained rows, service games consistent 100%. My first listing of the kept folder looked empty only because `head` cut it off | the question | no new result | records updated, dated |
| ~13:20 | **The new person, verbatim:** "Yes, but find the single thread that is also evaluating a deletion. Check if its the same copy and message it if it is. Dont want some sort of error caused by two threads deleting the same thing. If its safe, delete it" | | | |
| ~13:20–13:35 | Found the thread among the sessions' transcripts: `b2538231…`, listed as `tennis-predictions-9e`, the session that applied the repair on 13 Oct. At 13:16–13:18 it had copied the candidate's Stage 0 and timeline into `…/2026-10-09_rg_box_scores/candidate_tables/` (96 MB), snapshotted `data/dump` and `data/raw`, and removed `tnr_sb_rg_candidate` with `run_chain.py --cleanup`. It then added the dated note to README § 10.4 (line 854). **I deleted nothing.** Checked: the folder is gone; the two Stage 0 copies' SHA-256 equal `candidate_trim.json`'s "after"; `data/dump` and `data/raw` are in place (its own before/after count was running). Sent it a message: I would not touch the copy, and would update the study's other records after re-reading each. Updated: the evidence README's row and the two checking scripts' usage notes | the request | no new result | |

## 6. Judgment calls and deviations

All made before any outcome result of this candidate.

1. **The indoor fill.**
   * **Options:**
     * (a) keep it, so the reading is the repair plus the fill;
     * (b) rebuild the frame with `--indoor-men-only`, so the reading is the repair alone;
     * (c) build a full control, today's template without the candidate tables.
   * **Chosen: (b).**
     * The reading is the repair's bug check, and (a) confounds it.
     * (c) costs about four hours of CPU and a second set of GPU fits, and `compare.py` takes no control but the reference.
   * **Seen by then:** the input check only.
   * **The other branch:** (a) would add the fill's own effect, which its paired check reads at the close as −0.002 [−0.016, +0.013] mLL. That is immaterial against a 0.1 tolerance, but would blur which change moved the reading.
2. **The "uneven" clause.** *The call a reviewer should examine first.*
   * **Options:**
     * (a) the RG decision's text: any flag stops the adoption;
     * (b) the adoption-by-kind decision's default harm, made later the same day, which says it takes "the form of the Roland Garros rule": a flag is harm only "in a way its dose does not explain".
   * **Chosen: (b).**
     * That decision reads candidate builds "by kind of change" (its "What it does not change").
     * The seven flags are the repair's own dose: the WTA's first 2013–2014 service-game counts, with nothing moving before RG 2013.
   * **Seen by then:** the input check only.
   * **The other branch:** (a) stops the adoption on flags that are the fix itself.
3. **The recipe.**
   * **Options:** the reference's (58 inputs, the books' average, the old indoor input), or today's template (57 inputs, Pinnacle first, the indoor fill).
   * **Chosen: the reference's.**
     * `compare.py`'s yardstick is the reference.
     * A comparison across the odds change resolves only about ±0.3 mLL (errata E1), too wide for a 0.1 tolerance.
   * **A deviation** from the checklist line "Build the candidate on the template as it stands at build time".
4. **R: the trim and the timeline.** The sandbox Stage 0 was trimmed to the live tables plus the named matches. The timeline was not rebuilt, since it would re-link match days from changed source folders, and the candidate changes no match or date.
5. **The fits' seasons:** 2019–2024 with seeds 0–3, as the reference's comparison uses; 2019 serves stage 2's coefficients only.

Made after the reading:

6. **Not searching the lean for a cause.**
   * **Options:**
     * (a) slice the reading (seasons, players of the corrected Slams, the WTA's 2013–2014 rows) to explain the −0.026;
     * (b) take it as the declared harm check and stop.
   * **Chosen: (b).**
     * Slices are one reading (adoption by kind, point 5).
     * The comparison is blind to a repair's plausible effect (±0.049 against 0.02).
     * A repair is not vetoed by its outcome (errata E4).
     * Slicing after seeing the sign invites the winner's luck.
   * **Seen by then:** the reading.
   * **The other branch:** a slice leaning harder could suggest a bug. It could not change the decision under the rule, whose alarm (−0.1 with the interval below 0) did not ring.
   * *Revisited 10 Oct, about 00:50, at the owner's question.* The slices were read as description (chronology). They put the lean at the Slams and the 500s, where the fix acts first. They are unresolved, and the Slams are the most negative of five levels.
     * Men and women lean alike, so the women's 2013–2014 flags are not indicated as the driver.
     * The recommendation is unchanged, for a reason the backtest cannot measure: train-live consistency at the Australian Open and Roland Garros (README § 10.3, step 13).
7. **When to apply the adoption.**
   * **Options:**
     * (a) swap the tables and rebuild Stage 0 now;
     * (b) swap now and rebuild later;
     * (c) both together, at a coordinated rebuild after the lower-level-evidence study's arm builds.
   * **Chosen: (c).**
     * (a) would fail that study's gate G2 in any sandbox set up afterwards, as the indoor fill did at 06:52 UTC.
     * (b) would split prediction runs, which build Stage 0 from the decided tables, from template builds, which copy the live Stage 0. A replay proof would then fail.
   * **Seen by then:** the reading. The timing does not bear on the verdict.
   * **The other branch:** (a) brings the repair into the template sooner. No Australian Open or Roland Garros is near, so the cost of waiting is small.
8. **After the official decision (10 Oct, ~10:25): when to apply it, and the sandbox.**
   * **Options:**
     * (a) apply now;
     * (b) wait for the level-layer work, running in another session, to report done;
     * for the sandbox: delete it, rename it, or leave it.
   * **Chosen: (b), and rename.**
     * The level-layer work edits the chain's builders and builds the template. Its replay builds Stage 0 from the decided tables, so a swap now could fail it for a reason not its own.
     * Its `run_chain.py --setup` uses the default sandbox path, which this build occupied. Renaming frees the path without deleting anything, which the project's rule asks to discuss first.
   * **Seen by then:** all results above. The timing does not bear on the verdict.
   * **The other branch:** (a) risks the conflict the owner warned against. Leaving the sandbox would block that work's setup, or invite its `--cleanup`.

## 7. Claims and their evidence

| Claim (README § 10.3–10.4) | Evidence | Status |
|---|---|---|
| The reading: −0.026 [−0.076, +0.023], unresolved, P(better) 0.145; men and women unresolved | `data/studies/current_best_model/2026-10-09_rg_box_scores/vs_reference_2026-10-08/scores.csv` | observed |
| The comparison resolves ±0.049; harm: no | `…/vs_reference_2026-10-08/adoption_read.json` | observed |
| The inputs the repair cannot reach are identical to the reference's (17 of 58) | `…/vs_reference_2026-10-08/inputs.csv` | observed |
| The seven flags sit in WTA 2013–2014 only | `…/vs_reference_2026-10-08/inputs_by_season.csv` | observed |
| The flags are the fix's own dose | `…/input_dose/coverage.csv`, `dose_rows.csv`, `timing.csv`, `summary.json` | observed counts; "explained" is an inference from the timing and coverage |
| The first collection's `indoor` flag is the decided fill (32,634 rows) | the first collection's frame, kept in `first_collect_indoor_filled/`; the count was read in the console, not saved | observed; reproducible |
| The ATP's 2013–2015 hold changes (~1e-6 SD) come from a constant pooled across tours | sizes from `inputs_by_season.csv`; the ATP's service games change only from RG 2016 (`dose_rows.csv`) | inference: the mechanism was not traced in code |
| Every fit used frame `8549316e…` | `reference.fit_meta` on `…/fits/*.npz` (console) | observed |
| The candidate holds every decided row unchanged | `adopt.py --check` (console) | observed; reproducible |

* **Numbers resting on a choice made after seeing results:** none of the reading's. Judgment calls 6 and 7 came after it; neither changes a number.
* **Subagent findings this phase rests on:** the three reviewers' confirmations (README §§ 8.4, 9, 10.1), taken as reported and as recorded there. No subagent ran in this phase.

## 8. Weak points

* **Threats to validity, most important first:**
  1. **The "uneven" clause** (judgment call 2). Read literally, the RG rule stops the adoption on the seven flags. The adoption rests on the later decision's refinement.
  2. **The lean.** The comparison cannot resolve an effect of about −0.03.
     * A real small harm would pass the 0.1 tolerance unseen.
     * The most plausible route: the WTA's 2013–2014 hold inputs now come from Roland Garros alone, a clay Slam, while later seasons draw on every event. TabPFN trains on those rows.
  3. **The candidate is not today's template.** It omits the Pinnacle-first odds, the dropped input and the indoor fill. Their interactions with the repair are untested here; checklist item 10, the holdback, reads the combination.
  4. **The pooled-constant explanation** of the ATP's tiny 2013–2015 changes is inferred, not traced.
  5. **Power:** blind (±0.049 against a plausible 0.02). This was known before the reading.
  6. **Repeated looks:** one look at this candidate's outcomes.
* **Where a flaw would most likely hide:**
  * in the RG 2013–2014 service-game fills, for instance a counting convention unlike the WTA's own counts of later seasons. The reviewers checked the values against the score and the break points, not against the WTA's convention;
  * in the `set_svgms` path of the Stage 0 build, which is tested and whose log shows 2,951 corrections.
* **What a re-design would do:**
  * read the candidate on today's template against a control without the repair, with seeds 0–15, to tighten the interval;
  * **the experiment most likely to overturn the conclusion:** the candidate without the WTA 2013–2014 fills. If the lean vanishes, the Roland Garros-only early hold data is the cause. It was not run: the fills are correct data, and the effect is below resolution.

## 9. Reviewer checklist

* [ ] Re-derive the primary: `./python.sh src/eda/current_best_model/compare.py --candidate data/studies/current_best_model/2026-10-09_rg_box_scores` gives the "both tours / both stages" row of `scores.csv`.
* [ ] Confirm that no 2025–2026 result was read: compare.py's default `--through` is 2024 (`THROUGH`), and `summary.json` records `results_read_through` and `scored_seasons` [2020, 2024].
* [ ] Confirm the fitted frame: every `fits/*.npz` records `model_frame_sha256` `8549316e…`.
* [ ] Check the verdict words against the intervals: "unresolved" (the interval spans 0); the rule's harm is not met.
* [ ] Judge call 2 against the texts: the [RG decision](../../decisions/2026-10-09-roland-garros-box-scores.md), point 2, and [adoption by kind](../../decisions/2026-10-09-adoption-by-change-class.md), points 4 and "What it does not change".
* [ ] Rerun `input_dose.py`. It needs the candidate's Stage 0: the sandbox's, or rebuilt as in § 10.
* [ ] `./python.sh -m pytest test/rg_first_serve_recount test/input_data_audit test/data_continuity` (94 pass).
* [ ] `./python.sh src/eda/rg_first_serve_recount/adopt.py --check` reports "ready".

## 10. Reproduction

```
# the tennis environment (./python.sh) unless marked; OUT=data/studies/current_best_model/2026-10-09_rg_box_scores
./python.sh src/eda/model_rebuild/run_chain.py --setup --candidate --out $OUT
# in the sandbox (C:/Users/zerom/tnr_sb), with the candidate's tables copied in (cp -f; check their SHA-256):
#   src/eda/predictability_diagnostic/stage0_build.py --box-overrides <candidate>/slam_box_overrides.csv \
#       --corrections-dir <candidate>/corrections --confirm-live-overrides      (README § 7; log: 2,272 overrides, 2,951 corrections)
./python.sh src/eda/rg_first_serve_recount/candidate_trim.py --sandbox C:/Users/zerom/tnr_sb --out $OUT
#   in the sandbox: src/eda/predictability_diagnostic/stage1_odds.py          (identical to the live table: 93,031 rows)
./python.sh src/eda/model_rebuild/run_chain.py --lane 0 --from timing_features --out $OUT      # 32 min; the timeline is not rebuilt
./python.sh src/eda/model_rebuild/run_chain.py --lane 1 --out $OUT          # 220 min on the shared machine
./python.sh src/eda/model_rebuild/run_chain.py --lane 2 --out $OUT          # 28 min, beside lane 1
./python.sh src/eda/model_rebuild/run_chain.py --lane 3 --out $OUT && ./python.sh src/eda/model_rebuild/run_chain.py --collect --out $OUT
# the men-only indoor rebuild: build_frame.py --indoor-men-only, the leak-proof frame and the Elo frames
#   (run_chain's runner, record chain_lane1i.json), then lane 3 and --collect again
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out $OUT --seeds 0-3 --seasons 2019-2024   # GPU, ~14 min on a free card
./python.sh src/eda/rg_first_serve_recount/input_dose.py --candidate-stage0 C:/Users/zerom/tnr_sb/data/studies/predictability_diagnostic --out $OUT
./python.sh src/eda/current_best_model/compare.py --candidate $OUT
./python.sh src/eda/current_best_model/adoption_read.py --scores $OUT/vs_reference_2026-10-08/scores.csv --kind repair
```

* **Kept as the record, superseded:** `first_collect_indoor_filled/`, the frame with the indoor fill (`af51f912…`). It was never fitted.
* **The sandbox moved on 10 Oct, ~10:25,** to `C:/Users/zerom/tnr_sb_rg_candidate` (judgment call 8). The commands above name its old path; with the new one, set `MODEL_REBUILD_SANDBOX` for `run_chain.py`, and pass the new path to `--candidate-stage0` and `--sandbox`.
* **The fits:** seeds 0–3, seasons 2019–2024; 8 estimators, softmax temperature 0.9, pretraining limits ignored.

*Log finished 10 Oct 2026, 00:30 (UTC−7), before the report.*
