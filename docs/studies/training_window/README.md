# Should the current best model train on recent seasons only?

8 October 2026 · Written for the owner · Research evidence, not a decision.

**The owner's question.** The current best model trains each season on almost all the past data. Should it use only more recent seasons? The reason given: "Because the close is an input, the model learns from its training seasons how far to move away from it. If the value of moving away changes over time, that learned amount goes stale. Trained on softer-close years, it would move too far once the close sharpens; trained the other way round, it would move too little."

**What the model trains on today.** Season Y is fitted on every main-tour match with a closing price from 2013 to Y − 1:
* 27,813 matches for 2019, 50,003 for 2024 and 60,249 for the live 2026 fits.
* Not used as training rows:
  * seasons before 2013 (2010–2012 only warm up the ratings);
  * men's 2018 (the frame has no odds for it yet);
  * matches without a closing price (qualifying, lower tiers).

**The test.** The current model, refitted on seven other training sets:

| Arm | Training rows for season Y | Rows for 2024 |
|---|---|---|
| **exp** (the current model) | every season 2013 .. Y − 1 | 50,003 |
| last7, last5, last3 | only the last 7, 5 or 3 seasons | 29,737 / 22,190 / 14,840 |
| rand7, rand5, rand3 (size controls) | a random draw from 2013 .. Y − 1 the size of last7, last5 or last3 (a new draw per seed) | the same as lastN |
| decay4 (recency-weighted) | each match kept with probability ½^(age / 4), age in seasons (TabPFN takes no sample weights) | 24,154 |

* **The settings:** every arm has the 58 inputs, the decided settings and seeds 0–3. Season Y is fitted on earlier seasons only.
* **Both stages.** Each arm gets its own speed adjustment by the decided rule (28-day memory, weekly feed), refitted walk-forward on that arm's own forecasts of 2019 .. Y − 1.
* **Scored** on 2020–2024: 22,265 matches, debut seasons out. The comparisons are against the current model (both stages), the recalibrated average close and Pinnacle.
* **Seasons ≤ 2024 only.** 2025–2026 is the [proposed clean holdout](../clean_holdout_rebuild/README.md), so nothing from it is read.
* **Units.** mLL per match; **+ = the named arm is better**. A 95% interval spanning 0 is a tie. The intervals are over four-week blocks, plus the seeds' variance.
* **The reading rules** were written before any score was computed (`data/studies/training_window/reading_rules.md`).

**Note for reviewers (9 Oct 2026): a flaw in this study's intervals, found after it ran. The study was not re-run.**
* **The flaw.** The arm-against-arm intervals add both arms' seed-to-seed variance as if their seed noise were independent. That covers each arm against the current model, the recency pairs, stage 1 alone and the speed adjustment's side check. Every arm used the same TabPFN seeds (random states 0–3), so much of that noise is shared and cancels in the difference. Adding both counts it twice.
  * Found by the adoption framework's statistics review ([finding 1](../adoption_framework/review_statistics.md)). With the same interval code, a model compared with itself got ±0.087 mLL instead of 0.
  * The most is shared where both sides are the current model's own fits: the two-part recalibrations and the speed adjustment. The least is shared by the random-draw arms, whose training draw changes with the seed.
* **What it does.** Those intervals are too wide; the estimates are right. Not affected: the gains over the average close and Pinnacle (a price has no seeds), and the realisation coefficients.
* **What it can change.** The stored results hold no interval without the seed term, so the size is unknown here.
  * On 2020–2024 every estimate against the current model is negative. Narrower intervals there can only strengthen the answer: keep the expanding window.
  * The rows nearest to 0 could come to read worse: rand3, −0.30 [−0.61, +0.01]; the two-part recalibration on the last two seasons, −0.25 [−0.56, +0.06]; the speed adjustment, men 2020–2024, −0.30 [−0.68, +0.08].
  * For the speed adjustment on the reference model, the review found the seed part small: the SE fell only from 0.169 to 0.162 when paired.
  * The era rows could come to clear 0 either way: the short windows lean better in 2020–21 and worse in 2022–23.
