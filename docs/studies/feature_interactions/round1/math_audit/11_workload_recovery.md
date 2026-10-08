# Math audit · family 11 · Workload and recovery

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md). Fat and Fit are I-052's kernels. Every load-based modulation below inherits a main effect (fatigue beyond `sets_14d`) that is itself unproven at the close, so their weights are low unless the mechanism is specific.

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-051 | refine | – | split: On → B11, Ex → I-056 sensitivity, Off → I-052 sensitivity |
| I-052 | pass | 1 | stand-alone (ΔFat beyond sets_14d) |
| I-053 | pass | 1 | stand-alone (age × Fat) |
| I-054 | refine | 0.5 | block B6 (transient uncertainty flattens the price) |
| I-055 | refine | 1 | block B-REPUTE (anchoring on names) |
| I-056 | pass | 0.5 | stand-alone contrast |
| I-057 | refine | – | sensitivity of I-052 |
| I-058 | refine | 0.5 | block B9a (constitution × own load) |
| I-059 | refine | 0.5 | block B10 (arrival debt) |
| I-060 | refine | 0.5 | block B10 |
| I-061 | refine | 0.5 | block B9a |
| I-062 | refine | – | sensitivity of I-052 |

### I-051 · Load split: on-site survival against carried-over debt
- type_basis: W: three differences ΔOn, ΔEx, ΔOff; three different mechanisms (survival or rhythm, within-event struggle, carried-over debt)
- swap_ok: yes
- redundancy: their sum is roughly sets_14d; Off is Fat restricted to off-site load
- novelty_r2: to compute
- effect_bound_mll: 0.1–0.4 (originator, optimistic); ≈ 0.03 per part
- mde_mll: n/a (split)
- controls: sets_14d; Std
- trait: none
- sign: On +, Ex −, Off −
- deployment: per destination
- verdict: refine
- weight: –
- kill_reason: 
- fix: split by mechanism: On joins block B11 (on-site rhythm, with I-075, I-076); Ex becomes a graded "scare" sensitivity of I-056; Off a sensitivity of I-052. The "equal coefficients" test is dropped
- notes: the 2010–2018 expectation for Ex uses durations only (result-free)

