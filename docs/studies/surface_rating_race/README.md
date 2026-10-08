# The surface-offset rating race: TrueSkill Through Time against Elo

**The owner's request of 6 October 2026,** after the [surface-Elo-pieces study](../surface_elo_pieces/README.md):

* give TrueSkill Through Time (TTT) the same surface-offset structure that made the offset Elo a better rating than the 30% blend;
* race the two head to head with the local, non-thinking TabPFN-3.5, calibrated.

The owner's note governs the reading. Bets are placed before the close, so information that the market has not priced at the time of the bet, but has by the close, is useful.

**Status.** On the race's evidence the owner decided the same day to swap the old Elo blend for the offset Elo in the model ([decision](../../decisions/2026-10-06-offset-elo.md)). §5 checks that swap in the model as it stood. TTT is still the owner's leading base-rating candidate ([decision of 3 Oct 2026](../../decisions/2026-10-03-leading-rating-candidate.md)); whether its form changes is the owner's call. The [plan](plan.md) was fixed before any race fit ran. Additions made after results were seen are labelled post hoc. No paid API call was made: every fit ran on the local GPU.

**Units.** Milli-log-loss. Positive = the second-named forecast is better. 95% intervals over four-week blocks. An interval that spans 0 is a tie.

## The answer

**Inside the model the two offset ratings tie, everywhere.** `ttt_off` against `elo_off`, both calibrated, in 2022–2026:

| Endpoint (positive = the TTT offset is better) | Men | Women | Both tours |
|---|---|---|---|
| **H1**, each fed the Polymarket price 24 hours before the start (2025–2026, 2,648 matches) | −0.18 [−0.59, +0.22] | −0.33 [−1.04, +0.37] | **−0.25 [−0.73, +0.22], tie** |
| **H2**, no price at all (23,727 matches) | −0.31 [−0.89, +0.26] | +0.29 [−0.39, +0.97] | **−0.02 [−0.49, +0.45], tie** |
| **H3**, at the close (23,727 matches) | −0.04 [−0.19, +0.12] | +0.02 [−0.12, +0.16] | **−0.01 [−0.12, +0.10], tie** |
| **H4**, does the price move toward the TTT offset's view between 24 h and 30 min? Slope on Δ, event openers (1,067) | +0.11 [−0.13, +0.36] | +0.23 [−0.13, +0.59] | **+0.17 [−0.12, +0.46], tie** |

By the pre-registered rule, a tie defaults to the cheaper rating: **the offset Elo.** A pass takes about a second, against 22 minutes (men) and 7 minutes (women) for the TTT offset.

Three findings matter more than the tie:

1. **The structure matters, the family does not.** At the 24-hour price, the offset form beats the blend form in both families. The decided TTT, which is the blend, is *worse* than the old Elo there.

   | At the 24-hour price (2,648 matches) | Gain |
   |---|---|
   | Elo: blend → offset | **+0.78 [+0.03, +1.54]** |
   | TTT: blend → offset | **+1.19 [+0.59, +1.78]** |
   | Old Elo → decided TTT | **−0.65 [−0.95, −0.36]** |

   The signs are the same at the 30-minute price and on the clean event openers (§4). There, the TTT gain and the decided TTT's loss stay clear of zero; the Elo gain does not. If the model is to carry TTT, it should carry TTT with offsets, never the decided blend.
2. **As a rating on its own, the TTT offset is the best of the four** (§2). Rescaled the way the Elo-pieces study scored ratings:
   * it beats the offset Elo by +3.61 (men) and +2.46 (women) on every level in 2019–2026;
   * it beats the decided TTT by +1.91 for men; for women the two tie.

   Inside the full model with its other 53 inputs, that advantage is gone. The decision record saw the same for the decided TTT: most of its gain over Elo is already in the other inputs.
3. **For betting before the close, the model as a whole holds information the 24-hour price lacks.**
   * Between 24 hours and 30 minutes, the price moves toward the model's no-odds view: slope +0.107 [+0.040, +0.174] on event openers, +0.090 [+0.033, +0.146] on every match with a price.
   * Fed the 24-hour price, the offset arms beat that price by +1.84 (`elo_off`) and +1.59 (`ttt_off`), both ties. Fed the 30-minute price, they are level with it (−0.15 and −0.39).

   This supports the owner's thesis about timing. Neither rating adds to it beyond the other.

