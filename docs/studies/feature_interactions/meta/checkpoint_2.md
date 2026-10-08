# Checkpoint 2 (M2): the screen as run, M2's rules, and the pre-registration

7 October 2026 · Meta-auditor · Research evidence, not a decision. This audits the process, before 2025–2026 is opened. My rulings on process disputes are final (team.md). I keep the [look ledger](look_ledger.md).

**Read:**
* plan.md ("Fixed at M1", "M2: what the rules gave", "M1: the freeze"), `m1_fixes.md`, `round3/screen.md`;
* the screen's outputs (`screen_results.csv`, `known_null_results.csv`, `descriptive_results.csv`, `exploratory_binj_members.csv`, `screen_run.log`);
* `g5/binj_g5.json`, `g5_build.py`, `g5_score.py`;
* `red_team.md`, `final_test_verification.md`, `preregistration.md`, `final/check.json`, `final/shrinkage.json`;
* `final_test.py`, `tabpfn_tests.py`.

**Ran** (ledger row 30). I read no 2025–2026 result.
* The screen's multiplicity, recomputed from its outputs.
* Every frozen input file and every hash line of the pre-registration, re-hashed. The population hash was computed from the model frame's ids, without its result column.
* One base-only look at 2014–2024 (§3.1).
* An attempt to reproduce the shrinkage (§2).

**The version audited:** `preregistration.md` SHA-256 `316e3251f60bae2bd47a02c63652767049970e120b60f057a28dd1b249096141`.

## Verdict: run after the listed fixes

* **The screen.** It ran once and as frozen. Its gates and multiplicity are exactly what plan.md fixed: my independent weighted Holm and BH agree to 4e-15. The known-null rule was applied as written (0 of 6).
* **M2.** It applied the rules fixed at M1 without discretion: eligibility, the G5 harm and capture lines, the nudge decision.
* **The primary endpoint is sound and insulated.** It is the disjoint-seed encompassing test, read by its two-sided 95% interval. Every hash line matches the files on disk, and all 387 frozen inputs are unchanged.
* **No 2025–2026 result has been read, and nothing found stops the run.**
* **Five things must be fixed first.** All are mechanical and need no 2025–2026 data:
  * the registered effect size mixes B-INJ with a change of calibration window, which in 2020–2024 was as large as the expected gain (§3.1);
  * the run does not check the hashes of some of its inputs: two external code files, the model frame and the pre-rebuild Stage 0 matches file;
  * the pre-registration's own text has no recorded hash;
  * a few statements are inaccurate;
  * the stated expected gain cannot be reproduced.

### Required before the run

| # | Change |
|---|---|
| R-A | **Decompose the effect size** (§3.1).<br>• Add arm **B₁₄**: logit P = s′_tour·η_B. s′ is fitted exactly like F's nudge (maximum likelihood, no intercept, one slope per tour, walk-forward on seasons 2014 to Y − 1, the same seed means), without x.<br>• Report three gains: F vs B (the registered deployment gain), F vs B₁₄ (**the part due to B-INJ**) and B₁₄ vs B (the calibration-window part). Per-match log-loss differences add exactly, so the first equals the sum of the other two.<br>• The readings table's effect-size column reads F vs B₁₄.<br>• The final-test verifier checks the new arm on synthetic outcomes (gain* ≈ 0 for F vs B₁₄ at β = 0) |
| R-B | **Hash every input of the run, and check the hashes before any result is loaded.**<br>• Add to the code hash `src/eda/tabpfn_thinking/common.py` (now `2911e7b615eced59…`) and `src/eda/surface_elo_pieces/early_price_score.py` (now `a68902aa872faaaa…`). Both are imported: `T.blocks`, `T.compare`, `T.ll`, `T.symmetrize` and `T.fit_logistic` feed the primary, the calibration and the effect size. Both sit untracked in other studies' folders.<br>• Add the model frame and the pre-rebuild Stage 0 matches file, which `tabpfn_tests.frame`, `screen.load` (inside `x_scaled`) and `tml_exposed` read. Both equal the frozen manifest today.<br>• `run()` compares every file hash before `population()` loads the results |
| R-C | **Freeze the text itself.** Once the amendments are made:<br>• record `preregistration.md`'s SHA-256 in a ledger row;<br>• have `--run` write it into `final_primary.json`;<br>• the report cites it |
| R-D | **Text corrections** in the pre-registration:<br>• the Tennis My Life departure, stated accurately (§3.2);<br>• the claim's limit in the readings (§3.3);<br>• I-043's inputs;<br>• the red team's two suggested secondaries declared "not run; anything later is exploratory";<br>• the note that a near relative was already scored on 2025–2026 (§3.3);<br>• "gains below about 0.57 mLL";<br>• a crash rule (§3.5);<br>• `shrinkage.json`'s power fields (0.25, 0.50) declared superseded by the verifier's (19%, 0.57) |
| R-E | **The expected gain must be reproducible** (§2). Save the script that wrote `final/shrinkage.json`, state how the five Wald rows enter rule 10 and which Silverman formula sets the bandwidth, recompute, and restate the expected gain and the power at it |

