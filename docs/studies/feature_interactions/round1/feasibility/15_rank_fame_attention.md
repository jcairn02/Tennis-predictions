# Feasibility (G2) · family 15: Rank, fame, attention and visibility

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/15_rank_fame_attention.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-080 | Attention-modulated disagreement | stage0 rank, round; level; Delta1; same-day counts (timing es) | 100 / 100 \| 100 / 100 | 8,593 | WF-RESULTS | no | 0.16 | 3 | **pass** | 100%; R2 0.16 (crowding term not built). Delta1's scaling and N are walk-forward fits on results; built here (d1_x_negA); swap ok; aug R2 0.34 |
| I-081 | Profile weight by price level | model frame; odds | 100 / 100 \| 100 / 100 | 8,593 | WF-RESULTS | no | 0.67 | 1 | **pass** | R2 0.67. N is a walk-forward fit on results; built here (d1_x_lopsided); swap ok; aug R2 0.74 |
| I-082 | Salience-weighted evidence: form earned where nobody watches | stage0 box scores by level (men's Challenger 99%; ITF none) | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | – | 4 | **pass** | defined everywhere (weight 0 without low-visibility matches). women's low-visibility box scores are thin: measure in round 2; not built here; coverage estimated (weight 0 without evidence); R2 in round 2 |
| I-083 | Fallen-star premium | stage0 titles and Slam QFs (built); pieces Elo peak (built) | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.46 | 2 | **pass** | 100%; R2 0.46. built here (fame_x_fall); swap ok; aug R2 0.52 |
| I-084 | Pair prominence modulates how much the price knows | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw) or Elo levels; odds | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.27 | 1 | **pass** | 100%; R2 0.27. Elo levels: pieces R_a/R_b; built here (z_x_SigmaT); swap ok; aug R2 0.35 |

## Auditor's notes

All built. N-based secondaries need walk-forward fits on results inside the screen.
