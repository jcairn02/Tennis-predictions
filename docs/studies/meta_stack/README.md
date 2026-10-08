# A meta-model over a market-free TabPFN and the closing line

6 October 2026 · Research evidence, not a production, model or betting decision.

**The owner's request (6 Oct 2026).** The current best model, the local TabPFN-3.5 (non-thinking) in expanding windows, takes the closing line as one of its 54 inputs. Test instead a logistic meta-model over three inputs: the same TabPFN without the closing line, the closing line, and the difference between the two. Decide how much data goes to the model and how much to the meta-learner, with mathematical justification. Then compare with the current best.

**Keys.** Results are in milli-log-loss per match. **Positive = the second-named forecast has the lower log loss (better)**. A 95% interval that spans 0 is a **tie**. **Observed** = computed here; **inferred** = reasoning; **proposal** = not decided.

## In short

* **Observed. The meta-model is worse than the current best.** The primary test, fixed before the test seasons were scored: both tours, 2022–2026, 23,819 matches, the current best against the meta-model:
  * both tours **−1.15 [−1.76, −0.55]**: the current best is better;
  * men −1.45 [−2.14, −0.76]: the current best is better;
  * women −0.83 [−1.73, +0.06]: a tie leaning the same way.
  * The meta-model's point estimate trails in all five seasons (clearly in 2023 and 2024) and in both halves (2022–2024 −1.12, 2025–2026 −1.21, both clearly).
  * The gap was predicted before the test (about −1).
* **Observed. Against the close the meta-model is a tie: +0.14 [−0.07, +0.36].** It keeps about a tenth of the current best's +1.30 [+0.65, +1.94]. It learns weights of 0.94–1.01 on the closing line and 0.07–0.14 on the no-odds model.
* **Observed. The difference as a third input adds nothing in any form.**
  * On the log-odds scale it is an exact combination of the other two inputs. The literal three-input model makes the same forecasts as the two-input one (0.000 ± 0.014).
  * On the probability scale: +0.01 [−0.11, +0.13], a tie.
  * As a disagreement-size term: −0.03 [−0.09, +0.02], a tie.
* **Observed and inferred. How much data for the model and how much for the meta-learner: all of it, for both.**
  * Cross-fitting does this. The model trains on every season before the one it forecasts; the meta-learner is fitted on the model's genuine out-of-sample forecasts of every earlier season (from 2014).
  * Two weights cost about 0.4/W milli-log-loss for W seasons of meta-data (the tr(J⁻¹K)/(2n) result; measured tr(J⁻¹K) = 1.94–1.95).
  * Seasons withheld from the model cost it first-order, and the weights do not drift in a way that favours short windows. So longer is better: an expected excess of about 0.2 milli, against about 0.4 for the best hold-out split (about three seasons for the meta-learner). The prequential check on 2019–2021 agrees.
* **Observed. The shortfall is not a data-split problem.** With weights fitted on the test seasons themselves, a ceiling no split can reach, the meta-model still trails the honest current best:
  * −0.77 [−1.44, −0.10] with weights per tour and season;
  * −1.11 [−1.70, −0.51] with weights per tour.
* **Observed. The no-odds model knows nothing the current best does not.**
  * Added beside the current best, its weight is −0.04 to +0.03 and the gain −0.03 [−0.08, +0.02], a tie.
  * Giving the close its own weight beside the current best gains nothing either: −0.02 [−0.13, +0.10].
* **Inferred. Why.**
  * The meta-model can use the no-odds model only through one weight on its whole forecast. That forecast's log-odds correlate 0.95 with the close's (90% of the variance shared), and what remains mixes what the price lacks with the model's own errors.
  * With the odds as an input, TabPFN can learn which inputs move the price, and in which matches. That is where its edge is.
  * Recommendation (proposal): keep the closing line inside the model.

## The third variable: the log-odds difference drops out (inferred, then checked)

