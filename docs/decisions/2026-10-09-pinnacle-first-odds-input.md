# The current best model's odds input is "Pinnacle first", in training and live

**Decided by the owner on 9 October 2026,** after the [odds-sources study](../studies/odds_sources/README.md). Recorded the same day.

The owner's words:

> "Change training strategy to be 'Training: use Pinnacle first. That's tennis-data's Pinnacle through July 2025, cross-checked against OddsTrader's copy, then OddsTrader's to 7 September 2025, and BetOnline's closing line after that. Keep every season from 2013; there's no need to start "after some year".' With a note wherever we store information about this model that if we can get the missing pinnacle data we will then retrain it with all pinnacle."

> "The plan is to feed pinnacles current line with the margin removed live no matter where we bet yeah?" (Yes: § 2.)

**Confirmed by the owner as the production rule, 9 October 2026:**

> "ok , your suggested strategy of train on pinnacle only if it exists, and train on betonline if it doesnt (after 2025). At bet time use the current pinnacle line as the input to the model. is now the production rule."

Three points the owner's summary leaves implicit, as § 1 and § 2 specify:
1. BetOnline takes over from August 2025, not from 2026: that is when Pinnacle's own closes run out.
2. The books' average fills in only where neither book prices a match.
3. Live, Pinnacle's margin is removed proportionally, as in training. BetOnline's current line stands in while Pinnacle has no line.

The note in § 3 stands: if the missing Pinnacle closes are obtained, the model is retrained on Pinnacle throughout.

**This makes the odds input a production rule. It does not approve the rest of a production pipeline.** Before it can run:
* a recorder of Pinnacle's current line (the guest service of § 2);
* the prediction run's forecasting step (upcoming matchups and bet-time prices).

## Decision

1. **In training,** the model's odds input (`odds_logit`, one of its 58 inputs) is the margin-free log-odds (proportional) of:
   1. **Pinnacle's close.**
      * Up to 31 July 2025: tennis-data.co.uk's PSW/PSL (Stage 1), cross-checked against OddsTrader's timed recording of Pinnacle (book 20).
      * Where the two differ by more than 0.1 in log-odds and at least 3 other books price the match, the one nearer the other books' median is used.
      * OddsTrader's recording alone where tennis-data has no Pinnacle price. It runs to 7 September 2025.
   2. **BetOnline's closing line** (OddsTrader's last recorded line) where Pinnacle has none: from August 2025 on.
   3. **The books' average** (Stage 1's average, the earlier input) only where neither book prices a match: under 1% of rows, 6% of 2026's so far.

   Any OddsTrader line stamped more than 30 minutes after the listed start is left out: some are in-play prices. Every season from 2013 stays in training. The code is `src/eda/current_best_model/odds_input.py`.
2. **Live, at every venue (Pinnacle, BetOnline, Polymarket) and whenever the bet is made,** the model is fed **Pinnacle's current line with the margin removed** (proportionally). BetOnline's current line stands in only while Pinnacle has none yet.
   * Pinnacle's website serves its prices to logged-out visitors through a guest service: 106 upcoming matchups on the probe of 9 Oct ([research](../research/early-lines/README.md#update-9-october-2026-pinnacle-on-oddstrader-and-pinnacles-own-site)).
   * No recorder or prediction-run step reads it yet. Until one does, no live forecast has its decided input.
3. **The missing Pinnacle data: retrain with Pinnacle everywhere when it is found.** Pinnacle's own closes are missing from August 2025:
   * tennis-data's column stops being Pinnacle's close that month;
   * OddsTrader's recording stops on 7 September 2025.

   BetOnline stands in for those rows only because Pinnacle's are missing. **If the missing Pinnacle closes are obtained, the model is retrained on Pinnacle's closes throughout,** replacing the BetOnline stand-ins (and the average where Pinnacle then exists). The sources:
   * the project's own recording from now on;
   * a paid history such as BettingIsCool (Pinnacle from 2021, from €99 a month);
   * OddsPapi's free tier (from January 2026).
4. **Everything else in the configuration is unchanged:** the 58 inputs, the fit, the calibration, the serve-speed stage and the training history.

## Why

From the [odds-sources study](../studies/odds_sources/README.md) (mLL; + = the first named worse unless stated):
* **Pinnacle is the sharpest single input.** Its close beats the books' average by 0.67 mLL [0.34, 1.00] on 2019–2025.
* **Walk-forward weights for a "weighted average of the sharpest books" put about all the weight on Pinnacle.** BetOnline's weight is about 0 since 2023.
* **The books' average drifted.** It changed its book set in August 2025, and its gross recording errors rose in 2026.
* **tennis-data's and BetOnline's records are clean.** When Pinnacle is the outlier among the books, it is usually right.
* **The model retrained this way** (the bet-timing study's arm `pf`, seeds 0–3, 2020–2025, at BetOnline's last line; + = Pinnacle first more accurate):
  * level with the earlier model fed the books' average: −0.02 [−0.34, +0.31], unresolved (P(better) 0.46);
  * better than the earlier model fed BetOnline's own line: +0.41 [+0.05, +0.76];
  * right-sized: realisation 1.06.

## What it changes

* **The frozen reference stays as built,** on the books' average. It is the yardstick (`compare.py`), not the live model.
* **Building the template** gains one step after `run_chain.py --collect`: `./python.sh src/eda/current_best_model/odds_input.py --apply <out>` ([current-best-model decision](2026-10-08-current-best-model.md), "Building it").
  * It needs OddsTrader's tables to cover the frame's matches: the adapter's monthly pull, `odds_sources/table.py --link`, then `--books-eids`.
* **The instance of 9 Oct 2026:** `data/studies/current_best_model/pinnacle_first_2026-10-09/`. It is the reference's frame with this odds input, its fits, its comparison with the reference, and the backtest ([report](../studies/pinnacle_first/README.md)).
