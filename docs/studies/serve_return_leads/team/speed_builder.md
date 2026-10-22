# Speed builder: second serves, the first–second gap, fault speed and the fade within a match

16 Oct 2026 · Role: the speed builder of the [serve/return-leads study](../process_log.md) ([brief](../briefs/01_speed_builder.md)) · Claude Opus 5.5 (`claude-opus-5-5`), a subagent of the lead's session `6483c720-30a3-46ff-9519-287690b6f9d8` · Diagnostic and exploratory: nothing in production changes.

**Labels.** *Observed* = run or read here (path given). *Inferred* = my reasoning. *Assumption* = a choice I made. *Unknown* = not established.

**Outcomes.** Every result is read through `src/eda/serve_return_leads/readings.py` only (tournament dates before 29 Jul 2026). The build code (`src/eda/serve_return_leads/speed_ext.py`) reads no result column.

## Summary (written after the readings)

* **Built** (all outcome-free; every timing probe passes, § 4):
  * the second-serve 28-day form `spd2_L_B` (and the 14-day `spd2_T_B`);
  * the form of the per-match first − second gap, `gap_L_B`;
  * a fault-speed deviation `fault_dev_28` (2025–26 only);
  * the fade within the previous match, `fade_dev_14`.
* **The reproduction:** `build_on` reproduces `spd_L_B` exactly.
  * The stored column (`speed_columns_augmented.parquet`) has **no value for any men's 2018 match**: the 30 Sep frame keys lack that season. A reading of 2017–19 on it counts 2018 as 0.
  * The speed stage fits on 2019 on, so production is unaffected (inference).
  * Here 2018 gets values, on extended keys.
* **Readings, beyond the close, men** (§ 5):
  * The second-serve form held its registered sign in all four 2013–24 eras: +1.86, +2.03, +2.12, +0.75; 2013–24 **+2.76**; 2025–26 +1.90.
  * The first serve on the same fit: +0.38, +1.46, +3.97, −0.41; 2013–24 +1.94; 2025–26 +3.81.
  * Jointly over 2013–24 the second serve carries the signal (+1.98 against +0.84); in 2025–26 the first does (+2.81 against +1.02).
  * The gap, the fade and fault speed are unresolved. The gap leans against its registered sign; fault speed's orth z's are an artefact.
* **Recommendation** (§ 6): register `spd2_L` as a second hypothesis in the speed family (Holm with T4) for the check on unseen matches. Do not register the gap, the fade or fault speed.

## 1. Registered before any reading (16 Oct 2026, 14:35 PDT)

*Correction, added 14:45 PDT: the file was saved at 14:28:18 PDT (its modification time); "14:35" was my estimate.*

Written after inspecting outcome-free data only: the speed panel's columns and counts, the point tables' coverage, the builder's code. No reading of any new column, and no new reading of `spd_L_B`, had been computed when this section was written.

**Every column is A − B, men only; "+" means the player higher on it is expected to beat the price.**

