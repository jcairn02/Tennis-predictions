# Feasibility (G2) · family 12: Fatigue crossed with style and the point model (attrition)

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/12_fatigue_style_attrition.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-063 | Fatigue composed through the point model | stage3_ratings p_serve_a/b; stage2_iid; Fat | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.77 | 3 | **defer** | kappa, eta, lambda 'tuned on 2013-2018' with no stated target (M5). data pass (100%); R2 0.77 with kappa 0.01 fixed; built here (fatigue_composed); swap ok; aug R2 0.78 |
| I-064 | Own style × own fatigue | history.long_table minutes, games; the clock's es/lf (pre-rebuild); stage3 style | 84 / 61 \| 88 / 82 | 8,593 | SAFE | no | 0.83 | 1 | **pass** | R2 0.83. sign undeclared; inherits I-052's tau; built here (fat_x_sty); swap ok; aug R2 0.84 |
| I-065 | The opponent who exploits fatigue | history.long_table minutes, games; the clock's es/lf (pre-rebuild); points per match (pace) | 84 / 59 \| 88 / 82 | 8,593 | SAFE | no | 0.80 | 3 | **pass** | men 84%, women 59% (2014-21); 88%/82% (2022-24). no primary declared; IOS-based Ret2 is clock-built; built here (pace_x_oppfat); swap ok; aug R2 0.81 |
| I-066 | Rally pace × load and age: attrition exposure in minutes | stage0 minutes and points (pace); odds; model inputs | 100 / 72 \| 100 / 99 | 8,593 | SAFE | no | 0.94 | 2 | **pass** | men 99.9%, women 72% (2014-21); 99%/99% (2022-24). E_min x dsets R2 0.941 passes; E_min x dage 0.950 fails: dsets is the column; built here (emin_x_dsets); swap ok; aug R2 0.95; emin_x_dage R2 0.95 |
| I-067 | Heat × age × load × style | weather archive and venue coordinates: not on disk | – / – \| – / – | 8,593 | STATIC | no | – | 16 | **defer** | data not held. free historical weather (no paid API) plus a venue table; days of work; not built here; coverage estimated (data not held); R2 in round 2 |

## Auditor's notes

Data pass. I-063 is deferred for the same reason as I-052 (κ, η, λ). Pace (seconds per point) covers men fully and women 59–72% in 2014–21. I-067's weather is not held.
