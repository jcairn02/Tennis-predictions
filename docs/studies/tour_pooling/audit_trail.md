# Tour pooling: methods and audit trail

9 October 2026 · Written for a future reviewer (a more capable model or a statistician) auditing whether this study was set up soundly and whether its conclusions follow from its results · Companion to the owner's report ([README.md](README.md)) and the pre-registered design ([design.md](design.md)).

**What this file adds.** The report says what was found, and the design says what was planned. This file records:
* what was done, in what order;
* what had been seen when each decision was made;
* why each judgment call went the way it did;
* where the study is weakest.

It is meant to be read with skepticism. § 9 is a checklist of the places a flaw would most likely hide.

## 1. The question and the answer given

* **The owner's three requests, 9 Oct 2026, paraphrased from the prompt:**
  1. **Split.** Train one model per tour and compare it with the pooled model, season by season from 2022, expanding window.
  2. **A flag.** If there is no men/women categorical input, add one and test it.
  3. **Borrowing.** Build models that use their own tour's data mainly and "borrow" the other tour's at lower weight. Find when borrowing helps or hurts, and compose 1–2 selective models.
* **The conclusion given** ([README](README.md) § 5):
  * keep the pooled model with its `tour` flag;
  * decline every alternative;
  * keep one after-the-fact lean, an even average of an own-tour and the pooled model for women, as an unbuilt candidate.
* **Its basis:** no candidate is resolved better on the declared primary. After the winner's-luck correction every candidate's expected gain is below 0. One arm (aligned) is resolved worse for men.

## 2. The fixed setup (what every arm shares)

* **The yardstick:** the current instance `data/studies/current_best_model/pinnacle_first_2026-10-09/`, read only. Its fits were never refitted or modified.
  * Frame SHA-256: `6996d41e67dd7ac5219846c999cd94b24f63273c41e3fa07c28707dd03ded7f2`.
  * 67,226 matches from 2013–2026: 34,719 men's and 32,507 women's.
  * 58 inputs, `tour` among them (0 = men, 1 = women).
* **The learner, as the instance's runner** (`src/eda/model_rebuild/fits.py`):
  * the local TabPFN-3.5 (`tabpfn-v3.5-20260909`) with 8 estimators, softmax temperature 0.9, and pretraining limits ignored;
  * season Y trained on 2013 .. Y − 1;
  * the query is season Y's matches as stored, then with A and B swapped; symmetrised downstream;
  * seeds 0–3 (production averages 16).
* **The comparison recipe:** `src/eda/current_best_model/compare.py`'s functions, unchanged (`walk_forward`, `forecasts`, `paired`, `close_forecast`, `populations`).
  * **Calibration and speed stage:** per-tour calibration slopes plus stage 2's speed coefficient b, fitted walk-forward on 2019 .. Y − 1 on each model's own seed-mean forecasts, debut seasons out, b shrunk with τ = 0.05.
  * **The speed column:** `data/studies/infosys_atp_backfill/speed_columns_augmented.parquet` (`spd_L_B`), the same for every model, zero for women.
  * **Dropped:** 40 women's matches of June 2026 that have no speed value. Their value would be 0 anyway.
* **The scored windows:**
  * **W1:** 2022 to 28 Jul 2026, the declared primary: 23,758 matches (12,341 men's, 11,417 women's), 57 four-week blocks.
  * **W2:** 2020–2024, the decided comparison's default: 22,265 matches, 55 blocks.
  * W1 and W2 share 2022–24.
* **The sealed holdout:** events from 2026-07-29 on.
  * `a_won` is read only through a parquet filter `tournament_date < 2026-07-29` applied before the column is read, with asserts.
  * The fits predict sealed matches, but nothing scores them.
  * `common.job_data` refuses any training row of season ≥ Y or dated on or after the seal.
  * Tests check all of this.
* **The statistic:**
  * **Paired difference:** 1000 × mean(LL_base − LL_candidate), in mLL per match, + = the candidate better.
  * **Interval:** the cluster-sandwich SE over four-week blocks, t on blocks − 1 df. Plus the seed term: the variance over seeds 0–3 of the per-seed loss difference, divided by 4 ("matched seeds", since the arms share TabPFN random states). For arms with random training draws, the draw changes with the seed, so the seed term also carries draw noise, estimated from only 4 points.
  * **"Unresolved"** when the 95% interval spans 0. **P(better)** is the t CDF of est / SE, the flat-prior reading of one test.