**What this suggests for the owner's decision** (suggestions, not decisions):

* **In the model, replace the old blend with the offset Elo** (`elo_off`). It ties at the close and is ahead where the owner bets: +0.78 at the 24-hour price, +1.01 without a price (5 of 5 seasons). It is the cheapest option. *Adopted by the owner the same day ([decision](../../decisions/2026-10-06-offset-elo.md)); §5 checks it in the model as it stood.*
* **Wherever TTT is used, use it with offsets.** The decided blend is worse than the old Elo at every Polymarket price tested (−0.65 at 24 hours). Its offset form is +1.19 better than the blend there.
* **For the base-rating slot of the 3 October decision,** the TTT offset is the strongest rating on its own. For men it leads every alternative by +1.6 to +3.6. For women it leads the offset Elo by +2.5 to +2.6 and ties the decided TTT. Inside the full model it is no better than the offset Elo.
* **For women,** no rating change has helped in either study. Every women's comparison with base ties, except two arms that are worse at the close (§3).

## 1. The surface-offset TTT

### The model

Each player has an overall skill and an offset per surface (`ttt_offset.py`). In a match on surface s, each side's performance is its overall skill plus its offset on s plus noise. This is TrueSkill's team factor, with the player's two skills as the team. The forecast is

P(A wins) = Φ((μ_A + o_A − μ_B − o_B) / √(2 + s²_A + so²_A + s²_B + so²_B)).

| Part | Prior and drift | Source |
|---|---|---|
| Overall chain | the decided TTT's: men σ₀ 1.125, drift 0.4 per √year, smoothing over 2,336.5 days; women 1.5, 0.5, 602 days | frozen, never retuned |
| Offset chain | σ_o 0.25, drift 0.1 per √year, both tours | tuned (`tune.py`) |

* **The offset.** It starts at 0 and moves only on its surface. That is the offset Elo's structure in Bayesian form. Expectation propagation smooths both chains.
* **The time rule** is `ttt_pass_timed`'s leak-proof timeline, unchanged: a result joins the model the day after its latest possible finish, and a match reads the model as of its earliest possible start.
* **The decided TTT instead blends** an overall chain with a surface-only chain started at the newcomer's prior, the structure that the Elo-pieces study found biased for players new to a surface.

### Tuning

* **Rule.** The offset's two constants were tuned on 2013–2018 only: a 4 × 4 grid, lowest log loss on the rating-systems study's evaluation matches. These are every level with qualifying: 64,208 men's and 25,676 women's matches.
* **Result.** Both tours chose σ_o = 0.25 and drift 0.1, inside the grid on both constants. The surface is a smooth valley: three settings for the men and one for the women are within 0.1 milli of the best (`tuning.csv`).
* **Design evidence, in-sample for the two constants.** Against the decided TTT: +0.97 [+0.44, +1.50] (men) and +0.84 [+0.01, +1.66] (women). Against the overall chain alone: +4.69 and +4.30.

### Checks

| Check | Result |
|---|---|
| Offsets off = the decided TTT's overall chain | **Identical**: 0 of 451,006 rows differ (the full 2010–2018 history of both tours, against `match_timing/ttt_timed.parquet`); also exact on synthetic data (test) |
| The team update | equals the exact posterior moments of a 2-v-2 game (Monte Carlo test, 4 million draws) |
| Leak probe on real data (`probe.py`; every level, 2023–2024; four cut days per tour; results after the cut reversed) | **PASS**: 0 of 22,472–63,593 earlier matches moved at any cut, while 11,125–51,366 later ones did |
| A full pass's early rows equal the tuning pass's | identical 2013–2018 log loss on both tours |

**The offsets look like tennis.** Nadal's clay offset is +0.61 (grass −0.28). Djokovic's grass offset is +0.40. Federer's hard offset is +0.36 and his clay offset −0.24. Sinner's hard offset is +0.41.

Like the offset Elo, experienced players carry a positive average offset: +0.13 on hard and +0.17 on clay for players with at least 100 matches on the surface. It partly mirrors the inexperience penalty.

## 2. The ratings alone

Each rating's own forecast, with no model, rescaled: its log-odds times one slope per tour, fitted on 2013–2018 (`ratings_alone.csv`). This was added after the raw table was seen (post hoc), to match the Elo-pieces study's method.

