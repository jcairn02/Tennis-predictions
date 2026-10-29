# Predictions

One folder per match day, `predictions/<YYYY-MM-DD>/` (the day the matches are listed for; Shanghai's "12 Oct" matches start on the evening of 11 Oct in Pacific time). The master notebook's bet-day cells write it (`scripts/master_pipeline.ipynb`, section A; [how it works](../docs/studies/master_pipeline/README.md)).

## What to open

**`<day>/bet_sheet_<made>.xlsx`**, the newest one. A sheet is written by cell A5, and again after each reprice (A5b; A6 until 27 Oct 2026); `<made>` is the local time it was made. An earlier sheet is never replaced: it stays as the record of what a bet rested on.

| Sheet | What it holds |
|---|---|
| Bet sheet | One row per predicted match, bets first:<br>• **BET:** the player, the stake, Pinnacle's odds and the lowest odds still worth taking<br>• **PASS:** no side is +EV at Pinnacle's price; the note gives the odds that would make it a bet<br>• **BLOCKED:** a safety rule fired (a data gap, a stale price, a started match), and which<br>Each row also gives the model's chance, the market's chance (since 24 Oct 2026: what Pinnacle's posted price implies, its margin included), the edge (model minus market: positive means positive expected profit) and the expected profit. The header gives the totals, the price's time, the model, the stake rule and the notes that apply to every match. |
| Matches | Every figure of both players, in Pinnacle's order: the price and its margin, the model before and after stage 2, the recent serve-speed gap, how much the model's 16 runs disagree, the Pinnacle price at which the expected profit would be zero, identifiers |
| Not predicted | The listed main-tour matches with no prediction, and why (a first round waits for the event's first played match) |
| Run | Where the sheet came from: the run, the model instance, the prices, the rules, the run's notes |
| How to read | Every column in plain words |

The notebook shows the same table under A5.

**How a row is decided.** These are the daily pipeline's rules; the sheet only reports them.
* **BET:** positive expected profit at Pinnacle's own odds, margin included, and no safety rule fired.
* **The stake:** the owner's research rule of 8 Oct 2026, in units. Favourites are staked to win 1 unit, even money stakes 1 unit, and underdogs a little under 1 unit. It sizes by the price, not by the edge. It is not a decided staking rule; `STAKE_RULE = None` in the notebook's setup cell hides it.
* **Expected profit:** the model's own estimate, not a measured return.

## records/

The machine record behind each sheet:
* `bet_sheet_<made>.csv`: every figure, on the daily pipeline's sides A and B, with ids and flags.
* its `.provenance.json`: the inputs' hashes, the stage-2 coefficients, the parameters, the run's notes.
* the daily engine's own archive of each live run: `live_<run>.csv` and its provenance.

Files written before 13 Oct 2026 (`live_<run>_diagnostics_<time>.csv`, at the top of `2026-10-12/`) are the same record in the old layout.

## clv/ (since 25 Oct 2026)

**The closing-line ledger:** every bet sheet's predictions against Pinnacle's closing price, the line's move since the sheet, and each pick's closing-line value. The notebook's A8 (`tp.clv_ledger()`) rebuilds it in full from the records above each time it runs, so nothing in it is kept by hand. The design is an agent's choice ([how it works](../docs/studies/master_pipeline/README.md#the-closing-line-a8); [process log, Part 18](../docs/studies/master_pipeline/process_log.md)).
* `ledger.csv`: one row per sheet and predicted match. `last_before_start` marks the sheet a bet most likely came from, `first_sheet` the first one.
* `ledger.provenance.json`: the sources read and their times, the two checks, the rules.
* `summary.json`: what A8 shows.

**The close** is Pinnacle's own listing, when one of our pulls read it within 15 minutes of its pre-match market shutting; else TennisExplorer's record of Pinnacle (the close the model's training data uses), when it is known to hold within 2 hours of the start. A match with only an earlier price is listed but left out of the figures. TennisExplorer has no qualifying pages, so a qualifying match's close exists only if Pinnacle's listing was read near its start.

These check the prices taken, not the model: the market does not move toward this model before the close ([production-integrity plan](../docs/decisions/2026-10-22-production-integrity-plan.md), principle 8). They are the sheets' picks at the sheet's price, not the bets placed.

## Inputs

**The odds input of every forecast** is the owner's production rule of 9 Oct 2026 ([decision](../docs/decisions/2026-10-09-pinnacle-first-odds-input.md)). At every venue (Pinnacle, BetOnline, Polymarket) and bet time, it is Pinnacle's current line with the margin removed proportionally. BetOnline's current line stands in only while Pinnacle has none. The model it feeds is trained on Pinnacle's closes, with BetOnline's closing line where Pinnacle's are missing (from August 2025).

**The live inputs** are built as the [decision of 8 Oct 2026](../docs/decisions/2026-10-08-prediction-run-box-scores.md) requires: box scores refreshed first, the upcoming matches' inputs built by the training code in a sandbox, and a gate on missing box scores (a BLOCKED row's "Data gap"). The daily engine `src/eda/daily_prediction/` does it; its runs are in `data/studies/daily_prediction/runs/`.