Write z_C for the closing line's log-odds that player A wins and z_M for the no-odds model's. On the log-odds scale the difference is z_M − z_C. That is an exact linear combination of the other two inputs, so a logistic meta-model cannot use it:

b_C·z_C + b_M·z_M + b_D·(z_M − z_C) = (b_C − b_D)·z_C + (b_M + b_D)·z_M

The three-input model makes exactly the same forecasts as the two-input one, here called **S2**. Its three weights are not identified; only these two combinations are. The literal three-column version (S3lit) is fitted anyway, to show this on the data.

The difference can add something only if it enters non-linearly. Two forms are tested:

* **S3p** uses the difference on the probability scale, p_M − p_C.
* **S3q** lets the weight on the disagreement change with its size, through the signed square d·|d|, where d = z_M − z_C.

The log of the probability ratio, log(p_M / p_C), is not a fourth option. Side A is random, so every input must change sign when A and B are swapped. The part of log(p_M / p_C) that does so is (z_M − z_C)/2, collinear again.

There is no intercept: side A is random, so its true value is zero, and fitting it would only add noise.

## The plan, fixed before the design and test results

Written while the extra local fits ran, before `design.py` or `score.py` had produced any number.

* **The current best** (the comparator): local TabPFN-3.5 on the closing odds plus 53 inputs, four seeds, expanding windows from 2013. One slope per tour on its log-odds, refitted each season on all out-of-sample seasons from 2019 to the season before. Rebuilt here; it reproduces the surface-IOS study's figure exactly: **+1.30 [+0.65, +1.94]** over the recalibrated closing price, both tours, 2022–2026 (men +1.57 [+0.82, +2.33], women +1.00 [−0.01, +2.00]).
* **The meta-model (S2).** Per tour, a logistic regression without an intercept on the closing line's log-odds and the no-odds TabPFN's log-odds. The no-odds TabPFN is the same model, inputs, windows and seeds without the odds column. The difference enters as explained in the next section.
* **The meta-learner's data.** Chosen by the rule below from 2014–2021 only. No 2022–2026 match is read before the choice.
  * Take the window W, the number of earlier out-of-sample seasons the meta-learner is fitted on, that minimises the expected excess log loss: estimation plus drift.
  * Use the drift model the data support: a random walk if the season-to-season deviations of the weights are positively correlated and the walk's variance is positive; otherwise independent season effects.
  * If the hold-out design's best expected excess is lower, use the hold-out design instead.
  * W is capped at the seasons available (2014 onwards). The prequential check on 2019–2021 is reported, and overrides the rule only if it contradicts it beyond its interval.
* **Primary endpoint.** S2 against the current best, both tours, 2022–2026. Paired 95% interval over four-week blocks, with the seeds' variance added (the surface-IOS study's method). Better, worse or tie by the interval.
* **Secondary, all reported.**
  * Each tour, each season, 2022–2024 and 2025–2026.
  * S2 and the current best against the recalibrated close.
  * The other forms of the difference: the probability-scale difference (S3p), the signed square of the log-odds difference (S3q), and the literal three-column model (S3lit, which must equal S2).
  * Two diagnostics of the current best: E1 adds the no-odds forecast to it; E2 gives the closing line its own weight beside it.
  * Sensitivities: the current best on S2's window; S2 on the current best's window.
* **Expectation, stated before the test.** S2 should trail the current best by about 1 milli-log-loss.
  * The 2019–2021 validation seasons: fitted in-sample, which flatters it, the no-odds model's weight beside the close is −0.16 to +0.26, with a standard error of 0.11–0.18 per season.
  * Earlier studies point the same way. In the TabPFN-thinking design's dry run with linear models, stacking recovered +0.10 of the +0.79 that the same inputs gave used directly. In the market-anchoring study, stacking a 36-input sporting forecast on the price scored −0.14 [−0.30, +0.02].

## How much data for the model, how much for the meta-learner

### The argument (inferred: standard large-sample results)

