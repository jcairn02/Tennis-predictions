# Elo by surface: giving the model the pieces, tested with TabPFN-3.5-Plus over 2022–2026

6 October 2026 · Research evidence, not a production, model or betting decision.

**Key for every score.** Log loss: lower is better. Gains are in milli-log-loss (mLL): +1 means the named model's
average log loss is 0.001 lower than the one it is compared with, so **positive = the named model is better**.
Brackets are paired 95% intervals clustered in four-week blocks of tournament dates. A range that spans 0 is a **tie**.
Labels: **observed** is computed here, **inferred** is a reading, **suggestion** is a proposal.

## The answer

**Observed. Given the closing odds, the idea neither improves nor hurts the best model.** Section 6 explains why a
stronger standalone predictor can tie next to the price, and §5.7 has an exploratory hint of where it may still help.

* **The pre-registered endpoint.** The evidence-based representation (`primary`) against the current best model's
  inputs (`base`), both tours, 2022–2026, three seeds each, on TabPFN-3.5-Plus: **−0.01 [−0.24, +0.21], a tie.** The
  interval rules out any gain above about +0.2 mLL.
* **The suggestion exactly as written** (`literal`): **−0.08 [−0.26, +0.10], a tie.**
* **Each season as one sample**, primary against base, both tours (positive = primary better):

  | 2022 | 2023 | 2024 | 2025 | 2026 | Mean [95%] | Seasons positive |
  |---|---|---|---|---|---|---|
  | −0.17 | −0.01 | −0.36 | +0.19 | +0.44 | +0.02 [−0.37, +0.40], tie | 2 of 5 |

  * Men: +0.14 [−0.19, +0.47], a tie, positive in 4 of 5 seasons.
  * Women: −0.18 [−0.51, +0.15], a tie, positive in 2 of 5.
* **Observed. Without the odds, the same representation does help.** Primary against base, both without the odds:
  * both tours: **+1.36 [+0.43, +2.29], better**;
  * men: **+2.74 [+1.23, +4.25], better, positive in all 5 seasons**;
  * women: −0.14 [−1.28, +1.00], a tie.
* **Inferred.** The surface information is real, and the closing price already holds it. This matches the earlier
  [market-anchoring](../market_anchoring/README.md) result on surface Elo. TabPFN can use the representation: it does so
  where the price is absent.
* **Observed (corrected the same day). Once recalibrated, TabPFN-3.5-Plus matches the thinking model.**
  * Plain Plus is over-confident. One calibration slope per tour, fitted on its own 2019–2021 pilot forecasts (men
    0.885, women 0.96), fixes it, as the [surface-IOS study](../surface_ios/README.md) found for the local model.
  * Recalibrated Plus against the current TabPFN-3.5-Thinking fit: +0.12 [−0.24, +0.49], a tie. Raw Plus was −0.52
    [−1.05, 0.00].
  * Against the closing odds recalibrated on each fold's training matches, recalibrated Plus is **+1.34 [+0.72, +1.96],
    better** (men **+1.62 [+0.81, +2.43]**). Thinking is +1.22 [+0.63, +1.81].
  * The idea's result does not change: recalibrated `primary` against recalibrated `base` is −0.05 [−0.26, +0.16], a
    tie (§5.4).
* **Observed. Against the early price, not proven** (§5.8). The test used the Polymarket price 24 hours out on 1,067
  clean matches, with free local GPU fits.
  * **Does the new representation predict the move to the close?** The pre-registered specification says yes, +0.33
    [+0.09, +0.57], but it is flawed: its control contains the early price. The price-free versions give +0.07 (tie)
    and +0.14 [+0.03, +0.25]. At most that is about half a point of probability per standard deviation.
  * **Its edge over the old representation on outcomes** is the same at 24 hours as at the close: +1.11 and +1.09, both
    ties.
  * **The firmer lead is broader.** The early price drifts toward the sporting model as a whole by the close, and the
    model fed that price beats it, recalibrated, by +2.85 [+0.14, +5.57].
* **Cost.** 97 paid non-thinking jobs, **1,565,378 tokens**, exactly the server's quotes (7.8% of the monthly quota).
  Fits are not billed. The early-price test made no paid call.

## 1. The question

The owner's two suggestions for the best 2026 model ([leak-proof TabPFN-3.5-Thinking](../tabpfn_leakproof/README.md)),
verbatim in [strategy.md](strategy.md) §1:

