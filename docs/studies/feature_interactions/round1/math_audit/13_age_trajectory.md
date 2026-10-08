# Math audit · family 13 · Age and career trajectory

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md). Age is a slow trait (variance × 1.25).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-068 | refine | 1 | block B-AGE (column 1) |
| I-069 | refine | – | sensitivity of I-068 inside B-AGE |
| I-070 | refine | 1 | block B-AGE (column 2) |
| I-071 | refine | 1 | block B-REPUTE |

### I-068 · Age reshapes the profile: return and rally decay first
- type_basis: W: Δ[(age − 28)·shape] = ½[Δa·Σshape + Σa·Δshape], shape = return-heaviness of the spw IOS
- swap_ok: yes (tested)
- redundancy: nearest age_sq −0.18; corr 0.03 with I-046
- novelty_r2: 0.13
- effect_bound_mll: 0.05–0.15 (originator); central ≈ 0.03
- mde_mll: block B-AGE: 0.14 (w 1); × 1.25
- controls: age, age_sq; ΔO^spw, ΔD^spw (via the IOS inputs); Σa·η; Σshape·η; Std
- trait: slow
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 1
- kill_reason: 
- fix: column 1 of block B-AGE; the hinge (age − 29)+ is a sensitivity; the outcome-free precheck (after 29 the return residual drifts below the serve residual, next-match statistics only) stays
- notes: corrects the model's lagging profile, not the price

### I-069 · Style-specific ageing: servers age more slowly
- type_basis: W: Δ[(age − 29)+·(RetShare − 0.5)·M]
- swap_ok: yes
- redundancy: the same mechanism and almost the same column as I-068 (hinge × return share × memory)
- novelty_r2: to compute
- effect_bound_mll: within I-068's
- mde_mll: n/a
- controls: as I-068
- trait: slow
- sign: −
- deployment: sensitivity
- verdict: refine
- weight: –
- kill_reason: 
- fix: pre-declared sensitivity of I-068 inside B-AGE; its statistics-only age-curve check (2010–2018 box scores) is a useful shared precheck
- notes: 

### I-070 · Age-dependent trust in recent form
- type_basis: W (U character): Δ[(Short − Long)·h(age)], h = (25 − age)+ − κ(age − 30)+, κ = 0.5 fixed now
- swap_ok: yes (tested; Short = adjperf_tpw_2w, Long = spw IOS O + D, both standardised)
- redundancy: computed R² 0.63 on the 58 (age +0.77); same (recent − long) as I-031, weighted by age instead of reliability
- novelty_r2: 0.63
- effect_bound_mll: 0.1–0.3 (originator); central ≈ 0.04
- mde_mll: block B-AGE
- controls: Δ(Short − Long) through the existing form and IOS inputs; age; Σh·η; Σ(S − L)·η; Std
- trait: slow × state
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 1
- kill_reason: 
- fix: column 2 of block B-AGE, one composite (points form against the long-memory points level); per-statistic versions are sensitivities
- notes: 37% of women's player-matches are aged 23 or younger

### I-071 · Rank anchoring × career trajectory
- type_basis: W: Δ(g·a), g = ê(log rank) − Elo (ê fitted per tour on seasons ≤ 2018, Elo on log rank, no outcomes), a = (age − 27)/5
- swap_ok: yes (tested)
- redundancy: rank is not an input; computed R² 0.16 (Δg alone 0.25)
- novelty_r2: 0.16
- effect_bound_mll: 0.1–0.4 (originator); central ≈ 0.05
- mde_mll: block B-REPUTE: 0.14 (w 1); × 1.25
- controls: Δg, ΔT, age; Σg·η; Σa·η; Std; unranked indicator
- trait: slow
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B-REPUTE with Δ(g·a) as the column; Δg and the trajectory terms are sensitivities
- notes: seen-2025/26 evidence (market anchoring 2013–2025: age the strongest nudge; Stage 4's women's rank): screen, but the final test cannot confirm it
