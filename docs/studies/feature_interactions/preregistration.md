# The final test: pre-registration

7 October 2026. Written after the screen and M2 ([plan.md](plan.md), "M2: what the rules gave"), before any 2025–2026 result is read. It follows the meta-auditor's checkpoint 1 §6.3 and checkpoint 2's required changes R-A to R-E ([checkpoint_2.md](meta/checkpoint_2.md)). Once the hash lines below are filled and the text's own SHA-256 is recorded in the look ledger, nothing here changes, and `final_test.py --run` runs once.

## What is tested

**One bundle against the current best**, on 2025–2026:

| Arm | Definition |
|---|---|
| **B**, the current best | the 58-input local TabPFN-3.5 (`model`), raw log-odds η_B, walk-forward (each season trained on 2013 to the season before), deployed with the decided calibration: one slope per tour on η_B, fitted on every earlier out-of-sample season from 2019 |
| **F**, the bundle | B plus the nudge layer of plan.md rule 7: logit P_F = s_tour·η_B + b·x, where x is **B-INJ** (registered as "hidden physical impairment"; as measured, rust after a break of six weeks or more, below). B-INJ is the screen's only eligible member (weighted Holm 0.002, weighted BH 0.002). It is deployed as a nudge because TabPFN captured only 0.39 of its term (rule 6) |
| **B₁₄**, the calibration control (checkpoint 2, R-A) | logit P = s′_tour·η_B, fitted exactly like F's nudge but without x. It separates B-INJ's part of F's gain from the change of calibration window (F's slopes from 2014, B's from 2019) |

**How F and B₁₄ are fitted.**
* x is the frozen screen column with the screen's preprocessing: clipped at the 99th percentile of \|x\| on the screen's 2014–2021 rows, divided by its SD there, missing → 0.
* s_tour, b and s′_tour are fitted by maximum likelihood, with no intercept, one slope per tour and b pooled.
* The data are B's out-of-sample forecasts and results of every season from 2014 to the season before, using the seed means of the seeds held for each season: 0–2 in 2014–2015, 0–5 in 2016–2018, 0–15 from 2019.

**Population.** The frozen pre-rebuild model frame's main-tour matches with closing odds in 2025 and 2026, debut seasons out.
* 8,520 matches: 4,394 men's and 4,126 women's; 5,105 in 2025 and 3,415 in 2026.
* Later matches are excluded. The SHA-256 of the sorted match ids is below.
* **These seasons are not naive to every layoff-type idea.** The predictive frontier's "recovery context" group (rest, absence × Elo, retirement losses) was scored against the close from 2019, 2025–2026 included, and tied. B-INJ's members are new constructions, never scored on 2025–2026.

**Data version: the frozen pre-rebuild inputs for B and F alike. The Tennis My Life first-serve fault is not repaired.** The fault is in men's Slams from August 2025 ([round2/feasibility_round2.md](round2/feasibility_round2.md) §4). The departure was accepted at checkpoint 2 (§3.2):
1. It departs from the R2-measure ruling's point 1 ("repair") and from checkpoint 1 §6.3 item 2, which assumed a repair. Repairing means rebuilding shared pipelines that belong to other studies (the IOS, the surface profile, the two-week form) and refitting the base's 16 seeds. The base would then no longer be the frozen B.
2. The 476 rows that the official feeds replaced in the live tables are **not** used, and the 97 Roland Garros 2026 qualifying rows stay.
3. The fault reaches B and F alike, except through B-INJ's member I-045, which reads first serves. The fault-clean secondary excludes any exposure. That is stricter than R2-measure point 2's "share under 20%". It also counts the player's own event, the match itself included, which is conservative.
4. No λ-attenuation is applied.

**Forecasts and files.**
* B's 2025–2026 forecasts (seeds 0–15) and the column arm's (seeds 0–7) exist and have never been scored. All are covered by `FORECASTS_SHA256`.
* The B-INJ column for 2013–2026 is `data/studies/feature_interactions/final/binj_x.parquet`. Its 2013–2024 rows reproduce the frozen screen column exactly (checked by `final_test.build_x`).
* `--run` checks every hash below **before it loads any result**.

## Primary endpoint

logit P(A wins) = Σ_{tour × season} a·η_B[0–7] + Σ_tour c·η_B[0–7]³ + b·dev

