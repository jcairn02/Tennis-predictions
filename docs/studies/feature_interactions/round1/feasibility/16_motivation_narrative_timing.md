# Feasibility (G2) · family 16: Motivation, narrative and information timing

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/16_motivation_narrative_timing.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-085 | Drifting favourite: over-reaction to news against the ratings favourite | walk-forward no-odds forecasts; odds | 38 / 32 \| 100 / 100 | 8,593 | WF-RESULTS | no | – | 2 | **defer** | no-odds forecasts exist only for 2019-2026: 2014-21 coverage 38% (men), 32% (women) < 50%. fit the no-odds arm for 2014-2018 (about 15 local fits) or declare a cheaper walk-forward price-free forecast; not built here; coverage estimated (no-odds forecasts from 2019 only); R2 in round 2 |
| I-086 | Last-round narrative: surprise wins and flattering scorelines | stage1_odds of the previous match; stage0 rounds | 43 / 45 \| 42 / 44 | 8,593 | MARKET | no | 0.16 | 2 | **defer** | coverage 43%/45% (2014-21) < 50%: no rule when the previous match was lost or unpriced. declare one missingness rule (critique S11); then 100%; built here (d_surprise_x_late); swap ok; aug R2 0.20 |
| I-087 | Price-formation window | timing es, lf (days); Delta1, N | 100 / 100 \| 100 / 100 | 8,593 | WF-RESULTS | no | 0.57 | 1 | **pass** | 100%; R2 0.57. day resolution only; built here (d1_x_short_window); swap ok; aug R2 0.60 |
| I-088 | Title last week: recency premium against a letdown | stage0 previous event title (built); the clock | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.06 | 1 | **pass** | 100%; nonzero on 2.3% of rows. built here (title_x_first); swap ok; aug R2 0.07 |
| I-089 | Calendar motivation | stage0 calendar, rank (built); points-to-defend table (not on disk) | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.03 | 2 | **pass** | primary built (100%; nonzero 1.4%). the 'def' secondary needs a hand-made points table; built here (top_x_pre_x_late); swap ok; aug R2 0.05 |
| I-090 | Elite effort before Slams; incentive cliffs | stage0 rank, level, Slam dates (built) | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.03 | 1 | **pass** | 100%; nonzero 1.7%. thresholds to declare in advance; built here (elite_pre_slam); swap ok; aug R2 0.05 |
| I-091 | Public narrative statistics: head-to-head and venue records | stage0 meetings (built); tournament ids across seasons | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.11 | 2 | **pass** | 100%; R2 0.11. the venue-record secondary needs tournament-id continuity checks; built here (h2h_raw_n3); swap ok; aug R2 0.12 |

## Auditor's notes

I-085 lacks no-odds forecasts before 2019 (coverage 38% men, 32% women). I-086 needs a missingness rule (coverage 43–45%). I-089's points-to-defend secondary needs a hand-made table. The others pass with small informative subsets (1.4–2.3% non-zero).
