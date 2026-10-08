# Feature interactions: the master list of round-0 ideas

6 October 2026 · Synthesizer (round 1, step 1 of [plan.md](plan.md)) · Research evidence, not a decision.

This is bookkeeping. It merges the four brainstormers' lists into one ID space so the mathematical and feasibility auditors can rule on every idea and the brainstormers can rebut. Nothing here judges, ranks, kills or improves an idea. Every row keeps its provenance and links to its source section; the originators' formulas are quoted where they are rewritten.

**Read:** [brief.md](brief.md), [team.md](team.md), [plan.md](plan.md), the critique's M2, S5, S6 and section 6 ([team_critique.md](round0/team_critique.md)), and the four lists in full: [mechanics](round0/ideas_mechanics.md) (MEC-), [mathematics](round0/ideas_mathematics.md) (MAT-), [market](round0/ideas_market.md) (MKT-), [body and schedule](round0/ideas_body.md) (BOD-). **Not read**, to stay neutral: the literature scout's and the cartographer's files, and any data.

**Files.** One table per family under [master_list/](master_list/); [withdrawn.md](master_list/withdrawn.md) (ideas their originators closed); [merges.md](master_list/merges.md) (the merges and the near-duplicates kept apart); a machine-readable copy in `data/studies/feature_interactions/master_list.csv`.

## The merge rule

Adopted from the critique's S5: ideas merge **only** when they are algebraically identical in the modulator × difference basis, with the same population. In practice: the same primary column built from the same per-player quantity, differing at most in construction constants (window, decay, shrinkage, centring, normalisation), in residualisation (a choice of control in a linear screen), or in the estimator of that same quantity, which stays inside the row as a named variant. Ideas that share a mechanism but differ in formula stay separate and are cross-referenced as a cluster. A lens count gives no prior. Four merges were made, absorbing five source rows ([merges.md](master_list/merges.md)); the hazard merge I-042 is the most contestable.

## Counts

| Source | Live ideas | Closed by the originator | Master rows |
|---|---|---|---|
| Mechanics (MEC) | 21 | 9 set aside | 21 rows, 3 of them merged |
| Mathematics (MAT) | 20 (one a diagnostic) | 7 killed by calculation | 20 rows, 4 of them merged |
| Market (MKT) | 25 (one a diagnostic) | 4 "not proposed" | 25 rows, 1 of them merged |
| Body and schedule (BOD) | 30 | 0 | 30 rows, 1 of them merged |
| **Total** | **96** | **20** (W-01 … W-20) | **91 master IDs** (I-001 … I-091) |

| Family | Rows | IDs |
|---|---|---|
| [01 Serve dominance, leverage and format](master_list/01_serve_dominance_leverage_format.md) | 7 | I-001 … I-007 |
| [02 Composition through the point model](master_list/02_composition_point_model.md) | 6 | I-008 … I-013 |
| [03 Style matchups between specific statistics](master_list/03_statistic_style_matchups.md) | 7 | I-014 … I-020 |
| [04 Handedness and physique](master_list/04_handedness_physique.md) | 4 | I-021 … I-024 |
| [05 Scoring luck, pressure and sequence](master_list/05_scoring_luck_pressure.md) | 3 | I-025 … I-027 |
| [06 Volatility](master_list/06_volatility.md) | 3 | I-028 … I-030 |
| [07 Reliability, evidence and uncertainty](master_list/07_reliability_evidence_uncertainty.md) | 4 | I-031 … I-034 |
| [08 Price calibration and anchor construction](master_list/08_price_calibration_anchor.md) | 7 | I-035 … I-041 |
| [09 Retirement, injury and settlement](master_list/09_retirement_injury_settlement.md) | 4 | I-042 … I-045 |
| [10 Surface switching and profile staleness](master_list/10_surface_switching_staleness.md) | 5 | I-046 … I-050 |
| [11 Workload and recovery](master_list/11_workload_recovery.md) | 12 | I-051 … I-062 |
| [12 Fatigue × style and the point model (attrition)](master_list/12_fatigue_style_attrition.md) | 5 | I-063 … I-067 |
| [13 Age and career trajectory](master_list/13_age_trajectory.md) | 4 | I-068 … I-071 |
| [14 Travel, venue and conditions](master_list/14_travel_venue_conditions.md) | 8 | I-072 … I-079 |
| [15 Rank, fame, attention and visibility](master_list/15_rank_fame_attention.md) | 5 | I-080 … I-084 |
| [16 Motivation, narrative and information timing](master_list/16_motivation_narrative_timing.md) | 7 | I-085 … I-091 |

