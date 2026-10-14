# Red team 1: the tour-pooling runner, cache, scorer and design

9 Oct 2026 · **Reviewed:** `src/eda/tour_pooling/common.py` and `fits.py` as amended at 14:57, `queue.sh`, `score.py`, the missing-input count in `segments.py`, `docs/studies/tour_pooling/design.md` (14:11), and the code they mirror. **Ground rules:**
* No fit started, no study file changed.
* The only results read were training labels (seasons ≤ Y − 1, filtered at read time) for fingerprints. No score was looked at.
* **Unit:** mLL per match, + = the candidate better.

**Status key:** **open**, **fixed** (in the code now; tests cover it), or **partly fixed**.

## Blockers

**B1. Sealed results through `compare.outcomes`: fixed in the scorer.**
* **Where:** `src/eda/current_best_model/compare.py:103-108` reads `a_won` for `season <= through`. With `through = 2026` that loads 869 sealed matches (29 Jul to 23 Sep 2026: 416 men, 453 women).
* **Now:** `score.py:137-144` reads results with a `tournament_date < 2026-07-29` filter at read time and asserts it. Lines 166 and 176 keep sealed ids out of `info`.
* **Rule:** no study code may call `compare.outcomes` or `compare.compare(through=2026)`.

**B2. `notour` cannot answer question 2: the tour stays in the inputs. Open (acknowledged).**
* **Where:** `common.py:86-88` drops `tour` only.
* **The exact proxy:**
  * `in_indoor` is missing on all 32,507 women's matches.
  * It is missing on no men's training match. Its only 127 men's gaps are the 2026 US Open, which is sealed.
  * The v3.5 checkpoint's config has `"use_nan_indicators": true`.
  * So "indoor missing and best of three" names the women's tour exactly (strict-xfail test `test_notour_inputs_do_not_name_the_tour_by_their_missing_values`).
* **Partial proxies:**
  * `best_of = 5` marks 6,946 of 34,719 men's rows (every men's Slam), and level 0 with best of three marks every women's Slam.
  * Hold and break-point statistics are missing on 99.9%, 99.2% and 16.8% of women's 2013, 2014 and 2015 rows, against 0.06% of men's. The inputs are `form_hold`, `form_bp_faced_pg`, `form_brk` and `formdef_bp_faced_pg`.
  * Box-score spreads differ by tour (men's SD over women's):
    * 1.6–1.9 for 8 of the 12 `form_*` inputs and for `adjperf_tpw_2w`;
    * 2.0–2.5 for four `prod_*` inputs.
  * `surf_layoff`'s days are fractional on 25.3% of women's 2013–18 rows against 1.4% of men's: the match clock's estimated days. The v3 cache rounds them for the classifier, but TabPFN still sees them in every arm.
* **The claim at stake:** `score.py:602-605` writes "question 2: the tour input's value (- notour's reading)" into `summary.json`. That is the misleading claim: the model never loses the tour.
* **Fix:**
  * Relabel it "the explicit flag's value beyond an exact proxy" and amend `design.md` before the reading.
  * If the owner wants the literal answer, add two arms: `noindoor` (57 inputs) and `notour_noindoor` (56).
    * The tour's worth = `notour_noindoor` against `noindoor`.
    * `indoor`'s worth for men = pooled against `noindoor`.
    * Call it "as tour-blind as the inputs allow".

## Should-fix

**S1. What borrowsim borrows. Partly fixed: declared in `common.py:201-202`, not yet in `design.md`.**
* **The Slam exclusion:** `level` with `best_of` names the tour at a Slam, so no other-tour Slam match is borrowed. In the 2022 cache (v2), pi ≤ 0.002 for all 4,428 women's Slam matches offered to the men's model, and for all 4,422 men's Slam matches offered to the women's model.
* **The other tilts:**
  * toward close prices: the women's model keeps the closest third of men's matches at mean pi 0.60, and the most lopsided third at 0.36;
  * toward recent seasons, in the 2026 cache (v2): the men's model keeps women's 2013–18 matches at 0.44–0.46 and 2021–25 matches at 0.55–0.57. The women's model is flat.
