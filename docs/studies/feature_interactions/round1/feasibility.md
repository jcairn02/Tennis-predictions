# Round 1 · Feasibility audit (gate G2): summary

6 October 2026 · Feasibility auditor (the round-0 cartographer, continued) · Research evidence, not a decision.

**Scope.** G2 as adopted in [plan.md](../plan.md) (critique §5 and M5, M6), applied to the 91 master ideas. Each idea was checked for:
* coverage, for both players;
* the count of 2025–26 matches it applies to;
* its timing class;
* novelty, as R² on the 58 inputs;
* swap integrity;
* build cost.

Verdicts are **pass**, **defer** (with what is missing) or **kill**. A kill is allowed only for infeasibility or a confirmed leak; **none** was needed. Per-family rulings are in [feasibility/](feasibility/), one file per family numbered as in the [master list](../master_list.md). The machine-readable copy is `data/studies/feature_interactions/round1/feasibility.csv`.

**No results (M5).**
* No candidate was related to `a_won`. No price was studied against outcomes.
* Seasons after 2024 were only counted (`test_counts.json`), except for presence flags (Pinnacle, heights, speed history, point records).
* The current best's walk-forward forecasts were read as inputs to I-040 and I-041. They are forecasts, not results.

**How the numbers were made (observed).**
* Scripts are in `src/eda/feature_interactions/round1/feasibility/`.
* `augment.py` builds the shared [panel](../../../../src/eda/feature_interactions/panel.py) for 2014–2024. It adds each player's own history, from the pre-rebuild Stage 0 and clock, cut at 31 Dec 2024 before anything is derived. It also adds Stage B dispersion, the shot-level sides, event countries and the forecasts.
* `builders_a/b/c.py` build the primary column of **76 ideas**, with constants fixed where the originators left them open (noted per row).
* `audit.py` measures four things:
  * coverage;
  * the **full swap test**, under which all 76 primaries and their secondaries pass (the shared `panel.check_swap`, corrected at 19:13, agrees);
  * R² by OLS on the 58 inputs over 2014–2021;
  * an augmented R², which adds the input differences times tour, surface and best of five, or the |difference| and squared terms for context columns. It approximates what TabPFN can form.
* The other 15 ideas had their coverage estimated from their inputs, and their R² is left to round 2.

## Verdicts

| Family | Pass | Defer | Build hours |
|---|---|---|---|
| 01 Serve dominance, leverage, format | 7 | 0 | 10 |
| 02 Composition through the point model | 2 | 4 | 11 |
| 03 Style matchups | 5 | 2 | 17 |
| 04 Handedness, physique | 4 | 0 | 15 |
| 05 Scoring luck, pressure | 3 | 0 | 9 |
| 06 Volatility | 3 | 0 | 9 |
| 07 Reliability, evidence | 3 | 1 | 9 |
| 08 Price calibration, anchor | 7 | 0 | 10 |
| 09 Retirement, injury | 4 | 0 | 12 |
| 10 Surface switching | 5 | 0 | 7 |
| 11 Workload, recovery | 10 | 2 | 32 |
| 12 Fatigue × style | 3 | 2 | 25 |
| 13 Age | 4 | 0 | 6 |
| 14 Travel, venue, conditions | 5 | 3 | 34 |
| 15 Rank, fame, attention | 5 | 0 | 11 |
| 16 Motivation, information timing | 5 | 2 | 11 |
| **Total** | **75** | **16** | **228** (pass 173, defer 55) |

**Build hours by timing class:**
* safe by construction: 47 ideas, 119 h;
* inputs already on the leak-proof clock: 19 ideas, 27 h;
* new cross-player constructions needing the clock and `probe.py`: 4 ideas, 36 h;
* fits on results, walk-forward: 9 ideas, 14 h;
* market quotes: 6 ideas, 8 h;
* static or schedule: 6 ideas, 24 h.

## The 16 deferrals and what each needs

