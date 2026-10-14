# Centring the IOS ratings before the 7 matchup products

8 October 2026 · Written for the owner · A study, not a decision: it changes no decided file.

**The owner's request (8 Oct 2026):** "Centre the IOS ratings before forming the 7 prod_* products. Their spread grew 25–56% in 2025–2026 when the ITF box scores arrived. The model never saw that shift in training, and it falls in the seasons you'll bet in. Its cost in log loss has never been measured."

**Keys.** Scores are in mLL (milli-log-loss per match). **Positive = the centred arm has the lower log loss (better)**; a 95% interval that spans 0 is a **tie**. *Observed* = computed here; *inferred* = reasoning.

The plan, the comparisons and the reading rules were fixed before any result: [preregistration.md](preregistration.md). Its SHA-256 (CRLF normalised to LF) is in `data/studies/ios_product_centring/preregistration.sha256`, and the scorer refuses to run if the file changed.

**Note for reviewers (9 Oct 2026): a flaw in this study's intervals, found after it ran. The study was not re-run.**
* **The flaw.** The intervals of P and S1–S6 add each arm's seed-to-seed variance as if the two arms' seed noise were independent. Both arms used the same TabPFN seeds (random states 0–3), so most of that noise is shared and cancels in the difference. Adding both counts it twice.
  * Found by the adoption framework's statistics review ([finding 1](../adoption_framework/review_statistics.md)). With the same interval code (`serve_speed_tabpfn.score.paired_stats`), a model compared with itself got ±0.087 mLL instead of 0.
* **What it does.** Those intervals are too wide; the estimates are right. S7 is unaffected (a block-only interval).
* **It changes no reading here.** A corrected (paired) interval is never narrower than the block-only one, which `results.json` holds for every comparison. Every block-only interval spans 0: the primary's is [−0.25, +0.13], and S1's (2022–2024) [−0.14, +0.04].
* **"What it does not show" overstates the seed noise.** *Inferred:* paired, most of the seed part would cancel. The primary's SE would then lie between 0.09 (the blocks alone) and 0.13, probably near 0.09, and more seeds would narrow it less than that section says.
* **Not re-run, on purpose.** The pre-registered comparison ran once, and its results stand as registered.
  * Its scorer still computes the registered interval. The shared function now offers the paired term: `paired_stats(..., matched_seeds=True)` ([checklist](../adoption_framework/checklist.md), item 1).
  * Checklist item 5 plans a paired re-read of 2022–2024. Re-reading 2025–2026 would be a further look at the proposed clean holdout.

## In short

* **Observed. The drift was real, and centring removes it.** From 2024 to 2026 the products' spread grew 22–58% for five of the seven statistics on each tour. Centred, it moves between −19% and +7%.
* **Observed. It made no measurable difference to the current best model (both stages).**
  * Primary, both tours, 2025 – 28 Jul 2026: **−0.06 [−0.33, +0.21] mLL, a tie.**
  * 2022–2024, where the ITF regime was absent: −0.05 [−0.21, +0.11], a tie.
  * Every season, each tour, stage 1 alone, and the model fed Polymarket's 24-hour price: all ties.
  * The point estimates run from −0.11 to +0.02. They lean very slightly towards today's products, well inside the noise.
* **The answer to "what did the drift cost?"** Nothing measurable. At 95% the cost was at most about 0.21 mLL on 2025–2026, against the model's +1.94 over the recalibrated close on the same matches.
* **Inferred. Why so little.**
  * As built, the products were mostly a rescaled copy of the offence and defence differences the model already has. Those explain 86–94% of the men's products' variance.
  * Inside a season, the as-built and centred versions correlate 0.89–0.99.
* **Reading, as pre-registered.** The primary is a tie and 2022–2024 is not worse. So the pre-registered rule recommends centring on mechanism alone: it keeps the products' meaning fixed when data coverage changes, as it will again.
  * No log-loss gain is shown.
  * Keeping the products as built costs nothing measurable either.
  * Adoption is the owner's decision. This study changes no decided file.

