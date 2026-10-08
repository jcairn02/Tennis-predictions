# Feasibility (G2) · family 08: Price calibration and anchor construction

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/08_price_calibration_anchor.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-035 | Margin-aware de-vig | stage1_odds avg_a/b, overround | 100 / 100 \| 100 / 100 | 8,593 | MARKET | no | 0.92 | 1 | **pass** | R2 0.92 (a convex function of the price). a de-vig variant of the anchor; also an input-replacement candidate; built here (shin_gap); swap ok; aug R2 0.93 |
| I-036 | Obscure-match slope: FLB by level, round and fame | stage0 rank (unranked rule); odds | 100 / 100 \| 100 / 100 | 8,593 | MARKET | no | 0.27 | 1 | **pass** | rank 99.7%; R2 0.27. built here (z_x_obscure); swap ok; aug R2 0.32 |
| I-037 | Book dispersion as uncertainty | stage1_odds max_a/b; avg | 100 / 100 \| 100 / 100 | 8,593 | MARKET | no | 0.05 | 1 | **pass** | R2 0.05. Max may include exchanges (unknown); built here (z_x_arb); swap ok; aug R2 0.06 |
| I-038 | Best-price skew: steam or shading, told apart by fame | stage1_odds max, avg, b365; fame from stage0 history (titles, Slam QFs) | 100 / 100 \| 100 / 100 | 8,593 | MARKET | no | 0.07 | 2 | **pass** | R2 0.07 / 0.51. fame built here from own history; built here (k_x_fam); swap ok; aug R2 0.08; k_x_notfam R2 0.51 |
| I-039 | Sharp–soft split (diagnostic) | stage1_odds Pinnacle; N (walk-forward ridge on results) | 100 / 99 \| 100 / 99 | 5,054 | WF-RESULTS | no | 0.46 | 2 | **pass** | Pinnacle 99.4% (2014-24); test only 2,580 + 2,474 (Pinnacle ends Jan 2026). diagnostic; N is fitted on results by season inside the screen; built here (sharp_minus_avg); swap ok; aug R2 0.48 |
| I-040 | Context-dependent recalibration of the adjustment | current best's walk-forward forecasts (2014-2024 held); contexts | 100 / 100 \| 100 / 100 | 8,593 | WF-RESULTS | no | 0.12 | 2 | **pass** | forecasts exist for every 2014-2024 match. a calibration-layer term; contexts to fix (1-3); built here (c_x_adj); swap ok; aug R2 0.18 |
| I-041 | Non-linear shrinkage of the adjustment | as I-040 | 100 / 100 \| 100 / 100 | 8,593 | WF-RESULTS | no | 0.42 | 1 | **pass** | R2 0.42. the screen's own cubic is in eta, not in the adjustment; built here (adj_cubed); swap ok; aug R2 0.52 |

## Auditor's notes

Every quote is held for 2014–2024 (average, best, Pinnacle, Bet365: 99.4% or more). Pinnacle stops in January 2026, so I-039 has 5,054 of 8,593 test matches. The current best's walk-forward forecasts now exist for every 2014–2024 match (M1), so I-040 and I-041 can be built. **No opening odds exist on disk before 2025** (tennis-data.co.uk is closing only; Polymarket covers 2025–26; the BetOnline lines in docs/research cover 2024–26 and are not held): the critique's C5 discovery move test cannot run.
