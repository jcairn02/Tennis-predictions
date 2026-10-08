# The hypothesis family for the screen (for the M1 freeze)

6 October 2026 · Mathematical auditor, after the round-2 [rulings](rulings.md) · Research evidence, not a decision. This is the single list the orchestrator hashes at M1. The machine-readable copy is `data/studies/feature_interactions/round2/hypothesis_family.csv`, built from the table below by `src/eda/feature_interactions/round1/math_audit/build_family.py`.

**34 hypotheses** (updated 7 October for checkpoint 1): 9 stand-alone columns or arms, 25 blocks. That is 33 screen rows plus H-S2.
* Raw weights sum to 24.0 after the addenda and B4's drop. Normalised to mean 1 they become 2.83, 1.42 and 0.71.
* The `multipliers` column gives each block's applied member signs and the sign tested (checkpoint 1 §1.2). It is the table's own orientation.
* **80%-power MDE**, population-averaged, joint 2014–2024 coefficient test, one-sided weighted Holm:
  * 0.12 mLL at weight 2, 0.14 at weight 1, 0.15 at weight 0.5;
  * 0.17 for a two-sided Wald row at weight 0.5;
  * × 1.23 for fixed traits, × 1.25 for slow traits.

**Rules every row inherits (from the round-1 audit, the rulings and [builders.md](../builders.md)):**
* **Price-slope rows** (`x_times_eta`): the candidate is s·η. The controls are the M-set and Std, never s·η itself, and never a symmetric s on its own.
* **Signed-sum blocks:** each member is standardised on the 2014–2021 rows, multiplied by its declared sign and summed. That gives one coefficient, tested one-sided.
* **Wald blocks:** k df, two-sided, weight 0.5.
* **A member whose pre-declared result-free gate fails before M1 drops.** Its block survives with the rest.
* **"Fitted jointly"** means each listed row's columns enter the other's regression as controls; each row keeps its own test.
* **Sensitivities** are pre-declared, never rescue a failed primary, and never enter the bundle.

## The family

