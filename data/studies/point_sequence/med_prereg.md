# E1 mechanism gate: pre-registration (written before any effect was estimated)

Registered 6 Oct 2026, 18:40 PDT, by the TESTER-2 agent of the point-sequence session. Plan: the auditor's round 3,
item 2 (binding), with the brainstormer's F2 for operational detail. Code: `src/eda/point_sequence/med_*.py`.
Outputs: `data/studies/point_sequence/med_*`. **Research, not a decision.**

Question: do medical / physio events in a WTA player's previous match predict (M1) retirement or walkover-out in her
next match, or (M2) a lower serve-point residual in her next match? Secondary: do her within-match fade markers
(first serves in, double faults, tempo) predict M2 as a difference in differences against the match before?

## 0. What was inspected before registering (structure only; no exposure-outcome contrast was computed)

Observed in `wta_events.parquet` (646,726 non-point records) and the linked tables:

* Medical records come as `MedicalTreatment` (reasons PhysioCalled, PhysioCancelled, PhysioEvaluationStarted,
  PhysioArrived, TreatmentInProgress, TreatmentComplete, NoTreatment), `PhysioCalled` and `PhysioCallCancelled`.
  **The recording vocabulary changes by year**: 2019 logs record the call and the cancellation as MedicalTreatment
  reasons and treatment as TreatmentInProgress; 2020 adds TreatmentComplete/NoTreatment; 2021 mainly
  TreatmentComplete (TreatmentInProgress 40 records); 2022+ the full sequence call → evaluation → in progress → complete.
  Separate `PhysioCalled` records: 35 (2019), 301 (2020), 738 (2021), 866–1,023 a year (2022–24).
* **The reasons Injury, Illness and Heat exist only on `Suspension` records, which never name a player** (4,239 of
  4,239 have no player). Injury/Illness/Heat suspensions: 133 (2021), 142, 141, 210 (2022–24). `HeatBreak10Minutes`
  (43) is the scheduled heat-rule break. So INJURY needs an attribution rule (section 2).
* `ToiletBreak` reasons: NoClothingChanged 12,350, ClothingChanged 125.
* Every event record of a linked match has its player's Stage 0 side (`player_side_ab` 1/2); side 0 occurs only in
  unlinked logs (and one record without a player).
* WTA logs: full logs from June 2019 (513 bare logs Jan–May 2019, no attributes). Of 25,164 linked primary logs,
  24,840 have a Stage 0 box score; log points / box serve points is 1.000 in the median, below 0.9 for 76 logs.
* Per-point clock: WTA-log sequences have distinct point times in ≥ 98% of matches (about 1% of 2019 and 2021 logs carry
  one repeated time); serve number is known for every WTA-log point.
* Stage 0 WTA statuses: completed, retired (incl. `retired_unmarked`, `walkover_after_play`), walkover (incl. 7 byes),
  other (defaulted, abandoned, unknown). Walkovers by year: 128, 71, 161, 241, 202, 468 (2019–24; the 2024 jump is
  unexplained: a source change is suspected). Minutes exist for only ~4.5k WTA matches a year (tour level), so the
  previous match's length is taken from its log.
* `statsmodels` is not installed in the `tennis` environment: the regressions are written in numpy (IRLS and
  cluster-robust sandwich variances), with unit tests.

## 1. Units and windows

* **Player-pairs (t, t+1)** of WTA singles (Stage 0 `tour == 'wta'`), ordered by Stage 0 `order`.
  * **t (previous match):** a match she played (status completed, retired or other; not a walkover or bye).
  * **t+1 (next match):** her next Stage 0 match at any level, skipping byes and walkovers she *received* (they say
    nothing about her). A walkover she *gave* is a valid t+1.
  * Day of a match: `timing.parquet` `start` (best-estimate day). Gap = day(t+1) − day(t); keep gap ≤ 21 days.
* **Windows by day(t):** discovery 4 Jun 2019 – 31 Dec 2021; replication 1 Jan 2022 – 31 Dec 2024.
  **Closed holdout:** pairs whose t+1 is dated on or after 1 Jan 2025 are dropped (counted only). No 2025–26 outcome
  is read.