| Column | What it is | Direction | Reason (inference) |
|---|---|---|---|
| `spd_L_B` | The serve-speed stage's 28-day first-serve speed memory, reproduced | **+** | As locked (T4). Read for comparison only |
| `spd2_L_B` (primary of this memo) | The same builder on second-serve speeds: second serve recently above own normal | **+** | Same mechanism as the first serve: pace above one's normal signals physical condition and confidence (an injured or tired player takes pace off both serves; a confident one hits the second serve bigger). Second-serve speed is not in common betting information. Expected weaker than the first serve: the second serve is hit with spin and margin, so pace is a noisier gauge of capacity |
| `spd2_T_B` | Its 14-day version | **+** | As above (secondary; it comes free with the builder) |
| `gap_L_B` | The same builder on the per-match gap (first − second serve speed): the gap recently wider than own normal | **+** | Shocks shared by both serves in a match (the court's radar and its calibration that day, balls, heat, altitude) cancel inside the match before filtering, so the gap isolates the max-effort serve's pace relative to the controlled one. A tired or injured player loses pace on the effort serve more than on the spin serve. *Competing mechanism:* a player who starts hitting his second serve harder (confidence) narrows the gap; the registered sign bets that the effort-serve channel dominates |
| `fault_dev_28` (descriptive: 2025–26 data only) | The player's recent (28 days) first-serve fault speed minus first-serve-in speed, against his own normal from 2025 | **−** | When his misses are faster than his makes by more than usual, his big serve is not landing (timing or rhythm off, or over-hitting). Box scores show the first-serve percentage, not which serves miss |
| `fade_dev_14` | His previous match within 14 days: last-third minus first-third first-serve-in speed, against his own normal fade | **+** | A bigger late drop than he usually shows signals fatigue or a physical problem that worsened during that match, carried into the next match; holding speed signals fitness. The market sees the last match's score and length, not the speed trajectory inside it |

**The first–second gap (task B): the form of the per-match gap, not the difference of the two forms.** Reasons, before reading:
1. The difference of the two forms (`spd_L_B` minus `spd2_L_B` in km/h) is, apart from clipping, a fixed linear combination of the two columns. The joint fit of `spd_L_B` with `spd2_L_B` already reads it, so it would add no new reading.
2. A filter run on the per-match gap cancels the match-level shocks common to both serves before filtering, which neither form can do. That is a distinct question: has the player's effort serve gained on his controlled serve, beyond the conditions of the day?

**Added 14:43 PDT, still before any reading** (after the outcome-free correlations of § 3): a second joint fit, `spd_L_B` with `gap_L_B` beyond the close, in the same two windows (2025–26, 2013–24). `gap_L_B` correlates 0.41 with `spd_L_B` and −0.61 with `spd2_L_B`, so its own reading partly repeats theirs. The brief's joint fit (`spd_L_B` with `spd2_L_B`) is unchanged.

**What decides the recommendation (fixed now).** Each column's readings are reported for every window. For the recommendation I weigh, in this order: (i) whether it holds its registered sign beyond the close across the 2013–24 eras (discovery over many seasons, the edge-anatomy lesson); (ii) whether it adds to `spd_L_B` in the joint fit; (iii) 2025–26, which is where `spd_L_B` itself was found, so it cannot confirm anything. Coverage and the probe are gates: a column that fails its timing probe is not read.

## 2. Plan

1. Reproduce `spd_L_B` exactly with `build_on` on the augmented history.
2. Second-serve history; its constants by outcome-free estimates (§ 3); `spd2_L_B`, `spd2_T_B`.
3. The gap history and `gap_L_B`.
4. Fault speed: what exists, coverage, `fault_dev_28`.
5. The fade: point-ordered sources, coverage by year and level, `fade_dev_14`.
6. A cut-scramble probe for each new column.
7. Readings (`readings.read`, `readings.fit_joint`), then the recommendation.

## 3. Build log

*(written while working; see § 8 for times)*

### 3.1 The reproduction (observed: `data/studies/serve_return_leads/speed/reproduce.json`)

* `build_on` on `live_panel.BACKFILLED` (SHA-256 `56731cba…`, checked against its record) reproduces `speed_columns_augmented.parquet` (SHA-256 `2add9204…`) **exactly**: 0 differing values in each of its 20 columns over all 63,737 matches, `assert_frame_equal` passed.
* **The frame keys lack the men's 2018 season.** `frame_keys.parquet` (the 30 Sep frame's 63,737 matches) has no men's match of 2018, so `spd_L_B` is missing for all 2,620 men's 2018 matches of the 10 Oct frame. The readings' 2017–19 era would count them 0.
  * I added them as extra targets (keys from Stage 0 and the current timing table, the frame read with match id, tour, season and tournament date only). The 10 Oct frame's 416 men's matches from 29 Jul 2026 on were excluded: no value is built for an unseen match.
  * Targets share no state, so the extension leaves every `frame_keys` row bit-identical (0 moved in all 20 columns). It gives `spd_L_B` a non-zero value on 2,537 of the 2018 matches. Every column below, `spd_L_B` included, is read on the extended keys.
* Orientation: the 10 Oct frame's A/B equals the keys' A/B on all 31,683 men's matches both hold (observed, player ids only).

### 3.2 Second-serve history (A)

**How the builder uses each field** (observed in the code: `adaptive/columns.py`, `latency/features_latency.py`, `features.py`, `panel.py`):

| Field | Where it enters | Second serve |
|---|---|---|
| `y` | the filter's observation, centred by the as-of edition offsets; the offsets' fit | `spd2` (key statistics: ks2 − 0.5; AO match centre: mc2 + 0.5; point tables: mean of timed second serves in) |
| `y_raw` | not read by this builder (only by `features.py`'s registered window statistic, and that reads `y`) | `spd2_raw`, for consistency |
| `n` | the noise R = ν_basis + σ²/n; the offsets' weights 1/(τ² + s²/n) | `n2`: timed second serves in (points) or first_total − first_in (key statistics) |
| `basis` | ν_ks or ν_pts; part of the edition key | unchanged: the second serve comes from the same record as the first |
| `use` | which rows enter the history and the offsets | `use2` = `use` & `spd2` ≥ 100 km/h & `n2` ≥ 10 |
| edition offsets | refit per target day on the series' own use rows | refit on second serves (each radar's second-serve offset is its own); the disk snapshots are never read (their fingerprint differs) |
| release days | per player-match, `availability.parquet` | unchanged: the second serve arrives with the first |

* **Rows** (observed): men's usable first-serve rows 32,147 → 31,864 second-serve rows. Dropped: 51 without `spd2`, 222 with `n2` under 10 or missing, 10 with `spd2` under 100 km/h (the floor is the analogue of the first serve's 120 km/h: the lowest real values sit near 104 km/h at the 0.05% quantile, below them sit errors such as 42.5 km/h).
* The 956 AO 2026 match-centre rows (both tours) lack `n2` in the panel; it was taken from the same statistics file (first_total − first_in), on rows whose first-serve count matches the panel's record (all 956).

