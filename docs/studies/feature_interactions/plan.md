# Feature interactions: the plan, and what was adopted from the critique

6 October 2026. Written before round 1 and before any candidate was related to a result. It records the orchestrator's decision on every amendment of the [configuration critique](round0/team_critique.md) and fixes the procedure from here. The hypothesis table and the final test's pre-registration are added at M1 and M2, each hashed.

## Decisions on the critique's amendments

| Amendment | Decision | Reason or modification |
|---|---|---|
| M1 fit the current best for 2014–2018 | **adopted, done** | Arm `model` fitted walk-forward for 2014–2019, seeds 0–2 (`data/studies/feature_interactions/local/`). The 2019 fits equal the rating race's exactly (max difference in probability 0). Seeds 3–5 are added only where a disjoint-seed check needs them |
| M2 a coefficient test with one fixed specification | **adopted** | The screen becomes the critique's section 6: free slopes per tour × season, an odd cubic per tour, the type's marginality controls, z of b as the statistic; out-of-sample gains reported, never gating |
| M3 one joint analysis of 2014–2024 | **adopted** | Filter z₁ > 1 on 2014–2021; z_joint on 2014–2024; weighted Holm (claims, one-sided 5%) and weighted BH q = 0.10 (bundle eligibility); replication in the same direction z₂ > 0.67. **Added:** a variant refined after the screen is tested on 2022–2024 alone, with Holm over the refined variants, and cannot use the joint statistic |
| M4 player-level inference for player traits | **adopted** | Fixed traits: permutation of traits across players within tour (≥ 1,000); slow traits: variance × 1.25; others: four-week blocks and shared players together (dyadic). The most conservative is used |
| M5 freeze before looking; look ledger | **adopted** | The ledger is `meta/look_ledger.md`, kept by the meta-auditor. The orchestrator's harness checks of this afternoon read 2014–2024 results with existing inputs only (no candidate) and are its first rows |
| M6 integrity before results | **adopted** | Side A is Stage 0's `player_a_id` from the pre-rebuild copy; never the order in the match id. Swap tests for every column; input hashes; the probe for cross-player features; a fresh harness verifier at M1 |
| M7 G1 kills only for listed reasons | **adopted** | Hard kills (a)–(e) only; otherwise weights 0.5 / 1 / 2 |
| M8 G5 checks deployment and harm | **adopted** | Harm below −0.10 mLL drops a column; capture slope ≥ 0.5 deploys it as a TabPFN column, else as a nudge; at most six candidates and eight columns |
| M9 one bundle arm; disjoint-seed encompassing test | **adopted, with the sidedness fixed now** | The owner is not asked mid-study (his standing instruction is to build and score in-session). The primary reading is the **two-sided 95% interval on b** (the project's convention, MDE about 0.55 mLL); the one-sided p is reported beside it. Sixteen seeds per arm; the match list frozen and hashed at M2 |
| S1 nudge layer | adopted | the deployment for terms TabPFN does not capture |
| S2 omnibus "levels" arm | adopted | one pre-registered hypothesis: the players' sums as context columns |
| S3 finalist red team | adopted | a fresh agent at M2 |
| S4 auditors read the literature in round 1 | adopted | as priors, never as a sole kill reason |
| S5 against anchoring | adopted | merges only for algebraic identity; provenance kept; two contrarian ideas per brainstormer in round 2 |
| S6 template additions | adopted | for the hypothesis table's rows |
| S7 pool the tours by default | adopted | |
| S8 subgroup candidates must be large | adopted | |
| S9 shrink selected estimates | adopted | Tweedie's formula over the family's joint z |
| S10 placebo families | adopted | P1 shuffles within strata (empirical-null widening), P2 player-label permutation, P3 known-null set, P4 synthetic |
| S11 one missingness rule | adopted | |
| S12 GPU budget | noted | about 400 local fits, scheduled around other sessions |
| C1 prospective extension | recommended to the owner | not part of this study |
| C2 2022–2026 as the confirmation set | **rejected** | the owner named 2025–2026 as the test |
| C3 hybrid arm | deferred to M2 | if capture is mixed |
| C4 Polymarket move test | adopted as a secondary endpoint | |
| C5 move test in discovery | adopted if opening odds exist before 2025 | the cartographer checks |
| C6 formula-first auditing; anyone may rebut a kill | adopted | |
| C7 two missing lenses | adopted | information timing; measurement reliability, assigned in round 2 |

## H-S2, the omnibus "levels" arm (fixed 6 Oct 2026, before any result of it exists)

* **Columns** (17, kind context: unchanged when A and B swap), built by `src/eda/feature_interactions/features/levels.py` from the player panel: the two players' sums A + B of the 7 surface-IOS offence ratings (`srf_O_eff_<s>`) and the 7 defence ratings (`srf_D_eff_<s>`) for ace, df, first_in, first_won, second_won, hold, bp_saved; overall Elo (R_A + R_B); age; sets in the last 14 days.
* **Arm** `levels`: the 58 inputs plus the 17 columns. Local TabPFN-3.5, walk-forward 2016–2024 (trained on 2013 to the season before), seeds 0–5; the base arm `model` refitted with seeds 3–5 on the same seasons.
* **Test, after M1** (the critique's S2 and M9 form): the disjoint-seed encompassing regression on 2016–2024, logit P = Σ a_tour,season·η_B[0–2] + Σ c_tour·η_B[0–2]³ + b·(η_levels[3–5] − η_B[3–5]), b > 0, four-week blocks and shared players; the paired log-loss gain reported as the effect size. One hypothesis in the family, weight 1.
* The forecasts may be computed before M1; nobody scores them until the hypothesis table is frozen.

## Orchestrator decisions during the builds (6 Oct 2026, before M1, no result read)

* **The harness verifier's fixes are all applied** ([harness_verification.md](meta/harness_verification.md), B1–B14): the crash on a season without one tour; adaptive permutations for fixed traits (1,000, then a fresh 20,000 when p ≤ 0.01); the history's round order within an event; the freeze covering every column, the trait columns and every builder file, and refusing to run after a swap failure; the Wald path's smallest-W covariance with an F(k, G − k) reference; the known-null set through the same pipeline; permutations among observed players only; no result column given to builders; and the low-severity rest.
* **Wald blocks with a fixed-trait member** (B3: height; B-HOME: country) are screened with the slow-trait widening, covariance × 1.25, instead of a permutation. Reason: the verifier measured the fixed-trait design effect against the current best at 1.11, already covered by the screen's own variance (ratio 0.96), so × 1.25 is conservative.
* **Pre-declared result-free gates are binding as declared.** Split-half gates use the raw correlation (not Spearman–Brown, which would be a choice made after the values were seen). B4 is dropped: I-019 and I-021 failed their persistence gates, and I-018 failed MEC-10's out-of-sample serve-point condition on both tours.

## Fixed at M1, before the screen reads any result (7 Oct 2026; the meta-auditor's checkpoint 1, X-1 and F-7)

**After the screen: from the family to the bundle (M2).** No choice below is left for after the screen.

1. **Eligibility.** A member is bundle-eligible when its weighted BH q-value is below 0.10, computed on p_eff (its joint p when it passes the filter and replicates, else 1) over all 34 members, H-S2 included. Claims about single members use weighted Holm at a one-sided 5%.
2. **Ranking and cap.** Eligible members are ranked by p_joint / weight (ascending; ties by the larger z_joint), and at most six enter.
   * At most eight TabPFN columns in all, counting every deployment column of a multi-column member. A member whose columns would break the cap is deployed as a nudge instead.
   * H-S2 counts as one member, and its 17 context columns are exempt from the column cap.
3. **Deployment route by the family's deployment form.**
   * Rows whose form is "nudge" go straight to the nudge layer.
   * Rows whose form names TabPFN columns (including "columns or nudge") get one G5 arm.
4. **The G5 arm.** The 58 inputs plus the member's frozen `tabpfn` columns. Local TabPFN-3.5 with the usual settings, walk-forward 2016–2024 (each season trained on 2013 to the season before), seeds 0–2, both orientations.
5. **Harm.** The arm's paired log-loss gain over the base (seeds 0–2 each), both tours pooled, on 2020–2024, each forecast calibrated by the decided walk-forward slope per tour (fitted on every earlier out-of-sample season from 2019). If the point estimate is below −0.10 mLL, the member is deployed as a nudge instead of a column.
6. **Capture.**
   * The slope is the OLS slope, without an intercept, of (η_arm − η_base) on the screen's fitted term b̂·x. It uses raw log-odds, seed-0–2 means and 2016–2024.
   * b̂ comes from one pooled fit on 2014–2024 with the screen's specification (slopes per tour × season, the cubic, the row's controls), on the model base. For a Wald row it is the coefficient vector.
   * A slope of at least 0.5 deploys the member as TabPFN columns. A lower slope deploys it as a nudge.
7. **The bundle arm F.**
   * F is TabPFN with the 58 inputs plus every column-deployed member's columns (and H-S2's 17 if eligible), seeds 0–15, walk-forward 2016–2026.
   * A nudge layer is added on top: logit P_F = s_tour·η_A + Σ_k b_k·x_k.
     * η_A is that arm's raw log-odds, or the base's when no column is deployed.
     * s_tour is one slope per tour; each b_k is pooled over tours.
     * There is no intercept and no cubic.
     * x_k is the member's screen column as built: standardised by its 2014–2021 SD, with its η forms evaluated at η_A.
   * The nudge layer is fitted by maximum likelihood, walk-forward on the arm's out-of-sample forecasts of every season from 2016 (from 2014 when the arm is the base) to the season before. It replaces the decided calibration for F; the base keeps the decided calibration.
