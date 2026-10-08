# Pre-registration: pair strength on 2025–2026

7 October 2026, written before any 2025–2026 result is related to pair strength or to the arm below. Research evidence, not a decision. The run (`./python.sh src/eda/pair_strength/final_test.py --run`) checks every hash below before it loads a result, writes the two primaries to disk before anything else, and runs once.

## What was seen before this was written

* **Development seasons 2014–2024**, every look listed in the [ledger](ledger.md): the reproduction of I-084, the exploration of its form and mechanism, ten calibration layers, the feature-interactions levels arm, and the arm `elosum` with its placebo.
* **2025–2026: no result read by this study.** It read counts, coverage, constants and forecasts only; its TabPFN fits of 2025–2026 train on earlier seasons. Other studies have scored the current best on these seasons overall and by tour, season, data fault and Polymarket subset. As far as their reports show, none has split them by pair strength. The arm `elosum` was fitted today and has never been scored on them.

## The hypotheses (one-sided; family-wise 5% by Holm: the smaller p against 0.025, then the larger against 0.05)

**H1, the lead (the feature-interactions study's I-084, reversed).** The calibration slope of the current best's forecast falls as the pair's combined strength rises.

* logit P(A wins) = Σ_{tour × season} a·η + Σ_tour c·η³ + Σ_tour m·η|η| + b·(s·η), no intercept.
* η is the current best's raw out-of-sample log-odds: the 58-input local TabPFN-3.5, symmetrised, the mean of every seed available (0–15).
* s = (R_A + R_B − mean_tour) / SD_tour: the two players' overall Elo (Elo pieces, the ratings of the model's `elo_overall` input). The constants are fixed on 2014–2021, debut seasons out (`CONSTANTS_JSON` below).
* The variance of b is the largest of the four-week-block, shared-player and union clustered variances, with t on G − 1 degrees of freedom (G = 21 four-week blocks).
* **H1: b < 0.**

**H2, inclusion in the model.** The arm `elosum` has a lower log loss than the current best.

* `elosum` is the 58 inputs plus R_A + R_B as one context column, the same local TabPFN-3.5 settings, walk-forward. Each arm uses seeds 0–7.
* Each arm is deployed with the decided calibration: one slope per tour, fitted on that arm's own out-of-sample forecasts of 2019 to Y − 1.
  * The model's history uses every seed available.
  * The arm's history uses seeds 0–2 for 2019–2024 and seeds 0–7 for 2025.
* The statistic is the paired mean log-loss difference (model minus arm) with the four-week-block cluster SE, t on G − 1.
* **H2: the mean difference is above 0.**

## Effect sizes (reported with 95% intervals; mLL per match, positive = the second-named has the lower log loss, better; spanning 0 = tie)

* **H2's paired gain itself** (the arm against the model).
* **For H1, the layer `lin` against `B14`.**
  * `lin` is a slope per tour plus b_tour·(elo_sum × η). `B14` is a slope per tour.
  * Both are fitted on the base's out-of-sample forecasts of 2014 to Y − 1 and applied to Y = 2025, 2026.

## Secondaries (descriptive, never confirmatory)

1. H1 by tour and by season.
2. H1 on the price base: the de-vigged average close in place of η.
3. The weakest-fifth form: 1[elo_sum ≤ the tour's 20th percentile of 2014–2024] × η. The direction consistent with H1 is b > 0 (weak pairs steeper).
4. The layers `lin_pooled` and `q1` against `B14`; `lin` against the decided calibration B (2019 to Y − 1); `B14` against B.
5. **Polymarket**: the 2,648 matches with a price 24 hours before the listed start. H1's coefficient with each of these as the base:
   * the 24-hour price;
   * the 30-minute price;
   * the model fed the 24-hour price.
6. H2 by tour and by season.
7. H2's encompassing coefficient with disjoint seeds: base = the model's seeds 8–15; deviation = the arm's 0–7 minus the model's 0–7.
8. The arm's own H1 coefficient.
9. Both arms fed the 24-hour Polymarket price, paired.

## Power (from the development estimates; both are upper-end guesses)

**H1.**
* The development estimate, from the screen's nuisance on 2014–2024, is b −0.0316 per SD (SE 0.0113, 50,087 matches).
* On 8,520 matches the SE is about 0.027, so the expected t is about −1.15.
* Power is about 17% at 2.5% and about 28% at 5%.
* The lead was selected as the most extreme of 34 tests, so its size is probably overstated and the power lower still.

**H2.**
* The development gain is +0.17 [+0.07, +0.27] mLL: decided calibration, 2020–2024, 22,265 matches.
* On 8,520 matches the SE is about 0.08, so the expected t is about 2.1.
* Power is about 50% at 2.5% and about 65% at 5%.
* At the smaller 2022–2024 estimate (+0.11), power is about 24% and 36%.

**A tie on either is therefore likely even if the effect is real.**

## Reading (fixed now)

* **H2 rejected (Holm).** Adding the Elo sum improves the current best on unseen seasons. It is the candidate model change for the owner to decide, sized by its interval.
* **H2 not rejected, gain above 0.** Not confirmed; consistent with the development estimate if the interval contains it. A prospective continuation on matches after 7 October 2026 is the next test.
* **H2's gain at or below 0.** No support on new seasons; keep the current model.
* **H1 rejected.** The slope pattern holds beyond the current best on new seasons; the `lin` layer's effect size gives its practical value.
* **H1 not rejected.** Not confirmed. At this power that is not evidence of absence.
* **The Polymarket secondaries.** They describe whether the pattern exists at the venue's own prices. They decide nothing.
* **After the run.** Every later analysis of 2025–2026 results is exploratory and gets its own ledger row.

## Hashes (checked by the run before any result is loaded)

CODE_SHA256: 5e98f970ee83bc18fdf82ac978a4997bcae3aae3a6217d6fd865b4862428dc03
FORECASTS_SHA256: 702e1b802f410692fd152fb5c701ed7ecd2f489f5d12b6c52ba4e5116aa86c36
MODEL_FRAME_SHA256: 6113966fd8286cb41738eb7b52e0d6d9e2d7631c980c3aec7be6e4bbbaaab06b
PIECES_SHA256: 40661ce97ee43f6fda8ff69f033c4799bb3e4fd4236efe6a44d95f6cd5e985e2
STAGE0_SHA256: 271d2561f31d0c8cc407e5fb9b73d572115173e329e272c337f8daddda4662af
EARLY_SHA256: 22809fa7a9422a22f28953292cca0d5db894470f3218bc23d45d3cdce9729a5c
POPULATION_SHA256: b76b595aeabfcab65677446780dc3f4ae25611859b9751d3dfefc2bb27f276c2
CONSTANTS_JSON: {"atp": {"mean": 4378.98921577699, "q20": 4201.171163883104, "sd": 253.27708178975504}, "wta": {"mean": 4357.498690053659, "q20": 4190.617328208602, "sd": 235.28683893283224}}

The code hash covers `src/eda/pair_strength/final_test.py`, `src/eda/pair_strength/common.py`, `src/eda/feature_interactions/screen.py`, `src/eda/feature_interactions/common.py` and `src/eda/tabpfn_thinking/common.py`. The forecasts hash covers every `model` file in `data/studies/feature_interactions/local/` and `data/studies/surface_rating_race/local/`, and every `elosum` file in `data/studies/pair_strength/local/`.