### I-052 · Duration × recency: a fitness–fatigue kernel on the match clock
- type_basis: W: ΔFat = Δlog(1 + Σ L_j·exp(−Δ_j/τ2)); ΔFit with τ1 is a sensitivity
- swap_ok: yes
- redundancy: sets_14d is a 14-day box-car of sets from event start dates; Fat uses minutes and real days (the clock's obs)
- novelty_r2: to compute (needs minutes histories at all levels)
- effect_bound_mll: central ≈ 0.06; upper ≈ 0.3 (sets_7d +0.30 [+0.05, +0.54] at the close, HIST and seen-2025/26)
- mde_mll: 0.14 (w 1)
- controls: sets_14d; surf_layoff pairs; Std; minutes-imputed indicator (points or games fallback) as miss_A − miss_B and miss·η
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: pass
- weight: 1
- kill_reason: 
- fix: fix τ2 = 3 days and τ1 = 21 days in advance (the grid becomes sensitivities); if tuned instead, only on a price-free target (the player's next-match opponent-adjusted points won, a statistic, 2013–2018; a ledger row). I-051's Off, I-057 and I-062 are its sensitivities
- notes: the 12-day Masters from 2023 changes rest in replication: report the stage heterogeneity

### I-053 · Age × recovery debt
- type_basis: W: Δ[Fat·(age − 26)+] = ½[ΔFat·Σa + ΣFat·Δa], a = (age − 26)+
- swap_ok: yes (tested with sets_14d for Fat)
- redundancy: computed R² 0.79 on the 58 (age dominates the product); the S2 levels arm (Σage, Σsets) also carries its TabPFN form
- novelty_r2: 0.79 (proxy)
- effect_bound_mll: 0.05–0.3 (originator); central ≈ 0.04
- mde_mll: 0.14 (w 1); × 1.25 (age is slow)
- controls: ΔFat, age, age_sq, sets_14d; ΣFat·η, Σa·η; Std
- trait: slow (age) × state
- sign: −
- deployment: TabPFN difference column
- verdict: pass
- weight: 1
- kill_reason: 
- fix: the τ2(age) form and the Bo5 variant are sensitivities
- notes: the brief's own example; market anchoring found age the strongest single nudge given the price (in-sample, seen)

### I-054 · Both tired against one tired
- type_basis: S: s = ΣFat − c, d = η (z1); z2 and the pair are sensitivities
- swap_ok: yes (tested with sets_14d)
- redundancy: corr −0.37 with I-049's column; the S2 arm's Σsets carries the TabPFN form
- novelty_r2: 0.08
- effect_bound_mll: ≤ 0.05 (both depleted is rare outside Slam second weeks)
- mde_mll: block B6: 0.16 (w 0.5)
- controls: M-set; ΔFat; I-049's column; Std
- trait: none
- sign: − (low confidence)
- deployment: nudge
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B6 (a variance mechanism)
- notes: 

### I-055 · The favourite's hidden fatigue
- type_basis: M: the contrast z1 − z2 = sign(η)·abs(ΔFat): s = abs(ΔFat), d = sign(η) ✓
- swap_ok: yes (tested)
- redundancy: computed R² 0.41 (0.51 with the M-set)
- novelty_r2: 0.41
- effect_bound_mll: ≤ 0.05
- mde_mll: block B-REPUTE: 0.14 (w 1)
- controls: ΔFat; abs(ΔFat)·η (so the step, not a slope change, is tested); M-set; Std
- trait: none
- sign: − on the contrast
- deployment: nudge
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B-REPUTE (the market anchoring on names: I-071, I-083)
- notes: 

### I-056 · Previous-round scare × rest
- type_basis: W contrast (typed M / W, but no price term): b(Scare·1[rest ≤ 1]) − b(Scare·1[rest ≥ 2])
- swap_ok: yes
- redundancy: the two-week profile averages the scare's statistics; no rest or closeness input
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.3 (originator); about 20% of matches have exactly one scared player; central ≈ 0.04
- mde_mll: 0.16 (w 0.5)
- controls: ΔScare (the sum of the two columns); Δrest; Std
- trait: none
- sign: − on the contrast (fatigue at ≤ 1 day, over-reading undone at ≥ 2)
- deployment: TabPFN difference columns
- verdict: pass
- weight: 0.5
- kill_reason: 
- fix: primary Scare = 1[deciding set]; closeness, points below expectation and I-051's Ex are sensitivities
- notes: 

### I-057 · Acute-to-chronic load spike
- type_basis: W: f(R_A) − f(R_B), R = (L7 + c)/(L28/4 + c)
- swap_ok: yes
- redundancy: a ratio of two windows of the same load that Fat and Fit weigh; sports-science artefacts known
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.03 beyond Fat and Fit
- mde_mll: n/a
- controls: Fat, Fit; sets_14d; Std
- trait: none
- sign: −
- deployment: sensitivity
- verdict: refine
- weight: –
- kill_reason: 
- fix: pre-declared sensitivity of I-052; it stays an input of I-042's hazard estimator (c)
- notes: 28-day minutes complete for 55% of women's player-matches

### I-058 · Recovery as a player trait
- type_basis: W: Δ[Trait·Fat] = ½[ΔTrait·ΣFat + ΣTrait·ΔFat]
- swap_ok: yes
- redundancy: none; prior failure (late decline is not a trait: UFC stage C)
- novelty_r2: to compute
- effect_bound_mll: small (≤ 0.02)
- mde_mll: block B9a: 0.16 (w 0.5); × 1.25
- controls: ΔFat, ΔTrait; ΣFat·η; ΣTrait·η; Std
- trait: slow
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B9a; the split-half reliability above the pure-luck replay is a result-free G2 gate
- notes: 

### I-059 · Last week's deep run × a short gap × travel
- type_basis: W (three-way within a player): Run_A − Run_B
- swap_ok: yes
- redundancy: sets_14d counts last week's sets as load; near-duplicate of I-088
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); ≈ 3% of player-matches; central ≈ 0.02
- mde_mll: block B10: 0.16 (w 0.5)
- controls: the component differences; sets_14d; Std
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B10; τ ∈ {2, 4} fixed at 2 days now; Trav from the continent map (buildable from country codes)
- notes: 

### I-060 · Consecutive weeks away × age
- type_basis: W: Δ[Wk·(1 + α(age − 28)+) + β·Away]
- swap_ok: yes
- redundancy: one 14-day window, no place
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); central ≈ 0.02
- mde_mll: block B10
- controls: ΔWk, Δage, ΔAway, Fat, Fit; Std
- trait: none × slow
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B10 with α = 0.05 and β = 0.1 fixed now; the continent map is a small table to build
- notes: 

### I-061 · Season odometer × age × time of year
- type_basis: W with an S modulation: s = 1[month ≥ 9], d = Δ[Odo·(age − 27)+]
- swap_ok: yes
- redundancy: no season-level load
- novelty_r2: to compute
- effect_bound_mll: 0.02–0.1 (originator); central ≈ 0.01
- mde_mll: block B9a
- controls: d; s·η; ΔOdo; Δage; Std
- trait: none × slow
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B9a; the ranking-band expectation frozen on 2010–2018 from minutes only
- notes: 

### I-062 · Off-tour load: team ties and their travel
- type_basis: W: ΔTeam
- swap_ok: yes
- redundancy: largely inside Fat once team ties are counted; 34% of ties undated
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.02
- mde_mll: n/a
- controls: Fat built with team ties; sets_14d; Std
- trait: none
- sign: −
- deployment: sensitivity
- verdict: refine
- weight: –
- kill_reason: 
- fix: build Fat (I-052) with team ties included and keep the team-only term as a sensitivity
- notes: 