| Rescaled | Every level, 2019–2026: men | women | Race population, 2022–2026: men | women |
|---|---|---|---|---|
| Stage 1 Elo → offset Elo | +0.94 [+0.43, +1.46] | +0.89 [+0.12, +1.66] | +2.28 [+0.56, +4.01] | +0.13, tie |
| Stage 1 Elo → decided TTT | +2.64 [+1.88, +3.40] | +2.86 [+1.52, +4.19] | +2.54 [+0.77, +4.32] | +2.44 [+0.45, +4.43] |
| Stage 1 Elo → TTT offset | **+4.55 [+3.51, +5.59]** | **+3.35 [+1.70, +5.01]** | **+4.11 [+1.78, +6.45]** | **+2.75 [+0.43, +5.07]** |
| Offset Elo → TTT offset | **+3.61 [+2.79, +4.43]** | **+2.46 [+1.06, +3.87]** | **+1.83 [+0.23, +3.42]** | **+2.62 [+0.63, +4.62]** |
| Decided TTT → TTT offset | **+1.91 [+1.40, +2.42]** | +0.50, tie | **+1.57 [+0.09, +3.04]** | +0.31, tie |

The race population is the main tour with closing odds, debut seasons out.

**Raw forecasts tell the same story except for the offset Elo.** On every level, its raw sum is *worse* than Stage 1 Elo for the men: −1.58 [−2.22, −0.94] in 2019–2026. Its slopes are 0.90–0.95, so it is over-confident as it stands. Once rescaled, it is better: the table's +0.94. The TTT offset is mildly over-confident too (slopes 0.92–0.97) and wins raw or rescaled.

## 3. Inside the model: the race

### Fits

