# The surface-offset rating race: plan

**Fixed on 6 October 2026, before any race fit was run.** Two things were already decided when this plan was written: the surface-offset TrueSkill Through Time (TTT) model, whose two constants are tuned on 2013–2018 by `tune.py`, and the arms. The scorer is written to this plan. Anything added after the results are seen will be labelled post hoc.

## The question

The surface-Elo-pieces study ([report](../surface_elo_pieces/README.md)) found that the surface-offset Elo is a better rating than the 30% blend. Inside the model it tied at the closing odds. It was ahead without the odds, and it leaned ahead at the price 24 hours before the start.

TrueSkill Through Time is the owner's leading base-rating candidate ([decision](../../decisions/2026-10-03-leading-rating-candidate.md)). Its surface part, however, is the same blend design.

The owner asked on 6 October 2026 for two things:

* give TTT the same surface-offset structure;
* race it against the offset Elo with the local, non-thinking TabPFN-3.5, calibrated.

The owner's note governs how the race is read: bets are placed before the close. Information that the market has not priced when the bet is placed, but has by the close, is useful. So the race is read at the price 24 hours before the start, without any price, and at the close.

## The surface-offset TTT

Each player has an overall skill and an offset per surface. In a match on surface s, a side's performance is overall skill + offset on s + noise. This is TrueSkill's team factor, with the player's two skills as the team.

* **The overall chain** keeps the decided TTT's constants, which are frozen and never retuned here: sigma0, gamma and the smoothing span.
* **The offset chain** has its own prior deviation (sigma_o) and drift (gamma_o). Both are tuned on the rating-systems study's evaluation matches of 2013–2018. The rule is the lowest log loss, on a 4 × 4 grid that is widened past any edge.
* **The forecast** is P = Φ((μ_A + o_A − μ_B − o_B) / √(2 + Σ variances)).
* **Timing.** It runs on the leak-proof timeline exactly as `ttt_pass_timed` does. With the offsets off, it reproduces the decided TTT's overall chain exactly. That is tested on synthetic data and on the real 2010–2012 history, where the largest difference was 0.
* **Leaks.** The real-data leak probe runs before the race is scored (`probe.py`).

## Arms

Every arm is the best 2026 model's 54 inputs with only the rating changed (`arms.py`):

| Arm | Rating inputs |
|---|---|
| `base` | Stage 1 surface Elo as the blend (`elo_logit`) and `surface_first`, unchanged |
| `elo_off` | overall Elo + the Elo surface offset, plus both players' surface matches this season and days since their last surface match (in place of `elo_logit` and `surface_first`): the Elo-pieces study's primary |
| `ttt_blend` | the decided TTT's log-odds in place of `elo_logit` |
| `ttt_off` | `elo_off`'s structure with TTT: the offset TTT's overall part and offset part of z, plus the same two pairs |
| `both_off` | exploratory: `elo_off`'s and `ttt_off`'s rating parts together, plus the pairs |

Each arm is also fitted without the closing odds (`<arm>_noodds`).

## Fits

The fits use the local TabPFN-3.5 (`tabpfn-v3.5-20260909`, the same weights as the API's non-thinking v3.5), with:

* 8 estimators;
* softmax temperature 0.9;
* pretraining limits ignored;
* seeds 0, 1 and 2.

Each season Y from 2019 to 2026 is trained on the main-tour matches with odds of 2013 to Y − 1. Every season-Y match is predicted as stored and with the players swapped; the two are symmetrised and averaged over the seeds.

The arms with odds have two extra queries for the matches with Polymarket prices in 2025–2026. In these, the closing odds are replaced by the price 24 hours before the listed start (**early**) and 30 minutes before it (**late**).

## Calibration

Non-thinking TabPFN is over-confident. Calibration is a per-arm, per-tour slope on the log-odds: a logistic fit without intercept of the result on the arm's 2019–2021 seed-mean forecasts. The no-odds arms get their own slopes.

The slope is applied to the 2022–2026 forecasts and, for the arms with odds, to their early and late queries. No early prices exist before 2025 to fit an early-specific slope. Uncalibrated results are reported as a sensitivity.

## Population and units

* **Population.** The primary population excludes the debut seasons: matches with a player whose first match in Stage 0 falls in that season. These include the 2026 WTA identity split, as in the Elo-pieces study. All matches are a sensitivity.
* **Units.** Milli-log-loss. Positive = the second-named forecast is better.
* **Intervals.** 95% paired intervals over four-week blocks are the primary interval. Seasons as samples (2022–2026, t on 4 df) and calendar-week clusters are reported alongside. An interval that spans 0 is a tie.

## Endpoints: `ttt_off` against `elo_off`

| | What | Data |
|---|---|---|
| **H1, at the bet's price** | calibrated `ttt_off` vs `elo_off`, each fed the Polymarket price 24 h before the start | 2025–2026, every match with that price; event openers with a 3-day buffer (the Elo-pieces study's clean set) as a sensitivity |
| **H2, information** | calibrated `ttt_off_noodds` vs `elo_off_noodds` | 2022–2026 |
| **H3, at the close** | calibrated `ttt_off` vs `elo_off` | 2022–2026 |
| **H4, priced by the close but not at 24 h** | OLS without intercept of the move M = logit P(30 min) − logit P(24 h) on b = logit `elo_off_noodds` and Δ = logit `ttt_off_noodds` − logit `elo_off_noodds`. Both regressors are free of any price. Cluster-robust intervals over four-week blocks. A positive Δ slope means the price moves toward the TTT-offset view by the close. | 2025–2026, clean and all |

## The same comparisons, secondary

* every arm against `base`;
* `ttt_off` against `ttt_blend` (does the offset help TTT?);
* `ttt_blend` against `elo_off`;
* `both_off` against the better single arm (exploratory);
* each arm against the price it was fed. For the close, that is the closing price recalibrated per fold. For the 24-hour price, it is the price itself and the price recalibrated by a leave-one-block-out logistic fit.

## Decision rule (which rating the model should carry)

1. **H2 favours one rating** (interval excluding 0). That rating is preferred, unless H1 or H3 favours the other (interval excluding 0 against it). If they do, the reading is "conflict", reported as such.
2. **H2 ties.** The rating that H1 or H3 favours with an interval excluding 0 is preferred. If neither does, or they conflict, the result is a tie.
3. **A tie.** The cheaper rating is the default: the offset Elo, at about a second per pass against TTT's minutes.

The same rule reads `ttt_off` against `ttt_blend`, and each arm against `base`.

## Power

At the close, the Elo-pieces study's paired arm differences had a minimum detectable effect (80%) of about 0.4. Without the odds the differences are larger and noisier. At the 24-hour price, with about 2,600 matches, the half-width was about 1.3 in the Elo-pieces study, so H1 detects only large differences.

## Already seen

* `elo_off` against `base`, at the close and without the odds, in 2022–2026, through the paid API (the Elo-pieces study).
* Whether the decided TTT beats Stage 1 Elo as a rating alone, in 2019–2026 (the rating-systems study).

Never seen: any TTT arm inside TabPFN in 2022–2026, and any surface-offset TTT result outside the tuning years.

## Cost

GPU only. There are no paid API calls.
