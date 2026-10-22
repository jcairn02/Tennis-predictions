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

## Amendment of 21 October 2026: OddsTrader's tables kept current, and mirrored prices left out

**What was found.** The retrain of 21 Oct priced its newest matches at the books' average: from late September the
average stood in for BetOnline's closes that were on disk (September 164 of 323 matches, October 149 of 149, against
3-9% before). The scripted builds since 13 Oct ran a copy of the finishing steps without the link and the every-book
pull, which stayed as built on 9 Oct. While fixing it, 4 OddsTrader prices turned out to be mirror images of
tennis-data's books (the OddsTrader event linked with its sides exchanged: e.g. Bergs v Alcaraz, Shanghai 2026, every
OddsTrader book at 89% for Bergs, tennis-data's average, Bet365 and Betfair at 8-10%). Details: the in-season retrain
study's [process log](../studies/in_season_retrain/process_log.md), § 4c.

**1. A repair of how the rule is built (no change to the rule).** `odds_input.py --apply` brings OddsTrader's tables up to
date for the frame itself (a month listed again where its listing predates a match's final line, the link, the
every-book pull for the events it lacks) and refuses a frame they do not cover. The every-book pull asks only for events
it does not hold. Every build path runs the one list of finishing steps (`finish_instance`). The "What it changes"
bullet above ("It needs OddsTrader's tables to cover the frame's matches") is now done by the step.

