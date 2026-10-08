# Pair strength: should the forecast's confidence depend on how strong the two players are?

7 October 2026 · Research evidence, not a production, model or betting decision.

**The owner's request (7 Oct 2026).** Investigate deeply the feature-interactions study's lead, I-084: "pair prominence × the forecast", z −2.99 against its declared direction ([that study](../feature_interactions/README.md), [its note](../feature_interactions/next_candidates.md)). See whether it has promise for the best local, non-thinking TabPFN-3.5 model (the 58-input model, "the current best"). The owner was not sure what the lead meant.

**Keys.**
* **b** is the change in the forecast's slope (the multiplier on its log-odds) per standard deviation (SD) of pair strength. **Negative = the forecast should be flatter (closer to 50%) for strong pairs.**
* z and t are b divided by its standard error; they carry b's sign.
* **Gains** are milli-log-loss (mLL) per match, paired: **positive = the second-named has the lower log loss (better)**. A 95% interval that spans 0 is a **tie**.
* **Observed** = computed here; **inferred** = reasoning; **suggestion** = not decided.

## In short

* **What the lead meant.** A forecast can be right on average and still be too confident in some kinds of match. The lead said the model is a little too confident when both players are strong and not confident enough when both are weak.
* **What it is (observed, 2014–2024).**
  * It is the well-known favourite–longshot bias of low-level matches. The closing price carries it, and the model inherits it.
  * It is concentrated in the weakest fifth of pairs, the WTA and the 250s. Favourites there win a little more often than priced.
  * It holds on Pinnacle's prices and under another de-vig, so it is not a margin artefact.
  * It is about a third the size the study's example suggested. At a 70% forecast it moves the right answer by under 1 point (69.4% for strong pairs, 70.9% for weak ones), not 2.
* **Built into the calibration (observed):** ten walk-forward forms on 2015–2024, every one a tie with the current calibration. The best was +0.12 [−0.01, +0.25].
* **Built into TabPFN (observed):** the 58 inputs plus the pair's Elo sum as one more input, on 2014–2024.
  * The current best's decided calibration: +0.17 [+0.07, +0.27], better.
  * The same column shuffled (a placebo): a tie. The real column against the placebo: +0.12 [+0.06, +0.17], better.
* **The one-shot test on 2025–2026 (pre-registered and hashed; 8,520 matches): neither hypothesis confirmed.**
  * **H1, the slope pattern:** b +0.022 [−0.030, +0.074], a tie, with the point estimate on the other side.
  * **H2, the Elo-sum model against the current best:** −0.07 [−0.29, +0.16], a tie, leaning worse.
  * Polymarket's own prices show no pattern either.
* **Inferred.** The development gain of the Elo-sum model sat mostly in the weakest fifth of pairs, where the favourite–longshot pattern lives. In 2025–2026 that pattern was absent, and that is exactly where the model lost (−1.44 [−2.94, +0.06], exploratory).
* **Recommendation (suggestion):** keep the current best unchanged; do not add the Elo sum. I-084 and the Elo-sum input have now used the 2025–2026 holdout. Any further test of them must be prospective, on matches after 7 October 2026.

## What the lead meant, in plain words

The model gives a probability, say 70% for the favourite. Over many such matches, favourites should win about 70% of the time. If they win 72%, the model was not confident enough; if 68%, too confident.

The feature-interactions study asked whether the right amount of confidence depends on how good the two players are as a pair. It measured pair strength as player A's Elo plus player B's Elo, so it is the same whichever player is called A.
* **The registered guess:** strong pairs are better known, so the forecast should be *more* confident for them.
* **The data said the opposite** (z −2.99): less confident for strong pairs, more for weak ones.
* **Why the study could not claim it.** It tested only the registered direction, and with 34 tests, one this extreme in either direction turns up by chance about 9% of the time. So it was a lead, to be checked on seasons nobody had used: 2025–2026.

**Its size was overstated.** The study's example (a 70% favourite plays at 67.8% in strong pairs and 72.1% in weak ones) came from a fit that also contained a closely related measure, the weaker player's ranking (correlation −0.70), which inflated both. Measured alone (observed, 2014–2024, simplest form):

| Pair strength | A 70% forecast is better at |
|---|---|
| two weak players (−1.5 SD) | about 70.9% |
| an average pair | 70% |
| two strong players (+1.5 SD) | about 69.4% |

## Development: what the pattern is (2014–2024, 50,087 matches)

