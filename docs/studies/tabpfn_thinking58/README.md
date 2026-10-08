# One TabPFN-3.5-Thinking fit on the 58 inputs: against the calibrated non-thinking model, with the serve-speed offset, and the return at the BetOnline and Pinnacle closes

8 October 2026 · Research evidence, not a production, model or betting decision.

**Keys.**
* Log loss: lower is better. Gains are in milli-log-loss (mLL), **positive = the second-named forecast is better**. Thinking is second wherever it appears.
* Brackets are paired 95% intervals over four-week blocks of tournament dates. A range that spans 0 is a **tie**.
* ROI is profit per unit staked. Its brackets come from 2,000 draws of four-week blocks.
* Labels: **observed** is computed here, **inferred** is a reading, **suggestion** is a proposal.

Every number below is read from `data/studies/tabpfn_thinking58/` (`results.json`, `roi.csv`); `src/eda/tabpfn_thinking58/tables.py` prints the tables.

## The answer

* **Observed. On the 58 inputs, Thinking without calibration ties the calibrated non-thinking model.**
  * Its twin is the free local TabPFN-3.5 on the identical upload: the same 39,918 training matches, inputs and settings, without thinking. Against it, Thinking gains **+0.14 [−0.14, +0.43] on 2022–2026, a tie** (men +0.08, women +0.22, both ties).
  * Against the current best model's first stage (16 seeds, walk-forward, calibrated): −0.01 [−0.30, +0.27], a tie.
  * Every season is a tie.
* **Observed. With the serve-speed offset, it is still a tie.** The offset is not an input. It is the current best model's second stage on the forecast's log-odds, part of its final forecast. Coefficients exist from 2024.
  * Thinking plus the offset (no slope) against the current best model (both stages), 2024–2026: **−0.05 [−0.45, +0.34], a tie** (men −0.27, women +0.17).
  * Over 2022–2026: −0.00 [−0.29, +0.28].
  * The offset adds as much to Thinking as to the local model: +0.21 [+0.07, +0.34] (men +0.40 [+0.14, +0.67]), against +0.19 for the current best model.
* **Observed. Thinking needs no calibration; the local model does.**
  * Thinking's slope on its own 2022–2026 log-odds is 0.987 ± 0.023 (men) and 0.988 ± 0.024 (women). That is consistent with 1.
  * Recalibrating it walk-forward costs a little: −0.07 [−0.15, +0.01], a tie.
  * The twin's slope is 0.909 (men) and 0.896 (women). Recalibrating it is worth +0.75 [+0.18, +1.33].
  * The raw twin trails Thinking by 0.84 [0.27, 1.40]. The decided slope closes that gap, as on the 54 inputs ([earlier check](../tabpfn_leakproof/README.md)).
* **Observed. At Polymarket's price 24 hours out (2,648 matches, 2025–2026) it is a tie too.**
  * Thinking plus the offset against the current best model: −0.37 [−1.39, +0.65].
  * Each beats that price, recalibrated, by about +2.8 to +3.2 (men +4.1 to +4.8).