Per tour the meta-model has k = 2 weights, b = (b_C, b_M). Three things can make its log loss on a new season worse than the best weights for that season would give.

**1. Estimating the weights.** Fitted by maximum likelihood on n matches, the weights miss the best ones by a random error with covariance J⁻¹KJ⁻¹/n. Here J is the per-match information matrix and K the per-match covariance of the score. The log loss is quadratic near its minimum, so on new matches the expected cost is

½·tr(J · J⁻¹KJ⁻¹/n) = **tr(J⁻¹K) / (2n)** nats per match.

This is Takeuchi's correction (TIC); when the model is right, K = J and it is k/(2n), the term behind AIC. A test in `test/meta_stack/` checks it by simulation. For k = 2 and one tour-season (about 2,300–2,400 matches) it is about 0.4 milli-log-loss. With W seasons it is about 0.4/W.

**2. Drift.** The best weights move from season to season, as the market, the tours and the model change. A meta-learner fitted on the W seasons before the target learns their average, which misses the target season's. The expected cost is ½·tr(J·S_W), where S_W is the covariance of that miss:

* **Independent season effects** (covariance τ²): S_W = τ²(1 + 1/W). This favours the longest window.
* **A random walk** (step covariance Q): S_W = Q(W + 1)(2W + 1)/(6W). This has an optimum at W* = √(3a/c + ½), with a = tr(J⁻¹K)/(2n) and c = ½·tr(JQ).

**3. What the model loses.** A textbook hold-out split fits the model on the older seasons and the meta-learner on the model's forecasts of the newer W seasons. The model that forecasts the target season has then never seen those W seasons, the most recent ones. The cost is

Δ(W) = L\*(model trained to Y−1−W) − L\*(model trained to Y−1),

where L\* is the log loss under each model's best weights. It is first order in the data withheld. If each withheld season costs about d, the split's total a/W + d·W is smallest at **W\* = √(a/d)**, where it costs 2√(ad).

**Cross-fitting** (walk-forward stacking) avoids that cost:

* The model for each season is trained on every season before it, exactly as in the current best.
* The meta-learner is fitted on the forecasts each earlier window made for its own next season. Those forecasts are genuinely out of sample.
* Its only cost is that those forecasts came from models trained on less data, so the weights it learns suit slightly weaker models. That is part of the drift term, and second order in the weights.

So, per match:

* cross-fit(W) = tr(J⁻¹K)/(2nW) + drift(W)
* hold-out(W) = tr(J⁻¹K)/(2nW) + drift(W) + Δ(W)

**What the formulas say before measuring.** The model should be trained on every season before the one it forecasts. The meta-learner should be fitted on out-of-sample forecasts of as many earlier seasons as drift allows. The measurements below set that number.

### The inputs, measured on 2014–2021 (observed; `design.py` → `design.json`)

Every number here comes from out-of-sample forecasts of 2014–2021. No 2022–2026 match was read. This study added the seasons 2014–2018 (both models, four seeds) and the hold-out fits; where they repeat a surface-IOS window they agree with it to within 0.004 milli-log-loss (`reproducibility.json`).

| Measured | Men | Women |
|---|---|---|
| tr(J⁻¹K), independent matches (four-week clusters) | 1.95 (1.82) | 1.94 (2.13) |
| Matches per season (mean) | 2,389 | 2,271 |
| a = estimation cost of one season of meta-data | 0.41 milli | 0.43 milli |
| Weights per season: on the close, b_C / on the no-odds model, b_M | 0.68 to 1.30 / −0.16 to +0.29 | 0.86 to 1.16 / −0.02 to +0.22 |
| Season-to-season variation beyond sampling noise, ½·tr(Jτ²) | 0.24 milli | none |
| Lag-1 correlation of the weights' season deviations (b_C, b_M) | −0.39, −0.47 | −0.79, −0.56 |
| Trend of b_M with the size of the window that made the forecasts (mismatch) | +0.01 (SE 0.07) per log-row | +0.02 (SE 0.07) |
| Δ(W): the hold-out model's lost seasons, W = 1, 2, 3 | 0.06, 0.15, 0.14 milli | 0.07, 0.09, 0.10 milli |
| d, cost per withheld season | 0.056 milli | 0.039 milli |
| A hold-out split's best W\* = √(a/d) and its cost 2√(ad) | 2.7 seasons, 0.30 milli | 3.3 seasons, 0.26 milli |

