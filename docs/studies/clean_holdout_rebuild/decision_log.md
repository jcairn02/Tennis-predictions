# Decision log: the clean-holdout rebuild

Every ruling, deviation and look-related event, in order. **Status values:** proposed (awaiting the owner), approved, declined, superseded. Nothing here is approved yet, except the principle of 0.9 (9 Oct 2026).

## 0. Set-up (proposed, 8 Oct 2026)

| ID | Item | Proposal | Status |
|---|---|---|---|
| 0.1 | The holdout | H = seasons 2025 and 2026 by the frame's `season` (from the events of 30 Dec 2024): H-exposed to 28 Jul 2026 and H-sealed from 29 Jul 2026 to each look | proposed |
| 0.2 | Development data and eras | D = seasons ≤ 2024 with men's 2018 added. Choose on 2020–21 and 2022–23; confirm on 2024; fragile window 2016–19; training floor 2013 | proposed |
| 0.3 | Scaffold | the closing odds, overall Elo and the six context columns (mechanism) | proposed |
| 0.4 | Learner and settings | local TabPFN-3.5, 8 estimators; temperature from {0.8, 0.9, 1.0} on D; 3 seeds in selection, 8 in the final | proposed |
| 0.5 | Primary estimand | edge of stage 1 + stage 2 over the recalibrated average close on H, both tours, walk-forward: raw, corrected and H-sealed | proposed |
| 0.6 | Pre-registered responses | `01_contract.md` §5 | proposed |
| 0.7 | Logs | `look_ledger.md` started at stage 0; executors' tool logs kept | proposed |
| 0.8 | The seal | `data/studies/feature_provenance/seal.json` (feature-provenance plan, phase 0) | proposed |
| 0.9 | The selection rule (Q8) | Top-down removal over a cluster tree fixed before any score, with stability (`03` §5, items 4–7, redrafted 9 Oct 2026). Its constants are Q30 | **approved in principle** by the owner on 9 Oct 2026 (a decision record on adoption by kind of change, off limits under `04` §1; its content is in `03` §5, item 4); constants proposed |

## R0 rulings

(empty)

## R1 changes

(empty)

## R2 rulings

(empty)

## Freeze

(protocol hash, date)

## Deviations

(empty)

## Looks

(see `look_ledger.md`)