**Then:** run `--check`, re-hash, record the final hashes and the fixes (an `m2_fixes.md`, as at M1) and add a ledger row. Run `--run` once. No further checkpoint is needed unless a fix touches the primary.

**Before the report** (not the run):
* `round3/screen.md`'s reading of B-INJ still says "longer than the field's norm"; the red team showed that condition blocks 7 of 106,296 returns. Reword it as in §3.3.
* The exploratory signals keep their labels (§1): I-084 and I-036 against their declared direction, KN-TTTLOGIT, B11's On, C-1.

## 1. The screen as run against plan.md (observed)

**Once, as frozen.**
* `--screen` refuses to run on any table, builder or input hash mismatch. It ran once, from 08:09, about 39 minutes (`screen_run.log`, ledger row 22).
* The 387 files of the frozen inputs manifest still match today.
* Since the freeze, `arms.py`, `g5_build.py`, `g5_score.py`, `final_test.py` and `tabpfn_tests.py` were changed or added, all between 08:51 and 09:35. The screen's outputs were written at 08:46–08:48, so none of these can touch them.
* `tabpfn_tests.encompassing`'s one-tour fix skips the cubic column of an absent tour, so the pooled screen's H-S2 is unchanged.

**Gates and multiplicity (recomputed independently from `screen_results.csv`).**

| Step | As plan.md fixed it | As run |
|---|---|---|
| widening | P1's null SD when above 1.10; × √1.25 for slow traits (now B7, B9a and H-S2 too); × 1.25 covariance for the Wald rows with a trait | P1 never above 1.10 (0.87–0.99). Every slow row and H-S2 at 1.118; B3, B-HOME, B-LEVER and B-SWITCH at 1.25. B-INJ (trait none) at 1.0 |
| filter, replication | z₁ > 1 and z₂ > 0.67, oriented by the declared sign; Wald p₁ < 0.3173 and the scalar contrast > 0.67 | correct for every row, the "−" rows included (B-MOTIV fails replication, B-REPUTE the filter, I-053 replication) |
| weighted Holm, BH | p_eff over 34 members, weights normalised to mean 1 (raw sum 24.0) | identical to brute-force step-down and step-up rules (largest difference 4e-15) |
| result | | **B-INJ alone.** p 3.4e-5 at a normalised weight of 0.71 gives Holm 0.0016 and BH 0.0016. Next is B-VENUE: q 0.148, above 0.10 |

**P3, the known nulls.**
* The rule as written gives 0 of 6 (p_eff below 0.05/34 = 0.00147).
* KN-TTTLOGIT has a two-sided p of 0.011. One of six at that level has about a 6.6% chance under the global null, so it is unremarkable. Its gloss in `screen.md` ("the model over-weights the rating it already holds") is an inference.

**Scope.**
* The descriptive outputs are exactly F-6's frozen set: I-008's four sensitivities, B11's three members, INFO-1 and C-1.
* The two looks after the batch (rows 23 and 28) are labelled exploratory and changed nothing.

