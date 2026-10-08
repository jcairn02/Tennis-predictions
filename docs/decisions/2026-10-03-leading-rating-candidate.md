# TrueSkill Through Time is the leading candidate for the base rating

**Stated by the owner on 3 October 2026,** who asked that it be made clear to future reviewers: "CURRENTLY trueskill through time performed the best and is our leading ELO candidate for our model." Recorded on 3 October 2026.

## Decision

**TrueSkill Through Time (TTT) is currently the leading candidate for the model's base rating.** This is the version run causally, as built in the [rating systems study](../studies/rating_systems/README.md). The base rating is the slot that Stage 1's surface Elo has filled in every study so far.

"Currently" is the owner's word. This is the present standing, not a final choice. It holds until a rating beats TTT under the same protocol, or until the rebuild listed below changes the answer.

## The evidence

Every number is read from `data/studies/rating_systems/summary_results.json` (the `raw` and `leader` blocks), written by `src/eda/rating_systems/summary_results.py`.

* **Population.** Every evaluation match of the study: men's and women's singles from Grand Slams down to Challenger and WTA 125, qualifying included.
* **Units.** Figures are in milli-log-loss, with 95% intervals clustered by four-week calendar blocks.
* **Protocol.** Each of the nine ratings, Elo included, was built under the same time rule. Its constants were tuned on the log loss of 2013–2018 and then frozen. The tuning years' log loss is the rule that picks the leader.

| | Men | Women |
|---|---|---|
| Rank on the tuning years, 2013–2018 (the selection rule) | 1st of 9 | 1st of 9 |
| Better than surface Elo, 2019–2026 (after the tuning years) | +2.65 (+1.89 to +3.40) | +3.00 (+1.67 to +4.33) |
| Better than surface Elo, 2022–2026 | +2.90 (+2.06 to +3.74) | +2.29 (+0.92 to +3.67) |
| Runner-up after 2019 | Glicko with correlated surface skills | TrueSkill with correlated surface skills |
| TTT against that runner-up, 2019–2026 | +0.54 (−0.02 to +1.10) | −0.29 (−1.29 to +0.71) |
| TTT against that runner-up, 2022–2026 | +0.85 (+0.18 to +1.53) | −0.68 (−1.99 to +0.62) |

* **Men.** TTT is best in every window, both in the tuning years and after them.
* **Women.** TTT was best in the tuning years, the selection rule; there it beat the correlated-surface TrueSkill by +0.99 (+0.09 to +1.88). After those years the two are level within the noise, with the correlated-surface TrueSkill slightly ahead. It is the runner-up to watch for the women.
* **The smoothing check.** TTT holds when two-week events are held back: +2.59 (men) and +2.75 (women) in 2019–2026.
* **The audit's repaired cohort.** On main-tour matches with trusted dates, TTT alone beats calibrated Elo by +2.07 (men) and +3.05 (women), 2019–2026.
* **The literature** ranks smoothing systems like it highest ([review](../research/rating-systems/README.md)).

## What it does not do

* **It is not an edge on the market.** Added to the closing odds it gains about nothing:
  * +0.04 (men) and −0.02 (women) through the shared test;
  * +0.08 (−0.01 to +0.16) against calibrated Pinnacle in the audit's test (men, 2019 to 13 Jan 2026, where the Pinnacle odds on file end).

  A better base rating improves the forecast; it does not beat the bookmakers.
* **Most of its gain over Elo is already in the promising features.** In the audit's full feature model (2022–2026):
  * swapping Elo for TTT gains +0.48 (men) and +0.19 (women);
  * keeping both ratings gains +1.17 and +1.21.

## Before it is used in a model

* **Rebuild it on the repaired history.** The study's history still holds the 2026 duplicate player IDs (one player split across two identities) and dates matches by event start. The audit's repairs fixed both in their own pipeline.
* **Allow for its cost.** The men's full pass takes about 19 minutes; Elo's takes about a second.
* **Note the smoothing window.** For the men it reached the largest value tried (416 weeks). The last doubling gained 0.12.

## Not decided

* **Whether surface Elo is kept beside it.** Together they add about a milli-log-loss to the full model, and the study suggested carrying both.
* **Whether earlier studies are redone with TTT.** Their results stand as recorded, with surface Elo as the base.
* **What could replace it:** any rating that beats TTT under the same protocol. One untested idea, raised on 2 October 2026, is a rating built from players' past closing prices instead of their results.
* **The project's status.** No model, dataset, market or roadmap is selected. TTT is a candidate component.
