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