| hid | members | primary column(s) | test | sign | multipliers | weight | trait | controls | deployment | module | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I-008 | I-008 | z_spw = logit P_iid(expit(μ + O^spw_A − D^spw_B), expit(μ + O^spw_B − D^spw_A); format, final-set rule), as its remainder after a per-tour OLS projection on the 58 inputs fitted on 2013–2018 without outcomes | single coefficient | + | x as is; tested + | 2 | slow | Std (ratings_iid, ios_points_short) | TabPFN diff column (z_spw), else nudge | f03_composition | sensitivities: z_C1, damped (V 0.154 / 0.183), link-corrected (MEC-L1), z_C1 − z_spw two-sided (MAT-K1); I-014, I-015 descriptive; robust to first/second-serve faults |
| I-036 | I-036 | η·O, O = max(log rank_A, log rank_B) − tour median (unranked = 1500 plus a flag) | single coefficient | + | x as is; tested + | 1 | slow | M-set; Std; unranked flag × η; fitted jointly with I-084, B-FLB, B-LEVER | nudge | f10_price_slopes | Lahvička's largest slope; [A/I]: rerun on the Pinnacle anchor descriptively |
| I-042 | I-042 | τ = ĥ_B/p − ĥ_A/(1 − p) = −Δĥ(1 + cosh z) − Σĥ·sinh z, p = σ(η); ĥ = estimator (a), k = 160 | single coefficient | + | x as is; tested + | 1 | slow | M-set; Std; no Δĥ, no Σĥ·η | nudge | f11_retirement | weight 2 → 1 (addendum): 89% of τ is spanned by the 58 plus the M-set, so even at coefficient 1 the identifiable value is ≈ 0.06 mLL; shape test (Δĥ free) secondary; estimators b, c and moment-K sensitivities; settlement rules unverified |
| I-049 | I-049 | E·η, E = 1[min(n_A, n_B) < 3] centred | single coefficient | + | x as is; tested + | 0.5 | none | M-set; Std; fitted jointly with B6 (BOD-C2, I-054) | nudge | f10_price_slopes | seen-2025/26 evidence; the rival BOD-C2 predicts the opposite sign |
| I-053 | I-053 | Δ[Fat·(age − 26)+], Fat τ = 3 days | single coefficient | − | x as is; tested − | 1 | slow | ΔFat, age, age_sq, sets_14d; ΣFat·η, Σa·η; Std | TabPFN diff column | f20_fatigue | the brief's own example |
| I-082 | I-082 | Δ(w̃_L·s_L): opponent-adjusted points form in low-visibility matches, w̃ = w/(w + 200 points) | single coefficient | + | x as is; tested + | 1 | none | adjperf_tpw_2w, nearest form_*, Δ(w̃_H·s_H), missing-lower-level flag; Std | TabPFN diff column | f12_salience | β_L > β_H secondary; lower-level box scores double in 2025 (covariate shift) |
| I-084 | I-084 | η·(ΣR − mean)/SD, ΣR = A's plus B's overall Elo | single coefficient | + | x as is; tested + | 0.5 | slow | M-set; η × level; Std; fitted jointly with I-036, B-FLB | nudge | f10_price_slopes | corr −0.70 with I-036; its TabPFN form is inside S2 |
| LIT-2 | LIT-2 | abs(η)·ΔF (s = sign(η)·ΔF), F = log(1 + titles + Slam QF or better), strictly earlier | single coefficient | + | x as is; tested + | 0.5 | slow | M-set; ΔF; Std; fitted jointly with B-REPUTE | nudge | f16_repute (to add) | opposite sign to I-083 (corr 0.50) |
| S2 | levels arm | 17 sums A + B as TabPFN context: 14 surface-IOS O/D, overall Elo, age, sets_14d | disjoint-seed encompassing (plan.md) | + | n/a (TabPFN arm) | 1 | slow (× 1.25) | as pre-registered | TabPFN context columns | levels | fixed 6 Oct 2026; t₁ and t₂ divided by √1.25 before the joint z, the filter and the replication (checkpoint 1 R-7); spans the spw sums (98%) |
| B-LEVER | I-001, I-006, κ_surf | η·κ_pair (within tour × surface); 1[bo5]·η; η·κ_surf (the surface-mean leverage) | Wald 3 df | ± | n/a (Wald) | 0.5 | slow | M-set; η·1[slam]; Std; fitted jointly with B-FLB, I-036 | nudge | f02_leverage (add κ_surf) | expected ≈ 0.01–0.03 (the close applies ≈ the damped leverage); sensitivities I-002, I-011, MEC-K2 |
| B-FLB | LIT-1, MAT-L1 | L·η, L = 1[not the event's first main-draw round]; HP·η, HP = 1[Slam or Tour Finals] | signed sum | + | +1, +1; tested + | 0.5 | none | M-set; Std; fitted jointly with I-036, I-084, B-LEVER | nudge | f10_price_slopes (to add) | Lahvička's other two slopes; round depth a sensitivity |
| B2 | I-012, I-013 | shield x = c_{A→B} − c_{B→A} (MEC-04, declared g); e_ace | signed sum | + | +1, +1; tested + | 0.5 | slow | iosO_ace, iosD_ace, prod_ace, ΔD^spw, τ_spw = O·D (MEC-L1); ΣD^spw·η, Σg·η, ΣO^ace·η, ΣD^ace·η; Std | TabPFN diff columns | f03_composition (KEEP_I012 = True) | contested (I-012's precheck look); e_df, e_hold sensitivities; exposed to ace faults |
| B3 | I-016, I-022 | ρ_A·D^sw_B − ρ_B·D^sw_A; O^sw_A(h̄ − h_B) − O^sw_B(h̄ − h_A) | Wald 2 df | ± | n/a (Wald) | 0.5 | fixed (height) | per member (round-1 cards); height permuted within tour | TabPFN diff columns | f04_second_serve | exposed to double-fault faults |
| B6 | I-033, BOD-L2, I-054 + BOD-C2 (as U_rest) | s·η with s = flux Σ(form − ℓ)²; Σabs(age − 28.5); U_rest = R² − mean, R = [std Σlog1p(rest) − std ΣFat]/√2 (standardised per tour on 2014–2021 rows) | signed sum | − | +1, +1, +1 (each an uncertainty measure); tested − | 1 | slow | M-set; R·η (the rest axis's linear slope, as an η-modulator control); ΔFat, Fat-imputed difference; Std; fitted jointly with I-049 | nudge | f13_uncertainty (update) | addendum: I-054 and BOD-C2 correlate −0.944, so both enter as one U-shaped member (flatter at both ends of the rest axis); I-028 dropped by its gate (split-half 0.041); I-034 withdrawn; I-029, I-030 dropped |
| B7 | I-023, I-031, I-032, I-048 | height-prior ace shift (+); re-anchored points form (+); ΔIOS_spw·r̄ (+); Δ[(1 − w)E_spw], Δ[(1 − w)F_spw] (−) | signed sum | declared per member | +1, +1, +1, −1, −1 (I-023, I-031, I-032, I-048 E, F); tested + | 1 | slow (× 1.25 gates; height P2 a diagnostic only) | unweighted ΔO^ace, Δh; form_s, Δℓ; ΔIOS, r̄·η; plain ΔE, ΔF; Std | TabPFN diff columns | f07_evidence_age | gates on the slow-trait widening × 1.25; P2 on height is computed and reported, never folded into p (checkpoint 1 R-6); CV(r) 0.584, CV(r̄) 0.176, height-ace 0.40 passed; a P3 sdev pass is read beside I-048 |
| B9a | I-024, I-058, I-061 | Δ[h·Fat] (−), Δ[h·(age − 28)+] (−); Δ[Trait·Fat] (+); Δ[Odo·(age − 27)+]·1[month ≥ 9] (−) | signed sum | declared per member | −1, −1, +1, −1 (I-024 h·Fat, h·age, I-058, I-061); tested + | 0.5 | slow (× 1.25 gates; height P2 a diagnostic only) | per member | TabPFN diff columns | f21_constitution | gates on the slow-trait widening × 1.25; P2 on height reported only (checkpoint 1 R-6); I-058 passed its split-half gate |
| B9b | I-063, I-065, I-066 | leverage-composed ΔFat (−); R_A·Fat_B − R_B·Fat_A (+); E_min·ΔFat (−) | signed sum | declared per member | −1, +1, −1 (I-063 oriented like ΔFat, I-065, I-066); tested + | 0.5 | slow | per member; ΔFat; Std | TabPFN diff columns | to build | κ, η, λ from serve- and return-point residuals (statistic targets) |
| B10 | I-059, I-088, I-060, I-074 | Run_A − Run_B; Δ(τ·first); Δ[Wk·(1 + 0.05(age − 28)+) + 0.1·Away]; jet lag from continent offsets | signed sum | − | −1, −1, −1, −1; tested + | 0.5 | none | component differences; sets_14d; Std | TabPFN diff columns | f23_arrival | continent map built (BOD-R2, R3) |
| B11 | I-051 (On), I-075, I-076 | ΔOn; Δ[OS·Nov], Nov = surface switch + indoor switch + continent change; r_A·c_B − r_B·c_A | signed sum | + | +1, +1, +1; tested + | 0.5 | none | per member; Std | TabPFN diff columns | f24_onsite | on-site count shared by the three columns |
| B-SWITCH | I-046, I-047, I-050 | Δ[q·shape]; Δ[New·Sty]·sgn(surface); Δ[New·(age − 28)]; Δ[In·Sty] | Wald 4 df | ± | n/a (Wald) | 0.5 | slow | per member; Std | TabPFN diff columns | f25_switch | both tours' indoor flag from the Court field |
| B-CLUTCH | I-026 (I-009, I-027 dropped by their gates) | r = z_C2 − z_C1 (remainder form); Δb·(β̄_c/β̂_AB); ΔR (resilience excess) | signed sum | + | +1 (I-026); tested + | 0.5 | slow | per member; Std | TabPFN diff columns | f08_clutch | gate drops recorded at checkpoint 1 §1.4 (I-009 split-half 0.160 / 0.270 < 0.3; I-027 −0.072 / −0.011 ≤ 0.1) |
| B-ANCHOR | I-037, I-038 | η·a (−); k·(2fam − 1) (+) | signed sum | declared per member | −1, +1; tested + | 0.5 | none | M-set; k; ΔF; Std | nudge | f14_anchor | [A]: no value at margin-free venues |
| B-RECAL | I-040, I-041 | r̄·adj; adj³ (adj = η − z) | Wald 2 df | ± | n/a (Wald) | 0.5 | none | adj; M-set; Std | nudge | f15_recal | corrects the model, not the market |
| B-INJ | I-043, I-044, I-045 | ΔRust (−); Δ(inj·1[L ≥ 56]·1[m ≤ 2]·e_pre) (−); ΔDec = −ΔTr (within-event serve decay) (−) | signed sum | − | −1, −1, −1 (ΔRust, inj·e_pre, ΔDec); tested + | 0.5 | none | per member; surf_layoff pairs; Std | TabPFN diff columns | to build | I-045 is ΔDec = −ΔTr, the mechanism's direction (checkpoint 1 R-5); the serve-speed variant is infeasible |
| B-VENUE | I-072 (+ I-077); I-073 dropped by its gate | v_e·ΔO^ace; I·(ΔG + ΔH) | signed sum | + | +1 (I-072); tested + | 0.5 | slow | ΔO^ace, v_e·η; I·η; Std | TabPFN diff columns | to build | I-073's split-season carry-over failed (≤ 0.124 < 0.15, checkpoint 1 §1.4); field solve needs clock and probe; I-072 carry-over 0.661 / 0.566 ≥ 0.3 |
| B-HOME | I-078, I-079 | ΔH·1[250 or 500]; Δ(home·wc) | Wald 2 df | ± | n/a (Wald) | 0.5 | fixed (country) | ΔH, Δwc; g·η; Std; country permuted within tour | TabPFN diff columns | f27_home | home as a main effect tied at the close |
| B-AGE | I-070 | Δ[(Short − Long)·h(age)], h = (25 − age)+ − 0.5(age − 30)+ | single coefficient | + | +1 (I-070); tested + | 0.5 | slow | form and IOS differences; age; Σh·η; Σ(S − L)·η; Std | TabPFN diff column | f07_evidence_age (KEEP_I068 = False) | I-068 and I-069 dropped by their gate |
| B-REPUTE | I-071, I-083, I-055 | Δ(g·a); Δ(F·R); sign(η)·abs(ΔFat) | signed sum | − | +1, +1, +1; tested − | 1 | slow | per member; abs(ΔFat)·η; Std; fitted jointly with LIT-2 | TabPFN diff columns or nudge | f16_repute | the price anchors on reputation that lags the state |
| B-INFO | I-080, C-2, INFO-2 | Δ1·(−A); (F − z)·O_min; s·Δ(w̃_q·s_q) | signed sum | + | +1, +1, +1; tested + | 1 | slow | Δ1, A·η; F − z, O_min·η; Δ(w̃_q·s_q), s·η, I-082 and I-076 columns; Std | TabPFN diff columns or nudge | f17_info (update) | I-081, I-087 withdrawn; Δ1 and F rescaled to the price's SD, no outcomes |
| B-OVERREACT | I-025, I-085, I-086, I-091 | ΔΛ (−); abs(r)·sign F (+); Δs·1[round ≥ QF] (−); raw H2H·1[n ≥ 3] (−) | signed sum | declared per member | −1, +1, −1, −1; tested + | 0.5 | none | per member; r for I-085; S11 missingness for I-086 | TabPFN diff columns or nudge | f18_overreact | β_f from the iid model or walk-forward |
| B-MOTIV | I-089, I-090 | Δtop·1[250/500]·1[Slam main draw ≤ 8 days]; Δpost | signed sum | − | +1, +1; tested − | 0.5 | slow | Δtop; s·η; Std | TabPFN diff columns | to build | Δdef deferred (no points table) |
| B-PREV | BOD-L1, I-056 | ΔPrevX (previous on-site match's extra sets, graded); Δ[PrevX·(1[rest ≤ 1] − 1[rest ≥ 2])] | signed sum | − | −1, −1; tested + | 1 | none | sets_14d, ΔFat, Δrest, missing-score flag; Std | TabPFN diff columns | f20_fatigue (update) | I-056's other Scare definitions are sensitivities |
| B-STATE | BOD-C1 | ΔPastFat (mean Fat over the player's own matches in the 14 days before) | signed sum | + | +1 (BOD-C1); tested + | 0.5 | none | ΔFat, sets_14d; nearest inputs recomputed by the module's rule (F-1); Std | TabPFN diff columns | to build | INFO-1 dropped by checkpoint 1 R-1 (its premise is false: the IOS state already counts the player's own matches); INFO-1 runs only as a descriptive sensitivity |
| B-LOAD | I-052, I-051 (Off) | ΔFat (τ = 3 days, minutes or imputed); ΔOff (its off-site part) | signed sum | − | −1, −1; tested + | 1 | none | sets_14d, surf_layoff pairs, imputed-minutes flag; Std | TabPFN diff columns | f20_fatigue (update) | Fit, ACWR (I-057), team ties (I-062) are sensitivities; the 12-day Masters change rest in 2023+ |

## Outside the family (pre-declared, not claims)

* **The sharp-anchor diagnostic** (C-1 with I-039), descriptive, in the batch.
  * s_PS beyond η.
  * η's gain against the calibrated Pinnacle close and against the calibrated average, on the same matches.
* **An optional M2 representation arm** (MAT-K1, spw-only). The orchestrator runs it only if GPU time allows.
* **Novelty diagnostics** (MAT-K2): b for s̃·η reported beside s·η.
* **Data quality** (MAT-R1): event-fault flags, and down-weighting as a robustness sensitivity of the new columns.
* **The final test's measurement items** (MAT-R2), in [rulings.md](rulings.md).
* **The P3 known-null placebos** of plan.md, unchanged.

## Changes from the round-1 family of 34

| Change | Rows |
|---|---|
| Removed as units | I-001 and I-006 (into B-LEVER); I-052 (into B-LOAD); I-056 (into B-PREV); B5 (its between-match member failed the rule) |
| Added | B-LEVER, B-FLB (LIT-1 + MAT-L1), LIT-2, B-PREV (BOD-L1 + I-056), B-STATE (INFO-1 + BOD-C1), B-LOAD (I-052 + I-051's Off) |
| New members | B6: I-028, BOD-L2, BOD-C2 in; I-034 out. B-INFO: C-2, INFO-2 in; I-081, I-087 out. B2: I-012 back in (contested) |
| Weights | I-001 1 → 0.5 (B-LEVER); B2 1 → 0.5; B-AGE 1 → 0.5 (I-070 alone); B6 0.5 → 1; B5's 2 gone; I-042 2 → 1 (addendum: its identifiable part is ≈ 0.06 mLL at most) |
| Primaries | I-008 → z_spw remainder; I-042 → τ without a Δh control; I-085 → abs(r)·sign F; I-086 with S11 |
| Dropped by result-free gates | I-029, I-030, I-068, I-069 |
| Withdrawn by originators | I-034, I-081, I-087 |
| Retired or killed | I-007 retired; MEC-K1 killed (e) |
| Checkpoint 1 (7 Oct) | B4 dropped (all three members failed their pre-declared gates). B-STATE = BOD-C1 alone (INFO-1 out, R-1). I-045 written as ΔDec = −ΔTr (R-5). B7 and B9a gate on × 1.25, with height P2 a diagnostic (R-6). H-S2 widened × 1.25 (R-7). Gate drops shown in B-CLUTCH and B-VENUE. The multipliers column is added (F-4). No weight or test changed |
