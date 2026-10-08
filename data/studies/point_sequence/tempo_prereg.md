# Pre-registration: women's own-serve tempo and pressure pace, trait gate (outcome-free)

Written 6 Oct 2026 by TESTER-1 from the binding spec (scoped audit, section 2, item B), before any tempo value,
adjustment, shuffle or reliability was computed. Frozen by its SHA-256 in `tempo_prereg.sha256`; `tempo_run.py` refuses
to run if the hash differs. Deviations go to `tempo_results.json` under "deviations", never here.

**Seen before writing (data semantics only):** in the WTA umpire log, a point's `t_utc` marks the **end** of the point:
the gap to the previous point within a game has a median of 24.3 s when the current point is an ace and 33.4 s
otherwise, 40.5 s on second-serve points against 28.9 s on first-serve points, and 29.1 s after an ace against 33.4 s
(all 2019–2026 log points, gaps 0–300 s). Umpire ids exist only in the raw event files
(`data/dump/points/wta/events/<year>.parquet`, `umpire_id`; 34 of 4,273 matches of 2021 show two ids).

## Population and gaps (no match result is read)

* Item 1's population restricted to matches whose chosen sequence is the WTA umpire log (`source == wta`), women,
  `obs` from 1 Jun 2019, seasons ≤ 2024. Points in order with `t_utc`.
* A **gap** = t_utc of a point − t_utc of the previous point, for the server's points in **regular games** that are not
  the game's first point (game openers out); tie-break points out. Kept if 5 s ≤ gap ≤ 120 s.
* Excluded: any gap with an interruption record between the two points (`wta_events.next_point_seq` = the later
  point's seq, same match): Let, Challenge, MedicalTreatment, PhysioCalled, PhysioCallCancelled, ToiletBreak (toilet
  or clothing), Suspension, PlayResumed, StateIndicator with reason Correction, ReWarmupAfterSuspensionStarted or
  RestartedAfterSuspension, and also BallMarkInspection and Overrule (umpire procedures; added here).
* Umpire = the match's most frequent `umpire_id` in the raw log (matched on tournament / year / match code).

## Adjustment

* Least squares with fixed effects (alternating projections to convergence) on the gap in seconds:
  **primary** = server (player) + umpire + event-year (tournament × season) + score state before the point (server's
  and receiver's points, 0–3 each, deuce / advantage server / advantage receiver) + previous point's type (ace, double
  fault, other) + **current point's type and serve number** (ace; double fault; other on a first serve; other on a
  second serve). The current-point terms are added to the spec because the timestamp marks the end of the point, so the
  gap contains the current point's own duration (see above). **Secondary** = the spec's list exactly (no current-point
  terms). Both are reported; the verdict is the primary's, and a disagreement is reported.
* Adjusted gap = gap − (all fitted effects except the player's).

## Statistics per player-match (on her own serve)

* **Tempo level**: median adjusted gap; weight n = her eligible gaps; X = n × median, D = n (needs n ≥ 5).
* **Pressure pace**: median adjusted gap on pressure points (30–30, deuce, break point against: receiver on 40 and
  ahead, or advantage receiver) minus median on her other eligible points; needs ≥ 2 of each; weight
  w = n_p n_o / (n_p + n_o); X = w × pace, D = w. Higher = slows down more under pressure than her own norm.
* **Null**: pressure labels shuffled at random among her eligible gaps within the match (the count kept), 10 shuffles,
  seeds `[20261006, 93, j]`; pressure pace recomputed.

## Endpoint and pass rule

* Split-half reliability as `trait_reliability.run_population` on players with ≥ 40 (≥ 20 per half; primary) and ≥ 100
  (≥ 50 per half; reported) tempo-population matches; 50 splits; the same splits for real and null; 2,000-resample
  player bootstrap, 95% percentile interval.
* **Pressure pace passes** if real r − null r (mean of 10) ≥ 0.10 at ≥ 20 per half with the interval above 0.
* **Tempo level**: reliability (split-half r, both depths) reported; **R² with the 58 model inputs** must be < 0.1 for it
  to count as new information: for women's model-frame matches (`model_frame.parquet`, `obs` 1 Jun 2019 – 2024) where
  both players have ≥ 5 tempo-population matches in the 364 days before (by `obs`; strictly earlier day, or an earlier
  round of the same event), pre-match tempo = the n-weighted mean of those matches' tempo levels; OLS of
  tempo_A − tempo_B on the 58 `in_*` inputs (surface, level and round one-hot); in-sample R² (criterion) and 5-fold
  cross-validated R² reported; also tempo_A alone.
* Reported: the population medians of raw and adjusted gaps, the fitted effects' spread (umpire, event-year, score
  state, point types), the population mean pressure pace (real and null).
