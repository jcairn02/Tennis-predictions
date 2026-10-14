# The Pinnacle-first model: the men's backtest, season by season

9 October 2026 · Written for the owner · Research evidence. The odds input itself is decided ([decision](../../decisions/2026-10-09-pinnacle-first-odds-input.md)); nothing here decides a bet or a stake.

**The owner's request** (9 Oct 2026): "Do this, then find wherever we are at with the plan for the best tabpfn3.5 offline model and repeat the backtest we've done before to see how we do in log loss and ROI for mens only, year to year."

**How to read the numbers.**
* **Log loss:** lower is better. A gain is in milli-log-loss (mLL), **+ = the model better** than what it is compared with.
* **ROI** is profit per unit staked, under the owner's staking: to win 1 unit on a favourite, d/(2(d − 1)) units on an underdog.
* **Intervals** are 95%, over four-week blocks (for ROI, from 2,000 block draws).
* **Verdicts:** "better" or "worse" when the interval clears 0, otherwise "unresolved" with P(better) ([adoption framework](../adoption_framework/README.md) § 7).

## The answer in short

* **Built:** the current best model with the decided Pinnacle-first odds input.
  * The frozen reference's frame, only the odds input changed.
  * Fitted with 16 seeds for 2019–2026, both stages.
  * Its folder is `data/studies/current_best_model/pinnacle_first_2026-10-09/`.
* **Against the frozen reference** (the decided comparison, 2020–2024, + = Pinnacle first better):
  * both tours +0.01 mLL [−0.29, +0.31], men −0.14 [−0.57, +0.29], women +0.18: all unresolved;
  * no input flagged.

  The switch is level.