* **Not re-run, on purpose.** `score.py` now pairs the seed term between two forecasts, and keeps the old interval as `lo_unpaired` / `hi_unpaired` ([checklist](../adoption_framework/checklist.md), item 1). A re-run would read 2020–2024 only, and would overwrite `results.csv`.

## The answer in short

* **No: keep training on every season from 2013.**
  * No shorter or recency-weighted window beat the current model.
  * Every estimate is slightly worse, and every interval spans 0.
  * The last 3 seasons lost clearly in 2022–23.
* **The mechanism is real.** The training seasons do set how far the model moves away from the close:
  * trained on the last 5 seasons, TabPFN moves 33% further; on the last 3, 51% further;
  * a random draw of the same size moves no further (2% and 9% less);
  * so the recent seasons, not the smaller training set, teach the bigger moves.
* **The size of the move.** The realisation coefficient measures how much of the model's disagreement with the close comes true (1 = right-sized, below 1 = too far, above 1 = not far enough). These are TabPFN's own moves, before the speed adjustment.
  * **Against the books' average close** (the model's input), the current model moves a little too little: **1.26** (SE 0.18). The last 7 and last 5 seasons bring that to about 1 (1.04 and 0.94). Your mechanism works as described.
  * **Against Pinnacle's sharper price**, the current model is already right-sized: **0.98** (SE 0.14). The recent windows over-shoot: 0.85, 0.80 and, for the last 3 seasons, 0.67.
* **The extra moves add no information.** Each version can be given its best possible size in hindsight: one scale, fitted in-sample on 2020–2024.
  * At their best sizes, against the average close: the current model 1.50 mLL, the last 5 seasons 1.37, the last 3 seasons 1.18. No window beats the current model.
  * The current model's own sizing error is worth only 0.06: 1.44 actual against 1.50 at its best size.
  * Men show it most clearly. The last 5 seasons size the men's moves exactly right (1.00), and still gain less over the close than the current model: 1.58 against 1.71.
  * Correcting the size by cutting the window costs more information than the correction is worth.
* **The value of moving away bounces from season to season, without a trend.**
  * The current model's realisation by season was 1.78, 1.51, 0.84, 1.19 and 1.34, a spread consistent with sampling noise (p = 0.64).
  * A short window learns its few seasons' level and carries it forward. In 2022–23 the last-3 model's windows were 58–59% matches from 2020–21, the seasons in which moving away paid most. Its moves were then about twice too big (realisation 0.41 and 0.53), and it lost 1.14 mLL.
* **Row for row, recent matches are worth no more than old ones.** The last N seasons against a random draw of the same size: −0.14, −0.02 and −0.08, all ties.
* **The training size matters little above about 20,000 matches.**
  * Dropping 31–56% of the matches at random (rand5) cost 0.07, a tie.
  * Cutting to 10,000–15,000 matches (rand3) cost 0.30 [−0.61, +0.01], just short of clear.
* **The cheap alternative also fails.** It re-sizes the current model's move away from the close on recent seasons without refitting (rebuild protocol Q29). It tied:
  * fitted on 2019 .. Y − 1: −0.07;
  * fitted on the last two seasons: −0.25, and worse in 2022–23.
  * The walk-forward scales are as noisy as the season-to-season realisation.

## The measurements

### Against the current model (both stages)

Both tours. + = the named arm is better than the current model.