## The problem

* **The products.** The model has 7 IOS matchup products: aces, double faults, first serves in, first- and second-serve points won, holds, break points saved. Each is `prod = O_A·(−D_B) − O_B·(−D_A)`, formed from the surface-effective ratings O + E_s and D + F_s.
* **Why they drift.** IOS ratings are measured from the pool's zero point. A common shift (o₀, d₀) of every rating adds `d₀(O_B − O_A) + o₀(D_A − D_B)` to a product. The 14 offence and defence differences (A − B) are untouched.
* **The shift happened.** ITF box scores exist only from January 2025 to May 2026. While they were in the pool, the level of the main-tour players rose. The audit's measure, the mean defence of the model's players on women's holds, was 0.41 in 2024, 0.54 in 2025 and 0.73 in 2026 ([input-data audit, #6](../input_data_audit/README.md)). This study's reference level shows the same rise (below).

## What was built

* **The reference level.** At every daily snapshot of the decided surface IOS: the unweighted mean of `O + E_s` and `D + F_s` per surface. It is taken over every player who served or returned in a main-tour observation of that statistic that is released by the snapshot day and played in the last 52 weeks.
* **How it was computed.** The decided solve was run again with a read-only hook on its snapshot generator. The re-solve reproduces the stored ratings of every row exactly, so the levels belong to the ratings the model reads.
* **The centred product.** `prod_c = −(O_A − m_O)(D_B − m_D) + (O_B − m_O)(D_A − m_D)`, with m from the match's own snapshot (its earliest possible start) and surface.
* **The arm.** The model's 58 inputs with only the 7 products replaced. Each centred product equals `prod + m_D(O_A − O_B) − m_O(D_A − D_B)`.

## Checks (gates; all passed before any result was read)

| Gate | What it checks | Result (`data/studies/ios_product_centring/checks/`) |
|---|---|---|
| G1 | The hooked re-solve reproduces the stored surface-IOS ratings of every row, all 14 runs | pass: largest difference 0.0 in all six rating arrays of all 14 runs |
| G2 | The products as built equal the model frame's 7 `prod_*` inputs, 63,737 matches | pass: largest difference 0.0, the same missing values |
| G3 | Leak probe: reversing every result after a cut day moves nothing about a match that surely finished by it (2023–2024 slice, four cut days; holds, first-serve points, aces) | pass: 0 of 13,758 / 19,744 / 29,141 / 31,163 earlier matches moved (largest difference 0.0); 71,186 / 53,172 / 25,068 / 19,022 later centred products did move |
| G4 | This study's fit runner reproduces a stored base fit (model, 2025, seed 0) in all three query blocks | pass: largest difference 0.0 |
| G5 | The scorer's stage-2 fit reproduces the published L_weekly coefficients of 2024–2026 | pass: largest difference 0.0 on all 15 |
| G6 | The centred products are antisymmetric, the flip is an involution, and the other 51 inputs and 8 identifier columns are unchanged | pass |

## The results (observed; `results.json`, `results.csv`)

Both stages: stage 1 is the local TabPFN-3.5 with the 58 inputs, seeds 0–3 for both arms. Stage 2 is `logit q = s_tour·η + b̃·spd_L`, refitted walk-forward on each arm's own forecasts. **Positive = the centred arm has the lower log loss (better).** The intervals combine four-week blocks with both arms' seed variance.

