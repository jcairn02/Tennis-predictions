# Round 2 rulings · mathematical auditor

6 October 2026 · Research evidence, not a decision. Rule (critique §8, adopted): one rebuttal per contested verdict, ruled **ACCEPT**, **REJECT** or **CONTESTED** (a contested idea enters the screen at weight 0.5); rulings are final. New ideas get pass / refine / kill, with kills only for reasons (a)–(e). The frozen result is [hypothesis_family.md](hypothesis_family.md).

**Read:** the four rebuttals, their outputs in `data/studies/feature_interactions/round2/` (mechanics `checks`, `part_c`, `part_g`, `part_g2`, `part_h`; mathematics `day_noise_precheck`, `novelty_r2`, `measurement_checks`; market `i042`; feasibility `r2_checks`), the analysts' builders in `src/eda/feature_interactions/features/` and [builders.md](../builders.md). No result was read for these rulings.

## Rebuttals

| # | Rebuttal | Ruling | Reason (citing the rebuttal's computation) |
|---|---|---|---|
| MEC-R1 | I-008: test the remainder after a result-free projection | ACCEPT | Projected per tour on 2013–2018 without outcomes, the remainder keeps SD 0.205 (men) and 0.089 (women) in 2019–2021 (part A), 7 and 3 times the ≈ 0.03 a 0.09 mLL term needs; the form now applies to the new primary z_spw (MAT-R4) |
| MEC-R2a | I-012: g declared, novelty R² 0.922 / 0.929 | ACCEPT | MEC-04's formula leaves no free constant, and the declared column is under 0.95 (part A) |
| MEC-R2b | I-012: the precheck must be the joint fit | CONTESTED | The joint fit is the theory-consistent gate: the link O·D is predicted at γ = −0.24, observed −0.27 ± 0.14, and correlates 0.70 with the shield, which then sits at +0.053 ± 0.044 against a predicted +0.050 (part G2). But the form was chosen after both were computed, z is only 1.2 (men; women uninformative), and the analysts' gate finds p_struct forecasting serve points worse than additive IOS (−0.23 milli per point, men; `f03_composition`). So I-012 re-enters B2, B2 drops to weight 0.5, τ_spw = O·D becomes a B2 control, and the precheck counts as no evidence at M2 (a ledger row) |
| MAT-R1a | I-042: no Δh control | ACCEPT | τ = −Δh(1 + cosh z) − Σh·sinh z is one structural column whose leading term is the Δh part; with Δh free only 32% (men) and 24% (women) of its value remains (N14). Primary τ with the M-set and Std; the Δh-free shape test is a secondary |
| MAT-R1b | I-042: replace the estimator by a moment-K beta-binomial rate | REJECT | The builder already fixed estimator (a), k = 160, by the round-1 rule: out-of-sample log loss on the 2013–2018 retirement label, a price-free target (`i042.json`, `f11_retirement`). (a) is itself a beta-binomial posterior mean; moment-K becomes a sensitivity. Its precheck gives a de-noised persistent hazard SD of 1.03 pp (main tour) and 1.56 pp (all levels), so the fixed rule keeps weight 2 |
| MAT-R2 | I-007's substitute measures the price, not the truth | ACCEPT | The two-level noise split implies a true Bo5/Bo3 ratio of 1.197 (N1–N6), inside the close's 1.19–1.27, so I-006's mispricing is expected ≈ 0.01 mLL; I-007 is retired (no post-M1 row) |
| MAT-R3 | I-001: weight 0.5 in B-LEVER | ACCEPT | A leverage change is damped to 0.39 (Bo3, N7) of the iid's, and the close applies 43% (men) of it (mechanics part B; η 36%, part C). So the price ≈ the damped truth and I-001 expects ≈ 0, before the 22% decline of specialization (N11). B-LEVER = {I-001, I-006's format slope, κ_surf·η}, Wald 3 df |
| MAT-R4 | I-008's primary: z_spw, not z_C1 | ACCEPT | The three components forecast next-match serve points worse than the serve-point IOS (−0.07 and −0.14 milli per point, 2018–2021, blend fixed on 2013–2017: N12). That is a statistic target M5 allows. z_spw leaves residual SD 0.25 / 0.21 on the 58 (N15) and is immune to first/second-serve recording faults; z_C1 becomes a sensitivity |
| MAT-R5 | B5's precheck: drop I-029 | ACCEPT | By the round-1 rule: pair CV 0.20 / 0.24 with split-half reliability 0.23 / 0.33, or 0.19 / 0.18 with 0.15 / 0.16 in first differences (N8–N9). I-029 and its sensitivity I-030 drop, B5 dissolves, and I-028 moves to B6, kept only if its own reliability gate (≥ 0.3) passes before M1 |
| MAT-R6 | Findings 1–3 hold; I-010's V; lift R²-only deferrals | ACCEPT | I-010's sensitivity takes V = 0.154 / 0.183 (N3), since serve and return days co-move (N4). The R²-only deferrals of I-008, I-009 and I-012 are lifted by the Frisch–Waugh-equivalent remainder form; I-015 stays a decomposition |
| MKT-R1 | Withdraw I-081 | ACCEPT | With adj for N the column is adj·tanh²(z/2), W-16's form (< 0.01 mLL); a null member costs the composite √(2/3) of its z |
| MKT-R2 | Withdraw I-087 | ACCEPT | w ≤ 1 day in 62% of matches and 93% from the round of 16 on (corr 0.48 with round), so the modulator is round depth; with adj it is κ²-bounded (≤ 0.03). INFO-2 carries the timing claim |
| MKT-R3 | Withdraw I-034 | ACCEPT | For two unbiased Gaussian views the posterior variance does not depend on their disagreement, so abs(Δ1) has no derived sign |
| MKT-R4 | I-085: F without a fit; primary abs(r)·sign F | ACCEPT | F = c·(Elo inputs), c fixed by SD-matching on 2014–2018, needs no outcomes (coverage 100%). r·1[sign r ≠ sign F] = ½r − ½·abs(r)·sign F exactly (checked), so with r controlled the identifiable column is abs(r)·sign F, sign + |
| MKT-R5 | I-086: apply S11 | ACCEPT | In the QF+ rows that carry the column, both previous prices exist in 99.6–99.9% (`r2_checks`); zero plus missingness controls is the adopted rule |
| BOD-R1 | I-051's Off is not a sensitivity of I-052 | ACCEPT | ΔOff's novel variance (46%) is 2.4 times ΔFat's (19%), and neither explains the other (R² 0.543 → 0.546): my round-1 premise was wrong. I-052 becomes B-LOAD {ΔFat, ΔOff}, sign − |
| BOD-R2 | I-060: the continent map is built | ACCEPT | The ITF ids' IOC codes plus the 81-code map leave 1.8% of rows unmapped and map 79–82% of matches fully; S11 covers the rest |
| BOD-R3 | I-074: continent-level offsets | ACCEPT | A ≥ 5-hour trigger is decided by continent changes; the proxy covers 93–95% of first-match rows and the trigger fires on 1.3% / 0.8% of rows: a B10 member |
| BOD-R4 | I-075: novelty from the parts on disk | ACCEPT | Surface switch, indoor switch (Court field) and continent change are on disk (13.5% / 11.9% and 20.5% / 20.9% of rows) |