* **Model and settings.** Local TabPFN-3.5 (`tabpfn-v3.5-20260909`, the API's non-thinking weights): 8 estimators, softmax temperature 0.9, seeds 0–2.
* **Folds.** Walk-forward over 2019–2026. Each season is trained on the main-tour matches with odds of 2013 to the season before, and predicted in both orientations. The two are symmetrised and averaged over the seeds.
* **Arms.** Five, each with and without the closing odds, for 240 fits (`local_fits.py`).
* **Calibration.** One slope per arm and tour from its own 2019–2021 forecasts. With odds, the slopes are 0.886–0.892 for men and 0.962–0.968 for women. Without odds, they are 0.853–0.896 and 0.917–0.941.

**All comparisons, both tours** (calibrated; debut seasons out; the 24-hour column covers every match with a Polymarket price; `both_off` is exploratory):

| Comparison (calibrated) | At the close, 2022–2026 | No price, 2022–2026 | No price, men | 24-hour price, 2025–2026 |
|---|---|---|---|---|
| `base` → `elo_off` | −0.05 [−0.24, +0.14] | **+1.01 [+0.18, +1.84]** | **+2.24 [+0.99, +3.50]** | **+0.78 [+0.03, +1.54]** |
| `base` → `ttt_blend` | −0.09 [−0.21, +0.04] | −0.21 [−0.73, +0.31] | +0.19 [−0.38, +0.75] | **−0.65 [−0.95, −0.36]** |
| `base` → `ttt_off` | −0.06 [−0.25, +0.12] | **+0.98 [+0.11, +1.86]** | **+1.93 [+0.73, +3.12]** | **+0.53 [+0.03, +1.03]** |
| `base` → `both_off` | −0.08 [−0.29, +0.12] | **+1.29 [+0.33, +2.26]** | **+2.32 [+0.90, +3.73]** | +0.59 [−0.29, +1.47] |
| `ttt_blend` → `ttt_off` | +0.03 [−0.16, +0.21] | **+1.19 [+0.48, +1.91]** | **+1.74 [+0.74, +2.74]** | **+1.19 [+0.59, +1.78]** |
| `elo_off` → `ttt_blend` | −0.04 [−0.25, +0.17] | **−1.22 [−2.09, −0.34]** | **−2.05 [−3.25, −0.86]** | **−1.44 [−2.33, −0.55]** |
| `elo_off` → `ttt_off` | −0.01 [−0.12, +0.10] | −0.02 [−0.49, +0.45] | −0.31 [−0.89, +0.26] | −0.25 [−0.73, +0.22] |
| `elo_off` → `both_off` | −0.03 [−0.15, +0.08] | +0.29 [−0.20, +0.77] | +0.07 [−0.58, +0.73] | −0.20 [−0.63, +0.24] |
| `ttt_off` → `both_off` | −0.02 [−0.19, +0.15] | +0.31 [−0.18, +0.80] | +0.39 [−0.40, +1.17] | +0.05 [−0.63, +0.74] |

Per tour, the race itself is a tie everywhere: men −0.04 at the close, −0.31 without a price and −0.18 at 24 hours; women +0.02, +0.29 and −0.33. Every one of these is a tie.

### At the close

* **Every arm ties with base:** `elo_off` −0.05 [−0.24, +0.14], `ttt_blend` −0.09 [−0.21, +0.04], `ttt_off` −0.06 [−0.25, +0.12].
* **Two exceptions, both women.** The decided TTT is worse than base, −0.25 [−0.46, −0.05], and so is the exploratory `both_off`, −0.42 [−0.72, −0.12]. The two offset arms lean the same way (−0.25 and −0.23, ties).
* **Against the closing price recalibrated per fold,** every arm is better, by +1.23 to +1.32. Base, for example, gains +1.32 [+0.72, +1.92], positive in all five seasons. That is the known edge of the non-thinking model over the tennis-data close.

### Without any price

* **The offset forms gain, the blend does not.** Seasons as samples, 2022–2026:
  * old Elo → offset Elo: +1.01, positive in 5 of 5 seasons (men +2.24 [+0.99, +3.50]);
  * old Elo → TTT offset: +0.98, 4 of 5 (men +1.93 [+0.73, +3.12]);
  * decided TTT → TTT offset: +1.19 [+0.48, +1.91], 5 of 5;
  * old Elo → decided TTT: −0.21 [−0.73, +0.31], a tie, 1 of 5.
* **For women, no rating change helps** without a price: every comparison with base ties (−0.64 to +0.18).
* **The race (H2): −0.02 [−0.49, +0.45], a tie.** Seasons −0.36, −0.32, −0.09, −0.35 and +1.50 (1 of 5 positive).
* **Both ratings together** (`both_off`): +0.29 [−0.20, +0.77] over the offset Elo and +0.31 [−0.18, +0.80] over the TTT offset, both ties.

The Elo-pieces study's paid API run found the same direction for its primary without odds: +2.74 for men and +1.36 for both tours (raw, seed 0). The local calibrated fit gives +2.24 and +1.01.

## 4. Before the close: the owner's question

These are the matches with Polymarket prices, 2025–2026 (2,648; 1,067 clean event openers). The arms were trained with the closing odds and fed the price 24 hours before the listed start.

| Comparison (calibrated) | 24 h, every match | 24 h, clean openers | 30 min, every match |
|---|---|---|---|
| `elo_off` → `ttt_off` (H1) | −0.25 [−0.73, +0.22] | −0.04 [−0.78, +0.69] | −0.23 [−0.63, +0.17] |
| base → `elo_off` | **+0.78 [+0.03, +1.54]** | +0.88 [−0.38, +2.13] | +0.58 [−0.13, +1.30] |
| base → `ttt_off` | **+0.53 [+0.03, +1.03]** | +0.83 [−0.16, +1.83] | +0.35 [−0.13, +0.84] |
| base → `ttt_blend` | **−0.65 [−0.95, −0.36]** | **−0.68 [−0.97, −0.40]** | **−0.66 [−1.02, −0.30]** |
| `ttt_blend` → `ttt_off` | **+1.19 [+0.59, +1.78]** | **+1.52 [+0.53, +2.51]** | **+1.01 [+0.29, +1.73]** |

Uncalibrated forecasts give the same signs.

**Against the price each arm was fed** (raw price; positive = the arm is better):

| | 24 h | 30 min |
|---|---|---|
| base | +1.06 [−3.02, +5.14] | −0.74 [−5.28, +3.80] |
| `elo_off` | +1.84 [−1.84, +5.53] | −0.15 [−4.39, +4.09] |
| `ttt_blend` | +0.40 [−3.88, +4.69] | −1.40 [−6.14, +3.35] |
| `ttt_off` | +1.59 [−2.43, +5.61] | −0.39 [−4.86, +4.09] |

* **Every one is a tie.** The direction is consistent, though: about +1.6 to +1.8 for the offset arms at 24 hours, and about 0 at 30 minutes.
* **Men.** At 24 hours: +3.06 (`elo_off`) and +2.88 (`ttt_off`), both ties.
* **Recalibrating the price makes the baseline weaker, not stronger.** The cross-fitted slope costs about a milli. `elo_off`, the Elo-pieces study's primary, gains +2.83 [+0.63, +5.03] against the recalibrated 24-hour price but +1.84 [−1.84, +5.53] against the raw one (clean openers: +2.74 and +2.01). That study's +2.85 was against the recalibrated price; against the price as quoted the margin is smaller.

**The move (H4 and its companions).** OLS without intercept of M = logit P(30 min) − logit P(24 h) on two regressors, both free of any price: b = logit `elo_off_noodds` and Δ = logit `ttt_off_noodds` − b. Intervals are cluster-robust over four-week blocks.

* **The price moves toward the model's view:** β_b = +0.107 [+0.040, +0.174] on event openers, +0.090 [+0.033, +0.146] on every match with a price.
* **Not toward the TTT offset beyond the offset Elo:** Δ +0.17 [−0.12, +0.46] on openers, −0.03 [−0.31, +0.24] on every match.

**The same move test for every arm against base** (secondary, in the plan before any no-odds forecast was scored). The price moves toward every offset form beyond the old Elo, and toward the TTT offset beyond the decided TTT:

| Δ = logit arm − logit reference (no-odds forecasts) | Slope on Δ, event openers | Slope on Δ, every priced match |
|---|---|---|
| `elo_off` → `ttt_off` | +0.170 [−0.116, +0.456] | −0.033 [−0.306, +0.239] |
| `base` → `elo_off` | **+0.159 [+0.032, +0.287]** | **+0.224 [+0.015, +0.433]** |
| `base` → `ttt_blend` | +0.166 [−0.054, +0.386] | +0.129 [−0.046, +0.304] |
| `base` → `ttt_off` | **+0.175 [+0.076, +0.274]** | **+0.180 [+0.057, +0.302]** |
| `base` → `both_off` | **+0.188 [+0.083, +0.292]** | **+0.216 [+0.087, +0.345]** |
| `ttt_blend` → `ttt_off` | **+0.181 [+0.031, +0.331]** | **+0.205 [+0.022, +0.389]** |

This is the owner's pattern: information the 24-hour price lacks and the close absorbs. It sits in the offset structure, which both families now have. It does not separate the TTT offset from the offset Elo.

**How much it is worth in money is measured elsewhere.** The [line-sharpening study](../line_sharpening/README.md) (another session, the same day) bet the current best model at Polymarket's early market instead of the close on 2,933 main-tour matches of 2026. The result was the same performance: $0.00 per 100 matches realized (−0.86 to +0.91), and the market moved only 7% of the way toward the model in between. The moves here are of that small size. Per unit of log-odds, the price moves about 0.1 with the model's own view (β_b) and 0.16–0.22 with the offset forms' difference from the old Elo (Δ). The information is real; its value at the early market's prices and fees is not yet shown.

## 5. After the owner's decision: the swap in the model as it stands

On 6 October the owner decided to swap the old Elo blend for the offset Elo in the model ([decision](../../decisions/2026-10-06-offset-elo.md)). By then the model also carried the surface IOS profile, kept the same day ([decision](../../decisions/2026-10-06-surface-ios-profile.md); the surface-IOS study's arm `sprof`).

* **The new inputs.** `model_frame.py` writes the model's 58 inputs for all 63,737 matches (`data/studies/surface_rating_race/model/`). Every input is checked value for value against its source: the 31 unchanged ones against the leak-proof refit's upload, the surface profile against `sprof`, and the six Elo inputs against `elo_off`.
* **The check.** `composed.py` fits and scores the model before and after the swap exactly as in the race. It was run after the decision and was not pre-registered.

| Calibrated, both tours | 24-hour price (2,648) | Without any price (23,727) | At the close (23,727) |
|---|---|---|---|
| The model before → after the swap | **+0.74 [+0.04, +1.45]** | **+0.83 [+0.07, +1.59]** | −0.07 [−0.24, +0.10] |
| Original inputs → surface profile (that decision alone) | −0.02 [−0.42, +0.38] | +0.25 [−0.02, +0.52] | +0.01 [−0.10, +0.11] |
| Offset Elo → offset Elo + surface profile | −0.06 [−0.43, +0.31] | +0.07 [−0.07, +0.21] | −0.01 [−0.10, +0.08] |
| Original inputs → both decisions | **+0.72 [+0.06, +1.39]** | **+1.08 [+0.25, +1.90]** | −0.06 [−0.26, +0.13] |

| The model before → after the swap | Men | Women |
|---|---|---|
| 24-hour price | +0.44 [−0.71, +1.58] | **+1.11 [+0.04, +2.18]** |
| Without any price | **+1.59 [+0.42, +2.75]** | +0.01 [−0.91, +0.93] |
| At the close | +0.05 [−0.20, +0.31] | −0.21 [−0.48, +0.07] |

* **The swap holds in the model.** Its gains on top of the surface profile match its gains on the original inputs: +0.74 against +0.78 at 24 hours, and +0.83 against +1.01 without a price. Without a price it is positive in all five seasons.
* **The move to the close follows it.** The price moves toward the new model's no-odds view beyond the old model's: +0.234 [+0.037, +0.431] on every priced match, +0.175 [+0.041, +0.310] on event openers (`composed_moves.csv`).
* **The surface profile adds nothing once the offset Elo is in.** It ties everywhere in that comparison. Its no-odds gain on the original inputs is reproduced here (+0.25; men +0.84 [+0.40, +1.28], as in its own study's +0.83). That gain is largely what the offset Elo now carries.
* **At the 24-hour price, the reason the profile was kept,** it ties even on its own: −0.02 [−0.42, +0.38].

## 6. Limitations

* **The 24-hour test is small.** It covers two seasons and about 2,600 matches of one venue (Polymarket), with a half-width of about 0.5 for arm against arm and about 4 against the price. Ties there are not proof of no difference.
* **Calibrating the early queries.** The slopes come from close-fed forecasts. A model trained on the close and fed a noisier price may need a different slope. Arm-to-arm comparisons share that error.
* **The identity split.** The history keeps the 2026 duplicate player IDs, as the decided TTT does. Debut seasons are left out of every primary comparison, as in the Elo-pieces study.
* **Not re-tuned.** The TTT offset's overall constants are the decided TTT's. Re-tuning them jointly with the offset might gain a little more.
* **No refit with Thinking.** The local non-thinking model, calibrated, tied Thinking in the Elo-pieces study's check; no paid fit was made here.
* **The 30 September snapshot.** Every input was built on that day's Stage 0 and match timeline. Another session rebuilt both at 00:35 UTC on 7 October, bringing repairs to 8,040 matches, the Slam box scores, new results and 42 changed WTA ids. The decided TTT has since been rebuilt (women +3.22 over Elo in 2019–2026, was +2.93). This study's results stand on the snapshot whose hashes are in `inputs_manifest.json`.

## Files

| File | What |
|---|---|
| [plan.md](plan.md) | the pre-registration, fixed before any race fit |
| `src/eda/surface_rating_race/ttt_offset.py` | the TTT offset model and its leak-proof pass |
| `src/eda/surface_rating_race/runs.py`, `tune.py`, `probe.py`, `features.py` | history and constants, tuning, leak probe, full-history pass and the ratings alone |
| `src/eda/surface_rating_race/arms.py`, `local_fits.py`, `score.py` | the arms, the GPU fits, the scorer |
| `src/eda/surface_rating_race/model_frame.py`, `composed.py` | after the decision: the model's 58 inputs, and the swap checked in the model as it stood |
| `test/surface_rating_race/` | 8 tests: exact reproduction of the decided TTT, team-update moments, no leak, arms and flip, the model's arm |
| `data/studies/surface_rating_race/` | `tuning.csv`, `tuning_choice.json`, `probe.json`, `ttt_offset.parquet` (872,704 matches), `ttt_offset_run.json`, `ratings_alone.csv`, `features_summary.json`, `local/` (336 fits: the race's 240 and the check's 96), `results.csv`, `results.json`, `moves.csv`, `predictions.parquet`, `model/model_frame.parquet` and `model/model_inputs.json`, `composed_results.csv`, `composed_moves.csv`, logs. `results_partial.*` and `moves_partial.csv` are monitoring runs on incomplete fits, superseded by the final files |
| `data/studies/surface_rating_race/inputs_manifest.json` | SHA-256 of every input table the runs read, recorded on 6 Oct 2026 before another session's planned rebuild of Stage 0 and the match-timing tables. A rerun after that rebuild reads different inputs |