* **Three states for t:**
  1. **logged and flagged**, 2. **logged and unflagged**, 3. **unlogged**.
  * **Logged** = a linked WTA umpire log: `seq_matches` row with source `wta`, a Stage 0 `match_id`,
    `primary_in_source`, log `full`, `score_check` not `winner_differs` / `sets_differ` (likely mislinks), and, where
    Stage 0 has a box score, log points ≥ 0.9 × box serve points.
  * Unlogged t (Slams, ITF, team events, tour matches without a usable log) are excluded from every estimate; the
    logged share is reported by year (all t, and t at WTA tour / 125 / qualifying levels).
* **Primary exclusion:** t ended in *her own* retirement (status retired, she lost). Included as a sensitivity.

## 2. Exposures (from her own records in the log of t)

Counts per player in t:
* calls = `PhysioCalled` records + `MedicalTreatment` records with reason PhysioCalled;
* cancels = `PhysioCallCancelled` records + `MedicalTreatment` with reason PhysioCancelled or NoTreatment;
* treats = `MedicalTreatment` with reason TreatmentInProgress or TreatmentComplete;
* evals = `MedicalTreatment` with reason PhysioEvaluationStarted or PhysioArrived.

Exposures:
* **TREATED** (primary) = treats > 0, or calls > cancels (a call not cancelled), or (evals > 0 with no call and no
  cancellation recorded).
* **INJURY** (nested) = TREATED and the log of t holds a `Suspension` with reason Injury, Illness or Heat
  (not HeatBreak10Minutes) attributed to her: if she is the only TREATED player of t, it is hers; if both are TREATED,
  it goes to the player whose medical record (any of the four kinds) is nearest *before* the suspension in log order
  (nearest after, if none is before).
* **TOILET** (negative control) = any `ToiletBreak` record of hers.
* **OPP_TREATED** (specificity mirror) = her opponent in t is TREATED.

Contrasts (each against logged pairs only):
* TREATED = 1 against TREATED = 0.
* INJURY = 1 against TREATED = 0 (treated-without-injury pairs are left out of this contrast).
* TOILET = 1 against 0, among TREATED = 0 pairs (so no toilet effect can come from a co-occurring treatment).
* OPP_TREATED = 1 against 0, among TREATED = 0 pairs.

## 3. Endpoints

* **M1** = in t+1 she retired or gave a walkover (Stage 0 status retired or walkover, and she lost t+1). At any level.
  Effect = **risk ratio, > 1 = exposed players retire / withdraw more**.
* **M2** = 100 × (spw / svpt − p_serve) in t+1, in percentage points. spw, svpt = her serve points won and played from
  Stage 0's box score, or, where Stage 0 has none, counted from the usable sequence of t+1 (`sequences.parquet`,
  `usable`); p_serve = `stage3_ratings` p_serve for her side (pre-match, own-history rating). Defined where t+1 has
  ≥ 1 serve point of hers (completed or retired; walkovers have none). Weights = svpt.
  Effect = **shift in pp, negative = exposed players serve worse than expected**.
* Descriptive only: the share of logged t (in window) with any next match within 21 days, by exposure (withdrawals
  before a draw are invisible to M1; this shows how much).

## 4. Adjustment set (every outcome model)

* minutes decile of t: playing time from the log of t = sum of the gaps between consecutive points, each capped at
  300 s (suspensions, medical time-outs and rain count at most 5 min); decile cuts from discovery pairs;
* result of t (won / lost);
* days since: categories 0–1, 2, 3–4, 5–7, 8–14, 15–21;
* surface of t+1 (Hard, Clay, Grass, other/unknown);
* age at t+1 (Stage 0; else age at t + gap; else the discovery median with a missing flag), centred, plus its square;
* **propensity score quintile** (cuts from discovery): logistic P(exposure | t) fitted on the discovery rows of that
  exposure's contrast only (≤ 2021), on: age, age², level group of t (T1000 + Finals, T500, T250, 125), qualifying
  flag, surface of t, minutes decile, result of t, her pre-match p_serve in t and her opponent's. One score per
  exposure (TREATED, INJURY, TOILET, OPP_TREATED).

## 5. Estimators

* **M1:** Poisson regression with log link on the 0/1 endpoint (modified Poisson), player-clustered sandwich variance;
  RR = exp(β), 95% Wald interval, two-sided p.
* **M2:** weighted least squares (weights svpt), player-clustered sandwich variance; shift in pp.
* Each window is fitted separately. Clustering by player (a player appears in many pairs).