* **Observed. The return.** The owner's staking rule, a bet on any positive expected return at the book's close, completed matches, the final forecasts:

  | Close | Matches | Thinking + speed offset | Current best model (both stages) | Current best − Thinking, points |
  |---|---:|---|---|---|
  | **Pinnacle** (3 Jan 2022 – 12 Jan 2026; margin 2.74%) | 19,602 | **+1.55% [+0.28, +2.87]** on 9,429 bets | **+1.50% [+0.38, +2.73]** on 10,186 bets | −0.04 [−0.94, +0.85], tie |
  | **BetOnline** (1 Jan 2024 – 28 Jul 2026; margin 3.81%) | 12,624 | **+4.24% [+2.41, +5.99]** on 4,594 bets | **+2.93% [+1.20, +4.77]** on 4,888 bets | −1.31 [−2.57, +0.05], tie |

  * **Not the price.** Betting the market-average close's own view the same way loses: −1.96% recalibrated and −7.94% de-vigged at Pinnacle; −2.41% and −5.04% at BetOnline.
  * **Men carry it.** Pinnacle: men +2.02% (Thinking) and +2.48% (current best); women +0.88% and +0.73%, ties. BetOnline: men +5.17% and +4.60%; women +3.00% and +1.23%, ties.
  * **The bigger the claimed edge, the bigger the return, and of about the claimed size.** Current best at Pinnacle:
    * edges above 0, claimed 2.9% on average, returned +1.50%;
    * above 2%, claimed 5.0%, returned +3.75%;
    * above 5%, claimed 8.2%, returned +9.68%.
  * **Taking only the top 50% of bets by edge** (above each forecast's median edge, about 2%) roughly halves the bets and doubles or triples the return per unit staked, though the total profit is smaller:
    * Pinnacle: Thinking + offset +4.08% [+1.61, +6.33], current best +3.87% [+1.72, +6.07];
    * BetOnline: +7.15% [+3.37, +11.13] and +8.44% [+5.40, +11.64].
  * **BetOnline in 2026 alone** (3,190 matches, January to July), edge above 0:
    * Thinking + offset +8.71% [+5.99, +12.50], current best +5.76% [+3.11, +9.35];
    * top 50% with the threshold set on 2024–2025 bets: +12.00% [+7.08, +18.00] and +9.75% [+2.82, +16.58].
    * 2026 was a good season for every forecast, the price control included (+1.09%, against −5.27% and −2.42% in 2024 and 2025). Seven months give only 9 four-week blocks, so its intervals are too narrow.
* **Inferred.** Paying for Thinking buys nothing measurable over the free local model with its slope, its 16 seeds and the speed offset, in log loss or in money. The local model's one handicap, over-confidence, is what the slope fixes.
  * Both make money at both closes in this backtest. **Read that with the caveats below:** the inputs were chosen by studies that had seen 2022–2026, and the prices are archived quotes, not proven fills.
* **Cost.** One fit and one prediction batch: **169,141 tokens billed** against a quote of 676,563 (0.85% of the monthly quota), 338 seconds.

## The question

The owner, 8 Oct 2026:
* "Do ONE paid fit to close the gap on the 58 columns and compare tabpfn3.5 nonthinking calibrated to tabpffn 3.5 thinking noncalibrated. When doing so also compose ROI against betonline/pinnacle close. Bet 1 unit at even, bet X units to win 1 on favorites and slightly <1 unit on underdogs proportional to how much of an underdog they are, partially informed by what you think kelly would want (win more than 1 unit, but not an exact 1to1)."
* Then: "Don't forget to also include the serving speed offset we've added in the conclusions, its not IN the model but its apart of the final log loss of the model."

**The gap.** The two earlier Thinking fits ([2 Oct](../tabpfn_thinking/README.md), [5 Oct](../tabpfn_leakproof/README.md)) used the 54 inputs from before the owner's decisions of 6 Oct 2026. Every result on the 58 inputs came from the local non-thinking model.

**Why compare raw Thinking with the calibrated local model.** On the 54 inputs, the calibrated local model tied Thinking. A check the same day found Thinking's own calibration slope consistent with 1 there. So the question was whether that holds on the 58 inputs, with and without the speed offset.

## Design, fixed before the paid call

**The upload** (`build_frame.py`; checked before anything was written):

| | |
|---|---|
| Training | The 58-input model frame's 39,918 main-tour matches with closing odds, 2013–2021. These are the earlier Thinking fits' rows and labels, checked equal |
| Inputs | The 58 of the owner's decisions of 6 Oct 2026 ([offset Elo](../../decisions/2026-10-06-offset-elo.md), [surface IOS profile](../../decisions/2026-10-06-surface-ios-profile.md)). The 31 kept from the 54-input fit were checked equal, value for value |
| Query | The 23,819 test matches of 2022–2026 as stored, then with A and B swapped: differences negated, the (A, B) pairs exchanged, context unchanged |
| Query, early block | The 2,692 test matches of 2025–2026 with a Polymarket price 24 hours before the listed start, with that price in the odds column, stored and swapped. These are the rating race's early-block matches, checked equal |
| Query rows in all | 53,022, in one prediction batch |
| Configuration | The earlier Thinking fits': `v3.5_default`, thinking on, effort high, log-loss metric, 8 estimators, softmax temperature 0.9, seed 0 |
| The guard | The leak-proof refit's once-only guard, with its own schema and receipt folder: one fit, one prediction, never repeated on an unknown outcome |

**The forecasts compared** (`score.py`):

| Name | What it is |
|---|---|
| Thinking | The paid fit, symmetrised (the mean of the two orientations). **Not calibrated** |
| Twin | The local open checkpoint on the same upload and settings without thinking, seed 0 (`local_twin.py`). **Calibrated** by the decided rule. Seeds 1–3 measure the fit noise; the 4-seed mean is a check. On 2022's matches its seed 0 reproduces the rating race's 2022 seed-0 fit, which was trained on the same rows: mean absolute difference 0.0000009 |
| Current best model | As decided ([speed-offset decision](../../decisions/2026-10-07-speed-nudge.md)): the local 58-input model walk-forward (season Y trained on 2013 to Y − 1), the 16-seed mean of the serve-speed study's fits. 2022–2023: the decided calibration slope. 2024–2026: both stages |

* **The decided calibration.** One slope per tour on the log-odds, fitted on the walk-forward model's out-of-sample forecasts of 2019 to Y − 1, applied to season Y (`serve_speed_tabpfn.score.Scorer.slopes`).
  * The twin is trained on 2013–2021, so it has no out-of-sample season before 2022. It takes these slopes: the same model, inputs and settings.
  * Its raw slope matches the walk-forward model's (in-sample on 2022–2026: 0.909 and 0.896 against 0.909 and 0.898).
* **The serve-speed offset** (`adaptive/adjust.py`, always the 28-day memory, the weekly feed's coefficients):
  * **The current best model:** logit q = s_tour,Y · η + b̃_Y · `spd_L`.
  * **Twin + offset:** the same rule on the twin's log-odds.
  * **Thinking + offset:** η_Thinking + b̃_Y · `spd_L`, with no slope, as the owner specified "noncalibrated".
  * **Its reach:** coefficients exist for 2024–2026 (b̃ 0.028, 0.029, 0.038). It is 0 for women, so it changes men's forecasts only.
* **The prices** (`books.py`; prices stay in gitignored files):
  * **Pinnacle:** tennis-data.co.uk's `PSW/PSL` as Stage 1 linked them. They are untimed, and they stop on 12 Jan 2026.
  * **BetOnline:** the last line OddsTrader recorded, linked and cleaned as in the [BetOnline-lines study](../betonline_lines/README.md). Uncertain closes are left out.
  * **Coherence and orientation:** a pair outside overround 1.00–1.20 gives no price. A's orientation was checked against the market average's odds on all 13,730 BetOnline-period rows.
  * **Excluded:** four rows whose tennis-data row has changed since Stage 1's snapshot.
* **The bet.** At each book's close, back the side whose expected return p·d − 1 is larger and above the threshold: 0 is primary, 2% and 5% are sensitivities. Completed matches only, so a retirement voids the bet. Checks: retirements settled on the player who advanced, and flat 1-unit stakes.
* **The owner's staking rule** (`common.stake`). The stake is 1/(d − 1) units on a favourite, to win 1 unit. On an underdog it is d / (2(d − 1)), which wins d/2.
  * **Why that underdog stake.** Kelly stakes (p·d − 1)/(d − 1) of the bankroll. If the edge is the same size in probability at every price, p = 1/d + δ, that is δ·d/(d − 1), proportional to d/(d − 1). Scaled to 1 unit at even money, that gives the underdog stake.
  * **On favourites** the owner's to-win-1 rule bets 2/d times this Kelly shape.

  | Decimal odds | 1.10 | 1.25 | 1.50 | 1.80 | 2.00 | 2.50 | 3.00 | 5.00 | 10.0 |
  |---|---|---|---|---|---|---|---|---|---|
  | Stake (units) | 10.00 | 4.00 | 2.00 | 1.25 | 1.00 | 0.83 | 0.75 | 0.63 | 0.56 |
  | Win (units) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.25 | 1.50 | 2.50 | 5.00 |

* **Order of work.** The scorer was written, and run on the free forecasts, before the paid call (`score_dry_run.log`). The local forecasts' returns were therefore seen before Thinking's existed; Thinking's were not. Three views were added after every result was in, at the owner's request or as checks: the top 50% of bets, BetOnline's 2026 alone, and the split by when BetOnline's last line was stamped.

## Results

### 1. Log loss at the close, base forecasts, 2022–2026 (23,819 matches)

| Comparison | Both tours | Men | Women |
|---|---|---|---|
| **Twin, calibrated → Thinking** | **+0.14 [−0.14, +0.43] tie** | +0.08 [−0.28, +0.43] tie | +0.22 [−0.22, +0.66] tie |
| Twin, 4 seeds, calibrated → Thinking | +0.06 [−0.17, +0.29] tie | −0.09 [−0.40, +0.23] tie | +0.21 [−0.15, +0.57] tie |
| Current best, stage 1 → Thinking | −0.01 [−0.30, +0.27] tie | −0.12 [−0.51, +0.27] tie | +0.10 [−0.32, +0.53] tie |
| Twin, raw → Thinking | +0.84 [+0.27, +1.40] better | +0.75 [+0.07, +1.43] better | +0.93 [+0.14, +1.73] better |
| Close, recalibrated → Thinking | +1.17 [+0.65, +1.68] better | +1.54 [+0.94, +2.14] better | +0.76 [−0.02, +1.54] tie |
| Close, recalibrated → Twin, calibrated | +1.02 [+0.39, +1.65] better | +1.47 [+0.76, +2.17] better | +0.54 [−0.41, +1.50] tie |
| Close, recalibrated → Current best, stage 1 | +1.18 [+0.54, +1.82] better | +1.66 [+0.92, +2.41] better | +0.66 [−0.30, +1.62] tie |

* **Each season, twin → Thinking:** 2022 +0.11, 2023 +0.17, 2024 +0.35, 2025 −0.25, 2026 +0.42. All are ties.
* **The fit's own noise.** Single twin seeds differ from seed 0 by −0.02 to +0.16 (one of three clears 0). So a gap of about 0.15 between two single fits is within the noise. Thinking is a single fit.
* **Agreement.** Thinking and the calibrated twin correlate 0.9986 in log-odds. They differ by 0.81 points of probability on average (1.67 at the 90th percentile), and change the favourite in 254 of 23,819 matches.

### 2. With the serve-speed offset

2024–2026, 13,734 matches; the offset changes men's forecasts only:

| Comparison | Both tours | Men | Women |
|---|---|---|---|
| **Current best model (both stages) → Thinking + offset** | **−0.05 [−0.45, +0.34] tie** | −0.27 [−0.79, +0.26] tie | +0.17 [−0.43, +0.78] tie |
| Twin + offset → Thinking + offset | +0.15 [−0.24, +0.54] tie | −0.07 [−0.57, +0.42] tie | +0.38 [−0.23, +0.99] tie |
| Close, recalibrated → Thinking + offset | +1.56 [+0.76, +2.35] better | +2.28 [+1.33, +3.22] better | +0.80 [−0.31, +1.90] tie |
| Close, recalibrated → Current best model | +1.61 [+0.64, +2.58] better | +2.54 [+1.37, +3.72] better | +0.62 [−0.80, +2.04] tie |
| Thinking → Thinking + offset (what the offset adds) | +0.21 [+0.07, +0.34] better | +0.40 [+0.14, +0.67] better | 0 |
| Current best, stage 1 → both stages | +0.19 [+0.06, +0.33] better | +0.38 [+0.11, +0.64] better | 0 |

Over 2022–2026, with the offset from 2024, the current best model → Thinking + offset is −0.00 [−0.29, +0.28], a tie. Against the recalibrated close, both are +1.29.

### 3. Does Thinking need calibration?

| | Men | Women |
|---|---|---|
| Thinking's slope on its 2022–2026 log-odds (in-sample, diagnosis only; 1 = calibrated) | 0.987 ± 0.023 | 0.988 ± 0.024 |
| The twin's, raw | 0.909 ± 0.021 | 0.896 ± 0.022 |
| The twin's, after the decided slope | 1.007 ± 0.024 | 0.955 ± 0.023 |

Scored on 2023–2026, with each forecast's own slope fitted walk-forward on its earlier test seasons:
* **Thinking raw → recalibrated:** −0.07 [−0.15, +0.01], a tie: no gain.
* **Twin raw → recalibrated:** +0.75 [+0.18, +1.33], better.
* **Both recalibrated, twin → Thinking:** +0.10 [−0.19, +0.39], a tie.

*Inferred.* Thinking departs from the close about as far as the calibrated twin does: the SD of its log-odds minus the close's is 0.186 for men and 0.168 for women, against 0.181 and 0.211. The raw twin departs much further (0.288 and 0.279). Thinking's search arrives where the slope takes the local model.

The women's decided slope still leaves the twin a little over-confident in 2022–2026 (0.955). Thinking's nominal lead for women (+0.22, a tie) is in that direction.

### 4. At Polymarket's price 24 hours out

2025–2026: 2,648 matches, the rating race's population (every match with both Polymarket prices, debut seasons out). Every forecast is fed that price in its odds column.

| Comparison | Both tours | Men | Women |
|---|---|---|---|
| Current best model → Thinking + offset | −0.37 [−1.39, +0.65] tie | −0.61 [−2.19, +0.96] tie | −0.08 [−1.20, +1.03] tie |
| Twin + offset → Thinking + offset | −0.40 [−1.40, +0.61] tie | −0.72 [−1.86, +0.42] tie | −0.01 [−1.39, +1.37] tie |
| 24-hour price, recalibrated → Thinking + offset | +2.78 [+0.76, +4.79] better | +4.08 [+2.02, +6.14] better | +1.23 [−2.57, +5.03] tie |
| 24-hour price, recalibrated → Current best model | +3.15 [+1.31, +4.99] better | +4.69 [+2.12, +7.26] better | +1.31 [−2.63, +5.25] tie |
| 24-hour price, recalibrated → Twin + offset | +3.18 [+0.74, +5.61] better | +4.80 [+2.31, +7.28] better | +1.24 [−2.97, +5.44] tie |

### 5. The return at the closes

The primary setting: the owner's staking rule, threshold 0, completed matches.

| Subset | Forecast | Pinnacle | BetOnline |
|---|---|---|---|
| All | Thinking + offset | +1.55% [+0.28, +2.87] | +4.24% [+2.41, +5.99] |
| | Current best model | +1.50% [+0.38, +2.73] | +2.93% [+1.20, +4.77] |
| | Twin + offset | +1.59% [+0.59, +2.70] | +3.40% [+1.08, +5.70] |
| | Close, recalibrated (control) | −1.96% [−4.72, +0.87] | −2.41% [−6.48, +2.07] |
| | Close, de-vigged (control) | −7.94% [−11.58, −4.54] | −5.04% [−9.87, +0.03] |
| Men | Thinking + offset / current best / twin + offset | +2.02% / +2.48% / +2.45% | +5.17% / +4.60% / +5.65% |
| Women | the same three | +0.88% / +0.73% / +0.96%, ties | +3.00% / +1.23% / +1.31%, ties |
| 2022–2023 (no offset exists) | the same three | +0.89% / +1.54% / +1.32% | — |
| 2024 on (offset active) | the same three | +2.26% / +1.46% / +1.94% | as All |
| 2024 on, men | the same three | +2.55% / +2.65% / +3.21% | as Men |

**Each forecast against Thinking's, in percentage points** (paired; all ties): current best −0.04 at Pinnacle and −1.31 [−2.57, +0.05] at BetOnline; twin + offset +0.05 and −0.84.

**By season** (Thinking + offset / current best):
* Pinnacle: 2022 −1.01% / +0.30%, 2023 +2.57% / +2.70%, 2024 +2.55% / +1.85%, 2025 +1.93% / +1.18%. Its 2026 is 167 matches in January.
* BetOnline: 2024 +2.62% / +2.85%, 2025 +3.21% / +1.67%, 2026 +8.71% / +5.76%.
* In 2022 at Pinnacle the twin beat Thinking by +1.64 points [+0.19, +3.10]. In 2025 and 2026 at BetOnline Thinking led the current best. These are single cells among many.

**Thresholds and staking** (Thinking + offset / current best / twin + offset):

| Setting | Pinnacle | BetOnline |
|---|---|---|
| Edge above 2% | +3.66% / +3.75% / +2.99% | +7.56% / +8.59% / +6.66% |
| Edge above 5% | +10.10% / +9.68% / +9.29% (1,476 / 1,747 / 1,844 bets) | +12.04% / +13.93% / +12.20% (852 / 1,064 / 1,046 bets) |
| **Top 50% of bets by edge** (above each forecast's median edge) | **+4.08% [+1.61, +6.33] / +3.87% [+1.72, +6.07] / +2.98% [+0.73, +5.57]**; edges above 1.86% / 1.92% / 2.01%; 4,714 / 5,093 / 5,150 bets | **+7.15% [+3.37, +11.13] / +8.44% [+5.40, +11.64] / +7.19% [+4.31, +9.94]**; edges above 1.93% / 2.17% / 2.20%; 2,297 / 2,444 / 2,442 bets |
| Flat 1-unit stakes | +2.90% / +2.82% / +2.46% | +5.92% / +4.69% / +5.00% |
| Retirements settled on the player who advanced | +1.20% [−0.12, +2.58] / +1.01% [−0.21, +2.20] / +1.13% [−0.01, +2.22] | +3.99% / +2.64% / +3.04% |

**The top 50% of bets** is the owner's request of 8 Oct 2026: bet only when the edge is past a threshold that keeps half of the bets.
* **The threshold** is each forecast's median edge among the bets it would make. It reads the edges only, never a result.
* **The check.** For a season it is also set from the earlier seasons' bets alone, which a bettor could have done (the next table).
* **Profit.** The top half earns most of the profit on a quarter of the stake. The bottom half (edges between 0 and the median) roughly breaks even at Pinnacle: +0.54% for Thinking + offset, +0.66% for the current best. At BetOnline it returns +2.87% and +0.96%.

**Claimed edge against realized return.** The mean edge a forecast claims for its bets, against what they returned (Thinking + offset / current best):

| Bets taken | Pinnacle, claimed | Pinnacle, realized | BetOnline, claimed | BetOnline, realized |
|---|---|---|---|---|
| Edge above 0 | 2.74% / 2.89% | +1.55% / +1.50% | 3.11% / 3.44% | +4.24% / +2.93% |
| Edge above 2% | 4.81% / 5.00% | +3.66% / +3.75% | 5.48% / 5.74% | +7.56% / +8.59% |
| Top 50% by edge | 4.66% / 4.92% | +4.08% / +3.87% | 5.38% / 5.94% | +7.15% / +8.44% |
| Edge above 5% | 8.05% / 8.23% | +10.10% / +9.68% | 9.03% / 9.27% | +12.04% / +13.93% |

*Inferred.* Realized returns rise with the claimed edge and are roughly its size, which is what a real edge looks like rather than noise. The same selection caveats apply (below).

**BetOnline in 2026 alone:** 1 Jan – 28 Jul 2026, 3,190 completed matches, 9 four-week blocks. Seven months and 9 blocks make these intervals too narrow; read them as rough.

| Rule | Thinking + offset | Current best model | Twin + offset | Price control (recalibrated close) |
|---|---|---|---|---|
| Edge above 0 | **+8.71%** [+5.99, +12.50]; 1,203 bets, +174 units | **+5.76%** [+3.11, +9.35]; 1,323 bets, +129 | +9.03% [+6.02, +12.09]; 1,260 bets, +181 | +1.09% [−6.30, +9.57] |
| Top 50% by edge (2026's own median edge) | **+11.84%** [+6.50, +17.44]; edge > 2.18%, 601 bets, +84 | **+7.18%** [+2.01, +11.96]; edge > 2.63%, 661 bets, +50 | +6.45% [+1.72, +10.65]; 630 bets, +44 | +1.16% |
| Top 50% by edge, threshold from 2024–2025 bets only | **+12.00%** [+7.08, +18.00]; edge > 1.84%, 666 bets, +97 | **+9.75%** [+2.82, +16.58]; edge > 2.03%, 773 bets, +81 | +7.19% [+2.70, +11.87]; 690 bets, +57 | +1.78% |
| Edge above 0, men / women | +7.95% / +9.61% | +6.52% / +5.04% | +10.55% / +7.83% | −0.74% / +2.69% |

* **Thinking against the current best in 2026:** −2.95 [−4.97, −1.22] points at edge above 0, and −4.66 [−7.81, −1.70] for the top half on 2026's own median. Thinking was better in that season. With the threshold set on earlier seasons it is −2.25 [−5.79, +1.05], a tie.
* **Over 2024–2026 the two tie** (−1.31 [−2.57, +0.05]). One season, chosen after the fact, is not evidence for Thinking.
* **2026 was good for everyone.** The price control made +1.09% there, against −5.27% and −2.42% in 2024 and 2025. Part of 2026's return is the season, not the model.

**BetOnline's "close" is its last recorded line,** and 4,791 of those lines were stamped more than an hour before the listed start. A stale line beside the true closing average would be a look-ahead no bettor has. The return does not depend on it:
* lines stamped within an hour of the start: +4.00% / +2.85% / +3.55%;
* lines stamped earlier: +4.52% / +3.00% / +3.23%;
* the price control loses on both (−2.32% and −2.63%).

### 6. Men and women separately

The owner's request of 8 Oct 2026. The speed offset is 0 for women, so for women "Thinking + offset" is Thinking, and the current best model is its first stage with the decided slope.

**Log loss** (positive = Thinking better):

| Comparison | Men | Women |
|---|---|---|
| Twin, calibrated → Thinking, 2022–2026 | +0.08 [−0.28, +0.43] tie | +0.22 [−0.22, +0.66] tie |
| Current best, stage 1 → Thinking, 2022–2026 | −0.12 [−0.51, +0.27] tie | +0.10 [−0.32, +0.53] tie |
| Current best (both stages) → Thinking + offset, 2024–2026 | −0.27 [−0.79, +0.26] tie | +0.17 [−0.43, +0.78] tie |
| The same at Polymarket's 24-hour price, 2025–2026 | −0.61 [−2.19, +0.96] tie | −0.08 [−1.20, +1.03] tie |
| Close, recalibrated → Thinking + offset, 2024–2026 | +2.28 [+1.33, +3.22] better | +0.80 [−0.31, +1.90] tie |
| Close, recalibrated → Current best, 2024–2026 | +2.54 [+1.37, +3.72] better | +0.62 [−0.80, +2.04] tie |
| What the speed offset adds, 2024–2026 (to Thinking / to the current best) | +0.40 / +0.38, both better | 0 |
| Calibration slope: Thinking / twin raw / twin calibrated | 0.987 / 0.909 / 1.007 | 0.988 / 0.896 / 0.955 |

* **Seasons.** Every season is a tie for both tours except one: men's 2025, where the twin beat Thinking, −0.75 [−1.49, −0.02].
* **Men** have an edge over the closing price; Thinking and the local model share it equally.
* **Women** have no clear edge over the close in log loss.

**The return**, owner's staking, completed matches; Thinking + offset / current best model:

| | Men, Pinnacle (10,203 matches) | Men, BetOnline (6,557) | Women, Pinnacle (9,399) | Women, BetOnline (6,067) |
|---|---|---|---|---|
| **Edge above 0** | **+2.02%** [+0.62, +3.45] / **+2.48%** [+0.78, +4.30] | **+5.17%** [+3.40, +7.43] / **+4.60%** [+2.19, +7.43] | +0.88% [−1.18, +3.01] / +0.73% [−0.80, +2.21] | +3.00% [−0.68, +6.28] / +1.23% [−1.78, +3.94] |
| Bets; profit (units) | 5,052; +259 / 5,372; +304 | 2,460; +258 / 2,672; +246 | 4,377; +80 / 4,814; +114 | 2,134; +113 / 2,216; +65 |
| **Top 50% by edge** | **+4.77%** [+2.11, +7.36] / **+6.15%** [+2.86, +9.53] | **+8.54%** [+4.21, +13.15] / **+9.76%** [+4.60, +15.49] | +3.27% [−0.67, +7.22] / +2.06% [−0.53, +4.85] | +5.33% [−0.87, +12.03] / +5.91% [+0.72, +10.84] |
| Edge above 5% | +13.11% / +13.47% | +15.06% / +18.76% | +6.39% / +3.90% | +8.58% / +5.93% |
| Retirements settled on the player who advanced | +1.71% [+0.39, +3.03] / +2.03% [+0.37, +3.61] | +4.96% / +4.49% | +0.49% / +0.20% | +2.70% / +0.75% |
| Closing price alone (control), edge above 0 | −1.47% | −4.87% | −2.50% | −0.36% |
| Thinking + offset's bets if the book's own price were right: expected; luck's 95% range | −2.3%; −4.4% to −0.4% | −3.7%; −7.6% to −0.5% | −2.6%; −4.8% to −0.6% | −3.7%; −7.7% to −0.2% |

* **Every Thinking-versus-current-best difference above is a tie.**
* **Men make money at both books,** and the result survives settling retirements.
* **Women's bets beat the books' prices but do not clear the margin reliably.** At Pinnacle they return +0.7% to +0.9%, above the −4.8% to −0.6% that luck gives against Pinnacle's own price. Every women's interval on profit still includes 0.

**BetOnline in 2026 alone, by tour** (Thinking + offset / current best; price control last):

| Rule | Men (1,640 matches) | Women (1,550 matches) |
|---|---|---|
| Edge above 0 | +7.95% [+3.25, +13.06], 657 bets, +85 / +6.52% [+2.21, +10.95], 739 bets, +71; price −0.74% | +9.61% [+6.05, +13.74], 546 bets, +88 / +5.04% [+0.36, +9.53], 584 bets, +58; price +2.69% |
| Top 50%, threshold from the same tour's 2024–2025 bets | +9.20% [+2.02, +19.35], 361 bets / +4.95% [−4.24, +13.71], 451 bets; price −1.20% | +15.28% [+6.43, +23.85], 302 bets / +12.44% [+2.13, +22.04], 318 bets; price +4.39% |

* **Men in 2026** look like their other seasons.
* **Women in 2026** are well above their 2024–2025 returns, and the women's price control was positive too: a good season for women's favourites at BetOnline rather than a new edge.

### 7. Why the price-only control can show a profit

The control bets the market-average close, recalibrated, against one book's close. It can only find sides where that book's price differs from the other books' average: a little line shopping. That is worth much less than BetOnline's 3.8% margin, so its long-run expectation is negative. Over 2024–2026 it returned −2.41%; at Pinnacle over 2022–2026, −1.96%.

To separate luck from edge, each set of bets was replayed 1,000 times with outcomes drawn from the book's own margin-free price, as if that price were exactly right (`luck_lo`, `luck_hi` in `roi.csv`; matches independent):

| Bets | Actual | Expected if the book's price is right | Luck's 95% range |
|---|---|---|---|
| Price control, BetOnline 2026, top 50% (190 bets) | +1.78% | −3.69% | −16.5% to +9.5% |
| Price control, BetOnline 2024–2026 (1,405 bets) | −2.41% | −3.53% | −8.0% to +0.7% |
| Price control, Pinnacle 2022–2026 (3,984 bets) | −1.96% | −2.60% | −5.5% to +0.2% |
| Current best, BetOnline 2024–2026 (4,888 bets) | +2.93% | −3.70% | −5.9% to −1.4% |
| Current best, Pinnacle 2022–2026 (10,186 bets) | +1.50% | −2.43% | −3.8% to −1.1% |
| Thinking + offset, BetOnline 2026 (1,203 bets) | +8.71% | −3.79% | −9.3% to +1.3% |

* **The control's +1.78% in 2026 is luck.** On 190 bets anything from −16% to +9% happens by chance, around an expectation of −3.7%.
* **The models' returns are far outside luck's range** against each book's own price. This replay ignores the clustering within weeks that the block intervals keep, so it is the less cautious of the two measures. The selection caveats below still apply.

## What it does and does not show

* **Thinking ties the free model.** With the slope, the 16 seeds and the speed offset, the free local model is level with Thinking in log loss, at the close and at the 24-hour price. It is also level in money at both books. On these inputs, a paid fit adds nothing detectable. The intervals rule out a Thinking lead above about +0.3–0.4 mLL at the close.
* **The returns are not an untouched holdout.**
  * The 58 inputs were chosen by studies that had seen 2022–2026.
  * The calibration rule and the offset's 28-day memory were decided after seeing 2022–2026 and 2024–2026 results.
  * The local forecasts' returns were seen before this report's design was final; Thinking's were not.
  * Read the returns as optimistic upper bounds, not as expected profit.
* **Archived quotes, not fills.**
  * Pinnacle's prices are tennis-data's untimed "most recent before play"; BetOnline's are its last recorded line.
  * Limits, account restrictions and line moves at the moment of a bet are not in the data.
  * The model's odds input is the market-average close, so these bets assume it is computed from prices at the moment of betting, just before the start.
* **Retirement settlement is not verified.** Books' rules differ. With retirements settled on the player who advanced, the Pinnacle returns fall to about +1.0–1.2% and their intervals reach 0.
* **Many cells.** Two books, two populations, four bet rules, two stakings, tours, periods and seasons were examined. The primary setting was fixed before the paid call; the top-50% rule and the 2026 view came after the results. Single-season and single-tour cells that clear 0 are expected by chance.
* **One Thinking fit, one seed.** Its run-to-run variation is unknown. The two 54-input Thinking fits agreed to a log-odds correlation of 0.9999.
* **Women.** No return for women is distinguishable from zero, and the offset never touches them.

## Cost and run record

* **The run** (`thinking_run.json`, `thinking/`): fit 258 s (queue 0.8 s), prediction 44 s, 338 s end to end.
* **Tokens:** quoted 676,563 (fit 472,188, prediction 204,375); billed 169,141.
* **The server** echoed the requested configuration and reported `n_estimators: 2` at the top level of its metadata, as for the earlier fits.
* **The key.** The VS Code process held a different `TABPFN_TOKEN` from the one saved in the Windows user environment. The saved key was passed to the call's process and accepted. Neither was printed.
* **The twin's four local fits** took about 40 seconds each on the RTX 5090.

## Files and run

| What | Where |
|---|---|
| Shared definitions: inputs and their swap, the staking rule, the upload | `src/eda/tabpfn_thinking58/common.py` |
| The upload and its checks | `build_frame.py` → `data/studies/tabpfn_thinking58/upload/`, `manifest.json` |
| The prices at Pinnacle and BetOnline | `books.py` → `book_odds.parquet` (gitignored), `book_counts.json` |
| The non-thinking twin (env `tennis-tabpfn-local`) | `local_twin.py` → `local/seed0..3.npz`, `local_twin.log` |
| The paid call (env `tennis-tabpfn`) and its guard | `dispatch.py`, `guard.py` → `quotes.json`, `thinking/`, `thinking_run.json`, `thinking_run.log` |
| Scoring and the return | `score.py` → `results.json`, `results.csv`, `roi.csv`, `predictions.parquet`, `predictions_early.parquet`; `score_dry_run.log` is the run before the paid call |
| The tables in this report | `tables.py` → `tables.md` |
| Tests | `test/tabpfn_thinking58/`: 22 in `tennis` (the SDK check is skipped there), 15 guard tests in `tennis-tabpfn` |

Run order, from the repository root:

```bash
./python.sh src/eda/tabpfn_thinking58/build_frame.py
./python.sh src/eda/tabpfn_thinking58/books.py
./python_tabpfn_local.sh src/eda/tabpfn_thinking58/local_twin.py
./python_tabpfn.sh src/eda/tabpfn_thinking58/dispatch.py --quote                  # free
./python_tabpfn.sh src/eda/tabpfn_thinking58/dispatch.py --run --spend-tokens     # re-uses the saved predictions
./python.sh src/eda/tabpfn_thinking58/score.py
./python.sh src/eda/tabpfn_thinking58/tables.py
./python.sh -m pytest test/tabpfn_thinking58 -p no:cacheprovider
```

The paid call's predictions are saved. Re-running `dispatch.py --run` re-uses them and sends nothing.