**Constants** (observed: `constants.json`). Rule, fixed before computing: *each frozen first-serve constant × (the series' estimate ÷ the first serve's estimate), the same estimator for both*; h (14 / 28 days), c = 2, the 364-day window and the clip at 4 are the column's definition and stay.

| Constant | Estimator | First serve: estimate (frozen) | Second serve: estimate → used |
|---|---|---|---|
| σ (per-serve noise) | pooled within-match SD, point tables, men ≤ 2023 | 13.38 (13.49) | 11.30 → **11.39** |
| s (offsets' weight) | median within-match SD | 12.31 (12.4) | 9.64 → **9.72** |
| τ² (offsets' weight) | the engineer's two-way residual estimator, men ≤ 2023 | 30.4 (22) | 33.7 → **24.4** |
| s2f, q, ν_pts, ν_ks | the modeller's one-step-ahead MSE of a match's centred speed, h = 14, men ≤ 2022 (Nelder–Mead) | 24.8, 0.053, 24.7, 44.8 (12, 0.011, 7, 8) | 34.4, 0.082, 58.7, 71.4 → **16.6, 0.0169, 16.6, 12.8** |
| standardiser | SD of unclipped A − B, men's 2022–23 frame matches | (1.9496 for `spd_L_B`) | **2.119** km/h (`spd2_T_B`: 1.666) |

* **Caveat (observed):** my one-step estimator does not land on the frozen first-serve constants. Its criterion is flat: at the frozen values the MSE is 26.06 against 25.82 at its optimum. The ratios rest on weakly identified estimates.
* **So a sensitivity was built, outcome-free and never read:** the frozen filter constants with only σ, s and n the second serve's. It correlates **0.995** with `spd2_L_B` (men, non-zero). The constants choice is immaterial to the column (inference).
* *Inference:* second serves vary less within a match than first serves (σ ratio 0.84) but much more from match to match relative to their form (ν ratios 1.6–2.4). Second-serve pace is partly a tactical choice.
* **Values:** `spd2_L_B` is non-zero on the same matches as `spd_L_B` (± 1 per season); 26 values clipped. Correlation with `spd_L_B` on men's matches where both are non-zero: **0.42**.

### 3.3 The gap (B)

* `gap_L_B` = the builder on y = y1 − `spd2` (use & use2). Both values come from the same record, so the key-statistic and match-centre shifts cancel.
* Noise: n is replaced by n_eff with σ_g²/n_eff = σ1²/n1 + σ2²/n2, σ_g² = σ1² + σ2² (σ_g 17.66; median n_eff 38). The same ratio rule gives τ_g² 24.7, s_g 15.75, s2f 10.7, q 0.0051, ν_pts 10.2, ν_ks 11.7. Standardiser 1.759 km/h.
* Correlations (men, all three non-zero, 29,796 matches): with `spd_L_B` **0.41**, with `spd2_L_B` **−0.61**.

### 3.4 Fault speed (C)

* **What exists on disk** (observed): the first-serve fault speed is recorded only by the Infosys feeds (`faultSrvSpd`).
  * With values: the Infosys Slam files, AO 2025, RG 2025 and RG 2026 (`data/dump/points/infosys_slams/points.parquet`).
  * Without: the ATP's own decrypted files of 2018–21 (`infosys_atp`) and the Challenger files (`infosys_challengers`) hold none.
  * The IBM feeds (Sackmann's Slam files, SlamTracker) record only the speed of the serve that started the point.
  * So there is no history before 2025.
* **Built:** `fault_dev_28` = (fault speed − first-serve-in speed of the same match), mean over his matches of the last 28 days, minus his normal (his matches 28–364 days back, shrunk to the field's mean as of es with weight K0 = 3).
  * Rows: men's usable player-matches with ≥ 5 timed faults, 1,391 (AO 2025 466, RG 2025 456, RG 2026 469). Fault minus serve-in: mean +2.5 km/h, SD 4.0.
  * Released by scenario B's day, as `spd_L_B`. Under B a Slam's rows arrive after the event, so a Slam's own later rounds never see its earlier ones.
* **Coverage** (men's seen matches with a value): **298 in 2025, 141 in 2026** (11% and 8%), all in the weeks after those three Slams. The instant rule (lf + 1, what live Slam feeds could give) would give 505 and 248.
* **Its reading is descriptive only** (2025–26, no discovery history).

### 3.5 The fade (D)

**Point-ordered first-serve speeds on disk** (observed; order = `seq` in the harmonised point tables, which never runs backwards across sets except 7 points of 1.9 million in Sackmann's; in the Infosys Slam files, set, game and point number):

| Source (panel name) | Raw files | Harmonised | Men's coverage with order |
|---|---|---|---|
| slam_pbp | `data/dump/points/sackmann_archive/slam_pointbypoint/` | `shot_level/stage1_points_slam_pbp.parquet` | AO 2011–21, RG 2011–17 and 2020–21, W 2011–24, USO 2011–24 |
| slam_tracking | `data/dump/points/slam_ball_tracking/points/` | `stage1_points_slam_tracking.parquet` | AO 2020–24, RG 2019–24 |
| slamtracker | `data/dump/points/wimbledon/points.parquet`, `.../usopen/points.parquet` | `stage1_points_slamtracker.parquet` | W 2019 and 2021–26, USO 2022–26 |
| infosys_slams | `data/dump/points/infosys_slams/points.parquet` | (read raw) | AO 2025, RG 2025–26 |
| ausopen_mc | `data/dump/points/ausopen/set_statistics.parquet` | — | **no point order:** per-set averages only (nearly all 2026). Not used, so **AO 2026 has no fade** |
| infosys (tour) | `data/raw/public_dump/atp_pipeline_handoff/infosys_deep/`, `.../infosys_full/` (the ATP match centre) | `stage1_points_infosys.parquet` | tour 2021 (part) – 2024; Challengers 2022–24 (about 40 a year) |
| sirgenkii (tour) | `data/dump/points/sirgenkii_infotennis/` | `stage1_points_sirgenkii.parquet` | Jan–Apr 2025 |

* **RG 2018 is missing** from every source. The ATP Stats Centre per-point files (collection package P9) would add the tour from 2018 and from 2025 on.
* **Built:** `fade_dev_14` = for his previous point-timed match within 14 days (the latest released one, obs ≥ es − 14): last-third minus first-third mean first-serve-in speed (his own timed first serves in, equal-count thirds in point order, n ≥ 30), minus his normal fade (his other released fades within 364 days, shrunk to the field's mean as of es with K0 = 3).
  * Clock: `timing.parquet`, a match counts from lf + 1, the target reads at es. One source per player-match: the largest n, ties by the panel's precedence.
  * Then A − B, over its SD (5.95 km/h at side level), clipped at ±4 SD as the builder columns are (added before reading: the fade has speed-gun glitches up to ±45 km/h).
    * *Correction (15:08):* the divisor is the SD of A − B over men's 2022–23 matches with a value, 7.64 km/h (`fade_dev_14.json`); 5.95 km/h is the side-level SD.
* **Rows** (observed): 19,735 men's player-matches. Fade: mean −1.0 to −2.1 km/h by source, SD 5.3–6.8; sampling noise alone ≈ 4.6 km/h.
* **Coverage**, the share of men's seen matches where at least one side has a value:

| Season | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to 28 Jul) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| All matches | 11% | 14% | 13% | 11% | 8% | 11% | 27% | 23% | 67% | 70% | 81% | 31% | 14% |
| Slam main draws | 33% | 44% | 41% | 41% | 31% | 38% | 43% | 47% | 84% | 76% | 87% | 65% | 42% |
| Tour main draws | 5% | 7% | 7% | 4% | 2% | 4% | 20% | 17% | 63% | 69% | 80% | 23% | 6% |

  A Slam main draw's R2 onward is about half its matches, so 33–47% is near complete there. The Slams from 2015 are covered (RG 2018 and AO 2026 excepted), so the brief's condition is met.
* Correlation with the other speed columns: 0.01–0.05 (independent information).

## 4. Timing probes (observed; all pass; written 15:00 PDT, before any reading)

**The 19 cut days:**
* `match_timing/probe.py`'s four fixed days (2023-09-06, 2024-01-24, 2024-07-10, 2024-08-14);
* each Slam's second Wednesday in 2024–26 within the frame;
* six random days from 2014 on.

**Builder columns** (`adaptive/columns.py`'s `probe_b_adaptive` under scenario B, on each series' own history, constants and standardisers, over the extended keys):
* On day D, every row released after D gets a random speed and a new release day in (D, D + 60].
* No column or flag of a men's frame match with es ≤ D may move (`spd_T_B`, `spd_L_B`, both late flags, the mode).
* Leaky controls: (i) the columns with rows admitted at lf + 1; (ii) a flag that peeks a week ahead.

| Series | Values moved | Leaky (i) moved | Leaky (ii) moved | File |
|---|---|---|---|---|
| First serve (`spd_L_B`, extended keys) | **0** | 3,392 | 113 | `probe_spd.json` |
| Second serve (`spd2_*`) | **0** | 3,391 | 120 | `probe_spd2.json` |
| Gap (`gap_*`) | **0** | 3,393 | 120 | `probe_gap.json` |

**Window columns** (`probe_window`):
* On day D, every row released after D gets a random value.
* No target side with es ≤ D may move: the deviation, the recent value, the normal or the field mean, exactly.
* Leaky control: rows admitted up to *peek* days after es.

| Column | Values moved | Leaky moved | Peek | File |
|---|---|---|---|---|
| `fade_dev_14` (release lf + 1) | **0** | 914 | 7 days | `fade_dev_14.json` |
| `fault_dev_28` (release: scenario B) | **0** | 410 | 30 days | `fault_dev_28.json` |

* **A failure, logged.** The fault probe was first run with a 7-day peek. Its leaky control moved nothing (0 on all 19 days), so that run did not pass. The reason: scenario B releases a Slam's rows after the event, up to 22 days after lf + 1, so a 7-day leak could never reach them.
* The control's peek is now the rows' longest release lag plus 8 days (at least 7). Re-run: 0 moved, leak detected on the AO 2025, RG 2025 and RG 2026 days.
* The probe of the values themselves did not change between the two runs (0 moved both times).
* *Added 15:10:* in the final re-run on the final code, the fade's control uses the same rule (peek 8 days: its lag is 0) and moved 1,287 values; its values moved 0. The column files of that re-run are byte-identical to the ones read in § 5 (SHA-256 `5bafccfb…` builder columns, `899db522…` fade, `2a8e4233…` fault). Every `.json` records the final `speed_ext.py` (SHA-256 `28550730…`).
* **Scales** (outcome-free; for the clip only): `fade_dev_14` SD 7.64 km/h (men's 2022–23 matches with a value), 24 values clipped; `fault_dev_28` SD 3.56 (2025–26), none clipped.

## 5. Readings (observed; computed 15:01:00–15:04:18 PDT, in one run of `speed_read.py`)

* **Matches:** men's seen matches, debut seasons out: 34,289 (tournament dates to 28 Jul 2026), through `readings.seen_frame('atp')`.
* **Each cell** is the z of β per RMS of the oriented value (+ = the registered direction holds), cluster-robust over four-week blocks, with t on G − 1.
* **"Model"** = beyond the current model's both-stages forecast, which includes the first-serve speed stage. It exists from 2020, so its 2013–24 cell (raw form) is the 2020–24 one.
* **Pooled eras** = the inverse-variance pool of the four era fits, derived from the same readings (no new fit). The edge-anatomy ledger's 2013–24 figure is of this kind: +2.7 for speed there, +2.83 here.
* **Values present** (share of men's matches with a non-zero value):
  * builder columns: 60% in 2013–16, 97%, 98%, 99.9% in 2023–24, 100% in 2025–26;
  * the fade: 10%, 10%, 42%, 76%, 24%;
  * fault speed: 10% (2025–26).

| Column (direction) | Form, base | 2013–16 | 2017–19 | 2020–22 | 2023–24 | 2013–24 | 2020–24 | 2025–26 | Pooled eras |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `spd_L_B` (+), for comparison | raw, close | +0.38 | +1.46 | +3.97 | −0.41 | +1.94 | +1.53 | +3.81 | +2.83 |
| | orth, close | +0.72 | +1.27 | +2.92 | −0.84 | +1.74 | +0.94 | +2.90 | +2.10 |
| | raw, model | — | — | +3.31 | −2.50 | −0.45 | −0.45 | +2.41 | |
| | orth, model | — | — | +2.48 | −2.87 | −0.67 | −0.93 | +1.78 | |
| **`spd2_L_B` (+)** | raw, close | +1.86 | +2.03 | +2.12 | +0.75 | **+2.76** | +1.96 | +1.90 | +3.34 |
| | orth, close | +2.02 | +1.87 | +2.10 | −0.03 | +2.54 | +1.39 | +1.17 | +2.96 |
| | raw, model | — | — | +1.89 | −0.30 | +0.97 | +0.97 | +1.54 | |
| | orth, model | — | — | +1.92 | −0.85 | +0.77 | +0.54 | +0.87 | |
| `spd2_T_B` (+) | raw, close | +1.68 | +1.37 | +1.67 | +0.50 | +1.98 | +1.46 | +1.55 | +2.58 |
| | orth, close | +1.81 | +1.14 | +1.66 | −0.22 | +1.78 | +0.94 | +0.87 | +2.16 |
| | raw, model | — | — | +1.49 | −0.46 | +0.58 | +0.58 | +1.18 | |
| | orth, model | — | — | +1.50 | −0.97 | +0.41 | +0.18 | +0.56 | |
| `gap_L_B` (+) | raw, close | −1.17 | −0.12 | +0.38 | −0.93 | −0.85 | −0.51 | +0.27 | −0.96 |
| | orth, close | −1.06 | −0.18 | −0.04 | −0.67 | −0.86 | −0.54 | +0.83 | −1.01 |
| | raw, model | — | — | +0.18 | −1.65 | −1.19 | −1.19 | −0.22 | |
| | orth, model | — | — | −0.18 | −1.39 | −1.16 | −1.15 | +0.40 | |
| `fade_dev_14` (+) | raw, close | +0.08 | −0.51 | +1.03 | +0.31 | +0.58 | +0.82 | +0.31 | +0.47 |
| | orth, close | +0.44 | −0.48 | +1.02 | +0.36 | +0.58 | +0.82 | +0.41 | +0.74 |
| | raw, model | — | — | +1.00 | +0.25 | +0.74 | +0.74 | +0.38 | |
| | orth, model | — | — | +1.03 | +0.30 | +0.74 | +0.76 | +0.41 | |
| `fault_dev_28` (−), 2025–26 only | raw, close | | | | | | | +1.52 | |
| | orth, close | | | | | | | +5.55 † | |
| | raw, model | | | | | | | +1.47 | |
| | orth, model | | | | | | | +5.19 † | |

† Artefact-prone (point 5 below).

**Joint fits beyond the close** (z, with P(β > 0); `readings_joint.csv`):

| Window (matches, blocks) | `spd_L_B` | `spd2_L_B` |
|---|---|---|
| 2013–24 (29,895, 141) | +0.84 (0.80) | **+1.98 (0.975)** |
| 2025–26 (4,394, 21) | **+2.81 (0.995)** | +1.02 (0.84) |

| Window | `spd_L_B` | `gap_L_B` |
|---|---|---|
| 2013–24 | +2.73 (0.996) | −1.73 (0.04) |
| 2025–26 | +3.43 (0.999) | −1.08 (0.15) |

**What the readings show (observed).**
1. **`spd2_L_B` held its registered sign beyond the close in all four eras** (raw +1.86, +2.03, +2.12, +0.75).
   * Over 2013–24: +2.76, its range above zero (P(β > 0) 0.997); pooled eras +3.34. 2020–24 +1.96 (P 0.97); 2025–26 +1.90 (P 0.96).
   * The first serve on the same fit: +0.38, +1.46, +3.97, −0.41; 2013–24 +1.94 (P 0.97); 2025–26 +3.81.
   * Beyond the model's 48 inputs (orth) it keeps +2.54 over 2013–24; its 2023–24 cell falls to −0.03.
   * Beyond the model's forecast: 2020–22 +1.89, 2023–24 −0.30, 2025–26 +1.54 (P 0.93); 2020–24 +0.97 (P 0.83). Unresolved.
   * `spd2_T_B` (14 days) shows the same pattern, weaker in every window (2013–24 +1.98).
2. **Jointly with `spd_L_B`:**
   * over 2013–24 the second serve keeps z +1.98 (P 0.975) and the first falls to +0.84 (P 0.80);
   * in 2025–26 the first keeps +2.81 (P 0.995) and the second falls to +1.02 (P 0.84).
3. **The gap cleared zero in no window.** Over 2013–24 it reads −0.85 (P(β > 0) 0.20), leaning against its registered sign. Beside `spd_L_B` it reads −1.73 (P 0.04) in 2013–24 and −1.08 (P 0.15) in 2025–26.
4. **The fade cleared zero in no window** (|z| ≤ 1.03 in every form and base). 2013–24 +0.58 (P 0.72). Where its coverage is highest, 2023–24 (76%): +0.31.
5. **Fault speed, 2025–26 only:** raw +1.52 (P 0.93) beyond the close, +1.47 beyond the model, in its registered direction.
   * Its orth form reads +5.55 and +5.19. **That is an artefact, not evidence.**
   * Its 439 values lie in 6 of the window's 21 four-week blocks (observed, outcome-free), so the cluster-robust SE rests on six effective clusters. And the orth form projects on 48 inputs fitted on those 439 rows.

**What I infer.**
1. **Second-serve speed form is the steadier speed signal over the discovery seasons.** It held its sign in every era, including 2023–24, when the first serve's turned (the edge-anatomy study's "cost in 2023").
2. **Over 2013–24, most of what the two forms share beyond the close is carried by the second serve.** The first serve dominates only in 2025–26, the window where the first-serve lead was found, so that dominance is partly the selection.
3. **The signal is not the effort serve gaining on the controlled one.**
   * The gap is first − second. With the first serve held fixed, a second serve slower than normal went with losing: that is the gap's negative sign beside `spd_L_B`.
   * So the signal lives in what both serves share, and the second serve gauges it with less noise.
   * The registered gap direction bet on the effort-serve channel. The data lean to the competing channel: pace on the controlled serve.
   * That shared part fits physical form and confidence. It also fits any match-level shock common to both serves that per-event offsets do not remove, such as a court's own radar at the Slams (an assumption, not checked here) or a hot day. The two are not separable here.
4. **The within-match fade carries no detectable information beyond the close at this coverage.** A single match's fade is mostly sampling noise (§ 3.5).
5. **Fault speed cannot be judged:** three Slams of data.

## 6. Recommendation

1. **Register the second-serve form, `spd2_L`, for the check on unseen matches, as a second hypothesis in the speed family.**
   * **HS2:** β(`spd2_L`) > 0. The player whose second serve has recently risen above his own normal beats the close.
   * **Build it exactly as here:**
     * the second-serve history and `use2`, the constants of `constants.json`, the standardiser 2.119 km/h;
     * scenario B's release before 8 Oct 2026 and the daily feed's from 8 Oct, as T4's rule.
   * **Live:** the daily feed's key statistics carry the second-serve average (`live_panel.new_rows`), so it can be built as `spd_L_D` is. That build does not exist yet; nothing in production was touched.
   * **Test HS and HS2 with Holm inside the speed family,** at the look's level. That keeps the family's error rate; the cost is that the first of the two is tested at half the level. Report the two columns' joint fit beside the verdicts, without verdict words.
   * **Why**, in the order fixed in § 1:
     * (i) its sign held in all four 2013–24 eras beyond the close, as the first serve's did not;
     * (ii) it adds to `spd_L_B` over 2013–24 (joint z +1.98) and is not redundant in 2025–26 (P 0.84);
     * (iii) 2025–26 reads +1.90.
   * **What it rests on:**
     * seen matches only;
     * 2013–24 is a fair discovery window for this column, which nobody had read before today;
     * but the speed family was picked for its 2025–26 showing, and this was one of five columns tried;
     * its edge beyond the model's own speed stage is unresolved (2020–24 P 0.83, 2025–26 P 0.93).
   * **The alternative I do not recommend now:** one combined speed score (the two columns' mean over their frozen RMS) as the family's single test. It has more power if both are real, but it would change T4 after its lock-in, with weights chosen with these readings in view.
2. **Do not register the gap, the fade or fault speed.**
   * The gap is unresolved and leans against its registered sign; the two forms already hold its information.
   * The fade is unresolved in every window. Its coverage is uneven (Slams only before 2021), and live use needs point-level data within days.
   * Fault speed has no history before 2025 on disk.
3. **What would change this: the ATP Stats Centre per-point files (package P9).** They would give the tour's fade and fault speeds from 2018 and from 2025 on, the only route to a real discovery test of either.

## 7. Threats to validity, and where a flaw would hide

1. **Second-serve key statistics** (most rows from 2022 on) are the ATP's "2nd Serve Average Speed". Whether it includes double faults' second serves, and whether it is a ceiling like the first serve's (the −0.5 shift the panel applies to both), is *unknown*; `n2` there counts second-serve points, double faults included.
2. **The second-serve constants rest on a flat criterion** (§ 3.2). The sensitivity's 0.995 correlation says this does not move the column; it does not say the constants are right.
3. **The fade is mostly sampling noise per match** (4.6 of 6.1 km/h SD). Thirds are by his own serve count, not by time.
   * Conditions that change within a match (nightfall, the roof, temperature, ball changes) are not removed. The opponent's fade in the same match would be the control; it was not used, to keep the brief's definition.
   * The fade can also track how close and long the last match was, which the market sees through the score.
4. **The fade's sample changes by era:** Slams only before 2021 (8–14% of matches), mostly the tour in 2022–24 (67–81%), then sparse again (31%, 14%). Its 2013–24 reading is dominated by 2022–24 tour matches; its 2025–26 one by Slams and early-2025 tour events.
5. **The fade's clock is the instant rule (lf + 1),** as the brief asks. Live, it needs point-level data within a day or two: at the Slams the live feeds, on the tour the ATP's match centre. Under the weekly feed's release (scenario B) a Slam's own rounds would never see each other, and the column would almost vanish there.
6. **Fault speed:** three Slams, 439 matches valued. Any reading is descriptive.
7. **Small key effects:**
   * The 2018 targets use the current timing table; the other keys use the 7 Oct clock (90 of 68,606 sides differ between the two).
   * The fade rows' sides come from the source links' orientation; a match whose A and B a later rebuild swapped (about 21) would give the opponent's id.
8. **Multiplicity:** five new columns × seven windows × two forms × two bases. The 2025–26 window is where the speed lead was found, so it cannot confirm any speed column.
9. **What the speed columns measure** (§ 5, inference 3). The signal sits in what both serves share within a match. Player form is one explanation; a shock common to both serves that the per-event offsets miss is another (a Slam court's own radar, an assumption not checked here; heat and balls that vary by day). A per-court or per-day offset would separate them; none was built here.
10. **The recommended column is one of five read.** It was declared this memo's primary before reading (§ 1). Its 2013–24 z of +2.76 would still clear a five-way Bonferroni bar (one-sided p ≈ 0.003 × 5), but that is a statement about these seen seasons, not a confirmation.

**What a re-design would do.**
* Collect the ATP Stats Centre per-point files (P9): the tour's fade from 2018 and from 2025 on, and fault speeds on the tour.
* Use time-based thirds, with the opponent's fade in the same match as the conditions control.
* Tune the second-serve constants by a better-identified, outcome-free criterion (maximum likelihood of the state-space model, or the latency study's within-match information gain).

## 8. What I read and when (PDT, 16 Oct 2026)

| When | What | Results seen |
|---|---|---|
| 14:13–14:20 | Code and documents: CLAUDE.md, the brief, the edge-anatomy README, `readings.py`, `common.py`, the study's process log and lock-in, the builder chain (`adaptive/columns.py`, `latency/features_latency.py`, `features.py`, `panel.py`, `live_panel.py`, `infosys_atp_backfill/columns.py`), the constants' provenance (`design/modeller_state.py`, `modeller_variance.json`, `engineer_systems.py`, `design/2_audit.md` C3) | Already-published readings only (the edge-anatomy README's ledger: `spd` z +3.8 in 2025–26, +2.7 in 2013–24; −1.32 mLL in 2023) |
| 14:20–14:26 | Outcome-free counts and distributions: the augmented panel (second-serve, count and fault-speed coverage by year and source; spd2 quantiles and its low tail), the point tables' coverage by source and year, the Infosys raw files' coverage, the release lags by source under scenario B | Speeds and counts only |
| ~14:25 | **`readings.seen_frame('atp')` loaded once for alignment:** its shape, column names, seasons and last tournament date; its `in_spd` (edge anatomy's speed column) compared with the stored `spd_L_B` by match id (equal on all 18,652 rows that hold both); the 2018 gap found there | **No result column was printed, summarised or used** |
| 14:26 | `frame_keys` by tour and season (no men's 2018); match-id formats | Keys only |
| 14:28 | § 1 saved: directions, the gap's form, the decision order | None |
| 14:34 | Reproduction (§ 3.1) | Values only |
| 14:35 | Constants (§ 3.2) | Speeds only |
| 14:38–14:41 | The fade, fault and builder columns built; coverage | Values only |
| 14:41 | Probes started (§ 4) | Values only |
| 14:41 | Orientation check: the 10 Oct frame's player ids against the keys' (frame read with match id, tour, season and tournament date only) | Ids only |
| 14:42 | Outcome-free correlations among the new columns; the fade's distribution by source and year | Values only |
| 14:43 | § 1 amended: the second joint fit (`spd_L_B` with `gap_L_B`) | None |

*The first three rows' times are approximate: everything in them happened between the brief's file time (14:11) and my first clock reading (14:27), in the order listed.*

*Correction, 14:45: the times in this table up to here were first written as estimates (14:44, 14:47, 14:52, 14:58), which ran ahead of the clock. They are replaced by the files' modification times; the § 1 amendment's time is corrected the same way.*

Continued (times from the clock):

| When | What | Results seen |
|---|---|---|
| 14:41–14:59 | Probes: second serve (pass 14:48), gap (14:57), first serve on the extended keys (14:58), fade (14:58); fault speed failed its leaky control (14:58), then passed with the longer peek (15:00) | Values only |
| 15:00 | § 4 written | None |
| **15:01:00–15:04:18** | **The readings, one run of `speed_read.py`:** every registered column, all windows, forms and bases; the two joint fits. The only look at results in this work | **All of § 5** |
| 15:05 | Fault values' four-week blocks (frame read with match id, tour, season, tournament date and debut flag only) | Counts only |
| 15:06 | The edge-anatomy process log and ledger header read, to find how its 2013–24 speed z was computed; the pooled-era z's derived from `readings.csv` (no new fit) | Already-computed readings |
| 15:07–15:10 | The builds re-run on the final code: the column files are byte-identical | Values only |
| 15:08 onward | §§ 5–7 written | — |

## 9. Reproduction

```
./python.sh src/eda/serve_return_leads/speed_ext.py reproduce      # spd_L_B exactly; the 2018 extension
./python.sh src/eda/serve_return_leads/speed_ext.py constants      # constants.json (outcome-free)
./python.sh src/eda/serve_return_leads/speed_ext.py build          # builder_columns.parquet / .json, builder_coverage.csv
./python.sh src/eda/serve_return_leads/speed_ext.py probe first    # probe_spd.json (spd_L_B on the extended keys)
./python.sh src/eda/serve_return_leads/speed_ext.py probe second   # probe_spd2.json
./python.sh src/eda/serve_return_leads/speed_ext.py probe gap      # probe_gap.json
./python.sh src/eda/serve_return_leads/speed_ext.py fade           # fade_dev_14.* with its probe
./python.sh src/eda/serve_return_leads/speed_ext.py fault          # fault_dev_28.* with its probe
./python.sh src/eda/serve_return_leads/speed_read.py               # readings.csv, readings_joint.csv, readings.json
```

* **Outputs** are in `data/studies/serve_return_leads/speed/`. The build reads no result column; the readings go through `readings.py` only.
* **Every file is new.** No existing file was edited, and no git command was run.

**Reviewer checklist.**
* `reproduce.json`: 0 mismatches in every column.
* Each `probe_*.json` and each window column's `.json`: moved 0, leaky above 0.
* `readings.json`: the last tournament date is 2026-07-28.
* § 1's directions match `REGISTERED` in `speed_read.py`.
* The fault orth z's are flagged, not used.