**What the report may not present as findings.**
* I-084 (joint z −2.99) and I-036 (−1.65) point against their declared direction, which a one-sided test cannot claim. They are hypotheses for a later study.
* B11's On (+3.29) is a descriptive main effect. It is not a family member and not a claim.
* C-1 is descriptive.
* None of these may appear in the report's findings beside B-INJ.

## 2. M2 against the rules fixed at M1

| Rule (plan.md "Fixed at M1") | Applied | Finding |
|---|---|---|
| 1, eligibility (BH q < 0.10) and claims (Holm) | B-INJ only | correct |
| 2, ranking and cap | one member, three columns | not binding |
| 3, route by the family's form | "TabPFN diff columns", so one G5 arm | correct |
| 4, the G5 arm | 58 inputs plus the three frozen columns, 2016–2024, seeds 0–2, both orientations | as specified. The 2026 build reproduces the frozen 2013–2024 column and all three deployment columns exactly (`g5_build` checks) |
| 5, harm | calibrated paired gain, 2020–2024: +0.044 [−0.157, +0.245] mLL (positive = the arm better; a tie) | not below −0.10, so not harmful. `g5_score` computes it as the rule says |
| 6, capture | slope 0.393 of the arm's deviation on b̂·x, b̂ = 0.042 per SD from one pooled 2014–2024 fit (z 3.94), raw log-odds, seed means, 2016–2024 | below 0.5, so **B-INJ is a nudge**. The code is the rule |
| 7, the bundle | F = B plus the nudge s_tour·η_B + b·x, fitted walk-forward from 2014 | as specified. Its effect size has a flaw I did not see at M1 (§3.1) |
| 8, C3 | dropped | – |
| 10, Tweedie shrinkage | ẑ 3.41, expected 0.12 mLL | **not reproducible** (below) |

**Nothing was chosen after looking.** The one addition after G5 is the column-arm secondary, ruled on in §3.4.

**The shrinkage (R-E).**
* No script in the repository writes `final/shrinkage.json` (ledger row 29).
* Rule 10 speaks of the 34 members' z_joint, but the five Wald rows have none.
* At the file's own bandwidth (0.523), every z set I tried gives ẑ ≈ 3.85, not 3.41: the 29 single-coefficient rows oriented by their sign, or 34 with the Wald rows mapped from their p.
* The two common "Silverman" formulas give different results:
  * 0.9·min(SD, IQR/1.34)·n^−1/5 gives a bandwidth of 0.42–0.53 and ẑ 3.84–3.97;
  * 1.06·SD·n^−1/5 gives 0.68–0.76 and ẑ 3.22–3.42. The stated 3.41 is close to this form on 34 values, but not at the stated bandwidth.
* The expected gain therefore lies between 0.10 and 0.16 mLL. By the verifier's fitted power curve, the power at it lies between 17% and 26%.
* This changes no decision. It is a pre-registered statement, so it must be reproducible.

## 3. The pre-registration against checkpoint 1 §6.3

| §6.3 item | In the pre-registration | Finding |
|---|---|---|
| 1 population | 8,520 matches, sorted-id SHA-256, the frozen pre-rebuild version; later matches excluded | complete. The hash matches |
| 2 Tennis My Life | not repaired; fault-clean subset | **a departure, accepted below, but stated inaccurately** (§3.2) |
| 3 arms | B and F; seeds 0–15; B's decided calibration; the 2026 build reproduces 2013–2024 | complete |
| 4 primary | per tour × season slopes on η_B[0–7], per-tour cubic, dev from seeds 8–15, largest of three variances, t on 20 df, the two-sided 95% interval read, one-sided p beside it | complete, and as coded |
| 5 effect size, expectations | F vs B deployed; power 16% / 34% / 72–76% at 0.1 / 0.2 / 0.5 mLL, MDE 0.57, 19% at the expected gain; "a tie is the likely reading" | the effect size is confounded (§3.1). The expected gain is not reproducible (§2) |
| 6 secondaries | per tour and season; fault-clean; Polymarket and the move test; the bundle without already-scored members (equals the primary); no-odds not run; the column arm (added) | complete. With one finalist, "each finalist alone" is the bundle. The column arm is ruled on in §3.4 |
| 7 stale columns | I-045's fault exposure, E's three-season window, 2026 coverage of I-043 | complete, except I-043's inputs, misstated (§3.3) |
| 8 red team before the hash | yes (09:45, hash 09:46) | complete |
| 9 the code verified and hashed | yes; bug 1 and the power fixed | two imported modules are not hashed (R-B) |
| 10 readings and claim limits | critique §7's table | add the claim's limit (§3.3) and "about 0.57" |

