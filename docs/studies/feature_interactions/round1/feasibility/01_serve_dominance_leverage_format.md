# Feasibility (G2) · family 01: Serve dominance, leverage and format

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/01_serve_dominance_leverage_format.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-001 | Price × the pair's serve-dominance leverage | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw); stage1_odds avg; best_of | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.23 | 3 | **pass** | all inputs held for every match; leak-proof IOS inherited. leverage curve from stage2_iid; aug R2 0.85 (TabPFN-formable from inputs x context); built here (x_lev); swap ok; aug R2 0.85 |
| I-002 | Serve-dominance compression of the rating gap | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw); stage2_iid | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.37 | 2 | **pass** | held; built here. Stage 3 p_serve is the alternative source; built here (comp); swap ok; aug R2 0.54; z_x_D R2 0.32 |
| I-003 | Pair serve dominance and tiebreak share as context | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.04 | 1 | **pass** | held; built here. context; tb_share variant not built; built here (m_pair); swap ok; aug R2 0.24 |
| I-004 | Four point-structure sums as context | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw, ace, first_in) | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.34 | 1 | **pass** | held; built here. sig3, sig4 overlap the adopted S2 levels arm; built here (sig1_SO_spw); swap ok; aug R2 0.50; sig2_SD_spw R2 0.26; sig3_SO_ace R2 0.10; sig4_SO_fi R2 0.01 |
| I-005 | Serve-point offence and defence as exchanged pairs | surface_ios/surface_features srf_O_eff/srf_D_eff _a/_b (spw) as pairs | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-BUILT | no | 0.52 | 1 | **pass** | the pair's sums are new (R2 0.52, 0.45); its differences alone would fail novelty (0.98). an enabler for TabPFN, not a screen term; built here (sO_spw); swap ok; aug R2 0.64; dD_spw R2 0.98; dO_spw R2 0.98; sD_spw R2 0.45 |
| I-006 | Best-of-five leverage the price under-transmits | stage3_ratings p_serve_a/b; best_of | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.33 | 1 | **pass** | held; built here. nonzero on Bo5 rows only (9.8%); aug R2 0.99: nearly ratings_iid x 1[bo5]; built here (L_bo5); swap ok; aug R2 0.99 |
| I-007 | Bo5 damping check (diagnostic) | model frame; reads 2013-2021 results | 100 / 100 \| 100 / 100 | 8,593 | WF-RESULTS | no | – | 1 | **pass** | diagnostic, no column; runs only inside the frozen screen batch (M5). its gating of I-001, I-003, I-010, I-011 must be pre-declared at M1, both branches; not built here; coverage estimated (model frame); R2 in round 2 |

## Auditor's notes

Every column is built from held inputs (surface IOS for serve points, Stage 3, the odds) and passes the full swap test. Two are close to what TabPFN can already form from an input and a context column: I-006 (augmented R² 0.99, essentially `ratings_iid` × best of five) and I-001 (0.85). That is not a G2 failure. I-007 reads results: it may run only inside the frozen screen, and its gating of I-001, I-003, I-010 and I-011 must be declared at M1.
