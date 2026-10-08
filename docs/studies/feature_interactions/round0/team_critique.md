# Configuration critique: the team, the gates, the screen and the final test

6 October 2026 · Configuration critic, round 0 · Research evidence, not a decision. Every amendment is a proposal. Before round 1 the orchestrator adopts or rejects each one in `plan.md` with a one-line reason; the meta-auditor checks that record at M1.

**Read in full:** [brief.md](../brief.md), [team.md](../team.md); for context the [surface IOS](../../surface_ios/README.md), [meta stack](../../meta_stack/README.md) and [TabPFN thinking](../../tabpfn_thinking/README.md) reports, and the [rating race](../../surface_rating_race/README.md) report for its Polymarket 2025–2026 sample. **Not read:** other agents' round-0 files (the folder was empty when this was written).

**Keys.** Gains are milli-log-loss (mLL) per match, paired: **positive = the named arm has the lower log loss (better)**; a 95% interval that spans 0 is a tie. Δ is a true gain averaged over the whole population, in mLL. **Power** is the chance a test detects a true Δ; **MDE** is the Δ detected with 80% power. **Observed** = computed here; **inferred** = reasoning; **proposal** = an amendment; **author claim** = what a cited paper says.

**What this critique read, for the look ledger.** Every computation ran through `./python.sh` as an inline script; nothing was saved except this file.

* No result (`a_won`) of 2022–2026 was read. For 2025–2026 only row counts and dates were read.
* Results of 2014–2021 were read once, to measure placebo design effects: real results against the 54-input predecessor's walk-forward forecasts, with **randomly generated features only** (no candidate, no real feature). One piece of knowledge came out of it: residuals against that forecast carry a small career-long player-level persistence (section 1.3). Log it; it bears on any "player-level mispricing" candidate.
* Everything else used forecasts without results, or simulated results.

## In short: the must-amendments

1. **Fit the current best for 2014–2018 before the screen.** Its walk-forward forecasts exist only for 2019–2026. Against it, discovery has 12,101 matches instead of 34,880, and the screen could find only effects of about 0.6 mLL, several times the largest seen given the close. The 2014–2018 forecasts on disk are the 54-input predecessor's, which differs from the current best by as much as a 0.2–0.3 mLL term would move it. Cost: about 30 local fits.
2. **Make the screen a coefficient test with one fixed specification.** It needs free calibration slopes per tour and season, an odd cubic in the forecast, and every interaction tested beyond its main effects. For a symmetric modulator s, the main effects include s × the forecast's log-odds. The out-of-sample log-loss difference needs four times the matches for the same power, so it becomes the reported effect size, not the gate.
3. **Replace "significant in discovery, then replicates" (G3 → G4) with one joint analysis of 2014–2024.** Use a lenient discovery filter, replication in the same direction, weighted Holm for claims and weighted BH for the bundle. At the same 5% family-wise error, power for a true 0.2 mLL effect rises from 0.62 to 0.90, and for 0.1 mLL from 0.20 to 0.53.
4. **Use player-level inference for player-level traits.** For a fixed per-player trait (height, hand, country) the true null variance is 1.23 times what four-week-block intervals report.
5. **Freeze before looking.**
   * No result is read before M1.
   * One primary hypothesis per candidate, hashed.
   * Construction constants are tuned on targets free of the price and of the current best.
   * A look ledger, and a register of features already scored on 2025–2026.
6. **Run integrity checks before any result is read.**
   * Swap and orientation tests for every new column. The match id lists the players in sorted order, which matches side A in only 50.3% of matches.
   * The id map after today's rebuild, and input hashes.
   * The leak probe.
   * A harness verified on planted effects by an agent who did not write it.
7. **G1 kills only for listed reasons; the auditor's judgement becomes p-value weights.** "The market prices it", "interactions explain 2%" and "TabPFN could form it" are not kill reasons.
8. **G5 checks deployment and harm; it is not a significance gate.** As written it passes a true 0.2 mLL effect about 22% of the time, after the effect has already survived G4.
9. **The final test is one bundle arm against base.** The primary endpoint is an encompassing test whose arm deviation comes from seeds disjoint from the base offset.
   * The planned paired interval detects a true 0.3 mLL gain 15% of the time. Its MDE is 1.6–2.1 mLL, more than the model's whole edge over the price.
   * The disjoint-seed encompassing test detects it 48–61% of the time (MDE about 0.43).
   * With shared seeds the same test rewards the averaging of fit noise: 9–20% false positives at a nominal 5%.
   * Freeze the match list and use 16 seeds per arm. If nothing passes G4, keep 2025–2026 closed.

## 1. The numbers behind the amendments (observed)

### 1.1 Sample sizes

The model population: `data/studies/surface_rating_race/model/model_frame.parquet`, the main tour with closing odds, debut seasons out. Four-week blocks are counted from the harness's origin (Monday 4 January 2010).

| Window | Role | Matches | Four-week blocks |
|---|---|---|---|
| 2013 | first training season; no out-of-sample forecast can exist | 5,024 | 13 |
| 2014–2021 | discovery screen (needs walk-forward forecasts) | **34,880** (men 16,717, women 18,163) | 92 |
| 2016–2021 | discovery with at least three training seasons behind each forecast | 24,747 | 67 |
| 2019–2021 | the only discovery seasons with the current best's forecasts today | 12,101 | 31 |
| 2022–2024 | replication | 15,207 | 36 |
| 2025–2026 | final test (counted, not opened) | 8,520 (men 4,394, women 4,126) | **21** |

* **The 58-input current best has walk-forward forecasts only for 2019–2026.** They are in `data/studies/surface_rating_race/local/model__<season>__seed<k>.npz`, seeds 0–2. The 2014–2018 forecasts on disk (`data/studies/meta_stack/walkforward.parquet`) are the 54-input predecessor's.
* **The final test has 21 clusters.** Its intervals use t with 20 degrees of freedom (critical value 2.09, not 1.96), and its cluster variance is itself noisy.

