# R4 test verifier: `score.py` on synthetic outcomes (agent 5)

7 October 2026 · agent 5 (test verifier). I read the brief, `team.md`, `CLAUDE.md`, `2_audit.md` (C5–C7, Q5), `lead_notes.md`, `3_strategist_build.md`, the draft pre-registration (as edited at 14:25), the harness (`common`, `arms`, `forecasts`, `score`, `local_fits`), the shared helpers it copies or imports (`tabpfn_thinking/common.py`, `feature_interactions/{tabpfn_tests,screen}.py`), `surface_ios/score.seed_var` and `test_ssp_harness.py`.

* **Labels.** **Observed** = computed here; each figure names its script and output. *Inferred* = reasoning. **Fix** = what the owner should change; I edited no builder's file.
* **What was verified.** Scorer code hash `072dfe41…b586bc` (`SCORER_CODE_SHA256` as `score.py --check` computes it, 14:40). `score.py` (13:58) and `forecasts.py` (13:57) did not change during my work. `arms.py` and `common.py` changed at 14:24 (the red team's F1 fix to `feature_status`, outside the scoring path); I re-ran part 1 and the strategist's 23 tests on the final code. Both pass.
* **No match result was read.** Part 1 proves it for `--synthetic` and `--check`. The only labels my scripts touch are the fake labels of the strategist's stand-in world, in a temporary folder (part 8). No GPU; `score.py --run` was not run on the study tree.
* **Scripts:** `src/eda/serve_speed_tabpfn/design/verifier_*.py`. **Outputs:** `data/studies/serve_speed_tabpfn/design/verifier_*`.
* **Directions.** P2 and every paired gain: mLL, positive = the named arm has the lower log loss (better). Coefficients: log-odds per unit of the column, positive = the higher-speed man wins more than the base says. A 95% interval spanning 0 is a tie. Rates are per replicate, with Monte Carlo SEs.

## Verdict: **sign off with fixes.** Fix V1–V5 before the hash; the fits may continue.

**What holds (observed):**
* P2 measures what §7 says, with the right sign. It is unbiased for the exact expected gain: every planted row is within 1.4 Monte Carlo SEs. Its interval covers that gain in 94.2–96.0% of replicates.
* **P2 is conservative at the null.** It rejects 0.35–0.75% two-sided against a nominal 5%, because the empirical seed term double-counts per-match seed noise. At the planted effects that term is 0.1–4% of SE² and costs at most 1.8 power points.
* S0 is unbiased (|bias| ≤ 0.0011 per unit) and covers β in 95.4–97.4% of replicates. Its null rejection is 3.1–4.7%.
* Every endpoint, S0–S14, reads with its registered sign under a planted improvement and under a planted reversal (33 rows × 2 worlds). S13 and S14 behave as defined.
* Calibration, the close's calibration and the nudge read seasons < Y only: bit-identical under perturbation, with a positive control.
* Seed sets are one set per comparison. Calibration uses seeds 0–3. The seed term equals `surface_ios.seed_var` to the last bit.
* `--run` refused all 16 refusal cases before reading a label.

**What must change:**
* **S6(b)'s odds regression is not a valid test (V1).**
* `--run` can spend its one run with fits missing (V2).
* Three pre-registration texts would mislead a reader (V3–V5).

## 1. Issues and fixes

| # | Severity | Owner | Issue (observed unless marked) | Fix |
|---|---|---|---|---|
| V1 | **High** (a secondary; fix or drop before the hash) | Strategist | **S6(b), odds version** (`score.moves`: M on [η_B,early − logit p24, η_A1,early − η_B,early]) **rejects a true null in 24–43% of replicates** (`verifier_s6.json`: 41.5% all, 23.7% clean; the full null world, `verifier_multiplicity`: 43.0% / 24.3%). With A1 1% more confident than the base and no information, the slope is −4.3 and rejects in 100%. Two mechanisms, both present in real fits (*inferred*, then confirmed by switching each off): **(a)** η_B,early's seed noise sits in both regressors with opposite signs, while x1 correlates with M (the 24-h price's error reverts), giving a bias of about +0.28; **(b)** any arm-level confidence difference t puts t·η_B into x2, while M's residual carries −λ(1−a)·η_B (the base's raw over-confidence against the price), so the slope is driven by (1−a)/t. Seed-level t (SD ≈ 0.001 for a 16-seed mean) varies by sample, so the cluster SE misses it: the slope's SD across replicates is 1.24 against a reported SE of about 0.5. The no-odds version is valid: 4.8–6.8% at the null, unaffected by t | Regress M on **[η_B^{0–7},early − logit p24, η_B^{0–7},early, η_A1,early − η_B^{8–15},early]** and read the last slope (disjoint base seeds plus an η_B control). Observed: null 5.8–7.2% in all three null worlds; planted +0.89 against an expected +0.92, detected 100%. Or drop the odds version and keep the no-odds one. Either way, state it in §8 |
| V2 | **Medium** (before the hash) | Strategist | **`--run` does not refuse missing fits.** With every A2 fit absent, it ran, wrote `results.json`, marked S8_A2 and S8_A1_vs_A2 unavailable and dropped the multiplicity denominator from 31 to 29. The one run is spent. A missing P2 fit aborts the run, but only **after** `labels()` loaded the outcomes, so §11's "before reading any result" holds for hashes, features, stale fits and reuse checks, not for missing fits (`verifier_prereg.json`, stand-in world) | Before `labels(P)`, refuse if any (arm, season, seed) in `needed_fits()` is missing, the list `--check` already writes |
| V3 | **Medium** (pre-registration text) | Strategist / lead | **§8 S8 says "the second-named arm better".** The code makes positive = A2, A3, A1 and A3 respectively, the **first**-named arm of "A2 against the base; A3 against the base; A1 against A2; A3 against A1". Verified by planted worlds (part 5) | Write: "positive = A2 / A3 / A1 / A3 (the first-named arm in each pair) better" |
| V4 | **Medium** (decision text) | Lead | **Decision row 3 overstates.** "The column does not deliver it" is the reading in **25–50%** of worlds where the column delivers **all** of the planted term (capture 1.0, β 0.05–0.09; table 3). Cause: S0 has far more power than P2 at small effects (93% against 43–76% at β 0.09). *Inferred:* P2's gain grows as c(2 − c) and its SE as c, so its power **falls** as capture rises; S0's does not depend on capture | Reword row 3: "S0 detects information beyond the base; P2 ties. P2 has less power than S0 at small effects, so the tie does not show the column fails; S10 (capture) and S9 say whether it delivers" |
| V5 | **Medium** (process; before any real-A1 check) | Strategist / lead | **`synthetic(arms="real")` exposes the learned speed coefficient before the hash.** It reports S10 (and P2 under a planted β) from the real A1 forecasts. TabPFN learned that coefficient from match results of 2013..Y−1, which include 2024–25 for the 2025–26 fits. Reading it before the hash relates `spd_f` to a function of results (brief 2.1). *Inferred* | Gate `arms="real"` behind `verify_prereg` (run it only after the hash), or drop S10 and P2's mean from its output. For the lead's planned real-A1 repeat, see §9 |
| V6 | Low (label) | Strategist | **S0/S12's b is per unit of the column, not per SD of the column.** `encompassing` divides by sd_z and back. `spd_f`'s SD is 1.106 in men 2024–26 and 0.991 in 2022–23 (`verifier_prereg.json`). For S12 the unit is one registered SD of x_raw (5.998 km/h), the published β's unit | Change "per SD of the column" (header, S0, S12, `encompassing`'s `unit`) to "per unit of the column (spd_f: one s_f = 2.224 km/h; spd_raw: 5.998 km/h)". `sd_z` is already in the output |
| V7 | Low | Strategist | `FORECASTS_SHA256` "pins" the fits (§2–§3), but `--run` never checks it | If the line holds a hex, recompute `forecasts_hash()` in `--run` and refuse on a difference |
| V8 | Low | Strategist / lead | `core.autocrlf = true` here. `verify_prereg` hashes raw bytes (the code hash normalises CRLF), so a later checkout of the committed file can change its hash and `--run` will refuse. This fails safe | Hash with CRLF → LF normalised in `verify_prereg` and in the command that writes `preregistration.sha256` |
| V9 | Low | Strategist | S10's a is in raw log-odds, while S0's b is on the calibrated (outcome) scale, so a / b_S0 overstates the delivered share by 1/s (about 1.1). Observed: S10 = capture·β/s exactly | Also report s_Y·a / b_S0, with s_Y A1's men's calibration slope |
| V10 | Low (statistical; the ruling stands) | Lead (report text) | The empirical seed term makes P2 (and S14, S7, S1–S8) **conservative near 0**: half of SE² at the null, 0.1–4.4% at the planted effects (table 2). Block-only P2 is near nominal everywhere (4.8–5.5% at the null; coverage 94.0–96.0%). The real seed noise is per-match: a seed-level temperature is 3.5% of it, and the block design effect is 0.84 (`verifier_seeds.json`). So the term has little to protect against (*inferred*) | No code change. In the report, call P2's interval conservative near 0 and cite S11's block-only interval beside it |
| V11 | Info | Lead | §10's power is for the strategist's model of an x_raw-like column (E[z²] ≈ 0.63, partial coverage). On the real `spd_f` (non-zero on 7,066 of 7,068; E[z²] ≈ 1.22) the registered tests are more powerful per unit β (table 3): P2 74–76% at β 0.09 and capture 0.5 against §10's 45–51%. The units differ (§10 is per SD of x_raw), so this is not a contradiction | Add table 3 as "power per unit of spd_f" |
| V12 | Info | Lead | **Multiplicity under the null** (300 replicates, every arm, `verifier_multiplicity/`): mean 1.70 of 31 intervals exclude 0, against the code's 0.05 × 31 = 1.55. The mix is not chance: S13 contributes 0.49 (by construction), the S6(b) odds rows 0.67 (V1), and the paired rows ≤ 0.013 each. The count is overdispersed: P(≥ 5) = 4% | After V1, give this null reference instead of "5% × K", and state the denominator |
| V13 | Info | — | `Bank.eta` averages with pandas' NaN-skipping mean, unlike `forecast`, which refuses NaN. Latent only: td ids are checked per fit, and the early ids are identical across all 16 base seeds (observed) | Optional: refuse NaN in `eta` |
| V14 | Info | Lead | **[lead] counts** (observed; counts only): recency both / one / neither 5,420 / 1,130 / 518. Women's `id_conflict` **in the scored population: 21** (all 2026, all flipped); 67 of the frame's 88 are debut-season matches. `POPULATION_SHA256` `e4ab0787…5296ef27`. `repro_check.json`: passed, max difference 0.0 on all blocks | Fill §6 |