**Noted, not rebuttals.**
* I-020's originator agrees with the kill.
* B4's target is men-only in substance (N10). It stays pooled at 0.5.
* The analysts' result-free gate dropped I-068 (the return residual does not drift after 29: +0.0011 ± 0.0008, men; `f07_evidence_age`), and I-069 goes with it. B-AGE is I-070 alone, at weight 0.5.

## New ideas

| ID | Ruling | Weight | Reason and fix |
|---|---|---|---|
| MEC-L1 serve–return link | refine | – | No slot: R² 0.987 / 0.961 on the 58, remainder ≈ 0.013 match log-odds (part H). Its column τ_spw = O·D is a B2 control, and a link-corrected composition is a sensitivity of I-008. Its gate holds (γ̂ −0.27 ± 0.14) |
| MEC-K1 information-weighted Elo | kill (e) | – | Results-based rating variants tied at the close in ≥ 2 independent designs (inventory §3.1: offset Elo given odds −0.09 / +0.06, SEP 2016–21 design years; elo_off at the close −0.05, SRR; TTT and Glicko onM ties, RS stage B). Leverage-weighting re-estimates the same results. Its premise, a leverage-blind market, is contradicted by part B (43% applied ≈ the damped truth, N7) |
| MEC-K2 head-to-head dominance | refine | – | A sensitivity of I-001's modulator inside B-LEVER: prior ≤ 0.01, pair-specific gap variance ≈ 0 (N10), and its parent expects ≈ 0 |
| MAT-L1 later-round slope | refine | 0.5 | Merged with LIT-1's later-round column (the same Lahvička slope) in B-FLB; LIT-1's draw-relative binary L is primary, round depth a sensitivity |
| MAT-K1 spw-only profile | refine | – | Outside the family: an optional M2 representation arm. Its screen contrast z_C1 − z_spw is a sensitivity of I-008, and its result-free part (N12) already set I-008's primary |
| MAT-K2 levels leak non-linearly | refine | – | A novelty diagnostic: report b for s̃·η beside s·η (B-LEVER, I-036, I-084, B-FLB, S2). See the K2 note below |
| MAT-R1 recording-fault detector | refine | – | A data-quality step, no slot. Report the flags to the data-continuity study (new: Roland Garros qualifying 2022, women, first serves +6.5 pp, z 10.0). Down-weighting flagged events is a robustness sensitivity of the new columns only |
| MAT-R2 2025–26 measurement shift | refine | – | A final-test pre-registration item; see below |
| LIT-1 later-round and high-profile slopes | refine | 0.5 | Block B-FLB {L·η, HP·η}, one-sided +. HP correlates 0.71 with the format slope and L −0.26 with I-036, so B-FLB is fitted jointly with B-LEVER, I-036 and I-084. I-036 stays stand-alone: it is Lahvička's largest slope and should not be diluted |
| LIT-2 fame asymmetry | pass | 0.5 | Stand-alone abs(η)·ΔF, sign +, fitted jointly with B-REPUTE (corr 0.50 with I-083, opposite sign), so neither composite absorbs the other |
| C-1 sharp anchor | refine | – | Not a bundle candidate (Pinnacle ends in January 2026). Merged with I-039 as a descriptive diagnostic in the batch: s_PS beyond η, and η's gain against calibrated Pinnacle and against the average on the same matches |
| C-2 rating against price × obscurity | refine | 1 | B-INFO: (F − z)·O_min, sign +, controls F − z and O_min·η |
| BOD-L1 previous match's extra sets | refine | 1 | B-PREV with I-056: its graded PrevX equals I-056's Scare in best of three, so the main effect and its rest contrast are one mechanism. Literature grade B (Goossens et al.) |
| BOD-L2 career stage × forecast | refine | 1 | B6 (sign −, flatten) |
| BOD-C1 fatigue-contaminated form | refine | 0.5 | B-STATE with INFO-1 (sign +), controls ΔFat and sets_14d |
| BOD-C2 staleness × forecast | refine | 1 | B6 (sign −), fitted jointly with I-049 (corr +0.29): a declared rival |
| INFO-1 own-result update | refine | 0.5 | B-STATE, in the formulation below |
| INFO-2 late-formed first-round price | refine | 1 | B-INFO: s·Δ(w̃_q·s_q), sign +, controls the linear term, s·η, I-082's and I-076's columns |

