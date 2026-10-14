# Serve-speed change in the best TabPFN model: an expanding-window test on 2024–2026

7 October 2026 · Research evidence, not a production, model or betting decision. The test ran once, from a hashed [pre-registration](preregistration.md) (SHA-256 `19b5ac0d…8b0dde`).

**Owner's decision, 7 Oct 2026:** "the current best model" now includes the walk-forward speed adjustment of §6.4 ([decision](../../decisions/2026-10-07-speed-nudge.md)).

**Follow-up, when speeds arrive late** ([latency.md](latency.md); exploratory). With today's sources, no same-event speed is available at bet time: ManTennisData publishes weekly, and the Slam feeds are collected after each event. The adjustment still keeps +0.27 to +0.38 mLL (66–92% of +0.41); the top of the range needs a 28-day memory. A one-day delay costs nothing.

**Follow-up, adaptive memory** ([adaptive.md](adaptive.md); exploratory). A switch (14-day memory when the speeds are in hand, 28-day when they are late) was built and audited. It was beaten by **always using the 28-day memory**, in every availability scenario, instant included: instant +0.54 against +0.41; today's sources +0.38; switch − always-28 = −0.09 to −0.13 mLL, 28-day better.

**Note for reviewers (9 Oct 2026): a flaw in this study's intervals, found after the test ran. The study was not re-run.**
* **The flaw.** Most comparison intervals here add each arm's seed-to-seed variance as if the two arms' seed noise were independent (§5). Both arms used the same TabPFN seeds (random states 0–15, or 0–7), so most of that noise is shared and cancels in the difference. Adding both counts it twice.
  * Found by the adoption framework's statistics review ([finding 1](../adoption_framework/review_statistics.md)). With the same interval code (`score.paired_stats`), a model compared with itself got ±0.087 mLL instead of 0.
* **What it does.** The affected intervals are too wide; the estimates are right.
  * The verifier's null worlds already showed it. The registered interval rejected a true null in 0.35–0.75% of them, against a nominal 5% (§5). The block-only interval, which has no seed term, rejected at about its nominal rate: 1.0–3.4% one-sided against 2.5% (`data/studies/serve_speed_tabpfn/design/verifier_worlds/synthetic/w1_b0_*`). *Inferred:* the double count is the reason.
* **What it can change.** A corrected (paired) interval is never narrower than the block-only one, which `results.csv` holds for every affected row, and is narrower than the registered one when the arms share seed noise.
  * **Affected:** P2's registered and calendar-week intervals (S11), and S1–S5, S6a, S7, S8 and S14.
  * **Only two readings could come to exclude 0** (positive = the speed arm better): S8's registered statistic as a column (A2) against the base, +0.10 [−0.07, +0.26], block-only [+0.01, +0.18]; and S8's arm with women's values (A3) against the base, +0.15 [−0.04, +0.34], block-only [+0.01, +0.28].
  * Every other affected interval spans 0 even at its narrowest. That includes P2 (block-only +0.07 [−0.02, +0.15]).
  * **Not affected:** S9, the nudge behind the owner's decision (+0.41 [+0.04, +0.78], a block-only interval); S11's block-only interval; S13; the coefficient tests S0, S6b and S12; and the latency and adaptive follow-ups (block-only intervals).
* **Not re-run, on purpose.** The registered test ran once, and its results stand as registered.
  * A paired re-read would be a new look at the 2024–26 results, including 2025–26, the proposed clean holdout. Log it in the [look ledger](look_ledger.md).
  * The shared function now offers the paired term: `score.paired_stats(..., matched_seeds=True)` ([checklist](../adoption_framework/checklist.md), item 1). It is off by default, so this study's scorer still computes the registered interval.
* **The code fingerprint changed.** The fix lives in `score.py`, so the harness's code hash (`common.code_hash()`) no longer equals the `SCORER_CODE_SHA256` that the pre-registration and `results.json` record.
  * Every run that checks it had already run.
  * `score.py --synthetic --arms real` now refuses, and the latency and adaptive `--check` modes report `scorer_code: false`. This fix is the reason, not tampering.
  * The default path computes exactly what it did, so the registered numbers still reproduce.

