# The fast check before the first in-season retrain: rules fixed before any result (20 Oct 2026, 18:55 PDT)

Instance: template_2026-10-16 (its walk-forward fits, seeds 0-3; frame 67,226 matches). Results of seasons <= 2024 only.
Units: mLL per match, paired; + = the named arm better. Intervals: 4-week blocks plus the paired seed term
(current_best_model/compare.paired).

## Part A: does growing stage 2 harm? (no new TabPFN fit)
- Seasons 2020-2024. Cut-offs: the 1st of February .. November of each season. Segment k: the season's matches with
  es in [c_k, c_k+1); the last segment runs to the season's end. January is identical in both arms and left out.
- Annual arm: s_atp, s_wta, b fitted on 2019 .. Y-1, debut seasons out, b shrunk with tau 0.05 (compare.walk_forward).
- Grown arm: the same fit on 2019 .. Y-1 plus the season's non-debut matches with lf + 1 <= c_k, from their
  walk-forward forecasts.
- Both: eta = the seeds 0-3 mean; the speed column spd_L_B of speed_columns_augmented.parquet; women's column 0.
- PRIMARY: both tours, 2020-2024 pooled, grown vs annual.
- HARM: worse by more than 0.10 with the whole 95% interval below 0. No harm = the owner's condition 2 met for stage 2.
- Report only: men, women, each season; the coefficients by cut-off.

## Part B: the guard of 9 Oct (six TabPFN fits)
- Seasons 2022, 2023, 2024; cut-off 1 July; seeds 0, 1; the decided settings (8 estimators, softmax 0.9, pretraining
  limits ignored).
- In-season fit: 2013 .. Y-1 plus the season's matches with lf + 1 <= 1 July; predicts the season's matches with
  es >= 1 July, stored and swapped, symmetrised. Matches with es < 1 July < lf + 1 are in neither.
- PRIMARY: live configuration (in-season fit + grown stage 2 through 1 July) vs decided (walk-forward fit + annual
  stage 2), seeds 0-1 matched, both tours, three seasons pooled.
- THE GUARD FAILS if (i) the primary is worse by more than 0.10 with the whole 95% interval below 0, or (ii) the TabPFN
  part alone (in-season vs walk-forward, both with the annual stage 2) gains more than +1.0: a suspected leak.
- Mechanical checks (no result read): no training row with lf + 1 > the cut-off; no predicted match with es < the
  cut-off; training rows = the season rule's + the admitted ones.
- Report only: recalibration slopes of each configuration's log-odds on the predicted matches, per tour; the spread of
  each fit's log-odds about the close.

## Not tested
Whether retraining within the season improves forecasts: plausible size 0.001-0.01, far below this check's resolution;
decided by the 9 Oct policy.