* **Realisation:** c in logit P = logit q_close + c · (logit q − logit q_close), with a block-sandwich SE (`src/eda/training_window/score.py`). Below 1 means the model moves too far from the close.
* **Winner's luck:** sel = SE × m_K (adoption framework § 4). m_K is the expected maximum of K independent standard normals: 1.27 for K = 6, 1.54 for K = 10.

## 3. The arms and composites (exact definitions in `src/eda/tour_pooling/common.py` and `score.py`)

| Name | Models | Training rows for season Y (pool = 2013 .. Y − 1) | Inputs | Example sizes, Y = 2022 |
|---|---|---|---|---|
| pooled (yardstick) | 1 | the pool | 58 | 42,538 |
| split | per tour | own tour's pool | 58 (`tour` constant; TabPFN drops constant columns) | men 21,951; women 20,587 |
| notour | 1 | the pool | 57 (`tour` dropped) | 42,538 |
| borrow50 | per tour | own + `rng(borrow50).choice(other, round(0.5 n_other))` | 58 | men 32,245; women 31,563 |
| borrow25 | per tour | own + a random `round(0.25 n_other)` subset **of borrow50's draw** (nested) | 58 | |
| borrowsim | per tour | own + other rows kept when u < π, π from the similarity cache (below); u uniform below 0.5 exactly on borrow50's rows (coupled) | 58 | about own + 0.5 n_other |
| aligned | 1 | the pool | 58; 39 box-score diffs (`form_*`, `formdef_*`, `iosO_*`, `iosD_*`, `prod_*`, `adjperf_tpw_2w`, `ios_points_short`) divided by their own tour's SD on the pool | 42,538 |
| sizectl (control) | per tour | a random draw from the whole pool of size n_own | 58 | n_own, about 48% own tour |
| pooled reproduction | 1 | the pool (2022, seed 0 only) | 58 | must equal the instance's stored fit |

* **Draws:** `default_rng([20261009, Y, seed, arm code, tour code])`, new for each season and seed.
* **The coupling's marginal:** P(keep) = ½ · min(1, 2π) + ½ · max(0, 2π − 1) = π for π in [0, 1].
* **The similarity cache** (`borrow_sim_v3/`). For each (tour, Y):
  * **The classifier:** a HistGradientBoosting (200 iterations, learning rate 0.1, 31 leaves, L2 1.0, seed 0), 5-fold stratified out-of-fold.
  * **What it is fitted on:** the pool's inputs only, with no results: P(own tour | x).
  * **The features:** |A − B| of the price log-odds, `elo_games`, `elo_overall`, `ratings_iid`, `elo_surf_offset`, `age` and `sets_14d`; (min, max) of `surf_season` and of `surf_layoff`, the latter taken at whole days; and `surface`, `level`, `best_of`, `round`.
  * **The inclusion probability:** density ratio r = p / (1 − p) · n_other / n_own; π = min(1, κ r), with κ set by bisection so that Σ π = 0.5 n_other.
  * **The resulting draw:** AUC 0.852–0.859; π = 1 for 20–23% of other-tour rows; effective n ≈ 62% of n_other.
  * **What it means in practice:** π ≈ 0 for every other-tour Slam match. The rest are taken at about 63%, tilted toward close prices, 1000s and 250s.
  * **A residual tilt:** rows that had fractional layoffs still get π 0.42 against 0.52 ([borrow_report.md](../../../data/studies/tour_pooling/borrow_report/borrow_report.md)).
* **Composites (no new fits):**
  * **blend.** Per tour, logit q = a_T η_split + c_T η_pooled (+ b · spd for men), fitted jointly without an intercept on 2019 .. Y − 1. η is the logit of the 4-seed mean.
    * Weights: a / (a + c) = 0.18–0.29 for men and 0.13–0.51 for women in 2022–26, each with an SE of 0.34–0.55, so they are essentially unidentified.
  * **select.** For each tour and season Y in 2021–2026, take the arm among {pooled, split, borrow25, borrow50, borrowsim, aligned} with the lowest both-stage log loss on that tour's scored seasons 2020 .. Y − 1. Ties go to the earlier-listed arm; 2020 uses pooled.
  * **blend_control (declared control).** The blend with split replaced by the instance's seeds 4–7. Its weights are unidentified.
  * **pooled8 and avg_split_pooled (post-hoc controls).** Equal-weight log-odds means of 8 fits: pooled seeds 0–7, and split 0–3 with pooled 0–3. Pseudo-seed k pairs seeds k and 4 + k (or split k with pooled k).

