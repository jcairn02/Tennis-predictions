# A 10-8 or 13-11 decider is read as a match tiebreak where its event plays them; the Laver Cup 2026's two box scores restored

**Asked by the owner on 13 October 2026, decided the same day.** The bet sheet of 11 October blocked three Shanghai
matches for "no box score yet" of Ruud's, Fritz's and Alcaraz's Laver Cup matches. The owner asked (verbatim,
[master-pipeline process log](../studies/master_pipeline/process_log.md), Part 2):

> "Why would there be no box score? if we were running predictions, wouldnt it make sense to wire up obtaining the necessary data to getting the predictions? or at least the previous steps should be run to get them? such that theres a logical flow in the master script"

Claude found that Tennis My Life had published both box scores and that Stage 0 had rejected them, and recommended
(verbatim):

> 1. **Fix the score reading.** At an event where other deciding sets were certainly 10-point tiebreaks, read an ambiguous 10-8 or 13-11 as a tiebreak too. Within the main tour it changes only these two matches, and it fixes every future Laver Cup. It changes the shared data builder, so under your adoption rules it's a repair and your call. I recommend yes.
> 2. **Add a data check to the bet day, before the 10-minute prediction run.** It would list every recent match without a usable box score, with the cause and the remedy [...]

and the owner answered: **"yes do this"**. Carried out by Claude (the same process log).

## Decision

1. **The rule.** A main-tour event plays a match tiebreak instead of its deciding set when at least one of its
   completed deciders is certainly one (a 10-7 ends no set) and every decider's last "set" reaches 10. At such an
   event, a deciding score of 10-8, 11-9, 12-10, 13-11 or longer is read as a match tiebreak: a set won, no games.
   Without that evidence, a 10-8 stays an advantage set, as before.
2. **Main tour only:** the Slams' main draws, the Finals, the 1000s, 500s and 250s, and team events, never qualifying
   (`history.MAIN_TOUR`). Lower-level history keeps its frozen reading; there the same rule would go through the
   candidate route, if ever.
3. **On bet days at once; in training at the next rebuild.** Prediction runs build Stage 0 with the repository's
   builder, so they read the two box scores from their next run. Training takes them at the next template build. No
   retrain for this alone.
4. **No separate harm check** (a departure from the adoption framework's default for a repair, stated as its § 0
   asks). Two matches of 875,000, four players' inputs for about three weeks, are far below what any model comparison
   can resolve, and a candidate build costs about four hours. The next template build's harm check covers it with the
   other repairs ([13 Oct](2026-10-13-tml-lower-level-revisions.md), rule 4).

## Evidence

* **Classified before any result:** a repair (our own misreading of data the model already uses). No model was read for
  this decision.
* **The cause** (observed: `data/raw/public_dump/tennis_my_life/2026.csv`, rows 2391 and 2403):
  * Ruud v Cerundolo `6-7(4) 6-4 10-8` and Alcaraz v Fritz `6-3 4-6 13-11` have full box scores in Tennis My Life.
  * `repair_data.plain_match_tiebreak` never rewrites a 10-8 or 13-11 without rule evidence: both are legal
    advantage sets.
  * Stage 0's event-level rule (`mtb_event`) measured the share of bracketed deciders in the raw score. Tennis My
    Life writes no brackets, so it saw 0 of 4 at the Laver Cup 2026; the two 10-7s are bracketed only later, when
    counted.
  * Read as sets, the scores hold 41 and 43 games. The box scores' 159 and 143 serve points fell under check B9's 4.5
    per game, and both were dropped (`box_status = failed_check`).
  * The Cup's 10-7 matches passed. Laver Cup box scores were complete in 2024 and 2025 (9 of 9 each).
* **The footprint, every row compared** (Stage 0 built before and after with `stage0_build.py --out-dir` on the same
  inputs; scratchpad `s0_compare3.py`, process log Part 2):
  * `stage0_matches`: 2 rows change, the two matches above. Their format becomes `match_tiebreak`, and their box
    scores are restored (`failed_check` → `full`).
  * `stage0_match_players`: their 4 player rows. Box counts restored; games 19 and 23 instead of 43 and 41.
  * The cleaning log, the coverage cells and the summary move by exactly those counts (C35 and C39 −2 each, C41 +2,
    a new C42 of 2). `stage0_level_applied.csv` is byte-identical. Every other row of 873,642 matches is unchanged.
* **The same pattern elsewhere:** 3,670 ambiguous deciders sit at events with certain match tiebreaks. 3,668 are ITF
  (lower level, frozen; ITF box scores are not inputs). The 146 at the Slams are at events without match tiebreaks:
  advantage sets, correctly kept as sets.
* **The three blocked matches of 11 October:** on the repaired Stage 0, the bet-day data check reads all eight Shanghai
  matches as ready.

## Implemented

* `src/eda/feature_alpha_audit/repair_data.py`: `plain_match_tiebreak(..., event_rule=False)`.
* `src/eda/predictability_diagnostic/stage0_build.py`: `MAIN_LEVELS`, `match_tiebreak_events`, the `mtb_rule` column
  read by `score_columns`, and the cleaning-log note C42.
* Tests: `test/predictability_diagnostic/test_stage0_build.py`, two new; the builder's and the repairs' 98 tests pass.
* With it, for the owner's second point: the bet-day **data check** (`tp.data_check`, notebook cell A3b,
  `src/pipeline/readiness.py`) applies the run's gate before the run. It names each gap's cause (Tennis My Life has
  none yet; our check rejected Tennis My Life's; a qualifier without a qualifying match) and its fix. The bet sheet
  names the cause too.

## To undo

Call `plain_match_tiebreak` without `event_rule` in `stage0_build.score_columns` (or drop the `mtb_rule` column). The
next build reads the two scores as sets again, and drops their box scores.