1. **Item 5.** Give the model the pieces of surface Elo (overall rating, surface-only rating, each player's surface
   match count) instead of the fixed 70/30 blend.
2. **Item 6.** Represent surface switches better than "first matches on this surface", which enters as A minus B. Use
   both players' counts, days since each last played on the surface, and last season's form on it.

The owner asked for four steps:
* audit the idea;
* build a representation from self-discovered evidence;
* have it reviewed by an independent auditor (Opus 5.5) and review that review;
* test the result with the non-thinking TabPFN-3.5-Plus, season by season over 2022–2026.

**How the work ran, in order:**

| Step | Record |
|---|---|
| Evidence on seasons 2010–2021 only, then a draft strategy | [strategy.md](strategy.md), `evidence.py` |
| Independent audit (Opus 5.5) of the evidence, the strategy and the code | [audit.md](audit.md) |
| The main statistician's review: every finding re-derived or answered | [audit_review.md](audit_review.md) |
| The amended, pre-registered protocol | [preregistration.md](preregistration.md) |
| Pilot on 2019–2021, then the confirmation and a no-odds diagnostic on 2022–2026 | sections 5–6 |

The audit's changes were all made before any 2022–2026 result of any arm was seen.

## 2. The claims, checked

These checks use the design seasons only. The verdicts are corrected per the audit (S5).

| Claim | Verdict |
|---|---|
| "A surface rating built on 5 matches is noise" | **Wrong in kind: it is biased, and the bias is informative.** Surface ratings start at 1500, so a man with ≤ 5 matches on a surface sits 445–459 Elo points below his overall rating. With 20–40 matches he is still 252 below. Players new to a surface win less often than overall Elo expects. Men with ≤ 5 career matches on it are −5.8 points (SE 3.4) and with 11–20 matches −4.7 (SE 1.5); women with 11–20 are −2.8 (SE 0.9). Against the recalibrated market the same men are +1.5 (SE 2.6) and −0.5 (SE 1.0): the price already has it (`evidence_priced.csv`) |
| Tennis Abstract 50/50, ours 30%, TTT 35% | Correct for men. Women: ours 25%, TTT 30% |
| "The right weight depends on how much evidence each player has" | **Direction right, no gain.** The best single weight rises with evidence: men 0.25 at 11–20 matches to 0.45 above 80, women 0.25 to 0.35. Those gains are only 0–0.8 mLL and are in-sample upper bounds. A per-player weight w·n/(n + k) on the existing surface rating tunes to k = 0: shrinking low-count ratings discards the inexperience penalty |
| "Only the pieces let the model learn that" | **Not in a linear model.** Overall plus surface-only rating, forward-chained 2016–2021, no odds: +0.10 [−0.23, +0.42], a tie against the blend. A rating that weighs evidence itself does better (section 3) |
| "First matches on this surface vanishes when both players are new, as in the first grass week" | **Confirmed.** In the opening week of the grass season both players are flagged in 61% (men) and 62% (women) of main-tour matches. Over all matches the A − B flag is zero in 92% of men's hard-court, 80% of clay and 65% of grass matches |
| "Add both counts, days since, last season's form" | **This season's counts and the layoff inform; career counts and form do not.** Without the odds, beside the offset Elo: season counts + layoff +2.56 [+1.36, +3.75] (men) and +3.83 [+2.53, +5.12] (women), both better. Career counts −0.75 [−1.41, −0.08] (men), worse. Last season's form +0.17 / −0.06, about nothing. With the odds every piece ties |
| "The no-odds model trails the market by 31–34 mLL early in the clay and hard seasons, 10 later" | Quoted correctly from [market anchoring](../market_anchoring/README.md) §6.4, which covers the men's main tour. It describes a no-odds model; the model under test holds the odds |

## 3. From the evidence to the representation

**A better surface Elo: the surface offset** (`pieces.py`, mode `offset`). Each player carries a surface offset beside
Stage 1's overall rating:
* it starts at 0;
* it moves only on that surface, by the surprise of the combined forecast;
* it has its own K, tuned on 2013–2018.

The offset Elo is unbiased with no evidence and weighs evidence through its K. Without the odds it beats the fixed blend
(`evidence_elo_only.csv`, `evidence_beside_offset.csv`):

