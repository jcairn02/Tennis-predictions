# Feasibility (G2) · family 09: Retirement, injury and settlement

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/09_retirement_injury_settlement.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-042 | Retirement hazard × price (settlement and fragility) | stage0 status (retired, walkover) at all levels; odds | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.43 | 3 | **pass** | 100%; R2 0.43. variant (c) pools other players' finished seasons: by season only (safe); settlement rules unverified; built here (tau_hazard); swap ok; aug R2 0.46 |
| I-043 | Rust after an unplanned layoff × age × how it began | stage0 gaps, retirements, entry codes; E[gap] frozen 2010-2018 | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.23 | 3 | **pass** | 100%; R2 0.23. E[gap] must use no outcome (calendar only); built here (rust); swap ok; aug R2 0.27 |
| I-044 | Returning from injury: reputation against rust | stage0 status, dates; pieces Elo | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.01 | 2 | **pass** | 100%; nonzero on 1.0% of rows. power is the math auditor's call; near-duplicate of I-043; built here (inj_return); swap ok; aug R2 0.03 |
| I-045 | Within-event serve decay: a fatigue or injury sensor | stage0 box scores of this event's earlier rounds; profile; speeds (partial) | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.74 | 4 | **pass** | both players with an earlier on-site match: 46% of rows (0 otherwise). per-match residual slopes to build; speed variant partial; built here (both_onsite); swap ok; aug R2 0.74 |

## Auditor's notes

Own history (status, gaps, Elo) covers every match. I-044 is non-zero on 1% of rows, a power question for the mathematical auditor. The point-sequence study tested related questions on 2014–2024 outcomes today (E1: medical events and the next match; B1: carry-over of finishing form). That look sits outside this study's ledger and concerns I-042, I-044 and I-045.