| Comparison | Matches | Gain, mLL [95%] | Reading |
|---|---:|---|---|
| **P: both tours, 2025 – 28 Jul 2026** | 8,520 | **−0.06 [−0.33, +0.21]** | **tie** |
| S1: both tours, 2022–2024 | 15,207 | −0.05 [−0.21, +0.11] | tie |
| S2: both tours, 2022–2026 | 23,727 | −0.06 [−0.22, +0.11] | tie |
| S3: 2022 / 2023 / 2024 / 2025 / 2026 | 3,415–5,135 each | −0.01 / −0.04 / −0.11 / −0.11 / +0.02 | each a tie |
| S4: men, 2025–2026 | 4,394 | −0.08 [−0.46, +0.30] | tie |
| S4: women, 2025–2026 | 4,126 | −0.04 [−0.45, +0.38] | tie |
| S4: men, 2022–2026 | 12,341 | −0.06 [−0.27, +0.16] | tie |
| S4: women, 2022–2026 | 11,386 | −0.06 [−0.26, +0.15] | tie |
| S5: stage 1 only (calibrated), 2025–2026 | 8,520 | −0.07 [−0.35, +0.21] | tie |
| S6: both fed Polymarket's price 24 hours before the start, 2025–2026 | 2,648 | −0.11 [−0.50, +0.28] | tie |

**Context (S7): each arm, both stages, against the closing price recalibrated the decided way.** Positive = the arm better than the close; block-only intervals.

| | 2025 – 28 Jul 2026 | 2022–2026 |
|---|---|---|
| Today's model | +1.94 [+0.91, +2.96] | +1.33 [+0.70, +1.97] |
| Centred products | +1.88 [+0.84, +2.92] | +1.28 [+0.65, +1.90] |

**Stage 2 barely notices.** The two arms' walk-forward coefficients agree to within 0.002. For example, for 2025: s_atp 0.912 against 0.911, s_wta 0.928 against 0.930, b̃ 0.029 against 0.029.

## What it does not show

* **Small effects.** The primary's standard error is 0.13 mLL: 0.09 from the four-week blocks, the rest from TabPFN's seed-to-seed noise with 4 seeds per arm. A true effect under about 0.37 mLL would usually read as a tie. With 16 seeds per arm the error would be about 0.10.
* **The decided application.** Both arms are applied with their seeds 0–3 mean, not the base's 16-seed mean, so that the seed sets match. That is why the context row differs slightly from published figures.
* **Other reference definitions.** Only the pre-registered one was tried: main-tour players of the last 52 weeks, unweighted, per surface. Weighting by matches, or the model's own players, was not tried, by design: nothing was tuned.
* **The 14 differences.** They are free of the level by construction, but their spread can still move with coverage: −10% to +8% from 2024 to 2026 here. They were not changed.
* **The data snapshot.** The model frame is the 6 October build on the 30 September tables, for both arms. The 7–8 October Stage 0 rebuild and data fixes are in neither.
* **Fresh data.** The test seasons have been read by earlier studies (below). This is not an untouched holdout.

## If the owner adopts it

* **Build.** Add the reference level to the surface-IOS build (`reference.py`'s hook in `surface_ios/build_features.py`), form the products from centred ratings (`surface_ios/arms.py`, recipe `prod`), then rebuild the model frame (the offset-Elo decision's steps).
* **Live use.** The level is read from each day's snapshot of the live solve, at no extra cost.
* **Stage 2.** It needs nothing new: its coefficients are refitted on the model's own forecasts, as they would be for any stage-1 change.
* **A separate question, not tested.** As built, the products carried little beyond the 14 differences. Whether they earn their place at all is a question the owner's "all these features stay in" leaves closed.

## The products before and after (observed; outcome-free, `diagnostics.json`)

