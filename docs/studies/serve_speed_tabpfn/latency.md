# When speeds arrive late: does the speed adjustment stay predictive?

7–8 October 2026 · A follow-up to the [serve-speed TabPFN study](README.md). **Exploratory:**
* 2024–2026 results had already been read by the study's pre-registered test;
* the scenarios and the headline comparisons were fixed in [plan.md](../../../data/studies/serve_speed_tabpfn/latency/plan.md) before any computation;
* the outcome run was made once (look ledger row 40).

**Keys.**
* **Gains are milli-log-loss (mLL) per match,** men 2024–26 (7,068 matches). **Positive = the speed adjustment is better** than the calibrated model without it.
* **Intervals are 95%;** one that spans 0 is a tie.
* **Labels:** **observed** = computed here; *inferred* = reasoning; **suggestion** = not decided.

## In short

**The question** (the owner, 7 Oct 2026): "If we CANT get the speed reading in time, is there a way to make it still predictive?"

**Why it matters** (*observed*). The study's +0.41 mLL let each match's speed reach the next match's feature as soon as the match ended. Today's sources are slower:
* **ManTennisData** (all tour-level speeds from 2025) publishes every **Sunday at 16:10 CET** and carries matches finished by the **Friday**. Its commit history shows a median lag of 5 days, and Saturday and Sunday matches wait a further week.
* **The Slam feeds** are collected **after each event.**
* So at bet time **no speed from the current event is ever available.** The latest usable reading is a median **17 days** old instead of 7, and only 50% of men have their latest reading in hand against 88%.

**The answer** (*observed*, exploratory). The adjustment was refitted walk-forward on what each scenario makes available.

| Scenario | Gain (mLL; positive = the adjustment better) | Share of the study's gain |
|---|---|---|
| Instant: the study, as run | +0.41 [+0.04, +0.78] | 100% |
| **Today's sources, unchanged** (weekly ManTennisData; Slams after the event) | **+0.29 [+0.01, +0.56]** | **70%** |
| **Today's sources, with a 28-day memory instead of 14** (chosen without results) | **+0.38 [+0.11, +0.64]** | **92%** |
| Today's sources, filling late speeds from box scores (the "nowcast") | +0.27 [+0.00, +0.54] | 66% |
| A 1-day delay on everything (a daily collector) | +0.41 [+0.09, +0.73] | 100% |
| A 3-day delay | +0.33 [+0.10, +0.56] | 80% |
| A 7-day delay | +0.19 [+0.05, +0.34] | 47% |
| A 14-day delay | +0.11 [−0.00, +0.21] | 26% (tie) |

**Reading.**
* **Yes: it stays predictive with today's slow sources.** Today's sources are best reported as a range: **+0.27 to +0.38 mLL, 66–92% of the instant gain**, across the three methods tried. The auditor's caution: the 28-day memory was not one of the two headline comparisons fixed in advance, so picking the best of three flatters it.
  * As built, the gain is about 70%.
  * With the speed form remembered longer (a 28-day half-life, chosen without results), it is about 90%.
  * **Independent check.** The auditor rebuilt both today's-sources columns with its own code, identical to 2.5e-14, and its leak probe on the 28-day version moved nothing ([audit](../../../data/studies/serve_speed_tabpfn/latency/4_audit.md)).
* *Inferred:* most of what predicts is a man's speed form over the last few weeks, not only yesterday's match. Earlier-event readings remain for 85–88% of players, and a longer memory stops them fading too fast.
* **The box-score nowcast does not help.** A box score adds only 0.03 R² beyond what the filter already knows about a player's speed.
* **A one-day delay costs nothing.** A daily collector would keep the full gain.