| Arm | 2020–2024 | 2020–21 | 2022–23 | 2024 |
|---|---|---|---|---|
| last7 | −0.15 [−0.39, +0.09] tie | +0.01 [−0.18, +0.19] tie | −0.27 [−0.69, +0.14] tie | −0.12 [−0.82, +0.57] tie |
| last5 | −0.09 [−0.50, +0.32] tie | +0.34 [−0.15, +0.82] tie | −0.46 [−1.23, +0.32] tie | +0.03 [−0.76, +0.82] tie |
| last3 | −0.38 [−0.99, +0.22] tie | +0.61 [−0.37, +1.58] tie | **−1.14 [−2.24, −0.04] worse** | −0.27 [−1.00, +0.47] tie |
| rand7 | −0.01 [−0.21, +0.18] tie | −0.06 [−0.20, +0.07] tie | +0.03 [−0.28, +0.34] tie | −0.02 [−0.46, +0.41] tie |
| rand5 | −0.07 [−0.31, +0.18] tie | −0.19 [−0.67, +0.30] tie | +0.11 [−0.18, +0.39] tie | −0.25 [−0.79, +0.29] tie |
| rand3 | −0.30 [−0.61, +0.01] tie | −0.40 [−1.03, +0.23] tie | −0.27 [−0.75, +0.21] tie | −0.22 [−1.13, +0.69] tie |
| decay4 | −0.06 [−0.30, +0.19] tie | +0.16 [−0.12, +0.44] tie | −0.14 [−0.63, +0.36] tie | −0.19 [−0.57, +0.20] tie |
| Two-part recalibration, 2019 .. Y − 1 | −0.07 [−0.32, +0.17] tie | −0.07 [−0.59, +0.44] tie | −0.15 [−0.50, +0.19] tie | +0.08 [−0.33, +0.49] tie |
| Two-part recalibration, last two seasons | −0.25 [−0.56, +0.06] tie | −0.07 [−0.59, +0.44] tie | **−0.53 [−1.04, −0.01] worse** | +0.05 [−0.45, +0.55] tie |

* **By tour,** 2020–2024, the last 7, 5 and 3 seasons:
  * men: −0.25, −0.16 and −0.36;
  * women: −0.04, −0.02 and −0.41;
  * all ties.
* **On TabPFN alone** (calibrated, no speed adjustment), the last 7, 5 and 3 seasons give −0.14, −0.08 and −0.37, all ties. The speed adjustment does not drive the result.
* **Recency at a fixed size,** the last N seasons against a random draw of the same size, 2020–2024: −0.14 [−0.43, +0.16], −0.02 [−0.50, +0.45] and −0.08 [−0.77, +0.60], all ties. The short windows win in 2020–21 and lose in 2022–23; neither era is clear.

### How far each version moves, and how much of it comes true

TabPFN's own forecast (calibrated, before the speed adjustment), 2020–2024, both tours.
* **Spread:** the standard deviation of the forecast's log-odds minus the recalibrated close's.
* **Realisation:** 1 = right-sized, below 1 = too far, above 1 = not far enough.
* **Gain:** mLL over the recalibrated average close; + = the forecast is better.
* **At its best size:** the gain with the realisation fitted in-sample, so every version's moves are scaled right in hindsight.

| Arm | Spread | Realisation, average close | Realisation, Pinnacle | Gain over the average close | At its best size |
|---|---|---|---|---|---|
| **exp** (the current model) | 0.129 | **1.26** (SE 0.18) | **0.98** (SE 0.14) | **+1.44 [+0.80, +2.07] better** | **1.50** |
| last7 | 0.143 (+11%) | 1.04 (0.16) | 0.85 (0.13) | +1.29 [+0.57, +2.02] better | 1.29 |
| last5 | 0.171 (+33%) | 0.94 (0.14) | 0.80 (0.12) | +1.36 [+0.55, +2.17] better | 1.37 |
| last3 | 0.195 (+51%) | 0.76 (0.12) | 0.67 (0.11) | +1.07 [+0.11, +2.03] better | 1.18 |
| rand7 | 0.128 (−1%) | 1.28 (0.17) | 0.99 (0.14) | +1.42 [+0.81, +2.04] better | 1.49 |
| rand5 | 0.126 (−2%) | 1.30 (0.19) | 0.98 (0.15) | +1.37 [+0.74, +2.00] better | 1.44 |
| rand3 | 0.117 (−9%) | 1.18 (0.18) | 0.88 (0.15) | +1.13 [+0.55, +1.70] better | 1.15 |
| decay4 | 0.141 (+9%) | 1.15 (0.17) | 0.92 (0.14) | +1.38 [+0.71, +2.06] better | 1.41 |

* **A smaller random draw moves less, not more.** TabPFN holds closer to the close when it has fewer matches.
* **Men** (realisation against the average close):
  * the current model 1.40 (SE 0.20);
  * the last 5 seasons 1.00 (0.18), gaining 1.58 against the current model's 1.71.
