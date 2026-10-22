# TabPFN-3.5-Thinking runs beside the current best model; the bet sheet decides on their 50/50 average in log-odds

**Decided by the owner on 20 October 2026.** Carried out by Claude the same day ([process log, Part 6](../studies/master_pipeline/process_log.md)). The owner's words:

> "The intention is to have a tabpfn 3.5 paid thinking version I can run IN ADDITION to the tabpfn3.5 nonthinking version, so I can see their results side by side in the tennis bet sheet. So its EITHER the nonthinking-calibrated version OR ( the thinking-noncalibrated version AND nonthinking-calibrated version) that's output in the display."
>
> "We'll use basically a 50/50 ensemble to calculate edge/expected profit."
>
> "The only difference between that model and the nonthinking is how its called (the API) and that we do not calibrate those probabilites, we use the probabilities given to us from the API."
>
> "We only need US odds. Convert lowest odds to take into american as well."
>
> Later the same morning, to the three defaults Claude had put to the owner: "one seed for thinking, averaging in log
> odds not a plain average, pattern adjusted after averaging is correct."

**Amended by the owner the same evening: Thinking takes stage 2's serve-speed term, never its calibration.** The
morning's wiring had read "we use the probabilities given to us from the API" as no stage 2 at all, so the 50/50
average carried only half of each men's speed nudge. The owner's words, on reading that:

> "Tabpfn3.5 thinking should still move with the serve speed numbers wtf? just not the calibration."