What the rows say:

* **The meta-model is close to right.** tr(J⁻¹K) ≈ k = 2, so the k/(2n) formula applies.
* **No random walk.** The weights' season deviations alternate in sign rather than persist. For the women they vary no more than sampling noise; for the men, slightly more.
* **No mismatch.** The weights do not trend with the size of the window that made the forecasts (one to eight seasons of training), so forecasts from the early, smaller windows teach the meta-learner the same weights.
* **Withheld seasons cost the stack little.** The no-odds model on its own loses 1.27, 2.45 and 3.72 milli when its last 1, 2 or 3 seasons are withheld (both tours, 2019–2021; all clearly below zero). With the closing line beside it, the loss falls to 0.06, 0.12 and 0.12. The close already carries most of what the newest seasons would teach the model.

**Expected excess log loss per match** (milli, both tours, independent season effects; lower = better):

| Meta-learner's seasons W | 1 | 2 | 3 | 5 | 8 | 12 |
|---|---|---|---|---|---|---|
| Cross-fit | 0.66 | 0.39 | 0.30 | 0.23 | 0.19 | 0.17 |
| Hold-out | 0.73 | 0.52 | 0.42 | – | – | – |

The random-walk model would give a finite optimum instead (cross-fit 0.60 at W = 2), but the data reject it: the deviations do not persist.

**The prequential check, 2019–2021** (observed; `design_prequential.csv`). Each season is scored by a meta-learner fitted only on earlier seasons. Gain over cross-fitting on every season from 2014, positive = better:

| Design | Both tours | Men | Women |
|---|---|---|---|
| Cross-fit, last season only\* | −0.70 [−1.40, +0.01] | −1.82 [−3.24, −0.40] | +0.03 [−0.63, +0.68] |
| Cross-fit, last 2 | −0.16 [−0.54, +0.22] | −0.60 [−1.31, +0.12] | +0.31 [−0.05, +0.67] |
| Cross-fit, last 3 | −0.17 [−0.43, +0.08] | −0.52 [−0.99, −0.05] | +0.21 [−0.09, +0.50] |
| Cross-fit, last 5 | +0.07 [−0.03, +0.17] | +0.02 [−0.11, +0.16] | +0.12 [−0.01, +0.24] |
| Hold-out, W = 1\* | −0.78 [−1.50, −0.05] | −1.80 [−3.21, −0.38] | −0.12 [−0.80, +0.56] |
| Hold-out, W = 2 | −0.23 [−0.58, +0.11] | −0.63 [−1.28, +0.02] | +0.21 [−0.15, +0.56] |
| Hold-out, W = 3 | −0.27 [−0.55, +0.01] | −0.60 [−1.11, −0.08] | +0.09 [−0.19, +0.36] |

\* Without the men's 2019 season: the men's 2018 season has no odds, so a one-season window before 2019 is empty.

The formula's predictions sit inside these intervals: cross-fit last 1, 2, 3 at −0.45, −0.18, −0.09 against every season from 2014; hold-out W = 1, 2, 3 at −0.51, −0.30, −0.21.

Two side readings on the same seasons:

* S2 (cross-fit from 2014) against the closing line with one slope: +0.09 [−0.26, +0.43], a tie.
* The current best's slope on the same seasons beats S2 by +1.08 [+0.24, +1.92].

### The choice (made by the plan's rule before any 2022–2026 stack was scored)