### 1.2 How big a realistic effect is, and how noisy TabPFN is (forecasts only, no results)

* **Size of a signal.** The mean of p(1 − p) is 0.198 for the current best (2019–2021) and 0.194 for the predecessor (2014–2021). A term worth Δ moves the forecast's log-odds with a standard deviation of √(2Δ / 0.198):
  * 0.1 mLL: 0.032; 0.2 mLL: 0.045; 0.3 mLL: 0.055; 0.5 mLL: 0.071.
  * So a 0.2 mLL term is about one percentage point of probability. For scale, TabPFN's whole adjustment to the price averages 1.7 points and is worth about 1.3 mLL.
* **Seed noise.** One seed's log-odds differ from the three-seed mean by 0.019 (root mean square; median 0.015). The noise term E[w·σ²] is 2.1 × 10⁻⁵ for a three-seed mean and 0.8 × 10⁻⁵ for an eight-seed mean.
* **Arm against arm, near-identical models.** Shown: the log-odds standard deviation, then the paired log-loss interval's implied null half-width on 23,819 / 8,520 matches.
  * Offset-Elo arm against the current best: 0.021; ±0.12 / ±0.21. This reproduces the brief's ±0.12.
  * Surface-profile arm (`sprof`) against the current best: 0.037; ±0.20 / ±0.36.
  * 54-input predecessor against the current best: **0.046**; ±0.25 / ±0.45.
* **Inferred.** The predecessor differs from the current best by as much as a 0.2–0.3 mLL term would move it. A screen against the predecessor in 2014–2018 would credit candidates with structure the current best already holds: the surface profile and the offset Elo.

### 1.3 Clustering: what four-week blocks miss (2014–2021 results, random features, 300 draws per row)

Fit y ~ σ(a_tour·η + b·x) with no intercept, where η is the predecessor's walk-forward log-odds and x is random. The spread of b̂ across draws is the true null spread. Each cell is a variance relative to the model-based variance; the sampling error is about ±0.10.

| Random feature | True null variance | Four-week-block estimate | Shared-player (dyadic) estimate |
|---|---|---|---|
| independent per match | 1.05 | 0.99 | 0.98 |
| **fixed per player**, u_A − u_B (like height, hand, country) | **1.23** | 0.98 | 1.06 |
| per player and season | 1.02 | 1.01 | 0.99 |
| per tournament, × η (a context modulation) | 1.07 | 0.94 | 0.93 |
| per four-week block, × η | 0.86 | 0.85 | 0.92 |

* **Inferred.** Results against the forecast carry a small career-long player effect: a player the forecast misjudges stays misjudged. A fixed trait inherits that effect. Four-week blocks do not see it, and the dyadic estimator sees only a third of it.
* At the Holm threshold for 40 hypotheses (z ≈ 3.0, one-sided), a null fixed trait therefore passes 2.6 times as often as intended. At 1.96 it passes 7.7% of the time instead of 5%.
* Re-measure against the current best once its 2014–2018 forecasts exist.

### 1.4 Power: which test, which window (computed; formulas checked by simulation)

Take a term whose true coefficient gives a population-averaged gain Δ (in nats), with n matches and a design effect DE.

