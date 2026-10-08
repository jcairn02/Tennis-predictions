# Math audit · family 07 · Reliability, evidence and uncertainty

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-031 | refine | 1 | block B7 (thin evidence, reliability) |
| I-032 | refine | 1 | block B7 |
| I-033 | refine | 0.5 | block B6 (transient uncertainty flattens the price) |
| I-034 | refine | 0.5 | block B6 |

**A general bound for reweighting ideas (MAT's κ² rule, checked).** Rescaling the model's adjustment (RMS ≈ 0.1 logit) by a factor with RMS κ across matches is worth ≈ κ² mLL. Reliability weights with a coefficient of variation c recover about c² of the reweighted signal's own value. With c ≈ 0.17–0.5 and signals worth 0.3–1 mLL beyond the price, each such column is worth ≤ 0.05–0.1: block material.

### I-031 · Re-anchor the two-week form on the long-memory level
- type_basis: U (W): Δform* = Δ[ℓ + r(raw − ℓ)]; given Δraw and Δℓ, the new part is Δ[(1 − r)·ℓ] − Δ[(1 − r)·raw] = ½[Δ(1 − r)·Σ(ℓ − raw) + Σ(1 − r)·Δ(ℓ − raw)]
- swap_ok: yes
- redundancy: r is not an input; surf_season pairs are a partial proxy
- novelty_r2: to compute (needs Stage B's decayed weights)
- effect_bound_mll: ≈ CV(r)² × the form's orthogonal value (0.3–0.5): ≈ 0.02–0.1
- mde_mll: block B7: 0.14 (w 1)
- controls: the existing form_s; Δℓ; Σ(raw − ℓ)·η; Σr·η; Std
- trait: none (recent state)
- sign: +
- deployment: TabPFN difference column (beside form_s)
- verdict: refine
- weight: 1
- kill_reason: 
- fix: one composite column (re-anchored adjperf_tpw, the points form) in block B7; the 16 per-statistic columns are sensitivities. Precheck CV(r) ≥ 0.2 (result-free)
- notes: MAT's +0.1 to +0.4 is optimistic against its own κ² rule

### I-032 · Unknown is not average: the evidence behind each IOS value
- type_basis: U: s = r̄ (harmonic mean of n/(n + K)), d = ΔIOS ✓
- swap_ok: yes (tested)
- redundancy: computed: r̄ (K = 20 surface matches) has R² 0.69 on the 58 through the surf_season pairs; ΔIOS·r̄ has R² 0.07
- novelty_r2: 0.07
- effect_bound_mll: computed CV(r̄) 0.17 (men), 0.18 (women), just above the originator's 0.15 kill line: ≈ 0.03 by the κ² rule
- mde_mll: block B7
- controls: the unweighted ΔIOS (iosO, iosD); r̄·η; Std
- trait: none
- sign: +
- deployment: TabPFN pair (n_A, n_B) or the weighted difference
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B7 with ΔIOS = the spw total (O + D) difference; K fixed now at 20 surface matches (a constant, not tuned); the pair form is a sensitivity
- notes: W-13's warning (Stage 3 posterior variances nearly uniform) is borne out only partly: evidence counts vary more (p10 0.64, median 0.88)

### I-033 · Flux: when short and long memory disagree
- type_basis: U × M: s = F_pair = Σ(form − ℓ)², d = η ✓
- swap_ok: yes
- redundancy: TabPFN could form a function of form and IOS differences, never this sum of squares
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.1 (MAT); an extra 0.04 logit² of variance flattens the odds ≈ 6%, so ≈ 0.02 typical
- mde_mll: block B6: 0.16 (w 0.5)
- controls: M-set; Std
- trait: none
- sign: −
- deployment: nudge
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B6; fix "form" = adjperf_tpw_2w and ℓ = the long-memory points level, both on one scale; the originator's feature-only gate (≥ 5% of matches with flux variance > 0.03) stays
- notes: 

### I-034 · Conflict shrinkage: statistics and ratings disagree
- type_basis: U, M: s = abs(Δ1) (centred), d = η; Δ1 = points view − results view
- swap_ok: yes (tested)
- redundancy: Δ1 is built from two inputs; computed R² of z·abs(Δ1) on the 58 is 0.13 (0.22 with the M-set)
- novelty_r2: 0.13
- effect_bound_mll: ≈ 0.01–0.03 (a disagreement of 0.5 logit implies ≈ 1–2% flattening); originator 0.05–0.2
- mde_mll: block B6
- controls: M-set; Δ1 (main effect); Std. abs(Δ1) alone is not a regressor (symmetric)
- trait: none
- sign: −
- deployment: nudge
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B6. Rescale the two views result-free (each to the price's SD within tour, as computed here, or by regressing the price on each view on 2013–2018); the walk-forward outcome calibration of the original reads results
- notes: 
