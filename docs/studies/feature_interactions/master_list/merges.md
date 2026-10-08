# Merges made, and near-duplicates kept separate

Part of the [master list](../master_list.md). Rule (critique S5, adopted in plan.md): merge only when two ideas are algebraically identical in the modulator × difference basis, with the same population. Operationally: the same primary column, built from the same per-player quantity, so that the two would coincide once construction constants (window, decay, shrinkage strength, centring or normalisation) are set alike. Differences in those constants, in residualisation (which, in a linear screen, is a choice of control) or in estimators of the same per-player quantity are kept inside the merged row as variants, with provenance. Any originator may contest a merge of its own idea; the auditors also hold the four raw lists.

## The four merges (five source rows absorbed)

### I-001 = MEC-01 + MAT-M1 · price × the pair's serve-dominance leverage

* MEC: "x = ℓ·(λ_AB − 1)", λ_AB = L(m_AB)/L̄_c. MAT: "z_adj = z_mkt(1 + b·κ_pair)", κ_pair = β_L(μ_pair)/β_L(μ_surface) − 1; linear variant "z_mkt + b′·z_mkt·m_pair".
* Both are d × s with d = the de-vigged price log-odds (ℓ = z_mkt = `odds_logit`) and s = L(m)/L_ref − 1, where L is the iid logit-scale leverage ∂logit P/∂Δ and m = μ + ½(ΣO^spw − ΣD^spw) from the same surface-IOS serve-point ratings.
* Only L_ref differs. MEC: L̄_c, the mean of L over the cell's training matches (cell = tour × surface × indoor). MAT: L at the surface-mean dominance (tour × surface). With a_c = L(μ_c)/L̄_c, x_MEC = a_c·x_MAT + (a_c − 1)·ℓ: the same column up to a per-cell normalisation constant. MAT's linear variant is the first-order expansion, κ ≈ (L′/L)(m − μ).
* Kept as stated differences: MEC's arm (b) (λ as context); MAT's predicted b ≈ c² and its dependence on I-007; MEC tests two-sided, MAT one-sided.

### I-008 = MEC-05 + MAT-C1 · the surface-IOS profile composed into a match log-odds

* MEC: "x = logit P_iid(p^c_{A→B}, p^c_{B→A}; f)". MAT: "z_C1 = logit P_iid(p_AB, p_BA; best of, deciding-set rule)". Both use p = fi·fw + (1 − fi)·sw, each part expit(μ_s + O^s_server − D^s_returner) from the surface IOS, and the scheduled format with its deciding-set rule. The formula is identical.
* The residual variants differ: MEC's x_res subtracts the spw-IOS composition (a new column); MAT's subtracts `ratings_iid` (an input). In a linear screen, x tested with control c equals (x − c) tested with control c, so these are control choices, recorded in the row. The originators' kill thresholds (0.05 and 0.1 mLL) differ.

### I-028 = MEC-17 (primary arm) + MAT-S5 · within-match streakiness compresses the price

* MEC: "x = ℓ·(v − v̄_c)", v = V_A + V_B, V = the shrunk, decayed mean of "the excess dispersion of the games share across sets beyond the iid dispersion at that match's own serve rates". MAT: "z × (K_pair − K̄)", K_pair = κ̂_A + κ̂_B, κ̂ = "the excess variance of the player's per-set game share beyond what the iid model gives at the match's own rates", shrunk.
* Both are d × s with d = the price log-odds and s = the centred sum of the same per-player statistic. Differences are constants: MEC decays and centres within its cell, MAT centres on K̄; "dispersion" versus "variance" (one definition to fix); reliability thresholds 0.1 and 0.3.
* MEC-17's secondary arms stay attached to I-028: (ii) between-match serve-point residual variance and V_A − V_B.

### I-042 = MAT-W2 + MKT-20 + BOD-12 · retirement hazard × price