* **Coefficient (score or Wald) test:** z ≈ √(2nΔ / DE).
* **Paired log-loss difference with the true coefficient** (the project's `compare`): z ≈ √(nΔ / (2·DE)). That is half the coefficient test's z, so it needs **four times the matches** for the same power. An estimated coefficient or TabPFN's fit noise lowers it further.
* **Check by simulation** (simulated results, discovery size, 300 draws):

  | True Δ | Coefficient test z (theory) | Power at 1.96 | Paired log-loss z (theory) | Power at 1.96 |
  |---|---|---|---|---|
  | 0.2 mLL | 3.85 (3.74) | 0.96 | 1.98 (1.87) | 0.49 |
  | 0.1 mLL | 2.72 (2.64) | 0.78 | 1.39 (1.32) | 0.26 |

**MDE in mLL** (80% power, DE = 1; multiply by 1.23 for fixed per-player traits):

| Window | Matches | Coefficient test, one test, two-sided 5% | Coefficient test, one of 40, one-sided Bonferroni | Paired log loss, one test, two-sided 5% |
|---|---|---|---|---|
| 2014–2021 | 34,880 | 0.11 | 0.21 | 0.45 |
| 2016–2021 | 24,747 | 0.16 | 0.30 | 0.63 |
| 2019–2021 | 12,101 | 0.32 | 0.62 | 1.30 |
| 2022–2024 | 15,207 | 0.26 | 0.49 | 1.03 |
| **2014–2024 joint** | 50,087 | **0.08** | **0.15** | 0.31 |
| 2025–2026 | 8,520 | 0.46 | 0.88 | 1.84 |
| 2022–2026 (option C2) | 23,727 | 0.17 | 0.32 | 0.66 |

**Inferred.** Earlier candidates mostly tied given the close, with |gain| < 0.15 mLL, so realistic interaction effects are 0.05–0.2 mLL. Only the coefficient test on the largest windows can see effects that small.

### 1.5 Two-stage designs under multiplicity (simulated: 40 hypotheses, 3 true, 37 null, 20,000 studies)

Power per true effect, at three true sizes:

| Design | Δ = 0.1 | Δ = 0.2 | Δ = 0.3 | Null candidates passed per study |
|---|---|---|---|---|
| As written (G3 then G4): BH q = 0.10 in 2014–2021, then Holm 5% in 2022–2024 | 0.20 | 0.62 | 0.86 | 0.005 |
| Bonferroni 5% in 2014–2021, then p < 0.05 in 2022–2024 | 0.15 | 0.55 | 0.83 | 0.001 |
| **Joint, Holm 5%**: filter z₁ > 1, replication z₂ > 0.67 | **0.53** | **0.90** | **0.99** | 0.045 |
| Joint, BH q = 0.10, same filter | 0.69 | 0.95 | 0.99 | 0.33 |

* **With 80 hypotheses:** joint Holm 0.88 at Δ = 0.2, against 0.58 as written.
* **Fixed per-player traits (DE 1.23):** joint Holm 0.82, against 0.47 as written.
* **Inferred.** The serial design spends its error rate twice: its family-wise error is 0.1–0.7%, a tenth of the intended 5%, and it loses about half of the real 0.2 mLL effects. The joint analysis holds the family-wise error at 5% and finds 90% of them.
* **Author claim.** Skol et al. (2006) reached the same conclusion for two-stage genetic studies: joint analysis is almost always more powerful than treating stage 2 as a replication.

### 1.6 The final test's power (simulated: 8,520 matches, 21 blocks, TabPFN-like fit noise, 400 draws)

Power at three true bundle gains:

| Test | Δ = 0.2 | Δ = 0.3 | Δ = 0.5 |
|---|---|---|---|
| Paired log loss, 95% interval excludes 0 (as planned) | 0.09 | 0.15 | 0.20 |
| Paired log loss, one-sided 5% | 0.15 | 0.25 | 0.34 |
| **Encompassing test, deviation from disjoint seeds, one-sided 5%** | **0.46** | **0.61** | **0.88** |
| The same, two-sided 5% | 0.33 | 0.48 | 0.77 |

* **MDE (80%).** The paired log loss needs 1.6 mLL (one-sided) to 2.1 mLL (two-sided, t with 20 df), more than the model's whole edge over the price (+1.30). The encompassing test needs about 0.43 one-sided, or 0.55 two-sided.
* **More seeds barely help power:** three and eight seeds agree to within 0.01. Under a real effect the variance comes from the signal itself, not from TabPFN's noise.
* **Per tour** (about 4,300 matches each), the encompassing MDE is about 0.85 mLL. Per-tour results in the final test can only be descriptive.

### 1.7 A bias in the naive encompassing test (simulated, the new columns carry nothing)

Regress the results on the base's log-odds and on the arm's deviation from it. When both come from the **same** fits, the regression rewards averaging two noisy forecasts. False-positive rate at a nominal one-sided 5%:

| Matches | Fit noise per arm, E[w·σ²] | Deviation from the same fits | Deviation from disjoint seeds |
|---|---|---|---|
| 8,520 | 2.1 × 10⁻⁵ (a three-seed mean) | 8.8% | 2.8% |
| 8,520 | 4.2 × 10⁻⁵ | 12.8% | 3.8% |
| 27,308 | 2.1 × 10⁻⁵ | 12.4% | 4.2% |
| 27,308 | 4.2 × 10⁻⁵ | 20.2% | 5.4% |

The disjoint-seed version keeps the power shown in 1.6.

## 2. Must amendments (proposal)

Each amendment gives the reason, then the exact change.

### M1. The current best's forecasts for 2014–2018

**Why** (1.1, 1.2, 1.4). Without them, the screen against the current best has 12,101 discovery matches, with an MDE of 0.62 mLL among 40 hypotheses. Substituting the predecessor's 2014–2018 forecasts tests against a model that differs from the current best by as much as the signal sought.

**Change.**
* Before M1, fit the 58-input model walk-forward for 2014–2018: train on 2013 to the season before, predict both orientations, symmetrise.
* Use seeds 0–5: 0–2 for the screen's offset, 3–5 for the disjoint-seed checks. That is 30 local fits of about 15 seconds each.
* Refit 2019 with seeds 0–2 to check that it reproduces the stored forecasts.
* The discovery window is 2014–2021 (34,880 matches). Restricting it to 2016–2021 is a pre-declared sensitivity, because the earliest windows train on one or two seasons.

### M2. The screen: a coefficient test with one fixed specification

**Why** (1.4). The out-of-sample log-loss difference needs four times the data. A screen with a fixed offset, no curvature term, or an interaction without its main effects finds "effects" that are calibration or context.

**Change** (the full specification is in section 6).
* **Model.** logit P(A wins) = Σ a_tour,season·η + Σ c_tour·η³ + controls + b·x. No intercept; one row per match, in its stored orientation; debut seasons out.
* **Gate on the z of b.** For a single pre-specified coefficient, the expected out-of-sample gain is Δ minus about 1/(2n) ≈ 0.014 mLL, so a real coefficient is a real gain (compare Clark and West 2007 on nested models).
* **Effect sizes, reported but never gating:**
  * the leave-one-season-out log-loss gain in 2014–2021;
  * the forward gain in 2022–2024, with b fitted on 2014–2021.
* **Two versions, both reported.** η is the current best's forecast (this version decides) or the de-vigged closing price (the owner's ranking lens). A candidate that passes against the current best but leans negative against the price is flagged "corrects the model, not the market". It stays eligible.

**Marginality: an interaction is tested beyond its main effects.** Every candidate is rewritten in one basis, a symmetric modulator × a difference, before the screen.

