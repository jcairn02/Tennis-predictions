# Feature interactions, round 1: the mathematical audit

6 October 2026 · Mathematical auditor (G1) · Research evidence, not a decision. Every ruling follows [plan.md](../plan.md): hard kills only for reasons (a)–(e), formula before narrative, no result read.

**Read:** the brief, team, plan, the critique (§1.4, §2, §5), the master list with its 16 family files, `withdrawn.md` and `merges.md`, the four raw idea lists, the literature (as priors) and the inventory's §3 register. **Computed, result-free:** 41 proxy columns on the 2013–2021 player panel with the result column dropped at load (`src/eda/feature_interactions/round1/math_audit/`; outputs in `data/studies/feature_interactions/round1/math_audit/`). Every proxy passed a swap test. Prices entered only as regressors or modulators, which is look-ledger row 6.

## Keys

* **Value rule.** A missing log-odds term τ is worth ≈ 99·E[τ²] mLL (gain, higher is better), since E[p(1 − p)] = 0.198. A price-slope modulation with RMS κ is worth 79κ² (men) or 68κ² (women). These reproduce the mathematics lens's weights: E[p(1 − p)z²] = 0.157 and 0.136, E[2 cosh z] = 3.63 and 3.13.
* **The G2 line, 0.09 mLL, is a term of RMS ≈ 0.030 logit beyond the current best.** That is a third of TabPFN's whole adjustment.
* **MDE** (80% power, population-averaged, joint 2014–2024 coefficient test, one-sided weighted Holm over the proposed 34 hypotheses including S2):
  * by weight: 0.12 mLL at weight 2, 0.14 at weight 1, 0.16 at weight 0.5;
  * 0.17 two-sided; a single test 0.08;
  * fixed traits × 1.23, slow traits × 1.25;
  * a subgroup-only effect must reach the MDE divided by its share (Bo5 ≈ 1.4, a 2% subgroup ≈ 7).

## Verdicts

| | Count | IDs |
|---|---|---|
| **pass** | 10 | I-001 (1), I-008 (2), I-036 (1), I-042 (2), I-049 (0.5), I-052 (1), I-053 (1), I-056 (0.5), I-082 (1), I-084 (0.5) |
| **refine → a block** | 59 | 22 blocks, below |
| **refine → a stand-alone variant** | 1 | I-006 (the format slope 1[bo5]·η, two-sided, 0.5) |
| **refine → no slot** | 18 | sensitivities: I-002, I-010, I-011, I-030, I-057, I-062, I-069. Covered by S2: I-003, I-004, I-005. Decompositions of I-008: I-014, I-015. Folded: I-077. Split: I-051. Deferred: I-035, I-064. Post-M1 diagnostics: I-007, I-039 |
| **kill** | 3 | I-017 (b), I-020 (c, flagged), I-067 (c, flagged) |

The result is 34 hypotheses including S2: 11 stand-alone and 22 blocks. Withdrawn W-01 … W-20: all confirmed, none revived.

**The kills.**
* **I-017** (b): a rotation of existing inputs, R² = 1 on the 58. Supporting (e): IOS style tied with the odds twice (UFC stage D; MT §7).
* **I-020** (c): serve speeds cover 12% of men's 2013–2021 matches.
* **I-067** (c): no weather data is held.

The two (c) kills await the feasibility auditor.

**Weight 2:**
* **I-008**, the surface-IOS profile composed through the iid model. Its residual on the 58 inputs is 0.21 (men) and 0.10 (women) log-odds.
* **I-042**, retirement hazard × price, by exact label algebra. Conditional on its hazard-spread precheck.
* **B5**, the pair's volatility flattening the price. Conditional on a pair-CV precheck.

The two conditional rules are fixed in [withdrawn_and_blocks.md](math_audit/withdrawn_and_blocks.md).

**Weight 1:** I-001, I-036, I-052, I-053, I-082, and the blocks B2, B7, B-AGE, B-REPUTE and B-INFO.

## Blocks (members and tests in [withdrawn_and_blocks.md](math_audit/withdrawn_and_blocks.md))

| Block | Members | Weight |
|---|---|---|
| B2 free points and ace curvature | I-012, I-013 | 1 |
| B3 second-serve style | I-016, I-022 | 0.5 |
| B4 matchup-specific deviations | I-018, I-019, I-021 | 0.5 |
| B5 volatility flattens the price | I-028, I-029 | 2 (rule) |
| B6 transient uncertainty | I-033, I-034, I-054 | 0.5 |
| B7 evidence and staleness weighting | I-023, I-031, I-032, I-048 | 1 |
| B9a constitution × load | I-024, I-058, I-061 | 0.5 |
| B9b match demand × fatigue | I-063, I-065, I-066 | 0.5 |
| B10 arrival debt | I-059, I-060, I-074, I-088 | 0.5 |
| B11 on-site rhythm | I-051 (On), I-075, I-076 | 0.5 |
| B-SWITCH switch state × own style | I-046, I-047, I-050 | 0.5 |
| B-CLUTCH non-iid scoring skill | I-009, I-026, I-027 | 0.5 |
| B-ANCHOR artefacts of the average [A] | I-037, I-038 | 0.5 |
| B-RECAL the model's adjustment | I-040, I-041 | 0.5 |
| B-INJ hidden impairment | I-043, I-044, I-045 | 0.5 |
| B-VENUE venue × serve | I-072, I-073 | 0.5 |
| B-HOME home | I-078, I-079 | 0.5 |
| B-AGE age and memory | I-068, I-070 | 1 |
| B-REPUTE reputation anchoring | I-055, I-071, I-083 | 1 |
| B-INFO thin-information disagreement | I-080, I-081, I-087 | 1 |
| B-OVERREACT over-reaction to recent results | I-025, I-085, I-086, I-091 | 0.5 |
| B-MOTIV calendar effort | I-089, I-090 | 0.5 |