8. **C3**, the hybrid arm, is dropped.
9. **Empty outcomes.**
   * No member eligible: 2025–2026 stays closed and the study reports the screen.
   * Every eligible member fails harm: they all go to the nudge layer.
   * Only H-S2 eligible: the bundle is the levels arm.
10. **Shrinkage (S9).** Tweedie's formula, ẑ = z + d/dz log f(z), with f a Gaussian-kernel density (Silverman's bandwidth) over the 34 model-base z_joint values.
    * Each member's expected gain is 1000·max(ẑ, 0)²/(2·50,087) mLL, times its capture slope (1 for nudges).
    * The pre-registration states the sum and the power at it.

**The final test (round 5).** The meta-auditor's checkpoint 1, §6.3, lists what the final pre-registration must contain; it is written at M2 and hashed before any 2025–2026 result is read. The primary reading stays the two-sided 95% interval on the disjoint-seed encompassing coefficient b.

**The known-null alarm (P3).** If more than one of the six known nulls passes the family's Bonferroni line (p_eff < 0.05/34), the family's claims and bundle eligibility are suspended and checkpoint 2 investigates.
* A recalibrated re-run is exploratory: no claim, no bundle and no opening of 2025–2026 follows from it.
* The one exception is a code error fixed without reference to any family result: the corrected batch then runs once more, with a ledger row.
* The six known nulls' z_joint and KN-SDEV's W/k are reported in any case.

