# Math audit · family 02 · Composition through the point model

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md); notation as in [family 01](01_serve_dominance_leverage_format.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-008 | pass | 2 | stand-alone; I-010, I-014, I-015 its sensitivities or decomposition |
| I-009 | refine | 0.5 | block B-CLUTCH |
| I-010 | refine | – | damped sensitivity of I-008 |
| I-011 | refine | – | sensitivity of I-001 (identical to first order) |
| I-012 | refine | 1 | block B2 (free points and ace curvature) |
| I-013 | refine | 1 | block B2, e_ace only |

### I-008 · The surface-IOS profile composed into a match log-odds
- type_basis: C: z_C1 = logit P_iid(p_AB, p_BA; format, deciding-set rule), p = fi·fw + (1 − fi)·sw from the surface IOS. Merge MEC-05 + MAT-C1 confirmed (identical formula; the residual variants are control choices)
- swap_ok: yes (tested on the proxy)
- redundancy: not an identity; corr 0.92 with ratings_iid and elo_games (computed). Contains the cross-statistic exposure of I-014/I-015 and part of I-001's leverage (residual corr 0.21 with I-001)
- novelty_r2: 0.98 on the 58 (men 0.978, women 0.992); residual SD 0.21 (men) and 0.10 (women) match log-odds
- effect_bound_mll: ≈ 0.10 central (sum-dependent hidden part RMS 0.14 men / 0.10 women, damped by c, half priced, reliability ≈ 0.5); upper 0.8–1.35 men if the price ignored composition (MAT A6, checked)
- mde_mll: 0.12 (w 2)
- controls: C: the six component differences (ΔO, ΔD of fi, fw, sw); ratings_iid; ios_points_short; Std
- trait: slow
- sign: + (beyond its linear part)
- deployment: TabPFN difference column; nudge if capture < 0.5
- verdict: pass
- weight: 2
- kill_reason: 
- fix: primary = z_C1 (undamped); sensitivities: the damped composition (I-010), the residual on ratings_iid (MAT) and MEC's x_res. G2 should judge this C column by its residual SD in log-odds (0.21 / 0.10, against the ≈ 0.03 a 0.09 mLL term needs), not by R² < 0.95, or test the residual itself (identical by Frisch–Waugh)
- notes: MEC's "99.7% linear" is the serve-point edge, not the match log-odds; the match level adds the pair's leverage, which differences cannot carry

### I-009 · Games route and the points-versus-games residual
- type_basis: C (X): r = z_C2 − z_C1 (hold IOS composed through sets minus the points route)
- swap_ok: yes
- redundancy: d logit hold / d logit p is 2.50–2.99, near-linear (W-11), so most of r is a linear combination of existing hold and component inputs; the new part is set- and match-level
- novelty_r2: to compute (needs the set-level hold composition)
- effect_bound_mll: ≤ 0.1 (prior); central ≈ 0.02 (persistent return big-point skill: Slam split-half 0.21 / 0.19)
- mde_mll: block B-CLUTCH (0.16 at w 0.5)
- controls: z_C1 (I-008); hold differences; prod_hold; Std
- trait: slow
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-CLUTCH (with I-026, I-027); keep the originator's result-free precheck (split-half reliability of the per-player hold residual ≥ 0.3, 50+ matches a half) as its G2 gate
- notes: clutch family mostly priced (PD stage 4 onM ties; MA conversion luck tie), but those rows are HIST or seen-2025/26, so not an (e) kill

### I-010 · Noise-integrated composition
- type_basis: C: z_C4 = logit E_u[P_iid]; at fixed pair dominance and format a monotone transform of z_C1
- swap_ok: yes
- redundancy: I-008 up to a pair- and format-dependent monotone rescaling; its distinct content is the dominance-dependent damping (I-001's territory)
- novelty_r2: as I-008
- effect_bound_mll: ≤ 0.05 beyond I-008
- mde_mll: n/a
- controls: as I-008
- trait: slow
- sign: +
- deployment: sensitivity of I-008
- verdict: refine
- weight: –
- kill_reason: 
- fix: fold into I-008 as its damped sensitivity; V from Stage 3's over-dispersion moments (statistics, 2013–2018), never tuned on outcomes, so nothing is read while it is built
- notes: its diagnostic role duplicates I-007

### I-011 · The price on the point scale
- type_basis: C × M: d_pt = Δ_prof − Λ⁻¹(z; m_pair, format). Since Λ⁻¹(z; m) ≈ z/β_L(m), given Δ_prof and the M-set its novel part is ∝ z·κ_pair, which is I-001 with the opposite sign
- swap_ok: yes
- redundancy: identical to I-001 to first order
- novelty_r2: as I-001
- effect_bound_mll: ≤ 0.05 (originator), within I-001's
- mde_mll: n/a
- controls: as I-001
- trait: slow
- sign: − on d_pt (= + on I-001)
- deployment: sensitivity of I-001
- verdict: refine
- weight: –
- kill_reason: 
- fix: fold into I-001 as a sensitivity (the originator: do not screen unless C1 passes)
- notes: 

### I-012 · Free-point shield
- type_basis: C / X: x = c_{A→B} − c_{B→A} = ½[Δg·ΣD^spw − Σg·ΔD^spw] + curvature (g = the shield's elasticity shortfall)
- swap_ok: yes (tested)
- redundancy: 94% linear in the 21 IOS inputs per tour (computed 0.94; originator 94%); nearest iosD_ace +0.79, prod_ace +0.71
- novelty_r2: 0.90 on the 58 pooled (0.94 per tour); residual SD 0.012 serve-point logit (men) ≈ 0.06 match log-odds
- effect_bound_mll: ≤ 0.2 men if the remainder were true and unpriced; central ≈ 0.03
- mde_mll: block B2 (0.14 at w 1)
- controls: ΔO^ace, ΔD^spw (via the IOS inputs), ΣD^spw·η, Σg·η, prod_ace, Std
- trait: slow
- sign: + (favours big servers against strong returners)
- deployment: TabPFN difference column
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B2 with I-013's e_ace (nearly orthogonal: corr 0.09); the statistic-level precheck (does return elasticity fall with the server's ace share?) uses serve points only and is result-free
- notes: rich arm (returns in play) is thin before 2022: sensitivity only

### I-013 · Within-player squares that complete prod_s
- type_basis: W (S-form): sq_s = ΔO_s·ΣO_s − ΔD_s·ΣD_s; e_s ≈ linear + ½σ″(μ)(sq_s + 2·prod_s), so given the linear and prod controls e_s and sq_s test the same second-order term
- swap_ok: yes (tested)
- redundancy: computed R² on the 58: e_ace 0.88, e_df 0.95, e_hold 0.97, e_first_won 0.99; only e_ace is clearly novel
- novelty_r2: 0.88 (e_ace)
- effect_bound_mll: ≤ 0.05 (aces enter the match only through serve points); central ≈ 0.02
- mde_mll: block B2
- controls: ΔO_ace, ΔD_ace, prod_ace, ΣO_ace·η, ΣD_ace·η, Std
- trait: slow
- sign: + (favours the extreme server)
- deployment: TabPFN difference column; its TabPFN form is also inside S2 (the ace sums)
- verdict: refine
- weight: 1
- kill_reason: 
- fix: one column, e_ace, in block B2; e_df, e_hold, e_first_won are sensitivities (they fail G2 novelty)
- notes: 