**2. A rule added: an OddsTrader price that mirrors tennis-data's books is left out.** BetOnline's close, or OddsTrader's
recording of Pinnacle, that is the odds study's "swapped" against tennis-data's average (over 1.0 in log-odds and 10
points of chance from it, and within 0.35 of its mirror) is not this match's price. The match takes the next source:
tennis-data's Pinnacle where that is Pinnacle's (to July 2025), else the average. A gross gap that is not a mirror is
kept and listed in `odds_input.json` for a look, since either record may be the wrong one (5 matches on the instance
of 21 Oct, among them Osaka v Kalinina, where tennis-data's average of 3.5% looks the wrong one).

The question put to the owner: "Correct the live model now? A corrected copy of today's retrain with the repaired odds
(288 recent matches to BetOnline, 3 mirrored prices replaced, the new mirror rule), the same checks as this morning, and
a switch only if they pass. About an hour; no bet day meanwhile." **The owner's answer: "Yes, start now (Recommended)".**
The corrected instance: `data/studies/current_best_model/template_2026-10-21b/` (291 rows differ from the 21 Oct
instance: 2026, 288 average → BetOnline and 1 BetOnline → average; 2023 and 2025, 1 each, a mirrored OddsTrader Pinnacle
→ tennis-data's).

## Amendment of 21 October 2026, evening: the closing line from 2025 on, applied at the next retrain

**What was found** ([research note](../research/pinnacle-gap/README.md), 21 Oct 2026):
* **TennisExplorer's match pages show Pinnacle's match-winner price**, free and without a login. Each price comes with every change and its time, and with the opening and its time, for the tour-level matches of every month from January 2025.
  * Against the project's own recordings of Pinnacle's website (18–20 Oct 2026), its price matched to the cent on 210 of 227 readings.
* **August – October 2025 are different.** The site's Pinnacle prices there show no times, and they are the same numbers as tennis-data's PSW/PSL. From November 2025 the prices are timed again.
* **tennis-data's column stopped being Pinnacle's own close on 24 July 2025**, the day after Pinnacle's public API closed. It matched OddsTrader's timed Pinnacle 62–73% in each of the first three weeks of July, then 9%.
* **The four matches the mirror rule of 21 Oct changed were tennis-data rows with the two players' prices swapped**, not OddsTrader links with swapped sides. On each, every book on TennisExplorer agrees with OddsTrader:
  * Konjuh v Sherif (Lyon 2023);
  * Gauff v Sabalenka (French Open final 2025);
  * Zverev v Fery (Wimbledon semifinal 2026);
  * Bergs v Alcaraz (Shanghai 2026).

**The owner's words** (21 Oct 2026, verbatim):

> "Fill the gap from November 2025 with the site's time-stamped Pinnacle prices in place of BetOnline's close. Do a test build compared with the current model,
>
> Reverse the 21 October rule so that when OddsTrader and tennis-data are mirror images, OddsTrader wins. That fixes the four matches.
>
> Find a shared file thats clear to future agents when we rebuild that we plan to update the strategy for how we deal with the closing line 2025+ on the next retrain
>
> Include in our automatic download script downloading pinnacles closing value weekly (or daily if theres a daily script thats being executed)"

And minutes later:

> "\"Do a test build compared with the current model\" I said this but I take it back . DO NOT DO THE TEST YET"

**The training rule from the next retrain** (§ 1 as amended; rule `2026-10-21` in `odds_input.py`):
1. **Pinnacle's close:**
   * tennis-data's PSW/PSL to 31 July 2025, reconciled with OddsTrader's recording, and OddsTrader's to 7 September 2025, as before;
   * **from 1 November 2025, TennisExplorer's time-stamped Pinnacle price** (its last before the match) where those have none. A price the site shows without any time is not used.
2. **BetOnline's closing line** where Pinnacle has none.
3. **The books' average** where neither prices the match.

**Mirror images (the rule of 21 Oct turned round):** where OddsTrader's Pinnacle (chosen by the reconciliation) or BetOnline's close is the mirror image of tennis-data's books, OddsTrader's price stands: tennis-data's row is the swapped one.
* Only those two cases. Where the reconciliation took tennis-data's own Pinnacle, it stays.
* Why: at the 2021 US Open OddsTrader's recording of Pinnacle failed, and 18 of its lines there look like mirrors. A version of the reversal that also acted on them would have replaced tennis-data's correct closes.
* On the live instance's own per-source table (in memory, no fit) the reversal changes exactly the four matches above, each to the side every book on TennisExplorer supports.

**A guard:** a month from November 2025 with 50 or more matches, of which TennisExplorer prices under 75%, stops the step before anything is rewritten. A broken feed must not fall back to BetOnline unseen, as the average did in the builds of 13–21 Oct (`--allow-low-te-coverage` overrides it knowingly).

**The site's own errors** (added early on 22 Oct 2026, after reading every flagged match of the gap by hand; no result read). BetOnline's close stays where TennisExplorer's Pinnacle price is:
* far from the median of the site's other books (at least 3 agreeing, the odds study's thresholds: over 1.0 in log-odds and 10 points). Three in 2026: Kopriva v Engel (Munich), Carreno Busta v Halys (Doha), Guo v Kessler (Roland Garros);
* far from both BetOnline's close and the books' average while those two agree with each other: the site's whole page the wrong way round. One in 2026: Atmane v Tiafoe (Washington).

**What it changes, counted in memory** on the live instance's frame (no fit, no result; `src/eda/pinnacle_gap/dry_run.py`, `data/studies/pinnacle_gap/dry_run.json`):
* 4,545 matches change source: 4,311 from BetOnline's close and 232 from the average to TennisExplorer's Pinnacle, and the 2 mirror fixes before August 2025.
* TennisExplorer prices 87–98% of each month's matches from November 2025, so the guard passes.
* The four mirrored matches are among them:
  * Bergs v Alcaraz and Zverev v Fery move from the average to the site's Pinnacle, which agrees with OddsTrader;
  * Konjuh v Sherif and Gauff v Sabalenka are the two mirror fixes.

**How it is applied:**
* **Rule `2026-10-21` is the step's default,** so the next retrain or template build applies it by itself (`finish_instance` → `odds_input.py --apply`). The step brings TennisExplorer's pages up to date itself, from 20 Oct 2025.
* **The instances built before keep their rule,** the live one included. `--rule 2026-10-09` reproduces them; it was checked to give the live instance's odds input exactly, on all 67,531 matches.
* **Recorded in the project's working guide** (CLAUDE.md, "The current best model"), so the agent that next rebuilds reads it.
* **The daily download task fetches TennisExplorer's pages** (`src/ingest/scheduled.py`, job `pinnacle_closes`): the finished tour-level matches of the last 21 days.

**Deferred by the owner: the test build comparing the new rule with the current model.** Don't run it until the owner asks ("DO NOT DO THE TEST YET").

**Recommended, not decided:** end tennis-data's Pinnacle prices on 23 July 2025 instead of 31 July (the break above). Until the owner decides, the cut-over stays 31 July, with the reconciliation catching the gross gaps.

**§ 3 now:** the missing Pinnacle closes are found from November 2025 (TennisExplorer). For 24 July – 31 October 2025 no free Pinnacle close is known. OddsTrader's timed Pinnacle covers the matches to 7 September.
