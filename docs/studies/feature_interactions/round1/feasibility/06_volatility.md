# Feasibility (G2) · family 06: Volatility

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/06_volatility.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-028 | Within-match streakiness compresses the price | stage0 set scores (100%); Stage 3 expectations; point data where held | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | – | 4 | **pass** | set scores held for every match. one definition (dispersion vs variance) must be fixed; not built here; coverage estimated (set scores); R2 in round 2 |
| I-029 | The pair's day-to-day variance flattens the odds | ufc_ideas/stageB_adj z (own matches); or IOS residuals | 99 / 96 \| 100 / 98 | 8,593 | SAFE | no | 0.06 | 3 | **pass** | Stage B z route: 99%/96% (2014-21), 99.5%/98% (2022-24). the IOS-residual route would be cross-player: clock and probe; built here (z_x_Vpair); swap ok; aug R2 0.08 |
| I-030 | Volatility compression: the price prices means, not variance | stageB_adj z_tpw, 52 weeks; or predictive_frontier | 99 / 96 \| 100 / 98 | 8,593 | SAFE | no | 0.06 | 2 | **pass** | as I-029 (built here as the z variance). frontier's variability was scored on 2022+ (contaminated); built here (z_x_V); swap ok; aug R2 0.08 |

## Auditor's notes

Built from Stage B's per-match z (each player's own matches; opponents' norms from their earlier matches): coverage 96% or more, R² about 0.06. Residuals against IOS would be cross-player and need the clock and the probe. I-028 needs set scores parsed from the score strings (all held).