## 2. Parts 1–8 at a glance

| Part | Check | Result (observed) | Script → output |
|---|---|---|---|
| 1 | **No outcome read in synthetic mode.** Call trace: `labels`, `job_data` and the fingerprint check never run. Read spy: every parquet read names its columns, and none is a result. Substitution: copies of the model frame without `a_won`, Stage 0 reduced to ids, and the early frame without results; plus a frame whose `a_won` is coin flips | **Pass.** Output bit-identical to the real files in both substitutions; `--check` also runs on the stripped copies (men 7,068) | `verifier_noread.py` → `verifier_noread.json` |
| 2 | Worlds from the real base forecasts (`model`, seeds 0–15, 2019–2026; reuse checks passed) and the real `spd_f` | W1 = the scorer's own `synthetic()`; W2 = both arms with independent noise of the measured structure; W2s = W2 plus a structural column perturbation; W3 = real seeds only | `verifier_seeds.py`, `verifier_worlds.py` |
| 3 | Null | Table 2 | `verifier_tables.py` → `verifier_tables.json` |
| 4 | Planted β 0.05 / 0.09 / 0.15 × capture 0.5 / 1.0 | Table 3 | same |
| 5 | Signs of P2 and S0–S14 | **Pass** (all 33 rows, both worlds; decision rows 1 and 2) | `verifier_signs.py` → `verifier_signs.json` |
| 6 | Seasons < Y only | **Pass** (§6) | `verifier_window.py` → `verifier_window.json` |
| 7 | Seeds | **Pass** (§7) | `verifier_seedsets.py` → `verifier_seedsets.json` |
| 8 | Pre-registration against the code; refusals | 16 refusals pass; mismatches in §8; V2 | `verifier_prereg.py` → `verifier_prereg.json` |

