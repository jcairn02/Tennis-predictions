# Feasibility (G2) · family 13: Age and career trajectory

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/13_age_trajectory.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-068 | Age reshapes the profile: return and rally decay first | stage0 age; surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.14 | 1 | **pass** | R2 0.14. built here (age_x_shape); swap ok; aug R2 0.27 |
| I-069 | Style-specific ageing: servers age more slowly | stage3 serve/return; stage0 age | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.40 | 1 | **pass** | R2 0.40. M (profile memory) is a constant per tour; built here (style_age_drift); swap ok; aug R2 0.51 |
| I-070 | Age-dependent trust in recent form | perplayer_form; 52-week z level; stage0 age | 100 / 99 \| 100 / 99 | 8,593 | SAFE | no | 0.21 | 2 | **pass** | R2 0.21. the short and long profiles must be declared; built here (age_trust_form); swap ok; aug R2 0.25 |
| I-071 | Rank anchoring × career trajectory | stage0 rank, age; pieces Elo; rank->Elo line (result-free, earlier seasons) | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.20 | 2 | **pass** | 99.5-99.8%; R2 0.20. the line is fitted on Elo and rank only; built here (rank_vs_elo_x_age); swap ok; aug R2 0.25 |

## Auditor's notes

All four are built; R² 0.14–0.40.