* **Men, 2020 to 28 Jul 2026, at the close, both stages** (the TabPFN forecast plus the serve-speed offset, refitted each season; [§ 7](#7-the-serve-speed-offset-in-these-numbers)):
  * **Log loss:** better than its own Pinnacle-first price by **+1.70 mLL [+0.96, +2.44]**. It is ahead in 6 of 7 seasons; 2023 is behind (−0.85, unresolved).
  * **ROI, the owner's staking, edge above 0:**
    * **Pinnacle +2.05%** [+0.3, +4.0], 6,488 bets, +316 units (2020 – Sep 2025);
    * **BetOnline +2.21%** [+0.5, +4.1], 6,305 bets, +281 units (2020 – Jul 2026).

    Both are positive in 6 of 7 seasons; 2023 lost at both. Edges above 2% return +5.91% and +4.07%; above 5%, +9.73% and +7.48%.
  * **Against the earlier model (the books' average):** level in log loss (−0.11 [−0.56, +0.34]) and in money (−0.27 and −0.66 points, unresolved).
* **Read with the caveats in § 6:**
  * the inputs were chosen on these seasons;
  * 2026 is fed BetOnline's line, since Pinnacle's is missing;
  * these are archived closes, not fills.

## 1. Where the plan for the best offline TabPFN-3.5 model stands

"The current best model" is a template ([decision](../../decisions/2026-10-08-current-best-model.md)): the local, non-thinking TabPFN-3.5 on 58 inputs, then the walk-forward serve-speed adjustment.

| Date | Step | State |
|---|---|---|
| 6–7 Oct | The 58 inputs (offset Elo, surface IOS profile), the serve-speed stage | Decided |
| 8 Oct | Rebuilt on the corrected tables; frozen as the reference (`reference_2026-10-08/`, its odds input the books' average); new data enters only as a candidate compared with it | Decided, built (fits: seeds 0–3) |
| 8 Oct (evening) | The ATP's 2018–2021 Stats Centre speeds in stage 2's history | Decided |
| 8 Oct | The prediction run: box scores first, live inputs from the training chain, a gate | Built; does not forecast yet (it needs upcoming matchups and bet-time prices) |
| 8–9 Oct | IOS products centred; split by level; recent seasons only; close drift | Studied, recipe unchanged (ties, or "keep as is") |
| 8 Oct | A rebuild with 2025–2026 as a clean holdout | Proposal, not run |
| **9 Oct** | **The odds input "Pinnacle first", in training and live** ([decision](../../decisions/2026-10-09-pinnacle-first-odds-input.md)) | **Decided; the instance `pinnacle_first_2026-10-09/` built and fitted (seeds 0–15, 2019–2026)** |

**Still missing for a live bet:**
* a recorder of Pinnacle's current line, from the guest service its website reads;
* the prediction run's last step: upcoming matchups and their prices into a forecast;
* Pinnacle's own closes from August 2025. When they are found, the model is retrained on Pinnacle throughout.

## 2. The decided comparison with the frozen reference

`compare.py --candidate pinnacle_first_2026-10-09`, the procedure of the current-best-model decision. Seeds 0–3, both stages, 2020–2024 (22,265 matches, debut seasons out). Each model is fed its own odds input. + = Pinnacle first better:

| | Both tours | Men | Women |
|---|---|---|---|
| **Pinnacle first − reference, both stages** | +0.01 [−0.29, +0.31], unresolved (P 0.53) | −0.14 [−0.57, +0.29], unresolved (P 0.26) | +0.18 [−0.37, +0.73], unresolved (P 0.74) |
| Stage 1 alone | +0.02 [−0.29, +0.32], unresolved | −0.14 [−0.57, +0.30], unresolved | +0.18 [−0.37, +0.73], unresolved |
| For scale: each model's gain over its own calibrated close, reference / Pinnacle first | +1.37 / +1.09, both better | +1.48 / +1.23, both better | +1.26 / +0.95, both better |

* **The input check:** 1 input of 58 changed (the odds), none flagged "uneven".
* **By season,** both tours: 2020 +0.05, 2021 +0.44, 2022 +0.03, 2023 −0.29, 2024 −0.12. All unresolved.
* **By level:** Slams +0.70 (P 0.96), 1000s −0.44 (P 0.07), 500s −0.21, 250s +0.02. All unresolved.
* **Reading.**
  * The two models are level in accuracy at the close.
  * The edge over the model's own price is smaller with Pinnacle (+1.09 against +1.37). That is expected: the sharper input leaves less for the other inputs to add.
  * Accuracy against results is what counts here, and that is level.

## 3. The backtest: what was run

The Thinking-58 study's backtest ([report](../tabpfn_thinking58/README.md) § 5–6), repeated for men, season by season (`src/eda/pinnacle_first/backtest.py`).
* **The model:** the Pinnacle-first instance, both stages, the decided recipe.
  * Its forecast averages seeds 0–15.
  * The per-tour calibration slope and the speed stage's b are fitted walk-forward on 2019 .. Y − 1, from seeds 0–3.
  * It is fed its own input at the close: Pinnacle's close to 7 Sep 2025, BetOnline's line after.
  * Stage 2 reads the template's current speed history, with the ATP backfill.
* **For comparison:** the earlier model, the frozen reference (the books' average as input; seeds 0–3, all it has), through the same recipe.
* **The matches:** men, 2020 to 28 Jul 2026, where the earlier backtest ended.
  * Matches from 29 Jul 2026 are the proposed sealed holdout; their results are not read.
  * 40 matches of June 2026 whose ids changed at the 7 Oct rebuild have no speed value and are left out.
* **Log loss:** debut seasons out, as the decided comparisons.
* **The return:** the earlier backtest's rules.
  * Completed matches with a coherent price at the book.
  * Back the side whose expected return p·d − 1 is the larger and above the threshold.
  * The owner's staking.
  * The rules: edge above 0 (primary), above 2% and 5%, and the top half of bets by edge, its threshold taken from the same book's earlier seasons.
* **The books:**
  * Pinnacle's close, the one the model's input uses: tennis-data's to July 2025, OddsTrader's to 7 Sep 2025. No faithful Pinnacle price exists after that.
  * BetOnline's last recorded line.
* **The control** bets the model's own input price, recalibrated: what the price alone earns.

## 4. Men, season by season

| Season | Log-loss matches | Model's log loss | Gain over its own price, mLL (+ = model better) | ROI at Pinnacle, edge > 0 | ROI at BetOnline, edge > 0 |
|---|---:|---:|---|---|---|
| 2020 | 1,259 | 0.5708 | +2.29 [−0.90, +5.47], unresolved (P 0.94) | **+8.50%** [+0.5, +18.8]; 498 bets, +62 u | +3.83% [−1.8, +10.4]; 483 bets, +32 u |
| 2021 | 2,466 | 0.5885 | **+2.64 [+0.95, +4.32], better** | +3.72% [−2.0, +9.3]; 1,069 bets, +77 u | +3.10% [−2.4, +8.4]; 1,022 bets, +69 u |
| 2022 | 2,601 | 0.5795 | +1.32 [−0.39, +3.04], unresolved (P 0.94) | +3.45% [−0.5, +7.0]; 1,184 bets, +73 u | +3.29% [−0.6, +7.8]; 1,041 bets, +60 u |
| 2023 | 2,672 | 0.5903 | −0.85 [−3.05, +1.35], unresolved (P 0.21) | −0.61% [−4.0, +2.5]; 1,473 bets, −26 u | −2.97% [−6.7, +0.4]; 1,142 bets, −74 u |
| 2024 | 2,674 | 0.5813 | +1.63 [−0.12, +3.37], unresolved (P 0.97) | +2.36% [−0.6, +6.1]; 1,304 bets, +84 u | +1.78% [−0.6, +5.1]; 993 bets, +41 u |
| 2025 | 2,620 | 0.5972 | **+2.31 [+0.20, +4.41], better** | +1.69% [−3.1, +6.9]; 960 bets, +45 u (to 7 Sep) | **+4.40%** [+1.1, +9.6]; 953 bets, +102 u |
| 2026 (to 28 Jul) | 1,774 | 0.5889 | **+3.57 [+0.78, +6.35], better** | — (no Pinnacle price) | **+7.16%** [+1.3, +12.3]; 671 bets, +51 u |
| **All** | **16,066** | **0.5862** | **+1.70 [+0.96, +2.44], better** | **+2.05%** [+0.3, +4.0]; 6,488 bets, **+316 u** | **+2.21%** [+0.5, +4.1]; 6,305 bets, **+281 u** |

* **Log loss: an edge over the price in 6 of 7 seasons;** 2023 is the exception. Pooled, the model beats its own Pinnacle-first price by +1.70 mLL. Over 2020–2024 alone: +1.28 [+0.43, +2.13], better.
* **Money: positive at both books in 6 of 7 seasons;** 2023 lost at both.
* **The price alone loses:**
  * at BetOnline, −1.35% on 2,049 bets;
  * at Pinnacle it finds almost nothing to bet (7 bets), since it is Pinnacle's own price.
* **Bigger edges return more**, and about what they claim:

  | Rule | Pinnacle, claimed → realised | BetOnline, claimed → realised |
  |---|---|---|
  | Edge > 0 | 2.9% → **+2.05%** | 3.5% → **+2.21%** |
  | Edge > 2% | 5.0% → **+5.91%** [+2.0, +10.0] (3,192 bets) | 5.5% → **+4.07%** [+0.7, +7.6] (3,561 bets) |
  | Edge > 5% | 7.8% → **+9.73%** [+3.1, +17.2] (1,187 bets) | 8.5% → **+7.48%** [+1.7, +13.5] (1,518 bets) |
  | Top 50% by edge (threshold from earlier seasons) | **+5.54%** [+1.8, +9.4] | **+4.26%** [+0.3, +7.9] |

  Every season of every rule is in [backtest_tables.md](../../../data/studies/pinnacle_first/backtest_tables.md).

## 5. Against the earlier model (the books' average)

Paired, the same men's matches, + = Pinnacle first better:
* **Log loss** (4 seeds each):
  * pooled 2020–2026: −0.11 mLL [−0.56, +0.34], unresolved (P 0.31);
  * 2020–2024: −0.14, which is `compare.py`'s men's figure;
  * by season −0.49 to +0.73, every one unresolved.
* **Its gain over its own price:** +1.89 [+1.10, +2.67] for the earlier model (over the books' average), against +1.70 here (over Pinnacle's price). The sharper price leaves less to add.
* **Money, edge above 0:**

  | Book | Pinnacle first | Earlier model | Difference, points |
  |---|---|---|---|
  | Pinnacle | +2.05% | +2.32% | −0.27 [−1.2, +0.8], unresolved |
  | BetOnline | +2.21% | +2.88% | −0.66 [−1.9, +0.5], unresolved |

  At edge above 2%:

  | Book | Pinnacle first | Earlier model | Difference, points |
  |---|---|---|---|
  | Pinnacle | +5.91% | +4.92% | +0.99 [−1.8, +4.1], unresolved |
  | BetOnline | +4.07% | +3.15% | +0.92 [−1.9, +3.9], unresolved |

* **So the switch costs nothing measurable** in log loss or money, and it removes the need for the books' average at bet time.

**Against the earlier backtest's numbers.** Thinking-58, men, the current best model of 8 Oct:
* Pinnacle: +2.48% over 2022 – Jan 2026;
* BetOnline: +4.60% over 2024 – Jul 2026.

Over the same windows here (edge above 0; profit over stake pooled across the seasons):

| Book and window | Pinnacle first | The earlier model, as rebuilt here |
|---|---|---|
| Pinnacle, 2022 – Sep 2025 | +1.41% (4,921 bets) | +1.97% (5,294 bets) |
| BetOnline, 2024 – Jul 2026 | +3.65% (2,617 bets) | +3.68% (2,708 bets) |

So most of the gap to the earlier backtest is the setup, not the odds input. The setups differ in four ways:
* the frame (rebuilt on the corrected tables);
* the speed stage (here from 2020, there from 2024);
* the Pinnacle price (here only Pinnacle's faithful close, to Sep 2025);
* the seeds.

## 6. What it does and does not show

* **Not an untouched holdout.** The 58 inputs were chosen by studies that had seen 2022–2026 (2025–2026 included), and the odds input was chosen today on 2019–2025 prices. Read the returns as optimistic, as the earlier backtest's.
* **2026 is fed BetOnline's line,** because Pinnacle's 2026 prices are missing. Live, Pinnacle's current line will be fed. So 2026 shows the stand-in, not the plan.
* **Closes, not mid-way prices.** Every price is a close (tennis-data's untimed one, or the last line OddsTrader recorded). Betting before the close was measured in the [bet-timing study](../bet_timing/README.md).
* **Archived quotes, not fills.** Limits and account restrictions are not in the data.
* **Pinnacle's return stops on 7 Sep 2025:** no faithful Pinnacle price exists after it.
* **Many cells.** 7 seasons, 2 books, 4 rules, 4 forecasts. The primary is the pooled edge-above-0 return and the pooled log loss. Single seasons are flags.

## 7. The serve-speed offset in these numbers

The owner's question (9 Oct 2026): "does this include the serve speed offset? this roi?"

**Yes.** Every log loss and ROI above is the model's final forecast, both stages: logit q = s_tour,Y · η + b̃_Y · `spd_L`, men only.
* The coefficients are refitted each season on 2019 .. Y − 1, as `compare.py` applies the decided recipe, so the offset runs from 2020.
* The earlier model got the same treatment.
* b̃ for the new model:

  | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---:|---:|---:|---:|---:|---:|---:|
  | 0.022 | 0.018 | 0.012 | 0.072 | 0.030 | 0.025 | 0.035 |

* The earlier backtest (Thinking-58) applied it only from 2024, the window its decision was tested on.

**What it adds** (men; the same model without the offset, its calibration slope alone; + = with the offset better):

| Log loss | mLL |
|---|---|
| 2024–2026 (the decision's window) | **+0.31 [+0.05, +0.56], better.** In line with the decision's +0.41 [+0.04, +0.78] on 2024–26 |
| 2020–2023 | −0.31 [−0.74, +0.11], unresolved (P(better) 0.07). The 2023 coefficient, fitted on the thin speed data of 2019–2022, is more than twice the later ones, and 2023 alone reads −1.32 |
| 2020–2026 | −0.04 [−0.31, +0.23], unresolved |

| Return, edge above 0 | Offset from 2020 (the figures above) | No offset | Offset from 2024 only (the earlier backtest's way) |
|---|---|---|---|
| Pinnacle, 2020 – Sep 2025 | +2.05% | +2.37% | +2.11% |
| Pinnacle, 2024 – Sep 2025 | +2.07% | +2.70% | +2.07% |
| BetOnline, 2020 – Jul 2026 | +2.21% | +2.61% | +2.66% |
| BetOnline, 2024 – Jul 2026 | +3.65% | +3.57% | +3.65% |

* **The offset's effect on money is within noise.** Paired, pooled from 2020, what it adds is −0.32 points [−1.0, +0.3] at Pinnacle and −0.39 [−1.3, +0.5] at BetOnline, both unresolved.
* **Reading.** It earns its place in log loss where it was decided (2024 on), and that is the period that resembles live use. Its early seasons rest on sparse speed data. Applied from 2024 only, as before, the returns are +2.11% (Pinnacle) and +2.66% (BetOnline).

## 8. The predicted edge: thresholds and bands

The owner's questions (9 Oct 2026): the return when betting only above a predicted ROI, and why the returns looked higher than predicted.

**The edge is the bet's predicted ROI,** p·d − 1: the expected profit per unit staked at the book's price. Men, 2020 on, the model above ([backtest_tables.md](../../../data/studies/pinnacle_first/backtest_tables.md)).

**A threshold is a floor:** "over 1%" holds every bet predicted above 1%, so its average prediction is higher.

| Predicted ROI over | Pinnacle: bets a year (share of matches) | Mean predicted → realised | Profit | BetOnline: bets a year (share) | Mean predicted → realised | Profit |
|---|---|---|---:|---|---|---:|
| 0% | 1,151 (48%) | 2.9% → +2.05% | +316 u | 962 (42%) | 3.5% → +2.21% | +281 u |
| 1% | 799 (34%) | 3.9% → +4.82% | +306 u | 723 (32%) | 4.5% → +4.06% | +271 u |
| 2% | 567 (24%) | 5.0% → +5.91% | +206 u | 543 (24%) | 5.5% → +4.07% | +167 u |
| 5% | 211 (9%) | 7.8% → +9.73% | +102 u | 232 (10%) | 8.5% → +7.48% | +102 u |
| 10% | 34 (1.4%) | 13.0% → +19.86% | +29 u | 52 (2.3%) | 14.1% → +10.65% | +28 u |

**In disjoint bands, realised ROI scatters around the prediction:** some above, some below, every prediction inside its band's interval.

| Predicted ROI band | Pinnacle: mean predicted → realised | BetOnline: mean predicted → realised |
|---|---|---|
| 0–1% | 0.4% → +0.1% [−2.0, +2.1] | 0.4% → +0.2% [−1.8, +2.2] |
| 1–2% | 1.4% → +3.5% [+0.0, +6.9] | 1.5% → +4.1% [+0.9, +7.2] |
| 2–3% | 2.5% → +6.0% [−0.2, +12.3] | 2.4% → +3.2% [−3.1, +9.4] |
| 3–5% | 3.8% → +2.6% [−4.4, +9.9] | 3.9% → +1.6% [−5.3, +7.8] |
| 5–7.5% | 6.0% → +7.7% [−0.5, +16.7] | 6.1% → +4.5% [−2.6, +12.2] |
| 7.5–10% | 8.6% → +9.1% [−6.1, +24.5] | 8.6% → +12.5% [+0.9, +24.3] |
| 10% and over | 13.0% → +19.9% [+0.3, +40.9] | 13.9% → +10.7% [−4.3, +26.1] |

* **The model's predicted ROI is about right, within noise.** Overall it ran a little hot at Pinnacle and a little cold at BetOnline (all bets: 3.5% predicted, +2.2% realised).
* **Skill, not luck:** the same bets would lose about 2–2.5% (Pinnacle) and 3.5% (BetOnline) if the book's own price were right. Every band is above that.
* **The 0–1% band breaks even:** volume without profit. Nearly all the profit is in bets predicted above 1%.
* **Not an untouched holdout** (§ 6): read as optimistic.

## Files and reproduce

| What | Where |
|---|---|
| The instance (frame, fits, comparison) | `data/studies/current_best_model/pinnacle_first_2026-10-09/` ([README](../../../data/studies/current_best_model/pinnacle_first_2026-10-09/README.md)) |
| The odds input | `src/eda/current_best_model/odds_input.py`; tests `test/current_best_model/test_odds_input.py` |
| The backtest | `src/eda/pinnacle_first/backtest.py` → `data/studies/pinnacle_first/backtest.json`, `backtest_tables.md`; tests `test/pinnacle_first/` |

```
./python.sh src/eda/current_best_model/odds_input.py --from-reference data/studies/current_best_model/pinnacle_first_2026-10-09
bash src/eda/bet_timing/run_when_free.sh src/eda/model_rebuild/fits.py --out data/studies/current_best_model/pinnacle_first_2026-10-09 --seeds 0-15 --seasons 2019-2026 --wait-memory-only
./python.sh src/eda/current_best_model/compare.py --candidate data/studies/current_best_model/pinnacle_first_2026-10-09
./python.sh src/eda/pinnacle_first/backtest.py
./python.sh -m pytest test/pinnacle_first test/current_best_model -q
```
