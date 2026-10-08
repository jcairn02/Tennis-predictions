# Latency follow-up: feature variants and result-free readings (agent 2, modeller)

7 October 2026. Written **before** the lead's outcome run; the nowcast design below is fixed as built. All numbers are **observed** unless marked *inferred*.

No match result was read. Statistic targets were used only on ≤ 2023, and 2024–26 only as values. No GPU was used. `features.py` and `panel.py` are unedited; their SHA-256 values are in the metadata.

## Built

* **Code:** `src/eda/serve_speed_tabpfn/latency/features_latency.py`. It runs in 3 minutes with the probes and reuses the study's histories, snapshots and filter by import.
* **`latency/variants.parquet`:** `match_id` plus 11 columns `spd_<scenario>_<method>`.
  * Each is clip(Δf̂ / its own SD over men's 2022–23 frame matches, ±4).
  * Women are 0, and no value is NaN.
* **`variants_meta.json`:**
  * the constants and SDs;
  * the nowcast's coefficients and noise;
  * the M1 / M2 grids;
  * the Probe B records;
  * the input and code hashes.
* **`readings.json`:** all the readings below.
* **Tests:** `test/serve_speed_tabpfn/test_ssp_latency_features.py`, **10 passed**.

### Scenarios and methods

* **A** is the backtest as run: own history by order, snapshots at lf + 1. **`spd_A_M0` equals `spd_f` exactly** on all 63,737 matches.
* **B and L1/L3/L7/L14:** a row enters a history only if `release ≤ es` *and* it passes the order rule. The edition snapshots are refitted on released rows only. Release days come from the engineer's `availability.parquet`.
* **Astrict** (descriptive) is lf + 1 applied to own history too. It drops a same-event row on 4.9% of men's sides, an artefact of the clock's windows.
* **M0:** constants as built.
* **M1:** the half-life alone, on a grid of 3–60 days.
* **M2:** the nowcast below.

**Tuning criterion for M1 and M2.** The column's own information on T1 (men 2019–22, with 2023 as the check):

gain = MSE(T − ΔL̂_A) − MSE(T − ΔL̂_A − b·Δf̂)

* T is the within-match A − B first-serve speed difference, and ΔL̂_A the instant level.
* I did not use T1's full-forecast MSE, because it also rewards the level, which is not in the column. Under it, M1 would choose 42 days and *lose* on the 2023 check (164.20 → 165.40 km/h²).
* Both grids are stored.

## The nowcast (M2): design

**What enters.** A history match whose speed is not yet released at `es`, but whose box score is (`box_release` = lf + 1 ≤ es), enters as a pseudo-observation of its centred speed:

> z_nc = L + a·f_pred + c0 + β′d, with noise variance R_nc

* (L, f_pred) is the filter's state just before that match.
* d is the match's box rates minus the player's own rates over his earlier box matches within 364 days (own order; at least 150 service points and 3 matches):
  * aces, double faults and first serves in per service point;
  * first-serve points won per first serve in;
  * second-serve points won per second serve;
  * log service points.
* Box scores are read with explicit columns: `ace, df, svpt, first_in, first_won, second_won, has_box`, never `won`.

**Estimation.** OLS on men's timed matches as targets of the instant filter, with ≤ 2022 for the fit (7,759 matches) and 2023 for the check (4,125).
* The target is u = the match's centred speed minus the level L̂ from the player's earlier rows.
* Coefficients:

  | c0 | a | ace | df | first in | first won | second won | log svpt |
  |---:|---:|---:|---:|---:|---:|---:|---:|
  | 0.02 | 0.931 | +17.4 | −15.8 | −14.4 | +4.4 | −1.3 | +0.13 |

* Edition fixed effects barely move β, so it is not driven by playing conditions.
* **Fit:** R² 0.132 on ≤ 2022. On 2023 it is **0.072, against 0.042 without the box score**. The residual variance is 29.0 km/h².

**Noise.** R_nc is the residual variance times a factor, by the criterion above. B: ×1.5 = **43.6 km/h²**. L7: ×1.0 = **29.0**. A real point-mean row has a noise of about 11.

**One rule, added after the first tuning.** A nowcast row counts only after the side's first released speed. Without it, a leading nowcast fixed the diffuse level near 0 km/h, and the first tuning hit the grid's edge. A test now holds this rule.

**Scope.** Only timed matches whose speed is late are filled; untimed events stay out, so A is unchanged. Under B, 45% of men's 2024–26 sides use at least one nowcast row (L7: 50%).

## Result-free readings

* **T1:** the information Δf̂ adds beyond A's level about the within-match speed difference, in km/h². Positive = it adds information; the 2023 interval is a four-week-block bootstrap. Share = gain / A's gain. The 2019–22 share is in-sample for M1 / M2.
* **Gate:** pp per SD of the variant's f̂ on first-serve points won, men 2022–23 (29,514 matches), with target-edition fixed effects and A's level as a control. The ratio to A is in brackets. Service points won and aces are in `readings.json`.
* **2024–26 (values only):** the correlation with A's `spd_f`, and the SD in km/h. The non-zero share is ≥ 0.9994 for every variant.

| Variant | T1 gain 2023 | Share 2023 | Share 2019–22 | Gate: first-serve won | Corr with A | SD |
|---|---|---:|---:|---|---:|---:|
| **A_M0** | 4.91 [1.02, 8.53] | 1.00 | 1.00 | +0.33 [+0.21, +0.45] | 1.000 | 2.49 |
| Astrict_M0 | 3.77 [0.39, 7.36] | 0.77 | 0.86 | +0.29 (0.89) | 0.965 | 2.39 |
| L1_M0 | 2.64 [−0.77, 5.90] | 0.54 | 0.75 | +0.28 (0.85) | 0.872 | 2.15 |
| L3_M0 | 1.81 [−0.98, 4.64] | 0.37 | 0.65 | +0.24 (0.74) | 0.765 | 1.86 |
| L7_M0 | 0.89 [−2.66, 4.12] | 0.18 | 0.46 | +0.17 (0.51) | 0.637 | 1.52 |
| L14_M0 | −0.41 [−2.25, 1.52] | −0.08 | 0.34 | +0.20 (0.61) | 0.476 | 1.06 |
| **B_M0** | 0.84 [−2.99, 4.26] | 0.17 | 0.58 | +0.23 [+0.12, +0.33] (0.69) | 0.685 | 1.66 |
| B_M1 (h 28) | 1.04 [−2.85, 4.54] | 0.21 | 0.62 | +0.25 (0.77) | 0.673 | 2.15 |
| **B_M2** | 1.18 [−2.84, 4.84] | 0.24 | 0.60 | +0.24 [+0.13, +0.36] (0.74) | 0.706 | 1.68 |
| L7_M1 (h 28) | 1.09 [−2.54, 4.34] | 0.22 | 0.50 | +0.21 (0.64) | 0.628 | 2.07 |
| L7_M2 | 1.25 [−2.66, 4.64] | 0.26 | 0.50 | +0.20 (0.60) | 0.667 | 1.57 |

* Ratios to A on service points won and aces: B_M0 0.90 and 0.59; B_M2 0.92 and 0.60.
* On the 2023 T1, every lagged variant ties with 0. One season cannot rank them.

**Reading (*inferred*).**
* **Today's sources (B) keep about 60% of A's T1 information** (2019–22), and 0.6–0.9 of its per-SD gate effects.
* What is lost is mainly the previous round of the same event: under B it is usable for under 0.5% of those sides, per the engineer.
* **The nowcast recovers a little.** On B it moves the 2023 share from 0.17 to 0.24, the first-serve ratio from 0.69 to 0.74, and the correlation with A from 0.685 to 0.706. A re-tuned half-life recovers about as much.
* A box score is a weak stand-in for a radar reading: it adds 0.03 R² beyond the filter's own state.
* If the nudge's gain scales with the square of the per-SD effect, live B keeps roughly half or more of A's +0.41 mLL. Only the outcome run can say.

## Probe B (release days honoured), B_M0 and B_M2

* **Days (19):** the timing probe's four, every 2024–26 Slam second Wednesday in the frame, and 6 random days.
* **Noise on day D:** speeds released after D are noised in both the filter and the snapshots. For M2, every box score released after D is redrawn too.
* **Checked:** every men's frame side with **es ≤ D** (stricter than lf ≤ D), on f̂, σ̂, L̂ and the γ̂ used.
* **Result: 0 moved. PASS for both.**
* **Leaky control** (rows admitted at lf + 1): 3,393 sides moved.
* Under lf + 1 no nowcast row can exist, so the box path is exercised by the main check only.

## Caveats

1. The readings use A's level as the common reference, so variants differ only in Δf̂, the column the nudge uses.
2. 2023 is one season, and its T1 intervals span 0 for every lagged variant.
3. The nowcast is linear with one noise; richer versions (opponent-adjusted rates, noise by recency) were not tried.

## Looks

| # | Seasons | What was related to what |
|---|---|---|
| L1 | Men ≤ 2022, check 2023 | Statistic target: a timed match's centred speed minus the instant level, against the prior f̂ and box deviations (nowcast OLS, with and without edition FE). Also in a scratchpad exploration of the same fit |
| L2 | Men 2019–22, check 2023 | T1 grids for M1 (half-life) and M2 (noise), by information gain and by full-forecast MSE |
| L3 | Men 2019–23 | T1 against every variant's Δf̂ beyond A's level |
| L4 | Men 2022–23 | Gate: aces, first-serve points won and service points won against each variant's f̂, edition FE |
| L5 | 2024–26 | Values only: correlations with A, SDs, non-zero and nowcast shares |

No variant was related to a result, a price or an outcome.
