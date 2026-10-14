# Predictions

One folder per match day, `predictions/<YYYY-MM-DD>/` (the day the matches are listed for; Shanghai's "12 Oct" matches start on the evening of 11 Oct in Pacific time). The master notebook's bet-day cells write it (`scripts/master_pipeline.ipynb`, section A; [how it works](../docs/studies/master_pipeline/README.md)).

## What to open

**`<day>/bet_sheet_<made>.xlsx`**, the newest one. A sheet is written by cell A5, and again after each reprice (A6); `<made>` is the local time it was made. An earlier sheet is never replaced: it stays as the record of what a bet rested on.

| Sheet | What it holds |
|---|---|
| Bet sheet | One row per predicted match, bets first:<br>• **BET:** the player, the stake, Pinnacle's odds and the lowest odds still worth taking<br>• **PASS:** no side is +EV at Pinnacle's price; the note gives the odds that would make it a bet<br>• **BLOCKED:** a safety rule fired (a data gap, a stale price, a started match), and which<br>Each row also gives the model's and the market's chance, the edge and the expected profit. The header gives the totals, the price's time, the model, the stake rule and the notes that apply to every match. |
| Matches | Every figure of both players, in Pinnacle's order: the price and its margin, the model before and after stage 2, the recent serve-speed gap, how much the model's 16 runs disagree, the price at which the edge would vanish, identifiers |
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

## Inputs

**The odds input of every forecast** is the owner's production rule of 9 Oct 2026 ([decision](../docs/decisions/2026-10-09-pinnacle-first-odds-input.md)). At every venue (Pinnacle, BetOnline, Polymarket) and bet time, it is Pinnacle's current line with the margin removed proportionally. BetOnline's current line stands in only while Pinnacle has none. The model it feeds is trained on Pinnacle's closes, with BetOnline's closing line where Pinnacle's are missing (from August 2025).

**The live inputs** are built as the [decision of 8 Oct 2026](../docs/decisions/2026-10-08-prediction-run-box-scores.md) requires: box scores refreshed first, the upcoming matches' inputs built by the training code in a sandbox, and a gate on missing box scores (a BLOCKED row's "Data gap"). The daily engine `src/eda/daily_prediction/` does it; its runs are in `data/studies/daily_prediction/runs/`.
