# Feasibility (G2) · family 07: Reliability, evidence and uncertainty

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/07_reliability_evidence_uncertainty.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-031 | Re-anchor the two-week form on each player's long-memory level | stageB_adj z; perplayer_form (rebuilt); 52-week z level | 100 / 99 \| 100 / 99 | 8,593 | SAFE | no | 0.70 | 3 | **pass** | 98.7-99.8% everywhere; R2 0.70. K' and the long level must be declared; replace or join form_s: declare; built here (d_reanchor); swap ok; aug R2 0.74 |
| I-032 | Unknown is not average: the evidence behind each IOS value | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b; evidence per player (IOS information or surface unit counts) | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.95 | 3 | **defer** | the weighted IOS statistic is not declared; the spw-net version with surface-count weights has R2 0.953. pass once the statistic and r's source are declared and R2 < 0.95; built here (net_x_rbar); swap ok; aug R2 0.98 |
| I-033 | Flux: when short and long memory disagree | as I-031; stage1_odds avg | 100 / 99 \| 100 / 99 | 8,593 | SAFE | no | 0.27 | 2 | **pass** | R2 0.27. statistic behind form to declare (tpw here); built here (z_x_flux); swap ok; aug R2 0.29 |
| I-034 | Conflict shrinkage: statistics and ratings disagree | model frame ratings_iid, elo_overall, elo_surf_offset; odds | 100 / 100 \| 100 / 100 | 8,593 | WF-RESULTS | no | 0.67 | 1 | **pass** | R2 0.67. Delta1's rescaling constants are walk-forward fits on results: computed inside the screen (M6); built here (z_x_absD1); swap ok; aug R2 0.75 |

## Auditor's notes

I-031 and I-033 use the rebuilt per-player profile and pass. I-032 fails novelty as built here (0.953) only because its statistic and evidence source are undeclared. Δ1's scaling constants (I-034) are walk-forward fits on results and belong inside the screen.