**Keys.**
* **Gains are milli-log-loss (mLL) per match, paired.** **Positive = the speed model is better** (lower log loss) than the model without speed, unless a row says otherwise.
* **Coefficients are log-odds per unit of the column.**
  * One unit of `spd_f` = 2.224 km/h of the two players' speed-state difference.
  * One unit of `spd_raw` = 5.998 km/h, the published statistic's SD.
  * **Positive = the man whose serve speed rose more than his opponent's wins more often than the model says.**
* **Intervals are 95%.** One that spans 0 is a **tie**.
* **Labels:**
  * **observed** = computed here, with its file;
  * *inferred* = reasoning;
  * **suggestion** = not decided.

## In short

**The question** (the owner, 7 Oct 2026). The men's serve-speed change was the one point-derived signal that had replicated: +0.090 [+0.017, +0.162] log-odds per SD in 2022–24 given the model. Now that much more speed data has been downloaded, how should it go into the best local, non-thinking TabPFN-3.5? And does it improve prediction scores in 2024–2026 in an expanding window, and by how much?

**What was done.**
1. **The data.**
   * Every serve-speed source the project holds was merged into one leak-proof table: 42,900 player-matches. That includes this morning's downloads:
     * ManTennisData, the ATP's per-match first-serve averages 2021–26;
     * the decrypted AO 2025, RG 2025 and RG 2026 point files.
   * The engineer found the measuring systems break inside the test years. Same men, Wimbledon 2024→25: **+8.5 km/h**. So each match's speeds are re-centred on what each event's radar read, using only matches already finished.
2. **The feature.**
   * A two-speed Bayesian filter tracks each player's first-serve speed: a slow "normal level" and a fast "current form" that fades with a 14-day half-life.
   * The column is the two players' difference in current form.
   * **This is the imputation and the prior:**
     * a player with little data gets a small, shrunk value;
     * a player with no recent data gets the prior, "no change" (0);
     * the column is never missing.
3. **The test.**
   * The 58-input model was refitted with this one extra column on the GPU, season by season: 2024 trained on 2013–2023, 2025 on 2013–2024, 2026 on 2013–2025, with 16 seeds.
   * It was compared with the same model without the column on 7,068 men's matches.
   * The design was fixed and hashed before this study read any 2024–2026 result (§5 lists what was not blind).
4. **The team.** Five Opus agents and the lead (§8):
   * an engineer, a Bayesian modeller and an integration strategist designed and built;
   * an auditor ruled between them and red-teamed the build;
   * a verifier checked the scorer on synthetic outcomes.

**What the feature predicts** (*observed*, before any match result was read).
* A man serving faster than his own recent norm serves better next time: **+0.33 percentage points of first-serve points won per SD of his speed state (1.12 km/h) [+0.20, +0.46]**.
  * This is beyond his box-score form, and with event-edition fixed effects (statistic targets, 2022–23).
* It carries what the published 14-day window carries, and more. Fitted together on the same targets, f̂ keeps **+0.45 [+0.30, +0.59]** pp per SD, and the window adds nothing positive (−0.17 [−0.32, −0.01]).

**The answers** (*observed*, men 2024–26, 7,068 matches; `data/studies/serve_speed_tabpfn/results.json`):

| Question | Result | Reading |
|---|---|---|
| **Primary (P2): does the speed column improve the TabPFN model's log loss?** (positive = with speed better) | **+0.07 [−0.05, +0.18] mLL** | **Tie.** About 3% of the model's own edge over the closing price |
| Is there speed information the model lacks? (S0, the information test; positive = the faster-trending man wins more than the model says) | **+0.065 [+0.012, +0.118]** log-odds per unit | **Yes.** The interval excludes 0 |
| Does the original 14-day statistic replicate in the blind seasons 2025–26? (S12; positive as above) | **+0.103 [+0.029, +0.178]** per 5.998 km/h, p 0.009 | **Yes.** Consistent with the published +0.090 |
| How much of that information did TabPFN use? (S10, capture; a point value) | **8%** | TabPFN leaves almost all of it unused |
| The same information as a "nudge" on the model's output (S9, a pre-registered **secondary**; positive = the nudge better) | **+0.41 [+0.04, +0.78] mLL** (shrunk); +0.45 [+0.002, +0.91] unshrunk | **Better** (descriptive). About 19% of the model's edge over the close |
| For scale: the model against the calibrated closing price (S13; positive = the model better) | +2.20 [+1.10, +3.30] mLL | The model leads the close |