* MAT: "τ_hz = ĥ_B/p_mkt − ĥ_A/(1 − p_mkt)". BOD: "z = h_B/p − h_A/(1 − p)". MKT: "c/(π(1 − π))" with c = h_B(1 − π) − h_A·π, and c/(π(1 − π)) = h_B/π − h_A/(1 − π). The three columns are the same function of (h_A, h_B, p), on the same population.
* In the M2 basis: τ = −½·Δh/(p(1 − p)) + ½·Σh·(1 − 2p)/(p(1 − p)), an S-term (modulator 1/(p(1 − p)), difference Δh) plus the pair's total hazard times an odd function of the price.
* The hazard estimators are nested variants of one per-player quantity: (a) MKT-20, a shrunk 24-month rate; (b) MAT-W2, a shrunk retirement and walkover rate with recent-retirement and layoff modifiers; (c) BOD-12, a walk-forward logistic model that adds age, Fat, the load ratio, best of and month. **This is the most contestable merge**: if the auditors judge the estimator part of the column, the row splits back into its three sources without other changes.

## Near-duplicates kept separate (cross-referenced as clusters)

| Rows | Shared | Why kept separate |
|---|---|---|
| I-001, I-002 | dominance compression | I-002's primary modulates the IOS gap, not the price; its secondary z × D is a linear, probability-scale version of I-001 |
| I-003, I-004, I-005 | pair sums as context | Nested information, not identical: m_pair = ½(σ1 − σ2); the pairs carry ΣO^spw and ΣD^spw; I-004 adds ΣO^ace, ΣO^fi. Also near the adopted S2 levels arm |
| I-028, I-029, I-030 | price × a variance sum | Different statistics: within-match set-to-set; between-match serve and return logit residuals net of binomial; total-points residual SD |
| I-014, I-015, I-016 | second-serve matchups | Different formulas (specialisation contrast; full exposure × loss product; risk index × attack); I-014 and I-015 sit inside I-008 |
| I-046, I-047 | switch state × own style | Binary first-matches flag vs a graded state with layoff; IOS spw (D − O) vs Stage 3 or IOS share; opposite sign conventions |
| I-048, I-032 | evidence weight n/(n + k) | Different use: reweighting surface against all-surface IOS vs a harmonic-mean weight on ΔIOS |
| I-031, I-070, I-033 | recent minus long memory | Weighted by reliability, by age, or squared and summed against the price |
| I-043, I-044 | return from injury | Graded excess gap with decay and age vs indicators × pre-break Elo |
| I-059, I-088 | last week's run, first match here | Graded by wins, gap and travel vs a title indicator |
| I-068, I-069 | age × style | Linear age × IOS spw shape vs hinge × return share × profile memory |
| I-089, I-090 | elite players before Slams | Same d (Δ1[rank ≤ 20]); s differs (QF and later at pre-Slam events vs 250/500 events, all rounds), so the populations differ |
| I-078, I-079 | home × event size | I-078's g(level) is unspecified; its first column equals I-079's secondary only if g = 1[not a Slam] |
| I-051, I-075, I-076 | on-site match count | The same count enters three different columns (a difference; × novelty; × the opponent's cold start) |
| I-019, I-025 (b), I-091 | head-to-head | Points residual; results-minus-points luck; raw record as narrative |
| I-020, I-045 | serve-speed change | × the returner's defence vs alone; windows of five and two matches |
| I-006, I-063, W-12 | Bo5 × a difference | Different d (composed rating gap; fatigue; the model's adjustment) |
| I-035, W-15 | overround modulator | Convex vs linear function of the price |
| I-081, W-16 | lopsidedness × an adjustment | N vs the model's own adjustment; 1 − v vs \|z\| |
| I-072, I-077 | venue conditions × serve | Estimated venue pace vs an altitude table |
| I-036, I-080, I-084 | obscurity, attention, prominence | Different modulators (rank, attention index, total strength) and differences (price; Δ1; price and profile) |
| I-030, I-034 | shrink the price | The market originator's own merge condition; different modulators (variance sum vs \|Δ1\|) |