**The level of the main-tour players** (the reference level, holds, defence `m_D`, mean over the season's snapshots):

| | 2015 | 2018 | 2020 | 2022 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Women's holds | −0.01 | +0.08 | +0.12 | +0.08 | +0.08 | **+0.26** | **+0.44** |
| Women's aces | +0.14 | +0.14 | +0.18 | +0.13 | +0.14 | **+0.28** | **+0.37** |
| Men's break points saved | +0.02 | +0.05 | +0.07 | +0.06 | +0.06 | +0.08 | +0.09 |

The level moved before 2025 as well (women's holds rose from −0.01 in 2015 to +0.12 in 2020), whenever the pool's composition changed. The ITF months moved it most.

**The products' spread, as built and centred** (SD over the model's matches; change from 2024 to 2026):

| | Men: as built | Men: centred | Women: as built | Women: centred |
|---|---:|---:|---:|---:|
| Aces | +37% | +6% | +33% | −3% |
| Double faults | −0% | −3% | +12% | +7% |
| First serves in | +7% | +2% | −10% | −7% |
| First-serve points won | +45% | −3% | +58% | −13% |
| Second-serve points won | +32% | −3% | +26% | −19% |
| Holds | +40% | +1% | +50% | −16% |
| Break points saved | +22% | −2% | +27% | −3% |
| *The 14 offence and defence differences, for comparison* | *−1% to +8%* | | *−10% to +5%* | |

* **The audit's figures reproduce.** Men's holds as built: SD 0.383 / 0.491 / 0.534 in 2024 / 2025 / 2026. Women's: 0.228 / 0.275 / 0.343. Centred: 0.196 / 0.213 / 0.198 for men, 0.196 / 0.181 / 0.165 for women.
* **As built, the products were mostly a rescaled copy of inputs the model already has.** The two rating differences explain 86–94% of the variance of the men's products for first- and second-serve points, holds and break points saved (2022–2026). Centred, they explain 60–74%. For aces it is 72% against 37%.
* **Within a season, little changes.** As-built and centred products correlate 0.89–0.99 inside each season. The fix mainly changes the products' scale across seasons, not the order of matches within one.

## Deviation from the pre-registration

* **Snapshots with no reference players.** The plan did not say what the level is when no player qualifies. Settled before any result was read: the level is 0 there, so the product stays as built.
  * This affects women's holds in 2013–2014, when no women's hold box scores exist and every hold rating is 0, so their products are 0 either way.
  * It also affects the first weeks of 2010.

## What was read

* **Match results:** the model frame's 2019 – 28 Jul 2026 outcomes, read once by `score.py`. That covers the stage-2 refits from 2019 and the scored seasons 2022–2026.
* **Already-exposed seasons.** 2025 – 28 Jul 2026 is the "H-exposed" part of the [clean-holdout proposal](../clean_holdout_rebuild/README.md), read about 20 times by earlier studies; this read adds one.
* **Not read:** no match after 28 Jul 2026.
* **Outcome-free steps:** everything before the scoring run (the re-solves, the products, the probe, the fits and a dry run of the scorer on drawn coin-flip outcomes) read no result.
* **A change made elsewhere during the run.** At 20:42 on 8 Oct another session pointed `surface_ios.common.ios_constants` at a new IOS constants registry (`src/eda/ios_constants/registry.py`). Its version in effect returns exactly Stage B's constants and typical units (checked after the run). The re-solves also reproduced the stored ratings exactly (G1), so nothing here depends on the registry.

## Files and how to run

Code in `src/eda/ios_product_centring/`, tests in `test/ios_product_centring/`, outputs in `data/studies/ios_product_centring/`. Run from the repository root:

| Step | Command | Writes |
|---|---|---|
| Re-solve with the hook (about 11 min on 14 workers) | `./python.sh src/eda/ios_product_centring/reference.py` | `reference/<tour>_<stat>.npz`, `checks/g1_reference.json` |
| Centred products, the arm's frame, diagnostics | `./python.sh src/eda/ios_product_centring/products.py` | `centred_products.parquet`, `arm_frame.parquet`, `diagnostics.json`, `checks/g2_products.json`, `checks/g6_symmetry.json` |
| Leak probe | `./python.sh src/eda/ios_product_centring/probe.py` | `checks/g3_probe.json` |
| TabPFN fits (GPU; reproduction first) | `./python_tabpfn_local.sh src/eda/ios_product_centring/fits.py` | `local/cprod__<season>__seed<k>.npz`, `local/repro/`, `checks/g4_repro.json` |
| The one scoring run | `./python.sh src/eda/ios_product_centring/score.py` | `results.json`, `results.csv`, `checks/g5_stage2.json` |
| Tests | `./python.sh -m pytest test/ios_product_centring -q` | |

The decided pipeline is untouched. Adopting the change would mean adding the hook's level to the surface-IOS build and forming the products from centred ratings, then rebuilding the model frame.