* **Fix:** amend `design.md`, then have the analyst report borrowsim against borrow50 for Slam and non-Slam matches and by season. Recency is the training-window question and must not be credited to similarity. Re-check both tilts on the v3 cache.

**S2. Coupled draws. Fixed** (`common.py:28-31`, `134-148`).
* borrow25 is a random half of borrow50's rows, and borrowsim keeps a row when u < pi, with u below 0.5 exactly on borrow50's rows.
* borrow50's draw is unchanged, so its existing fits stay valid; the fingerprint test confirms.
* The tests cover: the nesting, the coupling, P(keep) = pi, and independence across seeds and seasons.

**S3. The blend is nearly unidentified. Open.**
* **Where:** `score.py:312-345` fits four free coefficients (a_T, c_T per tour) plus b.
* **Evidence** (from the split fits, forecasts only, no result):
  * split's and pooled's seed-mean log-odds correlate 0.998–0.999 per tour in each season 2019–2023;
  * their difference has SD 0.058–0.070.
* **The failure:** a and c are identified only along that difference. For Y = 2022 the fit has 6,312 men's and 5,793 women's matches of 2019–21. Expect large offsetting a and c that swing from season to season (`composites.csv` keeps `se_a` and `se_c`; check them before reading the blend).
* **Fix:** logit q = s_T · [η_pooled + w_T (η_split − η_pooled)] (+ b · `spd_L` for men).
  * Keep w_T in [0, 1], or give it a N(0, τ²) prior shrinking toward pooled.
  * Report w_T and its SE each season.

**S4. Part of a blend gain is plain averaging. Open.**
* **The issue:** the blend averages 8 fits against the yardstick's 4 (production averages 16).
* **Scale:** pooled seeds 0–3 and 4–7 differ by SD 0.011–0.016 in log-odds, against 0.06–0.07 for split against pooled. Most of a blend gain would be real diversity, but not all.
* **Fix (no GPU):** score the same blend with η_split replaced by pooled seeds 4–7 (on disk for 2019–2026), and read the blend against it.

**S5. The similarity cache. Fixed in the runner, partly fixed in the scorer.**
* **Runner, fixed:**
  * `common.py:225-239` refuses a cache without its record, or with another version, other features or another frame.
  * The record is written first, via tmp + replace (`common.py:276-280`).
  * Fits store the cache's SHA-256 (`fits.py:108-109`).
* **Scorer, open:** `score.py:234-239` still scores a borrowsim fit whose cache is missing, with only a warning, and never compares `meta["draw"]["sim_cache_sha256"]` with the cache file.
* **Fix:** refuse instead, and compare the hash. Also, the docstring at `score.py:18-19` still names `borrow_sim_situation/`.

**S6. The "missing inputs" segment was a tour indicator. Fixed in `segments.py:168`** (`indoor` is left out).
* Counted over all 58 inputs, "none" held 34,504 men and 0 women.
* Left as `design.md:83` words it, it would be a tour split.