Families are mechanism clusters defined for this list; a row sits in one family and cross-references the others in its notes.

## Notation used in every family table

* **η** is the screen's offset, the current best's out-of-sample log-odds (critique §6); **ℓ = z = z_mkt** is the de-vigged closing log-odds (`odds_logit`). Δx = x_A − x_B, Σx = x_A + x_B.
* **The M2 basis.** Every primary column is written as a symmetric modulator **s** times an antisymmetric difference **d**, or as the composed (C), weighted (U) or price (M) quantity. Identities used: cross-player O_A·D_B − O_B·D_A = ½[ΔO·ΣD − ΣO·ΔD]; within-player product x_A·y_A − x_B·y_B = ½[Δx·Σy + Σx·Δy]; square x_A² − x_B² = Δx·Σx.
* **Swap** gives the originator's stated behaviour (anti/diff, sym/context, pair) and whether the rewrite agrees. It agrees in every row that has a column (I-007 is a diagnostic with none); no swap disagreement was found.
* **Controls** are the critique's M2 marginality set for the row's type, plus the main effects the originator named. **M-set** = η, η³ and η·\|η\| per tour. **S**: d and s·η. **W**: the linear differences (a quadratic W also its S-form's sum × η). **X**: the differences, each sum × η, the existing `prod_<s>`. **C**: the linear part of the composition. **U**: the unweighted difference. **Std** (every row): the one to three nearest existing inputs, chosen without results, and missingness (miss_A − miss_B; the symmetric missing indicator × η). The price version replaces η by the price.
* **Anchor** classes [I] (information) and [A] (an artefact of the average close) are the market lens's own; other lenses gave none.
* Effects are the originators' priors in mLL of gain (higher is better), not measurements.

## For the auditors: pointers, not verdicts

* **Merges to confirm or split:** I-001, I-008, I-028 and, first, I-042 (three hazard estimators kept as variants).
* **Diagnostics or representations, not features:** I-007 (the Bo5 damping check that its originator says gates I-001, I-003, I-010, I-011), I-039 (sharp–soft split), I-017 (a rotation of existing inputs).
* **Construction that reads results or leaves the tuning target open** (look-ledger rows): I-007, I-010 (V tuned by a no-odds log loss), I-052 and I-063 (constants "tuned on 2013–2018", target not stated), I-025 (β_f fitted on 2010–2018 outcomes).
* **Prior evidence that includes 2025–2026 seasons** as cited by the originators (critique S6): I-006, I-020, I-030, I-035, I-037, I-049, I-063, I-071, I-080, I-085, I-086, I-087.
* **Data not on disk:** I-067 (weather), I-074 (time zones), I-077 (elevations), I-060 (continent map), I-089's "def" (points table). **Partial coverage:** I-020, I-026, I-027 (point or speed data); I-022, I-023 (men only); I-050, I-073 (women's indoor flag missing).
* **Type labels that differ from the formula:** I-025 arm (b) and I-056 (typed M, no price term); I-017 (typed X, a linear rotation).
* **No declared sign:** I-016, I-064, I-079, I-081; I-001's sources differ in sidedness. **Several columns, no declared primary:** I-013, I-024, I-031, I-047, I-051, I-065, I-066, I-070, I-072, I-078.

## All master IDs

Each ID links to its family table, which holds the full row and the link to the source section.