* **The rule now:** logit(Thinking's chance) = logit(the API's own chance) + b̃_Y · `spd_L`, with the local model's b̃
  for the match's season and speed feed and the same `spd_L`, 0 for women; no calibration slope. The ensemble is then
  ½ s·η + ½ logit(the API's chance) + b̃·`spd_L`: the speed nudge at full strength.
* **It is the form already used and recommended:** the 8 Oct Thinking study's "Thinking + offset", and the master
  pipeline's recommendation of 11–13 Oct ("η + the local b̃·spd_L, no slope").
* **Why the local b̃:** it is the only estimate (one of Thinking's own would need a paid fit per past season), and
  `spd_L` is in neither model's 57 inputs, so the term is new information to both.
* **Done** by Claude the same evening (`dp_predict.speed_only`; `predictions.csv` gains `q_a_thinking_api`, the API's
  own, and `q_a_thinking` becomes Thinking with the term; the curves and a reprice carry both). Runs made before it keep
  the morning's rule: `live_2026-10-20_081558`'s 14 men's matches had speed gaps of −1.6 to +1.5 units, so its
  ensemble chances sit up to about 0.6 points from the amended rule's. [Process log](../studies/master_pipeline/process_log.md), Part 7.

## The rule

**Two settings of the notebook's `MODEL`:**
* `"tabpfn35"`: the current best model alone, unchanged.
* `"tabpfn35_thinking"`: the same run, plus TabPFN-3.5-Thinking beside it. Thinking never runs alone.

**Thinking is the local model in everything but two things:**
* how it is called: the hosted API, paid;
* its probabilities are used as the API gives them. ~~There is no stage 2: neither the calibration slope nor the serve-speed term.~~ *Amended the same evening (above): no calibration slope, but stage 2's serve-speed term is added.*

Everything else is the same:
* the active instance's 57 inputs;
* exactly the local fit's training rows for the season. The daily engine checks their hash against the season fit's;
* the same rows to predict: each match at the 91 grid prices and at its own price, stored and with the players swapped. The two orientations are averaged, as the local model's are. That is how both models are asked, not a calibration.

**The ensemble decides.**
* It is the two chances without patterns averaged 50/50 in log-odds: logit q = ½ logit(the local model's stage-2 chance) + ½ logit(Thinking's chance). Near even money this is almost the plain average (60% and 70% give 65.2%); at long odds it leans further from 50% (10% and 20% give 14.3%, not 15%).
* The five-pattern adjustment, while on, is added to the average's log-odds, as it is to the local model's today.
* "Model chance", the edge, the expected profit, the decision, the lowest odds to take, the break-even prices and a reprice all use it.

**The bet sheet shows US odds only.**
* Pinnacle's price, the lowest odds to take, the fair odds, a venue's price and the notes are all American odds. The machine record keeps decimal odds, because expected profit is computed from them.
* A run with Thinking shows three chances without patterns, the non-thinking, the thinking and the ensemble, where a local run shows one.

**If the Thinking call fails,** the run still gives the local model's predictions:
* the predict cell says so in capitals;
* the sheet's first run note says so;
* `predictions.csv` says `ensemble` "off", and `provenance.json` gives the reason.

## Cost and limits

* **The season fit:** one paid fit per instance and season, with seed 0. It is made by A4 when the active instance has none, or by C9.
  * About 180k tokens and 8 minutes: the 13 Oct bill was 181,901 tokens, 25% of its quote.
  * The fit of `template_2026-10-16` for 2026 was made by A4 at 08:16–08:23 on 20 Oct: 181,901 tokens again (quoted 727,604, as on 13 Oct).
  * A rebuilt instance needs its own fit.
* **Its training rows are the local model's: season Y on 2013 .. Y − 1** (the annual protocol of the current best model).
  * For 2026: 62,869 matches of 2013–2025.
  * The 4,357 matches of 2026 in the instance's frame are not training rows for either model. Their results reach every prediction through the inputs (ratings, forms, serve profiles).
  * The owner decided on 9 Oct that live fits grow within the season ([current best model](2026-10-08-current-best-model.md), "Live fits grow within the season"). That is not built for either model yet, and needs its calibration guard first.
* **The day's call:** one paid call per A4 run, all its matches together.
  * The cost barely depends on the number of matches: 126,286 quoted for 5 matches (13 Oct, billed 31,572), 136,939 for 30 (20 Oct quote).
  * So about 32–35k tokens a run.
  * A reprice (A6) reads the stored curves, at no cost.
* **The account:** 5M tokens a day and 20M a month. 15.4M of this month's 20M remained on 20 Oct.

## The three choices put to the owner, and the answers (20 Oct 2026)

| Choice | Claude's first default | The owner's answer | What the other way would have done |
|---|---|---|---|
| Thinking's seeds | seed 0 only | **Confirmed** | 16 seeds, as the local model: 16 times the cost |
| How the two chances are averaged | the plain average of the chances | **In log-odds, not the plain average.** Changed at 08:36, before the first live Thinking run (`live_2026-10-20_081558`) reached its predict step | the plain average: 0.17 points apart from the log-odds average near 50% (60% and 70%), 0.71 at 10% and 20% |
| Where the patterns go | after the average | **Confirmed** | to each model before averaging: about 0.05 points apart at the largest shift with the two models 10 points apart |

## What is known about how good it is

**The ensemble itself has not been measured on past matches.**
* Its predictions earn no edge credit (the [adoption framework](../studies/adoption_framework/README.md)).
* A walk-forward test would need a paid Thinking fit per past season: about 180k tokens each, so about 1.3M for 2019–2025.

**One earlier result points the same way.** The 8 Oct Thinking study used 58 inputs, one more than today's model.
* Uncalibrated Thinking was level with the calibrated local model: −0.01 mLL, 95% interval [−0.30, +0.27], 2022–26.
* In money at Pinnacle's close it was also level: +1.55% against +1.50%.

**The five-pattern adjustment's size was measured on top of the local model**, not the ensemble.

## Where it lives

| Part | Where |
|---|---|
| The switch | `scripts/master_pipeline.ipynb` (`MODEL`, `SPEND_TOKENS`) and `src/pipeline/predict.py` |
| The paid season fit | `src/pipeline/thinking.py`, `thinking_api.py` |
| The day's paid call | `src/eda/daily_prediction/dp_thinking.py`, through the project's guard (`src/eda/tabpfn_thinking58/guard.py`) |
| The step | `dp.py run_day --thinking --spend-tokens` |
| The ensemble | `dp_predict.py` (`log_odds_mean`) |
| The sheet | `src/pipeline/diagnostics.py`, `bet_sheet.py` |
| Tests | `test/daily_prediction/test_thinking.py`, `test/master_pipeline/test_master_pipeline.py` |