## 4. Chronology: what was known when each decision was made

Local time, 9 Oct 2026 (UTC−7). "Results" means outcome-based scores of any candidate.

| Time | Event | Results seen by the lead at that point |
|---|---|---|
| 13:40–13:58 | Read the template, compare.py, the fit runner, the adoption framework, the clean-holdout proposal, the surface-split precedent (separate surface models −0.28 [−0.77, +0.21]) and the training-window study | none from this study. The precedent's result was known |
| 13:58–14:00 | Wrote common.py, fits.py and queue.sh; checked the plans; queued split, notour, borrow50 and borrow25 behind another study's GPU job | none |
| 14:02 | Wrote design.md: arms, composites, primaries, the winner's-luck K = 6, segments, gates | none |
| 14:05 | Launched three agents (briefs in § 7) and the borrowsim v1 cache build | none |
| 14:07 | **v1 sampler degenerate:** AUC 1.000, every π = 0.5. Build stopped | none (inputs only) |
| 14:09–14:16 | Found `indoor` missing on every women's row. Built v2 (situation features without indoor); 2022 AUC 0.878. Amended design.md. The analyst found the same independently | none |
| 14:17–14:32 | split fitted, then notour | none |
| ≈ 14:37 | **First score:** the statistician's run on split (W1 +0.023 [−0.290, +0.337]; men −0.08, women +0.14; by season) | split only |
| 14:49 | borrow50 started | split |
| 14:52–14:57 | Read red team 1 (blind to scores) and the analyst's layoff artifact (v2 selected on dating precision) | split |
| 14:57–15:00 | **Amended common.py:** the v3 sampler (whole-day layoffs, a cache record check); **coupled draws** (borrow25 nested, borrowsim coupled); new arms **sizectl** (red team N3) and a **pooled reproduction** (N8). Checked that borrow50's 29 existing fits have identical masks | split |
| 15:00–15:47 | Built the v3 cache, slowly: the CPU was saturated by other sessions. OpenMP threads limited to 2; parallel builders for 2024–26 | split |
| 15:13 | Red team 1 final: 2 blockers, 9 should-fixes | split |
| 15:18–15:47 | borrow25 fitted | split |
| ≈ 15:43 | **Statistician's 2nd run:** notour, borrow50, blend_control | split, notour, borrow50, blend, blend_control |
| ≈ 15:45 | **Post-hoc controls requested** (pooled8, avg_split_pooled), because blend_control's weights were unidentified | as above |
| 15:47–16:03 | Pooled reproduction (exact: max diff 0.0), then sizectl | as above |
| ≈ 15:51 | **Statistician's 3rd run:** post-hoc controls, borrow25. avg_split_pooled reads women +0.125, P 0.87 | plus borrow25 and the post-hoc controls |
| ≈ 15:58 | The analyst's final report: Part A; Part B partial | plus segment flags for split, borrow50, blend |
| 16:03–16:31 | borrowsim fitted | – |
| 16:31 | **Interim run** with borrowsim and sizectl, plus segments and money, so the report could be drafted while aligned fitted | all but aligned and select |
| ≈ 16:45 | **Report draft.** "Decline" was **pre-filled for aligned and select before their results**, and the women's 50/50 average was recommended as a shadow run | all but aligned and select |
| 16:31–16:56 | aligned fitted | – |
| 16:57–17:03 | **Final run:** score, segments, money, figures. select and the winner's luck scored for the first time | everything |
| ≈ 16:50–17:07 | Red team 2 audited the draft. The women's shadow recommendation was judged "the garden of forking paths". Numbers matched | everything |
| 17:09–17:10 | Report rewritten: the women's lean downgraded to "keep as a candidate, don't build"; the headline corrected; definitions tightened; design.md's change log completed | everything |

