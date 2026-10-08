# Round-2 builds · analyst STRUCTURE

6 October 2026 · EDA analyst "STRUCTURE" · Research evidence, not a decision. Built to the final [hypothesis family](../hypothesis_family.md) and [rulings](../rulings.md), which supersede the round-1 cards where they differ. **No result was read:** no builder or diagnostic touches `a_won`; nothing after 2024 is loaded (history is cut at the panel's last season inside every builder); prices enter only as η in the batch.

## Status of my rows

| hid | members kept (dropped by their result-free gate) | test · sign · weight · trait | module | swap test |
|---|---|---|---|---|
| I-008 | I-008 (z_spw remainder) | single · + · 2 · slow | `f03_composition` | pass |
| B-LEVER | I-001 κ_pair, I-006 format slope, κ_surf | Wald 3 df · ± · 0.5 · slow | `f02_leverage` | pass |
| B2 | I-012 (contested, restored by MEC-R2b), I-013 | signed sum · + · 0.5 · slow | `f03_composition` | pass |
| B3 | I-016, I-022 | Wald 2 df · ± · 0.5 · fixed (height; screened with the slow-trait widening × 1.25, orchestrator decision) | `f04_second_serve` | pass |
| (B4) | **dropped** (orchestrator decision): I-019, I-021 failed their persistence gates; I-018 failed MEC-10's out-of-sample serve-point condition on both tours | – | `f05_matchup` (code, gates, probe kept; no row) | – |
| B7 | I-023, I-031, I-032, I-048 (E and F columns) | signed sum · + (signs per member) · 1 · slow (checkpoint 1, R-6 / F-2; height permutation a diagnostic only) | `f07_evidence_age` | pass |
| B-CLUTCH | I-026 · dropped I-009, I-027 | signed sum · + · 0.5 · slow | `f08_clutch` | pass |
| B-VENUE | I-072 · dropped I-073 | signed sum · + · 0.5 · slow | `f09_venue` | pass |
| B-AGE | I-070 · dropped I-068 (and I-069 with it) | single · + · 0.5 · slow | `f07_evidence_age` | pass |
| (B5) | dissolved by the B5 rule: I-029 fails; I-028 fails its gate for B6 | – | `f06_volatility` (measures only, no row) | – |

Swap tests: `./python.sh src/eda/feature_interactions/screen_batch.py --prepare --module <m>` for each module (partial tables in `data/studies/feature_interactions/hypotheses/`). Diagnostics: each module's `__main__` writes `data/studies/feature_interactions/round2/structure/<module>.json`. Helper tests: `test/feature_interactions/test_structure_lib.py` (7 pass).

## How every row is built

* **Library.** `f01_structure_lib.py` holds the shared helpers and no hypothesis (`HYPOTHESES = []`; it is a `f*` module so the batch hashes it). Point probabilities use Stage 3's 2010–2018 tour × surface averages (`stage4_constants.csv`), the same centre the surface IOS uses; compositions use `stage2_iid` with each match's best-of and the Slams' deciding-set rules.
* **Result-free centring.** Every symmetric modulator is centred on 2014–2021 rows; every block member is divided by its 2014–2021 SD and multiplied by its declared sign. A member missing on a row contributes 0 there, with its missingness among the controls.
* **Remainder form.** `resid_on_58` subtracts a least-squares projection on the 58 inputs (intercept, missing indicators) fitted on 2013–2018 rows, per tour where the family says so. It is swap-consistent: refitted on the swapped panel, the remainder changes sign exactly.
* **The clock.** Every cross-player construction accumulates per key with `clock_sum`: a source counts from `lf + 1`, a target reads the state at `es`. Sums accumulate within each key only, so no other key's values can reach a target, not even through rounding.
* **Probe-equivalent.** `probe_check` reverses every result of matches that surely started after a cut day (winner and both players' statistics exchanged) and rebuilds the state. Every panel match starting on or before the cut must keep its value **exactly**; the count of later matches that moved shows the probe has power. The cuts are 2016-09-07, 2019-07-10, 2021-01-27, 2023-09-06 and 2024-07-10. Constants (frozen centroids, K) are held fixed.
* **Gates.** "Split-half" is the raw correlation of the two halves, as in the project's shot-level and Stage 3 code. Spearman–Brown values are given where a gate is close.
* **Std.** The nearest inputs to the candidate on 2014–2021 rows, by |correlation|. `odds_logit` is excluded for price slopes because it is the price base's own offset.

## I-008 · the surface-IOS serve points composed through the iid model (weight 2)

* **Column.** z_spw = logit P_iid(expit(μ + O^spw_A − D^spw_B), expit(μ + O^spw_B − D^spw_A); best-of, deciding-set rule), from the leak-proof surface IOS (`srf_O_eff_spw`, `srf_D_eff_spw`). x = its remainder after a per-tour projection on the 58 inputs fitted on 2013–2018 (MEC-R1, MAT-R4). Sign +.
* **Controls.** ratings_iid, ios_points_short (the family's Std). **Deployment.** TabPFN diff column `f03_z_spw`, else a nudge.
* **Numbers (observed, 2014–2021 unless stated).**
  * corr(z_spw, ratings_iid) 0.926; corr(z_spw, z_C1) 0.981; R² of z_spw on the 58 is 0.964.
  * Remainder SD, men / women: 0.257 / 0.204 (2014–21), 0.248 / 0.201 (2019–21), 0.230 / 0.193 (2022–24). The ruling quotes 0.25 / 0.21 (N15).
  * Novelty R² of x on the 58: 0.023. Nearest inputs: ratings_iid −0.106, elo_games −0.087, elo_overall −0.085, ios_points_short −0.080. corr with κ_pair·η 0.087.
  * Coverage 100% on both tours and windows.
* **Sensitivities** (`SENSITIVITIES`, same remainder form, never hypotheses; `SENSITIVITY_OF` maps each to I-008, whose controls the batch reuses for its descriptive outputs). SD men / women and correlation with the primary:
  * z_C1: 0.218 / 0.096, r 0.66;
  * damped (V 0.154 / 0.183): 0.102 / 0.105, r 0.91;
  * link-corrected (MEC-L1, γ_s = 1 − 2p̄_s): 0.261 / 0.204, r 0.994;
  * z_C1 − z_spw (two-sided): 0.157 / 0.188, r −0.70.
* **Timing.** A per-match function of the leak-proof IOS; inherits its probe.

## B-LEVER · the price's leverage by match structure (Wald 3 df, weight 0.5)

* **Columns** (symmetric modulators, the batch forms s·η):
  1. κ_pair = β_L(m_pair)/β_L(μ_cell) − 1, centred within tour × surface (I-001);
  2. 1[bo5], centred within tour (I-006's format slope; men's Slams);
  3. κ_surf = β_L(μ_cell)/β_L(μ_tour) − 1, centred within tour.
  * m_pair = μ_spw + ½(O_A + O_B − D_A − D_B) from the surface IOS. β_L is the iid model's d logit P/dΔ at Δ = 0, with the match's best-of and deciding-set rule (h = 10⁻³).
* **Controls.** The M-set; η·1[Slam]. Std: prod_bp_saved, iosD_second_won, prod_first_won (κ_pair), ratings_iid, ios_points_short, points_52w (format), form_ace, iosO_first_won (κ_surf).
* **Fitted jointly** with I-036 and B-FLB: their modulators × η enter as controls, imported from the market analyst's `f10_price_slopes` (obscurity, unranked flag, `flb_parts` L and HP). That module in turn imports `lever_columns`, and both pass the batch together.
* **Numbers.**
  * RMS on 2014–2021, men / women: κ_pair 6.5% / 2.5% (the audit 6.5 / 2.6); κ_surf 3.0% / 1.1% (the rebuttal 3.2% for men); 1[bo5] 0.40 / 0.
  * Novelty R² of s·η on the 58: 0.275, 0.160, 0.027. The batch's R² column (0.865) is that of the modulators themselves; 1[bo5] is the best_of input.
  * Column correlations ≤ 0.12; 1[bo5] correlates 0.67 with B-FLB's HP.
* **Deployment.** Nudge; TabPFN context form `f02_kappa_pair`. **Constants.** None tuned.
* **Open issue.** The rebuttal's fix "compute κ at full match dominance, adding I-072's event intercept" is not in the family row, so it is not in the primary. The serve-point venue pace could be added from `f09_venue` as a sensitivity.

## B2 · free points and ace curvature (signed sum, weight 0.5)

* **Members.**
  * I-012 (+): the free-point shield x = c_{A→B} − c_{B→A} (MEC-04, declared g). For server P and returner Q: a = expit(μ_ace + O^ace_P − D^ace_Q), r = expit(logit r0 − k·D^spw_Q), with r0 = (p0 − a0)/(1 − a0) at the server's own rates. k = p̄(1 − p̄)/((1 − ā)·r̄(1 − r̄)) from the cell averages, so the mean elasticity is 1. Then c = logit(a + (1 − a)r) − (μ + O^spw_P − D^spw_Q).
  * I-013 (+): e_ace = expit(μ_ace + O^ace_A − D^ace_B) − expit(μ_ace + O^ace_B − D^ace_A).
* **Controls.** iosO_ace, iosD_ace, prod_ace, ΔD^spw, τ_spw = O^spw_A·D^spw_B − O^spw_B·D^spw_A (MEC-L1); Std formdef_ace, iosO_first_won, form_ace.
  * η-modulators: ΣO^ace, ΣD^ace, ΣD^spw, Σg (g = 1 − the returner elasticity at the server's own rates), centred within tour × surface.
* **Deployment.** TabPFN diff columns `f03_shield`, `f03_e_ace`. Exposed to ace recording faults (R2-measure).
* **Novelty and coverage.** R² on the 58: shield 0.899, e_ace 0.882, block 0.892; τ_spw 0.973. corr(shield, e_ace) 0.085; corr(shield, τ_spw) −0.47. Coverage 100%.
* **I-012's precheck** (`shield_precheck`, 2013–2018 pool matches, 122,716 men's and 42,712 women's serve rows): the analysts' form failed.
  * Slope of the serve-point residual on D^spw × (the server's ace rate − mean), player-clustered SE: men −0.009 ± 0.076, women +0.023 ± 0.277. The shield predicts −1.13 and −1.17 on the same rows.
  * p_struct forecasts serve points worse than the additive IOS: −0.23 milli per point (men), −0.07 (women); lower log loss is better.
  * Ruling MEC-R2b (CONTESTED) restores I-012 at the block's reduced weight with τ_spw as a control. The precheck is a ledger row and counts as no evidence at M2. `KEEP_I012 = True`.

## B3 · second-serve style matchups (Wald 2 df, weight 0.5, fixed trait height)

* **Members** (each as its own column of the Wald block):
  * I-016 (±): ρ_A·D^sw_B − ρ_B·D^sw_A, ρ = z(O^df) + z(O^sw). Each z is the surface-IOS offence, centred within tour × surface and divided by its pooled SD (both players, 2014–2021).
  * I-022: O^sw_A(h̄ − h_B) − O^sw_B(h̄ − h_A), heights in cm, h̄ = the tour's mean over both players on 2014–2021 rows. Pooled over tours.
* **Controls** (per member, the round-1 cards): iosO_df, iosO_second_won, iosD_second_won, prod_df, prod_second_won, Δheight, miss_height. Std: iosO_first_won, iosO_hold (I-016), prod_first_won, iosO_ace (I-022).
  * η-modulators: Σρ, ΣD^sw, ΣO^sw, Σheight.
* **Trait.** `prepare` returns height_a/_b; the row is `"trait": "fixed", "trait_cols": ["height"]`, `"wald": True`. A Wald block has no permutation null (verifier B9), so the batch screens it with the slow-trait widening, covariance × 1.25 (plan.md, orchestrator decision).
* **Prechecks** (statistic level, 2013–2018 pool matches, player-clustered z):
  * I-016, the residual of second-serve points won on ρ × D^sw: men −2.25, women +2.73. The double-fault residual: men +5.74, women −0.94. Not both intervals include 0, so it **passes** (MEC-07's kill needs both to).
  * I-022, the second-serve residual on O^sw × (h̄ − h_returner): men +1.60, women +2.63; pooled ≈ +2.5. **Passes** pooled. On men alone the interval would include 0 (z 1.60).
* **Novelty and coverage.** R² on the 58: I-016 0.725, I-022 0.487; corr 0.19. Coverage men 100%; women 93% (2014–21) and 64% (2022–24), from heights.
* **Deployment.** TabPFN diff columns `f04_risky_second`, `f04_kick_short`. Exposed to double-fault and first/second-split faults (R2-measure).

## B7 · unknown is not average: evidence and staleness (signed sum, weight 1, trait slow)

* **Members** (signs as declared):
  * I-023 (+), the height prior for thin histories: Δ[K_h/(n + K_h)·(β_h(h − h̄) − O^ace)], n = Stage 3's rated serve points. β_h and h̄ per tour come from O^ace on height, players with ≥ 5,000 rated serve points, 2013–2018 panel rows: β_h 0.0476 per cm (men), 0.0465 (women); h̄ 187.1 / 174.0 cm.
  * I-031 (+), the re-anchored points form: the existing input is r·raw with r = s0/(s0 + K3) (Stage B: s0 = Σ2^(−age/2 weeks), K3 = 10 men, 20 women). So form* − form = (1 − r)·ℓ, and the column is Δ[((1 − r) − c)·ℓ].
    * ℓ = the 52-week level Σz/(n + K3) of z_adjperf_tpw on the clock.
    * c = the pooled 2014–2021 mean of 1 − r. Given Δℓ this is identical; the centring stops Δℓ from setting the member's scale.
    * The rebuilt form reproduces `in_adjperf_tpw_2w` to 4.5·10⁻⁸ on all 54,882 rows.
  * I-032 (+): (r̄ − mean)·Δ(O^spw + D^spw), r̄ = the harmonic mean of NS/(NS + 20).
  * I-048 (−), two columns as the family lists them: Δ[((1 − w) − c)·E_spw] and Δ[((1 − w) − c)·F_spw], with w = NS/(NS + 10)·exp(−layoff/180).
* **Controls** (the family's): iosO_ace, Δheight, miss_height; adjperf_tpw_2w, Δℓ, miss_ℓ; ΔO^spw, ΔD^spw; ΔE_spw, ΔF_spw; Std form_hold, form_first_won. η-modulator: r̄.
* **Gates** (all pass):
  * CV(r) = 0.584 (≥ 0.2; 2013–2021 model rows).
  * CV(r̄) = 0.176 (≥ 0.15); r̄ deciles 0.64 / 0.88 / 0.93.
  * The height ace check, on 2013–2018 pool matches of thin histories (< 1,000 rated serve points; 8,129 men's and 2,968 women's rows): the blended O~ improves next-match ace forecasts by 0.40 milli per serve point pooled (men 0.47, women 0.21; ≥ 0.05).
* **Constants.** K_h = 100 was tuned on that same result-free target over a grid of 25–8,000. Log loss per point: 0.181925 at 100, 0.182323 for the plain IOS, 0.182558 at the audit's 1,000. K3 is Stage B's. 20, 10 and 180 were fixed by the audit.
* **Novelty and coverage.** R² on the 58: I-023 0.066, I-031 0.452, I-032 0.063, I-048 (E + F) 0.109; block 0.106. |corr| between members ≤ 0.11 (E and F parts 0.34). Coverage 100% (missing heights and ℓ enter as zero plus a missingness control).
* **Deployment.** TabPFN diff columns `f07_height_prior`, `f07_reanchor`, `f07_ios_x_rbar`, `f07_stale_E`, `f07_stale_F`. The profile parts are exposed to ace faults (R2-measure).
* **Trait** (meta-auditor checkpoint 1, R-6 / F-2): `"trait": "slow"`, so B7 gates on the slow-trait widening. `"trait_cols": ["height"]` is kept: the batch computes the height permutation as a diagnostic only, never folded into p_joint, because height enters I-023 alone.

## B-AGE · I-070 alone (weight 0.5)

* **Column.** Δ[(Short − Long)·h(age)], h = (25 − age)+ − 0.5(age − 30)+. Short = adjperf_tpw_2w and Long = spw IOS O + D, each divided by its pooled 2014–2021 SD (BOD-28, as the audit fixed it). Sign +.
* **Controls.** age, adjperf_tpw_2w, ΔLong; Std age_sq, iosO_bp_saved. η-modulators: Σage, Σh, Σ(S − L).
* **Gate that dropped I-068** (`age_drift_precheck`, 2013–2018 pool matches): the return-minus-serve residual on (age − 29)+ has slope +0.0011 ± 0.0008 (men, 122,547 rows) and +0.0005 ± 0.0013 (women). The mechanism needs a negative slope. Binned means for men stay flat at −0.016 to −0.025 from 29 to 45. `KEEP_I068 = False`, as the rulings note.
* **Novelty and coverage.** R² 0.637 on the 58 (nearest age 0.78, age_sq 0.43, iosO_bp_saved 0.22); coverage 100%.
* **Deployment.** TabPFN diff column `f07_age_trust_form`.

## B-CLUTCH · persistent non-iid scoring skill (signed sum, weight 0.5): I-026 alone

* **Kept member** I-026 (+), big-point return skill × the scarcity of break points: x = Δb·(s − mean s).
  * Δb is Stage 4's `bigpoint_return|single`: the shrunk importance-weighted minus plain return points won, from earlier Grand Slams' point files (own history).
  * s = β̄_c/β̂_AB. β̂_AB is the mean of the iid expected break points per service game at p_AB and p_BA: q³ + 4pq³ + 10p²q³ + 20p³q³·q/(1 − 2pq), which is 0.59 at p = 0.62 and 0.33 at 0.70, matching MEC-18. β̄_c is its tour × surface mean.
  * Stage 4 stores only A − B, so `prepare` carries Δb as halves (±Δb/2). That makes the swap exact. Orientation verified: Stage 4's age and height differences equal the panel's A − B to 10⁻⁶.
* **Controls.** Δb; Std prod_bp_saved, prod_first_won. η-modulators: s, 1[Δb missing].
* **Coverage.** 89% / 85% (men / women, 2014–21), 86% / 85% (2022–24). **R²** 0.116 on the 58. **Deployment.** `f08_bigpoint_x_scarcity`.
* **Open issue.** Sackmann's Slam point files end in 2024, so Δb goes stale in 2025–26 unless the point-sequence table extends it.
* **Dropped by their gates** (2010–2018 statistics):
  * I-009, in the remainder form the family gives. The per-player hold residual (holds − service games × game(p) at the match's own serve-point share) has split-half r 0.160 (men, 521 players with 50+ matches a half) and 0.270 (women, 108), below 0.3. Spearman–Brown gives 0.28 / 0.43. The break side, for information: 0.248 / 0.239. On 2010–2021: 0.151 / 0.234.
  * I-027. The excess of consolidations and breaks back over the player's other games in the same match (point-by-point counts, `shot_level/stage1_match_stats`) has split-half r −0.072 (men, 83 players with 15+ matches a half) and −0.011 (women, 24); gate > 0.1. On 2010–2021: −0.037 / −0.049. Method of moments finds no between-player variance for men.

## B-VENUE · venue conditions × serve profile (signed sum, weight 0.5): I-072 alone

* **Kept member** I-072 (+): v_e·ΔO^ace (I-077 folded in).
  * v_e = Σw·u/(Σw·n + 2,000) over the venue's serves released by es: earlier editions plus the current edition's earlier days, qualifying included.
  * u = (aces − π·n)/(π(1 − π)), with π the surface-IOS ace expectation as of that match.
  * w = 2^(−years/2). The 2,000 points and the half-life are MEC-03's.
  * Venue = tour × normalised tournament name × surface.
* **Controls.** iosO_ace; Std prod_hold, prod_first_won, prod_bp_saved. η-modulator: v_e.
* **Gate passes.** Venue carry-over (the pace from earlier editions against the edition's own ace residual, 2014–2021 editions with 2,000+ serve points): r = 0.661 (men, 1,356 editions) and 0.566 (women, 300), against the 0.3 gate. The mechanics brainstormer, adjusting for who played, measured 0.52 / 0.42.
* **Probe passed.** At every cut the earlier rows' maximum change is 0.0; 1,888–35,714 later rows move.
* **Numbers.** SD of v_e on 2014–2021 rows: 0.113 (men) and 0.120 (women) logit, over 262 venues. R² of the column on the 58 is 0.036. Coverage 100% (no earlier edition gives v_e = 0).
* **Deployment.** `f09_venue_pace_x_ace`.
* **Dropped:** I-073, per-player indoor deviations G (serve) and H (return). Indoor comes from Stage 0's flag, tennis-data's Court (f25_switch's join) or the event's majority. The odd/even-season carry-over (players with 1,500+ indoor points) is G −0.006 (men, 177) / −0.083 (women, 83) and H 0.124 / 0.077, all below 0.15. Its probe passed with I-072's.

## B5 · the pair's volatility (dissolved) and I-028 for B6 (`f06_volatility`, no row)

* **Measures built** (importable for B6 or a restored B5):
  * I-029: σ²_P = (Σw·x + K·m)/(Σw + K), the long-memory shrunk mean of x_j = ½[(u_s² − 1/(n_s p_s(1 − p_s))) + (u_r² − 1/(n_r p_r(1 − p_r)))]. Here u_s and u_r are the serve-point and return-point logit residuals against the surface IOS, w = 2^(−age/104 weeks), and the clock applies.
  * I-028: κ_P is the same long-memory mean of the per-match excess variance of the per-set games share beyond the iid variance at the match's own hold rates. Sets of more than 13 games drop the match.
  * Modulators `i029_modulator` (V_pair/V̄_c − 1) and `i028_modulator` (K_pair − K̄_c); `prepare_volatility` builds the states.
* **Constants** (method of moments, 2010–2018, players with 10+ matches):
  * I-029: K 25.7 / 45.0 matches, m 0.0715 / 0.0710 (men / women).
  * I-028: K 266 (men; τ² = 2.8·10⁻⁶) and capped at 10,000 for women (τ² < 0).
  * The 104-week half-life was fixed in advance.
* **The B5 rule, applied** (`pair_cv_precheck`, players with 50+ matches a half, 2010–2018):
  * I-029: split-half r 0.279 (men, 508 players) and 0.225 (women, 197), below 0.3 (Spearman–Brown 0.44 / 0.37).
  * De-noised per-player CV 0.159 / 0.129, so pair CV 0.113 / 0.091, below 0.2.
  * If the mean own day variance is taken as half the serve × return residual cross-product (0.048 / 0.052), pair CV is 0.31 / 0.23. The raw reliability criterion fails either way.
  * B5 dissolves, as the rulings record.
* **I-028's gate for B6** (split-half ≥ 0.3): r 0.011 (men) and 0.154 (women). It fails, so I-028 should not enter B6 (f13_uncertainty).
* **Probe passed** for I-029's clock-built state. Earlier rows' maximum change is 0.0 at all five cuts; 1,858–35,722 later rows move.
* **History order.** These are the live numbers. `history.long_table()` changed its own-order sort at 22:00 (events placed by their earliest day, verifier B3), which moved the split-half values slightly from my first runs (I-029 men 0.241 → 0.279).
  * Before the per-key accumulation fix, `clock_sum` let other players' values move earlier sums by 5·10⁻¹² through floating-point rounding. That is fixed and tested.

## B4 · matchup-specific serve-point deviations: DROPPED (orchestrator decision, 6 Oct 2026)

Every member failed a pre-declared result-free gate, read as declared: I-019 and I-021 their persistence gates (below), I-018 MEC-10's out-of-sample serve-point condition on both tours (+0.002 and −0.016 milli per point, against 0.02). `f05_matchup.HYPOTHESES` is empty; the builders, gates, probe and diagnostics stay importable, with the row as built kept as `B4_SPEC`. The build is recorded below.

All three members are field statistics on the clock. Source rows are put in a canonical order (match, server), so the frozen k-means fit and every sum are independent of the history table's row order. They are built from 420,732 pool serve rows (main tour, qualifying, Challengers; ≥ 20 serve points; completed or retired). Each row's residual is r = logit((spw_n + ½)/(spw_d + 1)) − (μ + O^spw_S − D^spw_R), against the leak-proof surface IOS.

* **Kept: I-018 (+), the style-pair residual table** (MEC-10).
  * Six styles per tour, by k-means (seed 20261006, 20 starts) on standardised pooled IOS (cur_O_spw, cur_D_spw, cur_O_ace, cur_O_first_in, cur_O_df) plus hand (1 = left). Fitted on 2010–2016 serve rows and frozen.
    * Men's styles hold 12,593–31,573 rows each; one of the six is the left-handers (hand centroid +2.47 SD; women +3.31).
    * The largest style is the big servers (O^spw +1.79, D +1.26, ace +1.19).
  * τ_ij = Σn·r/(Σn + 20,000) over serves from style i to style j released by es. The 36 cells of each match's tour ride as context columns.
  * x = τ_{s(A)s(B)} − τ_{s(B)s(A)}, with the styles recomputed in `combine` from the panel's IOS and hand, so the batch's hand permutation reassigns them.
* **The gate, applied per tour.** The cell-by-cell correlation between 2010–2016 and 2017–2021 (the audit's ≥ 0.3) is 0.528 for men (contrast τ_ij − τ_ji 0.466) and −0.065 for women (contrast 0.014).
  * It passes for men only, so the member is kept on men's rows and is 0 on women's (`MEN_ONLY_I018`). That follows the rulings' "B4 is men-only in substance (N10)".
  * **Flag for the auditor.** The originator's second condition, an out-of-sample serve-point gain of 0.02 milli per point, is not met: +0.002 (men), −0.016 (women). The audit's card kept only the stability gate, so I applied only that. A strict reading of MEC-10 drops I-018 too, and B4 with it.
* **Dropped: I-019, the points head-to-head residual** (MEC-11): r_AB = Σ(u^A − u^B)/(Σ points + 1,000). The meeting-to-meeting persistence for pairs with 3+ meetings is 0.032 (men, 5,590 pairs, 16,435 meetings) and 0.043 (women, 2,186 pairs), 2010–2018. On 2010–2021 it is 0.033 / 0.045. The gate is 0.05.
* **Dropped: I-021, the left-hand deviation** G_A·L_B − G_B·L_A, a two-stage extended IOS with E for serving to left-handers and F for returning against them.
  * Method-of-moments shrinkage, 2010–2018: K_E 29,739 / 11,483 and K_F 39,987 / 36,047 serve points.
  * F_R odd/even-season r for right-handed returners with 1,500+ return points against left-handers: 0.071 (men, 423) and 0.026 (women, 98). The shuffled-hand placebo's 95th percentile is 0.086 / 0.207. The gate (≥ 0.15 and above the placebo) fails.
* **Controls** (the kept member's): five style-indicator differences, the five clustering-input differences, Δhand; Std iosO_hold, iosO_first_won, elo_overall.
* **Trait.** `prepare` returns hand_a/_b as 1 (left), 0 (right) or NaN; the row is `"trait": "fixed", "trait_cols": ["hand"]`.
* **Probe passed** for all three fields (τ cells, E/F, head-to-head sums). Earlier rows' maximum change is 0.0 at every cut; 1,918–35,775 later rows move. The frozen centroids are held fixed: they are 2010–2016 constants of IOS ratings, with no price and no result.
* **Novelty and coverage.** R² of the block on the 58 is 0.175; nearest iosO_hold 0.33, iosO_first_won 0.33, elo_overall 0.30. Nonzero on 35% of 2014–2021 rows (men's rows with two different styles). Coverage 100%.
* **Deployment.** `f05_style_pair`.

## Batch check (final run, all nine modules together)

`--prepare --module f01_structure_lib,…,f09_venue`, rerun after the orchestrator's decisions, and again on 7 Oct for f02, f03, f04, f07, f08 and f09 after checkpoint 1 (B7 slow, f03's `SENSITIVITY_OF`): eight rows, every swap test true (x and controls). Novelty R² is of x on the 58 inputs (2014–2021); for the price-slope block it is that of the modulators. Coverage is the share of rows with every column of x defined.

| hid | k | novelty R² | coverage men 2014–21 / 2022–24 | coverage women 2014–21 / 2022–24 |
|---|---|---|---|---|
| B-LEVER | 3 | 0.865 (s·η: 0.275 / 0.160 / 0.027) | 1.00 / 1.00 | 1.00 / 1.00 |
| I-008 | 1 | 0.023 | 1.00 / 1.00 | 1.00 / 1.00 |
| B2 | 1 | 0.892 | 1.00 / 1.00 | 1.00 / 1.00 |
| B3 | 2 | 0.725 | 1.00 / 1.00 | 0.93 / 0.64 |
| B7 | 1 | 0.106 | 1.00 / 1.00 | 1.00 / 1.00 |
| B-AGE | 1 | 0.637 | 1.00 / 1.00 | 1.00 / 1.00 |
| B-CLUTCH | 1 | 0.116 | 0.89 / 0.86 | 0.85 / 0.85 |
| B-VENUE | 1 | 0.036 | 1.00 / 1.00 | 1.00 / 1.00 |

The batch now drops `a_won` before building (B10); every builder runs unchanged.

## Open issues for the orchestrator and the auditor

1. **Gates that dropped members**, all result-free and all recorded in the modules' `KEEP` flags (one switch each):
   * I-068 (B-AGE) and I-073 (B-VENUE);
   * I-009 and I-027 (B-CLUTCH);
   * I-018, I-019 and I-021 (B4, so the block is dropped);
   * I-029 (B5, dissolved);
   * I-028, which therefore should not enter B6.
2. **Decided by the orchestrator:** B4 is dropped (I-018 fails MEC-10's out-of-sample condition on both tours); split-half gates use the raw correlation as declared, so I-009 stays dropped (Spearman–Brown, not used: 0.43 for women).
3. **Harness.**
   * Wald blocks with a fixed-trait member (B3) are screened with the slow-trait widening, × 1.25 (orchestrator decision).
   * B7 gates on the slow-trait widening; its height permutation is a diagnostic only (checkpoint 1, R-6 / F-2).
4. **Coupled modules.** B-LEVER (f02) and f10's I-036, I-084 and B-FLB import each other's modulators inside functions, so there is no import cycle. They must be frozen together; they pass the batch together.
5. **Final-test builds (2025–26).**
   * Every builder cuts history at the panel's last season.
   * Every fitted constant is fixed in the code or computed on 2010–2018 / 2013–2018 / 2014–2021 rows only: the remainder projections, β_h, the frozen style centroids, the centring and scaling.
   * So `panel(max_season=2026)` rebuilds the same columns. Δb (B-CLUTCH) goes stale after 2024 (no Slam point files).
6. **Recording faults** (rulings R2-measure). Ace-based columns are exposed: B2 (both members), I-023 in B7, I-072 in B-VENUE (women's aces, December 2024 – February 2026). So are double-fault and first/second-split columns: B3. I-008's z_spw, B-LEVER, I-031, I-032, I-048 and I-070 are not, or only through the IOS profile.
7. **TabPFN columns.** They are returned in each `combine`'s `tabpfn` dictionary but not written through `registry.register`, to avoid concurrent writes to the shared `registry.json`. The orchestrator can register them when it builds the arms.
8. **Price-slope novelty.** For B-LEVER the batch's `novelty_r2` is that of the modulators s, not of s·η. The s·η values are in this report and in `f02_leverage.json`.

## Files

* Modules, `src/eda/feature_interactions/features/`:
  * `f01_structure_lib.py` (shared library);
  * `f02_leverage.py` (B-LEVER);
  * `f03_composition.py` (I-008, B2);
  * `f04_second_serve.py` (B3);
  * `f05_matchup.py` (B4, dropped: measures only, no row);
  * `f06_volatility.py` (B5's measures, no row);
  * `f07_evidence_age.py` (B7, B-AGE);
  * `f08_clutch.py` (B-CLUTCH);
  * `f09_venue.py` (B-VENUE).
* Diagnostics, gates and probes: `data/studies/feature_interactions/round2/structure/<module>.json`.
* Batch partial tables: `data/studies/feature_interactions/hypotheses/partial_<module>.csv`.
* Tests: `test/feature_interactions/test_structure_lib.py`.
* Data read (read-only): the panel's sources, `history.long_table()`, `surface_ios/surface_features.parquet`, `predictability_diagnostic/stage3_ratings.parquet`, `stage4_constants.csv`, `stage4_features.parquet` (`bigpoint_return|single`), `ufc_ideas/stageB_adj.parquet` and its summary, `shot_level/stage1_match_stats.parquet` (point-by-point counts), and tennis-data.co.uk's Court field through `f25_switch`. The point-sequence session's tables were not read.
