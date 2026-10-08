# Feasibility (G2) · family 10: Surface switching and profile staleness

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/10_surface_switching_staleness.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-046 | Early in a surface season, return-heavy profiles are stalest | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw); pieces season_n | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.21 | 1 | **pass** | R2 0.21. q = 1[n < 3] here: declare the threshold; built here (g_early); swap ok; aug R2 0.29 |
| I-047 | Surface-switch adaptation by style and by age | pieces season_n, days_since; stage3 serve/return; stage0 age | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.12 | 1 | **pass** | R2 0.12 / 0.11. no primary declared: two columns; built here (new_x_sty); swap ok; aug R2 0.20; new_x_age R2 0.11 |
| I-048 | A stale surface profile: reliability by surface layoff | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b srf_E/srf_F (spw); pieces NS, days_since | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.38 | 2 | **pass** | R2 0.38. reweights the surface deviations the surface-IOS study scored (sdev arm, tie, 2022-26); built here (stale_dev); swap ok; aug R2 0.48 |
| I-049 | Early-surface-season under-confidence of the price | model frame surf_season pairs; odds | 100 / 100 \| 100 / 100 | 8,593 | MARKET | no | 0.28 | 1 | **pass** | R2 0.28. motivating slopes fitted on 2013-2025; built here (z_x_early); swap ok; aug R2 0.38 |
| I-050 | Indoor/outdoor switch × serve style | stage0 indoor of this and the previous match; stage3 style | 88 / 0 \| 89 / 0 | 4,394 | SAFE | no | 0.10 | 2 | **pass** | men 88%/89%; women 0%: Stage 0 has no women's indoor flag, and tennis-data's Court covers only priced main-tour matches. men only; women not buildable from held data; built here (inout_x_sty); swap ok; aug R2 0.16 |

## Auditor's notes

All five are built and pass. I-048 reweights the surface deviations whose arm (sdev) the surface-IOS study scored as a tie on 2022–26. I-050 is men only: no women's indoor flag exists for their earlier matches.