* **S (s × d):** control for d and for **s·η** (s·η_price in the price version). Without s·η, any s that changes how confident the forecast should be (round, level, both players' strength) loads onto s·d through d's correlation with η.
* **W (f(A) − f(B)):** control for the linear difference. x_A² − x_B² = (x_A − x_B)(x_A + x_B), so a quadratic W is an S-term with the sum as its modulator; deduplicate the two.
* **X (cross-player):** O_A·D_B − O_B·D_A = ½[(O_A − O_B)(D_A + D_B) − (O_A + O_B)(D_A − D_B)], so products are S-terms in the players' sums. Control for the differences, for each sum × η, and for the existing `prod_<s>`.
* **M (market state):** control for η, η³ and η·|η| per tour. Otherwise the term is calibration curvature, which the deployed slope partly handles already.
* **C and U:** control for the linear part of the composition, or for the unweighted difference.
* **Every candidate:**
  * the one to three existing inputs most correlated with it, chosen without results;
  * missingness: miss_A − miss_B, and the symmetric missing indicator × η.
* **Nothing left after the controls means a new main effect.** That is allowed, because the owner asked for features the model does not use yet. It is labelled and counted as a main effect.

### M3. One joint analysis of discovery and replication

**Why** (1.5). The serial gates find half the real 0.2 mLL effects at a tenth of the error budget.

**Change.**
* **G3 becomes a filter:** z₁ > 1.0 in the pre-declared direction on 2014–2021.
* **G4 tests the joint statistic** z_joint = (√n₁·z₁ + √n₂·z₂) / √(n₁ + n₂) on 2014–2024:
  * Claims about single features use weighted Holm: one-sided, 5% family-wise, over every hypothesis registered at M1. Those stopped by the filter count with p = 1.
  * Eligibility for the final bundle uses weighted BH at q = 0.10. A false component costs the bundle a few hundredths of a mLL of noise, not a false claim.
  * Both require replication in the same direction: z₂ > 0.67 (one-sided p < 0.25). Report the heterogeneity between the stages.
* **Why the filter is safe.** For a null hypothesis, P(passes the filter and the joint test) ≤ P(passes the joint test), so the filter cannot inflate the error.

### M4. Player-level inference for player-level traits

**Why** (1.3). The true null variance of a fixed per-player trait is 1.23 times the block estimate.

**Change.**
* **Fixed traits** (height, hand, country, birth cohort, career constants): the p-value comes from at least 1,000 permutations of the trait across players within each tour. That is the exact null for "this trait carries nothing".
* **Slow traits** (season-to-season correlation within a player ≥ 0.7, checked without results): multiply the variance by 1.25, or use a player-cluster wild bootstrap.
* **All others:** cluster by four-week blocks and shared players together.
* Use the most conservative of these. Re-measure the factor against the current best at M1, with random features only, as a ledger row.

### M5. Freeze before looking; keep a look ledger

**Why.** "Data settles disputes" invites quick checks during the rulings. Analysts will want to retune a half-life after seeing a result. And earlier studies have already scored likely candidates on 2025–2026.

**Change.**
* **No result is read before M1, by anyone.** Rounds 1–2 use only result-free checks: algebra, swap tests, coverage, correlations, the candidate's R² on the 58 inputs, and distributions.
* **At M1 each candidate is one row of a hypothesis table, hashed into `plan.md`.** The row records:
  * the formula and code path;
  * the construction constants;
  * the controls and the population;
  * pooled or tour-specific;
  * the sign (or "two-sided");
  * the weight;
  * the deployment form.

  Variants are pre-declared sensitivities. They cannot rescue a failed primary or enter the bundle.
* **Construction constants** (half-lives, shrinkage) are tuned only on targets that involve neither the price nor the current best: forecasting the statistic itself, or prediction without odds, on 2013–2018. The surface IOS study tuned this way.
* **The screen runs once,** as a scripted batch over the frozen table.
* **The meta-auditor keeps the ledger.** Every run that reads results is a row: time, script hash, candidates, seasons, statistic. This critique's look is the first row.
* **The cartographer's register** records the seasons on which each earlier feature was scored against the close.
  * Anything already scored on 2025–2026 may enter the bundle, but this study cannot confirm it there. The report says so. Examples: the men's serve speed, the surface-IOS forms, the Elo and TTT variants.
  * The brief's "2% interactions" and "context carries nothing" describe TabPFN's forecasts on 2022–2026 matches. That description uses no results, so it does not contaminate this study's test seasons.

### M6. Integrity before any result is read

**Why.**
* The project's largest past error was mechanical: 22 of 53 inputs leaked.
* One harness judges every candidate.
* **A trap observed here.** The match id lists the two players in sorted id order, which agrees with side A in only **50.3%** of the 63,737 matches. The frame's A is Stage 0's `player_a_id` (`a_won` agrees in 100%). A feature oriented from the match id would have a random sign, which destroys its signal and produces a false negative.

**Change.**
* **Unit tests for every new column.** A − B columns change sign when A and B swap; symmetric columns do not.
* **Orientation and joins.**
  * Side A is Stage 0's `player_a_id`, taken from the pre-rebuild copy that is consistent with the frame.
  * New tables are joined through `data/studies/data_continuity/rebuilds/2026-10-07T0005Z/id_map.csv`.
  * An inputs manifest records the SHA-256 of every table read, as `surface_rating_race/inputs_manifest.json` does.
* **Cross-player features pass `probe.py`** before any result is read.
* **Columns derived from a model fitted on results** (any learned "bias" or residual feature) are computed only from matches that surely finished before the start, including for TabPFN's training rows.
* **A harness verifier** (a new agent, not the harness's author) signs off before M1 closes:
  * **planted effects:** simulated results y ~ Bernoulli(σ(η_cal + β·x)) on real candidate columns at Δ = 0.1, 0.2 and 0.3 mLL; detection must match section 1.4 to within ±10 points;
  * **β = 0:** false positives at most nominal;
  * **the placebo families of section 6.**

### M7. G1 kills only for listed reasons; judgement becomes weights

**Why.**
* The costliest error is killing the one real idea. The cheapest is carrying an extra null: going from 40 to 80 hypotheses costs 2 points of power under the joint design (0.90 → 0.88).
* The tempting arguments are not evidence here.
  * "The market surely prices this" is what the screen tests, and the owner's premise rejects it as a conclusion.
  * The 2% interaction share describes what TabPFN learned from its own 54 inputs. It says nothing about terms TabPFN cannot form.
  * "TabPFN could form it" is testable: if TabPFN has, the screen against the current best finds nothing.

**Change.**
* **Hard kills only:**
  * (a) wrong swap behaviour that no reformulation fixes;
  * (b) algebraic identity with an existing input, up to sign, scale or a monotone transform;
  * (c) infeasibility or leak risk confirmed by G2;
  * (d) no stated mechanism;
  * (e) a family already tied at the close in two or more independent designs with no new mechanism (cite the study).
* **Everything else passes with a weight:** 0.5 (doubtful or contested), 1, or 2 (strong mechanism and adequate power), normalised to mean 1. The weights feed weighted Holm and BH (Genovese, Roeder and Wasserman 2006).

### M8. G5 checks deployment and harm

**Why.**
* On 2019–2024 (27,308 matches), a TabPFN arm's paired interval excludes 0 for a true 0.2 mLL effect about 22% of the time (0.3 mLL: 37%). As written, G5 would discard most real effects that survived G4, after the expensive work is done.
* G5's real questions are whether TabPFN uses the column and whether the column harms it.

**Change.** Each bundle-eligible candidate gets one TabPFN arm: base plus its columns, walk-forward 2016–2024 (or 2019–2024), seeds 0–2. Pre-registered rules:
* **Harm.** Drop the column if its paired gain over base is below −0.10 mLL (point estimate).
* **Capture** (no results needed). Regress the arm's deviation from base on the screen's term b̂·x.
  * Slope ≥ 0.5: deploy the candidate as a TabPFN column.
  * Slope < 0.5: TabPFN is not using it, so deploy it through the nudge layer (S1).
* **Cap.** At most six candidates and eight new columns; ties are broken by joint z.
* No candidate is dropped for a non-significant TabPFN gain.

### M9. The final test

**Why** (1.6, 1.7). The planned interval reads "tie" whatever the truth, for any plausible effect. The obvious repair (an encompassing test with shared seeds) is biased.

**Change.** The skeleton is in section 7.
* **Freeze the population at M2.** Hash the 2025–2026 match list (today 8,520 after the debut exclusion). Matches that arrive later go to C1.
* **Arms.** Base B and one bundle arm F, deployed by M8's rules. Sixteen seeds each (0–15), both orientations, recalibrated per tour as decided. Base is refitted with the same seeds.
* **Primary endpoint.** The encompassing test with a disjoint-seed deviation:

  logit P(A wins) = a_tour·η_B[0–7] + c_tour·η_B[0–7]³ + b·(η_F[8–15] − η_B[8–15])

  * The hypothesis is b > 0, one-sided at 5%, with four-week clusters and t on 20 degrees of freedom.
  * The owner chooses before opening between one-sided 5% (MDE 0.43) and the project's two-sided 95% convention (MDE 0.55).
* **Effect size.** F's paired log-loss gain over B across all 16 seeds, with a 95% interval (a tie if it spans 0). It is reported, not used as the decision.
* **The pre-registration states:**
  * the MDEs;
  * the expected gain, from shrunk pre-2025 estimates (S9);
  * that a tied gain is the likely reading even if the bundle is real.
* **If no candidate passes G4, 2025–2026 stays closed** for a later study.

## 3. Should amendments (proposal)

### Deployment and the TabPFN side

* **S1. A nudge layer.**
  * **What.** The screened terms enter as walk-forward logistic nudges on the current best: logit = (the decided slope per tour)·η_B + Σ b_k·x_k. Each b_k is fitted, pooled over tours unless pre-declared otherwise, on B's own out-of-sample forecasts from 2014 to the season before (the meta-stack design).
  * **Cost.** About k / (2n) ≈ 0.01 mLL per term, with n ≈ 35,000–50,000.
  * **Why.** It deploys exactly what the screen measured, it is immune to TabPFN ignoring a weak column, and it is the natural home for market-state and context-slope terms. It is required by M8 whenever capture fails.
* **S2. An omnibus "levels" TabPFN arm, pre-registered as one hypothesis.**
  * **What.** Add 17 symmetric columns as context: the players' sums A + B of the 7 surface-IOS offence and 7 defence values, Elo overall, age, and sets in 14 days. Test it on 2016–2024 with the disjoint-seed encompassing test (power about 0.95 at 0.2 mLL on 39,954 matches).
  * **Why.** It tests the brief's central structural claim (differences hide levels) with TabPFN's own flexibility. It also covers the reverse failure, where TabPFN can use what a linear screen misses: in the TabPFN-thinking study, linear fits on the same inputs found +0.09 to +0.79 against TabPFN's +1.57.
  * **Cost.** About 80 fits.
* **S3. A finalist red team at M2** (a fresh agent).
  * It re-implements each finalist from its written specification; values must match to 1e-9, or the difference must be explained.
  * It tries to break each finalist: leaks; orientation; a proxy for the disagreement between price and model, or for player identity; the rebuilt Stage 0; coverage artefacts.
  * It reports before the final pre-registration is hashed.

### Process

* **S4. The auditors read `literature.md` in round 1,** as priors and for redundancy, never as a sole reason to kill. Additions from the literature in round 2 are capped at 10.
* **S5. Against anchoring.**
  * The master list merges ideas only when they are algebraically identical in the modulator × difference basis. Every idea keeps its provenance and original wording.
  * Brainstormers may contest a merge of their own ideas.
  * The auditors also receive the four raw lists.
  * An idea proposed by several lenses gains no prior: the lenses share the brief, so they are not independent.
  * Each brainstormer adds at least two ideas in round 2 that contradict a claim of the brief.
* **S6. Additions to the idea template:**
  * a quantitative prior: Δ in mLL, sign, where, and coverage share;
  * the main-effect decomposition (M2);
  * the novel variance (R² on the 58 inputs, without results);
  * the deployment form: a TabPFN difference column, a context column, or a nudge;
  * whether its 2025–2026 performance has been seen.

### Statistics

* **S7. Pool the tours by default,** with tour-specific nuisance slopes.
  * A tour-specific test (two degrees of freedom) only where the mechanism is tour-specific and was pre-declared.
  * If the effect is real in one tour only, the pooled test loses a factor of √2 in z. If it is real in both, the pooled test gains √2.
  * Per-tour final results are descriptive (MDE about 0.85 mLL).
* **S8. Candidates limited to a subgroup must be large inside it.** The required effect inside the subgroup is the population MDE divided by the subgroup's share.
  * Grass (11.1% of discovery matches): at least 1.3 mLL inside grass matches with the joint analysis, 1.9 with discovery alone.
  * Best of five (9.8%): at least 1.5 and 2.2 respectively.
  * Merge such candidates into broader forms, or drop them.
* **S9. Shrink the estimates of selected candidates.**
  * **Method.** Tweedie's formula over the family's joint z values (Efron 2011), or the conditional estimate given selection.
  * **Why.** At the Holm threshold, a passing true 0.1 mLL effect is read about 50% too high on average, and a 0.2 mLL effect about 7% too high.
  * The final test's expectation uses the shrunk values.
* **S10. Placebo families** (section 6), beyond M6's synthetic controls:
  * shuffles within strata;
  * permutation of player labels;
  * a known-null set.
* **S11. One missingness rule for both models.**
  * TabPFN takes NaN.
  * The linear screen sets a missing difference to 0 and adds the missingness controls of M2.
  * Both use the same rows.

### Logistics

* **S12. A GPU budget.** About 30 fits for M1, about 80 for S2, up to 180 for G5 and about 100 for the final test: roughly 400 local fits, or 3–4 hours on the shared RTX 5090. Schedule them with the other sessions.

## 4. Could amendments (proposal)

* **C1. A prospective extension.** Pre-register the same primary endpoint on matches after the freeze, with alpha spending (for example O'Brien–Fleming), looking at about 15,000 cumulative matches around the end of 2027. These are the cleanest data the project will ever have. The MDE falls to about 0.25 mLL.
* **C2. The owner's option: make 2022–2026 the confirmation set and select on 2014–2021 only.**
  * The MDE falls from 0.43 to about 0.15 (encompassing).
  * The cost is the replication stage, and 2022–2024 has been seen by earlier studies for other features.
  * Not recommended unless the owner prefers it, since the brief names 2025–2026 as the test.
* **C3. A hybrid arm:** TabPFN with the columns, plus the walk-forward nudge for the same terms, fitted on that arm's own out-of-sample forecasts. It corrects itself: the nudge shrinks to zero where TabPFN captured the term. No choice of deployment is then needed.
* **C4. A move test on Polymarket as the betting secondary.**
  * **What.** Regress logit P(30 min) − logit P(24 h) on the bundle's deviation from base without odds, with cluster-robust intervals, as in the rating race's H4.
  * **Why.** It uses price moves rather than results, so it can be more powerful. Its power depends on the spread of that deviation, which is unknown until the bundle exists.
* **C5. A move test in discovery,** from opening to closing prices, if the tennis-data files carry opening odds before 2025. Check availability. It would test "information the early price lacks" on 2014–2024 without spending the final test.
* **C6. Formula-first auditing.** The mathematical auditor rules on the formula, type and data before reading the mechanism, to blunt persuasive narratives. Any brainstormer may also rebut any kill (one rebuttal per kill), not only kills of its own ideas.
* **C7. Two missing lenses,** assigned to the existing brainstormers in round 2:
  * information timing: withdrawals, late finishes, schedule news, entry status;
  * measurement reliability: box-score quality, retirements, walkovers, dead rubbers.

## 5. The gates, rewritten (proposal)

**G1, mechanism.** Round 1, the mathematical auditor; algebra only, no data.
* **Pass rule.** Pass unless one of M7's hard kills (a)–(e) applies. Set the weight to 0.5, 1 or 2, and record the expected Δ and sign.
* **Never a kill reason:** "priced in"; "interactions explain 2%"; "TabPFN could form it".

**G2, feasibility, timing and power.** Round 1, the feasibility auditor; coverage counts and result-free correlations.
* **Coverage.** Defined for both players on at least 50% of the 2014–2021 matches and at least 50% of the 2022–2024 matches, per tour claimed. Countable for 2025–2026.
* **Timing.** A timing class is assigned. Cross-player features pass the probe.
* **Novelty.** R² on the 58 inputs below 0.95.
* **Integrity.** The swap and orientation tests pass.
* **Power.** Population-averaged expected Δ at least 0.09 mLL (the joint 50%-power point among 40 hypotheses). Otherwise the candidate joins a block or is deferred.
* **Never a kill reason:** a small expected Δ alone, if the candidate can join a block.

**G3, discovery filter.** Round 3, the harness; 2014–2021, 34,880 matches.
* **Pass rule.** z₁ > 1.0 in the declared direction (|z₁| > 1 if two-sided), with M4's variance and placebo calibration.
* **Never a kill reason:** a non-significant z₁.

**G4, joint analysis.** Round 3, the harness; 2014–2024, 50,087 matches.
* **Pass rule.** z_joint passes weighted Holm (claims; one-sided 5% family-wise) or weighted BH at q = 0.10 (bundle), and z₂ > 0.67.

**G5, deployment and harm.** M2, the orchestrator; TabPFN arms on 2016 (or 2019) to 2024.
* **Pass rule.** The column is kept unless its gain is below −0.10 mLL. A capture slope of at least 0.5 means a column; otherwise a nudge. At most six candidates and eight columns.
* **Never a kill reason:** a non-significant TabPFN gain.

**G6, final test.** Round 5; 2025–2026, 8,520 matches.
* **Pass rule.** The disjoint-seed encompassing test, one-sided 5% (or two-sided, as the owner chooses before opening).

## 6. The screen's specification (proposal, for the harness)

1. **Rows.** The model population of 2014–2021 (discovery) and 2022–2024 (replication). Debut seasons out. One row per match, in its stored orientation.
2. **Offset.** η is the current best's walk-forward log-odds: the 58 inputs, seeds 0–2, symmetrised, raw. The free slopes do the calibration.
3. **Model.** logit P(A wins) = Σ_{tour,season} a·η + Σ_tour c·η³ + Σ_j γ_j·control_j + b·x. No intercept: side A is random, so the true intercept is zero. The 22 nuisance slopes cost nothing at this size.
4. **Controls.** M2's marginality set for the candidate's type, plus its one to three nearest existing inputs, plus missingness.
5. **Preprocessing,** all fixed without results on the discovery rows:
   * the candidate is standardised;
   * modulators are centred before products are formed;
   * values are winsorised at 0.5% and 99.5%.
6. **Statistic.** The z of b, with standard errors clustered by four-week blocks and shared players together (dyadic: Aronow, Samii and Assenova 2015). Fixed traits use M4's permutation p-value instead. Use the more conservative.
7. **Joint statistic and gates** as in M3. One-sided in the declared direction; two-sided hypotheses carry a weight of 0.5 if their sign was not declared.
8. **The price version** is identical, with η the de-vigged closing log-odds. Reported and ranked; it does not gate.
9. **Effect sizes:**
   * the leave-one-season-out gain in 2014–2021;
   * the forward gain in 2022–2024 (b fitted on 2014–2021);
   * both with four-week-block intervals and the direction key.
10. **Placebos, each run through the whole pipeline:**
    * **P1. Shuffles within strata.** Shuffle each candidate within tour × season × surface × η-decile, 200 times. If the empirical null spread of z exceeds 1.10, widen the candidate's standard error by that factor (Efron's empirical null).
    * **P2. Player-label permutation** for fixed and slow traits (M4).
    * **P3. A known-null set.** At least five features from earlier studies that tied at the close in more than one design and are not among the 58 inputs: for example the TTT offset difference, the surface study's deviation columns (R2) and its net-shift column (P1). If more than one passes G4, the screen is miscalibrated: stop and investigate.
    * **P4. Synthetic planted effects and β = 0** (M6).
11. **Ledger.** One batch run per frozen table, logged. Exploratory variants after the batch are labelled as such and cannot enter the bundle.

## 7. The final test's pre-registration skeleton (proposal; fixed at M2, hashed, run once)

**Setup**

| Item | Content |
|---|---|
| Population | the frozen 2025–2026 match list (main tour with closing odds, debut seasons out); hash and count recorded |
| Arms | B, the current best; F, B plus the bundle as deployed by G5 (columns and/or nudges); 16 seeds each; recalibrated per tour, walk-forward from 2019, as decided |
| Primary | the disjoint-seed encompassing test of b > 0 (M9); sidedness fixed before opening |
| Effect size | F's paired log-loss gain over B, 95% four-week-block interval, t with 20 df; positive = F better |
| Stated in advance | the MDEs (0.43 one-sided, 0.55 two-sided); the expected gain (the shrunk sum of the components × capture) and the power at it; per tour about 0.85 |

**Secondary endpoints** (descriptive; no claims)
* each tour; each season;
* F_noodds against B_noodds (eight seeds each);
* the subset with a Polymarket price 24 hours before the start (about 2,600 matches): F against B, and each against that price. The encompassing MDE there is about 1.3 mLL, and the price comparison's half-width about ±4 mLL;
* C4's move test;
* each finalist alone (base plus one, eight seeds).

**Readings**

| Primary test | Paired gain | Reading |
|---|---|---|
| significant | interval above 0 | adds to the current best on untouched seasons, by the stated gain |
| significant | tie | adds information; the size is uncertain (expected at this power) |
| not significant | any | not confirmed; gains below about 0.43–0.55 mLL remain possible, and the pre-2025 evidence stands as stated |
| b < 0 (two-sided check) | worse | harmful; do not adopt |

**If nothing passed G4:** do not open 2025–2026.

## 8. Roles, order and the back-and-forth (proposal)

**Roles.**
* **Add a harness verifier at M1 (M6) and a finalist red team at M2 (S3).** Both are fresh agents. The orchestrator wrote the brief and the harness, and the meta-auditor watches process, not code.
* No role is redundant. The critic is one-shot by design.
* The mathematical auditor also owns each candidate's power entry: its MDE at its coverage.

**Order.**

| Step | What happens | Results read? |
|---|---|---|
| 0 → 1 | the orchestrator records adopt or reject for every amendment here in `plan.md` | no |
| 1 | merge by algebra (S5); both auditors, with the literature (S4); in parallel, M1's 2014–2018 fits and the harness build | no |
| 2 | one rebuttal each; rulings; literature additions (at most 10); the hypothesis table | no |
| M1 | freeze and hash; harness verification on synthetic results; the design effect re-measured against the current best with random features (a ledger row) | design only |
| 3 | the screen batch: filter, joint test, placebos, effect sizes | yes, once |
| M2 | G5 arms; red team; bundle; the final pre-registration, hashed | 2016–2024 |
| 5 | the final test | 2025–2026, once |
| M3 | the claims checked against the evidence | — |

**What is exchanged.** Rows, not prose.
* **Mathematical auditor**, one row per idea:
  * ID; type in the modulator × difference basis;
  * swap check; redundancy (algebra, and R² on the 58 inputs);
  * an effect bound, with a two-line derivation; the MDE at its coverage;
  * draft controls;
  * verdict: pass with weight, refine with the exact fix, or kill with the hard reason.
* **Feasibility auditor**, one row per idea:
  * ID; tables and columns;
  * coverage by tour in 2014–2021, 2022–2024 and 2025–2026 (counts only);
  * timing class; whether the probe is needed; build cost; verdict.
* **Rebuttal:** at most 150 words per contested verdict. It must contain either a result-free computation (with the number) or algebra showing the reason wrong, or a reformulation that removes it. No new idea, except as a fix.
* **Ruling:** accept, reject, or "contested". A contested idea enters the screen at weight 0.5. Rulings are final.

**How disputes end.**
* Factual disputes that need no results: the orchestrator computes and posts the answer.
* Disputes about value: the screen decides, at weight 0.5.
* Disputes about leaks: the probe decides; failing that, the stricter construction wins.
* Disputes about process: the meta-auditor decides.

**When to stop.**
* One rebuttal round only.
* The table is frozen at M1. Ideas arriving after M1 go to a "next study" list and never enter this study's 2025–2026 test.
* The screen runs once. G5 ends with the bundle. The final test runs once.

## 9. Failure modes and where each is handled

| Failure mode | Where it would bite | Handled by |
|---|---|---|
| Groupthink and anchoring | one brief, one taxonomy, one merger | S5, C7, the M7 weights |
| Auditor too harsh | G1 | M7 |
| Auditor too lenient; variants multiply | G1–G2 | M5 (one hypothesis each), the G2 power rule |
| Main effects dressed as interactions | the screen | M2 marginality, the "new main effect" label |
| Leaks: cross-player features, the clock, derived columns | feature builds | M6, the probe, out-of-fold derived columns |
| Forking paths | constants, variants, retuning | M5 |
| Multiple testing | dozens of candidates | M3, M7 weights |
| Selection bias; 2022–2024 reused | G4, G5, report | M3 (valid under selection), M8 (no significance gate), S9 (shrinkage), M9 (untouched test) |
| The screen mis-specified | calibration, context, curvature | M2, M1 |
| The screen underpowered | discovery size | M1, M2, M3 |
| TabPFN ignores what the screen finds | G5, final | M8 capture rule, S1 nudge layer |
| TabPFN finds what the screen misses | G3 | S2 omnibus arm |
| Clustering understated | fixed per-player traits | M4 |
| Orientation errors | joins | M6 |
| The final test underpowered | round 5 | M9 (encompassing test), C1, C2 |

## Appendix: how the numbers were computed (observed)

* **Counts.** The model frame, debut seasons out; four-week blocks are `(date − 2010-01-04) // 28` days, the harness's `blocks`.
* **Noise.** Arms `model`, `sprof`, `elo_off` and `base` of `surface_rating_race/local/`, seasons 2019–2021, seeds 0–2. Each arm is symmetrised; w comes from the current best's seed mean. No results were used.
* **Design effects.**
  * Inputs: `meta_stack/walkforward.parquet` (`p_base`, 2014–2021), joined to the frame and to player ids from the pre-rebuild Stage 0 copy.
  * Model: y ~ a_men·η + a_women·η + b·x, no intercept.
  * Spread: 300 random draws per feature type. Standard errors were averaged over the first 60 draws; ratios are taken to the model-based variance.
* **Power.**
  * Simulated results y ~ Bernoulli(σ(η + β·x)) on the 2014–2021 predecessor log-odds, with β set to give Δ; 300–400 draws.
  * The final-test simulations used 8,520 sampled rows in 21 contiguous blocks, with Gaussian fit noise at the measured E[w·σ²].
  * The multiplicity designs used a normal model of z₁ and z₂ with means √(2nΔ), over 20,000 studies.

## Sources (methods; accessed 6 October 2026)

* Skol, Scott, Abecasis, Boehnke (2006). Joint analysis is more efficient than replication-based analysis for two-stage genome-wide association studies. *Nature Genetics* 38:209–213. <https://www.nature.com/articles/ng1706>
* Genovese, Roeder, Wasserman (2006). False discovery control with p-value weighting. *Biometrika* 93(3):509–524. <https://doi.org/10.1093/biomet/93.3.509>
* Benjamini, Bogomolov (2014). Selective inference on multiple families of hypotheses. *JRSS B* 76(1):297–318. <https://doi.org/10.1111/rssb.12028>. For a family-level version of M3, if the orchestrator groups hypotheses by mechanism.
* Aronow, Samii, Assenova (2015). Cluster-robust variance estimation for dyadic data. *Political Analysis*. <https://doi.org/10.1093/pan/mpv018>
* Harvey, Leybourne, Newbold (1998). Tests for forecast encompassing. *Journal of Business & Economic Statistics* 16(2):254–259. <https://ideas.repec.org/a/bes/jnlbes/v16y1998i2p254-59.html>
* Clark, McCracken (2001). Tests of equal forecast accuracy and encompassing for nested models. *Journal of Econometrics* 105(1):85–110. Working paper: <https://www.kansascityfed.org/documents/5407/pdf-RWP01-14.pdf>
* Clark, West (2007). Approximately normal tests for equal predictive accuracy in nested models. *Journal of Econometrics* 138(1):291–311. <https://www.nber.org/papers/t0326>
* Efron (2011). Tweedie's formula and selection bias. *JASA* 106(496):1602–1614. <https://doi.org/10.1198/jasa.2011.tm11181>