**What this timeline shows.**
* The design and the first sampler fix were made blind to results.
* The coupling, sizectl and the reproduction were added after seeing split's first score. They are variance-reduction and attribution devices, and sizectl was proposed by a red team that had read no scores.
* The two post-hoc controls, and everything said about the women's average, came after seeing results.
* The report's "Decline" for aligned and select was written before their results. A reviewer should treat that wording as possibly anchored, though the results that followed (aligned worse for men, select −0.01) do not contradict it.

## 5. Results, compactly (final run; + = the candidate better than pooled; both stages)

| Model | W1 both tours | W1 men | W1 women | W2 both tours |
|---|---|---|---|---|
| split | +0.023 [−0.290, +0.337] | −0.082 | +0.137 | −0.062 |
| notour | −0.067 [−0.213, +0.078] | +0.026 | −0.168 [−0.342, +0.006] | −0.029 |
| borrow25 | +0.047 [−0.170, +0.265] | +0.016 | +0.081 | +0.024 |
| borrow50 | +0.030 [−0.113, +0.172] | +0.020 | +0.040 | +0.015 |
| borrowsim | +0.014 [−0.140, +0.169] | −0.017 | +0.048 | −0.071 |
| aligned | −0.007 [−0.122, +0.108] | **−0.162 [−0.306, −0.017]** | +0.160 | **−0.149 [−0.280, −0.017]** |
| blend | +0.037 [−0.056, +0.130] | +0.011 | +0.066 | +0.007 |
| select | −0.014 [−0.117, +0.089] | −0.016 | −0.012 | −0.056 |
| sizectl (control) | −0.167 [−0.343, +0.009] | **−0.312 [−0.601, −0.022]** | −0.011 | −0.106 |
| blend_control (control) | −0.028 | −0.032 | −0.024 | −0.060 |
| pooled8 (post hoc) | −0.021 [−0.079, +0.038] | −0.005 | −0.037 | −0.010 |
| avg_split_pooled (post hoc) | +0.066 [−0.092, +0.224] | +0.011 | +0.125 [−0.094, +0.345] | +0.034 |

* **Every model against its calibrated close, W1 both tours:** +0.99 to +1.20; pooled +1.157 [+0.557, +1.757].
* **Realisation, W1 both tours:** 0.98 (split) to 1.10 (borrow50), SE about 0.15. By tour: 0.89–1.14.
* **Decomposition, W1:** pooled − split = (sizectl − split) + (pooled − sizectl), an exact identity on the same matches.
  * **Mix** (split vs sizectl): +0.19 [−0.15, +0.54].
  * **Size** (pooled vs sizectl): +0.17 [−0.01, +0.34]; men +0.31 [+0.02, +0.60]. In W2, men's size is +0.39 [+0.10, +0.68], and women's mix and size both flip sign.