### 3.1 The effect size carries a calibration-window term (R-A)

**What the code compares.**
* For each test season, logit P_F − logit P_B = (s_tour − cal_tour)·η_B + b·x.
* F's slope s is fitted from 2014; B's calibration from 2019 (rule 7: the nudge "replaces the decided calibration for F; the base keeps" it).

**The primary is insulated.**
* Its per tour × season slopes on η_B[0–7] absorb (s − cal)·η_B exactly, apart from (s − cal)·(η_B[8–15] − η_B[0–7]).
* That remainder is about 0.0005 logit (the verifier's SD of 0.008 for the seed difference, times a slope gap of at most 0.06), against b·x's SD of about 0.04.

**The effect size is not insulated.** Ledger row 30 measured the term on 2020–2024, base only, with `final_test`'s own functions:

| Slopes | 2019 window (B's calibration) | 2014 window (F's nudge, without x) |
|---|---|---|
| men | 0.887–0.906 | 0.892–0.897 |
| women | 0.930–0.970 | 0.893–0.908 |

* The window alone moves the paired log loss by −0.30 to +0.37 mLL in single seasons. Pooled over 2020–2024 it is +0.03 [−0.14, +0.20], a tie (positive = the 2014-window slope better).
* For two test seasons, the term can be as large as the expected B-INJ gain (0.10–0.16 mLL).
* The verifier saw only +0.006 because its synthetic slopes were constant. The real women's slopes drift.
* As registered, a positive or negative "F vs B" could therefore be calibration rather than B-INJ.

**Ruling.**
* B₁₄ is added before the hash (R-A), and the size attributed to B-INJ is F vs B₁₄.
* F vs B stays as the deployment gain, since it is what switching to F would deliver.
* This corrects a confound found by audit. No 2025–2026 value informed it, and the 2014–2024 look that sized it involves no candidate.

### 3.2 The Tennis My Life departure: accepted, restated

**Accepted.**
* Repairing means rebuilding shared pipelines that belong to other studies (the IOS, the surface profile, the two-week form) and refitting the base's 16 seeds. The base would then no longer be the frozen B.
* The fault reaches B and F alike, except through I-045. That member is a tie on its own (joint z +1.56, exploratory), and its exposure is men only, on 375 of 8,520 matches (4.4%).
* Serve-points-won inputs are unaffected.
* The fault-clean subset checks the rest.

**The text must say this accurately (R-D).** It cites checkpoint 1 §6.3 as allowing the departure, but §6.3 item 2 assumed a repair, and "says which set is used" referred to the forecast set after a repair. The text should state that:
1. it departs from R2-measure point 1 and from §6.3 item 2, accepted at checkpoint 2 for the reasons above;
2. the 476 rows that the official feeds replaced in the live tables are **not** used, and the 97 Roland Garros 2026 qualifying rows stay;
3. the fault-clean subset departs from point 2's "share under 20%" rule by excluding any exposure, which is stricter. It also counts the player's own event, the match itself included, which is conservative;
4. no λ-attenuation is applied (point 4).

### 3.3 The claim's wording against the red team

**What matches.** The pre-registration's "What B-INJ measures" follows the red team:
* the name: rust after a break of six weeks or more, mostly the off-season, fading over the matches since the return;
* not "hidden impairment" or "an unplanned layoff";
* the three readings of the frozen builder and the 8.6e-12 reproduction;
* I-044's dilution;
* the result without 2020–2021;
* the data version and the 101 missing ages.

**Still to fix (R-D):**
1. **The readings table must carry the claim's limit.** A positive primary supports the rust reading only, not an injury signal (red team §4.2).
2. **I-043's inputs are misstated.** "Reads only the clock's days, ranks and entries" omits age (the factor 1 + 0.05(age − 28)+; its 101 missing 2026 rows are missing ages). It also omits the status of the player's last match before the break: a retirement, or a walkover he gave.
3. **The red team's two suggested secondaries were not adopted:** x on off-season against other returns, and I-043 alone. Say so, and say that either, if run after the test, is exploratory.
4. **The seasons are not naive to the family.**
   * The predictive frontier's "recovery context" group (rest, absence × Elo, retirement losses) was scored against the close from 2019, 2025–2026 included, and tied (inventory register; the math audit's I-044 card).
   * B-INJ's members are new constructions, so secondary 4 rightly equals the primary. But the report must not call 2025–2026 untouched by layoff-type features.
