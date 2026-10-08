# Math audit · family 09 · Retirement, injury and settlement

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-042 | pass | 2 | stand-alone; merge kept, one primary estimator fixed before M1 |
| I-043 | refine | 0.5 | block B-INJ |
| I-044 | refine | 0.5 | block B-INJ |
| I-045 | refine | 0.5 | block B-INJ (box-score form only) |

**Ruling on the I-042 merge.** The three sources estimate the same per-player quantity, the hazard that the player fails to complete this match; the column τ is one fixed function of (h_A, h_B, p). So the estimator is not part of the column and the merge stands as one hypothesis. But the estimators are not mere constants: (c) adds state variables (Fat, load ratio, best of, month) that overlap the load family. One primary must therefore be fixed before M1 by a price-free target: out-of-sample log loss on the retirement label itself, walk-forward on 2013–2018 (a "statistic" target under M5; one ledger row). The other two become sensitivities that cannot rescue a failed primary.

### I-042 · Retirement hazard × price
- type_basis: W × M, exact: τ = h_B/p − h_A/(1 − p) = −Δh·(1 + cosh z) − Σh·sinh z (checked against the synthesizer's form); an S-term (modulator 1 + cosh z, convex weight on the favourite's hazard) plus the pair's total hazard × an odd function of the price
- swap_ok: yes
- redundancy: no retirement input; the label-composition algebra P(A advances) = (1 − h_A − h_B)·P_c + h_B is exact
- novelty_r2: to compute (needs Stage 0 status histories)
- effect_bound_mll: ½σ_h²·E[2 cosh z]: E[2 cosh z] = 3.63 (men), 3.13 (women), computed; σ_h = 0.5 / 1 / 2 pp → 0.05 / 0.18 / 0.73 (men). Realistic 0.05–0.2
- mde_mll: 0.12 (w 2); × 1.25 if the hazard behaves as a slow trait
- controls: Δh (the linear hazard difference); M-set; Std. NOT Σh·η: the Σh·sinh z part is the hypothesis
- trait: slow (persistent hazard) with a state part (recent retirement)
- sign: + (coefficient = the share of retirement risk the close leaves out; 1 if every book voids)
- deployment: nudge (the exact functional form); a TabPFN column is a sensitivity
- verdict: pass
- weight: 2
- kill_reason: 
- fix: weight rule fixed now and applied before M1 from MAT's result-free precheck: de-noised persistent hazard SD ≥ 1 pp → 2; 0.5–1 pp → 1; < 0.5 pp → drop at G2. In the η-version use p = σ(η); hazards from matches with lf + 1 ≤ es
- notes: settlement rules of the books in the average are unverified in all three sources (feasibility auditor). MKT's "retired in the last 30 days" secondary is a difference Δ1[…]

### I-043 · Rust after an unplanned layoff × age × how it began
- type_basis: W: Rust_A − Rust_B, Rust = U·exp(−n/ν)·(1 + ρ(age − 28)+ + η·1[injury start] + ψ·1[PR/SR])
- swap_ok: yes
- redundancy: surf_layoff pairs cannot tell "played elsewhere" from "did not play"; plain rust looked priced (SEP: layoff > 400 days −4.5 pp, SE 2.7, against the market, 2013–21)
- novelty_r2: to compute
- effect_bound_mll: 0.02–0.15 (originator); about 2% of matches, so the in-subgroup MDE is ≈ 7 mLL; central ≈ 0.02
- mde_mll: block B-INJ: 0.16 (w 0.5); in-subgroup ≈ 8
- controls: ΔU; Δage; surf_layoff pairs; Std
- trait: none (state)
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-INJ; ρ, η, ψ, ν fixed in advance (not tuned on outcomes); E[gap] frozen on 2010–2018 from the calendar alone
- notes: near-duplicate of I-044; both stay as separate columns of one block

### I-044 · Returning from injury: reputation against rust
- type_basis: W, U: Δ(inj·1[L ≥ 56]·1[m ≤ 2]·e_pre)
- swap_ok: yes
- redundancy: the frontier's absence × Elo tied (seen-2025/26)
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.1 on 1–2% of matches; central ≈ 0.01–0.03
- mde_mll: block B-INJ
- controls: the term without e_pre; Δe_pre; surf_layoff pairs; Std
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-INJ
- notes: 

### I-045 · Within-event serve decay
- type_basis: W: Tr_A − Tr_B (shrunk slope of first_won and first_in residuals over this and the previous event); the product with Fat is a sensitivity
- swap_ok: yes
- redundancy: form_first_won, form_first_in are means, not slopes
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.03 (noisy)
- mde_mll: block B-INJ
- controls: form_first_won, form_first_in; Std
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-INJ with the box-score form only; the serve-speed variant is infeasible before 2022 (12% coverage, as I-020); split-half reliability above the pure-luck replay is the result-free gate
- notes: 
