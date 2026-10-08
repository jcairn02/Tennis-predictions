# Math audit · family 01 · Serve dominance, leverage and format

Round 1, mathematical auditor, 6 Oct 2026. Research evidence, not a decision. Keys, the value rule and the MDE table are in [the summary](../math_audit.md). η = the current best's out-of-sample log-odds (the screen's offset), z = the de-vigged close; M-set = η, η³, η·abs(η) per tour; Std = the 1–3 nearest inputs plus missingness. Numbers marked *computed* come from `src/eda/feature_interactions/round1/math_audit/` (seasons ≤ 2021, no result read).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-001 | pass | 1 | stand-alone; I-002, I-011 its sensitivities, I-003 its modulator |
| I-002 | refine | – | sensitivity of I-001 |
| I-003 | refine | – | covered by the S2 levels arm; I-001's modulator |
| I-004 | refine | – | covered by the S2 levels arm |
| I-005 | refine | – | covered by the S2 levels arm; process flag (two-orientation training) |
| I-006 | refine | 0.5 | stand-alone format slope, two-sided |
| I-007 | refine | – | post-M1 descriptive diagnostic; no gating role |

### I-001 · Price × the pair's serve-dominance leverage
- type_basis: M × S: s = κ_pair = β_L(μ_pair)/β_L(μ_cell) − 1 (centred within tour × surface), d = η (z in the price version). Merge MEC-01 + MAT-M1 confirmed (same column up to a per-cell constant)
- swap_ok: yes (s sym, d anti; tested on the proxy)
- redundancy: none algebraic; κ is a pair sum, uncorrelated with every difference. ratings_iid and ios_points_short hold the pair's dominance only inside composed values
- novelty_r2: 0.27 on the 58 (computed, z·κ)
- effect_bound_mll: ≤ 0.10 pooled if wholly unpriced (men 0.07–0.19, women 0.01–0.03, damped); ≈ 0.03 if half priced
- mde_mll: 0.14 (w 1); men-only mechanism, so men must reach about 0.29
- controls: M-set; η × surface × tour (cell slopes, so only within-cell dominance identifies b); Std (prod_bp_saved, prod_first_won); NOT κ·η as a separate control (it is the candidate)
- trait: slow (modulator from long-memory IOS)
- sign: + on η·κ (b ≈ c², 0.5–0.75, if the price ignores dominance)
- deployment: nudge (S1); the TabPFN context form (m_pair) is covered by the S2 levels arm
- verdict: pass
- weight: 1
- kill_reason: 
- fix: use MAT's normalisation (κ against the cell's mean-dominance leverage); I-002 (comp, and its z × D) and I-011 are pre-declared sensitivities, not hypotheses
- notes: computed RMS κ within cell 6.5% men, 2.6% women (MAT 7.1%, 2.8%); value 500·E[w z²]·κ² = 0.33 men undamped, × c⁴. Correlates 0.21 with I-008's residual: report both

### I-002 · Serve-dominance compression of the rating gap
- type_basis: S: s = D = p_a + p_b − 2μ, d = g = p_a − p_b (IOS spw gap); secondary z × D is I-001 on the probability scale (a monotone transform of the same modulator)
- swap_ok: yes
- redundancy: corr 0.82 with I-001's column; R² 0.80 on the 58 + z·κ (computed). Given the M2 control D·η (≈ I-001), the identifiable part is D·(g − bη), a dominance-rescaled disagreement
- novelty_r2: 0.36 on the 58; 0.80 with I-001's column added
- effect_bound_mll: ≤ 0.01 beyond I-001 (κ² rule on the IOS–forecast disagreement)
- mde_mll: n/a (no slot)
- controls: as I-001
- trait: slow
- sign: + on comp
- deployment: sensitivity of I-001
- verdict: refine
- weight: –
- kill_reason: 
- fix: fold into I-001 as a pre-declared sensitivity (comp in place of η·κ); the kill test "vanishes with z × surface" is built into I-001's cell-slope controls
- notes: [I] anchor class (market lens)