## Rulings the coordinator asked for

**INFO-1: the cleanest formulation (legitimate).**
* **Why it is safe.** A player's own previous match surely finished before his next could start, so its box score is safe by construction for his features. The clock's lf + 1 rule exists for cross-player solves.
* **Column.** For each player, K = his own earlier matches with lf + 1 > es of this match: those the leak-proof IOS state has not counted, almost always the previous day's round.
* For each k in K:
  * take the serve residual (points won minus their expectation from the IOS state at es_k) and the return residual;
  * apply the IOS solver's one-step update to his own O and D: the information-weighted residual times the one-match weight, from the solver's decay and shrinkage, fixed and not tuned.
* Opponents' ratings are not updated.
* x = (δO_A + δD_A) − (δO_B + δD_B), sign +. Run `probe.py` anyway.
* **Caveats.**
  * Its prevalence is a clock-width artefact: either player has rest ≤ 0 in 34% (men) and 37% (women) of matches in 2014–21, but 31% and 2.4% in 2022–24 (`r2_checks`).
  * The two-week form already holds the last match, so expect ≤ 0.05.
  * As a process fix (recompute the base's IOS with own results) it would change the base: an owner decision, not this study's.

**R2-measure: what the final test must do about the Tennis My Life faults.** The faults affect the base and every arm.
1. **Repair before the test, without results.** Before the final pre-registration, replace faulty 2025–26 box scores with Sackmann or official records wherever they exist, extending the data-continuity study's replacements. The faults are women's aces and double faults (December 2024 – February 2026) and men's Slam first serves (since about August 2025). Apply the same repaired inputs to the base and every arm, and hash them.
2. **Count, pre-register, report.** Count each test match's contaminated share of the affected statistics' evidence (source flags only). Pre-register a secondary endpoint on matches where both players' share is under 20%, reported beside the primary, never gating.
3. **Flag the exposed arms.** Columns built from aces, double faults or the first/second split are exposed: B2, B3, the I-008 sensitivities built on z_C1, the profile parts of B7. The primary z_spw is not, because serve points won do not depend on the split. Report these arms' test results with the exposure.
4. **No λ-attenuation.** It is a model change with unknown sign, and is not applied unless pre-registered as its own arm.

**Math K2 (boosting recovers R² 0.56 / 0.47 of the pair's dominance from the 58).** It changes no weight:
* I-001 is already at 0.5, on the stronger price-structure ground;
* the screen tests against η, which already contains whatever TabPFN recovers;
* rank-based modulators (I-036, B-FLB, C-2) are not sums of the 58's levels.

Report s̃·η beside s·η as a diagnostic; G2 and G5 should cite flexible R² for S columns.

**The B5 precheck.** By my own rule the between-match column fails (reliability < 0.3; CV < 0.2 in first differences), so B5 loses weight 2 and dissolves. Its within-match member survives only through B6 and its own gate.

**I-012's declared look.** Ruled CONTESTED above, with three conditions:
* the shield enters at the block's reduced weight (B2, 0.5), with the link term τ_spw as a control;
* the look is a ledger row (both precheck forms computed before the form was fixed);
* nothing from the precheck may be cited as evidence for B2 at M2.


## Addendum, 6 October 2026 (late): two construction issues raised at build time

The market analyst raised both, in [builds/market.md](builds/market.md) and `round2/market/diagnostics.json`. Both rulings use only result-free construction diagnostics.

| Issue | Ruling | Reason and fix |
|---|---|---|
| B6: I-054 (ΣFat·η) and BOD-C2 (Σlog1p(rest)·η) correlate −0.944, both declared − | refine | More Fat is less rest. Two near-opposite columns with one sign cancel in the signed sum: the pair keeps SD ≈ 0.33 of one member. Read together, the two declared mechanisms say the forecast is flatter at both ends of one rest axis, a U that no linear sum can hold.<br>Neither sign changes (re-signing would be a post-hoc sign choice). Neither member is dropped (keeping BOD-C2 alone would silently re-sign I-054).<br>**Fix.** Both enter as one pre-declared U-shaped member: U_rest = R² − mean, where R = [std Σlog1p(rest) − std ΣFat]/√2, standardised per tour on 2014–2021. Sign −. The axis's linear slope R·η is an η-modulator control, so U_rest is identified by curvature alone.<br>B6 = {I-033, BOD-L2, U_rest}: a signed sum, sign −, weight 1. The separate linear columns become sensitivities |
| B6: I-028 fails its split-half gate | confirm | Split-half 0.041 < 0.3 (men −0.001, women 0.148; method-of-moments between-player variance ≈ 0): dropped by the pre-declared gate |
| B-RECAL: adj³ is 89% spanned by the 58 plus the M-set | no change | (η − z)³ shares η³ and z with the screen's nuisance. Testing it beyond that cubic is I-041's actual hypothesis: shrink the adjustment, not the forecast. The remainder (RMS ≈ 0.066 logit) identifies b. Wald 2 df at 0.5 stands |
| I-042: τ is 66% spanned by the 58 and 89% with the M-set | weight 2 → 1 | Its Σĥ·sinh z part is mostly the mean hazard times a smooth odd function of the price, which the screen's calibration terms absorb; that part is calibration, not hazard information. The hazard-specific remainder has RMS ≈ 0.036 logit, worth ≈ 0.06 mLL even if the close omitted every retirement (the analyst's estimate): half the weight-2 MDE. The precheck rule set weight 2 assuming the whole τ was identifiable, and that premise fails on a result-free diagnostic. The mechanism stays exact, so weight 1; the column, sign and controls are unchanged |

**Effect on the family.**
* Still 35 hypotheses. I-008 is now the only weight-2 row.
* Raw weights sum to 24.5. MDE (one-sided, weighted Holm): 0.12 / 0.14 / 0.15 mLL at weights 2 / 1 / 0.5; 0.17 for a two-sided Wald row at 0.5.
* hypothesis_family.md and its CSV are updated.


## Addendum, 7 October 2026: the meta-auditor's checkpoint 1 (R-1, R-5, R-6, R-7, R-8; F-1, F-4)

These are recorded as ruled in [checkpoint_1.md](../meta/checkpoint_1.md). They are text and construction corrections made before any result. No weight or test changes beyond them.

| Item | Change |
|---|---|
| R-1, F-1 | B-STATE = BOD-C1 alone: ΔPastFat, sign +, weight 0.5, the same controls, its nearest inputs recomputed by the module's own result-free rule. INFO-1 is dropped: its premise (that the IOS state misses the player's own last match) is false. The panel's IOS change correlates 0.879 with the proposed update, slope 1.10. INFO-1 runs only as a descriptive sensitivity; it never gates and never enters the bundle. This supersedes this file's earlier INFO-1 ruling |
| R-5, F-4 | B-INJ's I-045 member reads ΔDec = −ΔTr (within-event serve decay), sign −. That is the registered mechanism and the code's direction; the family's earlier "ΔTr, −" text was wrong |
| R-6 | B7 and B9a gate on the slow-trait widening (variance × 1.25), as B3 and B-HOME do. The height permutation (P2) is computed and reported as a diagnostic of the height members only, never folded into the block's p |
| R-7 | H-S2 receives the slow-trait widening: t₁ and t₂ are divided by √1.25 before the joint z, the filter and the replication |
| R-8 | B4 is dropped: I-019 and I-021 failed their persistence gates, and I-018 failed MEC-10's serve-point clause |
| Text only | B-CLUTCH (I-026 alone after I-009 and I-027 failed their gates) and B-VENUE (I-072 alone after I-073 failed) now show their built members |
| F-4 | A `multipliers` column states each block's applied member signs and its tested sign |

**Effect.**
* 34 hypotheses (33 screen rows plus H-S2). Raw weights sum to 24.0.
* MDE (one-sided, weighted Holm): 0.12 / 0.14 / 0.15 mLL at weights 2 / 1 / 0.5; 0.17 for a two-sided Wald row at 0.5.
* hypothesis_family.md and its CSV (now with the `multipliers` column) are rebuilt by `build_family.py`.