* **dev** = logit P_F[8–15] − logit P_B[8–15]: each arm deployed (F with its nudge layer, B with its calibration), computed from the seed mean of seeds 8–15. That is disjoint from the offset's seeds 0–7 (critique §1.7).
* The free slopes absorb the calibration difference within dev, apart from a term of about 0.0005 logit (checkpoint 2 §3.1).
* **The variance** is the union-clustered one (four-week blocks and shared players, the largest of three), with t on G − 1 degrees of freedom (21 four-week blocks, 20 df).
* **The reading is the two-sided 95% interval on b.**
  * Above 0: the bundle adds information beyond the current best.
  * Below 0: it is harmful.
  * Spanning 0: a tie.
  * The one-sided p is reported beside it.

## Effect size and expectations

* **Effect size, read: F against B₁₄**, B-INJ's own part. The paired log-loss gain, seed means of 0–15, in mLL. Positive = F has the lower log loss (better). 95% interval over four-week blocks; a tie when it spans 0.
* **Reported beside it:** B₁₄ against B (the calibration window's part) and F against B (the deployment gain). Per match, the last equals the sum of the other two.
* **Expected gain** (rule 10; `src/eda/feature_interactions/shrinkage.py` → `final/shrinkage.json`).
  * The 34 members' one-sided joint p are mapped to z = Φ⁻¹(1 − p). The five Wald rows enter through the same map.
  * f is SciPy's Gaussian kernel density with its Silverman rule: kernel SD (3n/4)^(−1/5) × SD(z) = 0.688.
  * B-INJ's z of 3.99 shrinks to **3.41**: an expected gain of **0.116 mLL** (capture 1 for a nudge).
  * The narrower textbook bandwidth, 0.9·min(SD, IQR/1.34)·n^(−1/5) = 0.441, gives 3.96 and 0.156 mLL.
  * The likely range is therefore 0.12–0.16 mLL. (`shrinkage.json`'s earlier power fields, 0.25 and an MDE of 0.50, are superseded by the verifier's below.)
* **Power**, as coded, from the final-test verifier's synthetic runs ([final_test_verification.md](meta/final_test_verification.md)):
  * the primary is conservative, with a false-positive rate of 2.35% at a nominal 5%, because it takes the largest of three variances;
  * power is 16% at 0.1 mLL, 34% at 0.2 and 72–76% at 0.5;
  * the 80% MDE is about 0.57 mLL;
  * **power is 19–26% at the expected gain.**
* **A tie is the likely reading even if B-INJ is real.** A tie does not refute the 2014–2024 evidence (z_joint 3.99, both windows in the declared direction).

## Secondary endpoints (descriptive; no claim follows from them)

1. **Each tour and each season**: the primary's b and the effect sizes. Per-tour results are descriptive (MDE about 0.85 mLL).
2. **Fault-clean subset**: matches where neither player has a Tennis My Life men's Slam box-score row from August 2025 in his own history of the 104 weeks up to the match. 375 of the 8,520 are exposed.
3. **Polymarket**, every match with a price 24 hours before the listed start (2,648; and the 1,067 clean event openers):
   * F and B fed that price, against each other and against it;
   * the move of the price from 24 hours to 30 minutes regressed on the nudge's term b·x (OLS without intercept, four-week clusters).
4. **The bundle without members already scored on 2025–2026**: none of B-INJ's members was, so this equals the primary.
5. **Not run:** the no-odds bundle, and the red team's two suggestions (x on off-season returns against other returns; I-043 alone). Any of them run after the test is exploratory.
6. **The column deployment**, added after the screen and G5 and pre-registered before the test was opened. It answers the direct "features inside TabPFN" question.
   * The TabPFN arm `binj` (the 58 inputs plus B-INJ's three frozen columns, seeds 0–7) against B (seeds 0–7), each with the decided calibration.
   * The calibration histories use binj's 3-seed means in 2019–2024 against B's 16. The verifier found this immaterial (seed SD 0.008).
   * It was rejected as the deployment by the capture rule (slope 0.39). It is a descriptive gain of that arm and **never rescues a tied primary or confirms B-INJ**.

## What B-INJ measures (the red team, [red_team.md](meta/red_team.md): pass with caveats)

* **The claim's wording.**
  * The "longer than the field's norm" condition almost never binds. The walk-forward expected gap E is at most about 26 days, so it blocks 7 of 106,296 returns.
  * In effect, every break of six weeks or more counts, and off-season returns carry about 60% of the rust and 54% of x².
  * The tested claim is therefore **rust after a break of six weeks or more (mostly the off-season), decaying over the matches since the return**. It is not "hidden impairment" or "an unplanned layoff".
* **I-043's inputs**, the member that carries the block in 2014–2024 (exploratory decomposition, [round3/screen.md](round3/screen.md)):
  * the clock's days (the break and the matches since);
  * the walk-forward field table E (tour, week of the year, ranking band);
  * age, through the factor 1 + 0.05·(age − 28)+;
  * the status of the player's last match before the break (a retirement, or a walkover he gave);
  * a protected ranking (PR or SR).
* **I-044 dilutes the test.** It is a clipped spike (±9.7 SD) on 1.2% of rows. It carries about 17% of the test's leverage while null on its own, which costs about 0.03 mLL of power. It stays in, because B-INJ is tested as frozen.
* **The three readings of the specification the frozen builder implements**, matched by the red team's independent code to 8.6e-12 on all 55,144 rows of 2013–2024:
  * E's fallback runs tour × week × ranking band, then tour × week, then tour, with at least 60 rows per cell and no prior;
  * I-044's protected ranking counts both PR and SR;
  * I-045's match sequence is each match's position in the player's full history, gaps kept.
* **Robustness, 2014–2024.**
  * Without the 2020–2021 seasons the screen still passes: z₁ +2.90, z₂ +1.93, joint +3.48.
  * There is no leak at six cut days, and the column is not a proxy (R² 0.10–0.12 on the 58 inputs; correlation with the model's forecast −0.06; the top-10 players hold 7% of the rust).

## What is stale or shifts in the test years

* **I-045 reads first serves**, so it is exposed to the fault (secondary 2).
* **The walk-forward field table E** uses the three previous seasons, so 2025 reads 2022–2024.
* **I-043's 2026 coverage is 97.1%.** 101 rows lack it because a player's age is missing in the pre-rebuild Stage 0; missing values count as 0.

## Readings (critique §7), with the claim's limit

| Primary b | Effect size (F against B₁₄) | Reading |
|---|---|---|
| interval above 0 | interval above 0 | the bundle adds to the current best on 2025–2026, by the stated gain |
| interval above 0 | tie | adds information; its size uncertain (expected at this power) |
| spans 0 | any | not confirmed; gains below about 0.57 mLL remain possible, and the 2014–2024 evidence stands as stated |
| interval below 0 | any | harmful; do not adopt |

**The claim's limit.** A positive primary supports the rust reading only (a break of six weeks or more, mostly the off-season), never an injury or impairment signal.

## Process

* The red team's report and the final-test code's verification came before this hash. The meta-auditor's checkpoint 2 signed off on the run after its listed fixes, which this text and the code now carry.
* **`final_test.py --run` runs once**, with a ledger row, and its outputs are reported whatever they show.
* **The crash rule** (checkpoint 2 §3.5):
  * if `--run` stops before `final_primary.json` is written, nothing it printed beyond the error is read; the cause is fixed and verified on synthetic outcomes, a ledger row is added, and the run is repeated once;
  * if it stops after, the primary stands and only the failed secondaries are re-run, once.

## Hashes

POPULATION_SHA256: b76b595aeabfcab65677446780dc3f4ae25611859b9751d3dfefc2bb27f276c2
BINJ_X_SHA256: d64593c3a97b2b91b949622de7459ae7a2506a00d54ece0bc6e1b76e45d98e20
EARLY_SHA256: 22809fa7a9422a22f28953292cca0d5db894470f3218bc23d45d3cdce9729a5c
FORECASTS_SHA256: 05fe3b611929dc7cad7a7df345085734c1d784324e47e8f8e61bef7ae67d8a53
MODEL_FRAME_SHA256: 6113966fd8286cb41738eb7b52e0d6d9e2d7631c980c3aec7be6e4bbbaaab06b
STAGE0_MATCHES_SHA256: 271d2561f31d0c8cc407e5fb9b73d572115173e329e272c337f8daddda4662af
FINAL_TEST_CODE_SHA256: e32a3033ae4c7d66f6d257a439b21965b7f6cc24258826d6daf5549454bf3e49
