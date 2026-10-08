# Math audit · withdrawn ideas and the proposed blocks

Round 1, mathematical auditor, 6 Oct 2026. Research evidence, not a decision. Keys in [the summary](../math_audit.md).

## Withdrawn ideas W-01 … W-20: all twenty closures confirmed, none revived

| ID | Ruling | One line |
|---|---|---|
| W-01 | confirm | Exact iid identity: deuce and ad courts carry half of a game's sensitivity each; the average deviation lives on in I-021 |
| W-02 | confirm | Expected points depend on closeness, not dominance (164–166 points across m = 0.56–0.70, exact) |
| W-03 | confirm | Bounded: ≤ 0.3 points of hold rate even against a second-serve specialist |
| W-04 | confirm | Exactly zero under additive iid; I-017, its structural test, is killed (b) as well |
| W-05 | confirm | (−ab) − (−ab) = 0 after antisymmetrisation; only I-022's asymmetric form can carry a sign |
| W-06 | confirm | (e): shot-level rally and matchup features tied at the close (SL stage 2, 0 of 280 rows; boosting on both players' values, SL stage 3) and the long-rally edge was worse (SL ranking) |
| W-07 | confirm | Unknown before the toss; the set probability does not depend on the first server (exact) |
| W-08 | confirm | No weather archive or start-time-of-day venue table on disk; same as I-067's (c) |
| W-09 | confirm | The late-match decline is not a player trait (UFC stage C): nothing stable to cross |
| W-10 | confirm | ≤ 0.019 logit, only in matches reaching a deciding set: < 0.01 mLL |
| W-11 | confirm | d logit hold / d logit p within ±5% of 2.65 over the men's range: linear suffices |
| W-12 | confirm | κ² rule on 20% of men's rows: ≤ 0.013 mLL. The Bo5 question moves to the price's slope (I-006 refined), not the adjustment |
| W-13 | confirm | Posterior variances small and uniform (≤ 0.025 mLL). Evidence counts vary more (I-032: CV 0.17), which is why I-032 survives |
| W-14 | confirm | The average's reliability ≥ 0.994: < 0.001 mLL |
| W-15 | confirm | ≤ 0.007 mLL; the convex version (I-035) is computed at ≤ 0.006, same verdict. The kept suggestion (Shin or power de-vig of the odds input) is a representation question for M2 |
| W-16 | confirm | Rescales the adjustment on few matches. I-081 inherits its form and joins B-INFO at low expected value |
| W-17 | confirm | Exists only for 2025–2026: rule 1 |
| W-18 | confirm | Five-book quotes stop in 2018: unusable in the test seasons |
| W-19 | confirm | (e) for the listed main effects (surface Elo, surface IOS, TTT: tied at the close in several designs, inventory §3.1). Load and luck re-enter only through I-052 (a new measurement on the full history) and I-025 (in a block) |
| W-20 | confirm | 2–4 matches a season: no power at any effect size |

## The blocks

**Why blocks.** G2 asks a candidate below about 0.09 mLL (population-averaged) to join a block or be deferred. That threshold is a missing log-odds term with RMS ≈ 0.030 beyond the current best, a third of TabPFN's whole adjustment. Most interaction ideas sit at 0.01–0.05 central, so they are tested as one hypothesis per shared mechanism.

**How a block is tested (proposal for the harness).** Each member column is standardised on the discovery rows (result-free) and multiplied by its declared sign. The block's single column is their sum. Its controls are the union of the members' M2 controls. That gives one coefficient and one one-sided z, which fits the screen as written. Blocks with a two-sided member use a k-df Wald test instead, at weight 0.5. A member whose result-free precheck fails before M1 is dropped from its block; the block survives with the rest. The composite loses power when one member carries all the signal (about 1/√k of its z); that is the price of the multiplicity saved.

| Block | Members (column, sign) | Shared mechanism | Test | Weight | Expected Δ, mLL |
|---|---|---|---|---|---|
| B2 | I-012 shield (+), I-013 e_ace (+) | free points and ace curvature beyond additive IOS | composite | 1 | ≈ 0.05 |
| B3 | I-016 risk × attack (±), I-022 kick × short returner (+) | second-serve style matchups | Wald, 2 df | 0.5 | ≤ 0.05 |
| B4 | I-018 style pair (+), I-019 points H2H (+), I-021 hand deviation (+) | matchup-specific serve-point deviations | composite | 0.5 | ≈ 0.05 |
| B5 | I-028 within-match (−), I-029 between-match (−; I-030 sensitivity) | the pair's volatility flattens the price | composite | 2 (rule) | 0.1–0.3 if pair CV ≥ 0.3 |
| B6 | I-033 flux (−), I-034 conflict (−), I-054 both tired (−) | transient uncertainty flattens the price | composite | 0.5 | ≈ 0.05 |
| B7 | I-023 height prior (+), I-031 re-anchored form (+), I-032 ΔIOS·r̄ (+), I-048 stale deviation (−) | unknown is not average: evidence and staleness weighting | composite | 1 | ≈ 0.1 |
| B9a | I-024 height × Fat, × age (−), I-058 recovery trait (+), I-061 odometer × age (−) | constitution × own load | composite | 0.5 | ≈ 0.03 |
| B9b | I-063 leverage × ΔFat (−), I-065 grinder × opponent's Fat (+), I-066 expected minutes × ΔFat (−) | match demand × fatigue | composite | 0.5 | ≈ 0.04 |
| B10 | I-059 deep run (−), I-088 title × first match (−), I-060 weeks away (−), I-074 jet lag (−, if built) | arrival debt | composite | 0.5 | ≈ 0.05 |
| B11 | I-051's On (+), I-075 on-site × novelty (+), I-076 rhythm × cold start (+) | on-site rhythm | composite | 0.5 | ≈ 0.04 |
| B-SWITCH | I-046 (±), I-047 style × sgn(surface) (+), I-047 age (±), I-050 indoor switch × style (+) | own switch state × own style or age | Wald, 4 df | 0.5 | ≈ 0.04 |
| B-CLUTCH | I-009 games − points (+), I-026 big-point return × scarcity (+), I-027 resilience (+) | persistent non-iid scoring skill | composite | 0.5 | ≈ 0.03 |
| B-ANCHOR | I-037 dispersion (−), I-038 skew contrast (+) | artefacts of the average close [A] | composite | 0.5 | ≈ 0.05 |
| B-RECAL | I-040 r̄ × adj (+), I-041 adj³ (±) | recalibrating the model's own adjustment | Wald, 2 df | 0.5 | ≤ 0.05 |
| B-INJ | I-043 rust (−), I-044 injury return (−), I-045 serve decay (−) | hidden physical impairment | composite | 0.5 | ≈ 0.03 |
| B-VENUE | I-072 venue pace × ΔO^ace (+; I-077 folded in), I-073 indoor deviation (+) | venue conditions × serve profile | composite | 0.5 | ≈ 0.03 |
| B-HOME | I-078 ΔH × small event (±), I-079 home × wild card (±) | home crowd, travel and hype | Wald, 2 df | 0.5 | ≈ 0.02 |
| B-AGE | I-068 age × shape (−; I-069 sensitivity), I-070 age × (short − long) (+) | age changes what the long memory and recent form mean | composite | 1 | ≈ 0.06 |
| B-REPUTE | I-071 rank gap × age (−), I-083 fallen star (−), I-055 tired favourite (−) | the price anchors on reputation that lags the state | composite | 1 | ≈ 0.07 |
| B-INFO | I-080 Δ1 × low attention (+), I-081 adj × lopsidedness (+), I-087 adj × short turnaround (+) | where the market knows less, the disagreement weighs more | composite | 1 | ≈ 0.05 |
| B-OVERREACT | I-025 luck (−), I-085 drift (−), I-086 surprise (−), I-091 raw H2H (−) | the price over-reacts to salient recent results | composite | 0.5 | ≈ 0.04 |
| B-MOTIV | I-089/I-090 merged elite pre-Slam (−), I-089's post-Slam (−) | calendar effort | composite | 0.5 | ≈ 0.02 |

**Rules fixed now for the two conditional weights.** B5 and I-042 keep weight 2 only if their result-free prechecks, run in round 2 and before M1, clear the bar: B5 a de-noised pair CV ≥ 0.3 with split-half reliability ≥ 0.3 (else 1 at CV 0.2–0.3, else dropped); I-042 a de-noised persistent hazard SD ≥ 1 pp (else 1 at 0.5–1 pp, else dropped).

**The S2 levels arm.** Its 17 sums are a TabPFN-form umbrella for several of these: the spw sums of I-003, I-004 and I-005 are 98% linear in its 14 IOS sums (computed), and its age, load and Elo sums let TabPFN form I-013's, I-053's, I-054's and I-084's products. In the linear screen those stay separate hypotheses; in TabPFN they need no arm of their own.