**The batch's frozen scope (F-6).**
* Run once inside the batch, as descriptive outputs that never gate: every module's `SENSITIVITIES` (I-008's four variants, INFO-1's column, B11's per-member decomposition), and the sharp-anchor diagnostic C-1 (Pinnacle's de-vigged log-odds minus the average's, beyond η; η's gain over the calibrated Pinnacle and the calibrated average on the same matches).
* Never run: MAT-K2's s̃·η. Anything run after the batch is an exploratory, logged look that cannot change a claim or the bundle.

**Hashes.** `prepare.json` records the table, every builder file and every input file the build reads (the inputs manifest), including the forecast files already on disk for 2014–2026 (the 2025–2026 base forecasts, seeds 0–15, exist and have never been scored). The screen refuses to run if any of them changed.

## M2: what the rules gave (7 Oct 2026; [round3/screen.md](round3/screen.md))

* **Eligible:** B-INJ alone (weighted BH q 0.002; also a claim, weighted Holm p 0.002). The known-null alarm did not fire (0 of 6).
* **B-INJ's family deployment form** is TabPFN columns, so it received a G5 arm (`binj`: the 58 inputs plus its three frozen columns, 2016–2024, seeds 0–2). The 2026 build reproduced every frozen 2013–2024 column exactly.
* **Harm:** +0.044 [−0.157, +0.245] mLL, calibrated, 2020–2024 (positive = the arm better; a tie). Not harmful.
* **Capture:** slope 0.393 below the 0.5 line (b̂ 0.0421 per SD from the pooled 2014–2024 fit, z 3.94). **B-INJ is deployed as a nudge** (`data/studies/feature_interactions/g5/binj_g5.json`).
* **The bundle:** F = the base B plus the nudge layer logit P_F = s_tour·η_B + b·x_BINJ (rule 7), fitted walk-forward on B's out-of-sample forecasts from 2014 to the season before. No new TabPFN fit is needed.

## The rounds from here

| Step | What happens | Results read? |
|---|---|---|
| 1 | a synthesizer merges the four lists by algebra (S5) into `master_list.md`; the mathematical and feasibility auditors rule (G1, G2), with the literature; the orchestrator rebuilds the screen to the M2 specification | no |
| 2 | one rebuttal per contested verdict (any brainstormer, any kill), rulings, at most ten literature additions, two contrarian ideas and the two missing lenses; analysts build the surviving features and their result-free diagnostics (coverage, swap tests, R² on the 58 inputs) | no |
| M1 | the hypothesis table is frozen and hashed here; a fresh agent verifies the screen on planted effects; the design effect is re-measured against the current best with random features (a ledger row); the meta-auditor's checkpoint 1 | design only |
| 3 | the screen runs once, as a batch, with its placebos | 2014–2024, once |
| M2 | G5 TabPFN arms (2016–2024), the S2 levels arm, the red team, the bundle, the final pre-registration hashed; the meta-auditor's checkpoint 2 | 2016–2024 |
| 5 | the final test | 2025–2026, once |
| M3 | the meta-auditor's checkpoint 3; the report | – |

## M1: the freeze (7 Oct 2026)

The hypothesis table is frozen after checkpoint 1's fixes ([m1_fixes.md](meta/m1_fixes.md)): 33 screen rows plus H-S2, the six known nulls, 0 swap failures, 32 tests passing. The screen (`screen_batch.py --screen`) refuses to run unless all three hashes below match; it runs once.

FROZEN_TABLE_SHA256: aa8f8f618ca3a243f7485619f855d8aca555418e0372a1099cee61c0767a86a5
FROZEN_MODULES_SHA256: 7fd465467c10c2c646f867c2c3c941cfe0dd8b49fac1c69c2c1d3ab1747ac31c
FROZEN_INPUTS_SHA256: b783f7908e6494484b24699c546af164d4af457fb5472203a0718f92a4cd9eb6