| | Men | Women |
|---|---|---|
| Check years 2019–2021, main tour | **+4.50 [+2.06, +6.94], better** | +1.81 [−0.99, +4.61], tie |
| Check years 2019–2021, all evaluation levels | **+1.57 [+0.31, +2.83], better** | +1.44 [−0.27, +3.16], tie |
| Forward-chained 2016–2021, main tour | **+2.16 [+0.58, +3.73], better** | **+1.44 [+0.10, +2.77], better** |
| The same, 2016–2018 only | +0.54 [−1.53, +2.61], tie | +1.12, tie |
| The same, 2019–2021 only | **+4.17 [+1.82, +6.52], better** | +1.85, tie |
| Against a surface-blind offset (a control from the audit) | **+6.44 [+3.99, +8.89], better** | **+4.61 [+3.21, +6.01], better** |

* The control shows that the gain is surface structure, not a second, general correction of the overall rating.
* The offset is also a systematic shift. For players with more than 160 matches on a surface it averages +48 to +77 Elo
  points on every surface: experienced players beat newcomers whom overall Elo overrates. So it partly mirrors the
  inexperience penalty.
* Given the odds it adds nothing: −0.03 (men) and +0.01 (women), both ties.

**The final representation** ([preregistration.md](preregistration.md)). Columns are in `arms.py`.

| Arm | What changes from the best model's 54 inputs | Columns |
|---|---|---|
| `base` | Nothing. Checked value for value against the leak-proof upload | 54 |
| **`primary`** | `elo_logit` and `surface_first` out. In: overall Elo, the surface offset as its own piece, and both players' season surface matches and days since their last surface match | 58 |
| `literal` | The suggestion as written: overall Elo, the 1500-started surface-only rating, and both players' career surface matches, season surface matches, days since the last surface match and last season's surface form | 62 |
| `elo_only` / `switch_only` | Primary's Elo change alone / primary's switch change alone | 55 / 57 |

Per-player values go in as (A, B) pairs that are exchanged when the two players swap. "Both new" and "one new" therefore
stay distinct, which an A − B difference cannot do.

**What the audit changed.** The audit's full findings and my response are in [audit.md](audit.md) and
[audit_review.md](audit_review.md).
* `primary` dropped career counts and last season's form: they were null or harmful beside the offset in every
  design-year fit.
* Matches with a player whose first recorded match falls in the current season are left out. This takes out the 2026
  WTA identity split: 73 test matches whose players re-appear under new IDs with no history.
* The decision rule now reports the minimum detectable effect (MDE).
* A lost seed can no longer drop a season silently.
* Stronger leak probes:
  * Stage 1's date-and-round probe on every new Elo pass moved 0 of 3.2 million protected match-rows;
  * deleting every later match moved nothing.
* The text of the strategy was corrected.

## 4. The test

**Model and settings.** TabPFN-3.5 with thinking off (`v3.5_default`; served as `tabpfn-v3.5-20260909`, standard
mode), 8 estimators, softmax temperature 0.9. These are the best model's settings without thinking.

**Walk-forward.** Each season Y in 2022–2026:
* trains on the main-tour matches with odds of 2013 to Y − 1;
* is predicted as stored and with A and B swapped, and the two orientations are averaged.

The 2022 fold's training set is exactly the best model's 39,918 matches.

**Seeds.** Three seeds per arm, averaged. In the pilot, base's seeds 0 and 1 differed by up to 3.5 points of
probability on a match (0.4 on average).

**Population.** 23,727 test matches: men 12,341, women 11,386. The 92 matches with a player in his or her first
recorded season are left out.

**Pilot (2019–2021, design years, seed-matched).** The pilot was read only to fix the MDE, not to change the arms.
* Primary against base: +0.38 [−0.02, +0.79], a tie. Men +0.60 [+0.08, +1.12], better; women +0.15, a tie.
* Literal: +0.28 [−0.03, +0.59], a tie.
* From it, the MDE at 80% power was fixed before any confirmation call: **0.40 mLL for both tours together** and
  0.51–0.52 per tour.

## 5. Results

### 5.1 Every arm against the best model's inputs

Positive = the arm is better than base; 2022–2026, three seeds (`results_confirm.csv`).