* **Women:** the current model 1.10 (0.23); the last 5 seasons 0.87 (0.17).
* **The decided two-stage forecast:**
  * **The realisation** against the average close is 1.10 for the current model, and 0.93, 0.85 and 0.70 for the last 7, 5 and 3 seasons. Against Pinnacle it is 0.87, and 0.76, 0.73 and 0.62.
  * **The gain** over the average close is +1.28 [+0.58, +1.97]; over Pinnacle +0.94 [+0.22, +1.66]. Both are better than the price.
  * **The speed term** adds a disagreement of its own for men, which went the wrong way in 2023 (side finding below).

### By season

TabPFN's realisation against the average close (1 = right-sized). SEs: 0.27–0.62 for the current model, 0.19–0.65 for the others.

| Season | exp | last7 | last5 | last3 | rand5 | rand3 |
|---|---|---|---|---|---|---|
| 2020 | 1.78 | 1.78 | 1.65 | 1.74 | 1.55 | 1.60 |
| 2021 | 1.51 | 1.41 | 1.42 | 1.09 | 1.49 | 1.34 |
| 2022 | 0.84 | 0.76 | 0.62 | **0.41** | 0.95 | 0.78 |
| 2023 | 1.19 | 0.82 | 0.70 | **0.53** | 1.36 | 1.25 |
| 2024 | 1.34 | 1.05 | 0.99 | 0.96 | 1.29 | 1.28 |
| Spread across seasons beyond noise | p = 0.64 | p = 0.47 | p = 0.23 | **p = 0.02** | p = 0.86 | p = 0.71 |

* **The current model's season-to-season swings fit sampling noise around a constant.** Against Pinnacle: 1.28, 0.94, 0.63, 1.02, 1.22; p = 0.68.
* **The short windows' moves grow as their windows fill with 2020–21:**
  * the last 3 seasons' spread rose from 0.117 (2020) to 0.19–0.22 (2021–2023);
  * the last 5 seasons' from 0.124 to 0.20 (2023–24);
  * the current model's stayed at 0.12–0.14.
* **That is the owner's mechanism, run by noise.** The learned move does follow the training seasons. What it followed here was two seasons' luck, not a lasting change in the market.

## A side finding: the speed adjustment's record on 2020–2024

The scorer also measures what the speed adjustment added walk-forward: the current model's two stages against its calibrated stage 1, men. The serve-speed study related speed to match results only once, on 2024–26, so these seasons were never scored.

| Men | 2020 | 2021 | 2022 | 2023 | 2024 | 2020–2024 |
|---|---|---|---|---|---|---|
| Speed adjustment against the calibrated base (+ = the adjustment helped) | −0.03 tie | −0.04 tie | **+0.21 [+0.02, +0.40] better** | **−1.58 [−3.06, −0.09] worse** | +0.11 [−0.36, +0.58] tie | −0.30 [−0.68, +0.08] tie |
| Shrunk coefficient b̃ in force | 0.022 | 0.019 | 0.007 | 0.076 | 0.028 | |

* **2020–21 barely move.** Little speed data existed before ManTennisData (from 2021).
* **2023's loss sits in the large speed gaps.**
  * The 179 matches (7%) with |`spd_L`| above 2 lost 14.3 mLL each: 61% of the season's loss.
  * In 2022 the same group gained 2.8 each.
* **Part of it is today's impossible speed records** (`speed_check.py`).
  * Today's corrupt-data review listed 130 rows: 107 distinct panel records, 105 of them used by the panel, 51 of those in 2023.
  * The 189 men's 2023 matches within 60 days of one lost 7.5 mLL each: 34% of the loss.
  * The other 2,483 matches still lost 1.1 each.
* **What it does and does not say.**
  * It does not overturn the pre-registered 2024–26 result.
  * It says the adjustment's walk-forward record before 2024 is not positive, and that the impossible records hurt.
  * Applying the exclusions to the speed panel and refitting the adjustment were left to the owner by the [corrupt-data decision](../../decisions/2026-10-08-corrupt-data-fixes.md).

