# Math audit · family 16 · Motivation, narrative and information timing

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md); N and Δ1 as in [family 15](15_rank_fame_attention.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-085 | refine | 0.5 | block B-OVERREACT |
| I-086 | refine | 0.5 | block B-OVERREACT |
| I-087 | refine | 1 | block B-INFO (N → adj) |
| I-088 | refine | 0.5 | block B10 (arrival debt) |
| I-089 | refine | 0.5 | block B-MOTIV (merged column with I-090) |
| I-090 | refine | 0.5 | block B-MOTIV |
| I-091 | refine | 0.5 | block B-OVERREACT |

### I-085 · Drifting favourite: over-reaction to news
- type_basis: M, W: s = 1[sign(r) ≠ sign(F)] (symmetric), d = r = z − F, F a walk-forward price-free forecast
- swap_ok: yes
- redundancy: F exists (the rating race and meta-stack no-odds arms); the symmetric signed square tied (meta stack S3q −0.03, seen)
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.15 (originator); central ≈ 0.02
- mde_mll: block B-OVERREACT: 0.16 (w 0.5)
- controls: r; s·η; M-set; Std
- trait: none
- sign: − (the drifted favourite is better than priced)
- deployment: nudge
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-OVERREACT; F must be the walk-forward forecast for the target season (trained on earlier seasons only)
- notes: seen-2025/26 evidence: screen, but the final test cannot confirm it

### I-086 · Last-round narrative: surprise wins and flattering scorelines
- type_basis: S: s = 1[round ≥ QF], d = Δsurprise (1 − p_prev of the last win); Δλ (last-match conversion luck) a sensitivity (it is I-025's one-match version)
- swap_ok: yes
- redundancy: Elo and the two-week profile move after the result, but not by its surprise against its own price
- novelty_r2: to compute (needs the previous match's odds)
- effect_bound_mll: 0.02–0.15 (originator); central ≈ 0.02
- mde_mll: block B-OVERREACT
- controls: Δs; s·η; Std; missing-previous-price indicator (as miss_A − miss_B and miss·η)
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-OVERREACT
- notes: seen-2025/26 evidence (market anchoring's conversion luck, 2019–25)

### I-087 · Price-formation window
- type_basis: S: s = 1[w ≤ 1], w = min over players of (es − lf of the previous match), d = N → adj; z × 1[w ≤ 1] a sensitivity
- swap_ok: yes
- redundancy: with adj it rescales the model's adjustment in about a quarter of matches: κ² rule
- novelty_r2: to compute
- effect_bound_mll: 0.02–0.1 (originator); ≤ 0.03
- mde_mll: block B-INFO: 0.14 (w 1)
- controls: adj; s·η; Std
- trait: none
- sign: +
- deployment: nudge
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B-INFO with adj in place of N; the clock's day resolution limits it
- notes: motivated by line-sharpening data from 2026 (seen): screen, but the final test cannot confirm it

### I-088 · Title last week: recency premium against a letdown
- type_basis: W: Δ(τ·first) = ½[Δτ·Σfirst + Στ·Δfirst]
- swap_ok: yes
- redundancy: near-duplicate of I-059 (indicator against graded); sets_14d reads a title run as plain load
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); 2–4% of matches; central ≈ 0.02
- mde_mll: block B10: 0.16 (w 0.5); in-subgroup ≈ 5
- controls: Δτ, Δfirst; Στ·η; Σfirst·η; Std
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B10 with I-059; the lost-final and surface-switch versions are sensitivities
- notes: 

### I-089 · Calendar motivation
- type_basis: S: s = pre·1[round ≥ QF] (event-level), d = Δtop (top = 1[rank ≤ 20]); Δpost (a Slam QF+ within 21 days) and Δdef (points to defend) secondary
- swap_ok: yes
- redundancy: same d as I-090; the populations differ only by s
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.15 (originator); a small subgroup (well under 2% of matches), central ≈ 0.01
- mde_mll: block B-MOTIV: 0.16 (w 0.5); in-subgroup ≥ 8
- controls: Δtop; s·η; Std
- trait: slow (rank)
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: merge with I-090 into one column of block B-MOTIV, s = 1[250 or 500]·1[a Slam main draw starts within 8 days] (all rounds; QF+ a sensitivity); Δpost is the block's second column; Δdef deferred (needs a hand-made points table)
- notes: 

### I-090 · Elite effort before Slams; incentive cliffs
- type_basis: S: s = 1[250/500]·1[Slam within 8 days], d = Δ1[rank ≤ 20]
- swap_ok: yes
- redundancy: see I-089; 305 men's and 592 women's 2013–2021 matches qualify (2.2%)
- novelty_r2: to compute
- effect_bound_mll: 0.02–0.15 (originator); central ≈ 0.01
- mde_mll: block B-MOTIV
- controls: Δtop; s·η; Std
- trait: slow
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: merged column of block B-MOTIV (with I-089); the seeded and cliff variants are deferred (thresholds would be a forking path)
- notes: S8: a subgroup this small needs ≈ 7 mLL inside it

### I-091 · Public narrative statistics: head-to-head and venue records
- type_basis: S: s = 1[n ≥ 3] (pair-level), d = raw = (wins_A − wins_B)/(n + 1), with the shrunk head-to-head Elo residual as a control; the venue record a sensitivity
- swap_ok: yes
- redundancy: head-to-head results forms were worse given the odds in PD stage 4 (one design, overfitting); the over-weighting hypothesis is new
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.1 (originator); central ≈ 0.01
- mde_mll: block B-OVERREACT
- controls: raw's Elo residual; s·η; Std
- trait: none (pair history)
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-OVERREACT; tournament-id continuity across seasons to check for the venue arm
- notes: 