## Cross-cutting findings

1. **The marginality control s·η is the candidate itself for price-slope ideas.**
   * Where d is the price (I-001, I-028–I-030, I-033, I-034, I-036, I-037, I-049, I-054, I-084, refined I-006, I-042's Σh·sinh z part), the η-version's candidate is s·η.
   * If s·η is also a control, as the master list's code sets, b is identified only through −s·(η − z). That tests a rescaling of the model's adjustment, worth about κ² mLL.
   * Fix: the control set for these is the M-set plus Std.
   * Related: a symmetric s alone has no main effect in the intercept-free antisymmetric screen, so drop the "E", "O", "a", "m", "V" and "abs(Δ1)" main-effect controls.
2. **Constructions that read results.**
   * N is a ridge fitted on results with the price as offset, which breaks M5. Use the current best's adjustment η − z instead, or build N walk-forward after M1.
   * Δ1's outcome-calibrated rescaling: rescale to the price's SD instead.
   * I-025's β_f: take it from the iid model or fit it walk-forward.
   * I-010's V: Stage 3's statistic moments.
   * I-063's κ, η, λ: serve- and return-point residuals.
   * I-052's τ: fixed in advance.
   * I-042's estimator: chosen on the retirement label, a statistic target, with a ledger row.
3. **G2's R² < 0.95 misjudges composition columns.** z_C1 (I-008) has R² 0.98 on the 58 but a residual of 0.21 log-odds, seven times the 0.03 a 0.09 mLL term needs. Judge C columns by the residual SD, or test the residual (identical by Frisch–Waugh).
4. **The S2 levels arm already spans the spw sums** (98% linear in its 14 IOS sums). I-003, I-004 and I-005 add nothing to it, and S2 carries the TabPFN forms of I-013, I-053, I-054 and I-084.
5. **I-006's premise fails on the price's own structure.**
   * Its column is a product of two inputs: corr 0.994 with 1[bo5]·ratings_iid.
   * At matched ratings the close applies a Bo5/Bo3 log-odds ratio of 1.19–1.27. That is the iid 1.25, and above the 1.10–1.13 that day-noise damping implies.
   * So the format slope is tested two-sided. The same number serves as the result-free substitute for I-007.
6. **Pairs to fit jointly.** I-036 (obscurity) and I-084 (prominence) correlate −0.70 and declare the same sign, so fit them in one model. I-049 and I-054 correlate −0.37. I-048 correlates 0.63 with the surface study's deviation placebo (P3) and is 55% new, so it is tested beyond the plain deviations, and a P3 "pass" must be read beside it.
7. **Seen-2025/26 evidence** (I-006, I-020, I-030, I-035, I-037, I-049, I-063, I-071, I-080, I-085, I-086, I-087). These may be screened and enter the bundle, but this study cannot confirm them on 2025–2026. No weight was raised on that evidence, and the final report should show the bundle's test with and without them.
8. **Process.** I-005's suggestion to train TabPFN on both orientations is a harness decision for the orchestrator, not a hypothesis.

## Files

* Per family: [01](math_audit/01_serve_dominance_leverage_format.md) · [02](math_audit/02_composition_point_model.md) · [03](math_audit/03_statistic_style_matchups.md) · [04](math_audit/04_handedness_physique.md) · [05](math_audit/05_scoring_luck_pressure.md) · [06](math_audit/06_volatility.md) · [07](math_audit/07_reliability_evidence_uncertainty.md) · [08](math_audit/08_price_calibration_anchor.md) · [09](math_audit/09_retirement_injury_settlement.md) · [10](math_audit/10_surface_switching_staleness.md) · [11](math_audit/11_workload_recovery.md) · [12](math_audit/12_fatigue_style_attrition.md) · [13](math_audit/13_age_trajectory.md) · [14](math_audit/14_travel_venue_conditions.md) · [15](math_audit/15_rank_fame_attention.md) · [16](math_audit/16_motivation_narrative_timing.md); [withdrawn and blocks](math_audit/withdrawn_and_blocks.md).
* CSV, one row per master ID: `data/studies/feature_interactions/round1/math_audit.csv`, built from the cards by `build_csv.py`.
* Computations: `novelty.py` (R² on the 58, bounds, MDE table, the I-007 substitute), `overlaps.py`, `swap_check.py`, with `candidates.py` and `common_audit.py`. Outputs: `novelty.csv`, `numbers.json`, `overlaps.json`, `swap_check.json`, and the cached panel without results (`panel_le2021_noresult.parquet`). The cache was deleted on 8 Oct 2026 after a rebuild reproduced all 281 of its columns exactly. `common_audit.load_panel()` writes it again on first use, with one more column (`eta_model`) that no audit script reads.
