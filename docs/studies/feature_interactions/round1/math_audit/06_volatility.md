# Math audit · family 06 · Volatility

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md). All three are price × (the pair's variance sum): M × S with s = a centred variance sum and d = η. In the η-version of the screen the candidate is s·η itself, so s·η is not also a control.

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-028 | refine | 2 | block B5 (within-match column) |
| I-029 | refine | 2 | block B5 (between-match column, primary) |
| I-030 | refine | – | sensitivity of I-029 inside B5 (with a binomial fix) |

**The bound (MAT A7, checked).** If the pair's day variance flattens the true log-odds by d ln z / d ln V = −½(1 − c²) and the price ignores it, the value is 79·(½(1 − c²)·CV_pair)² per unit: pair CV 0.2 → 0.12–0.20 mLL, 0.3 → 0.28–0.45, 0.11 if conditions explain half the over-dispersion. The pair CV is about the per-player CV / √2. So the block's power hinges on the persistence precheck, which is result-free.

### I-028 · Within-match streakiness compresses the price
- type_basis: M × S: s = K_pair − K̄ (sum of the players' excess set-to-set dispersion of the games share beyond iid at the match's own rates), d = η. Merge MEC-17 + MAT-S5 confirmed (constants only)
- swap_ok: yes
- redundancy: no input carries a variance; tour-level streakiness is in `tour`, so the column must be centred within tour
- novelty_r2: to compute (needs per-set game shares from Stage 0 histories)
- effect_bound_mll: ≤ 0.1–0.2 (below I-029's: within-match swings are a part of day variance)
- mde_mll: block B5: 0.12 (w 2); × 1.25 (slow trait)
- controls: M-set; Std (nearest by proxy); I-029's column in the same fit
- trait: slow (per-player variance)
- sign: − (flatter for erratic pairs)
- deployment: nudge (slope modifier); context column s for TabPFN as a sensitivity
- verdict: refine
- weight: 2
- kill_reason: 
- fix: one definition: excess variance (not dispersion) of the per-set games share, shrunk, centred within tour × surface; MEC's decay and MAT's centring as constants fixed now. Join block B5. G2 gate: split-half reliability ≥ 0.3 (MAT's threshold, the stricter)
- notes: MEC-17's secondary V_A − V_B (a W difference) is dropped: under an iid-type model only the sum enters

### I-029 · The pair's day-to-day variance flattens the odds
- type_basis: M × S: s = V_pair/V̄ − 1, V_pair = σ̂²_A + σ̂²_B (long-memory squared serve and return logit residuals minus the binomial part, shrunk), d = η. The Δprofile × s term is a modulation of the model's adjustment (κ² rule, ≤ 0.02): sensitivity only
- swap_ok: yes
- redundancy: none; the residuals use cross-player ratings, so the clock and the probe apply
- novelty_r2: to compute
- effect_bound_mll: see the bound above; central ≈ 0.1 if the precheck finds a pair CV ≥ 0.3
- mde_mll: block B5: 0.12 (w 2); × 1.25
- controls: M-set; Std
- trait: slow
- sign: −
- deployment: nudge
- verdict: refine
- weight: 2
- kill_reason: 
- fix: primary between-match column of block B5. Weight rule fixed now, applied before M1 from the result-free precheck: de-noised pair CV ≥ 0.3 → the block keeps weight 2; 0.2–0.3 → 1; below 0.2 or split-half reliability < 0.3 → the block drops at G2
- notes: prior: the predictive frontier's reliability/variability family +0.23 [−0.04, +0.50] against Pinnacle + profile (men, a tie, seen-2025/26)

### I-030 · Volatility compression: the price prices means, not variance
- type_basis: M × S: s = σ²_A + σ²_B (52-week SD of total-points residuals), d = η; same form as I-029 with another variance measure
- swap_ok: yes
- redundancy: near-duplicate of I-029; without a binomial correction its σ² also measures match length (format, closeness), which the M-set partly absorbs and partly confounds
- novelty_r2: to compute
- effect_bound_mll: within B5's
- mde_mll: n/a
- controls: as I-029
- trait: slow
- sign: −
- deployment: sensitivity
- verdict: refine
- weight: –
- kill_reason: 
- fix: subtract the binomial part (1/(n p(1 − p)) per match) and keep it as I-029's pre-declared sensitivity inside B5; its merge condition with I-034 is handled by B6 (different modulator)
- notes: seen-2025/26 evidence (frontier, 2019+): screen, but the final test cannot confirm it
