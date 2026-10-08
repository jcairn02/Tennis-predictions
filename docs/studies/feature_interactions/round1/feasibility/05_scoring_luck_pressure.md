# Feasibility (G2) · family 05: Scoring luck, pressure and sequence

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/05_scoring_luck_pressure.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-025 | Conversion luck: results beyond the points | stage0 points won/played, past results; beta_f | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | – | 4 | **pass** | own history (99% main tour); each past result from lf + 1. beta_f must be fixed without this study's outcomes: walk-forward by season or from the iid model (M6); arm (b) is pair-level; not built here; coverage estimated (own history, 0 when empty); R2 in round 2 |
| I-026 | Big-point return skill × the scarcity of break points | stage4 bigpoint_return (Slam point files); IOS hold | 89 / 85 \| 86 / 85 | 8,593 | SAFE | no | 0.26 | 3 | **pass** | 89%/85% (2014-21), 86%/85% (2022-24). Sackmann's Slam point files stop in 2024: values go stale in 2025-26 unless the point-sequence table extends them; built here (x_bigpoint); swap ok; aug R2 0.30 |
| I-027 | Resilience excess: breaking back and consolidating | shot_level/stage3_sides break_back, consolidate (\|has) | 85 / 83 \| 97 / 92 | 8,593 | SAFE | no | 0.36 | 2 | **pass** | 85%/83% (2014-21), 97%/92% (2022-24). the point-sequence table (stable since 18:24) could rebuild it with more coverage; built here (x_resilience); swap ok; aug R2 0.38 |

## Auditor's notes

I-025 uses past results as inputs, which is allowed, but its β_f must not be fitted on the discovery outcomes in-sample: fix it walk-forward by season or from the iid model (M6). I-026 reads Sackmann's Slam point files, which end in 2024; its values go stale in the test years unless the point-sequence table extends them.
