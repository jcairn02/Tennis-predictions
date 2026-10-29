# A match's listed start time never withholds a prediction or a bet

**Decided by the owner on 24 October 2026**, after Claude explained the bet sheet's "the match has started" block and
the evidence below. The owner's words, verbatim:

> Why would this code block fights that already have started according to the model? Clearly I cant bet on the fight if
> its in the past, so why not output a prediction? what harm is there in that? If the models timing is wrong and I CAN
> bet on it still, it just wasted my opportunity

> Yo, it just doesnt matter if its started in the eyes of the model. If it started I cant bet it. If it uses a "live
> line" then I wont be able to bet it. Their live bet section is different than pre-bet. So there's literally zero
> risk. just give me the prediction

## Decision

* **The bet sheet** (`src/pipeline/diagnostics.py`, cell A5) no longer blocks a match whose listed start has passed.
  It is decided like any other match: BET or PASS, with its stake. `minutes_to_start` stays in the record. Every other
  block is unchanged: a stale price, the data check, the read-backs, the live-model check.
* **Matches still listed pre-match after their listed start** (`src/pipeline/live.py`: cell A2's `todays_matches`, and
  cell A6's `live_prices`). Pinnacle can still list a match with a pre-match price after its listed start or its
  market's cutoff; the staging's reasons for this are "start not after the pull" and "market cutoff not after the pull".
  Such a match is now linked, predicted and repriced like any other. Before, A2 dropped it without a word, and A6
  skipped it. **This part is Claude's reading of the owner's rule**: the same rule, one step before the sheet. An
  in-play market stays out. A live price is never the model's input, which the owner's "live line" point also covers.

The rule it replaces was an agent's choice made while the pipeline was designed ([master pipeline process
log](../studies/master_pipeline/process_log.md), Part 2, choice 6), not the owner's. It was never tested against how
tennis start times behave.

## Evidence the owner had seen

* **The listed start is a moving estimate, wrong in both directions** [observed]. The source is Pinnacle's own listing,
  read every 10 minutes from 04:50 UTC on 22 Oct to 16:50 UTC on 23 Oct (P11's capture,
  `data/dump/odds/pinnacle_capture/`). It covers 32 tour-level singles matches seen pre-match before their first listed
  start, then in play.
  * 26 of the 32 could still be bet pre-match after the start first listed: Pinnacle had pushed the start back. They
    stayed open a median 80 minutes past that start (11 for over 2 hours; the longest, Altmaier v Fritz in Lyon, for
    7 hours 10 minutes).
  * 15 of the 32 went in play more than 10 minutes before the start listed at their last pre-match reading (median
    43 minutes early).
  * Pinnacle's pre-match cutoff equals the listed start on 99.4% of the readings. Across every level, doubles
    included, 83 of the 246 matchups whose cutoff passed reopened with a later time.
* **The bet sheet of 24 Oct, 08:08 PDT, rebuilt as of its own time with the new rule**: 3 of 13 rows change.
  * Duckworth v Kovacevic (Basel Q1): BLOCKED to BET on Duckworth at +132 (lowest odds +126, expected profit +2.9%,
    0.88 units). Its listed start was 13 seconds after the price was read, so it had very likely started.
  * Bertola v Paul and Moutet v Machac: BLOCKED to PASS.
  * The other 10 rows are unchanged.

## Checks

* `test/master_pipeline/test_master_pipeline.py`:
  * a listed start an hour past decides exactly as a start in the future;
  * the staging writes the two reasons the linker reads;
  * the linker keeps a still-listed match and leaves an in-play one out;
  * the reprice prices a still-listed match and leaves an in-play one out.
* **Reproduced on the old code** (a scratch copy with the block restored), on the test's 23 matches with their listed
  start an hour past:
  * old code: 23 of 23 blocked as started;
  * new code: 8 BET, 12 PASS and 3 BLOCKED (the replay's own data check).
* No replay proof: no input of the model changes.

## Left as it is

* **A match that really is in play keeps the run's pre-match price** on the sheet until the stale-price limit blocks
  it (60 minutes in the notebook). The owner's point: Pinnacle takes such a bet only in its separate live section.
* **Polymarket trades during play.** A Polymarket price typed in for a started match is a live price, and the sheet
  cannot tell.