**The worlds** (truth for every frame match 2019–2026; z = `spd_f`, 0 for women):
* **W1, the scorer's `--synthetic` machinery** (`score.synthetic`, output redirected to `verifier_worlds/synthetic/`):
  * y ~ Bernoulli(expit(0.9·η_B + β·z)), with η_B the base's real 16-seed log-odds;
  * A1's seed k = η_B + capture·(β/0.9)·z + N(0, 0.019²);
  * the base keeps its real seeds. *Inferred blind spot:* the base's seed noise is inside the truth, so only A1's noise reaches P2, while the seed term counts both arms.
* **W2, two-sided** (the scorer's own functions, forecasts injected):
  * truth = a_tour·μ + β·z, with μ the real 16-seed mean and a = 0.92 for men, 0.87 for women. These slopes are assumed; the real ones need outcomes;
  * both arms are synthetic, with **independent** seed noise of the measured structure: per-match SD = each match's real SD across the 16 seeds (RMS 0.0187); seed temperature τ ~ N(0, 0.0028²); no within-block clustering (design effect 0.84).
* **W2s:** W2 plus u ~ N(0, 0.02²) in A1 only, fixed across seeds: adding a column moves the fit without adding information.
* **W3, real seed noise only:** each replicate splits the 16 real seeds at random into truth (6), base (5) and A1 (5). The comparison is P2 with one 5-seed set; the null is exact.

## 3. The null (β = 0): P2 and S0 rejection rates

Nominal: 5% two-sided, 2.5% per side. Monte Carlo SE: ±0.49 points at 5% with 2,000 replicates, ±0.13 at 0.35%. E[G] is the exact expected gain given each replicate's calibrated forecasts (`score.synthetic`'s formula); its mean is the unconditional expectation.