**Reading** (the pre-registered decision table, row 3).
* Row 3 reads, verbatim: "S0 detects information beyond the base; P2 ties. P2 has less power than S0 at small effects and loses power as capture rises, so the tie does not show the column fails; S10 (capture) and S9 (nudge) say whether it delivers."
* The speed state carries information beyond the best model, which already holds the closing odds. The registered statistic replicates out of sample (S12).
* **Put in as a TabPFN column, it does not measurably improve the score.** TabPFN applies only about 8% of it (S10; *inferred* to be the main reason).
* Applied directly to the model's output as a small walk-forward logistic adjustment (S9), it was better by about **0.4 mLL** [+0.04, +0.78].
  * That is a pre-registered *secondary*, so it is descriptive, not the confirmatory claim.
  * Four of 30 secondary intervals exclude 0, against about 0.6 expected by chance (P ≈ 1.7%).

**Suggestion** (for the owner): integrate serve speed as a nudge on the TabPFN forecast rather than as a TabPFN column, and confirm it prospectively (§7).

## 1. The question and the starting point

**The starting point** (the [point-sequence study](../point_sequence/README.md), §5.6). The men's first-serve speed over the last 14 days minus the last 364 days, A − B, gave:
* replication 2022–24: +0.090 [+0.017, +0.162] log-odds per SD given the model, and +0.097 given the close;
* discovery: −0.018, a tie, on only 860 matches.

It was the one point-derived statistic with a replicated signal. It was data-starved:
* the men's 2025–26 coverage was 13% of matches;
* there was no tour-level speed after April 2025.