| Arm | Both tours | Men | Women | Seasons positive (both tours) |
|---|---|---|---|---|
| **primary** (pre-registered endpoint) | **−0.01 [−0.24, +0.21], tie** | +0.14 [−0.19, +0.47], tie | −0.18 [−0.51, +0.15], tie | 2 of 5 |
| literal (the suggestion as written) | −0.08 [−0.26, +0.10], tie | +0.05 [−0.19, +0.29], tie | −0.22 [−0.46, +0.01], tie | 2 of 5 |
| elo_only | +0.03 [−0.17, +0.23], tie | +0.20 [−0.08, +0.48], tie | −0.15 [−0.47, +0.17], tie | 2 of 5 |
| switch_only | +0.01 [−0.13, +0.14], tie | +0.12 [−0.06, +0.30], tie | −0.12 [−0.32, +0.08], tie | 3 of 5 |

* **The pre-registered reading is a tie at the expected effect size.** Primary's interval (±0.22) is narrower than the
  MDE of 0.40.
* **Observed.** Every arm leans slightly positive for men (+0.05 to +0.20, positive in 3–4 of 5 seasons) and slightly
  negative for women (−0.12 to −0.22). The arms share most of their inputs, so these are not four independent signs.

### 5.2 By season (seasons as samples)

Primary against base, positive = primary better:

| Tour | 2022 | 2023 | 2024 | 2025 | 2026 | Mean [t interval, 4 df] |
|---|---|---|---|---|---|---|
| Both | −0.17 | −0.01 | −0.36 | +0.19 | +0.44 | +0.02 [−0.37, +0.40], tie |
| Men | −0.20 | +0.53 | +0.16 | +0.08 | +0.14 | +0.14 [−0.18, +0.47], tie |
| Women | −0.14 | −0.60 | −0.93 | +0.31 | +0.77 | −0.12 [−0.97, +0.73], tie |

Women's 2024 is −0.93 [−1.63, −0.24], worse. It is one of 15 season-by-tour cells, so one such cell is expected by
chance.

### 5.3 Where the idea was meant to help

Primary against base, both tours, 2022–2026. Grass has only 10 four-week blocks, so it is directional; the
calendar-week intervals agree throughout.

| Subset | Matches | Gain |
|---|---|---|
| Early surface season (either player < 3 matches on the surface this season) | 5,527 | −0.23 [−0.71, +0.25], tie |
| Both players new to the surface this season | 2,107 | +0.42 [−0.24, +1.08], tie |
| The rest of the season | 18,200 | +0.05 [−0.19, +0.30], tie |
| Grass | 3,034 | −0.17 [−1.10, +0.76], tie |

Across 4 arms × 2 tours × 4 subsets, one cell excludes zero: switch_only on men's grass, +0.64 [+0.05, +1.23], better.
About two such cells are expected by chance.

### 5.4 Against the closing odds

The odds are recalibrated per tour on each fold's training matches. Positive = the model is better than the price.

| Forecast | Both tours | Men | Women |
|---|---|---|---|
| TabPFN-3.5-Thinking, the current best model (one fit on 2013–2021) | **+1.22 [+0.63, +1.81], better** | **+1.52 [+0.77, +2.28], better** | **+0.89 [+0.07, +1.70], better** |
| Plus, base | +0.70 [−0.13, +1.52], tie | +0.92 [−0.24, +2.09], tie | +0.45 [−0.63, +1.53], tie |
| Plus, primary | +0.68 [−0.12, +1.49], tie | +1.06 [−0.08, +2.21], tie | +0.27 [−0.71, +1.25], tie |
| Plus, the other arms | +0.62 to +0.73, ties | +0.97 to +1.12, ties | +0.23 to +0.33, ties |

Plus against Thinking directly, as first scored (raw Plus):
* **2022, identical training matches and inputs:** −0.56 [−1.49, +0.38], a tie.
* **2022–2026:** −0.52 [−1.05, 0.00], Thinking ahead at the edge.