### I-003 · Pair serve dominance and tiebreak share as context
- type_basis: context s only (m_pair, tb_share); no hypothesis of its own: a symmetric column has no main effect in the antisymmetric, intercept-free screen
- swap_ok: yes (context)
- redundancy: m_pair is 98% linear in the S2 levels arm's 14 IOS sums plus cell dummies (computed); tb_share is a monotone function of m_pair at even strength
- novelty_r2: 0.04 on the 58 (context); 0.98 on S2's columns
- effect_bound_mll: only through products: I-001's
- mde_mll: n/a
- controls: n/a
- trait: slow
- sign: n/a
- deployment: modulator of I-001; TabPFN form inside S2
- verdict: refine
- weight: –
- kill_reason: 
- fix: no separate slot; I-001 is its screen product and S2 its TabPFN arm
- notes: the originator's kill test (a 2019–2021 TabPFN arm) would read results before M1; drop it

### I-004 · Four point-structure sums as context
- type_basis: context s (σ1 = ΣO^spw, σ2 = ΣD^spw, σ3 = ΣO^ace, σ4 = ΣO^fi); acts through Δx·σk
- swap_ok: yes (context)
- redundancy: σ3, σ4 are S2 columns; σ1, σ2 are 98% linear in S2's 14 IOS sums (computed)
- novelty_r2: ≥ 0.98 on S2's columns
- effect_bound_mll: bounded by S2's
- mde_mll: n/a
- controls: n/a
- trait: slow
- sign: n/a
- deployment: S2 levels arm
- verdict: refine
- weight: –
- kill_reason: 
- fix: covered by the adopted S2 arm; the 84-column ridge proxy is not a pre-declarable test and is dropped
- notes: 

### I-005 · Serve-point offence and defence as exchanged pairs
- type_basis: pair (O^spw_A, O^spw_B), (D^spw_A, D^spw_B) = an invertible map of (Δ, Σ)
- swap_ok: yes (pair)
- redundancy: Σ parts 98% linear in S2's sums; Δ parts close to linear in the IOS inputs
- novelty_r2: ≥ 0.98 (sums on S2)
- effect_bound_mll: bounded by S2's
- mde_mll: n/a
- controls: n/a
- trait: slow
- sign: n/a
- deployment: S2 levels arm
- verdict: refine
- weight: –
- kill_reason: 
- fix: covered by S2; forward its process suggestion (train TabPFN on both orientations) to the orchestrator as a harness question, not a hypothesis
- notes: two-orientation training would change the base model itself; it needs its own decision

### I-006 · Best-of-five leverage the price under-transmits
- type_basis: as written S: s = 1[bo5], d = u − v; computed u − v ≈ 0.243·ratings_iid on Bo5 rows (corr 0.994), so L ≈ 1[bo5] × an existing input. Corrected: the mechanism's column is s·η (a format slope)
- swap_ok: yes
- redundancy: L has R² 0.99 on the 58 + 1[bo5]·z + 1[bo5]·ratings_iid (computed); what is left (SD 0.054 on Bo5 rows) is worth ≤ 0.03 mLL
- novelty_r2: L 0.33 on the 58; 0.99 with its M2 controls
- effect_bound_mll: format slope ≤ 0.09 if the price applied Bo3 leverage (κ ≈ 0.1 on 9.8%); prior ≈ 0.04 (thinking study, seen)
- mde_mll: 0.17 two-sided; in-subgroup about 1.7
- controls: M-set; η·1[slam] (separates format from event level); Std
- trait: none
- sign: two-sided: computed, the close applies a Bo5/Bo3 log-odds ratio of 1.19–1.27 at matched ratings (≈ the iid 1.25, above the damped 1.10–1.13), while Stage 1's outcome hint points the other way
- deployment: nudge (calibration slope modifier)
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: test x = 1[bo5]·η (price version 1[bo5]·z), two-sided; L itself becomes a descriptive sensitivity
- notes: seen-2025/26 evidence (Stage 1 2013–2026, thinking study 2022–2026): screen, but the final test cannot confirm it. Subgroup 9.8% (S8)

### I-007 · Bo5 damping check (diagnostic)
- type_basis: diagnostic (no column): ratio of logistic slopes of results on ratings_iid, Bo5/Bo3
- swap_ok: n/a
- redundancy: n/a
- novelty_r2: n/a
- effect_bound_mll: n/a
- mde_mll: n/a
- controls: n/a
- trait: n/a
- sign: n/a
- deployment: none
- verdict: refine
- weight: –
- kill_reason: 
- fix: it reads results, so it cannot gate anything before M1. Weights now carry both the damped and the undamped bound; the price-only substitute is computed (market ratio 1.19–1.27). Run the original once, after M1, in the screen's batch, as a registered descriptive row that cannot change any frozen weight, sign or hypothesis
- notes: one look-ledger row when it runs