## 6. Pass rule (primary family)

Holm over the four discovery p-values {TREATED, INJURY} × {M1, M2}. A cell passes when **all** hold:
1. Holm-adjusted p < 0.05 in discovery;
2. discovery point estimate RR ≥ 1.5 (M1) or shift ≤ −0.5 pp (M2);
3. replication point estimate on the same side (RR > 1; shift < 0);
4. the TOILET control's 95% interval covers the null on the same endpoint in **both** windows.

The gate passes if at least one cell passes. The strict reading of (4) (TOILET null on both endpoints in both windows)
is reported alongside; if the two readings disagree, the report says so.

## 7. Placebo and mirror

* **Placebo:** TREATED permuted 500 times within season × result of t × minutes decile, in each window, through the
  identical M1 and M2 models. Reported: mean and 2.5–97.5% range of placebo estimates, the share of permutations with
  nominal p < 0.05 (expected ≈ 5%), and the permutation p-value of the observed estimate.
* **Mirror:** OPP_TREATED through the identical models (expected null).

## 8. Secondary family (women's fade markers; k = 3, own Holm)

* **Units:** triples (t−1, t, t+1): (t, t+1) a primary pair whose t has its WTA log as the chosen usable sequence;
  t−1 = her previous played match before t, at most 21 days before t, with M2 available; t+1 with M2 available.
