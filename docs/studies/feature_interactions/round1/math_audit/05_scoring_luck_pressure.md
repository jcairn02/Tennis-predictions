# Math audit · family 05 · Scoring luck, pressure and sequence

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md).

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-025 | refine | 0.5 | block B-OVERREACT; built strictly from earlier matches, β_f out of fold |
| I-026 | refine | 0.5 | block B-CLUTCH |
| I-027 | refine | 0.5 | block B-CLUTCH |

### I-025 · Conversion luck: results beyond the points
- type_basis: W, a new per-player d: Λ_A − Λ_B (decayed, shrunk mean of e_k = y_k − σ(β_f(t_k − ½))). Arm (b), head-to-head luck, is a pair-level d with no price term: its "M / X" label is wrong
- swap_ok: yes
- redundancy: elo_games and elo_overall mix luck with level; no exact identity
- novelty_r2: to compute (needs Λ from Stage 0 histories)
- effect_bound_mll: 0–0.15 (originator); central ≈ 0.02
- mde_mll: block B-OVERREACT (0.16 at w 0.5)
- controls: elo_games, elo_overall, adjperf_tpw_2w, points_52w; Std
- trait: none (13-week memory)
- sign: − (lucky players priced too short)
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-OVERREACT. Build Λ only from matches with lf + 1 ≤ es. β_f must not be fitted on outcomes that include the target season: take it from the iid model (P(win given the points share), simulated, no data) or fit it walk-forward on earlier seasons only. Arm (b) becomes a sensitivity
- notes: near (e): conversion luck tied (MA §6.6, −0.01 [−0.10, +0.09], 2019–25) and tiebreak / deciding-set records tied (PD stage 4), but both are seen-2025/26 or HIST, so weight 0.5 rather than a kill

### I-026 · Big-point return skill × the scarcity of break points
- type_basis: S: s = β̄_c/β̂_AB (inverse expected break points per service game; symmetric), d = Δb ✓
- swap_ok: yes
- redundancy: the modulator is a function of serve dominance (family 01); b is Stage 4's bigpoint_return (coverage 86–88%, inventory §2.7), whose main effect tied given the odds with a negative coefficient given Elo
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.02 (originator: tiny)
- mde_mll: block B-CLUTCH
- controls: Δb; s·η; Std
- trait: slow (b)
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-CLUTCH; use Stage 4's bigpoint_return history (feasible), not only the thin shot-level point data
- notes: 

### I-027 · Resilience excess: breaking back and consolidating
- type_basis: W: R_A − R_B (excess over own hold and break rates); S arm s = 4p(1 − p) from the price, which needs the M-set
- swap_ok: yes
- redundancy: form_hold, form_brk carry the plain rates
- novelty_r2: to compute (point sequences)
- effect_bound_mll: ≤ 0.02 (tiny)
- mde_mll: block B-CLUTCH
- controls: form_hold, form_brk; Std; for the S arm: ΔR, s·η, M-set
- trait: slow
- sign: +
- deployment: TabPFN difference column
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-CLUTCH (W form only; the S arm is a sensitivity); the split-half carry-over of the excess (> 0.1) is a result-free G2 gate
- notes: the point-sequence table is mid-build (inventory §4.6): feasibility auditor to confirm coverage
