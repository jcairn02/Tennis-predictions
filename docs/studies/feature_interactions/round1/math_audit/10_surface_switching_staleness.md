# Math audit · family 10 · Surface switching and profile staleness

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-046 | refine | 0.5 | block B-SWITCH |
| I-047 | refine | 0.5 | block B-SWITCH (style and age columns) |
| I-048 | refine | 1 | block B7 (thin evidence, reliability); tested beyond the plain deviations |
| I-049 | pass | 0.5 | stand-alone slope |
| I-050 | refine | 0.5 | block B-SWITCH |

**On I-048 and the known-null placebos.** I-048's new part is Δ[(1 − w)·E], where E is the surface deviation that the surface-IOS study's R2 arm (`sdev`, planned as a P3 known null) enters plainly. Computed on the spw deviation: corr 0.63 with the plain ΔE, and R² 0.45 on the 58 inputs plus the plain ΔE, so 55% of it is new. It is not an identity. It must be tested beyond the plain ΔE and ΔF (its U-type control), and the meta-auditor should read a P3 "pass" of `sdev` together with I-048's result, since the two are correlated by construction.

### I-046 · Early in a surface season, return-heavy profiles are stalest
- type_basis: W / U: Δ[q·shape] = ½[Δq·Σshape + Σq·Δshape], q = 1[n_surf_season < 3] (fixed now; the source left the threshold open), shape = (D^spw − D̄_c) − (O^spw − Ō_c)
- swap_ok: yes (tested)
- redundancy: nearest iosO_ace −0.31, prod_hold +0.31; corr 0.03 with I-068
- novelty_r2: 0.21
- effect_bound_mll: ≤ 0.05; prior: the surface study's early-season subgroup did not replicate (+0.42, then +0.05, a tie; seen)
- mde_mll: block B-SWITCH: 0.17 (two-sided block)
- controls: ΔO^spw, ΔD^spw (via the IOS inputs); surf_season pairs; Σq·η; Σshape·η; Std
- trait: none (switch state) × slow (shape)
- sign: two-sided (undeclared; staleness and transfer predict different directions)
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-SWITCH (Wald, two-sided)
- notes: early-season subgroup about 24% of matches

### I-047 · Surface-switch adaptation by style and by age
- type_basis: W: Δ[New·Sty] and Δ[New·(age − 28)], New = exp(−n/ν)·log(1 + layoff/30), ν = 2 fixed now
- swap_ok: yes (tested)
- redundancy: nearest iosO_ace +0.20 (style), age +0.25 (age)
- novelty_r2: 0.10 (style), 0.10 (age)
- effect_bound_mll: 0.05–0.2 (originator); central ≈ 0.02 each
- mde_mll: block B-SWITCH
- controls: ΔSty, Δage, surf_season and surf_layoff pairs, ΣNew·η, ΣSty·η, Σage·η, Std
- trait: none × slow
- sign: the style column's sign flips by surface (grass: servers adapt; clay: returners): use Sty·sgn_surface (+1 grass, −1 clay, 0 hard) with sign +; the age column two-sided
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: two columns in block B-SWITCH; the surface-signed style term is the stated three-way hypothesis
- notes: switch main effects tie at the close (SEP S1, ✗ design years; SEP §5)

### I-048 · A stale surface profile: reliability by surface layoff
- type_basis: U: Δios* = Δios − Δ[(1 − w)·E], new part Δ[(1 − w)·E] = ½[Δ(1 − w)·ΣE + Σ(1 − w)·ΔE], w = n/(n + 10)·exp(−layoff/180) (constants fixed now)
- swap_ok: yes (tested)
- redundancy: see the box above (55% new beyond the plain deviation); nearest elo_surf_offset +0.32
- novelty_r2: 0.23 (E), 0.25 (F); 0.45 with the plain ΔE added
- effect_bound_mll: ≤ 0.05 (the deviations themselves are priced: SI §3.7, ✗ design years)
- mde_mll: block B7: 0.14 (w 1)
- controls: the plain ΔE, ΔF (U-control); iosO, iosD; Std
- trait: none × slow
- sign: − on Δ[(1 − w)·E] (if the model over-trusts stale deviations)
- deployment: TabPFN difference columns (O and D) beside iosO/iosD
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B7 with two columns built on the spw deviation (E_spw, F_spw); the 14 per-statistic versions are sensitivities
- notes: its weight n/(n + k) is I-032's r

### I-049 · Early-surface-season under-confidence of the price
- type_basis: M × S: s = E − Ē, E = 1[min(n_A, n_B) < 3] (24% of matches, computed), d = η
- swap_ok: yes (tested)
- redundancy: TabPFN holds every piece (surf_season pairs, odds_logit) but learned no context dependence; corr −0.37 with I-054's column
- novelty_r2: 0.04
- effect_bound_mll: ≈ 0.14 if market anchoring's observed slopes hold (1.15 early vs 1.06, seen; 79κ²·share); central ≈ 0.04 (the joint context-slope test tied, +0.12 [−0.08, +0.32], 2019–25)
- mde_mll: 0.16 (w 0.5)
- controls: M-set; I-054's column in the same fit; Std. Not E alone (no main effect) and not E·η (it is the candidate)
- trait: none
- sign: +
- deployment: nudge (slope modifier)
- verdict: pass
- weight: 0.5
- kill_reason: 
- fix: the graded E′ and the per-surface split are sensitivities
- notes: contested: two seen designs tied (MA joint slopes; SEP odds × both players new), one hint (MA +0.31 on top of profile and context, 2019–26). Seen-2025/26 evidence: screen, but the final test cannot confirm it

### I-050 · Indoor/outdoor switch × serve style
- type_basis: W / S: Δ[In·Sty], In = 1[the previous match had the other indoor status]·exp(−n_recent/ν)
- swap_ok: yes
- redundancy: indoor is a men-only context input; women's indoor exists in tennis-data's Court field (100%, inventory §4.3)
- novelty_r2: to compute (needs the previous match's indoor status)
- effect_bound_mll: 0.02–0.1 (originator); central ≈ 0.01
- mde_mll: block B-SWITCH
- controls: ΔSty, ΔIn, ΣIn·η, ΣSty·η, Std
- trait: none × slow
- sign: + (servers gain indoors)
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-SWITCH; take both tours' indoor status from tennis-data's Court field
- notes: autumn-only mechanism