**The model trains on every season before the one it forecasts. The meta-learner is fitted on the model's out-of-sample forecasts of every season from 2014 to the season before** (cross-fitting, `S2_WINDOW = "from2014"`).

* **Drift:** independent season effects, because the deviations do not persist, so longer is better.
* **Hold-out:** its best expected excess (0.42 at W = 3) is above cross-fitting's (0.17–0.19 at W = 8–12).
* **Prequential check:** last 5 ties every-season-from-2014 (+0.07 [−0.03, +0.17]), so it does not override the rule.
* **What that means for the test seasons:** 2022–2026 get 8–12 seasons of meta-data (the men 7–11), about 17,000–28,000 matches per tour. The expected estimation cost is 0.04–0.06 milli, the expected excess in all 0.17–0.19.

In one line for the owner's question: **give the model all the data and the meta-learner all of the model's earlier out-of-sample forecasts; neither has to give anything up.** A meta-model with two weights needs about 0.4/W milli of data cost, and a hold-out split would buy that at a first-order price in the model. If a hold-out split were used anyway, the formula puts its best size at about three seasons for the meta-learner.

## Results, 2022–2026 (observed; `score.py` → `results.csv`, `results.json`, `coefficients.csv`)

Every meta-learner is refitted for each test season, per tour, on out-of-sample forecasts of earlier seasons only. Intervals: paired, four-week blocks, with the seeds' variance added. Positive = the second-named forecast has the lower log loss (better).

**The primary comparison: the current best against the meta-model S2.**

| | Both tours | Men | Women |
|---|---|---|---|
| **2022–2026** | **−1.15 [−1.76, −0.55]**: current best better | −1.45 [−2.14, −0.76]: current best better | −0.83 [−1.73, +0.06]: tie |
| 2022 | −0.23 [−1.41, +0.95]: tie | −0.54 [−1.68, +0.59]: tie | +0.12 [−1.79, +2.03]: tie |
| 2023 | −1.43 [−2.55, −0.30]: current best better | −1.01 [−2.68, +0.66]: tie | −1.87 [−3.27, −0.48]: current best better |
| 2024 | −1.67 [−3.26, −0.08]: current best better | −1.46 [−3.14, +0.23]: tie | −1.90 [−4.38, +0.58]: tie |
| 2025 | −1.20 [−2.69, +0.28]: tie | −2.05 [−3.96, −0.15]: current best better | −0.31 [−2.21, +1.60]: tie |
| 2026 | −1.23 [−3.69, +1.24]: tie | −2.54 [−4.97, −0.12]: current best better | +0.14 [−3.57, +3.84]: tie |
| 2022–2024 | −1.12 [−1.83, −0.41]: current best better | −1.01 [−1.79, −0.23]: current best better | −1.24 [−2.32, −0.16]: current best better |
| 2025–2026 | −1.21 [−2.41, −0.02]: current best better | −2.25 [−3.61, −0.89]: current best better | −0.13 [−1.80, +1.55]: tie |

Log loss, both tours, 2022–2026 (lower = better): current best 0.58794, S2 0.58909, recalibrated close 0.58923.

