# 01: The evaluation contract

These are the hard rules of the rebuild. A rule changes only by a decision-log entry approved before the first exact score of the stage it governs. Units are mLL per match; **+ = the model is better** than the recalibrated close; a 95% interval spanning 0 is a tie.

## 1. Windows

| Symbol | Definition (by the frame's `season`) | Matches with odds, main tour | Role |
|---|---|---:|---|
| **D** | seasons ≤ 2024, history from 2010 | about 55,000 (2013–2024), plus men's 2018 (2,620) | every fitted quantity and every choice |
| D-choose | 2020–2021 (E1) and 2022–2023 (E2) | about 17,100 | where the selection scores arms |
| D-confirm | 2024 (E3) | about 5,100 | confirmation; a choice must hold here |
| D-fragile | 2016–2019 | about 17,700, or 20,300 with men's 2018 | a sign flip is a regime flag, never a veto on its own |
| **H-exposed** | seasons 2025 and 2026, events up to 28 Jul 2026 (2025 begins with the events of 30 Dec 2024) | 8,593 (men 4,394, women 4,199; 73 women's 2026 matches fall in debut seasons) | the holdout, already read by earlier studies |
| **H-sealed** | events from 29 Jul 2026 to each look | 869 with the average close so far, growing | the clean part of the holdout |
| **H** | H-exposed ∪ H-sealed | | the primary holdout |

* **Why choose on 2020+ (D-only evidence).** The current design's edge over the close was a tie in 2015–2019 and positive in 2020–2024 (`feature_provenance/edge_pooled.csv`, seasons ≤ 2024 only). Choosing where no arm can beat the close would choose on noise.
* **Alternatives for reviewers (Q4):**
  * choose on 2019–2020 and 2021–2022, confirm on 2023–2024;
  * or confirm on two eras.
* **Training floor.** 2013 for in-context training, with 2010–2012 as rating warm-up, by rule (Q5 covers re-checking constants).

## 2. What may touch H

1. **No fitted quantity sees H.** This covers:
   * rating, profile and IOS constants and memories;
   * normalisers, priors and shrinkage;
   * calibration slopes;
   * the stage-2 coefficients and τ;
   * the learner's settings, the feature list and every axis choice.

   A quantity tuned on 2013–2018 (or 2010–2018 norms) is D-fitted and may be kept. One tuned on any window containing 2025–2026 may not keep its value: it is re-chosen on D or set to its neutral default (`03_rebuild_stages.md` §1).
2. **Walk-forward inside H is mechanical, not a choice.** After the design is frozen:
   * 2025 is forecast by fits trained on ≤ 2024;
   * 2026 by fits trained on ≤ 2025, with calibration slopes and stage-2 coefficients refitted by their frozen rules on earlier out-of-sample seasons.

   This is how the model would run live. A D-only variant (every H season from fits on ≤ 2024) is reported as a secondary (Q3).
3. **One look.** H is scored once, by a script that runs only after the design hash is logged. Every touch of H outcomes is logged in `look_ledger.md`, including a row count that reads a result column. That covers anyone at all: owner, analyst, executor or reviewer. After the look, nothing is re-tuned on H. H-sealed then gets further looks only at the pre-registered checkpoints.
4. **Quarantine.**
   * H rows are physically absent from every table the selection reads.
   * Features for H matches are computed into a separate sealed store and hashed. Computing as-of features for H matches uses only results that precede each match, so it does not read the target outcomes.
5. **The clean room.**
   * **The executors** (people or agents running stages 5–7) work in a folder that holds:
     * the D tables;
     * the selection code;
     * this protocol, which contains no H result.

     They do not read study reports, the studies index or the decision records outside it, because those quote 2025–2026 results. Their tool logs are kept, and the holdout auditor checks them for reads outside the folder.
   * **The H store and the bias-correction estimates** are sealed until the look.

## 3. No current-model value in any rule

Adapted from the UFC v4 rebuild's production-blind rule (`UFC-Predictions/docs/v4_rebuild/01_principles.md` §2.10, §5). No value of the current best model (its list, constants, memories, settings or arms) may enter a decision as:
* the baseline a difference is measured against;
* a tie-break, a fallback or a grid centre;
* a scaffold member;
* a "settled" exemption.

The test: someone who never saw the current model could compute every pick from the D scores, the grid's geometry and the logged rule.

* **Where current-model values may appear:** as report-only anchors, computed after a decision is logged, and in parity checks, which test that code reproduces numbers.
* **Mechanism-chosen items.** They are written down with their reason before any score:
  * the scaffold (the closing odds, overall Elo, match context);
  * the learner;
  * the population;
  * the benchmark.

  A reviewer may challenge any of them (Q6, Q7).
* **Symmetry.** No earlier verdict is applied in either direction, and no feature is dropped because it failed on 2025–2026. Every built candidate in the menu competes on D. The exceptions are exclusions by mechanism, each logged:
  * leaking constructions;
  * columns that read a model's forecast;
  * market-internal columns.

## 4. Estimands

**Primary (one number, written before the look).** The edge of the rebuilt model (stage 1 + stage 2) over the recalibrated tennis-data average close:
* on H, both tours, debut seasons excluded, main-tour main draws completed or retired;
* walk-forward as in §2.2;
* reported three ways: **raw**, **corrected** (raw minus the sealed bias estimates of the repeated choices; see `02_contamination_and_forecast.md` §4) and **H-sealed only**.

**Secondary (each reported, none decisive).**
* Each tour; H-exposed and H-sealed apart; 2025 and 2026 apart.
* Stage 2's gain for men with speeds.
* The D-only variant.
* The Betfair Exchange close as the benchmark (de-vigged, not recalibrated: it has no D history).
* The Polymarket close.
* The winner's-curse-corrected D estimate, against the H estimate.
* **Report-only anchors:** the current model's edge on H-sealed (the only part of H where its reading is clean), and its H-exposed reading labelled as contaminated.
* **Betting returns at the venue:** reported, never used to choose.

**Contamination diagnostics at the look.**
1. Raw against corrected.
2. H-exposed against H-sealed (a large gap that the corrections do not explain points to unmodelled leakage, or to a change of era).
3. The share of the selected columns whose idea or choice was exposed to 2025–2026 (from `feature_provenance/provenance_58.csv` and the menu's `seen_2025_2026`).
4. Optionally, the a-priori-menu sensitivity (Q26).

## 5. Pre-registered responses

* **Ship as the candidate for paper or small-stake betting** if the corrected H edge's lower bound is above 0. Prospective checkpoints follow.
* **Treat as a lead, not an edge** if the corrected H edge is positive but its interval spans 0. Keep it running on H-sealed; nothing is re-tuned.
* **Ship nothing** if the corrected H edge is ≤ 0. Diagnose on D only. A revised design is validated only on matches after the look.
* **Under no outcome** is anything chosen on H after the look. After the final checkpoint, H becomes development data for the next rebuild.
* **The owner may override any branch;** the override is logged. Following the UFC precedent, a failed gate is an owner decision point, not an automatic verdict.

## 6. Metrics and conventions

* **Log loss for every choice.** Brier and accuracy are reported, never used to choose.
* **Intervals:** paired cluster t over four-week blocks of tournament dates from 2010-01-04.
* **Symmetrisation:** each match forecast in both orientations and averaged.
* **Recalibration:** one slope per tour through the origin on the log-odds, for the model and for the close, fitted walk-forward on earlier out-of-sample seasons. The fitting window's start is a D choice (Q12 covers the stage-2 parts).
* **Debut seasons** are excluded from scoring.
* **Every stage output** carries the data snapshot hash, the menu hash, the seeds and the windows. Runs cached across a rebuild of the tables are not compared.

## Open questions in this document

Q1 (H by season or by date), Q2 (H-sealed inside the primary or apart), Q3 (walk-forward or D-only as primary), Q4 (the era layout), Q6 (the learner fixed or checked on D), Q7 (temperature), Q16 (the response thresholds), Q20 (the number of looks). The full list is in `04_review.md`.
