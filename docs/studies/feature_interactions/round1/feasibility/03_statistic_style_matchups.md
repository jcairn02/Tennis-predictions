# Feasibility (G2) · family 03: Style matchups between specific statistics

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/03_statistic_style_matchups.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-014 | Second-serve exposure × the returner's second-serve specialisation | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (first_in, first_won, second_won) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.61 | 1 | **pass** | held; R2 0.61. w1 = w2 = 1 here; built here (x_exposure); swap ok; aug R2 0.64 |
| I-015 | Second-serve exposure against second-serve return | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (first_in, second_won) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.99 | 1 | **defer** | novelty R2 0.995. interpretable form of I-008; same remedy; built here (E2); swap ok; aug R2 1.00 |
| I-016 | Risky second servers against second-serve attackers | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (df, second_won) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.72 | 1 | **pass** | held; R2 0.72. two-sided; built here (x_risky); swap ok; aug R2 0.80 |
| I-017 | Total strength against style difference (structural null) | model frame in_iosO_s, in_iosD_s | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 1.00 | 0 | **defer** | R2 1.000: a rotation of inputs. not a candidate column; at most a representation test of the screen, outside G2; built here (dY_ace); swap ok; aug R2 1.00 |
| I-018 | Style-pair residual table | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b; stage0 hand, box scores; k-means styles | 100 / 99 \| 100 / 98 | 8,593 | CLOCK-NEW | yes | – | 8 | **pass** | inputs held (IOS 100%, hand 98-100%); the residual table is a field statistic. centroids frozen on 2010-2016; tau_ij must be rebuilt day by day on timing.parquet and probed; not built here; coverage estimated (both hands known); R2 in round 2 |
| I-019 | Points-based head-to-head residual | stage0 meetings and box scores; IOS expectations at each meeting | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.06 | 4 | **pass** | defined everywhere (0 without meetings); 60% of rows have a meeting. expectations at past meetings from surface_features (pool matches) or Stage 3; built here (h2h_any); swap ok; aug R2 0.15 |
| I-020 | Lost first-serve speed × the returner | shot_level/stage3_sides spd1_change (\|has); surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw) | 70 / 68 \| 95 / 84 | 7,608 | SAFE | no | 0.27 | 2 | **pass** | both players' speed history 70%/68% (2014-21), 95%/84% (2022-24); test 4,103 + 3,505. brief's direction to watch; scored on 2022-2026 earlier (critique M5: cannot be confirmed in 2025-26); built here (x_speed); swap ok; aug R2 0.32 |

## Auditor's notes

The IOS products pass (I-014 0.61, I-016 0.72). I-017 is a rotation of inputs (R² 1.00), not a column. I-018 is a field statistic (the clock, then probe.py). 60% of matches have an earlier meeting for I-019. I-020's speed history covers 70% / 68% and 95% / 84% of matches, but the men's serve-speed signal was already scored on 2022–2026.