| ID | Missing | Unlocks it |
|---|---|---|
| I-008, I-009, I-010, I-012, I-015 | Novelty: R² 0.980, 0.964, 0.970, 0.954, 0.995 (the composition is near-linear in the inputs) | Declare the column as its remainder after a projection on the 58 inputs fitted without outcomes on 2013–2018 (MAT-C1's own rule), and report the remainder's SD. I-010 also needs V fixed without results. I-012 needs its elasticity g declared |
| I-017 | R² 1.000: a rotation of inputs | Not a column; at most a representation test of the screen, outside G2 |
| I-032 | Its IOS statistic and evidence source are undeclared; the serve-points version has R² 0.953 | Declare both; recompute R² |
| I-052, I-063 | Constants "tuned on 2013–2018" with no target (M5) | A target free of the price and the current best (for example next-match serve residuals, 2013–2018), or fixed values. The data pass. The dependents inherit the τ, which must be frozen at M1 |
| I-060 | Event countries exist only for evaluation events; no continent map | Extend countries to ITF and Challenger weeks (ITF ids carry a code) and build a continent map, about 6 h |
| I-067 | Weather and venue coordinates are not on disk | A free historical weather archive plus a venue table: days of work, no paid API |
| I-074, I-075, I-077 | Time-zone and elevation tables are not on disk | Hand-built public tables, 2–6 h each; I-075 waits for all three |
| I-085 | No-odds walk-forward forecasts exist only from 2019: 2014–21 coverage 38% (men), 32% (women) | Fit the no-odds arm for 2014–2018 (about 15 local fits), or declare a cheaper walk-forward price-free forecast |
| I-086 | Coverage 43–45%: undefined when the previous match was lost or unpriced | One missingness rule (critique S11), then 100% |

## Leak risks and integrity

* **Constructions that read results.** None leaks as specified, provided M6 holds.
  * I-007 is a diagnostic. It runs only in the frozen screen batch, and its gating of I-001, I-003, I-010 and I-011 is declared at M1.
  * I-025's β_f must not be fitted on the discovery outcomes in-sample. Fit it walk-forward by season, or fix it from the iid model. Its e_k use only matches finished by the clock (lf + 1).
  * These are walk-forward fits on strictly earlier seasons, computed inside the screen: Δ1's scaling (I-034, I-080, I-087), the nudge index N (I-039, I-080, I-081, I-087) and the no-odds forecast (I-085).
  * I-040 and I-041 post-process the current best's walk-forward forecasts, which now exist for every 2014–2024 match.
* **Unstated tuning targets** (I-052, I-063, and I-010's V) are deferred, not killed.
* **Cross-player constructions need the clock and `probe.py`** before any result: I-018 (style-pair table), I-021 (hand terms in the IOS), I-072 (venue pace), I-073 (indoor terms).
  * I-012's returns-in-play arm and I-029's IOS-residual route would also need them. Their own-sequence routes (Stage B z) do not.
  * The predictive frontier's existing court-speed terms (`pf_event_*`) were never probed. Do not reuse them.
* **Leaking tables stay out** (CLAUDE.md): weekly IOS, `ttt_pass`, Bradley–Terry, MESR, revaluation. No ruled idea depends on them.
* **Swap and orientation.**
  * Every built column passes the full swap: `_a`/`_b` exchanged, the model's differences and the forecast negated, A-side probabilities flipped.
  * Side A is Stage 0's `player_a_id` throughout (pre-rebuild copies). Nothing is oriented from the match id.

## Data facts the coordinator asked for

* **The point-sequence table** (`data/studies/point_sequence/`, another session's study) is **stable but its study is not finished**.
  * `sequences.parquet`, `seq_matches.parquet` and `coverage_model.csv` were unchanged from 18:24 to 19:26, with no process running.
  * Its report still reads "[RESULTS PENDING]".
  * Its own coverage file shows these shares of model matches with an own sequence, and with both players having at least 20 earlier sequenced matches:

    | Window | Men, own | Women, own | Men, ≥ 20 earlier | Women, ≥ 20 earlier |
    |---|---|---|---|---|
    | 2014–2021 | 87.8% | 66.7% | 96.3% | 59.0% |
    | 2022–2024 | 95.3% | 98.9% | 90.4% | 92.8% |

  * Links are in pre-rebuild ids, and the 21 flipped re-keyed matches are handled by that study.
  * That study has already read 2014–2024 outcomes for its B1 (finishing-form carry-over) and E1 (medical events) tests. **The meta-auditor should log this as a look relevant to I-027, I-028, I-042, I-044 and I-045** if they are rebuilt from it.
* **Opening odds before 2025: none exist on disk.**
  * tennis-data.co.uk holds closing prices only.
  * Polymarket paths cover 2025–26 only; so does the early-price frame (5,105 matches in 2025, 3,488 in 2026).
  * The BetOnline lines surveyed in `docs/research/betonline-lines` would cover 2024–26 at most and are not held.
  * The critique's C5 move test in discovery cannot run.
* **Women's holes that shape these ideas** (observed):
  * minutes are missing in 2014–15, so minutes-based kernels cover women 61% in 2014–21 (I-052 family; I-057 only 51%);
  * no indoor flag exists for women's matches, and men's exist only at main-tour level (Challenger 0.2%, ITF 0%) (I-050, I-073: men only);
  * both heights are present in 64% of 2022–24 matches but only 39% of 2025–26 (I-022–I-024 stay men only);
  * hold, break and break-point counts are missing in 2013–14 (form inputs, inherited);
  * low-visibility box scores are thin (I-082: women's coverage of evidence to measure in round 2).
* **Test-window counts (2025–26, rows only).**
  * The model population has 4,394 men's and 4,199 women's matches.
  * Pinnacle quotes exist for 2,580 and 2,474 (they stop in January 2026: I-039).
  * Both players' serve-speed history exists for 4,103 and 3,505 (I-020).
  * Shot-level point records exist for 1,867 and 1,100.
  * Sackmann's Slam point files end in 2024, so I-026's per-player values freeze in the test years unless extended from the point-sequence table.
* **Already scored on 2022–2026 by earlier studies** (critique M5: may enter the bundle, cannot be confirmed in 2025–26):
  * I-020, the men's serve speed;
  * I-030, the frontier variability;
  * I-048, the surface-IOS deviations, an arm scored as a tie;
  * I-049, slopes fitted on 2013–2025;
  * and those the master list flags (I-006, I-035, I-037, I-063, I-071, I-080, I-085, I-086, I-087).

## Files

* Scripts: `base.py`, `history_feats.py`, `augment.py`, `builders_a.py`, `builders_b.py`, `builders_c.py`, `audit.py`, `test_counts.py`, `rulings_a.py`, `rulings_b.py`, `rulings_c.py`, `family_notes.py`, `assemble.py` (run in this order; `assemble.py` writes the CSV and the family files).
* Data in `data/studies/feature_interactions/round1/`:
  * `feasibility.csv`, the deliverable;
  * `feasibility_metrics.csv`, every built column with coverage, swap test and both R²;
  * `test_counts.json`;
  * `_panel_aug.parquet`, the augmented 2014–2024 panel. It is reusable by the analysts, but its history columns are approximations: windows count earlier matches by the clock's lf, and the minutes kernel is undefined unless every earlier match in the last 14 days has minutes;
  * `_history_feats_2010_2024.parquet`.