**The reproduction (observed).** The screen's I-084 row, rebuilt with its frozen builder and its own machinery, gives exactly the published values: z₁ −2.6566, z₂ −2.0326, joint −2.9846 (model); joint −3.1155 (price). Script: `reproduce.py`.

**Pair strength alone** (Elo sum × η, the screen's nuisance; joint z of 2014–2021 and 2022–2024; negative = flatter for strong pairs):

| Base | b per SD (pooled) | 95% interval | joint z |
|---|---|---|---|
| The current best's forecast | −0.032 | [−0.054, −0.009] | −2.88 |
| The closing price (average, de-vigged) | −0.045 | [−0.072, −0.017] | −3.29 |
| Pinnacle's close | – | – | −3.33 |
| The average close, power de-vig | – | – | −3.02 |

**Its shape (observed).**

* **The weakest pairs carry it.** Slopes by fifth of pair strength, relative to the middle fifth (positive = steeper):
  * weakest fifth +0.097 [+0.026, +0.168];
  * second +0.032; fourth +0.025;
  * strongest −0.020 [−0.087, +0.048].

  A quadratic term is positive (z +1.76): the slope falls with strength, then levels off.
* **The price has it, the model's own view does not add it.** Splitting the model's log-odds into the price and the model's adjustment:
  * the price's slope falls with strength (z −2.77);
  * the adjustment's goes the other way, a tie (+1.47).
* **It is the stronger player's level, the favourite's.**
  * Favourite's Elo −2.59, underdog's +0.62 (fitted together).
  * Higher of the two −2.42, lower +0.50.
* **Where.**
  * WTA −3.27, ATP −0.91 (a tie).
  * Within level: 250s −3.98, Slams −1.76, 1000s −0.50, 500s −0.40.
  * Seasons: negative in 9 of 11. The largest is 2024 (−0.112 [−0.197, −0.027]); 2016, 2020 and 2023 are near 0 or positive.
* **Not explained by** (elo_sum's z with each control):
  * the bookmaker margin (−3.20);
  * the level, best of five and round depth (−2.87);
  * the mismatch size (−2.81);
  * experience (−3.43);
  * age (−3.30).
* **Other strength measures agree** (each alone): TrueSkill Through Time sum −3.00; log-rank sum +2.98 (more ranking points = stronger, so the same direction).

**Inferred: what it is.** It is the favourite–longshot bias concentrated in low-level matches (Lahvička's "both outside the top 50"; [literature](../feature_interactions/round0/literature.md)): favourites of weak pairs are underpriced. The current best takes the price as an input and calibrates with one slope per tour, so it inherits the bias. The "too confident for elite pairs" half of the study's reading is weak; the pattern is mostly the weak-pair half.

## Development: can the model use it?

**As a calibration layer** (walk-forward, each layer fitted on the out-of-sample forecasts of 2014 to Y − 1; against B14, the same window with one slope per tour; `deploy.py`):

| Layer | 2015–2024 | 2015–2021 | 2022–2024 | Better |
|---|---|---|---|---|
| lin: + elo_sum × η per tour (the reversed I-084) | +0.03 [−0.09, +0.15] | +0.00 | +0.09 | tie |
| lin_pooled: one b for both tours | +0.03 [−0.06, +0.12] | +0.02 | +0.05 | tie |
| q1: the weakest fifth steeper | +0.12 [−0.01, +0.25] | +0.16 | +0.04 | tie |
| quad: linear + square | +0.04 [−0.10, +0.17] | −0.01 | +0.14 | tie |
| level: a slope per tour × level | −0.07 [−0.24, +0.10] | −0.11 | +0.01 | tie |
| level_lin | +0.05 [−0.17, +0.27] | −0.02 | +0.19 | tie |
| lrank / ttt (other strength measures) | +0.03 / −0.01 | – | – | tie |
| mset: cubic and η\|η\| | −0.12 [−0.26, +0.02] | −0.20 | +0.05 | tie |

Gains in mLL, positive = the layer better than B14.

On the price alone (not the model), mset is +0.27 [+0.05, +0.49] better and q1 +0.14 [+0.01, +0.27]. The price needs a curved calibration; the model does not.

**As a TabPFN input.**

* **The levels arm** of the feature-interactions study (17 sums, the Elo sum among them; `levels_check.py`, 2016–2024):
  * it absorbs about 45% of the pattern (b −0.032 → −0.018, z −2.41 → −1.38);
  * calibrated, it ties the model: +0.05 [−0.12, +0.21] (2017–2024).
* **The arm `elosum`**: the 58 inputs plus R_A + R_B, local fits, seeds 0–2 (`local_fits.py`, `score_arm.py`, `where_gain.py`).

| Comparison (development) | Gain, mLL | Better |
|---|---|---|
| elosum vs model, the decided calibration, 2020–2024 | +0.17 [+0.07, +0.27] | elosum |
| ATP / WTA (same) | +0.23 [+0.09, +0.37] / +0.11 [−0.07, +0.29] | elosum / tie |
| elosum vs model, calibrated from 2014, 2015–2024 | +0.15 [+0.08, +0.22] | elosum |
| 2015–2021 / 2022–2024 (same) | +0.17 [+0.08, +0.26] / +0.11 [−0.00, +0.22] | elosum / tie |
| Encompassing with disjoint seeds (model seeds 3–5 as the base), 2016–2024 | b +2.23 [+1.11, +3.34] (positive = the arm adds information) | elosum |
| Seed check: elosum vs the model's seeds 3–5, 2017–2024 | +0.21 [+0.13, +0.29] | elosum |
| **Placebo** (the column shuffled within tour × season) vs model, 2015–2024 | +0.03 [−0.02, +0.08] | tie |
| elosum vs the placebo, 2015–2024 | +0.12 [+0.06, +0.17] | elosum |

* **Where the development gain sat:**
  * weakest fifth of pairs +0.40 [+0.16, +0.64];
  * favourites of 70–80% +0.40 [+0.24, +0.57];
  * the 250s +0.20 [+0.08, +0.31];
  * both tours.
* The arm removes only about a quarter of the slope pattern itself (b −0.032 → −0.024).

## The one-shot test on 2025–2026

[Pre-registered](preregistration.md) and hashed (SHA-256 b75ab3a8…) before any 2025–2026 result was read. Run once at 13:36. Every input, code and forecast hash matched. 8,520 matches (4,394 men's, 4,126 women's), 21 four-week blocks. Outputs: `data/studies/pair_strength/final/`.

**The stated power was low:** H1 about 17–28%; H2 about 50–65% at the full development gain and 24–36% at its 2022–2024 size. Both are before any discount for selection.

| Endpoint | Result | Holm (one-sided, family-wise 5%) | Reading |
|---|---|---|---|
| **H1**: b < 0 (flatter for strong pairs), the current best's 16-seed forecast | **b +0.022 [−0.030, +0.074]**, t +0.88, p 0.81 | not rejected | **tie**; the point estimate is on the other side |
| **H2**: elosum better than the current best (seeds 0–7 each, the decided calibration) | **−0.07 [−0.29, +0.16] mLL**, t −0.61, p 0.72 | not rejected | **tie**, leaning worse |

**Effect sizes and secondaries** (pre-registered, descriptive):

| What | Result | Reading |
|---|---|---|
| lin against B14 (H1's layer) | −0.14 [−0.52, +0.24] | tie |
| lin_pooled / q1 against B14 | −0.13 [−0.41, +0.16] / −0.12 [−0.32, +0.08] | ties |
| lin against the decided calibration B; B14 against B | −0.08 [−0.53, +0.38]; +0.06 [−0.07, +0.20] | ties |
| H1 by tour: ATP / WTA | +0.048 [−0.022, +0.118] / −0.002 [−0.080, +0.075] | ties (the WTA, the development's strongest, shows nothing) |
| H1 by season: 2025 / 2026 | +0.042 / −0.012 | ties |
| H1 on the closing price | +0.024 [−0.040, +0.089] | tie |
| Weakest fifth (H1's direction is +) | −0.089 [−0.252, +0.075] | tie, the other side |
| **Polymarket** (2,648 matches): H1 on the 24-hour price / the 30-minute price / the model fed the 24-hour price | +0.045 [−0.048, +0.139] / +0.025 / +0.037 | ties; no pattern at the venue's prices |
| H2 by tour: ATP / WTA | −0.08 [−0.34, +0.18] / −0.05 [−0.45, +0.35] | ties |
| H2 by season: 2025 / 2026 | −0.20 [−0.56, +0.15] / +0.14 [−0.09, +0.37] | ties |
| H2's encompassing, disjoint seeds | b −0.61 [−3.38, +2.16] | tie (development +2.23) |
| The arm's own H1 coefficient | +0.033 [−0.021, +0.086] | tie |
| Both arms fed the 24-hour Polymarket price | +0.22 [−0.09, +0.53] | tie |

**Exploratory, after the run** (ledger row 13; it cannot change a reading).

* **One suspect for H2 was Elo inflation.** The pair sum drifts upward: 12.6% and 12.8% of the WTA's 2025 and 2026 matches lie above the training seasons' 95th percentile, against 5% with no drift; the ATP shows none.
  * It is not where the arm lost: above that line −0.01 [−1.01, +0.99], below −0.07 [−0.27, +0.13].
* **The arm lost in the weakest fifth of pairs:** −1.44 [−2.94, +0.06] (643 matches). The other fifths: +0.34 [+0.03, +0.66], +0.29, −0.03, −0.15.

## What it means (inferred) and what next (suggestions)

* **Why it did not carry over.** The development signal, in the price, in the model and in the Elo-sum arm, was the favourite–longshot bias of weak pairs. In 2025–2026 that pattern was absent: H1 ties on the other side, at the average close and at Polymarket alike. The Elo-sum arm had learned to correct it, so the correction cost it in exactly those matches.
  * It may have been weaker all along (selection from 34 tests; seasons vary, 2023 was positive).
  * Or the market priced weak pairs better in 2025–2026.
  * The data cannot tell these apart yet.
* **Process suspects** (per the owner's premise, a null is not a verdict):
  1. **Power.** H2's interval half-width was 0.22 mLL, so the test detected a gain reliably (80%) only from about 0.3 mLL. H1's expected t was about −1.2.
  2. **Non-stationarity.** A calibration bias of the market can move with the market. A model that learns a static correction from 2013–2024 is exposed to that; a recency-weighted calibration is one untested answer.
  3. **Elo drift.** It is real for the WTA. A field-relative pair strength (the sum minus the tour's recent mean) would remove it, but the exploratory split says drift was not where the loss was.
* **Suggestions.**
  * Keep the current best unchanged.
  * Do not add the Elo sum or a pair-strength calibration layer.
  * I-084 and the Elo-sum input have now been opened on 2025–2026. The feature-interactions study's other near misses (B-VENUE, on-site rhythm, B-OVERREACT) are still untouched there.
  * If the owner wants to keep watching this one, the same pre-registered H1 and H2 can be scored prospectively on matches after 7 October 2026.

## Limitations

* **2014–2024 was not fresh.** The lead was the most extreme of 34 one-sided tests on those seasons, and this study explored them further (ledger rows 1–10). Only 2025–2026 is clean, and it was opened once.
* **The test was small** (8,520 matches; 21 blocks, t on 20 degrees of freedom). 2026 is partial, to early October.
* **Seeds.** The development arms used seeds 0–2; the test used 0–7 per arm and 16 for H1's base. The arm's calibration history used 3 seeds, the model's up to 16.
* **Prices.** Closing prices are archived average closes, not executable bet-time prices, and a log-loss gain is not a betting return. Pinnacle's close ends in January 2026, so the test has no Pinnacle base.
* **Model and data.** The local TabPFN is the open checkpoint, not the API's Plus or Thinking; no paid call was made. The model frame is the frozen pre-rebuild version the feature-interactions study used, so the Tennis My Life men's Slam first-serve fault is unrepaired. It touches both arms alike.

## Files

| What | Where |
|---|---|
| Code | `src/eda/pair_strength/`: `common.py`, `reproduce.py`, `explore.py`, `deploy.py`, `levels_check.py`, `local_fits.py` and `launch_when_free.sh` (GPU, env `tennis-tabpfn-local` through `./python_tabpfn_local.sh`), `score_arm.py`, `where_gain.py`, `final_test.py`, `explore_test.py` |
| Tests | `test/pair_strength/test_pair_strength.py` (4: swap symmetry, a planted slope recovered, walk-forward reads only earlier seasons, the primary on synthetic 2025–2026 outcomes) |
| Development outputs | `data/studies/pair_strength/`: `reproduce.json`, `explore.json`, `deploy.json`, `levels_check.json`, `score_arm.json`, `where_gain.json`; fits in `local/` (`elosum`, `elosum_perm`) with their logs |
| The test | [preregistration.md](preregistration.md), [ledger.md](ledger.md); `data/studies/pair_strength/final/`: `check.json`, `dry_run.json` (synthetic), `final_primary.json`, `final_results.json`, `explore_test.json` (exploratory) |