* **Markers** from her serve points in t (x = the point's index in the match / 100):
  * FSI: first serve in (serve_no = 1);
  * DF: double fault (end = DF by her);
  * TEMPO: seconds since the previous point, only where that point is in the same game and the gap is 5–120 s.
  * Controls removed first by one tour-wide OLS fitted on discovery WTA-log points: score state in the game (server and
    receiver points capped at 3; deuce, advantage server, advantage receiver; tie-break points as their own block),
    tie-break, court side (points already played in the game even = deuce court); for TEMPO also the current point's
    serve number and end (ace / DF / other).
  * Per player-match slope of the residual on x (≥ 30 serve points; TEMPO ≥ 20 usable gaps), minus the discovery mean
    slope in its match-length decile (total points of t), oriented so that **positive = fading** (FSI −slope,
    DF +slope, TEMPO +slope = slowing), standardised by the discovery SD.
* **Target:** D = M2(t+1) − M2(t−1), pp. WLS of D on the marker (per SD) plus the primary adjustment set (minutes
  decile, result of t, days-since category, surface of t+1, age), weights 1 / (1/svpt(t+1) + 1/svpt(t−1)),
  player-clustered. Statistic: **pp per SD of fade; negative = more fading → serves worse next, relative to before.**
  Forward (M2(t+1)) and reverse (M2(t−1)) coefficients are reported separately.
* **Pass:** Holm over the three discovery p-values < 0.05, discovery coefficient < 0, replication coefficient < 0.

## 9. Pre-declared sensitivities (not in the pass rule)

Own retirements in t included; M2 on completed t+1 only; points-played decile instead of minutes; Mantel–Haenszel RR
for M1 stratified by result of t × PS quintile; strata fresh (t won, t+1 at the same event) and stale (t lost, t+1 at
a later event); level of t+1 added as a covariate.

## 10. Power (inferred, from F2, before counting)

About 9–10k logged pairs in discovery, ~8% treated (~750). M1 base ~1.5–3%: a risk ratio ≥ 2 is detectable, 1.5 is
marginal. M2 standard error ~0.2–0.25 pp: −0.5 pp is detectable. Updated with the real counts in section 12 before any
estimate.

## 11. What the result closes or opens (audit round 3)

* **A null** closes medical and distress events as a pre-match signal, together with E1's market and G1 tests; G3
  (in-play medical events) is downgraded; the women's fade markers are closed as state signals.
* **A pass**: stop and report. No market or model test is run here; the main session decides the next step.

## 12. Registration-time counts (filled after building the pair table, before estimating)

Observed (`med_build_summary.json`, build after deviations D1–D2; no exposure-outcome contrast computed):

| | discovery (4 Jun 2019 – 2021) | replication (2022–24) |
|---|---|---|
| played t in window (any level) | 114,274 | 225,056 |
| pairs with t+1 ≤ 21 days | 95,673 | 192,088 |
| … of which t logged | 10,074 | 21,014 |
| own retirement in t (excluded) | 112 | 252 |
| **primary pairs** (players) | **9,962** (575) | **20,762** (768) |
| TREATED | 601 (6.0%) | 1,282 (6.2%) |
| INJURY | **7** | **29** |
| TOILET (among TREATED = 0) | 1,626 | 4,309 |
| OPP_TREATED (among TREATED = 0) | 706 | 1,431 |
| M2 available (box / sequence) | 9,009 (8,911 / 98) | 18,692 (18,538 / 154) |
| triples base (t+1 and t−1 with M2, t−1 ≤ 21 d, t a WTA-log sequence) | 7,233 | 11,751 |
| t+1 masked by the holdout (dropped) | 29 | 2,615 |

* Logged share of pairs by season, t at WTA tour / 125 / qualifying level: 0.67 (2019 from 4 Jun), 0.98, 0.96,
  0.97, 0.98, 0.98 (2020–24); of all pairs (ITF and Slams included): 0.07, 0.13, 0.12, 0.11, 0.11, 0.11.
* TREATED share by season: 6.7, 6.4, 5.6, 6.4, 6.1, 6.0% (stable across the changes of log vocabulary).
* **INJURY is structurally thin**: no Injury / Illness / Heat suspension reason is recorded before 2021 (0 in 2019–20),
  and of 885 such suspensions in all logs 2019–26, 468 can be attributed to a treated player and 417 have none.
  Most attributable ones end in that player's retirement (excluded from the primary). F2 expected ~400 injury pairs.
* Overall (not by exposure) M1 rate: 2.07% discovery (206 events), 2.09% replication (433). M2: svpt-weighted SD
  7.55 pp per pair, median 67 serve points.

Power, recomputed (inferred; normal approximations, Holm's first step at α = 0.0125 → z 2.50, clustering ignored):
* TREATED, M1: ~12 events expected under the null. Power ≈ 0.20 for RR 1.5, ≈ 0.77 for RR 2.
* TREATED, M2: SE ≈ 0.33 pp (F2 assumed 0.20–0.25). Power ≈ 0.16 for −0.5 pp, ≈ 0.69 for −1.0 pp.
* INJURY: 7 discovery pairs. M1 is not testable (~0.15 events expected); M2 SE ≈ 3 pp.
* **So the registered thresholds (RR 1.5, −0.5 pp) sit near the detection floor in discovery.** A null here rules out
  large effects (RR ≥ ~2, M2 ≤ ~−1 pp), not the thresholds themselves. The interpretation in section 11 is read
  with this limit.

## 13. Deviations

All three were made after registration and **before any exposure-outcome contrast was computed** (found in a
structure check of the first pair build: gap histogram and counts only).

* **D1. The match day is `timing.parquet` `obs`, not `start`.** Section 1 (following the brief) called `start` the
  best-estimate day. It is the tournament start date (`src/eda/match_timing/timing.py`: `m["start"] =
  to_day(tournament_date)`); the best-estimate day is `obs` (the exact day, else the class median offset inside the
  window; timing.py rule 5). With `start`, every round of an event shared one day and every in-event gap was 0.
  `obs` is used for the windows, the 21-day rule, days since and the triples' t−1 gap.
* **D2. Stricter holdout.** Besides t+1 dated on or after 1 Jan 2025, every Stage 0 row of season 2025 or later is
  masked (the 2025 season's first events start in the last days of December 2024).
* **D3. Zero-event cells.** A cell whose exposed group has no M1 event cannot be fitted by Poisson regression; it is
  reported as not estimable and enters Holm with p = 1. (Registered here because the first count showed INJURY in
  only 7 discovery pairs.)

Made **after** the first estimation run (a pipeline check with 20 permutations; the registered estimates were the
same in the final run, which used the registered 500 permutations). None enters the pass rule:

* **D4. Bug fix in a descriptive table.** In "next match within 21 days", TOILET's exposed group had included
  treated players; it is now taken among TREATED = 0 pairs, as in its contrast.
* **D5. Unregistered additions, labelled descriptive or exploratory:** M1 split into retirements and walkovers given
  (`med_results.json`, `m1_components_descriptive`); the TREATED M1 model with the player's own 365-day history of
  retirements / walkovers given, matches played and earlier TREATED matches added; and the one-sided permutation
  tail of the placebo (`src/eda/point_sequence/med_explore.py`, `med_explore.json`).
