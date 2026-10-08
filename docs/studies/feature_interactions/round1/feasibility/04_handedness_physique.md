# Feasibility (G2) · family 04: Handedness and physique

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/04_handedness_physique.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-021 | How each player serves to, and returns against, left-handers | stage0 hand, box scores; extended IOS with hand terms | 100 / 99 \| 100 / 98 | 8,593 | CLOCK-NEW | yes | – | 10 | **pass** | hand 98-100%; a new IOS solve on the clock. probe.py before any result; not built here; coverage estimated (both hands known); R2 in round 2 |
| I-022 | Kick second serve against a short returner | stage0 height; surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (second_won) | 100 / 93 \| 100 / 64 | 4,307 | STATIC | no | 0.49 | 1 | **pass** | men 99.8%/99.9%; women 93%/64% but test 1,624 of 4,199. claimed for men; women would pass G2 but not the test window; built here (x_kick); swap ok; aug R2 0.53 |
| I-023 | Height as the serve prior for thin histories | stage0 height; IOS ace; stage3 serve_pts | 100 / 93 \| 100 / 64 | 4,307 | STATIC | no | 0.45 | 2 | **pass** | as I-022; beta_h fitted result-free (height -> ace offence, 2014-2018 here). K_h = 5,000 points here; built here (x_height_prior); swap ok; aug R2 0.57 |
| I-024 | Height × age and height × load | stage0 height, age; Fat (I-052) | 84 / 57 \| 88 / 56 | 4,307 | SAFE | no | 0.80 | 2 | **pass** | h x Fat column only (R2 0.80; minutes-based Fat: men 84%/88%). h x (age - 28)+ fails novelty (0.958); Fat inherits I-052's tau; built here (h_x_fat); swap ok; aug R2 0.81; h_x_age28 R2 0.96 |

## Auditor's notes

Men's heights are near complete. Women's (93% in 2014–21, 64% in 2022–24) would pass G2, but only 1,624 of 4,199 women's test matches have both, so the originators' men-only claim stands. I-021 needs a new IOS solve with hand terms on the clock, then the probe. I-024's height × age fails novelty (0.958); height × Fat passes.
