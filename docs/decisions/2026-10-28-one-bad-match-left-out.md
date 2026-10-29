# One bad match is left out, loudly; every other match is predicted (the notebook's A1–A8)

**The owner's decision, 28 October 2026.** Verbatim, first mid-turn during that afternoon's failed A4 (process log,
Part 23):

> while you fix a single row it shouldnt hold up the whole pipeline. Time matters here

then, asking for this change that evening (Part 25):

> Implement this. Be sure to mention the match that was left out and that there was an error in one row clearly and
> loudly, however still give all the other predictions

**The design below is Claude's** (an agent's choice, in the production-integrity plan's sense). It moves no pick of a
match that is predicted: the others are predicted exactly as if the matchups CSV had not listed the bad one. How it was
done and checked: [master pipeline process log](../studies/master_pipeline/process_log.md), Part 25.

## What happens now

A match whose own row cannot be handled is **left out, with its reason**. The step goes on with the others, and the
match is named loudly where it happens, at the end of A4, and at the top of the bet sheet.

| Step | One bad row | Said where |
|---|---|---|
| A2 | An error while linking one listing leaves that listing out ("ERROR while linking this listing", with the error). The others are linked | one `!!!` line; the listing's reason; the sheet's "Not predicted" |
| A3 | `check_matchups` no longer raises for a row. A row that would fail (its price, its start time, its day, its event, a name) is flagged with the problem | `!!!` lines naming each one |
| A3b | An error while checking one match gives it the verdict "check failed". The others are checked | `!!!` lines; the row is shown first, in red |
| A4, before the run | The rows A3's check flags are left out: the run predicts a checked copy of the CSV, kept in the run's folder. The CSV as given is kept too | the end of A4 |
| A4, the run's matchups step | A row the run cannot place (its event, a player, its live row, its day) is left out with its live row | the run's log (`!!!`); the end of A4 |
| A4, the prices step | A price not strictly between 0 and 1 leaves its match out | the same |
| A4, the tables step | A match the run's check cannot place in its own data is left out, and the data are built again without it, only when this happens. The check runs right after Stage 0 and again after the additions step. If the first check finds the match, the rebuild costs one Stage 0 build (about 2 minutes); if only the second does, the additions' merge too (5–11 minutes). The check names the cause: Stage 0 built the row under another id (which), or kept no row of it, or built it otherwise, or the odds builder would not price it, or its sides disagree | the same |
| A4, earlier rounds | An earlier qualifying round from TennisLive that the run cannot add is listed. Its player's match is still predicted, without it, and the gate decides on it as before | the end of A4; a red alert and a warning on that match |
| A5 | Each match left out is a NOT PREDICTED row whose reason starts "ERROR in its row", whatever `left_out=` says. The sheet's first lines, in red, name each one with its error and say the others were predicted | the sheet (notebook and workbook) |
| A5b | An error repricing one match leaves it at its earlier price (the sheet blocks it once that is stale). The others are repriced | `!!!` lines |
| A7 | An error grading one run gives that run the state "ERROR". The other runs are graded | `!!!` lines |
| A8 | A bet sheet's record that cannot be read is left out of the ledger; one row whose figures fail keeps empty figures. The rest is read | `!!!` lines |

The run's record of what it left out is `left_out.json` in its folder (`src/eda/daily_prediction/dp_leftout.py`; the
notebook layer reads it with `src/pipeline/left_out.py`).

## What still stops

* **A run whose every match is left out.** It names them all.
* **A failure that names no match:** a tour-wide condition, a missing file, an error inside the states or the fit.
* **Replays (C8 and the replay proof) and the 8 Oct path (`run.py`):** they keep every refusal. A proof that leaves
  matches out would prove less.

## Why this design

* **"As if not listed" is a promise the owner can check.** At the matchups and prices steps nothing has read the bad
  match's live row yet, so its row and its meta row are simply dropped. At the tables step Stage 0 already holds it. Its
  row is taken out, the timeline is put back as it was (the additions step appends to it), and Stage 0 is built again.
  Leaving the row in the data and only not predicting it would cost nothing. But the row carries a placeholder result,
  and its timeline window would not be pinned to its day. Whether that result could reach another match of the day
  could not be ruled out in every case (a delayed event).
* **The check foresees the two later refusals it can.** A main-draw match at a level the odds builder does not price
  (its own `LINK_LEVELS`), and sides that disagree. So those are left out at the check, where Stage 0 can be rebuilt,
  instead of stopping the run later.
* **The earlier rounds stay.** A left-out match's players' earlier rounds are real results, history for every match.
* **Loud means three places:** the step's own output, the last lines of A4 (where the eye lands after a ten-minute
  run), and the top of the bet sheet in red. A match that vanished from the sheet without a word would be worse than
  the stop it replaces.

## Evidence

On 28 Oct's files (process log, Part 25):

* **Two real runs of the engine**, each in a work tree of its own (removed after), with no download, no GPU and no
  checkpoint left. The input was the 15:30 run's 9 men's matches with three bad rows added: a player no source knows,
  a price outside 0–1 (Cobolli v Berrettini's), and a Florence Challenger quarter-final the odds builder does not price.
  * Each step left out its own bad match and said so: the matchups step, then the prices step, then the run's check.
  * The first run (the check after the additions only) rebuilt through the additions step: 970 s for the tables step.
    The second (the check right after Stage 0 too) rebuilt Stage 0 alone (96 s): 572 s. Every table of the two runs
    is equal: Stage 0's matches and players, the odds, the timeline, the live rows, the meta and the prices.
  * **The 8 matches predicted have all 57 inputs equal, bit for bit, to the 15:30 run's.**
* **Tests:** 29 new (`test/prediction_run/test_left_out.py`, `test/daily_prediction/test_dp_left_out.py`,
  `test/master_pipeline/test_one_bad_match.py`) and one of 28 Oct's women's-switch tests changed with the behaviour.
  The notebook's own test of its saved state is deselected, as before (your notebook is saved with output).

## Left to the owner

* **Stop predicting the live match's id** (process log, P23.9). The run would read each live row's id from its own
  Stage 0, by position, instead of predicting it. Today's two Guangzhou matches would then have been predicted, not
  left out. It changes how every live match is keyed, so it needs the replay proof. **My recommendation: do it next.**
  It turns the most common cause of a left-out match into a predicted one.
* **An earlier round the run cannot add.** The match it serves is predicted without that result. The gate blocks a
  qualifying round 2 or 3 whose round before is missing. A main-draw match of a qualifier who still has some
  qualifying match in the data gets neither a block nor a bar (tennis-predictions-24's point, 28 Oct 2026). **My
  recommendation:** give such a match the gate's "do not bet: inputs incomplete", as for a missing round. That changes
  picks, so it would be shown to you with and without it before it goes live.
