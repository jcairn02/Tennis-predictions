# Feasibility (G2) · family 14: Travel, venue and conditions

6 October 2026 · feasibility auditor, round 1 · [summary](../feasibility.md) · [family table](../../master_list/14_travel_venue_conditions.md)

Coverage = share of matches with the column defined for both players: men / women, 2014–21 | 2022–24 (%). R² = on the 58 inputs, 2014–21, plain OLS (aug = with context × difference or |difference|, d² terms). Test n = 2025–26 model rows of the claimed tours (counts only). Timing codes: see the summary.

| ID | Title | Data | Coverage | Test n | Timing | Probe | R² | Build h | Verdict | Reason / what is missing |
|---|---|---|---|---|---|---|---|---|---|---|
| I-072 | Leak-proof venue pace × each player's serve/return shape | stage0 box scores by tournament id; IOS expectations | 100 / 100 \| 100 / 100 | 8,593 | CLOCK-NEW | yes | – | 8 | **pass** | box scores held; venue keys from tournament ids. a field statistic: day-by-day on timing.parquet, then probe.py; venue continuity across editions to check; not built here; coverage estimated (box-score history by event); R2 in round 2 |
| I-073 | Per-player indoor deviations in the profile | stage0 indoor; extended IOS with an indoor term | 100 / 0 \| 100 / 0 | 4,394 | CLOCK-NEW | yes | – | 10 | **pass** | men only: indoor flags exist for men's main-tour matches only (Challenger 0.2%, ITF 0%; women none). the indoor term is estimated from main-tour history; probe.py before any result; not built here; coverage estimated (indoor flag: men only); R2 in round 2 |
| I-074 | Jet lag: zones × days since the last match × direction | city -> UTC offset table (not on disk); the clock | – / – \| – / – | 8,593 | SAFE | no | – | 6 | **defer** | time-zone table not held. build from event cities (tennis-data Location for the main tour; lower levels from names and ids); not built here; coverage estimated (table not held); R2 in round 2 |
| I-075 | On-site acclimatisation × how new the conditions are | tables of I-074, I-050, I-077 | – / – \| – / – | 8,593 | SAFE | no | – | 3 | **defer** | depends on three tables not yet built. not built here; coverage estimated (tables not held); R2 in round 2 |
| I-076 | Event rhythm against a cold start | stage0 entries, qualifying (same tournament id in 98% of Q entrants); the clock | 100 / 100 \| 100 / 100 | 8,593 | SAFE | no | 0.43 | 2 | **pass** | 100%; R2 0.43. the cartographer's question answered: qualifying links to its main draw; built here (rhythm_vs_cold); swap ok; aug R2 0.44 |
| I-077 | Altitude × serve profile × acclimatisation | venue elevation table (not on disk); stage0 | – / – \| – / – | 8,593 | STATIC | no | – | 2 | **defer** | elevation table not held. about a dozen high venues; a hand-made public table; small subgroup; not built here; coverage estimated (table not held); R2 in round 2 |
| I-078 | Home split into crowd and no travel | stage0 country; event country (stage4 table); JL from I-074 | 100 / 100 \| 100 / 100 | 8,593 | STATIC | no | 0.06 | 2 | **pass** | home x not-Slam built (100%); R2 0.06. g(level) unspecified; the JL column waits for I-074; built here (home_x_notslam); swap ok; aug R2 0.09 |
| I-079 | Home hype: home wildcards and home players at small events | stage0 country, entry; event country | 100 / 100 \| 100 / 100 | 8,593 | STATIC | no | 0.12 | 1 | **pass** | 100%; R2 0.12. Kingston blank; Monte Carlo coded Monaco; built here (home_x_wc); swap ok; aug R2 0.14 |

## Auditor's notes

I-072 and I-073 are cross-player: build on the clock, then probe.py; I-073 is men only. I-074, I-075 and I-077 wait for tables not on disk (time zones, elevations). Indoor flags exist only for men's main-tour matches (Challenger 0.2%, ITF 0%), so I-073's indoor term learns from main-tour history only. The cartographer's I-076 question is answered: 98% of qualifiers' qualifying matches share the main draw's tournament id.
