# Round 3: the screen (run once, 7 October 2026)

The frozen family of 34 members against the current best model's own out-of-sample forecast (gating) and the closing price (reported), on 2014–2024 (50,087 main-tour matches with odds, debut seasons out). The procedure is fixed in [plan.md](../plan.md) and frozen by hash (ledger row 22). Outputs: `data/studies/feature_interactions/hypotheses/screen_results.csv`, `known_null_results.csv`, `descriptive_results.csv`, log `screen_run.log`.

**Keys.**
* **z** is the coefficient's z, **positive = in the member's declared direction** (two-sided rows: Wald tests, reported as p). z₁ is 2014–2021, z₂ 2022–2024, the joint z combines them.
* **Gains** are out-of-sample milli-log-loss (mLL), **positive = the member lowers the log loss (better)**: leave-one-season-out in 2014–2021, forward in 2022–2024. A 95% interval that spans 0 is a **tie**.
* Gates: filter z₁ > 1; replication z₂ > 0.67; weighted Holm (claims, one-sided 5%) and weighted BH (bundle, q < 0.10).

## The result

**One member passes every gate: B-INJ (registered as hidden physical impairment; as measured, rust after a break of six weeks or more).** It is both a claim (Holm p 0.002) and bundle-eligible (BH q 0.002). Nothing else is eligible. The known-null alarm did not fire: 0 of 6 known nulls passed.

| Member | Weight | z₁ | z₂ | joint z | p (one-sided) | Holm | BH q | Gain 2014–2021 | Gain 2022–2024 |
|---|---|---|---|---|---|---|---|---|---|
| **B-INJ** rust after a break (registered: hidden impairment; I-043, I-044, I-045) | 0.5 | +3.51 | +1.93 | **+3.99** | <0.0001 | **0.002** | **0.002** | +0.19 [−0.03, +0.42] tie | +0.02 [−0.31, +0.36] tie |
| B-VENUE venue pace × serve (I-072) | 0.5 | +2.13 | +1.32 | +2.50 | 0.006 | 0.29 | 0.15 | +0.06 [−0.09, +0.20] tie | +0.12 [−0.14, +0.37] tie |
| B-OVERREACT over-reaction to recent results | 0.5 | +1.64 | +1.38 | +2.13 | 0.017 | 0.77 | 0.23 | +0.02 tie | +0.06 tie |
| B11 on-site rhythm | 0.5 | +1.35 | +1.54 | +1.97 | 0.024 | 1 | 0.23 | −0.04 tie | +0.07 tie |
| B-STATE past fatigue (BOD-C1) | 0.5 | +0.87 | +1.93 | +1.79 | 0.037 | 1 (filter fails) | 1 | −0.03 tie | +0.07 tie |
| H-S2 the levels arm (TabPFN, encompassing) | 1 | +1.37 | +1.05 | +1.73 | 0.042 | 0.94 | 0.23 | – | – |
| B-MOTIV calendar effort | 0.5 | +2.39 | +0.49 | (+2.27) | – | 1 (replication fails) | 1 | +0.07 tie | −0.05 tie |
| B9a constitution × load | 0.5 | +0.10 | +2.53 | +1.48 | 0.070 | 1 (filter fails) | 1 | −0.04 [−0.07, −0.00] worse | +0.01 [+0.00, +0.03] better |
| I-008 the composed serve-point profile | **2** | +1.07 | −0.41 | +0.67 | 0.25 | 1 (replication fails) | 1 | +0.01 tie | −0.06 tie |
| B-LEVER serve-dominance leverage (Wald, 3 df) | 0.5 | Wald p 0.51 | | | 0.21 | 1 | 1 | | |

The other 24 are not eligible: every joint p is above 0.09, or a gate fails (I-084's −2.99 below is not a tie). Full rows are in the CSV. Two results point **against** the declared direction, which a one-sided rule cannot count; they are reported as exploratory signals:
* **I-084**, pair prominence × η: joint z **−2.99**. Inferred: the current best's forecast may be too steep, not too flat, for pairs of high combined Elo (one of 34 one-sided tests; a reversal was never a registered hypothesis).
* **I-036**, obscurity × η (jointly fitted with I-084): joint z −1.65.

## Placebos and descriptive outputs (never gating)

**Known nulls** (features that tied at the close in earlier designs; joint z, two-sided):
* KN-TTTOFF +0.59; KN-SNET +0.49; KN-ELOSURF −0.79; KN-SURFCAREER −0.39; KN-SDEV (Wald, 8 df) p 0.55.
* **KN-TTTLOGIT −2.53 (p 0.011)**: the decided TTT's log-odds carries a negative coefficient beyond the current best. Inferred: possibly a sign the model over-weights the rating it already holds. One of six known nulls at p 0.011 has about a 6.6% chance under the global null.
* None crosses the family's Bonferroni line (0.05/34), so there is **no alarm**.

**Pre-declared descriptive outputs.**
* **I-008's four sensitivities**: all ties (joint z −0.06 to +0.80).
* **B11, member by member.**
  * **On** (matches already played at this event) has joint z **+3.29**.
  * The two interaction members I-075 (+0.10) and I-076 (+0.99) are null.
  * So B11's signal is a main effect, not an interaction (ruling R-2).
* **INFO-1**: joint z +0.83, null, as its false premise predicted.
* **C-1, the sharp anchor.**
  * Pinnacle's de-vigged log-odds minus the average's adds beyond the current best: joint z **+2.98**. Inferred: Pinnacle is sharper than the average (an [A]-type signal at the average close).
  * **The current best beats the calibrated Pinnacle close** too: 2022–2024 +1.06 [+0.27, +1.85] mLL (better); 2014–2021 +0.21 [−0.37, +0.78] (tie). Against the calibrated average: +1.19 [+0.47, +1.91] and +0.28 [−0.28, +0.83]. Inferred: the model's edge is not just the average lagging Pinnacle.

## Exploratory, after the batch: what carries B-INJ (ledger row 23)

Each member was screened alone with B-INJ's controls. This cannot change the claim or the bundle; B-INJ enters whole. The gains are point estimates without intervals.

| Member | Non-zero in | joint z (model base) | z₁ | z₂ | Gain 2014–2021 | Gain 2022–2024 |
|---|---|---|---|---|---|---|
| **I-043 rust after a break of six weeks or more** | 100% (decays to ~0) | **+4.05** | +3.89 | +1.44 | +0.25 | +0.09 |
| I-044 returning from injury × reputation | 1.2% | +0.48 | +0.60 | −0.04 | −0.02 | −0.03 |
| I-045 within-event serve decay | 91% | +1.56 | +1.21 | +0.99 | +0.01 | +0.03 |

**Reading (inferred; corrected after the red team, [red_team.md](../meta/red_team.md)).**
* **What carries the block.** I-043, rust after a break of six weeks or more.
  * The registered "longer than the field's norm" condition almost never binds (it blocks 7 of 106,296 returns), so in effect every break of six weeks or more counts. Off-season returns carry about 60% of the rust. The block is not evidence of an "unplanned" layoff or of an injury.
  * The column grows with the length of the break and decays over the matches played since the return (half-weight after about 1.4 matches).
  * It is amplified by age past 28, a retirement or a walkover the player gave just before the break, and a protected ranking.
* **What it means for the price.** In 2014–2024, such players did worse than both the current best and the closing price expected; this was not confirmed on 2025–2026 ([README](../README.md)). Ratings, rank and the market's memory do not decay during a break; match sharpness does.
* **What it is not.** It is an interaction of break length with matches since the return, age and the last match's status, all within one player. It is not a serve/return statistic.