| ID | Title | Family | Type | Provenance |
|---|---|---|---|---|
| [I-001](master_list/01_serve_dominance_leverage_format.md) | Price × the pair's serve-dominance leverage | 01 | M × S | MEC-01 + MAT-M1 |
| [I-002](master_list/01_serve_dominance_leverage_format.md) | Serve-dominance compression of the rating gap | 01 | C (M × S secondary) | MKT-04 |
| [I-003](master_list/01_serve_dominance_leverage_format.md) | Pair serve dominance and tiebreak share as context | 01 | S (enabler) | MAT-C3 |
| [I-004](master_list/01_serve_dominance_leverage_format.md) | Four point-structure sums as context | 01 | S | MEC-02 |
| [I-005](master_list/01_serve_dominance_leverage_format.md) | Serve-point offence and defence as exchanged pairs | 01 | S (enabler) | MAT-S1 |
| [I-006](master_list/01_serve_dominance_leverage_format.md) | Best-of-five leverage the price under-transmits | 01 | C, S | MKT-03 |
| [I-007](master_list/01_serve_dominance_leverage_format.md) | Bo5 damping check (diagnostic) | 01 | M × S (diagnostic) | MAT-M5 |
| [I-008](master_list/02_composition_point_model.md) | The surface-IOS profile composed into a match log-odds | 02 | C | MEC-05 + MAT-C1 |
| [I-009](master_list/02_composition_point_model.md) | Games route and the points-versus-games residual | 02 | C (X) | MAT-C2 |
| [I-010](master_list/02_composition_point_model.md) | Noise-integrated composition | 02 | C | MAT-C4 |
| [I-011](master_list/02_composition_point_model.md) | The price on the point scale | 02 | C × M | MAT-C5 |
| [I-012](master_list/02_composition_point_model.md) | Free-point shield | 02 | C / X | MEC-04 |
| [I-013](master_list/02_composition_point_model.md) | Within-player squares that complete `prod_s` | 02 | W (X) | MAT-W1 |
| [I-014](master_list/03_statistic_style_matchups.md) | Second-serve exposure × the returner's second-serve specialisation | 03 | X | MEC-06 |
| [I-015](master_list/03_statistic_style_matchups.md) | Second-serve exposure against second-serve return | 03 | X | MAT-X2 |
| [I-016](master_list/03_statistic_style_matchups.md) | Risky second servers against second-serve attackers | 03 | X | MEC-07 |
| [I-017](master_list/03_statistic_style_matchups.md) | Total strength against style difference (structural null) | 03 | X (representation) | MAT-X1 |
| [I-018](master_list/03_statistic_style_matchups.md) | Style-pair residual table | 03 | X | MEC-10 |
| [I-019](master_list/03_statistic_style_matchups.md) | Points-based head-to-head residual | 03 | X (pair-specific) | MEC-11 |
| [I-020](master_list/03_statistic_style_matchups.md) | Lost first-serve speed × the returner | 03 | X | MEC-21 |
| [I-021](master_list/04_handedness_physique.md) | Serving to, and returning against, left-handers | 04 | X | MEC-09 |
| [I-022](master_list/04_handedness_physique.md) | Kick second serve against a short returner | 04 | X | MEC-12 |
| [I-023](master_list/04_handedness_physique.md) | Height as the serve prior for thin histories | 04 | U / W | MEC-16 |
| [I-024](master_list/04_handedness_physique.md) | Height × age and height × load | 04 | W | BOD-29 |
| [I-025](master_list/05_scoring_luck_pressure.md) | Conversion luck: results beyond the points | 05 | W | MEC-08 |
| [I-026](master_list/05_scoring_luck_pressure.md) | Big-point return skill × the scarcity of break points | 05 | S | MEC-18 |
| [I-027](master_list/05_scoring_luck_pressure.md) | Resilience excess: breaking back and consolidating | 05 | W (S arm) | MEC-19 |
| [I-028](master_list/06_volatility.md) | Within-match streakiness compresses the price | 06 | U / M; S × U | MEC-17 + MAT-S5 |
| [I-029](master_list/06_volatility.md) | The pair's day-to-day variance flattens the odds | 06 | S (× U) | MAT-S4 |
| [I-030](master_list/06_volatility.md) | Volatility compression: the price prices means | 06 | U; M × S | MKT-05 |
| [I-031](master_list/07_reliability_evidence_uncertainty.md) | Re-anchor the two-week form on the long-memory level | 07 | U (W) | MAT-U1 |
| [I-032](master_list/07_reliability_evidence_uncertainty.md) | Unknown is not average: evidence behind each IOS value | 07 | U | MAT-U2 |
| [I-033](master_list/07_reliability_evidence_uncertainty.md) | Flux: when short and long memory disagree | 07 | U × M (S) | MAT-U4 |
| [I-034](master_list/07_reliability_evidence_uncertainty.md) | Conflict shrinkage: statistics and ratings disagree | 07 | U, M | MKT-08 |
| [I-035](master_list/08_price_calibration_anchor.md) | Margin-aware de-vig | 08 | M | MKT-01 |
| [I-036](master_list/08_price_calibration_anchor.md) | Obscure-match slope | 08 | M × S | MKT-06 |
| [I-037](master_list/08_price_calibration_anchor.md) | Book dispersion as uncertainty | 08 | U | MKT-14 |
| [I-038](master_list/08_price_calibration_anchor.md) | Best-price skew: steam or shading | 08 | M | MKT-15 |
| [I-039](master_list/08_price_calibration_anchor.md) | Sharp–soft split (diagnostic) | 08 | S (agreement indicator) | MKT-16 |
| [I-040](master_list/08_price_calibration_anchor.md) | Context-dependent recalibration of the adjustment | 08 | M × U | MAT-M2 |
| [I-041](master_list/08_price_calibration_anchor.md) | Non-linear shrinkage of the adjustment | 08 | M | MAT-M3 |
| [I-042](master_list/09_retirement_injury_settlement.md) | Retirement hazard × price | 09 | W × M | MAT-W2 + MKT-20 + BOD-12 |
| [I-043](master_list/09_retirement_injury_settlement.md) | Rust after an unplanned layoff | 09 | W | BOD-13 |
| [I-044](master_list/09_retirement_injury_settlement.md) | Returning from injury: reputation against rust | 09 | W, U | MKT-21 |
| [I-045](master_list/09_retirement_injury_settlement.md) | Within-event serve decay | 09 | W | BOD-30 |
| [I-046](master_list/10_surface_switching_staleness.md) | Early in a surface season, return-heavy profiles are stalest | 10 | W / U | MEC-15 |
| [I-047](master_list/10_surface_switching_staleness.md) | Surface-switch adaptation by style and by age | 10 | W | BOD-20 |
| [I-048](master_list/10_surface_switching_staleness.md) | A stale surface profile: reliability by surface layoff | 10 | U | BOD-21 |
| [I-049](master_list/10_surface_switching_staleness.md) | Early-surface-season under-confidence of the price | 10 | M × S | MKT-02 |
| [I-050](master_list/10_surface_switching_staleness.md) | Indoor/outdoor switch × serve style | 10 | W / S | BOD-22 |
| [I-051](master_list/11_workload_recovery.md) | Load split: on-site survival against carried-over debt | 11 | W | BOD-01 |
| [I-052](master_list/11_workload_recovery.md) | Fitness–fatigue kernel on the match clock | 11 | W | BOD-02 |
| [I-053](master_list/11_workload_recovery.md) | Age × recovery debt | 11 | W (+ S variant) | BOD-03 |
| [I-054](master_list/11_workload_recovery.md) | Both tired against one tired | 11 | S (+ pair) | BOD-05 |
| [I-055](master_list/11_workload_recovery.md) | The favourite's hidden fatigue | 11 | M | BOD-08 |
| [I-056](master_list/11_workload_recovery.md) | Previous-round scare × rest | 11 | M / W | BOD-09 |
| [I-057](master_list/11_workload_recovery.md) | Acute-to-chronic load spike | 11 | W | BOD-10 |
| [I-058](master_list/11_workload_recovery.md) | Recovery as a player trait | 11 | U / W | BOD-11 |
| [I-059](master_list/11_workload_recovery.md) | Last week's deep run × a short gap × travel | 11 | W | BOD-14 |
| [I-060](master_list/11_workload_recovery.md) | Consecutive weeks away × age | 11 | W | BOD-17 |
| [I-061](master_list/11_workload_recovery.md) | Season odometer × age × time of year | 11 | W (S month) | BOD-18 |
| [I-062](master_list/11_workload_recovery.md) | Off-tour load: team ties and their travel | 11 | W | BOD-19 |
| [I-063](master_list/12_fatigue_style_attrition.md) | Fatigue composed through the point model | 12 | C (S character) | BOD-04 |
| [I-064](master_list/12_fatigue_style_attrition.md) | Own style × own fatigue | 12 | W | BOD-06 |
| [I-065](master_list/12_fatigue_style_attrition.md) | The opponent who exploits fatigue | 12 | X | BOD-07 |
| [I-066](master_list/12_fatigue_style_attrition.md) | Rally pace × load and age: attrition in minutes | 12 | S | MEC-20 |
| [I-067](master_list/12_fatigue_style_attrition.md) | Heat × age × load × style | 12 | S / W | BOD-24 |
| [I-068](master_list/13_age_trajectory.md) | Age reshapes the profile: return and rally decay first | 13 | W | MEC-14 |
| [I-069](master_list/13_age_trajectory.md) | Style-specific ageing: servers age more slowly | 13 | W | BOD-27 |
| [I-070](master_list/13_age_trajectory.md) | Age-dependent trust in recent form | 13 | W (U character) | BOD-28 |
| [I-071](master_list/13_age_trajectory.md) | Rank anchoring × career trajectory | 13 | W | MKT-10 |
| [I-072](master_list/14_travel_venue_conditions.md) | Leak-proof venue pace × serve/return shape | 14 | S | MEC-03 |
| [I-073](master_list/14_travel_venue_conditions.md) | Per-player indoor deviations in the profile | 14 | S × new difference | MEC-13 |
| [I-074](master_list/14_travel_venue_conditions.md) | Jet lag | 14 | W | BOD-15 |
| [I-075](master_list/14_travel_venue_conditions.md) | On-site acclimatisation × how new the conditions are | 14 | W | BOD-16 |
| [I-076](master_list/14_travel_venue_conditions.md) | Event rhythm against a cold start | 14 | X | MKT-22 |
| [I-077](master_list/14_travel_venue_conditions.md) | Altitude × serve profile × acclimatisation | 14 | S (+ W) | BOD-23 |
| [I-078](master_list/14_travel_venue_conditions.md) | Home split into crowd and no travel | 14 | W / X | BOD-26 |
| [I-079](master_list/14_travel_venue_conditions.md) | Home hype: home wildcards and small events | 14 | W, S | MKT-23 |
| [I-080](master_list/15_rank_fame_attention.md) | Attention-modulated disagreement | 15 | S | MKT-07 |
| [I-081](master_list/15_rank_fame_attention.md) | Profile weight by price level | 15 | M | MKT-09 |
| [I-082](master_list/15_rank_fame_attention.md) | Salience-weighted evidence: form earned where nobody watches | 15 | W (U character) | MKT-11 |
| [I-083](master_list/15_rank_fame_attention.md) | Fallen-star premium | 15 | W, M | MKT-18 |
| [I-084](master_list/15_rank_fame_attention.md) | Pair prominence modulates how much the price knows | 15 | S × M | MAT-S2 |
| [I-085](master_list/16_motivation_narrative_timing.md) | Drifting favourite: over-reaction to news | 16 | M, W | MKT-12 |
| [I-086](master_list/16_motivation_narrative_timing.md) | Last-round narrative: surprise wins and flattering scorelines | 16 | W | MKT-13 |
| [I-087](master_list/16_motivation_narrative_timing.md) | Price-formation window | 16 | S | MKT-17 |
| [I-088](master_list/16_motivation_narrative_timing.md) | Title last week: recency premium against a letdown | 16 | W | MKT-19 |
| [I-089](master_list/16_motivation_narrative_timing.md) | Calendar motivation | 16 | W, S | MKT-24 |
| [I-090](master_list/16_motivation_narrative_timing.md) | Elite effort before Slams; incentive cliffs | 16 | W | BOD-25 |
| [I-091](master_list/16_motivation_narrative_timing.md) | Public narrative statistics: head-to-head and venue records | 16 | W | MKT-25 |

Withdrawn ideas W-01 … W-20 are in [withdrawn.md](master_list/withdrawn.md).