**Suggestions** (none decided):
1. For live use with today's sources, compute the speed form with the **28-day memory (B-M1)**. The [adaptive follow-up](adaptive.md) then found the 28-day memory better even with instant speeds, so it is the better memory everywhere.
2. **Run the weekly ManTennisData refresh** (the acquisition study's option 2). Without it, live forecasts get no tour-level speed at all.
3. **Consider a daily source.** It needs the owner's decision (§5).

## 1. When each speed becomes usable

*Observed* ([engineer's note](../../../data/studies/serve_speed_tabpfn/latency/1_engineer.md); `latency/availability.parquet`).

* **ManTennisData,** from all 89 commits of 2025–26 and 10 consecutive file versions.
  * Every commit lands on a Sunday at 16:10 CET (14:10 UTC in summer).
  * A match appears in the first commit after both first-serve averages exist:

    | Match day | Next Sunday's commit | A week later |
    |---|---:|---:|
    | Mon | 92 | 0 |
    | Tue | 202 | 2 |
    | Wed | 114 | 2 |
    | Thu | 72 | 20 |
    | Fri | 62 | 9 |
    | Sat | 27 | 60 |
    | Sun | **0 of 43** | 52 |

  * Six weekly commits were missed in 2025–26, four in a row in May–June 2026.
* **Rule B (today's sources).**
  * Tour level: the speed is usable from the Monday after the first Sunday on or after `lf + 2`, where `lf` is the match's latest possible finish. It reproduces 91% of the actual commits.
  * Slams: usable from the event's last main-draw day + 3.
  * Box scores (Tennis My Life, downloaded daily): the next day.
* **What it leaves at bet time,** men 2024–26:

  | Latest reading | Usable at the match: instant | Usable: today's sources |
  |---|---:|---:|
  | From an earlier event, non-Slam | 100% | 85.5% |
  | From the same event, non-Slam | 62% | **0.5%** |
  | Slam, earlier event | 100% | 88% |
  | Slam, same event | 99.7% | **0.0%** |

## 2. What was built

*Observed* ([modeller's note](../../../data/studies/serve_speed_tabpfn/latency/2_modeller.md); `latency/variants.parquet`). Each variant recomputes the study's speed form using only the speeds usable at the match's earliest start. This applies to the player's own history and to the event-radar offsets alike.

* **M0:** the study's filter unchanged (14-day half-life).
* **M1:** the half-life re-tuned for the delay on result-free targets: the within-match speed difference on 2019–22, with 2023 as the check. It chose **28 days** for both B and the 7-day delay.
* **M2, the nowcast:** a match whose speed is late but whose box score is in enters the filter as a speed estimate from its box score.
  * The inputs are aces, double faults, first serves in, first- and second-serve points won and service points, as deviations from the player's own rates.
  * The estimate has its own, larger noise.
* **Checks:**
  * the instant variant equals the study's column exactly;
  * a leak probe on B and B-M2 moved nothing of any match that started before the cut, while a leaky control moved 3,393;
  * 20 tests pass;
  * the auditor's independent rebuild of B-M0 and B-M1 is identical (2.5e-14), and its probe on B-M1 (15 cut days) moved nothing.
* **Under B,** 2.2% of men's sides still use a row from their current event. All are week-one rounds of two-week events, released the following Monday: the weekly rule working, not a leak. At the Slams it is 0.

## 3. Result-free readings (seasons ≤ 2023)

*Observed* (`latency/readings.json`). "Share" is the share of the instant variant's information about the next match's within-match speed difference. "Gate" is the effect on first-serve points won, per SD of the variant, with event-edition fixed effects.

| Variant | Share 2019–22 | Gate: first-serve points won, ratio to instant | Correlation with the instant column, 2024–26 |
|---|---:|---:|---:|
| Today's sources (B-M0) | 0.58 | 0.69 | 0.69 |
| B, 28-day memory (B-M1) | 0.62 | 0.77 | 0.67 |
| B, nowcast (B-M2) | 0.60 | 0.74 | 0.71 |
| 7-day delay | 0.46 | 0.51 | 0.64 |

* Single-season 2023 readings tie for every delayed variant.
* *Inferred:* result-free, today's sources keep about 60–75% of the information. The outcome run (§4) agrees.

## 4. The outcome run (exploratory, once)

*Observed* (`latency/results_latency.csv`, `.json`).
* **The harness.** `score_latency.py` reuses the study's scorer unedited. It first reproduced S9 (+0.410 [+0.045, +0.775]) and S0 exactly, a difference of 0.0.
* **For each variant:**
  * the adjustment was refitted walk-forward on 2019..Y−1 and shrunk (τ = 0.05) as decided;
  * it was compared with the calibrated model.
* **The headline comparisons fixed in advance** were today's sources unchanged (B-M0) and with the nowcast (B-M2); everything else is descriptive.

| Variant | Adjustment, shrunk (mLL; positive = better) | Unshrunk | Information test, log-odds per unit of the variant (positive = the faster-trending man wins more than the model says) |
|---|---|---|---|
| Instant (as run) | +0.41 [+0.04, +0.78] | +0.45 [+0.00, +0.91] | +0.065 [+0.012, +0.118] |
| **B-M0, today's sources** | **+0.29 [+0.01, +0.56]** | +0.31 [−0.03, +0.65] | +0.054 [+0.014, +0.095] |
| **B-M1, 28-day memory** | **+0.38 [+0.11, +0.64]** | +0.42 [+0.09, +0.74] | +0.064 [+0.022, +0.106] |
| **B-M2, nowcast** | **+0.27 [+0.00, +0.54]** | +0.29 [−0.05, +0.63] | +0.054 [+0.012, +0.096] |
| 1-day delay | +0.41 [+0.09, +0.73] | +0.46 [+0.08, +0.84] | +0.070 [+0.027, +0.113] |
| 3-day delay | +0.33 [+0.10, +0.56] | +0.37 [+0.10, +0.65] | +0.064 [+0.027, +0.102] |
| 7-day delay | +0.19 [+0.05, +0.34] | +0.22 [+0.05, +0.39] | +0.066 [+0.024, +0.109] |
| 7-day delay, 28-day memory | +0.30 [+0.12, +0.48] | +0.34 [+0.14, +0.55] | +0.071 [+0.027, +0.116] |
| 14-day delay | +0.11 [−0.00, +0.21], tie | +0.12 [−0.00, +0.25], tie | +0.046 [−0.001, +0.092], tie |

**By season,** the 28-day memory under today's sources (B-M1): 2024 +0.11 [−0.32, +0.54], 2025 +0.36 [−0.09, +0.82], 2026 +0.79 [+0.16, +1.43]. Single seasons tie except 2026. The instant version shows the same pattern: +0.20, +0.32, +0.87.

**The fitted adjustment** under B-M1 (shrunk, per unit of its column): 0.028 (2024), 0.029 (2025), 0.038 (2026). The column's unit is 1.95 km/h.

## 5. Routes to faster speeds

**Update, 8 Oct 2026:** the owner [approved all scraping for sports prediction, decryption included](../../decisions/2026-10-08-scraping-approved.md). Every route below is now allowed, so the "Position" column is history. What remains is building the collectors.

*Observed* (the engineer's §5; the decisions quoted there).

| Route | Lag | Position under the decisions |
|---|---|---|
| ATP Stats Centre pages, collected daily (ManTennisData's own route; its collector is a separate repository) | next morning | **Needs the owner's decision.** atptour.com's terms forbid systematic retrieval. Whether rendering the pages counts as the barred decryption of the Stats Centre files is the owner's call |
| Wimbledon and US Open feeds during the event | minutes | **Already allowed** (24 Sep). Collection during an event waits for the betting pipeline (6 Oct) |
| AO and RG Infosys files during the event | minutes | Allowed only for AO 2025, RG 2025 and RG 2026; 2027 needs the decision extended |
| AO match centre (plain API), during the event | minutes | Covered for AO 2026 (24 Sep); Tennis Australia's terms; collection during the event waits (6 Oct) |
| Flashscore | minutes | Slams only; no decision covers it |
| Decrypting the ATP's Infosys files | minutes | Barred (7 Oct) |

*Inferred:* a 1–3-day lag keeps 80–100% of the gain. So a daily tour-level collector plus live Slam feeds would restore essentially the whole +0.41. With today's sources, the 28-day memory gets close.

## 6. What it means

* **Observed.**
  * The speed adjustment keeps most of its value when speeds arrive late: 70% as built, 92% with a longer memory. It disappears only when every speed is two weeks late.
  * The nowcast from box scores adds nothing.
* *Inferred.* The study's half-life (14 days) was tuned for instant data. With late data the best memory is longer, because the readings that arrive are older.
* **Suggestions:**
  1. **Use the 28-day memory (B-M1) for live forecasts with today's sources.**
     * It changes one constant of the speed filter, and the adjustment is refitted on it.
     * This is the owner's call: it changes what "the current best model" computes live.
     * With a daily source, the study's instant version applies.
  2. **Schedule the weekly ManTennisData refresh** for Monday, after the Sunday 16:10 CET commit.
     * Collect each Slam's feed the day after its final at the latest.
     * Watch for missed weeks: four in a row in May–June 2026.
  3. **For the full gain, decide on a daily tour-level source.** Collect the Slam feeds during the event once the betting pipeline exists (6 Oct cadence).
  4. **Drop the nowcast.**

## 7. Caveats

* **Exploratory.**
  * 2024–26 was already read by the pre-registered test.
  * Eleven variants were scored, and only two comparisons were fixed as headlines. B-M1's 28-day memory was chosen without results, but it was not a headline. Reading the best of three after seeing outcomes biases its gain upward.
* **A pre-run deviation from the plan.** M1 and M2 were tuned on the column's own information about the within-match speed difference, not on the full speed forecast.
  * The full-forecast criterion picked a 42-day half-life that lost on the 2023 check.
  * The change was recorded in the code, the metadata and the note before the outcome run; the note only about 40 s before the run's check step.
* **The live build must be rebuilt.** The acquisition study's `speeds.parquet` was rewritten (16:21, 7 Oct) after this study's panel was frozen. These numbers use the frozen panel. A live build must rebuild and re-hash the panel and the features.
* **The intervals are wide** (lower bounds near 0 for B-M0 and B-M2), and single seasons tie except 2026.
* **Scenario B is modelled from 2025–26 publishing behaviour** and applied to every season. The real 2025 data arrived in a one-off autumn backfill, so a live system in early 2025 would have had less.
* **Bet time.** The scenarios assume a bet at the match's earliest start. A bet a day earlier adds about a day of delay. That costs nothing at the 1-day scale (L1), but matters on top of today's sources.
* **Closing prices** are archived average closes, not bet-time prices.

## 8. Files

| What | Where |
|---|---|
| Plan (fixed first), notes, audit | `data/studies/serve_speed_tabpfn/latency/`: `plan.md`, `1_engineer.md`, `2_modeller.md`, `3_strategist.md`, `4_audit.md` |
| Availability model | `src/eda/serve_speed_tabpfn/latency/availability.py` → `latency/availability.parquet`; evidence in `latency/evidence/` |
| Variants and readings | `src/eda/serve_speed_tabpfn/latency/features_latency.py` → `latency/variants.parquet`, `variants_meta.json`, `readings.json` |
| Outcome run | `src/eda/serve_speed_tabpfn/latency/score_latency.py` → `latency/results_latency.csv`, `.json` |
| Tests | `test/serve_speed_tabpfn/test_ssp_latency_*.py` |