**Correction: recalibrated, Plus is level with Thinking** (`recalibrated.py` → `recalibrated.csv`). This is a post-hoc
sensitivity, prompted the same day by the [surface-IOS study's](../surface_ios/README.md) side finding.
* **The method.** Each arm gets one slope per tour on its log-odds, fitted on its own walk-forward 2019–2021 pilot
  forecasts and applied to 2022–2026:
  * base: men 0.885, women 0.96;
  * primary and literal: the same to three decimals;
  * `elo_only` and `switch_only` have no pilot forecasts and take base's slope.

| 2022–2026, positive = the second-named better | Both tours | Men | Women |
|---|---|---|---|
| Raw base → recalibrated base | **+0.65 [+0.18, +1.11], better** | +0.70 [−0.12, +1.52], tie | **+0.59 [+0.32, +0.86], better** |
| Thinking → recalibrated base | +0.12 [−0.24, +0.49], tie | +0.09, tie | +0.16, tie |
| Closing price → recalibrated base | **+1.34 [+0.72, +1.96], better** | **+1.62 [+0.81, +2.43], better** | **+1.04 [+0.12, +1.96], better** |
| Closing price → Thinking | **+1.22 [+0.63, +1.81], better** | **+1.52 [+0.77, +2.28], better** | **+0.89 [+0.07, +1.70], better** |
| Recalibrated base → recalibrated primary | −0.05 [−0.26, +0.16], tie | +0.10, tie | −0.21 [−0.52, +0.10], tie |
| Recalibrated base → recalibrated literal | −0.07 [−0.24, +0.10], tie | +0.12, tie | **−0.27 [−0.50, −0.05], worse** |
| Recalibrated base → recalibrated elo_only / switch_only | −0.05 / −0.00, ties | | |

* The base and primary forecasts here are the three-seed means; the slopes come from fewer seeds (two for base, one
  for primary and literal).
* The intervals cover the sampling of matches, not the seeds' own variance.

### 5.5 Without the odds: is the information there?

Diagnostic, one seed; positive = primary better (`results_diagnostic.csv`).

| | Both tours | Men | Women |
|---|---|---|---|
| primary_noodds against base_noodds | **+1.36 [+0.43, +2.29], better** | **+2.74 [+1.23, +4.25], better** | −0.14 [−1.28, +1.00], tie |
| Seasons positive | 5 of 5 | 5 of 5 | 3 of 5 |
| Both no-odds models against the recalibrated odds | −8.28 (base) and −6.92 (primary), worse | | |

**The pre-registered reading** (better without the odds, a tie with them): **the information is real and priced.**

### 5.6 Noise and robustness

* **Seed noise.** Single base seeds differ by up to 0.19 mLL: seed 2 against seed 0 is −0.19 [−0.34, −0.03]. The paired
  intervals cover the sampling of matches, not the fit's own noise. So single-fit differences of about 0.2 mLL between
  TabPFN runs are not evidence. That is why the confirmation averages three seeds.
* **All test matches, the 92 left-out matches included:** primary −0.01 [−0.23, +0.22], unchanged.
* **Billing.**
  * Every fit billed 0 tokens. The sequential pilot measured it cleanly: tokens were read before the fit, between fit
    and prediction, and after.
  * Every prediction billed its quote.
  * Per-job token deltas in `run_confirm.jsonl` and `run_diagnostic.jsonl` mix the two stages, which ran at the same
    time. The study's total is the account delta.

### 5.7 Exploratory: where the closing market is less settled

Added after the confirmation, on the owner's question whether the stronger predictor should help when the odds drift.
It is not pre-registered. It uses only the saved predictions (`unsettled.py` → `unsettled_market.csv`). Primary against
base, positive = primary better:

| Bookmaker price dispersion at the close (best price against the average) | Both tours | Men | Women |
|---|---|---|---|
| Least dispersed third | −0.09 [−0.36, +0.18], tie | −0.24, tie | +0.09, tie |
| Middle third | −0.35 [−0.78, +0.08], tie | −0.20, tie | −0.51, tie |
| **Most dispersed third (least settled)** | **+0.40 [+0.02, +0.78], better** | **+0.88 [+0.29, +1.48], better** | −0.12, tie |

* The Pinnacle-against-average gap, a second measure of how settled the price is, points the same way but more weakly:
  in its highest third, +0.18 [−0.30, +0.65], a tie.
* By level: 1000s +0.40 [−0.03, +0.83], a tie; 500s −0.53 [−1.00, −0.06], worse; Slams and 250s ties.
* About 60 cells were examined, so a few intervals that clear zero are expected by chance. The dispersion thirds are
  not monotone: the middle third is the lowest.

*Inferred.* This is a hint, consistent with the idea that the representation matters where the price has not settled.
It is not evidence.

### 5.8 The early-price test: does it know what the price 24 hours out does not?

Run on the owner's request of 6 October 2026, to the plan in [early_price_plan.md](early_price_plan.md), which was
fixed before any forecast was compared with a price or a result. No paid call was made: 24 fits ran on the free local
TabPFN-3.5 on this machine's GPU. Their forecasts agree with the paid API's for the same arms and seeds: log-odds
correlation 0.9998, mean gap 0.3 points of probability, no more than between two seeds.

**The sample.** 2025–2026 test matches linked to their Polymarket market, with the price 24 hours and 30 minutes
before the listed start (`early_price_frame.py`). The clean population has **1,067 matches** (582 men, 485 women). Both
players are playing their first match of the event, and their previous match surely ended at least 3 days before, so
every input existed 24 hours out. 2,648 matches with both prices, later rounds included, are a sensitivity.

**Test 1, the move.** The move is M = logit of the price 30 minutes out − logit of the price 24 hours out, in P(A). A
positive slope means the price moves toward that forecast. Both tours, clean population (`early_price_results.csv`,
`early_price_checks*.csv`):

| Specification | Slope on Δ, the new representation's change [95%] | Reading |
|---|---|---|
| Pre-registered: M on D and Δ. D = old no-odds forecast − the 24-hour price | +0.332 [+0.091, +0.574] | positive, **but see below** |
| Δ alone, free of any price (post hoc) | +0.066 [−0.046, +0.179] | tie |
| M on the old forecast b and Δ, both free of any price (post hoc) | +0.139 [+0.028, +0.251]; men +0.080 (tie), women +0.236 [+0.084, +0.388] | positive, women only |

* **Observed. The pre-registered specification is flawed.**
  * Its control D contains the 24-hour price, whose own noise reverts by the close. That part of M is predicted by D
    mechanically.
  * Δ correlates −0.28 with D: where the old model disagrees with the early price, the new one sits nearer the price.
  * Partialling D out therefore lends Δ part of that mechanical reversion.
  * Because Δ never sees a price, its covariance with the move equals its covariance with what the early price lacks.
    So the price-free versions are the valid ones. I should have specified one before the run.
* **Observed. The size, even at its largest valid estimate (+0.139), is small.** A one-standard-deviation change in Δ
  (0.175 log-odds) moves the price by about 0.6 points of probability.
* **The move happens before match day.** Pre-registered specification: 24 hours → 6 hours +0.306 [+0.055, +0.557];
  6 hours → 30 minutes +0.060 [−0.032, +0.153], a tie.
* **Observed. The old sporting model itself predicts the move**, price-free: +0.099 [+0.040, +0.159], and men and women
  alike. The price 24 hours out lags the sporting model as a whole.

**Tests 2 and 3, the money (outcomes).** Clean population, both tours; positive = the second-named forecast better:

| Comparison | Given the 24-hour price | Given the 30-minute price |
|---|---|---|
| Stacks: price + new no-odds forecast against price + old (cross-fitted) | +1.11 [−1.19, +3.41], tie | +0.64 [−0.51, +1.80], tie |
| Deployment: the new representation against the old, both fed the price | +1.11 [−0.21, +2.42], tie | +1.09 [−0.18, +2.36], tie |
| Deployment, new representation, against the price recalibrated | **+2.85 [+0.14, +5.57], better** (men +5.51 [+0.99, +10.02]) | +0.79 [−4.67, +6.24], tie |
| Deployment, old representation, against the price recalibrated | +1.75 [−0.91, +4.41], tie | −0.31 [−6.03, +5.42], tie |

* On all 2,648 matches the stack gain is +1.09 [+0.08, +2.11] (better) at 24 hours against +0.24 (tie) at the close.
  But that population's later rounds carry the timing caveat.
* Against the raw 24-hour price rather than the recalibrated one, the model is +2.12 [−4.54, +8.78], a tie.

**Inferred: not proven.**
* There are signs, in specifications chosen after the fact and mostly for women, that the new representation knows a
  little of what the 24-hour price misses. The effect is at most about half a point of probability per standard
  deviation.
* The deployment edge over the old representation is the same at 24 hours as at the close. An edge built on what the
  early price lacks would shrink by the close, and this one does not.
* With 1,067 clean matches, the test could settle only large effects.

**The firmer lead is broader.** The 24-hour Polymarket price moves toward the sporting model as a whole by the close.
The with-odds model fed that price beats it, recalibrated, by about 3 mLL, while at the close it ties. If there is
money at bet time, it is more likely in betting earlier with the model than in this Elo representation. Both readings
are on one Polymarket year and are exploratory.

## 6. What it means

**Why "better on its own" is not "better next to the price".** A model that holds the odds gains only from information
the odds do not already contain.
* The new representation is better than the 30% blend as a standalone predictor: men +2.74 without the odds.
* What makes it better is surface experience, layoffs and specialisation. The closing price already prices all of
  that, so next to the close the old and new Elo carry the same information.
* That is why the test is a tie rather than a loss: the new inputs **do not hurt**, they are redundant with the price.
* The same reasoning says where they should help: wherever the price used has not yet absorbed that information. Early
  prices, a thin market or missing odds are all such cases.

**Inferred.**

* **The representation was the suspected weak point, and the evidence says it is not.** The fixed blend, the A − B flag
  and the missing layoff were real flaws in Elo-only terms. Fixing them helps a model that does not see the price (men
  +2.7 mLL). But the closing price already holds this information: the inexperience penalty, the layoff penalty and
  surface specialisation. A model that holds the price gains nothing from re-deriving it. This is the same pattern as
  surface Elo in the [market-anchoring study](../market_anchoring/README.md) and TrueSkill Through Time in the
  [rating systems study](../rating_systems/README.md).
* **This is not a verdict that the closing line cannot be beaten** (the owner's premise). It says this information is not
  where the edge is. The process suspects, in order:
  1. **The price used is the close.** Surface switches are news that the market absorbs before the close. Against
     prices days or hours before the match (the Polymarket price paths), the same inputs might matter. A no-odds gain of
     2.7 mLL for men is the size of information an early price could lack.
  2. **The tour level.** The main tour is the most efficient market. Challenger and WTA 125 matches, where the
     Polymarket study found the most accounts beating the close, have thinner prices and more surface switchers.
  3. **The model.** This is now an unlikely suspect. Recalibrated Plus is level with Thinking and beats the price
     (§5.4). Even recalibrated, primary's gain is bounded at about +0.2 mLL.

## 7. Suggestions

1. **Against the close, switching to `primary` is a free choice, so decide it by robustness.** (Revised after the
   owner's question; the first version said to keep the inputs as they are.)
   * With the closing price it neither helps nor hurts: −0.01 [−0.24, +0.21], a tie.
   * It is the stronger predictor whenever the price is less informative.
   * If the model will be fed prices taken before the close, prefer `primary`. The exploratory hint in §5.7 points the
     same way.
   * Do not expect it to raise the edge over the close, and do not spend a paid thinking refit on it alone.
   * For women it never helped, with or without the odds. In a model pooled across tours that is a reason for caution,
     not against.
2. **Keep the surface offset Elo and the season and layoff inputs for market-free uses.** They beat the 30% blend and
   the flag without the odds: +2.7 mLL for men in TabPFN, and +2.2 Elo-only. Examples are building a price where the
   market is thin, or a forecast made before odds exist. If TrueSkill Through Time replaces Elo, give it the same
   surface-offset structure.
3. **Run the early-price question on more data.** §5.8 ran it on Polymarket's 2025–2026 prices and it is not settled:
   1,067 clean matches can only see large effects. Three ways to more data:
   * Betfair historical data gives early prices for many seasons. It needs the owner's account; the adapter
     `src/ingest/betfair_history.py` is ready.
   * A timing rule that admits later rounds when the previous round's listed start was more than a day earlier roughly
     doubles the sample.
   * Waiting: the sample grows by about 150 clean matches a month.

   Make the move test price-free from the start: regress the move on the forecasts, never on a difference that contains
   the early price.
4. **Study betting earlier with the model as a whole.** In §5.8 the 24-hour price drifts toward the sporting model by
   the close, and the model fed that price beats it, recalibrated, by about 3 mLL. That lead is broader, and probably
   worth more, than the Elo representation.
5. **Recalibrate any non-thinking TabPFN-3.5 forecast per tour on earlier seasons before comparing anything.** Plus
   and the local model are over-confident; one slope per tour on their own 2019–2021 forecasts is worth +0.65 mLL here
   and brings them level with Thinking (§5.4). The deployment forecasts of the early-price test (§5.8) were not
   recalibrated. Their edge over the early price may be understated.
6. **For further TabPFN screening, use the free local TabPFN-3.5 on this machine's GPU.** It was set up on 6 Oct 2026.
   The owner has raised concern about paid API costs (relayed by another session; no rule is recorded yet), so ask
   before any paid call. Use at least three seeds: single-fit differences of 0.2 mLL are within the fit noise.
7. **Repair the 2026 WTA identity split upstream.** From June 2026, WTA players re-appear under new IDs with no history.
   That resets Elo, counts and profiles for every model, the base included.

## 8. Limits

* **One model, one design.** Only the non-thinking model was tested, in a walk-forward from 2013, at the best model's
  settings.
* **2026 is partial and not like the other seasons.** It runs from January to July and has more clay and grass than a
  full season.
* **The base inputs were chosen by earlier studies after their 2022–2026 results were seen.** `primary` and `literal`
  drop two of them, which slightly favours `base`.
* **The ablations have little power.** They cannot attribute the small tilts between the Elo and switch changes.
* **The secondary results are unadjusted.** That covers the arms, tours, seasons and subsets. Read them as exploratory.
* **The odds are closing prices.** They are tennis-data's average of archived quotes, not executable prices. A log-loss
  gain is not a betting return.
* **History starts in 2010.** Every player starts at 1500 then. Counts and offsets are truncated for players active
  before 2010; the 3-year layoff cap makes the layoff exact from 2013 on.
* **The repair's alias IDs.** The feature-alpha repair's alias identities still touch about 1.8% of test matches. Most
  are single rows and affect every arm alike.

## 9. Files and run

| What | Where |
|---|---|
| The pieces: Elo variants (Stage 1 reproduced exactly, anchored, offset, surface-blind control), surface-switch quantities, leak probes | `src/eda/surface_elo_pieces/pieces.py` → `data/studies/surface_elo_pieces/pieces.parquet`, `pieces_meta.json` |
| Design-year evidence (A–G) | `evidence.py` → `evidence_*.csv`, `evidence.json`, `evidence.log` |
| Arms, frames and jobs | `arms.py`, `build_frames.py` → `frame.parquet`, `frame_manifest.json`, `jobs.json` |
| Paid calls (env `tennis-tabpfn`) and their once-per-job guard | `dispatch.py`, `guard.py` → `tabpfn/<job>/` receipts, `quotes_*.json`, `run_*.jsonl`, `run_*.log` |
| Scoring | `score.py` → `results_{pilot,confirm,diagnostic}.{json,csv}`, `predictions_*.parquet`, `mde.json` |
| Exploratory split by how settled the closing market is (not pre-registered) | `unsettled.py` → `unsettled_market.csv` |
| Recalibration sensitivity (post hoc): one slope per arm and tour from the 2019–2021 pilot | `recalibrated.py` → `recalibrated.csv`, `recalibrated.json` |
| The early-price test: sample, local GPU fits, scores, post-hoc checks ([plan](early_price_plan.md)) | `early_price_frame.py`, `early_price_local.py` (env `tennis-tabpfn-local`), `early_price_score.py`, `early_price_checks.py` → `early_price_frame.parquet`, `local/*.npz`, `early_price_results.{json,csv}`, `early_price_checks*.csv`, `early_price_counts.json` |
| Tests | `test/surface_elo_pieces/` (11 pass) → `tests.xml` |
| The audit's scratch scripts | `data/studies/surface_elo_pieces/audit_scratch/` (listed in [audit.md](audit.md) §5) |

Run from the repository root:

```bash
./python.sh src/eda/surface_elo_pieces/pieces.py        # about 7 minutes
./python.sh src/eda/surface_elo_pieces/evidence.py
./python.sh src/eda/surface_elo_pieces/build_frames.py
./python_tabpfn.sh src/eda/surface_elo_pieces/dispatch.py --quote --stage confirm             # free
./python_tabpfn.sh src/eda/surface_elo_pieces/dispatch.py --run --stage confirm --spend-tokens # re-uses saved predictions
./python.sh src/eda/surface_elo_pieces/score.py --stage confirm
./python.sh -m pytest test/surface_elo_pieces -p no:cacheprovider
```

Every job's predictions are saved. Re-running `dispatch.py --run` re-uses them and sends nothing. The API key in
sessions started from this VS Code window may be stale. Ask the owner before any new paid call: the owner has raised
concern about API costs (relayed 6 Oct 2026), though no rule is recorded.