## What it means

* **For now, the expanding window stays.**
  * Within 2020–2024 there is no detectable drift in the value of moving away from the close for a recent window to track.
  * Following the last few seasons adds their noise.
  * The long window averages it out. Its moves are right-sized against Pinnacle and a little timid against the softer average close, and that timidity is worth about 0.06 mLL.
* **The failure mode to watch is still the owner's.** If the market sharpens for good, or absorbs what the features measure, the current model will over-react season after season. The sign would be a realisation below 1 in every new season, against the average close and against Pinnacle.
  * Track it walk-forward each season; the scorer here computes it.
  * Today it shows no trend.
  * One low season means nothing: 2022 was 0.84, and 2024 was back at 1.34.
* **More data is not the reason to keep the old seasons either.** Above about 20,000 matches, more rows add little. The reason is that recent seasons on their own teach the model to over-react.
* **For the rebuild protocol** (Q28, Q29):
  * this is D-only evidence for the neutral defaults: the expanding window, and one slope per tour;
  * if the window stays an axis, these arms are its menu, and on D none of them wins.

## What it does not show

* **2025–2026 are not read** (the proposed holdout). Nor is any early price: Polymarket's 24-hour price exists only in 2025–2026.
* **The early seasons.** The scored seasons are 2020–2024. Whether the 2015–2019 tie with the close was a training-size effect is the [feature-provenance plan](../feature_provenance/plan.md)'s phase 2, still open.
* **One learner.** TabPFN learns in context from the rows it is given. A parametric model could use a window differently.
* **Four seeds per arm.** The decided model averages 16. Every arm here has 4, so they compare like with like.
* **The 30 September frame.** It still holds the WTA 2015 rows corrected at source today. Short windows drop them; the random draws keep some. Nothing suggests that mattered: the random draws tie the current model.
* **The best-size gains are in-sample.** They are a diagnostic of information content, not a forecast anyone could have made.
* **No money.** A log-loss gain against an archived close is not a betting return.

## Checks

* **Inputs.** The 24 stored fits of the current model match this harness's rebuilt inputs: columns, shapes, match order, settings, and 6 of 6 stored fingerprints (`input_check.json`).
* **Reproduction.** The 16 refits that share the current model's rows (last7 and rand7, 2019–2020) equal the stored forecasts exactly, with a maximum difference of 0.0.
* **Stage 2.** The current model's 2024 coefficients equal the published ones exactly (`serve_speed_tabpfn/adaptive/coefficients.json`).
* **Tests.** 75 pass (`./python.sh -m pytest test/training_window -q`). They cover:
  * no arm ever trains on season Y or later;
  * the window and size-control rules;
  * the decay sampling;
  * the stage-2, realisation and two-part fits on synthetic data;
  * the season ≤ 2024 reader.
* **Compute.** 168 new local fits in 29 minutes (RTX 5090).

## Code and outputs

| What | Where |
|---|---|
| Arms, frame reader (seasons ≤ 2024, asserted), stage-2 rule | `src/eda/training_window/common.py` |
| Fit plan, CPU input check, GPU runner (`tennis-tabpfn-local` env) | `src/eda/training_window/fits.py` |
| Scorer and checks | `src/eda/training_window/score.py` |
| The side check on the speed adjustment's 2023 loss | `src/eda/training_window/speed_check.py` → `speed_check.json` |
| Fits, logs | `data/studies/training_window/local/`, `fits.log`, `score.log` |
| Results by comparison, window and tour; per-season coefficients; checks | `data/studies/training_window/results.csv`, `season_params.csv`, `results.json`, `input_check.json`, `fit_plan.csv` |
| Reading rules (fixed before scoring) | `data/studies/training_window/reading_rules.md` |

Run:

```
./python.sh src/eda/training_window/fits.py --plan
./python.sh src/eda/training_window/fits.py --check
./python_tabpfn_local.sh src/eda/training_window/fits.py --run
./python.sh src/eda/training_window/score.py
./python.sh src/eda/training_window/speed_check.py
```