5. **Before the report, not the run:** `round3/screen.md`'s "Reading (inferred)" must drop "longer than the field's norm". Because the field norm does not bind, it must also not describe B-INJ as an "unplanned" layoff.

### 3.4 The column-arm secondary, added after the screen: accepted as descriptive

**Accepted**, for three reasons:
* it was decided, fitted and hashed (`FORECASTS_SHA256`) before any 2025–2026 result was read;
* it cannot change the primary, the bundle or the claim;
* it answers the owner's direct question (the feature inside TabPFN).

**Its origin is a forking path, and four conditions close it:**
1. **Order.** The report presents it after the primary and the effect sizes, labelled "added after the screen and G5; pre-registered before the test was opened".
2. **No rescue.** It never rescues a tied primary. A column-arm gain is reported as a descriptive gain of that TabPFN arm, never as confirmation of B-INJ.
3. **The asymmetry is stated.** Its calibration histories use binj's 3-seed means in 2019–2024 against B's 16. The verifier found this immaterial (seed SD 0.008).
4. **Per-tour results are descriptive.**

### 3.5 The once-only run

**What is in place.**
* The primary is written to disk before any secondary, and a failing secondary cannot lose it.
* The run refuses on a missing result, a changed population, x file, early frame, forecasts or code (the files hashed so far).
* Every walk-forward fit for season Y uses seasons < Y. The 2026 nudge and calibration read 2025's results, as walk-forward requires.

**What is missing.**
1. **The remaining inputs and the text's own hash** (R-B, R-C).
2. **A crash rule** (R-D):
   * if `--run` stops before `final_primary.json` is written, nothing it printed beyond the error is read; the cause is fixed and verified on synthetic outcomes, a ledger row is added, and the run is repeated once;
   * if it stops after, the primary stands, and only the failed secondaries are re-run, once.
3. **Low:** in `--check` mode, drop `a_won` after `tabpfn_tests.frame` (ledger row 29(b)).

## 4. The ledger

* **Complete through row 28.** The agents' rows 27 (the verifier, synthetic only) and 28 (the red team's one look at 2014–2024) are numbered in time order, so no renumbering is needed.
* **Added** (with their times):
  * row 29: disclosures not in rows 24–28. These are the 2025–2026 features and counts that were read, the 2025–2026 `a_won` held in memory unused by `--check` and the 2026 panel, the red team's result-free price correlations, and the unsaved shrinkage computation;
  * row 30: this checkpoint, including its base-only look at 2014–2024.
* **Still to come:** a row for the fixes with the final pre-registration's SHA-256 (R-C), and the run's own row.

## 5. Anything that should stop the run

**Nothing found invalidates the primary.**
* **No leak.** The red team's six cut probes and own-match reversals, the 2026 build's exact reproduction of 2013–2024, and the walk-forward fits all say so.
* **Frozen.** The population, forecasts, x and code are frozen and match.
* **Valid and conservative.** The primary is a valid, conservative test (size 2.35% at a nominal 5%). Its power at the expected gain is low: about 19% as stated, 17–26% pending R-E. A tie is the likely reading, and the pre-registration says so.

**The run waits only for R-A to R-E.** Run it once after they are recorded.

## 6. Not checked here

* I did not re-run the verifier's synthetic suite, re-implement the nudge, or audit the `binj` TabPFN fits beyond their logs and hashes.
* I did not check how the Polymarket early-price frame was built; its hash is fixed.
* The shrinkage was reconstructed only from the screen's z values.