**The data since then** ([serve-speed acquisition](../serve_speed_acquisition/README.md), 7 Oct 2026, the owner's decision):
* **ManTennisData:** the ATP Stats Centre's per-match first-serve average, tour level and some Challengers, Oct 2021 – Oct 2026.
* **The decrypted Infosys files** of AO 2025, RG 2025 and RG 2026: every point's serve speed, main draws and qualifying, both tours.

## 2. The data: one table from every source

*Observed* (`src/eda/serve_speed_tabpfn/panel.py`; `data/studies/serve_speed_tabpfn/speed_panel.parquet`; [build note](../../../data/studies/serve_speed_tabpfn/design/3_engineer_build.md)).

* **The table.** 43,089 player-matches, 42,900 in use.
  * Men's sources:
    * ManTennisData: 19,707;
    * Slam point feeds (Sackmann, Hawk-Eye copies, SlamTracker, AO/RG Infosys 2025–26): 11,362;
    * the ATP handoff's key statistics: 370;
    * AO match centre: 474;
    * Infosys and SirGenkii points: 36.
  * Women: Slams only, 10,951. No WTA tour-level speed exists anywhere.
* **One value per player-match.**
  * At tour level the ATP key statistic comes first, minus 0.5 km/h: on complete point tables it is the point mean rounded up in 81.5% of matches. This keeps training and test rows on the same basis, because 2025–26 tour data are almost all key statistics.
  * At the Slams the point mean comes first.
* **Dropped:**
  * implausible values (27 broken ManTennisData values of 54–119 km/h);
  * fewer than 10 timed serves;
  * mislinks. These include 10 quarter-finals that the acquisition's table labels as qualifying (§9).
* **Measuring systems differ, and they break inside the test years** (same men, median change):
  * Wimbledon 2024→25: +8.5 km/h (every court timed from 2025);
  * AO 2023→24: +3.5;
  * US Open 2025→26: +9.7. The model frame ends with events starting by 28 Jul 2026, so this one does not reach the test.
  * Tour events also differ: persistent SD 1.7 km/h, year-specific 1.0. Qualifying reads 1.3–3.7 km/h slower than main draws.
* **The fix: as-of edition offsets.**
  * For every match, each earlier speed is centred on its event-edition's offset (event × year × main/qualifying × basis).
  * The offset is fitted with a player-plus-edition model on the matches that **surely finished before this match could start** (`lf + 1 ≤ es`, the project's leak-proof clock).
  * A new edition is learned within 1–3 days.
  * On a result-free target that cannot reward carried artefacts (the A − B speed difference within the next match), this beat frozen offsets for men in 2023: by +4.47 km/h² of mean squared error [+2.19, +6.75], as-of better.
* **Coverage of men's model matches** (both players timed within 28 days / at least one): 2024 79% / 95%, 2025 74% / 90%, 2026 78% / 93%. The old 14-day window had both sides in 61%, 50% and 52%.

## 3. The feature: what it is and how it handles thin data

*Observed* (`src/eda/serve_speed_tabpfn/features.py`; [design](../../../data/studies/serve_speed_tabpfn/design/1_modeller.md), [ruling](../../../data/studies/serve_speed_tabpfn/design/2_audit.md)).

**The model of a player's speed.** Each timed match gives a centred first-serve average z. The model is z = L + f + noise:
* **L is his normal level.** It drifts slowly as a random walk, 4 km/h² a year.
* **f is his current form.** It decays toward 0 with a **14-day half-life**, with variance 12 km/h².
* **The noise depends on the data:**
  * a match-day term, 7 km/h² for point means and 8 for key statistics;
  * sampling noise of 13.5² km/h² divided by the number of timed first serves.
* **Robustness.** A reading more than 2 SD from expectation is clipped, so one broken value cannot swing a player.
* **The constants.** They were tuned on seasons ≤ 2022 by predicting the next match's speed, checked on 2023, and frozen.

**The feature.** A Kalman filter runs over each player's own matches of the last 364 days before the match and returns the posterior mean of his current form, f̂, at the match's earliest possible start. The column is:

&nbsp;&nbsp;&nbsp;&nbsp;**`spd_f` = (f̂_A − f̂_B) / 2.224 km/h**, clipped at ±4.

**The priors and the imputation.**
* **A thin record shrinks itself.** One match is about half noise, so a single fast match moves f̂ about half way. Several confirming matches move it further.
* **No recent match means f̂ drifts back to 0.** "No known change" is the prior. f̂ is near 0 within about six weeks.
* **A player never timed has f̂ = 0.** So the column is never missing. It is non-zero on 7,066 of 7,068 men's test matches.
* **The level's prior is uninformative.** A population or height prior would leak speed *level* into the *change*: correlation 0.51 with the career level, against 0.14 uninformative.
* **Evidence that 0 is the right value** (*observed*, 2023). The slopes of the next match's within-match speed difference on f̂ are 0.68–0.97 whether both, one or neither player was timed within 14 days (0.87 / 0.97 / 0.68). Even decayed values carry information.

**Women.** Their speeds exist only at Slams, and their signal appears only within a Slam. The primary column is men-only; women are 0. A secondary arm (A3) carries women's values.

**What it predicts, before any match result** (*observed*; statistic targets on ≤ 2023, logged in the [look ledger](look_ledger.md)):
* **Next-match speed.** Out-of-sample R² 0.051 [0.030, 0.074] against the published window's 0.019 [−0.002, 0.052], filter better.
  * That is the R1 frozen-offset version, on a per-player target the audit found biased toward carried edition effects.
  * On the audit's clean within-match target the two full speed forecasts tie: window − filter −2.12 [−6.24, +1.92] km/h² of MSE; negative = window better.
* **Next-match serving, beyond his box-score serve form, with event-edition fixed effects** (men 2022–23; per SD of his speed state, 1.12 km/h; positive = he serves better):
  * first-serve points won +0.33 pp [+0.20, +0.46];
  * from earlier events only +0.32 [+0.09, +0.55];
  * service points won +0.11 [+0.02, +0.20].
* **New to the model and the market.** On 2022–23 it explains R² 0.12 on the 58 inputs and 0.003 on the closing odds (R1 version, in sample).

**Leak-proof.**
* Own history runs in order, and every pooled quantity follows the clock.
* Two probes were run: one replaced speeds after a cut in the match order, the other after a cut day, with noise. They were run by the builder (26 cuts each) and independently by the red team (30 each). **No value of an earlier match moved.** The red team's deliberately leaky controls fired at every cut; the builder's fired at 24 of 26 order cuts and on 16 of 26 days.
* The red team rebuilt all three columns without importing the build: **identical to 2e-14** on all 63,737 matches.

## 4. How it enters the model

The current best is the local, non-thinking TabPFN-3.5 with 58 inputs (closing odds included), the model of the owner's decisions of 6 Oct 2026.

| Arm | Inputs | Purpose |
|---|---|---|
| **A1 `spd`** | 58 + `spd_f` | **The primary** |
| A2 `spd_raw` | 58 + the registered 14-day statistic, on the new data | Does the new data alone help? |
| A3 `spd_all` | 58 + `spd_f` with women's Slam values | Do women's values help women, or dilute men? |
| A1 no-odds | 57 + `spd_f` | For betting before the close |

**The settings.** 8 estimators, temperature 0.9, 16 seeds (A1) or 8 (others) in 2024–26, and 4 seeds in 2019–23 for calibration. That is 223 fits, about 2 GPU hours.
* The base model's existing fits were reused after three reproduction fits matched them **bit for bit** (maximum difference 0.0).

## 5. The test (expanding window, pre-registered)

* **The expanding window.** Each test season Y in 2024, 2025 and 2026 is predicted by fits trained on 2013 to Y − 1.
* **Calibration** follows the decided convention: one slope per tour, refitted for each Y on the arm's own out-of-sample seasons 2019 to Y − 1.
* **The primary, P2.** The calibrated paired log-loss gain of A1 over the base, men 2024–26, debut seasons out: 7,068 matches.
  * Its interval adds the seed-to-seed variance to a four-week-block interval.
  * It is conservative near 0: the verifier measured a 0.35–0.75% false-positive rate against a nominal 5%. A block-only interval is reported beside it.
* **The secondaries.** S0–S14 are descriptive (§6). One confirmatory test means no correction. The count of secondary intervals that exclude 0 is read against a simulated null.
* **Not blind.**
  * 2024 was in the published 2022–24 replication.
  * The base's 2025–26 forecasts had been scored by the feature-interactions final test.
  * The shot-level study once scored its old, sparse speed feature against the close over 2022–26.
  * **The new coverage had never been related to any 2024–26 result.**
* **Power, stated before the run** (*inferred*, synthetic). For an effect of 0.09 per unit of `spd_f` (numerically the published value, which was per SD of x_raw), the TabPFN column had roughly 43–76% power at a capture of 1.0–0.5. The information test S0 had 93%.
  * The observed capture, 8% (§6.3), was far below the 0.5–1.0 assumed.

## 6. Results

All rows are *observed* (`results.json`, `results.csv`); men 2024–26 unless stated.

### 6.1 The primary: the speed column in TabPFN

| | mLL (positive = with speed better) | Reading |
|---|---|---|
| **P2, registered interval** | **+0.07 [−0.05, +0.18]** | **Tie** |
| P2, block-only interval (S11) | +0.07 [−0.02, +0.15] | Tie |
| P2, calendar-week interval (S11) | +0.07 [−0.05, +0.18] | Tie |
| P2 on the Brier score (S14; positive = with speed better, 1000 × Brier) | +0.03 [−0.02, +0.07] | Tie |
| P2 on raw, uncalibrated forecasts (S7) | +0.09 [−0.04, +0.23] | Tie |
| P2 as a share of the model's edge over the close (S13, point value) | 3% | – |

**By season** (S1) and **the blind seasons** (S2). Every row ties; the column is slightly positive in every season.

| Season | Matches | mLL (positive = with speed better) |
|---|---|---|
| 2024 (not blind) | 2,674 | +0.10 [−0.13, +0.32], tie |
| 2025 | 2,620 | +0.01 [−0.12, +0.13], tie |
| 2026 (to early August) | 1,774 | +0.11 [−0.19, +0.40], tie |
| **2025–26 (S2)** | 4,394 | +0.05 [−0.08, +0.17], tie |

**By recency** (S3). Both sides timed within 28 days: +0.06 [−0.08, +0.20]. One side: +0.08 [−0.15, +0.32]. Neither, the harm check: +0.08 [−0.24, +0.39]. All tie.

### 6.2 Is the information there? Yes

| Test | Coefficient (positive = the faster-trending man wins more than the model says) | Reading |
|---|---|---|
| **S0**: `spd_f` beyond the base's forecast, men 2024–26 | **+0.065 [+0.012, +0.118]** per unit (2.224 km/h), p 0.017 | **Excludes 0** |
| **S12**: the registered 14-day statistic on the new data, 2025–26 only (blind) | **+0.103 [+0.029, +0.178]** per 5.998 km/h, p 0.009 | **Excludes 0**; the published 2022–24 value was +0.090 |

* **Size** (*inferred*). In a 50–50 match, one unit (2.2 km/h of relative speed form) moves the win chance by about 1.6 points. A 5 km/h edge moves it by about 3.6 points, beyond what the model already says.
* **These tests read the information, not the TabPFN column.** They regress the result on the column with the base model's log-odds as controls (a slope per season and a cubic).

### 6.3 Why the column does not deliver: TabPFN barely uses it (S10)

* TabPFN's own adjustment toward the faster-trending player is **0.005 log-odds per unit**, against the 0.065 that is there. That is a **capture of 8%** (7% on the calibrated scale). It is a point value; across S0's interval it runs from about 4% to 42%.
* *Inferred:* the signal is weak, and the training data barely show it, so TabPFN's prior treats the column as near-noise.
  * In the 2024 fit's training rows, only 24% of men's matches have both players timed within 28 days (42% at least one). In the 2026 fit it is 33% (51%). Before 2022 it is mostly Slam rounds (*observed*).
  * The feature-interactions study also saw partial capture: its B-INJ was captured at 39%.
* The other column arms behave alike (S8). All tie under the registered interval.
  * The registered statistic: +0.10 [−0.07, +0.26].
  * With women's values, scored on men: +0.15 [−0.04, +0.34].
  * A1 against A2: +0.01 [−0.16, +0.17].
  * A3 against A1: +0.04 [−0.11, +0.20].
  * Positive = the first-named arm better throughout.

### 6.4 The nudge: the same information applied directly (S9)

**The nudge.** The forecast becomes logit q = s·η_model + b̃_Y·`spd_f`.
* η_model is the TabPFN model's log-odds, and s is its calibration slope.
* b̃_Y is fitted only on seasons 2019 to Y − 1, the same expanding window, and shrunk toward 0.
* The fitted b was 0.040 / 0.040 / 0.045 for 2024 / 2025 / 2026 (shrunk: 0.030 / 0.033 / 0.039).

| | mLL (positive = the nudge better than the calibrated model) | Reading |
|---|---|---|
| **Shrunk (pre-registered τ = 0.05)** | **+0.41 [+0.04, +0.78]** | **Better** |
| Unshrunk | +0.45 [+0.002, +0.91] | Better (lower bound +0.002) |

* That is about **19% of the model's edge over the close** (+0.41 of +2.20 mLL; a descriptive ratio).
* It is a pre-registered secondary with a block-only interval (the same base forecasts on both sides).
* *Inferred:* it fits the information test. With b ≈ 0.035 against S0's 0.065, the expected gain is about 0.4 mLL.

### 6.5 Women, no odds, Polymarket's early price

| Row | mLL (positive = the speed arm better) | Reading |
|---|---|---|
| Women, A3 (their Slam values) against the base (S4) | +0.04 [−0.11, +0.18]; without the 21 id-conflict matches +0.04 [−0.11, +0.19] | Ties |
| Women, A1 (women 0; a check that the men's column does no harm) | +0.02 [−0.07, +0.11] | Tie |
| Both tours, A1 (S4) | +0.04 [−0.03, +0.11] | Tie |
| **Without the closing odds** (S5): no-odds A1 against the no-odds base | −0.01 [−0.22, +0.20] | Tie |
| **At Polymarket's price 24 hours before the start** (S6a), men 2025–26, 1,442 matches; clean event openers 582 | +0.15 [−0.11, +0.40]; openers +0.11 [−0.25, +0.47] | Ties |
| Did the price move from 24 h to 30 min toward the speed view? (S6b; slope, positive = toward) | +0.78 [−1.09, +2.64]; no-odds −0.19 [−1.22, +0.84]; openers +3.19 [−2.12, +8.50] / +0.95 [−0.30, +2.20] | Ties |

### 6.6 Multiplicity

* 4 of the 30 counted secondary intervals exclude 0: S0, the two nudges and S12.
* Under the verifier's simulated null, 3 or more happens 5.0% of the time and 4 or more 1.7%.
* The four are not independent: they all read the same coefficient-type information.

## 7. What it means

**Observed.**
* **The speed state is real information beyond the model, which already holds the closing odds,** and it replicated out of sample: S0 (2024–26) and S12 (blind 2025–26).
* **The pre-registered integration, one more TabPFN column, does not measurably improve the score.**
  * +0.07 mLL, a tie; TabPFN uses about 8% of the information.
  * The test was built so that this reading (row 3) is not "no signal". *Inferred:* the column's power falls when the signal is weak and TabPFN uses little of it.

*Inferred.*
* **The right integration is outside TabPFN: a walk-forward logistic nudge on its log-odds.**
  * It is cheap and transparent, and it re-fits each season on earlier seasons only.
  * In the expanding window it added +0.41 [+0.04, +0.78] mLL, about a fifth of the model's lead over the close.
  * That is on top of a model that already holds the closing odds. It is the size of the best single features this project had found before (0.25–0.4 mLL, the point-sequence study's summary).
* **It still needs confirmation.** It is a secondary, and its interval clears 0 only modestly.

**Suggestions** (none decided):
1. **Adopt "speed as a nudge"** as the candidate integration: `spd_f` as built here, b fitted walk-forward with τ = 0.05 shrinkage. Confirm it with a pre-registered prospective test on matches after 7 Oct 2026, with the nudge as the primary.
2. **Keep the data current.** A weekly ManTennisData refresh (the acquisition study's option 2) and AO/RG 2027 (option 4). The nudge is only as good as the 2026–27 coverage.
3. **Improve TabPFN's capture,** if a column is preferred. Ideas: train on seasons where speed exists, or decrypt the ATP's 2015–20 files (the acquisition study's option 5, the owner's call). More training rows with speed might lift capture.
4. **Women:** no use for now. Their speeds exist only at Slams, and nothing improved.
5. **Before the close:** speed showed no detectable gain (ties) without the odds or at the 24-hour price (S5, S6). The nudge was not tested at the early price; that is worth a look in the prospective test.

**Process suspects for the column's tie,** per the owner's premise:
* capture (the main one);
* the key-statistic error tail: about 4–7.5% of tour matches are more than 10 km/h off;
* AO 2024's measuring break, which the as-of centring absorbs less well than the others;
* seed count.

## 8. How the team worked

The configuration was fixed in advance ([team.md](team.md)). Each agent was an Opus 5.5 instance, and every file is kept in `data/studies/serve_speed_tabpfn/design/`.

| Agent | What it did | What it changed |
|---|---|---|
| **Speed-data engineer** | R1 proposal; built the panel, the as-of offsets and the frame join (10 tests) | Found the measuring breaks in the test years, the key statistic's ceiling rule, the QF label bug and the women's 2026 id conflicts |
| **Bayesian state modeller** | R1 proposal; built the filter, both probes and the columns (10 tests) | The two-state filter; never-NaN with a shrinking prior; the mechanism gate |
| **Integration strategist** | R1 proposal; built the fit runner, the scorer and the draft pre-registration (29 tests) | The redundancy and price looks; the power simulations; the single-column design |
| **Auditor and red team** | R2 ruling on every conflict; R4 independent rebuild and probes | Overturned the modeller's "centring doesn't help" (a biased target); made P2 alone the primary; found that the rating race's reused base fits (seeds 0–2) carried no fingerprints, so they were reproduced first |
| **Test verifier** | R4 checks of the scorer on synthetic outcomes; a re-check after fixes | Caught an invalid secondary (S6b rejected a true null 24–43% of the time), a run-spending bug and three misleading texts; all fixed before the hash |

The **lead** wrote the brief, relayed between agents, kept the [look ledger](look_ledger.md), ran all 223 GPU fits and the one scoring run, and wrote this report. There was no rebuttal round: the audit's conditions for changing a ruling were already contradicted by its own measurements ([lead notes](../../../data/studies/serve_speed_tabpfn/design/lead_notes.md)).

**Discipline.** Before the hash, no speed feature was related to any match result in any season. Design choices used result-free targets on seasons ≤ 2023: next-match speed and serve statistics. The test read results once.

## 9. Side findings (defects found on the way; not fixed here)

| Defect (observed) | Where | Effect here |
|---|---|---|
| ManTennisData quarter-finals ("QF") are labelled qualifying (`startswith("Q")`) in all 1,426 rows | `src/eda/serve_speed_acquisition/speeds.py` (line 227) | 10 rows mislinked; the panel drops them by checking the round. **Fixed upstream on 7 Oct 2026, after this study's run.** The label caused 8 of the 10, which now link to their own quarter-finals. The other 2 (Jodar–Fils, Canada 2026, on the pair's Washington R32) are a date tie in the linker, and the round check still drops them ([acquisition, section 5](../serve_speed_acquisition/README.md#5-limits)). A rebuild of this panel would make T-P5's count 2 |
| 88 women's 2026 model-frame matches carry other player ids than the rebuilt Stage 0: 67 conflicts, 21 sides flipped | the model frame (30 Sep Stage 0 snapshot) | Women's A1 is 0; A3 reported with and without them (21 in the scored population) |
| The model frame has no men's 2018 matches, and ends with events starting by 28 Jul 2026 | `surface_rating_race/model/model_frame.parquet` | Inherited by every arm |
| The rating race's base fits (seeds 0–2) store no fingerprint | `data/studies/surface_rating_race/local/` | Reproduced bit for bit before reuse |
| An earlier proposal's price-move regression (S6b) gives false positives in 24–43% of null replicates | this study's draft | Replaced before the hash by the verifier's corrected version |

## 10. Limitations

* **One confirmatory test, and it tied.** The nudge's gain is a secondary, and its interval's lower bound is only +0.04.
* **2024 is not blind.** 2025–26 is blind for the new coverage only.
* **2026 is partial,** to early August.
* **Closing prices are archived average closes,** not executable bet-time prices. A log-loss gain is not a betting return.
* **The key statistics carry an error tail** (4–7.5% of tour matches more than 10 km/h off), the same in training and test.
* **No WTA tour-level speed exists.**
* **The local TabPFN is the open checkpoint,** not the API's Thinking mode.

## 11. Files and reruns

| What | Where |
|---|---|
| Brief, team, pre-registration (+ `.sha256`), look ledger | `docs/studies/serve_speed_tabpfn/` |
| Design rounds: proposals, audit, rulings, build notes, red team, verifier | `data/studies/serve_speed_tabpfn/design/` |
| Code | `src/eda/serve_speed_tabpfn/`: `panel.py`, `features.py`, `common.py`, `arms.py`, `local_fits.py`, `forecasts.py`, `score.py` |
| Tests (49) | `test/serve_speed_tabpfn/` |
| Panel, features, fits, results | `data/studies/serve_speed_tabpfn/`: `speed_panel.parquet`, `features/speed.parquet` (+ `speed_meta.json`), `local/` (223 fits), `results.json`, `results.csv`, `check.json`, `logs/` |

```
./python.sh src/eda/serve_speed_tabpfn/panel.py          # the panel (about 30 s)
./python.sh src/eda/serve_speed_tabpfn/features.py       # the columns and probes (about 3 min)
./python.sh -m pytest test/serve_speed_tabpfn -q         # 49 tests
./python_tabpfn_local.sh src/eda/serve_speed_tabpfn/local_fits.py --run --jobs all   # GPU, about 2 h
./python.sh src/eda/serve_speed_tabpfn/score.py --check  # result-free
```

`score.py --run` refuses to run again: `results.json` exists.