| World | Reps | Mean E[G] (mLL) | Mean P2 | SD(P2) | RMS SE: registered / block-only | P2 reject + / − | **P2 two-sided** | Block-only + / − (two-sided) | Coverage of E[G]: registered / block-only | S0 reject + / − (two-sided) | S0 covers β |
|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 (scorer's own) | 2,000 | −0.0016 | −0.0027 | 0.0233 | 0.0393 / 0.0232 | 0.05% / 0.30% | **0.35%** | 2.0% / 3.25% (5.25%) | 99.65% / 95.0% | 1.75% / 1.40% (3.15%) | 96.9% |
| W2 (two-sided) | 2,000 | −0.0000 | +0.0006 | 0.0317 | 0.0445 / 0.0315 | 0.35% / 0.40% | **0.75%** | 2.80% / 2.65% (5.45%) | 99.25% / 94.7% | 1.55% / 1.95% (3.50%) | 96.5% |
| W2s (column moves the fit) | 1,000 | −0.0342 | −0.0327 | 0.1046 | 0.1083 / 0.1036 | 0.60% / 4.90% | **5.50%** | 0.80% / 6.00% (6.80%) | 96.6% / 95.5% | 1.80% / 2.20% (4.00%) | 96.0% |
| W3 (real seeds, 5 v 5) | 2,000 | −0.0000 | −0.0012 | 0.0566 | 0.0799 / 0.0562 | 0.15% / 0.25% | **0.40%** | 2.05% / 2.75% (4.80%) | 99.5% / 95.3% | – | – |
| All arms (`verifier_multiplicity`) | 300 | – | – | – | – | – | 1.3% | – | – | 2.3% / 2.3% (4.7%) | – |

* **The block-only SE matches P2's true spread** (RMS 0.0315 against SD 0.0317 in W2). The registered SE is √2 larger, because the seed term is 50% of SE² at the null (W2 0.498, W3 0.484).
* **In W2s, A1 really is worse** (E[G] −0.034 mLL, A1 worse), and the 4.9% negative rejections are true detections. The registered interval is then near nominal (seed term 9% of SE²).
* **S0 is mildly conservative** because it takes the largest of three variances. The week interval of S11, which carries the seed term, rejects 0.6% (W2).
* **Decision rows at the null** (W2): row 4 in 95.75%, row 5 in 1.95%, row 3 in 1.55%, row 1 in 0.35%, row 2 in 0.40%.

## 4. Planted effects

β is in log-odds per unit of `spd_f`; capture is the share of β·z added to A1 on the calibrated scale.
* G* = the ideal gain: perfect calibration, no seed noise.
* E[G] = the mean exact expected gain given the forecasts.
* Bias = mean(P2 − E[G]) ± MC SE.
* Power = P(lo > 0).
* 500 replicates per row. Rows with the same β share their outcome draws (common random numbers), so S0 is identical across captures.

| World | β | Capture | G* | E[G] | Mean P2 | Bias | Coverage: registered / block-only | **P2 power**: registered / block-only | S0 mean b (bias ± MC SE) | S0 covers β | **S0 power** | S10 (constructed) | S14 power | Decision rows 1 / 3 / 4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 0.05 | 0.5 | 0.231 | 0.229 | 0.232 | +0.003 ± 0.007 | 94.4 / 94.0% | **32.8** / 33.6% | 0.0507 (+0.0007 ± 0.0012) | 95.4% | **46.2%** | 0.0278 (0.0278) | 31.6% | 164 / 72 / 264 |
| W1 | 0.05 | 1.0 | 0.308 | 0.306 | 0.313 | +0.006 ± 0.014 | 94.2 / 94.2% | **21.2** / 21.4% | same | 95.4% | 46.2% | 0.0556 (0.0556) | 20.0% | 106 / 125 / 268 (1 row 2) |
| W1 | 0.09 | 0.5 | 0.748 | 0.746 | 0.753 | +0.007 ± 0.013 | 95.0 / 94.8% | **76.0** / 76.6% | 0.0908 (+0.0008 ± 0.0011) | 97.0% | **93.4%** | 0.0500 (0.0500) | 73.4% | 380 / 87 / 33 |
| W1 | 0.09 | 1.0 | 0.997 | 0.995 | 1.009 | +0.014 ± 0.025 | 94.6 / 94.6% | **46.2** / 46.4% | same | 97.0% | 93.4% | 0.1000 (0.1000) | 42.4% | 231 / 236 / 32 (1 row 2) |
| W1 | 0.15 | 0.5 | 2.073 | 2.069 | 2.082 | +0.012 ± 0.021 | 95.6 / 95.4% | **99.2** / 99.2% | 0.1509 (+0.0009 ± 0.0011) | 96.6% | **99.8%** | 0.0833 (0.0833) | 99.0% | 496 / 3 / 1 |
| W1 | 0.15 | 1.0 | 2.762 | 2.759 | 2.784 | +0.025 ± 0.041 | 95.0 / 95.0% | **87.2** / 87.2% | same | 96.6% | 99.8% | 0.1667 (0.1667) | 84.8% | 436 / 63 / 1 |
| W2 | 0.05 | 0.5 | 0.229 | 0.229 | 0.221 | −0.008 ± 0.007 | 95.6 / 95.2% | **31.0** / 32.8% | 0.0489 (−0.0011 ± 0.0011) | 96.2% | **42.6%** | 0.0272 (0.0272) | 31.2% | 155 / 60 / 285 |
| W2 | 0.05 | 1.0 | 0.306 | 0.306 | 0.289 | −0.017 ± 0.014 | 95.6 / 95.2% | **16.0** / 16.2% | same | 96.2% | 42.6% | 0.0543 (0.0543) | 16.4% | 80 / 133 / 286 (1 row 2) |
| W2 | 0.09 | 0.5 | 0.743 | 0.742 | 0.731 | −0.011 ± 0.012 | 95.2 / 95.0% | **74.2** / 75.6% | 0.0892 (−0.0008 ± 0.0011) | 97.4% | **93.2%** | 0.0489 (0.0489) | 73.8% | 371 / 95 / 34 |
| W2 | 0.09 | 1.0 | 0.990 | 0.990 | 0.966 | −0.024 ± 0.024 | 95.0 / 95.0% | **43.2** / 43.2% | same | 97.4% | 93.2% | 0.0978 (0.0978) | 42.0% | 216 / 250 / 34 |
| W2 | 0.15 | 0.5 | 2.059 | 2.056 | 2.050 | −0.006 ± 0.021 | 96.0 / 96.0% | **98.8** / 98.8% | 0.1499 (−0.0001 ± 0.0011) | 97.0% | **100%** | 0.0815 (0.0815) | 98.8% | 494 / 6 / 0 |
| W2 | 0.15 | 1.0 | 2.744 | 2.741 | 2.723 | −0.018 ± 0.041 | 96.0 / 96.0% | **83.6** / 83.8% | same | 97.0% | 100% | 0.1630 (0.1630) | 83.0% | 418 / 82 / 0 |
| W2s | 0.09 | 0.5 | 0.743 | 0.709 | 0.714 | +0.005 ± 0.012 | 95.8 / 95.8% | **67.0** / 67.8% | 0.0905 (+0.0005 ± 0.0010) | 96.6% | 95.4% | 0.0489 (0.0489) | 66.0% | 335 / 142 / 23 |
| W3 | 0.09 | 0.5 | 0.743 | 0.743 | 0.760 | +0.017 ± 0.012 | 95.4 / 95.0% | **75.6** / 76.6% | – | – | – | – | – | – |

**Reading (observed unless marked).**
* **P2 is unbiased for the exact expected gain.** The largest |bias| / MC SE is 1.4 (W3).
* **E[G] is within 0.004 mLL of G*** in W1–W3. Seed noise and calibration error cost almost nothing; W2s's structural perturbation costs 0.034 mLL.
* **Coverage is 94.0–96.0%** for both intervals (registered 94.2–96.0%).
* **The seed term costs 0–1.8 points of power.** It is 0.1–4.4% of SE² at these effects.
* **S0 recovers β within 0.0011**, covers it in 95–97% of replicates, and is more powerful than P2 in every row.
* **P2's power falls as capture rises.** At β 0.09 it is 74–76% at capture 0.5 and 43–46% at 1.0 (V4).
* **S10 equals capture·β/s exactly** (raw scale; V9).

## 5. Signs and definitions (part 5)

* **Worlds** (`verifier_signs.py`). Truth for men: a_tour·μ + 0.5·`spd_f` + 0.25·`spd_raw` (NaN → 0); for women: + 0.5·`spd_f_all`.
* **Arms.** Each arm captures part of what its own column carries:
  * A1: 0.5 of the `spd_f` term;
  * A2: 0.5 of the `spd_raw` term;
  * A3: 0.8 of the `spd_f_all` term;
  * the no-odds pair: 0.85·μ ± the A1 shift;
  * early-fed forecasts: the base and A1 plus d ~ N(0, 0.1²).
* **Synthetic prices.** The 30-min price moves toward the speed term.
* **Two worlds.** "Improve" holds that truth in every season. "Harm" reverses the speed terms in 2024–26 only, with the same arms.
* **Result.** Every row has the expected sign in both worlds. The decision table picks row 1 (improve) and row 2 (harm).

| Endpoint | Unit | Expected (improve / harm) | Improve | Harm |
|---|---|---|---|---|
| P2 | mLL | + / − | +29.25 [+25.72, +32.79] | −42.54 [−48.86, −36.23] |
| S0 | log-odds per unit | + / − | +0.65 [+0.59, +0.71] | −0.66 [−0.74, −0.58] |
| S1 2024 / 2025 / 2026 | mLL | + / − | +31.9 / +27.0 / +28.5, all exclude 0 | −49.0 / −32.7 / −47.3, all exclude 0 |
| S2 | mLL | + / − | +27.61 [+23.06, +32.16] | −38.62 [−47.73, −29.51] |
| S3 both / one / neither | mLL | + / − | +36.0 / +9.95 / +0.74 (neither: tie) | −51.8 / −17.6 / −0.55 (neither: tie) |
| S4 A1 women | mLL | 0 / 0 | +0.02 [−0.07, +0.11], tie | −0.01 [−0.08, +0.06], tie |
| S4 A1 both; A3 women; A3 women without `id_conflict` | mLL | + / − | +15.15; +4.44; +4.32 | −22.03; −7.75; −7.77 |
| S5 | mLL | + / − | +33.01 [+28.92, +37.09] | −51.36 [−58.92, −43.80] |
| S6(a) all / clean | mLL | + / − | +25.66 / +12.48 | −42.46 / −22.05 |
| S6(b) odds all / clean | slope | + / − | +1.45 / +1.49 | −1.42 / −1.46 |
| S6(b) no-odds all / clean | slope | + / − | +0.93 / +1.00 | −0.91 / −0.93 |
| S7 | mLL | + / − | +31.56 [+27.54, +35.57] | −47.48 [−54.72, −40.24] |
| S8 A2 v base; A3 v base (men) | mLL | + / − | +10.50; +39.90 | −12.41; −72.54 |
| S8 A1 v A2 (positive = **A1** better) | mLL | + / − | +18.76 [+16.63, +20.90] | −30.12 [−34.40, −25.83] |
| S8 A3 v A1 (positive = **A3** better) | mLL | + / − | +10.64 [+9.01, +12.28] | −30.01 [−34.33, −25.70] |
| S9 shrunk / unshrunk | mLL | + / − | +42.20 / +45.69 | −40.78 / −62.13 |
| S10 (a > 0 = moved toward the higher speed state) | log-odds per unit | + / + | +0.272 (= 0.5·0.5/0.92) | +0.272 |
| S11 block-only / week | mLL | + / − | +29.25 (both) | −42.54 (both) |
| S12 | log-odds per unit | + / − | +0.80 [+0.68, +0.92] | −0.83 [−0.95, −0.70] |
| S13 (positive = calibrated base better than calibrated close) | mLL | + / + | +2.38 [+0.92, +3.85] | +0.44 [−0.62, +1.50], tie |
| S14 (positive = A1 lower Brier) | 1000 × Brier | + / − | +12.52 [+10.97, +14.06] | −17.78 [−20.49, −15.06] |

**S13 against synthetic closes** (no speed term anywhere):

| World | S13 (mLL) | Close's slopes (men, 2024–26) | Reading |
|---|---|---|---|
| A: truth = the base; the real close | +1.43 [+0.34, +2.51] | about 1.13 | Base better: positive, as defined |
| B: a perfect close (it knows a term d ~ N(0, 0.3²) that the base lacks) | −9.60 [−12.29, −6.91] | about 1.03 | Close better: negative |
| C: the same close, over-confident (logit p = 1.25 × truth) | −5.61 [−8.94, −2.27] (uncalibrated: −0.77) | about 0.82 ≈ 1/1.25 | The decided recalibration recovers it |

S14's seed term is computed on the Brier scale (code: `seed_loss(qk, y, brier)`). Observed: at the null, S14 rejects 0.4% per side (W2), as conservative as P2.

## 6. Calibration and the nudge read seasons < Y only (part 6)

The world is the planted improve world with every arm injected (`verifier_window.json`). For each Y in 2024–2026:

| Perturbation | Per-tour slopes of all 6 arms | Close's slopes (S13) | Nudge s, b̂, SE, b̃ (S9) | Calibrated season-Y forecasts of all 6 arms; nudge forecast |
|---|---|---|---|---|
| B: outcomes of Y flipped | **bit-identical** | **bit-identical** | **bit-identical** | **bit-identical** |
| A: outcomes, every arm's forecasts and p_mkt of seasons ≥ Y replaced by noise | **bit-identical** | **bit-identical** | **bit-identical** | (replaced by construction) |
| C (positive control): outcomes of Y − 1 flipped | changed | changed | changed (b̂_2024 0.614 → 0.063) | changed |

**Fit metadata** (observed at 14:2x; meta only, never a speed arm's forecast):

| Folder | Fits | `train_seasons` = [2013, Y − 1] | Training shape = the expanding window's | Fingerprint |
|---|---|---|---|---|
| This study, fits so far | 53 | 53 / 53 | 53 / 53 | 53 |
| This study, reproductions | 3 | 3 / 3 | 3 / 3 | 3 |
| Feature interactions (`model` seeds 3–15, plus 2019 seeds 0–2) | 107 | not stored | 107 / 107 | 107; all equal this harness's (`checks/fingerprint_check.json`) |
| Rating race (`model` 0–2 from 2020; `model_noodds` 0–2) | 45 | not stored | 45 / 45 | none; reproduced exactly (`checks/repro_check.json`, max difference 0.0) |

`forecasts.load_fit` refuses a copy of a real fit whose stored training shape is one row short, and loads the unchanged copy (refusal test).

## 7. Seeds (part 7)

* **One seed set per comparison** (`verifier_seedsets.json`). Each of the 21 paired comparisons ran in a fresh `Scorer` with `Bank.per_seed` spied:
  * scored seasons: one seed set, the same for both arms (0–15 for A1 against the base, including S4 A1 and S6(a); 0–7 for the rest);
  * calibration reads: seeds 0–3, td, windows exactly 2019..Y − 1 for each scored Y.
* **Other endpoints:**
  * S0 and S12: base 0–15;
  * S10: A1 and base 0–15;
  * S13: base 0–15;
  * S6(b): base and A1 early, 0–15; the no-odds pair, 0–7;
  * S9: base 0–3 for each fit window, 0–15 applied.
* **Tamper test.** A bank that returns one seed fewer for A1 is refused ("unequal seed sets"). Equality is by construction (one `seeds` tuple per `Comparison`); the shape check is the assertion.
* **The seed term equals `surface_ios.seed_var` bit for bit.** P2 (16 seeds): v_base 0.000407212…, v_arm 0.000865813… (mLL²). S8_A2 (8 seeds): equal too.
* **Convention note (V10, *inferred*).** surface_ios calibrated each seed with its own slope; this scorer uses the arm's seed-mean slope, as the audit's C6 says. Own slopes are impossible here: A1 has only seeds 0–3 in 2019–23. On the base, the own-slope variance is 1.09× the seed-mean one. Reword §7 to "the surface-IOS seed_var formula".

## 8. The pre-registration against the code

**Mismatches:**
1. **§8 S8 direction** "the second-named arm better": the code is first-named better (V3).
2. **§8 S6(b)**: the odds version as specified is not a valid test (V1). The code implements the text faithfully, so the text must change.
3. **§7 decision row 3**: its reading is stronger than the test supports (V4).
4. **Header, §8 S0 and S12**: "per SD of the column" should read per unit of the column (V6).
5. **§11 step 6**: "refuses, before reading any result" does not cover missing fits; a missing secondary fit does not stop the run (V2).
6. **§2–§3, `FORECASTS_SHA256` "pins them"**: not enforced (V7).
7. **§7 "the surface-IOS seed_var convention"**: the formula, yes; the per-seed calibration differs (V10).
8. **§9 "against the 5% expected by chance"**: the null count is not binomial at 5% (V12).
9. **§10 power**: a different column model and different units (V11).
10. **§6 `id_conflict` "88 in 2026"**: 21 in the scored population (V14).
11. **§5**: omits the build note's 1,000-row minimum per tour for a calibration fit, which is in the code. Add one line.

**Matches** (observed): P2's definition, population and sign; 7,068 = 2,674 / 2,620 / 1,774; 33 blocks; women 6,586 (2,460 / 2,485 / 1,641); both tours 13,654; Polymarket 1,442 (232 + 1,210), clean 582 (117 + 465), with 12 and 11 blocks; calibration (per tour, no intercept, 2019..Y − 1, debut out, seeds 0–3, applied to the scored seed mean); S0's design (season × tour slopes, per-tour cubic, the largest of three clustered variances, t on 32 df); S1–S5, S7 and S9–S14 as written; the decision table's logic; the code-hash file list; the six keys `--run` verifies.

**Refusals of `--run`** (16 cases, the stand-in world, `labels()` booby-trapped): results already present; no pre-registration; no `.sha256`; a `.sha256` that does not match; the draft's `[lead]` placeholders; the real draft text, hashed; each of the six recorded hashes wrong; a stand-in feature meta; reproduction check not passed; a stale speed fit. All refuse before any label is read. With every fit present, `--run` runs and writes both files.

## 9. Repeating the checks with the real A1 forecasts

* **Before the hash, result-free only:**
  * the loader's acceptance of every A1 file (columns, training shape, ids, `feature_sha256`);
  * the seed sets present;
  * `--check`'s stale-fit list.
* **Not before the hash** (V5): anything that relates A1's forecasts to `spd_f` or to an outcome. That includes S10, P2 under a planted β, and `synthetic(arms="real")`. TabPFN learned A1's use of the column from results that include 2024–25 for the 2025–26 fits.
* **After the hash, before `--run`:**
  * `verifier_worlds.py`'s W1 with `arms="real"`;
  * the part 6 and part 7 scripts with the real A1 injected in place of the synthetic one.
  The code is frozen by then, so the look cannot change the test; log it.

## 10. Looks (for the ledger)

| # | Seasons | What was related to what | Script → output |
|---|---|---|---|
| V-L1 | 2019–2026 | Forecasts only: the base's 16 seeds' deviations (per-match SD, seed temperature, block design effect, heteroscedasticity by \|η\|) | `verifier_seeds.py` → `verifier_seeds.json` |
| V-L2 | 2019–2026 | **Synthetic outcomes** drawn from the real base forecasts and the real `spd_f`, scored by `score.py` (P2, S0, S10, S11, S13, S14). The real closing price `p_mkt` is scored against synthetic outcomes in S13. No statistic of the real feature–forecast or feature–price relation was computed or reported | `verifier_worlds.py` → `verifier_worlds/`; `verifier_tables.py` → `verifier_tables.json`, `.csv` |
| V-L3 | 2019–2026 | As V-L2 with every arm injected (`spd_raw` and `spd_f_all` values used to build synthetic arms) and **synthetic** Polymarket prices on the real priced rows | `verifier_signs.py`, `verifier_window.py`, `verifier_seedsets.py`, `verifier_multiplicity.py`, `verifier_s6.py` → their `.json` |
| V-L4 | 2022–2026 | Feature values only: `spd_f`'s SD (men 2022–23, 2024–26) and non-zero count | `verifier_prereg.py` → `verifier_prereg.json` |
| V-L5 | 2024–2026 | Counts only: populations, blocks, recency strata, `id_conflict`, priced rows | same |
| V-L6 | – | Fit metadata (`train_seasons`, shapes, fingerprint presence) and the two reuse-check files; `--check`'s byte hash of the existing fit files. No speed arm's forecast was read | `verifier_window.py`, `verifier_noread.py` |
| V-L7 | – | The **fake labels** of the strategist's stand-in world (`test_ssp_harness.make_world`), in a temporary folder | `verifier_prereg.py` |

* No real `a_won`, winner, score or result column was read for any season.
* No speed feature was related to any real result or real price.

**Files left in place** (no deletion; for the lead to clean up):
* smoke chunks `verifier_worlds/*_s999.json` and `verifier_multiplicity/null_s999.json`, excluded from every table;
* temporary folders outside the repo: `%TEMP%\ssp_verifier_window_*`, `%TEMP%\ssp_verifier_prereg_*`, and this session's scratchpad (`noread`, `noread_final`: outcome-stripped copies of the model frame, Stage 0 and the early frame).

## Re-verification of the strategist's fixes (7 October 2026, 15:00)

* **What changed.** `score.py` (14:50) and the pre-registration (14:51). `forecasts.py` is byte-identical to round 1 (SHA-256 prefix `e4e18682…`); the NaN refusal (V13) is in `score.py`'s `Bank.eta`.
* **Code verified:** `SCORER_CODE_SHA256` `6bcfc06c…0c04ba8`.
* **Tests and part 1.** The study folder's 49 tests pass, the harness's 29 included. Part 1 (no outcome read in `--synthetic` or `--check`) passes again on the new code.
* **Scope.** Synthetic outcomes only, as before; no real result read, no speed-arm forecast read. I re-checked only what changed.
* **New scripts and outputs:**
  * `verifier_reverify.py` → `verifier_reverify.json`;
  * the round-1 scripts re-run with `--tag reverify`, giving `verifier_s6_reverify.json`, `verifier_signs_reverify.json` and `verifier_multiplicity/reverify_null_s11–16.json`.
  * The round-1 evidence files are kept unchanged.

### Verdict: **sign off.** Nothing found here blocks the hash.

* **Tested and passed:** V1, V2, V5, V7, V8, the fallback, the signs and V12 (table below).
* **Checked by reading the code and the pre-registration only:**
  * V3: S8 now reads "first-named";
  * V4: decision row 3 is reworded, in code and text;
  * V6: "per unit" labels, which also appear in the re-run outputs;
  * V9: `a_cal` added, not tested numerically;
  * V11: a power-per-unit table is in §10;
  * V13: `Bank.eta` refuses NaN.
* **V10 stands by the ruling.**

| Item | Check (observed) | Result |
|---|---|---|
| **V1** S6(b) odds | `score.moves()` now regresses M on [η_B^{0–7} − logit p24, η_B^{0–7}, η_A1^{0–15} − η_B^{8–15}]. It equals the verifier's `control_disj` within **1.3e-12** on every replicate of every world. Null two-sided rejection (all / clean, 400 replicates): measured seed temperature **6.2% / 7.2%**; no temperature **6.0% / 6.2%**; A1 1% more confident with no information **6.5% / 5.8%** (was 100%). Planted: **+0.895 / +0.887** (expected +0.92), detected in 100%. The no-odds version: 4.8–6.8%. In the full null world (600 replicates): 7.8% / 5.5% (was 43% / 24%) | **Pass.** The slight excess over 5% matches the no-odds version and CR1 with 12 and 11 clusters; acceptable for a descriptive secondary |
| **V2** missing fits | Stand-in world, `labels()` booby-trapped: one P2 fit missing (`spd` 2026 seed 15), all 44 A2 fits missing, and one race `model_noodds` seed missing are each **refused before `labels()`**, with no `results.json`. Control (all present): runs, K = 30 | **Pass** |
| **V7** `FORECASTS_SHA256` | A recorded hash equal to the fits runs. One fit rewritten after the hash, or a recorded `0…0`, is **refused before `labels()`**. A line without a hex is not checked (fits not pinned) | **Pass** |
| **V8** CRLF | `--hash-prereg`'s function (`hash_prereg`) on LF text gives the raw LF SHA-256, which equals `prereg_sha256`. The same file converted to CRLF after hashing still verifies, and its keys parse. Hashing the CRLF file gives the LF hash. `--run` on a CRLF checkout runs. A raw `sha256sum` of a CRLF file is refused, so the lead must use `--hash-prereg`, as §11 says | **Pass** |
| **V5** `arms="real"` | On the real tree (no `preregistration.sha256`) it is refused ("no hashed pre-registration") with **zero fit files opened** (spy on `load_fit` and `np.load`). On the stand-in world it is refused before a hash and runs after a valid one. `arms="synthetic"` needs no hash | **Pass** |
| **Fallback** | A `LinAlgError` or `ValueError` (NumPy's `LinAlgError` is a `ValueError`) in S6 (K 30 → 26), S9 (→ 28), S12 (→ 29) or a paired secondary (S8_A2, → 29) marks it unavailable; `--run` completes, with P2 and S0 present. The same error in **P2, S0, S10, S13 or S14 aborts `--run` with no `results.json`**: they sit outside every `try` in `evaluate`, and P2 is computed first | **Pass.** *Note:* the fallback also catches a coding `ValueError` in a secondary. The error text is kept in `results.json`, and the report must state K |
| **Signs** (part 5) | All **33 rows × 2 worlds** keep their registered signs; decision rows 1 and 2; K = 30. S6(b) odds now +1.59 / +1.62 (improve) and −1.57 / −1.58 (harm). Units read "per unit of `spd_f` (one s_f = 2.224 km/h)" and "per unit of `spd_raw` (5.998 km/h)" | **Pass** |
| **V12** multiplicity null | 600 replicates (6 × 100), every arm, no speed term, S13 not counted | below |

### V12: the null reference for §9 (observed, `verifier_multiplicity/reverify_null_s11–16.json`)

* **K = 30** counted intervals in all 600 replicates (S0–S14 less S13; S10 and the ratio are point values).
* **Null mean count = 0.62** (SD 1.06) of 30. A binomial at 5% would give 1.50.
* **P(count ≥ 3) = 5.0%** (MC SE 0.9); **P(≥ 4) = 1.7%** (0.5); **P(≥ 5) = 0.7%** (0.3). Also P(≥ 1) = 37.3% and P(≥ 2) = 16.0%.
* **Distribution:** 0: 376; 1: 128; 2: 66; 3: 20; 4: 6; 5: 1; 7: 1; 9: 2. The tail is overdispersed, because the P2-like rows move together.
* **Largest per-row rates:** S6(b) odds all 7.8%, no-odds all 7.2%, S11 block-only 6.5%, S9 unshrunk 5.8% (a real loss: a nudge fitted at β = 0 adds noise). The paired rows carrying the seed term are each ≤ 1.3%.
* **Decision rows:** row 4 in 96.2%, row 3 in 1.2%, row 5 in 1.3%, rows 1 and 2 in 0.7% each.
* **Caveat (*inferred*).** This null has no structural column perturbation. If adding the column moves TabPFN's forecasts without information (W2s), the paired rows detect that real harm more often, and the count rises.