**Against the closing price** (recalibrated on each window's training matches; positive = better than the price):

| Forecast | Both tours | Men | Women |
|---|---|---|---|
| Current best | +1.30 [+0.65, +1.94] | +1.57 [+0.82, +2.33] | +1.00 [−0.01, +2.01]: tie |
| S2, the meta-model | +0.14 [−0.07, +0.36]: tie | +0.12 [−0.21, +0.46]: tie | +0.17 [−0.13, +0.46]: tie |
| E1, current best + no-odds model | +1.27 [+0.62, +1.92] | +1.54 [+0.78, +2.30] | +0.98 [−0.04, +1.99]: tie |
| E2, close + current best, separate weights | +1.28 [+0.54, +2.02] | +1.62 [+0.71, +2.53] | +0.92 [−0.20, +2.04]: tie |

**The third variable** (both tours, 2022–2026):

| Comparison | Gain |
|---|---|
| S2 against S3lit (the literal three inputs) | 0.000 [−0.014, +0.014]: identical forecasts, as the algebra says |
| S2 against S3p (+ probability difference) | +0.01 [−0.11, +0.13]: tie |
| S2 against S3q (+ signed square of the disagreement) | −0.03 [−0.09, +0.02]: tie |
| Current best against S3p / S3q | −1.15 [−1.72, −0.57] / −1.19 [−1.77, −0.60]: current best better |

**What the meta-model learned** (`coefficients.csv`; per tour, refitted each test season on every out-of-sample season from 2014):

* **Weight on the close:** 0.94–1.01.
* **Weight on the no-odds model:** 0.07–0.14, standard error about 0.04.
* **What that means:** the price is kept almost as it is, nudged about a tenth of the way toward the sporting model's log-odds.
* **S3p:** its probability-difference weight is negative everywhere (−0.57 to −1.66, standard error 0.69–0.95) and offsets the larger log-odds weight it gives the model. That is the same nudge, reshaped, and it makes the same forecasts.

**Diagnostics of the current best** (both tours):

| Comparison | Gain |
|---|---|
| Current best against E1 (+ the no-odds model) | −0.03 [−0.08, +0.02]: tie. The no-odds model's weight beside the current best is −0.04 to +0.03 (SE 0.05–0.09) |
| Current best against E2 (the close given its own weight) | −0.02 [−0.13, +0.10]: tie. The close's extra weight is −0.36 to +0.07 (SE 0.19–0.34) |

**Ceiling: S2 with weights fitted on the test matches themselves** (a diagnostic, not a forecast; against the honest current best):

| Weights fitted | Both tours | Men | Women |
|---|---|---|---|
| Per tour, over 2022–2026 | −1.11 [−1.70, −0.51] | −1.41 [−2.09, −0.73] | −0.78 [−1.64, +0.08]: tie |
| Per tour and season | −0.77 [−1.44, −0.10] | −1.03 [−1.79, −0.26] | −0.49 [−1.47, +0.49]: tie |

**Sensitivities** (both tours, all ties):

| Comparison | Gain |
|---|---|
| The current best with its slope fitted from 2014 (S2's window), against the current best | +0.11 [−0.02, +0.24] |
| S2 on the current best's window (from 2019), against S2 | −0.09 [−0.21, +0.03] |
| The current best from 2014 against S2 | S2 trails by 1.27 [0.69, 1.84] |

## What it means (inferred), and what next

* **The meta-model is a restricted version of what the current best already does.**
  * Write the no-odds forecast as z_M = λ·z_C + e: its projection on the price plus a residual e. Then S2's forecast is (b_C + b_M·λ)·z_C + b_M·e.
  * Everything the sporting model knows beyond the price must come through one number, b_M, applied to e. The residual has a standard deviation of 0.36–0.38 in log-odds against about 1.0 for the price.
  * But e mixes what the price lacks with the model's own errors: the injuries, news and late information the market knows and the 53 inputs do not. One weight cannot separate them, so the meta-learner sets it to about 0.1.
  * The with-odds TabPFN sees the price and the inputs together. It can learn which inputs carry information beyond the price, in which matches, and by how much. In linear terms, the stack is that model with every input's adjustment to the price forced through a single shared direction.
  * E1 shows the asymmetry. The no-odds forecast adds nothing to the current best (−0.03), while the current best adds 1.15 to the stack.
* **Why the data split cannot rescue it.**
  * The meta-learner's estimation cost here is about 0.05 milli.
  * The ceiling with in-sample weights still trails by 0.77–1.11.
  * The no-odds model on its own does improve with data: withholding its last season costs it 1.27 milli. But beside the price it gains almost nothing from more data (0.06 per season), because the price already carries it.
* **The same answer as before, now on the best model.** The TabPFN-thinking design's dry run found that stacking recovers +0.10 of +0.79. The market-anchoring study's stack scored −0.14. Here, with the current best's own inputs and windows, the stack keeps +0.14 of +1.30.
* **The current best stays as it is.** Neither of the two cheap changes tested on it helps: adding the sporting forecast (E1) or freeing the price's weight (E2). Fitting its slope on every season from 2014 rather than from 2019 is +0.11 [−0.02, +0.24], a tie leaning positive. It is not adopted here: it was looked at on the test seasons.
* **Proposals, where the idea could still earn its keep** (not tested):
  1. **A sporting model trained beyond the odds' reach.** A market-free model does not need odds to train. It could learn from matches the current best cannot use: the men's 2018 season, qualifying, Challengers. The stack is then the natural way to combine it with a price, but its weight would have to rise well above 0.1 to matter.
  2. **An earlier price.** Against Polymarket's price 24 hours before the start, where the Elo-pieces study saw the price drift toward the sporting model, a market-free forecast may carry more that the price lacks than it does at the close. The same S2 with the early price as z_C is a cheap test once those prices are aligned with this frame.
  3. **Feature-level nudges.** If the price is to be kept outside the model, the market-anchoring study's form (the price plus ridge-penalised nudges, one per input) avoids the single-direction restriction that limits S2.

## Limitations

* **The model.** The local open checkpoint (tabpfn-v3.5-20260909), not the API's Plus or Thinking. Every fit is free and local; no paid call was made.
* **The test seasons were seen before.** 2019–2026 have been inspected by earlier studies. The current best's walk-forward slope was itself proposed after its 2022–2026 result was seen, while S2's design was chosen on 2014–2021 alone. That asymmetry favours the current best slightly, but cannot explain a gap of 1.15 with an interval of ±0.6.
* **Price and payoff.** Closing prices are archived average closes, not executable bet-time prices. A log-loss difference is not a betting return.
* **Early windows.** The forecasts of 2014–2018 come from models trained on one to five seasons. No difference in the learned weights was detectable (the mismatch trend), so they were kept.
* **The drift estimates** rest on seven to eight seasons per tour and are imprecise. The choice they support (a long window) matters little: from 2014 or from 2019 makes S2 differ by 0.09, a tie.
* **The hold-out comparison** is measured on 2019–2021 only. No hold-out fit queried a test season.
* **One empty window:** the men's 2019 season has no one-season window (no men's 2018 odds). It is left out of the one-season designs' validation comparisons only.

## Files and how to run

Code in `src/eda/meta_stack/`, tests in `test/meta_stack/`, outputs in `data/studies/meta_stack/`. The 2019–2026 fits of both models are the surface-IOS study's (`data/studies/surface_ios/local/`, arms `base` and `base_noodds`), read only and checked against its manifest's fingerprints.

| Step | Script | Writes |
|---|---|---|
| Extra local fits: 2014–2018 for both models, and the hold-out fits (env `tennis-tabpfn-local`; about 20 minutes on a shared GPU) | `./python_tabpfn_local.sh src/eda/meta_stack/run_local.py` | `local/*.npz`, `local/runs.jsonl`, `run_local.log` |
| One forecast table per match; the repeated windows checked | `forecasts.py` | `walkforward.parquet`, `holdout.parquet`, `reproducibility.json` |
| The design argument's inputs and the prequential check (2014–2021 only) | `design.py` | `design.json`, `design_prequential.csv` |
| The test, 2022–2026 | `score.py` | `results.csv`, `results.json`, `coefficients.csv`, `test_predictions.parquet`, `score.log` |
| Tests | `./python.sh -m pytest test/meta_stack` | 18 tests: collinearity, antisymmetry, no look-ahead, the k/(2n) cost by simulation, both optimum formulas, the frames sent to the model |

The meta-models are in `meta.py`, shared paths in `common.py`. Run everything except `run_local.py` with `./python.sh`.
