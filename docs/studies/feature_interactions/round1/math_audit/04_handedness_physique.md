# Math audit · family 04 · Handedness and physique

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md). Hand and height are fixed per-player traits: inference by permutation of the trait across players within tour (M4), variance × 1.23.

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-021 | refine | 0.5 | block B4 (matchup-specific deviations) |
| I-022 | refine | 0.5 | block B3 (second-serve style) |
| I-023 | refine | 1 | block B7 (thin evidence, reliability) |
| I-024 | refine | 0.5 | block B9a (constitution × own load) |

### I-021 · Serving to, and returning against, left-handers
- type_basis: X: G_A·L_B − G_B·L_A = ½[ΔG·ΣL − ΣG·ΔL] ✓, G = E + F from an extended IOS
- swap_ok: yes
- redundancy: hand is not an input; the crude forms (lefty indicator, record against the hand) tied or were slightly worse (PD stage 4, one design)
- novelty_r2: to compute (needs the extended IOS solve)
- effect_bound_mll: ≤ 0.1 overall (originator); lives in the 24% (men) / 15% (women) mixed-hand matches
- mde_mll: in-subgroup about 0.8, × 1.23 (fixed trait)
- controls: ΔG, ΔL; ΣG·η, ΣL·η; Std; missing-hand indicator
- trait: fixed (hand) × slow (E, F)
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B4; the extended IOS is a field solve (clock and probe); the odd/even-season persistence of F (≥ 0.15, above a shuffled-hand placebo) is a result-free G2 gate
- notes: literature: the elite left-hander edge has faded (Loffing et al.)

### I-022 · Kick second serve against a short returner
- type_basis: X: O^sw_A·(h̄ − h_B) − O^sw_B·(h̄ − h_A) = ½[ΔO^sw·(2h̄ − Σh) + ΣO^sw·Δh] ✓
- swap_ok: yes (tested)
- redundancy: nearest iosO_ace +0.52, prod_first_won −0.50
- novelty_r2: 0.45
- effect_bound_mll: ≤ 0.03 (originator: tiny)
- mde_mll: block B3
- controls: ΔO^sw, Δh, ΣO^sw·η, Σh·η, prod_second_won, Std, missing-height indicator
- trait: fixed (height)
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B3 with I-016; pooled (women's heights cover 64% in 2022–24, above G2's 50%), not men-only
- notes: height × height cancels exactly (W-05)

### I-023 · Height as the serve prior for thin histories
- type_basis: U / W: Δ[K_h/(n + K_h)·(β_h(h − h̄) − O^ace)], a reliability weight × (height prior − rating)
- swap_ok: yes (tested)
- redundancy: nearest iosO_ace −0.48; height main effect tied (−0.02, men)
- novelty_r2: 0.35 (computed with β_h from players with ≥ 5,000 serve points, seasons ≤ 2018, K_h = 1,000)
- effect_bound_mll: ≤ 0.05 (young men with few rated points)
- mde_mll: block B7 (0.14 at w 1); × 1.23
- controls: the unweighted ΔO^ace; Δh; Std; missing-height indicator
- trait: fixed (height) × state (evidence)
- sign: +
- deployment: TabPFN difference column (replacing nothing)
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B7; β_h fitted on statistics only (O^ace on height); the next-match ace-forecast check for players under 1,000 rated serve points (≥ 0.05 milli per point) is a result-free gate
- notes: 

### I-024 · Height × age and height × load
- type_basis: W: Δ[h·(age − 28)+] and Δ[h·Fat]; each = ½[Δx·Σy + Σx·Δy]
- swap_ok: yes (tested with sets_14d for Fat)
- redundancy: nearest prod_hold −0.35 (age arm), iosO_ace +0.55 (load arm)
- novelty_r2: 0.19 (age arm), 0.43 (load arm)
- effect_bound_mll: 0.02–0.1 (originator); central ≈ 0.02
- mde_mll: block B9a (0.16 at w 0.5); × 1.23
- controls: Δh, Δ(age − 28)+, ΔFat; Σh·η, Σage·η, ΣFat·η; Std
- trait: fixed (height)
- sign: − for both
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: both columns join block B9a; they need I-052's Fat (sets_14d is only the fallback)
- notes: weak mechanism; the block carries it
