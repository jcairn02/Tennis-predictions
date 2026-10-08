# Math audit · family 12 · Fatigue × style and the point model (attrition)

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md). Fat is I-052's kernel.

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-063 | refine | 0.5 | block B9b (match demand × fatigue); constants from statistic targets |
| I-064 | refine | – | deferred: two-sided, needs a result-free statistic-level precheck first |
| I-065 | refine | 0.5 | block B9b |
| I-066 | refine | 0.5 | block B9b |
| I-067 | kill | – | (c) flagged: no weather data on disk |

### I-063 · Fatigue composed through the point model
- type_basis: C (S character): first order s = the iid leverage at the pair's dominance and format, d ∝ ΔFat; the Bo5 factor 1.25 (1.10–1.13 damped) is the main modulation
- swap_ok: yes
- redundancy: best_of × ΔFat is formable by TabPFN once Fat exists; the dominance part needs pair sums
- novelty_r2: to compute
- effect_bound_mll: 0.1–0.3 (originator); Bo5 is 9.8% of matches and the Fat main effect is unproven, so central ≈ 0.02
- mde_mll: block B9b: 0.16 (w 0.5); in-subgroup (Bo5) ≈ 1.6
- controls: the plain ΔFat; s·η; 1[bo5]·ΔFat; Std
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B9b. κ (serve-point decrement per unit Fat), η (its share on return) and λ (growth per 100 points) are estimated from serve- and return-point residuals against pre-match expectations on 2013–2018: statistics, free of the price and of the current best (M5); never tuned on match outcomes
- notes: seen-2025/26 evidence (the thinking study's Slam gain, 2022–2026)

### I-064 · Own style × own fatigue
- type_basis: W: Δ[Fat·Sty] = ½[ΔFat·ΣSty + ΣFat·ΔSty]
- swap_ok: yes
- redundancy: BOD-04's own calculation: under a uniform decrement the scoring structure is nearly style-neutral, so any effect needs statistic-specific decrements
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.05
- mde_mll: n/a
- controls: ΔFat, ΔSty, ΣFat·η, ΣSty·η, Std
- trait: none × slow
- sign: two-sided (the sign is the hypothesis)
- deployment: none yet
- verdict: refine
- weight: –
- kill_reason: 
- fix: defer. Revive at weight 0.5 in block B9b only if a result-free precheck finds style-specific decrements: regress each statistic's residual (first_in, df, first_won, rpw_second) on Fat × style terciles, 2013–2018 box scores only
- notes: 

### I-065 · The opponent who exploits fatigue
- type_basis: X: R_A·Fat_B − R_B·Fat_A = ½[ΔR·ΣFat − ΣR·ΔFat]; X2 with Ret2 likewise
- swap_ok: yes
- redundancy: prod_* cross offence with defence, never style with state; grinder style tied at the close (UFC stage C) but not crossed with the opponent's fatigue
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); central ≈ 0.02
- mde_mll: block B9b
- controls: ΔR (ΔRet2), ΔFat; ΣR·η; ΣFat·η; prod_second_won (X2); Std
- trait: slow × state
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B9b with X1 (pace) as the column and X2 as a sensitivity; seconds-per-point split-half reliability ≥ 0.3 is a result-free gate (women's minutes start in 2016)
- notes: 

### I-066 · Rally pace × load and age: attrition in minutes
- type_basis: S: s = E_min = E_points(closeness, format) × mean(mpp_A, mpp_B), d = Δsets_14d (primary) or Δage (sensitivity)
- swap_ok: yes
- redundancy: E_points depends on the price's closeness, so s is partly a function of η: the M-set is a control
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.03; prior: fatigue × expected length showed no sign given Elo (UFC stage C)
- mde_mll: block B9b
- controls: d; s·η; M-set; Std
- trait: none
- sign: − (long expected matches tax the more loaded player)
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B9b with d = ΔFat once Fat exists (Δsets_14d reads as form, not fatigue); Δage is a sensitivity
- notes: W-02 (attrition from serve dominance) was killed by calculation: length depends on closeness, not dominance

### I-067 · Heat × age × load × style
- type_basis: S / W: s = Heat_m, d = Δ[Fat·(1 + ρ(age − 28)+)·(1 + ψR)]
- swap_ok: yes
- redundancy: none
- novelty_r2: n/a
- effect_bound_mll: unknown
- mde_mll: n/a
- controls: n/a
- trait: none
- sign: −
- deployment: none
- verdict: kill
- weight: –
- kill_reason: (c) flagged for the feasibility auditor: no venue coordinates or weather archive on disk (inventory §3.3); climate normals are a weak proxy
- fix: revive if a historical weather archive is joined, with the feasibility auditor's approval
- notes: W-08 closed weather on the same grounds
