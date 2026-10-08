# Math audit · family 15 · Rank, fame, attention and visibility

Round 1, mathematical auditor. Research evidence, not a decision. Keys in [the summary](../math_audit.md).

**On N and Δ1.** N (the market lens's profile nudge index) is a ridge fit of the result on 37 inputs with the price as offset: it reads results and the price while it is built, so it cannot exist before M1 and its construction target breaks M5. Fix: use the current best's own out-of-sample adjustment, adj = η − z (no new result read), or build N walk-forward after M1 as a learned column under M6, frozen at M1. Δ1's rescaling by outcome calibration slopes likewise reads results; rescale each view to the price's SD within tour (computed here) instead.

| ID | Verdict | Weight | Where it goes |
|---|---|---|---|
| I-080 | refine | 1 | block B-INFO |
| I-081 | refine | 1 | block B-INFO (N → adj; sign declared + by the block) |
| I-082 | pass | 1 | stand-alone |
| I-083 | refine | 1 | block B-REPUTE |
| I-084 | pass | 0.5 | stand-alone slope, fitted jointly with I-036 |

### I-080 · Attention-modulated disagreement
- type_basis: S: s = −A (attention index: level, round depth, star power; crowding added if the schedule counts are clean), d = Δ1 ✓
- swap_ok: yes (tested)
- redundancy: computed R² 0.075 (0.11 with the M-set); corr −0.29 with I-034's column
- novelty_r2: 0.075
- effect_bound_mll: 0.1–0.4 (originator); κ² logic on Δ1's small value given the price gives ≈ 0.03 central, ≤ 0.1
- mde_mll: block B-INFO: 0.14 (w 1)
- controls: Δ1; A·η; Std
- trait: slow (rank part) × none
- sign: +
- deployment: TabPFN difference column (Δ1·A) or nudge
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B-INFO; Δ1 rescaled result-free; N·(−A) a sensitivity with adj in place of N
- notes: motivating evidence from Polymarket 2025–2026 (seen): screen, but the final test cannot confirm it. TabPFN's largest gain was at the Slams, against this idea

### I-081 · Profile weight by price level
- type_basis: M: s = 1 − v = tanh²(z/2) (lopsidedness), d = N → adj
- swap_ok: yes
- redundancy: with adj in place of N it is W-16's form (killed by calculation by its originator: lopsidedness × the adjustment)
- novelty_r2: to compute (needs η)
- effect_bound_mll: κ² × the nudge's own value: ≤ 0.03–0.07
- mde_mll: block B-INFO
- controls: adj (or N); M-set; Std
- trait: none
- sign: + (the block's direction: the profile matters more where the market leans on names; the originator left it open, leaning +)
- deployment: nudge
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B-INFO with adj in place of N; the originator may rebut the declared sign
- notes: 

### I-082 · Salience-weighted evidence: form earned where nobody watches
- type_basis: W (U character): Δ(w̃_L·s_L), low-visibility opponent-adjusted points form with its own evidence weight
- swap_ok: yes
- redundancy: the two-week profile pools all levels; no level split exists
- novelty_r2: to compute (needs per-level decayed sums)
- effect_bound_mll: 0.1–0.5 (originator); central ≈ 0.05, upper ≈ 0.2 (players arriving from Challengers and qualifying)
- mde_mll: 0.14 (w 1)
- controls: adjperf_tpw_2w and the nearest form_*; Δ(w̃_H·s_H) (the high-visibility analogue, for the β_L > β_H contrast); Std; missing-lower-level indicator
- trait: none
- sign: +
- deployment: TabPFN difference column
- verdict: pass
- weight: 1
- kill_reason: 
- fix: primary β_L one-sided; β_L > β_H reported as a secondary contrast; k = 200 points fixed (the frontier's constant)
- notes: lower-level box scores more than double in 2025 (a covariate shift into the test seasons); ITF has none

### I-083 · Fallen-star premium
- type_basis: W, M: Δ(F·R) = ½[ΔF·ΣR + ΣF·ΔR], F = log(1 + titles + Slam QF+), R = peak Elo − current Elo
- swap_ok: yes
- redundancy: no fame or peak input; literature on popularity premia is mixed (buzz profits vanished on replication)
- novelty_r2: to compute
- effect_bound_mll: 0.05–0.2 (originator); central ≈ 0.02
- mde_mll: block B-REPUTE: 0.14 (w 1); × 1.25
- controls: ΔF, ΔR; ΣF·η; ΣR·η; Std
- trait: slow
- sign: −
- deployment: TabPFN difference column
- verdict: refine
- weight: 1
- kill_reason: 
- fix: join block B-REPUTE (with I-071, I-055); titles from Stage 0 rounds and levels, strictly earlier
- notes: [I], or [A] if it vanishes with Pinnacle

### I-084 · Pair prominence modulates how much the price knows
- type_basis: S × M: s = ΣT (the pair's overall Elo sum, standardised), d = η; the Δprofile × ΣT term is a sensitivity (an adjustment rescaling, κ² rule)
- swap_ok: yes (tested)
- redundancy: computed corr −0.70 with I-036 (prominence mirrors obscurity); R² 0.28; the Elo sum is an S2 column, so its TabPFN form is inside S2
- novelty_r2: 0.28 (0.32 with the M-set)
- effect_bound_mll: 79κ²: κ = 4% → 0.13; Lahvička's high-profile slope (+0.07 on about 20%) → ≈ 0.08 at a soft book; central ≈ 0.03
- mde_mll: 0.16 (w 0.5)
- controls: M-set; η × level; I-036's column in the same fit; Std (points_52w +0.43)
- trait: slow
- sign: +
- deployment: nudge
- verdict: pass
- weight: 0.5
- kill_reason: 
- fix: fit jointly with I-036: in a monotone world the two declared signs conflict; jointly they can express a U-shape (Lahvička found the bias strongest in both obscure and high-profile matches)
- notes: 
