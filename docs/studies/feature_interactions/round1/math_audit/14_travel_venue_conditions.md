# Math audit · family 14 · Travel, venue and conditions

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-072 | refine | 0.5 | block B-VENUE (one primary product) |
| I-073 | refine | 0.5 | block B-VENUE |
| I-074 | refine | 0.5 | block B10 (arrival debt), if the time-zone table is built |
| I-075 | refine | 0.5 | block B11 (on-site rhythm) |
| I-076 | refine | 0.5 | block B11 |
| I-077 | refine | – | folded into I-072 (venue pace covers altitude venues) |
| I-078 | refine | 0.5 | block B-HOME |
| I-079 | refine | 0.5 | block B-HOME |

### I-072 · Leak-proof venue pace × serve/return shape
- type_basis: S: s = v_e (shrunk ace residual of earlier editions), d = ΔO^ace (primary); v_e·ΔD^spw a sensitivity; v_e as context a sensitivity
- swap_ok: yes
- redundancy: the model has surface and men's indoor only; the frontier's thinner same-edition proxy tied (+0.07 against Pinnacle, seen)
- novelty_r2: to compute (field statistic)
- effect_bound_mll: ≤ 0.1 (originator); central ≈ 0.02
- mde_mll: block B-VENUE: 0.16 (w 0.5)
- controls: ΔO^ace (iosO_ace); v_e·η; Std
- trait: none (venue) × slow
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: one primary product (v_e·ΔO^ace) in block B-VENUE; v_e from editions with lf < es on the clock, passed through probe.py; the result-free carry-over check (r ≥ 0.3 for the edition's own residual; mechanics measured 0.52 men, 0.42 women) is the G2 gate
- notes: venue key continuity (moved and renamed events) to check

### I-073 · Per-player indoor deviations in the profile
- type_basis: S × a new difference: I·(ΔG + ΔH) from an extended IOS with an indoor term
- swap_ok: yes
- redundancy: surface deviations of the same kind were priced (SI §3.7, ✗ design years; SI R2 tie): a near-(e), but indoor is a different condition
- novelty_r2: to compute (needs the extended solve)
- effect_bound_mll: small (≤ 0.03)
- mde_mll: block B-VENUE
- controls: d; I·η; indoor; Std
- trait: slow
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-VENUE; both tours' indoor flag from tennis-data's Court field (100%, inventory §4.3); the split-season carry-over of G and H (≥ 0.15) is a result-free gate; the extended IOS is a field solve (clock and probe)
- notes: 

### I-074 · Jet lag
- type_basis: W: JL_A − JL_B with direction, days since the last match away, age
- swap_ok: yes
- redundancy: nothing about place is an input
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); the trigger (≥ 5 zones within ≤ 5 days) is rare; central ≈ 0.02
- mde_mll: block B10: 0.16 (w 0.5)
- controls: the component differences; Std
- trait: none
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B10 only if a city → UTC-offset table (with daylight saving) is built before M1 from tennis-data's Location (100%); otherwise B10 runs without it. Feasibility auditor to rule
- notes: 

### I-075 · On-site acclimatisation × how new the conditions are
- type_basis: W: Δ[OS·Nov] = ½[ΔOS·ΣNov + ΣOS·ΔNov]
- swap_ok: yes
- redundancy: OS is I-051's On; Nov overlaps I-047, I-050 and I-074's inputs
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); central ≈ 0.02
- mde_mll: block B11: 0.16 (w 0.5)
- controls: ΔOS, ΔNov; ΣOS·η; ΣNov·η; Std
- trait: none
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B11; Nov from the parts on disk (surface switch, indoor switch from Court; time zones only if I-074's table exists); altitude dropped (I-077)
- notes: 

### I-076 · Event rhythm against a cold start
- type_basis: X: r_A·c_B − r_B·c_A = ½[Δr·Σc − Σr·Δc] ✓
- swap_ok: yes
- redundancy: r is I-051's On before the log; c is close to I-075's novelty for first matches
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); central ≈ 0.02
- mde_mll: block B11
- controls: Δr, Δc; Σr·η; Σc·η; Std
- trait: none
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B11; qualifying-to-main-draw linkage to confirm (feasibility auditor)
- notes: 

### I-077 · Altitude × serve profile × acclimatisation
- type_basis: S: s = Alt, d = ΔiosO_ace (+ a W part)
- swap_ok: yes
- redundancy: altitude venues are a subset of I-072's venue pace, which estimates their speed directly from earlier editions
- novelty_r2: n/a
- effect_bound_mll: < 0.05 overall (originator); 2% of matches, so the in-subgroup MDE is ≈ 7 mLL
- mde_mll: n/a
- controls: n/a
- trait: none
- sign: +
- deployment: none
- verdict: refine
- weight: –
- kill_reason: 
- fix: fold into I-072 (no separate column; no elevation table needed)
- notes: 

### I-078 · Home split into crowd and no travel
- type_basis: W / X: (H_A − H_B)·g(level) with g = 1[250 or 500] fixed now; the X term H·JL needs I-074's table (sensitivity); H × log rank a sensitivity
- swap_ok: yes
- redundancy: with g = 1[not a Slam] its first column equals I-079's secondary; home as a main effect tied at the close (PD stage 4)
- novelty_r2: to compute
- effect_bound_mll: 0.02–0.1 (originator); central ≈ 0.01
- mde_mll: block B-HOME: 0.17 (two-sided)
- controls: ΔH; g·η; Std
- trait: fixed-like (player country × event country): permutation of country within tour
- sign: two-sided
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-HOME (2-df Wald with I-079's primary)
- notes: literature: home +4.3 points with rank and fixed effects (Gucciardi and Ruberti), never against odds

### I-079 · Home hype: home wildcards and small events
- type_basis: W: Δ(home·wc) = ½[Δhome·Σwc + Σhome·Δwc]; secondary = I-078's first column
- swap_ok: yes
- redundancy: entry and country are not inputs; both main effects tied at the close (PD stage 4)
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.1 (originator); central ≈ 0.01
- mde_mll: block B-HOME
- controls: Δhome, Δwc; Σhome·η; Σwc·η; Std
- trait: fixed-like
- sign: two-sided (the originator left it open)
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-HOME
- notes: [I/A]