* **Winner's luck on the declared family** (K = 6): the best is borrow25, +0.047, with sel 0.138, so est − sel = −0.091.
* **Segments:** 45 read cells per comparison. For pooled vs split in W1, one cell clears 0: women's heavy favourites, −0.82 [−1.51, −0.14], BH q 0.88. It reverses in 2020–21.
* **Full tables:**
  * `data/studies/tour_pooling/scores/` (scores.csv, summary.json with every file's SHA-256);
  * `segments/segments.md`;
  * `money/roi.csv`.

## 6. Judgment calls, with the reasons given at the time

1. **The tour flag is tested by removal, not addition.** The flag already exists. notour keeps an exact tour proxy: `indoor` is missing for every women's match and for no men's training match, and TabPFN uses NaN indicators. Partial proxies remain too: best of five; women's hold statistics missing in 2013–15; box-score spreads 1.6–2.5× wider for men.
   * Red team B2 asked for `noindoor` and `notour_noindoor`. Declined: neither is a production option, and the box-score scales would still name the tour. **So question 2 was answered as "the explicit flag's value given the tour is otherwise recognisable", not "the value of tour information".**
2. **borrowsim keeps `best_of` and `level`**, so it never borrows the other tour's Slams. That was declared, not changed (red team S1): best of five is a different event, and its absence for women is real. Consequence: borrowsim against borrow50 mostly tests "drop the other tour's Slams" (−0.02 W1, −0.09 W2).
3. **The draws were coupled after borrow50 had started.** borrow50's draw call was kept bit-identical (29 fits checked), so only the not-yet-fitted arms changed.
4. **The blend was left unconstrained as declared** (red team S3), though its weights are unidentified. The red team's proposed constrained form was not run.
5. **The post-hoc controls were added after the blend's reading**, to separate seed averaging from own-tour diversity. Result: pooled8 vs pooled −0.02; avg_split_pooled vs pooled8 +0.09 (women +0.16, P 0.94). They are labelled "post-hoc control" in every table and kept out of select and the declared winner's-luck family.
6. **An interim scoring run (one extra read of 2025 to 28 Jul 2026)** let the report be drafted while aligned fitted. No choice was made from it beyond the wording of the report.
7. **The women's 50/50 average was downgraded** after red team 2:
   * three of its four supporting readings reuse the same women's split forecasts;
   * 2026 supplies over half of its gain;
   * corrected for the search: +0.125 − 1.54 × 0.110 ≈ −0.04, or −0.08 counting the choice of tour;
   * a season of live data gives an SE of about 0.24 mLL.
8. **The scorer does not check each fit's runtime or job fingerprint** (red team S7). The test suite does (`test_fits_on_disk_*`). Declared, not fixed.
9. **The money analysis** (`money.py`) is context only: in-sample, 4-seed versions, archived closes (Pinnacle's to Sep 2025), many cells. No decision rests on it.

## 7. The team and their briefs (the prompts themselves are not saved; summarised here)

* **Every agent was told:**
  * use `./python.sh`;
  * never start a GPU fit;
  * never read a result dated 2026-07-29 or later (filter before reading `a_won`);
  * write only in their named files;
  * no git;
  * report in mLL, + = the candidate better, never "tie": "unresolved" with P(better);
  * later, keep OpenMP threads at 2 or fewer.
* **The statistician:**
  * built `score.py`: compare.py's functions unchanged, a checked loader for the study's fits, the composites, realisation, winner's luck and forecasts.parquet;
  * had to pass three validations before reporting: the instance against itself is exactly 0; the decided comparison (instance vs frozen reference, W2) reproduces; and unit tests;
  * later added the red team's fixes (S5, S8, S9, B2 labels), blend_control, and the two post-hoc controls.
* **The red team:**
  * **Review 1,** before results were trusted: leakage, recipe drift, masks, the sampler, aligned, the meta, the design. It also wrote `test_common.py`.
  * **Review 2:** audited the report's numbers and claims.
  * It read no score before review 1.
* **The tennis and market analyst:**
  * **Part A:** the tours' input scales, and what borrowsim borrows.
  * **Part B:** the segment flags with Benjamini–Hochberg, and the size/mix decomposition.
  * The analyst independently found the v1 degeneracy and found the v2 layoff artifact.

## 8. Threats to validity (the study's own list, most important first)

1. **The incumbent's advantage.**
   * The 58 inputs, TabPFN's settings, the calibration recipe and the speed stage were all chosen with the pooled model, largely on 2020–24 (see the [feature provenance](../feature_provenance/README.md) study).
   * Separate or borrowing models were never re-tuned: no per-tour input selection, settings or shrinkage.
   * So "split ≈ pooled" holds under the pooled model's configuration. A tuned split could differ in either direction. *This is the largest untested assumption.*
2. **The pooled model already treats the tours separately in places:**
   * per-tour calibration slopes;
   * a men-only speed stage;
   * per-tour shrinkage inside the inputs (women's serve form K3 = 20 against men's 10).

   So the comparison is between deployed systems, not raw learners, and the split's room to win is narrower than it sounds.
3. **Power.** Paired SEs are 0.05–0.16 mLL per arm; plausible true effects are ≤ 0.1. "Unresolved" here means "small or zero", not "zero". The primaries were declared on W1, which spans only 4.6 seasons.
4. **Context size and TabPFN.** Pooled contexts (about 60k rows in 2026) sit further beyond the pretraining regime than split contexts (about 30k). sizectl separates size from mix, but TabPFN's behaviour may be non-linear in context size.
5. **Draw noise.** The borrowing and size-control arms draw new rows per seed. Their seed term rests on 4 draws.
6. **Overlapping windows and repeated looks.**
   * W1 and W2 share 2022–24, so "agrees across windows" is not independent confirmation.
   * 2025 to 28 Jul 2026 had already been read about 20 times by earlier studies. This study read it in five full and two partial scoring runs, plus the segment and money runs.
7. **Winner's-luck K is a judgment:** 6 declared, about 10 with the post-hoc controls, about 20 if the choice of tour counts. m_K assumes independent variants; the arms are strongly correlated, which makes the correction conservative.
8. **The odds input changes inside W1.** From Aug 2025 it is BetOnline's close (17.5% of scored matches), and the books' average for 1.3%. This applies equally to every arm.
9. **Segment analysis:** 45 cells × comparisons × 2 windows, all BH q ≈ 0.9 or above. The mechanism stories in the report are labelled inference and rest on unresolved leans.
10. **aligned's scales:**
    * they mix construction (the shrinkage difference) with tennis;
    * women's 2013–14 hold ratings are near 0;
    * the `prod_*` spreads drift by season.

    Its clear harm to men may reflect those distortions rather than "translation" as an idea.
11. **Anchoring.** The report draft pre-filled "Decline" for aligned and select (§ 4).

## 9. Checklist for a reviewer

* [ ] Re-derive one primary row by hand from `forecasts.parquet`. The statistician did: 108 rows within 6.7e-16.
* [ ] Confirm that no `a_won` dated 2026-07-29 or later enters any table:
  * `score.outcomes`;
  * segments' read filter;
  * money's assert.
* [ ] Check the fits on disk against today's masks and fingerprints (`./python.sh -m pytest test/tour_pooling -q`: 142 pass, 1 expected failure).
* [ ] Check that the coupling change at 14:57 left borrow50's draw unchanged (`test_common.py` fingerprints).
* [ ] Judge whether § 8 point 1 (the incumbent's advantage) invalidates the conclusion. If it might, the experiment that answers it is a per-tour re-selection of inputs and settings on 2013–2021 only, scored on W1.
* [ ] Judge whether the seed term's 4-draw estimate understates uncertainty for the random-draw arms (§ 8 point 5). One remedy is more seeds for those arms.
* [ ] Recompute the winner's luck with correlated variants (scale by √(1 − ρ), using the arms' between-arm correlation of per-match differences).
* [ ] Check that the report's verdict words match the intervals ("better/worse" only when the 95% interval clears 0).
* [ ] Check that every after-the-fact item is labelled as such (`role = "post-hoc control"` in scores.csv; README).
* [ ] Test the stated mechanism (purity +0.19, size +0.17) for stability across windows. It flips for women in W2.

## 10. Reproduction

```
./python.sh src/eda/tour_pooling/fits.py --arm <arm> --plan                    # training rows per job (CPU)
OMP_NUM_THREADS=2 ./python.sh src/eda/tour_pooling/fits.py --arm borrowsim --prepare   # the v3 similarity cache (CPU)
bash src/eda/tour_pooling/queue.sh split notour borrow50 borrow25 borrowsim aligned sizectl   # GPU, one arm per runner
bash src/eda/bet_timing/run_when_free.sh src/eda/tour_pooling/fits.py --arm pooled --seeds 0 --seasons 2022
./python.sh src/eda/tour_pooling/score.py          # writes scores/; reads 2019 .. 28 Jul 2026 results
./python.sh src/eda/tour_pooling/borrow_report.py  # inputs only
./python.sh src/eda/tour_pooling/segments.py
./python.sh src/eda/tour_pooling/money.py
./python.sh src/eda/tour_pooling/figures.py
./python.sh -m pytest test/tour_pooling -q
```

* **Environments:** the `tennis` env for the CPU steps; the `tennis-tabpfn-local` env for the fits (tabpfn 9.1.0, the checkpoint above, RTX 5090). Both envs run numpy 2.4.6, so the draws reproduce across them.
* A fit on disk is never redone; the fits are deterministic given the seed and the frame.
* **Superseded similarity caches,** kept as the record:
  * `borrow_sim/` (v1, degenerate);
  * `borrow_sim_situation/` (v2, the layoff artifact).