**S7. The scorer's fit checks. Partly fixed.**
* **What `score.py:209-249` checks:** names, settings, frame, columns, ids, the td block, shape, and rows by tour and season.
* **What it lacks:** the runtime (tabpfn, torch, checkpoint, device equal to the instance's) and the fingerprint of today's `job_data`.
* **Fix:** add both, as `test_fits_on_disk_*` do. The fingerprint needs training labels read with the date filter.

**S8 (new). "pooled" names two things in the scorer. Open.**
* **Where:** `score.py:102` takes `ARMS = tuple(C.ARMS)`, which now holds the reproduction arm `pooled`. Lines 566-568 first set `models["pooled"]` to the yardstick (the instance's fits), then `models[arm]` for every complete arm.
* **The failure:** the repro arm has 1 file of 32, so it is never complete today. Completed, it would silently replace the yardstick.
* **Also missing:** the reproduction comparison itself exists nowhere in the code. It is `test_the_pooled_reproduction_fit_equals_the_instances_stored_fit` here.
* **Fix:** exclude `pooled` (and `sizectl`, unless meant as a candidate) from the scorer's arm list, or rename the arm `pooled_repro`.

**S9 (new). `select` changes with which arms are complete. Open.**
* **Where:** `score.py:569-575` builds the pool from the complete arms.
* **The failure:** a run with only split done scores "select" over {pooled, split}, and `declared_primaries["question 3: select"]` reports it without qualification.
* **Fix:** score `select`, and fill its declared primary, only when all six `SELECT_POOL` arms are complete. Do the same for the winner's-luck line (`complete_search` already flags it).

## Notes

* **N1. The `query_rows` convention.**
  * `fits.py:105` stores `{"td": k}` (2,339 for split wta 2022). Other runners store 2k = len(`p_td`) (9,890 for the instance's 2022).
  * A check copied from `training_window/fits.py:61` fails on every study fit.
  * Check len(`p_td`) == 2 · len(`ids_td`), as `score.py:230` does.
* **N2. Sealed labels in memory. Partly fixed.**
  * `job_data` now refuses sealed training rows (`common.py:310-311`; tested).
  * `fits.py:61` still loads `a_won` for all 67,226 rows, sealed included, even for `--plan` and `--prepare`, which need none. Read labels with the date filter on the GPU path only.
* **N3. The size control. Fixed** (`sizectl`: split's size, pooled's mix; tested).
* **N4. The selection family.** K = 6 (`design.md:72`, `score.py:105-106`). If split, or a per-tour mix read off the tour flags (split for women, pooled for men), can become the "how to pool" suggestion, the family is 7–9. Route per-tour choices through the walk-forward composites only.
* **N5. Per-tour calibration.**
  * `walk_forward` fits s_atp and s_wta on each model's own forecasts. The pooled yardstick therefore already has a tour-specific scale, and split can win only on shape.
  * This is symmetric (no bias) and the right question for the deployed system. The "stage 1" flag includes those slopes.
  * Stage 2's b is fitted on men's rows only (women's z = 0), so it does not couple the tours.
* **N6. The odds source changes inside the scored seasons.** From August 2025 the input is mostly BetOnline's close: 4,095 of 2026's 4,357 matches, the same for both tours. The 2025–26 season flags are read on a source the training seasons never had.
* **N7. Data gaps outside this study.** The 2026 US Open's men's rows lack `indoor` (sealed). `indoor` exists for men only: a candidate data fix for the owner, which would also remove B2's exact proxy.
* **N8. `select`'s early picks are close to arbitrary.** For 2022 it chooses on 2020–21 only: 3,725 men's and 3,335 women's matches, 2020 being the short season. Report its picks per tour and season.
* **N9. The bet set.** A gain where both models sit on the close is worth nothing at the close. Add a flag for the matches where either model's disagreement with the calibrated close exceeds the margin, with the realisation slope per tour and arm.
* **N10. `points_52w` is treated two ways.** borrowsim drops it as "units differ by tour" (`common.py:191-194`), while aligned keeps it on the common scale (`common.py:71-74`). Pick one; its men's-to-women's SD ratio is 1.09.
* **N11. Two builders of one cache.**
  * `sim_inclusion`'s temporary names are fixed (`<file>.tmp`, `common.py:276`). If borrowsim's GPU runner reaches a season whose cache is missing while `--prepare` is still building it, both processes write the same tmp files.
  * The v3 cache was empty at 15:10.
  * Let `--prepare` finish before queueing borrowsim, or add the pid to the tmp names.
  * Each arm's runner is a new process, so `common.py` changes reach every arm not yet started and never a running one. borrow50's draw is the same before and after the amendment.

**History.** The first borrowsim version (`borrow_sim/`, out-of-fold AUC 1.000, every pi 0.5, i.e. a random half) and the second (`borrow_sim_situation/`, which selected on dating precision; found by the analyst) are superseded. The tests require AUC < 0.99, an effective n below 0.95 · n_other, and a cache record matching today's version, features and frame.

## Checked and found right

* **Masks:**
  * split is exactly the own tour's 2013 .. Y − 1;
  * borrow25 and borrow50 keep every own row and exactly round(share · n_other) other-tour rows, from the pool only;
  * borrow25 is nested in borrow50;
  * sizectl has exactly n_own rows from the whole pool, in its mix;
  * draws are reproducible, new per seed, and independent across seeds, seasons and tours;
  * query rows are the season's matches of the model's tour or tours;
  * both-tour arms, `pooled` included, train on the whole pool.
* **Inputs:** the instance's 58 in order; `notour` is the 57 without `tour`; the swap is an involution for every arm.
* **`job_data`:** column order, training rows, and td as stored then swapped. It refuses training rows of season Y or later, and sealed ones.
* **The pooled job, rebuilt from the study's pieces,** has the instance's stored 2022 fingerprint.
* **aligned:**
  * the 39 inputs are all differences;
  * the ratings, price, age, workload, pairs and context are untouched;
  * the SD per tour over the training rows is 1;
  * the scaling commutes bit for bit with the swap;
  * the scales ignore rows of season Y or later.
* **borrowsim, on the v2 cache** (14:20 run; the v3 cache did not exist at the final run, so these checks skipped and re-arm by themselves once it does):
  * its ids are exactly the other tour's pool rows, seasons ≤ Y − 1;
  * pi lies in [0, 1], Σ pi = 0.5 · n_other, pi = min(1, κ r), and r = p / (1 − p) · n_other / n_own;
  * the direction is right: own-like rows are kept more.
* **borrowsim, without any cache:**
  * the draw, on a synthetic pi over 40 seeds: P(keep) = pi, pi = 0 is never kept, pi = 1 always;
  * the coupling with borrow50;
  * on synthetic tours, the build is deterministic and favours own-like rows, and a stale or unrecorded cache is refused;
  * the features don't change under the swap and read neither `tour` nor `indoor`;
  * `np.fmin` and `np.fmax` are moot: neither pair has a missing side, and real layoff inputs are ≥ 0, so v3's rounding is safe.
* **The draw cannot collapse onto a few rows.** A 50% target draws at least half of n_other in expectation.
  * Perfect separation flattens pi to 0.5.
  * Near-perfect separation pushes pi to 0 or 1: a fixed set with an effective n near n_other / 2.
* **TabPFN 9.1.0** drops all-NaN and constant training columns, so the women's split model (`tour`, `best_of`, `indoor`) does not fail.
* **Both environments run numpy 2.4.6,** so the scorer reproduces the runner's draws.
* **The fits on disk** match their masks, the instance's runtime, and today's job-data fingerprints. The cache-hash check waits for borrowsim's first fit.

## Test results

`./python.sh -m pytest test/tour_pooling/test_common.py -q` (15:12): **80 passed, 22 skipped, 1 xfailed, no warnings, 122 s.** The machine was at 100% CPU from other sessions; the same suite took 17 s when it was quiet.

* **The xfail (strict) is B2:** `indoor`'s missingness names the tour in `notour`'s inputs. If `notour` stops carrying the proxy, the test turns into a failure, so the note gets updated.
* **The 22 skips:**
  * 21 borrowsim checks that need the v3 cache (`borrow_sim_v3/` was empty). The same checks passed on the v2 cache at 14:20 (81 passed, 1 xfailed then).
  * The GPU reproduction check: `pooled__both__2022__seed0.npz` was not written yet.
* **Fits checked** (seasons 2019, 2022 and 2026 on disk): 24 split, 12 notour, 16 borrow50 (2019, 2022).
  * All match their masks, columns, ids, td layout, config, frame and the instance's runtime.
  * All carry the fingerprint of today's `job_data`, built with training labels read with the date filter.
* **What the file tests:**
  * the frame and the inputs;
  * every arm's masks: split, borrow25 and borrow50 counts and nesting, sizectl, independence across seeds and seasons;
  * the query masks;
  * `job_data`: order, td as stored then swapped, and the leak and sealed-row refusals;
  * the pooled job against the instance's 2022 fingerprint;
  * aligned: unit SD, untouched columns, the swap, training-only scales;
  * borrowsim: features, cache validity and degeneracy, the draw and its coupling (real and synthetic pi), direction, and the synthetic build with stale-cache refusal;
  * the runner's plan; the fits on disk; the pooled reproduction (skips until it exists).
* **On a busy machine:** the synthetic booster runs with one OpenMP thread. With all 16 threads it crawled under contention (more than 10 minutes).
