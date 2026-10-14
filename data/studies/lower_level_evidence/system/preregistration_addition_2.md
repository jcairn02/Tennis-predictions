# Pre-registration, addition 2: the evaluator's four questions

Written 9 October 2026, 21:06 UTC, by the lead. No score of any arm of this run had been computed or read: role D's
report of about 21:05 UTC, and its queue, which runs input checks and fits only. This file has its own SHA-256
(`preregistration_addition_2.sha256`). The earlier files are unchanged: `preregistration.md` (`cc65bcd5…`) and
`preregistration_addition_1.md` (`c718e6d0…`).

## 1. Matches of 2026 with no serve-speed memory

**The fact (role D).** The frozen frame's speed memory is missing for 909 matches of 2026, 416 of them men's, from
15 June to 23 September 2026. It is a gap in the frozen speed panel. compare.py would leave those men's matches without a
stage-2 forecast.

**The rule.**
* **Primary and every reading: score them with no stage-2 nudge.**
  * The speed term b̃ · `spd_L` is 0, so the forecast is s_tour · η, the per-tour calibration alone.
  * This is the value a centred speed memory takes when it holds no information, and the value every women's match already gets.
  * It applies identically to every arm.
* **Sensitivity, reported beside the primary:** the same readings with those 909 matches left out.

## 2. Women's ITF box scores before 2025

**The fact (role D).** Women hold ITF box scores on 31 matches of 2022. ITF box scores do not start in January 2025 for women, as addition 1 and the SPEC assumed.
* Men have none before 2025, so the shortcuts of addition 1 still hold for the men's arm SYS_ITFASIS.
* REF_noITF and SYS_BOTH_ITFASIS have women's inputs from 2022 on that may differ from the arms they are compared with.

**The rule.** Wherever an arm's inputs differ from its comparator's in a season, that arm is fitted on that season. No fit is copied unless its inputs are identical (role D's queue already checks this). Reading these arms on the holdout is unchanged. Where inputs differ before 2025, dev readings are reported too.

## 3. What "no secondary is worse" means in the recommendation

The original sentence: "unresolved with P(better) ≥ 0.80 and the pooled 2020–2026 primary is better and no secondary is
worse".

**"No secondary is worse"** means: none of the following **men's holdout readings of SELECTED against REF**, both stages, is "worse" after a **Holm correction** across these eight readings (family-wise 5%):
1. season 2025;
2. season 2026;
3. the less-exposed side has fewer than 10 main-tour results in 365 days;
4. both sides have 10 or more;
5. a 365-day box-score share gap of 0.5 or more;
6. a share gap under 0.5;
7. falsification (both sides have 20 or more main-tour results and both shares are under 0.10);
8. stage 1 alone (all men's holdout matches).

All other readings are reported and carry no condition: other arms, the dose curve, women, the rule test and dev. The raw (uncorrected) labels of the eight are reported too.

## 4. P(better)

**P(better) = Φ(estimate / SE),** as the pre-registration says. compare.py's t-based value is recorded beside it, and any step of the selection where the two would disagree is flagged.

## 5. Unchanged

Everything else in `preregistration.md` and addition 1 stands. SYS's internals will be fixed at checkpoint 1 by a further addition, which records the full SHA-256 of these files:
* `classes/classes.csv`;
* `relationship/params.parquet`;
* `relationship.py`;
* `level_layer.py`;
* `level_layer_ios.py`.
