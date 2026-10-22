# The five-pattern adjustment is switched on in the daily predictions

**Switched on by the owner on 13 October 2026**, after the unpriced-leads study's single check passed and the live values were proved equal to the historical ones. The owner's words:

> "switch it on and be clear in prediction csv's the predictions with it on and the predictions when its off"

Carried out by Claude on 13–14 Oct 2026. The study: [report](../studies/unpriced_leads/README.md), [rules of the check](../studies/unpriced_leads/check_now_rules.md), [process log](../studies/unpriced_leads/process_log.md).

## What it is

Five patterns found in 2013–24 matches that the closing odds missed, combined into one score with the registered members, signs and equal weights:
* luck read as skill;
* the post-Slam letdown;
* fast courts amplifying big servers;
* status over-priced and low-visibility form under-priced;
* rhythm the singles record misses.

The daily engine adds the score to stage 2's log-odds:

    logit q = s_tour·η + b̃·spd_L + b·z

* **b = 0.0616 per unit of z.** This is the rules' size: the 45% prior updated with the check's reading.
* **z is capped at ±3.5.** The largest move is 0.216 log-odds, about 5 points at even odds.
* **z uses the check's frozen parameters**, and the live gate is the registered gate's trailing form.

## Evidence

* **The single check.** Its rules were frozen before any result from 2025 on was read for these patterns. It covered 9,457 matches from 2025 to 23 Sep 2026:
  * β/se +3.80 beyond the full current model (pass mark +1.0);
  * +3.85 beyond the close, with realisation 0.78;
  * Pinnacle months +2.6, BetOnline months +2.5.
* **Live equals historical.** On a replay of 13 Jul 2026 (23 matches, training dating):
  * the seven members computed live equal the historical values;
  * the score equals the historical score to 1e-13;
  * the predict step applies b·z exactly, and with the switch off its output is unchanged.

## What the prediction files show

**`predictions.csv`.** `q_a` is the prediction used, with the patterns while the switch is on. Beside it:
* `q_a_patterns_off` and `q_a_patterns_on`;
* `patterns` ("on" or "off");
* `pattern_applied` (False where a match has no score);
* `pattern_shift` (b·z in log-odds) and `pattern_z`.

**The other files:**
* `curves.parquet` carries `q_a_patterns_off` beside `q_a`.
* Reprice files give both versions.
* `graded.csv` adds `ll_model_patterns_off`.

**The bet sheet:**
* "Model chance without patterns" stands beside "Model chance", and the header says whether the adjustment is on.
* Notes flag a bet that exists only because of the patterns ("Keep the stake small") and a bet whose side the patterns switch.
* The record CSV adds the decision without the patterns: `pick_patterns_off`, `ev_*_patterns_off` and `patterns_effect`.

## Switching it off

Set `"status": "off"` in `data/studies/unpriced_leads/check_now/adjustment.json`. The engine then runs no pattern step. The files show `patterns` "off" and the version without the patterns.

## Known limits

* **Short rest under 20 hours** needs a scheduled start time for each upcoming match. Until a start-time feed exists it counts 0 for most live matches; in the live-dating replay it was known for 4 of 23.
* **Court speed** reads the instance's surface-IOS extract, which ends with the 8 Oct tables. Until the next template rebuild refreshes it, an event's newest days do not count.
* **Five members are not computed live.** These are luck's three and the lower-level pair in reputation.
  * Luck stays switched off: the box-score supply is below 70% of a year earlier, even with the lower-level feed.
  * Since the lower-level feed (14 Oct 2026), the lower-level pair is switched on. It counts 0 under the rules' "a pattern whose data is missing for a match adds nothing".
  * Building these members live, with a new parity proof, is the follow-up.
* **The monthly re-check** of the size (rules § 8) needs the check's instance paths made arguments.
* **Stakes** are not changed automatically.
* **`compare.py` does not include the adjustment.** A study that compares "both stages" compares without it unless it adds the term.

## Amendment, 16 Oct 2026: the fast-courts pattern reads today's ratings

**Found on 16 Oct.** In every live run since the switch-on, the fast-courts pattern was missing for every match.
* It needs each player's ace rating. The live code looked the ratings up by match in a file pinned to the 10 Oct model build, and a match not yet played is never in such a file.
* The same file also left the venue's newest days out of the court-speed estimate. That is the "court speed" limit above, which understated the problem.
* The 13 Oct proof could not see it: it replayed July matches, which the file holds.

**Fixed on 16 Oct at the owner's instruction,** who called the pinned file an example of agents "freezing irrationally rigid". The rules freeze the parameters (members, signs, projections, scales, b, the gate rule), not the data.
* **The states step** also saves the ace ratings it solves on today's tables: the live matches and every match since the run's checkpoint (`ios_ace_recent.parquet`). This takes no extra solving, and the 57 inputs are unchanged.
* **The pattern step** lays those ratings over the current model build's own table. The live match's ace gap is then the model's own input, and the court speed counts the event's earlier days.
* **Every run checks** that gap against the model's input, and counts the venue history still without a rating (`live_patterns.json`, `venue_pace`).

**Verified on 16 Oct** on a re-run of the 14 Oct bet day (two Shanghai quarter-finals, unplayed in the tables; no fit):
* The pattern was present on both matches, with an ace gap equal to the model's input.
* The 57 inputs were bit for bit the same with and without the new ratings.
* On the 63 men's matches played inside the run's window where both versions had a value, the pattern from the run's ratings matched the one from the model build's table within 7.5e-6. It also covered all 71 men's matches, against 59 on the old path.
* At the 14 Oct prices, the fixed pattern would not have listed the Jodar bet.

The "court speed" limit above no longer applies. Evidence: the study's [process log](../studies/unpriced_leads/process_log.md), 16 Oct.

## Amendment, 16 Oct 2026: renamed events are one venue

**The owner's call** ("fix this"): the court-speed estimate joins a renamed event to its own history. The 2026 Shanghai main draw is filed as "Shanghai" and every earlier edition as "Shanghai Masters", so this year's matches had read only this year's rows: 64 serve rows a quarter-final, now 2,383.
* **The renames joined** come from an audit of every main-tour event's names over 2010–2026. They are Shanghai 2026, Rio 2020, Nur-Sultan → Astana, Adelaide 1 and 2, Charleston 1, Guadalajara 2, Cluj-Napoca 2, Calvia → Mallorca and Japan Open Tokyo → Tokyo.
* **Kept apart:** a move of city or of surface, such as Montreal and Toronto.
* **This departs from the checked definition.** The check scored values built with the old key. In its window 406 of 9,326 matches (4.4%) sit at venues the renames join, and their pattern shift moves by a median 0.02 points (at most 1.8). The check's result stands as it was read; live values use the joined venues from now on.
