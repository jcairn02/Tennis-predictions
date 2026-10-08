# Feasibility (G2) · family 02: Composition through the point model

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/02_composition_point_model.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-008 | The surface-IOS profile composed into a match log-odds | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (first_in, first_won, second_won); stage2_iid | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.98 | 2 | **defer** | novelty R2 0.980 >= 0.95. passes once declared as its remainder after a result-free projection on the 58 inputs (MAT's own residual rule); built here (z_C1); swap ok; aug R2 0.99 |
| I-009 | Games route and the points-versus-games residual | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (hold, serve components); stage2_iid | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.96 | 2 | **defer** | novelty R2 0.964 >= 0.95. same remedy as I-008; split-half reliability check is result-free; built here (r_games_minus_points); swap ok; aug R2 0.98 |
| I-010 | Noise-integrated composition | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw); V from stage3_shrinkage or tuned | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.97 | 2 | **defer** | novelty R2 0.970; V's tuning reads 2013-2018 results (no odds): declare V or its target. built with V = 0.04; built here (z_C4); swap ok; aug R2 0.98 |
| I-011 | The price on the point scale | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw); stage1_odds avg; stage2_iid | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.87 | 2 | **pass** | held; built here (R2 0.87). originator: screen only if I-008 passes; built here (d_pt); swap ok; aug R2 0.92 |
| I-012 | Free-point shield: aces beyond the returner's reach | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (ace, spw) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.95 | 2 | **defer** | novelty R2 0.954 (linear g). the elasticity function g must be declared; the returns-in-play arm is a field statistic (clock, probe; ~17,000 men's matches); built here (shield_x); swap ok; aug R2 0.97 |
| I-013 | Within-player squares that complete prod_s | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (ace, df, hold, first_won) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.60 | 1 | **pass** | held; sq_ace 0.60, sq_df 0.39, sq_hold 0.91. declare one hypothesis or one per statistic before M1; built here (sq_ace); swap ok; aug R2 0.63; sq_df R2 0.39; sq_first_won R2 0.89; sq_hold R2 0.91 |

## Auditor's notes

The composition family is almost linear in the 58 inputs: z_C1 0.980, the games route 0.964, the noise-integrated version 0.970 (in family 03, I-015 0.995; I-012 0.954). As raw columns these fail novelty. The remedy is the originator's own: declare the remainder after a projection on the 58 inputs fitted without outcomes (2013–2018) and report its SD. I-011 (0.87) and I-013's squares pass. I-010's variance V must be fixed before M1 without reading results.
