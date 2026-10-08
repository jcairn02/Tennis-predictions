# Math audit · family 08 · Price calibration and anchor construction

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md). [A] terms improve the score against the tennis-data average but not against a margin-free bet-time price (Polymarket, exchanges): their weight is capped at 0.5.

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-035 | refine | – | deferred: bound ≤ 0.01 computed; the de-vig belongs to the odds input |
| I-036 | pass | 1 | stand-alone, fitted jointly with I-084 |
| I-037 | refine | 0.5 | block B-ANCHOR |
| I-038 | refine | 0.5 | block B-ANCHOR (one contrast column) |
| I-039 | refine | – | post-M1 descriptive diagnostic |
| I-040 | refine | 0.5 | block B-RECAL |
| I-041 | refine | 0.5 | block B-RECAL |

### I-035 · Margin-aware de-vig
- type_basis: M: derived exactly to first order, logit p_S − z ≈ (Q − 1)·sinh z (since (π − ½)/(π(1 − π)) = sinh z): s = the overround m, d = sinh z
- swap_ok: yes
- redundancy: computed R² 0.991 on the M-set plus sinh z (0.916 on the 58): at a fixed margin it is an odd monotone function of odds_logit; only the margin's variation (SD 0.55 pp) is new
- novelty_r2: 0.92 on the 58; 0.99 with the M-set
- effect_bound_mll: computed ≤ 0.006 (men), 0.004 (women) at coefficient 1 for the part beyond the M-set; W-15's calculation, with a convex function
- mde_mll: n/a
- controls: M-set; Std
- trait: none
- sign: +
- deployment: none as a hypothesis
- verdict: refine
- weight: –
- kill_reason: 
- fix: defer as a screen hypothesis. Its sound part is a representation choice: a Shin or power de-vig of the odds input, which aligns training with margin-free bet-time prices; test it, if at all, as an M2 variant of the base's odds column, outside the claims family
- notes: seen-2025/26 evidence (sharp benchmark 2026; market anchoring 2013–2025). [A]

### I-036 · Obscure-match slope: favourite–longshot bias by rank
- type_basis: M × S: s = O = max(log rank_A, log rank_B) − tour median, d = η
- swap_ok: yes (tested)
- redundancy: rank is not an input; computed corr −0.70 with I-084's column (obscurity is the mirror of prominence)
- novelty_r2: 0.27 (0.28 with the M-set)
- effect_bound_mll: ≈ 0.19 at a soft book (Lahvička: slope +0.09 on the 29% of matches with both players outside the top 50, 79κ²·share); central ≈ 0.05 on the average close
- mde_mll: 0.14 (w 1)
- controls: M-set; η × level, η × round depth (the context slopes, so that rank rather than event size identifies b); I-084's column in the same fit; Std; unranked indicator × η
- trait: slow (rank)
- sign: +
- deployment: nudge; rank as a TabPFN context column is a sensitivity
- verdict: pass
- weight: 1
- kill_reason: 
- fix: fit jointly with I-084 (each tested one-sided on its own coefficient); drop O's symmetric "main effect" from the controls (it has none in the antisymmetric frame)
- notes: [A/I]: rerun with the Pinnacle anchor as a classification check (not a gate)

### I-037 · Book dispersion as uncertainty
- type_basis: U: s = a = 1 − (1/max_A + 1/max_B), d = η
- swap_ok: yes (tested)
- redundancy: computed: a > 0 in 46% of matches, so OddsPortal's maximum crosses routinely; a measures best-of-many spread more than genuine arbitrage. MAT-U5 (W-14): the average's reliability is ≥ 0.994
- novelty_r2: 0.07 (0.11 with the M-set)
- effect_bound_mll: ≤ 0.05
- mde_mll: block B-ANCHOR: 0.16 (w 0.5)
- controls: M-set; Std
- trait: none
- sign: −
- deployment: nudge; needs bookmaker quotes at bet time
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-ANCHOR; N × a and Δ1 × a are sensitivities
- notes: the motivating prior was post hoc (about 60 cells) and seen-2025/26. [A/I, U]

### I-038 · Best-price skew: steam or shading, told apart by fame
- type_basis: M: two columns k·(1 − fam), k·fam with opposite predicted signs; as one hypothesis the contrast x = k·(2fam − 1), d = k = logit p_max − z
- swap_ok: yes
- redundancy: R² of k on the 58 is 0.56 (computed); fam needs I-083's fame F
- novelty_r2: 0.56
- effect_bound_mll: ≤ 0.05
- mde_mll: block B-ANCHOR
- controls: k; ΔF; M-set; Std
- trait: none
- sign: + on the contrast
- deployment: nudge; needs bookmaker quotes at bet time
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: one contrast column k·(2fam − 1) with k as control, in block B-ANCHOR
- notes: [A] by construction

### I-039 · Sharp–soft split (diagnostic)
- type_basis: diagnostic: N·α against N·(1 − α), α = 1[sign(Pinnacle − average) = sign(N)]
- swap_ok: yes
- redundancy: n/a
- novelty_r2: n/a
- effect_bound_mll: n/a (Pinnacle stops in January 2026, so not a test-season feature)
- mde_mll: n/a
- controls: n/a
- trait: none
- sign: n/a
- deployment: none
- verdict: refine
- weight: –
- kill_reason: 
- fix: not a hypothesis. N is fitted on results with the price as offset, so build it only after M1, walk-forward (M6), or use the current best's own adjustment (η − z) in its place; then report the split once as a descriptive diagnostic (a ledger row)
- notes: 

### I-040 · Context-dependent recalibration of the adjustment
- type_basis: M × U: s = c, d = adj = η − z; contexts fixed now: c = r̄ (I-032's evidence weight). The format context is dropped (W-12's calculation: ≤ 0.013) and "adjustment size" is I-041
- swap_ok: yes
- redundancy: a modulation of the model's own adjustment: κ² rule
- novelty_r2: to compute (needs η)
- effect_bound_mll: ≤ 0.05–0.1 (RMS κ 0.2–0.3)
- mde_mll: block B-RECAL: 0.17 (two-sided block)
- controls: adj (its own slope); M-set; Std
- trait: none
- sign: +
- deployment: nudge (recalibration layer)
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-RECAL with I-041 (2-df Wald, since I-041 is two-sided); its prequential kill test reads results and moves after M1
- notes: corrects the model, not the market

### I-041 · Non-linear shrinkage of the adjustment
- type_basis: M: s = adj², d = adj (the cubic b3·adj³); a soft threshold is a sensitivity
- swap_ok: yes
- redundancy: the screen's nuisance cubic is in η, not in the adjustment, so not collinear
- novelty_r2: to compute
- effect_bound_mll: ≤ 0.05; the meta-stack's signed square tied in a no-odds stack
- mde_mll: block B-RECAL
- controls: adj; M-set; Std
- trait: none
- sign: two-sided (soft threshold or heavy tails)
- deployment: nudge
- verdict: refine
- weight: 0.5
- kill_reason: 
- fix: join block B-RECAL
- notes: 
