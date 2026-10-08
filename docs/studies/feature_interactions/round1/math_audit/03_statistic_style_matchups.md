# Math audit · family 03 · Style matchups between specific statistics

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md); notation as in [family 01](01_serve_dominance_leverage_format.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-014 | refine | – | descriptive decomposition of I-008 |
| I-015 | refine | – | descriptive decomposition of I-008 |
| I-016 | refine | 0.5 | block B3 (second-serve style) |
| I-017 | kill | – | (b) a rotation of existing inputs |
| I-018 | refine | 0.5 | block B4 (matchup-specific deviations) |
| I-019 | refine | 0.5 | block B4 |
| I-020 | kill | – | (c) flagged: serve-speed coverage |

### I-014 · Second-serve exposure × the returner's second-serve specialisation
- type_basis: X: x ∝ E_B·c_A − E_A·c_B = −½[ΔE·Σc − ΣE·Δc] ✓
- swap_ok: yes (tested)
- redundancy: inside I-008's composition (its first-order cross term); corr 0.56 with I-015
- novelty_r2: 0.49 on the 58; residual SD 0.004 serve-point logit ≈ 0.02 match log-odds
- effect_bound_mll: ≤ 0.02
- mde_mll: n/a
- controls: as I-008
- trait: slow
- sign: +
- deployment: none (interpretation of I-008)
- verdict: refine
- weight: –
- kill_reason: 
- fix: report as a pre-declared descriptive decomposition of I-008 if I-008 passes; no slot
- notes: 

### I-015 · Second-serve exposure against second-serve return
- type_basis: X: E_2 = (1 − fi_AB)(1 − sw_AB) − (1 − fi_BA)(1 − sw_BA), a product of two expit matchups
- swap_ok: yes (tested)
- redundancy: R² 0.995 on the 58 (computed): fails G2 novelty
- novelty_r2: 0.995 (residual SD 0.003)
- effect_bound_mll: ≤ 0.01
- mde_mll: n/a
- controls: as I-008
- trait: slow
- sign: − on E_2 (A's second-serve points lost)
- deployment: none
- verdict: refine
- weight: –
- kill_reason: 
- fix: descriptive decomposition of I-008 only (its originator: "dies with C1")
- notes: 

### I-016 · Risky second servers against second-serve attackers
- type_basis: X: ρ_A·D^sw_B − ρ_B·D^sw_A = ½[Δρ·ΣD^sw − Σρ·ΔD^sw] ✓
- swap_ok: yes (tested)
- redundancy: nearest iosO_df +0.50, form_df +0.44; corr 0.08 with I-015
- novelty_r2: 0.69 (men 0.84, women 0.60)
- effect_bound_mll: ≤ 0.05
- mde_mll: block B3 (two-sided, 0.17)
- controls: ΔO^df, ΔO^sw, ΔD^sw, Σρ·η, ΣD^sw·η, prod_df, prod_second_won, Std
- trait: slow
- sign: two-sided (undeclared)
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B3 with I-022 (2-df Wald, two-sided); keep the statistic-level precheck (residuals of second-serve points and double faults on ρ × D^sw) as its G2 gate
- notes: 

### I-017 · Total strength against style difference (structural null)
- type_basis: linear rotation: ΔT_s = iosO_s + iosD_s, ΔY_s = iosO_s − iosD_s; no modulator
- swap_ok: yes
- redundancy: an identity with existing inputs up to a linear map: R² = 1 on the 58 by construction, and after its own nearest-input controls (its two components) nothing is left to test
- novelty_r2: 1.00
- effect_bound_mll: 0 as a new column
- mde_mll: n/a
- controls: n/a
- trait: slow
- sign: n/a
- deployment: none
- verdict: kill
- weight: –
- kill_reason: (b) identical to a linear map of existing inputs (iosO_s, iosD_s). Supporting (e): IOS style and the 21 IOS columns tied linearly with the odds (UFC stage D style −0.03 / +0.02; MT §7 −0.16 / −0.15)
- fix: the structural prediction (ΔY carries nothing given the price under iid) may be reported once, after M1, as a descriptive diagnostic outside the family
- notes: the "ΔY composite" weights were never specified

### I-018 · Style-pair residual table
- type_basis: X (categorical): τ_{s(A)s(B)} − τ_{s(B)s(A)}, k = 6 frozen styles
- swap_ok: yes
- redundancy: a style pair needs both players' levels; partly carried by prod_s; hand is a clustering input (overlap I-021)
- novelty_r2: to compute (needs the τ table)
- effect_bound_mll: ≤ 0.05 (originator)
- mde_mll: block B4 (0.16 at w 0.5)
- controls: style-indicator differences; the clustering inputs' differences; Std
- trait: slow (styles) and field (τ)
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B4; τ from serve-point residuals of matches finished before es (clock and probe); the 2010–2016 vs 2017–2021 cell-by-cell stability (corr ≥ 0.3) is a result-free G2 gate
- notes: literature: intransitivity does not beat Pinnacle (Clegg and Cartlidge v2)

### I-019 · Points-based head-to-head residual
- type_basis: pair-specific d: r_AB = Σ_k(u^A_k − u^B_k)/(Σ points + 1,000)
- swap_ok: yes
- redundancy: no pair input exists; results-form head-to-head tied or worse at the close (PD stage 4, five forms, one design)
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.02 (about 60% of matches have a meeting)
- mde_mll: block B4
- controls: IOS spw differences; missing-meeting indicator × η; Std
- trait: none (pair history)
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B4; the meeting-to-meeting persistence check (pairs with ≥ 3 meetings, corr ≥ 0.05) is a result-free gate
- notes: 

### I-020 · Lost first-serve speed × the returner
- type_basis: X: s_A·D^spw_B − s_B·D^spw_A = ½[Δs·ΣD^spw − Σs·ΔD^spw] ✓
- swap_ok: yes
- redundancy: none
- novelty_r2: n/a
- effect_bound_mll: n/a (coverage)
- mde_mll: n/a
- controls: n/a
- trait: none
- sign: −
- deployment: none
- verdict: kill
- weight: –
- kill_reason: (c) flagged for the feasibility auditor: serve speeds cover 12% of men's 2013–2021 matches (11–25% a season; inventory §4.6), below G2's 50% and the originator's own 30% floor
- fix: revisit when speeds cover the discovery years; the brief's men's-serve-speed lead stays a 2022+ question
- notes: seen-2025/26 evidence (shot level, 2022–2026)
